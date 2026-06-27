"""LIVE end-to-end probe for the §N DuckDuckGo walkthrough (EXPLORE-04,
docs/frontend/object_exploration.md §5.1 / N.3-N.10).

This is the *evidence* probe for Task 4's clean-GPU human checkpoint —
modeled directly on ``probe_live_archive_scan.py``'s structure, but driving
the §N sequence instead of the §8D.45 retrieval walkthrough:

  1. Confirms ``/api/subsystem_status.all_real == True`` (§8D.46) BEFORE
     anything else. No stub fallback. A non-real status is a loud failure,
     never silently degraded.
  2. Triggers a REAL Selenium scan against DuckDuckGo, watches the
     per-snapshot WebSocket through the ``done`` frame.
  3. Authors ``self=duckduckgo`` (N.3) and drag-wires the REAL
     materialised WebBrowser python-object tree onto it via
     ``POST /api/editor/link`` with ``inherit_types=true`` — the same
     request the gateway's drag-wire gesture issues (07-04/07-05).
  4. Asserts at least one REAL typed field was inherited, checked against
     the real ``OBJECT_HAS_*`` / ``FUNCTION_*_TYPE`` edges via
     ``GET /concepts/{id}/next_rank`` (probe_python_api.py style — real
     edges, not mocked).
  5. Asserts the revealed ``url{}`` / ``dom{}`` rank-1 fields stay
     type-stripped on DuckDuckGo's own data block (rank-1 minimalism,
     N.4/N.5) even though the type graph resolves internally.
  6. Asserts ``{chunk samples}`` per-sample iteration (N.9) advances over
     the REAL scanned chunk distribution via
     ``POST /api/ui/signal_stream`` + ``POST /api/ui/signal_advance``.

Every step prints the *actual* data observed so the operator can read the
evidence from the terminal, not just trust an assertion.

Run as (the REAL run, reserved for Task 4's clean-GPU checkpoint):

    python scripts/probe_live_duckduckgo_walkthrough.py --backend http://127.0.0.1:8080

Requires the backend to be up with REAL subsystems (no WFH_FAKE_*, no
NO_WEBDRIVER). The scan can take 30-180 seconds depending on DuckDuckGo's
response.

Self-test (STUB mode, in-process, proves the gate + assertion scaffold
have teeth WITHOUT booting any real subsystem):

    WFH_FAKE_SLM=1 WFH_FAKE_EMBEDDER=1 NO_WEBDRIVER=1 \\
        python scripts/probe_live_duckduckgo_walkthrough.py --self-test \\
        --backend http://127.0.0.1:8080
"""

from __future__ import annotations

import argparse
import asyncio
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
# DuckDuckGo's HTML search endpoint — matches the §N walkthrough's
# canonical "duckduckgo url" reference (object_exploration.md §5.1).
DUCKDUCKGO_QUERY = "university library"
DUCKDUCKGO_URL = (
    "https://duckduckgo.com/html/?q="
    + urllib.parse.quote_plus(DUCKDUCKGO_QUERY)
)
# Hard ceiling so a flaky DuckDuckGo doesn't hang the probe.
SCAN_TIMEOUT_SEC = 240.0


