<!-- refreshed: 2026-06-20 -->
# Architecture

**Analysis Date:** 2026-06-20

## System Overview

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                         BROWSER (greenfield fe/)                         │
├───────────────┬───────────────┬───────────────┬──────────────────────────┤
│ store.mjs     │ gateway.mjs   │ magic_markdown │  projector.mjs           │
│ (sole truth)  │ (outbound     │ .mjs / _panel  │  (3D Real register —    │
│ `fe/store.mjs`│  seam)        │ / _halo / _ges │   UMAP xyz + HSV)        │
│               │ `fe/gateway   │ -tures.mjs     │  `fe/projector.mjs`      │
│               │  .mjs`        │  `fe/magic_*`  │                          │
└──────┬────────┴──────┬────────┴──────┬─────────┴────────────┬─────────────┘
       │ applyFrame     │ buildRequest   │ render/mount/halo    │ setNodes(coords)
       │ (WS frames)    │ (REST mirror)  │ (controlled view)    │ (umap_canonical)
       ▼                ▼                                       ▲
┌──────────────────────────────────────────────────────────────────────────┐
│         OPTIONAL: Milkdown controlled edit layer (?slate=milkdown)       │
│  `frontend_src/milkdown_slate.mjs` → bundled to                          │
│  `backend/static/js/fe/vendor/milkdown_slate.bundle.mjs`                 │
│  setText (inbound truth) / onCommit (outbound intent) — never authoritative│
└──────────────────────────────────────────────────────────────────────────┘
       │ fetch /api/* (REST)                       │ WS /api/ws/workspace/{id}
       ▼                                            │ (typed frame vocabulary)
┌──────────────────────────────────────────────────────────────────────────┐
│                    FastAPI app — `backend/main.py` (port 8080)           │
│                         `backend/api/routes.py` (5400+ lines, one router)│
├───────────────┬───────────────┬───────────────┬──────────────────────────┤
│ concept CRUD  │ ui/* mirror   │ chunk/scan/    │ agent / evolution_log /  │
│ /concepts*    │ routes (pin,  │ retrieval      │ apparitions / radiation  │
│               │ fold, compile)│ /chunk_*,/map/*│ /agent/*, /evolution_log │
└───────┬───────┴───────┬───────┴───────┬────────┴──────────┬───────────────┘
        │                │               │                    │
        ▼                ▼               ▼                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│            ONE LIFECYCLE DISPATCHER — `backend/services/                 │
│            concept_lifecycle.py::apply_update_lifecycle /                │
│            apply_delete_lifecycle` (+ `_apply_create_lifecycle` wrapper   │
│            in routes.py)                                                  │
│  ConceptDiff (pure classification) → WS broadcast → ConceptIndex upsert  │
│  → output-projection schedule → evolution log append → cascade nudge     │
└───────┬───────────────┬───────────────┬───────────────┬──────────────────┘
        │               │               │               │
        ▼               ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐
│ Chunk-side   │ │ Concept-side │ │ Layout       │ │ Evolution log /      │
│ vectorization│ │ vectorization│ │ Service      │ │ rollback             │
│ TF-IDF       │ │ nomic embed  │ │ (UMAP+force- │ │ `services/           │
│ incremental  │ │ incremental  │ │ directed,    │ │ evolution_log.py`    │
│ + UMAP joint │ │ + PageRank   │ │ §6.1)        │ │                      │
│ `services/   │ │ joint        │ │ `services/   │ │                      │
│ tfidf_*`     │ │ `services/   │ │ layout_      │ │                      │
│              │ │ concept_     │ │ service.py`  │ │                      │
│              │ │ index_       │ │              │ │                      │
│              │ │ service.py`  │ │              │ │                      │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────────────┘
        │               │               │
        ▼               ▼               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│   Kuzu graph DB (one ConceptNode table, one ConceptEdge table) +         │
│   `backend/database.py` (`_effective_db_path` nests legacy dirs as       │
│   `<path>/data.kuzu`, kuzu ≥0.11 file-based)                             │
└──────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| FastAPI app + lifespan | Boots Selenium driver, inits DB, mounts static + templates, single `/api`-prefixed router | `backend/main.py` |
| Route layer | All REST endpoints (concepts, ui mirror, chunk/scan/retrieval, agent, evolution log, ontology) — one 5400-line router, no sub-routers | `backend/api/routes.py` |
| WS frame vocabulary | Canonical typed-frame envelope + per-type builders (`umap_canonical`, `concept_changed`, `compute_graph_layout`, `ontology_layout`, `agent_token`, ...) + monotonic `frame_seq` | `backend/api/ws_frames.py` |
| Concept lifecycle dispatcher | Pure `ConceptDiff` classification + the one mutation chain every create/update/delete goes through | `backend/services/concept_lifecycle.py` |
| Graph editor | Kuzu read/write surface for ConceptNode/ConceptEdge | `backend/services/graph_editor.py` |
| Concept index service | Nomic embedding incremental update + PageRank joint recompute (concept-side vectorization) | `backend/services/concept_index_service.py` |
| TF-IDF service / worker | Chunk-side TF-IDF incremental update | `backend/services/tfidf_service.py`, `backend/services/tfidf_worker.py` |
| Layout service | UMAP-linear-radial force-directed 3D layout (chunks) + compute-graph bisector placement | `backend/services/layout_service.py` |
| Chunk projector service | Maps chunk records → projector-consumable node payloads | `backend/services/chunk_projector_service.py` |
| Apparition service | Triple-product (`pagerank · tfidf_cos · nomic_cos`) retrieval ranking for halos | `backend/services/apparition_service.py` |
| Evolution log | Append-only diff log + three rollback scopes (single/range/actor) | `backend/services/evolution_log.py` |
| Agent runtime | LangGraph+GPT4All meta-cognition tick, ActionResolver, on the same lifecycle path as REST | `backend/services/agent_runtime.py` |
| Scanner / DOM pipeline | Selenium-driven scan → chunk extraction → content-tree dedup | `backend/dom/scanner.py`, `backend/dom/pipeline.py`, `backend/dom/content_tree.py` |
| Served editor (greenfield) | Default `/` surface — magic-markdown black-slate grid + 3D projector canvas | `backend/templates/editor.html` |
| Legacy projector | Demoted `/legacy` 3D-only surface, kept for reference | `backend/templates/index.html`, `backend/static/js/cp/*.js` |
| fe/ store | Sole frontend truth; folds WS frames; `registry()` resolves `{ref}` by root field | `backend/static/js/fe/store.mjs` |
| fe/ gateway | The only outbound seam; pure `buildRequest(gesture)` + thin fetch wrapper | `backend/static/js/fe/gateway.mjs` |
| magic-markdown model | Parse/render/registry/decompose — the syntax-agnostic field-tree engine | `backend/static/js/fe/magic_markdown.mjs` |
| magic-markdown panel | DOM mount for the panel/graph dual rendering of a node | `backend/static/js/fe/magic_markdown_panel.mjs` |
| magic-markdown gestures | Pure gesture classifier (`resolveGesture`) shared by custom slate + Milkdown | `backend/static/js/fe/magic_markdown_gestures.mjs` |
| Apparition halo | Pure `haloLayout` (ray mechanics) + `haloVDom` (SVG render), camera-azimuth coupled | `backend/static/js/fe/magic_markdown_halo.mjs` |
| 3D projector | THREE.js points scene; `buildPointArrays` (pure) renders backend HSV, never invents colour | `backend/static/js/fe/projector.mjs` |
| Milkdown edit layer | Controlled-view ProseMirror editor; source under `frontend_src/`, bundled to vendor | `frontend_src/milkdown_slate.mjs`, `backend/static/js/fe/vendor/milkdown_slate.bundle.mjs` |

## Pattern Overview

**Overall:** Backend-computes / frontend-renders monolith. A single FastAPI process owns all layout, embedding, ranking, and graph-mutation logic; the browser is a thin, pure-rendering client whose only persisted state lives in one JS store object, refreshed exclusively by WebSocket frames and REST-mirror responses.

**Key Characteristics:**
- One lifecycle dispatcher (`concept_lifecycle.py`) — every mutation path (REST PATCH, agent ActionResolver, scanner-driven backing-version bump) funnels through the same diff → broadcast → index → projection → log chain. No parallel mutation paths.
- Controlled-view frontend — the fe/ store is the only truth; both the custom magic-markdown DOM and the Milkdown ProseMirror DOM are pure projections (`setText` replace-all inbound, `onCommit`/gesture outbound). Reconnect re-render is provably identical (EDIT-03 contract).
- Dual, independent vectorization pipelines — chunk-side (TF-IDF + UMAP) and concept-side (nomic + PageRank) never share state or mix axes; Layout Service and Concept Index Service are sibling services, never nested.
- One edge table — `ConceptEdge` is the union enum of every typed relationship (wiring, web-ontology, Python-native, port-binding). No second edge table for any subsystem.
- WS-first, REST-mirrors-WS — every gesture's REST call either returns inline frames or relies on the WS broadcast to update peer tabs; the gateway's `buildRequest` is pure and the only place gesture→route mapping lives.

## Layers

The design's "Real / Imaginary / Symbolic" registers map onto concrete code layers as follows:

**Real register (3D rendered space):**
- Purpose: visualize the UMAP-positioned chunk/concept field with backend-computed HSV colour.
- Location: `backend/static/js/fe/projector.mjs` (frontend render), `backend/services/layout_service.py` + `backend/services/chunk_projector_service.py` (backend compute).
- Contains: THREE.js points scene, pure `buildPointArrays`/`haloLayout` geometry functions, UMAP/force-directed placement.
- Depends on: `umap_canonical` / `ontology_layout` / `compute_graph_layout` WS frames (`backend/api/ws_frames.py`).
- Used by: `editor.html`'s `bootProjector()`, the halo's camera-azimuth coupling.

**Symbolic register (panel/field-tree text):**
- Purpose: the editable name/description/value/compiled field-tree — the "data block dissolves into the field-tree" model.
- Location: `backend/static/js/fe/magic_markdown.mjs` (parse/render/registry), `magic_markdown_panel.mjs` (DOM mount), `frontend_src/milkdown_slate.mjs` (alternate ProseMirror-backed edit surface).
- Contains: syntax-agnostic recursive descent decomposition, `{ref}` token resolution, gesture classification.
- Depends on: `store.mjs` for concept/edge state.
- Used by: `editor.html`'s `render()` / `enterMilkdownEdit()`.

**Imaginary register (apparition halo — candidates not yet committed):**
- Purpose: render retrieval candidates as collapsed circular phantoms radiating from a focal panel, ray-distance encoding similarity.
- Location: `backend/static/js/fe/magic_markdown_halo.mjs` (pure layout + SVG render).
- Contains: `haloLayout` (focal + candidates + camAngle → polar positions), `haloVDom`.
- Depends on: `/api/radiation` (triple-product retrieval), `projector.mjs`'s `azimuth()` for ray-angle coupling.
- Used by: `editor.html`'s `openHalo()` / `renderHalo()` / camera `onFrame` callback.

**Backend services layer:**
- Purpose: every computation (layout, embedding, ranking, compile) the frontend is forbidden from doing.
- Location: `backend/services/*.py` (~50 modules).
- Contains: lifecycle dispatcher, both vectorization pipelines, agent runtime, evolution log, compile pipeline, ws_replay backpressure.
- Depends on: `backend/database.py` (Kuzu), `backend/dom/*` (scanner/content-tree).
- Used by: `backend/api/routes.py` exclusively (services are never imported by frontend code).

## Data Flow

### Primary Request Path (concept edit)

1. User blurs a Milkdown/custom-slate edit → `gateway.send({kind:"concept-update", ...})` (`backend/templates/editor.html:172-173`)
2. `buildRequest` maps to `PATCH /api/concepts/{id}` (`backend/static/js/fe/gateway.mjs:36-37`)
3. Route handler reads pre-state, calls `_apply_update_lifecycle` (`backend/api/routes.py:2185`, `2408-2445`)
4. `concept_lifecycle.py::apply_update_lifecycle` computes `ConceptDiff.from_pre_post`, then: WS broadcast (`build_concept_changed`) → ConceptIndex upsert if `embed_fields_changed` → output-projection schedule if `effective_data_changed` → evolution-log append (`backend/services/concept_lifecycle.py:33-120`+)
5. Frontend WS `onmessage` applies the `concept_changed` frame to `store.applyFrame` and re-renders unless an edit is in progress (`backend/templates/editor.html:291-301`)

### Scan → Retrieval → Visualization Flow

1. `/api/snapshot` triggers Selenium scan via `backend/dom/scanner.py` → chunks stream as `chunks_partial`/`chunk_added` WS frames (`backend/api/routes.py:854-1077`)
2. Scan-end fires a joint UMAP refit; `umap_canonical` frame broadcasts 6D (xyz+HSV) coords (`backend/api/ws_frames.py:200-246`)
3. `projector.mjs::setNodes(coords)` renders backend HSV directly — never invents colour (`backend/static/js/fe/projector.mjs:27-51`, `296`)
4. Retrieval (`/api/chunk_search`, `/api/radiation`) ranks by triple product `pagerank · tfidf_cos · nomic_cos`; halo candidates render as collapsed circular phantoms (`backend/static/js/fe/magic_markdown_halo.mjs`)

**State Management:**
- Frontend: one mutable `state` object inside `createStore()` closure (`backend/static/js/fe/store.mjs:15-20`); no Redux/global singleton beyond the one store instance created in `editor.html`.
- Backend: Kuzu is the durable store; in-memory `_SEQ_COUNTERS` (per-workspace frame-seq, `backend/api/ws_frames.py:121-122`) and idempotency cache (`backend/api/routes.py:162-210`) are process-local and reset on restart.

## Key Abstractions

**ConceptNode / ConceptEdge (the one record):**
- Purpose: every first-class object in the workspace — fixtures, scanned chunks, authored concepts, Python-API trees, compute-graph nodes — is a `ConceptNode`; every relationship is a `ConceptEdge`.
- Examples: `backend/services/graph_editor.py`, `backend/ontology/models.py`.
- Pattern: type_hint is a naming convention, never a type discriminator; one table, one edge table.

**ConceptDiff (pure mutation classification):**
- Purpose: decide once what changed (data/description/rendering/backing-version) so every downstream consumer reads the same answer instead of re-deriving heuristics.
- Examples: `backend/services/concept_lifecycle.py:48-120`.
- Pattern: frozen dataclass with derived boolean properties (`embed_fields_changed`, `effective_data_changed`).

**WS frame envelope (typed, monotonic):**
- Purpose: single source of truth for the wire contract between backend services and the frontend store.
- Examples: `backend/api/ws_frames.py` (`FrameType`, `make_frame`, per-type builders).
- Pattern: every frame stamps `type` + `frame_seq` (monotonic per workspace scope) + optional `workspace_id`; frontend discards lower-seq frames.

**Pure-core / impure-shell split (frontend):**
- Purpose: keep geometry/parsing/classification logic unit-testable in Node without a browser.
- Examples: `buildPointArrays`/`createProjector` split in `projector.mjs`; `haloLayout`/`haloVDom` split in `magic_markdown_halo.mjs`; `buildRequest`/`GestureGateway` split in `gateway.mjs`.
- Pattern: every `*.mjs` module's pure functions have a matching `*.test.mjs`.

## Entry Points

**Backend process:**
- Location: `backend/main.py`
- Triggers: `uvicorn.run("backend.main:app", host="127.0.0.1", port=8080, reload=True)` when run directly; `lifespan` context boots the Selenium driver (unless `NO_WEBDRIVER=1`) and calls `init_db()`.
- Responsibilities: mounts `/static`, registers `templates/`, includes the single `router` under `/api`, serves `/` (greenfield editor, default), `/editor` (explicit alias), `/legacy` (demoted 3D projector).

**Served editor (frontend boot):**
- Location: `backend/templates/editor.html` (inline `<script type="module">`)
- Triggers: page load → IIFE at the bottom (`loadConcepts()` → `loadChunks()` → `render()` → `connectWS()` → `bootProjector()`).
- Responsibilities: hydrate store from `/api/concepts` + `/api/chunk_nodes`/`/api/chunk_details`, open the workspace WebSocket, boot the THREE.js projector via `/api/recompute_umap`.

**REPL harness:**
- Location: `scripts/sim_frontend.py`
- Triggers: CLI invocation (`env-scenario`, `watch-activity`, individual actions).
- Responsibilities: drives the same REST/WS surface the browser uses, for scripted acceptance verification.

## Architectural Constraints

- **Threading:** FastAPI's asyncio event loop is captured at lifespan startup (`set_event_loop`, `backend/main.py:29-30`) so worker threads (Selenium callbacks, background scan tasks) can push WS frames via `call_soon_threadsafe`; without this capture the async WS plumbing in `routes.py` silently no-ops.
- **Global state:** module-level singletons include the mapper/driver singleton (`_get_mapper()`, `backend/api/routes.py:742`), the per-workspace WS frame-seq counters (`_SEQ_COUNTERS`, `backend/api/ws_frames.py:122`), and the idempotency cache (`backend/api/routes.py`). All are process-local and not persisted.
- **One router, no sub-routers:** `backend/api/routes.py` is a single ~5400-line `APIRouter` covering every REST surface (legacy mapper endpoints, concept CRUD, ui mirror, agent, evolution log). New endpoints are added to this file, not split into per-domain routers.
- **Frontend has no compute runtime:** no UMAP fitter, no embedding model, no PageRank — these constraints are enforced architecturally (no such library is imported under `backend/static/js/fe/` or `frontend_src/`).

## Anti-Patterns

### Bypassing the lifecycle dispatcher

**What happens:** A new mutation path (e.g. a future bulk-import route) writes directly to Kuzu via `graph_editor.py` without calling `apply_update_lifecycle`/`apply_delete_lifecycle`.
**Why it's wrong:** Skips WS broadcast (other tabs go stale), ConceptIndex upsert (retrieval ranks against a stale embedding), evolution-log append (rollback loses the edit), and cascade nudge (`{ref}`-consumers don't recompile).
**Do this instead:** Always route concept mutations through `backend/services/concept_lifecycle.py`'s helpers, as `backend/api/routes.py:2178-2207` (`_apply_create_lifecycle`, `_apply_update_lifecycle`, `_apply_delete_lifecycle`, `_schedule_output_projection`) already do.

### Frontend inventing colour or layout

**What happens:** A frontend module computes its own hue from an id hash or distance metric instead of consuming `umap_canonical`'s HSV channels.
**Why it's wrong:** Violates "backend computes, frontend renders" — colour state becomes inconsistent across tabs and untestable against the real UMAP fit.
**Do this instead:** `buildPointArrays` only falls back to a positional hue sweep when no 6-vector is present, explicitly labeled "bootstrap stand-in" (`backend/static/js/fe/projector.mjs:18-22,41-45`); once a real frame arrives the fallback never reappears.

### Authoritative state inside the editable DOM

**What happens:** Treating the ProseMirror/contenteditable DOM as the source of truth (e.g. reading back `innerHTML` to decide what to persist on every keystroke).
**Why it's wrong:** Breaks reconnect-identity (EDIT-03) and the controlled-view contract; makes the WS-driven re-render path diverge from what's on screen.
**Do this instead:** `setText`/`replaceAll` are the only inbound paths; `onCommit` on blur is the only outbound path (`frontend_src/milkdown_slate.mjs:7-13`); the store stays sole truth and `__mm_rerender` always re-derives identically.

## Error Handling

**Strategy:** Loud failure for subsystem unavailability (no-mocks contract, §8D.46); silent-but-logged failure for secondary/non-critical lifecycle side-effects.

**Patterns:**
- `backend/api/errors.py` registers dedicated handlers (`register_workflow_error_handler`, `register_slm_unavailable_handler`) so a missing GGUF or dead Selenium driver surfaces as a 503, never a silent stub substitution.
- `concept_lifecycle.py` helpers "swallow internal errors and print a tagged warning so a secondary subsystem hiccup never blocks the primary mutation" (`backend/services/concept_lifecycle.py:18-19`) — applies to broadcast/index/projection/log, never to the primary Kuzu write.
- Frontend `gateway.mjs::send` catches fetch errors and calls `opts.onError`, returning `null` rather than throwing, so one failed gesture never crashes the render loop.

## Cross-Cutting Concerns

**Logging:** Python `logging` module per-service (`logger = logging.getLogger(__name__)`, e.g. `backend/services/concept_lifecycle.py:24,30`); frontend uses `console.warn` for best-effort failures (e.g. `editor.html:113,283,303,358`).

**Validation:** Pydantic request models for every REST body (`ConceptNodeRequest`, `PurgeWorkspaceRequest`, `RollbackSingleRequest`, etc., referenced throughout `backend/api/routes.py`); frontend gesture validation lives entirely in `resolveGesture`/`buildRequest`'s pure pattern matches, returning `null` for unrecognized gestures.

**Authentication:** Not present — `actor: str = "user:_anon"` is the default actor tag on lifecycle calls (`backend/api/routes.py:2178`); no auth middleware exists.

---

*Architecture analysis: 2026-06-20*
