# Object: PythonAPIMaterialiser (Library-Imports Middleware)

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §9.6 (Python-native API trees), §9.7 (library-imports middleware — the §1.2 generalisation), §1.2 verbatim, §18.28 (orphan trees anti-goal).

**Status.** Realised (core) — the four-fixture materialisation is realised (incl. the `OBJECT_HAS_*` + `FUNCTION_INPUT_TYPE`/`FUNCTION_OUTPUT_TYPE` type-ontology edges + transitive type-target closure; `scripts/probe_python_api.py`). The generalised **library-imports middleware** (§1.2) is now realised too: `materialise_module(module_path)` + `walk_hierarchy` + `get_materialised_qualname` in `python_api_materialiser.py`, exposed at `POST /api/python_api/materialise_module` and the `python-api-materialise-module` REPL action, materialise an Object/Property/Function tree for every top-level imported class of a `wfh_imports.py`-style module (submodule-only recursion guard = the §7 explosion safeguard). **`re_materialise` (§2.4/§3.3) is wired**: `re_materialise(module_path)` re-walks (add new + refresh existing with backing-version bump) and **GCs the subtrees of classes no longer imported**, scoped via a per-module provenance registry so it never touches the fixtures or another module's trees — exposed at `POST /api/python_api/rematerialise_module` + the `python-api-rematerialise-module` REPL action (the §3.3 explicit-reimport alternative to an OS file-watcher). Verified offline: a 2-class module re-walked after dropping a class GCs exactly that class's tree (`removed=[Beta]`, `Alpha` kept). **First-boot via `materialise_module(WORKSPACE_IMPORTS_MODULE)` (§3.1) is now wired**: `backend/wfh_imports.py` (the shipped canonical imports module) imports the four fixture classes, and `ensure_foundation_python_trees` materialises it through the middleware (the per-qualname loop is the fallback). Verified: a fresh boot yields the python-native trees (`python_object × 3` — `GraphEditor` backs Database + Editor — `+ python_function × 35`) via the imports module, with all four fixture cards present.

---

## §1 — What it is

The materialiser walks a Python module's recursive object + package/module hierarchy via `inspect` and produces an Object/Property/Function ConceptNode tree for each class/property/method, all with the read-only / no-datablock contract. The user's §1.2 update generalised the materialiser into a *library-imports middleware*: given a simple module that holds `import some_pkg` / `from some_pkg import some_class` statements, the middleware resolves every imported symbol and walks each one's hierarchy. The four foundational fixtures (Agent, WebBrowser, Database, Editor) are the first application of this rule; any user-imported library flows through the same pipeline.

