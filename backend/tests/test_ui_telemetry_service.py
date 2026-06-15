"""Unit tests for backend.services.ui_telemetry_service.

The service is the frontend → backend pipe for MutationObserver
reports. Tests cover:

  * Push assigns monotonic per-workspace seqs.
  * Drain with since_seq paginates correctly.
  * Drain is non-destructive (multiple consumers).
  * Workspace isolation (workspaces don't see each other's entries).
  * clear_workspace wipes both buffer + seq counter.
  * Push triggers the broadcast callable when one is wired.
  * Bounded cap rolls oldest entries off the head.
"""

from __future__ import annotations

from backend.services.ui_telemetry_service import (
    UITelemetryService,
    TelemetryEntry,
)


def test_push_assigns_monotonic_seqs():
    svc = UITelemetryService()
    e1 = svc.push("ws1", kind="a")
    e2 = svc.push("ws1", kind="b")
    e3 = svc.push("ws1", kind="c")
    assert (e1.seq, e2.seq, e3.seq) == (1, 2, 3)


def test_drain_with_since_seq_paginates():
    svc = UITelemetryService()
    for k in ("a", "b", "c", "d"):
        svc.push("ws1", kind=k)
    # since_seq=2 → entries with seq > 2 (i.e. seq 3 and 4)
    tail = svc.drain("ws1", since_seq=2)
    assert [e.kind for e in tail] == ["c", "d"]
    # since_seq=0 returns everything currently buffered
    all_entries = svc.drain("ws1", since_seq=0)
    assert len(all_entries) == 4


def test_drain_is_non_destructive():
    svc = UITelemetryService()
    svc.push("ws1", kind="a")
    svc.push("ws1", kind="b")
    # First consumer drains
    first = svc.drain("ws1", since_seq=0)
    # Second consumer drains the same range
    second = svc.drain("ws1", since_seq=0)
    assert [e.seq for e in first] == [e.seq for e in second]
    # Entries still in buffer
    assert len(svc.drain("ws1", since_seq=0)) == 2


def test_workspaces_are_isolated():
    svc = UITelemetryService()
    svc.push("ws1", kind="a")
    svc.push("ws1", kind="b")
    svc.push("ws2", kind="c")
    # ws1 sees only its 2; ws2 sees only its 1
    assert len(svc.drain("ws1", since_seq=0)) == 2
    assert len(svc.drain("ws2", since_seq=0)) == 1
    # Sequence counters are per-workspace — first push in each
    # workspace gets seq=1, not a shared counter.
    assert svc.head_seq("ws1") == 2
    assert svc.head_seq("ws2") == 1


def test_clear_workspace_drops_buffer_and_seq():
    svc = UITelemetryService()
    svc.push("ws1", kind="a")
    svc.push("ws1", kind="b")
    svc.clear_workspace("ws1")
    assert svc.drain("ws1", since_seq=0) == []
    assert svc.head_seq("ws1") == 0
    # Next push restarts the seq counter from 1
    e = svc.push("ws1", kind="c")
    assert e.seq == 1


def test_push_invokes_broadcast_callable():
    captured = []

    def _b(seq, frame):
        captured.append((seq, frame))

    svc = UITelemetryService(broadcast=_b)
    svc.push("ws1", kind="card-added", target_id="X", count=3,
             extra={"foo": "bar"})
    assert len(captured) == 1
    snap, frame = captured[0]
    assert frame["type"] == "ui_telemetry"
    assert frame["workspace_id"] == "ws1"
    assert frame["entry"]["kind"] == "card-added"
    assert frame["entry"]["target_id"] == "X"
    assert frame["entry"]["count"] == 3
    assert frame["entry"]["extra"] == {"foo": "bar"}


def test_bounded_cap_rolls_off_head():
    svc = UITelemetryService(cap=3)
    for k in ("a", "b", "c", "d", "e"):
        svc.push("ws1", kind=k)
    out = svc.drain("ws1", since_seq=0)
    # Cap=3 keeps the 3 most-recent entries (c, d, e); seqs 3,4,5.
    assert [e.kind for e in out] == ["c", "d", "e"]
    assert [e.seq for e in out] == [3, 4, 5]
    # head_seq tracks the most-recent assigned seq even after rolloff
    assert svc.head_seq("ws1") == 5


def test_empty_kind_rejected():
    svc = UITelemetryService()
    import pytest
    with pytest.raises(ValueError):
        svc.push("ws1", kind="")


def test_default_workspace_id_normalised():
    """Empty workspace_id collapses to '_default' so the CLI's bare
    default workspace and the explicit '_default' literal share state.
    """
    svc = UITelemetryService()
    svc.push("", kind="a")
    svc.push("_default", kind="b")
    # Both routed to the same per-workspace buffer
    assert len(svc.drain("_default", since_seq=0)) == 2
    assert len(svc.drain("", since_seq=0)) == 2
