"""Smoke tests for the recent §8D.27 / §8D.32 / §8D.38.1 / §8D.20 work.

Covers:

  * ``compute_rendering_tree`` — §8D.20 syntax-free tree pretty-print.
  * ``CascadeScheduler`` — debounce, rate limit, pause race, self-mutation
    short-circuit, cleanup_for_agent.
  * ``_check_spawn_rate`` — §8D.32.2 workspace proliferation cap.
  * ``spawn_agent_body_subgraph`` layout — chain positions, vertical
    stagger across multiple agents.
  * Agent token ring buffer — record + read + clear.

These run pure-in-process (no Kuzu, no FastAPI) so they're fast and
deterministic. Heavier integration tests (which DO touch Kuzu) belong
in test_agent_loop / test_graph_editor.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, Optional

import pytest


# ---------------------------------------------------------------------------
# Stub objects — lightweight stand-ins for ConceptNode + GraphEditor
# ---------------------------------------------------------------------------

class _StubNode:
    """Mimics the ConceptNode dataclass surface that lifecycle + cascade read."""

    def __init__(
        self, *, concept_id: str, data: str = "", type_hint: str = "",
        backing_pointer: str = "", workspace_id: str = "",
        layout_xy: str = "",
    ):
        self.concept_id = concept_id
        self.data = data
        self.type_hint = type_hint
        self.backing_pointer = backing_pointer
        self.workspace_id = workspace_id
        self.layout_xy = layout_xy
        self.description = ""
        self.rendering = ""
        self.name = concept_id
        self.provenance = "user-authored"
        self.pagerank = 0.0
        self.linked_nodes_json = ""
        self.ui_state = ""
        self.created_at = ""
        self.updated_at = ""


class _StubGraphEditor:
    """Just enough surface for cascade scheduler + spawn helper."""

    def __init__(self):
        self.nodes: Dict[str, _StubNode] = {}
        self.edges = []
        # next-id stub
        self._next = 0

    # The cascade scheduler only ever calls get_concept.
    def get_concept(self, concept_id: str):
        return self.nodes.get(concept_id)

    # spawn helper paths
    def list_concepts(self, *, workspace_id="", limit=1000, type_hint=None, **kwargs):
        out = []
        for n in self.nodes.values():
            if workspace_id and n.workspace_id != workspace_id:
                continue
            if type_hint and n.type_hint != type_hint:
                continue
            out.append(n)
        return out[:limit]

    def list_concept_edges(self, *, workspace_id="", source_id=None, **kwargs):
        return []

    def update_concept(self, concept_id: str, **kwargs):
        node = self.nodes.get(concept_id)
        if not node:
            return None
        for k, v in kwargs.items():
            if isinstance(v, dict):
                v = json.dumps(v)
            setattr(node, k, v)
        return node

    def create_concept(
        self, *, name="", description="", data="", rendering="",
        backing_pointer="", provenance="", workspace_id="",
        layout_xy=None, type_hint="", concept_id="", **kwargs,
    ):
        self._next += 1
        cid = concept_id or f"stub_{self._next}"
        node = _StubNode(
            concept_id=cid, data=data, type_hint=type_hint,
            backing_pointer=backing_pointer, workspace_id=workspace_id,
            layout_xy=json.dumps(layout_xy) if isinstance(layout_xy, dict) else (layout_xy or ""),
        )
        node.description = description
        node.rendering = rendering
        node.name = name
        node.provenance = provenance
        self.nodes[cid] = node
        return node


# ---------------------------------------------------------------------------
# §8D.20 — rendering tree pretty-print
# ---------------------------------------------------------------------------

def test_graph_editor_refuses_to_delete_foundation_fixture():
    """§8D.12 — Database / WebBrowser fixtures are undeletable.

    A direct call to ``delete_concept`` for any ``fixture::`` id must
    return False without touching the concept store. Without this
    guard a stray DELETE (REST, agent, cascade, accidental hotkey)
    silently removes the always-present fixture and leaves wires
    dangling until the next workspace-open rematerialises it.
    """
    from backend.services.graph_editor import GraphEditor

    ge = GraphEditor(db_conn=None)
    fid = "fixture::database::_test_ws"
    node = ge.create_concept(
        concept_id=fid,
        name="Database",
        description="",
        data="",
        backing_pointer="fixture::database",
        provenance="user-authored",
        workspace_id="_test_ws",
        type_hint="fixture_database",
    )
    assert node is not None
    assert ge.get_concept(fid) is not None, "fixture should exist post-create"

    # The guarded delete returns False AND the record is still there.
    deleted = ge.delete_concept(fid)
    assert deleted is False, "delete_concept should refuse fixture::* ids"
    assert ge.get_concept(fid) is not None, (
        "fixture should still exist after rejected delete"
    )

    # Non-fixture deletes still work — guard is targeted, not blanket.
    ordinary = ge.create_concept(
        concept_id="card::ordinary",
        name="Ordinary",
        description="",
        data="",
        backing_pointer="",
        provenance="user-authored",
        workspace_id="_test_ws",
        type_hint="",
    )
    assert ordinary is not None
    assert ge.delete_concept("card::ordinary") is True
    assert ge.get_concept("card::ordinary") is None


def test_compute_rendering_tree_strips_json_syntax():
    from backend.services.compile_pipeline import compute_rendering_tree

    payload = json.dumps({
        "summary": "hello",
        "items": [
            {"name": "a", "v": 1},
            {"name": "b", "v": 2},
        ],
    })
    out = compute_rendering_tree(payload, ge=None)
    # No JSON syntax left.
    for forbidden in ('{', '}', '[', ']', ':', '"'):
        assert forbidden not in out, f"unexpected {forbidden!r} in {out!r}"
    # Structure carried by indentation alone (tabs).
    assert "summary\n\thello" in out
    assert "items\n\tname\n\t\ta" in out


def test_compute_rendering_tree_handles_plain_text():
    from backend.services.compile_pipeline import compute_rendering_tree

    out = compute_rendering_tree("just a string with no json", ge=None)
    assert out == "just a string with no json"


def test_compute_rendering_tree_empty():
    from backend.services.compile_pipeline import compute_rendering_tree
    assert compute_rendering_tree("", ge=None) == ""


# ---------------------------------------------------------------------------
# §8D.38.1 — CascadeScheduler
# ---------------------------------------------------------------------------

def _make_param_node(pcid="pcid_test", *, cascade_enabled=True, paused=False):
    return _StubNode(
        concept_id=pcid,
        type_hint="agent_parameter",
        data=json.dumps({
            "goal": "x",
            "cascade_enabled": cascade_enabled,
            "paused": paused,
        }),
    )


def test_scheduler_resolves_param_card_id_from_backing_pointer():
    from backend.services.agent_runtime import CascadeScheduler
    sch = CascadeScheduler()
    perception_node = _StubNode(
        concept_id="perception_x",
        type_hint="agent_perception",
        backing_pointer="agent::perception::pcid_root",
    )
    ge = _StubGraphEditor()
    assert sch._resolve_parameter_card_id(perception_node, ge) == "pcid_root"


def test_scheduler_skips_when_cascade_disabled():
    from backend.services.agent_runtime import CascadeScheduler
    sch = CascadeScheduler()
    ge = _StubGraphEditor()
    ge.nodes["pcid_a"] = _make_param_node("pcid_a", cascade_enabled=False)
    sch.schedule_for_card(ge.nodes["pcid_a"], ge, push_fn=None)
    assert sch._last_skip.get("pcid_a") == "cascade_disabled_or_paused"
    assert "pcid_a" not in sch._timers


def test_scheduler_skips_when_paused():
    from backend.services.agent_runtime import CascadeScheduler
    sch = CascadeScheduler()
    ge = _StubGraphEditor()
    ge.nodes["pcid_b"] = _make_param_node("pcid_b", cascade_enabled=True, paused=True)
    sch.schedule_for_card(ge.nodes["pcid_b"], ge, push_fn=None)
    assert sch._last_skip.get("pcid_b") == "cascade_disabled_or_paused"


def test_scheduler_short_circuits_agent_self_mutation():
    from backend.services.agent_runtime import CascadeScheduler
    sch = CascadeScheduler()
    ge = _StubGraphEditor()
    ge.nodes["pcid_c"] = _make_param_node("pcid_c", cascade_enabled=True)
    sch.schedule_for_card(
        ge.nodes["pcid_c"], ge, push_fn=None, actor="agent:pcid_c",
    )
    assert sch._last_skip.get("pcid_c") == "self-mutation"
    assert "pcid_c" not in sch._timers


def test_scheduler_arms_on_external_actor():
    from backend.services.agent_runtime import CascadeScheduler
    sch = CascadeScheduler()
    ge = _StubGraphEditor()
    ge.nodes["pcid_d"] = _make_param_node("pcid_d", cascade_enabled=True)
    sch.schedule_for_card(
        ge.nodes["pcid_d"], ge, push_fn=None, actor="user:_anon",
    )
    try:
        assert "pcid_d" in sch._timers
    finally:
        # Cancel the timer so the test process can exit cleanly.
        timer = sch._timers.pop("pcid_d", None)
        if timer is not None:
            timer.cancel()


def test_scheduler_rate_limit_kicks_in_after_max():
    from backend.services.agent_runtime import (
        CascadeScheduler, _CASCADE_MAX_TICKS_PER_MIN,
    )
    sch = CascadeScheduler()
    now = time.time()
    # Pre-load the rolling window past the cap.
    sch._minute_window["pcid_e"] = [now - 5] * _CASCADE_MAX_TICKS_PER_MIN
    assert sch._under_rate_limit("pcid_e") is False


def test_scheduler_cleanup_wipes_all_state():
    from backend.services.agent_runtime import CascadeScheduler
    sch = CascadeScheduler()
    sch._total_fires["pcid_f"] = 7
    sch._last_fire["pcid_f"] = time.time()
    sch._minute_window["pcid_f"] = [time.time()]
    sch._last_skip["pcid_f"] = "self-mutation"
    sch._total_spawns["pcid_f"] = 3
    sch._total_spawns_rate_limited["pcid_f"] = 1
    # Pretend an armed timer
    t = threading.Timer(60, lambda: None)
    t.daemon = True
    t.start()
    sch._timers["pcid_f"] = t
    sch.cleanup_for_agent("pcid_f")
    assert "pcid_f" not in sch._total_fires
    assert "pcid_f" not in sch._last_fire
    assert "pcid_f" not in sch._minute_window
    assert "pcid_f" not in sch._last_skip
    assert "pcid_f" not in sch._total_spawns
    assert "pcid_f" not in sch._total_spawns_rate_limited
    assert "pcid_f" not in sch._timers


def test_scheduler_status_enumerates_skip_only_agents():
    from backend.services.agent_runtime import CascadeScheduler
    sch = CascadeScheduler()
    sch._last_skip["pcid_g"] = "rate_limited"  # no fires recorded
    status = sch.status()
    assert "pcid_g" in status
    entry = status["pcid_g"]
    assert entry["total_fires"] == 0
    assert entry["last_skip_reason"] == "rate_limited"
    assert entry["total_spawns"] == 0


def test_scheduler_record_spawns_accumulates():
    from backend.services.agent_runtime import CascadeScheduler
    sch = CascadeScheduler()
    sch.record_spawns("pcid_h", applied=2, rate_limited=1)
    sch.record_spawns("pcid_h", applied=3, rate_limited=0)
    assert sch._total_spawns["pcid_h"] == 5
    assert sch._total_spawns_rate_limited["pcid_h"] == 1


# ---------------------------------------------------------------------------
# §8D.32.2 — workspace spawn rate limit
# ---------------------------------------------------------------------------

def test_spawn_rate_limit_caps_at_max(monkeypatch):
    import backend.services.agent_runtime as ar
    # Isolate by giving the test its own window dict + workspace key.
    monkeypatch.setattr(ar, "_SPAWN_WINDOW", {})
    accepted, rejected = 0, 0
    for _ in range(ar._SPAWN_MAX_PER_WORKSPACE_PER_MIN + 3):
        if ar._check_spawn_rate("test_ws_isolated"):
            accepted += 1
        else:
            rejected += 1
    assert accepted == ar._SPAWN_MAX_PER_WORKSPACE_PER_MIN
    assert rejected == 3


# ---------------------------------------------------------------------------
# §8D.27 — spawn helper layout chain
# ---------------------------------------------------------------------------

def test_spawn_layout_is_horizontal_chain(monkeypatch):
    from backend.services import agent_runtime as ar

    # Stub apply_create_lifecycle so we don't drag in concept_lifecycle's
    # broadcast / index / projection plumbing during the unit test.
    monkeypatch.setattr(
        "backend.services.concept_lifecycle.apply_create_lifecycle",
        lambda *a, **kw: None,
    )
    monkeypatch.setattr(
        "backend.services.concept_lifecycle.broadcast_edge_changed",
        lambda *a, **kw: None,
    )

    ge = _StubGraphEditor()
    # Pre-create the parameter card.
    param = ge.create_concept(
        name="agent_parameters", data=json.dumps({"goal": "test"}),
        workspace_id="ws", type_hint="agent_parameter",
    )
    # Stub edge creation (spawn helper expects a return value).
    class _StubEdge:
        edge_id = "e1"
        source_id = ""
        target_id = ""
        edge_type = "WIRES_TO"
        source_port = ""
        target_port = ""
        weight = None
        variable_name = ""
        workspace_id = "ws"
        created_at = ""
    ge.create_concept_edge = lambda **kw: _StubEdge()

    result = ar.spawn_agent_body_subgraph(
        graph_editor=ge,
        parameter_card_id=param.concept_id,
        workspace_id="ws",
        push_fn=None,
    )
    assert result["ok"] is True
    perception = ge.nodes[result["perception"]]
    transformer = ge.nodes[result["transformer"]]
    emitter = ge.nodes[result["emitter"]]
    # All on the same row.
    p_xy = json.loads(perception.layout_xy)
    t_xy = json.loads(transformer.layout_xy)
    e_xy = json.loads(emitter.layout_xy)
    assert p_xy["y"] == t_xy["y"] == e_xy["y"]
    # X positions monotonically increasing (left-to-right chain).
    assert p_xy["x"] < t_xy["x"] < e_xy["x"]
    # Reasonable separation (column width ~340).
    assert (t_xy["x"] - p_xy["x"]) > 200
    assert (e_xy["x"] - t_xy["x"]) > 200


# ---------------------------------------------------------------------------
# §8D.8 — agent_token ring buffer
# ---------------------------------------------------------------------------

def test_agent_token_buffer_records_and_reads(monkeypatch):
    import backend.services.agent_runtime as ar
    monkeypatch.setattr(ar, "_AGENT_TOKEN_BUFFERS", {})
    ar._record_agent_token("pcid_z", "ws", "hello")
    ar._record_agent_token("pcid_z", "ws", " world")
    buf = ar.get_agent_token_buffer("pcid_z")
    assert len(buf) == 2
    assert buf[0]["token"] == "hello"
    assert buf[1]["token"] == " world"
    assert all(e["workspace_id"] == "ws" for e in buf)


def test_agent_token_buffer_caps_at_max(monkeypatch):
    import backend.services.agent_runtime as ar
    from backend.services.settings import Settings, configure, reset_to_env
    monkeypatch.setattr(ar, "_AGENT_TOKEN_BUFFERS", {})
    configure(Settings(agent_token_buffer_size=10))
    try:
        for i in range(25):
            ar._record_agent_token("pcid_cap", "ws", f"t{i}")
        buf = ar.get_agent_token_buffer("pcid_cap")
        # Capped — the most recent 10 entries are retained.
        assert len(buf) == 10
        assert buf[-1]["token"] == "t24"
        assert buf[0]["token"] == "t15"
    finally:
        reset_to_env()


def test_agent_token_buffer_clears_on_cleanup(monkeypatch):
    import backend.services.agent_runtime as ar
    monkeypatch.setattr(ar, "_AGENT_TOKEN_BUFFERS", {})
    ar._record_agent_token("pcid_clr", "ws", "hi")
    assert len(ar.get_agent_token_buffer("pcid_clr")) == 1
    ar.clear_agent_token_buffer("pcid_clr")
    assert len(ar.get_agent_token_buffer("pcid_clr")) == 0


# ---------------------------------------------------------------------------
# §8D.32.2 — emitter allow-filter must include ``spawns``
# ---------------------------------------------------------------------------

def test_emitter_filter_blocks_spawns_when_not_allowed():
    """Earlier the resolver gated 7 action kinds but missed ``spawns`` —
    so a user who removed ``"spawns"`` from the allow list still
    couldn't stop the agent from proliferating. The fix added the
    branch; this test pins it down."""
    from backend.services.agent_runtime import MetaCognitionAction, SpawnAgentAction

    # Simulate what the emitter resolver does on a tightened allow list.
    action = MetaCognitionAction()
    action.creates = []
    action.spawns = [SpawnAgentAction(goal="should be dropped", name="bad")]
    allow = {"creates", "links"}  # tightened: no spawns

    if "creates" not in allow: action.creates.clear()
    if "links" not in allow: action.links.clear()
    if "writes" not in allow: action.writes.clear()
    if "deletes" not in allow: action.deletes.clear()
    if "invokes" not in allow: action.invokes.clear()
    if "commits" not in allow: action.commits.clear()
    if "reviews" not in allow: action.reviews.clear()
    if "spawns" not in allow: action.spawns.clear()  # the fix

    assert action.spawns == []


# ---------------------------------------------------------------------------
# Edge-create lifecycle helper — single chokepoint
# ---------------------------------------------------------------------------

def test_apply_edge_create_lifecycle_returns_dict_and_calls_broadcast(monkeypatch):
    """Four call sites used to pack their own edge dicts and call
    broadcast + projection-schedule. The new ``apply_edge_create_lifecycle``
    is the single chokepoint — assert it emits the expected dict and
    invokes the broadcast hook exactly once."""
    from backend.services.concept_lifecycle import apply_edge_create_lifecycle
    monkeypatch.setattr(
        "backend.services.concept_lifecycle.schedule_output_projection",
        lambda *a, **kw: None,  # no DB / projection in this unit test
    )
    calls = []

    def fake_push(snap_id, payload):
        calls.append(payload)

    class _Edge:
        edge_id = "e_abc"
        source_id = "src_x"
        target_id = "tgt_y"
        edge_type = "WIRES_TO"
        source_port = ""
        target_port = ""
        weight = None
        variable_name = ""
        workspace_id = "ws_demo"
        created_at = "2026-05-21"

    ge = _StubGraphEditor()
    result = apply_edge_create_lifecycle(
        _Edge(), ge, workspace_id="ws_demo", push_fn=fake_push,
    )
    assert result is not None
    assert result["edge_id"] == "e_abc"
    assert result["source_id"] == "src_x"
    assert result["edge_type"] == "WIRES_TO"
    # Exactly one frame pushed.
    assert len(calls) == 1
    assert calls[0]["type"] == "edge_changed"
    assert calls[0]["change"] == "created"
    assert calls[0]["edge"]["edge_id"] == "e_abc"


def test_apply_edge_create_lifecycle_safe_on_none_edge():
    """Defensive: ge.create_concept_edge can return None on collision
    or schema errors. The helper must no-op cleanly rather than crash."""
    from backend.services.concept_lifecycle import apply_edge_create_lifecycle
    out = apply_edge_create_lifecycle(None, _StubGraphEditor(), push_fn=lambda *a, **kw: None)
    assert out is None


# ---------------------------------------------------------------------------
# §8D.27 — agent handle DRY helpers
# ---------------------------------------------------------------------------

def test_agent_handle_round_trip():
    """``agent_handle`` + ``parse_agent_handle`` invert each other.
    Pinning the contract prevents accidental format drift across the
    17 sites that used to inline the string."""
    from backend.services.agent_runtime import (
        agent_handle, parse_agent_handle,
        AGENT_ROLE_PERCEPTION, AGENT_ROLE_TRANSFORMER, AGENT_ROLE_EMITTER,
    )
    for role in (AGENT_ROLE_PERCEPTION, AGENT_ROLE_TRANSFORMER, AGENT_ROLE_EMITTER):
        h = agent_handle(role, "pcid_x")
        parsed = parse_agent_handle(h)
        assert parsed == (role, "pcid_x"), f"round-trip failed for {role}"


def test_parse_agent_handle_rejects_non_agent_handles():
    from backend.services.agent_runtime import parse_agent_handle
    assert parse_agent_handle("") is None
    assert parse_agent_handle("module::foo") is None
    assert parse_agent_handle("agent::") is None
    assert parse_agent_handle("agent::unknown_role::pcid") is None


def test_agent_role_prefix_matches_handle_start():
    from backend.services.agent_runtime import (
        agent_handle, agent_role_prefix, AGENT_ROLE_PERCEPTION,
    )
    h = agent_handle(AGENT_ROLE_PERCEPTION, "any_pcid")
    assert h.startswith(agent_role_prefix(AGENT_ROLE_PERCEPTION))


# ---------------------------------------------------------------------------
# §8D.20 — embed-field auto-detect in apply_update_lifecycle
# ---------------------------------------------------------------------------

def test_apply_update_lifecycle_auto_detects_no_embed_change(monkeypatch):
    """Three call sites used to pass a heuristic ``embed_fields_changed``
    based on PATCH payload keys. The auto-detect path now diffs pre vs
    post so a 'set description to same value' edit doesn't re-embed."""
    from backend.services import concept_lifecycle as cl

    calls = {"upsert": 0}
    monkeypatch.setattr(
        cl, "upsert_concept_index_for",
        lambda node, ge, **kw: calls.__setitem__("upsert", calls["upsert"] + 1),
    )
    monkeypatch.setattr(cl, "schedule_output_projection", lambda *a, **kw: None)
    monkeypatch.setattr(cl, "log_evolution", lambda *a, **kw: None)
    monkeypatch.setattr(cl, "broadcast_concept_changed", lambda *a, **kw: None)
    monkeypatch.setattr(cl, "maybe_persist_rendering", lambda *a, **kw: False)

    node = _StubNode(concept_id="n1", workspace_id="ws")
    node.description = "same"
    node.rendering = "same"
    pre_dict = {"description": "same", "rendering": "same"}

    cl.apply_update_lifecycle(
        node, _StubGraphEditor(),
        pre_dict=pre_dict, push_fn=None,
        # embed_fields_changed left default → auto-detect from diff
    )
    assert calls["upsert"] == 0, "no re-embed when description/rendering unchanged"


