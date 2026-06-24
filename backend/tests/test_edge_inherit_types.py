"""Pytest coverage for the Phase 7 EXPLORE-03 / N.4 edge-create
I/O-type-inheritance extension (``inherit_types`` on ``EditorLinkRequest`` /
``ConceptEdgeRequest``).

Seeds a materialised python_object tree (mirroring
scripts/probe_python_api.py's ``_SyntheticBrowser`` fixture, same pattern as
backend/tests/test_next_rank_route.py) into a throwaway Kuzu DB via
``backend/services/db_janitor.py::temp_db_dir`` (CLAUDE.md §R.9 hygiene),
creates a plain target node, then exercises the route handlers directly:

  1. editor_link / create_concept_edge WITHOUT inherit_types behaves exactly
     as before — plain edge, target gains NO typed neighbors (backward
     compatible).
  2. editor_link / create_concept_edge WITH inherit_types=True — after the
     edge is created, the target gains equivalent typed edges mirroring the
     source's rank-1 OBJECT_HAS_PROPERTY/OBJECT_HAS_FUNCTION/
     FUNCTION_INPUT_TYPE/FUNCTION_OUTPUT_TYPE neighbors.
  3. an invalid source/target pair still 400s (HTTPException), with
     inherit_types True or False — validation is never bypassed for the
     fast path (RESEARCH Security Domain / T-07-06).
  4. the inheritance runs through apply_edge_create_lifecycle (same
     dispatcher as the primary edge) so the fan-out fires once per edge,
     never a parallel write path.

No real subsystems are needed for this pure graph-mutation test (run under
WFH_FAKE_SLM=1 / WFH_FAKE_EMBEDDER=1 / NO_WEBDRIVER=1 per the plan's verify
step, though this test itself never touches SLM/embedder/Selenium).
"""

from __future__ import annotations

import os

import kuzu
import pytest
from fastapi import HTTPException

from backend.services import backing_version
from backend import database
from backend.services.db_janitor import temp_db_dir
from backend.services.graph_editor import GraphEditor
from backend.services.python_api_materialiser import PythonAPIMaterialiser
import backend.api.routes as routes


class _SyntheticBrowser:
    """Toy class mirroring scripts/probe_python_api.py's fixture shape."""

    current_url: str = ""
    """The browser's current URL."""

    @property
    def title(self) -> str:
        """The page title."""
        return ""

    def snapshot(self) -> dict:
        """Capture the current DOM and return a snapshot."""
        return {}

    def navigate(self, url: str, timeout: int = 30) -> bool:
        """Navigate to a URL. Returns True on success."""
        return False


_WS = "test_edge_inherit_types_ws"
_INHERIT_EDGE_TYPES = {
    "OBJECT_HAS_PROPERTY",
    "OBJECT_HAS_FUNCTION",
    "FUNCTION_INPUT_TYPE",
    "FUNCTION_OUTPUT_TYPE",
}


@pytest.fixture
def inherit_graph(monkeypatch):
    """Seed a materialised python_object tree (the source) + a plain
    user-authored target ConceptNode in a throwaway Kuzu DB, and monkeypatch
    routes._get_graph_editor() to resolve against it — same isolation
    pattern as test_next_rank_route.py's next_rank_graph fixture.
    """
    backing_version.reset()
    with temp_db_dir("test_edge_inherit_types") as temp_dir:
        db_path = os.path.abspath(os.path.join(temp_dir, "db"))
        db = kuzu.Database(db_path)
        conn = kuzu.Connection(db)

        prior_db_path, prior_db, prior_conn = (
            database.DB_PATH, database.db, database.conn,
        )
        database.DB_PATH = db_path
        database.db = db
        database.conn = conn
        database.init_db()

        ge = GraphEditor(db_conn=conn)
        monkeypatch.setattr(routes, "_get_graph_editor", lambda: ge)

        mat = PythonAPIMaterialiser(graph_editor=ge)
        rec = mat.materialise_class(_SyntheticBrowser, workspace_id=_WS)
        source_id = rec["concept_id"]

        target = ge.create_concept(
            name="plain_target",
            description="a plain user-authored node with no types yet",
            data="",
            provenance="user-authored",
            workspace_id=_WS,
        )

        try:
            yield ge, source_id, target.concept_id
        finally:
            database.conn = None
            database.db = None
            database.DB_PATH, database.db, database.conn = (
                prior_db_path, prior_db, prior_conn,
            )


def _target_typed_neighbor_edges(ge, target_id):
    return [
        e for e in ge.list_concept_edges(workspace_id=_WS, source_id=target_id)
        if e.edge_type in _INHERIT_EDGE_TYPES
    ]


# ---------------------------------------------------------------------------
# Test 1 — inherit_types defaults False / omitted: behaves exactly as today.
# ---------------------------------------------------------------------------

