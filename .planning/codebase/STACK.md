# Technology Stack

**Analysis Date:** 2026-06-14

## Languages

**Primary:**
- Python 3.13 - Entire backend (`backend/`, `app.py`, `scripts/`). Targeted by `mypy.ini` (`python_version = 3.13`).
- JavaScript (ES modules + classic scripts) - Custom 3D/2D frontend in `backend/static/js/`.

**Secondary:**
- HTML / Jinja2 templates - `backend/templates/index.html`, `backend/templates/editor.html`.
- CSS - `backend/static/css/styles.css`, `backend/static/styles.css`.

## Runtime

**Environment:**
- Python 3.13 (CPython). Modules addressed as `backend.<sub>.<mod>` via absolute path on `sys.path` (no top-level `__init__.py`; `namespace_packages = True` in `mypy.ini`). `app.py` appends repo root to `sys.path`.
- ASGI server: Uvicorn (`uvicorn==0.27.1`). Default bind `127.0.0.1:8080` (`app.py::_serve`, `backend/main.py`).
- Browser runtime for frontend: ES modules + `<script type=module>`; `.mjs` MIME registered in `backend/main.py` (`mimetypes.add_type("text/javascript", ".mjs")`).

**Package Manager:**
- Python: pip with pinned + floor-version `backend/requirements.txt`; test deps in `backend/test_requirements.txt`.
- Node: npm. Root `package.json` + `package-lock.json` present. Lockfile: present.
- No `pyproject.toml` / `setup.py` — dependencies are managed via the requirements text files only.

## Frameworks

**Core (backend):**
- FastAPI `0.110.0` - HTTP + WebSocket API. App constructed in `backend/main.py` (`app = FastAPI(...)`); routes in `backend/api/routes.py` (138 route decorators incl. one WebSocket).
- Pydantic `2.6.2` - Request/response models, structured SLM output validation.
- Uvicorn `0.27.1` - ASGI server (`app.py`).
- Jinja2 (via `fastapi.templating.Jinja2Templates`) - Server-rendered `index.html`.

**Core (frontend):**
- Three.js `r128` (CDN: `cdnjs.cloudflare.com/.../three.js/r128/three.min.js`) + OrbitControls (`cdn.jsdelivr.net/npm/three@0.128.0`) - the 3D layout/projection surface (`backend/templates/index.html` lines 417-420). Entry module `backend/static/js/chunk_projector.js`; mixins under `backend/static/js/cp/`.
- Vanilla-JS greenfield "magic markdown" frontend under `backend/static/js/fe/` (ES `.mjs` modules: `magic_markdown.mjs`, `projector.mjs`, `store.mjs`, `gateway.mjs`). No build step — served as raw static assets.
- `@mdxeditor/editor` `^4.0.3` - the ONLY npm dependency (root `package.json`); pulls a large React/MDX/micromark/radix-ui tree into `node_modules/` (used by the `fe/` markdown editor work).
- Font Awesome 6.0.0 (CDN) for icons.

**Testing:**
- pytest + pytest-asyncio - Backend tests (`backend/test_requirements.txt`, `backend/tests/`).
- httpx - Async test client.
- Node test runner - `*.test.mjs` files under `backend/static/js/fe/` and `cp/` (e.g. `hsv_color.test.mjs`); `cp/package.json` declares `"type": "module"` so the pure helpers run under `node`.
- REPL verification harness - `scripts/sim_frontend.py` (~160+ actions, 19 categories) driven via `python app.py --repl`; `env-scenario --name full-smoke` runs the 92/96 scenario contract.

**Build/Dev:**
- mypy - Gradual static typing (`mypy.ini`). Permissive global defaults; per-module strictness for `backend.services.ids`, `backend.services.concept_lifecycle`, `backend.services.settings`, `backend.dom.pipeline`. Excludes `backend_slow/`, `kuzu_db/`, `snapshots/`, `scripts/diag_*`.
- No bundler/transpiler for the frontend — assets are cache-busted by source mtime via `_asset_version()` in `backend/main.py`.

