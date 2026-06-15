"""§R.2 — full database ontology mapped to the 3D UMAP GUI.

Verbatim anchor (USER_REQUIREMENTS_VERBATIM.md §R.2): "the full database
ontology mapped to our 3D umap GUI, which integrates our full set of DB
functional-objects and scanned webpage chunk structures."

Drives the REAL LayoutService.recompute_ontology over the REAL GraphEditor
and the REAL ConceptIndexService (slots carry explicit precomputed nomic
vectors — the service's own documented path; no subsystem fakes). Cleans
its own side files (§R.9: the test never leaves an ontology_frame orphan).
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.concept_index_service import ConceptIndexService
from backend.services.graph_editor import GraphEditor
from backend.services.layout_service import LayoutService

WS = "ws_ontol_test"


def _build_world():
    """12 concepts: 5 in semantic cluster A, 5 in cluster B (explicit nomic
    vectors), 2 vectorless (a fixture + a python_function — the §6.1 hash
    placeholder lane). One typed edge. Returns (ge, ci, layout, frames)."""
    rng = np.random.default_rng(42)
    ge = GraphEditor()
    ci = ConceptIndexService(graph_editor=ge)
    frames = []
    layout = LayoutService(broadcast=lambda sid, frame: frames.append(frame))

    base_a = rng.normal(size=768)
    base_b = rng.normal(size=768)
    ids_a, ids_b = [], []
    for i in range(5):
        cid = f"cluster_a_{i}"
        ids_a.append(cid)
        ge.create_concept(concept_id=cid, name=f"alpha {i}",
                          description="library catalogues", data="",
                          workspace_id=WS, type_hint="")
        v = base_a + rng.normal(scale=0.05, size=768)
        ci.upsert_slot(cid, workspace_id=WS,
                       embedding_nomic=[float(x) for x in v],
                       embedding_tfidf=[0.0])
    for i in range(5):
        cid = f"cluster_b_{i}"
        ids_b.append(cid)
        ge.create_concept(concept_id=cid, name=f"beta {i}",
                          description="selenium webdrivers", data="",
                          workspace_id=WS, type_hint="")
        v = base_b + rng.normal(scale=0.05, size=768)
        ci.upsert_slot(cid, workspace_id=WS,
                       embedding_nomic=[float(x) for x in v],
                       embedding_tfidf=[0.0])
    # The functional-object lane: a fixture + a python-native function with
    # no nomic vector yet (placeholder until next index pass).
    ge.create_concept(concept_id=f"fixture::database::{WS}", name="Database",
                      description="unified storage handle", data="",
                      workspace_id=WS, type_hint="")
    ge.create_concept(concept_id="pyfn_web_query", name="web_query",
                      description="WebBrowser.web_query", data="",
                      workspace_id=WS, type_hint="python_function")
    ge.create_concept_edge(source_id="cluster_a_0", target_id="cluster_b_0",
                           edge_type="RELATES_TO", workspace_id=WS)
    return ge, ci, layout, frames, ids_a, ids_b


def test_full_ontology_gets_coords_and_frame():
    ge, ci, layout, frames, ids_a, ids_b = _build_world()
    try:
        out = layout.recompute_ontology(WS, concept_index=ci, graph_editor=ge)
        coords = out["coords"]
        # EVERY workspace concept projects — functional objects included.
        assert len(coords) == 12
        assert f"fixture::database::{WS}" in coords
        assert "pyfn_web_query" in coords
        assert all(len(v) == 6 for v in coords.values())
        assert out["fitted"] is True
        # names + type_hints ride along for the projector's labelling.
        assert out["names"]["pyfn_web_query"] == "web_query"
        assert out["type_hints"]["pyfn_web_query"] == "python_function"
        # Coordinate-free one-edge-table adjacency present.
        assert {"src_id": "cluster_a_0", "dst_id": "cluster_b_0",
                "kind": "RELATES_TO"} in out["edges"]
        # Dual-routed: the ontology_layout frame was broadcast.
        onto_frames = [f for f in frames if f.get("type") == "ontology_layout"]
        assert onto_frames, "no ontology_layout frame broadcast"
        assert onto_frames[-1]["count"] == 12
    finally:
        layout.purge_workspace(WS)


def test_neighbour_preservation_between_clusters():
    """Real UMAP/SVD over the nomic vectors: intra-cluster distances stay
    below inter-cluster distances (the §6.1 neighbour-preserving contract,
    applied to the concept ontology)."""
    ge, ci, layout, frames, ids_a, ids_b = _build_world()
    try:
        out = layout.recompute_ontology(WS, concept_index=ci, graph_editor=ge)
        coords = out["coords"]
        P = {cid: np.asarray(coords[cid][:3]) for cid in ids_a + ids_b}

        def _avg(pairs):
            ds = [float(np.linalg.norm(P[a] - P[b])) for a, b in pairs]
            return sum(ds) / len(ds)

        intra = _avg([(a, b) for i, a in enumerate(ids_a) for b in ids_a[i + 1:]])
        inter = _avg([(a, b) for a in ids_a for b in ids_b])
        assert intra < inter, f"intra {intra:.2f} !< inter {inter:.2f}"
    finally:
        layout.purge_workspace(WS)


def test_purge_drops_ontology_state():
    ge, ci, layout, frames, *_ = _build_world()
    layout.recompute_ontology(WS, concept_index=ci, graph_editor=ge)
    assert layout.get_ontology_coords(WS)
    opath = layout._ontology_path(WS)
    assert os.path.exists(opath)
    layout.purge_workspace(WS)
    assert layout.get_ontology_coords(WS) == {}
    assert not os.path.exists(opath)


def test_vectorless_concepts_get_hash_placeholder():
    """No index slots at all → every concept still lands on the ontology
    shell via the deterministic hash placeholder; fitted=False."""
    ge = GraphEditor()
    ge.create_concept(concept_id="lone_a", name="lone a", description="",
                      data="", workspace_id=WS)
    ge.create_concept(concept_id="lone_b", name="lone b", description="",
                      data="", workspace_id=WS)
    ci = ConceptIndexService(graph_editor=ge)
    layout = LayoutService(broadcast=None)
    try:
        out = layout.recompute_ontology(WS, concept_index=ci, graph_editor=ge)
        assert out["fitted"] is False
        assert set(out["coords"]) == {"lone_a", "lone_b"}
        # Deterministic: same id → same placeholder.
        again = layout.recompute_ontology(WS, concept_index=ci, graph_editor=ge)
        assert again["coords"]["lone_a"] == out["coords"]["lone_a"]
    finally:
        layout.purge_workspace(WS)
