# Code Constraint: Backend Services

**Surface scope.** `backend/services/*.py` — every service singleton.

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §2.1 (backend computes, frontend renders), §2.3 (two progressive vectorization pipelines as siblings), §2.8 (subsystem failures are loud), §13 (no-mocks contract), §13.4 (no quiet degradation).

---

## §1 — Must hold

### §1.1 Singletons via accessor

Every service exposes a `get_<name>_service(broadcast=None)` accessor that returns the process-wide singleton, optionally wiring the broadcast hook on first call.

| Service | Accessor |
|---|---|
| LayoutService | `get_layout_service(broadcast=_ws_push)` |
| ConceptIndexService | `get_concept_index_service(broadcast=_ws_push, graph_editor=ge)` |
| UIStateService | `get_ui_state_service(broadcast=_ws_push)` |
| ApparitionService | `get_apparition_service()` |
| EvolutionLog | `get_evolution_log()` |
| GlobalTfidfStore | `get_default_store()` (or `get_default()`) |
| RolloutCoordinator | `get_rollout_coordinator(broadcast=_ws_push)` |
| AgentRuntime | `get_agent_runtime()` |

### §1.2 Eager init in lifespan

Services with heavy startup cost (Selenium driver, LangGraph state machine, GPT4All model) MUST initialise eagerly in the FastAPI lifespan handler so the first user gesture doesn't pay the cold-load cost.

### §1.3 Thread safety

Service singletons MUST be thread-safe. Per-workspace locks where state is per-workspace (UIStateService); coarser locks where state is global (BackingRegistry).

### §1.4 Real backends in production

In production paths:

- SLMClient loads real GPT4All `Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf` on CUDA.
- EmbeddingService loads real GPT4All `Embed4All` with `nomic-embed-text-v1.5.f16.gguf` on CUDA (or CPU if `WFH_EMBEDDER_DEVICE=cpu`).
- SeleniumClient loads real Geckodriver Firefox.
- LangGraph imports `langgraph.graph.StateGraph` — missing import is a hard error, not a fallback.

Fake gates (`WFH_FAKE_SLM=1`, `WFH_FAKE_EMBEDDER=1`, `NO_WEBDRIVER=1`) are HARNESS-ONLY and explicit. Production paths never set them.

**Test signal.** `GET /api/subsystem_status` returns `all_real: true` in production. CI gates on this.

### §1.5 Llama is forbidden

`SLMClient._resolve_model_name` rejects any `WFH_SLM_MODEL=*llama*` loudly. Llama is not a fallback.

**Anti-goal anchor.** Forbidden-concepts §3.

### §1.6 Loud failure

A failed nomic load, a dead Selenium driver, a missing GGUF — these surface as 503s on the affected REST routes; the cascade halts; the WS frames stop. Quiet degradation to stubs is forbidden.

**Anti-goal anchor.** §13.4.

### §1.7 Two-sibling vectorization pipelines

- Chunk side: GlobalTfidfStore (incremental TF-IDF + multi-frequency bands) + LayoutService (joint 6D UMAP at scan-end).
- Concept side: ConceptIndexService (incremental nomic + PageRank refit on cascade settle).

The two services are SIBLINGS, never nested. Each owns its update path; they compose at the ApparitionService level.

### §1.8 LayoutService 6D + perimeter rescale

LayoutService MUST fit 6D UMAP (n_components=6) and apply perimeter rescale for `provenance == agent-output`.

**Anti-goal anchor.** §18.23, the §1.2.2 6D contract.

### §1.9 ApparitionService multi-frequency mode

ApparitionService MUST report active mode via `get_mode()`. After K observed-utility events (default K=32), transitions to multi-frequency aggregation; the transition is automatic.

**Anti-goal anchor.** §18.25.

### §1.10 FoundationFixtures four-fixture materialisation

`ensure_foundation_fixtures(workspace_id)` MUST produce exactly FOUR root python_object ConceptNodes (Agent, WebBrowser, Database, Editor) plus their member trees. Idempotent on `backing_pointer` match.

**Anti-goal anchor.** §18.27.

### §1.11 PythonAPIMaterialiser library-imports middleware

The materialiser MUST handle arbitrary imported libraries via the `wfh_imports.py` middleware — not just the three fixtures (§S removed Editor).

**Anti-goal anchor.** §18.28.

### §1.12 ChunkBuilder pattern detection + live-update emission

