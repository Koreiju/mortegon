# Code Architecture Suite

> **Status: planned (implementation blueprint).** The from-design code architecture. No code is written against it yet.
>
> **What this suite is.** The **implementation blueprint** — the layer that turns the design (`DOMAIN_MODEL.md` + the `frontend/` suite + the object/feature/constraint docs) into a concrete module/service decomposition, data schemas, wire contracts, and per-module internal logic + key signatures. It sits **below** [`code_constraints/`](../code_constraints/) in the chain: where `code_constraints/` says *what conditions the code must hold*, this suite says *how the code is structured to hold them*.
>
> **Precedence.** Design wins on *intent*: when this suite disagrees with `DOMAIN_MODEL.md` / `USER_REQUIREMENTS_VERBATIM.md` §M/§N/§O / the `frontend/` suite, the design wins and this blueprint is corrected. This suite is authoritative only on *structure* (which file owns what, which signature, which schema).

---

## §0 — The Selectivity Filter (what we factor in, and what we don't)

This suite is **deliberately selective**. The design docs carry far more than the code needs.

**Factored IN** (design → code architecture):
- **Module / service decomposition + responsibilities** — one file/object per responsibility.
- **The seams** — the one lifecycle dispatcher (§10.2); the two vectorization pipelines (§2.3); the frontend's three Spine seams (FrameBus / WorkspaceStore / GestureGateway).
- **Data schemas** — ConceptNode, ConceptEdge, EditDiff, LayoutFrame, ChunkPatternSchema, UIState ([`data_schemas.md`](data_schemas.md)).
- **Wire contracts** — REST routes, WS frames, idempotency, `subsystem_status` ([`contracts.md`](contracts.md)).
- **No-mocks subsystem boundaries** — SLM / embedder / Selenium / LangGraph + the harness-only fake gates (§13).
- **Named algorithms** (interface + internal logic, not derivation) — the triple-product retrieval + the panel `max(minmax(nomic), minmax(tfidf))` deviation (§8.1 / §O.22), the UMAP-linear-radial-force layout with target-sphere fit + 1D-radial settle (§6.1 / §O.17), the recursive syntax-agnostic compile (§7.1), the cone-ray-similarity halo transport (§O.18).
- **Per-module internal logic + key function signatures** (the Q2 depth choice).

