# Codebase Structure

**Analysis Date:** 2026-06-20

## Directory Layout

```
web_fiber_haptics/
├── backend/                      # FastAPI app + all compute services (Python)
│   ├── main.py                   # entry point, port 8080, lifespan, route mounting
│   ├── database.py               # Kuzu init/close, _effective_db_path nesting
│   ├── api/
│   │   ├── routes.py             # the one router — every REST/WS endpoint (~5400 lines)
│   │   ├── ws_frames.py          # typed WS frame vocabulary + builders
│   │   └── errors.py             # workflow / SLM-unavailable error handlers
│   ├── services/                 # ~55 service modules — lifecycle, layout, embedding,
│   │                              # retrieval, agent runtime, evolution log, janitor
│   ├── dom/                      # Selenium scanner + DOM/content-tree pipeline
│   ├── ontology/                 # cypher engine, knowledge graph, field types
│   ├── mapper/                   # legacy chunk mapper/pipeline (pre-greenfield)
│   ├── agent/                    # langgraph_loop, shadow_resolver
│   ├── agentic/                  # fluid_engine, tool_registry, xpath_executor (legacy)
│   ├── analytics/                # loop_closure, segment_embedder
│   ├── demos/                    # demo_agent_loop.py, demo_live_tarot.py
│   ├── templates/
│   │   ├── editor.html           # DEFAULT served surface — greenfield magic-markdown editor
│   │   └── index.html            # legacy 3D-only projector, served at /legacy
│   ├── static/
│   │   ├── css/styles.css
│   │   ├── js/
│   │   │   ├── fe/                # greenfield magic-markdown spine (ESM, tested)
│   │   │   │   ├── store.mjs                  # sole frontend truth
│   │   │   │   ├── gateway.mjs                # the only outbound seam
│   │   │   │   ├── magic_markdown.mjs          # parse/render/registry model
│   │   │   │   ├── magic_markdown_panel.mjs    # DOM mount (panel/graph dual render)
│   │   │   │   ├── magic_markdown_gestures.mjs # pure gesture classifier
│   │   │   │   ├── magic_markdown_halo.mjs     # apparition halo (pure layout + SVG)
│   │   │   │   ├── projector.mjs               # THREE.js 3D Real register
│   │   │   │   ├── vendor/milkdown_slate.bundle.mjs  # bundled Milkdown edit layer
│   │   │   │   └── *.test.mjs                  # one test file per module
│   │   │   ├── cp/                # legacy 3D projector mixins (chunk_projector.js tree)
│   │   │   └── tests/             # legacy cp/* browser test harness (test_runner.js)
│   │   └── *.mp4, *.ttf            # legacy demo media assets
│   └── tests/                     # pytest suite — one test_*.py per service/feature
├── frontend_src/                  # Milkdown SOURCE (pre-bundle) — esbuild → backend/static/js/fe/vendor/
│   └── milkdown_slate.mjs         # controlled-view ProseMirror editor source
├── frontend_e2e/                  # Playwright e2e specs against the live served editor
│   ├── black_slate.spec.js
│   ├── edit.spec.js
│   ├── halo.spec.js
│   ├── milkdown.spec.js
│   ├── projector.spec.js
│   └── playwright.config.js
├── scripts/                       # REPL harness + live evidence probes (no test framework)
│   ├── sim_frontend.py            # the REPL — ~160+ actions, env-scenario contract
│   ├── probe_live_*.py            # §8D.45/47/48/49 live full-stack evidence probes
│   ├── probe_no_mocks.py          # §8D.46 real-subsystem contract verification
│   ├── reset_env.py / reset_state.py
│   ├── run_full_stack_tests.py
│   └── samples/                   # fixture HTML pages for probes
├── docs/                          # the documentation chain (source-of-truth order in CLAUDE.md)
│   ├── USER_REQUIREMENTS_VERBATIM.md
│   ├── DOMAIN_MODEL.md
│   ├── FRONTEND_REDESIGN.md
│   ├── DOC_MAP.md
│   ├── MORTEGON_INTEGRATION_SCHEME.md / CODEBASE_GAP_ANALYSIS.md  # historical
│   ├── object_model/              # one doc per first-class object
│   ├── features/                  # one doc per cross-cutting feature
│   ├── code_constraints/          # must-hold / must-not per programming surface
│   ├── code_architecture/         # implementation blueprint below code_constraints
│   ├── code_specs/                # line-level specs immediately above CODE
│   └── frontend/                  # per-surface frontend reference suite
├── .planning/                      # GSD: roadmap, requirements, phase plans, codebase map
│   ├── PROJECT.md / REQUIREMENTS.md / ROADMAP.md / STATE.md / TEST_MATRIX.md
│   ├── codebase/                  # THIS document set (ARCHITECTURE/STRUCTURE/STACK/...)
│   ├── intel/
│   └── phases/
├── test_packages/                  # large corpus of saved scan fixtures (one dir per scanned site)
├── kuzu_db/                         # default Kuzu DB directory (legacy nesting target)
├── snapshots/                       # scan snapshot artifacts
├── logs/
└── test-results/                    # Playwright output
```