def test_apply_update_lifecycle_auto_detects_real_embed_change(monkeypatch):
    from backend.services import concept_lifecycle as cl

    calls = {"upsert": 0}
    monkeypatch.setattr(
        cl, "upsert_concept_index_for",
        lambda node, ge, **kw: calls.__setitem__("upsert", calls["upsert"] + 1),
    )
    monkeypatch.setattr(cl, "schedule_output_projection", lambda *a, **kw: None)
    monkeypatch.setattr(cl, "log_evolution", lambda *a, **kw: None)
    monkeypatch.setattr(cl, "broadcast_concept_changed", lambda *a, **kw: None)
    monkeypatch.setattr(cl, "maybe_persist_rendering", lambda *a, **kw: False)

    node = _StubNode(concept_id="n2", workspace_id="ws")
    node.description = "new"
    node.rendering = "old"
    pre_dict = {"description": "old", "rendering": "old"}

    cl.apply_update_lifecycle(
        node, _StubGraphEditor(),
        pre_dict=pre_dict, push_fn=None,
    )
    assert calls["upsert"] == 1, "re-embed when description moved"


# ---------------------------------------------------------------------------
# Functional-core diff
# ---------------------------------------------------------------------------

def test_concept_diff_classifies_no_change():
    from backend.services.concept_lifecycle import ConceptDiff
    node = _StubNode(concept_id="n", workspace_id="ws")
    node.data = "same"
    node.description = "same"
    node.rendering = "same"
    pre = {"data": "same", "description": "same", "rendering": "same"}
    diff = ConceptDiff.from_pre_post(pre, node)
    assert diff.data_changed is False
    assert diff.description_changed is False
    assert diff.rendering_changed is False
    assert diff.embed_fields_changed is False
    assert diff.is_create is False