def _section(title: str) -> None:
    print(f"\n== {title} {'=' * max(0, 60 - len(title))}")


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _get(url: str, timeout: float = 30.0) -> Dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _post(url: str, body: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Pure, directly-callable assertion helpers (required by Task 2 — these are
# unit-testable in isolation and exercised by --self-test below without
# booting any real subsystem).
# ---------------------------------------------------------------------------

def assert_all_real(status: Dict[str, Any]) -> None:
    """§8D.46 — raises unless ``/api/subsystem_status`` reports every
    subsystem real. No stub fallback is permitted past this gate."""
    _assert(isinstance(status, dict),
            f"subsystem_status must be a dict, got {type(status)}")
    _assert(status.get("all_real") is True,
            f"subsystems are NOT all real (no-mocks contract §8D.46 "
            f"violated): {status}")


def assert_shadow_dom_present(payload: Dict[str, Any]) -> None:
    """N.7 — a completed scanner call resolves to a ShadowDOM object
    whose rank-1 fields (``url``/``dom``) must both be present and
    non-empty/non-null on the payload describing the call's resolution."""
    _assert(isinstance(payload, dict),
            f"shadow DOM payload must be a dict, got {type(payload)}")
    url_val = payload.get("url")
    dom_val = payload.get("dom")
    _assert(url_val not in (None, "", {}, []),
            f"ShadowDOM payload missing a non-empty 'url' field: {payload}")
    _assert(dom_val not in (None, "", {}, []),
            f"ShadowDOM payload missing a non-empty 'dom' field: {payload}")


def assert_min_chunks(chunks: List[Any], n: int = 1) -> None:
    """The real scanned chunk distribution must contain at least ``n``
    samples before per-sample iteration (N.9) can be meaningfully driven."""
    _assert(isinstance(chunks, list),
            f"chunks must be a list, got {type(chunks)}")
    _assert(len(chunks) >= n,
            f"expected at least {n} chunk(s), got {len(chunks)}: {chunks!r}")


# ---------------------------------------------------------------------------
# WebSocket scan watcher — drains the per-snapshot WS until 'done' or timeout
# (identical structure to probe_live_archive_scan.py's watcher).
# ---------------------------------------------------------------------------

async def _watch_scan_ws(backend: str, snap_ws_id: int,
                         timeout: float = SCAN_TIMEOUT_SEC) -> Dict[str, Any]:
    try:
        import websockets
    except ImportError:
        raise RuntimeError("websockets package required to watch the scan")

    ws_base = backend.replace("https://", "wss://").replace("http://", "ws://")
    ws_url = f"{ws_base}/api/ws/nodes/{snap_ws_id}"
    print(f"  subscribing to {ws_url}")

    counts: Dict[str, int] = {}
    nodes_so_far = 0
    chunks_seen: List[Dict[str, Any]] = []
    started = time.monotonic()
    done = False
    error: Optional[str] = None

    async with websockets.connect(
        ws_url, ping_interval=20, open_timeout=20,
        max_size=32 * 1024 * 1024,
    ) as ws:
        while not done:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            except asyncio.TimeoutError:
                if time.monotonic() - started > timeout:
                    error = "watch_timeout"
                    break
                elapsed = int(time.monotonic() - started)
                print(f"  [{elapsed:4d}s] scanning… frames={counts} "
                      f"nodes={nodes_so_far}", flush=True)
                continue
            try:
                frame = json.loads(raw)
            except Exception:
                continue
            ftype = (frame.get("type") or "").strip()
            counts[ftype] = counts.get(ftype, 0) + 1
            if ftype == "nodes":
                ns = frame.get("nodes") or []
                nodes_so_far += len(ns)
                chunks_seen.extend(ns)
            elif ftype == "chunk_added":
                nodes_so_far += 1
                chunk = frame.get("chunk") or frame
                chunks_seen.append(chunk)
            elif ftype == "done":
                done = True
                if frame.get("error"):
                    error = frame["error"]
            elif ftype == "error":
                error = frame.get("message") or "unknown_error"
                done = True

    return {
        "frame_counts":     counts,
        "nodes_streamed":   nodes_so_far,
        "chunks_seen":      chunks_seen,
        "elapsed_sec":      round(time.monotonic() - started, 1),
        "completed":        done and not error,
        "error":            error,
    }


# ---------------------------------------------------------------------------
# Probe steps (the REAL run)
# ---------------------------------------------------------------------------

def step_subsystem_real(backend: str) -> Dict[str, Any]:
    _section("1) /api/subsystem_status -> real subsystems active")
    s = _get(f"{backend}/api/subsystem_status")
    print(f"  slm       = {s.get('slm', {}).get('backend')} "
          f"({s.get('slm', {}).get('model')})")
    print(f"  embedder  = {s.get('embedder', {}).get('backend')} "
          f"({s.get('embedder', {}).get('model')}, "
          f"device={s.get('embedder', {}).get('device')})")
    print(f"  selenium  = {s.get('selenium', {}).get('backend')} "
          f"(loaded={s.get('selenium', {}).get('loaded')})")
    print(f"  langgraph = {s.get('langgraph', {}).get('backend')} "
          f"(StateGraph={s.get('langgraph', {}).get('has_StateGraph')})")
    assert_all_real(s)
    print("  [OK] all_real = True")
    return s


def step_trigger_scan(backend: str) -> int:
    _section("2) Triggering live Selenium scan of DuckDuckGo")
    print(f"  URL: {DUCKDUCKGO_URL}")
    encoded = urllib.parse.quote(DUCKDUCKGO_URL, safe=":/?=&%")
    resp = _get(f"{backend}/api/snapshot?url={encoded}", timeout=60)
    snap_id_raw = resp.get("snapshot_ws_id")
    snap_id = int(snap_id_raw) if snap_id_raw is not None else -1
    _assert(resp.get("status") == "accepted" and snap_id >= 0,
            f"snapshot trigger failed: {resp}")
    print(f"  snapshot accepted: ws_id={snap_id}")
    return snap_id


async def step_watch_scan(backend: str, snap_id: int) -> Dict[str, Any]:
    _section("3) Watching scan WebSocket until 'done'")
    summary = await _watch_scan_ws(backend, snap_id)
    print(f"  elapsed:        {summary['elapsed_sec']}s")
    print(f"  frame counts:   {summary['frame_counts']}")
    print(f"  nodes streamed: {summary['nodes_streamed']}")
    print(f"  completed ok:   {summary['completed']}  (error={summary['error']})")
    _assert(summary["completed"], f"scan never completed: {summary}")
    _assert(summary["nodes_streamed"] > 0,
            f"scan completed with zero nodes streamed: {summary}")
    assert_min_chunks(summary["chunks_seen"], n=1)
    print(f"  [OK] {len(summary['chunks_seen'])} real chunk(s) streamed "
          f"from the live DuckDuckGo scan")
    return summary


def step_locate_scanner(backend: str) -> str:
    _section("4) Locating the materialised WebBrowser python-object tree")
    try:
        _post(f"{backend}/api/foundation/ensure", {"workspace_id": ""}, timeout=60)
    except Exception:
        pass
    concepts = _get(f"{backend}/api/concepts", timeout=30).get("concepts") or []
    scanner = None
    for c in concepts:
        if (c.get("type_hint") == "python_object"
                and "WebBrowserManager" in (c.get("backing_pointer") or "")):
            scanner = c
            break
    _assert(scanner is not None,
            f"could not locate the materialised WebBrowserManager python_object "
            f"node among {len(concepts)} concepts (foundation fixtures not "
            f"materialised?)")
    scanner_id = scanner["concept_id"]
    print(f"  scanner node: {scanner_id}  (name={scanner.get('name')})")
    return scanner_id


def step_author_duckduckgo(backend: str) -> str:
    _section("5) Authoring self=duckduckgo (N.3)")
    resp = _post(f"{backend}/api/concepts", {
        "name": "duckduckgo",
        "description": "DuckDuckGo search walkthrough (§N live probe)",
        "data": json.dumps({"query": "see {scan} for the live result set"}),
    }, timeout=30)
    duck_id = resp.get("concept_id") or ""
    _assert(bool(duck_id),
            f"authoring self=duckduckgo did not return a concept_id: {resp}")
    print(f"  duckduckgo node: {duck_id}")
    return duck_id


def step_drag_wire_inherit(backend: str, scanner_id: str, duck_id: str) -> List[Dict[str, Any]]:
    _section("6) Drag-wire-equivalent: editor/link inherit_types=true (N.4)")
    resp = _post(f"{backend}/api/editor/link", {
        "source_id": scanner_id,
        "target_id": duck_id,
        "edge_type": "RELATES_TO",
        "workspace_id": "",
        "inherit_types": True,
    }, timeout=30)
    _assert(resp.get("ok") is True,
            f"editor/link inherit_types=true did not succeed: {resp}")
    inherited = resp.get("inherited_edges") or []
    print(f"  inherited_edges: {len(inherited)}")
    for e in inherited[:5]:
        print(f"    {e.get('edge_type')}  -> {e.get('target_id') or e.get('target')}")
    return inherited


def step_assert_real_type_inheritance(backend: str, duck_id: str) -> List[Dict[str, Any]]:
    _section("7) GET next_rank — asserting >=1 REAL typed field inherited")
    resp = _get(f"{backend}/api/concepts/{duck_id}/next_rank", timeout=30)
    _assert(resp.get("ok") is True, f"next_rank call failed: {resp}")
    neighbors = resp.get("neighbors") or []
    print(f"  next_rank neighbors: {len(neighbors)}")
    real_typed = [
        n for n in neighbors
        if n.get("edge_type") in (
            "OBJECT_HAS_PROPERTY", "OBJECT_HAS_FUNCTION",
            "FUNCTION_INPUT_TYPE", "FUNCTION_OUTPUT_TYPE",
        )
    ]
    for n in real_typed[:10]:
        print(f"    {n.get('edge_type'):>22}  {n.get('name')}  "
              f"(type_hint={n.get('type_hint')})")
    _assert(len(real_typed) >= 1,
            f"expected >=1 real OBJECT_HAS_*/FUNCTION_*_TYPE neighbor after "
            f"inherit_types, got {neighbors}")
    print(f"  [OK] {len(real_typed)} real typed field(s) inherited onto "
          f"DuckDuckGo via the materialiser's own edge vocabulary")
    return real_typed


def step_assert_rank1_minimalism(backend: str, duck_id: str) -> None:
    _section("8) Rank-1 minimalism — DuckDuckGo's OWN data stays type-stripped (N.4/N.5)")
    import re
    duck = _get(f"{backend}/api/concepts/{duck_id}", timeout=30)
    data = duck.get("data") or ""
    print(f"  data block: {data[:200]!r}")
    _assert(not re.search(r"\w+\s*:\s*\w+\s*=", data),
            f"DuckDuckGo's data block carries a typed colon-slot after "
            f"inherit (rank-1 minimalism violated): {data!r}")
    print("  [OK] DuckDuckGo presents NO types post-inherit")


def step_signal_iteration(backend: str, duck_id: str, total_chunks: int) -> List[Optional[int]]:
    _section("9) {chunk samples} per-sample iteration over the REAL scanned distribution (N.9)")
    total = max(1, min(total_chunks, 10))
    _post(f"{backend}/api/ui/signal_stream", {
        "workspace_id": "", "card_id": duck_id,
        "total": total, "signal_index": 0, "field_path": "scan.chunk",
    }, timeout=30)
    advanced: List[Optional[int]] = []
    for _ in range(min(total, 5) + 1):
        resp = _post(f"{backend}/api/ui/signal_advance", {
            "workspace_id": "", "card_id": duck_id, "step": 1,
        }, timeout=30)
        sig = ((resp.get("state") or {}).get("signal_stream") or {}).get(duck_id) or {}
        advanced.append(sig.get("signal_index"))
    print(f"  total={total}  advanced indices: {advanced}")
    _assert(len(advanced) >= 2 and advanced[0] != advanced[1] or total == 1,
            f"per-sample iteration did not advance the cursor across steps: {advanced}")
    print(f"  [OK] {{chunk samples}} per-sample iteration advances over the "
          f"real distribution ({total} samples)")
    return advanced


def step_restore(backend: str, duck_id: str) -> None:
    _section("10) Cleanup — delete the transient duckduckgo probe node")
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"{backend}/api/concepts/{duck_id}",
            method="DELETE",
        ), timeout=10)
        print(f"  deleted: {duck_id}")
    except Exception as e:
        print(f"  (cleanup skipped: {e})")


