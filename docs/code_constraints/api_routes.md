# Code Constraint: REST API Route Contract

**Surface scope.** `backend/api/routes.py` (every `@router.<verb>` endpoint).

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §2.5 (idempotency keys), §10 (streaming architecture), §13 (no-mocks contract), §14 (REPL ↔ frontend).

---

## §1 — Must hold

### §1.1 Idempotency on every mutation

Every POST / PATCH / DELETE route MUST accept an optional `idempotency_key` body field. Replays with the same key within 5 minutes return the original effect.

**Test signal.** `env-scenario idempotency-replay`.

### §1.2 Workspace-scoped requests

Every mutation route accepts a `workspace_id` field (default `""` resolving to `"_default"`). State changes are scoped to that workspace; cross-workspace pollution is forbidden.

**Test signal.** `env-scenario workspace-isolation`.

### §1.3 Confirm-token on destructive operations

`POST /api/purge_workspace` requires `confirm: "erase"` in the body. Any other token returns 400.

**Test signal.** `env-scenario purge-requires-confirm`.

### §1.4 Error envelope

Errors return `{ok: false, error: "<message>", _status: <code>, detail?: "<longer>"}`. HTTP status carries the code. 503s for missing real subsystems (per the no-mocks contract).

### §1.5 Four-fixture endpoint family

Each foundation fixture (§9.5) has its primary-function endpoints:

| Fixture | Endpoints |
|---|---|
| Agent | `POST /api/agent/meta_prompt`, `POST /api/agent/prompt`, `POST /api/agent/output`, `POST /api/agent/invoke` (legacy), `POST /api/agent/spawn`, `POST /api/agent/tick`, `PATCH /api/concepts/<pcid>` (pause/unpause) |
| WebBrowser | `GET /api/snapshot` (legacy entry, returns 202 Accepted; carries `?url=...&query=...&workspace_id=...`), `POST /api/web_browser/scan` (realized — the named WebBrowser.scan primitive) |
| Database | `POST /api/search`, `POST /api/database/cypher`, `POST /api/database/concept`, `GET /api/concepts/<id>` |
| Editor | `POST /api/concepts` (Editor.create), `POST /api/concept_edges` (Editor.link), `PATCH /api/concepts/<id>` (Editor.overwrite), `DELETE /api/concepts/<id>` (Editor.delete) |

### §1.6 UI mirror endpoint family

Every UIStateService setter has a REST endpoint under `/api/ui/`:

| Setter | Endpoint |
|---|---|
| select / hover / pin / unpin / collapse / hover_rect | `POST /api/ui/{name}` |
| url_visibility / register_billboard_url | `POST /api/ui/{name}` |
| compile_expand / compile_collapse | `POST /api/ui/{name}` |
| halo_focus / halo_clear / halo_chain_push / halo_chain_clear | `POST /api/ui/{name}` |
| pin_chrome / latch / viewport_spine | `POST /api/ui/{name}` |
| autocomplete / autocomplete_clear | `POST /api/ui/{name}` |
| edit_open / edit_close | `POST /api/ui/{name}` |
| signal_stream / signal_advance / signal_stream_clear / signal_reset | `POST /api/ui/{name}` (the §11.6 signal-stream stepper) |
| node_fold | `POST /api/ui/node_fold` (the §7.3.4 inline `{ref}`-token fold) |

The `RolloutCoordinator` play/pause/step (§7.5) live under their own prefix, NOT `/api/ui/`: `POST /api/rollout/play`, `POST /api/rollout/pause`, `POST /api/rollout/step`. They drive the same UIStateService mirror (`rollout_state`) via `ui_state_changed` frames (see [`ws_frames.md`](ws_frames.md) §1.5), so the `watch-activity` `rollout` row reflects them.

Read: `GET /api/ui/state?workspace_id=...`, `GET /api/ui/node_state/<node_id>`, `GET /api/ui/hidden_billboards`.

### §1.7 Subsystem status surface

`GET /api/subsystem_status` returns `{ok, all_real, slm: {backend, model, loaded, fake_env}, embedder: {...}, selenium: {...}, langgraph: {...}}`. Production deployments poll it; CI asserts `all_real: true`.

### §1.8 Workspace WS endpoint shape

`WS /api/ws/workspace/<workspace_id>?resume=<seq>` opens a long-lived per-workspace WS. On open, the server sends bootstrap frames (current `concept_index_update` + `umap_canonical`). Subsequent frames are workspace-scoped.

### §1.9 Snapshot WS endpoint shape

`WS /api/ws/nodes/<snapshot_id>?resume=<seq>` opens a per-scan WS for legacy scan-only tabs.

### §1.10 Replay endpoint

`GET /api/snapshots/<snapshot_id>/replay?since=<seq>` returns the replay buffer for a snapshot. Used by env-scenarios + reconnection logic.

---

## §2 — Must not

### §2.1 Mutate state in a GET endpoint

GETs are pure reads. State mutations (cache invalidations, lazy refits) belong in POST/PATCH/DELETE.

### §2.2 Return a 200 on a Pydantic validation failure

Validation failures return 422 (FastAPI default) or 400 (`HTTPException(status_code=400, ...)`).

### §2.3 Skip the workspace_id check

A route that operates on a concept MUST verify the concept belongs to the requested workspace.

### §2.4 Return raw exception strings to the client

Errors get a structured envelope. The exception traceback goes to server logs.

### §2.5 Bypass the lifecycle dispatcher for "performance"

Even bulk mutations go through the dispatcher per record (or as one bulk diff with one EditDiff per primitive call).

---

## §3 — Code anchors

| File | Responsibility |
|---|---|
| `backend/api/routes.py` | Every REST route |
| `backend/api/ws_frames.py` | Frame builders for WS responses |
| `backend/api/__init__.py` | Router registration |

---

## §4 — Anti-goal anchors

| Constraint | Anti-goal |
|---|---|
| §1.1 (idempotency) | §18 (rapid retries must produce one effect) |
| §1.3 (confirm token) | §18.4 (purge destroys; confirm prevents accidents) |
| §1.7 (subsystem status) | §13 (no-mocks contract) |
| §1.8 (workspace WS shape) | §18.1 (severance — the workspace WS is the long-lived channel) |

---

## §5 — Feature touchpoints

Every feature that exposes a REST route:
- [`four_fixture_api.md`](../features/four_fixture_api.md)
- [`halo_retrieval.md`](../features/halo_retrieval.md)
- [`click_to_edit.md`](../features/click_to_edit.md)
- [`live_scan_streaming.md`](../features/live_scan_streaming.md)
- [`live_scan_cleanup.md`](../features/live_scan_cleanup.md)
- [`evolution_log_rollback.md`](../features/evolution_log_rollback.md)
- [`in_place_activity_viewer.md`](../features/in_place_activity_viewer.md)
- [`no_mocks_contract.md`](../features/no_mocks_contract.md)