**Factored OUT** (stays design-only; *not* in this suite):
- The **Mortegon philosophy** — registers (Real / Imaginary / Symbolic), alchemy, telos, shape-of-death. (Architectural *consequences* are factored in; the framing is not.)
- **Aspirational / long-horizon** items — the fluid-agent simulation (§12.8).
- **Theme / UX micro-detail** — the stainless-steel-over-black visual system, hover tints, easing curves. (Lives in `frontend/theme.md`; the code architecture references it, doesn't restate it.)
- The **historical analysis-plan** — `MORTEGON_INTEGRATION_SCHEME.md`, `CODEBASE_GAP_ANALYSIS.md` (§O.17).
- **Forbidden / legacy code** — not architected around; listed once in the **keep/remove ledger** (§4) as remove/replace targets.

The rule: *if it changes what a file does or what a signature is, it's in; if it's why the design wants it, it's out.*

---

## §1 — Place In The Doc Chain

```
DOMAIN_MODEL → object_model/ → features/ → code_constraints/ → code_architecture/ → code_specs/ → CODE
(intent)       (object shape)  (UX)        (must-hold)         (THIS: how it's built)  (exact contract)
```

Each doc here cross-references the design by `§X.Y` (into `DOMAIN_MODEL.md`) and `§O.n` (into `USER_REQUIREMENTS_VERBATIM.md`), and names the `code_constraints/` surface it realises. The **line-level specs** one layer down — exact typed signatures, pre/postconditions, raised errors, constants, and step-precise algorithms — live in [`../code_specs/`](../code_specs/) (this suite gives the *blueprint*; that suite gives the *implementable contract*).

---

## §2 — The Suite

**Top level — shared + cross-cutting:**
| Doc | Scope |
|---|---|
| [`data_schemas.md`](data_schemas.md) | The 6 records (ConceptNode, ConceptEdge, EditDiff, LayoutFrame, ChunkPatternSchema, UIState) + the backing-pointer registry + the persistence map |
| [`contracts.md`](contracts.md) | REST route table (gesture catalogue → endpoints), WS frame schemas + sequencing, idempotency/resume/backpressure, `subsystem_status`, lifecycle fan-out |
| [`subsystems.md`](subsystems.md) | The four real subsystems (SLM / embedder / Selenium / LangGraph) + harness-only fake gates + the no-mocks contract + `subsystem_status` |
| [`migration.md`](migration.md) | The keep / remove / replace ledger — forbidden (graph-analytics, hyperbolic, Llama) + legacy (`cp/*.js`) → targets, per file |

**Backend** ([`backend/`](backend/) — index [`backend/README.md`](backend/README.md)):
| Doc | Service(s) |
|---|---|
| [`backend/lifecycle.md`](backend/lifecycle.md) | ConceptLifecycle dispatcher + cascade scheduler |
| [`backend/layout.md`](backend/layout.md) | LayoutService (6D UMAP-linear-radial-force) |
| [`backend/retrieval.md`](backend/retrieval.md) | ConceptIndexService + ApparitionService + GlobalTfidfStore + EmbeddingService |
| [`backend/compute.md`](backend/compute.md) | ConceptualCompute + LangGraph + compile pipeline + RolloutCoordinator |
| [`backend/agent.md`](backend/agent.md) | AgentRuntime + Agent fixture + `template` + SLMClient |
| [`backend/materialiser.md`](backend/materialiser.md) | PythonAPIMaterialiser + library middleware + FoundationFixtures |
| [`backend/scanner.md`](backend/scanner.md) | WebBrowserManager (Selenium) + ChunkBuilder + `pattern_map` + compiled-from-scans |
| [`backend/persistence.md`](backend/persistence.md) | Kuzu + LayoutFrame / ConceptIndex files + EvolutionLog + BackingRegistry + UIStateService mirror |

**Frontend** (greenfield; [`frontend/`](frontend/) — index [`frontend/README.md`](frontend/README.md)):
| Doc | Tier / modules |
|---|---|
| [`frontend/spine.md`](frontend/spine.md) | FrameBus + WorkspaceStore + GestureGateway |
| [`frontend/cell.md`](frontend/cell.md) | ConceptView + FieldTree + field_strategies |
| [`frontend/real.md`](frontend/real.md) | Projector + chunk_field + texture_cache (3D + scan streaming) |
| [`frontend/imaginary.md`](frontend/imaginary.md) | Editor + subgraph_layout (2D + cascade reflow) |
| [`frontend/membranes.md`](frontend/membranes.md) | Billboard + Halo + LinkLayer |
| [`frontend/pulse.md`](frontend/pulse.md) | Reconciler + tweens + raf (liveness engine) |

---

## §3 — Per-Doc Template

Each architecture doc covers, per module/service:
1. **Responsibility** — the one job it owns (cross-ref the design §).
2. **Public surface** — key class / function signatures (Python for backend, TS-ish for frontend).
3. **Internal logic** — the load-bearing algorithm / control flow, as pseudocode or a sequence (the Q2 depth).
4. **Dependencies** — what it calls; what calls it; through which seam.
5. **Realises** — the `code_constraints/` rule(s) it satisfies.
6. **Excluded** — design matter deliberately *not* encoded here (per §0).

---

## §4 — Keep / Remove Ledger (existing code)

The backend is aligned to the design; the frontend is greenfield. The existing tree carries design-**forbidden** and **legacy** code that the architecture targets for removal/replacement, not adaptation.

| Existing code | Verdict | Why / target |
|---|---|---|
| `backend/services/` lifecycle / layout / ui-state / scanner glue, `backend/mapper/` (Selenium scan), Kuzu/cypher, SLM + embedding wrappers | **Keep & align** | The real subsystems; align signatures to the [`backend/`](backend/) suite |
| `backend/analytics/algorithms/*` (topology, spectral, curvature, centrality, tree-kernels, graphlets, wavelets, hyperbolic-embeddings, graph-invariants, hashing) | **Remove** | The **forbidden graph-analytics retrieval framework** (top-of-doc forbidden concepts; §19). Retrieval is the triple product (§8.1), not graph analytics |
| `backend/analytics/{scoring,clustering,evolution,auto_fit,ontologizer,...}` keyed to the analytics framework | **Audit → remove or fold** | Keep only what the design's retrieval/index/evolution-log needs; drop the analytics-framework dependents |
| `backend/ontology/hyperbolic_layout.py`, `gyrovector.py` | **Remove** | **Forbidden layout** — replaced by UMAP-linear-radial-force (§6.1) |
| `backend/ontology/{knowledge_graph,cypher_engine,field_types,models}.py` | **Keep & align** | Concept graph / Kuzu / typed fields are design-current |
| `backend/static/js/cp/*.js`, `chunk_projector.js`, `chunk_projector.monolith.js` | **Replace** | The legacy frontend; superseded by the greenfield `fe/` tree (the [`frontend/`](frontend/) suite; `FRONTEND_REDESIGN.md` §11) |
| Any Llama SLM path / `_FAST_HARNESS_MODEL` | **Remove** | **Forbidden** — Nous-Hermes-2-Mistral-7B-DPO only (§13.5) |
| `scripts/sim_frontend.py` + `probe_live_*` | **Keep** | The REPL verification surface (§14) |
| `backend/agentic/fluid_engine.py` | **Defer** | Realises the aspirational fluid-sim (§12.8) — out of the current blueprint scope (§0) |

[`migration.md`](migration.md) carries the per-file keep/remove/replace detail and the `cp/` → `fe/` dissolution map.

---

## §5 — Conventions

- **Backend computes; frontend renders** (§2.1). No UMAP / embedder / PageRank / compile on the client.
- **Greenfield frontend** — the `fe/` module tree is built fresh from `FRONTEND_REDESIGN.md` §11; the legacy `cp/*.js` is not a reference.
- **No-mocks in production** (§13) — the four real subsystems always; fake gates are harness-only and never set in production paths.
- **One lifecycle dispatcher; one inbound WS seam; one outbound gesture seam** — every mutation and every gesture routes through the single seam (§10.2 backend; FrameBus/GestureGateway frontend).
- **Idempotency on every mutation route** (§2.5); **append-only evolution log** (§2.6).
- Signatures here are **indicative** (names + shapes), not frozen API — the design's intent governs; this suite keeps them coherent.