## Directory Purposes

**`backend/services/`:**
- Purpose: every unit of backend computation — the lifecycle dispatcher, both vectorization pipelines, layout, retrieval, agent runtime, evolution log, db hygiene.
- Contains: one module per service concern, no nested packages; flat namespace under `backend.services`.
- Key files: `concept_lifecycle.py` (the dispatcher), `layout_service.py`, `concept_index_service.py`, `tfidf_service.py`, `apparition_service.py`, `evolution_log.py`, `agent_runtime.py`, `db_janitor.py`.

**`backend/api/`:**
- Purpose: the HTTP/WS boundary — one router, one frame vocabulary, one error-handler module.
- Contains: `routes.py` (every endpoint), `ws_frames.py` (wire contract), `errors.py`.
- Key files: `routes.py` — when adding a new endpoint, add it here; there is no per-domain router split.

**`backend/static/js/fe/`:**
- Purpose: the greenfield magic-markdown editor's entire client-side logic — pure-core/impure-shell pairs, each with a co-located `.test.mjs`.
- Contains: `store.mjs`, `gateway.mjs`, `magic_markdown*.mjs`, `projector.mjs`, `vendor/` (bundled third-party).
- Key files: `store.mjs` (sole truth), `gateway.mjs` (sole outbound seam) — both load-bearing for the controlled-view contract.

**`backend/static/js/cp/`:**
- Purpose: the legacy 3D-only projector (demoted to `/legacy`), kept for reference and the 3D chunk field.
- Contains: `chunk_projector.js` mixins (`layout.js`, `force_layout.js`, `hsv_color.js`, `instance_manager.js`, `scanner.js`, `search.js`, `workspace.js`, ...).
- Key files: not actively extended; new 3D work happens in `fe/projector.mjs`.

**`frontend_src/`:**
- Purpose: source-of-truth for the Milkdown edit layer before bundling (Milkdown/ProseMirror is npm-distributed, not single-file ESM, so it cannot be served directly).
- Contains: `milkdown_slate.mjs` only.
- Key files: edits here require re-running esbuild to regenerate `backend/static/js/fe/vendor/milkdown_slate.bundle.mjs`.

**`frontend_e2e/`:**
- Purpose: Playwright specs that exercise the served editor in a real browser (black-slate styling, edit gestures, halo, Milkdown, projector).
- Contains: one `*.spec.js` per surface + `playwright.config.js`.

**`scripts/`:**
- Purpose: the REPL harness (`sim_frontend.py`) plus every live full-stack evidence probe (`probe_live_*.py`) that proves the four lodestar use cases against real subsystems.
- Contains: flat `.py` files, no subpackages except `samples/`.
- Key files: `sim_frontend.py` (env-scenario contract runner), `probe_no_mocks.py` (subsystem reality check).

**`docs/`:**
- Purpose: the layered documentation chain — design ideation → object model → features → code constraints → code architecture → code specs, per `docs/DOC_MAP.md`.
- Contains: top-level `.md` files (verbatim requirements, domain model, frontend redesign) plus per-layer subdirectories.
- Key files: `docs/USER_REQUIREMENTS_VERBATIM.md` is the binding source-of-truth; `docs/DOC_MAP.md` navigates the chain.

**`.planning/`:**
- Purpose: GSD process state — roadmap, requirements capture, phase plans, and this codebase map.
- Contains: `PROJECT.md`, `ROADMAP.md`, `STATE.md`, `TEST_MATRIX.md`, `codebase/` (this doc set), `phases/`, `intel/`.

**`test_packages/`:**
- Purpose: large corpus of saved HTML/scan fixtures from real sites, used by offline mapper/chunker tests.
- Generated: partially (scan output saved once, then committed as fixture).
- Committed: yes — treated as golden test data, not build artifacts.

## Key File Locations

**Entry Points:**
- `backend/main.py`: FastAPI app, lifespan, static/template mounting, `/`, `/editor`, `/legacy` routes.
- `backend/templates/editor.html`: greenfield frontend boot script (inline ESM).
- `scripts/sim_frontend.py`: REPL harness entry point.

