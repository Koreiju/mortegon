# Documentation Map — Web Fiber Haptics

> **⚠ All-Real Tests For Everything (DOMAIN_MODEL §0 / §13, verbatim §Q.1).** The load-bearing testing mandate cuts across every layer of this chain: every feature is verified end-to-end against the **real** stack — real SLM (Nous-Hermes-2-Mistral-7B-DPO/CUDA), real embedder (nomic/CUDA), real WebBrowser (live Selenium), real LangGraph — with `GET /api/subsystem_status` reporting `all_real: true`. A stub-only "pass" is never sufficient. The mandate down-flows: **DOMAIN_MODEL §0** (statement) → object/feature docs (per-capability acceptance) → **code_specs/repl.md** + **code_specs/backend/scanner.md** (spec-level assertions) → `scripts/probe_no_mocks.py` + `probe_live_*.py` + the `all_real`-gated env-scenarios (code). New capability ships with its all-real probe/scenario or it does not ship (§14.4).

> **Purpose.** This is the navigation index for the design-and-realisation chain across the workspace's documentation. The chain runs from **design ideation** (the source-of-truth domain model) through **object-level elaboration** (one document per first-class object in the model) and **feature-level elaboration** (one document per cross-cutting user-visible feature) into **code-level constraint specification** (one document per programming surface the codebase must hold). At every link of the chain, downstream documents inherit from upstream and add the next layer of specificity; the chain is non-circular; the upstream is always authoritative when two layers conflict.

---

## §0 — The Layered Chain

```
DESIGN IDEATION                  OBJECT ELABORATION                 FEATURE ELABORATION                   CODE CONSTRAINT
═══════════════════              ══════════════════                 ══════════════════                    ═══════════════
DOMAIN_MODEL.md            →     object_model/<Object>.md       →   features/<feature>.md            →    code_constraints/<surface>.md
(philosophical anchor)           (first-class-object reference)     (cross-cutting feature reference)     (programming-surface conditions)
(verbatim user voice)            (data shape + invariants)          (UX contract + acceptance bar)        (must-hold / must-not-hold)
(register-level framing)         (lifecycle + lifecycle hooks)      (REPL gestures + WS frames)           (concurrency / persistence / errors)
                                 (how objects compose)              (sequence-level state machine)        (test scenarios + probes)
```

| Layer | What it answers | Where to look |
|---|---|---|
| **Design ideation** | *What is this workspace for, philosophically and structurally? What does the user mean when they say X?* | [`DOMAIN_MODEL.md`](DOMAIN_MODEL.md) |
| **Object elaboration** | *What is the shape of object O? What invariants hold over its lifetime? How does it compose with peers?* | [`object_model/`](object_model/) |
| **Feature elaboration** | *What is the user-visible behaviour of feature F? What gestures invoke it? What is its full state machine?* | [`features/`](features/) |
| **Code constraints** | *What conditions must the codebase hold for the design to be realised? What patterns are forbidden?* | [`code_constraints/`](code_constraints/) |
| **Code architecture** | *How is the code structured to hold the design — modules, services, schemas, REST/WS contracts, internal logic?* | [`code_architecture/`](code_architecture/) |
| **Code specs** | *What is the exact implementable contract — typed signatures, pre/post, errors, constants, step-precise algorithms?* | [`code_specs/`](code_specs/) |

The chain extends past the four elaboration layers above into the two code layers: `code_constraints/` → `code_architecture/` (blueprint) → `code_specs/` (line-level contract) → CODE.

### §0.1 The Source-of-Truth Order

When two layers disagree, **the more authoritative layer wins**, with the precedence:

1. [`USER_REQUIREMENTS_VERBATIM.md`](USER_REQUIREMENTS_VERBATIM.md) — the user's words verbatim.
2. [`DOMAIN_MODEL.md`](DOMAIN_MODEL.md) — the integrated design elaboration.
3. [`object_model/`](object_model/) docs — object-level realisation.
4. [`features/`](features/) docs — feature-level realisation.
5. [`code_constraints/`](code_constraints/) docs — code-level realisation.
6. [`code_architecture/`](code_architecture/) docs — structural realisation (authoritative on *structure*, not intent).
7. [`code_specs/`](code_specs/) docs — line-level realisation (authoritative on *exact contract*, not intent).

