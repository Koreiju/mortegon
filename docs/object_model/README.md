# Object Model

> **Layer purpose.** This directory carries one document per first-class object in the workspace's design. Each object document elaborates [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) into the *object-level realisation* — the data shape, the lifecycle, the invariants, the peer interactions, and the persistence rules — without yet committing to a specific programming surface (REST routes, frontend rendering, code file). The next layer down, [`code_constraints/`](../code_constraints/), then articulates the programming-side conditions that realise these objects in code.
>
> See [`DOC_MAP.md`](../DOC_MAP.md) §2 for the place of this layer in the documentation chain.

---

## §0 — Reading Order

Each object doc is self-contained but composes through cross-references. The recommended reading order is:

1. **Data records** — the shape primitives the workspace stores and manipulates.
2. **Foundational fixtures** — the four primary functional objects every workflow touches.
3. **Backend services** — the singletons that orchestrate the data records and fixtures.
4. **Frontend components** — the surfaces the user interacts with.

Read by category, not alphabetically; objects within a category compose with each other before composing across categories.

---

> **Catalogue status (2026-05-30 cleanup).** This catalogue is partly aspirational. **Files that exist today:** `ConceptNode`, `ConceptEdge`, `ChunkPatternSchema` (data records); `Agent`, `WebBrowser`, `Database`, `Editor` (fixtures); `ConceptLifecycle`, `LayoutService`, `ApparitionService`, `UIStateService`, `PythonAPIMaterialiser`, `RolloutCoordinator` (services); `Halo` (frontend). **Every other row below is planned (no file yet)** — e.g. `EditDiff`, `LayoutFrame`, `UIState`, `ConceptIndexService`, `ConceptualCompute`, `AgentRuntime`, `EvolutionLog`, `FoundationFixtures`, `GlobalTfidfStore`, `BackingRegistry`, `ChunkBuilder`, `SeleniumClient`, `SLMClient`, `EmbeddingService`, `CompiledFromScans`. The **frontend-component** rows (`KnowledgePanel`, `FieldTree`, `Billboard`, `Projector`, `PatternMap`, `URLSetPanel`) are **superseded by the [`docs/frontend/`](../frontend/) suite** (`concept_view`, `field_tree`, `billboard`, `projector`, `pattern_map_and_url_set`) — use the suite, not those links. Treat unbuilt rows as design intent, not navigable docs.

## §1 — Data Records

The four core data records and the supplementary persistence shapes.

| Doc | Domain anchor | What it captures |
|---|---|---|
| [`ConceptNode.md`](ConceptNode.md) | §3.1 | The universal record every workspace surface (panel, halo phantom, compiled child, agent body card, materialised python_object) is an instance of |
| [`ConceptEdge.md`](ConceptEdge.md) | §3.2, §3.2.1 | Hard links (committed `ConceptEdge` rows in Kuzu) and soft links (in-memory apparition cache); the commitment fan and possibility ring layout split |
| [`EditDiff.md`](EditDiff.md) | §11.4 | Append-only evolution-log record; carries before/after snapshots and actor identity for rollback |
| [`LayoutFrame.md`](LayoutFrame.md) | §6.1, §11.1 | Per-workspace storage of canonical 6D UMAP coords (3 position + 3 HSV) and per-URL roots |
| [`ChunkPatternSchema.md`](ChunkPatternSchema.md) | §15.8 | The `pattern_map` entry — pattern hash, url root, golden trio, sampled chunks, PageRank, sub-patterns |
| [`UIState.md`](UIState.md) | §10.5 | The frontend mirror: selected/hovered/pinned/halo_focus/halo_chain/editing_field/latch_state/pin_chrome/autocomplete_state/viewport_visible_rows/compile_expansions |

---

## §2 — Foundational Fixtures (§9.5)

The four primary functional objects the user and the agent compose with. Each is materialised as a `python_object` ConceptNode with `python_function` children carrying port schemas (§9.8).

