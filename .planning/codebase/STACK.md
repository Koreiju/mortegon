# Technology Stack

**Analysis Date:** 2026-06-20

## Languages

**Primary:**
- Python 3.13 - Entire backend (`backend/`, `app.py`, `scripts/`). Targeted by `mypy.ini` (`python_version = 3.13`); verified runtime is `Python 3.13.14`.
- JavaScript (vanilla ES modules) - the served editor/projector frontend in `backend/static/js/fe/`.

**Secondary:**
- HTML / Jinja2 templates - `backend/templates/`.
- CSS - `backend/static/css/`.
- A small bundled-ESM source tree (`frontend_src/milkdown_slate.mjs`), compiled by esbuild and never served unbundled — the only frontend code with a build step.

## Runtime

**Environment:**
- Python 3.13 (CPython). Modules addressed as `backend.<sub>.<mod>` via absolute path on `sys.path` (no top-level `__init__.py`; `namespace_packages = True` in `mypy.ini`). `app.py` appends repo root to `sys.path`.
- ASGI server: Uvicorn `0.40.0`. Default bind `127.0.0.1:8080` (`app.py::_serve`, `backend/main.py`).
- Browser runtime for frontend: ES modules + `<script type=module>`; `.mjs` MIME explicitly registered in `backend/main.py` (`mimetypes.add_type("text/javascript", ".mjs")`) because Windows misreports the default MIME and browsers refuse to load `type=module` scripts otherwise.

**Package Manager:**
- Python: pip with pinned versions in `backend/requirements.txt` (production); test deps in `backend/test_requirements.txt`.
- Node: npm. Root `package.json` + `package-lock.json` present. Lockfile: present.
- No `pyproject.toml` / `setup.py` - dependencies are managed via the requirements text files only.

## Frameworks

**Core (backend):**
- FastAPI `0.127.0` - HTTP + WebSocket API. App constructed in `backend/main.py` (`app = FastAPI(...)`); routes in `backend/api/routes.py` (136 `@router.*` decorators incl. WebSocket endpoints).
- Pydantic `2.12.5` - Request/response models, structured SLM output validation.
- Uvicorn `0.40.0` - ASGI server (`app.py`).
- Jinja2 (via `fastapi.templating.Jinja2Templates`) - server-rendered `index.html`.

**Core (frontend):**
- Vanilla-JS greenfield "magic markdown" frontend under `backend/static/js/fe/` (ES `.mjs` modules: `magic_markdown.mjs`, `magic_markdown_gestures.mjs`, `magic_markdown_halo.mjs`, `magic_markdown_panel.mjs`, `projector.mjs`, `store.mjs`, `gateway.mjs`). No build step for this tree — served as raw static assets, mounted at `/static` (`backend/main.py:71`).
- `@milkdown/*` (`core`, `ctx`, `preset-commonmark`, `prose`, `utils`, all `^7.21.2`) - the controlled-view editable-slate layer added on top of the magic-markdown tree (`docs/MILKDOWN_SLATE_GOAL.md`). Authored at `frontend_src/milkdown_slate.mjs`, bundled via esbuild into `backend/static/js/fe/vendor/milkdown_slate.bundle.mjs`, and loaded by the served `.mjs` tree behind `?slate=milkdown`.
- The 3D projector (`backend/static/js/fe/projector.mjs`) renders the backend-computed 6D-UMAP + HSV-colored + azimuth-aware layout and the halo retrieval phantoms — no client-side UMAP/embedding math.
- No React/MDX dependency remains in the served app (the prior `@mdxeditor/editor` line is gone from `package.json`; Milkdown is the only editor-library dependency now).

**Testing:**
- pytest + pytest-asyncio - Backend tests (`backend/test_requirements.txt`, `backend/tests/`).
- httpx - Async test client.
- Node's built-in test runner (`node --test`) - frontend unit tests co-located as `*.test.mjs` in `backend/static/js/fe/` (e.g. `magic_markdown.test.mjs`, `magic_markdown_gestures.test.mjs`, `magic_markdown_halo.test.mjs`, `magic_markdown_panel.test.mjs`, `projector.test.mjs`, `spine.test.mjs`, `integration.test.mjs`); run via `npm run test:fe`.
- Playwright `@playwright/test ^1.49.0` - browser e2e, `frontend_e2e/` (`black_slate.spec.js`, `edit.spec.js`, `halo.spec.js`, `milkdown.spec.js`, `projector.spec.js`); config at `frontend_e2e/playwright.config.js`; run via `npm run test:e2e`.
- REPL verification harness - `scripts/sim_frontend.py` (~160+ actions, 19 categories) driven via `python app.py --repl`; `env-scenario --name full-smoke` runs the 92-scenario contract, asserted green in both stub and real-stack modes.