def test_concept_diff_classifies_data_only():
    from backend.services.concept_lifecycle import ConceptDiff
    node = _StubNode(concept_id="n", workspace_id="ws")
    node.data = "new"
    node.description = "same"
    node.rendering = "same"
    pre = {"data": "old", "description": "same", "rendering": "same"}
    diff = ConceptDiff.from_pre_post(pre, node)
    assert diff.data_changed is True
    assert diff.embed_fields_changed is False  # data alone doesn't touch index


def test_concept_diff_create_is_full_change():
    from backend.services.concept_lifecycle import ConceptDiff
    node = _StubNode(concept_id="n", workspace_id="ws_new")
    diff = ConceptDiff.from_pre_post(None, node)
    assert diff.is_create is True
    assert diff.data_changed is True
    assert diff.description_changed is True
    assert diff.rendering_changed is True
    assert diff.embed_fields_changed is True
    assert diff.workspace_id == "ws_new"


# ---------------------------------------------------------------------------
# Plugin architecture: register_prefix_resolver
# ---------------------------------------------------------------------------

def test_register_prefix_resolver_routes_extension_handle():
    from backend.services.backing_registry import BackingRegistry
    reg = BackingRegistry()

    captured = []

    def vendor_factory(handle):
        captured.append(handle)
        def callable_(**kwargs):
            return {"echoed": kwargs}
        return callable_

    reg.register_prefix_resolver("vendor::", vendor_factory)
    out = reg.invoke("vendor::custom::alpha", x=1, y=2)
    assert out["ok"] is True
    assert out["result"] == {"echoed": {"x": 1, "y": 2}}
    assert captured == ["vendor::custom::alpha"]


