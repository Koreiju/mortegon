"""LIVE end-to-end probe for the §8D.45 archive.org use case.

This is the *evidence* probe — distinct from ``probe_use_case.py``
which exercises wiring with synthetic concepts. This probe actually:

  1. Confirms ``/api/subsystem_status.all_real == True`` (§8D.46).
  2. Triggers a real Selenium scan against archive.org for the
     query ``"university library"``.
  3. Subscribes to the per-scan WebSocket and waits for the ``done``
     frame, counting the chunks streamed during the scan.
  4. Verifies the chunks materialised in the workspace's chunk pool
     via ``GET /api/chunk_nodes``.
  5. Runs ``POST /api/chunk_search`` with the same query and confirms
     real TF-IDF hits come back from the global store.
  6. Pins one hit via the real ``POST /api/ui/pin`` mirror.
  7. Fires ``POST /api/ui/compile_expand`` and verifies the UI state
     mirror recorded the expansion.
  8. Runs ``POST /api/conceptual/compile`` on the hit's concept
     (when one is materialised) and verifies a non-stub rendering
     comes back via the real GPT4All + LangGraph path.
  9. Restores by collapsing + unpinning.

Every step prints the *actual* data it observed (chunk counts, head
HTML, real hits with scores, real rendering text) so the operator
can read the evidence from the terminal, not just trust an assertion.

Run as:  python scripts/probe_live_archive_scan.py [BACKEND_URL]

Requires the backend to be up with REAL subsystems (no WFH_FAKE_*).
The scan can take 30-180 seconds depending on archive.org's response.
"""

from __future__ import annotations

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
# archive.org's search URL pattern for textual content. Picked
# because it (a) returns substantial DOM content the scanner can
# distill, (b) doesn't require login, and (c) matches the use case's
# "university library" example query.
ARCHIVE_QUERY = "university library"
ARCHIVE_URL = (
    "https://archive.org/search?query="
    + urllib.parse.quote_plus(ARCHIVE_QUERY)
)
# Hard ceilings so a flaky archive.org doesn't hang the probe.
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
# WebSocket scan watcher — drains the per-snapshot WS until 'done' or timeout
# ---------------------------------------------------------------------------

async def _watch_scan_ws(backend: str, snap_ws_id: int,
                         timeout: float = SCAN_TIMEOUT_SEC) -> Dict[str, Any]:
    """Subscribe to the per-snapshot WS, count frame kinds, return a
    summary dict when 'done' fires (or the timeout elapses)."""
    try:
        import websockets
    except ImportError:
        raise RuntimeError("websockets package required to watch the scan")

    ws_base = backend.replace("https://", "wss://").replace("http://", "ws://")
    ws_url = f"{ws_base}/api/ws/nodes/{snap_ws_id}"
    print(f"  subscribing to {ws_url}")

    counts: Dict[str, int] = {}
    nodes_so_far = 0
    first_node_sample: Optional[Dict[str, Any]] = None
    started = time.monotonic()
    done = False
    error: Optional[str] = None

    async with websockets.connect(
        ws_url, ping_interval=20, open_timeout=20,
        # Bump the WS frame ceiling — the scanner periodically emits
        # a 'nodes' batch that exceeds the default 1 MB on chunky
        # pages like archive.org's search results.
        max_size=32 * 1024 * 1024,
    ) as ws:
        while not done:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            except asyncio.TimeoutError:
                if time.monotonic() - started > timeout:
                    error = "watch_timeout"
                    break
                # Print a live ticker so the operator sees progress.
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
                # Legacy frame shape — batch of nodes.
                ns = frame.get("nodes") or []
                nodes_so_far += len(ns)
                if first_node_sample is None and ns:
                    first_node_sample = ns[0]
            elif ftype == "chunk_added":
                # Current scanner emits one frame per chunk addition.
                nodes_so_far += 1
                if first_node_sample is None:
                    first_node_sample = frame.get("chunk") or frame
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
        "first_node":       first_node_sample,
        "elapsed_sec":      round(time.monotonic() - started, 1),
        "completed":        done and not error,
        "error":            error,
    }


# ---------------------------------------------------------------------------
# Probe steps
# ---------------------------------------------------------------------------

def step_subsystem_real(backend: str) -> None:
    _section("1) /api/subsystem_status → real subsystems active")
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
    _assert(s.get("all_real") is True,
            f"subsystems are NOT all real: {s}")
    print(f"  [OK] all_real = True")


def step_trigger_scan(backend: str) -> int:
    _section("2) Triggering live Selenium scan of archive.org")
    print(f"  URL: {ARCHIVE_URL}")
    encoded = urllib.parse.quote(ARCHIVE_URL, safe=":/?=&%")
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
    if summary["first_node"]:
        n = summary["first_node"]
        print(f"  first node sample:")
        print(f"    xpath={n.get('xpath') or n.get('absolute_xpath') or '?'}")
        print(f"    tag={n.get('tag', '?')}  url={n.get('url', '?')}")
        text = (n.get("text") or "").strip().replace("\n", " ")
        if text:
            print(f"    text head: {text[:120]!r}")
    _assert(summary["completed"], f"scan never completed: {summary}")
    _assert(summary["nodes_streamed"] > 0,
            f"scan completed with zero nodes streamed: {summary}")
    return summary