**Build/Dev:**
- esbuild `^0.28.1` - bundles ONLY the Milkdown layer: `npm run build:milkdown` runs `esbuild frontend_src/milkdown_slate.mjs --bundle --format=esm --outfile=backend/static/js/fe/vendor/milkdown_slate.bundle.mjs`.
- mypy - Gradual static typing (`mypy.ini`). Permissive global defaults; per-module strictness for `backend.services.ids`, `backend.services.concept_lifecycle`, `backend.services.settings`, `backend.dom.pipeline`. Excludes `backend_slow/`, `kuzu_db/`, `snapshots/`, `logs/`, `__pycache__/`, `test_packages/`, `scripts/diag_*`.

## Key Dependencies

**Critical (no-mocks subsystems, §8D.46):**
- `gpt4all==2.8.2` - On-device SLM (`backend/services/slm_client.py`) AND nomic embedder (`backend/services/embedding_service.py` / `Embed4All`, `backend/services/chunk_instance_embedder.py`). Production SLM model: `Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf` (Llama overrides rejected loudly by `slm_client.py::_resolve_model_name`).
- `einops>=0.7.0` - tensor reshape support for the embedding/SLM stack.
- `langgraph==1.1.9` - Compute-graph / agent compile chains (`langgraph.graph.StateGraph`) in `backend/agent/langgraph_loop.py`, `backend/agent/shadow_resolver.py`, `backend/services/conceptual_compute.py`, `backend/api/routes.py`. Now correctly pinned in `backend/requirements.txt` (previously imported but unlisted). No fake gate — a missing import is a hard error.
- `selenium==4.39.0` + `webdriver-manager==4.0.2` - Live web scanner (`backend/services/selenium_client.py::WebBrowserManager`). Firefox via bundled `backend/drivers/geckodriver.exe`. Now pinned (previously unlisted).
- `kuzu==0.11.3` - Embedded graph database (`backend/database.py`). File-based layout (`kuzu_db/data.kuzu`); pin corrected from the stale `0.3.2`.

**Infrastructure:**
- `numpy==2.1.3` - Embedding vectors / layout math across services.
- `umap-learn==0.5.9.post2` - real UMAP fit for the 6D chunk/ontology layout (replaces the SVD placeholder; backs the projector's HSV-azimuth render).
- `scikit-learn==1.6.1` - TF-IDF + ML utilities (chunk-side retrieval pipeline).
- `networkx==3.3` - Graph operations / PageRank support.
- `datasketch==1.9.0` - MinHash / LSH (containment / dedup, content-tree dedup §U).
- `Pillow>=10.2.0` - Image handling (media pipeline).
- `aiohttp>=3.9.3` - Async HTTP client (outbound image-proxy fetches).
- `psutil` (optional, not in `requirements.txt`) - Kuzu lock-holder diagnostics (`backend/database.py::_find_lock_holders`, guarded import).

## Configuration

**Environment:**
- Settings via `WFH_<UPPER_SNAKE_FIELD>` env vars (`backend/services/settings.py`; dataclass fields auto-bound to `WFH_*`).
- Key knobs (see `CLAUDE.md`): `WFH_FAKE_SLM`, `WFH_FAKE_EMBEDDER`, `NO_WEBDRIVER` (harness-only gates, forbidden in production); `WFH_SLM_MODEL` (default `Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf`, Llama rejected loudly); `WFH_SLM_DEVICE=cuda`, `WFH_EMBEDDER_DEVICE=cuda` (cpu permitted as a real-to-real swap); `WFH_DB_PATH` (Kuzu path override, default `<repo>/kuzu_db`); `WFH_BACKEND_URL` (aligns the REPL's `:8000` default with the server's actual `:8080`).
- No `.env` file detected. GGUF model binaries live in an external cache (`~/.cache/gpt4all/`) and are gitignored.

**Build:**
- `mypy.ini` - Type-check config.
- `package.json` / `package-lock.json` - npm dependencies (`@milkdown/*` runtime deps; `@playwright/test` + `esbuild` dev deps).
- `frontend_e2e/playwright.config.js` - Playwright e2e config.
- No `tsconfig.json`; no bundler config for the main `fe/` tree (intentionally raw ESM, only the Milkdown layer is bundled).

## Platform Requirements

**Development:**
- Python 3.13, pip, npm.
- CUDA-capable GPU for real SLM + embedder runs (CPU override exists for the embedder only via `WFH_EMBEDDER_DEVICE=cpu`; harness fake gates avoid GPU entirely).
- Firefox + bundled `geckodriver.exe` (Windows) for live Selenium scans.
- Windows-first environment (PowerShell; `.exe` driver; Windows-specific lock-file handling in `backend/database.py`), but paths are largely OS-agnostic in code.

**Production:**
- Single Uvicorn process serving FastAPI on `127.0.0.1:8080` plus the static frontend; logs mirrored to `logs.txt` via the `_Tee` setup in `app.py`. No containerization / CI deploy config detected in scope.

---

*Stack analysis: 2026-06-20*
