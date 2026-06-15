# Code Architecture — Wire Contracts (REST + WebSocket)

> **Status: planned.** The HTTP + WebSocket surface between backend and frontend (and the REPL). Distilled from `DOMAIN_MODEL.md` §10 / §14.2 / §13 and `frontend/{frame_bus,gesture_gateway}.md`. Realises `code_constraints/{api_routes,ws_frames,streaming}.md`.

---

## §1 — Invariants

1. **One inbound seam, one outbound seam** (frontend) — all truth arrives on the **workspace WebSocket** via `FrameBus`; all intent leaves via `GestureGateway` REST. No view opens its own socket/fetch.
2. **Idempotency key on every retry-sensitive mutation** (POST/PATCH/DELETE) — replays return the original effect without re-applying (§5). The key is an `idempotency_key` **body field** (not an HTTP header); the route layer keeps a 5-minute (`idempotency_ttl_sec=300`) per-`(workspace, target, key)` dedup window. A missing key skips dedup (the mutation applies normally) — naturally-idempotent field-set UI mutations (hover / pin / collapse / latch, last-write-wins) rely on that and carry no key.
3. **Monotone frame sequencing** — each workspace WS frame carries `frame_seq`; `?resume=<seq>` replays the last 5 minutes (§2.4).
4. **Lossy backpressure** — drop oldest `chunks_partial`/progress; always keep `done`, `error`, latest `umap_canonical`, latest `concept_index_update`, all `concept_changed`, all `evolution_diff`.
5. **Every mutation route enters the one lifecycle dispatcher** (§10.2). There is no second mutation path.
6. **No-mocks** — production never sets a fake gate; `GET /api/subsystem_status` reports `all_real: true` (§13).

---

## §2 — REST Routes (the gesture catalogue → endpoints, §14.2)

Grouped by surface; each carries an `idempotency_key` body field unless marked (read). The frontend `GestureGateway` kind maps 1:1 to a row; the REPL action of the same name hits the same route.

### §2.1 Pin / panel chrome
| Route | Body | Returns frame |
|---|---|---|
| `POST /api/ui/hover` | `{chunk_id, rect?}` | `ui_state_changed` |
| `POST /api/ui/pin` | `{chunk_id, rect}` | `ui_state_changed` (pinned_billboards, last_stick_rect) |
| `POST /api/ui/pin_chrome` | `{panel_id, top?,left?,width?,height?,minimised?}` (field-merge) | `ui_state_changed (pin_chrome)` |
| `POST /api/ui/unpin` | `{node_id}` | `ui_state_changed (unpin)` |
| `POST /api/ui/collapse` | `{node_id, collapsed}` | `ui_state_changed` |
| `POST /api/ui/latch` | `{card_id, latched}` | `ui_state_changed (latch)` |

### §2.2 Editing / field-tree / fold
| Route | Body | Returns |
|---|---|---|
| `PATCH /api/concepts/{id}` | `{name?, description?, data?}` (field-merge) | `concept_changed` (+`concept_index_update` if description) |
| `POST /api/ui/node_fold` | `{card_id, node_path, expanded}` | `ui_state_changed (node_fold)` (§7.3.4 inline rank-1 fold) |
| `POST /api/ui/compile_expand` / `compile_collapse` | `{card_id}` | `concept_changed`×N + `ui_state_changed (compile_expansions)` (double-left, §O.1) |
| `POST /api/ui/autocomplete` / `autocomplete_clear` | `{row_id, query, parent_card_id?}` | `ui_state_changed (autocomplete)` |
| `GET /api/concept_completions` | `?prefix=&parent_card_id=` | (read) ranked candidates |

