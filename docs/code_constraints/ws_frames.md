# Code Constraint: WebSocket Frame Schema + Routing

**Surface scope.** `backend/api/ws_frames.py` (frame builders) + `backend/api/routes.py` `_ws_push` (dual-router) + every emitter (LayoutService, ConceptIndexService, UIStateService, lifecycle dispatcher, agent runtime, scanner).

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §2.4 (monotone WS frame sequencing), §10.1 (workspace WebSocket frame catalogue), §18.1 (scan ↔ streaming severance — the critical anti-goal this surface guards), §6.1 (`umap_canonical` carries 6-vector).

---

## §1 — Must hold

### §1.1 Workspace-WS dual-routing

Every payload emitted via `_ws_push(snapshot_id, payload)` MUST:

- Route to the snapshot WS queue keyed by `snapshot_id` (legacy path).
- If `payload` is a dict and carries `workspace_id`, ALSO route to the workspace WS queue keyed by `payload["workspace_id"]`.
- If `workspace_id` is missing on a payload that SHOULD have one (`chunk_added`, `chunks_partial`, `umap_canonical`, scan-end `done`, `concept_changed`, `concept_index_update`, `agent_token`, `evolution_diff`, `ui_state_changed`, `purge_workspace`, `cascade_status`, `rollout_paused`, `rollout_resumed`), the emitter is buggy and the payload is dropped from the workspace WS — the §18.1 severance regression.

**Test signal.** `env-scenario scan-streaming-routes-to-workspace-ws`; `env-scenario halo-focus-roundtrip`; the §16.5 live-scan probe asserts dual-routing across the full chain.

### §1.2 Monotone `frame_seq`

Every emitted frame MUST carry a monotone `frame_seq` per workspace. `_ws_push` injects the seq from `next_frame_seq(str(snapshot_id))` if missing. `?resume=<seq>` replays the last 5 minutes via WsReplayBuffer.

**Test signal.** `env-scenario reconnect-resume` (planned).

### §1.3 Lossy backpressure with priority

When a queue is at capacity, oldest `chunks_partial` / progress frames drop first; `done`, `error`, latest `umap_canonical`, latest `concept_index_update`, all `concept_changed`, all `evolution_diff`, all `ui_state_changed` MUST survive.

**Test signal.** Slow-consumer probe (planned).

### §1.4 Frame schemas

| Frame type | Required fields | Optional fields |
|---|---|---|
| `chunk_added` | `concept_id`, `workspace_id`, `frame_seq` | `chunk_data`, position triplet seed |
| `chunk_replaced` | `concept_id`, `workspace_id`, `frame_seq` | `chunk_data` |
| `chunk_removed` | `concept_id`, `workspace_id`, `frame_seq` | — |
| `umap_canonical` | `workspace_id`, `coords` (dict[chunk_id → 6-vector]), `url_roots`, `bounding_radii`, `frame_seq` | `provenance` |
| `concept_changed` | `concept_id`, `workspace_id`, `change` ("created"/"modified"/"deleted"/"linked"), `frame_seq` | `new_state` snippet |
| `concept_index_update` | `workspace_id`, `updates` (dict[card_id → slot]), `frame_seq` | `pagerank_settle` flag |
| `agent_token` | `agent_id`, `workspace_id`, `token`, `partial` (bool), `frame_seq` | `pcid` |
| `evolution_diff` | `edit_id`, `workspace_id`, `actor`, `target`, `action`, `frame_seq` | `before`, `after` |
| `ui_state_changed` | `workspace_id`, `kind`, `state` (dict), `frame_seq` | — |
| `rollout_paused` | realized as a `ui_state_changed` frame with `kind="rollout_paused"`; `state.rollout_state` carries `card_id`, `field_path`, `paused`, `signal_index`, `signal_total`, `node_id`, `interval_ms`, `updated_at` | — |
| `rollout_resumed` | realized as a `ui_state_changed` frame with `kind="rollout_resumed"`; same `state.rollout_state` shape (`paused=False`) | — |
| `purge_workspace` | `workspace_id`, `frame_seq` | `nodes_purged` count |
| `cascade_status` | `workspace_id`, `per_agent` (dict), `frame_seq` | — |
| `done` | `type`, `workspace_id`, `frame_seq` | `error`, `result` |
| `error` | `type`, `workspace_id`, `frame_seq`, `error` (str) | `detail` |

The `umap_canonical` frame's `coords` MUST carry a 6-vector per chunk (3 position + 3 HSV) per §6.1. Legacy 3-vector format is a deprecated payload shape.

### §1.5 `ui_state_changed` `kind` discriminator

