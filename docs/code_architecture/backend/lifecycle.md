# Backend — Lifecycle Dispatcher + Cascade Scheduler

> **Owns:** the single mutation funnel + the downstream recompute cascade — **two realized paths**: the **synchronous** `{ref}`-consumer recompile (`concept_lifecycle.py`) and the **debounced** agent-tick scheduler (`agent_runtime.py::CascadeScheduler`). Files: `concept_lifecycle.py`, `agent_runtime.py`. Design: §10.2 / §7.4 / §10.6. Realises `code_constraints/lifecycle_invariants.md`, `concurrency.md`.

---

## §1 — Responsibility

**Every** mutation — from any actor (user, agent, cascade, scanner, editor, materialiser, rollback) — goes through one funnel. There is **no second mutation path** (§10.2). The cascade keeps renderings continuous downstream of edits (§7.4 / §8D.38.4 — cascade is the default; the Compile button is a forced-sync affordance, not the primary trigger). It is realized as **two paths**: (a) a **synchronous** `{ref}`-consumer recompile that runs inside the edit's own `apply_update_lifecycle` (cycle-safe via visited-set + depth cap — no timer), and (b) the **debounced** agent-tick `CascadeScheduler` for agent body cards. The ~800ms debounce applies to path (b) only.

---

## §2 — Public Surface

```python
def apply_update_lifecycle(node: ConceptNode, *, actor: str, change_kind: str,
                           workspace_id: str, idempotency_key: str | None = None,
                           skip_cascade: bool = False) -> EditDiff
def apply_delete_lifecycle(node_id: str, *, actor: str, workspace_id: str,
                           idempotency_key: str | None = None,
                           cascade_remove_edges: bool = True) -> EditDiff

# path (a) — synchronous {ref}-consumer recompile (internal to concept_lifecycle.py):
def _cascade_recompile_consumers(node: ConceptNode, ge) -> None  # BFS, visited-set + depth cap, runs inline

class CascadeScheduler:                                          # path (b) — debounced AGENT tick (agent_runtime.py)
    def schedule_for_card(self, node, ge, *, actor: str) -> None # arm a debounced tick for an agent body card
    def status(self, pcid: str = "") -> dict                     # GET /api/agent/cascade_status
```

---

## §3 — Internal Logic

### §3.1 The fan-out (ordered; the one contract, `contracts.md` §5)
```
apply_update_lifecycle(node, actor, change_kind, ws, key):
  1. fixture guard (delete only): backing_pointer.startswith("fixture::") → EditDiff(action="rejected"); return
  2. idempotency: if key seen < 5min for ws → return the stored prior EditDiff (NO re-apply)
  3. Kuzu write: atomic upsert (or delete + edge sweep if cascade_remove_edges)
  4. EvolutionLog.append(EditDiff(before, after, actor, target, action, key))     # persistence.md
  5. ConceptIndexService.upsert(node)         # re-embed description→nomic, rendering→tfidf   # retrieval.md
  6. LayoutService.schedule_output_projection(node)  if provenance ∈ {scanner-emitted, agent-output}  # §9.12
  7. broadcast WS concept_changed {concept_id, change_kind, node}
  8. cascade (see §3.2): _cascade_recompile_consumers(node)  if data changed & actor ∉ {conceptual_compute, cascade*}   # path (a), synchronous
        + CascadeScheduler.schedule_for_card(node, actor)    if node is an agent body card                              # path (b), debounced
  return EditDiff
```
The order is load-bearing: persist → log → index → project → notify → cascade. A failure before step 3 raises (no partial); a subsystem failure inside 5/6 surfaces as 503 + halts the cascade (`subsystems.md` §2).

### §3.2 The cascade — two paths (actor-aware short-circuit, §7.4)

**(a) `{ref}`-consumer recompile — SYNCHRONOUS** (`_cascade_recompile_consumers`, inside `apply_update_lifecycle`; fires when `data` changed & actor ∉ {`conceptual_compute`, `cascade*`}):
```
BFS from edited node (visited-set + depth ≤ _CASCADE_MAX_DEPTH = 16):
  dirty = nodes whose data/description carry a {ref} resolving to `cur`   # by concept_id or slugified name
  for consumer in dirty, if consumer not visited:
    visited.add(consumer);  recompile via ConceptComputeNode(consumer).compile()   # persists actor="conceptual_compute"
    enqueue consumer at depth+1                                                     # → excluded from re-entry, no storm
```
No timer — the recompile completes inside the editing request. The visited-set + the `conceptual_compute`/`cascade*` actor-exclusion ARE the storm guard (the BFS is the sole authority for the transitive walk).

**(b) Agent-tick — DEBOUNCED** (`CascadeScheduler.schedule_for_card`; only for agent body cards):
```
if node is an agent parameter/perception/transformer/emitter card:
  if actor == f"agent:{pcid}":  skip                    # self-loop guard — the agent's own writeback
  if paused | !cascade_enabled | over per-minute rate cap:  skip
  _arm(pcid): debounce ~CASCADE_DEBOUNCE_MS → _fire → one MetaCognitionTick (re-checks paused at fire)
```
- Both self-loop guards prevent an **agent re-triggering itself** but do **not** serialise across actors (§7.4) — two actors editing concurrently is last-write-wins (optimistic, §2.7).
- **Iteration ⟺ external `{ref}`** (§O.19): the cascade only fans into a recursively-chunked iterable when a node *externally* references it by curly-brace; internal aggregate structure does not trigger per-sample iteration.
- The cascade **recomputes values but never auto-unfolds** a collapsed node (§O.13) — fold state is UI, owned by the frontend mirror.

---

## §4 — Dependencies

- **Calls:** Kuzu (persistence.md), EvolutionLog, ConceptIndexService (retrieval.md), LayoutService (layout.md), compile (compute.md), WS broadcaster.
- **Called by:** every REST mutation route (`contracts.md` §2) — pin/edit/compile/wire/scan-emit/agent-emit/rollout/rollback all resolve here.

---

## §5 — Excluded

- The register meaning of "continuous compilation"; the alchemical framing of cascade. Only the fan-out order + the short-circuit rule are encoded.