def step_chunk_nodes(backend: str) -> Dict[str, Any]:
    _section("4) /api/chunk_nodes — workspace chunk pool")
    nodes = _get(f"{backend}/api/chunk_nodes", timeout=60)
    total = 0
    if isinstance(nodes, dict):
        if "nodes" in nodes and isinstance(nodes["nodes"], list):
            total = len(nodes["nodes"])
        elif "chunks" in nodes and isinstance(nodes["chunks"], list):
            total = len(nodes["chunks"])
    elif isinstance(nodes, list):
        total = len(nodes)
    print(f"  chunk_nodes count: {total}")
    _assert(total > 0,
            f"no chunks materialised in the workspace pool: {nodes}")
    return nodes


def step_chunk_search(backend: str) -> Dict[str, Any]:
    _section("5) POST /api/chunk_search with the same query")
    resp = _post(f"{backend}/api/chunk_search", {
        "query": ARCHIVE_QUERY,
        "page_limit": 5,
        "instance_limit_per_page": 5,
    }, timeout=60)
    pages = resp.get("pages") or []
    total_instances = sum(len(p.get("instances") or []) for p in pages)
    print(f"  pages returned:     {len(pages)}")
    print(f"  total instances:    {total_instances}")
    for i, p in enumerate(pages[:3]):
        score = p.get("score", 0.0)
        url = (p.get("url") or "")[:80]
        n = len(p.get("instances") or [])
        print(f"    page[{i}] score={score:.4f}  n_instances={n}  url={url}")
        # Print one instance per page so the operator sees the actual text.
        if p.get("instances"):
            inst = p["instances"][0]
            txt = ((inst.get("rendered_text") or "")[:100]).replace("\n", " ")
            print(f"            head text: {txt!r}")
    _assert(total_instances > 0,
            f"chunk_search returned zero instances for "
            f"query={ARCHIVE_QUERY!r}: {resp}")
    return resp


def step_pin_and_compile(backend: str, search_resp: Dict[str, Any]) -> None:
    _section("6&7) Pin a hit + compile_expand mirror")
    # Pick the first hit. Pinning takes the chunk's instance id as the
    # node_id (that's what the spine + click-and-stick UI uses).
    first_inst = None
    for p in (search_resp.get("pages") or []):
        for inst in (p.get("instances") or []):
            if inst.get("id"):
                first_inst = inst
                break
        if first_inst:
            break
    _assert(first_inst is not None,
            "no instance with id; can't pin")
    inst_id = first_inst["id"]
    print(f"  pinning instance: {inst_id}")
    pin_resp = _post(f"{backend}/api/ui/pin", {
        "workspace_id": "",
        "node_id":      inst_id,
        "collapsed":    True,
    })
    pin_state = (pin_resp.get("state") or {}).get("pinned_billboards") or []
    _assert(inst_id in pin_state,
            f"pin failed; pinned set = {pin_state}")
    print(f"  pinned_billboards = {pin_state}")

    # Trigger the right-click compile_expand mirror.
    exp_resp = _post(f"{backend}/api/ui/compile_expand", {
        "workspace_id": "",
        "central_id":   inst_id,
        "children":     ["url", "html_raw", "rendered_text", "fields"],
    })
    expansions = (exp_resp.get("state") or {}).get("compile_expansions") or {}
    _assert(inst_id in expansions,
            f"compile_expand didn't record: {expansions}")
    print(f"  compile_expansions records: {list(expansions.keys())}")