ChunkBuilder MUST detect chunk patterns incrementally during scan and emit `concept_changed` on the `pattern_map` ConceptNode per detection. Pattern detection MUST include golden-trio extraction per §15.8.1.

**Anti-goal anchor.** §18.29.

---

## §2 — Must not

### §2.1 Quietly substitute a stub for a missing real backend in production

§13.4. Missing GGUF → 503; missing Selenium → 503; missing LangGraph → import error at module load.

### §2.2 Run UMAP with `n_components=3` (position only)

§1.2.2 + §1.8 require 6D fit.

### §2.3 Skip perimeter rescale for agent-output chunks

§18.23.

### §2.4 Materialise fewer than four foundation fixtures

§18.27.

### §2.5 Persist UIStateService state to disk

§10.5 — UI state is in-memory only.

### §2.6 Share state between workspaces in any service

Workspace isolation is invariant.

### §2.7 Bypass the broadcast hook on service mutation

Every state-changing service method that affects user-visible state emits the appropriate WS frame.

### §2.8 Run on a service singleton before it's initialised

Accessor-on-first-use pattern; if init fails (e.g., missing GGUF), the call propagates 503 to the caller.

---

## §3 — Code anchors

| File | Service | Constraints touched |
|---|---|---|
| `backend/services/concept_lifecycle.py` | ConceptLifecycle (dispatcher) | §1.1, §1.6 (loud), §1.3 (thread safety) |
| `backend/services/layout_service.py` | LayoutService | §1.1, §1.8 (6D + perimeter) |
| `backend/services/concept_index_service.py` | ConceptIndexService | §1.1, §1.7 (sibling) |
| `backend/services/apparition_service.py` | ApparitionService | §1.1, §1.9 (multi-freq mode) |
| `backend/services/conceptual_compute.py` | ConceptualCompute (LangGraph) | §1.4 (LangGraph required) |
| `backend/services/python_api_materialiser.py` | PythonAPIMaterialiser | §1.11 (middleware) |
| `backend/services/foundation_fixtures.py` | FoundationFixtures | §1.10 (three fixtures; §S removed Editor) |
| `backend/services/agent_runtime.py` | AgentRuntime | §1.4 (real GPT4All), §1.5 (no Llama) |
| `backend/services/slm_client.py` | SLMClient | §1.4 (real model), §1.5 (no Llama) |
| `backend/services/embedding_service.py` | EmbeddingService | §1.4 (real nomic) |
| `backend/services/selenium_client.py` | SeleniumClient (WebBrowserManager) | §1.2 (eager init), §1.4 (real driver) |
| `backend/services/ui_state_service.py` | UIStateService | §1.1, §1.3 (per-workspace locks) |
| `backend/services/evolution_log.py` | EvolutionLog | §1.1, atomic with Kuzu |
| `backend/services/global_tfidf_store.py` | GlobalTfidfStore | §1.7 (sibling); multi-freq bands |
| `backend/services/backing_registry.py` | BackingRegistry | §1.3 (thread safety) |
| `backend/services/compiled_from_scans.py` | CompiledFromScans | (pattern materialisation surface) |

---

## §4 — Anti-goal anchors

| Constraint | Anti-goal |
|---|---|
| §1.4 (real backends) | §13.4, §18 (no mocks) |
| §1.5 (no Llama) | Forbidden-concepts §3 |
| §1.8 (6D + perimeter) | §18.23, §1.2.2 contract |
| §1.9 (multi-freq mode) | §18.25 |
| §1.10 (three fixtures) | §18.27 |
| §1.11 (library middleware) | §18.28 |
| §1.12 (live pattern_map) | §18.29 |
| §1.6 (loud) | §13.4 |

---

## §5 — Feature touchpoints

- [`four_fixture_api.md`](../features/four_fixture_api.md)
- [`6d_umap.md`](../features/6d_umap.md)
- [`halo_retrieval.md`](../features/halo_retrieval.md)
- [`multi_frequency_pagerank.md`](../features/multi_frequency_pagerank.md)
- [`library_imports_middleware.md`](../features/library_imports_middleware.md)
- [`pattern_map.md`](../features/pattern_map.md)
- [`live_scan_streaming.md`](../features/live_scan_streaming.md)
- [`no_mocks_contract.md`](../features/no_mocks_contract.md)
- [`perimeter_outputs.md`](../features/perimeter_outputs.md)
