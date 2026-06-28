"""LIVE end-to-end probe for the §O.18 halo cone-ray transport (HALO-03, D-01).

This is the *evidence* probe for the D-01 real-subsystem acceptance bar —
modeled directly on ``probe_live_archive_scan.py`` (the real Selenium scan
→ real retrieval flow) and ``probe_live_duckduckgo_walkthrough.py`` (the
``--self-test`` stub-mode behavioral-gate pattern). It actually:

  1. Confirms ``/api/subsystem_status.all_real == True`` (§8D.46) BEFORE
     any acceptance assertion. No stub fallback — a non-real status is a
     loud failure, never silently degraded.
  2. Triggers a REAL Selenium scan against archive.org, watches the
     per-snapshot WebSocket through the ``done`` frame (real chunks land
     in the workspace's chunk pool).
  3. Runs the real ``POST /api/chunk_search`` retrieval and picks a focal
     chunk id (a 2D query-element analog — the focal the halo opens on).
  4. Calls the REAL ``GET /api/apparitions/{focal_id}?transport=1&ray_project=1``
     retrieval against the real triple-product index (real nomic + TF-IDF
     over the real scan).
  5. ASSERTS cone-placement monotonicity: across the returned candidates,
     the cone distance derived from ``transport.{radial,along_ray}`` is
     MONOTONIC in ``transport.similarity`` (the real normalized
     pagerank·tfidf·nomic score) — more similar candidates sit nearer the
     cone apex (§O.18, "most-similar nearest the apex").
  6. ASSERTS delete-transports-next: deletes the top (most-similar)
     candidate via the real ``DELETE /api/concepts/{concept_id}``, re-runs
     the same real apparitions call, and asserts the next-most-similar
     candidate from the BEFORE set now occupies the nearest-apex slot in
     the AFTER set (§O.18/§O.14).

The monotonicity + delete-transport assertions are factored into small,
PURE helper functions (``assert_cone_monotonic``, ``assert_delete_transports_next``)
so the ``--self-test`` gate below can exercise them — and the ``all_real``
gate — entirely in-process, without booting any real subsystem.

Every step prints the *actual* data observed so the operator can read the
evidence from the terminal, not just trust an assertion. A screenshot is
NOT acceptance proof — this probe's exit-0 + its printed assertions are
(per the plan's threat model T-08-09/T-08-10).

Run as (the REAL run — MAIN CONTEXT ONLY, clean-GPU preflight, per
STATE.md env discipline; NEVER from a verifier subagent — a wedged
CUDA/Selenium boot hangs an agent):

    python scripts/probe_live_cone_transport.py --backend http://127.0.0.1:8080

Requires the backend to be up with REAL subsystems (no WFH_FAKE_*, no
NO_WEBDRIVER). The scan can take 30-180 seconds depending on archive.org's
response.

Self-test (STUB mode, fully in-process — proves the all_real gate fires
and the monotonicity/delete-transport assertion scaffold has teeth,
WITHOUT booting any real subsystem or requiring a live backend):

    python scripts/probe_live_cone_transport.py --self-test

(The optional ``--backend`` flag is accepted but unused by --self-test —
the stub fixtures are crafted in-process so no live backend call is made.)
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
# Matches the §8D.45 canonical "university library" lodestar query, reused
# by probe_live_archive_scan.py — keeps the retrieval index populated with
# the same well-understood real-world content.
ARCHIVE_QUERY = "university library"
ARCHIVE_URL = (
    "https://archive.org/search?query="
    + urllib.parse.quote_plus(ARCHIVE_QUERY)
)
# Hard ceiling so a flaky archive.org doesn't hang the probe.
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


def _delete(url: str, timeout: float = 30.0) -> Dict[str, Any]:
    req = urllib.request.Request(url, method="DELETE")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Pure, directly-callable assertion helpers — unit-testable in isolation and
# exercised by --self-test below WITHOUT booting any real subsystem.
# ---------------------------------------------------------------------------

def assert_all_real(status: Dict[str, Any]) -> None:
    """§8D.46 — raises unless ``/api/subsystem_status`` reports every
    subsystem real. No stub fallback is permitted past this gate."""
    _assert(isinstance(status, dict),
            f"subsystem_status must be a dict, got {type(status)}")
    _assert(status.get("all_real") is True,
            f"subsystems are NOT all real (no-mocks contract §8D.46 "
            f"violated): {status}")


def _cone_apex_distance(transport: Dict[str, Any]) -> float:
    """The scalar cone-apex distance the §O.18 contract is monotonic over.

    Mirrors the frontend's halo_cone.mjs decision (08-02 SUMMARY decisions):
    ``radial`` IS the authoritative apex-distance metric ("most-similar
    nearest the apex" per routes.py's own comment), NOT the combined
    Euclidean distance of radial+along_ray (which is U-shaped/non-monotonic
    for the backend's ``(1-s)*R`` / ``s*R`` formula — verified numerically
    in 08-02). This probe asserts on ``radial`` for that same reason.
    """
    return float(transport["radial"])


def assert_cone_monotonic(candidates: List[Dict[str, Any]]) -> None:
    """§O.18 — across a candidate list each carrying ``transport.{similarity,
    radial,along_ray}``, asserts that sorting candidates by DESCENDING
    similarity yields a NON-DECREASING ``radial`` (apex distance) — i.e.
    more-similar candidates sit no farther from the cone apex than
    less-similar ones. Raises AssertionError on the first violation.

    Requires at least 2 candidates with a ``transport`` block to assert
    anything meaningful; raises if fewer are present (a monotonicity claim
    over 0-1 points is vacuous and likely indicates a broken retrieval).
    """
    transported = [c for c in candidates if c.get("transport")]
    _assert(len(transported) >= 2,
            f"need >=2 transported candidates to assert monotonicity, got "
            f"{len(transported)} of {len(candidates)}: {candidates!r}")
    ordered = sorted(transported,
                      key=lambda c: c["transport"]["similarity"],
                      reverse=True)
    prev_radial = None
    prev_sim = None
    for c in ordered:
        t = c["transport"]
        radial = _cone_apex_distance(t)
        sim = float(t["similarity"])
        if prev_radial is not None:
            _assert(radial >= prev_radial - 1e-9,
                    f"cone placement NOT monotonic: candidate with "
                    f"similarity={sim} (radial={radial}) sits CLOSER to the "
                    f"apex than a strictly more-similar candidate "
                    f"(similarity={prev_sim}, radial={prev_radial}) — "
                    f"violates §O.18 'most-similar nearest the apex'")
        prev_radial = radial
        prev_sim = sim


def assert_delete_transports_next(before: List[Dict[str, Any]],
                                   after: List[Dict[str, Any]]) -> None:
    """§O.18/§O.14 — after deleting the top (most-similar) candidate from
    ``before`` and re-querying into ``after``, the candidate that was
    second-most-similar in ``before`` must now occupy the nearest-apex
    (smallest ``radial``) slot in ``after`` — it "transports in" to fill
    the vacated cone position.

    Raises if ``before`` has fewer than 2 transported candidates (nothing
    to promote), if the expected promoted id is missing from ``after``, or
    if it does not occupy the nearest-apex slot in ``after``.
    """
    before_t = [c for c in before if c.get("transport")]
    after_t = [c for c in after if c.get("transport")]
    _assert(len(before_t) >= 2,
            f"need >=2 transported candidates in 'before' to assert "
            f"delete-transports-next, got {len(before_t)}")
    _assert(len(after_t) >= 1,
            f"'after' has zero transported candidates: {after!r}")

    before_ordered = sorted(before_t,
                             key=lambda c: c["transport"]["similarity"],
                             reverse=True)
    top_id = before_ordered[0].get("card_id")
    expected_next_id = before_ordered[1].get("card_id")

    after_ids = [c.get("card_id") for c in after_t]
    _assert(top_id not in after_ids,
            f"deleted top candidate {top_id!r} still present in 'after' "
            f"candidate list: {after_ids!r}")
    _assert(expected_next_id in after_ids,
            f"expected next-most-similar candidate {expected_next_id!r} "
            f"(from 'before') missing from 'after' candidate list: "
            f"{after_ids!r}")

    after_ordered = sorted(after_t,
                            key=lambda c: _cone_apex_distance(c["transport"]))
    nearest_apex_id = after_ordered[0].get("card_id")
    _assert(nearest_apex_id == expected_next_id,
            f"next-most-similar candidate {expected_next_id!r} did NOT "
            f"transport into the vacated nearest-apex slot after deleting "
            f"{top_id!r} — nearest-apex slot in 'after' is occupied by "
            f"{nearest_apex_id!r} instead "
            f"(after order by radial: {[c.get('card_id') for c in after_ordered]!r})")


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
        "frame_counts":     counts,
        "nodes_streamed":   nodes_so_far,
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
    _assert(summary["completed"], f"scan never completed: {summary}")
    _assert(summary["nodes_streamed"] > 0,
            f"scan completed with zero nodes streamed: {summary}")
    print(f"  [OK] real chunks streamed from the live archive.org scan")
    return summary


def step_chunk_search_focal(backend: str) -> List[str]:
    """Real retrieval over the real scan; returns >=2 real chunk-node ids
    ordered as the search engine ranked them (first id is the probe's
    focal — the 2D-query-element analog the halo opens on)."""
    _section("4) POST /api/chunk_search -> real chunk-node ids")
    resp = _post(f"{backend}/api/chunk_search", {
        "query": ARCHIVE_QUERY,
        "page_limit": 10,
        "instance_limit_per_page": 5,
    }, timeout=60)
    ids: List[str] = []
    for p in (resp.get("pages") or []):
        for inst in (p.get("instances") or []):
            if inst.get("id"):
                ids.append(inst["id"])
    _assert(len(ids) >= 2,
            f"need >=2 real chunk-node ids from chunk_search to drive a "
            f"focal + transport assertion, got {len(ids)}: {resp}")
    print(f"  real chunk-node ids found: {len(ids)}")
    print(f"  focal candidate: {ids[0]}")
    return ids


def step_apparitions_transport(backend: str, focal_id: str) -> List[Dict[str, Any]]:
    _section(f"5) GET /api/apparitions/{focal_id}?transport=1&ray_project=1")
    encoded = urllib.parse.quote(focal_id, safe="")
    resp = _get(
        f"{backend}/api/apparitions/{encoded}"
        f"?transport=1&ray_project=1&k=10",
        timeout=60,
    )
    candidates = resp.get("candidates") or []
    print(f"  candidates returned: {len(candidates)}")
    for c in candidates[:6]:
        t = c.get("transport") or {}
        print(f"    {c.get('card_id')!r:>40}  score={c.get('score'):.4f}  "
              f"similarity={t.get('similarity')}  radial={t.get('radial')}  "
              f"along_ray={t.get('along_ray')}")
    return candidates


def step_assert_monotonic(candidates: List[Dict[str, Any]]) -> None:
    _section("6) ASSERT cone placement monotonic in real triple-product similarity")
    assert_cone_monotonic(candidates)
    print("  [OK] candidates ordered by descending similarity have "
          "non-decreasing radial (apex distance) — §O.18 holds against "
          "the REAL retrieval")


def step_delete_top_and_reassert(backend: str, focal_id: str,
                                  before: List[Dict[str, Any]]) -> None:
    _section("7) Delete top candidate -> assert next-most-similar transports in")
    transported = [c for c in before if c.get("transport")]
    ordered = sorted(transported,
                      key=lambda c: c["transport"]["similarity"],
                      reverse=True)
    top_id = ordered[0]["card_id"]
    expected_next = ordered[1]["card_id"]
    print(f"  deleting top candidate: {top_id}")
    print(f"  expecting promotion of: {expected_next}")
    del_resp = _delete(f"{backend}/api/concepts/{urllib.parse.quote(top_id, safe='')}")
    _assert(del_resp.get("ok") is True,
            f"DELETE /api/concepts/{top_id} did not report ok: {del_resp}")
    encoded = urllib.parse.quote(focal_id, safe="")
    after_resp = _get(
        f"{backend}/api/apparitions/{encoded}"
        f"?transport=1&ray_project=1&k=10",
        timeout=60,
    )
    after = after_resp.get("candidates") or []
    print(f"  re-queried candidates: {len(after)}")
    for c in after[:6]:
        t = c.get("transport") or {}
        print(f"    {c.get('card_id')!r:>40}  similarity={t.get('similarity')}  "
              f"radial={t.get('radial')}")
    assert_delete_transports_next(before, after)
    print(f"  [OK] {expected_next!r} transported into the vacated "
          f"nearest-apex slot after deleting {top_id!r}")


# ---------------------------------------------------------------------------
# Self-test — STUB mode, fully in-process, proves the gate + scaffold have
# teeth WITHOUT booting any real subsystem or requiring a live backend.
# ---------------------------------------------------------------------------

def run_self_test() -> int:
    """Proves, in-process, with crafted fixtures (no live backend call):

    (a) the all_real gate FIRES — a stub ``all_real:false`` status fed into
        ``assert_all_real`` raises (caught here as the EXPECTED outcome),
        and a real-looking ``all_real:true`` status passes.
    (b) ``assert_cone_monotonic`` has teeth — raises on a deliberately
        NON-monotonic candidate set (a less-similar candidate placed
        nearer the apex than a more-similar one) and passes on a
        monotonic one.
    (c) ``assert_delete_transports_next`` has teeth — raises when the
        expected next-most-similar candidate is NOT promoted into the
        vacated nearest-apex slot, and passes on a correctly-promoted
        fixture.

    Exits 0 only if every behavioral expectation above held.
    """
    failures: List[str] = []

    _section("self-test (a): all_real gate fires on a stub all_real:false status")
    try:
        assert_all_real({"all_real": False, "slm": {}, "embedder": {}})
        failures.append(
            "assert_all_real did NOT raise on a stub all_real:false "
            "status — the gate has no teeth"
        )
    except AssertionError:
        print("  [OK] assert_all_real raised on a stub all_real:false status")
    try:
        assert_all_real({"all_real": True, "slm": {}, "embedder": {}})
        print("  [OK] assert_all_real passed on a stub all_real:true status")
    except AssertionError as e:
        failures.append(f"assert_all_real raised on a VALID all_real:true status: {e}")

    _section("self-test (b): assert_cone_monotonic has teeth")
    monotonic_fixture = [
        {"card_id": "a", "score": 0.9,
         "transport": {"similarity": 1.0, "radial": 0.0, "along_ray": 40.0}},
        {"card_id": "b", "score": 0.5,
         "transport": {"similarity": 0.5, "radial": 20.0, "along_ray": 20.0}},
        {"card_id": "c", "score": 0.1,
         "transport": {"similarity": 0.0, "radial": 40.0, "along_ray": 0.0}},
    ]
    non_monotonic_fixture = [
        {"card_id": "a", "score": 0.9,
         # BROKEN: most-similar candidate placed FARTHEST from the apex.
         "transport": {"similarity": 1.0, "radial": 40.0, "along_ray": 0.0}},
        {"card_id": "b", "score": 0.5,
         "transport": {"similarity": 0.5, "radial": 20.0, "along_ray": 20.0}},
        {"card_id": "c", "score": 0.1,
         "transport": {"similarity": 0.0, "radial": 0.0, "along_ray": 40.0}},
    ]
    try:
        assert_cone_monotonic(non_monotonic_fixture)
        failures.append(
            "assert_cone_monotonic did NOT raise on a deliberately "
            "non-monotonic candidate set — the assertion has no teeth"
        )
    except AssertionError:
        print("  [OK] assert_cone_monotonic raised on a non-monotonic fixture")
    try:
        assert_cone_monotonic(monotonic_fixture)
        print("  [OK] assert_cone_monotonic passed on a monotonic fixture")
    except AssertionError as e:
        failures.append(f"assert_cone_monotonic raised on a VALID monotonic fixture: {e}")

    _section("self-test (c): assert_delete_transports_next has teeth")
    before_fixture = monotonic_fixture  # a=most similar, b=next, c=least
    after_correct = [
        # 'a' deleted; 'b' (the expected next-most-similar) now nearest-apex.
        {"card_id": "b", "score": 0.5,
         "transport": {"similarity": 0.5, "radial": 0.0, "along_ray": 40.0}},
        {"card_id": "c", "score": 0.1,
         "transport": {"similarity": 0.0, "radial": 40.0, "along_ray": 0.0}},
    ]
    after_wrong = [
        # 'a' deleted; but 'c' wrongly occupies the nearest-apex slot
        # instead of 'b' — the promotion did NOT happen as expected.
        {"card_id": "c", "score": 0.1,
         "transport": {"similarity": 0.0, "radial": 0.0, "along_ray": 40.0}},
        {"card_id": "b", "score": 0.5,
         "transport": {"similarity": 0.5, "radial": 40.0, "along_ray": 0.0}},
    ]
    try:
        assert_delete_transports_next(before_fixture, after_wrong)
        failures.append(
            "assert_delete_transports_next did NOT raise on a wrongly-"
            "promoted 'after' fixture — the assertion has no teeth"
        )
    except AssertionError:
        print("  [OK] assert_delete_transports_next raised on a wrong-promotion fixture")
    try:
        assert_delete_transports_next(before_fixture, after_correct)
        print("  [OK] assert_delete_transports_next passed on a correctly-"
              "promoted fixture")
    except AssertionError as e:
        failures.append(
            f"assert_delete_transports_next raised on a VALID correctly-"
            f"promoted fixture: {e}")

    if failures:
        print(f"\n[probe_live_cone_transport --self-test] FAILED "
              f"({len(failures)} expectation(s) not met):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\n[probe_live_cone_transport --self-test] ALL EXPECTATIONS HELD — "
          f"the all_real gate fires and the monotonicity/delete-transport "
          f"assertion scaffold has teeth (no live backend was contacted)")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="LIVE probe for the §O.18 halo cone-ray transport (HALO-03, D-01)")
    parser.add_argument("--backend", default=DEFAULT_BACKEND,
                        help=f"backend base URL (default: {DEFAULT_BACKEND}); "
                             f"unused by --self-test")
    parser.add_argument("--self-test", action="store_true",
                        help="run the STUB-mode in-process self-test instead "
                             "of the real cone-transport run (no real "
                             "subsystem boot, no live backend call)")
    args = parser.parse_args(argv)
    backend = args.backend

    if args.self_test:
        print("[probe_live_cone_transport] --self-test (fully in-process, "
              "no live backend)")
        return run_self_test()

    print(f"[probe_live_cone_transport] LIVE end-to-end run against {backend}")
    print(f"[probe_live_cone_transport] query = {ARCHIVE_QUERY!r}")
    print("[probe_live_cone_transport] MAIN-CONTEXT-ONLY: never run this "
          "from a verifier subagent — a wedged CUDA/Selenium boot hangs it.")

    try:
        step_subsystem_real(backend)
        snap_id = step_trigger_scan(backend)
        asyncio.run(step_watch_scan(backend, snap_id))
        ids = step_chunk_search_focal(backend)
        focal_id = ids[0]
        before = step_apparitions_transport(backend, focal_id)
        step_assert_monotonic(before)
        step_delete_top_and_reassert(backend, focal_id, before)
        print(f"\n[probe_live_cone_transport] ALL CHECKS PASS — real "
              f"archive.org scan + real triple-product retrieval + real "
              f"cone-ray transport monotonicity + real delete-transports-"
              f"next, end-to-end (§O.18 / HALO-03 / D-01)")
        return 0
    except AssertionError as e:
        print(f"\n[probe_live_cone_transport] FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
