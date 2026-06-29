"""STEP-01 / D10 — signal-stream cursor resolves a real 3D chunk id.

Verbatim anchor (08-03-PLAN.md Open-Q1, resolved BACKEND-SIDE): "populate
the EXISTING `signal_id` field from an ordered sampled-chunk list at the
cursor index, backend-side." Confirmed gap (08-PATTERNS.md): no caller in
the codebase ever set `signal_id` to a real chunk concept_id before this
plan — `set_signal_stream`/`advance_signal` only ever passed through
whatever was already in the dict.

Drives the REAL `UIStateService` directly (no Kuzu, no graph editor needed)
— mirrors `test_signal_iteration_rerender.py`'s in-memory-service pattern.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.ui_state_service import UIStateService

WS = "ws_signal_chunk_id"


def _svc():
    return UIStateService()


def test_set_signal_stream_resolves_signal_id_from_ordered_at_index():
    """Test 1: set_signal_stream(card, total=N, signal_index=k,
    ordered=[c0..cN-1]) stores an entry whose signal_id == ordered[k]."""
    ui = _svc()
    ordered = ["chunk_a", "chunk_b", "chunk_c"]
    snap = ui.set_signal_stream(
        WS, "bank", total=3, signal_index=1, ordered=ordered,
    )
    entry = (snap.signal_stream or {}).get("bank") or {}
    assert entry.get("signal_id") == "chunk_b"


def test_advance_signal_rewraps_and_reresolves_signal_id():
    """Test 2: advance_signal moves signal_index by step (modulo total) AND
    re-resolves signal_id to ordered[new_index] — wrapping from the last
    index back to 0 resolves signal_id == ordered[0]."""
    ui = _svc()
    ordered = ["chunk_a", "chunk_b", "chunk_c"]
    ui.set_signal_stream(WS, "bank", total=3, signal_index=2, ordered=ordered)

    snap = ui.advance_signal(WS, "bank", step=1)
    entry = (snap.signal_stream or {}).get("bank") or {}
    assert int(entry.get("signal_index")) == 0  # wrapped 2 -> 0
    assert entry.get("signal_id") == "chunk_a"  # re-resolved at the new index

    snap = ui.advance_signal(WS, "bank", step=1)
    entry = (snap.signal_stream or {}).get("bank") or {}
    assert int(entry.get("signal_index")) == 1
    assert entry.get("signal_id") == "chunk_b"


def test_advance_signal_without_ordered_preserves_prior_signal_id():
    """Test 3: when no ordered list is available for a card (ordered is
    None/empty), advance_signal preserves the prior signal_id rather than
    clobbering it to None (backward-compatible with existing callers —
    RolloutCoordinator.play/pause/reset — that never pass ordered)."""
    ui = _svc()
    # A pre-STEP-01-shaped caller: signal_id supplied directly, no ordered list.
    ui.set_signal_stream(WS, "legacy_card", total=4, signal_index=0,
                         signal_id="manually_set_id")
    snap = ui.advance_signal(WS, "legacy_card", step=1)
    entry = (snap.signal_stream or {}).get("legacy_card") or {}
    assert int(entry.get("signal_index")) == 1
    assert entry.get("signal_id") == "manually_set_id", (
        "signal_id must be preserved, not clobbered to None, when no "
        "ordered list was ever registered for this card"
    )


def test_out_of_range_index_resolves_to_none_never_raises():
    """Test 4 (bounds, V5): a signal_index that would index out of
    ordered's range resolves signal_id to None, never raising — total and
    len(ordered) disagreeing must not crash the cursor."""
    ui = _svc()
    # total=5 but ordered only has 2 entries — a total/ordered mismatch.
    ordered = ["chunk_a", "chunk_b"]
    snap = ui.set_signal_stream(WS, "mismatched", total=5, signal_index=0,
                                ordered=ordered)
    entry = (snap.signal_stream or {}).get("mismatched") or {}
    assert entry.get("signal_id") == "chunk_a"

    # Advance forward into the out-of-range zone (index 2..4 have no
    # corresponding ordered element) — must resolve None, not raise.
    snap = ui.advance_signal(WS, "mismatched", step=2)
    entry = (snap.signal_stream or {}).get("mismatched") or {}
    assert int(entry.get("signal_index")) == 2
    assert entry.get("signal_id") is None

    # Keep advancing through the mismatched tail and finally wrap back to 0
    # (modulo total=5) — signal_id must re-resolve correctly once back in range.
    snap = ui.advance_signal(WS, "mismatched", step=3)  # 2 + 3 = 5 % 5 = 0
    entry = (snap.signal_stream or {}).get("mismatched") or {}
    assert int(entry.get("signal_index")) == 0
    assert entry.get("signal_id") == "chunk_a"
