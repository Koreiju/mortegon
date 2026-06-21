# External Integrations

**Analysis Date:** 2026-06-20

This is a **local-first / self-hosted** application: there are no third-party SaaS APIs, no cloud auth provider, and no outbound payment/identity calls. The "integrations" are on-device model runtimes, an embedded graph database, a headful browser scanner, and a small set of npm-distributed editor libraries bundled at build time. Per the §8D.46 no-mocks contract (`CLAUDE.md`), production paths run these real subsystems with no silent stub fallback.

## APIs & External Services

**Model runtimes (on-device, no network API):**
- GPT4All SLM - local quantized inference via `gpt4all==2.8.2` (llama.cpp backend).
  - Client: `backend/services/slm_client.py`
  - Model: `Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf` (default; Llama overrides rejected loudly by `_resolve_model_name`). Device: CUDA (`WFH_SLM_DEVICE`).
  - GGUF loaded from external cache `~/.cache/gpt4all/`.
  - Surface: `async_stream_chat`, `generate_text`, `generate_json`, `generate_structured` (Pydantic/JSON-schema validated).
  - Failure mode: `SLMUnavailableError` → FastAPI 503 + cascade halt (`backend/api/errors.py::register_slm_unavailable_handler`); never a silent stub substitution in production.
  - Stub gate (harness-only, forbidden in production): `WFH_FAKE_SLM=1`.
- GPT4All nomic embedder - 768-dim text embeddings via `Embed4All`.
  - Client: `backend/services/embedding_service.py`; batch/dedup wrapper `backend/services/chunk_instance_embedder.py::ChunkInstanceEmbedder`.
  - Models: `nomic-embed-text-v1.5.f16.gguf` (default), `nomic-embed-text-v1.f16.gguf` (per-instance chunk embedder). Device: CUDA (`WFH_EMBEDDER_DEVICE`, `cpu` permitted as a real-to-real swap).
  - Uses nomic `search_document:` / `search_query:` task prefixes; llama.cpp calls serialized per model (not thread-safe).
  - Page-level embedding = L2-normalized mean of deduped per-instance embeddings.
  - Stub gate (harness-only): `WFH_FAKE_EMBEDDER=1` (hash-deterministic 768-dim fake).

**Compute orchestration:**
- LangGraph `1.1.9` - Compute-graph / agent compile chains via `langgraph.graph.StateGraph`.
  - Used in `backend/agent/langgraph_loop.py`, `backend/agent/shadow_resolver.py`, `backend/services/conceptual_compute.py`, `backend/api/routes.py`.
  - No fake gate — a missing import is a hard error by design.
  - Now correctly pinned in `backend/requirements.txt` (closed the prior unlisted-dependency gap).

**Web scanner (outbound browser automation):**
- Selenium `4.39.0` + Firefox - live headful web scanning of arbitrary user URLs, primary lodestar target `https://archive.org/search?query=university+library` (also general archive.org pages and other sites).
  - Client: `backend/services/selenium_client.py::WebBrowserManager` (thread-safe singleton; eager boot at FastAPI startup via `backend/main.py` lifespan unless `NO_WEBDRIVER=1`).
  - Driver: bundled `backend/drivers/geckodriver.exe`; `webdriver-manager==4.0.2` (`GeckoDriverManager`) as fallback resolver.
  - Hardening: stale Firefox profile-lock cleanup (`parent.lock` / `.parentlock` / `lock`); custom per-host Referer derivation to avoid 502s from archive.org/Wikimedia CDN image fetches (`backend/api/routes.py` ~lines 1907-1940).
  - DOM pipeline: `backend/dom/scanner.py` (MutationObserver-based settle detection, tuned around archive.org/YouTube settle timing), `backend/dom/content_tagger.py` (content-tree extraction/dedup, §U), `backend/dom_deep_serializer.py`.

**Frontend editor library (npm, bundled — not a runtime network call):**
- `@milkdown/*` `^7.21.2` (core, ctx, preset-commonmark, prose, utils) - the controlled-view editable Markdown surface, authored in `frontend_src/milkdown_slate.mjs`, bundled by esbuild into `backend/static/js/fe/vendor/milkdown_slate.bundle.mjs`, served as a static asset (no CDN fetch at runtime). Loaded behind `?slate=milkdown`.

## Data Storage

