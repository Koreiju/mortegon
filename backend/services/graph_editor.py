"""
Phase 4A — Knowledge graph editor service (section 8A).
W4 — Adds unified ConceptNode CRUD on top of the legacy entity
CRUD (UserNote, OntologyNode, etc.). The unified ConceptNode model
(§8D.44) is the canonical record type going forward; the legacy
entities co-exist as separate tables for backward compat per §8A.12.

CRUD operations for UserNotes, OntologyNodes, PinnedComponents,
ContextAssemblies, ConceptNodes / ConceptEdges, and their
relationships. Powers the graph editor panel and the 3D knowledge
overlay.
"""

import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# W4 / §8D.44 — Unified ConceptNode dataclass
# ---------------------------------------------------------------------------

@dataclass
class ConceptNode:
    """The uniform concept-node record (§8D.44).

    Every artefact in the unified Database is a ConceptNode. Records
    differ only by ``name``, ``linked_nodes`` (denormalised view of
    edges), and ``backing_pointer`` (opaque runtime handle resolving
    to a python implementation per §8D.44's separability rule).

    Embedding vectors are stored separately in the Kuzu schema
    (``embedding_nomic``, ``embedding_tfidf`` columns) — they are
    elided from the dataclass to keep the in-memory record small;
    callers wanting embeddings hit ``GraphEditor.get_concept_embedding``.
    """

    concept_id: str = ""
    name: str = ""
    description: str = ""
    data: str = ""              # the constructor template (§8D.30)
    rendering: str = ""         # compiled instance of the template
    linked_nodes_json: str = "[]"   # denormalised; authoritative store is ConceptEdge
    backing_pointer: str = ""   # opaque internal handle (§8D.44)
    pagerank: float = 0.0
    provenance: str = "user-authored"  # user-authored | agent-authored | derived-from-chunk | committed-subgraph
    workspace_id: str = ""
    layout_xy: str = ""         # JSON {"x": float, "y": float}
    ui_state: str = ""          # JSON {minimised: bool, ...}
    type_hint: str = ""         # naming-convention tag (e.g. user_note, ontology_node, searchable_url)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.concept_id:
            self.concept_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass
class ConceptEdge:
    """A typed edge between two ConceptNodes (§8D.44, §8A.2).

    ``edge_type`` is one of §8A.2's typed labels (ANNOTATES, IS_A,
    HAS_A, PART_OF, RELATES_TO, DERIVED_FROM, INCLUDES, SIMILAR_TO,
    CLASSIFIES) OR §8D's port-binding labels (PROVIDES_VALUE_FOR,
    METHOD_OUTPUT, PROPERTY_REF, etc.). ``weight`` is the cosine
    similarity for auto-derived SIMILAR_TO edges, null otherwise.
    """

    edge_id: str = ""
    source_id: str = ""
    target_id: str = ""
    edge_type: str = "RELATES_TO"
    source_port: str = ""
    target_port: str = ""
    weight: Optional[float] = None
    variable_name: str = ""
    workspace_id: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.edge_id:
            self.edge_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class UserNote:
    note_id: str = ""
    content: str = ""
    tags: List[str] = None
    source_url: str = ""
    created_at: str = ""
    embedding: Optional[List[float]] = None

    def __post_init__(self):
        if not self.note_id:
            self.note_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self.tags is None:
            self.tags = []

    def to_concept_node(self, workspace_id: str = "") -> "ConceptNode":
        """§8D.44.2 migration shim — project this legacy entity into the
        unified ConceptNode schema. Caller is responsible for persisting
        the returned record through the standard lifecycle dispatcher.
        """
        return ConceptNode(
            concept_id=self.note_id,
            name=(self.content[:60].strip() or "user_note"),
            description=self.content or "",
            data=json.dumps({
                "tags": list(self.tags or []),
                "source_url": self.source_url or "",
            }, indent=2),
            rendering="",
            backing_pointer=f"legacy::user_note::{self.note_id}",
            provenance="user-authored",
            workspace_id=workspace_id,
            type_hint="user_note",
            created_at=self.created_at,
            updated_at=self.created_at,
        )


@dataclass
class OntologyNode:
    node_id: str = ""
    label_name: str = ""
    label_type: str = "concept"  # concept | category | property | relation
    description: str = ""
    properties: Dict[str, Any] = None
    embedding: Optional[List[float]] = None
    created_at: str = ""

    def __post_init__(self):
        if not self.node_id:
            self.node_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self.properties is None:
            self.properties = {}

    def to_concept_node(self, workspace_id: str = "") -> "ConceptNode":
        """§8D.44.2 migration shim."""
        return ConceptNode(
            concept_id=self.node_id,
            name=self.label_name or "ontology_node",
            description=self.description or self.label_name or "",
            data=json.dumps({
                "label_name": self.label_name or "",
                "label_type": self.label_type or "concept",
                "properties": dict(self.properties or {}),
            }, indent=2),
            rendering="",
            backing_pointer=f"legacy::ontology_node::{self.node_id}",
            provenance="user-authored",
            workspace_id=workspace_id,
            type_hint="ontology_node",
            created_at=self.created_at,
            updated_at=self.created_at,
        )


