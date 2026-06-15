"""Tests for the ActivityService."""
import pytest
from backend.services.activity_service import ActivityService, ActivityEntry


@pytest.fixture
def activity_svc():
    return ActivityService()


def test_emit_creates_entry(activity_svc):
    entry = activity_svc.emit(
        actor="mapper",
        action_verb="scanned",
        target_type="snapshot",
        target_id="snap-123",
        summary="Mapper scanned snapshot snap-123",
    )
    assert entry.entry_id
    assert entry.actor == "mapper"
    assert entry.action_verb == "scanned"
    assert entry.target_type == "snapshot"


def test_get_history(activity_svc):
    activity_svc.emit(actor="user", action_verb="labeled", target_type="node", target_id="n1")
    activity_svc.emit(actor="slm", action_verb="embedded", target_type="cluster", target_id="c1")
    activity_svc.emit(actor="media_pipeline", action_verb="downloaded", target_type="media_asset", target_id="m1")

    history = activity_svc.get_history(limit=10)
    assert len(history) == 3
    # Reverse chronological: most recent first
    assert history[0]["actor"] == "media_pipeline"
    assert history[2]["actor"] == "user"


def test_history_filtering(activity_svc):
    activity_svc.emit(actor="user", action_verb="labeled", target_type="node", target_id="n1")
    activity_svc.emit(actor="slm", action_verb="embedded", target_type="cluster", target_id="c1")
    activity_svc.emit(actor="user", action_verb="edited", target_type="node", target_id="n2")

    user_history = activity_svc.get_history(actor_filter="user")
    assert len(user_history) == 2

    node_history = activity_svc.get_history(target_type_filter="node")
    assert len(node_history) == 2


def test_causal_chain(activity_svc):
    e1 = activity_svc.emit(actor="user", action_verb="labeled", target_type="node", target_id="n1")
    e2 = activity_svc.emit(
        actor="slm", action_verb="auto-labeled", target_type="cluster",
        target_id="c1", parent_entry_id=e1.entry_id,
    )
    e3 = activity_svc.emit(
        actor="embedder", action_verb="re-embedded", target_type="segment",
        target_id="s1", parent_entry_id=e2.entry_id,
    )

    chain = activity_svc.get_causal_chain(e3.entry_id)
    assert len(chain) == 3
    # Root cause first
    assert chain[0]["actor"] == "user"
    assert chain[1]["actor"] == "slm"
    assert chain[2]["actor"] == "embedder"


def test_entry_detail(activity_svc):
    entry = activity_svc.emit(
        actor="user", action_verb="edited", target_type="note",
        target_id="note-1",
        diff={"content": {"old": "hello", "new": "hello world"}},
        context={"source": "knowledge_panel"},
    )
    detail = activity_svc.get_entry_detail(entry.entry_id)
    assert detail is not None
    assert detail["diff"]["content"]["new"] == "hello world"


def test_entry_detail_not_found(activity_svc):
    assert activity_svc.get_entry_detail("nonexistent") is None


def test_activity_entry_defaults():
    entry = ActivityEntry(actor="test", action_verb="tested", target_type="unit")
    assert entry.entry_id  # auto-generated UUID
    assert entry.timestamp  # auto-generated
    assert entry.actor_type == "system"