| Doc | Domain anchor | Primary surface |
|---|---|---|
| [`Agent.md`](Agent.md) | §9.5.1 Agent | `Agent.meta_prompt(text)` / `Agent.prompt(text)` / `Agent.output(schema?)` SLM primitives; live token stream |
| [`WebBrowser.md`](WebBrowser.md) | §9.5.1 WebBrowser | `WebBrowser.scan(url, query?)` producing live chunk stream + `pattern_map` output |
| [`Database.md`](Database.md) | §9.5.1 Database | `search(query, cypher?)` + `cypher(query)` + `concept(node_id [or list])` rank-1 KG walks under signal-stream |
| [`Editor.md`](Editor.md) | §9.5.1 Editor | `create` / `link` / `overwrite` / `delete` graph-mutation primitives that the agent's emitter also calls into |

---

## §3 — Backend Services (`backend/services/`)

The process-wide singletons that orchestrate every mutation, retrieval, and broadcast.

| Doc | Domain anchor | Owner role |
|---|---|---|
| [`ConceptLifecycle.md`](ConceptLifecycle.md) | §10.2, §2.2 | The single mutation dispatcher; every actor (user, agent, REPL, materialiser, scanner) enters through it |
| [`LayoutService.md`](LayoutService.md) | §10.3, §6.1, §6.6.1 | 6D UMAP joint fit, per-URL bounding-radius placement, perimeter-encompassing agent-output rescaling, `umap_canonical` broadcast |
| [`ConceptIndexService.md`](ConceptIndexService.md) | §10.4, §8.1, §8.1.1 | Per-concept nomic + TF-IDF + multi-frequency band update, PageRank refit, `concept_index_update` broadcast |
| [`ApparitionService.md`](ApparitionService.md) | §8.1, §8.1.1, §8.2, §7.7 | Halo retrieval (multi-frequency aggregation), closest-inverse, ray-projection coords, soft-link candidate generation |
| [`ConceptualCompute.md`](ConceptualCompute.md) | §10.6, §7.1, §7.2, §11.7 | `ConceptComputeNode` LangGraph primitive; `compile_subgraph_to_langgraph` chain builder |
| [`PythonAPIMaterialiser.md`](PythonAPIMaterialiser.md) | §9.6, §9.7 | Inspect-walks Python modules and produces Object/Property/Function ConceptNode trees; library-imports middleware |
| [`AgentRuntime.md`](AgentRuntime.md) | §12, §12.2, §12.2.1 | `MetaCognitionTick.run_async`; ActionResolver dispatching emitter actions through the lifecycle |
| [`EvolutionLog.md`](EvolutionLog.md) | §11.4 | Append-only EditDiff table; rollback (single / range / actor) |
| [`UIStateService.md`](UIStateService.md) | §10.5, §14 | The frontend UI mirror; setters for every mirror field; `ui_state_changed` broadcast |
| [`FoundationFixtures.md`](FoundationFixtures.md) | §9.5 | `ensure_foundation_fixtures(workspace_id)` materialises the four fixtures plus their member trees |
| [`GlobalTfidfStore.md`](GlobalTfidfStore.md) | §10.3, §15, §15.7, §8.1.1 | Incremental TF-IDF index with url-specific tokenisation and multi-frequency bands |
| [`RolloutCoordinator.md`](RolloutCoordinator.md) | §7.5, §17.1.2 | Play/pause iteration; signal-stream advance; `rollout_paused` / `rollout_resumed` frames |
| [`BackingRegistry.md`](BackingRegistry.md) | §3.3 | Opaque pointer → live Python resolution; version-bumped invalidation |
| [`ChunkBuilder.md`](ChunkBuilder.md) | §15.4, §15.8.1 | Per-chunk extraction, generalised xpath, golden-trio detection |
| [`SeleniumClient.md`](SeleniumClient.md) | §15.1, §9.5.1 WebBrowser | `WebBrowserManager` singleton; eager init on lifespan |
| [`SLMClient.md`](SLMClient.md) | §13.5, §9.5.1 Agent | GPT4All `Nous-Hermes-2-Mistral-7B-DPO` wrapper; CUDA; Llama rejected |
| [`EmbeddingService.md`](EmbeddingService.md) | §10.4, §8.1 | GPT4All `Embed4All` `nomic-embed-text-v1.5.f16.gguf` wrapper |
| [`CompiledFromScans.md`](CompiledFromScans.md) | §15.5, §15.8 | `SearchableURL` / `DetectedAccessor` / `XPathPattern` / `PinnedComponent` materialisation |

---

## §4 — Frontend Components (`backend/static/js/cp/`)

The user-facing surfaces. Each composes through the WebSocket-broadcasted state mirrors and the REST gesture endpoints documented in [`code_constraints/api_routes.md`](../code_constraints/api_routes.md).