(Layers 6–7 never override design intent: when a spec or blueprint disagrees with the design, the design wins and the lower layer is corrected.)

So if `object_model/Database.md` says one thing and `DOMAIN_MODEL.md` §9.5.1 says another, the DOMAIN_MODEL wins. If a code-constraint says "the lifecycle dispatcher must broadcast `concept_changed`" and the DOMAIN_MODEL §10.2 says "the lifecycle dispatcher must broadcast `concept_changed`", they agree because the code constraint is *derived from* the design. If they disagree, the code constraint is wrong and must be updated to match.

### §0.2 What Each Layer Adds

- The **domain model** captures *what the workspace is and what the user wants it to do*. It is philosophical (the three registers), structural (the four fixtures), and behavioural (the lodestar use cases). It uses the user's voice where possible.
- The **object model** docs decompose the domain model into *first-class objects* — data records, services, frontend components, scanner stages — each documented with its shape, lifecycle, invariants, peer interactions, and the section in DOMAIN_MODEL it elaborates.
- The **feature** docs reorganise the same content along *cross-cutting user-visible features* — halo retrieval crosses ApparitionService + LayoutService + UIStateService + frontend halo renderer; the four-fixture API crosses all four fixture objects + the materialiser middleware + the lifecycle dispatcher. Feature docs are the layer where UX contracts and acceptance bars live.
- The **code constraint** docs articulate the *programming-side conditions* the codebase must hold to realise the upstream layers — concurrency rules, persistence invariants, REST/WS shape contracts, test scenarios, anti-patterns, and CI acceptance gates.

---

## §1 — The Domain Model (Design Ideation)

[`DOMAIN_MODEL.md`](DOMAIN_MODEL.md) is the source. **Read it first.** Every downstream doc in this map cross-references DOMAIN_MODEL sections; the cross-references are by `§X.Y` and resolve unambiguously within DOMAIN_MODEL's section numbering.

Key entry points in the domain model:

| Section | Topic |
|---|---|
| §1.1 / §1.5 | The three Mortegon registers: Real / Imaginary / Symbolic |
| §1.2 / §1.2.1 / §1.2.2 | The four foundational fixtures and the user's verbatim spec |
| §3 | The ConceptNode + ConceptEdge schema |
| §4 / §4.1.1 / §4.6 / §4.6.1 / §4.6.2 | The unified knowledge panel UX |
| §6 / §6.1 / §6.6 | The 3D projector and the 6D UMAP |
| §6.6.4 | The computation-graph node — bisector placement + projector link network (§P) |
| §7 / §7.1 / §7.3 / §7.7 | Compilation, dialectical inversion, closest-inverse |
| §7.8 / §7.8.1–§7.8.5 | The compute graph as reservoir computer + cascaded rollout to the readout perimeter (§M / §P) |
| §8 / §8.1.1 / §8.2 / §8.2.1 | Retrieval and the halo |
| §9.5 / §9.5.1 / §9.6 / §9.7 | The four fixtures and the library-imports middleware |
| §10 / §10.2 | Streaming + lifecycle dispatcher |
| §11 / §11.4 | Persistence and the evolution log |
| §12 / §12.2 / §12.2.1 / §12.6.1 | The agent and editor-entanglement |
| §13 | The no-mocks contract |
| §14 / §14.2 / §14.5 | REPL ↔ frontend two-way feedback |
| §15 / §15.7 / §15.8 | The scanner, URL-set panels, `pattern_map` |
| §16 / §16.5 | Lodestar use cases + live-scan + DB-cleanup probe |
| §17 | Functional sequences reference |
| §18 | Known failure modes (anti-goals) |
| §20 | Glossary and cross-reference index |

### §1.1 Companion Source Documents