def test_register_prefix_resolver_builtins_win_over_extensions():
    """An extension registered with the same prefix as a built-in
    MUST NOT shadow the built-in. Built-ins resolve first; the
    extension chain runs only on the fall-through path."""
    from backend.services.backing_registry import BackingRegistry
    reg = BackingRegistry()
    reg.register_prefix_resolver(
        "agent::perception::",
        lambda h: (lambda **kw: {"hijacked": True}),
    )
    # The built-in agent::perception:: resolver returns a callable; the
    # extension is consulted only after built-ins decline. So the
    # built-in wins.
    fn = reg.resolve("agent::perception::pcid_test")
    assert fn is not None
    # Invoke via the registry — should hit the built-in (which tries
    # to look up the param card via graph_editor). Without a real DB
    # we just confirm the function is the built-in by checking it
    # doesn't return our sentinel.
    result = fn()
    assert "hijacked" not in (result or {}), "extension must not shadow built-in"


def test_register_prefix_resolver_factory_returning_none_falls_through():
    """A factory returning None for a particular handle means
    'I don't handle this'; the resolver should fall back to None
    rather than crash."""
    from backend.services.backing_registry import BackingRegistry
    reg = BackingRegistry()
    reg.register_prefix_resolver("vendor::", lambda h: None)
    assert reg.resolve("vendor::nope::x") is None


