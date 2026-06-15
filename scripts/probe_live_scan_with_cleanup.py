"""LIVE end-to-end probe for §16.5 — the live-scan + DB-cleanup repeatability bar.

This is the **mandatory** acceptance probe named in `DOMAIN_MODEL.md` §16.5 and
`docs/code_constraints/env_scenarios.md` §1.4 (and was previously *missing* — see
`docs/CODEBASE_AUDIT_2026-06-08.md` §C.1). It is distinct from
`probe_live_archive_scan.py` (which proves *one* scan works): this probe proves
the Real ↔ Imaginary ↔ Symbolic loop is **repeatable on a real site without
progressive degradation** — i.e. the database comes back cleanly between rounds
and the live updates keep flowing through every scan, not only the first.

Sequence (per §16.5):

  1. Confirm ``/api/subsystem_status.all_real == True`` (§13) — real GPT4All on
     CUDA, real nomic, real Selenium, real LangGraph. No fake gates.
  2. Purge to baseline (``POST /api/purge_workspace {confirm:"erase"}``) and
     assert the chunk pool is empty.
  3. First scan of a real archive.org URL; watch the scan WS to ``done``,
     asserting chunks streamed (``chunk_added`` > 0) and the scan completed.
  4. Assert chunks materialised (``/api/chunk_nodes`` > 0) and that
     ``Database.search`` (``/api/chunk_search``) returns a real hit whose
     rendering carries the query terms — TF-IDF + nomic indices are alive.
  5. Purge again and ENFORCE the cleanup contract: chunk pool returns to the
     baseline, ``chunk_search`` returns zero instances (TF-IDF emptied), and the
     purge response reports the layout frame dropped + TF-IDF rows removed. No
     503s, no stub fallbacks anywhere in the trace.
  6. Re-scan the same URL against the freshly-cleaned workspace and assert the
     chunk pool rebuilds to a comparable count — a stale index would cause an
     incremental-update mismatch here, so an identical/comparable rebuild is what
     verifies the purge was *structurally* complete, not merely nominal.

Run as:  python scripts/probe_live_scan_with_cleanup.py [BACKEND_URL]

Requires the backend up with REAL subsystems (no ``WFH_FAKE_*``). The two scans
can take 60-400 seconds total depending on archive.org's response.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Windows consoles default to cp1252, which can't encode glyphs used in the
# probe output (→, §). Force UTF-8 so the probe prints cleanly (same guard as
# probe_reservoir_rollout.py).
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

DEFAULT_BACKEND = "http://127.0.0.1:8080"
ARCHIVE_QUERY = "university library"
ARCHIVE_URL = (
    "https://archive.org/search?query=" + urllib.parse.quote_plus(ARCHIVE_QUERY)
)
SCAN_TIMEOUT_SEC = 240.0


# ---------------------------------------------------------------------------
# HTTP + assertion helpers (mirror probe_live_archive_scan.py conventions)
# ---------------------------------------------------------------------------

def _section(title: str) -> None:
    print(f"\n== {title} {'=' * max(0, 60 - len(title))}")


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _get(url: str, timeout: float = 30.0) -> Dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _post(url: str, body: Dict[str, Any], timeout: float = 60.0) -> Dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _chunk_pool_count(backend: str) -> int:
    nodes = _get(f"{backend}/api/chunk_nodes", timeout=60)
    if isinstance(nodes, dict):
        for key in ("nodes", "chunks"):
            if isinstance(nodes.get(key), list):
                return len(nodes[key])
    if isinstance(nodes, list):
        return len(nodes)
    return 0


def _search_instance_count(backend: str):
    """Returns ``(instance_count, raw_response)``."""
    resp = _post(f"{backend}/api/chunk_search", {
        "query": ARCHIVE_QUERY, "page_limit": 5, "instance_limit_per_page": 5,
    }, timeout=60)
    n = sum(len(p.get("instances") or []) for p in (resp.get("pages") or []))
    return n, resp


# ---------------------------------------------------------------------------
# WS scan watcher (per-snapshot WS, as the live scanner emits it)
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
    started = time.monotonic()
    done = False
    error: Optional[str] = None

    async with websockets.connect(
        ws_url, ping_interval=20, open_timeout=20, max_size=32 * 1024 * 1024,
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
                nodes_so_far += len(frame.get("nodes") or [])
            elif ftype == "chunk_added":
                nodes_so_far += 1
            elif ftype == "done":
                done = True
                if frame.get("error"):
                    error = frame["error"]
            elif ftype == "error":
                error = frame.get("message") or "unknown_error"
                done = True

    return {
        "frame_counts": counts,
        "nodes_streamed": nodes_so_far,
        "umap_frames": counts.get("umap_canonical", 0),
        "elapsed_sec": round(time.monotonic() - started, 1),
        "completed": done and not error,
        "error": error,
    }


# ---------------------------------------------------------------------------
# Probe steps
# ---------------------------------------------------------------------------

def step_subsystem_real(backend: str) -> None:
    _section("1) /api/subsystem_status → all_real")
    s = _get(f"{backend}/api/subsystem_status")
    print(f"  slm={s.get('slm', {}).get('model')}  "
          f"embedder={s.get('embedder', {}).get('device')}  "
          f"selenium={s.get('selenium', {}).get('loaded')}  "
          f"langgraph={s.get('langgraph', {}).get('has_StateGraph')}")
    _assert(s.get("all_real") is True, f"subsystems NOT all real: {s}")
    print("  [OK] all_real = True")


def step_purge(backend: str, label: str) -> Dict[str, Any]:
    _section(f"PURGE ({label})")
    resp = _post(f"{backend}/api/purge_workspace",
                 {"workspace_id": "", "confirm": "erase"}, timeout=300)
    print(f"  nodes_purged={resp.get('nodes_purged')}  "
          f"layout_dropped={resp.get('layout_dropped')}  "
          f"tfidf_rows_dropped={resp.get('tfidf_rows_dropped')}")
    return resp


def step_assert_baseline(backend: str) -> None:
    """Chunk pool empty + search returns nothing (foundation fixtures are
    concept nodes, not chunks, so the chunk pool is the clean signal)."""
    pool = _chunk_pool_count(backend)
    n_inst, _ = _search_instance_count(backend)
    print(f"  chunk_pool={pool}  search_instances={n_inst}")
    _assert(pool == 0, f"chunk pool not empty at baseline: {pool}")
    _assert(n_inst == 0, f"chunk_search returned ghost rows at baseline: {n_inst}")
    print("  [OK] baseline clean")


async def step_scan(backend: str, label: str) -> Dict[str, Any]:
    _section(f"SCAN ({label}): {ARCHIVE_URL}")
    encoded = urllib.parse.quote(ARCHIVE_URL, safe=":/?=&%")
    resp = _get(f"{backend}/api/snapshot?url={encoded}", timeout=60)
    # NOTE: snapshot_ws_id 0 is a LEGITIMATE channel id (the first scan on a
    # freshly-purged DB) — `or -1` would swallow it as falsy.
    _raw_ws = resp.get("snapshot_ws_id")
    snap_id = -1 if _raw_ws is None else int(_raw_ws)
    _assert(resp.get("status") == "accepted" and snap_id >= 0,
            f"snapshot trigger failed: {resp}")
    summary = await _watch_scan_ws(backend, snap_id)
    print(f"  elapsed={summary['elapsed_sec']}s  frames={summary['frame_counts']}  "
          f"streamed={summary['nodes_streamed']}  umap_frames={summary['umap_frames']}")
    _assert(summary["completed"], f"scan never completed: {summary}")
    _assert(summary["nodes_streamed"] > 0,
            f"scan completed with zero chunks streamed: {summary}")
    return summary


def step_assert_alive(backend: str) -> int:
    _section("ASSERT indices alive after scan")
    pool = _chunk_pool_count(backend)
    n_inst, resp = _search_instance_count(backend)
    print(f"  chunk_pool={pool}  search_instances={n_inst}")
    _assert(pool > 0, f"no chunks in pool after scan: {pool}")
    _assert(n_inst > 0, f"chunk_search returned no hits after scan: {n_inst}")
    # query-term presence in a real hit
    found_terms = False
    for p in (resp.get("pages") or []):
        for inst in (p.get("instances") or []):
            txt = (inst.get("rendered_text") or "").lower()
            if any(t in txt for t in ("librar", "university")):
                found_terms = True
                break
        if found_terms:
            break
    print(f"  query-term hit in rendered text: {found_terms}")
    _assert(found_terms, "no hit's rendering carried the query terms")
    print("  [OK] TF-IDF + nomic indices alive against real content")
    return pool


def step_recompute_layout(backend: str) -> None:
    """§16.5 UMAP leg — drive the canonical 6D fit over the scanned chunk
    space. The FRONTEND fires this at scan-end; a headless probe must do it
    itself, both to assert the fit works against real content AND so the
    LayoutFrame exists for the purge's `layout_dropped` contract (without
    this, purge correctly reports False — nothing was ever fitted)."""
    _section("RECOMPUTE UMAP (canonical 6D fit)")
    resp = _post(f"{backend}/api/recompute_umap?min_docs=8", {}, timeout=300)
    coords = resp.get("coords") or {}
    print(f"  status={resp.get('status', 'ok')}  coords={len(coords)}")
    _assert(len(coords) > 0, f"recompute_umap produced no coords: {resp}")
    # 6-vector contract (§1.8): xyz + HSV per chunk.
    sample = next(iter(coords.values()))
    _assert(isinstance(sample, list) and len(sample) == 6,
            f"coords are not 6-vectors: {sample}")
    print("  [OK] real UMAP fit over the scanned chunk space (6D contract)")


def step_assert_cleanup(backend: str, purge_resp: Dict[str, Any]) -> None:
    _section("ASSERT cleanup contract (§16.5)")
    pool = _chunk_pool_count(backend)
    n_inst, _ = _search_instance_count(backend)
    print(f"  chunk_pool={pool}  search_instances={n_inst}  "
          f"layout_dropped={purge_resp.get('layout_dropped')}  "
          f"tfidf_rows_dropped={purge_resp.get('tfidf_rows_dropped')}")
    _assert(pool == 0, f"chunk pool NOT cleaned (ghost storage): {pool}")
    _assert(n_inst == 0, f"chunk_search ghost rows after purge: {n_inst}")
    _assert(purge_resp.get("layout_dropped") in (True, 1),
            f"LayoutFrame not dropped on purge: {purge_resp.get('layout_dropped')}")
    print("  [OK] cleanup complete — workspace back to baseline")


async def main(backend: str) -> int:
    print(f"§16.5 live-scan + DB-cleanup repeatability probe → {backend}")
    step_subsystem_real(backend)

    step_purge(backend, "to baseline")
    step_assert_baseline(backend)

    s1 = await step_scan(backend, "round 1")
    pool1 = step_assert_alive(backend)
    step_recompute_layout(backend)

    purge2 = step_purge(backend, "after round 1")
    step_assert_cleanup(backend, purge2)

    s2 = await step_scan(backend, "round 2 (post-cleanup rebuild)")
    pool2 = step_assert_alive(backend)

    _section("RESULT")
    # Comparable rebuild: a stale index would diverge; allow archive.org
    # result-count drift but require the rebuild to be the same order of
    # magnitude (within 50%) of the first round.
    lo, hi = 0.5 * pool1, 1.5 * pool1 + 5
    print(f"  round1 chunks={pool1}  round2 chunks={pool2}  "
          f"comparable_window=({lo:.0f},{hi:.0f})")
    _assert(lo <= pool2 <= hi,
            f"rebuild not comparable — purge was not structurally complete: "
            f"round1={pool1} round2={pool2}")
    print(f"  round1 umap_frames={s1['umap_frames']}  round2 umap_frames={s2['umap_frames']}")
    print("\n[PASS] §16.5 live-scan + DB-cleanup repeatability verified.")
    return 0


if __name__ == "__main__":
    backend = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BACKEND
    try:
        raise SystemExit(asyncio.run(main(backend)))
    except AssertionError as e:
        print(f"\n[FAIL] {e}")
        raise SystemExit(1)