> **Reconciliation note (2026-05-30).** The per-component frontend specs now live in the [`docs/frontend/`](../frontend/) suite (`concept_view.md`, `field_tree.md`, `halo.md`, `billboard.md`, `projector.md`, `pattern_map_and_url_set.md`, `object_exploration.md`) + [`FRONTEND_REDESIGN.md`](../FRONTEND_REDESIGN.md). Of the rows below, only `Halo.md` exists as a file (reconciled to §O); `KnowledgePanel` / `FieldTree` / `Billboard` / `Projector` / `PatternMap` / `URLSetPanel` were never created and are **superseded by the suite** — treat the suite docs as canonical and disregard the dangling links.

| Doc | Domain anchor | Owner role |
|---|---|---|
| [`KnowledgePanel.md`](KnowledgePanel.md) | §4, §4.1, §4.2 | The single panel template every surface renders (hover billboard, pinned panel, halo phantom collapsed form, compiled-graph child) |
| [`FieldTree.md`](FieldTree.md) | §4.6, §4.6.1, §4.6.2 | Recursive editable tree with plus-signs (right + bottom) and signal-stream display |
| [`Halo.md`](Halo.md) | §8.2.1, §8.2.1.1, §8.2.1.2 | Concentric-circle halo renderer; ray-projection to conic surface; HSV-rotation phase loop on phantoms |
| [`URLSetPanel.md`](URLSetPanel.md) | §15.7 | User-created URL aggregator with `{urls_panel}` reference and url-specific TF-IDF tokenisation |
| [`PatternMap.md`](PatternMap.md) | §15.8.2 | Live-streaming output panel for chunk-pattern schemas; signal-stream over `pattern_hash` keys |
| [`Billboard.md`](Billboard.md) | §4.2, §6.1, §8.2.1.2 | Hover billboard with hidden-overlay click targets; 3D-resident image billboards or HSV-rotating fill |
| [`Projector.md`](Projector.md) | §6, §6.2, §8.2.1.2 | Three.js scene; per-frame HSV-rotation phase loop matched to camera azimuth |

---

## §5 — Cross-Composition Map

The objects compose along these axes. Each row names one composition relationship; see the cited object docs for the precise interaction.

