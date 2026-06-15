"""§R.7 — dynamic signal rendering over iteration (per-sample cascade re-fire).

Verbatim anchor (USER_REQUIREMENTS_VERBATIM.md §R.7): "Dynamic signal
rendering of structures over iteration on recursive-chunked tree-like
structures within the dialected graph-panel rendering scheme itself is also
present, along with a recognition in terms of design influence of
asynchronous recurrence over these structures in computation-graph-walk
time."

Domain anchor (DOMAIN_MODEL §4.6.1): "the cascade re-fires *per visible
signal*, not once for the whole iterable."

Drives the REAL RolloutCoordinator + REAL UIStateService + REAL cascade
(`_cascade_recompile_consumers`) + REAL ConceptComputeNode template compile.
No subsystem fakes (plain-kind compiles never touch the SLM).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.graph_editor import GraphEditor
from backend.services.rollout_coordinator import RolloutCoordinator
from backend.services.ui_state_service import UIStateService

WS = "ws_signal_iter"


def _world():
    """An iterable bank card (recursive-chunked sample holder) + a consumer
    whose data block references it, + a second-order consumer (the recursive
    tree shape: bank → reader → summary)."""
    ge = GraphEditor()
    ge.create_concept(concept_id="bank", name="bank",
                      description="sample bank",
                      data="sample-0", workspace_id=WS)
    ge.create_concept(concept_id="reader", name="reader",
                      description="reads the visible sample",
                      data="saw: {bank}", workspace_id=WS)
    ge.create_concept(concept_id="summary", name="summary",
                      description="summarises the reader",
                      data="summary of: {reader}", workspace_id=WS)
    ui = UIStateService()
    frames = []
    rc = RolloutCoordinator(
        ui_state_service=ui,
        broadcast=lambda sid, frame: frames.append(frame),
        graph_editor=ge,
    )
    ui.set_signal_stream(WS, "bank", total=3, signal_index=0,
                         paused=True, field_path="data")
    return ge, ui, rc, frames


def test_advance_refires_cascade_per_visible_signal():
    ge, ui, rc, frames = _world()
    assert (ge.get_concept("reader").rendering or "") == ""

    snap = rc.advance(WS, "bank", "data")
    entry = (snap.signal_stream or {}).get("bank") or {}
    assert int(entry.get("signal_index")) == 1

    # The consumer recompiled against the visible sample — and the cascade
    # walked the RECURSIVE tree: the second-order consumer re-rendered too.
    reader = ge.get_concept("reader")
    assert reader.rendering == "saw: sample-0"
    summary = ge.get_concept("summary")
    assert summary.rendering == "summary of: saw: sample-0"


def test_iteration_tracks_per_sample_data():
    """Swap the iterable's visible sample between advances (what the sample
    stepper does per §7.5) — each advance re-renders downstream against the
    CURRENT sample, never a stale one (E.9 diff-consistent state)."""
    ge, ui, rc, frames = _world()

    rc.advance(WS, "bank", "data")
    assert ge.get_concept("reader").rendering == "saw: sample-0"

    ge.update_concept("bank", data="sample-1")
    rc.advance(WS, "bank", "data")
    assert ge.get_concept("reader").rendering == "saw: sample-1"
    assert ge.get_concept("summary").rendering == "summary of: saw: sample-1"


def test_advance_logs_sample_boundary():
    """§3.3 — every advance lands a sample_boundary diff in the evolution
    log (rollback restores the iteration index with the data state)."""
    from backend.services.evolution_log import get_evolution_log

    ge, ui, rc, frames = _world()
    rc.advance(WS, "bank", "data")
    diffs = get_evolution_log().list_diffs(workspace_id=WS, limit=50)
    boundaries = [d for d in diffs if d.kind == "sample_boundary"
                  and d.target == "rollout:bank::data"]
    assert boundaries, "no sample_boundary diff recorded"
    last = boundaries[-1]
    assert last.before["signal_index"] == 0
    assert last.after["signal_index"] == 1


def test_wraparound_advance_still_refires():
    """The modulo wrap (index total-1 → 0) is still a cursor move — the
    per-sample re-fire must run."""
    ge, ui, rc, frames = _world()
    ui.set_signal_stream(WS, "bank", total=3, signal_index=2,
                         paused=True, field_path="data")
    ge.update_concept("bank", data="sample-2")
    snap = rc.advance(WS, "bank", "data")
    entry = (snap.signal_stream or {}).get("bank") or {}
    assert int(entry.get("signal_index")) == 0  # wrapped
    assert ge.get_concept("reader").rendering == "saw: sample-2"
