# Spec — Backend / API (FastAPI app, WS endpoint, middleware)

> Deepens [`code_architecture/contracts.md`](../../code_architecture/contracts.md). File: `backend/main.py` (+ route modules). Types: [`../types.md`](../types.md) §7. Constants: [`../constants.md`](../constants.md) §7. Errors: [`../errors.md`](../errors.md) §1.

The web layer: bind singletons on lifespan, register routes, enforce idempotency, run the per-workspace WS loop, map exceptions → status/frame. **It owns no domain logic** — every route is a thin adapter to a service that funnels through `apply_*_lifecycle`.

---

## §1 — Lifespan (boot)

```python
@asynccontextmanager
async def lifespan(app) -> AsyncIterator[None]
```
- **Does** — eager-init every singleton; fail loud.
- **Algorithm:**
  1. resolve env (`WFH_SLM_MODEL`→`SLM_MODEL`, devices, `WFH_DB_PATH`, fake gates).
  2. `SLMClient.load()` → on `*llama*` raise `ForbiddenModelError` (process exits); on load fail raise `SubsystemDownError`. Skipped only if `WFH_FAKE_SLM`.
  3. `EmbeddingService.load()` (nomic; CPU override = WARNING). 4. `WebBrowserManager.init()` unless `NO_WEBDRIVER`. 5. assert `langgraph.graph.StateGraph` importable else hard error.
  6. open Kuzu at `WFH_DB_PATH`; run migrations (3-vec→6-vec layout, shim `to_concept_node`).
  7. `ensure_foundation_fixtures(DEFAULT_WORKSPACE)` (materialiser.md) — exactly `AGENT_BODY_CARDS`-independent **4** fixtures.
  8. register singletons in `BackingRegistry`; start `CascadeScheduler`.
- **Post** — `GET /api/subsystem_status` returns `all_real:true` (production) or raises captured at boot.

---

## §2 — Idempotency (per-route, NOT middleware)

```python
# Realized (routes.py): idempotency is enforced PER MUTATION ROUTE via two
# helpers — there is no ASGI middleware. Each POST/PATCH/DELETE handler calls:
def _idempotency_lookup(workspace_id, target, key) -> Optional[dict]   # hit → return cached
def _idempotency_store(workspace_id, target, key, response) -> None    # miss → cache after
```
- **Applies to** — every mutation route, keyed by `(workspace_id, target, idempotency_key)`. The `idempotency_key` is a body field (not a header) on the request models.
- **Algorithm:** key absent → handler runs normally. Key present → `_idempotency_lookup` at the TOP of the handler: **hit** within `IDEMPOTENCY_WINDOW` → return the stored response verbatim (the service/dispatcher is never called); **miss** → run the handler (which funnels through `apply_*_lifecycle`), then `_idempotency_store` the response.
- **Post** — replays never re-apply (errors.md §2). The dedup lives at the route layer; the dispatcher itself is idempotency-agnostic (lifecycle.md §1).

---

## §3 — Route Registration (the catalogue → handlers)

Every row of `code_architecture/contracts.md` §2 is registered here, each handler ≤ ~10 lines: validate body (→`ValidationError`/422) → call the owning service → return `{ok:true}` or the read payload. The mutation routes return after the service has funnelled through `apply_*_lifecycle` (the frame is broadcast async). Completeness assertion (§14.4): a startup check verifies every `GestureGateway` kind has a registered route (test-time).

Representative bindings:
| Route | Handler → service |
|---|---|
| `PATCH /api/concepts/{id}` | `concepts.patch` → `apply_update_lifecycle(field-merge, actor=user)` (lifecycle.md) |
| `POST /api/conceptual/compile` | `compile.run` → `ConceptComputeNode.compile` (compute.md) |
| `POST /api/web_browser/scan` (legacy `GET /api/snapshot`) | → `run_pipeline_live` (scanner.md) — streams. Body `WebBrowserScanRequest{url, query, samples, duration_s, workspace_id}`; `duration_s` (§15.10 time-box, Q.2) maps to `SnapshotRequest.max_duration` → `trigger_snapshot(max_duration=…)` → `mapper.snapshot(max_duration=…)`. `duration_s=0` ⇒ sample-bounded default. |
| `POST /api/agent/tick` | `agent.tick` → `MetaCognitionTick.run_async` (agent.md) — streams `agent_token` |
| `GET /api/apparitions/{focal_id}` | → `ApparitionService.apparitions_for_focal` (read; `?transport=&ray_project=`) |
| `POST /api/ui/*` | `ui.<field>` → `UIStateService.set_<field>` (persistence.md; realized setters per §4) |
| `POST /api/ui/dominance_collapse` | `ui.dominance_collapse` → `UIStateService.set_dominance_collapse` — the generalized rank-dominance collapse/expand (§6.6.5 / §7.3.5, Q.3–Q.5). Body `{node_id, collapsed, workspace_id}`; computes the dominator's dominated-set reachability over the `ConceptEdge` graph (the same traversal feeding PageRank, §8.1.2), writes mirror `dominance_collapse[node_id]={collapsed,hidden_set,folded_set}`, frame `ui_state_changed(kind=dominance_collapse)`. |
| `GET /api/subsystem_status` | `status.get` → §5 |
| `POST /api/purge_workspace` | `purge.run` → one-transaction clear (persistence.md §3.5) |

---

## §4 — WebSocket Endpoint

```python
@app.websocket("/api/ws/workspace/{workspace_id}")
async def ws_workspace(sock, workspace_id: WorkspaceId, resume: int | None = None)
```
- **Algorithm:**
  1. accept; register `sock` in the workspace fan-out set.
  2. if `resume` and `now - frame_ts(resume) ≤ WS_RESUME_WINDOW` → replay buffered frames `> resume` in `frame_seq` order; else send a fresh full snapshot (`concept_changed`×N + `umap_canonical` + `ui_state_changed`).
  3. loop: `await broadcaster.next(workspace_id)`; assign monotone `frame_seq`; if backlog `> WS_BACKPRESSURE_HIGHWATER` shed sheddable types (errors.md §2); `await sock.send_json(frame)`.
  4. on disconnect → deregister; keep the 5-min ring buffer for `?resume`.
- **Invariant** — `frame_seq` strictly increases per workspace; scan `chunk_added` + `umap_canonical` are **dual-routed** here (not only a per-snapshot socket) (layout.md / §18.1).

---

## §5 — `GET /api/subsystem_status`

```python
def subsystem_status() -> SubsystemStatus
```
Probes each wrapper's `loaded` + `fake_env`; `all_real = AND(loaded && !fake_env for slm,embedder,selenium,langgraph,kuzu)`; includes `apparition_mode`. Pure read; never mutates. **CI asserts `all_real:true`** before contract scenarios (`repl.md`).

---

## §6 — Exception Mapping

**Realized:** handlers raise FastAPI `HTTPException(status_code=...)` inline at the route/service boundary (fixture-delete → 409, subsystem failure → 503, validation → 422/400, not-found → 404), per the `errors.md` §1 status/disposition contract. The single central exception-handler mapping a typed-exception taxonomy (`SubsystemDownError`/`FixtureGuardError`/…) — including `SubsystemDownError → CascadeScheduler.halt()` — is the design-intent OOP refactor (errors.md §1), not yet realized as distinct classes. Unhandled exceptions → 500 + logged; never a silent stub fallback (§13.4).

---

## §7 — Excluded
CORS/static-serving/uvicorn config (deployment, below the spec line); the Symbolic-register framing.
