"""Pytest coverage for GET /concepts/{id}/next_rank (Phase 7 EXPLORE-01 / D-03).

Seeds a materialised python_object tree (mirroring scripts/probe_python_api.py's
``_SyntheticBrowser`` fixture) into a throwaway Kuzu DB via
``backend/services/db_janitor.py::temp_db_dir`` (CLAUDE.md §R.9 hygiene — never
a bare ``tempfile.mkdtemp``), then calls the route handler directly against a
``GraphEditor`` bound to that DB, and asserts:

  1. every returned neighbor's edge_type is one of the four materialiser types
  2. a known property AND a known function neighbor both appear
  3. a self-referential edge is excluded from the result
  4. a non-existent concept_id returns 404

No real subsystems are needed for this pure graph-read test (run under
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


_WS = "test_next_rank_ws"


@pytest.fixture
def next_rank_graph(monkeypatch):
    """Seed a materialised python_object tree in a throwaway Kuzu DB and
    monkeypatch routes._get_graph_editor() to resolve against it, so the
    route handler under test reads the SAME graph the materialiser wrote —
    without disturbing the process-wide GraphEditor singleton other tests
    may rely on.
    """
    backing_version.reset()
    with temp_db_dir("test_next_rank_route") as temp_dir:
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

        try:
            yield ge, rec["concept_id"]
        finally:
            database.conn = None
            database.db = None
            database.DB_PATH, database.db, database.conn = (
                prior_db_path, prior_db, prior_conn,
            )


def test_next_rank_returns_only_materialiser_edge_types(next_rank_graph):
    ge, object_id = next_rank_graph
    result = routes.get_concept_next_rank(object_id, workspace_id=_WS)

    assert result["ok"] is True
    assert result["concept_id"] == object_id
    neighbors = result["neighbors"]
    assert len(neighbors) > 0, "expected at least one rank-1 neighbor"

    allowed_edge_types = {
        "OBJECT_HAS_PROPERTY",
        "OBJECT_HAS_FUNCTION",
        "FUNCTION_INPUT_TYPE",
        "FUNCTION_OUTPUT_TYPE",
    }
    for n in neighbors:
        assert n["edge_type"] in allowed_edge_types, (
            f"next_rank returned a neighbor outside the materialiser "
            f"vocabulary: {n}"
        )


def test_next_rank_includes_known_property_and_function(next_rank_graph):
    ge, object_id = next_rank_graph
    result = routes.get_concept_next_rank(object_id, workspace_id=_WS)
    neighbors = result["neighbors"]

    property_neighbors = [n for n in neighbors if n["edge_type"] == "OBJECT_HAS_PROPERTY"]
    function_neighbors = [n for n in neighbors if n["edge_type"] == "OBJECT_HAS_FUNCTION"]

    assert any(n["name"] == "current_url" for n in property_neighbors), (
        f"expected current_url property neighbor, got {property_neighbors}"
    )
    assert any(n["name"] == "navigate" for n in function_neighbors), (
        f"expected navigate function neighbor, got {function_neighbors}"
    )
    # Relation render-hints map correctly (D10 — pure render label, no new
    # computation beyond the edge_type the materialiser already wrote).
    for n in property_neighbors:
        assert n["relation"] == "property"
    for n in function_neighbors:
        assert n["relation"] == "function"


def test_next_rank_excludes_self_referential_edge(next_rank_graph):
    ge, object_id = next_rank_graph

    # Seed a self-referential edge directly using one of the four
    # materialiser edge types — next_rank must skip it (rank-1 only,
    # T-07-01 DoS mitigation), never fold a node back onto itself.
    ge.create_concept_edge(
        source_id=object_id,
        target_id=object_id,
        edge_type="OBJECT_HAS_PROPERTY",
        workspace_id=_WS,
    )

    result = routes.get_concept_next_rank(object_id, workspace_id=_WS)
    neighbors = result["neighbors"]
    assert all(n["concept_id"] != object_id for n in neighbors), (
        "next_rank must exclude self-referential edges"
    )


def test_next_rank_404s_on_unknown_concept_id(next_rank_graph):
    ge, object_id = next_rank_graph
    with pytest.raises(HTTPException) as exc_info:
        routes.get_concept_next_rank("does-not-exist-12345", workspace_id=_WS)
    assert exc_info.value.status_code == 404
