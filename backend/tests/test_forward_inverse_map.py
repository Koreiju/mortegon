"""§R.6 — forward-call inverse-lookup functional maps.

Verbatim anchor (USER_REQUIREMENTS_VERBATIM.md §R.6): "forward-call
inverse-lookup functional maps that reflect their full state space of
mappings in the database."

Runs against the REAL GraphEditor concept-edge store and the REAL
ConceptComputeNode compile (plain/template kind — no SLM dependency), so the
recorded state space is exercised end-to-end without any subsystem fakes.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.forward_inverse_map import (
    FORWARD_EDGE_TYPE,
    inverse_map,
    record_forward_call,
    recorded_inverse_ids,
    referenced_input_ids,
)
from backend.services.graph_editor import GraphEditor


def _editor_with_nodes():
    ge = GraphEditor()
    a = ge.create_concept(concept_id="inp_alpha", name="alpha",
                          description="input alpha", data="alpha-data",
                          workspace_id="ws_fim")
    b = ge.create_concept(concept_id="inp_beta", name="beta",
                          description="input beta", data="beta-data",
                          workspace_id="ws_fim")
    out = ge.create_concept(concept_id="out_node", name="out node",
                            description="consumes {alpha} and {beta}",
                            data="combined: {alpha} {beta}",
                            workspace_id="ws_fim")
    return ge, a, b, out


def test_referenced_input_ids_resolves_slugs():
    ge, a, b, out = _editor_with_nodes()
    ids = referenced_input_ids(out, ge, workspace_id="ws_fim")
    assert set(ids) == {"inp_alpha", "inp_beta"}


def test_record_and_inverse_map_roundtrip():
    ge, a, b, out = _editor_with_nodes()
    n = record_forward_call(
        ge, output_id="out_node", input_ids=["inp_alpha", "inp_beta"],
        fn_signature="template", workspace_id="ws_fim",
    )
    assert n == 2
    m = inverse_map(ge, "out_node", workspace_id="ws_fim")
    assert {r["source_id"] for r in m["as_output"]} == {"inp_alpha", "inp_beta"}
    assert all(r["fn_signature"] == "template" for r in m["as_output"])
    # The input side of the state space: alpha flowed INTO out_node.
    m_a = inverse_map(ge, "inp_alpha", workspace_id="ws_fim")
    assert [r["target_id"] for r in m_a["as_input"]] == ["out_node"]
    assert m_a["as_output"] == []


def test_record_is_idempotent_on_natural_key():
    ge, a, b, out = _editor_with_nodes()
    for _ in range(3):  # cascade re-fires must not grow the state space
        record_forward_call(
            ge, output_id="out_node", input_ids=["inp_alpha"],
            fn_signature="template", workspace_id="ws_fim",
        )
    edges = ge.list_concept_edges(
        workspace_id="ws_fim", target_id="out_node",
        edge_type=FORWARD_EDGE_TYPE,
    )
    assert len(edges) == 1


def test_recorded_inverse_ids_orders_and_dedupes():
    ge, a, b, out = _editor_with_nodes()
    record_forward_call(ge, output_id="out_node",
                        input_ids=["inp_alpha", "inp_beta"],
                        fn_signature="template", workspace_id="ws_fim")
    ids = recorded_inverse_ids(ge, "out_node", workspace_id="ws_fim")
    assert set(ids) == {"inp_alpha", "inp_beta"}
    assert len(ids) == len(set(ids))


def test_compile_records_forward_mapping():
    """The REAL ConceptComputeNode plain-template compile records its
    consumed {ref} inputs into the FORWARD_MAPPED_TO state space."""
    from backend.services.conceptual_compute import ConceptComputeNode

    ge, a, b, out = _editor_with_nodes()
    node = ConceptComputeNode("out_node", graph_editor=ge,
                              persist_rendering=False)
    result = node.compile()
    assert result["kind"] == "plain"
    assert "alpha-data" in result["rendering"]  # refs actually resolved
    m = inverse_map(ge, "out_node", workspace_id="ws_fim")
    assert {r["source_id"] for r in m["as_output"]} == {"inp_alpha", "inp_beta"}
    assert all(r["fn_signature"] == "template" for r in m["as_output"])


def test_closest_inverse_ranks_recorded_first():
    """§7.7 tier order: recorded mappings outrank nomic generalisation."""
    from backend.services.apparition_service import ApparitionService

    ge, a, b, out = _editor_with_nodes()
    record_forward_call(ge, output_id="out_node", input_ids=["inp_beta"],
                        fn_signature="template", workspace_id="ws_fim")
    svc = ApparitionService(concept_index=None, graph_editor=ge)
    cands = svc.closest_inverse("out_node", workspace_id="ws_fim", k=5)
    assert cands, "closest_inverse returned nothing"
    assert cands[0].card_id == "inp_beta"
    assert cands[0].provenance == "recorded-mapping"
    assert cands[0].score == 1.0
