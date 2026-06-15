# Spec — Backend / Materialiser (Python-API · Library · Fixtures)

> Deepens [`code_architecture/backend/materialiser.md`](../../code_architecture/backend/materialiser.md). Files: `python_api_materialiser.py`, `foundation_fixtures.py`. Types: [`../types.md`](../types.md) §2/§3. Constants: [`../constants.md`](../constants.md) §3 (`COMPILE_MAX_DEPTH` reused as walk depth).

---

## §1 — `materialise_class` / `materialise_qualified_name` (+ `walk_hierarchy`)

```python
# Realized names (python_api_materialiser.py): a live class → materialise_class;
# an importable dotted path → materialise_qualified_name; the recursive member
# walk that both drive → walk_hierarchy. (The "materialise_object" name is the
# spec's generic label for this pair.)
def materialise_class(self, cls, *, workspace_id: WorkspaceId, max_walk_depth: int = 4) -> list[ConceptNode]
def materialise_qualified_name(self, qualname: str, *, workspace_id: WorkspaceId, max_walk_depth: int = 4) -> list[ConceptNode]
def walk_hierarchy(self, root, *, workspace_id: WorkspaceId, max_walk_depth: int = 4) -> list[ConceptNode]
```
- **Does** — project a live class/instance into `python_object` + `python_property` + `python_function` ConceptNode trees, all `read_only`.
- **Pre** — importable qualname or a live object. **Post** — nodes upserted via lifecycle.md (provenance derived); edges added; idempotent on qualified names (re-import upserts, never duplicates). **Returns** the created/updated nodes.
- **Raises** — `ImportError`→`NotFoundError` (404) at the route.
- **Algorithm:**
```
root = ConceptNode(type_hint="python_object", read_only=True, description=cls.__doc__, backing=f"python_object::{q}")
for member in inspect.getmembers(cls) (depth ≤ max_walk_depth):
    if isproperty/descriptor:
        p = ConceptNode(type_hint="python_property", read_only=True, backing=f"python_property::{q}.{name}")
        edge(root, p, OBJECT_HAS_PROPERTY)
    if isfunction/ismethod:
        f = ConceptNode(type_hint="python_function", read_only=True, no_datablock=True,
                        data=signature_metadata_only(member),       # params+annotations ONLY — NEVER the source body
                        description=member.__doc__, backing=f"python_function::{q}.{name}")
        edge(root, f, OBJECT_HAS_FUNCTION)
        for ann in input_annotations(member):  edge(f, type_node(ann), FUNCTION_INPUT_TYPE)     # §8D.42.1
        edge(f, type_node(return_annotation(member)), FUNCTION_OUTPUT_TYPE)
register every backing in BackingRegistry; return nodes
```
- **Invariant** — function nodes carry `no_datablock=True`; their `data` is signature metadata, the body is **never** projected (assertion, §8D.4.2). The render form is `key: Type = value` (cell.md §3.1).

---

## §2 — `materialise_module` (+ `re_materialise`)

```python
# Realized names: materialise_module walks a whole imported module; re_materialise
# does the diff add/refresh/GC against the module-level _MODULE_MATERIALISED registry.
def materialise_module(self, module_name: str, *, workspace_id: WorkspaceId, max_walk_depth: int = 4) -> list[ConceptNode]
def re_materialise(self, module_name: str, *, workspace_id: WorkspaceId) -> dict   # diff: added/refreshed/gc'd
```
- For each exported symbol of the module → `materialise_class`/`materialise_qualified_name` (depth-bounded). Idempotent on qualnames. A **`backing_version_bump`** on any symbol invalidates the compile cache of referencing nodes (persistence.md §3.3 → cascade recompiles). Routes: `POST /api/python_api/materialise_module` (refresh: `POST /api/python_api/rematerialise_module`).

---

## §3 — `ensure_foundation_fixtures`

```python
def ensure_foundation_fixtures(workspace_id: WorkspaceId) -> tuple[ConceptNode, ConceptNode, ConceptNode, ConceptNode]
```
- **Post** — exactly **4** undeletable peer fixtures exist: `Agent`, `WebBrowser`, `Database`, `Editor`, backings `fixture::{agent,web_browser,database,editor}::<wsid>`. **Flat — no centrality hub** (Database is not root). Idempotent (re-run is a no-op if present).
- **Algorithm:** for kind in (agent, web_browser, database, editor): if absent, create via lifecycle.md with `read_only`-ish guard (the fixture delete-guard in lifecycle.md §2 makes them undeletable); register backing → the live runtime handle (SLMClient/WebBrowserManager/Kuzu+services/editor service). `SearchableURL/DetectedAccessor/XPathPattern` are **peers** compiled later (scanner.md), **not** children of Database.

---

## §4 — Dependencies / Excluded
**Calls:** `inspect`, `BackingRegistry` (persistence.md), lifecycle.md (upsert), ConceptIndexService (description→nomic). **Called by:** api.md lifespan (fixtures) + `POST /api/library_import`; the Agent fixture's functional objects. **Excluded:** which specific classes ship materialised (manifest concern); the "fixture" register meaning. The `no_datablock` body-exclusion is a **hard rule**, specified above.
