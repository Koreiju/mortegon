# Backend — Materialiser (Python-API Trees · Library Middleware · Fixtures)

> **Owns:** projecting live Python objects into read-only ConceptNode trees, the library-import middleware, and the four foundation fixtures. Files: `python_api_materialiser.py`, `foundation_fixtures.py`. Design: §8D.4.2 / §9.5 / §9.6 / §9.6.1 / §9.7 / §8D.35.1 / §8D.42.1. Realises `code_constraints/materialiser.md`.

---

## §1 — Responsibility

Materialise Python `Object / Property / Function` ConceptNode trees from live classes/modules (§8D.4.2), all `read_only:true` (🔒, latch hidden, no edits); function nodes carry `no_datablock:true` — the data field holds **signature metadata only, never the function body**. Ensure exactly **four** undeletable foundation fixtures (§8D.35.1). Import third-party libraries as materialised trees via middleware (§9.7).

---

## §2 — Public Surface

```python
# python_api_materialiser.py
def materialise_object(obj_or_qualname, *, max_walk_depth: int = 4) -> list[ConceptNode]
def materialise_library(module_name: str, *, max_walk_depth: int = 4) -> list[ConceptNode]  # POST /api/library_import
def backing_version_bump(qualname: str) -> None        # invalidate downstream compile cache (§15.6)

# foundation_fixtures.py
def ensure_foundation_fixtures(workspace_id: str) -> tuple[ConceptNode, ...]   # exactly 4; idempotent
```

---

## §3 — Internal Logic

### §3.1 `inspect`-walk (§9.6)
```
materialise_object(cls):
  for each member via inspect:
     property/descriptor → ConceptNode(type_hint="python_property", read_only=True),  edge OBJECT_HAS_PROPERTY
     method/callable     → ConceptNode(type_hint="python_function", read_only=True, no_datablock=True), edge OBJECT_HAS_FUNCTION
                           data = signature metadata (params, annotations) ONLY — never the source body
                           edges FUNCTION_INPUT_TYPE / FUNCTION_OUTPUT_TYPE per annotation → downstream type ontology (§8D.42.1)
     docstring → node.description (→ nomic, retrieval.md)
  idempotent on the qualified name (re-import upserts, never duplicates)
```
The **typed panel form** `key: Type = value` (§9.6.1) is the materialised render — the type slot in the field-tree (`frontend/cell.md`).

### §3.2 Library middleware (§9.7)
Reads a `wfh_imports.py`-style manifest module, walks each exported symbol (depth ≤ `max_walk_depth`, default 4), materialising each as a tree. Idempotent on qualified names. A **backing-version bump** (§15.6) invalidates the compile cache of every node referencing that backing (compute.md / persistence.md `BackingRegistry`).

### §3.3 The four fixtures (§8D.35.1 — flat, no hub)
`ensure_foundation_fixtures` materialises exactly four peers — **Agent · WebBrowser · Database · Editor** — all undeletable (the delete guard, lifecycle.md §3.1 step 1), all flat (no centrality hub; Database is not the root). `SearchableURL / DetectedAccessor / XPathPattern` are **peers** of the fixtures, not children of Database (compiled-from-scans, scanner.md). Each fixture's backing resolves via `BackingRegistry` (`fixture::{kind}::<wsid>`, persistence.md).

---

## §4 — Dependencies

- **Calls:** `inspect`, `BackingRegistry` (register backings, persistence.md), ConceptLifecycle (upsert the materialised nodes, lifecycle.md), ConceptIndexService (description → nomic, retrieval.md).
- **Called by:** boot/lifespan (`ensure_foundation_fixtures`), `POST /api/library_import`, the Agent fixture (its `template` + functional objects, agent.md).

---

## §5 — Excluded

- Which specific stdlib/third-party classes ship materialised (a manifest concern, not architecture). The register meaning of "fixture." The function-body exclusion is a hard rule (`no_datablock`), encoded; the rationale is design.