The `kind` field MUST identify which UIStateService setter fired, so peer surfaces can react selectively. Recognised kinds: `select`, `hover`, `pin`, `unpin`, `collapse`, `expand`, `hover_rect`, `url_collapse`, `url_expand`, `register_billboard_url`, `compile_expand`, `compile_collapse`, `halo_focus`, `halo_clear`, `halo_chain_push`, `halo_chain_clear`, `pin_chrome`, `latch`, `viewport_spine`, `autocomplete_open`, `autocomplete_close`, `edit_open`, `edit_close`, `signal_stream`, `signal_advance`, `signal_stream_clear`, `node_fold`, `rollout`, `rollout_paused`, `rollout_resumed`, `clear`.

> The set of kinds emitted by `ui_state_service.py::_emit(...)` MUST be a subset of this list (else §2.6 regresses). The `signal_*` kinds back the §11.6 signal-stream stepper, `node_fold` backs the §7.3.4 inline fold, and the `rollout*` kinds back the `RolloutCoordinator` play/pause. There is **no** separate top-level `rollout_*` frame type: rollout pause/resume is realized purely as a `ui_state_changed` frame whose `state.rollout_state` summary feeds the `watch-activity` `rollout` row (this keeps rollout on the one UI-state carrier rather than spawning a parallel stream, §14.4.4).

### §1.6 Pre-create workspace queue at long-running-mutation entry

Mutations that may emit many frames (scans, agent ticks, compile chains) MUST pre-create the workspace WS queue at start so frames emitted before a frontend subscribes are not dropped.

**Test signal.** `env-scenario scan-streaming-routes-to-workspace-ws`.

### §1.7 Replay buffer

`_ws_replay.record(snapshot_id, payload)` MUST capture every payload before routing. The replay endpoint `GET /api/snapshots/<snap_id>/replay` exposes it for testing + reconnection.

---

## §2 — Must not

### §2.1 Emit a scan-related payload without `workspace_id`

`chunk_added`, `chunks_partial`, scan-end `done`, scan-end `error`, and `umap_canonical` from the scanner path MUST carry `workspace_id`. Without it, dual-routing breaks and the §18.1 severance regresses.

### §2.2 Emit `umap_canonical` with 3-vector coords

The 6-vector format is canonical per §6.1. Legacy 3-vector payloads are deprecated.

**Anti-goal anchor.** §18 (the 6D UMAP contract).

### §2.3 Drop `concept_changed` or `evolution_diff` under backpressure

These are the Symbolic register's source of truth. The backpressure priority preserves them.

### §2.4 Emit a frame without a `frame_seq`

`_ws_push` auto-injects if missing; explicit emitters MUST NOT bypass `_ws_push`.

### §2.5 Coalesce `concept_changed` frames

Each mutation produces one `concept_changed`. Coalescing across mutations breaks the Symbolic register's per-mutation legibility.

### §2.6 Emit a `ui_state_changed` frame with an unknown `kind`

Peer surfaces switch on the kind to apply selective updates. Unknown kinds force a full re-sync.

---

## §3 — Code anchors

| File | Responsibility |
|---|---|
| `backend/api/ws_frames.py` | Frame builders (`build_umap_canonical`, `build_concept_changed`, etc.) |
| `backend/api/routes.py` `_ws_push` | Dual-router + frame_seq injection + backpressure |
| `backend/services/ws_replay.py` | Replay buffer (`WsReplayBuffer`) |
| `backend/services/layout_service.py` | `recompute_and_broadcast` builds + emits `umap_canonical` |
| `backend/services/concept_lifecycle.py` | Emits `concept_changed` per mutation |
| `backend/services/concept_index_service.py` | Emits `concept_index_update` on settle |
| `backend/services/ui_state_service.py` | Emits `ui_state_changed` per setter |
| `backend/services/agent_runtime.py` | Emits `agent_token` during transformer; emitter mutations route via lifecycle |
| `backend/services/evolution_log.py` | Emits `evolution_diff` per append |

---

## §4 — Anti-goal anchors

| Constraint | Anti-goal |
|---|---|
| §1.1 (dual-routing) | §18.1 (severance) |
| §1.4 (6-vector umap_canonical) | §18 (6D UMAP contract) |
| §1.6 (pre-create queue) | §18.1 (severance edge case — frames before subscribe) |
| §2.3 (no drop of concept_changed/evolution_diff) | §18 (Symbolic register completeness) |

---

## §5 — Feature touchpoints

- [`live_scan_streaming.md`](../features/live_scan_streaming.md)
- [`6d_umap.md`](../features/6d_umap.md)
- [`halo_retrieval.md`](../features/halo_retrieval.md)
- [`pattern_map.md`](../features/pattern_map.md)
- [`in_place_activity_viewer.md`](../features/in_place_activity_viewer.md)
- [`repl_two_way_feedback.md`](../features/repl_two_way_feedback.md)
- [`live_scan_cleanup.md`](../features/live_scan_cleanup.md)
- [`signal_stream.md`](../features/signal_stream.md)
- [`autoregressive_halo.md`](../features/autoregressive_halo.md)
