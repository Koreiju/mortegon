# Object: ConceptLifecycle (Dispatcher)

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §2.2 (one lifecycle dispatcher), §10.2 (dispatcher fan-out), §17.1.1 (Editor mutation sequence), §18 (anti-goals across actors).

**Status.** Realised — `apply_update_lifecycle` and `apply_delete_lifecycle` in `backend/services/concept_lifecycle.py` are the canonical mutation paths every actor goes through.

---

## §1 — What it is

The single mutation dispatcher. Every concept node and concept edge mutation — whether issued by the user from the GUI, by an REPL action, by an agent emitter through ActionResolver, by the scanner's chunk emission, by the python-API materialiser on workspace boot, or by a cascade re-fire — enters through `apply_update_lifecycle` or `apply_delete_lifecycle`. The dispatcher fans out to: Kuzu write → WS broadcast → ConceptIndex upsert → output-projection schedule → evolution-log diff → cascade scheduler nudge. There is no second mutation path.

The §1.5 framing places ConceptLifecycle at the heart of the **Imaginary register's operating mechanism** — it is the funnel through which every actor's mutation passes before becoming visible to peer surfaces. The Symbolic register's transparency depends on this: every mutation produces telemetry the REPL reads back; if a mutation skipped the dispatcher, the Symbolic surface would silently desync from the Imaginary.

---

## §2 — Shape

### §2.1 `apply_update_lifecycle`

```python
# Realized signature (backend/services/concept_lifecycle.py). The dispatcher
# takes the GraphEditor handle + the broadcast push_fn by dependency injection
# (the routes layer binds push_fn=_ws_push via the _apply_update_lifecycle
# wrapper). `actor` tags the EvolutionLog diff; the change_kind is derived from
# the pre/post diff, not passed. Idempotency is enforced at the ROUTE layer
# (see §3.3), NOT here.
def apply_update_lifecycle(
    node,                                # ConceptNode (or edge via apply_edge_create_lifecycle)
    ge,                                  # GraphEditor handle
    *,
    pre_dict: dict | None,               # pre-mutation snapshot (for the EvolutionLog before-image)
    embed_fields_changed: bool | None = None,  # None ⇒ auto-detect description/rendering change
    actor: str = "user:_anon",           # "user:..." | "agent:<pcid>" | "editor" | "cascade" | "materialiser" | "scanner" | "rollback"
    push_fn: Callable | None = None,     # WS broadcast hook (bound to _ws_push by the route wrapper)
    node_dict: dict | None = None,       # post-mutation wire dict (avoids a re-serialise)
    data_changed: bool | None = None,    # None ⇒ auto-detect data-field change
) -> ConceptNode:
    ...
```

### §2.2 `apply_delete_lifecycle`

```python
# Realized signature. workspace_id is read from pre_dict; the fixture-delete
# guard (§2.3 step 1) is keyed on pre_dict["backing_pointer"]. Idempotency is
# route-layer (§3.3). Returns None (the delete EditDiff is appended internally
# via log_evolution, not returned).
def apply_delete_lifecycle(
    concept_id: str,
    pre_dict: dict | None,               # pre-delete snapshot (workspace_id + backing_pointer + before-image)
    ge,                                  # GraphEditor handle
    *,
    actor: str = "user:_anon",
    push_fn: Callable | None = None,     # WS broadcast hook
) -> None:
    ...
```

### §2.3 Fan-out

Every dispatcher invocation triggers the following fan-out in order:

