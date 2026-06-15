# Codebase Structure

**Analysis Date:** 2026-06-14

## Directory Layout

```
web_fiber_haptics/
├── app.py                      # Process entry: stdout/stderr tee → logs.txt, uvicorn boot
├── CLAUDE.md                   # Persistent design lodestar (source-of-truth pointers)
├── README.md
├── package.json                # Frontend JS deps (Three.js etc.)
├── mypy.ini
├── backend/                    # All Python application code (PRIMARY)
│   ├── main.py                 # FastAPI app, lifespan, page routes
│   ├── database.py             # Kuzu schema + connection (ConceptNode/Edge + chunk tables)
│   ├── rag_store.py            # Retrieval store helpers
│   ├── dom_deep_serializer.py  # DOM serialization
│   ├── js_utilities.py         # JS injection helpers for Selenium
│   ├── wfh_imports.py          # Shared import shims
│   ├── api/                    # HTTP/WS surface
│   │   ├── routes.py           # ALL 138 REST routes + 3 WS endpoints (~4800 lines)
│   │   ├── ws_frames.py        # WS frame builders (typed)
│   │   └── errors.py           # Workflow error handler
│   ├── services/               # ~55 compute services (the engine room)
│   ├── dom/                    # DOM → trie → pattern → chunk pipeline
│   ├── mapper/                 # Snapshot mapper, chunk builder/absorber/render
│   ├── ontology/               # Concept-graph models, cypher engine, layout generator
│   ├── agent/                  # LangGraph loop, shadow resolver
│   ├── agentic/                # Fluid-session agentic flow (Phase 9)
│   ├── analytics/              # (legacy graph-analytics — forbidden in design)
│   ├── concept_builder/        # Concept construction helpers
│   ├── demos/                  # Demo scaffolding
│   ├── drivers/                # geckodriver.exe (Selenium)
│   ├── static/                 # Frontend assets (served at /static)
│   │   ├── js/cp/              # 3D chunk-projector modules (Three.js)
│   │   ├── js/fe/              # Greenfield ES-module (.mjs) editor (§T/§U/§V)
│   │   ├── js/chunk_projector.js  # 3D projector entry
│   │   └── css/styles.css
│   ├── templates/              # index.html, editor.html (Jinja2)
│   └── tests/                  # 45 pytest modules
├── scripts/                    # REPL harness + live probes + diagnostics
├── docs/                       # Design docs (source of truth — see CLAUDE.md)
├── backend_slow/               # VARIANT backend (api/dom/mapper/static/templates) — not active
├── _legacy_frontend/           # LEGACY monolith frontend — superseded
├── kuzu_db/                    # Kuzu DB artifacts (ignore)
├── snapshots/                  # Scan snapshots (ignore)
├── logs/ · logs.txt            # Runtime logs (ignore)
└── node_modules/               # JS deps (ignore)
```

## Directory Purposes

**`backend/services/`:**
- Purpose: all backend computation. The mutation chokepoint and both vectorization pipelines live here.
- Contains: lifecycle dispatcher, scanner, layout, TF-IDF, concept index, compile, agent, UI state, evolution log, fixtures.
- Key files: `concept_lifecycle.py`, `layout_service.py`, `concept_index_service.py`, `tfidf_service.py`, `global_tfidf_store.py`, `continuous_scanner.py`, `compile_pipeline.py`, `conceptual_compute.py`, `slm_client.py`, `agent_runtime.py`, `evolution_log.py`, `ui_state_service.py`, `foundation_fixtures.py`, `retrieval_service.py`, `rollout_coordinator.py`, `db_janitor.py`, `ids.py`.

**`backend/api/`:**
- Purpose: the only HTTP/WS surface.
- Key files: `routes.py` (everything), `ws_frames.py`, `errors.py`.

**`backend/dom/`:**
- Purpose: DOM distillation pipeline (scan → distilled content tree → patterns).
- Key files: `scanner.py`, `pipeline.py`, `content_tree.py`, `content_distiller_simple.py`, `xpath_tree_builder.py`, `dom_wl_miner.py`.

**`backend/mapper/`:**
- Purpose: snapshot mapping + chunk construction.
- Key files: `mapper.py`, `chunk_builder.py`, `chunk_absorber.py`, `chunk_render.py`, `pipeline_runner.py`, `snapshot_store.py`.

**`backend/ontology/`:**
- Purpose: concept-graph domain models + cypher.
- Key files: `models.py`, `cypher_engine.py`, `knowledge_graph.py`, `layout_generator.py`, `field_types.py`.

