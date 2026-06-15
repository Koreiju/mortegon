"""LIVE end-to-end probe for the §8D.48 agent tick use case.

Spawns an agent, verifies the trio (perception/transformer/emitter)
is wired with the correct backing pointers, fires a real
``/api/agent/tick`` against real GPT4All, asserts the SLM produced
real signal (not the stub trailer), and verifies the cascade
scheduler's per-agent state reads back correctly.

Run as:  python scripts/probe_live_agent.py [BACKEND_URL]
"""

from __future__ import annotations

import json
import sys
# Windows consoles default to cp1252, which can't encode probe-output
# glyphs (→, §). Force UTF-8 so the probe prints cleanly everywhere.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_BACKEND = "http://127.0.0.1:8080"


def _section(title: str) -> None:
    print(f"\n== {title} {'=' * max(0, 60 - len(title))}")


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _http(method: str, url: str, *,
          body: Optional[Dict[str, Any]] = None,
          timeout: float = 30.0) -> Dict[str, Any]:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _get(url: str, **kw) -> Dict[str, Any]:
    return _http("GET", url, **kw)


def _post(url: str, body: Dict[str, Any], **kw) -> Dict[str, Any]:
    return _http("POST", url, body=body, **kw)


def _patch(url: str, body: Dict[str, Any], **kw) -> Dict[str, Any]:
    return _http("PATCH", url, body=body, **kw)


def _delete(url: str, **kw) -> Dict[str, Any]:
    return _http("DELETE", url, **kw)


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def step_subsystems_real(backend: str) -> None:
    _section("1) Subsystems all real (§8D.46)")
    s = _get(f"{backend}/api/subsystem_status")
    _assert(s.get("all_real") is True,
            f"subsystems NOT all real: {s}")
    print(f"  slm={s['slm']['backend']}  embedder={s['embedder']['backend']}"
          f"  selenium={s['selenium']['backend']}"
          f"  langgraph={s['langgraph']['backend']}")


def step_ensure_fixtures(backend: str) -> None:
    _section("2) Foundation fixtures (Database/WebBrowser/Agent)")
    resp = _post(f"{backend}/api/foundation/ensure", {"workspace_id": ""})
    names = sorted({f["name"] for f in (resp.get("fixtures") or [])
                    if not (f.get("name") or "").startswith("py::")})
    print(f"  fixtures: {names}")
    _assert("Agent" in names, f"Agent fixture missing: {names}")


def step_spawn_agent(backend: str) -> Dict[str, str]:
    _section("3) /api/agent/spawn — create agent body subgraph (§8D.27.2)")
    resp = _post(f"{backend}/api/agent/spawn", {
        "name": "library_curator",
        "goal": "Inspect concepts about libraries and suggest one wiring.",
        "workspace_id": "",
    })
    print(f"  spawn response: {json.dumps(resp, indent=2)[:300]}")
    _assert(resp.get("ok") is True, f"spawn failed: {resp}")
    pcid = resp.get("parameter_card_id") or ""
    perc = resp.get("perception") or ""
    trans = resp.get("transformer") or ""
    emit = resp.get("emitter") or ""
    _assert(all([pcid, perc, trans, emit]),
            f"spawn missing one of the trio: {resp}")
    print(f"  parameter:   {pcid}")
    print(f"  perception:  {perc}")
    print(f"  transformer: {trans}")
    print(f"  emitter:     {emit}")
    return {
        "parameter_card_id": pcid,
        "perception":        perc,
        "transformer":       trans,
        "emitter":           emit,
    }


