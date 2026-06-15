<!-- refreshed: 2026-06-14 -->
# Architecture

**Analysis Date:** 2026-06-14

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (renders only)                        │
├──────────────────────────┬────────────────────────────────────────--┤
│   3D chunk projector      │   2D concept-graph / magic-markdown slate │
│  `backend/static/js/cp/`  │   `backend/static/js/fe/`                 │
│  (Three.js, UMAP-radial)  │   (ES-module .mjs greenfield, §T/§U/§V)   │
└──────────┬───────────────┴──────────────────┬────────────────────────┘
           │ REST (138 routes)                 │ WebSocket (3 endpoints)
           ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       API LAYER (FastAPI, :8080)                      │
│   `backend/main.py` (app + lifespan + page serving)                   │
│   `backend/api/routes.py` (all REST + WS handlers, ~4800 lines)       │
│   `backend/api/ws_frames.py` (frame builders) · `errors.py`          │
└──────────┬──────────────────────────────────────────────────────────┘
           │ every concept mutation routes through ↓
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│        LIFECYCLE DISPATCHER (single mutation chokepoint)              │
│   `backend/services/concept_lifecycle.py`                            │
│   apply_update_lifecycle / apply_delete_lifecycle:                    │
│   WS broadcast → ConceptIndex upsert → output-projection schedule    │
│   → evolution-log entry → cascade nudge                              │
└──────────┬──────────────────────────────────────────────────────────┘
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       SERVICE LAYER (computes)                        │
│  `backend/services/*.py` (~55 services)                              │
│  Two progressive vectorization pipelines:                            │
│   chunk side: tfidf_service + global_tfidf_store → layout_service     │
│               (UMAP joint 6D + force-directed radial)                │
│   concept side: ontology_field_embedder (nomic) →                    │
│               concept_index_service (PageRank)                        │
│  Scan: continuous_scanner → dom/scanner → mapper → chunk emission    │
│  Compute: compile_pipeline · conceptual_compute · slm_client         │
│  Agent: agent_runtime · agent/langgraph_loop · rollout_coordinator   │
└──────────┬──────────────────────────────────────────────────────────┘
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STORE + EXTERNAL                                                     │
│  Kuzu graph DB `backend/database.py` (ConceptNode + ConceptEdge +    │
│   ContentChunk + TriePattern + ChunkInstance + embeddings)           │
│  External: GPT4All SLM + nomic embedder (CUDA), Selenium/Firefox,    │
│   LangGraph                                                           │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| App + lifespan | FastAPI boot, Selenium eager init, DB init, page serving (`/`, `/editor`, `/legacy`) | `backend/main.py` |
| API router | All 138 REST routes + 3 WS endpoints; thin handlers delegating to services | `backend/api/routes.py` |
| WS frame builders | Construct typed WS frames (concept_index_update, umap_canonical, agent_token, etc.) | `backend/api/ws_frames.py` |
| Lifecycle dispatcher | Single mutation chain for every concept create/update/delete | `backend/services/concept_lifecycle.py` |
| Kuzu database | One ConceptNode + one ConceptEdge table; chunk/trie/embedding tables; schema in `init_db` | `backend/database.py` |
| Chunk vectorization | Incremental TF-IDF over rendering text | `backend/services/tfidf_service.py`, `backend/services/global_tfidf_store.py` |
| Layout service | UMAP joint 6D fit + force-directed radial 3D placement, projector links | `backend/services/layout_service.py` |
| Concept vectorization | nomic embedding over description | `backend/services/ontology_field_embedder.py` |
| Concept index + PageRank | Concept-side joint index, PageRank | `backend/services/concept_index_service.py` |
| Scanner | Live Selenium scan loop; emits chunks per snapshot | `backend/services/continuous_scanner.py`, `backend/dom/scanner.py` |
| Mapper | DOM → trie → pattern → chunk pipeline | `backend/mapper/mapper.py`, `backend/dom/pipeline.py` |
| Compile | Syntax-agnostic recursive compile + LangGraph chain | `backend/services/compile_pipeline.py`, `backend/services/conceptual_compute.py` |
| SLM client | GPT4All Nous-Hermes dispatch | `backend/services/slm_client.py` |
| Agent runtime | Meta-cognition tick, emitters, LangGraph loop | `backend/services/agent_runtime.py`, `backend/agent/langgraph_loop.py` |
| Evolution log | Append-only audit, three rollback scopes | `backend/services/evolution_log.py` |
| UI state | Server-authoritative pin/hover/halo/collapse state | `backend/services/ui_state_service.py` |

