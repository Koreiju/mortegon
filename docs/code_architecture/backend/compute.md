# Backend — Compute (Compile · LangGraph · Rollout)

> **Owns:** the `ConceptComputeNode` LangGraph primitive, the recursive syntax-agnostic compile, and the iterated-rollout driver. Files: `conceptual_compute.py`, `compile_pipeline.py`, `rollout_coordinator.py`. Design: §7.1 / §7.2 / §7.7 / §O.9 / §O.13 / §O.19 / §O.20 / §O.21. Realises `code_constraints/compile.md`. LangGraph is a hard no-mocks dependency (`subsystems.md`).

---

## §1 — Responsibility

Compile a ConceptNode's `data` field-tree into its `rendering` — **one syntax-agnostic recursive descent** (the data block dissolved into a field-tree; §7.1). Build the LangGraph `StateGraph` for a multi-node compute subgraph. Drive iteration over sampled chunks (the RolloutCoordinator). Compilation is **continuous** (cascade-driven, lifecycle.md §3.2); the Compile button is a forced sync.

---

## §2 — Public Surface

```python
class ConceptComputeNode:                       # binds concept_id + graph_editor + slm_client?
    def __call__(self, state: dict) -> dict     # LangGraph (state)->state node
    def compile(self) -> Rendering              # direct REPL/REST path

def compile_subgraph_to_langgraph(focal_id: str, max_depth: int = 4) -> StateGraph
def compile_chain(focal_id: str, *, use_slm: bool) -> list[Rendering]    # POST /api/conceptual/compile_chain

# rollout_coordinator.py  (full spec: ../../object_model/RolloutCoordinator.md)
class RolloutCoordinator:
    def play(node_id) -> None; def pause(node_id) -> None; def step(node_id) -> None
    def advance(node_id) -> SampleResult        # next instance from the memory queue
    def reset(node_id) -> None

# §7.8 reservoir rollout — operational mechanics (the FRAMING stays design-only, §5)
def resolve_input_by_inverse_lookup(node_id: str, port: str) -> ChunkSampleRef  # §7.8.1 typed input ← closest-inverse over chunk-pattern samples
def readout_nodes(focal_id: str) -> list[str]                                   # §7.8.2 perimeter = settled nodes with NO forward {ref}
# RolloutCoordinator emits readout deltas ASYNC (no global barrier, §7.8.3) — see agent.md / RolloutCoordinator.md
```

---

## §3 — Internal Logic

### §3.1 Dispatch kinds (auto-classified from the data block, §7.2)
| Kind | Trigger | Action |
|---|---|---|
| `plain` | no `{ref}`, no prompt markers | tree-print only; **no SLM** |
| `prompt` | free-text with `{slug}` refs | resolve refs → `SLMClient.generate` (agent.md) |
| `structured` | a pydantic field-tree schema (§O.20) | `build_pydantic_model_from_schema` → templated by the Agent `template` object (§O.21) → SLM structured output |
| `python` | `python_entry: module:callable` | resolve via `BackingRegistry`; invoke with resolved kwargs |

### §3.2 The compile descent (§7.1 / §O.9)
```
compile(node):
  resolve {var} references (cycle-safe; visited set)            # pulls referenced nodes' renderings
  detect + execute inline cypher → Database.cypher(...)         # inline-cypher rewrite (scanner.md/persistence.md)
  decompose top-level keys into child nodes <card_id>__<key>    # the simplified one-level subgraph (§7.1)
  print the resolved field-tree → rendering
  write back through apply_update_lifecycle(actor=..., skip_cascade=depth-guarded)   # lifecycle.md
```
- **Lazy reveal-as-it-walks** (§O.9): the descent follows `{ref}`s **on demand**; the cascade recomputes values but **never auto-unfolds** a collapsed node (§O.13 — fold is UI state).
- **Iteration ⟺ external `{ref}`** to a recursively-chunked iterable (§O.19): a `{ref}` into an iterable rooted at a base node drives per-sample compilation; internal aggregate nesting does not.

