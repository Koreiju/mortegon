# Code Constraint: Persistence + Cleanup

**Surface scope.** Kuzu storage + LayoutFrame JSON files + GlobalTfidfStore in-memory + IndexedDB texture cache + on-disk media cache + the purge handler.

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §11 (persistence and the evolution log), §11.1 (storage table), §11.2 (image persistence), §16.5 (live-scan + DB-cleanup probe), §18.4 (old domains persist after purge — the cleanup anti-goal).

---

## §1 — Must hold

### §1.1 Storage table

| Artefact | Storage |
|---|---|
| ConceptNode | Kuzu `ConceptNode` table |
| ConceptEdge | Kuzu `ConceptEdge` table |
| EditDiff | Kuzu `EditDiff` table (append-only) |
| Chunk content + extraction_trie | Kuzu (referenced from ChunkInstance ConceptNodes) |
| Persistent accessor table | Kuzu, keyed by `(domain, pattern_hash)` |
| `pattern_map` schemas | Inside `pattern_map` ConceptNode's `data` field |
| LayoutFrame (6-vector per chunk + url_roots) | Per-workspace JSON file on disk + in-memory cache |
| ConceptIndex (nomic + TF-IDF + PageRank) | In-memory + per-workspace persisted file |
| TF-IDF | GlobalTfidfStore — one ever-growing in-memory sparse matrix shared across workspaces (save/load to a single on-disk file), rows keyed `graph__<ws>__<concept_id>__<sample>`; per-workspace removal via `remove_workspace(ws)` (used by purge §1.8) |
| UIState mirror | In-memory only (transient) |
| Image textures | In-memory `Map<url, THREE.Texture>` + IndexedDB blob cache |
| Media assets (downloaded) | Disk file (`media/<domain>/<hash>.<ext>`) + `MediaAsset` records |
| Full DOM HTML snapshots | Disk file (`snapshots/`) referenced from `DomSnapshot` records |
| Replay buffer (5-min retention) | In-memory per snapshot |

### §1.2 Snapshots deduplicated by content hash

Same URL + same SHA256 content hash → no new `DomSnapshot` row. Repeated scans of static pages don't bloat the timeline.

### §1.3 Image single-fetch path

In-memory cache → IndexedDB blob → `fetch(proxy_url)` → `fetch(direct_url)`. The `X-Image-Proxy-Note` transparent-PNG fallback is NEVER cached as a successful image.

**Anti-goal anchor.** §18.10.

### §1.4 Texture sharing

Two chunks pointing at the same image URL share one `THREE.Texture` instance — no duplicate decode, no duplicate GPU upload.

### §1.5 LayoutFrame 6-vector format

LayoutFrame stores 6-vectors per chunk `(x, y, z, h, s, v)`. Legacy 3-vector files migrate on first load by re-deriving HSV from the TF-IDF index.

**Anti-goal anchor.** §1.2.2 6D contract.

### §1.6 Persistent accessor table populated incrementally

Each scan that detects a pattern populates `(domain, pattern_hash)` → accessor map in Kuzu. Subsequent scans of the same domain consult the table first.

### §1.7 EvolutionLog append-only

`EditDiff` rows are append-only. Rollback applies an inverse and records the rollback as a new diff (the log grows monotonically).

### §1.8 Cleanup contract (purge_workspace)

`POST /api/purge_workspace { confirm: "erase" }` MUST:

- **Bulk-delete every concept node + edge from Kuzu** (`ge.delete_concept` per listed id, raw Kuzu deletes, offloaded to a thread). This is intentionally NOT a per-card `apply_delete_lifecycle` walk: the consolidated `purge_workspace` frame (below) subsumes the per-card `concept_changed` broadcasts, the LayoutFrame drop subsumes the per-card output-projection schedules, and the ConceptIndex hydrate-on-next-touch handles index cleanup lazily. The per-card lifecycle was removed because it forced a synchronous nomic-embedder load inside the delete loop (a 2-card purge ran past 180s). Consequence: purge does NOT preserve per-concept EditDiff records — it is a deliberately final operation, which is why it is gated behind `confirm: "erase"`. The Kuzu-backed persistent accessor table (`compiled_from_scans` patterns ARE ConceptNodes) is cleared by this same bulk delete.
- Drop the persisted LayoutFrame (in-memory + on-disk JSON) via `layout_service.purge_workspace`.
- **Remove the workspace's rows from the GLOBAL TF-IDF store** via `global_tfidf_store.remove_workspace(ws)`. The store is a single, ever-growing in-memory accumulator keyed by `graph__<ws>__<concept_id>__<sample>` chunk ids; the bulk Kuzu delete removes the `ChunkInstance` nodes but NOT these vectors, so without this removal a post-purge `chunk_search` would surface ghost rows (score + preview, empty `html_raw`). The removal is a cheap CSR rebuild — no embedder load — so it stays inside the perf budget. The count is returned as `tfidf_rows_dropped`.
- Drop the UI-state mirror + the UI-telemetry ring buffer + the backing-pointer version registry (`backing_version.reset`).
- Drop the ConceptIndex slot cache — realized as lazy hydrate-on-next-touch pruning, NOT an explicit synchronous clear (keeps the bulk path off the embedder).
- Reset the `frame_seq` counter (`reset_frame_seq`).
- Emit one consolidated `purge_workspace` WS frame (`build_purge_workspace`).
- Shrink the on-disk Kuzu file size to within ~10% of pre-scan baseline (the §16.5 probe asserts this).

**Anti-goal anchor.** §18.4.

### §1.9 Foundation fixtures auto-rematerialise post-purge

After `purge_workspace`, `ensure_foundation_fixtures` is called on next workspace-open to re-materialise the three fixtures (§S removed Editor) + their member trees.

**Anti-goal anchor.** §18.27.

### §1.10 Workspace isolation

Cross-workspace pollution is forbidden. Every storage write keys by `workspace_id`. A workspace's purge does NOT affect other workspaces.

---

## §2 — Must not

### §2.1 Cache the transparent-PNG fallback as a successful image

§18.10 — the loader treats the `X-Image-Proxy-Note` response as a failed fetch.

### §2.2 Let the Kuzu file grow unboundedly across scan rounds

§18.4 — purge shrinks the file. The §16.5 probe asserts this.

### §2.3 Persist UI state to disk

§10.5 — UI state is in-memory only. Persistence would introduce stale-state-on-restart hazards.

### §2.4 Store ConceptNodes in two tables (one for users, one for scanner)

§3 — one record table.

### §2.5 Mutate EditDiff rows after append

Append-only — rollback records as a new diff, never as a mutation of the original.

### §2.6 Delete a foundation fixture in any cleanup path

§18.22, §18.27 — fixtures are undeletable; purge re-creates them via `ensure_foundation_fixtures`.

### §2.7 Skip the persistent-accessor-table clear on purge

§18.4 — old patterns surviving purge corrupt the next scan's incremental update path.

---

## §3 — Code anchors

| File | Responsibility |
|---|---|
| `backend/services/database.py` (Kuzu wrapper) | Kuzu schema + transactions |
| `backend/services/layout_service.py` | LayoutFrame storage + on-disk JSON |
| `backend/services/concept_index_service.py` | ConceptIndex in-memory + persisted file |
| `backend/services/global_tfidf_store.py` | TF-IDF per-workspace + per-band storage |
| `backend/services/evolution_log.py` | EditDiff table |
| `backend/services/compiled_from_scans.py` | Persistent accessor table |
| `backend/static/js/cp/sprite_manager.js` | Image fetch + IDB cache |
| `backend/api/routes.py` `/api/purge_workspace` | Purge handler orchestration |
| `backend/dom/pipeline.py` | DomSnapshot dedup by content hash |

---

## §4 — Anti-goal anchors

| Constraint | Anti-goal |
|---|---|
| §1.3 (single image fetch path) | §18.10 |
| §1.5 (6-vector LayoutFrame) | §1.2.2 6D contract |
| §1.8 (cleanup contract) | §18.4 |
| §1.9 (foundation re-materialisation) | §18.27 |
| §1.10 (workspace isolation) | (workspace contract) |

---

## §5 — Feature touchpoints

- [`live_scan_cleanup.md`](../features/live_scan_cleanup.md)
- [`6d_umap.md`](../features/6d_umap.md)
- [`pattern_map.md`](../features/pattern_map.md)
- [`evolution_log_rollback.md`](../features/evolution_log_rollback.md)
- [`no_mocks_contract.md`](../features/no_mocks_contract.md)