1. **Foundation-fixture guard** (only `apply_delete_lifecycle`) — reject deletes targeting any concept whose `backing_pointer` (or `concept_id`) starts with `fixture::`. Returns early WITHOUT running any fan-out step (no index removal, no EvolutionLog diff, no broadcast) and logs the rejection. This guard lives in the dispatcher (not only at the HTTP route) so every caller — agent emitter, editor primitive, DELETE route — is covered by one check (lifecycle_invariants §1.6 / §2.4).
2. **Idempotency** — enforced at the ROUTE layer BEFORE the dispatcher is invoked: each mutation route does `_idempotency_lookup` / `_idempotency_store` (5-min TTL, per `(workspace_id, target, key)`) and returns the cached response without re-calling the dispatcher. The dispatcher itself holds no idempotency cache (§3.3).
3. **Kuzu write** — atomic insert/update/delete in the appropriate table.
4. **EvolutionLog append** — record the diff with `actor`, `target`, `action`, `before`, `after`, `idempotency_key`, `created_at`.
5. **WS broadcast** — `concept_changed` frame to the workspace WS carrying `(concept_id, change_kind, new_state)`. For edges, both source and target receive the broadcast.
6. **ConceptIndex upsert** — for node modifies that touched `description`, re-embed via nomic; for modifies that touched `rendering`, re-vectorise TF-IDF across all five frequency bands.
7. **Multi-frequency aggregation refit** — when the workspace has accumulated K observed-utility events, schedule the per-band weight refit (debounced; settled state emits `concept_index_update`).
8. **Output-projection schedule** — `schedule_output_projection(workspace_id, ge)` runs UNCONDITIONALLY (debounced), not gated on provenance here. The LayoutService's `output_projection` then selects the peripheral nodes (those with a non-trivial `rendering`) and maps each one's ConceptNode provenance to a *projector* provenance: `agent-authored → agent-output` (→ perimeter-encompassing rescale, §6.6.1), everything else → `graph-output` (interior). The perimeter gating lives in `output_projection` / `LayoutService`, not in this dispatcher.
9. **Cascade scheduler nudge** — unless `skip_cascade` is true, enqueue downstream cards (cards referencing this concept via `{var}` in their description/data) for re-compile with debounce ~800 ms. The cascade scheduler's actor-aware short-circuit prevents an agent's emission from re-triggering its own perception in the same tick (§2.7).
10. **Return** the `EditDiff`.

---

## §3 — Lifecycle invariants

### §3.1 Single-dispatcher rule

Every mutation goes through one of the two functions. Direct Kuzu writes from anywhere else in the codebase are forbidden. Code reviews flag direct `kuzu_connection.execute(...)` calls outside `concept_lifecycle.py` and `graph_editor.py` internals.

### §3.2 Atomicity

The Kuzu write + EvolutionLog append happen in a single transaction. The WS broadcast happens *after* the transaction commits, so peer surfaces never see a state the persistence layer hasn't yet committed. The cascade scheduler nudge happens *last*, so downstream cards never compile against pre-commit state.

### §3.3 Idempotency

The `idempotency_key` is optional but every mutation route in `routes.py` accepts one. Replays during a flaky REPL run or a network retry produce the same effect once. The idempotency cache is at the **route layer** (`_idempotency_lookup` / `_idempotency_store` in `routes.py`), per `(workspace_id, target, key)`, 5-minute TTL — the route returns the cached response without re-invoking the dispatcher. The dispatcher itself is idempotency-agnostic (it has no such cache); keeping dedup at the route keeps the dispatcher a pure fan-out.

### §3.4 Actor-aware cascade

The cascade scheduler tags each enqueued re-compile with the originating `actor`. When the re-compile fires, if the originating actor's perception is currently active (the agent body subgraph is mid-tick for the same `pcid`), the re-compile is short-circuited. This prevents the loop: agent emits → cascade re-fires → agent perception re-reads its own emission → re-tick → infinite recursion.

### §3.5 No fan-out skipping