- [`USER_REQUIREMENTS_VERBATIM.md`](USER_REQUIREMENTS_VERBATIM.md) — every binding requirement in the user's own phrasing.
- [`CODEBASE_GAP_ANALYSIS.md`](CODEBASE_GAP_ANALYSIS.md) — **historical** (§O.17): an audit of the now-discarded codebase; its design intent is already in `DOMAIN_MODEL.md` §18 + the design docs. Not an implementation target.
- [`MORTEGON_INTEGRATION_SCHEME.md`](MORTEGON_INTEGRATION_SCHEME.md) — **historical** (§O.17): the operational 3D↔2D scheme; its additive detail is lifted into `DOMAIN_MODEL.md` §6.1 / §7.3.2 / §4.6 + the [`frontend/`](frontend/) suite.
- [`FRONTEND_REDESIGN.md`](FRONTEND_REDESIGN.md) — the frontend's vision-first **object model**: how the design's registers (§1.5), unified panel (§4), projector (§6), and halo (§8.2) become a from-scratch set of frontend objects (Spine / Cell / Canvases / Membranes / Pulse). The "missing middle" between *backend computes, frontend renders* (§2.1) and `code_constraints/frontend_rendering.md`. Object docs in `object_model/` (KnowledgePanel, FieldTree, Halo, Billboard, Projector) reconcile to its object set.
- [`frontend/`](frontend/) — the **standalone frontend API & feature reference suite** (21 docs, incl. [`frontend/object_exploration.md`](frontend/object_exploration.md) — recursive type-strict object-model exploration, the five-gesture panel model of §7.3.4, and the reservoir generative readout of §7.8).
  One document per surface, each complete on its own (identity / structure / composition / behaviours / activities / sequences / data / results / REPL mirroring / theme). [`frontend/README.md`](frontend/README.md) is the index; [`frontend/theme.md`](frontend/theme.md) is the dark-minimal stainless-steel-over-black visual system every other doc applies. This suite *references* the `FRONTEND_REDESIGN.md` object set; the redesign doc is the anchor, the suite is the detail.
- [`code_architecture/`](code_architecture/) — the **implementation blueprint** suite. **Top level:** README + [`data_schemas`](code_architecture/data_schemas.md) + [`contracts`](code_architecture/contracts.md) (REST + WS) + [`subsystems`](code_architecture/subsystems.md) (no-mocks) + [`migration`](code_architecture/migration.md) (keep/remove/replace ledger). **Per-area subdirs:** [`code_architecture/backend/`](code_architecture/backend/) (lifecycle · layout · retrieval · compute · agent · materialiser · scanner · persistence) and [`code_architecture/frontend/`](code_architecture/frontend/) (spine · cell · real · imaginary · membranes · pulse). Sits **below** `code_constraints/` — *how* the code is structured to hold the design: module/service decomposition, per-module internal logic + key signatures. Selectively distilled ([`code_architecture/README.md`](code_architecture/README.md) §0 filter — philosophy / aspiration / theme micro-detail / historical analysis-plan left out); backend **aligned**, frontend **greenfield**. Each area doc: responsibility · signatures · internal logic · dependencies · realises · excluded.
- [`code_specs/`](code_specs/) — the **line-level implementation specs**, one layer below `code_architecture/` and immediately above CODE. **Foundation:** README + [`types`](code_specs/types.md) (every record/enum/DTO/WS-frame fully typed) + [`constants`](code_specs/constants.md) (every magic number, value · meaning · source) + [`errors`](code_specs/errors.md) (exception → HTTP/WS/cascade catalogue). **Per-area:** [`code_specs/backend/`](code_specs/backend/) (api · lifecycle · layout · retrieval · compute · agent · materialiser · scanner · persistence) + [`code_specs/frontend/`](code_specs/frontend/) (spine · cell · real · imaginary · membranes · pulse) + [`code_specs/repl.md`](code_specs/repl.md) (sim_frontend actions · watch-activity 7-row dashboard · env-scenario contract · live probes). Each function: signature · params · returns · raises · pre/post · idempotency · step-precise algorithm · complexity · example.

---