**Configuration:**
- `backend/services/settings.py`: environment-knob reads (`WFH_FAKE_SLM`, `WFH_DB_PATH`, `WFH_SLM_MODEL`, etc.).
- `frontend_e2e/playwright.config.js`: e2e runner config.
- `.planning/config.json`: GSD config.

**Core Logic:**
- `backend/services/concept_lifecycle.py`: the one mutation dispatcher.
- `backend/api/ws_frames.py`: the WS wire contract.
- `backend/static/js/fe/store.mjs` + `gateway.mjs`: the frontend's only truth/seam pair.

**Testing:**
- `backend/tests/`: pytest suite, one `test_*.py` per backend module/feature.
- `backend/static/js/fe/*.test.mjs`: Node-run unit tests for pure frontend functions.
- `frontend_e2e/*.spec.js`: Playwright browser tests against the live served app.
- `scripts/probe_live_*.py`: live full-stack acceptance probes (not part of pytest/CI unit suite — run manually against a real backend).

## Naming Conventions

**Files:**
- Backend services: `snake_case.py`, named after the noun they own (`layout_service.py`, `concept_lifecycle.py`) or the verb-noun action they perform (`compile_pipeline.py`).
- Frontend fe/ modules: `magic_markdown*.mjs` family is prefixed by the model name; each has a co-located `<name>.test.mjs`.
- Probes: `probe_live_<use_case>.py` for live full-stack evidence; `probe_<subsystem>.py` for narrower mechanism checks.
- Tests: `test_<module_under_test>.py` mirrors the module name being tested (`test_layout_generator.py` tests `layout_generator.py`).

**Directories:**
- Backend domain packages are nouns (`dom/`, `ontology/`, `mapper/`, `agentic/`, `agent/`) — singular concept areas, not layered (no `controllers/`/`models/`/`views/` split).
- `fe/` (frontend, greenfield) vs `cp/` (chunk projector, legacy) — the two-letter prefixes distinguish the current architecture from the demoted one.

## Where to Add New Code

**New REST endpoint:**
- Add the route function to `backend/api/routes.py` (no new router file); if it mutates a concept, route through `backend/services/concept_lifecycle.py`'s helpers.
- New WS frame types are added to `backend/api/ws_frames.py`'s `FrameType` + a builder function, never as ad-hoc dict literals at the call site.

**New backend service:**
- Add a new flat module under `backend/services/`, named after the noun/responsibility it owns. Import it from `routes.py`; never import frontend code from a service.

**New frontend behavior (greenfield editor):**
- Pure logic goes in a new or existing `backend/static/js/fe/*.mjs` module with a matching `*.test.mjs`.
- DOM-mounting code stays in `magic_markdown_panel.mjs` or is wired inline in `editor.html`'s module script — `editor.html` is intentionally the only place that touches `document`/`window` orchestration across modules.
- New gestures are added to `magic_markdown_gestures.mjs::resolveGesture` and mapped in `gateway.mjs::buildRequest` — both pure, both unit-tested.

**Milkdown edit-layer changes:**
- Edit `frontend_src/milkdown_slate.mjs`, then re-bundle (esbuild) to `backend/static/js/fe/vendor/milkdown_slate.bundle.mjs`. Never hand-edit the bundle.

**New e2e coverage:**
- Add a `*.spec.js` under `frontend_e2e/` following the existing per-surface naming (`<surface>.spec.js`).

**New probe / REPL action:**
- Live full-stack evidence: add `scripts/probe_live_<use_case>.py` following the existing probe pattern (boot real subsystems, assert against `/api/subsystem_status`).
- REPL action: extend `scripts/sim_frontend.py`'s action catalogue; register any new acceptance scenario in the `env-scenario` contract.

## Special Directories

**`kuzu_db/`:**
- Purpose: default on-disk Kuzu database directory (legacy artifact layout); `backend/database.py::_effective_db_path` nests it as `<path>/data.kuzu` for kuzu ≥0.11.
- Generated: yes (runtime).
- Committed: no (data directory; gitignored).

**`test_packages/`:**
- Purpose: golden fixture corpus — one subdirectory per real scanned site, used by offline mapper/chunker tests.
- Generated: partially (captured once from real scans).
- Committed: yes.

**`snapshots/` / `logs/` / `test-results/`:**
- Purpose: runtime scan snapshots, log output, Playwright test artifacts.
- Generated: yes.
- Committed: no.

**`backend/static/js/cp/`:**
- Purpose: legacy 3D projector, demoted from `/` to `/legacy` by the §T/§U/§V strip.
- Generated: no (hand-written legacy code).
- Committed: yes — retained for reference, not actively extended.

---

*Structure analysis: 2026-06-20*