def test_editor_link_without_inherit_types_is_plain_edge(inherit_graph):
    ge, source_id, target_id = inherit_graph

    result = routes.editor_link(routes.EditorLinkRequest(
        source_id=source_id, target_id=target_id, edge_type="RELATES_TO",
        workspace_id=_WS,
    ))

    assert result["ok"] is True
    assert "inherited_edges" not in result
    assert _target_typed_neighbor_edges(ge, target_id) == []


def test_create_concept_edge_without_inherit_types_is_plain_edge(inherit_graph):
    ge, source_id, target_id = inherit_graph

    result = routes.create_concept_edge(routes.ConceptEdgeRequest(
        source_id=source_id, target_id=target_id, edge_type="RELATES_TO",
        workspace_id=_WS,
    ))

    assert "inherited_edges" not in result
    assert _target_typed_neighbor_edges(ge, target_id) == []


# ---------------------------------------------------------------------------
# Test 2 — inherit_types=True: target gains the source's typed fields.
# ---------------------------------------------------------------------------

def test_editor_link_with_inherit_types_copies_io_types(inherit_graph):
    ge, source_id, target_id = inherit_graph

    source_typed_edges = [
        e for e in ge.list_concept_edges(workspace_id=_WS, source_id=source_id)
        if e.edge_type in _INHERIT_EDGE_TYPES
    ]
    assert len(source_typed_edges) > 0, "fixture must materialise typed source edges"

    result = routes.editor_link(routes.EditorLinkRequest(
        source_id=source_id, target_id=target_id, edge_type="RELATES_TO",
        workspace_id=_WS, inherit_types=True,
    ))

    assert result["ok"] is True
    assert "inherited_edges" in result
    assert len(result["inherited_edges"]) == len(source_typed_edges)

    target_typed_edges = _target_typed_neighbor_edges(ge, target_id)
    assert len(target_typed_edges) == len(source_typed_edges)

    source_targets = {(e.edge_type, e.target_id) for e in source_typed_edges}
    target_targets = {(e.edge_type, e.target_id) for e in target_typed_edges}
    assert source_targets == target_targets, (
        "target must inherit the SAME typed neighbors (edge_type, target_id) "
        "as the source — an inheritance mirror, not a divergent copy"
    )


def test_create_concept_edge_with_inherit_types_copies_io_types(inherit_graph):
    ge, source_id, target_id = inherit_graph

    result = routes.create_concept_edge(routes.ConceptEdgeRequest(
        source_id=source_id, target_id=target_id, edge_type="RELATES_TO",
        workspace_id=_WS, inherit_types=True,
    ))

    assert "inherited_edges" in result
    target_typed_edges = _target_typed_neighbor_edges(ge, target_id)
    assert len(target_typed_edges) > 0
    assert any(n["name"] == "current_url" for n in [
        {"name": (ge.get_concept(e.target_id).name if ge.get_concept(e.target_id) else "")}
        for e in target_typed_edges
    ]), "expected the inherited property neighbor 'current_url' to appear"


# ---------------------------------------------------------------------------
# Test 3 — invalid source/target pair still 400s (validation never bypassed).
# ---------------------------------------------------------------------------

def test_editor_link_invalid_pair_400s_regardless_of_inherit_types(inherit_graph):
    ge, source_id, target_id = inherit_graph

    with pytest.raises(HTTPException) as exc_info:
        routes.editor_link(routes.EditorLinkRequest(
            source_id="does-not-exist-12345", target_id=target_id,
            workspace_id=_WS, inherit_types=False,
        ))
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException) as exc_info:
        routes.editor_link(routes.EditorLinkRequest(
            source_id=source_id, target_id="also-does-not-exist-67890",
            workspace_id=_WS, inherit_types=True,
        ))
    assert exc_info.value.status_code == 400


def test_create_concept_edge_invalid_pair_400s_regardless_of_inherit_types(inherit_graph):
    ge, source_id, target_id = inherit_graph

    with pytest.raises(HTTPException) as exc_info:
        routes.create_concept_edge(routes.ConceptEdgeRequest(
            source_id="nope-1", target_id=target_id,
            workspace_id=_WS, inherit_types=True,
        ))
    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Test 4 — inheritance fans out through apply_edge_create_lifecycle (one
# request, one lifecycle event per edge — never a parallel write path).
# ---------------------------------------------------------------------------

def test_inheritance_runs_through_apply_edge_create_lifecycle(inherit_graph, monkeypatch):
    ge, source_id, target_id = inherit_graph

    calls = []
    import backend.services.concept_lifecycle as concept_lifecycle
    real_apply = concept_lifecycle.apply_edge_create_lifecycle

    def _spy(edge, ge_arg, **kwargs):
        calls.append(edge)
        return real_apply(edge, ge_arg, **kwargs)

    monkeypatch.setattr(concept_lifecycle, "apply_edge_create_lifecycle", _spy)

    result = routes.editor_link(routes.EditorLinkRequest(
        source_id=source_id, target_id=target_id, edge_type="RELATES_TO",
        workspace_id=_WS, inherit_types=True,
    ))

    # One call for the primary edge + one call per inherited edge.
    assert len(calls) == 1 + len(result["inherited_edges"])
