# Spec — Backend / Persistence (Kuzu · Evolution Log · Backing Registry · UI Mirror)

> Deepens [`code_architecture/backend/persistence.md`](../../code_architecture/backend/persistence.md). Files: `evolution_log.py`, `backing_registry.py`, `ui_state_service.py`, Kuzu/cypher layer. Types: [`../types.md`](../types.md) §3/§6. Constants: [`../constants.md`](../constants.md) §7. Kuzu = no-mocks boundary.

---

## §1 — Kuzu / cypher layer

```python
def upsert_node(node: ConceptNode) -> None; def get(concept_id: ConceptId) -> ConceptNode | None
def delete_node(concept_id: ConceptId) -> None; def delete_edges_touching(concept_id: ConceptId) -> int
def upsert_edge(edge: ConceptEdge) -> None
def cypher(query: str, params: dict) -> list[Row]
```
- **`cypher`** — execute against Kuzu (inline-cypher from compile, compute.md §3); parameterised; invalid query raises → `CompileError`. Read or write per query. Single edge table (assertion: never a second, errors.md §3).
- All writes are transactional; `upsert_node`+`EvolutionLog.append` in lifecycle.md form one transaction.

---

## §2 — `EvolutionLog` (append-only)

```python
# Realized names (evolution_log.py). `append` is the module fn `log_evolution(...)`
# that the lifecycle calls; the three rollback scopes + the list + the inverse
# engine are methods on the EvolutionLog. The route params are edit_id_low/high
# (range) and actor + `since` (actor scope) — verified by the `evolution-rollback`
# scenario (single + range + actor, §11.4).
def list_diffs(self, *, workspace_id="", actor=None, target_prefix=None, limit=200) -> list[dict]   # the "history" read
def rollback_single(self, edit_id: int, workspace_id="") -> dict                                     # scope 1
def rollback_range(self, edit_id_low: int, edit_id_high: int, workspace_id="") -> dict               # scope 2
def rollback_actor_since(self, actor: str, since: float, workspace_id="") -> dict                    # scope 3 (+ `since` cutoff)
def _apply_reverse(self, diff: EditDiff, workspace_id: str) -> Optional[dict]                        # the inverse engine
# append: `log_evolution(target, kind, before, after, workspace_id, ge, actor, push_fn)` (module fn)
```
- **`append` (`log_evolution`)** — store immutable; monotone by `edit_id`/`created_at`. Never mutates/deletes prior diffs.
- **`rollback_single`** — `_apply_reverse` computes the inverse of `diff` (swap `before`/`after`), applies it via `apply_update_lifecycle`/`apply_delete_lifecycle` with `actor=rollback`, and **appends the rollback as a new diff** (history never shrinks, §2.6). **`rollback_range`** — inverse-apply `edit_id_high..edit_id_low` in reverse order. **`rollback_actor_since`** — inverse every diff by `actor` with `timestamp >= since` (e.g. undo an agent's session since a cutoff). `_apply_reverse` carries a `rollout:` branch so RolloutCoordinator sample boundaries are rollback-able (re-seats the signal-stream cursor, compute.md §4 / §3.3).
- **Post** — a rollback is itself in the log (re-rollback-able).

---

## §3 — `BackingRegistry`

```python
def register(self, backing: Backing, handle: Any) -> None
def resolve(self, backing: Backing) -> Any                  # raises BackingResolveError if absent
def bump_version(self, backing: Backing) -> int
def version(self, backing: Backing) -> int
```
- **`resolve`** — dispatch on the `Backing` prefix (types.md §3) → live handle. Stale → `BackingResolveError` (500; dependent compile skipped+logged, errors.md §1).
- **`bump_version`** — increment a per-pointer seq; the cascade treats every node referencing that backing as dirty (lifecycle.md) → recompiles. Used by materialiser (`backing_version_bump`) + scanner (re-scan). Returns the new seq.

---

## §4 — `UIStateService` (the mirror)

```python
# Realized names (ui_state_service.py). The snapshot is `to_dict()` (the wire
# dict) / `_snapshot_locked(workspace_id)` (the under-lock deep copy); each setter
# returns the new UIState and emits via `_emit(kind, ...)`. The telemetry merge
# lives on the SEPARATE ui_telemetry_service as `drain(...)`, not here.
def _snapshot_locked(self, workspace_id: str) -> UIState; def to_dict(self) -> dict
def set_<field>(self, workspace_id: str, ...) -> UIState       # ONE per UIState field (types.md §6)
# ui_telemetry_service.drain(...)  — merges batched frontend snapshots
```
- **Each `set_<field>`** — idempotent; mutates exactly that field; **broadcasts the full `ui_state_changed` frame on every call** via `_emit(kind, …)` with `last_change_kind=<kind>` (so peer tabs + REPL re-sync, §10.5; the kind set must be a subset of ws_frames.md §1.5). Realized setters: `set_pin_chrome`, `set_node_fold(card_id, field_path, expanded)`, `set_signal_stream(card_id, field_path, …)` / `advance_signal`, `set_url_collapsed(url, collapsed)` (the eye/domain toggle), `set_viewport_spine(ordered, total)`, `set_latch`, `set_halo_focus`, `set_rollout_state`, …
- **Telemetry merge (`ui_telemetry_service.drain`)** — field-merge batched frontend snapshots (pin chrome, fold state, viewport rows, signal stream) from `POST /api/ui/telemetry`; one broadcast after the batch.
- The mirror is the source for `?resume` replay (api.md §4) and the REPL `watch-activity` dashboard (repl.md).

---

## §5 — Persistence map + purge

| Artefact | Store |
|---|---|
| ConceptNode/Edge/EditDiff/chunk content/accessor table | Kuzu (`WFH_DB_PATH`) |
| LayoutFrame / ConceptIndex | per-workspace file + in-memory cache |
| Textures | `Map` + IndexedDB (`IDB_TEXTURE_STORE`) — client-side |
| DOM snapshots / media | disk (dedup `DOM_SNAPSHOT_DEDUP` / `media/<domain>/<hash>`) |
| UIState (fold/signal/pin-chrome/rows) | per-workspace mirror snapshot (for `?resume`) |

```python
def purge_workspace(self, workspace_id: WorkspaceId) -> None
```
Clears **every** store + resets `frame_seq` in **one transaction** → emits one `PurgeFrame` (spine.md resets all slices in one paint, §6.5).

---

## §6 — Dependencies / Excluded
**Calls:** KuzuDB, filesystem, broadcaster. **Called by:** lifecycle.md (write+log), compute.md (cypher, resolve), materialiser/scanner (register+bump), every `/api/ui/*` route. **Excluded:** Kuzu DDL (below the spec line); the Symbolic-register mirror meaning; the REPL ANSI render (repl.md / frontend/repl_mirroring).