> **Catalogue status (2026-05-30 cleanup).** The §2 / §3 / §4 catalogues below are partly aspirational; several listed docs were never created. **Existing files — `object_model/`:** ConceptNode, ConceptEdge, ChunkPatternSchema, Agent, WebBrowser, Database, Editor, ConceptLifecycle, LayoutService, ApparitionService, UIStateService, PythonAPIMaterialiser, RolloutCoordinator, Halo. **`features/`:** three_register_model, four_fixture_api, halo_retrieval, 6d_umap, signal_stream, click_to_edit, pattern_map, live_scan_cleanup. **`code_constraints/`:** lifecycle_invariants, ws_frames, repl_actions, api_routes, env_scenarios, backend_services, streaming, persistence, frontend_rendering. **All other rows are planned (no file yet).** The frontend per-component object docs (`KnowledgePanel`, `FieldTree`, `Billboard`, `Projector`, `PatternMap`, `URLSetPanel`) are **superseded by the [`frontend/`](frontend/) suite** + [`FRONTEND_REDESIGN.md`](FRONTEND_REDESIGN.md) — use those. Disregard dangling links to non-existent files.

## §2 — The Object Model (`object_model/`)

[`object_model/README.md`](object_model/README.md) is the object index. Each object doc carries:

- **Domain anchor** — the section(s) in DOMAIN_MODEL it elaborates.
- **Shape** — fields, types, defaults, invariants.
- **Lifecycle** — how the object is created, mutated, and disposed; which dispatcher handles each transition.
- **Peer interactions** — what it depends on, what depends on it.
- **Persistence** — where it lives in storage; what is persisted vs in-memory.
- **Anti-patterns** — what the object must never do.

### §2.1 Object Catalogue

**Data records:**
- [`ConceptNode.md`](object_model/ConceptNode.md) — the universal record (§3.1)
- [`ConceptEdge.md`](object_model/ConceptEdge.md) — hard links + soft links (§3.2)
- [`EditDiff.md`](object_model/EditDiff.md) — the evolution-log record (§11.4)
- [`LayoutFrame.md`](object_model/LayoutFrame.md) — the per-workspace 6D UMAP coords (§6.1, §11.1)
- [`ChunkPatternSchema.md`](object_model/ChunkPatternSchema.md) — `pattern_map` entries (§15.8)
- [`UIState.md`](object_model/UIState.md) — frontend UI mirror (§10.5)

**Foundational fixtures (§9.5):**
- [`Agent.md`](object_model/Agent.md) — SLM primitives (meta_prompt / prompt / output)
- [`WebBrowser.md`](object_model/WebBrowser.md) — `scan(url, query?)` + companions
- [`Database.md`](object_model/Database.md) — `search` / `cypher` / `concept`
- [`Editor.md`](object_model/Editor.md) — `create` / `link` / `overwrite` / `delete`

**Backend services:**
- [`ConceptLifecycle.md`](object_model/ConceptLifecycle.md) — the single mutation dispatcher (§10.2)
- [`LayoutService.md`](object_model/LayoutService.md) — 6D UMAP + perimeter rescaling (§10.3, §6.1, §6.6.1)
- [`ConceptIndexService.md`](object_model/ConceptIndexService.md) — multi-frequency PageRank (§10.4, §8.1.1)
- [`ApparitionService.md`](object_model/ApparitionService.md) — halo retrieval + ray-projection (§8.2)
- [`ConceptualCompute.md`](object_model/ConceptualCompute.md) — ConceptComputeNode + LangGraph (§10.6, §11.7)
- [`PythonAPIMaterialiser.md`](object_model/PythonAPIMaterialiser.md) — library-imports middleware (§9.6, §9.7)
- [`AgentRuntime.md`](object_model/AgentRuntime.md) — MetaCognitionTick + ActionResolver (§12)
- [`EvolutionLog.md`](object_model/EvolutionLog.md) — append-only diff store (§11.4)
- [`UIStateService.md`](object_model/UIStateService.md) — frontend mirror (§10.5)
- [`FoundationFixtures.md`](object_model/FoundationFixtures.md) — four-fixture ensure (§9.5)
- [`GlobalTfidfStore.md`](object_model/GlobalTfidfStore.md) — url-specific tokenisation + multi-freq bands (§15.7, §8.1.1)
- [`RolloutCoordinator.md`](object_model/RolloutCoordinator.md) — play/pause + signal-stream advance (§7.5, §17.1.2)
- [`BackingRegistry.md`](object_model/BackingRegistry.md) — backing pointer resolution (§3.3)
- [`ChunkBuilder.md`](object_model/ChunkBuilder.md) — pattern detection + golden trio (§15.4, §15.8.1)
- [`SeleniumClient.md`](object_model/SeleniumClient.md) — WebBrowserManager (§15.1)
- [`SLMClient.md`](object_model/SLMClient.md) — GPT4All wrapper (§13.5)
- [`EmbeddingService.md`](object_model/EmbeddingService.md) — nomic wrapper (§10.4)