**`backend/static/js/cp/`:**
- Purpose: 3D chunk projector (UMAP-radial force-directed render).
- Key files: `layout.js`, `force_layout.js`, `concept_graph.js`, `instance_manager.js`, `interaction.js`, `workspace.js`, `scanner.js`, `search.js`, `billboard.js`, `sprite_manager.js`.

**`backend/static/js/fe/`:**
- Purpose: greenfield ES-module editor (black-slate magic-markdown panels + halo).
- Key files: `magic_markdown.mjs`, `magic_markdown_gestures.mjs`, `magic_markdown_halo.mjs`, `magic_markdown_panel.mjs`, `projector.mjs`, `store.mjs`, `gateway.mjs` (+ co-located `*.test.mjs`).

**`scripts/`:**
- Purpose: verification harness + live evidence probes.
- Key files: `sim_frontend.py` (REPL, ~160 actions), `probe_live_*.py` (live all-real evidence per lodestar facet), `probe_no_mocks.py`, `reset_env.py`.

## Key File Locations

**Entry Points:**
- `app.py`: process launch + logging tee.
- `backend/main.py`: FastAPI app, lifespan, page routes (`/`, `/editor`, `/legacy`).

**Configuration:**
- `mypy.ini`: type-check config.
- `package.json`: frontend deps.
- Environment knobs (WFH_FAKE_SLM, NO_WEBDRIVER, WFH_DB_PATH, etc.): see `CLAUDE.md`.

**Core Logic:**
- `backend/services/concept_lifecycle.py`: mutation chokepoint.
- `backend/database.py`: schema (ConceptNode `:240`, ConceptEdge `:433`).
- `backend/api/routes.py`: all routes.

**Testing:**
- `backend/tests/`: 45 pytest modules.
- `scripts/sim_frontend.py`: `env-scenario` contract harness (92 scenarios).
- `scripts/probe_live_*.py`: live all-real probes.

## Naming Conventions

**Files:**
- snake_case Python modules: `concept_lifecycle.py`, `layout_service.py`.
- Services named `<domain>_service.py` or `<domain>.py`; probes `probe_<facet>.py`; live probes `probe_live_<facet>.py`.
- Frontend: `.js` for cp/ (legacy-style modules), `.mjs` for greenfield fe/ (ES modules), co-located `*.test.mjs`.

**Directories:**
- Backend subpackages by concern: `api`, `services`, `dom`, `mapper`, `ontology`, `agent`.
- Variant/legacy trees prefixed `backend_slow/` and `_legacy_frontend/`.

## Where to Add New Code

**New backend capability (a service):**
- Primary code: `backend/services/<name>.py` (sibling to existing services; do not nest pipelines).
- Wire into a route: add handler in `backend/api/routes.py`.
- Mutations MUST call `backend/services/concept_lifecycle.py` (never mutate concepts directly).
- New data: model on existing ConceptNode/ConceptEdge — a new fixture (`foundation_fixtures.py`), compiled-from-scans peer (`compiled_from_scans.py`), or Python-API tree (`python_api_materialiser.py`). Do NOT add a new Kuzu table.

**New REST/WS route:**
- Add to `backend/api/routes.py`; add frame builder to `backend/api/ws_frames.py` if it broadcasts.

**New frontend (greenfield editor):**
- Implementation: `backend/static/js/fe/*.mjs` with a co-located `*.test.mjs`.

**New 3D render feature:**
- Implementation: `backend/static/js/cp/*.js`.

**Tests:**
- Unit/integration: `backend/tests/test_<area>.py`.
- New scenario: register in `scripts/sim_frontend.py`; live evidence probe in `scripts/probe_live_<facet>.py`.

**Utilities:**
- Shared IDs/helpers: `backend/services/ids.py`; import shims: `backend/wfh_imports.py`.

## Special Directories

**`backend_slow/`:**
- Purpose: a parallel/variant backend tree (api/dom/mapper/static/templates).
- Generated: No. Committed: Yes. Not the active server — do not extend.

**`_legacy_frontend/`:**
- Purpose: superseded monolith frontend (`chunk_projector.monolith.js`).
- Committed: Yes. Reference only; new frontend work goes to `backend/static/js/fe/`.

**`backend/analytics/`:**
- Purpose: legacy graph-analytics retrieval (depth, subtree_size, wl_hash) — explicitly forbidden by design; do not call from new code.

**`kuzu_db/`, `snapshots/`, `logs/`, `node_modules/`, `__pycache__/`, `.mypy_cache/`:**
- Generated: Yes. Ignore (gitignored / runtime artifacts).

---

*Structure analysis: 2026-06-14*
