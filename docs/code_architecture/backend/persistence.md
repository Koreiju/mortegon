# Backend — Persistence (Kuzu · Files · Evolution Log · Backing Registry · UI Mirror)

> **Owns:** the storage layer + the append-only history + the backing-pointer resolver + the authoritative UI-state mirror. Files: `evolution_log.py`, `backing_registry.py`, `ui_state_service.py`, the Kuzu/cypher layer. Design: §11.1 / §11.4 / §3.3 / §10.5 / §6.5 / §15.6 / §2.6. Realises `code_constraints/persistence.md`, `concurrency.md`. KuzuDB is a no-mocks boundary (`subsystems.md`).

---

## §1 — Responsibility

Persist every record (the map in `data_schemas.md` §5); keep the **append-only evolution log** with three rollback scopes; resolve opaque `backing_pointer`s to live Python; own the authoritative **UIState mirror** that every surface (GUI tabs + REPL) re-syncs from. Optimistic concurrency, last-write-wins — conflict resolution is rollback, not locks (§2.7).

---

## §2 — Public Surface

```python
# kuzu / cypher layer
def upsert_node(node) -> None; def delete_node(id) -> None; def upsert_edge(edge) -> None
def cypher(query: str, params: dict) -> list[Row]        # inline-cypher execution (compute.md §3.2)

# evolution_log.py (append-only)
def append(diff: EditDiff) -> None
def rollback(edit_id) -> EditDiff                         # applies inverse; records ITSELF as a new diff
def rollback_range(from_id, to_id) -> list[EditDiff]
def rollback_actor(actor) -> list[EditDiff]

# backing_registry.py
def resolve(backing_pointer: str) -> Any                 # prefix → live handle (data_schemas.md §3)
def register(backing_pointer, handle) -> None
def bump_version(backing_pointer) -> int                 # invalidate downstream compile cache (§15.6)

# ui_state_service.py (the mirror; data_schemas.md §4.4)
def set_<field>(...) -> None                             # ONE idempotent setter per field; broadcasts full snapshot
def snapshot(workspace_id) -> UIState
def merge_telemetry(batch: list[dict]) -> None           # POST /api/ui/telemetry
```

---

## §3 — Internal Logic

### §3.1 Storage map (§11.1, `data_schemas.md` §5)
ConceptNode + ConceptEdge + EditDiff + chunk content + accessor table → **Kuzu** (`WFH_DB_PATH`). LayoutFrame (6-vectors) + ConceptIndex (nomic/PageRank/similar_to) → per-workspace file + in-memory cache. Textures → `Map` + IndexedDB. DOM snapshots → disk (dedup by SHA256). Media → disk + `MediaAsset` rows.

### §3.2 Evolution log + rollback (§11.4 / §2.6)
Append-only `EditDiff` (`data_schemas.md` §4.1); monotone by `created_at`. Rollback applies the **inverse** of the target diff(s) **and records the rollback itself as a new diff** — history never loses entries. Three scopes: single edit / edit range / actor scope. RolloutCoordinator's sample boundaries are diffs here (compute.md §3.4) so a rollout is range-rollback-able.

### §3.3 Backing registry (§3.3 / §15.6)
Opaque `backing_pointer` → live Python, by prefix (`python_object::`, `fixture::`, `agent::`, `xpath_pattern::`, `chunk::`, …). `bump_version` increments a per-pointer seq; any node referencing a bumped pointer has its compile cache invalidated (the cascade recompiles, lifecycle.md/compute.md). This is the seam materialiser + scanner use to keep renderings fresh when backings change.

### §3.4 UI mirror (§10.5)
The backend holds the authoritative `UIState`; **exactly one setter per field**, each idempotent and **broadcasting the full snapshot on every call** (`ui_state_changed`) so peer tabs + the REPL re-sync. `merge_telemetry` field-merges batched frontend snapshots (pin chrome, fold state, viewport rows, signal stream). The mirror is the source for `?resume` replay and the REPL `watch-activity` dashboard.

### §3.5 Purge (§6.5)
`POST /api/purge_workspace` clears every store + resets `frame_seq` in **one transaction** → emits a single `purge_workspace` frame; the frontend resets all slices in one paint (frontend/spine.md).

---

## §4 — Dependencies

- **Calls:** KuzuDB, the filesystem, IndexedDB (via the frontend for textures), WS broadcaster.
- **Called by:** ConceptLifecycle (write + log, lifecycle.md), compute.md (cypher, backing resolve), materialiser/scanner (register backings + version bump), every `/api/ui/*` route (mirror setters, `contracts.md`).

---

## §5 — Excluded

- The Symbolic-register meaning of the mirror; the REPL ANSI rendering (`frontend/repl_mirroring.md`). The Kuzu schema DDL (an implementation detail below the architecture line).
