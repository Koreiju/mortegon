# Spec — Backend / Compute (Compile · LangGraph · Rollout)

> Deepens [`code_architecture/backend/compute.md`](../../code_architecture/backend/compute.md). Files: `conceptual_compute.py`, `compile_pipeline.py`, `rollout_coordinator.py`. Types: [`../types.md`](../types.md) §5. Constants: [`../constants.md`](../constants.md) §3. LangGraph = hard dependency (no fake gate).
>
> **Realized names.** The class + core methods exist as specced: `ConceptComputeNode` (conceptual_compute.py:184) with `compile(...)` (:230). A few §1/§3 algorithm-step labels are illustrative and map to differently-named realized functions: the chain builder `compile_chain` → **`compile_subgraph_to_langgraph`** (conceptual_compute.py:487); inline-cypher `exec_inline_cypher` → **`execute_cypher`** (compile_pipeline.py:110). The rollout primitives (`play`/`pause`/`step`/`advance`/`reset`, §4) live on `RolloutCoordinator` (rollout_coordinator.py), NOT this module. The W31 `compute-*` scenarios verify the dispatch table end-to-end in `full-smoke`.

---

## §1 — `ConceptComputeNode`

```python
class ConceptComputeNode:
    def __init__(self, concept_id: ConceptId, graph_editor, slm: SLMClient | None = None): ...
    def __call__(self, state: dict) -> dict          # LangGraph node: reads/writes state[concept_id]
    def compile(self) -> Rendering                    # direct path (REST/REPL/cascade)
```
- **`compile`** — resolve the node's `data` field-tree to a `Rendering`. **Idempotent** given unchanged inputs (cached on input hash; `Rendering.cached` flags a cache hit). **Raises** `CompileError` (caught upstream → `error` frame, prior rendering kept, errors.md §1).

**Algorithm (`compile`):**
```
1. tree = FieldTree.parse(node.data)                          # syntax-agnostic (cell.md mirror)
2. dispatch = classify(tree)                                  # §2
3. resolved = resolve_refs(tree, visited=set(), budget=REF_RESOLVE_MAX)   # §3
4. resolved = exec_inline_cypher(resolved)                    # §3.2
5. text = dispatch_exec(dispatch, resolved)                   # §2 table
6. children = [decompose top-level key k → child id f"{concept_id}__{k}"]   # one-level subgraph (§7.1)
7. return Rendering(text, dispatch, children, cached=False)
```
The result is written back through `apply_update_lifecycle(actor=..., change_kind=COMPILE)` by the caller (cascade or route).

---

## §2 — Dispatch classification + execution

```python
def classify(tree: FieldNode) -> DispatchKind
def dispatch_exec(kind: DispatchKind, tree: FieldNode) -> str
```
| `DispatchKind` | `classify` trigger | `dispatch_exec` |
|---|---|---|
| `PLAIN` | no `{ref}`, no prompt/schema markers | `FieldTree.print(tree)` — **no SLM** |
| `PROMPT` | free-text body with `{slug}` refs | resolve refs → `SLMClient.generate(prompt)` (agent.md) |
| `STRUCTURED` | a pydantic field-tree schema present (§O.20) | `m = build_pydantic_model_from_schema(tree)`; `SLMClient.generate(prompt, schema=m)`; templated by the Agent `template` object (§O.21) |
| `PYTHON` | a `python_entry: "module:callable"` row | `fn = BackingRegistry.resolve(...)`; `fn(**resolved_kwargs)` |

```python
def build_pydantic_model_from_schema(tree: FieldNode) -> type[BaseModel]
```
Walks the field-tree: each `key: Type = default` row → a pydantic field (`Type` from the type slot, §9.6.1); nested blocks → nested models; lists from iterable markers (§O.19). Returns a `BaseModel` subclass.

---

## §3 — Ref resolution + inline cypher

