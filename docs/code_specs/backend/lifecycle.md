# Spec — Backend / Lifecycle Dispatcher + Cascade

> Deepens [`code_architecture/backend/lifecycle.md`](../../code_architecture/backend/lifecycle.md). File: `concept_lifecycle.py`. Types: [`../types.md`](../types.md). Constants: [`../constants.md`](../constants.md) §3/§7. Errors: [`../errors.md`](../errors.md). The **one mutation funnel** — no second path (assertion, errors.md §3).

---

## §1 — `apply_update_lifecycle`

```python
# Realized signature (concept_lifecycle.py). The GraphEditor handle + the
# broadcast push_fn are injected by the routes layer (the _apply_update_lifecycle
# wrapper binds push_fn=_ws_push). change_kind is DERIVED from the pre/post diff,
# not passed; workspace_id is read from node/pre_dict; idempotency is enforced at
# the ROUTE layer (§1.idempotency), NOT a param here.
def apply_update_lifecycle(
    node: ConceptNode, ge: GraphEditor, *, pre_dict: dict | None,
    embed_fields_changed: bool | None = None, actor: str = "user:_anon",
    push_fn: Callable | None = None, node_dict: dict | None = None,
    data_changed: bool | None = None,
) -> ConceptNode
```
- **Does** — persist + log + index + project + broadcast + cascade one node create/modify, in that fixed order.
- **Params** — `actor` is `Actor` or `f"agent:{id}"`; `pre_dict` is the pre-mutation snapshot (the EvolutionLog before-image); `embed_fields_changed`/`data_changed` default `None` ⇒ auto-detect from the pre/post diff.
- **Returns** — the updated `ConceptNode` (the `EditDiff` is appended internally via the EvolutionLog, not returned).
- **Raises** — `SubsystemDownError` (→503, halts cascade) if step 5/6 hits a dead subsystem; `BackingResolveError` if a referenced backing is stale (logged, dependent compile skipped, not fatal here).
- **Pre** — `node.workspace_id == workspace_id`; `node.concept_id` set (caller assigns uuid on create).
- **Post** — exactly **one** `concept_changed` broadcast; exactly **one** `EditDiff` appended; ConceptIndex reflects the new description/rendering; if a replay was deduped at the route layer, the dispatcher is **not** invoked at all (zero of the above).
- **Idempotent** — yes, but enforced at the **route layer** (`_idempotency_lookup`/`_idempotency_store`, per `(workspace_id, target, key)`, within `IDEMPOTENCY_WINDOW`), NOT inside this dispatcher.
- **Complexity** — O(1) write + O(out-degree) cascade marking (deferred, debounced).

**Algorithm (the fan-out — order is load-bearing):**
```
0. (idempotency is enforced at the ROUTE layer BEFORE this is called: the route
    does _idempotency_lookup/_idempotency_store and returns the cached response
    without re-invoking the dispatcher — the dispatcher holds no idempotency cache)
1. (delete-only fixture guard skipped here; this is update)
2. before = pre_dict (passed in);  Kuzu.upsert_node(node)        # atomic
3. diff = EditDiff(before, after=node, actor, target=concept_id, action=<derived>); EvolutionLog.append(diff)
4. ConceptIndexService.upsert(node)            # re-embed: description→nomic, rendering→tfidf  (raises SubsystemDownError if embedder dead)
5. LayoutService.schedule_output_projection(workspace_id, ge)   # UNCONDITIONAL (debounced); output_projection
                                                                # selects peripherals + maps agent-authored→agent-output (§9.12)
6. broadcaster.emit(ConceptChangedFrame(concept_id, <derived change_kind>, node))
7. CascadeScheduler.nudge(node, actor)         # (cascade re-fires pass actor="cascade")
8. return node
```
A failure before step 2 raises with no partial state; steps 2–3 are one Kuzu transaction.

**Example** — user renames a card: `apply_update_lifecycle(node{name:"X"→"Y"}, actor="user", change_kind=RENAME, ws, key)` → propagates `{X}`→`{Y}` in referrers via the cascade (step 8 marks every node whose `data` contains `{X}`).

---

## §2 — `apply_delete_lifecycle`

```python
# Realized signature (concept_lifecycle.py). workspace_id is read from pre_dict;
# the actual Kuzu delete happens in the caller (ge.delete_concept) BEFORE this is
# invoked, so the fixture guard here keys on pre_dict's backing_pointer/concept_id
# and returns EARLY (no fan-out) rather than appending a rejected diff. Returns None.
def apply_delete_lifecycle(
    concept_id: ConceptId, pre_dict: dict | None, ge: GraphEditor, *,
    actor: str = "user:_anon", push_fn: Callable | None = None,
) -> None
```
- **Fixture guard** — for a `fixture::` `backing_pointer`/`concept_id`, returns early with NO fan-out (no index removal, no EvolutionLog diff, no broadcast) + logs the §1.6 rejection. This lives in the dispatcher so every caller (agent emitter, editor primitive, DELETE route) is covered by one check (lifecycle_invariants §1.6/§2.4). `graph_editor.delete_concept` independently refuses the Kuzu drop (defense in depth). Read-only python-native deletes are surfaced as `ok:false` by the editor route / `ReadOnlyEditError` by the edit route.
- **Idempotency** — route-layer (as §1), not here.
- **Algorithm (realized order — note: the caller already ran `ge.delete_concept`):**
```
0. (route layer: pre_dict = snapshot; ge.delete_concept(concept_id) — guarded; then calls this)
1. FixtureGuard: if (pre_dict.backing_pointer | concept_id).startswith("fixture::"): log + return   # NO fan-out
2. if agent parameter card: CascadeScheduler.cleanup_for_agent(concept_id)
3. ConceptIndexService.remove(concept_id)
4. EvolutionLog.append(EditDiff(before=pre_dict, after=None, action=DELETE, actor))
5. broadcaster.emit(ConceptChangedFrame(concept_id, change="deleted", node=None))
6. LayoutService.schedule_output_projection(workspace_id, ge)   # referrers' {ref} now dangle → re-render to braced marker
```
- **Post** — a deleted node's referrers re-render their `{ref}` as the unresolved braced marker (BraceState.HIDDEN), not an error (compute.md). Deleting an agent's **parameter card** terminates that agent (agent.md).