### §2.3 Compile / retrieval / halo / wiring
| Route | Body | Returns |
|---|---|---|
| `POST /api/conceptual/compile` | `{concept_id, use_slm, persist_rendering}` | `concept_changed` |
| `POST /api/conceptual/compile_chain` | `{focal_id, max_depth, use_slm}` | `concept_changed`×N |
| `GET /api/apparitions/{focal_id}` | `?k=&transport=&ray_project=` | (read) candidates (triple product / panel max-minmax §O.22) (+ `GET /api/apparitions/mode`) |
| `POST /api/ui/halo_focus` · `POST /api/ui/halo_clear` | `{focal_card_id, candidates?}` / — | `ui_state_changed (halo)` (+ `halo_chain_push`/`halo_chain_clear`) |
| `POST /api/concept_edges` | `{source_id, target_id, edge_type?, source_port?, target_port?}` | `concept_changed`×2 (soft→hard promote; left-click-drag, N.4) |
| `POST /api/ui/viewport_spine` | `{ordered:[chunk_id], total}` | `ui_state_changed (viewport_spine)` |
| `POST /api/ui/url_visibility` (eye + domain-toggle: per-URL `set_url_collapsed`) | `{url, collapsed}` | `ui_state_changed (url_collapse)` |
| `ui-row-click` / `ui-hover-row` | composed — no dedicated route (pin+viewport_spine / hover+halo_focus) | `ui_state_changed` |

### §2.4 Scan / fixtures / agent / rollout / lifecycle
| Route | Body | Returns |
|---|---|---|
| `POST /api/web_browser/scan` (legacy: `GET /api/snapshot`, 202) | `{url, query?, samples?}` | `chunk_added`×N → `umap_canonical` → `done` |
| `POST /api/recompute_umap` | `{workspace_id?}` | `umap_canonical` (6-vectors) |
| `POST /api/editor/{create,link,overwrite,delete}` | primitive args (§9.5.1) | `concept_changed` (+ `evolution_diff` actor=editor) |
| `POST /api/python_api/materialise_module` (refresh: `/rematerialise_module`) | `{qualified_name}` | `concept_changed`×N (materialised tree) |
| `POST /api/agent/spawn` | `{goal, name?}` | `concept_changed`×4 + edges |
| `POST /api/agent/tick` | `{parameter_card_id}` | `agent_token` stream + `concept_changed`×emit |
| `GET /api/agent/cascade_status` | — | (read) per-actor fire counts |
| `POST /api/rollout/{play,pause,step}` | per §7.5 | `ui_state_changed (kind=rollout_resumed/rollout_paused)` — carries `rollout_state`; NOT a standalone frame (see §3 + ws_frames.md §1.4) |
| `POST /api/ui/signal_advance` / `signal_reset` | `{card_id, field_path, signal_index?}` | `ui_state_changed (signal_advance)` |
| `POST /api/purge_workspace` | `{workspace_id, confirm:"erase"}` (or url-scoped) | `purge_workspace` |
| `POST /api/evolution_log/rollback` / `rollback_range` / `rollback_actor` | per §11.4 | `evolution_diff` + `concept_changed` |
| `POST /api/ui/telemetry` | batched `{kind, snapshot}[]` | (mirror merge) → `ui_state_changed` |
| `GET /api/subsystem_status` | — | (read) §4 |

**Completeness rule:** a new gesture must add (route, frame, mirror field) here, a `GestureGateway` kind, a REPL action, and an env-scenario — or it is not integrated (§14.4).

---

## §3 — WebSocket Frames (§10.1)

One long-lived socket per workspace per tab: `GET /api/ws/workspace/{workspace_id}?resume=<seq>`. Every frame: `{frame_seq:int, type:str, workspace_id:str, ...}`.