```python
def resolve_refs(tree, visited: set[ConceptId], budget: int) -> FieldNode
def exec_inline_cypher(tree) -> FieldNode
```
- **`resolve_refs`** (cycle-safe, **lazy reveal-as-it-walks** §O.9): for each `{slug}` → look up node by name; if in `visited` or `budget==0` → leave the braced marker (BraceState), don't recurse; else `visited.add`, `budget-=1`, splice the referee's `rendering`. **Iteration ⟺ external `{ref}`** to a recursively-chunked iterable (§O.19) → expand per-sample (RolloutCoordinator drives, §4). Never auto-unfolds UI fold state (§O.13).
- **`exec_inline_cypher`** — detect a cypher literal in a value → `Database.cypher(q, params)` (persistence.md) → splice rows back as a field-subtree. Invalid cypher → `CompileError`.

```python
def compile_subgraph_to_langgraph(focal_id: ConceptId, max_depth: int = COMPILE_MAX_DEPTH) -> StateGraph
def compile_chain(focal_id: ConceptId, *, use_slm: bool) -> list[Rendering]
```
- **`compile_subgraph_to_langgraph`** — BFS from `focal_id` over hard edges (depth ≤ `max_depth`), wrap each node in a `ConceptComputeNode`, add as a `StateGraph` node, wire edges from `ConceptEdge` direction (`source_port→target_port`); return the compiled graph. **`compile_chain`** invokes it and returns per-node `Rendering`s in topo order.

```python
def resolve_input_by_inverse_lookup(node_id: ConceptId, port: str) -> ChunkSampleRef | None  # §7.8.1
```
- **`resolve_input_by_inverse_lookup`** (§7.8.1) — call `ApparitionService.closest_inverse(node_id, workspace_id=workspace_id, k=k)` (retrieval.md §3.3). **Realized API note:** `closest_inverse` takes the **consuming node's id** as the inverse focal (NOT a free `type_desc`) — it ranks candidates by the inverse triple-product against that node's description+rendering signature, `exclude_self=True`. Then **filter the ranked candidates to xpath chunk-pattern samples** (`pattern_map.sampled_chunks`, scanner.md), with the input port's declared type (`port_schema`, §9.8) as a **secondary type filter** → the nearest **generalized chunk sample**. Returns `ChunkSampleRef(chunk_id, pattern_id, score)`; the cascade then drives it as a render-compile chain (§3.2) over real functional-object links (§9.6.1), not string match. **Raises** — none fatal: an unresolvable port stays a braced marker (logged, mirrors `resolve_refs`). **Pre** — `port` is an input port of `node_id`. **Post** — the single highest-inverse-score `ChunkSampleRef`, or `None` if no pattern-sample candidate survives the filter. **Complexity** — O(k) over the ranked candidates. **Idempotent** given an unchanged sample family (a §8D.39.6 backing-version bump re-fires). *(**Realized** in `backend/services/conceptual_compute.py`: `resolve_input_by_inverse_lookup` + `ChunkSampleRef` (frozen dataclass) + `_pattern_sample_index` (`chunk_id→pattern_id` over `pattern_map.sampled_chunks`, recursing `sub_patterns`). The pattern-sample membership is the authoritative filter; the `port_schema` §9.8 secondary type filter is **best-effort/lenient** — `_port_declared_type` reads an authored `inputs`/`ports`/`input_schema` type from the consuming node's data when present, else accepts. Probe: `scripts/probe_reservoir_rollout.py`.)*

---

## §4 — RolloutCoordinator (iteration driver)

```python
class RolloutCoordinator:
    def play(self, node_id: ConceptId) -> None
    def pause(self, node_id: ConceptId) -> None
    def step(self, node_id: ConceptId) -> SampleResult
    def advance(self, node_id: ConceptId) -> SampleResult
    def reset(self, node_id: ConceptId) -> None
```
- **`advance`** — pull the **next instance's content** from the memory queue (`SampleSource`: `CHUNK_3D` from the 3D env, or `HALO` from retrieval — **per-instance content, not references-only**, §O.14); set `signal_stream[f"{node}::{path}"].signal_index`; compile the node for that sample; emit `rollout_*` + `ui_state_changed`. Returns `SampleResult(sample_idx, content, source, concept_id)`.
- **`play`/`pause`** — gate the cascade so the user edits at each iteration (the play loop §8D.25); each sample boundary is an `EditDiff` (persistence.md) → range-rollback-able. Full object spec: [`../../object_model/RolloutCoordinator.md`](../../object_model/RolloutCoordinator.md).