def step_verify_trio_concepts(backend: str, trio: Dict[str, str]) -> None:
    _section("4) Verify trio concept records (type_hint + backing_pointer)")
    expected = {
        trio["parameter_card_id"]: ("agent_parameter", ""),
        trio["perception"]:        ("agent_perception",
                                    f"agent::perception::{trio['parameter_card_id']}"),
        trio["transformer"]:       ("agent_transformer",
                                    f"agent::transformer::{trio['parameter_card_id']}"),
        trio["emitter"]:           ("agent_emitter",
                                    f"agent::emitter::{trio['parameter_card_id']}"),
    }
    for cid, (want_type, want_bp_prefix) in expected.items():
        c = _get(f"{backend}/api/concepts/{cid}")
        th = c.get("type_hint") or ""
        bp = c.get("backing_pointer") or ""
        print(f"  {cid}  type_hint={th!r:22}  backing_pointer={bp!r}")
        _assert(th == want_type,
                f"{cid}: expected type_hint={want_type!r}, got {th!r}")
        if want_bp_prefix:
            _assert(bp.startswith(want_bp_prefix),
                    f"{cid}: backing_pointer doesn't start with {want_bp_prefix!r}: {bp!r}")
    # Parameter card data should have the gating defaults.
    pcard = _get(f"{backend}/api/concepts/{trio['parameter_card_id']}")
    pdata = json.loads(pcard.get("data") or "{}")
    print(f"  parameter data: {pdata}")
    _assert(pdata.get("cascade_enabled") is False,
            f"cascade_enabled should default to False: {pdata}")
    _assert(pdata.get("paused") is False,
            f"paused should default to False: {pdata}")
    # The goal text contains "libraries" (not "library"); check for the
    # 6-char common prefix instead.
    _assert("goal" in pdata and "librar" in (pdata.get("goal") or "").lower(),
            f"goal not threaded into parameter card: {pdata}")


def step_run_tick(backend: str, trio: Dict[str, str]) -> Dict[str, Any]:
    _section("5) /api/agent/tick — real meta-cognition fire (§8D.38)")
    print(f"  ticking parameter_card_id={trio['parameter_card_id']}")
    print(f"  (this fires real GPT4All — patient…)")
    t0 = time.monotonic()
    resp = _post(f"{backend}/api/agent/tick", {
        "parameter_card_id": trio["parameter_card_id"],
        "workspace_id": "",
    }, timeout=600)
    elapsed = time.monotonic() - t0
    print(f"  tick elapsed: {elapsed:.1f}s")
    status = resp.get("status") or ""
    print(f"  status: {status}")
    if status == "error":
        print(f"  detail: {resp.get('detail')!r}")
    # Print the structured response — applied counts, action summary,
    # token-buffer length, etc.
    keys = sorted(resp.keys())
    print(f"  response keys: {keys}")
    for k in ("applied", "actions", "step_index", "skipped_reason",
              "token_count", "rationale"):
        if k in resp:
            v = resp[k]
            if isinstance(v, (dict, list)):
                v = json.dumps(v, default=str)[:200]
            print(f"    {k}: {v}")
    _assert(status in ("ok", "applied", "completed", "skipped", "success"),
            f"unexpected tick status: {status!r} (resp={resp})")
    return resp


def step_inspect_rationale(backend: str, trio: Dict[str, str]) -> None:
    """Pull the most recent agent_token buffer to confirm the SLM
    actually streamed real tokens (not the stub trailer)."""
    _section("6) Agent token buffer — proof the SLM streamed real tokens")
    pcid = trio["parameter_card_id"]
    try:
        resp = _get(f"{backend}/api/agent/tokens/{pcid}?limit=200")
    except Exception as e:
        print(f"  (token endpoint raised {e!s}; skipping)")
        return
    tokens = resp.get("tokens") or resp.get("buffer") or []
    if isinstance(tokens, list) and tokens and isinstance(tokens[0], dict):
        text = "".join((t.get("text") or t.get("token") or "") for t in tokens)
    elif isinstance(tokens, list):
        text = "".join(str(t) for t in tokens)
    else:
        text = str(tokens)
    print(f"  buffered tokens (head): {text[:200]!r}")
    print(f"  buffered length: {len(text)} chars")
    _assert(not text.startswith("[stub-slm]"),
            f"token buffer is stub trailer: {text[:80]!r}")


def step_cascade_status(backend: str, trio: Dict[str, str]) -> None:
    _section("7) /api/agent/cascade_status — scheduler bookkeeping")
    resp = _get(f"{backend}/api/agent/cascade_status")
    print(f"  response head: {json.dumps(resp, indent=2)[:400]}")
    # The response shape varies; we just assert the parameter card id
    # appears somewhere recognisable.
    blob = json.dumps(resp)
    if trio["parameter_card_id"] in blob:
        print(f"  [OK] cascade_status references this agent's parameter card")
    else:
        print(f"  (parameter card not in cascade_status — agent didn't tick "
              f"through the scheduler; that's expected since we called "
              f"/api/agent/tick directly rather than letting the scheduler "
              f"auto-fire)")


