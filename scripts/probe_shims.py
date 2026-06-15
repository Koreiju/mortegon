"""Quick verification of the §8D.44.2 to_concept_node() shims.

Standalone harness — no backend / no Kuzu needed; runs the in-memory
dataclasses' projection into the unified ConceptNode and asserts the
schema invariants the doc declares.
"""
from __future__ import annotations

import json
import sys
# Windows consoles default to cp1252, which can't encode probe-output
# glyphs (→, §). Force UTF-8 so the probe prints cleanly everywhere.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.graph_editor import (
    ConceptNode,
    ContextAssembly,
    OntologyNode,
    PinnedComponent,
    UserNote,
)


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def check_user_note() -> None:
    note = UserNote(
        content="my note about loan models",
        tags=["hypothesis", "research"],
        source_url="https://example.com/",
    )
    cn = note.to_concept_node(workspace_id="test_ws")
    _assert(isinstance(cn, ConceptNode), "UserNote.to_concept_node must return ConceptNode")
    _assert(cn.type_hint == "user_note", f"type_hint != user_note: {cn.type_hint}")
    _assert(cn.description == "my note about loan models", "description not preserved")
    _assert(cn.workspace_id == "test_ws", "workspace_id not threaded")
    _assert(cn.backing_pointer.startswith("legacy::user_note::"),
            "backing_pointer prefix wrong")
    data = json.loads(cn.data)
    _assert(data["tags"] == ["hypothesis", "research"], "tags not preserved")
    _assert(data["source_url"] == "https://example.com/", "source_url not preserved")
    print(f"  UserNote          OK  -> ConceptNode {cn.concept_id[:8]}")


def check_ontology_node() -> None:
    ont = OntologyNode(
        label_name="Product",
        label_type="entity",
        description="schema.org/Product",
        properties={"category": "ecommerce"},
    )
    cn = ont.to_concept_node()
    _assert(cn.type_hint == "ontology_node", "type_hint != ontology_node")
    _assert(cn.name == "Product", "name not preserved")
    _assert(cn.backing_pointer.startswith("legacy::ontology_node::"),
            "backing_pointer prefix wrong")
    data = json.loads(cn.data)
    _assert(data["label_type"] == "entity", "label_type lost")
    _assert(data["properties"]["category"] == "ecommerce", "properties lost")
    print(f"  OntologyNode      OK  -> ConceptNode {cn.concept_id[:8]}")


def check_pinned_component() -> None:
    pin = PinnedComponent(
        source_snapshot="snap_42",
        lca_xpath="/html/body/main/article",
        patricia_hash="abc123",
        label_summary="3 product cards",
    )
    cn = pin.to_concept_node()
    _assert(cn.type_hint == "pinned_component", "type_hint != pinned_component")
    _assert("article" in cn.name, "name should derive from xpath leaf")
    _assert(cn.provenance == "derived-from-chunk", "provenance wrong")
    data = json.loads(cn.data)
    _assert(data["source_snapshot_id"] == "snap_42", "source_snapshot lost")
    _assert(data["patricia_hash"] == "abc123", "patricia_hash lost")
    print(f"  PinnedComponent   OK  -> ConceptNode {cn.concept_id[:8]}")


def check_context_assembly() -> None:
    ca = ContextAssembly(
        name="my-research-thread",
        fragments=["a", "b", "c"],
        priority=10,
    )
    cn = ca.to_concept_node()
    _assert(cn.type_hint == "context_assembly", "type_hint != context_assembly")
    _assert(cn.name == "my-research-thread", "name not preserved")
    data = json.loads(cn.data)
    _assert(data["member_card_ids"] == ["a", "b", "c"], "fragments lost")
    _assert(data["priority_order"] == 10, "priority lost")
    print(f"  ContextAssembly   OK  -> ConceptNode {cn.concept_id[:8]}")


def main() -> int:
    print("[probe_shims] verifying §8D.44.2 to_concept_node() migration shims")
    check_user_note()
    check_ontology_node()
    check_pinned_component()
    check_context_assembly()
    print("[probe_shims] ALL FOUR SHIMS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