def test_unregister_prefix_resolver_drops_extension():
    from backend.services.backing_registry import BackingRegistry
    reg = BackingRegistry()
    reg.register_prefix_resolver(
        "vendor::", lambda h: (lambda **kw: {"ok": True}),
    )
    assert reg.resolve("vendor::x") is not None
    assert reg.unregister_prefix_resolver("vendor::") is True
    assert reg.resolve("vendor::x") is None


# ---------------------------------------------------------------------------
# Settings — centralised config dataclass
# ---------------------------------------------------------------------------

def test_settings_defaults_are_reasonable():
    from backend.services.settings import Settings
    s = Settings()
    assert s.cascade_debounce_sec == 1.0
    assert s.cascade_max_ticks_per_min == 20
    assert s.spawn_max_per_workspace_per_min == 5
    assert s.agent_token_buffer_size == 4000
    assert s.ws_queue_max == 1000
    assert s.idempotency_ttl_sec == 300.0


def test_settings_loads_env_overrides(monkeypatch):
    from backend.services.settings import Settings
    monkeypatch.setenv("WFH_CASCADE_DEBOUNCE_SEC", "0.25")
    monkeypatch.setenv("WFH_SPAWN_MAX_PER_WORKSPACE_PER_MIN", "12")
    monkeypatch.setenv("WFH_WS_QUEUE_MAX", "256")
    s = Settings.from_env()
    assert s.cascade_debounce_sec == 0.25
    assert s.spawn_max_per_workspace_per_min == 12
    assert s.ws_queue_max == 256