| `type` | Source | Payload (key fields) | Frontend effect |
|---|---|---|---|
| `chunk_added` / `chunk_replaced` / `chunk_removed` | scanner / chunk lifecycle | `{chunk_id:int, url, image_url?, provenance, summary?}` | mesh enter/update/exit (keyed) |
| `chunks_partial` / `instances_indexed` | scanner | progress | spine refresh (sheddable) |
| `umap_canonical` | LayoutService | `{coords:{chunk_id→[x,y,z,h,s,v]}, url_roots, bounding_radii}` (6-vector per chunk, §6.1) | interruptible tween to canonical (§5.4-FE) |
| `compute_graph_layout` | LayoutService (§6.6.4) | `{graph_id, node:{pos:[x,y,z], hsv:[h,s,v]}, readouts:[{chunk_id, pos:[x,y,z], hsv:[h,s,v]}], links:[ProjectorLink], settle_seq}` — bisector node + the settling readout's perimeter coord + UMAP-independent links; **never folded into `umap_canonical`** (§18.34) | place/slide the compute-graph node, seat the readout on the perimeter, redraw plain 3D links (`frontend/projector.md`) |
| `concept_changed` | lifecycle | `{concept_id, change_kind, node?}` | re-render panel; refresh apparitions |
| `concept_index_update` | ConceptIndexService | `{updated:[{id,pagerank,similar_to}]}` | refresh halo slots |
| `agent_token` | agent transformer | `{agent_id, token, partial}` | append to token ring |
| `evolution_diff` | EvolutionLog | the `EditDiff` | history view; cascade notice |
| `ui_state_changed` | UIStateService | full `UIState` snapshot + `last_change_kind` | mirror every view |
| rollout (paused/resumed) | RolloutCoordinator | realized as `ui_state_changed` with `kind ∈ {rollout_paused, rollout_resumed, rollout}`; `state.rollout_state = {card_id, field_path, paused, signal_index, signal_total, node_id, interval_ms}` — NOT a standalone frame type | play/pause indicator; edit affordances |
| `cascade_status` | cascade scheduler | per-actor fires / skips | viewer |
| `purge_workspace` | purge handler | consolidated clear | reset all slices + frame_seq |
| `done` / `error` | various | terminator / `--accent-error` envelope | settle the awaiting gesture |

**Dual-routing (§18.1):** scan `chunk_added` + `umap_canonical` MUST reach the **workspace** WS (not only a per-snapshot socket). `_ws_push` fans to both; `recompute_and_broadcast` keys on `workspace_id`.

**Async readout deltas (§7.8.3):** computation-graph **readout** chunks emit **per-node** in **settle order** — **no global rollout barrier** across subgraphs (§18.34). Each settling readout's **content** rides `chunk_replaced` while its **perimeter 6-vector + the re-placed bisector node + the links** ride the accompanying `compute_graph_layout` (so one readout updates without a full `umap_canonical` refit). Per-node coalescing (keep-latest), bounded by `READOUT_DELTA_MAX_INFLIGHT` (constants.md §3); `settle_seq` re-orders client-side. Same dual-routing rule as above (workspace WS).

---

## §4 — `GET /api/subsystem_status` (no-mocks operator surface, §13.3)

```json
{ "ok": true, "all_real": true,
  "slm":       {"backend":"gpt4all","model":"Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf","loaded":true,"device":"cuda","fake_env":false},
  "embedder":  {"backend":"nomic","model":"nomic-embed-text-v1.5.f16.gguf","device":"cuda","fake_env":false},
  "selenium":  {"backend":"selenium","loaded":true,"driver_class":"WebDriver","singleton_bound":true},
  "langgraph": {"backend":"langgraph","loaded":true,"has_StateGraph":true},
  "apparition_mode": "single-frequency | multi-frequency" }
```
CI asserts `all_real: true` before any contract-bearing scenario. A failed real load = **503 + cascade halt**, never a silent stub fallback (§13.4). `apparition_mode` reports single- vs multi-frequency aggregation (§8.1.1 / §18.25).

---

## §5 — The Lifecycle Fan-Out Contract (§10.2)

Idempotency is enforced at the **route layer** (each mutation route does `_idempotency_lookup`/`_idempotency_store`, 5-min per-`(workspace,target,key)` window) BEFORE the dispatcher is called — it is NOT a dispatcher fan-out step. Every mutation route then resolves to `apply_update_lifecycle` / `apply_delete_lifecycle`, which fans out **in order**: foundation-fixture guard (delete only — keyed on `backing_pointer`/`concept_id` `fixture::` prefix, returns early with NO fan-out) → Kuzu write → EvolutionLog append → ConceptIndex upsert → output-projection schedule (§9.12, unconditional; `output_projection` selects peripherals + maps `agent-authored → agent-output`) → WS `concept_changed` broadcast → cascade scheduler nudge (§7.4). Detail in [`backend/lifecycle.md`](backend/lifecycle.md) §3.

---

## §6 — Excluded (per README §0)

- The register-level *meaning* of frames (Symbolic-register transparency) — only the wire schema is here.
- REPL-viewer ANSI rendering — see `frontend/repl_mirroring.md`.
