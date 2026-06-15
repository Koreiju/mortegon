"""Unit tests for backend.services.conceptual_compute.

The ConceptComputeNode primitive turns a concept node into a LangGraph
callable, with Pydantic validation on structured outputs. These tests
cover the dispatch logic without booting the full backend — the
graph_editor is a tiny in-memory stub.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pytest

from backend.services.conceptual_compute import (
    ComputeNodeSpec,
    ConceptComputeNode,
    build_pydantic_model_from_schema,
    compile_subgraph_to_langgraph,
)


# ---------------------------------------------------------------------------
# In-memory graph_editor stub
# ---------------------------------------------------------------------------

@dataclass
class _Node:
    concept_id: str
    name: str = ""
    description: str = ""
    data: str = ""
    rendering: str = ""


@dataclass
class _Edge:
    source_id: str
    target_id: str


class _GE:
    """Minimal stub matching the GraphEditor surface ConceptComputeNode uses."""

    def __init__(self):
        self.nodes: Dict[str, _Node] = {}
        self.edges: List[_Edge] = []

    def get_concept(self, cid: str) -> Optional[_Node]:
        return self.nodes.get(cid)

    def update_concept(self, cid: str, **fields) -> Optional[_Node]:
        n = self.nodes.get(cid)
        if n is None:
            return None
        for k, v in fields.items():
            setattr(n, k, v)
        return n

    def list_concept_edges(self, *, workspace_id="", source_id="",
                           target_id="", limit=200) -> List[_Edge]:
        out = []
        for e in self.edges:
            if source_id and e.source_id != source_id:
                continue
            if target_id and e.target_id != target_id:
                continue
            out.append(e)
        return out[:limit]

    def add(self, n: _Node) -> _Node:
        self.nodes[n.concept_id] = n
        return n

    def link(self, src: str, tgt: str) -> None:
        self.edges.append(_Edge(src, tgt))


# ---------------------------------------------------------------------------
# Pydantic model factory
# ---------------------------------------------------------------------------

def test_build_pydantic_model_accepts_valid_payload():
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "price": {"type": "number"},
        },
        "required": ["title"],
    }
    M = build_pydantic_model_from_schema(schema, model_name="P")
    assert M is not None
    inst = M(title="Hello", price=1.5)
    dump = inst.model_dump() if hasattr(inst, "model_dump") else inst.dict()
    assert dump == {"title": "Hello", "price": 1.5}


def test_build_pydantic_model_rejects_missing_required():
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
        },
        "required": ["title"],
    }
    M = build_pydantic_model_from_schema(schema)
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        M()


def test_build_pydantic_model_returns_none_on_empty_schema():
    assert build_pydantic_model_from_schema({}) is None
    assert build_pydantic_model_from_schema({"properties": {}}) is None


# ---------------------------------------------------------------------------
# ComputeNodeSpec.from_concept — auto-classification
# ---------------------------------------------------------------------------

def test_spec_classifies_plain_when_data_not_json():
    n = _Node(concept_id="x", data="hello {world}")
    spec = ComputeNodeSpec.from_concept(n)
    assert spec.kind == "plain"


def test_spec_classifies_plain_when_dict_has_no_kind_keys():
    n = _Node(concept_id="x", data=json.dumps({"hello": "world"}))
    spec = ComputeNodeSpec.from_concept(n)
    assert spec.kind == "plain"


def test_spec_classifies_python_from_python_entry():
    n = _Node(concept_id="x",
              data=json.dumps({"python_entry": "json:dumps", "inputs": {"obj": 1}}))
    spec = ComputeNodeSpec.from_concept(n)
    assert spec.kind == "python"
    assert spec.python_entry == "json:dumps"
    assert spec.inputs == {"obj": 1}


def test_spec_classifies_structured_when_schema_and_prompt_present():
    n = _Node(concept_id="x", data=json.dumps({
        "prompt": "do thing",
        "output_schema": {"type": "object", "properties": {"a": {"type": "string"}}},
    }))
    spec = ComputeNodeSpec.from_concept(n)
    assert spec.kind == "structured"
    assert spec.prompt == "do thing"
    assert spec.output_schema is not None


def test_spec_classifies_prompt_when_only_prompt_present():
    n = _Node(concept_id="x", data=json.dumps({"prompt": "do thing"}))
    spec = ComputeNodeSpec.from_concept(n)
    assert spec.kind == "prompt"


def test_spec_explicit_kind_override():
    n = _Node(concept_id="x",
              data=json.dumps({"compute_kind": "plain", "prompt": "ignored"}))
    spec = ComputeNodeSpec.from_concept(n)
    assert spec.kind == "plain"


# ---------------------------------------------------------------------------
# ConceptComputeNode dispatch
# ---------------------------------------------------------------------------

def test_compile_plain_tree_prints_dict_data():
    ge = _GE()
    ge.add(_Node(concept_id="cc", data=json.dumps({"k": "v", "n": 1})))
    node = ConceptComputeNode("cc", graph_editor=ge, persist_rendering=False)
    out = node.compile()
    assert out["kind"] == "plain"
    # tree-print is whitespace-structured, syntax-free.
    assert "k" in out["rendering"] and "v" in out["rendering"]
    assert "n" in out["rendering"] and "1" in out["rendering"]


def test_compile_python_dispatch_invokes_callable():
    ge = _GE()
    ge.add(_Node(concept_id="cc",
                 data=json.dumps({"python_entry": "json:dumps",
                                  "inputs": {"obj": {"k": "v"}}})))
    node = ConceptComputeNode("cc", graph_editor=ge, persist_rendering=False)
    out = node.compile()
    assert out["kind"] == "python"
    assert '"k"' in out["rendering"]


def test_compile_python_dispatch_handles_bad_entry():
    ge = _GE()
    ge.add(_Node(concept_id="cc",
                 data=json.dumps({"python_entry": "nonexistent:fn"})))
    node = ConceptComputeNode("cc", graph_editor=ge, persist_rendering=False)
    out = node.compile()
    assert out["kind"] == "python"
    assert "python error" in out["rendering"] or "missing" in out["rendering"]


def test_compile_prompt_uses_slm_stub_when_no_client():
    ge = _GE()
    ge.add(_Node(concept_id="cc",
                 data=json.dumps({"prompt": "What is recursion?"})))
    node = ConceptComputeNode("cc", graph_editor=ge,
                              slm_client=None, persist_rendering=False)
    out = node.compile()
    assert out["kind"] == "prompt"
    assert "What is recursion?" in out["rendering"]
    assert "[stub-slm]" in out["rendering"]


def test_compile_structured_returns_validation_error_envelope_on_stub():
    """The stub SLM returns {_stub: True, ...} which doesn't satisfy
    the user's required fields. The compile should surface the
    validation error in the raw_output rather than crashing."""
    ge = _GE()
    ge.add(_Node(concept_id="cc", data=json.dumps({
        "compute_kind": "structured",
        "prompt": "give me a product",
        "output_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "price": {"type": "number"}},
            "required": ["title", "price"],
        },
    })))
    node = ConceptComputeNode("cc", graph_editor=ge,
                              slm_client=None, persist_rendering=False)
    out = node.compile()
    assert out["kind"] == "structured"
    raw = out["raw_output"]
    assert isinstance(raw, dict)
    # Stub doesn't satisfy required fields → validation envelope.
    assert "_validation_error" in raw


def test_compile_missing_concept_returns_diagnostic():
    ge = _GE()
    node = ConceptComputeNode("doesnotexist", graph_editor=ge)
    out = node.compile()
    assert out["kind"] == "missing"
    assert "error" in out


# ---------------------------------------------------------------------------
# Ref substitution + chain compilation
# ---------------------------------------------------------------------------

def test_compile_chain_walks_back_references_in_dep_order():
    ge = _GE()
    ge.add(_Node(concept_id="a", data="alpha"))
    ge.add(_Node(concept_id="b", data="bravo"))
    ge.add(_Node(concept_id="c", data="charlie"))
    ge.link("a", "b")
    ge.link("b", "c")
    app, ordered = compile_subgraph_to_langgraph(
        "c", graph_editor=ge,
    )
    # Walk should reach all three; focal last.
    assert set(ordered) == {"a", "b", "c"}
    assert ordered[-1] == "c"


def test_compile_chain_invoke_populates_state_for_each_node():
    ge = _GE()
    ge.add(_Node(concept_id="a", data="alpha"))
    ge.add(_Node(concept_id="b", data="bravo"))
    ge.link("a", "b")
    app, ordered = compile_subgraph_to_langgraph("b", graph_editor=ge)
    state = app.invoke({})
    assert "a" in state and "b" in state
    assert state["a"]["rendering"] == "alpha"
    assert state["b"]["rendering"] == "bravo"