**Frontend components (`cp/`):**
- [`KnowledgePanel.md`](object_model/KnowledgePanel.md) — the unified panel widget (§4)
- [`FieldTree.md`](object_model/FieldTree.md) — recursive editable tree (§4.6)
- [`Halo.md`](object_model/Halo.md) — concentric-circle halo with ray-projection (§8.2.1, §8.2.1.1, §8.2.1.2)
- [`URLSetPanel.md`](object_model/URLSetPanel.md) — `{urls_panel}` aggregator (§15.7)
- [`PatternMap.md`](object_model/PatternMap.md) — output panel (§15.8.2)
- [`Billboard.md`](object_model/Billboard.md) — hover billboard + 3D-resident chunk visual (§4.2, §6.1)
- [`Projector.md`](object_model/Projector.md) — Three.js scene + HSV-rotation animate loop (§6.2, §8.2.1.2)

---

## §3 — The Feature Documentation (`features/`)

[`features/README.md`](features/README.md) is the feature index. Each feature doc carries:

- **Domain anchor** — the section(s) in DOMAIN_MODEL it elaborates.
- **What the user sees** — UX contract in plain prose.
- **Gestures** — REPL actions, GUI gestures, agent emit-paths.
- **State machine** — full sequence from gesture to settled state.
- **WS frames + telemetry** — what crosses the wire.
- **Acceptance bar** — what env-scenario asserts the feature works.
- **Cross-objects** — which objects participate.

### §3.1 Feature Catalogue

**Framing features:**
- [`three_register_model.md`](features/three_register_model.md) — Real / Imaginary / Symbolic alchemical loop (§1.5)
- [`compile_collapse_dialectic.md`](features/compile_collapse_dialectic.md) — Right-click panel ↔ subgraph (§7.3)
- [`hard_soft_links.md`](features/hard_soft_links.md) — Commitment fan + possibility ring (§3.2.1)
- [`projective_inverse.md`](features/projective_inverse.md) — Closest-inverse as projection (§7.7)
- [`agent_integration_scheme.md`](features/agent_integration_scheme.md) — Recursion-over-iteration (§12.2.1)
- [`perimeter_outputs.md`](features/perimeter_outputs.md) — Agent outputs at projector edge (§6.6.1)
- [`2d_3d_separation.md`](features/2d_3d_separation.md) — Canvas separation contract (§6.6.2)

**API features:**
- [`four_fixture_api.md`](features/four_fixture_api.md) — Agent / WebBrowser / Database / Editor (§9.5.1)
- [`library_imports_middleware.md`](features/library_imports_middleware.md) — Generalised materialiser (§9.7)

**Retrieval features:**
- [`halo_retrieval.md`](features/halo_retrieval.md) — Concentric circles + ray-projection + autoregression (§8.2)
- [`multi_frequency_pagerank.md`](features/multi_frequency_pagerank.md) — Token / phrase / paragraph / document / pattern bands (§8.1.1)
- [`autoregressive_halo.md`](features/autoregressive_halo.md) — Walk the retrieval space (§8.2.2)

**3D / projector features:**
- [`6d_umap.md`](features/6d_umap.md) — 3 position + 3 HSV rotating (§6.1, §8.2.1.2)
- [`visibility_spine.md`](features/visibility_spine.md) — IntersectionObserver spine (§6.4, §8.3)
- [`click_and_stick.md`](features/click_and_stick.md) — Freeze-at-hover-rect (§4.2)