# ---------------------------------------------------------------------------
# Self-test — STUB mode, in-process, proves the gate + scaffold have teeth
# without booting any real subsystem.
# ---------------------------------------------------------------------------

def run_self_test(backend: str) -> int:
    """Proves, in-process, against a STUB backend:

    (a) the all_real gate FIRES — a real stub ``/api/subsystem_status``
        returns ``all_real:false``, and feeding that into
        ``assert_all_real`` raises (caught here as the EXPECTED outcome).
    (b) the assertion scaffold has teeth — ``assert_shadow_dom_present``
        and ``assert_min_chunks`` each RAISE on an empty/missing fixture
        and PASS on a minimal stub fixture.

    Exits 0 only if every behavioral expectation above held.
    """
    failures: List[str] = []

    _section("self-test (a): all_real gate fires against the REAL stub backend")
    try:
        status = _get(f"{backend}/api/subsystem_status", timeout=30)
        print(f"  live stub /api/subsystem_status -> all_real={status.get('all_real')}")
    except Exception as e:
        failures.append(f"could not reach {backend}/api/subsystem_status: {e}")
        status = None

    if status is not None:
        if status.get("all_real") is True:
            failures.append(
                "expected the backend under test to be running in STUB mode "
                "(all_real should be False) — self-test must be run against "
                "a WFH_FAKE_SLM=1 WFH_FAKE_EMBEDDER=1 NO_WEBDRIVER=1 backend"
            )
        else:
            try:
                assert_all_real(status)
                failures.append(
                    "assert_all_real did NOT raise on a stub all_real:false "
                    "status — the gate has no teeth"
                )
            except AssertionError:
                print("  [OK] assert_all_real raised on the real stub "
                      "all_real:false status, as expected")

    _section("self-test (b): assertion scaffold has teeth")

    # assert_shadow_dom_present — must raise on empty, pass on minimal fixture.
    try:
        assert_shadow_dom_present({})
        failures.append("assert_shadow_dom_present did NOT raise on {} (empty payload)")
    except AssertionError:
        print("  [OK] assert_shadow_dom_present raised on an empty payload")
    try:
        assert_shadow_dom_present({"url": "https://duckduckgo.com/", "dom": "<html/>"})
        print("  [OK] assert_shadow_dom_present passed on a minimal valid fixture")
    except AssertionError as e:
        failures.append(f"assert_shadow_dom_present raised on a VALID fixture: {e}")

    # assert_min_chunks — must raise on empty list, pass on a 1-item list.
    try:
        assert_min_chunks([], n=1)
        failures.append("assert_min_chunks did NOT raise on an empty list")
    except AssertionError:
        print("  [OK] assert_min_chunks raised on an empty chunk list")
    try:
        assert_min_chunks([{"id": "chunk-1"}], n=1)
        print("  [OK] assert_min_chunks passed on a minimal 1-chunk fixture")
    except AssertionError as e:
        failures.append(f"assert_min_chunks raised on a VALID 1-chunk fixture: {e}")

    if failures:
        print(f"\n[probe_live_duckduckgo_walkthrough --self-test] FAILED "
              f"({len(failures)} expectation(s) not met):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\n[probe_live_duckduckgo_walkthrough --self-test] ALL EXPECTATIONS "
          f"HELD — the all_real gate fires and the assertion scaffold has teeth")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="LIVE probe for the §N DuckDuckGo walkthrough (EXPLORE-04)")
    parser.add_argument("--backend", default=DEFAULT_BACKEND,
                        help=f"backend base URL (default: {DEFAULT_BACKEND})")
    parser.add_argument("--self-test", action="store_true",
                        help="run the STUB-mode in-process self-test instead "
                             "of the real walkthrough (no real subsystem boot)")
    args = parser.parse_args(argv)
    backend = args.backend

    if args.self_test:
        print(f"[probe_live_duckduckgo_walkthrough] --self-test against {backend}")
        return run_self_test(backend)

    print(f"[probe_live_duckduckgo_walkthrough] SN LIVE end-to-end run "
          f"against {backend}")
    print(f"[probe_live_duckduckgo_walkthrough] query = {DUCKDUCKGO_QUERY!r}")

    duck_id: Optional[str] = None
    try:
        step_subsystem_real(backend)
        snap_id = step_trigger_scan(backend)
        scan_summary = asyncio.run(step_watch_scan(backend, snap_id))
        scanner_id = step_locate_scanner(backend)
        duck_id = step_author_duckduckgo(backend)
        step_drag_wire_inherit(backend, scanner_id, duck_id)
        step_assert_real_type_inheritance(backend, duck_id)
        step_assert_rank1_minimalism(backend, duck_id)
        step_signal_iteration(backend, duck_id, len(scan_summary["chunks_seen"]))
        print(f"\n[probe_live_duckduckgo_walkthrough] ALL CHECKS PASS — "
              f"real DuckDuckGo scan + real drag-wire inherit_types + "
              f"rank-1 minimalism + real per-sample iteration end-to-end")
        return 0
    except AssertionError as e:
        print(f"\n[probe_live_duckduckgo_walkthrough] FAILED: {e}", file=sys.stderr)
        return 1
    finally:
        if duck_id:
            step_restore(backend, duck_id)


if __name__ == "__main__":
    raise SystemExit(main())