The fan-out is monolithic — every step runs on every mutation, even if some steps are no-ops for the specific change kind (e.g., a `rendering`-only modify still triggers a `concept_changed` broadcast and an EvolutionLog append, even though `description` didn't change and nomic re-embedding is skipped). The uniformity is what makes the Symbolic register's telemetry stream complete.

---

## §4 — Persistence

The dispatcher's outputs are persisted by the downstream steps:

| Output | Persistence |
|---|---|
| Kuzu ConceptNode / ConceptEdge row | Kuzu |
| EvolutionLog EditDiff | Kuzu `EditDiff` table (append-only) |
| ConceptIndex nomic + TF-IDF vectors | ConceptIndexService in-memory + per-workspace persisted file |
| Idempotency-key → prior EditDiff mapping | In-memory cache (5-min TTL); not persisted |
| Cascade scheduler queue | In-memory (resets on backend restart; cards that should re-compile after restart are re-discovered via lazy compile on next view) |

The dispatcher itself is stateless beyond the idempotency cache.

---

## §5 — Peer interactions

| Peer | Interaction |
|---|---|
| [`ConceptNode.md`](ConceptNode.md) | The records the dispatcher mutates |
| [`ConceptEdge.md`](ConceptEdge.md) | The link records the dispatcher mutates |
| [`Editor.md`](Editor.md) | The user-facing wrapper for the four primitives that call into the dispatcher |
| [`AgentRuntime.md`](AgentRuntime.md) | The agent emitter calls Editor primitives → dispatcher |
| [`PythonAPIMaterialiser.md`](PythonAPIMaterialiser.md) | Calls Editor.create for each materialised python_object/property/function |
| [`WebBrowser.md`](WebBrowser.md) | Scanner calls Editor.create for each emitted chunk |
| [`EvolutionLog.md`](EvolutionLog.md) | Receives the EditDiff append on every mutation |
| [`ConceptIndexService.md`](ConceptIndexService.md) | Receives the upsert on every node modify |
| [`LayoutService.md`](LayoutService.md) | Receives the projection schedule on `agent-output` provenance |
| [`UIStateService.md`](UIStateService.md) | Receives the `concept_changed` broadcast hook for mirror updates |
| [`RolloutCoordinator.md`](RolloutCoordinator.md) | Cascade-driven re-compile on signal advance routes through the dispatcher |

---

## §6 — Cross-references

- Feature touchpoints — virtually every feature in [`features/`](../features/) — the dispatcher is the funnel.
- Code constraints — [`lifecycle_invariants.md`](../code_constraints/lifecycle_invariants.md) carries the full must-hold/must-not catalogue.
- Sequence reference — DOMAIN_MODEL §17.1.1 (Editor mutation), §17.4 (cascade), §17.5 (agent tick), §17.10 (purge), §17.11 (rollback).

---

## §7 — Anti-patterns (must-not)

| Anti-pattern | Why forbidden | Guard |
|---|---|---|
| Direct Kuzu writes bypassing the dispatcher | Breaks WS broadcast + EvolutionLog + cascade — the Symbolic register desyncs from the Imaginary | Grep for `kuzu_connection.execute` outside the dispatcher; code review |
| Skipping the fan-out for "trivial" changes | Uniformity is what makes the telemetry complete; "trivial" is in the eye of the beholder | The dispatcher always runs the full fan-out; specific steps may be no-ops but the chain never short-circuits |
| Reading from Kuzu without checking the cascade scheduler is settled | A read mid-cascade may see stale rendering values | The cascade scheduler exposes `wait_settled(timeout)` for callers that need post-cascade consistency |
| Letting an EditDiff record fail to append while the Kuzu write succeeds | Rollback over the orphan mutation becomes impossible | The two are in one transaction; if either fails, both roll back |
| Letting an agent emitter re-trigger its own perception | §18.10 (and the §12 integration scheme convergence) | Actor-aware short-circuit in the cascade scheduler |
| Calling `apply_delete_lifecycle` on a foundation fixture | §18.22, §18.27 — fixtures must remain present | Guard returns `action="rejected"` without mutating |
| Coalescing many mutations into one EditDiff without preserving per-mutation atomic rollback granularity | Granular rollback is the design's conflict-resolution tool (§2.6) | `bulk_create` / `bulk_link` Editor primitives produce one EditDiff per atomic primitive call, not one diff for the whole batch |