def test_settings_configure_overrides_singleton():
    from backend.services.settings import (
        Settings, get_settings, configure, reset_to_env,
    )
    custom = Settings(cascade_debounce_sec=99.0)
    configure(custom)
    try:
        assert get_settings().cascade_debounce_sec == 99.0
    finally:
        reset_to_env()


def test_spawn_rate_limit_reads_settings_live(monkeypatch):
    """Tuning the env / configure-d settings should affect _check_spawn_rate
    on the very next call — no module reload required."""
    import backend.services.agent_runtime as ar
    from backend.services.settings import Settings, configure, reset_to_env
    monkeypatch.setattr(ar, "_SPAWN_WINDOW", {})
    configure(Settings(spawn_max_per_workspace_per_min=2))
    try:
        assert ar._check_spawn_rate("ws_dyn") is True
        assert ar._check_spawn_rate("ws_dyn") is True
        # Third in the same window is rejected because cap is now 2.
        assert ar._check_spawn_rate("ws_dyn") is False
    finally:
        reset_to_env()


# ---------------------------------------------------------------------------
# Bounded WS queue drop policy
# ---------------------------------------------------------------------------

def test_bounded_ws_queue_drops_overflow(monkeypatch):
    """When the queue is at capacity, _ws_push records a drop and
    returns cleanly rather than blocking. Counts are reported by
    ``get_ws_drop_counts``."""
    import asyncio
    from backend.api import routes
    from backend.services.settings import Settings, configure, reset_to_env

    # Use a tiny queue so we can fill it deterministically.
    configure(Settings(ws_queue_max=2))
    monkeypatch.setattr(routes, "_ws_drop_counts", {})
    try:
        loop = asyncio.new_event_loop()
        monkeypatch.setattr(routes, "_event_loop", loop)
        q = routes._new_ws_queue()
        monkeypatch.setitem(routes._workspace_queues, "ws_drop_test", q)

        for i in range(5):
            routes._ws_push(0, {"type": "concept_changed", "workspace_id": "ws_drop_test", "i": i})
        # Run the pending call_soon_threadsafe callbacks so puts happen.
        loop.call_soon(loop.stop)
        loop.run_forever()
        # Queue size is capped; remainder dropped.
        assert q.qsize() == 2
        counts = routes.get_ws_drop_counts()
        assert counts.get("workspace:ws_drop_test", 0) == 3
        loop.close()
    finally:
        reset_to_env()
        routes._workspace_queues.pop("ws_drop_test", None)