@dataclass
class PinnedComponent:
    pin_id: str = ""
    source_snapshot: str = ""
    lca_xpath: str = ""
    label_summary: str = ""
    patricia_hash: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.pin_id:
            self.pin_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_concept_node(self, workspace_id: str = "") -> "ConceptNode":
        """§8D.44.2 migration shim."""
        return ConceptNode(
            concept_id=self.pin_id,
            name=(self.lca_xpath.split("/")[-1] or "pinned_component"),
            description=(
                f"Pinned subtree at `{self.lca_xpath}` from snapshot "
                f"{self.source_snapshot or '<unknown>'}. "
                f"Patricia hash: {self.patricia_hash or '<none>'}."
            ),
            data=json.dumps({
                "source_snapshot_id": self.source_snapshot or "",
                "subtree_xpath": self.lca_xpath or "",
                "patricia_hash": self.patricia_hash or "",
                "label_summary": self.label_summary or "",
            }, indent=2),
            rendering="",
            backing_pointer=f"legacy::pinned_component::{self.pin_id}",
            provenance="derived-from-chunk",
            workspace_id=workspace_id,
            type_hint="pinned_component",
            created_at=self.created_at,
            updated_at=self.created_at,
        )


@dataclass
class ContextAssembly:
    assembly_id: str = ""
    name: str = ""
    fragments: List[str] = None  # ordered list of note/node/pin IDs
    priority: int = 0
    created_at: str = ""

    def __post_init__(self):
        if not self.assembly_id:
            self.assembly_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self.fragments is None:
            self.fragments = []

    def to_concept_node(self, workspace_id: str = "") -> "ConceptNode":
        """§8D.44.2 migration shim."""
        return ConceptNode(
            concept_id=self.assembly_id,
            name=self.name or "context_assembly",
            description=(
                f"Context assembly `{self.name or self.assembly_id}` "
                f"with {len(self.fragments or [])} fragment(s); "
                f"priority {self.priority}."
            ),
            data=json.dumps({
                "name": self.name or "",
                "member_card_ids": list(self.fragments or []),
                "priority_order": int(self.priority),
            }, indent=2),
            rendering="",
            backing_pointer=f"legacy::context_assembly::{self.assembly_id}",
            provenance="user-authored",
            workspace_id=workspace_id,
            type_hint="context_assembly",
            created_at=self.created_at,
            updated_at=self.created_at,
        )


# Relationship type enum matching section 8A
EDGE_TYPES = [
    "ANNOTATES", "IS_A", "HAS_A", "PART_OF",
    "RELATES_TO", "DERIVED_FROM", "INCLUDES",
    "SIMILAR_TO", "CLASSIFIES",
]