### §3.3 Closest-inverse at the output port (§7.7)
When a compiled node's output type needs a consumer, `ApparitionService.closest_inverse(output_type_desc)` (retrieval.md) returns the nearest type-compatible node — the inverse-lookup that lets compute graphs auto-suggest their downstream.

### §3.4 Rollout (the iteration driver, `object_model/RolloutCoordinator.md`)
`advance()` pulls the **next instance's content** from a memory queue (sourced from the 3D environment OR halo retrieval — **per-instance content, not references-only**, §O.14); `play/pause` gates the cascade so the user can edit at each iteration (the play loop §8D.25). Sample boundaries are recorded as `EditDiff`s (persistence.md) for diff-consistent rollback. The `signal_stream` UIState slot (`data_schemas.md` §4.4) mirrors the current sample index.

### §3.5 Reservoir rollout — inverse-lookup inputs · readout perimeter · async emission (§7.8.1–§7.8.3)

The cascade (§3.2; lifecycle.md §3.2) extended end-to-end into a **full rollout**. Three mechanics (the §7.8 *framing* stays design-only, §5 — these are the operational hooks):

- **Input assembly by inverse lookup (§7.8.1).** `resolve_input_by_inverse_lookup(node_id, port)` runs `ApparitionService.closest_inverse(node_id)` (§3.3 — the realized API takes the consuming **node's id** as the inverse focal, not a free type string) and **filters the ranked candidates to xpath chunk-pattern samples** (`scanner.md` `pattern_map` / `sampled_chunks`), with the input port's declared type (§9.8) as a secondary filter — the inverse of the forward compile. It returns the **generalized chunk sample(s)** that satisfy the input; the cascade then drives them through as render-compile chains over **real functional-object links** (§9.6.1), not string matches. This is the §3.3 closest-inverse read on the **input** side (the output side already auto-suggests downstream).
- **Readout-perimeter enumeration (§7.8.2).** `readout_nodes(focal_id)` returns the rollout's **terminal** nodes: a node is a readout iff its compile has **settled** AND **no other in-graph node carries a forward `{ref}` to it** (the §6.6.1 terminal criterion, computed over the live edge set). The complement is the **hidden state**. The set is **recomputed every rollout** — so the abstraction front advances as the graph grows (§7.8.5); a node that gains a downstream `{ref}` silently demotes from readout to hidden state.
- **Async emission (§7.8.3).** When a readout's per-sample value settles it emits **immediately** through the existing output-projection path (lifecycle §3.1 step 6 → `layout.md`) as a **per-node** `chunk_replaced` / `chunk_added` delta — **never a barrier-synchronised batch** (§18.34). Subgraphs with **differing rollout path lengths** (and recurrent maps back to hidden state) settle at different times; the coordinator emits in **settle order with no global step barrier** across subgraphs. Backpressure: at most `READOUT_DELTA_MAX_INFLIGHT` un-acked deltas per workspace (constants.md); excess **coalesce per node** (keep latest), mirroring the scan-streaming sched (`streaming.md`). The bisector node + projector links re-place on each delta (`layout.md` §3.1).

---

## §4 — Dependencies

- **Calls:** `SLMClient` (agent.md), `BackingRegistry` (python_entry, persistence.md), `Database.cypher` (persistence.md), `ApparitionService.closest_inverse` (retrieval.md), `langgraph.graph.StateGraph`.
- **Called by:** the cascade scheduler (lifecycle.md §3.2), `POST /api/conceptual/compile*`, `POST /api/rollout/*`, the editor's right-click/double-left compile gestures (`contracts.md` §2.2/§2.3).

---

## §5 — Excluded

- The reservoir-computing **framing / philosophy** (§7.8 prose, optimal-transport reading §7.8.4) stays design-only; **§3.5 encodes the operational rollout mechanics** (inverse-lookup inputs §7.8.1, readout-perimeter enumeration §7.8.2, async emission §7.8.3). The bisector compute-graph **node placement + projector link network** (§6.6.4) is LayoutService's (`layout.md` §3.1), not here. The fold/expand *gesture* + rendering is frontend (`frontend/cell.md`, `frontend/imaginary.md`, `frontend/projector.md`).
