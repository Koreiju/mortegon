"""Verify §8D.39.6 backing-pointer version mechanics.

Two paths exercised:

1. **Pure registry mechanics** — direct calls to ``backing_version``
   show monotone bumps, persistence shape, and per-workspace reset.

2. **End-to-end through compiled-from-scans** — re-materialise the
   same SearchableURL twice and confirm the version seq advanced.
   Then check that ``ConceptDiff`` exposed ``backing_version_bumped``
   would have flipped True for a no-op data update against the
   stale snapshot.
"""

from __future__ import annotations

import sys
# Windows consoles default to cp1252, which can't encode probe-output
# glyphs (→, §). Force UTF-8 so the probe prints cleanly everywhere.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import backing_version
from backend.services.concept_lifecycle import ConceptDiff


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def check_registry_mechanics() -> None:
    backing_version.reset()  # start clean
    ws = "probe_ws"
    bp = "compiled_from_scans::searchable_url::probe_xyz"

    _assert(backing_version.current(ws, bp) == 0, "unbumped key should read 0")
    new1 = backing_version.bump(ws, bp)
    _assert(new1 == 1, f"first bump should return 1, got {new1}")
    new2 = backing_version.bump(ws, bp)
    _assert(new2 == 2, f"second bump should return 2, got {new2}")
    _assert(backing_version.current(ws, bp) == 2, "current should match latest bump")

    # Other workspaces / pointers are independent.
    _assert(backing_version.current("other_ws", bp) == 0,
            "version is per-workspace")
    _assert(backing_version.current(ws, "compiled_from_scans::other") == 0,
            "version is per-backing-pointer")

    snap = backing_version.snapshot()
    _assert(f"{ws}::{bp}" in snap, "snapshot key shape")
    _assert(snap[f"{ws}::{bp}"] == 2, "snapshot value")

    # Per-workspace reset is scoped.
    backing_version.bump("other_ws", bp)
    backing_version.reset(ws)
    _assert(backing_version.current(ws, bp) == 0, "ws reset zeroes ws key")
    _assert(backing_version.current("other_ws", bp) == 1,
            "ws reset leaves other workspaces alone")
    print("  registry mechanics OK")


def check_concept_diff_integration() -> None:
    backing_version.reset()
    ws = "probe_diff_ws"
    bp = "compiled_from_scans::xpath_pattern::abc"

    # Build a tiny ad-hoc node-like object.
    class _Node:
        workspace_id = ws
        backing_pointer = bp
        data = '{"x":1}'
        description = "static"
        rendering = "<r>"

    pre = {"data": '{"x":1}', "description": "static", "rendering": "<r>"}

    # No version bump → diff is clean.
    diff0 = ConceptDiff.from_pre_post(pre, _Node(), pre_backing_version=0)
    _assert(not diff0.data_changed, "no field change → data_changed=False")
    _assert(not diff0.backing_version_bumped, "no bump → flag stays False")
    _assert(not diff0.effective_data_changed, "no field + no bump → effective stays False")

    # Bump the registry, recompute the diff against the same pre snapshot.
    backing_version.bump(ws, bp)
    diff1 = ConceptDiff.from_pre_post(pre, _Node(), pre_backing_version=0)
    _assert(not diff1.data_changed, "data text still unchanged")
    _assert(diff1.backing_version_bumped, "registry now ahead of pre → bumped=True")
    _assert(diff1.effective_data_changed,
            "effective_data_changed must flip True on a backing-version bump")
    print("  ConceptDiff integration OK")


def check_searchable_url_roundtrip() -> None:
    backing_version.reset()
    from backend.services.graph_editor import GraphEditor
    from backend.services.compiled_from_scans import CompiledFromScansMaterialiser

    ge = GraphEditor()
    mat = CompiledFromScansMaterialiser(graph_editor=ge)
    ws = "probe_e2e_ws"
    url = "https://example.com/search"
    xpath = "/html/body/form/input"

    rec1 = mat.materialise_searchable_url(
        url=url, search_field_xpath=xpath, workspace_id=ws,
    )
    _assert(rec1 is not None, "materialise returned record")
    bp = f"compiled_from_scans::searchable_url::{rec1['concept_id']}"
    _assert(backing_version.current(ws, bp) == 1,
            "first materialise bumps to 1")

    # Second materialise (idempotent on concept_id) should bump again.
    mat.materialise_searchable_url(
        url=url, search_field_xpath=xpath, workspace_id=ws,
    )
    _assert(backing_version.current(ws, bp) == 2,
            "second materialise bumps to 2")

    # Reset wipes this workspace.
    backing_version.reset(ws)
    _assert(backing_version.current(ws, bp) == 0, "purge resets to 0")
    print("  SearchableURL roundtrip OK")


def main() -> int:
    print("[probe_backing_version] verifying §8D.39.6 mechanics")
    check_registry_mechanics()
    check_concept_diff_integration()
    check_searchable_url_roundtrip()
    print("[probe_backing_version] ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