**Panel / editor features:**
- [`click_to_edit.md`](features/click_to_edit.md) — Hidden-overlay buttons + Shift-Enter (§4.1.1)
- [`plus_sign_field_tree.md`](features/plus_sign_field_tree.md) — Right + bottom progressive build (§4.6)
- [`signal_stream.md`](features/signal_stream.md) — One signal at a time (§4.6.1)
- [`play_pause_rollout.md`](features/play_pause_rollout.md) — Edit between iterations (§7.5)
- [`autocomplete.md`](features/autocomplete.md) — Linked-structure ranking (§4.7)

**Scanner features:**
- [`pattern_map.md`](features/pattern_map.md) — Live-streaming output (§15.8.2)
- [`url_set_panel.md`](features/url_set_panel.md) — `{urls_panel}` aggregator (§15.7)
- [`golden_trio.md`](features/golden_trio.md) — Content-precise extraction (§15.8.1)
- [`type_inheritance.md`](features/type_inheritance.md) — Passthrough composition (§15.9)

**Observability + verification features:**
- [`repl_two_way_feedback.md`](features/repl_two_way_feedback.md) — Symbolic register operationalised (§14)
- [`in_place_activity_viewer.md`](features/in_place_activity_viewer.md) — Six-row dashboard (§14.5, §11.8)
- [`live_scan_cleanup.md`](features/live_scan_cleanup.md) — Mandatory real-site probe (§16.5)
- [`evolution_log_rollback.md`](features/evolution_log_rollback.md) — Diff trail + rollback scopes (§11.4)

---

## §4 — The Code Constraints (`code_constraints/`)

[`code_constraints/README.md`](code_constraints/README.md) is the code-constraint index. Each constraint doc carries:

- **Surface** — which programming surface (services, REST, WS, frontend, REPL).
- **Must-hold** — conditions the code must guarantee.
- **Must-not** — anti-patterns forbidden by the design.
- **Test signal** — the env-scenario or probe that verifies the condition.
- **Code anchor** — file(s) that implement the surface.
- **Anti-goal anchor** — the §18 anti-goal the constraint guards against.

### §4.1 Constraint Catalogue

- [`backend_services.md`](code_constraints/backend_services.md) — service-level singleton, threading, fake-gate rules
- [`api_routes.md`](code_constraints/api_routes.md) — REST contract, idempotency keys, error envelopes
- [`ws_frames.md`](code_constraints/ws_frames.md) — frame schema, sequencing, dual-routing
- [`lifecycle_invariants.md`](code_constraints/lifecycle_invariants.md) — the one-and-only-one dispatcher rule
- [`frontend_rendering.md`](code_constraints/frontend_rendering.md) — what the frontend must render and must not
- [`repl_actions.md`](code_constraints/repl_actions.md) — gesture catalogue contract (§14.2)
- [`env_scenarios.md`](code_constraints/env_scenarios.md) — what env-scenarios assert and what acceptance bar each carries
- [`streaming.md`](code_constraints/streaming.md) — workspace-WS routing, backpressure, replay buffer
- [`persistence.md`](code_constraints/persistence.md) — Kuzu / LayoutFrame / file-on-disk storage rules
- [`concurrency.md`](code_constraints/concurrency.md) — actor-aware short-circuit, optimistic concurrency, last-write-wins
- [`error_handling.md`](code_constraints/error_handling.md) — 503-or-loud, no quiet degradation
- [`testing.md`](code_constraints/testing.md) — full-smoke contract, real-stack mode, stub mode
- [`ci_acceptance.md`](code_constraints/ci_acceptance.md) — `all_real: true` gate, env-scenario passing requirement

---

## §5 — Cross-Reference Mechanics

### §5.1 How To Find What You Need

| Question | First read | Then read |
|---|---|---|
| *What is the workspace philosophically?* | DOMAIN_MODEL §1.1, §1.5 | features/three_register_model.md |
| *What does object O look like in storage?* | object_model/`<O>`.md | DOMAIN_MODEL §3 if it's a ConceptNode |
| *What does feature F look like to the user?* | features/`<F>`.md | DOMAIN_MODEL §17 sequence for full state machine |
| *What does the codebase have to do to realise feature F?* | code_constraints/`<surface>`.md | features/`<F>`.md for the contract being realised |
| *What is the test for feature F?* | features/`<F>`.md → acceptance section | code_constraints/env_scenarios.md for the matching env-scenario |
| *What can the codebase never do?* | DOMAIN_MODEL §18 anti-goals | code_constraints/`<surface>`.md must-not section |
| *Where in the codebase does feature F live?* | DOMAIN_MODEL §20.3 code-file index | features/`<F>`.md → cross-objects section |

