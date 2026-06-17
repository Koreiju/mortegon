# Web Fiber Haptics: Autonomous Web Segmentation & Knowledge Graph

![Architecture](https://img.shields.io/badge/Architecture-FastAPI%20%2B%20Three.js-blue)
![Database](https://img.shields.io/badge/Graph_DB-Kuzu-orange)
![AI](https://img.shields.io/badge/AI-On--Device%20SLMs-purple)
![Testing](https://img.shields.io/badge/Testing-Pytest-green)

Web Fiber Haptics is an interactive web-segmentation pipeline designed to snapshot webpage graphs as trees and distill them into a much simpler content-only structure. It uses on-device SLMs and a 3D latent-space UI/X to bridge a typed concept/compute graph with a premium 3D Knowledge Graph Visualization Engine. You interface with the AI through the shared memory stream of the web you explore.

By labeling snapshots of pages as you go, you build a dataset that drives pure graph evolution algorithms—learning to segment webpages with structural patterns that best match your own labels. This forms the foundation for an on-device **Agentic Fluid Simulation** that evolves and learns to explore the web like you do, running off purely its own intelligence with the knowledge and directives you provide.

---

## 🌟 Core Features

- **3D Interactive Latent Space UI/X**: You interface with the AI through a shared memory stream of the web you explore. The semantic space is made visually complex by showing image media nodes with links to them, localizing their embeddings in latent space to 3D approximate geometries using `Three.js`.
- **Merge-Tree DOM Scanning & Distillation**: Snapshots webpage graphs as trees, using regex to search for different nodes of content (like media and posts), resolving dynamic content into a simpler, content-only structure. 
- **Triple-Product Retrieval**: Retrieval ranks by the triple product `pagerank · tfidf_cos · nomic_cos` (the two embedding axes — nomic over description, TF-IDF over rendering — never mix). The system segments webpages with structural patterns that best match your own manual labels. *(The legacy 79-feature graph-analytics framework is a forbidden concept — see below.)*
- **CAD Tools for Agentic Fluid**: You essentially CAD out the agentic fluid from the 3D GUI. It is an AI agent fluid particle continuum exploring its own latent space, propagating knowledge dynamics autoregressively from the database you build.
- **100% On-Device AI**: Utilizes a local quantized SLM via **GPT4All** (`Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf`, CUDA) for generation/auto-labeling, and a local embedding model (`nomic-embed-text-v1.5`) for semantic RAG search. Zero cloud dependencies. *(Llama is a forbidden SLM target.)*
- **Database Mycology & Autonomy**: The agentic fluid is intelligently forward-propagated through a self-assembling semantic open web of database search, extraction, transfer, and load. The system evolves the way you see the web over new domains by assembling its own database mycology of semantically enriched search engines.

## 🧱 Architecture / Tech Stack

The system is built on a high-performance, completely offline-first architecture:

1. **Backend / API**: **FastAPI** drives the async web server, managing live WebSocket streaming to the GUI and orchestrating background tasks.
2. **Web Automation**: **Selenium WebDriver** extracts live DOMs, handles infinite scrolling, and executes precise XPath-targeted JavaScript (the "haptic" feedback loop).
3. **Graph Database**: **KuzuDB** stores the persistent knowledge graph (DOM snapshots, structural properties, segment embeddings, user notes, and conversation history).
4. **Scientific Computing**: **NumPy, SciPy, scikit-learn, NetworkX** handle sparse graph algorithms, eigendecompositions, and clustering.
5. **Frontend Presentation**: **Three.js** manages the GPU-instanced 3D node rendering alongside real-time Chat and Retrieval sidebars.

---

## 📚 Documentation Map

The design and code documentation forms a four-layer chain — design ideation flows down into object models, then into feature elaborations, and finally into programming-side constraints. The chain is organised so that every commit can be traced from the user's binding requirement all the way to the file it changes.

### Source-of-Truth Precedence

When two documents disagree, the one earlier in this list wins. See [`CLAUDE.md`](CLAUDE.md) for the persistent session anchor.

| # | Doc | Role |
|---|---|---|
| 1 | [`docs/USER_REQUIREMENTS_VERBATIM.md`](docs/USER_REQUIREMENTS_VERBATIM.md) | Every binding requirement in the user's own phrasing. The doc and the code converge on this file. |
| 2 | [`docs/CODEBASE_GAP_ANALYSIS.md`](docs/CODEBASE_GAP_ANALYSIS.md) | **Historical** (§O.17) — an audit of the now-discarded codebase. Design intent already in DOMAIN_MODEL §18 + the design docs; not an implementation target. |
| 3 | [`docs/DOMAIN_MODEL.md`](docs/DOMAIN_MODEL.md) | Full design elaboration (~2,355 lines). The philosophical anchor; Real / Imaginary / Symbolic Mortegon framing. |
| 4 | [`docs/MORTEGON_INTEGRATION_SCHEME.md`](docs/MORTEGON_INTEGRATION_SCHEME.md) | **Historical** (§O.17) — operational 3D↔2D scheme; additive detail lifted into DOMAIN_MODEL §6.1 / §7.3.2 / §4.6 + the `frontend/` suite. |
| 5 | [`docs/DOC_MAP.md`](docs/DOC_MAP.md) | Structural map of the documentation chain. Read this to navigate between layers. |
| 6 | [`docs/FRONTEND_REDESIGN.md`](docs/FRONTEND_REDESIGN.md) + [`docs/frontend/`](docs/frontend/) | **Canonical frontend** — from-scratch object model + 21-doc per-surface reference suite (dark-minimal stainless-steel-over-black theme). |

### The Four-Layer Chain

```
DOMAIN_MODEL.md (design ideation — Mortegon §1.1 three registers, §1.2 four fixtures, §18 anti-goals)
   ↓
docs/DOC_MAP.md (master index — design → object → feature → constraint chain)
   ↓
docs/object_model/      docs/features/       docs/code_constraints/
(13 docs + README)      (8 docs + README)    (10 docs + README)
```

### Layer 1 — Object Model (`docs/object_model/`)

One document per first-class object in the workspace. Each elaborates `DOMAIN_MODEL.md` into the *object-level realisation* — data shape, lifecycle, invariants, peer interactions, persistence — without committing to a specific programming surface.

| Category | Docs |
|---|---|
| **Data records** | [`ConceptNode`](docs/object_model/ConceptNode.md), [`ConceptEdge`](docs/object_model/ConceptEdge.md), [`ChunkPatternSchema`](docs/object_model/ChunkPatternSchema.md) |
| **Foundational fixtures** (§9.5) | [`Agent`](docs/object_model/Agent.md), [`WebBrowser`](docs/object_model/WebBrowser.md), [`Database`](docs/object_model/Database.md), [`Editor`](docs/object_model/Editor.md) |
| **Backend services** | [`ConceptLifecycle`](docs/object_model/ConceptLifecycle.md), [`LayoutService`](docs/object_model/LayoutService.md), [`ApparitionService`](docs/object_model/ApparitionService.md), [`UIStateService`](docs/object_model/UIStateService.md), [`PythonAPIMaterialiser`](docs/object_model/PythonAPIMaterialiser.md) |
| **Frontend components** | [`Halo`](docs/object_model/Halo.md) |

Index: [`docs/object_model/README.md`](docs/object_model/README.md) — full catalogue with §5 cross-composition map between objects.

### Layer 2 — Features (`docs/features/`)

One document per cross-cutting user-visible feature. Organised by the Mortegon register the feature primarily belongs to.

| Register cluster | Docs |
|---|---|
| **Framing features** | [`three_register_model`](docs/features/three_register_model.md) |
| **API features** | [`four_fixture_api`](docs/features/four_fixture_api.md) |
| **Retrieval features** | [`halo_retrieval`](docs/features/halo_retrieval.md) |
| **3D / projector** | [`6d_umap`](docs/features/6d_umap.md) |
| **Panel / editor** | [`click_to_edit`](docs/features/click_to_edit.md), [`signal_stream`](docs/features/signal_stream.md) |
| **Scanner** | [`pattern_map`](docs/features/pattern_map.md) |
| **Observability** | [`live_scan_cleanup`](docs/features/live_scan_cleanup.md) |

Index: [`docs/features/README.md`](docs/features/README.md) — feature catalogue with §8 feature → anti-goal cross-reference and §9 feature doc anatomy template.

### Layer 3 — Code Constraints (`docs/code_constraints/`)

One document per programming surface in the codebase. Each articulates the *must-hold* and *must-not* conditions that realise the upstream object and feature layers in actual code.

| Surface | Doc |
|---|---|
| `apply_update_lifecycle` / `apply_delete_lifecycle` | [`lifecycle_invariants.md`](docs/code_constraints/lifecycle_invariants.md) |
| `backend/api/routes.py` REST endpoints | [`api_routes.md`](docs/code_constraints/api_routes.md) |
| `backend/api/ws_frames.py` WebSocket frames | [`ws_frames.md`](docs/code_constraints/ws_frames.md) |
| `backend/services/*.py` singletons | [`backend_services.md`](docs/code_constraints/backend_services.md) |
| `backend/static/js/cp/*.js` rendering | [`frontend_rendering.md`](docs/code_constraints/frontend_rendering.md) |
| `scripts/sim_frontend.py` `_ACTIONS` | [`repl_actions.md`](docs/code_constraints/repl_actions.md) |
| `scripts/sim_frontend.py` env-scenarios | [`env_scenarios.md`](docs/code_constraints/env_scenarios.md) |
| Workspace WS + LayoutService streaming | [`streaming.md`](docs/code_constraints/streaming.md) |
| Kuzu + LayoutFrame + on-disk | [`persistence.md`](docs/code_constraints/persistence.md) |

Index: [`docs/code_constraints/README.md`](docs/code_constraints/README.md) — full constraint catalogue with §3 cross-constraint map and §4 surface → anti-goal cross-reference.

### Reading Paths

| Audience | Path |
|---|---|
| **First-time reader** | `DOMAIN_MODEL.md` §1.1 (three registers) + §1.2 (four fixtures) → `DOC_MAP.md` → object_model README → features README. |
| **Implementer** | `CODEBASE_GAP_ANALYSIS.md` (next gap) → `code_constraints/<surface>.md` (must-hold) → `features/<F>.md` (what the user expects) → `object_model/<O>.md` (object shape). Update `DOMAIN_MODEL.md` last, only if implementation reveals a design refinement. |
| **Design contributor** | `USER_REQUIREMENTS_VERBATIM.md` (binding phrasing) → `DOMAIN_MODEL.md` → propagate down through the chain via `DOC_MAP.md`. |
| **Verifier** | `code_constraints/env_scenarios.md` (catalogue) → `features/live_scan_cleanup.md` (mandatory probe) → `features/in_place_activity_viewer.md` (operator's witness). |

### The Six Load-Bearing Commitments

Recapped in detail in [`CLAUDE.md`](CLAUDE.md) and enforced across every layer:

1. **Strict spine rule** (§8D.18.1) — retrieval chunks collapsed-hidden by default.
2. **Latch + form-fit panel** (§8D.1.2) — one unified knowledge-panel anatomy.
3. **Right-click compile/collapse toggle** (§8D.2.2) — symmetric synthesis ↔ analysis.
4. **Python-native Object/Property/Function trees** (§8D.4.2) — the four-fixture API materialises through `python_object` ConceptNodes.
5. **Cascade is the default** (§8D.38.4) — compilation is continuous; the Compile button is an affordance, not the trigger.
6. **REPL in-place activity viewer** (§11.8) — six-row dashboard refreshed via ANSI cursor codes; no append-spam.

### The No-Mocks Contract (§8D.46)

**Production paths run real subsystems. Always.** `GET /api/subsystem_status` returns `{slm, embedder, selenium, langgraph, all_real}`. CI gates require `all_real: true` before merge.

| Subsystem | Real | Harness-only fake gate |
|---|---|---|
| SLM | GPT4All `Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf` on CUDA (no Llama) | `WFH_FAKE_SLM=1` |
| Embedder | GPT4All `Embed4All` `nomic-embed-text-v1.5.f16.gguf` on CUDA | `WFH_FAKE_EMBEDDER=1` |
| Selenium | Headful Firefox via `backend/drivers/geckodriver.exe` | `NO_WEBDRIVER=1` |
| LangGraph | `langgraph.graph.StateGraph` — missing import is a hard error | none |

### Forbidden Concepts

Hard deletions; must not reappear in doc or code. See `DOMAIN_MODEL.md` §forbidden-concepts.

- **Concentric Fibonacci spheres** as the 3D layout — replaced by UMAP-linear-radial force-directed hybrid.
- **Graph analytics retrieval framework** — replaced by triple product `pagerank · tfidf_cos · nomic_cos`.
- **Llama** as an SLM target — Nous Hermes 2 DPO on CUDA only.
- **Two-panel hover/click split** — one knowledge-panel anatomy, one code path.
- **Stray dotted UI lines** — solid 2D↔3D link arrow only.
- **Concentric concept-graph rings** — replaced by ray-constrained placement around the focal card.

---

## ⚙️ Quickstart

### Prerequisites
- Python 3.10+ (Windows 11 + CUDA is the reference environment)
- `pip`
- Firefox (Selenium drives it via the vendored `backend/drivers/geckodriver.exe`)
- A CUDA GPU for the real SLM/embedder (GPT4All downloads the GGUFs to `~/.cache/gpt4all/` on first run)

### Step 1: Install Dependencies
Create a virtual environment and install the pinned tooling:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r backend/requirements.txt
```

### Step 2: Running the Server

**`app.py` is the canonical entry point** — it sets up `logs.txt` mirroring, mounts the database + templates, and serves the black-slate editor at `/`. The default port is **8080**.

```bash
# Serve only:
python app.py                         # → http://127.0.0.1:8080/

# Serve AND drop into the REPL in the SAME terminal (recommended dev loop):
python app.py --repl                  # backend on 8080 + FrontendEnv prompt

# Override host/port if needed:
python app.py --host 0.0.0.0 --port 8080
```

`python -m backend.main` also works (it runs the same `backend.main:app`) but skips the `app.py` logging/REPL wrapper — prefer `app.py`.

**Port alignment (important):** the backend serves **8080**, but the standalone REPL harness `scripts/sim_frontend.py` defaults to **8000**. When running the REPL separately, always point it at the backend: pass `--backend http://127.0.0.1:8080` (a global flag, BEFORE the subcommand) or set `WFH_BACKEND_URL=http://127.0.0.1:8080`. `python app.py --repl` wires this up for you automatically.

Navigate to `http://127.0.0.1:8080/` to interact with the editor.

---

## 🧪 Testing Protocol

### Unified full-stack test framework

One command boots a single managed backend and runs **every verification tier**
against it, with a unified pass/fail summary — `scripts/run_full_stack_tests.py`
(`npm run test:all`):

| Tier | What | Needs backend |
|---|---|---|
| `pytest` | `backend/tests/` unit + integration | no |
| `repl` | `sim_frontend.py env-scenario --name full-smoke` — the **full** REPL contract (~92 scenarios) | yes |
| `e2e` | Playwright `frontend_e2e/*.spec.js` — render-level acceptance the REPL can't reach | yes |
| `probes` *(--real)* | `probe_no_mocks` + the four `probe_live_*` lodestars | yes (real) |

```bash
npm run test:all            # STUB: pytest + repl + e2e  (→ ALL GREEN ✓)
npm run test:all:real       # all_real CUDA stack: + the live lodestar probes
python scripts/run_full_stack_tests.py --only repl --only e2e   # subset
python scripts/run_full_stack_tests.py --no-pytest --port 8090  # knobs
```

The framework owns the backend lifecycle (boot → wait-ready → run tiers →
teardown), so the REPL env-scenario contract and the Playwright suite run in the
**same framework against the same stack**. Playwright also self-boots a stub
backend (`webServer`, `reuseExistingServer`) so `npm run test:e2e` is standalone;
see [`frontend_e2e/README.md`](frontend_e2e/README.md). Last green: 2026-06-15
(stub: pytest + 92 scenarios + 5 e2e).

### Component test surfaces

The testing framework explicitly isolates geometric and graph-theoretic verifications within a temporary isolated KuzuDB instance (`test_kuzu_db`), ensuring active deployment data remains pristine.

> **Note (2026-06 audit, `docs/CODEBASE_AUDIT_2026-06-08.md`):** the 3D layout authority is the
> **UMAP-linear-radial force-directed hybrid** (`DOMAIN_MODEL.md` §6.1) — *not* a concentric-sphere
> layout, which is a **forbidden concept** (see the Forbidden Concepts table above). The chunk
> manifold is fitted by real `umap-learn` (neighbour-preserving) in
> `backend/services/layout_service.py::_embed_6d`, degrading loudly to TruncatedSVD only when
> umap is unavailable. Any remaining `test_layout_generator.py` Fibonacci-sphere assertions are
> legacy DOM-snapshot scaffolding flagged for removal (audit §B.1), **not** the projector layout.

Testing enforces physical math constraints over brittle E2E browser queries:
- **`test_cypher_engine.py`**: Asserts abstract LCA relationships accurately generate relational node arrays inside memory.
- **`env-scenario` suite** (`scripts/sim_frontend.py`): the REPL round-trip is the real verification surface (`DOMAIN_MODEL.md` §14) — REPL action → backend mutation → WS frame → render → telemetry → REPL read-back, in both stub and `all_real: true` modes.

Run the test suite globally via:
```bash
python -m pytest backend/tests/ -v
```

### Terminal harness for frontend simulation

`scripts/sim_frontend.py` lets you trigger the same REST + WebSocket
actions the frontend takes — create concepts, link them, query
apparitions, scan URLs, watch the broadcast stream — from a terminal.
Useful for post-change smoke checks without spinning up the browser.

```bash
# One-terminal integrated mode: backend serves AND drops you into the REPL.
# A browser tab at http://127.0.0.1:8080/ posts DOM mutations back to this
# same terminal (drain with `ui-telemetry`).
python app.py --repl

# Or, no backend needed — pure chunker regression:
python scripts/sim_frontend.py pipeline-smoke

# Or, two-terminal mode (terminal 1 backend, terminal 2 CLI):
NO_WEBDRIVER=1 python -m backend.main
python scripts/sim_frontend.py --backend http://127.0.0.1:8080 health
python scripts/sim_frontend.py --backend http://127.0.0.1:8080 env-scenario --name route-mount-smoke

# Catch-'em-all: run all 35 sub-scenarios end-to-end (~30 s warm).
python scripts/sim_frontend.py --backend http://127.0.0.1:8080 env-scenario --name full-smoke
```

The harness exposes **107 actions** mapped 1:1 against backend routes
and groups them into **35 named scenarios** covering the full surface:

| Bucket | Scenarios |
|---|---|
| Harness self-check (offline) | `action-registry-coverage`, `route-coverage`, `routes-list-shape`, `actions-by-category-coverage`, `chunker-regression`, `chunker-edge-cases` |
| Live backend, no embedder | `app-info-shape`, `route-mount-smoke`, `graph-schema-shape`, `health-perf`, `purge-requires-confirm`, `fixture-delete-guard`, `ui-roundtrip`, `spine-delta-emits`, `telemetry-roundtrip`, `workspace-isolation` |
| Read-only shape probes | `mapper-empty-shape`, `analytics-empty-shape`, `cascade-status-empty`, `agent-reviews-empty`, `evolution-log-shape`, `node-details-404`, `session-reconcile-empty`, `chunk-search-empty`, `search-hybrid-empty`, `concepts-export-shape` |
| Mutating + embedder | `warmup`, `concept-lifecycle`, `edge-roundtrip`, `idempotency-replay`, `upload-graph-roundtrip`, `chat-session-create`, `compiled-xpath-pattern-create`, `agentic-instantiate-shape`, `purge-and-rebuild` |
| Meta | `full-smoke` (composes all 34 above) |

CI gates the offline subset via
`backend/tests/test_sim_env_scenarios.py` — those scenarios run on
every `python -m pytest backend/tests/` invocation with no backend
required.

Full reference: `scripts/README_sim_frontend.md`. The authoritative scenario catalogue (currently ~66 scenarios in real-stack + stub modes) is documented at [`docs/code_constraints/env_scenarios.md`](docs/code_constraints/env_scenarios.md). The mandatory live-stack probe lives at [`docs/features/live_scan_cleanup.md`](docs/features/live_scan_cleanup.md).

### Static type checking (optional)

A gradual mypy config lives at `mypy.ini`. Defaults are permissive
(legacy modules pre-date typing), but the `NewType` id surfaces in
`backend/services/ids.py` and the modules that adopt them
(`concept_lifecycle`, `dom/pipeline`, `services/settings`) have
stricter per-module overrides so swapped-argument bugs caught by
`ConceptId` vs `WorkspaceId` distinctions surface in CI.

```bash
pip install mypy
mypy backend
```

---

*Note: One of the design patterns is to eventually interlace the agentic fluid with its own codebase, but that will be implemented in more matured development stages.*
