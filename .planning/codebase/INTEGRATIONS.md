# External Integrations

**Analysis Date:** 2026-06-14

This is a **local-first / self-hosted** application: there are no third-party SaaS APIs, no cloud auth provider, and no outbound payment/identity calls. The "integrations" are on-device model runtimes, an embedded graph database, a headful browser scanner, and CDN-served frontend libraries. Per the §8D.46 no-mocks contract (`CLAUDE.md`), production paths run these real subsystems with no silent stub fallback.

## APIs & External Services

**Model runtimes (on-device, no network API):**
- GPT4All SLM - Local quantized inference via `gpt4all` (llama.cpp backend).
  - Client: `backend/services/slm_client.py`
  - Model: `Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf` (default; Llama overrides rejected). Device: CUDA (`WFH_SLM_DEVICE`).
  - GGUF loaded from external cache `~/.cache/gpt4all/`.
- GPT4All nomic embedder - 768-dim text embeddings via `Embed4All`.
  - Client: `backend/services/embedding_service.py`
  - Models: `nomic-embed-text-v1.5.f16.gguf` (default), `nomic-embed-text-v1.f16.gguf` (per-instance chunk embedder). Device: CUDA (`WFH_EMBEDDER_DEVICE`).
  - Uses nomic `search_document:` / `search_query:` task prefixes. llama.cpp serialized per model via `RLock` (not thread-safe).

**Compute orchestration:**
- LangGraph - Compute-graph / agent compile chains via `langgraph.graph.StateGraph` + `END`.
  - Used in `backend/agent/langgraph_loop.py`, `backend/services/conceptual_compute.py`, `backend/api/routes.py`.
  - No fake gate — a missing import is a hard error by design.

**Web scanner (outbound browser automation):**
- Selenium + Firefox - Live headful web scanning of arbitrary user URLs (e.g. `https://archive.org/search?query=university+library`).
  - Client: `backend/services/selenium_client.py::WebBrowserManager`
  - Driver: bundled `backend/drivers/geckodriver.exe`; `webdriver_manager.firefox.GeckoDriverManager` as fallback resolver.
  - Gate: `NO_WEBDRIVER=1` skips driver init at boot (`backend/main.py` lifespan).

**Frontend libraries (CDN):**
- Three.js r128 + OrbitControls - `cdnjs.cloudflare.com`, `cdn.jsdelivr.net` (`backend/templates/index.html`).
- Font Awesome 6.0.0 - `cdnjs.cloudflare.com`.

## Data Storage

**Databases:**
- Kuzu (embedded graph DB) - single workspace store for ConceptNode/ConceptEdge records, TF-IDF state, concept graph, web ontology, meta-cognition substrate.
  - Connection: `backend/database.py` (`init_db`, `close_db`). Path via `WFH_DB_PATH`, default `<repo>/kuzu_db` (file-based: nests `<path>/data.kuzu` for legacy directory layout).
  - Client: `kuzu` Python driver. Single embedded process; lock-holder diagnostics via `psutil` (`_find_lock_holders`).

**File Storage:**
- Local filesystem only. Scan artifacts in `snapshots/`; logs in `logs/` + `logs.txt`; media (`backend/static/*.mp4`, fonts) served statically.

**Caching:**
- In-process model cache (`_MODEL_CACHE` in `embedding_service.py`). No external cache (Redis/etc.).
- Static asset cache-busting via source-mtime version stamp (`backend/main.py::_asset_version`).

## Authentication & Identity

**Auth Provider:**
- None. No login, sessions, tokens, or user accounts. CORS is fully open (`allow_origins=["*"]`, `backend/main.py`) — single-operator local app.

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry/etc.). Errors surface as FastAPI HTTP responses (`backend/api/errors.py`, `register_workflow_error_handler`); subsystem failures return 503 + halt cascade (no silent degradation).

**Logs:**
- All stdout/stderr + Python `logging` + uvicorn logs mirrored to `logs.txt` via `_Tee` (`app.py::_setup_file_logging`, truncated per run).
- Live operator view: REPL `watch-activity` 7-row ANSI in-place dashboard (`scripts/sim_frontend.py`).
- Subsystem health: `GET /api/subsystem_status` reports `{slm, embedder, selenium, langgraph, all_real}`.

## CI/CD & Deployment

**Hosting:**
- Self-hosted single Uvicorn process (`python app.py`, default `127.0.0.1:8080`). No cloud deploy config in scope.

**CI Pipeline:**
- No CI config files detected. Verification is the REPL scenario contract (`env-scenario --name full-smoke`, 92/96 scenarios) + live probes under `scripts/probe_live_*.py`, asserted green in both stub and real-stack modes.

## Environment Configuration

**Required env vars (real-stack production):**
- None strictly required (sensible defaults). Operationally: a downloaded GGUF in `~/.cache/gpt4all/`, a working Firefox + geckodriver, and a CUDA GPU.
- Optional overrides: `WFH_DB_PATH`, `WFH_SLM_MODEL`, `WFH_SLM_DEVICE`, `WFH_EMBEDDER_DEVICE`, `WFH_BACKEND_URL`.
- Harness-only gates (forbidden in production): `WFH_FAKE_SLM`, `WFH_FAKE_EMBEDDER`, `NO_WEBDRIVER`.

**Secrets location:**
- No secrets. No `.env`, no API keys, no credential files (all subsystems are local). Model binaries are gitignored, not secret.

## Webhooks & Callbacks

**Incoming:**
- WebSocket: `GET /ws/workspace/{workspace_id}` (`backend/api/routes.py:515`) - monotone per-workspace frame stream; `?resume=<seq>` replays last 5 minutes (`backend/services/ws_replay.py`). Frontend telemetry posted back via `cp/telemetry.js` MutationObservers, drained through `ui-telemetry` REPL actions.
- ~138 REST routes under `/api/*` (`backend/api/routes.py`), e.g. `/api/chunk_search`, `/api/compile_pipeline`, `/api/concepts`, `/api/concept_edges`, `/api/agent/tick`, `/api/ui/pin`, `/api/subsystem_status`, `/api/maintenance/cleanup_test_artifacts`.

**Outgoing:**
- Selenium HTTP fetches to user-specified scan targets only (e.g. archive.org). No other outbound calls except CDN asset loads from the browser.

## Notes on Out-of-Scope Variants

- `backend_slow/` - Legacy snapshot (api/dom/mapper/static/templates mirror); excluded from the active import graph and from mypy. Not an integration target.
- `_legacy_frontend/` - Pre-greenfield monolithic frontend (`chunk_projector.monolith.js`, `index_fe.html`). Superseded by `backend/static/js/cp/` + `fe/`.

---

*Integration audit: 2026-06-14*