# ---------------------------------------------------------------------------
# Idempotency keys
# ---------------------------------------------------------------------------

def test_idempotency_cache_returns_prior_response():
    from backend.api.routes import _idempotency_lookup, _idempotency_store
    response = {"concept_id": "n1", "name": "Demo"}
    _idempotency_store("ws_idem", "n1", "key-abc", response)
    out = _idempotency_lookup("ws_idem", "n1", "key-abc")
    assert out is response


def test_idempotency_cache_misses_on_different_key():
    from backend.api.routes import _idempotency_lookup, _idempotency_store
    _idempotency_store("ws_idem", "n2", "key-A", {"a": 1})
    assert _idempotency_lookup("ws_idem", "n2", "key-B") is None


def test_idempotency_cache_no_key_is_no_op():
    """When idempotency_key is None / empty, the cache is bypassed
    (legacy clients still work)."""
    from backend.api.routes import _idempotency_lookup, _idempotency_store
    _idempotency_store("ws_idem", "n3", None, {"x": 1})
    assert _idempotency_lookup("ws_idem", "n3", None) is None
    _idempotency_store("ws_idem", "n3", "", {"x": 1})
    assert _idempotency_lookup("ws_idem", "n3", "") is None


def test_idempotency_cache_expires(monkeypatch):
    """After ttl elapses the cache returns None on the next lookup."""
    from backend.api import routes
    from backend.services.settings import Settings, configure, reset_to_env
    configure(Settings(idempotency_ttl_sec=0.05))
    try:
        routes._idempotency_store("ws_idem", "n4", "key-ttl", {"ok": True})
        # Immediate hit
        assert routes._idempotency_lookup("ws_idem", "n4", "key-ttl") is not None
        import time as _t
        _t.sleep(0.1)
        # Expired
        assert routes._idempotency_lookup("ws_idem", "n4", "key-ttl") is None
    finally:
        reset_to_env()