## Pattern Overview

**Overall:** Layered service-oriented backend (compute) + thin render-only frontend, glued by REST mutations and monotone-seq WebSocket broadcast. A single lifecycle dispatcher is the mandatory chokepoint for all concept mutations.

**Key Characteristics:**
- Backend computes everything (layout, embeddings, PageRank); frontend has no UMAP/embedding runtime.
- One ConceptNode + one ConceptEdge schema; new capability is a new fixture / compiled-from-scans / Python-API tree, never a new card table.
- Two sibling progressive vectorization pipelines (chunk-side TF-IDF+UMAP, concept-side nomic+PageRank); the two embedding axes never mix.
- WebSocket frame seq monotone per workspace with `?resume=<seq>` replay; lossy backpressure keeps `done`/`error`/latest `generation`.
- Optimistic concurrency, last-write-wins; rollback is the user's conflict tool.

## Layers

**API layer:**
- Purpose: HTTP/WS surface, request validation, page serving.
- Location: `backend/main.py`, `backend/api/`
- Contains: route handlers, WS frame builders, error handlers.
- Depends on: service layer.
- Used by: frontend.

**Lifecycle dispatcher:**
- Purpose: single chain every concept mutation traverses.
- Location: `backend/services/concept_lifecycle.py`
- Depends on: ConceptIndex, output projection, evolution log, WS push.
- Used by: REST handlers in `routes.py` AND agent `agent_runtime`.

**Service layer:**
- Purpose: all computation — scanning, vectorization, layout, compile, agent.
- Location: `backend/services/` (~55 modules), plus domain packages `backend/dom/`, `backend/mapper/`, `backend/ontology/`, `backend/agent/`.
- Depends on: database + external subsystems.
- Used by: API layer, lifecycle.

**Persistence + external:**
- Purpose: Kuzu graph store; GPT4All, nomic, Selenium, LangGraph.
- Location: `backend/database.py`, `backend/rag_store.py`, `backend/drivers/`.

## Data Flow

### Primary Request Path — Scan → 3D (outside-in, §8D.45)

1. `POST` scan trigger / `continuous_scanner.watch()` starts a Selenium scan (`backend/services/continuous_scanner.py:58`).
2. `backend/dom/scanner.py` + `backend/mapper/mapper.py` distill DOM → trie patterns → content chunks (`backend/dom/pipeline.py`).
3. Chunks persist to `ContentChunk` / `ChunkInstance`; TF-IDF indexed incrementally (`backend/services/tfidf_service.py`).
4. Scan-end joint UMAP 6D fit + force-directed radial placement (`backend/services/layout_service.py:441` `recompute_ontology`, `_embed_6d`, `_project`).
5. `umap_canonical` (W7) frame broadcast over the workspace WS (`backend/api/routes.py:515` `/ws/workspace/{workspace_id}`).
6. Frontend `backend/static/js/cp/layout.js` + `force_layout.js` render chunks radially from doc-hub; scroll-driven extrusion (`chunk_projector.js`).

### Secondary Flow — Concept mutation → cascade (inside-out, §8D.47)

1. `POST /concepts` or `/concept_edges` handler in `backend/api/routes.py:2239`.
2. Handler calls `apply_update_lifecycle` (`backend/services/concept_lifecycle.py`).
3. Chain fires: WS broadcast (W5 `concept_index_update`) → ConceptIndex upsert + nomic embed → output projection schedule → evolution-log entry → cascade nudge recompiling `{ref}`-consumers.
4. `recompute_concept_index` / PageRank (`backend/services/concept_index_service.py`).

### Compute / agent flow

1. `POST /conceptual/compile_chain` (`routes.py:3306`) → `compile_pipeline.py` recursive descent → LangGraph chain → `slm_client.py` GPT4All dispatch.
2. Agent: `POST /agent/tick` → `agent_runtime.py` → `agent/langgraph_loop.py` streams real tokens (`agent_token` WS frame) → evolution log diff (actor=`agent:*`).

**State Management:**
- Server-authoritative UI state in `backend/services/ui_state_service.py` (pin/hover/halo/collapse), broadcast via WS so multi-tab hydrates without polling.

## Key Abstractions