## Key Dependencies

**Critical (model + compute):**
- `gpt4all>=2.7.0` - On-device SLM (`backend/services/slm_client.py`) AND nomic embedder (`backend/services/embedding_service.py` via `Embed4All`). The backend is `llama.cpp` under GPT4All (note thread-safety serialization in `embedding_service.py`).
- `langgraph` - Compute-graph / agent compile chains (`langgraph.graph.StateGraph, END` in `backend/agent/langgraph_loop.py`, `backend/services/conceptual_compute.py`, `backend/api/routes.py`). **Not pinned in `requirements.txt`** — installed out-of-band; missing = hard error per the no-mocks contract.
- `selenium` + `webdriver_manager` - Live web scanner (`backend/services/selenium_client.py::WebBrowserManager`). Firefox via bundled `backend/drivers/geckodriver.exe`. **Not pinned in `requirements.txt`.**
- `kuzu==0.3.2` - Embedded graph database (`backend/database.py`). Note: `requirements.txt` pins `0.3.2` but `CLAUDE.md` documents a kuzu ≥ 0.11 file-based layout (`kuzu_db/data.kuzu`) — version drift to verify.
- `scikit-learn>=1.4.0` - TF-IDF + ML utilities (chunk-side retrieval pipeline, `backend/services/tfidf_service.py`).
- `networkx>=3.2.1` - Graph operations / PageRank support.
- `numpy` - Embedding vectors / layout math (imported across services; listed in `test_requirements.txt`, transitively required at runtime).

**Infrastructure:**
- `aiohttp>=3.9.3` - Async HTTP client.
- `datasketch>=1.6.4` - MinHash / LSH (containment / dedup, `backend/services/chunk_containment.py`).
- `einops>=0.7.0` - Tensor rearrange (embedding/model paths).
- `Pillow>=10.2.0` - Image handling (`backend/services/media_pipeline.py`).
- `psutil` (optional) - Kuzu lock-holder diagnostics (`backend/database.py::_find_lock_holders`, guarded import).

## Configuration

**Environment:**
- Settings via `WFH_<UPPER_SNAKE_FIELD>` env vars (`backend/services/settings.py`; dataclass fields auto-bound to `WFH_*`).
- Key knobs (see `CLAUDE.md`): `WFH_FAKE_SLM`, `WFH_FAKE_EMBEDDER`, `NO_WEBDRIVER` (harness gates); `WFH_SLM_MODEL` (default `Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf`, Llama rejected loudly in `slm_client.py::_resolve_model_name`); `WFH_SLM_DEVICE=cuda`, `WFH_EMBEDDER_DEVICE=cuda`; `WFH_DB_PATH` (Kuzu path override, default `<repo>/kuzu_db`); `WFH_BACKEND_URL`.
- No `.env` file detected. GGUF model binaries live in an external cache (`~/.cache/gpt4all/`) and are gitignored.

**Build:**
- `mypy.ini` - Type-check config.
- `package.json` / `package-lock.json` - npm (single dependency).
- `.clj-kondo/`, `.lsp/`, `.vscode/` - Editor/LSP tooling dirs (incidental).

## Platform Requirements

**Development:**
- Python 3.13, pip, npm.
- CUDA-capable GPU for real SLM + embedder runs (CPU fallback exists in `embedding_service.py`; harness fake gates avoid GPU entirely).
- Firefox + bundled `geckodriver.exe` (Windows) for live Selenium scans.
- Windows-first environment (PowerShell; `.exe` driver), but paths are OS-agnostic in code.

**Production:**
- Single Uvicorn process serving FastAPI on `127.0.0.1:8080` plus the static frontend; logs mirrored to `logs.txt` via the `_Tee` setup in `app.py`. No containerization / CI deploy config detected in scope.

---

*Stack analysis: 2026-06-14*