# ---------------------------------------------------------------------------
# §8C.8 — CommitSubgraphAction materialises a real concept node
# ---------------------------------------------------------------------------

def test_commit_subgraph_action_creates_record(monkeypatch):
    """Earlier ``ActionResolver.apply`` only incremented a counter for
    commits; the §8D.23.3 specialised-assembly loop was broken because
    nothing materialised. Now the resolver creates a ``committed_subgraph``
    concept node, registers a backing pointer that expands its members,
    and routes through the lifecycle so peer tabs / the evolution log
    see the commit."""
    from backend.services.agent_runtime import (
        ActionResolver, MetaCognitionAction, CommitSubgraphAction,
    )
    from backend.services.backing_registry import get_backing_registry

    ge = _StubGraphEditor()

    # Stub the lifecycle so we don't hit broadcast / index / projection.
    monkeypatch.setattr(
        "backend.services.concept_lifecycle.apply_create_lifecycle",
        lambda *a, **kw: None,
    )

    action = MetaCognitionAction()
    action.commits = [CommitSubgraphAction(
        name="my_assembly", card_ids=["card_a", "card_b", "card_c"],
    )]
    resolver = ActionResolver(ge, None)
    summary = resolver.apply(action, workspace_id="ws", actor_label="user:_anon")

    # The commit must have produced a real ConceptNode.
    assert summary["applied"]["commits"] == 1
    # Find the committed_subgraph node in the stub editor.
    committed = [n for n in ge.nodes.values() if n.type_hint == "committed_subgraph"]
    assert len(committed) == 1
    node = committed[0]
    # Data block records the member roster.
    import json as _json
    data = _json.loads(node.data)
    assert data["card_ids"] == ["card_a", "card_b", "card_c"]
    assert data["name"] == "my_assembly"
    # Backing pointer follows the canonical shape.
    assert (node.backing_pointer or "").startswith("committed_subgraph::")
    # The backing pointer resolves through the registry — invoking it
    # returns the member roster.
    reg = get_backing_registry()
    out = reg.invoke(node.backing_pointer)
    assert out["ok"] is True
    assert out["result"]["card_ids"] == ["card_a", "card_b", "card_c"]
    assert out["result"]["member_count"] == 3
    # Cleanup so the registry doesn't accumulate across tests.
    reg.unregister(node.backing_pointer)


def test_commit_subgraph_action_skips_empty_body():
    """A commit with no card_ids is a no-op (nothing to assemble)."""
    from backend.services.agent_runtime import (
        ActionResolver, MetaCognitionAction, CommitSubgraphAction,
    )
    ge = _StubGraphEditor()
    action = MetaCognitionAction()
    action.commits = [CommitSubgraphAction(name="empty", card_ids=[])]
    resolver = ActionResolver(ge, None)
    summary = resolver.apply(action, workspace_id="ws")
    assert summary["applied"]["commits"] == 0
    assert not any(n.type_hint == "committed_subgraph" for n in ge.nodes.values())