class GraphEditor:
    """
    CRUD service for knowledge graph entities.

    Manages UserNotes, OntologyNodes, PinnedComponents, ContextAssemblies,
    and typed edges between them. Integrates with EmbeddingService for
    semantic retrieval.
    """

    def __init__(self, db_conn=None, embedding_service=None):
        self._db_conn = db_conn
        self._embedding_service = embedding_service
        # In-memory store for when DB is unavailable
        self._notes: Dict[str, UserNote] = {}
        self._ontology_nodes: Dict[str, OntologyNode] = {}
        self._pins: Dict[str, PinnedComponent] = {}
        self._assemblies: Dict[str, ContextAssembly] = {}
        self._edges: List[Dict] = []
        self._edit_history: List[Dict] = []

    # --- UserNote CRUD ---

    def create_note(self, content: str, tags: List[str] = None, source_url: str = "") -> UserNote:
        note = UserNote(content=content, tags=tags or [], source_url=source_url)
        if self._embedding_service:
            note.embedding = self._embedding_service.embed_query(content)
        self._notes[note.note_id] = note
        self._log_edit("create", "user_note", note.note_id)
        return note

    def get_note(self, note_id: str) -> Optional[UserNote]:
        return self._notes.get(note_id)

    def update_note(self, note_id: str, content: str = None, tags: List[str] = None) -> Optional[UserNote]:
        note = self._notes.get(note_id)
        if not note:
            return None
        old = asdict(note)
        if content is not None:
            note.content = content
            if self._embedding_service:
                note.embedding = self._embedding_service.embed_query(content)
        if tags is not None:
            note.tags = tags
        self._log_edit("update", "user_note", note_id, old=old, new=asdict(note))
        return note

    def delete_note(self, note_id: str) -> bool:
        if note_id in self._notes:
            del self._notes[note_id]
            self._log_edit("delete", "user_note", note_id)
            return True
        return False

    def list_notes(self, tag_filter: str = None) -> List[Dict]:
        notes = list(self._notes.values())
        if tag_filter:
            notes = [n for n in notes if tag_filter in n.tags]
        return [asdict(n) for n in notes]

    # --- OntologyNode CRUD ---

    def create_ontology_node(
        self, label_name: str, label_type: str = "concept",
        description: str = "", properties: Dict = None,
    ) -> OntologyNode:
        node = OntologyNode(
            label_name=label_name, label_type=label_type,
            description=description, properties=properties or {},
        )
        if self._embedding_service and description:
            node.embedding = self._embedding_service.embed_query(description)
        self._ontology_nodes[node.node_id] = node
        self._log_edit("create", "ontology_node", node.node_id)
        return node

    def get_ontology_node(self, node_id: str) -> Optional[OntologyNode]:
        return self._ontology_nodes.get(node_id)

    def update_ontology_node(self, node_id: str, **kwargs) -> Optional[OntologyNode]:
        node = self._ontology_nodes.get(node_id)
        if not node:
            return None
        old = asdict(node)
        for key, value in kwargs.items():
            if hasattr(node, key):
                setattr(node, key, value)
        if "description" in kwargs and self._embedding_service:
            node.embedding = self._embedding_service.embed_query(node.description)
        self._log_edit("update", "ontology_node", node_id, old=old, new=asdict(node))
        return node

    def delete_ontology_node(self, node_id: str) -> bool:
        if node_id in self._ontology_nodes:
            del self._ontology_nodes[node_id]
            self._log_edit("delete", "ontology_node", node_id)
            return True
        return False

    # --- PinnedComponent CRUD ---

    def create_pin(
        self, source_snapshot: str, lca_xpath: str,
        label_summary: str = "", patricia_hash: str = "",
    ) -> PinnedComponent:
        pin = PinnedComponent(
            source_snapshot=source_snapshot, lca_xpath=lca_xpath,
            label_summary=label_summary, patricia_hash=patricia_hash,
        )
        self._pins[pin.pin_id] = pin
        self._log_edit("create", "pinned_component", pin.pin_id)
        return pin

    def get_pin(self, pin_id: str) -> Optional[PinnedComponent]:
        return self._pins.get(pin_id)

    def delete_pin(self, pin_id: str) -> bool:
        if pin_id in self._pins:
            del self._pins[pin_id]
            self._log_edit("delete", "pinned_component", pin_id)
            return True
        return False

    # --- ContextAssembly CRUD ---

    def create_assembly(self, name: str, fragments: List[str] = None, priority: int = 0) -> ContextAssembly:
        assembly = ContextAssembly(name=name, fragments=fragments or [], priority=priority)
        self._assemblies[assembly.assembly_id] = assembly
        self._log_edit("create", "context_assembly", assembly.assembly_id)
        return assembly

    def get_assembly(self, assembly_id: str) -> Optional[ContextAssembly]:
        return self._assemblies.get(assembly_id)

    def add_to_assembly(self, assembly_id: str, fragment_id: str) -> Optional[ContextAssembly]:
        assembly = self._assemblies.get(assembly_id)
        if not assembly:
            return None
        if fragment_id not in assembly.fragments:
            assembly.fragments.append(fragment_id)
        return assembly

    # --- Edge operations ---

    def create_edge(self, source_id: str, target_id: str, edge_type: str, properties: Dict = None) -> Dict:
        if edge_type not in EDGE_TYPES:
            raise ValueError(f"Invalid edge type: {edge_type}. Must be one of {EDGE_TYPES}")
        edge = {
            "edge_id": str(uuid.uuid4()),
            "source_id": source_id,
            "target_id": target_id,
            "edge_type": edge_type,
            "properties": properties or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._edges.append(edge)
        self._log_edit("create", "edge", edge["edge_id"])
        return edge

    def get_edges(self, node_id: str) -> List[Dict]:
        """Get all edges incident to a node."""
        return [
            e for e in self._edges
            if e["source_id"] == node_id or e["target_id"] == node_id
        ]

    def delete_edge(self, edge_id: str) -> bool:
        before = len(self._edges)
        self._edges = [e for e in self._edges if e["edge_id"] != edge_id]
        if len(self._edges) < before:
            self._log_edit("delete", "edge", edge_id)
            return True
        return False

    # --- Search ---

    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Semantic search across notes and ontology nodes using
        embedding cosine similarity.
        """
        if not self._embedding_service:
            # Fallback: substring search
            return self._substring_search(query, top_k)

        query_emb = self._embedding_service.embed_query(query)
        results = []

        for note in self._notes.values():
            if note.embedding:
                sim = self._cosine_sim(query_emb, note.embedding)
                results.append({"type": "user_note", "id": note.note_id, "score": sim, "content": note.content})

        for node in self._ontology_nodes.values():
            if node.embedding:
                sim = self._cosine_sim(query_emb, node.embedding)
                results.append({"type": "ontology_node", "id": node.node_id, "score": sim, "label": node.label_name})

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    def _substring_search(self, query: str, top_k: int) -> List[Dict]:
        query_lower = query.lower()
        results = []
        for note in self._notes.values():
            if query_lower in note.content.lower():
                results.append({"type": "user_note", "id": note.note_id, "score": 1.0, "content": note.content})
        for node in self._ontology_nodes.values():
            if query_lower in node.label_name.lower() or query_lower in node.description.lower():
                results.append({"type": "ontology_node", "id": node.node_id, "score": 1.0, "label": node.label_name})
        return results[:top_k]

    @staticmethod
    def _cosine_sim(a: List[float], b: List[float]) -> float:
        import numpy as np
        a_arr = np.array(a)
        b_arr = np.array(b)
        denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
        if denom == 0:
            return 0.0
        return float(np.dot(a_arr, b_arr) / denom)

    # --- Edit history ---

    def _log_edit(self, operation: str, entity_type: str, entity_id: str, old=None, new=None):
        self._edit_history.append({
            "operation": operation,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "old": old,
            "new": new,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_edit_history(self, limit: int = 50) -> List[Dict]:
        return list(reversed(self._edit_history[-limit:]))

    def undo_last(self) -> bool:
        """Undo the last edit operation (simple implementation)."""
        if not self._edit_history:
            return False
        last = self._edit_history.pop()
        # Reverse the operation
        if last["operation"] == "create":
            entity_type = last["entity_type"]
            entity_id = last["entity_id"]
            if entity_type == "user_note":
                self._notes.pop(entity_id, None)
            elif entity_type == "ontology_node":
                self._ontology_nodes.pop(entity_id, None)
            elif entity_type == "pinned_component":
                self._pins.pop(entity_id, None)
            return True
        elif last["operation"] == "update" and last.get("old"):
            # Restore old state
            entity_type = last["entity_type"]
            entity_id = last["entity_id"]
            if entity_type == "user_note" and entity_id in self._notes:
                old = last["old"]
                self._notes[entity_id].content = old.get("content", "")
                self._notes[entity_id].tags = old.get("tags", [])
            return True
        return False

    # -----------------------------------------------------------------
    # W4 / §8D.44 — Unified ConceptNode + ConceptEdge CRUD
    #
    # These methods write through to Kuzu when ``self._db_conn`` is set
    # AND fall back to in-memory stores otherwise. The in-memory path
    # is the canonical no-DB development path (mirrors the older legacy
    # entity behaviour above); Kuzu is the canonical persistent path.
    # Embedding columns (``embedding_nomic``, ``embedding_tfidf``) are
    # written separately via ``set_concept_embedding`` to keep the
    # main upsert SQL small.
    # -----------------------------------------------------------------

    def _ensure_concept_stores(self):
        """Lazy-init the in-memory ConceptNode / Edge maps."""
        if not hasattr(self, "_concepts"):
            self._concepts: Dict[str, ConceptNode] = {}
        if not hasattr(self, "_concept_edges"):
            self._concept_edges: Dict[str, ConceptEdge] = {}

    # --- ConceptNode CRUD ---

    def create_concept(
        self,
        name: str,
        description: str = "",
        data: str = "",
        rendering: str = "",
        backing_pointer: str = "",
        provenance: str = "user-authored",
        workspace_id: str = "",
        layout_xy: Optional[Dict[str, float]] = None,
        ui_state: Optional[Dict[str, Any]] = None,
        type_hint: str = "",
        concept_id: Optional[str] = None,
    ) -> ConceptNode:
        """Create a ConceptNode. Idempotent on ``concept_id`` collision (returns existing)."""
        self._ensure_concept_stores()
        node = ConceptNode(
            concept_id=concept_id or "",
            name=name,
            description=description,
            data=data,
            rendering=rendering,
            backing_pointer=backing_pointer,
            provenance=provenance,
            workspace_id=workspace_id,
            layout_xy=json.dumps(layout_xy) if layout_xy else "",
            ui_state=json.dumps(ui_state) if ui_state else "",
            type_hint=type_hint,
        )
        # Idempotent on collision — return the existing in-memory record.
        if node.concept_id in self._concepts:
            return self._concepts[node.concept_id]
        # Fix: check Kuzu for an existing row before attempting CREATE.
        # Without this guard, idempotent foundation-fixture bootstrap
        # (called on every workspace WS connect) tried CREATE against
        # the existing row and logged a "ConceptNode CREATE failed"
        # warning each time. Now we MATCH first; if the row exists,
        # hydrate from it and skip the CREATE silently.
        if self._db_conn is not None:
            try:
                existing = self.get_concept(node.concept_id)
                if existing is not None:
                    # Already persisted; return the hydrated record.
                    return existing
            except Exception:
                # Probe failure is non-fatal; fall through to CREATE.
                pass
        self._concepts[node.concept_id] = node
        if self._db_conn is not None:
            try:
                self._db_conn.execute(
                    "CREATE (n:ConceptNode {"
                    "concept_id: $concept_id, name: $name, description: $description, "
                    "data: $data, rendering: $rendering, linked_nodes_json: $linked_nodes_json, "
                    "backing_pointer: $backing_pointer, pagerank: $pagerank, "
                    "provenance: $provenance, workspace_id: $workspace_id, "
                    "layout_xy: $layout_xy, ui_state: $ui_state, "
                    "type_hint: $type_hint, "
                    "created_at: $created_at, updated_at: $updated_at})",
                    parameters={
                        "concept_id": node.concept_id,
                        "name": node.name,
                        "description": node.description,
                        "data": node.data,
                        "rendering": node.rendering,
                        "linked_nodes_json": node.linked_nodes_json,
                        "backing_pointer": node.backing_pointer,
                        "pagerank": float(node.pagerank),
                        "provenance": node.provenance,
                        "workspace_id": node.workspace_id,
                        "layout_xy": node.layout_xy,
                        "ui_state": node.ui_state,
                        "type_hint": node.type_hint,
                        "created_at": node.created_at,
                        "updated_at": node.updated_at,
                    },
                )
            except Exception as e:
                # Downgrade to debug log on PK-collision errors so
                # benign races between concurrent idempotent creates
                # (e.g., two WS clients opening the same workspace
                # at the same time) don't flood the log.
                msg = str(e)
                if "exists" in msg.lower() or "primary key" in msg.lower() or "unique" in msg.lower():
                    logger.debug("ConceptNode already exists, skipping CREATE: %s", node.concept_id)
                else:
                    logger.warning("ConceptNode CREATE failed for %s: %s", node.concept_id, e)
        self._log_edit("create", "concept", node.concept_id)
        return node

    def get_concept(self, concept_id: str) -> Optional[ConceptNode]:
        self._ensure_concept_stores()
        if concept_id in self._concepts:
            return self._concepts[concept_id]
        if self._db_conn is not None:
            try:
                res = self._db_conn.execute(
                    "MATCH (n:ConceptNode) WHERE n.concept_id = $cid "
                    "RETURN n.concept_id, n.name, n.description, n.data, n.rendering, "
                    "n.linked_nodes_json, n.backing_pointer, n.pagerank, n.provenance, "
                    "n.workspace_id, n.layout_xy, n.ui_state, n.type_hint, "
                    "n.created_at, n.updated_at LIMIT 1",
                    parameters={"cid": concept_id},
                )
                if res.has_next():
                    row = res.get_next()
                    node = ConceptNode(
                        concept_id=row[0], name=row[1] or "", description=row[2] or "",
                        data=row[3] or "", rendering=row[4] or "",
                        linked_nodes_json=row[5] or "[]",
                        backing_pointer=row[6] or "",
                        pagerank=float(row[7]) if row[7] is not None else 0.0,
                        provenance=row[8] or "user-authored",
                        workspace_id=row[9] or "",
                        layout_xy=row[10] or "", ui_state=row[11] or "",
                        type_hint=row[12] or "",
                        created_at=row[13] or "", updated_at=row[14] or "",
                    )
                    self._concepts[concept_id] = node
                    return node
            except Exception as e:
                logger.warning("ConceptNode GET failed for %s: %s", concept_id, e)
        return None

    def update_concept(
        self,
        concept_id: str,
        **kwargs,
    ) -> Optional[ConceptNode]:
        """Update writable fields on a ConceptNode.

        Accepted kwargs: name, description, data, rendering,
        linked_nodes_json, backing_pointer, pagerank, provenance,
        layout_xy (dict or str), ui_state (dict or str), type_hint.
        """
        self._ensure_concept_stores()
        node = self.get_concept(concept_id)
        if not node:
            return None
        old = asdict(node)
        # Normalise dict-shaped kwargs to JSON strings for storage.
        if isinstance(kwargs.get("layout_xy"), dict):
            kwargs["layout_xy"] = json.dumps(kwargs["layout_xy"])
        if isinstance(kwargs.get("ui_state"), dict):
            kwargs["ui_state"] = json.dumps(kwargs["ui_state"])
        for key, value in kwargs.items():
            if hasattr(node, key):
                setattr(node, key, value)
        node.updated_at = datetime.now(timezone.utc).isoformat()
        # Write through to Kuzu.
        if self._db_conn is not None:
            try:
                # Build SET clause from supplied kwargs only (keep nulls
                # out of the SET to avoid clobbering existing fields).
                set_parts = []
                params: Dict[str, Any] = {"cid": concept_id, "updated_at": node.updated_at}
                for key in (
                    "name", "description", "data", "rendering",
                    "linked_nodes_json", "backing_pointer", "pagerank",
                    "provenance", "workspace_id", "layout_xy", "ui_state",
                    "type_hint",
                ):
                    if key in kwargs:
                        set_parts.append(f"n.{key} = ${key}")
                        params[key] = getattr(node, key)
                set_parts.append("n.updated_at = $updated_at")
                if set_parts:
                    self._db_conn.execute(
                        f"MATCH (n:ConceptNode) WHERE n.concept_id = $cid "
                        f"SET {', '.join(set_parts)}",
                        parameters=params,
                    )
            except Exception as e:
                logger.warning("ConceptNode UPDATE failed for %s: %s", concept_id, e)
        self._log_edit("update", "concept", concept_id, old=old, new=asdict(node))
        return node

    def delete_concept(self, concept_id: str, *, force: bool = False) -> bool:
        self._ensure_concept_stores()
        # §8D.12 — foundation fixtures (Database, WebBrowser, Agent) cannot be
        # deleted, hidden, soft-deleted, or duplicated. Reject at the
        # service layer so REST + agent + cascade paths are all guarded
        # rather than only the HTTP surface. The conventional concept_id
        # prefix is ``fixture::`` per ``foundation_fixtures.py``.
        #
        # ``force=True`` bypasses the guard. It is used ONLY by the §S.1
        # migration that purges the deprecated ``fixture::editor::*`` card
        # (and its python tree) left in pre-existing default workspaces —
        # never exposed to REST / agent / cascade callers.
        if (not force) and isinstance(concept_id, str) and concept_id.startswith("fixture::"):
            logger.warning(
                "[GraphEditor] Refusing to delete foundation fixture %s "
                "(§8D.12 says fixtures are undeletable).",
                concept_id,
            )
            return False
        existed = concept_id in self._concepts
        if existed:
            del self._concepts[concept_id]
        if self._db_conn is not None:
            try:
                # Delete incident edges first, then the node. Kuzu
                # requires directional MATCH for DELETE on
                # relationships ("Binder exception: Delete undirected
                # rel is not supported"), so we explicitly run two
                # directed deletes — outgoing then incoming — before
                # the node removal. The undirected form
                # ``-[e:ConceptEdge]-()`` would have caught both at
                # once but Kuzu rejects it at delete time.
                self._db_conn.execute(
                    "MATCH (n:ConceptNode)-[e:ConceptEdge]->() "
                    "WHERE n.concept_id = $cid DELETE e",
                    parameters={"cid": concept_id},
                )
                self._db_conn.execute(
                    "MATCH ()-[e:ConceptEdge]->(n:ConceptNode) "
                    "WHERE n.concept_id = $cid DELETE e",
                    parameters={"cid": concept_id},
                )
                self._db_conn.execute(
                    "MATCH (n:ConceptNode) WHERE n.concept_id = $cid DELETE n",
                    parameters={"cid": concept_id},
                )
                existed = True
            except Exception as e:
                logger.warning("ConceptNode DELETE failed for %s: %s", concept_id, e)
        # Drop incident edges from in-memory store too.
        if hasattr(self, "_concept_edges"):
            drop = [eid for eid, e in self._concept_edges.items()
                    if e.source_id == concept_id or e.target_id == concept_id]
            for eid in drop:
                del self._concept_edges[eid]
        if existed:
            self._log_edit("delete", "concept", concept_id)
        return existed

    def list_concepts(
        self,
        workspace_id: Optional[str] = None,
        type_hint: Optional[str] = None,
        provenance: Optional[str] = None,
        limit: int = 1000,
    ) -> List[ConceptNode]:
        """List ConceptNodes optionally filtered by workspace / type / provenance."""
        self._ensure_concept_stores()
        results: List[ConceptNode] = []
        if self._db_conn is not None:
            try:
                where = []
                params: Dict[str, Any] = {}
                if workspace_id is not None:
                    where.append("n.workspace_id = $wid")
                    params["wid"] = workspace_id
                if type_hint is not None:
                    where.append("n.type_hint = $th")
                    params["th"] = type_hint
                if provenance is not None:
                    where.append("n.provenance = $pr")
                    params["pr"] = provenance
                where_sql = ("WHERE " + " AND ".join(where)) if where else ""
                res = self._db_conn.execute(
                    f"MATCH (n:ConceptNode) {where_sql} "
                    f"RETURN n.concept_id, n.name, n.description, n.data, n.rendering, "
                    f"n.linked_nodes_json, n.backing_pointer, n.pagerank, n.provenance, "
                    f"n.workspace_id, n.layout_xy, n.ui_state, n.type_hint, "
                    f"n.created_at, n.updated_at LIMIT {int(limit)}",
                    parameters=params,
                )
                while res.has_next():
                    row = res.get_next()
                    node = ConceptNode(
                        concept_id=row[0], name=row[1] or "", description=row[2] or "",
                        data=row[3] or "", rendering=row[4] or "",
                        linked_nodes_json=row[5] or "[]",
                        backing_pointer=row[6] or "",
                        pagerank=float(row[7]) if row[7] is not None else 0.0,
                        provenance=row[8] or "user-authored",
                        workspace_id=row[9] or "",
                        layout_xy=row[10] or "", ui_state=row[11] or "",
                        type_hint=row[12] or "",
                        created_at=row[13] or "", updated_at=row[14] or "",
                    )
                    self._concepts[node.concept_id] = node
                    results.append(node)
                return results
            except Exception as e:
                logger.warning("ConceptNode LIST failed: %s", e)
        # In-memory fallback
        for node in self._concepts.values():
            if workspace_id is not None and node.workspace_id != workspace_id:
                continue
            if type_hint is not None and node.type_hint != type_hint:
                continue
            if provenance is not None and node.provenance != provenance:
                continue
            results.append(node)
        return results[:limit]

    # --- ConceptEdge CRUD ---

    def _find_concept_edge(
        self, source_id: str, target_id: str, edge_type: str,
        source_port: str = "", target_port: str = "", workspace_id: str = "",
    ) -> Optional["ConceptEdge"]:
        """§7 natural-key lookup — return the existing ConceptEdge matching the
        five-tuple (source, target, edge_type, source_port, target_port) in this
        workspace, or None. Checks the in-memory cache first, then Kuzu (so a
        persisted edge after a process restart still dedups). Used by
        ``create_concept_edge`` to guarantee no duplicate hard links."""
        sp = source_port or ""
        tp = target_port or ""
        ws = workspace_id or ""
        for e in self._concept_edges.values():
            if (e.source_id == source_id and e.target_id == target_id
                    and e.edge_type == edge_type
                    and (e.source_port or "") == sp
                    and (e.target_port or "") == tp
                    and (e.workspace_id or "") == ws):
                return e
        if self._db_conn is not None:
            try:
                res = self._db_conn.execute(
                    "MATCH (a:ConceptNode)-[e:ConceptEdge]->(b:ConceptNode) "
                    "WHERE a.concept_id = $src AND b.concept_id = $tgt "
                    "AND e.edge_type = $et AND e.source_port = $sp "
                    "AND e.target_port = $tp AND e.workspace_id = $ws "
                    "RETURN e.edge_id, e.weight, e.variable_name, e.created_at LIMIT 1",
                    parameters={
                        "src": source_id, "tgt": target_id, "et": edge_type,
                        "sp": sp, "tp": tp, "ws": ws,
                    },
                )
                if res.has_next():
                    row = res.get_next()
                    e = ConceptEdge(
                        edge_id=row[0], source_id=source_id, target_id=target_id,
                        edge_type=edge_type, source_port=sp, target_port=tp,
                        weight=row[1], variable_name=row[2] or "", workspace_id=ws,
                    )
                    if row[3]:
                        e.created_at = row[3]
                    self._concept_edges[e.edge_id] = e
                    return e
            except Exception as exc:
                logger.debug("ConceptEdge natural-key lookup failed: %s", exc)
        return None

    def create_concept_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str = "RELATES_TO",
        source_port: str = "",
        target_port: str = "",
        weight: Optional[float] = None,
        variable_name: str = "",
        workspace_id: str = "",
    ) -> ConceptEdge:
        self._ensure_concept_stores()
        # §7 (ConceptEdge.md) — the five-tuple (source, target, edge_type,
        # source_port, target_port) is the natural key; NEVER create a duplicate
        # hard link. Idempotent re-materialisation of the foundation python-API
        # trees (which runs on every workspace re-open) would otherwise pile up
        # duplicate OBJECT_HAS_* edges with fresh edge_ids, inflating PageRank +
        # churning every downstream edge-set diff. Return the existing edge.
        existing = self._find_concept_edge(
            source_id, target_id, edge_type, source_port, target_port, workspace_id,
        )
        if existing is not None:
            return existing
        edge = ConceptEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            source_port=source_port,
            target_port=target_port,
            weight=weight,
            variable_name=variable_name,
            workspace_id=workspace_id,
        )
        self._concept_edges[edge.edge_id] = edge
        if self._db_conn is not None:
            try:
                self._db_conn.execute(
                    "MATCH (a:ConceptNode), (b:ConceptNode) "
                    "WHERE a.concept_id = $src AND b.concept_id = $tgt "
                    "CREATE (a)-[e:ConceptEdge {"
                    "edge_id: $edge_id, edge_type: $edge_type, "
                    "source_port: $source_port, target_port: $target_port, "
                    "weight: $weight, variable_name: $variable_name, "
                    "workspace_id: $workspace_id, created_at: $created_at"
                    "}]->(b)",
                    parameters={
                        "src": source_id, "tgt": target_id,
                        "edge_id": edge.edge_id, "edge_type": edge.edge_type,
                        "source_port": edge.source_port,
                        "target_port": edge.target_port,
                        "weight": float(edge.weight) if edge.weight is not None else 0.0,
                        "variable_name": edge.variable_name,
                        "workspace_id": edge.workspace_id,
                        "created_at": edge.created_at,
                    },
                )
            except Exception as e:
                logger.warning("ConceptEdge CREATE failed (%s -> %s): %s", source_id, target_id, e)
        self._log_edit("create", "concept_edge", edge.edge_id)
        return edge

    def get_concept_edge(self, edge_id: str) -> Optional["ConceptEdge"]:
        """Look up a single ConceptEdge by id (in-memory cache first; DB fallback)."""
        self._ensure_concept_stores()
        cached = self._concept_edges.get(edge_id)
        if cached is not None:
            return cached
        if self._db_conn is None:
            return None
        try:
            res = self._db_conn.execute(
                "MATCH (a:ConceptNode)-[e:ConceptEdge]->(b:ConceptNode) "
                "WHERE e.edge_id = $eid "
                "RETURN e.edge_id, a.concept_id, b.concept_id, e.edge_type, "
                "e.source_port, e.target_port, e.weight, e.variable_name, "
                "e.workspace_id, e.created_at LIMIT 1",
                parameters={"eid": edge_id},
            )
            if res.has_next():
                row = res.get_next()
                edge = ConceptEdge(
                    edge_id=row[0], source_id=row[1], target_id=row[2],
                    edge_type=row[3] or "RELATES_TO",
                    source_port=row[4] or "", target_port=row[5] or "",
                    weight=float(row[6]) if row[6] not in (None, 0.0) else None,
                    variable_name=row[7] or "",
                    workspace_id=row[8] or "",
                    created_at=row[9] or "",
                )
                self._concept_edges[edge.edge_id] = edge
                return edge
        except Exception as e:
            logger.warning("ConceptEdge GET failed for %s: %s", edge_id, e)
        return None

    def delete_concept_edge(self, edge_id: str) -> bool:
        self._ensure_concept_stores()
        existed = edge_id in self._concept_edges
        if existed:
            del self._concept_edges[edge_id]
        if self._db_conn is not None:
            try:
                self._db_conn.execute(
                    "MATCH ()-[e:ConceptEdge]-() WHERE e.edge_id = $eid DELETE e",
                    parameters={"eid": edge_id},
                )
                existed = True
            except Exception as e:
                logger.warning("ConceptEdge DELETE failed for %s: %s", edge_id, e)
        if existed:
            self._log_edit("delete", "concept_edge", edge_id)
        return existed

    def list_concept_edges(
        self,
        workspace_id: Optional[str] = None,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        edge_type: Optional[str] = None,
        limit: int = 5000,
    ) -> List[ConceptEdge]:
        self._ensure_concept_stores()
        edges: List[ConceptEdge] = []
        if self._db_conn is not None:
            try:
                where = []
                params: Dict[str, Any] = {}
                if workspace_id is not None:
                    where.append("e.workspace_id = $wid")
                    params["wid"] = workspace_id
                if source_id is not None:
                    where.append("a.concept_id = $src")
                    params["src"] = source_id
                if target_id is not None:
                    where.append("b.concept_id = $tgt")
                    params["tgt"] = target_id
                if edge_type is not None:
                    where.append("e.edge_type = $et")
                    params["et"] = edge_type
                where_sql = ("WHERE " + " AND ".join(where)) if where else ""
                res = self._db_conn.execute(
                    f"MATCH (a:ConceptNode)-[e:ConceptEdge]->(b:ConceptNode) {where_sql} "
                    f"RETURN e.edge_id, a.concept_id, b.concept_id, e.edge_type, "
                    f"e.source_port, e.target_port, e.weight, e.variable_name, "
                    f"e.workspace_id, e.created_at LIMIT {int(limit)}",
                    parameters=params,
                )
                while res.has_next():
                    row = res.get_next()
                    edge = ConceptEdge(
                        edge_id=row[0], source_id=row[1], target_id=row[2],
                        edge_type=row[3] or "RELATES_TO",
                        source_port=row[4] or "", target_port=row[5] or "",
                        weight=float(row[6]) if row[6] not in (None, 0.0) else None,
                        variable_name=row[7] or "",
                        workspace_id=row[8] or "",
                        created_at=row[9] or "",
                    )
                    self._concept_edges[edge.edge_id] = edge
                    edges.append(edge)
                return edges
            except Exception as e:
                logger.warning("ConceptEdge LIST failed: %s", e)
        # In-memory fallback
        for edge in self._concept_edges.values():
            if workspace_id is not None and edge.workspace_id != workspace_id:
                continue
            if source_id is not None and edge.source_id != source_id:
                continue
            if target_id is not None and edge.target_id != target_id:
                continue
            if edge_type is not None and edge.edge_type != edge_type:
                continue
            edges.append(edge)
        return edges[:limit]

    def set_concept_embedding(
        self,
        concept_id: str,
        *,
        nomic: Optional[List[float]] = None,
        tfidf: Optional[List[float]] = None,
    ) -> bool:
        """Write description-nomic and/or rendered-tfidf vectors for a ConceptNode.

        Either or both vectors may be supplied. The two vectors are
        independent (different metrics, different roles per §8D.17 /
        §8D.43). Missing-vector defaults to keeping the existing value.
        """
        if self._db_conn is None or (nomic is None and tfidf is None):
            return False
        try:
            set_parts = []
            params: Dict[str, Any] = {"cid": concept_id}
            if nomic is not None:
                set_parts.append("n.embedding_nomic = $nomic")
                params["nomic"] = list(nomic)
            if tfidf is not None:
                set_parts.append("n.embedding_tfidf = $tfidf")
                params["tfidf"] = list(tfidf)
            self._db_conn.execute(
                f"MATCH (n:ConceptNode) WHERE n.concept_id = $cid "
                f"SET {', '.join(set_parts)}",
                parameters=params,
            )
            return True
        except Exception as e:
            logger.warning("set_concept_embedding failed for %s: %s", concept_id, e)
            return False


# ---------------------------------------------------------------------------
# Module-level singleton (lazy, bound to the default DB connection)
#
# Eleven sites (routes.py, agent_runtime cascade ticks, the six backing-
# registry resolvers, signal_fields, pipeline) used to construct fresh
# ``GraphEditor(db_conn=get_connection())`` instances on every call. The
# in-memory caches inside GraphEditor (``_concept_edges`` etc.) then
# diverged across instances: a concept created via one editor's cache
# could be missed by a second editor's ``get_concept_edge`` until the
# DB round-trip rehydrated the cache. Routing through a process-wide
# singleton fixes the cache coherence and avoids the per-call Kuzu
# connection overhead.
#
# Sites that pass a custom ``db_conn`` (signal_fields, pipeline — both
# called from scan workers with a scoped connection) keep constructing
# their own instance; this factory is the *default-connection* path.
# ---------------------------------------------------------------------------

import threading as _ge_threading

_DEFAULT_GE: Optional["GraphEditor"] = None
_DEFAULT_GE_LOCK = _ge_threading.Lock()


def get_default_graph_editor() -> "GraphEditor":
    """Return the process-wide GraphEditor bound to the default DB
    connection. Lazily constructed on first call. Thread-safe.

    Falls open on missing connection — instantiates with ``db_conn=None``
    so callers that only need the in-memory caches still work (e.g.,
    foundational fixture lookups in headless tests).
    """
    global _DEFAULT_GE
    with _DEFAULT_GE_LOCK:
        if _DEFAULT_GE is None:
            try:
                from backend.database import get_connection
                conn = get_connection()
            except Exception:
                conn = None
            _DEFAULT_GE = GraphEditor(db_conn=conn)
        return _DEFAULT_GE