| Composes | With | Through | See |
|---|---|---|---|
| ConceptLifecycle | ConceptNode, ConceptEdge | Every mutation enters via `apply_update_lifecycle` / `apply_delete_lifecycle` | [`ConceptLifecycle.md`](ConceptLifecycle.md) §lifecycle |
| LayoutService | ConceptLifecycle | The dispatcher calls `schedule_output_projection` (debounced) on every mutation; `output_projection` then selects peripheral nodes and maps `agent-authored → agent-output` projector provenance for perimeter rescale (§6.6.1) | [`LayoutService.md`](LayoutService.md) §refit-triggers |
| LayoutService | GlobalTfidfStore | UMAP fits over the full TF-IDF index across multi-frequency bands | [`GlobalTfidfStore.md`](GlobalTfidfStore.md) §umap-input |
| LayoutService | LayoutFrame | LayoutService writes; frame is persisted per workspace | [`LayoutFrame.md`](LayoutFrame.md) §write-paths |
| ConceptIndexService | ConceptLifecycle | Re-embedding fires on description/rendering change | [`ConceptIndexService.md`](ConceptIndexService.md) §reembed |
| ApparitionService | ConceptIndexService | Reads slots for nomic + PageRank + multi-frequency ranks | [`ApparitionService.md`](ApparitionService.md) §rank-sources |
| ApparitionService | LayoutService | Reads LayoutFrame for ray-projection of manifold neighbours | [`ApparitionService.md`](ApparitionService.md) §ray-projection |
| AgentRuntime | Editor | Agent emitter calls Editor primitives through ActionResolver | [`AgentRuntime.md`](AgentRuntime.md) §emitter, [`Editor.md`](Editor.md) §emit-actions |
| AgentRuntime | ApparitionService | Perception card reads halo surface around parameter focal | [`AgentRuntime.md`](AgentRuntime.md) §perceive |
| AgentRuntime | SLMClient | Transformer card fires GPT4All; streams `agent_token` frames | [`AgentRuntime.md`](AgentRuntime.md) §transform |
| WebBrowser | ChunkBuilder | `scan` invokes per-chunk extraction + golden-trio detection | [`WebBrowser.md`](WebBrowser.md) §scan, [`ChunkBuilder.md`](ChunkBuilder.md) §extract |
| WebBrowser | ConceptLifecycle | Each chunk lands as a ConceptNode through the lifecycle | [`WebBrowser.md`](WebBrowser.md) §emit, [`ConceptLifecycle.md`](ConceptLifecycle.md) §scanner |
| WebBrowser | LayoutService | Each chunk triggers preliminary radial placement → joint UMAP refit at scan-end | [`LayoutService.md`](LayoutService.md) §scan-end-refit |
| WebBrowser | ChunkPatternSchema | `pattern_map` materialises and updates live as patterns emerge | [`ChunkPatternSchema.md`](ChunkPatternSchema.md) §live-build |
| Database | GlobalTfidfStore | `search` queries the multi-frequency-band store | [`Database.md`](Database.md) §search |
| Database | ConceptIndexService | `concept` walks the rank-1 KG using the concept-graph edge table | [`Database.md`](Database.md) §concept |
| PythonAPIMaterialiser | ConceptNode | Each materialised python_object/property/function is a ConceptNode | [`PythonAPIMaterialiser.md`](PythonAPIMaterialiser.md) §emit |
| PythonAPIMaterialiser | FoundationFixtures | Materialises the four fixtures on workspace boot | [`FoundationFixtures.md`](FoundationFixtures.md) §ensure |
| EvolutionLog | ConceptLifecycle | Every mutation appends an EditDiff | [`ConceptLifecycle.md`](ConceptLifecycle.md) §evolution-emit |
| UIStateService | ConceptLifecycle | Receives broadcast hooks; surfaces UI mirror updates | [`UIStateService.md`](UIStateService.md) §broadcast |
| RolloutCoordinator | UIStateService | Signal-stream advance updates the `signal_stream` mirror field | [`RolloutCoordinator.md`](RolloutCoordinator.md) §advance |
| RolloutCoordinator | ConceptualCompute | Per-sample compile re-fire on signal advance | [`RolloutCoordinator.md`](RolloutCoordinator.md) §compile-loop |
| ChunkBuilder | ChunkPatternSchema | Detected patterns feed schema build; sampled chunks accumulate per pattern | [`ChunkBuilder.md`](ChunkBuilder.md) §pattern, [`ChunkPatternSchema.md`](ChunkPatternSchema.md) §sampled-chunks |
| KnowledgePanel (frontend) | UIStateService | Receives `ui_state_changed` frames; renders the unified panel anatomy | [`KnowledgePanel.md`](KnowledgePanel.md) §mirror |
| FieldTree (frontend) | KnowledgePanel | Rendered inside panel data slot under signal-stream constraint | [`FieldTree.md`](FieldTree.md) §inside-panel |
| Halo (frontend) | ApparitionService | Fetches candidates via REST; renders concentric ring + ray-projection | [`Halo.md`](Halo.md) §rendering |
| Halo (frontend) | LayoutService | Reads LayoutFrame for projector chunks' world positions; HSV state for collapsed-singular phantoms | [`Halo.md`](Halo.md) §projector-link |
| Projector (frontend) | LayoutFrame | Reads canonical positions and HSV state; per-frame phase rotation | [`Projector.md`](Projector.md) §animate |

---

## §6 — Status Markers

Each object doc carries a status marker at the top:

- **realised** — doc complete, code matches the doc
- **specified** — doc complete, code is partial or planned
- **planned** — doc captures intent, code does not exist

The marker tells the reader at a glance whether the doc is reliable as a description of running code or only as a description of design intent.

---

## §7 — How To Extend This Layer

When the domain model adds or refines an object:

1. Add or update the relevant `<Object>.md` in this directory.
2. Update [`DOC_MAP.md`](../DOC_MAP.md) §2 catalogue with the new doc.
3. Update [`README.md`](README.md) (this file) §1 / §2 / §3 / §4 with the new doc.
4. Update the §5 cross-composition map if the new object composes with existing ones.
5. Cross-link the relevant `features/<F>.md` and `code_constraints/<surface>.md` to the new object doc.
6. Where a new object replaces an old one, mark the old doc **deprecated** rather than deleting it (keep the file with a redirect note).