**ConceptNode / ConceptEdge:**
- Purpose: the one record + the one edge for all graph data.
- Examples: schema in `backend/database.py:240-259` (NODE) and `:433` (REL `ConceptEdge`).
- Pattern: `edge_type` is the union enum of all label families; one edge table never two.

**LayoutFrame:**
- Purpose: serialized 6D/3D coordinate set per workspace.
- Examples: `backend/services/layout_service.py:112`.

**Foundational fixtures:**
- Purpose: three peer undeletable ConceptNodes (Database, WebBrowser, Agent).
- Examples: `backend/services/foundation_fixtures.py`.

**Compiled-from-scans / Python-API trees:**
- Purpose: extend capability as peer nodes (SearchableURL, DetectedAccessor, XPathPattern; python_object/property/function).
- Examples: `backend/services/compiled_from_scans.py`, `backend/services/python_api_materialiser.py`.

## Entry Points

**`app.py`:**
- Location: `app.py`
- Triggers: process launch (tees stdout/stderr to `logs.txt`, runs uvicorn).
- Responsibilities: logging mirror + server boot.

**`backend/main.py`:**
- Location: `backend/main.py:48`
- Triggers: FastAPI app construction; `lifespan` eager-inits Selenium + DB.
- Responsibilities: middleware, static mount, page routes (`/`, `/editor`, `/legacy`), router include.

**WS endpoints:**
- `/ws/workspace/{workspace_id}` (`routes.py:515`) — main layout/index/agent frame stream.
- `/ws/nodes/{snapshot_id}` (`routes.py:648`) — node streaming.
- `/ws/chat/{session_id}` (`routes.py:1330`) — chat session.

## Architectural Constraints

- **Threading:** async FastAPI event loop captured in `lifespan` (`set_event_loop`); worker threads push WS frames via `call_soon_threadsafe`. Scanner runs its own thread loop (`continuous_scanner._run_loop`).
- **Global state:** singleton Selenium `WebBrowserManager` (eager-init in lifespan), singleton continuous scanner (`get_continuous_scanner()`), per-workspace WS frame queues. Kuzu connection in `backend/database.py`.
- **WS seq monotone:** per workspace; `?resume=<seq>` replays last 5 minutes (`backend/services/ws_replay.py`).
- **No real→stub fallback:** a failed subsystem load returns 503 and halts cascade; quiet degradation forbidden (`/api/subsystem_status` must report `all_real: true` in production).

## Anti-Patterns

### Bypassing the lifecycle dispatcher

**What happens:** a handler mutates a ConceptNode directly via `graph_editor` / SQL without calling `apply_update_lifecycle`.
**Why it's wrong:** skips WS broadcast, index upsert, output projection, evolution log, and cascade — downstream consumers go stale and rollback breaks.
**Do this instead:** route every create/update/delete through `backend/services/concept_lifecycle.py` (both `routes.py` and `agent_runtime.py` already do).

### Mixing the two embedding axes

**What happens:** retrieval blends nomic (description) and TF-IDF (rendering) into one score, or reintroduces graph-analytics features (depth, subtree_size, wl_hash).
**Why it's wrong:** forbidden by design; retrieval ranks by the triple product `pagerank · tfidf_cos · nomic_cos`, axes kept separate.
**Do this instead:** keep `tfidf_service.py` and `ontology_field_embedder.py` as sibling pipelines; combine only at the final triple product (`retrieval_service.py`).

### A new card type with its own table

**What happens:** adding a special-cased node kind with a dedicated Kuzu table.
**Why it's wrong:** breaks the one-ConceptNode / one-ConceptEdge invariant.
**Do this instead:** model it as a fixture, compiled-from-scans peer, or Python-API materialised tree on the existing schema.

## Error Handling

**Strategy:** loud failures for the four real subsystems (503 + halted cascade); secondary subsystem hiccups in the lifecycle chain are swallowed with tagged warnings so the primary mutation still completes.

**Patterns:**
- Workflow error handler registered globally (`backend/api/errors.py`, `register_workflow_error_handler`).
- Lifecycle helpers wrap each downstream step in try/except + warning log.

## Cross-Cutting Concerns

**Logging:** all stdout/stderr/logging teed to `logs.txt` via `_Tee` in `app.py`.
**Validation:** idempotency keys on every mutation route (retry-safe by construction).
**Authentication:** none (CORS `allow_origins=["*"]`; local-only app).

---

*Architecture analysis: 2026-06-14*