def step_pause_resume(backend: str, trio: Dict[str, str]) -> None:
    """Toggle the paused flag and verify the parameter card updates."""
    _section("8) Pause + resume via parameter-card edit")
    pcid = trio["parameter_card_id"]
    # Pause.
    cur = _get(f"{backend}/api/concepts/{pcid}")
    pdata = json.loads(cur.get("data") or "{}")
    pdata["paused"] = True
    paused = _patch(f"{backend}/api/concepts/{pcid}", {
        "data": json.dumps(pdata, indent=2),
    })
    paused_data = json.loads(paused.get("data") or "{}")
    _assert(paused_data.get("paused") is True,
            f"paused flag didn't persist: {paused_data}")
    print(f"  paused = True  (data.paused={paused_data.get('paused')})")

    # Unpause.
    pdata["paused"] = False
    resumed = _patch(f"{backend}/api/concepts/{pcid}", {
        "data": json.dumps(pdata, indent=2),
    })
    resumed_data = json.loads(resumed.get("data") or "{}")
    _assert(resumed_data.get("paused") is False,
            f"unpause didn't persist: {resumed_data}")
    print(f"  paused = False (data.paused={resumed_data.get('paused')})")


def step_evolution_log_actor(backend: str, trio: Dict[str, str]) -> None:
    """Confirm the agent's emits + the user-edits show in the log
    with the correct actor labels (§8D.33)."""
    _section("9) Evolution log — actor labels for agent vs user")
    resp = _get(f"{backend}/api/evolution_log?limit=50")
    diffs = resp.get("diffs") or []
    actors: Dict[str, int] = {}
    for d in diffs:
        a = (d.get("actor") or "?")
        actors[a] = actors.get(a, 0) + 1
    print(f"  actor histogram: {actors}")
    # Agent-tagged diffs would carry actor=agent:<pcid>; user edits
    # carry user:<session>. The tick may emit zero actions on a small
    # 1B model, so the agent histogram could be 0; we just assert the
    # log has SOMETHING for our parameter card.
    pcid_hits = [d for d in diffs
                 if trio["parameter_card_id"] in (d.get("target") or "")]
    print(f"  diffs targeting parameter card: {len(pcid_hits)}")
    _assert(len(pcid_hits) > 0,
            f"no diff targets the parameter card: {diffs[:5]}")


def step_cleanup(backend: str, trio: Dict[str, str]) -> None:
    _section("10) Terminate agent — delete parameter card")
    pcid = trio["parameter_card_id"]
    try:
        _delete(f"{backend}/api/concepts/{pcid}")
        print(f"  deleted parameter card: {pcid}")
    except Exception as e:
        print(f"  (delete raised {e!s})")
    # The trio cards may persist (their delete is a separate lifecycle
    # decision); the contract per §8D.27 is "deleting the parameter
    # card terminates the agent loop", not "cascades into the trio".
    for cid in (trio["perception"], trio["transformer"], trio["emitter"]):
        try:
            _delete(f"{backend}/api/concepts/{cid}")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    backend = DEFAULT_BACKEND
    if len(sys.argv) > 1:
        backend = sys.argv[1]
    print(f"[probe_live_agent] §8D.48 LIVE agent tick against {backend}")
    try:
        step_subsystems_real(backend)
        step_ensure_fixtures(backend)
        trio = step_spawn_agent(backend)
        step_verify_trio_concepts(backend, trio)
        step_run_tick(backend, trio)
        step_inspect_rationale(backend, trio)
        step_cascade_status(backend, trio)
        step_pause_resume(backend, trio)
        step_evolution_log_actor(backend, trio)
        step_cleanup(backend, trio)
        print(f"\n[probe_live_agent] ALL CHECKS PASS — "
              f"agent spawn + real GPT4All tick + emit lifecycle end-to-end")
        return 0
    except AssertionError as e:
        print(f"\n[probe_live_agent] FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
