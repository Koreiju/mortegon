# Code Constraint: Live Streaming

**Surface scope.** `backend/api/routes.py` `_ws_push` + `backend/services/layout_service.py` + the scanner streaming path + the workspace WS handler.

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §6.1 (incremental UMAP refits), §10.1 (workspace WS frame catalogue), §10.3 (Layout Service in streaming), §18.1 (severance — the critical anti-goal), §16.5 (live-scan probe asserts the contract).

---

## §1 — Must hold

### §1.1 Workspace-WS dual-routing per payload

Every payload emitted by the scan, the cascade, the agent tick, or any other long-running mutation MUST carry `workspace_id`. `_ws_push` routes to BOTH the snapshot WS queue (legacy) AND the workspace WS queue (the long-lived channel the frontend subscribes to). Without `workspace_id` injection, frames are dropped from the workspace WS — the §18.1 severance.

**Test signal.** `env-scenario scan-streaming-routes-to-workspace-ws`; §16.5 live-scan probe.

### §1.2 Pre-create the workspace WS queue at mutation start

When a long-running mutation starts (e.g., scan begins), the workspace WS queue MUST be pre-created. Frames emitted before a frontend subscribes are not dropped.

### §1.3 Incremental UMAP refits during scan

LayoutService MUST run incremental 6D UMAP refits during a scan (not just at scan-end). Default cadence: every K=64 new chunks → refit + `umap_canonical` broadcast.

**Test signal.** §16.5 probe asserts multiple `umap_canonical` frames before `done`.

### §1.4 Frame ordering preserved

WS frames within a workspace are monotonically sequenced by `frame_seq`. The router never re-orders.

### §1.5 Lossy backpressure with priority

When a queue is at capacity, oldest `chunks_partial` / progress frames drop first; `done`, `error`, latest `umap_canonical`, latest `concept_index_update`, all `concept_changed`, all `evolution_diff`, all `ui_state_changed` are preserved.

### §1.6 Replay buffer per snapshot

`WsReplayBuffer` retains the last 5 minutes of frames per snapshot. `?resume=<seq>` on WS reconnect replays missed frames.

### §1.7 Error path emits done with workspace_id

If a scan errors (Selenium failure, network timeout, etc.), the error path emits a `done` frame with `workspace_id` AND `error` fields populated. The frontend on the workspace WS sees the failure; no silent disappearance.

**Test signal.** §16.5 with NO_WEBDRIVER (or any other inducible Selenium failure).

### §1.8 No quiet degradation on stream side

If the LayoutService UMAP fit fails, the `umap_canonical` frame is not emitted; the frontend keeps chunks at their preliminary positions; the error surfaces via 503 on the next REST query.

---

## §2 — Must not

### §2.1 Emit a scan payload without `workspace_id`

§18.1 — the severance regression.

### §2.2 Emit a frame to the snapshot WS only when it should reach the workspace WS

The dual-router is for every workspace-scoped frame.

### §2.3 Defer the `pattern_map` materialisation to scan-end

§18.29 — incremental per-pattern emission is required.

### §2.4 Drop `concept_changed` / `evolution_diff` / `ui_state_changed` under backpressure

These are the Symbolic register's source of truth.

### §2.5 Run UMAP synchronously inline with the scan callback

The UMAP fit runs in a background thread (`threading.Thread(daemon=True)`); the on_stream callback returns quickly so the scanner can continue emitting chunks.

### §2.6 Let the workspace WS handler block on a slow consumer

Backpressure drops oldest progress frames; the queue never blocks the producer.

---

## §3 — Code anchors

| File | Responsibility |
|---|---|
| `backend/api/routes.py` `_ws_push` | Dual-router + frame_seq injection |
| `backend/api/routes.py` `trigger_snapshot` + `background_mapper_task` | Scan-end UMAP scheduling + workspace_id injection on every payload |
| `backend/services/layout_service.py` `recompute_and_broadcast` | UMAP refits + `umap_canonical` broadcast |
| `backend/services/ws_replay.py` | Replay buffer |

---

## §4 — Anti-goal anchors

| Constraint | Anti-goal |
|---|---|
| §1.1 (dual-routing) | §18.1 |
| §1.3 (incremental refits) | §18.29 + the live-update contract |
| §1.7 (error path emits done with workspace_id) | §18.1 |

---

## §5 — Feature touchpoints

- [`live_scan_streaming.md`](../features/live_scan_streaming.md)
- [`live_scan_cleanup.md`](../features/live_scan_cleanup.md)
- [`pattern_map.md`](../features/pattern_map.md)
- [`6d_umap.md`](../features/6d_umap.md)
- [`in_place_activity_viewer.md`](../features/in_place_activity_viewer.md)