**Databases:**
- Kuzu `0.11.3` (embedded graph DB) - single workspace store for ConceptNode/ConceptEdge records, TF-IDF state, concept graph, web ontology, meta-cognition substrate.
  - Connection: `backend/database.py` (`init_db`, `close_db`). Path via `WFH_DB_PATH`, default `<repo>/kuzu_db` (file-based: nests `<path>/data.kuzu` when the path is an existing non-empty directory, for legacy artifact layout support — `_effective_db_path`).
  - Lock-holder diagnostics via optional `psutil` (`_find_lock_holders`, matches `backend.main`/`uvicorn`/`scripts`/`kuzu_db` cmdline markers).
  - Side files alongside the store: `kuzu_db/concept_index_*.json` (per-workspace ConceptIndex), `kuzu_db/evolution_log_*.jsonl` (append-only edit log), `kuzu_db/layout_frame_*.json` (cached layout/ontology broadcasts).
  - Test-DB hygiene: `backend/services/db_janitor.py` - canonical `wfh_test_` temp-DB prefix, `temp_db_dir()` context manager, `sweep_all()` / `POST /api/maintenance/cleanup_test_artifacts` for retention sweeps over legacy-prefix strays and `ws_`-convention side-file orphans; `_default` and human-named workspaces are never swept.

**File Storage:**
- Local filesystem only. Scan artifacts in `snapshots/` (`distilled_html/`, `global_tfidf/`, `backing_versions.json`); logs in `logs/` + `logs.txt`.

**Caching:**
- In-process model cache (`_MODEL_CACHE` in `embedding_service.py`). No external cache (Redis/etc.).

## Authentication & Identity

**Auth Provider:**
- None. No login, sessions, tokens, or user accounts. CORS is fully open (`allow_origins=["*"]`, `backend/main.py`) - single-operator local app.

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry/etc.). Errors surface as FastAPI HTTP responses (`backend/api/errors.py::register_workflow_error_handler`); subsystem failures return 503 + halt cascade (no silent degradation).

**Logs:**
- All stdout/stderr + Python `logging` + uvicorn logs mirrored to `logs.txt` via `_Tee` (`app.py::_setup_file_logging`, truncated per run).
- Live operator view: REPL `watch-activity` seven-row ANSI in-place dashboard (`scripts/sim_frontend.py`) — scan / retrieval / visible 3D / hidden 3D / pinned / compile / subsystems.
- Subsystem health: `GET /api/subsystem_status` reports `{slm, embedder, selenium, langgraph, all_real}` - the no-mocks self-check, asserted `true` before any contract-bearing scenario runs.

## CI/CD & Deployment

**Hosting:**
- Self-hosted single Uvicorn process (`python app.py`, default `127.0.0.1:8080`). No cloud deploy config in scope.

**CI Pipeline:**
- No CI config files detected. Verification is the REPL scenario contract (`env-scenario --name full-smoke`, 92/92 scenarios green in both stub and real-stack modes) plus live probes under `scripts/probe_live_*.py` and the Playwright e2e suite (`frontend_e2e/`, 26/0 passing per the v1 milestone).

## Environment Configuration

**Required env vars (real-stack production):**
- None strictly required (sensible defaults). Operationally: a downloaded GGUF in `~/.cache/gpt4all/`, a working Firefox + geckodriver, and a CUDA GPU.
- Optional overrides: `WFH_DB_PATH`, `WFH_SLM_MODEL`, `WFH_SLM_DEVICE`, `WFH_EMBEDDER_DEVICE`, `WFH_BACKEND_URL`.
- Harness-only gates (forbidden in production): `WFH_FAKE_SLM`, `WFH_FAKE_EMBEDDER`, `NO_WEBDRIVER`.

**Secrets location:**
- No secrets. No `.env`, no API keys, no credential files (all subsystems are local). Model binaries are gitignored, not secret.

## Webhooks & Callbacks

**Incoming:**
- WebSocket workspace stream (`backend/api/routes.py`) - monotone per-workspace frame `seq`; `?resume=<seq>` replays the last 5 minutes; lossy backpressure drops oldest progress frames but always keeps `done`/`error`/latest `generation`. Carries scan progress, layout/ontology frames (incl. the 6D-UMAP/HSV projector frames), agent token streams, and cascade/compile updates to the served frontend (`backend/static/js/fe/gateway.mjs`, `store.mjs`).
- 136 `@router.*` REST + WS routes under `backend/api/routes.py`, e.g. `/api/chunk_search`, `/api/compile_pipeline`, `/api/concepts`, `/api/concept_edges`, `/api/agent/tick`, `/api/ui/pin`, `/api/ontology/layout`, `/api/subsystem_status`, `/api/maintenance/cleanup_test_artifacts`.

**Outgoing:**
- Selenium HTTP fetches to user-specified scan targets only (e.g. archive.org). `aiohttp` outbound fetches for image-proxying CDN-hosted media referenced by scanned pages. No other outbound third-party calls.

---

*Integration audit: 2026-06-20*