### §5.2 How To Add A New Feature

1. Capture the requirement in [`USER_REQUIREMENTS_VERBATIM.md`](USER_REQUIREMENTS_VERBATIM.md).
2. Audit current code and record the gap (the legacy [`CODEBASE_GAP_ANALYSIS.md`](CODEBASE_GAP_ANALYSIS.md) is historical, §O.17 — supersede it with a fresh audit).
3. Update [`DOMAIN_MODEL.md`](DOMAIN_MODEL.md) — add to the relevant existing section, or open a new §X.Y if the feature is structurally new.
4. Add or update the relevant `object_model/<Object>.md` if a new object is needed.
5. Create `features/<new_feature>.md` describing the user-visible behaviour, state machine, gestures, acceptance bar.
6. Update `code_constraints/<surface>.md` for each programming surface the feature touches (lifecycle, WS, REPL, etc.).
7. Add the REPL action and env-scenario per `code_constraints/repl_actions.md` + `code_constraints/env_scenarios.md`.
8. Add the §18 anti-goal in DOMAIN_MODEL for the regression the feature is most at risk of.
9. Update [`DOC_MAP.md`](DOC_MAP.md) (this file) §2 / §3 / §4 catalogues with the new doc(s).

### §5.3 Doc Numbering Conventions

- DOMAIN_MODEL uses `§X.Y.Z` section numbers that are stable identifiers (the backend code has ~280 references to specific §-numbers; renumbering breaks links).
- Object docs, feature docs, and constraint docs use **filename-based identifiers** (no internal numbering required) — the filename is the identifier.
- Cross-references between layers use the canonical form `[Object/Feature/Constraint] → [target file]#[optional anchor]`.
- Cross-references to DOMAIN_MODEL use the `§X.Y` form, with `DOMAIN_MODEL.md §X.Y` spelled out when leaving the doc.

### §5.4 What Stays In DOMAIN_MODEL vs Subsidiary Docs

| Content | Lives In | Reason |
|---|---|---|
| User's verbatim phrasing | DOMAIN_MODEL | Source-of-truth; downstream docs *quote* but do not duplicate |
| Philosophical framing (registers, alchemy, telos) | DOMAIN_MODEL | Source of the meta-level reasoning |
| Cross-feature reasoning (the dialectic between compile and collapse, the alchemy between Real and Imaginary) | DOMAIN_MODEL | Where multiple features synthesise |
| Object data shape (fields, types, defaults) | object_model/ | Where one object's identity is precise |
| Object lifecycle (mutations, hooks, peer notification) | object_model/ | Where one object's behaviour is precise |
| Feature UX contract (what the user sees / does) | features/ | Where one feature's user-visible behaviour is precise |
| Feature state machine (gesture-to-effect) | features/ | Where one feature's flow is precise |
| Code constraints (concurrency, persistence, error handling, testing) | code_constraints/ | Where one programming surface's rules are precise |
| Anti-patterns and forbidden code paths | DOMAIN_MODEL §18 + code_constraints/`<surface>`.md must-not | Anti-goals listed once in DOMAIN_MODEL, reiterated per surface for proximity |

---

## §6 — Status Markers

Each doc in the subsidiary directories carries one of these markers at the top:

| Marker | Meaning |
|---|---|
| **Status: realised** | Doc is complete; downstream code matches |
| **Status: specified** | Doc is complete; downstream code is partial or planned |
| **Status: planned** | Doc captures intent; downstream code does not exist |
| **Status: deprecated** | Doc is preserved for historical reference; do not implement against it |

The marker tells the implementer at a glance whether the doc is reliably representative of running code or merely of design intent.

---

## §7 — The Stable Identifiers (DOMAIN_MODEL §-numbers)

For sanity when navigating between the layers, here is the set of DOMAIN_MODEL §-numbers most often referenced from the subsidiary docs:

| Anchor | Object/Feature/Constraint | Subsidiary docs |
|---|---|---|
| §1.1 / §1.5 | Three registers | features/three_register_model.md |
| §3.1 | ConceptNode shape | object_model/ConceptNode.md |
| §3.2.1 | Hard vs soft links | features/hard_soft_links.md, object_model/ConceptEdge.md |
| §4.1.1 | Click-to-edit | features/click_to_edit.md, object_model/KnowledgePanel.md |
| §4.6 / §4.6.1 / §4.6.2 | Plus-signs + signal-stream | features/plus_sign_field_tree.md, features/signal_stream.md |
| §6.1 / §8.2.1.2 | 6D UMAP | features/6d_umap.md, object_model/LayoutService.md |
| §6.6.1 / §6.6.2 | Perimeter outputs + separation | features/perimeter_outputs.md, features/2d_3d_separation.md |
| §7.3 | Compile/collapse dialectic | features/compile_collapse_dialectic.md |
| §8.1.1 | Multi-freq PageRank | features/multi_frequency_pagerank.md, object_model/ApparitionService.md |
| §8.2.1 / §8.2.1.1 / §8.2.1.2 | Halo | features/halo_retrieval.md, object_model/Halo.md |
| §9.5 / §9.5.1 | Four fixtures | features/four_fixture_api.md, object_model/Agent.md / WebBrowser.md / Database.md / Editor.md |
| §9.7 | Library middleware | features/library_imports_middleware.md, object_model/PythonAPIMaterialiser.md |
| §10.2 | Lifecycle dispatcher | code_constraints/lifecycle_invariants.md, object_model/ConceptLifecycle.md |
| §10.5 | UI state mirror | object_model/UIStateService.md |
| §11.4 | Evolution log | object_model/EvolutionLog.md, features/evolution_log_rollback.md |
| §12 / §12.2.1 / §12.6.1 | Agent + integration scheme + entanglement | features/agent_integration_scheme.md, object_model/AgentRuntime.md |
| §14 / §14.2 / §14.5 | REPL | code_constraints/repl_actions.md, features/repl_two_way_feedback.md, features/in_place_activity_viewer.md |
| §15.7 / §15.8 | URL-set + pattern_map | features/url_set_panel.md, features/pattern_map.md, object_model/URLSetPanel.md, object_model/PatternMap.md |
| §16.5 | Live-scan probe | features/live_scan_cleanup.md, code_constraints/env_scenarios.md |
| §17 | Functional sequences | features/`<each>` carries its own sequence; DOMAIN_MODEL §17 holds the canonical reference |
| §18 | Anti-goals | code_constraints/`<each>` carries its surface's must-not list; DOMAIN_MODEL §18 holds the canonical reference |

---

## §8 — How To Read This Map

1. **First-time reader** — start at `DOMAIN_MODEL.md` and skim §1 through §5; then `features/README.md` to see the user-visible feature surface; then `object_model/README.md` to see the workspace's object structure; then `code_constraints/README.md` to see the programming conditions.

2. **Implementation-focused reader** — start at the [`frontend/`](frontend/) suite + `code_constraints/<surface>.md` for the must-hold conditions (`CODEBASE_GAP_ANALYSIS.md` is historical, §O.17 — not an implementation target); read the relevant `features/<F>.md` for what the user expects; read the relevant `object_model/<O>.md` for the object's shape and lifecycle. Update DOMAIN_MODEL last (the source of truth) only when the implementation reveals a design refinement.

3. **Design-focused reader** — start at `DOMAIN_MODEL.md` §1.1, §1.2; then `features/three_register_model.md` and `features/four_fixture_api.md`; then walk feature-by-feature through `features/` to see how each user-visible behaviour decomposes; then dip into `object_model/` for the objects each feature touches.

4. **Verification-focused reader** — start at `code_constraints/env_scenarios.md` for the full env-scenario catalogue; then `code_constraints/testing.md` for the full-smoke contract; then `features/live_scan_cleanup.md` and `features/in_place_activity_viewer.md` for the live verification surfaces.

The chain runs in both directions: from design ideation downward to code constraint, and from a code change upward to verify against the design ideation. This map exists so either direction is navigable.