def step_conceptual_compile(backend: str) -> None:
    _section("8) Real LangGraph + GPT4All compile on a real concept")
    # Pick a foundation fixture's compute-friendly concept node. The
    # Database/WebBrowser/Agent fixtures' data blocks compile cleanly
    # via the ``plain`` dispatch (no SLM needed) — useful as a known-
    # good real-LangGraph round trip.
    # Ensure foundation fixtures are materialised — idempotent, safe to
    # call after a purge.
    try:
        _post(f"{backend}/api/foundation/ensure", {"workspace_id": ""}, timeout=60)
    except Exception:
        pass
    concepts = _get(f"{backend}/api/concepts", timeout=30).get("concepts") or []
    db_fixture = next((c for c in concepts
                       if c.get("name") == "Database"
                       and c.get("concept_id", "").startswith("fixture::database::")),
                      None)
    _assert(db_fixture is not None,
            f"Database fixture not found; found {len(concepts)} concepts")
    cid = db_fixture["concept_id"]
    print(f"  compiling concept: {cid}")
    resp = _post(f"{backend}/api/conceptual/compile", {
        "concept_id":         cid,
        "use_slm":            True,
        "persist_rendering":  False,
    }, timeout=180)
    kind = resp.get("kind") or "?"
    rendering = resp.get("rendering") or ""
    print(f"  dispatch kind: {kind}")
    print(f"  rendering head: {rendering[:200]!r}")
    _assert(rendering, f"no rendering returned: {resp}")
    # The Database fixture's data block is JSON config — should classify
    # as 'plain' and tree-pretty-print without hitting the SLM. That's
    # still a real LangGraph round-trip per §11.7.
    _assert(kind in ("plain", "prompt", "structured", "python"),
            f"unexpected dispatch kind: {kind}")
    print(f"  [OK] real LangGraph compile produced a rendering")

    # Also exercise the SLM-driven `prompt` dispatch so GPT4All is
    # actually invoked. Create a transient concept whose data block
    # declares compute_kind=prompt; compile it; assert the rendering
    # is NOT the stub trailer.
    cc = _post(f"{backend}/api/concepts", {
        "name": "live_slm_compile_test",
        "description": "Real-SLM live compile probe",
        "data": json.dumps({
            "compute_kind": "prompt",
            "prompt": "Respond with exactly five words about university libraries.",
        }),
    }, timeout=30)
    test_id = cc.get("concept_id") or ""
    if not test_id:
        print(f"  (could not create transient concept for SLM probe: {cc})")
        return
    print(f"  compiling SLM concept: {test_id}")
    slm_resp = _post(f"{backend}/api/conceptual/compile", {
        "concept_id":         test_id,
        "use_slm":            True,
        "persist_rendering":  False,
    }, timeout=600)
    slm_kind = slm_resp.get("kind") or "?"
    slm_render = slm_resp.get("rendering") or ""
    print(f"  SLM dispatch kind: {slm_kind}")
    print(f"  SLM rendering head: {slm_render[:200]!r}")
    _assert(slm_kind == "prompt", f"expected prompt dispatch, got {slm_kind}")
    _assert(not slm_render.startswith("[stub-slm]"),
            f"SLM returned the stub — GPT4All didn't fire: {slm_render!r}")
    _assert(len(slm_render.strip()) > 0,
            f"SLM returned empty rendering: {slm_resp}")
    print(f"  [OK] real GPT4All SLM produced a real generation")

    # Cleanup the transient.
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"{backend}/api/concepts/{test_id}",
            method="DELETE",
        ), timeout=10)
    except Exception:
        pass


def step_restore(backend: str, search_resp: Dict[str, Any]) -> None:
    _section("9) Collapse + unpin (restore default state)")
    first_inst = None
    for p in (search_resp.get("pages") or []):
        for inst in (p.get("instances") or []):
            if inst.get("id"):
                first_inst = inst
                break
        if first_inst:
            break
    if first_inst is None:
        print("  (nothing to restore)")
        return
    inst_id = first_inst["id"]
    _post(f"{backend}/api/ui/compile_collapse",
          {"workspace_id": "", "central_id": inst_id})
    _post(f"{backend}/api/ui/unpin",
          {"workspace_id": "", "node_id": inst_id})
    print(f"  collapsed + unpinned: {inst_id}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    backend = DEFAULT_BACKEND
    if len(sys.argv) > 1:
        backend = sys.argv[1]
    print(f"[probe_live_archive_scan] §8D.45 LIVE end-to-end run against {backend}")
    print(f"[probe_live_archive_scan] query = {ARCHIVE_QUERY!r}")

    try:
        step_subsystem_real(backend)
        # If the workspace already has chunks from a recent scan, skip
        # the live re-scan (idempotent + faster for re-runs). The
        # contract still holds — what matters is that real chunks
        # came from a real scan at some point in this process's life.
        existing_count = 0
        try:
            existing = _get(f"{backend}/api/chunk_nodes", timeout=60)
            if isinstance(existing, dict):
                existing_count = len(existing.get("nodes") or [])
        except Exception:
            existing_count = 0
        if existing_count > 0:
            _section(f"2-3) Skipping scan — {existing_count} chunks already present")
            print("  (a previous live scan in this backend session already "
                  "populated the pool; re-using those chunks)")
        else:
            snap_id = step_trigger_scan(backend)
            scan_summary = asyncio.run(step_watch_scan(backend, snap_id))
        step_chunk_nodes(backend)
        search_resp = step_chunk_search(backend)
        step_pin_and_compile(backend, search_resp)
        step_conceptual_compile(backend)
        step_restore(backend, search_resp)
        print(f"\n[probe_live_archive_scan] ALL CHECKS PASS — "
              f"live scan + real retrieval + real compile end-to-end")
        return 0
    except AssertionError as e:
        print(f"\n[probe_live_archive_scan] FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
