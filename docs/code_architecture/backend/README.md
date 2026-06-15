# Code Architecture — Backend Suite

> **Status: planned (align existing).** The backend service decomposition, distilled from `DOMAIN_MODEL.md` §6–§15 and aligned to the design (keep the real subsystems; remove the forbidden frameworks — [`../migration.md`](../migration.md)). Each doc carries: responsibility · public surface (signatures) · internal logic · dependencies · realises (`code_constraints/`) · excluded. Shared records are in [`../data_schemas.md`](../data_schemas.md); wire contracts in [`../contracts.md`](../contracts.md); no-mocks boundaries in [`../subsystems.md`](../subsystems.md).

---

## §1 — The Seams

- **One lifecycle dispatcher** ([`lifecycle.md`](lifecycle.md)) — every mutation, every actor, one path (§10.2). No second mutation path.
- **Two progressive vectorization pipelines, siblings, never nested** (§2.3): the **chunk side** ([`layout.md`](layout.md) + `GlobalTfidfStore` in [`retrieval.md`](retrieval.md)) and the **concept side** ([`retrieval.md`](retrieval.md): ConceptIndexService). The two embedding axes never mix *for chunks* (§8D.17.1); knowledge panels deviate (§O.22).
- **Backend computes; frontend renders** (§2.1) — layout, embeddings, PageRank, compile, apparition scoring, the UI-state mirror are all backend.
- **Process-wide singletons** bound on the FastAPI lifespan; resolved through `BackingRegistry` ([`persistence.md`](persistence.md)).
- **Idempotency on every mutation; append-only evolution log; optimistic concurrency, last-write-wins** (§2.5–§2.7).

---

## §2 — Service Map

| Doc | Owns | Key file(s) (align) |
|---|---|---|
| [`lifecycle.md`](lifecycle.md) | mutation dispatcher + cascade scheduler | `concept_lifecycle.py` |
| [`layout.md`](layout.md) | 6D UMAP-linear-radial-force layout authority | `layout_service.py` |
| [`retrieval.md`](retrieval.md) | concept index + apparitions + TF-IDF + nomic | `concept_index_service.py`, `apparition_service.py`, `global_tfidf_store.py`, `embedding_service.py` |
| [`compute.md`](compute.md) | compile (LangGraph) + cascade + iterated rollout | `conceptual_compute.py`, `compile_pipeline.py`, `rollout_coordinator.py` |
| [`agent.md`](agent.md) | agent runtime + Agent fixture + `template` + SLM | `agent_runtime.py`, `slm_client.py` |
| [`materialiser.md`](materialiser.md) | python-API trees + library middleware + fixtures | `python_api_materialiser.py`, `foundation_fixtures.py` |
| [`scanner.md`](scanner.md) | Selenium scan + chunk build + pattern_map + web ontology | `selenium_client.py`, `chunk_builder.py`, `compiled_from_scans.py`, `dom/` |
| [`persistence.md`](persistence.md) | Kuzu + LayoutFrame/index files + evolution log + backing registry + UI mirror | `evolution_log.py`, `backing_registry.py`, `ui_state_service.py` |

---

## §3 — Reading Order

`lifecycle.md` (the funnel everything routes through) → `layout.md` + `retrieval.md` (the two pipelines) → `compute.md` (compile/cascade/rollout) → `scanner.md` + `materialiser.md` (where chunks and fixtures come from) → `agent.md` (the meta-cognition loop) → `persistence.md` (storage + mirror). Cross-cutting: [`../subsystems.md`](../subsystems.md) (no-mocks) and [`../migration.md`](../migration.md) (removals).