```python
def readout_nodes(focal_id: ConceptId) -> list[ConceptId]            # §7.8.2 — the rollout perimeter
def input_nodes(focal_id: ConceptId) -> list[ConceptId]             # §7.8.1 — the source leaves
def graph_component(focal_id: ConceptId) -> list[ConceptId]         # sorted component; graph_id = [0]
def stream_readout_deltas(focal_id, *, layout_service, broadcast) -> list[Frame]  # §7.8.3
# per-readout deltas emitted sequentially in settle order, no global barrier (§7.8.3)
```
- **`readout_nodes`** (§7.8.2) — over the **`{ref}`-connected component** of `focal_id`'s graph (`{ref}`-token-based, **not** edge-based — the `{ref}` tokens are the real dependency signal, consistent with the cascade's `_find_ref_consumers`; the `cascade-reflow` scenario creates refs without edges), a node is a **readout** iff its compile has **settled** (non-empty `rendering`) **AND no other in-component node holds a forward `{ref}` to it** (the §6.6.1 terminal criterion). Returns the perimeter set; the complement is hidden state. **Recomputed every rollout** — a node that gains a downstream `{ref}` demotes readout→hidden (the §7.8.5 advancing abstraction front). **Pure read; query-invariant** (any focal of the graph → same perimeter). **Complexity** — O(N) over the component. **Realized** in `conceptual_compute.py` on a shared `_component_index` helper; siblings **`input_nodes`** (the source leaves — component nodes with no in-component forward `{ref}`, the §6.6.4 input centroid) and **`graph_component`** (the sorted component; the component-invariant `graph_id` is `[0]`).
- **Async perimeter emission** (§7.8.3) — readout deltas stream **per-node, not as one barrier batch**. **Realized** as `stream_readout_deltas` (`conceptual_compute.py`): one `compute_graph_layout` frame **per readout** in settle order, each carrying that single readout's perimeter coord + the re-placed bisector node (a fresh monotone `settle_seq` per emit, data_schemas.md §4.5) + the coordinate-free links; exposed via `POST /api/compute_graph/layout {stream:true}` (api.md / contracts.md §3). The handoff's key insight: a single-threaded **per-readout sequential emit** already satisfies "asynchronous = not barrier-synchronised" — each delta is independent and `settle_seq`-ordered, so the client re-sequences out-of-order arrivals and a fast subgraph never waits for a slow one; **full cross-thread concurrency + the auto-hook into `advance()`/the cascade are a later refinement.** Backpressure: ≤ `READOUT_DELTA_MAX_INFLIGHT` deltas/workspace, then per-node coalesce (keep-latest, a dict collapses repeated settles of one node to its latest). **Forbidden (§18.34):** a global barrier that waits for all readouts then emits one batch, or a global rollout step across subgraphs.

---

## §5 — Dependencies / Excluded
**Calls:** `SLMClient` (agent.md), `BackingRegistry` + `Database.cypher` (persistence.md), `ApparitionService.closest_inverse` (retrieval.md), `langgraph.StateGraph`, `FieldTree` parse/print (mirrors cell.md). **Called by:** CascadeScheduler (lifecycle.md), api.md compile/rollout routes. **Excluded:** the reservoir *framing / philosophy* (§7.8 prose, optimal-transport §7.8.4) — but the operational mechanics (inverse-lookup inputs §7.8.1, readout enumeration §7.8.2, async emission §7.8.3) ARE specced above; the bisector node + projector links are `layout.md` §3; the fold/expand *gesture* + render (frontend/cell.md, imaginary.md, projector.md).