The §1.5 framing places PythonAPIMaterialiser at the boundary between the Real (the running Python runtime is, for the workspace, part of the world being measured) and the Imaginary (the materialised ConceptNode tree is the imaginary's structured image of that runtime). The Editor.create primitive (§9.5.1) is the mechanism through which the imaginary lays out the tree.

---

## §2 — Shape + Methods

### §2.1 Input contract

The middleware reads a module — typically `wfh_imports.py` in the workspace's config dir — whose body is `import` statements:

```python
# wfh_imports.py
from backend.services.selenium_client import WebBrowserManager
from backend.services.global_tfidf_store import GlobalTfidfStore  # also exposes Database surface
from backend.services.agent_runtime import MetaCognitionTick
from backend.services.graph_editor import GraphEditor

# user-imported libraries:
import numpy
from pandas import DataFrame
```

Each top-level resolved symbol becomes a root of a materialised tree.

### §2.2 Key methods

| Method | Purpose |
|---|---|
| `materialise_module(module_path, workspace_id, *, max_walk_depth=4)` | Read the imports module; resolve every symbol; produce ConceptNode trees |
| `materialise_class(class_obj, workspace_id, *, parent_id=None)` | Inspect a single class; produce its python_object + child python_property/python_function tree |
| `walk_hierarchy(symbol, max_depth)` | Recursive walk via `inspect`; depth-bounded |
| `re_materialise(module_path, workspace_id)` | Re-walk after `wfh_imports.py` changes; idempotent on stable qualified names; bumps `backing_pointer` version on changed symbols |
| `get_materialised_qualname(qualified_name, workspace_id)` | Lookup existing materialised root by qualified name (idempotency check) |

### §2.3 Walk algorithm

For each resolved symbol:

1. If it's a module — recurse into its `__all__` (or all public attributes if `__all__` is missing), depth-bounded by `max_walk_depth`.
2. If it's a class — materialise as `python_object` ConceptNode with `data={qualified_name, read_only: true, members: [<child ids>]}`; for each property and public method, materialise as `python_property` / `python_function` child.
3. If it's a property or `@property` descriptor — materialise as `python_property` with `data={qualified_name, read_only: true, value_type, static, no_datablock: true}`; description from the docstring or annotation.
4. If it's a function or method — materialise as `python_function` with `data={qualified_name, read_only: true, no_datablock: true, ports: <inspect.signature-derived port schema>}`.
5. Edges:
   - `OBJECT_HAS_PROPERTY` / `OBJECT_HAS_FUNCTION` from parent class to each member.
   - `FUNCTION_INPUT_TYPE` / `FUNCTION_OUTPUT_TYPE` from each function to the python_object representing its annotated input/output type. If the annotated type is itself in the walked hierarchy, the edge resolves; if it's in a different imported library's tree, the edge crosses libraries (which is what gives the type ontology its cross-library composability).
   - If a target type is referenced but not yet materialised, recursively materialise it (transitive closure within the walk depth).

### §2.4 Idempotency

Re-running the middleware over an updated `wfh_imports.py`:

- Newly-imported symbols add their subtrees via fresh `Editor.create` calls.
- Removed-import symbols dissolve their subtrees via `Editor.delete` cascading from the root.
- Symbols present in both — if the underlying Python signature changed (function signature, property type, class member list), bump the `backing_pointer` version per §15.6 and re-emit the affected ConceptNode records via `Editor.overwrite`. Dependent compile caches invalidate per §15.6.
- Symbols present in both with unchanged signatures — no-op.

The middleware's idempotency contract is what allows the four foundation fixtures + arbitrary user-imported libraries to be re-walked on every workspace boot without producing duplicate trees.

---

## §3 — Lifecycle

### §3.1 First-boot materialisation

`foundation_fixtures.ensure_foundation_fixtures(workspace_id)` calls `materialise_module(WORKSPACE_IMPORTS_MODULE, workspace_id)`. On a fresh workspace, this materialises the four fixtures' trees from scratch. On an existing workspace, idempotency kicks in.

### §3.2 User-initiated import

The user (or agent via emitter) calls `library-import { qualified_name }` from the REPL or via a GUI gesture. The middleware:

1. Resolves the qualified_name to a Python symbol.
2. Materialises its subtree via `materialise_class` or recursive `walk_hierarchy`.
3. Persists the new root + members in Kuzu.
4. Emits `concept_changed` × N (one per materialised node).
5. The frontend renders the new peer python_object tree alongside the four fixtures.

### §3.3 Re-import on `wfh_imports.py` change

A file-watcher (or an explicit `materialiser-reimport` REPL action) triggers `re_materialise`. The diff between the prior and current materialisation drives the create / overwrite / delete calls.

### §3.4 Workspace purge

Materialised trees are ConceptNodes like any other; the purge handler walks them through `apply_delete_lifecycle`. The next `ensure_foundation_fixtures` call re-materialises from scratch.

---

## §4 — Persistence

| Artefact | Storage |
|---|---|
| Materialised python_object / python_property / python_function ConceptNodes | Kuzu `ConceptNode` table |
| OBJECT_HAS_* / FUNCTION_*_TYPE edges | Kuzu `ConceptEdge` table |
| Backing pointer version per qualified_name | [`BackingRegistry.md`](BackingRegistry.md) — versioned mapping; bumped on signature change |
| Qualified-name → concept_id map | In-memory (rebuilt on workspace open from Kuzu); not separately persisted |

---

## §5 — Peer interactions

| Peer | Interaction |
|---|---|
| [`FoundationFixtures.md`](FoundationFixtures.md) | `ensure_foundation_fixtures` calls the middleware to materialise the four fixtures |
| [`Editor.md`](Editor.md) | Uses `Editor.create` and `Editor.link` for every materialised node and edge |
| [`ConceptLifecycle.md`](ConceptLifecycle.md) | All materialiser-issued mutations route through the dispatcher with `actor="materialiser"` |
| [`BackingRegistry.md`](BackingRegistry.md) | Registers each materialised node's backing pointer + version |
| [`ConceptualCompute.md`](ConceptualCompute.md) | Compile cache invalidates on backing-pointer version bump |
| [`Agent.md`](Agent.md), [`WebBrowser.md`](WebBrowser.md), [`Database.md`](Database.md), [`Editor.md`](Editor.md) | Each fixture is a materialised tree the middleware produces |

---

## §6 — Cross-references

- Feature touchpoints — [`features/library_imports_middleware.md`](../features/library_imports_middleware.md), [`features/four_fixture_api.md`](../features/four_fixture_api.md), [`features/type_inheritance.md`](../features/type_inheritance.md).
- Code constraints — [`backend_services.md`](../code_constraints/backend_services.md) (middleware is a service-side function, not a daemon), [`lifecycle_invariants.md`](../code_constraints/lifecycle_invariants.md) (actor=`materialiser`).
- Sequence reference — DOMAIN_MODEL §17.1.1 (Editor mutation — the materialiser is one of its actors).

---

## §7 — Anti-patterns (must-not)

| Anti-pattern | Why forbidden | Guard |
|---|---|---|
| Leaving orphan trees after a re-import | §18.28 — orphan trees indicate stale state | The re-materialiser diffs and drops removed symbols via `Editor.delete` |
| Producing duplicate trees for the same qualified_name | Breaks idempotency | The middleware checks `get_materialised_qualname` before materialising |
| Skipping the `FUNCTION_INPUT_TYPE` / `FUNCTION_OUTPUT_TYPE` edges | Breaks the type ontology — autocomplete + closest-inverse depend on these edges | The walk always materialises type-target edges, recursing if needed |
| Letting walk depth exceed configurable cap | Large libraries (numpy, pandas) explode the workspace | `max_walk_depth` defaults to 4; deeper exploration is opt-in per import |
| Materialising private members (`_*` prefix) | Pollutes the workspace with implementation detail | The walker skips `_*` members by default |
| Mutating materialised nodes via the GUI | Materialised nodes are read-only (latch hidden, 🔒 indicator) | The lifecycle dispatcher refuses edits on `read_only: true` data blocks |
| Falling back to a partial materialisation on inspect failure | Silent partial trees would corrupt the type ontology | An inspect failure on a target type errors loudly; the user must fix the imports module |