---

## §3 — `CascadeScheduler`

There are TWO realized cascade paths (§8D.38.4 "Cascade is the default"):

**(a) The general `{ref}`-consumer cascade** (`concept_lifecycle.py`, REALIZED). On any DATA edit (`effective_data_changed`, actor ∉ {`conceptual_compute`, `cascade*`}), `apply_update_lifecycle` calls `_cascade_recompile_consumers(node, ge)`: a BFS that finds downstream cards whose `data`/`description` reference the edited card via a `{slug}` (`_find_ref_consumers`, matched the way `resolve_concept_refs` resolves — by `concept_id` or slugified `name`) and recompiles each via `ConceptComputeNode(...).compile()`. Cycle-safe (visited-set) + depth-capped (`_CASCADE_MAX_DEPTH`=16); the nested compile-persists run as actor=`conceptual_compute` which is excluded from re-entering the cascade, so the BFS is the sole authority (no recompile storm). Verified by `cascade-reflow-roundtrip` (edit source → consumer auto-recomputes with no explicit compile; single-hop **and** 2-hop transitive `A ← B ← C`) and `cascade-cycle-safety` (a mutual `{ref}` cycle `A↔B` terminates fast + returns 200, proving the visited-set/depth-cap guard against an infinite recompile loop) — both in `full-smoke`. The recompile is **synchronous within the edit request** (not debounced); the per-edit storm guard is the visited-set + the `conceptual_compute`/`cascade*` actor-exclusion, not a timer. The debounced/rate-capped variant remains the **historical** design below (superseded — applies only to the agent tick path (b)).

**(b) The agent meta-cognition tick** (`agent_runtime.py::CascadeScheduler`, REALIZED). Schedules/fires debounced agent ticks for agent body cards with rate-limiting + the actor-aware self-loop guard:

```python
class CascadeScheduler:
    def schedule_for_card(self, node, ge, *, push_fn=None, actor: str = "") -> None  # arm a debounced agent tick
    def record_spawns(self, pcid: str, applied: int, rate_limited: int) -> None
    def status(self, pcid: str = "") -> dict          # per-agent fires/skips → GET /api/agent/cascade_status
    def cleanup_for_agent(self, pcid: str) -> None     # drop bookkeeping when a parameter card is deleted
    # internal: _arm (debounce CASCADE_DEBOUNCE_MS), _fire (run the tick), _under_rate_limit
```
- **algorithm:**
```
(a) general cascade (realized, concept_lifecycle._cascade_recompile_consumers):
          BFS dirty = { n : n.data/description contains a {ref} resolving to the edited card };
          recompile each (visited-set + depth ≤ _CASCADE_MAX_DEPTH); compile-persists don't re-enter.
(b) agent tick (realized): if node is an agent parameter/perception/transformer/emitter card → _arm a
          debounced tick for its pcid (rate-limited; actor-aware self-loop guard in _fire).
historical note — the original single algorithm: mark dirty = { n : n.data contains an unresolved {ref}
          to node.name }; debounce CASCADE_DEBOUNCE_MS; drain depth ≤ CASCADE_MAX_DEPTH:
     if actor.startswith("agent:") and last_writer(n) == actor:  status[actor].skips += 1; continue   # self-loop guard
     r = compile(n)                                  # compute.md (recomputes value; never auto-unfolds, §O.13)
     apply_update_lifecycle(n_with_rendering=r, actor="cascade", change_kind=COMPILE, ws, skip_cascade=guarded)
     status["cascade"].fires += 1
```
- **Invariant** — the agent self-loop guard prevents an agent re-triggering itself but does **not** serialise across actors (last-write-wins, §2.7). `halt()` (subsystem down) stops the drain; in-flight gestures get `error` frames.
- **Iteration ⟺ external `{ref}`** (§O.19): cascade fans into a recursively-chunked iterable only via an external curly-brace ref; internal aggregate nesting does not iterate.

---

## §4 — Dependencies / Excluded
**Calls:** Kuzu + EvolutionLog (persistence.md), ConceptIndexService (retrieval.md), LayoutService (layout.md), compile (compute.md), broadcaster (api.md). **Called by:** every mutation route. **Excluded:** the "continuous compilation" register framing.
