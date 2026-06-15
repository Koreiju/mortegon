# Web Fiber Haptics: Domain Model

> **Doc precedence.** This file is the *design elaboration*. The **source-of-truth requirements** live verbatim in [`USER_REQUIREMENTS_VERBATIM.md`](USER_REQUIREMENTS_VERBATIM.md); the **gap-to-code audit** ([`CODEBASE_GAP_ANALYSIS.md`](CODEBASE_GAP_ANALYSIS.md)) and the **3D↔2D operational scheme** ([`MORTEGON_INTEGRATION_SCHEME.md`](MORTEGON_INTEGRATION_SCHEME.md)) are **historical analysis-plan, superseded** (§O.17) — their additive design content is lifted into this file + the [`frontend/`](frontend/) suite; consult them for historical reasoning only. When this file disagrees with the verbatim file, the verbatim file wins.
>
> **Forbidden concepts (hard deletions).** The following ideas are *removed* from the design and must not appear as current-architecture descriptors:
> 1. Concentric Fibonacci-sphere layouts (3D *or* 2D) as the **primary placement authority** — the layout is the **UMAP-linear-radial force-directed hybrid** (§9). **Distinct from the allowed concentric-circle halo radiation** of §8.2 (apparition retrieval visualization around a focal panel, polar-coordinate proximity preserving scale-space periphery). The halo is a *retrieval-score visualization*, not a layout authority; the forbidden item is *layout-as-concentric-shells*, not *radiation-as-concentric-arcs*.
> 2. Graph-analytics retrieval (depth, subtree_size, branching_factor, cluster_id, pattern_frequency, content_density, wl_hash) — retrieval ranks by `pagerank · tfidf_cos · nomic_cos` (§8D.43).
> 3. Llama as an SLM target — production runs Nous Hermes 2 DPO on CUDA (§8D.46).
> 4. Two-panel hover/click split — one panel anatomy, one code path (§8D.1).
> 5. Stray dotted UI lines and dotted 2D↔3D connectors — solid only (§7.3). The hard/soft link distinction (§3.2, §8.2) is expressed through **stroke brightness and stroke weight** — both kinds are solid, **undirected** lines with **no arrowheads** (§O.16).
> 6. **(§S.1) The `Editor` fourth foundational fixture** — there are **three** fixtures (Agent, WebBrowser, Database; §9.5). The create/link/overwrite/delete gestures are intrinsic to the unified panel↔compute-graph scheme (§4/§7), not a Function-typed `Editor` object.
> 7. **(§S.3) The retrieval sidebar** — the standalone NL-search side panel is removed; in-editor halo queries with ray projections (§8.2 / §4.1.2) subsume it. The retrieval backend (§8.1) stays.
> 8. **(§S.4) Panel/node chrome** — coloured headers, hash-hue title bars, `×` / minimise buttons, any top bar. Every panel and computation node is the **black slate** (§4.1.2): thin silver border, black infill, serif white text, no chrome.
>
> **Scope.** Architectural, design, modelling, interaction, activity, functional, and objective requirements. No implementation diary. No evidence logs (the live probes carry those — see §14). Every section cross-references peer sections so the design composes; absent cross-references mean the relation is not load-bearing.

---

## §0 — All-Real Tests For Everything (§Q.1, §8D.46)

> **THE LOAD-BEARING TESTING MANDATE. Every test, every probe, every scenario exercises the real stack: the real SLM (Nous-Hermes-2-Mistral-7B-DPO on CUDA), the real embedder (nomic-embed-text-v1.5 on CUDA), the real WebBrowser (live Selenium / geckodriver), and real LangGraph (`langgraph.graph.StateGraph`). There is no feature that is "verified" by a stub. A green stub run is necessary but never sufficient — every commit must also be green against the four real subsystems with `GET /api/subsystem_status` reporting `all_real: true`.**

This is the strongest commitment in the design and it governs every other section. It is stated here at §0 — above the vision itself — because *correctness is observed against reality, not against a mock of reality* (§2.9, §14.1). The fake gates (`WFH_FAKE_SLM`, `WFH_FAKE_EMBEDDER`, `NO_WEBDRIVER`) exist **only** so the test harness can run on a machine without a GPU or network; they are **never** set on a production path, and a feature is **not done** until it has run end-to-end with all gates off.

**The acceptance rule (§Q.1).** For *every* user-visible capability the design names, there must exist:

1. An **all-real probe or env-scenario** that drives the capability through the live full stack (real models + real WebBrowser + real LangGraph), asserting `all_real: true` before it runs.
2. A **REPL-observable** trace of that run (§14) — the capability shows up in the in-place activity viewer (§14.5) and round-trips through the gesture catalogue (§14.2).
3. A **stub-mode** counterpart (`WFH_FAKE_*=1`) that stays green, proving the harness path is faithful to the real path.

The all-real probes already realising this are listed in §16 + CLAUDE.md (`probe_no_mocks.py`, `probe_live_archive_scan.py`, `probe_live_concept_graph.py`, `probe_live_agent.py`, `probe_live_iterated_compile.py`); the standing requirement of §0 is that **this set is exhaustive over the feature surface** — a new capability ships with its all-real probe, or it does not ship (§14.4 acceptance bar). The `env-scenario --name full-smoke` set runs in **both** modes on every commit (§14.4, §16.6). The down-flow of this mandate is concrete: §13 (the No-Mocks Contract) is its architectural statement, `code_specs/repl.md` + `code_specs/backend/scanner.md` carry the spec-level assertions, and `scripts/probe_no_mocks.py` + the `all_real`-gated scenarios are its code realisation. The contract is **loud** (§2.8): a missing GGUF, a dead driver, an absent LangGraph surface as a 503 + halted cascade, never a silent stub substitution.

---

## §1 — Vision and Identity

### §1.1 What Web Fiber Haptics Is

Web Fiber Haptics is a **single-user, on-device workspace** that joins three surfaces into one workflow:

- **3D Projector** — a spatial UMAP-fitted manifold of every chunk the workspace has ever scanned or computed (§9). The user (and the agent) read it as a *comparison surface* (§9.14): adjacency, distribution shape, nearest-neighbour relationships are directly visible as geometry.
- **2D Concept Editor** — a tangible computation-graph editor where every ConceptNode (§3) is a card with one unified anatomy (§4). The user composes by typing into rows, wiring `{var}` references, double-left-clicking to compile/collapse and right-clicking to fold the inline type graph (§7, §7.3.4), and watching the cascade re-fire as outputs propagate.
- **REPL** — a terminal harness (`scripts/sim_frontend.py`) that drives every gesture the GUI exposes through the same REST + WebSocket surface and reads back the same telemetry (§14). The REPL is the verification instrument; the in-place activity viewer (§11.8) is its dashboard.

The three surfaces are the shape of death (Mortegon) because of the bidirectional feedback flow between all three dimensions of alchemical being: 
1. **3D Projector - The Real**: Everything within the 3D projector, input or output, is interpreted and geometrically physically depicted as real sensory or perceptual measurements. This includes the live-updated scans of all shadow DOM pages that are in the workspace, as well as the perimeter-encompassing final outputs of the computation graph (the agent). This symbolizes the projection from the real to the imaginary space of the agent state or a physical perception of the agent from the 'real world'. The agent is then auto-corrected over the space of world perceptions as initial conditions to a recursion-over-iteration integration scheme of purely conceptual computational topologies with hard-typed functional-object python endpoints and the initial data structures as base perceptions to transform and produce the final set of computations with through the graph. This includes, in more developed programs created by the user, an agent computation graph with meta-cognitive capabilities that interact with the graph editor as its own object itself. So, the 2D concept editor itself is one of the fundamental building-block api functional objects that the specially designed agent computation graph interacts with and entangles itself with. The ultimate role of the agent computation graph, which is seamlessly integrated in structure and layout with its auto-complete-style suggestions over the conceptual computational space of each node, whether a functional-object node with Python bindings, or a concept node created by the user/scanned from shadow DOMs in the workspace. The outputs, after the computation graph recursively unrolls for every iteration over the provided input perception representational semantically linked structures, outputs something in exactly the same shapelessness and formlessness - carefully designed conceptual spaces as outputs that are then fed back into the real through the imaginary 2D space that is separate from the 3D space. 

2. **2D Concept Editor - The Imaginary**: The imaginary is best understood by examining the identifying etymology of the word; image. The computation graph editor space is an image of any and all perceptions, whether from what is seen of the 'real' that is reflected in pattern-structured web data, from what the user projects from their own ideas into the computational image of the same kind of conceptual thought flows, or even what the quantized SLM agent itself projects from its own imagination. Every single structure within the imaginary is fundamentally abstracted from the real as well, which motivates the transcendental imagery of real perception structures supporting entire flows of various projections of the perception through semantic space. The perceptions are semantic-graph-retrieval patterns from the very beginning because of the unified interface. The 3D world itself is retrieved by the imaginary in manifold form, which contracts to the abstract structures that characterize their base data structure primitives from scans, inputs, or generations. This is ultimately where the halo retrieval pattern comes into play. Here, when the user creates new concept nodes in either compiled data-structure-graph form (concept graph), a halo of retrieved data is shown as a radiating concentric circle away from the base retrieval node depending on normalized similarity to preserve scale-space boundaries at the periphery of the retrieval space and express the polar-coordinate proximality in this way. The result summaries are first shown around the perimeter of the queried 2D UI object in computation graph node (minimal/singular-linked) form. As the user clicks a node, a new node appears in the 2D editor to provide a continuous feedback that autoregresses over the retrieval space. Halos can also appear around computation graph nodes, which are simply singular-field knowledge panels with one key-value pair and references the rest of the way up the recursion-over-iteration tree by other variable(s). Right-clicking a more central node in the graph simply compiles the child/internally referenced links to other concept graph nodes into one editable knowledge panel. We should also note the imaginary property of forward-inverse-lookup roles that functional links to i/o types (can be semantically autocompleted depending on rendered value queries), where the functionality of the structure itself is purely projective through conceptual computation graphs. Every single representation is thus visually perceived as a distributional substance radiating from the focal points of inquiring semantic recursive object structures that preserve recursive tree-looking structures in their print rendering, but without any possible syntactical specificity and purely editable fields. Each pure-print rendered field in the knowledge panel representation that structures the computation graph representation is clicked to be edited, where clicking a pure-print token rendered in the knowledge panel immediately opens up its (possibly multiline and curly-brace containing) editable field, and pressing enter updates it back to its regular print within the print-rendered tree structure. This also presents a seamlessness and distributionality to the imaginary aspect of the agent's computation graph as the very realization of its structure. Hard and soft links are layed-out independently of each other, but share the same clear connection to the focal knowledge panels/computation graph nodes. Remember that right-clicking either one compiles the structure into the other representation. 

3. **REPL - The Symbolic**: Representations that are simple to understand yet comprehensive in their meaning and the transparency and visibility in every thing that happens both statically and dynamically within our app are invaluable and abstract. The capacity for the full conceptual structure of the app itself to be identified as something that is also represented to a similar philsophy as that which it is designed to be is a transcendental property of the permanence of its ultimate form. The notion that all interactions and operations and events within our app are not only fully recorded and accounted for in our console-render of the app, our REPL, purely realizes the computation graph of the app itself within its own symbolic space that agents and humans can interact with in the terminal and see the feedback of in both the real live full-stack app, as well as the simplified effects rendered to a statically-structured console with more like a dynamic screen update to it than a regular inifinite-scroll. Thus, other than its completeness, the symbolic realm hasn't got much to say on its own without external input and feedback. 

The shape of death is realized as a dialected of the telos of computation itself. To be a structural definite and static, or to be a completely free-flowing dynamism of infinite potentiality and transformation without limitation. The etymology of the Mortegon is just that, "Morte-" meaning "death", and "-gon" meaning "shape" (i.e. "polygon"). The existential dialectic of the generalizable intelligent computation is thus cleanly realized in its form of infinite self-negation and inversion. Not too different from what the Seal of Solomon was said to have symbolized. 

### §1.2 The User's Vision (Verbatim — Four Functional-Object Fixtures)

This section preserves the user's own phrasing as the design's seed — **the current authoritative formulation** (this prompt's update). The schema (§3), the unified panel (§4), the editor surfaces (§5), the foundation fixtures (§9.5), and the agent (§12) are all the realisation of this vision; the cross-references show where. **This text supersedes prior verbatim quotes of the vision** where the API surface differs.

> "1. **Agent**: slm with a meta-prompt, prompt, and output primitive functions
>
> 2. **WebBrowser**: for scanning, where scanning takes url input and maybe a search query and outputs a live-updated scan to the 3D gui of the shadow DOM
>
> 3. **Database**: for retrieval that takes a natural language or cypher query as input and gives an unstructured chunk result output; also has a 'concept' function that returns the rank-1 knowledge graphs of a given input node in the db, and can do this over iterative structures for multiple input nodes... note the 'signal-stream' constraint in our UI docs somewhere. This means that for iterables, only the signal node that's being iterated on is visible in the 2D ui panel, so knowledge panel structures can have multiple values that are iterated over for each rollout of the computation graph with recursive firing.
>
> 4. **Editor**: exposes all concept graph editor gestures like create, link, overwrite, and delete actions on input nodes, where nodes are represented as passing IDs of the nodes in the editor" (user, verbatim, this prompt's update — **SUPERSEDED by §S.1, 2026-06-12**: the Editor is no longer a fixture; these gestures are intrinsic to the unified panel scheme.)

The realisation: there are **three foundational fixtures** (§9.5) — Agent, WebBrowser, Database — each exposed as a Function-typed concept tree (§9.6) the user and the agent invoke identically. (§S removed the fourth, `Editor`: its mutation gestures are intrinsic to the panel scheme, not a fixture.) `EnvState` collapses into the projector (§9) as the rendering surface for the TF-IDF index; `AgentState` is a live computation subgraph (§12.1), authored by the user (§5) and by the agent itself through the **same concept-graph mutation lifecycle** the panel gestures use (§10.2 / §12.6.1) — not via a separate Editor object. The signal-stream constraint (§4.6.1) governs how iteration is displayed in panels.

> "Please make sure the standardized api formats are themselves generalized into a process of importing api objects from python libraries. What this middleware is meant to do is translate the recursive object and python package/module hierarchy from a simple module that stores library imports. We will keep it to our simple set of python-based four fundamental api objects that serve the core of our current data processing and interfacing functionality within our frontend-backend functional object design." (user, verbatim)

The realisation: the Python-API materialiser (§9.6) is generalised into a **library-imports middleware** (§9.7) — given a simple module that holds `import some_pkg` statements, the middleware walks the package's recursive object + module hierarchy and produces the Object/Property/Function ConceptNode tree (§9.6) with the same read-only no-datablock contract. The three canonical fixtures (Agent, WebBrowser, Database) are the first applications of this middleware; arbitrary imported libraries are subsequent applications under the same rule. (§S removed the former fourth fixture, `Editor`.)

> "All of the designs of each of these things must be meticulously interrogated for the secret relationships they, as pure objects, hold with each other within the fluid and seamless functional feedback between our right-clicking over compiles computation graph nodes vs compiled computation graph panels." (user, verbatim)

The realisation: §7.3's dialectical inversion between panel and compiled subgraph is the *visible* expression of these secret relationships; the three fixtures' pure-object identities are the structural skeleton beneath. A panel-gesture create (§S — the unified scheme's own mutation, not an `Editor` call) on a `WebBrowser.scan` output's chunks materialises new concept-graph nodes that themselves carry `{var}` references back to `Database.concept` rank-1 walks of those same chunks — the seamless feedback the user describes is the closure of: scan → chunks → concept-graph nodes → halo retrieval → panel/graph mutations → re-scan with refined `{urls_panel}` (§15.7).

> "Please pay attention to detail on the minimalism of our computational graph to knowledge panel sticking design from our 3D to our 2D. Also, live-scanning updates must be rigorously tested with proper database cleanup on real sites in our full-stack REPL test in the console." (user, verbatim)

The realisation: §4 + §7.3 + §8.2.1 specify the minimalist sticking (3D node → 2D panel with print-rendered, syntactically-stripped fields). §16.5 adds the **live-scan + DB cleanup REPL test on real sites** as a mandatory acceptance probe.

> "Then, pressing 'play/pause' can enable the user to edit the computation graph at various phases of the rollout when selecting different nodes within it to edit and either add or update data structures." (user, verbatim — §7.5)

> "Note that the 'inverse' on our concept cards automatically applies, because the compilation applies both forward function call and the inverse closest lookup." (user, verbatim — §7.7)

The closest-inverse lookup (§7.7) is therefore not a separate gesture — every Compile press applies forward execution AND inverse retrieval simultaneously when an input port is unbound. Bidirectionality is a link-level property of every typed edge (§3.2). In §1.5's Imaginary register framing, the closest-inverse is the *purely projective* property of the imaginary's functional links — the function's structure as projection through conceptual computation graphs.

### §1.2.1 Chunk-Pattern Ontology and URL-Set Panels (Verbatim)

> "Chunk pattern ontologies over sampled patterns should also be clearly linked to their queried urls to the web-browser's scan function. For example, querying the scan function with a url will produce a set of chunk patterns which themselves should be displayed as output, and linked as well to the database and the url to the chunk patterns (as the root of the chunk pattern schema). So we would build a url set within a user-created knowledge panel card (note url-specific tokenization within our tfidf vectorization but not quantized transformer retrieval) including a description of the evolving set of urls in the panel card that are referenced as external variables in their fields, which are automatically created as computational graph nodes for single-key:value minimalist field editing when the fields are clicked." (user, verbatim)

> "Of course, when clicked from pure-print to editable fields, additional buttons with '+' signs on the right and bottom of the singular key:value computation node are concatenated in the pure-print tree structure that can progressively build the compute node into a knowledge panel seamlessly, so perhaps our computational graph compilation via right-clicks simply re-aggregates externally referenced nodes into the minimalist pure-print tree-structured (tabs and newlines, no syntactical details other than pure key-values). Tabs and newlines in multiline fields are seamlessly integrated into the pure-print of the remainder of the tree data structure." (user, verbatim)

> "Since we do content detection in our scan, the url-type tag is exposed to the scan function. It could be that multiple urls are aggregated over a single panel that is referenced in the input variable in the functional object's 'scan' knowledge panel (likely called 'url') and you can reference {urls_panel} and all urls are passed through this field as an input type-appropriately. When this url-multiline/tree-based pure-print structured knowledge panel is referenced in the scan functional object compiled computational knowledge panel card, the url variable tags from our type detection and compilation (behind the scenes, where we can also track patterns for various api module types and their various data structures to detect our fundamental content patterns in their various regex and named tree pattern structures). There is type-inclusion via inheritance as well with referenced passthrough of our various panel/computational graph based data structures via their content patterns." (user, verbatim)

> "The scanner would then automatically fill in the blank chunk pattern fields, which then compile into the full and completely structured tree of each chunk patterns (golden-trio pattern rule for content-precise extraction alongside the generalized xpath patterns within the chunk pattern collections that provide our sampled chunk nodes in our scan GUI). This is where our iterative minimal value rendering to inherited typed functional inputs, our automatic function call link to our typed/named output panels that produces xpath chunk pattern schemas and their most recently computed set of new samples. This means that our live scan updates are reflected in live-updated umaps over the most recently updated and complete set of chunk vectors, as well as live updates to the structured chunk pattern schema to our name output field in our scan, like pattern_map or something that produces chunk sample queries over pageranked linked chunk vectors that have links to the chunk pattern skeletons within the recursive tree structure." (user, verbatim)

> "The ultimate aim of any structural rendering of combinations of special recursive-structured-types on our output that is linked to our input variables via the functional input/output link is to provide a universal structural representation and UI parsing/transformation that is flexible to types, structured templates, and references to functional-object node panels that are themselves also compiled computation graphs." (user, verbatim)

The realisation maps to §15.7 (URL-Set Knowledge Panel), §15.8 (Golden-Trio Pattern Rule + `pattern_map` Output), §4.6.2 (Plus-Signs on Right/Bottom progressively building a panel), §4.1.1 (Hidden-Overlay Edit Buttons), §8.2.1 (multi-semantic-frequency-PageRank with 6D-UMAP HSV-rotating halo), and §9.7 (Python-Library Middleware that generalises the four-object materialisation rule). Every claim in the verbatim above resolves to one or more of these sections.

### §1.2.2 Halo Mechanics — Multi-Semantic-Frequency-PageRank (Verbatim)

> "A clear design space must also be laid out for our halo-based retrieval mechanics (multi-semantic-frequency-pagerank), where nodes in our 3D are actually ray-projected to the conic surface of the concentric 2D similarity as collapsed singular nodes with their original image billboards or slowly rotating umap colors (where umap projections are supposed to be 6d, 3 for hsv that are then slowly rotated similar to how the 3D rotates)." (user, verbatim)

The realisation: §8.2.1 specifies the **multi-semantic-frequency-PageRank** ranking (the triple product §8.1 evaluated at multiple semantic frequencies — token / phrase / paragraph / document scales — with PageRank weights), the **6D UMAP** (`[x, y, z, h, s, v]` with the HSV triplet slowly rotating at the same period the 3D camera does so visual identity persists across observation angle), and the **ray-projection** of the focal panel's projector-resident chunks to the conic surface (the halo's inner ring) so the user reads simultaneously the focal's *retrieval space* (concentric halo) and the focal's *manifold neighbourhood* (the 3D points the ray projection collapses from).

> "The advance in our framework comes from how primitives are represented and interacted with. Our 2D concept graph compilation editor begins with the base universal primitive 'empty' node. This empty node shows all possible functional links extending from the empty node for the user to select and play around with. As the user types in descriptions and values, these fields are embedded via quantized SLM transformer and retrieval is applied to all nodes in the database, showing optional new functional objects radiating around the primary empty primitive node. Once the first object is created, the retrieval over suggested linked nodes enables the user to quickly link new functional objects and route new signals through the conceptual computation graph. The autonomous agent can also do the same with exposure to these node interaction tools. Our fundamental tools include things like database and web search, generative tasks (prompts and meta-prompts), retrieval, web navigation, env state edits/navigation, and other agent computation graph editor prompts."

The empty primitive (§5.1) is the universal start. The triple-product retrieval (§8.1) is the radiation source. The agent operates the same primitive identically (§12.5). The **fundamental tools** the user names — database/web search, generative tasks (prompts and meta-prompts), retrieval, web navigation, env state edits, agent computation graph edits — are all surfaced as Function-typed ConceptNodes through the Python-API materialiser (§9.6 / §9.8), uniformly accessible to user and agent.

> "Note that the 'inverse' on our concept cards automatically applies, because the compilation applies both forward function call and the inverse closest lookup."

The closest-inverse lookup (§7.7) is therefore not a separate gesture — every Compile press applies forward execution AND inverse retrieval simultaneously when an input port is unbound. Bidirectionality is a link-level property of every typed edge (§3.2).

### §1.3 Core Problem

Composing local AI workflows over the user's own knowledge — scanned web pages, authored ontologies, agent-emitted artefacts — without leaving the device. The user pours intent into one editor; the workspace's substrate runs real Selenium, real GPT4All, real nomic, real LangGraph, real Kuzu (§13); the comparison surface (§9.14) makes the workflow's behaviour empirically observable.

### §1.4 Endgame

A **single play loop** (§8D.25): scan ↔ compose ↔ compile ↔ read the projector ↔ revise. The loop is exercised by three lodestar use cases (§16) and one unified synthesis (§16.4). Anything that prevents any one of the four from running smoothly is a design or implementation gap (§14.1).

### §1.5 The Three Registers — Operating Together

§1.1 names the Mortegon as the shape of death across three registers, but what the registers actually do — how they touch, what flows between them, where the alchemy gets its bite — is what this section is for. The Real is the 3D Projector (§9), where every scanned chunk and every computation-graph output sits as a perceptual measurement in the same UMAP-fitted manifold; what we see in the projector is a sensory reading of the world the agent acts within and to which its outputs return. The Imaginary is the 2D Concept Editor (§4, §5, §7), where every perception is *abstracted*, *imaged*, *projected* — the perception we just saw rendered as geometry in the Real is now a concept node carrying a print-rendered tree, a halo of radiating candidates, a chain of `{var}` references, and (when the agent reaches into the panel) the very structure of its own reasoning. The Symbolic is the REPL (§14), the layer of full transparency over both, where the totality of what happens in either of the other registers is recorded, broadcast, and made interactable through the same gesture vocabulary by humans and agents alike. Each register is its own canvas; the Mortegon is what they *do to one another* as the user composes.

The flow between them is alchemical rather than sequential. A scan begins in the Real — chunks materialise in the projector as they stream in — and the moment a chunk lands, it is already a retrieval pattern, indexed for TF-IDF and nomic the same instant it appears (§8). The Imaginary contracts the Real into abstract structures: the manifold is *retrieved* in manifold form (§8.2.1.1's ray-projection makes this literal — the chunks nearest the focal are projected onto the halo's conic surface as collapsed singular nodes) and contracted further into the typed concept-graph primitives the editor manipulates. So the Real → Imaginary direction is, simply, *measurement abstracted through retrieval*, with no pre-retrieval phase to wait for. Every perception was always a retrieval pattern from the moment it became visible at all.

The Imaginary is fundamentally *abstracted* from the Real, but it is *transcendental* in the sense that any single Real measurement supports many parallel Imaginary projections — the same chunk lives in multiple semantic-frequency bands (§8.1.1), is referenced by multiple concept nodes' `{var}` chains, radiates from multiple focals' halos, and (when the agent's compute graph emits its terminal cards) returns to the Real at multiple perimeter locations (§6.6.1). These flows compose without exclusivity. The Imaginary is, in this way, an *image* of the Real (literally — the word's etymology) that supports flows of projection through semantic space without any one flow exhausting the perception it began from.

When the loop closes, the Imaginary's outputs return to the Real along a perimeter-encompassing path — the agent's final cards (the terminal points of its computation graph) land on the projector's outer envelope rather than in the manifold interior (§6.6.1). The user reads the Real's interior as observations and the Real's perimeter as syntheses; the 2D and 3D canvases stay spatially separate (§6.6.2) — the cross-canvas projection is the only coupling between them, and that coupling is one-way at the canvas level (3D state never writes back to the 2D pin coordinates). What we get is a *legible round-trip*: the Imaginary's output appears on a different canvas than where we composed it, so the closure of the cycle is visible.

What every concept node looks like, in this scheme, is a *distributional substance radiating from a focal point* — the §1.1 phrase made structural. Hard links form a commitment fan between the focal and the targets the user (or agent) has committed to wiring; soft links form the concentric possibility ring (§8.2.1) at the halo radius; the print rendering carries the structured field tree (§4.6); and every one of these is continuous around the focal in angular and radial position rather than a flat adjacency list. The user reads *density and direction* together. The hard/soft layout is spatially independent — the commitment fan and the possibility ring share the focal anchor but occupy distinct regions (the fan reaches outward to the committed targets; the ring sits concentric at the halo radius), so the user can always tell what is *structure* from what is *available expansion*. A click promotes a soft link to a hard link, and the spatial promotion echoes that: the phantom fades from the ring while the new hard edge materialises along the fan.

The Symbolic register makes the entire alchemy legible. Every step of the loop emits a frame — `chunk_added`, `umap_canonical`, `concept_changed`, `concept_index_update`, `ui_state_changed`, `agent_token`, `evolution_diff`, and the rest — and the REPL re-reads those frames in the same monotonic order the GUI received them (§10.1, §11.4). What we get in the Symbolic is not a log but a *running representation of the app as a computation graph within its own symbolic space* — the REPL transcript shares the same philosophical structure as the thing it is representing, which is what makes the REPL transcendentally permanent: the app is self-similar across the registers it composes through, and the Symbolic register is the surface that makes this self-similarity legible.

The deeper structure of the Mortegon is the *telos of computation itself* — the polar dialectic between structural definite (every compute graph fixes its structure when it compiles) and free-flowing dynamism (every halo, every autoregression, every cascade re-fire dissolves and reconstitutes structure). The Symbolic register holds both poles in the same telemetry stream: a `concept_changed` frame records the commitment, and the next `concept_index_update` records the dissolution as new soft-link candidates radiate from the changed node. The cycle, then, is *infinite self-negation and inversion* — every commitment negates the prior possibilities it consumed, and every possibility inverts the prior commitments it grew from. The Mortegon's shape-of-death is the geometric expression of this self-consuming process: every closed loop is simultaneously an opening, every settled structure is simultaneously an invitation to further halo retrieval.

When future sections need a register reference, here is the operational summary; the philosophical narrative above is the primary anchor and the table below is the index.

| Register | Surface | What it carries | Primary sections |
|---|---|---|---|
| Real | 3D Projector (§9) | Perceptual measurements: scanner-emitted chunks, computation-graph outputs, the comparison-surface geometry | §6, §9, §9.14, §15 |
| Imaginary | 2D Concept Editor (§4, §5, §7) | Images of perceptions: concept nodes, halo retrieval radiations, pure-print rendered fields, the agent's own reasoning graph | §4, §7, §8, §12 |
| Symbolic | REPL (§14) | Representations: REPL actions, WS frames, telemetry, the in-place activity viewer | §14, §11.7, §11.8 |

The hard link / soft link distinction is the Imaginary's mechanism for separating commitment from possibility, and §3.2.1 carries the full account: hard links are `ConceptEdge` records committed to Kuzu (solid full-colour lines along the commitment fan), soft links are halo-suggested candidates living in the apparition cache (solid lighter lines along the possibility ring), and the click that promotes a soft to a hard is also the spatial transition between the two regions. The autoregressive feedback that runs through the click (each promotion spawns a new focal whose own halo radiates) is the Imaginary's way of *exploring the latent connection space* without polluting the deterministic edge table — the cycle of negation and inversion playing out, in miniature, at every click.

### §1.6 On-Device Stack

| Subsystem | Production | Fake gate (harness-only) |
|---|---|---|
| **SLM** | GPT4All `Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf` on CUDA. **No Llama** (forbidden, §8D.46). | `WFH_FAKE_SLM=1` |
| **Embedder** | GPT4All `Embed4All` `nomic-embed-text-v1.5.f16.gguf` on CUDA. | `WFH_FAKE_EMBEDDER=1` |
| **Selenium** | Headful Firefox via `backend/drivers/geckodriver.exe`. | `NO_WEBDRIVER=1` |
| **LangGraph** | `langgraph.graph.StateGraph` orchestrating `ConceptComputeNode` chains (§11.7). | none (missing = 503) |
| **Graph DB** | KuzuDB embedded (`WFH_DB_PATH` overrideable). | none |
| **3D** | Three.js with InstancedMesh; backend computes layout, frontend renders (§9.4). |  |

Production paths **never set any fake gate**; `GET /api/subsystem_status` reports `all_real: true` (§13).

---

## §2 — Architectural Principles

These are the design's load-bearing invariants. Every component honours them; every commit re-asserts them.

### §2.1 Backend Computes; Frontend Renders

Layout (§9.4), embeddings (§8D.17), PageRank, lifecycle dispatch (§10.2), apparition scoring (§8D.43), compile dispatch (§7.1), and persistence (§11) are all backend services. The frontend has **no UMAP runtime**, **no embedding fitter**, **no global layout reasoner**. It receives canonical state on the WebSocket and renders.

### §2.2 One Lifecycle Dispatcher

Every concept mutation goes through `apply_update_lifecycle` / `apply_delete_lifecycle` (`backend/services/concept_lifecycle.py`). The dispatcher fans out to: Kuzu write → WS broadcast → ConceptIndex upsert (§8D.17) → output-projection schedule (§9.12) → evolution-log diff (§11.4) → cascade scheduler nudge (§7.4). There is no second mutation path; agent, user, REPL, and python-API materialiser all enter through it (§12.2).

### §2.3 Two Progressive Vectorization Pipelines

- **Chunk side:** TF-IDF incremental + UMAP joint refit at scan-end (§9.3). The Layout Service owns this.
- **Concept side:** nomic incremental + PageRank joint refit on cascade-settle (§8D.17). The Concept Index Service owns this.

The two services are **siblings**, never nested. The two embedding axes never mix for scan chunks (§8D.17.1); knowledge panels are the **exception** (§O.22) — both models run over the same rendered panel chunk, max-combined after min-max-normalizing each cosine to [0, 1] over its own space.

### §2.4 Monotone WebSocket Frame Sequencing

The workspace WS carries a monotone `frame_seq`. `?resume=<seq>` replays the last 5 minutes. Lossy backpressure drops oldest *progress* frames, keeps `done`, `error`, latest `umap_canonical`, latest `concept_index_update`, all `concept_changed`, all `evolution_diff` (§11.4).

### §2.5 Idempotency Keys On Every Mutation Route

Every POST/PATCH/DELETE accepts an idempotency key; replays return the original effect without re-applying. This makes the REPL ↔ frontend round-trip retry-safe (§14.3).

### §2.6 Append-Only Evolution Log; Three Rollback Scopes

`EditDiff` records are append-only (§11.4). Rollback applies the inverse and **records the rollback itself as a new diff**. Three scopes: single edit, edit range, actor scope. The user's tool for conflict resolution is rollback, not a pessimistic lock (§2.7).

### §2.7 Optimistic Concurrency, Not Pessimistic Locking

Last-write-wins across actors. The cascade scheduler's actor-aware short-circuit (`agent:<id>`) prevents agent self-loops but does **not** serialise across actors. User and agent edits compose; if they conflict the user rolls back through the evolution log (§11.4).

### §2.8 Subsystem Failures Are Loud

A failed nomic load, a dead Selenium driver, a missing GGUF — these surface as 503s and halt the cascade. Quiet substitution to stubs is the anti-pattern (§13.4).

### §2.9 Doc-First, Correctness Over Comprehensiveness

The order of operations on every iteration: (1) capture the requirement in [`USER_REQUIREMENTS_VERBATIM.md`](USER_REQUIREMENTS_VERBATIM.md), (2) audit the code, (3) record the gap analysis (note: [`CODEBASE_GAP_ANALYSIS.md`](CODEBASE_GAP_ANALYSIS.md) is now **historical**, §O.17 — a fresh audit supersedes it), (4) only then change code. A screenshot is **not** feature proof; verification runs in the REPL against the live full stack (§14.1).

---

## §3 — The ConceptNode Schema

Everything the workspace manipulates is a `ConceptNode` (§8D.44). One table, one edge table, separable backing pointers (§8D.44).

### §3.1 The Record

```python
@dataclass
class ConceptNode:
    concept_id:        str   # opaque UUID
    name:              str   # slug source; renames propagate {old} → {new}
    description:       str   # nomic-indexed (functional declaration; §8D.40)
    data:              str   # constructor template (§8D.30); JSON-serialised field-tree
    rendering:         str   # tf-idf-indexed; compile output (§8D.20)
    linked_nodes_json: str   # cached neighbour list
    backing_pointer:   str   # "python_function::<qual>", "agent::perception::<pcid>", ...
    pagerank:          float
    provenance:        str   # user-authored | agent-authored | derived-from-chunk | committed-subgraph
    workspace_id:      str
    layout_xy:         str   # last-known editor position
    ui_state:          str   # collapsed/expanded/pinned/latched
    type_hint:         str   # naming convention (NOT a discriminator)
    created_at:        str
    updated_at:        str
```

### §3.2 The Edge

One `ConceptEdge` dataclass; `edge_type` is the union enum of:

- §8A.2 typed labels (`IS_A`, `HAS_A`, `PART_OF`, `RELATES_TO`, `SIMILAR_TO`, `CLASSIFIES`, `DERIVED_FROM`, `INCLUDES`, `ANNOTATES`).
- §8D port-binding labels (`SOURCE_PORT`, `TARGET_PORT` via the edge's `source_port`/`target_port` fields).
- Web-ontology edges (`SearchableURL → DetectedAccessor`, `XPathPattern → DomSnapshot`, etc.; §8D.39).
- Python-native edges (`OBJECT_HAS_PROPERTY`, `OBJECT_HAS_FUNCTION`, `FUNCTION_INPUT_TYPE`, `FUNCTION_OUTPUT_TYPE`; §8D.4.2).

**One edge table; never two.** Forward query applies the map; inverse query is closest-match by triple product (§8D.7).

#### §3.2.1 Hard Links vs Soft Links (§1.5)

The Imaginary register (§1.5) carries connections between concept nodes in two modes:

| Mode | Persistence | Visual treatment | Source |
|---|---|---|---|
| **Hard link** | Committed `ConceptEdge` record in Kuzu — survives reloads, participates in PageRank, drives the cascade (§7.4). | Solid, **undirected** line; full-saturation brightness (per `edge_type` palette); ~2px stroke; **no arrowhead** (§O.16). | User wiring, agent emission via `LinkAction`, variable auto-creation (§8D.21.1), or compile-expand (double-left-click, §7.3.4) of a parent's `{var}` references. |
| **Soft link** | **Not persisted** — lives only in the in-memory apparition cache (§8.2) of the focal panel's halo. Vanishes when the halo closes. | Solid, **undirected** line (no dashes — §forbidden-concepts); lighter brightness (≈40 % of the hard-link palette); ~1px stroke; **no arrowhead** (§O.16). | Triple-product apparition retrieval (§8.1) around any focal panel. |

A **click on a soft link** (or the halo phantom it terminates at) promotes it to a hard link via `POST /api/concept_edges` (§5.4) and commits to Kuzu through the lifecycle (§10.2). The autoregressive feedback (§8.2) — clicking a soft link spawns a new concept node *and* a new halo radiating from it — is therefore the imaginary's mechanism for *exploring the latent connection space* without polluting the deterministic edge table.

The cascade (§7.4) acts only on hard links; soft links are never re-fired and never participate in PageRank. Inverse retrieval (§7.7) reads the hard-link graph for forward execution and the soft-link space (the ranked apparition surface) for the inverse closest-match suggestion.

### §3.3 Backing Pointer Resolution

`backing_pointer` is opaque to the editor; the runtime registry (`backend/services/backing_registry.py`) maps it to live Python. Examples:

| Pointer prefix | Resolves to |
|---|---|
| `python_object::<qual>` | The imported class object |
| `python_function::<qual>` | The bound callable |
| `python_property::<qual>` | The descriptor / dataclass field |
| `agent::perception::<pcid>` | A `PerceptionTick` bound to the parameter card |
| `agent::transformer::<pcid>` | The SLM dispatch surface for this agent |
| `agent::emitter::<pcid>` | The `ActionResolver` gate |
| `fixture::database::<wsid>` | The unified Database handle |
| `fixture::web_browser::<wsid>` | The `WebBrowserManager` singleton |
| `fixture::agent::<wsid>` | The meta-cognition tick registry |
| `xpath_pattern::<hash>` | The compiled accessor map for the pattern |
| `searchable_url::<hash>` | The detected search-input action |

A bumped pointer version (§8D.39.6) invalidates the cached compile.

---

## §4 — The Unified Knowledge Panel (§8D.1)

> **One template, one code path** — used identically for the hover billboard, the click-pinned panel, the apparition halo phantom, and the compiled-graph child. There is no second pin-panel widget, no separate "content summary." (§USER C.1, MORTEGON §1.1)

### §4.1 Anatomy (§8D.1.1)

Every panel — scan-spawned, user-created, agent-emitted, variable-auto-created — wears the four canonical fields:

| Field | Editable | Default source | Notes |
|---|---|---|---|
| `name` | Yes | Last two segments of the chunk's absolute xpath | Slug-derived; rename propagates `{old}→{new}` across descriptions and data of every other card |
| `description` | Yes | Empty for scan-spawned panels | Nomic-indexed; `{var}` references resolved at compile (§7.2) |
| `data` | Yes | Full chunk summary (no truncation; §8D.1.1) | The constructor template (§8D.30); dissolves into a field-tree at the UI layer (§4.5) |
| `rendering` | Read-only | Produced by Compile | Result of recursive substitution (§7.1); TF-IDF-indexed for retrieval |

Chrome: **none** — see the §4.1.2 black-slate design constraint (§S.4). The whole slate is the drag handle (textareas exempted); there is no header bar, no minimise button, no close button, no per-id hash colour.

#### §4.1.2 The Black-Slate Minimalist Design (§S.4, §S.5)

> "thin-silver border and completely black infill with serif white text … minimalism and intrigue within
> the unknown … only this blank editable bordered slate … similar for computation nodes … Nothing other
> than the black slate. No x, no minimizer, no top bar whatsoever." (user, verbatim, S.4)

The knowledge-panel half of the dialectic — and the computation-node half equally — is rendered as a **blank editable bordered slate**, and nothing else:

- **Thin silver (specular) border**, **completely black infill**, **serif white text**. One CSS contract (`--slate-border` ≈ `#c0c0c0` 1px, `--slate-fill` `#000`, serif white) applied to `.concept-card`, the pinned-panel surface, AND the value-only computation-node form. The prior coloured-header / hash-hue chrome (§4.1, formerly) is **removed everywhere** — it is now a forbidden concept (§18 black-slate clause).
- **No chrome whatsoever:** no `×`, no minimiser, no top bar, no header strip. Fixture undeletability (§9.5) is enforced at the lifecycle layer, not by an absent button — there is no button to absent. Affordances that were chrome (compile, latch, grow `+→`/`+↓`) surface as **hidden-overlay** controls on hover/edit (§4.1.1) over the slate, never as a persistent bar.
- **Collapse-into-parent gesture (§S.5).** A panel collapses into its **parent field computation node** — the value-only rank-1 form (§4.5, the existing `_applyCompiledChildMode` generalised). This is the same black slate at its most compact: one editable field, the rest referenced up the recursion-over-iteration tree by `{var}` (§4.6.1). The collapse gesture is the §7.3.4 base-node collapse / the §6.6.5 dominance fold; it must be available on every panel.
- **Clicking a collapsed node keeps its halo proximal (§S.5).** Clicking a collapsed-node form of a larger hidden panel structure fires the §8.2 focal halo: retrieved candidates **radiate proximal to the central (clicked) node** while the collapsed node *abstracts over* the semantic-space content and distribution complexity it hides. The halo is how a black slate with one visible field still exposes the depth it folds away — retrieval stays attached to the focal, not spread across a separate surface (which is exactly why the §8.3 retrieval sidebar is deprecated, §S.3).

This is purely a **rendering/chrome** contract: the four canonical fields (§4.1), the field-tree (§4.5), `{var}` linking, compile, and every gesture are unchanged — only the panel's *visual presentation* becomes the black slate.

#### §4.1.1 Click-To-Edit With Hidden-Overlay Buttons + Shift-Enter (§1.1 Imaginary, §1.2.1)

The user's framing is worth keeping at hand here too: *"Each pure-print rendered field in the knowledge panel representation that structures the computation graph representation is clicked to be edited, where clicking a pure-print token rendered in the knowledge panel immediately opens up its (possibly multiline and curly-brace containing) editable field, and pressing enter updates it back to its regular print within the print-rendered tree structure."* And from the §1.2.1 update: *"Interaction details with our syntactically-stripped recursive tree printed knowledge cards (minimalist-most text rendering) without any other display, however hidden buttons overtop the various layout sections, when clicked, become editable fields. Shift-enter rules for multilines value fields should also be followed, as well, of course, as curly-brace references."*

What this gives us is a panel whose resting form is *pure print* — tabs and newlines, no JSON braces, no HTML angle brackets, no YAML dashes, no chevrons or placeholder boxes or any per-row chrome — and whose interactivity is *latent* inside hidden buttons that overlay the various layout sections of the print rendering. The user sees only the print; the buttons are transparent and unstyled at rest, sized and positioned to match the bounding rect of the print token underneath, and they reveal a subtle focus indicator on hover (a one-pixel outline, a barely-visible background tint at around ten percent opacity) so the user knows the region is interactive without that knowledge breaking the minimalist-most rendering. On click, the button is replaced in place by a textarea pre-populated with the underlying value, the caret position respecting where in the printed text the click landed, and the user begins editing immediately.

When the user is done, *Enter* commits the value through the lifecycle (§10.2) and the field returns to its print form; *Shift-Enter*, in multi-line fields, inserts a literal newline without committing — with **intelligent `\t` / indent parsing** that auto-indents over the tree structure the way a smart markdown editor does (N.12); *Escape* discards and returns to the prior print at the prior value; and blur (clicking elsewhere) commits identically to Enter. While the field is in Edit, the cascade scheduler (§7.4) is *not* triggered per keystroke — the commit on Enter is the cascade trigger, which keeps the editor responsive while the user is typing and avoids recompiling on every character. Tabs and newlines from multi-line content integrate seamlessly into the pure print of the remainder of the tree data structure — the parent tree's indentation absorbs the multi-line content without introducing JSON-string quoting or escaped-newline glyphs anywhere — which is what makes the print form *recursive* in the §1.2.1 sense rather than syntactically structured. Curly-brace `{var}` references are honoured during the edit and resolve at compile (§7.2); the user can type them directly in the textarea exactly as they appear in the print rendering when the field has settled.

The same contract holds across every editable field in every representation — the `name`, `description`, and `data` field-tree rows on a standard pinned panel (§4.6), the single `name : value` row on a compiled-graph child (§7.3), and the plus-sign cutout templates (§4.6), which materialise directly into the Edit state on click so the user types immediately rather than first seeing an empty print form. Read-only fields (the python-native nodes of §9.6, the `rendering` field on any node) do not enter Edit on click; the click is visually a no-op but briefly highlights the field to signal the read-only constraint, which the panel header already marks with a 🔒 indicator. The print form is the only form for read-only fields, and the dialectic of edit-open / commit / return-to-print never gets invoked on them.

What this whole arrangement realises, at the UX layer, is the §1.1 Imaginary register's character — every concept node is a print rendering by default, every edit is an *opening* into the imaginary's editable field rather than a syntax-laden form, and the minimalist-most rendering of the §1.2.1 spec is enforced not by hiding capabilities but by *latent* interactivity. The print is unadorned, the buttons are invisible at rest, and the moment the user clicks, the field opens — the surface itself is the carrier of the imaginary's projective property (§7.7), with no chrome between the user and the structure they are composing.

### §4.2 Freeze-At-Hover-Rect On Click (§USER C.2, MORTEGON §1.2)

1. Mouse enters a 3D node → hover billboard appears at projected screen position.
2. Mouse moves between nodes → hover billboard updates in place.
3. Mouse clicks → the hover billboard's *current* `getBoundingClientRect()` is captured; a new draggable, multi-pinnable panel materialises at exactly that `(top, left, width, height)`; the hover billboard resets so the next hover can preview a different node.
4. The pinned panel is independent: drag header, resize via corner handle (`resize: both; outer overflow: hidden; body overflow: auto`; §4.4), minimise, close (×), Compile.

A second click on the same chunk **raises the existing panel's z-order and un-minimises** rather than spawning a duplicate.

### §4.3 Collapsed-By-Default (§USER C.4)

A newly pinned panel renders **collapsed** (name + read-only indicator only). The apparition halo phantom (§8.2) shares this collapsed form. Hover or click expands; blur (debounced) re-collapses.

### §4.4 Latch + Form-Fit + Slide-Out Data Panel (§8D.1.2)

A small latch button on the panel's right edge (between resize and close) toggles two modes:

- **Latched (default)** — only `name`, `description`, `rendering` visible. The `data` field is hidden but not unloaded. Latch icon ▶.
- **Unlatched** — `data` slides out as a side panel **at equal height** to the latched body, **visually joined** (one bounding outline, one drag handle, one resize handle on whichever side is currently widest). Latch icon ◀.

**Form-fit sizing:** each `<pre>` measures longest line; panel grows up to `max-width: 600px` (latched) / `800px` (unlatched) before introducing horizontal scroll. Empty fields hide their row entirely. Minimum panel = header strip + buttons.

**Equal-height contract:** the two halves resize together; a longer description grows both heights in lockstep.

Read-only python-native panels (§9.6) **hide the latch** and show a 🔒 indicator.

### §4.5 Compact Representation Standard (§8D.1.3)

> "There are various details mentioned perhaps elsewhere in the docs on the interaction properties and user experience activities on interactive/dynamic retrieval halo properties of apparition nodes, which literally should just display the name without anything else. This is a compact representation standard everywhere in the concept computation graph compilations in terms of representations." (user, verbatim)
>
> "please document in minimal naming scheme in compiled form everywhere without even the monotonous 'name' field." (user, verbatim)

Three representations of one ConceptNode, used everywhere consistently:

| Representation | What it shows |
|---|---|
| **Unfolded panel** (§4.1) | All four canonical rows + user-added rows (§4.6) |
| **Apparition halo phantom** (§8.2) | **Name only**. No score chips, no description preview, no rendering snippet. Scores live in slow-hover tooltip (§8.2). |
| **Compiled-graph child** (§7.3) | **Value only**. Name is implicit from structural position in parent's field-tree. Multi-line values expand the box to fit. |

The data-block as a separate JSON blob **dissolves**: at the UI layer the `data` field is rendered as a recursive **field-tree** of editable `name : value` rows (§4.6). Persistence still stores serialised JSON; the user never sees JSON syntax.

> "This means that data block components are removed entirely for editable text-only object fields that interface with multiple syntaxes of data objects themselves." (user, verbatim)

### §4.6 Plus-Sign Field-Tree Growth — Progressive Compute-Node → Panel (§USER E.3, E.4; §1.2.1)

The user's voice across several prompts is what carries this section: *"We can add horizontal (Parent-child) and vertical (neighbor) field with plus signs that appear and link as cutout templates to the real field that appears when either plus sign is then hovered over and clicked. Each node has a name and a value, could be numerical and singular, could be multiline with curly brace references."* And from §1.2.1: *"Of course, when clicked from pure-print to editable fields, additional buttons with '+' signs on the right and bottom of the singular key:value computation node are concatenated in the pure-print tree structure that can progressively build the compute node into a knowledge panel seamlessly, so perhaps our computational graph compilation via right-clicks simply re-aggregates externally referenced nodes into the minimalist pure-print tree-structured (tabs and newlines, no syntactical details other than pure key-values)."* What the §1.2.1 update sharpens, then, is the *placement* of the plus-signs (right and bottom of the singular key:value compute node), the *timing* of their appearance (only when the node is in Edit state per §4.1.1), and the *symmetry* of the build with right-click compile-collapse, which re-aggregates externally-referenced nodes back into the pure-print tree.

The plus on the right (`+→`) adds a child row indented one level — the horizontal axis is the parent-to-child direction, and what materialises becomes a grandchild of the current row's parent — and the plus on the bottom (`+↓`) adds a sibling row at the same nesting level. Both are rendered as cutout templates concatenated *into the pure-print tree structure itself*, falling back to the print rendering's tabs-and-newlines indentation rather than introducing any new visual idiom. Hover on a plus previews the slot it will create as a faint print placeholder; click materialises a real editable row in Edit state, so the user types immediately rather than seeing an empty placeholder row and then having to click it again. Each new row is itself a concept-node-shaped record — a name, a value, and the same capacity to grow further children of its own — and the value of any row may be a literal scalar, a multi-line string with `{var}` references (§7.2), or a nested structured tree of further rows. The reserved canonical rows like `name` and `description` are themselves field-tree rows with reserved key slugs, and the user can add arbitrary additional rows at any depth around them, which is what makes the panel anatomy of §4.1 a *default starting state* rather than a fixed shape.

The single-key:value compute graph node and the full knowledge panel are, in this scheme, *the same record at different sizes*. A compiled-graph child (§7.3) starts as a single `name : value` row; clicking on its print form opens the cell for editing and reveals the right and bottom plus-signs; as the user adds children and siblings, the node grows seamlessly into a full panel anatomy, with no "promote to panel" affordance because the field-tree growth *is* the promotion. The inverse — right-click compile-collapse, which §7.3 frames as the dialectical inversion between the synthesis (panel) and analysis (subgraph) representations — re-aggregates externally-referenced nodes back into the parent's pure-print tree-structured form (tabs and newlines, no syntactical details other than pure key-values). So the synthesis/analysis cycle of §7.3 is *also* the cycle between the singular compute-node and the full panel, and the dialectic plays out the same way at both scales. **The singular-primitive aspect is the discriminator (§O.19):** whether a 2D element *is* a computation-graph node or a knowledge panel follows from its granularity — a **singular primitive** (one field) IS a graph node; a non-singular aggregate is a **knowledge panel** that compiles to the graph form. The computation graph is built of singular-field nodes; a panel is their aggregation, and the panel↔graph dialectic (§7.3.4) moves between the two.

The user names the underlying impulse this realises: *"I would hope for a data-agnostic recursive tree interpreter for rendering the variable key:value fields that are generalizable between syntaxes and their native types, which when compiled, only show the values of the keys on computation graph concept nodes."* The same recursive descent that §7.1 uses to decompose the data block drives the editor's field tree — JSON input materialises as N key:value rows, HTML input materialises as element-name keys with attribute keys folded as `@attr` children, and indented text materialises by its indentation alone, with tree-pretty-print (§8D.20) as the canonical syntax-stripped form for any input. Tabs and newlines from multi-line value fields integrate seamlessly into the parent tree's indentation without ever surfacing JSON quoting or escaped-newline glyphs anywhere, which is what makes the print form *recursively* readable as the §1.2.1 spec requires.

**Key-value vs multiline inferred by consistent tabs; `{}` is the field on-ramp (§O.20).** Within one super-field (parent node), the interpreter implicitly distinguishes a **key-value** child (a singular value) from a **multiline** child — whose **key is the primary key to the multiline data, denoted by consistent tabs beneath it** — purely from indentation in the naked text field, with no syntax markers. A new field's on-ramp is a **variable key (spaces allowed, §O.10) beside a singular empty `{}`** (e.g. `scan for url {}`), exactly how the scanner represents functional-objects (§9.6.2); the empty `{}` is the unbound reference slot the user then fills or unfolds (§O.1). This is what lets **pydantic templates** (§7.2 / §O.20) be authored as field-trees rather than JSON schema.

**Long-field rendering — name truncation vs full values (review clarification §O.4).** Field *names* (the variable key) forward-truncate at a short length (default ~20 characters) with an ellipsis — the front is kept, the tail elided — and the full name shows on slow-hover; field *values* render in **full**, multiline and never truncated. So a long descriptive node name reads compactly while its multiline value (a prompt template, a chunk's content) is shown whole. The recursive tree rendering extends to **chunk samples** (§15.8): each sampled chunk renders as a tree node whose golden-trio fields (title / link / content) are its rank-1 children, under the same pure-print minimalism and the same name-truncation / full-value rule.

**Deduplicated value aliases — `↳` continuation rows (lifted from MORTEGON §1.1 as a design feature, §O.17).** When several keys / xpaths in a field-tree resolve to the *same* value (common in distilled chunk fields), the value prints once and its additional aliases render as `↳`-prefixed continuation rows beneath it (one alias name per row) — keeping the print minimal without losing which keys share a value. The alias names forward-truncate exactly like any field name (§O.4); the shared value renders in full once.

#### §4.6.1 Signal-Stream Constraint Under Iteration (§1.2 update; §9.5.1 Database.concept)

The user introduces the signal-stream constraint in passing in §1.2: *"Note the 'signal-stream' constraint in our UI docs somewhere. This means that for iterables, only the signal node that's being iterated on is visible in the 2D ui panel, so knowledge panel structures can have multiple values that are iterated over for each rollout of the computation graph with recursive firing."* This is, on the face of it, a display rule, but it has structural consequences for how iteration composes with the panel anatomy.

When a knowledge panel carries a field whose value is iterable — a list of chunk patterns returned from `WebBrowser.scan`, a list of rank-1 graphs returned from `Database.concept(node_id_list)`, a list of URLs passed through `{urls_panel}` into a downstream scan field, or any other unbounded-cardinality value — the panel renders only the currently-iterated signal node at any moment. The other elements of the iterable are stored in the underlying ConceptNode's `data` field (as references/values) and are not lost, but they are suppressed from the visible print rendering until the iteration advances to them. For **chunk-bearing** iterables the full distribution lives in 3D (§O.14) and the panel renders the **current instance's content** per-instance (the next-up in the variable's memory queue), sampled from the 3D env **or** by halo-retrieval (§O.18); scalar iterables (e.g. a URL list) remain as values in `data`. The default signal index is the first element when the iteration is not actively running, and the play/pause iterated rollout (§7.5) advances the index per step, with the panel re-rendering to show the new signal node's print form in place of the prior one. For a `Database.concept(node_id_list)` field, the iteration cycles through each node id in the list, the panel renders the rank-1 KG around that node as the visible signal, and the downstream cascade (§7.4) re-fires per signal — so the recursion-over-iteration tree composes correctly, with the recursive firing the user names operating on whichever element of the iterable is currently the visible signal. The suppressed iterable elements remain in storage and are accessible via direct REPL inspection (§14) at any time, which is what makes the constraint purely a display rule rather than a storage rule, and what lets the user step back through prior signals via the play/pause control without losing what was already iterated.

The signal-stream constraint resolves the tension between the §4 panel's minimalism (one signal visible at a time) and the unbounded-cardinality iterables that real workflows produce. It also lets us reason cleanly about the cascade — the cascade re-fires *per visible signal*, not once for the whole iterable, which is what gives recursion-over-iteration its tractable shape.

**Realisation (§R.7).** The per-visible-signal re-fire is enforced at the advance primitive: `POST /api/ui/signal_advance` routes through `RolloutCoordinator.advance` (the one advance primitive — it also lands the §11.4 `sample_boundary` diff), and a cursor move recompiles the iterable card's transitive `{ref}`-consumers through the bounded §7.4 BFS, so the dialectic graph-panel renderings track the *current* sample (E.9 diff-consistent state). Index 0 is a legitimate cursor position — the modulo wrap re-fires like any other move. REPL: the `iterated-signal-rerender` scenario drives advance → consumer-rendering assertions through the live stack.

**Conditional per-sample rendering (N.9).** Per-sample signal print-rendering is only performed when a downstream computation link **externally references** the node's recursively-chunked iterable (§9.6.2). An iterable that nothing downstream consumes displays only its uppermost abstraction — the collapsed `{ref}` (e.g. `chunk {chunk samples}`) — and does not stream per-sample until it is referenced; the full per-sample distribution lives in the 3D GUI regardless (§6, §9.6.2). This keeps the 2D tree minimal: signal-stream is a *lazy* rendering that activates on external consumption, not an always-on per-element render.

**Iterables are rooted at base/root nodes (§O.19).** A recursive chunk's iterable is *sourced to its base/root node*, so a panel that references the iterable **dynamically updates from the root source down to its fields** as the root changes. The reference honours the internal/external switch (§O.1): a `{curly brace}` reference keeps the iterable as an external in-memory node — and **only then is per-sample recursive chunk iteration applied** — whereas rendering the content **inline** in the panel does not trigger iteration. The contract is exact: **iteration ⟺ an external `{ref}` to a recursively-chunked iterable**.

#### §4.6.2 Three Rules Operating Together (§1.2.1 synthesis)

What the §1.2.1 update does, across the three preceding subsections, is tie together three rendering rules into one coherent surface that holds across every concept-node-shaped record. The minimalist-most print of §4.1.1 keeps the resting form pure and the interactivity latent in hidden overlay buttons. The plus-signs on the right and bottom of §4.6 grow the singular compute node into a full panel without ever introducing a "promote to panel" affordance. Shift-Enter for multi-line fields lets multi-line content live inside a single field without ever surfacing escaped-newline glyphs in the print form. And these three rules apply identically to every record across every representation — foundation fixtures, scan-spawned chunks, user-created cards, compiled-graph children, and halo phantoms once an apparition click has promoted them (§8.2.2). What the §1.1 Imaginary register calls *seamlessness and distributionality to the imaginary aspect of the agent's computation graph as the very realization of its structure* is what these three rules produce in lockstep across every surface.

### §4.7 Auto-Complete Over Linked Structures (§USER E.5)

> "auto-complete over nodes is structured as such between linked structures within the python-bound object card frameworks" (user, verbatim)

Typing in a new row's `name` field offers completions:

- **Default scope:** all workspace ConceptNode names ranked by `pagerank · nomic_cos(prefix)`.
- **Scoped:** when the editor is inside a python-bound object card (§9.6), completions are restricted to the object's properties/functions and recursively through their `FUNCTION_INPUT_TYPE` / `FUNCTION_OUTPUT_TYPE` linked types (§3.2).

Selecting a completion inserts `{<linked_name>}` into the value; the binding is recorded as a typed `{var}` reference (§7.2).

REST surface: `GET /api/concept_completions?prefix=<>&parent_card_id=<>` returns ranked candidates.

### §4.8 Curly-Brace References Span All Editable Fields (§8D.3, USER C.9)

`{slug-shaped-ref}` resolves on Compile from any editable section (name, description, data, rendering). Cycle-safe recursion (§7.2). Unresolved refs stay literal. Variable auto-creation (§8D.21.1) spawns a fresh empty primitive when the slug doesn't match an existing ConceptNode.

---

## §5 — Concept Authoring Modes (§8A, §8B, §8C unified)

The workspace presents three authoring entry points, all flowing into the same ConceptNode schema (§3) through the same lifecycle (§10.2):

### §5.1 Empty Primitive (§8D.22, USER D.3)

> "Our 2D concept graph compilation editor begins with the base universal primitive 'empty' node. This empty node shows all possible functional links extending from the empty node for the user to select and play around with. As the user types in descriptions and values, these fields are embedded via quantized SLM transformer and retrieval is applied to all nodes in the database, showing optional new functional objects radiating around the primary empty primitive node. Once the first object is created, the retrieval over suggested linked nodes enables the user to quickly link new functional objects and route new signals through the conceptual computation graph." (user, verbatim)

The universal start. `POST /api/concepts` with no name + no description materialises an empty ConceptNode. Typing into description or data fires nomic re-embedding (§8D.17); radiation around the focal surfaces top-K apparitions ranked by the **multi-semantic-frequency-PageRank aggregation** (§8.1.1) over the three canonical fixtures (Agent, WebBrowser, Database — §9.5) plus every materialised ConceptNode in the workspace, including imported python_object trees from the §9.7 library middleware. Selecting one wires it (§5.4) as a hard link on the commitment fan; the unselected candidates remain available on the possibility ring (§3.2.1) until the halo closes.

> "Also, when we begin our concept graph editor with an empty node, we perform pagerank-weighted retrieval over the rest of the saved nodes in our semantic graph database using description and rendered value fields jointly, or just one or the other if one field is empty." (user, verbatim)

The aggregated rank (§8.1.1) is the multi-frequency triple product across token / phrase / paragraph / document / pattern bands, with the per-band weights themselves PageRank-derived. When description is populated and data/rendering is empty, the per-band triple collapses to `pagerank · nomic_cos` at the band-appropriate granularity; when only data/rendering is populated, it collapses to `pagerank · tfidf_cos`; when both are populated, the full triple applies at each band before aggregation. The autonomous agent reads the same radiation surface through `apparition_service.surface_for(empty_id)` (§12.2) — what the agent sees through its perception card is the same multi-frequency aggregation the user sees.

### §5.2 Drag-A-Python-Module (§8D.4.2.6)

The user (or agent) types a qualified name (`backend.services.global_tfidf_store`) into an empty primitive and triggers import. The `PythonAPIMaterialiser` walks `inspect`-derived class structure and produces a read-only Object/Property/Function tree (§9.6). Idempotent by qualified_name.

### §5.3 Click-And-Stick (§4.2)

A 3D chunk's hover billboard → click → pinned panel. The pinned panel **is** the chunk's ConceptNode (with `provenance: derived-from-chunk`). Subsequent edits to the panel flow through the lifecycle the same as any user-authored node (§5.4).

### §5.4 Wiring (`POST /api/concept_edges`)

Drawing an edge calls the same lifecycle. Edge `edge_type` is chosen from §3.2's union. Port bindings live in `source_port`/`target_port` fields (§8D.4.1).

---

## §6 — The 3D Projector (§9)

> **Operational specifics** were historically maintained in [`MORTEGON_INTEGRATION_SCHEME.md`](MORTEGON_INTEGRATION_SCHEME.md) §2/§3/§9/§10, now **superseded** (§O.17): this section + the [`frontend/`](frontend/) suite (`projector.md`, `scan_streaming.md`) are canonical, and Mortegon's additive layout detail (target-sphere fit, hard collider, 1D-radial force) is lifted into §6.1. Consult Mortegon for non-contradictory historical detail only; it no longer "wins" on disagreement.

The projector is the workspace's **TF-IDF chunk manifold**. It shows every chunk the workspace has indexed: scanner-emitted (§9.2) and computation-graph-emitted (§9.12). **Concept cards do not appear in 3D.** The two surfaces are coupled only by click-and-stick (§5.3) and live output projection (§9.12).

### §6.1 Layout Pipeline — UMAP-Linear-Radial Force-Directed Hybrid (§9.3 – §9.7)

The single layout authority. Three states per chunk; transitions are monotone (§9.1):

| State | Owner | Trigger |
|---|---|---|
| **Preliminary radial** | Frontend | Chunk arrives via WS; placed at `hash(chunk_id)` unit-direction from URL root, distance `R · (1 + n/k_radial)` |
| **UMAP-locked canonical** | Backend → frontend | Scan-end UMAP joint fit emits `umap_canonical` (§10.1); frontend tweens chunks to canonical positions over ~600 ms |
| **Radial-slide refined** | Frontend force loop | Newcomer collision violates a locked chunk's neighbourhood; the locked chunk slides along its root-URL ray |

Forbidden: concentric Fibonacci shells, Fibonacci-as-primary placement, hash-direction-as-final.

**Joint 6D UMAP fit (§9.3, §8.2.1.2):** at scan-end, the backend fits UMAP over the *full* TF-IDF index — every chunk from every URL plus every graph-emitted output (§9.12) — producing one **6-vector per chunk**: the first three components are spatial position `(x, y, z)` in the manifold, the last three are colour `(h, s, v)` in HSV space. Position and colour are jointly the UMAP fit, sharing the same neighbour-preservation guarantees; there is no separate colour UMAP. The `umap_canonical` frame carries `workspace_id` + per-chunk integer ids (§9.4) + per-URL roots (§9.5) + the 6-vector per chunk. The renderer applies the HSV components with a phase offset proportional to current camera azimuth so chunk colours rotate slowly in lockstep with the projector orbit (default period 60 seconds; §8.2.1.2 for the full account).

**Bootstrap (transient) colour — the colour analogue of the *Preliminary-radial* position state.** Before the scan-end UMAP fit lands, a chunk has no content-HSV yet, so the frontend bootstraps its fill colour from a **hash of its parent `doc_id`** (a stable per-URL "hue family", saturation/lightness held in a vivid mid-band). This bootstrap is *transient by construction*: the next `umap_canonical` frame overwrites it with the canonical content-HSV (coords[3:6]), exactly as the hash-direction unit-vector position is overwritten by the canonical position (§6.1 table, §2132). The hash-family hue is therefore a **legibility bootstrap, not a colour authority** — the anti-"rainbow-confetti" intent it served is preserved by UMAP itself, since neighbour-preservation gives content-similar chunks (which includes same-`doc_id` siblings sharing vocabulary) similar canonical hues. Provenance tint (§9.12) lerps 25 % toward the provenance signature hue *on top of* the rotating content-HSV every frame, so content identity and provenance are both legible at once. Forbidden as a *final* colour authority: `doc_id`-hash hue, position-derived hue (deriving colour from the `(x,y,z)` channels rather than the `(h,s,v)` channels).

**What is REPL-checkable here vs render-only.** The backend half is fully locked in the REPL: the 6-vector frame format and the HSV channels' `[0,1]` setHSL-readiness are asserted by `env-scenario --name 6d-umap-format` against the real `LayoutService._project`; the frontend's pure colour maths (`umap6ToHsl`, `azimuthToHuePhase`, `applyHuePhase`, `hslToRgb` in `cp/hsv_color.js`) are factored free of THREE/DOM and unit-tested by `node cp/hsv_color.test.mjs`. The *continuous azimuth-locked hue rotation itself* — the per-frame `setHSL(applyHuePhase(h, phase), s, l)` in the `animate()` render loop — is a render-only visual: the Python REPL has no camera, no OrbitControls azimuth, and no `THREE.InstancedMesh`, so it **cannot** observe the rotation, and no scenario claims to. Its correctness rests on the unit-tested purity of the mapping plus the frame-format lock above; visual confirmation is by eye in the browser, which (per the standing directive) is *not* counted as feature proof.

**Hard collider repulsion (§9.7):** zero force above `2·R·safety`, exact-correction-in-one-step below. Single workspace-wide `R_collider` constant shared between image and text billboards.

**UMAP normalization + 1D-radial force (lifted from MORTEGON §2.1–§2.2 as a design feature, §O.17):** the joint fit is post-processed by a **target-sphere fit** — scale uniformly so the farthest chunk sits on a sphere of `TARGET_RADIUS` (default **40 units** — raised from the nominal 25 to resolve the **B.3** "3D spacing too close together" report, together with the collider `2·R·2.2` minimum and a 12-unit inter-URL gap; B.3 outranks the nominal default) — then the **hard Lagrange-style collider pass** above (N iterations of equal pairwise push to `2·R·safety`, no soft tail). The force-directed convergence then reduces to a **1D problem per chunk**: each chunk moves only along the ray `r(t)` from its root-URL position toward its UMAP position (azimuth/elevation fixed once UMAP locks it); pair repulsions are *projected onto each chunk's ray*, so a newcomer is pushed **radially, never tangentially**, and already-locked chunks keep their angular positions across scans.

**Per-URL bounding-radius placement (§9.5):** each URL has its own `root_position`, `bounding_radius`, `umap_locked` set, `hidden` flag, `accessor_dict`. New URL lands at `existing_max_radius + new_radius + safety_gap` in the direction with most empty space. Old URLs never move.

**Perimeter-encompassing agent-output placement (§6.6.1):** chunks whose provenance is `agent-output` are rescaled radially to land on the projector's outer envelope (a thin shell of thickness ~`1.2 · R_collider`) rather than in the manifold interior. Angular position from the UMAP fit is preserved; only the radial coordinate is rescaled. The user reads the manifold interior as observations (scanner-emitted) and the perimeter as syntheses (agent-emitted).

**Stable integer chunk ids (§9.4):** every chunk's id is permanent; TF-IDF, LayoutFrame, frontend `data-3d-node-id`, IndexedDB texture cache all key by it. The LayoutFrame now stores 6-vectors per chunk id (legacy 3-vector storage is a no-longer-permitted format; existing frames are migrated on first load by re-fitting HSV from the TF-IDF index).

### §6.2 Camera (§9.8)

- `minDistance = 0.6 × cluster_radius(orbit_target)` — recomputed per frame.
- `maxDistance = 3 × max(|chunk.position|)` — recomputed per frame.
- Scroll-zoom unrestricted.
- **Frame-on-scan:** camera tweens to new `root_position` at distance `1.8 × bounding_radius` on scan-end; suppressed if `_userHasInteracted == true` AND new root is already in view frustum.
- **Adaptive resize (§USER B.9):** `window.resize` (rAF-coalesced) + `ResizeObserver` on `#projector-panel`; `setSize(w, h, updateStyle=false)`; no no-change guard.

### §6.3 Visibility Model (§9.10)

Visibility is a **flag**, never a mesh mutation. Animate loop reads `workspace.hidden_urls : Set[str]` every frame and writes `scale=0` for every chunk/hub whose URL is hidden. The eye-button toggle (§USER G.3) flips set membership; the mesh's intrinsic scale is never touched. Workspace switching swaps the entire set.

### §6.4 Visibility Spine — Strict Default Collapse-Hidden (§8D.18.1)

> No third path for 3D visibility. Chunks are *either* viewport-visible *or* pinned-panel-referenced *or* hidden.

`chunkCollapseTarget[id] = 0` extrudes; `= 1` folds back into hub. The `IntersectionObserver` on the retrieval result list (§8.3) flips this per row. URL click toggles only that URL's chunks, scoped to viewport when a search is active.

### §6.5 Purge Semantics (§9.11)

`POST /api/purge_workspace { workspace_id, confirm: "erase" }`. Walks every concept, fires `apply_delete_lifecycle` per concept (so individual rollbacks still work), drops the persisted LayoutFrame, resets the `frame_seq` counter, emits one consolidated `purge_workspace` WS frame. The frontend removes every hub, chunk, pinned panel referring to a purged chunk, apparition cache slot, concept-index slot, agent-token buffer, and `frame_seq` high-water mark.

URL × button = same operation scoped to one URL.

### §6.6 The Projector As Comparison Surface (§9.14)

The projector is the **Real register** (§1.1, §1.5) of the workspace — the surface on which sensory measurements (scanner-emitted chunks) and graph emissions (computation outputs) co-exist as geometry. The user and the agent read it as the **auto-correction substrate** for the imaginary register's computations: graph outputs that fall *near* their inputs prove the imaginary preserved the real's structure; outputs that fall *far* prove the imaginary *transformed* the real (which may be desired — summarisation, classification, reformulation — or a bug). The five gestures below are the user's (and agent's) *instruments for reading the dialectic* between Real and Imaginary.

Five gestures the user (and agent) read:

1. **Adjacency reading** — outputs near inputs ⇒ graph is semantically faithful; far ⇒ transformative; scattered ⇒ unstable. The Real ↔ Imaginary feedback loop's *local correctness check*.
2. **Distribution-shape comparison** — provenance filters (§9.12) isolate scanner-emitted vs graph-output; user toggles to see mirror/contract/spread/cluster relationships. The *global correctness check*.
3. **Nearest-input lookup for an output** — hovering a pinned output card surfaces apparition arrows pointing at its nearest projector-neighbours; agreement with the graph's wired inputs ⇒ locally consistent.
4. **Per-sample iteration comparison** — sample stepper (§7.4) animates both 2D cascade and 3D projector; output trajectory through semantic space reveals stability.
5. **Cross-graph time-slicing** — provenance filters by graph and by session timestamp (§11.4); compositional A/B becomes directly readable.

This is the workspace's analytic instrument. No separate analytics surface exists; the projector *is* the surface. In §1.1's framing: every graph-emitted output is *fed back into the real through the imaginary 2D space*, and the projector is where the user observes whether the round-trip closed cleanly.

#### §6.6.1 Agent-Output Perimeter-Encompassing Placement (§1.1 gap-fill)

> "the perimeter-encompassing final outputs of the computation graph (the agent)" (user, verbatim, §1.1)

The agent's *final* outputs (the terminal cards of the agent's computation graph — the cards whose downstream cascade has settled and which carry no further `{var}` forward references) project to the **outer perimeter** of the projector manifold rather than into the manifold interior. The placement contract:

- For each agent-emitted chunk (`provenance: agent-output` per §3.1 + §9.12), the Layout Service computes the chunk's UMAP coords as usual.
- A **perimeter correction** is applied: the radial coordinate of agent-output chunks is rescaled so they land on the convex hull of the URL workspaces' bounding spheres (the projector's outer envelope), preserving angular position from the UMAP fit.
- The perimeter band is a thin shell (configurable thickness, default 1.2 × `R_collider`) where agent-output chunks fan out from the projector centre.
- The visual semantics: the user reads agent outputs at the *edge* of the manifold — these are the *finished* synthesis points; the manifold interior carries the scanner-emitted raw observations the agent's computation began from.

This is the §1.1 framing realised geometrically: the agent's outputs land at the projector's perimeter because they are *the projection from the imaginary back into the real*, and the real's perimeter is the natural locus for the loop's closing return. The user can read at a glance which chunks are *observations* (interior) and which are *synthesis* (perimeter).

#### §6.6.2 2D / 3D Spatial Separation Contract (§1.1 gap-fill)

> "carefully designed conceptual spaces as outputs that are then fed back into the real through the imaginary 2D space that is separate from the 3D space" (user, verbatim, §1.1)

The 2D Concept Editor and the 3D Projector are **spatially separate canvases** that share no coordinate system. The contract:

- **3D coordinates** are workspace-shared metric positions in the projector manifold (§9.4 LayoutFrame: `(x, y, z)`).
- **2D coordinates** are panel screen positions in the editor canvas (§4.2: pinned panel `(top, left, width, height)` in viewport pixels).
- The two coordinate systems **never share state**; the only coupling is via:
  - The **click-and-stick gesture** (§4.2): a 3D node's hover billboard → click → pinned panel that materialises at the *screen rect the hover billboard occupied at click time*. The pin captures a screen rect, not a 3D coord, and the 3D node's continued motion (e.g., from force-directed refinement) drives the `data-3d-node-id` arrow (§7) but does NOT drag the panel.
  - The **live output projection** (§9.12): a 2D output card's chunks project to 3D coords via UMAP and the perimeter-encompassing rule (§6.6.1). This is a one-way Imaginary → Real map; the 3D side does not write back to the 2D panel's coordinates.

Outputs cross from Imaginary to Real **through** the projection step (§9.12) — the 2D panel emits a chunk record that lands in the projector at perimeter coords; the Imaginary space remains separate from the Real space at the canvas level. This is what makes the round-trip *readable* — the user sees the Imaginary's output appear on a different canvas than where they composed it.

#### §6.6.3 Rank-1 in the Imaginary, Full Distribution in the Real — the 2D→3D Focus Coupling (§O.6, §O.7)

The 2D compute graph constrains perception to **rank-1**: a scan node shows the ShadowDOM's base functions/relations plus a `{chunk samples}` reference, not the whole sample set. The **full per-sample chunk distribution lives in the 3D Real** (§9, interior): running a scan streams every sampled chunk into the projector, and the 2D node's `{chunk samples}` is a **reference into that 3D-resident set** (§O.7) — chunks are not duplicated into the 2D data. The coupling during iteration is **one-way, 2D→3D** (§O.6): advancing the 2D per-sample signal (§4.6.1) flies/highlights the corresponding chunk in 3D, so the 2D stepper *drives the 3D focus* while the 3D keeps showing the full distribution. This preserves the §6.6.2 separation (the 2D holds a screen-space reference + a signal index, never 3D coordinates) and realises rank-1 minimalism (§9.6.2, §O): the Imaginary stays minimal and abstract; the Real carries the full empirical spread.

#### §6.6.4 The Computation-Graph Node — Bisector Placement + the Projector Link Network (P.8, P.9, P.10)

A compiled computation graph appears in the **3D projector** as a **single collapsed node**, distinct from the UMAP-embedded chunk cloud. Its placement and links realise the §7.8.4 optimal-transport framing geometrically:

- **Bisector placement (P.10).** The node sits on the **linear bisector** between two *hidden* centroids: (a) the centroid of **all input** nodes' 6D-UMAP coordinates (`xyzhsv`, §6.1), and (b) the **dynamically-updated** centroid of the graph's **output** (perimeter readout, §7.8.2) `xyz` coordinates. Neither centroid is rendered — only the computation-graph node is. As outputs stream in (§7.8.3) the output centroid moves, so the node **slides along the bisector** toward wherever the synthesis currently balances input against output. The node is therefore *literally* positioned on the transport line between the input and output knowledge distributions (§7.8.4).
- **Open/close gesture (P.10).** Clicking the computation-graph node **opens/closes** the computation graph in the 2D editor — the 3D collapsed node is the projector-side handle for the 2D graph. This is the dual of the §6.6.2 click-and-stick: there a 3D *chunk* → 2D *panel*; here a 3D *graph-node* → the 2D *editor graph*.
- **The projector link network (P.8, P.9) — independent of UMAP.** Separate from the UMAP embedding (it carries **no** coordinate state), the projector draws a **node-edge link network** of plain links: **root urls link to their chunk-sample nodes**; the **roots of input nodes** — or **click-sticked 3D nodes** brought into the 2D graph (e.g. urls, §6.6.2) — link to the **computation-graph node**; and **every perimeter output node** (§7.8.2) links to the computation-graph node. So the graph node is the **hub** of a readable forward-inverse circuit (§7.7): inputs (roots/urls) on one side, perimeter readouts on the other, both tied to the single bisector node. This link network is the §6.6.2 separation's **third** coupling channel — alongside click-and-stick and the live output projection (§9.12) — and the transport plan of §7.8.4 made visible.

#### §6.6.5 Generalized Rank-Dominance Collapse/Expand — The 3D Right-Click Gesture (§Q.3, §Q.4, §Q.5)

> "A root url node can be right clicked to collapse its chunk samples in embedding projector space. When the collapse occurs, all other nodes disappear except the url node, which can be right-clicked again to re-expand/unfold its containing structures." (user, verbatim, Q.3)
>
> "...this right click to expand collapse around nodes (with collapsed nodes hidden/temporarily disappeared) is a generalized gesture in 3D gui ... that adheres to rank dominance definitions of collapsing hierarchies through complex computation graphs." (user, verbatim, Q.5)

A **right-click on any dominator node** in the 3D projector — a **root URL doc-hub**, or a compiled **computation-graph bisector node** (§6.6.4) — toggles the **rank-dominance collapse**: the node's **dominated set** (everything it rank-dominates in the concept-edge graph, §8.1.2) folds into the node, and **all nodes outside the collapse's focus are hidden** (`scale=0`, §6.3), leaving the projector showing **only the dominator node**. A second right-click on that node **re-expands**: the dominated set returns to its prior positions and the previously-hidden nodes reappear. The gesture is **symmetric** and **generalized** — the same right-click, on the same kind of structural-dominator target, in either of the two projector node families (UMAP chunk-cloud roots and the UMAP-independent link-network compute nodes, §6.6.4).

**The two concrete cases (Q.3, Q.4):**

| Dominator target | Dominated set that folds | Isolate effect |
|---|---|---|
| **Root URL doc-hub** (Q.3) | that URL's **chunk-sample nodes** (the chunks whose layout root is this URL, §6.1) | every other URL's hub + chunks, and all compute nodes, hide; only the URL hub remains |
| **Compute-graph bisector node** (Q.4, §6.6.4 / P.10) | its **input distribution** (the input-centroid's member nodes) **and** its **output/perimeter-readout distribution** (the output-centroid's member nodes, §7.8.2) | the rest of the manifold hides; only the bisector node remains, the two hidden centroids' members folded into it |

Because the bisector node sits on the linear midpoint between the two *hidden* distribution centroids (the input-output dual-hidden-distribution-centroid linear-midpoint method, P.10), collapsing it folds **both** distributions it bisects — this is exactly the Q.4 requirement that the right-click apply to its **input-output distributions**.

**Rank-dominance is the membership rule (§8.1.2).** "Which nodes disappear" is **not** an ad-hoc per-URL scoping — it is the dominator node's **rank-dominance reachability set** over the one `ConceptEdge` graph (§3.2): the nodes the dominator structurally contains/reaches and that do not have an independent (non-dominated) path to a visible root. A root URL rank-dominates its chunk samples (the `OBJECT_HAS_*` / scan-emission containment edges); a bisector node rank-dominates its input and readout members (the §6.6.4 projector link-network edges). Collapsing hierarchies through **complex** computation graphs (Q.5) follows the same rule recursively: collapsing a dominator that itself contains sub-dominators folds the whole dominated sub-DAG, and re-expansion restores each sub-dominator to its prior fold level (the §8 fold-state-preservation contract, M.6, applied in the Real register).

**Distinct from the §18.12 anti-goal.** §18.12 forbids the *sidebar left-click* from exploding/collapsing nodes non-minimally. The §6.6.5 gesture is a **different gesture on a different surface**: a **right-click directly on the 3D dominator node** that *deliberately* isolates it. The §18.12 left-click still toggles only that URL's chunks scoped to viewport (§6.4); the §6.6.5 right-click is the intentional focus/isolate-and-fold instrument. The two never collide — different button, different surface (sidebar row vs 3D node), different mirror field (`url_collapsed`/`hidden_urls` for the viewport spine vs `dominance_collapse` for the isolate-fold).

**State + REPL mirror.** The collapse is a §10.5 mirror field `dominance_collapse[node_id] = { collapsed: true, hidden_set: [ids], folded_set: [ids], expanded_at }` driven by the `ui-dominance-collapse` / `ui-dominance-expand` gestures (§14.2) hitting `POST /api/ui/dominance_collapse`. Frame `ui_state_changed (kind=dominance_collapse)`; the in-place viewer's `visible 3D` / `hidden 3D` rows (§14.5) reflect the isolate. The gesture is REPL-drivable identically to a frontend right-click (the §14.1 round-trip), and is generalized to 2D in §7.3.5.

### §6.7 Full-Ontology Projection — The DB Ontology In The 3D UMAP GUI (§R.2)

> "Build out a fully functional new set of features that allows for the full database ontology mapped to our 3D umap GUI, which integrates our full set of DB functional-objects and scanned webpage chunk structures." (user, verbatim, R.2)

The projector's Real register carries **two co-resident populations**: the scanned-chunk field (§6.1, TF-IDF-side UMAP) and — per §R.2 — the **full concept ontology**: every ConceptNode in the workspace, including the foundation fixtures (§9.5), the python-native functional-object trees (§9.6), user-authored concepts, and the compiled-from-scans peers. The ontology projects through its **sibling pipeline's** vectors (§2.3: concept-side nomic), never the chunk side's TF-IDF:

- `LayoutService.recompute_ontology` fits the workspace's nomic slot vectors through the same neighbour-preserving 6D embedding the chunk field uses (real UMAP, loud SVD degradation §13.4), sphere-fit onto an **inner shell at 0.6·R** — chunks at the target radius remain the outer comparison surface (§6.6); the ontology is the workspace's *inner structure*. Vectorless concepts ride the §6.1 deterministic hash placeholder until the next recompute.
- Dual-routed (§10.1): `POST /api/ontology/layout` returns AND broadcasts the `ontology_layout` frame — `{coords (6-vectors), names, type_hints, edges, fitted}` — where `edges` is the **coordinate-free one-edge-table adjacency** (§3.2; the §18.34 rule applies: link networks never couple to the UMAP fit).
- The frontend renders a dedicated overlay group (octahedron markers sized by class — fixtures anchor larger, python-native members smaller — HSL from the fit's HSV channels, faint typed links), raycast-pickable as `onto::<concept_id>` so click-and-stick (§5.3) extends to ontology nodes. Refreshes on workspace-open and at scan-end, tracking the chunk field's cadence; purge clears it (§6.5).
- Persistence: `ontology_frame_<ws>.json` beside the layout frames (§11.1), swept for test workspaces by the §R.9 janitor.

REPL mirror: `ontology-layout` action + the `ontology-projection-roundtrip` scenario (asserts every concept gets a 6-vector, fixtures included, plus the WS frame).

---

## §7 — Compilation (§8D.2, §8D.14)

### §7.1 Recursive Syntax-Agnostic Compile (§8D.2)

One recursive descent over the data field. Recognises JSON, bracketed lists, indented trees, HTML element trees, plain text — the user never thinks about syntax. The compile:

1. **Resolve `{var}` refs** in all editable fields (§7.2), cycle-safe.
2. **Decompose top-level keys** into child concept cards keyed by `<panel_id>__<key>`. Parent's data block is rewritten to `{child_key}` placeholders.
3. **Re-substitute** on next Compile press through the children (recursive).
4. **Cypher detection (§8D.2.1)** — `MATCH...RETURN...` or `CALL...` patterns embedded in the data block are extracted, executed against the unified Database (`Database.cypher`), and the typed result substituted in place of the cypher pattern. Combined with `{var}` substitution and recursive decomposition, the data block is a fully programmable graph-aware query expression.
5. **Print** the substituted result to the `rendering` field.

REST surface: `POST /api/conceptual/compile { concept_id, use_slm, persist_rendering }`; `POST /api/conceptual/compile_chain { focal_id, workspace_id, max_depth, use_slm }` (§11.7).

**Realisation roster (the ONE descent, §E.1 + §R.5).** Strategy order — strict JSON → HTML element tree (`parse_html_tree`: content structure only, markup stripped, attributes never projected; repeated sibling tags fold to a list) → non-JSON bracketed list (`parse_bracketed_list`: `[a, b]` / `(a, b)`, quotes guard embedded commas) → §R.5 markdown-gesture outline (`parse_markdown_tree`: dashes, numbering, tabs, newline-with-trailing-text) → native indent `key: value` tree (behind the rank-1 structure gate so prose with a colon passes through) → plain-text passthrough. One detector (`_try_parse_structured`) feeds both the §8D.20 rendering print AND the canonical `decompose_top_level` entries (the same children on every surface — frontend `_decomposeValue` mirrors the order; billboard mirrors derive children from the backend entries). **Decompose splits out the root element's CHILDREN** — the root tag is implicit in the parent card's structural position (§4.5) — so the panel→graph→panel round trip commutes minus exactly one root level (§R.1). REPL hard-verification: the `syntax-agnostic-compile` scenario drives all five syntaxes through `/api/compile_pipeline` against the live stack.

**Compile is lazy reveal-as-it-walks (§O.9).** When the graph contains braced-hidden `{ref}`s (§O.1), compile follows them **on demand as the computation reaches them**, revealing each node in the 2D GUI as it is walked — so running the graph progressively unfolds it, and the reveal mechanic (§7.3.4) and the compile traversal are the *same* walk. This composes with the cascade (§7.4) and the per-sample signal-stream (§4.6.1): each iteration's walk reveals only the nodes that iteration touches, which keeps the visible graph at rank-1 minimalism (§O) even as a deep computation runs underneath.

### §7.2 Dispatch Kinds (§11.7)

`ConceptComputeNode` (`backend/services/conceptual_compute.py`) auto-classifies the data block's `compute_kind`:

| Kind | Behaviour |
|---|---|
| **`plain`** | Tree-print via `compute_rendering_tree` (§8D.20). No SLM. |
| **`prompt`** | Resolve `{slug}` refs in description+prompt; `SLMClient.generate_text`; rendering = response. |
| **`structured`** | Same as `prompt` but with JSON-schema `output_schema`; runtime builds Pydantic model via `build_pydantic_model_from_schema`; SLM fills it; validation failure surfaces as `{_validation_error, _raw}` envelope. |
| **`python`** | Data block declares `"python_entry": "module:callable"` + `inputs`; callable is dynamic-imported and invoked; rendering = return value. |

Dispatch result is written back through `apply_update_lifecycle` (§10.2) so peer tabs see the rendering, evolution log records it, cascade scheduler is informed.

**Pydantic templates in the minimalist text pattern (§O.20).** The `structured` kind's `output_schema` is **not authored as raw JSON schema** — it is exposed as the same **pure-print field-tree** (§4.6) the rest of the editor uses: field/variable names are inferred from the tree, `{var}` references carry content, and Tab / Shift-Enter markdown handlers (§4.1.1, N.12) build the multiline structure. **Agent outputs are processed downstream via these templates:** the *consuming* node's input panel carries the pydantic template, so the agent's `Agent.output(schema=…)` (§9.5.1) is validated and shaped by the template the downstream node already holds, and structured chunk samples from the scanner (§15.8) flow into the same templated fields. A singular such panel compiles intelligently into computation-graph form (§7.3.4).

### §7.3 Right-Click Compile/Collapse Toggle (§8D.2.2)

> "When right clicked again, they fold back into the original knowledge panel with the collapsed, latchable sliding hidden data block and the remaining three fields displayed normally." (user, verbatim)
>
> "Concept graph computation nodes should mimic the same hover/click to expand both graph links + details + apparitions in the fused gestures." (user, verbatim)

A **double-left-click** on a panel's body (not a textarea) toggles between two views — and the toggle is itself the design's **dialectical inversion** between two representations of the same ConceptNode record (the firing gesture moved from right-click to double-left-click in the M.7 update; right-click is now the inline next-rank type-graph fold of §7.3.4, and the REPL actions `ui-compile-expand`/`ui-compile-collapse` are unchanged — only the gesture that fires them moved):

| View | Imaginary mode | What it shows | Synthesis vs analysis |
|---|---|---|---|
| **Panel** (folded) | Knowledge synthesis | Name + description + rendering (collapsed; latched data) in one unified panel (§4) | **Synthesis** — the node as a single semantic unit |
| **Subgraph** (unfolded) | Knowledge analysis | Central node + one child per top-level data key (or per `{var}` reference), each child = single `name : value` simplified card with stringless edges | **Analysis** — the node as its decomposed structural skeleton |

- **Panel state → expand:** central panel becomes the central node of a simplified subgraph (§7.3.1); children spawned at `<panel_id>__<key>`. The data block's `{var}` references AND its top-level structure both materialise as edges/children simultaneously.
- **Subgraph state → collapse:** children dissolve; central panel restores. The underlying ConceptNode is untouched.

> "Remember that right-clicking either one compiles the structure into the other representation." (user, verbatim, §1.1)

The toggle's symmetry is the design contract — each double-left-click on the central panel-or-node flips between *synthesis* and *analysis* of the same record. This is the §1.1 Imaginary register's primary structural gesture: the user (and the agent) reads either the *whole* (panel) or the *parts* (subgraph) of the same imagery on demand, without ever touching the underlying record. The compiled subgraph's children carry the same hover/click/apparition affordances the original panel does (§4) — a hover on a compiled child surfaces apparitions ranked against that child's concept, a click pins the child as its own panel via the freeze-at-rect mechanic (§4.2), a double-left-click on a child re-enters the dialectic at that level, and a right-click on a child folds/unfolds that child's inline next-rank type-graph subtree (§7.3.4).

**Simplified back-propagated representation (§8D.2.2.1):**

- Each child shows **only its value** (`name` is implicit from structural position).
- Form-fit to the value's longest line and line-count.
- **Stringless edges** — plain lines, no per-edge text labels.
- **`{var}` propagation to leaves** — chains resolve until a literal leaf value is reached.
- **One-level graph form; recursive panel-form fold** — in compiled *graph* form the simplified children are one level deep, with deeper structure reached by graph-space right-click fold (§7.3.4; the M.7 "similar folding over right click properties... in graph space"). In *panel* form, the inline next-rank type-graph fold (§7.3.4) is instead **recursive to arbitrary depth, rank by rank** (superclass → properties → function I/O → reference targets), superseding the old one-level policy for panel exploration.

**Layout (§8D.2.2.2):** ray-constrained placement around the focal card per §8D.10 — same algorithm for small and large subgraphs. No predicted-overlap branching. The 2D ray-constraint is the **planar analogue of §6.1** (lifted from MORTEGON §6.4 as a design feature, §O.17): a **2D UMAP of the cards' nomic vectors recentred on the focal** sets each card's azimuth, and each card's *only* degree of freedom is its radial distance along the focal→UMAP ray; force-directed adjustment pushes overlapping cards apart **along their rays, never tangentially**. (The forbidden `_fibonacciPosition` concentric-ring placement is removed; the hash-direction angular seed is the only transient, §6.1.)

**Read-only variant (§8D.2.2.3):** when the central panel is a python-native node (§9.6), children render desaturated + 🔒; values non-editable; **double-left-click compile and right-click inline fold (§7.3.4) still work** — exploration is always permitted on read-only nodes, only editing is refused (§4.1.1).

#### §7.3.4 Refined Panel Gesture Model + Inline Next-Rank Type-Graph Fold (M.3–M.8)

The typed panel form (§9.6.1) is explored through five non-colliding gestures; this subsection reconciles them so the right-click is freed for granular exploration and the panel↔graph compile moves to double-left-click:

| Gesture | Target | Effect |
|---|---|---|
| **Hover** | a typed field / `{token}` (within its mini-card box bounds) | *preview* the next-rank expansion transiently (M.3/M.4) |
| **Single left-click** | a token (key / strict type / value) | *edit* it as a blended, borderless, cursor-blinking field — a smoothed text editor with no per-token chrome (M.8; §4.1.1) |
| **Right-click** | a token (key / strict type / value, base or reference form) | *toggle expand/collapse* over the token's **rank-1 links**, **inline in the knowledge-panel form** (folding is a panel mechanic, not a graph one — review clarification §O), preserving per-subtree fold state across toggles (M.6) |
| **Right-click** | the base / self node | *collapse the whole panel to the singular self node*; re-expand restores the prior fold state (M.6) |
| **Double left-click** | the panel body / base node — or, in graph form, a graph node | *panel → computation-graph form*, and *graph node → its containment panel*; the panel↔graph toggle is **symmetric in both representations** (M.7, this update) |
| **Left-click-drag** (graph form) | from one node to another | *wire a link*; the target **inherits the source's input-output types and object models** (N.4) and duplicate-instantiates the source as a rank-1 component (§9.6.2) |
| **Double-right-click** | a token reference / instance in rendered print | *delete* that abstractly-structured token reference or instance, in either panel or graph form (N.13) |

The **next-rank type graph** is any-and-all links off a node (M.5/M.6): superclass (`super:BaseWebDriver`), property (the class's typed attributes — properties are themselves modules, §9.6.1), function I/O (a function node expands to its typed input fields plus its inferred output-structure field, M.5), and `{var}` reference targets. Right-click collapses/expands over **rank-1 links** to the directly-linked nodes **in the knowledge-panel form** — recursively chunking the abstract syntax tree (M.3) one rank at a time, to arbitrary depth, each fold/unfold preserving the fold levels of its subtrees (M.6). The braces `{…}` are the panel's **fold marker** (§O.2): a folded reference shows `{name}`, and unfolding drops the braces and indents its rank-1 children. **The brace-reveal works in both forms (§O.1):** in **computation-graph form** the same braces mark nodes whose rank-1 links aren't all visible — **hover previews** them and a **click instantiates the rank-1 walk** as new visible nodes joined by **undirected line links**. Graph form has no *independent* fold state; it stays in **node-count parity** with the panel (revealing in one reveals in both). A `{ref}` to an already-visible node resolves to a **solid link**; a `{ref}` to a still-hidden node keeps its braces — the three brace states of §O.1a (braced-hidden / revealed-internal / resolved-external), the underlying graph edge identical in all three.

REPL-mirrored gestures (§14.2): `ui-node-expand { card_id, node_path }` / `ui-node-collapse { card_id, node_path }` toggle the inline fold (frame `ui_state_changed (kind=node_fold)`; mirror `node_fold_state[card_id] = { expanded_paths: [...] }`; base-node collapse is `ui-node-collapse` on the root path). The panel↔graph compile keeps `ui-compile-expand`/`ui-compile-collapse` but is now fired by double-left-click. **Left-click-drag** in graph form fires `concept-edge-create` (§5.4) carrying the source's I/O + object-model inheritance (N.4, §9.6.2); **double-right-click** fires `editor-delete` (§9.5.1) scoped to the token reference/instance under the cursor (N.13). The fold-state-preservation contract is guarded by §18.32. The full interaction-mechanics specification — with the canonical ASCII renderings — is `docs/frontend/object_exploration.md`.

#### §7.3.5 The Rank-Dominance Collapse Generalized Across 2D and 3D (§Q.5)

> "...a generalized gesture in 3D gui (as well as 2D, which also may or may not be implemented from the docs... check for this)..." (user, verbatim, Q.5)

**Is the collapse already in the 2D docs? — Partly.** The 2D editor already carries *two* dominance-collapse mechanics, but neither was previously named as the *same* generalized gesture as the 3D one:

1. **Right-click-on-self → collapse-to-self (§7.3.4, M.6).** Right-clicking the base/self node collapses the entire panel to its singular self node, retaining the full fold tree; re-expand restores it. This **is** a rank-dominance collapse in the Imaginary register — the self node rank-dominates its whole field-tree, and collapse-to-self folds exactly that dominated set, in panel form.
2. **Compute-graph node fold in graph form (§7.3.3 / §7.3.4, M.7).** In computation-**graph** form, a graph node's rank-1 links are reachable by hover-preview + click, and "similar folding over right-click properties... in graph space" folds them — node-count parity with the panel.

**The unification (Q.5).** §6.6.5 (Real) and the two mechanics above (Imaginary) are **one generalized gesture** — *right-click a dominator → fold its rank-dominance set; right-click again → unfold* — expressed in three renderings of the same invariant `ConceptEdge` graph:

| Register / form | Dominator | Dominated set folded | Visibility of non-dominated nodes |
|---|---|---|---|
| **3D projector** (§6.6.5) | root URL hub · bisector compute node | chunk samples · input+output distributions | **hidden** (`scale=0`) — the isolate |
| **2D panel form** (§7.3.4) | self node · any token with rank-1 links | the field-tree subtree under it | unaffected (panel is already the focus) |
| **2D graph form** (§7.3.4, §6.6.4) | a graph node | its rank-1 linked child nodes | other graph nodes stay; fold is local |

The **membership rule is identical** in all three — the dominator's rank-dominance reachability set over the one edge graph (§8.1.2) — and **fold-state is preserved** across collapse/re-expand in all three (M.6, §8 of `object_exploration.md`). The only difference is the **non-dominated-node visibility policy**: the 3D projector *isolates* (hides everything else, because the manifold is a shared spatial canvas where focus means clearing the field, Q.3); the 2D panel/graph forms leave siblings in place (the editor canvas already scopes attention to the focal). This visibility difference is a **rendering choice over one invariant gesture**, exactly as the brace-state distinctions of §O.1a are rendering choices over one invariant graph edge. The 2D↔3D round-trip stays faithful because both drive the **same** `dominance_collapse` mirror family (§6.6.5) keyed by node id; a REPL `ui-dominance-collapse` folds in every open surface that renders that node.

### §7.4 Live Debounced Cascade (§8D.14, §8D.38.4)

> Compilation is **continuous downstream** of user edits, agent emissions, scanner deliveries. The Compile button is an affordance for forced sync, not the primary trigger.

Edit a card → re-embed → downstream cards referencing it via `{ref}` re-compile → their renderings update → their own `{ref}`-consumers re-fire. **Realized (§8D.38.4):** this downstream `{ref}`-recompile runs **synchronously** inside the edit's `apply_update_lifecycle` — a cycle-safe BFS (visited-set + depth cap), not a timer; its storm guard is the visited-set + the `conceptual_compute`/`cascade*` actor-exclusion. The ~800 ms debounce that collapses bursts applies to the **agent-tick** path (`CascadeScheduler`), which the design originally generalised to all cards. (`code_architecture/backend/lifecycle.md` §3.2 · `code_specs/backend/lifecycle.md` §3.)

**Actor-aware short-circuit (§2.7):** the scheduler tags each re-fire with `actor=user|agent:<id>|cascade`; an agent's emission won't re-trigger its own perception in the same cascade tick (prevents tight self-loops).

**The background cascade stays within the revealed frontier (§O.13).** A cascade re-fire recomputes downstream *values* but does **not** auto-unfold hidden `{ref}`s — only an explicit play/compile walk reveals nodes as it goes (§O.9). The visible graph therefore stays at the user's chosen rank-1 depth even under continuous cascade, preserving rank-1 minimalism (§N.14): the user sees recomputed renderings on already-visible nodes, not a graph that grows itself.

### §7.5 Play/Pause Iterated Rollout Editing (§USER E.7, §8D.13)

> "pressing 'play/pause' can enable the user to edit the computation graph at various phases of the rollout when selecting different nodes within it to edit and either add or update data structures (including computation graph/knowledge template rendering scheme addition, modification, variable referencing and linking in multiline string fields as normal)." (user, verbatim)

A sample stepper iterates the compile over N sampled chunks (or inputs). At any iteration the user presses **Pause** → edit any node (name, value, plus-sign children) → press **Play** → next iteration uses the edited node's new content. Selecting a different node localises edit context to that node's sample of the rollout.

REST surface: `POST /api/rollout/play`, `POST /api/rollout/pause`, `POST /api/rollout/step`. WS frame `rollout_paused { sample_idx, current_node_id }`. The agent operates the rollout through the same surface (§12).

**Pause freezes at the walk frontier (§O.10).** Because compile is lazy reveal-as-it-walks (§O.9), Pause keeps the nodes revealed so far visible at rank-1, shows the current per-sample signal, and lets the user edit any revealed node; Resume continues the walk + iteration from there (diff-consistent per §7.6). **Per-sample iteration uses one readout node that cycles the signal (§O.11):** a function iterating over `{chunk samples}` shows the current sample's output in a *single* readout node (§4.6.1), while the per-sample outputs accumulate as the full distribution in 3D (§O.7) and the 2D stays rank-1.

### §7.6 Recursive Chunking + Diff-Consistent State (§USER E.8, §E.9, §8D.9)

> "The idea would be for the computation graph to abstract from the data itself by applying recursive chunking over large outputs like DOM scans, where chunks are standardized as knowledge object types as a downstream task for an SLM." (user, verbatim)
>
> "We ensure our state is diff-consistent such that when we roll back our recursion computation to a new sample in an early node, we re-localize our context to support recursion over that one computation node for all computation nodes. This would mean that the recursion in references comes from multiple samples being drawn from the same generalized-forward-truncated bank of xpath patterns in our scanned shadow DOM, where we apply 'context-aware' yield sampling from re-rendered templates for the full computation graph unrolling." (user, verbatim)

Outputs that exceed a chunk size are recursively chunked; each chunk becomes a downstream input the SLM can process. Compose over chunks, not raw payloads.

**Diff-consistent state.** Rolling back the rollout to an early sample re-localises the entire downstream context (§8D.9). Sample iteration draws from a generalised-forward-truncated bank of xpath patterns; context-aware yield sampling re-renders the templates per sample. The evolution log (§11.4) records every sample boundary so rollback (§2.6) restores both the data state and the iteration index together.

### §7.7 Closest-Inverse Lookup (§8D.7)

> "the 'inverse' on our concept cards automatically applies, because the compilation applies both forward function call and the inverse closest lookup." (user, verbatim)
>
> "if we have a function that takes input variables and compile the graph, the function node calls forward and outputs its own types (which are inferred upon output to be the object model of the output). Then, if/when we compile our graph with functional nodes, where we assign a concept node/graph to the output but not the input, we use a closest-inverse lookup to find the closest/most related set of input nodes." (user, verbatim)

A function-card with output wired but input unwired triggers an **inverse** retrieval automatically as part of every Compile:

1. Search persistent store for cards whose type matches the function's input parameter annotation.
2. For each candidate, embed (input, function metadata) into the same space the output embeds into.
3. Rank by `cos_sim(predicted_output_for_candidate, observed_output)` and surface the top match.

User accepts → wires the input; rejects → next candidate; refines → re-runs with sharper target description.

Generalisation: **bidirectionality is a link-level property**. Every edge in §3.2 supports forward execution and inverse retrieval; the inverse uses the same `pagerank · tfidf_cos · nomic_cos` triple product (§8.1). Property edges import value forward (parent property → child slot) and infer source backward (child observed value → which parent property could supply it). Method edges fire forward (call method → produce output) and inverse-retrieve backward (observed output → which method+inputs produced it). Compilation applies both directions in one pass.

**The Imaginary's projective property** (§1.1 gap-fill). In §1.1's framing the forward-inverse-lookup is the *purely projective* property of functional links — the function's structure is *projection through conceptual computation graphs*. The closest-inverse is therefore not a special mechanism; it is the *imaginary's projective inverse* — the same projection that runs forward (input → output) is read backward (output → closest input). The two directions are *the same projection*, just observed at different ends. This is why the inverse is *automatic*: there is no "reverse mode" to activate; the projective structure is bidirectional by its nature, and the editor surfaces both readings.

**The recorded state space (§R.6).** The inverse is **two-tier**: every forward application (any `ConceptComputeNode` dispatch — template, prompt, structured, python) **persists** its consumed `{ref}` inputs → output as `FORWARD_MAPPED_TO` ConceptEdges (one-edge-table §3.2; idempotent on the natural five-tuple so cascade re-fires never grow the space; the dispatch's function identity rides `variable_name`). `closest_inverse` consults the **recorded mappings first** — ground truth, `provenance="recorded-mapping"`, ranked above any cosine — and the nomic triple-product generalisation fills the unmapped remainder. The full recorded space is queryable per node: `GET /api/inverse_map/{id}` returns `as_output` (every recorded forward call INTO the node — the exact inverse) and `as_input` (everywhere its value has flowed forward). This is the §R.6 "forward-call inverse-lookup functional maps that reflect their full state space of mappings in the database", and the curly-brace external-memory references (§4.8) are what mint the inputs the map records. REPL: `inverse-map` action + the `inverse-map-state-space` scenario.

### §7.8 The Compute Graph as Reservoir Computer with Generative Readout (M.1)

> "Our 3D map is our world-distribution from sources like shadow DOM scans and the peripheral generated outputs of our final output layers of the computation graph. Then, our computation graph becomes a reservoir computer with a generative readout property. The perceptions that are provided to the reservoir are then mapped to a readout of the reservoir dynamics in strict-typed data structures that are inlaid with the way in which we parse conceptual computation graphs within our 2D ui editor." (user, verbatim, M.1)

The whole compute model reads as a **reservoir computer** (RC) — the unifying frame for §6.6 (the comparison surface), §7.4 (the cascade), and §12.2.1 (the recursion-over-iteration integration scheme):

- **Input — the perceptions / driving signal.** The Real register's world-distribution (§6.6, §9): every shadow-DOM scan chunk (§15) plus the *peripheral generated outputs of the graph's final layers* (the agent's perimeter-encompassing outputs, §6.6.1). These perceptions drive the reservoir; in the §12.2.1 framing they are the integration scheme's *initial conditions*.
- **Reservoir — the fixed high-dimensional nonlinear substrate.** The materialised typed concept-graph: the three fixtures + library trees (§9.6/§9.7) as the object-model substrate, together with the world-perception manifold, driven into a high-dimensional state by the perceptions through the recursive cascade (§7.4). The substrate's couplings (the typed module/property/function/inheritance edges of §9.6.1) are largely fixed — the user/agent *drives and reads* them rather than retraining them.
- **Generative readout — the only authored/trained layer.** The strict-typed data structures the user/agent compose as compute-knowledge-panels, whose values are produced *generatively* (real GPT4All, §13, via langgraph+pydantic templates, M.9) and whose **structure is inlaid with the 2D editor's parse** (§7.3.4, §9.6.1) — the readout *is* a typed recursive field-tree. The "generative readout property" is that the readout generates, rather than merely linearly combines, the reservoir's driven state, resolving the reservoir's continuous distributional dynamics into the discrete, referenceable, editable concept-graph the §7.3.4 gestures explore.

The closest-inverse (§7.7) is this readout read backward: the same projection that maps reservoir-state → typed output is read output → closest reservoir-driving input. The strict typing of the readout is precisely what lets a continuous reservoir dynamics resolve to an editable object model (§9.6.1) — the readout's type slots are the discretisation of the reservoir's state into the field-tree the editor renders.

**The readout lives as a 2D rank-1 node + a 3D distribution (§O.12).** The generative readout materialises as a *type-stripped* node in the 2D graph holding the current output, while the per-sample (and agent) outputs land in the 3D Real — agent outputs on the perimeter (§6.6.1) — and the 2D `{output}` is a reference into that 3D-resident set (mirroring §O.7). So the readout obeys the same rank-1-here / full-distribution-there split (§6.6.3) as the scan inputs: the Imaginary holds the abstract current value; the Real holds the empirical spread.

#### §7.8.1 The driving signal — inverse lookups over generalized chunk samples (P.1, P.2)

The reservoir's input (§7.8) is not raw chunks but **manifold structured data inputs** assembled by **inverse lookups over generalized chunk samples**. A scan's xpath chunk patterns (§15.8) are the *generalized* sample family; the compute graph's input nodes resolve their `{ref}`s by the **forward-inverse projection** (§7.7) — a function/field's output *type* is matched (inverse) against the pattern-linked chunk samples that satisfy it, so an input field typed `KnownOutputStructure` pulls, by inverse lookup, the generalized chunk samples whose pattern produces that structure. The links are **real functional-object links** (§9.6.1) — module / property / function / inheritance edges, not string matches. The cascade (§7.4) then drives these inputs through the graph as **cascaded render-compile chains**: each `{ref}`-consumer re-renders and re-compiles as its upstream sample advances (§4.6.1), recursively-iteratively over the manifold of samples.

#### §7.8.2 The rollout — cascaded render-compile to the readout nodes (P.3)

A **full rollout** is the recursive-iterative unfolding of the graph from inputs to its **readout nodes**: the *final-most recursive unfolded nodes* — the cards whose downstream cascade has settled and which carry no further forward `{ref}` (the §6.6.1 terminal-output criterion). The readout nodes form the **perimeter** — the *spherical (hyper)surface of input-output rendered panels* — of the rollout. This is the reservoir's **generative readout** (§7.8) materialised as the rollout's outer shell: the interior nodes are the **hidden state** (intermediate mappings), the perimeter is what the user reads.

#### §7.8.3 Asynchronous perimeter sampling + delta-streaming to the projector (P.4, P.6, P.7)

Because subgraphs have **differing rollout path lengths** — and **recurrent maps** fold the perimeter back onto hidden-state nodes of intermediate mappings — perimeter outputs settle at **different times** ("compute-graph-operation time relativity"). The perimeter is therefore sampled **asynchronously**: each readout node, when its value settles for the current sample, is **rendered and sent to the projector stream as a delta update** to the projector's network map (§10.2 streaming; a per-node delta, never a full re-fit). In the projector these readout nodes land at perimeter coords (§6.6.1) and, in **passive state** (no image billboard), animate by **physical + colour (HSV) rotation** from the 4–6 UMAP dims (§6.1 / §8.2.1.2) — the rotation is how a type-only readout node shows liveness without a billboard. Asynchrony is a first-class property: the watch-activity dashboard (§14.5) and the WS sequencing (§10.2) must tolerate readouts arriving out of rollout-order.

**Peripheral-only output projection — readouts ship as rendered panels (§R.4).** What reaches the projector is the **perimeter only**: each readout delta (and the snapshot overlay's readout payload) carries the node's `name` + its settled `rendering` — the §8D.20 clean-text tree — capped for the wire, and the 3D mirror renders it as a **panel** (the unified-panel idiom at its most compact, §4.5/§18.11: a screen-anchored mini-panel reprojected per frame), seated at its perimeter coordinate, its chunk seat, or a deterministic fan around the bisector node. **Hidden-state nodes never project** — the `readout_nodes` terminal criterion ("no in-component node references it" = §R.4's "no succeeding links") is enforced server-side, so interior values can only be reached by opening the 2D graph. REPL: the `readout-panel-projection` scenario asserts the perimeter-only rule + the panel payload.

#### §7.8.4 The whole graph as an iterated information-space procedural renderer; the optimal-transport dialectic (P.5, P.11)

Read end to end, the **forward-inverse integrated graph query + function calls** (§7.7) are an **iterated information-space procedural rendering scheme** for **partially recurrent mappings between iterated input samples** — running all the way to the **output knowledge-panel ⇄ computation-graph dialectic** (§7.3.4), which **procedurally renders the final output datatypes given the array of iterable inputs**. The dialectic representation is an **optimal transport between semantically complex yet linked knowledge**: the compute-graph node (§6.6.4) sits on the transport line between the input distribution's centroid and the output distribution's centroid, and the renderer **recurrently evolves over the input information and its own recurrent hidden-state representations** — i.e. a reservoir (§7.8) whose readout is *generated*, not linearly combined. "Procedural" is exact: the output is not stored, it is *re-rendered each rollout* from the inputs through the (largely fixed, §7.8) reservoir couplings.

#### §7.8.5 Hidden state vs readout perimeter; the advancing abstraction front (P.12)

During **iterative construction** the user builds and tests **smaller computation graphs** and reads their **perimeter** (the utmost abstractive layer) directly; the **hidden-state** interior and the **readout perimeter** are **smoothly differentiated** — there is no hard type boundary, only "is this node currently terminal (no forward `{ref}`)?". As the user **adds complexity**, the **abstraction front** — the reservoir's readout perimeter — **advances outward past** the intermediate nodes that were previously terminal: yesterday's readout becomes today's hidden state. This is the §6.6.3 rank-1-here / full-distribution-there split made *dynamic* — the perimeter is wherever the user has currently stopped unfolding, and it migrates as the graph grows, which is exactly why the projector's perimeter placement (§6.6.1) and the bisector node's output centroid (§6.6.4) are **dynamically** recomputed rather than fixed at compile time.

---

## §8 — Retrieval, Apparitions, and the Halo

> **Perceptions are retrieval patterns (§1.1 Imaginary).** Every observation the workspace makes — a scan-emitted chunk, a user keystroke, an agent emission — enters retrieval as a *semantic-graph-retrieval pattern* the moment it lands. The unified interface (§4 panel) means there is no "raw data" phase that precedes retrieval; the moment a chunk materialises it is indexed (§10.3 TF-IDF + §10.4 nomic) and a focal halo is one user gesture away. This is the §1.1 Imaginary register's foundational identity: *perception = retrieval pattern*.

### §8.1 Triple-Product Apparition Scoring + Multi-Semantic-Frequency-PageRank (§8D.43; §1.2.2)

Retrieval rank everywhere is the **triple product**:

```
score(candidate, focal) = pagerank(candidate) · tfidf_cos(focal.rendering, candidate.rendering) · nomic_cos(focal.description, candidate.description)
```

The **two embedding axes never mix** (§8D.17.1): descriptions go to nomic, renderings go to TF-IDF. The 3D projector only ever sees TF-IDF. PageRank operates on the concept graph.

**Knowledge-panel retrieval deviates; the search space blends data and computation (§O.22).** Knowledge panels are far more dynamically structured than scan chunks, so for *panels* the strict axis separation above is **excepted**: a panel partition is embedded by running **both** the quantized (nomic) **and** TF-IDF models over the **same rendered panel chunk** (following the iterable-recursion sampling rules, §4.6.1 / §O.20), and its retrieval score is `pagerank · max(minmax(nomic_cos), minmax(tfidf_cos))` — the **max** of the two cosine similarities, **each min-max normalized to [0, 1] over its own space** (raw cosine spaces at their independent scales can be biased, so both are normalized *before* the max), linked to the third (PageRank) metric. (Scan *chunks* keep the separated axes above; the same-render / max-combine rule is specifically for the dynamically-structured panels.) Which partition is embedded reflects the panel's **internal memory** — which fields are externally `{ref}`-referenced (functions) vs explicitly rendered as rank-1 steps inline (§O.19) — and the computation graph stays **isomorphic to the knowledge-panel containment bounds** (§7.3.4): one graph node ≅ one panel partition. The **dynamic embeddings of all panels** in the compute-graph context — including iterable chunks, functional-objects, and whole computation **subgraphs** — sit in the **same** halo embedding-search set as data chunks, so a halo can surface similar *computational tasks*, not only similar data: a specialized research-agent subgraph (its panel rendered + vectorized) is retrievable by similarity exactly as a chunk is. **Search over data space seamlessly blends with search over the space of computational tasks.**

#### §8.1.1 Multi-Semantic-Frequency-PageRank (§1.2.2)

The triple product (§8.1) evaluated at **a single semantic frequency** ranks only the focal-to-candidate alignment at the chunk-or-card granularity. The §1.2.2 update generalises retrieval to **multi-semantic-frequency**: the same triple product is evaluated at multiple semantic scales — *token*, *phrase*, *paragraph*, *document* (and, for the chunk-pattern variant, *pattern* / *sub-pattern* / *full-tree*) — and the per-frequency scores are combined into a single rank via PageRank-weighted aggregation across frequency bands.

The realisation:

| Frequency band | TF-IDF granularity | Nomic granularity | PageRank source |
|---|---|---|---|
| **Token** | per-token IDF (raw vocab) | n/a (nomic operates phrase-and-above) | per-token co-occurrence graph |
| **Phrase** | 2-5 gram TF-IDF | nomic over phrase chunks | phrase-level neighbour graph |
| **Paragraph** | per-paragraph TF-IDF (current default) | nomic over paragraph descriptions (current default) | concept-edge PageRank (§8.1) |
| **Document** | per-doc TF-IDF | nomic over doc-aggregated rendering | URL-level co-citation graph |
| **Pattern** (§15.8) | per-chunk-pattern TF-IDF | nomic over pattern descriptions | golden-trio + accessor-table neighbour graph |

The aggregated rank is `Σ_f w_f · triple_product_at_frequency(f)` where the weights `w_f` are themselves PageRank scores over the **semantic-frequency band graph** (high-frequency bands like token contribute when low-frequency context is ambiguous; low-frequency bands like document contribute when high-frequency context is uninformative). The weights are auto-tuned per-workspace from the observed-utility feedback recorded in the evolution log (§11.4) — a click-promotion of a soft→hard link credits the frequency bands that ranked the chosen candidate highest.

The single-frequency triple product (§8.1) is the default for new workspaces; multi-frequency aggregation activates once the workspace has accumulated ≥ K observed-utility events (default K = 32, configurable per workspace). The two retrieval surfaces are **interchangeable at the API level** — `apparition_service.surface_for(card_id)` returns the aggregated rank regardless of whether the workspace is in single- or multi-frequency mode.

#### §8.1.2 Rank-Dominance vs PageRank — Same Graph, Distinct Measures (§Q.6)

> "I think this is the same sort of measure or indexing over structures that is used in our pagerank term of our generalized retrieval tool for halos and db search, but I can't be too sure... so please check for that as well." (user, verbatim, Q.6)

**Checked. They are computed over the *same* graph but are *distinct* measures — aligned, not identical.**

Both run over the **one** `ConceptEdge` graph (the one-edge-table invariant, §3.2; "PageRank operates on the concept graph", §8.1). But they answer different questions:

| Measure | Question | Computation | Where used |
|---|---|---|---|
| **PageRank** | *How central / important is this node?* | stationary distribution of a damped random walk over all edges (`PAGERANK_DAMPING`, power-iteration, O(E)) — a **spectral/flow** centrality, a scalar per node | the **multiplicative weight** in the retrieval triple product (§8.1) and the multi-frequency aggregation (§8.1.1); halos + DB search |
| **Rank-dominance** | *What does this node structurally contain / dominate?* | the **dominator/reachability set** over the containment+compute DAG — a **set** per node (the descendants it dominates), a partial order, not a scalar | the **membership rule** for the collapse/expand gesture (§6.6.5, §7.3.5): which nodes fold and (in 3D) hide |

**The alignment (why the user's intuition is partly right).** A node's PageRank and its rank-dominance set are **positively correlated**: a dominator (a root URL, a bisector compute node) accumulates high PageRank *precisely because* it dominates many nodes — the in/out edges to its dominated set are what concentrate random-walk mass on it. So the two co-vary, and the design **uses PageRank as the collapse-onto heuristic**: when a right-click lands ambiguously (e.g. near several candidate roots), the **highest-PageRank dominator** in the neighbourhood is chosen as the collapse root, because the most-central node is almost always the structural dominator the user means to fold onto. This is the same "indexing over structures" the user sensed — PageRank *indexes which structures are the hubs worth collapsing onto*.

**The distinction (why they are not the same term).** PageRank cannot, by itself, tell you *which* nodes disappear on collapse — a scalar centrality has no containment semantics. The **dominated-set reachability** does that. So: **PageRank picks the dominator (the hub to fold onto); rank-dominance defines the membership (what folds and hides).** Both read the one edge graph; neither is the other. (Implementation note: rank-dominance reuses the same Kuzu edge traversal that feeds PageRank — `concept_index_service.py` — so there is no second graph and no second edge table, honouring §3.2.)

### §8.2 Apparition Halo — Name-Only Compact Standard (§USER D.1)

The halo phantom carries the candidate's **name only**. No score chips, no description preview, no rendering excerpt. Scores live in a slow-hover tooltip (rendered from `title` attribute or equivalent).

Halo radiates from **any focal panel**, not just the empty primitive: empty primitive, user-authored card, compiled-graph child (§7.3), python-native function. Backend: `apparition_service.surface_for(card_id)` returns top-K candidates; frontend renders one collapsed-panel-form phantom per candidate around the focal (§4.3).

#### §8.2.1 Concentric-Circle Radiation and the 6D UMAP Ray-Projection (§1.1, §1.2.2 — Imaginary)

The §1.1 phrasing of the halo says it best, so it's worth keeping the user's voice at hand: *"a halo of retrieved data is shown as a radiating concentric circle away from the base retrieval node depending on normalized similarity to preserve scale-space boundaries at the periphery of the retrieval space and express the polar-coordinate proximality in this way."* The halo is, then, polar coordinates around the focal panel's centre — the candidates fan out angularly by the direction of their nomic embedding relative to the focal's, and they sit at radial distances determined by how strongly they retrieved (the closer a candidate ranked to the top, the smaller its radial distance from the focal). What we get is a distributional substance radiating from the focal: a continuous angular sweep, a continuous radial gradient, and a periphery beyond which low-scoring candidates fall off the visible halo entirely. The user reads adjacency-to-focal as similarity-to-focal at a single glance, which is exactly what makes the halo legible without score chips or any other chrome.

The radial formula resolves to `r = r_focal + r_inner + (1 − normalized_score) · r_extent`, where `normalized_score` is the candidate's aggregated multi-frequency rank (§8.1.1) divided by the top candidate's rank, and the scale-space boundary at the periphery is preserved by a workspace-tunable `min_score_threshold` (default 0.3) below which candidates fall off the halo. This is not the forbidden concentric-sphere layout — the prohibition there was on concentric spheres as the *primary placement authority* over the workspace, and the halo is, instead, a *retrieval-score visualization* around a focal panel, a derivative reading rather than a layout authority. The two ideas were collapsed in earlier doc drafts; they are kept distinct here.

What makes the halo more than a 2D rendering is the ray-projection the §1.2.2 update specifies: *"nodes in our 3D are actually ray-projected to the conic surface of the concentric 2D similarity as collapsed singular nodes with their original image billboards or slowly rotating umap colors."* When the halo opens around a **2D query element** — the focal "stuck" node primitive, or one of its singular-field / computation-graph primitives (§O.18) — that element is the **apex/focus** of a common cone whose focal line is the 2D panel camera's, and whose lateral surface coincides with the halo's outer ring. The 3D nodes that retrieve against it are **transported along that cone by their retrieval similarity** (the triple product, §8.1; §O.18): the **normalized similarity of every halo-visible node sets both its radial and its along-ray distance** along the cone (more similar → nearer the apex), and — depending on **camera view** — its **angular placement** is the projected line of its intersection along the **shared cone surface normal**. Each transported node lands as a *collapsed singular node*. This **supersedes** the earlier "project the focal's manifold-nearest neighbours" mechanic (§O.18): the halo transports any *retrieval-similar* 3D node, not only the 3D-geometric nearest, and deleting a halo result transports in the next-most-similar from the retrieval-similarity queue (§O.14). What we get on the halo, then, is no longer just a 2D similarity ranking but a *superposition of retrieval space and manifold space* — every phantom is simultaneously a soft-link candidate by triple-product rank and (for projector-backed phantoms) a manifold-nearest chunk by 3D geometry. The §1.1 framing of the Imaginary retrieving the 3D world in manifold form, contracting it to abstract structures, is made literal at this surface.

The collapsed singular nodes carry the chunk's original image billboard when one is attached (§11.2) — so an image-bearing chunk stays visually identifiable as it collapses across the dimensional reduction — and otherwise carries the chunk's slowly-rotating UMAP colour. That colour is itself the second half of what the §1.2.2 update calls the 6D UMAP: *"umap projections are supposed to be 6d, 3 for hsv that are then slowly rotated similar to how the 3D rotates."* What UMAP fits per chunk is a 6-vector, not a 3-vector. The first three components are the spatial position (`x`, `y`, `z`) in the projector manifold that drives the LayoutFrame placements (§6.1, §9.4). The last three are the colour (`h`, `s`, `v`) in HSV space — determined by UMAP from the chunk's TF-IDF vector exactly the same way the position triplet is, but rendered as the chunk's fill colour rather than as a spatial coordinate. The HSV triplet rotates slowly around the canonical hue origin at the same period the 3D camera orbits the workspace centre (default 60 seconds for a full hue cycle, matched to camera azimuth), so as the user rotates the projector view, the chunk colours rotate in lockstep with the orbit. The semantic intent is that a chunk's visual identity shifts gracefully with the angle of observation — relative colour relationships are preserved at any instant, but the colour encoding itself is a continuous transformation, not a static label, which is what makes the rotation *similar to how the 3D rotates* in the user's phrasing.

The 6D fit is a single UMAP call producing one 6-vector per chunk — position and colour are jointly the UMAP fit, sharing the same neighbour-preservation guarantees, and there is no separate colour UMAP. And because the ray-projection preserves a chunk's HSV state, a collapsed singular phantom on the halo carries the same slowly-rotating hue its parent 3D chunk carries: visual identity persists across the dimensional collapse, and as the user rotates the projector, the halo's collapsed-singular phantoms rotate in colour with their projector parents. The Imaginary's manifold-form contraction of the Real is, in this way, both *legible* (the hues track, the positions ray-project) and *continuous* (everything rotates together with camera azimuth), which is how the halo achieves its distributional-substance character.

#### §8.2.2 Autoregressive Halo Feedback (§17.7)

> "As the user clicks a node, a new node appears in the 2D editor to provide a continuous feedback that autoregresses over the retrieval space." (user, verbatim, §1.1)

A click on a halo phantom is **not a one-shot wiring action** — it is the start of a recursive feedback loop:

1. **Click halo phantom** → `concept_edge_create` (§5.4) commits a hard link (§3.2.1) from the focal to the chosen candidate.
2. **New focal materialises** → the chosen candidate becomes a new pinned panel adjacent to the original focal (per §4.2 freeze-at-rect, but anchored to the phantom's screen position rather than a 3D node).
3. **New halo radiates** → the new panel's apparition surface fires immediately via `apparition_service.surface_for(new_card_id)`; a new concentric-ring halo (§8.2.1) appears around it.
4. **Repeat** → each click continues the recursion; the user is *walking the retrieval space* one focal at a time.

The autoregression is **finite** in practice: the user's attention bounds the recursion; the cascade scheduler's actor-aware short-circuit (§7.4) prevents the agent from auto-firing the same loop. But the *structural capacity* for unbounded autoregression is the point — the halo is the imaginary's mechanism for *unfolding latent connections* without committing to any single path until the user (or agent) clicks.

The REPL action `ui-halo-focus` (§14.2) and the env-scenario `halo-focus-roundtrip` exercise the single-step path; the recursive loop is exercised by chaining `ui-halo-focus` calls with different `focal_card_id` values as the autoregression advances.

#### §8.2.3 Halos Around Compiled-Graph Children (§7.3)

Compiled-graph children (the single `name : value` simplified nodes spawned by the compile-expand — double-left-click, §7.3.4) themselves carry halos:

> "Halos can also appear around computation graph nodes, which are simply singular-field knowledge panels with one key-value pair and references the rest of the way up the recursion-over-iteration tree by other variable(s)." (user, verbatim, §1.1)

A hover on a compiled-graph child triggers `apparition_service.surface_for(child_id)` — the apparition surface is *uniform* across all ConceptNode kinds (panel, child, halo phantom, fixture). No special-cased halo path; the same triple-product (§8.1) ranks candidates against the child's name + description + rendering exactly as for any other focal.

**Singular-primitive fields are first-class halo focals; hover-to-panel spans base and halo forms (§O.19).** The halo fires for **singular-primitive field representations with links in computation-graph form** — a singular-field graph node (§4.6 / §O.19) is a focal exactly as a panel is. And a 3D node shows its **knowledge-panel representation** on hover whether it sits in base-UMAP layout or has been **transported into a retrieval halo** (§O.18); clicking it sticks that panel into the 2D for graph integration (§4.2 / §5.3).

The recursion-over-iteration tree (the `{var}` reference chain that the child's value participates in) is what gives the compiled child its semantic neighbourhood: candidates the child's `{var}` chain *would* connect to surface as soft links (§3.2.1), and the user can click any of them to extend the chain. The autoregressive feedback (§8.2.2) propagates through compiled-graph children identically.

#### §8.2.4 Halo Gating — Text-Input Fields Only (review clarification §O.3)

A focal field opens a halo **iff it carries rendered literal text input** — a typed value, including a blank or in-progress text field (per N.10). A field whose value is a **pure `{ref}`** (a memory-access activation, optionally with an organising label) opens **no halo** — it is already bound to a node, so there is nothing to retrieve *for*. When a text field *also* embeds `{ref}` tokens (e.g. `summarise {chunk}`), the halo query is the **whole resolved field** — the literal text plus the resolved content of the embedded refs (§O.3). This scopes apparition retrieval to where the user is actually composing semantic content rather than onto already-bound references: a blank authoring field still radiates task-relevant candidates (§5.1), while a wired `dom {scan for duckduckgo url}` stays quiet.

### §8.3 Retrieval Scroll-Spine (§USER G.1)

> **§S.3 DEPRECATION (2026-06-12) — the retrieval SIDEBAR is removed.** The standalone right-side
> retrieval sidebar (the `#sidebar` NL-search panel + `#rs-latch` toggle + its result list) is an
> **anti-pattern**: in-editor halo queries with ray projections (§8.2 / §8.2.1.1) subsume it — retrieval
> radiates *proximal to the focal concept node* the user is composing (§4.1.2), so there is no separate
> surface to scroll. The retrieval **backend stays** (`/chunk_search`, `/apparitions`, the triple-product
> index §8.1); only the sidebar **UI surface** is retired. The scroll-spine *visibility rule* below still
> governs which retrieved chunks extrude in the 3D projector — it is now driven by the halo's result set
> and the §6.4 viewport spine, not by a sidebar result list.

Default state for retrieval chunks: **collapsed-hidden** (folded into hub; §6.4). An `IntersectionObserver` on the visible result set flips `chunkCollapseTarget[id] = 0` for rows currently in the scroll viewport. Off-viewport rows fold back. **No global "show all"**, no third path (§6.4).

### §8.4 URL Sidebar Interactions (§USER G.2, G.3)

| Element | Click effect |
|---|---|
| URL label | Toggle that URL's doc-hub collapse; scoped to viewport-visible rows when a search is active |
| Eye button | Flip the URL's `hidden` flag (§6.3) |
| × button | Purge that URL from the workspace (§6.5) |
| Hover URL row | Highlight matching hub sphere; show unified hover panel (§4) |

### §8.5 Result-Row Click → Fly + Pin (§USER G.6)

Click on `.instance-row`: (1) `chunkCollapseTarget=0` for the chunk, (2) camera tween to the chunk's 3D position, (3) pin the unified panel via freeze-at-rect (§4.2).

Click on `.page-card`: (1) camera tween to doc-hub, (2) drill into per-URL instance list, (3) pin the doc-hub's panel.

### §8.6 Hover Preview Uses The Unified Panel (§USER G.4)

No "root summary," no separate widget. One `#billboard` instance, content swapped per hover. Source can be 3D node, sidebar row, search-result row — all hit the same code path.

### §8.7 Persistent Accessor Table (§5.4)

Each `(domain, pattern_hash)` carries an `accessor_dict` — the inverse lookup from field name to relative xpath (§8D.39). Populated incrementally by every scan. Exposed in the editor as `XPathPattern` cards (§8D.15); accessor edits write back to the persistent table. Inverse path: a `{name}` reference in a compile chain resolves to the structural pattern that produces the field.

### §8.8 Retrieval-Driven Scan Feedback — The Unified Conceptual Program Model (N.11)

> "I can simply search or keep a running search of the most relevant chunks over a global perspective by doing similar for constructing our db vector and cypher-vector searches. This then enables dynamic computation for both scanning and RAG-based tasks that link back to which new urls to scan according to how well each search result chunk is evaluated by a language model that decides the critique of similarity from a logical and through-process based standpoint, so a kind of intelligent threshold on semantic similarity that decides which results to follow up on with their own scan instances. This bridges the gap between computation graphs and agent-based workflows through a unified conceptual program model." (user, verbatim, N.11)

The same minimal node structure (§9.6.2) that wires a `WebBrowser.scan` into a host node wires a `Database.search` / `Database.cypher` (§9.5.1) into a **running retrieval node** whose `{chunk samples}` iterable is the most-relevant chunks over the global index. A **language-model critique node** (an `Agent.prompt`, §9.5.1) reads each retrieved chunk and judges its similarity *reasoned* — a logical, through-process critique rather than a bare cosine score — and an **intelligent threshold** decides which chunks warrant follow-up. Each chunk that clears the threshold spawns **its own scan instance** (a new `WebBrowser.scan` over the chunk's URL), whose output re-enters the index, whose new chunks are re-critiqued — a closed loop.

This is the §7.8 reservoir's readout **driving new perceptions**: the readout (critiqued chunks above threshold) selects which new world-measurements (scans) to take, and the loop closes through the projector (§6.6). It is the unified conceptual program model the user names — *computation graphs and agent workflows are the same graph*: the critique-and-rescan loop is an agent behaviour (§12) expressed entirely in the minimal node structure of §9.6.2, with no agent-specific shim (§12.7). An **alternative localisation** (N.11): a dedicated **query panel/graph** whose halo retrieval (§8.2) acts as the context localiser, seeding the loop from the apparition surface around the query rather than from a flat global search.

**Database ontology walk + cypher building (§O.5).** The same mechanics apply to the concept-graph's *own* ontology, not only to web URLs. The Database node exposes its **rank-1 ontology nodes** and supports **recursive chunking over rank-1 walks** across linked ontology nodes. In the 2D GUI the user **keeps or deletes** (double-right-click, N.13) ontology fields per retrieval/cypher query; the kept set **assembles a cypher query** built up from **multiple semantic-retrieval runs over rendered-text nodes** (the halo gating of §8.2.4 means those runs fire from the rendered-text fields, not from already-bound `{ref}`s). **Retrieval halos thereby discover new cypher fields** to aggregate and walk — bridging semantic retrieval (`Database.search`) and structured graph query (`Database.cypher`, §9.5.1) within one node. The kept/deleted ontology fields are themselves rank-1 brace-revealed (§O.1) like any other node, so building a cypher is the same gesture vocabulary as exploring any object.

---

## §9 — Foundational Fixtures and Python-Native Trees (§8D.4.2, §8D.35.1)

### §9.5 Three Foundational Fixtures (§S supersedes the §1.2 four-fixture update; §8D.35.1)

Three peer ConceptNodes, all undeletable, all flat (no centrality hub).

> **§S DEPRECATION (2026-06-12) — the Editor fourth fixture is removed.** The §1.2 update had added a fourth
> fixture, `Editor`, exposing the concept-graph mutation gestures (`create`/`link`/`overwrite`/`delete`) as a
> Function-typed tree. Per §S.1 this is an **anti-pattern**: in-node editing and markdown-gesture syntax
> parsing over recursive text structures *already happens implicitly within the computation-graph framework*
> (the unified knowledge-panel syntax↔compute-graph scheme, §4/§7), so a separate `Editor` *object* is
> redundant. The mutation gestures are **intrinsic to the panel scheme** — the panel uses `/concepts` +
> `/concept_edges` directly (the same lifecycle, §10.2) — and need no fixture to represent them. The fixture
> set re-aligns with the three CLAUDE.md / §8D.35.1 peers.

| Fixture | Backing | Function |
|---|---|---|
| `Agent` | `fixture::agent::<wsid>` | SLM with meta-prompt + prompt + output primitive functions (§9.5.1). Meta-cognition tick + emitter catalogue (lightweight; agent bodies live in user-designated parameter cards per §8D.37). |
| `WebBrowser` | `fixture::web_browser::<wsid>` | Live Selenium runtime; `scan(url, query?)` outputs a live-updated 3D scan of the shadow DOM (§9.5.1, §15.7). |
| `Database` | `fixture::database::<wsid>` | Unified workspace storage (persistence + TF-IDF + concept graph + web ontology + meta-cognition substrate). `search(query)` + `cypher(query)` + `concept(node_id)` rank-1 KG walk (§9.5.1). |

**No centrality hub.** Database is not the root; it's the concept node whose backing pointer happens to resolve to persistence. `SearchableURL`, `DetectedAccessor`, `XPathPattern`, `PinnedComponent` (compiled-from-scans; §8D.39) are peers of the fixtures, not children of Database.

> "Fundamental objects cannot be 'X' ed out." (user, verbatim)

The `×` close button — like *all* panel chrome under the §S black-slate design (§4.1.2) — is absent everywhere; foundation fixtures (Agent, WebBrowser, Database) additionally cannot be deleted at all: `apply_delete_lifecycle` (§10.2) rejects deletion attempts on the `fixture::` prefix via the `fixture_delete_guard` env-scenario (§14).

### §9.5.1 The Three Base API Object Signatures (verbatim — current spec)

What follows is the user's own naming of the three foundational fixtures, then the structural shape each takes when it is materialised by §9.6 as a python_object ConceptNode with python_function children. The fixtures are the workspace's primitive computational endpoints; everything else — the imported libraries (§9.7), the user-authored concept cards, the agent's body subgraph (§12.1) — composes through these three. (The §1.2 update had named a fourth, `Editor`; §S removes it — see the deprecation note in §9.5 and the gesture-subsumption note below.)

**Agent.** The user writes: *"Agent: slm with a meta-prompt, prompt, and output primitive functions"*. So the Agent fixture is not a single black-box SLM call but three composable primitives — a meta-prompt setter, a prompt setter, and an `output` invoker that fires the SLM against whatever meta-prompt and prompt have most recently been set. The user (or the agent itself reaching into its own emitter) wires `Agent.meta_prompt → Agent.prompt → Agent.output` as a three-node chain; the chain's terminal `output` carries the live token stream (`agent_token` WS frames per §12.1) and, when a Pydantic schema is provided as the optional argument to `output`, validates the structured result before returning it. The earlier `Agent.invoke(meta_prompt, prompt, output_template?)` convenience wrapper still exists for single-call composition, but the three primitives are the canonical surface and what the agent body subgraph (§12.1) is now wired against. The Agent fixture also carries a **`template` functional-object** (§O.21) bound to this prompt–metaprompt–generation scheme: a single template engine that **simultaneously templates the input prompts** (resolving `{var}` content into `meta_prompt` + `prompt`) *and* **parses the output** (the pydantic schema given to `output`, §7.2 / §O.20). Authored in the minimalist field-tree pattern rather than raw JSON schema, `Agent.template` is the home of the pydantic tooling — input-prompt templating and output-parsing are the *same* member acting on the two ends of the chain.

**WebBrowser.** The user writes: *"WebBrowser: for scanning, where scanning takes url input and maybe a search query and outputs a live-updated scan to the 3D gui of the shadow DOM"*. The fixture's primary function is `WebBrowser.scan(url, query?)`. The recursive DOM scan discovers search fields when a query is given; pagination is implicit (the next-page button is pressed iff more samples remain; on stale pagination the scan transitions back to a previous URL); and the *output is a live scan into the projector* — chunks stream into the workspace as they materialise (per the workspace-WS dual-routing of §18.1, so chunks reach the long-lived frontend WS and not only the snapshot socket), and a returned `ScanResult` carries the chunk-pattern schema (§15.8, output panel typically named `pattern_map`) once the scan settles. Companion methods (`snapshot`, `navigate`, `click`, `more_results`, `filter`) decompose the implicit pagination loop into individually wirable Function nodes, and the older `WebBrowser.web_query(url, query?, samples)` form survives as the sample-bounded variant; bare `scan(url, query?)` is the unbounded form the §1.2 update names.

**Database.** The user writes: *"Database: for retrieval that takes a natural language or cypher query as input and gives an unstructured chunk result output; also has a 'concept' function that returns the rank-1 knowledge graphs of a given input node in the db, and can do this over iterative structures for multiple input nodes... note the 'signal-stream' constraint in our UI docs somewhere. This means that for iterables, only the signal node that's being iterated on is visible in the 2D ui panel, so knowledge panel structures can have multiple values that are iterated over for each rollout of the computation graph with recursive firing."* So Database has two primary functions and an iteration contract. `Database.search(query, cypher=False)` takes a natural-language or Cypher query and returns the unstructured chunk list — the NL form ranks by triple product (§8.1) and the Cypher form ranks by predicate order, with the flag forcing the latter when auto-detection would not. `Database.concept(node_id_or_list)` returns the rank-1 knowledge graph around the input — the focal plus every directly edge-connected concept node — and accepts a list of node ids for batch retrieval, at which point the signal-stream constraint (§4.6.1) takes over: the 2D panel renders only the currently-firing signal at any moment, while the other elements of the iterable remain in storage and are advanced through by the play/pause stepper (§7.5) for each rollout of the computation graph.

**Editor — DEPRECATED as a fixture (§S.1).** The §1.2 update had written: *"Editor: exposes all concept graph editor gestures like create, link, overwrite, and delete actions on input nodes."* §S removes the `Editor` *fixture*: the create/link/overwrite/delete gestures are **intrinsic to the unified knowledge-panel syntax↔compute-graph scheme** (§4/§7) — in-node editing and markdown-gesture syntax parsing over recursive text structures already perform graph mutation implicitly, so no separate Function-typed `Editor` object is needed to represent them. The gestures remain, as the panel scheme's own mutation path: a panel edit / `{var}` auto-create / right-click compile *is* a `create`/`link`/`overwrite`; deletion is the §N.13 double-right-click. Mechanically they route through the **same lifecycle dispatcher** (§10.2) the agent's emitter uses — `create_concept` / `create_concept_edge` / `update_concept` / `delete_concept` — via `/concepts` + `/concept_edges`. The agent therefore does **not** call into an Editor object; it authors through that same concept-graph mutation lifecycle (the entanglement of §12.6.1 is now "user-gesture and agent-emission share one mutation lifecycle," not "both call the Editor fixture"). The emit-action backings (`CreateCardAction`, `LinkAction`, `WriteFieldAction`, …, §12.2) are the agent's emission catalogue over that lifecycle.

The signal-stream constraint the user names in passing has its own home in §4.6.1; it governs every panel that carries an iterable value, not just Database.concept's returns. The user/agent reads one signal at a time; the play/pause iteration advances the visible signal; the recursive firing the user describes is the cascade re-firing downstream of each signal advance, with the panel rendering only the currently-active signal in its print-form tree.

### §9.6 Python-Native API Trees (§8D.4.2)

A python class is materialised by `backend/services/python_api_materialiser.py` as a one-level tree of ConceptNodes:

| Python construct | `type_hint` | `data` block |
|---|---|---|
| Class | `python_object` | `{qualified_name, read_only: true, members: [<child ids>]}` |
| Property | `python_property` | `{qualified_name, read_only: true, value_type, static, no_datablock: true}` |
| Function/method | `python_function` | `{qualified_name, read_only: true, no_datablock: true, ports: {inputs: [...], outputs: [...]}}` |

**Three invariants (§8D.4.2.1):**

1. **`read_only: true`** — editor refuses edits; latch button hidden; 🔒 indicator on header; right-click expand still works.
2. **`no_datablock: true`** (property + function) — data carries signature metadata only; backing python implementation is **not** projected into the editor.
3. **`backing_pointer` resolves to the live callable** — Compile/agent-invoke/REPL `backing-invoke` walk through the registry to the actual Python.

**Edge types (§8D.4.2.2):** `OBJECT_HAS_PROPERTY`, `OBJECT_HAS_FUNCTION`, `FUNCTION_INPUT_TYPE`, `FUNCTION_OUTPUT_TYPE`. These compose the **downstream type ontology** (§8D.42.1) and feed the typed-wiring constraints (§8D.4.1).

**Three fixtures' materialised trees (§9.5.1; §S removed the fourth `Editor`):** On `foundation_fixtures.ensure_foundation_fixtures(workspace_id)`:

- **Agent** → meta-cognition handle with the three SLM primitives (`meta_prompt`, `prompt`, `output`) + a **`template` functional-object** (§O.21 — parses input prompts *and* output simultaneously: `{var}`-templates `meta_prompt`/`prompt` and applies the pydantic output schema of `output`, authored as a field-tree per §O.20) + the legacy convenience `invoke` + the tick/spawn/fork/perceive/emit lifecycle methods. Each emit-action method's output type materialises the corresponding action card type (CreateCardAction, LinkAction, WriteFieldAction, etc.) as python_object children — these are exactly the **Editor** fixture's functions surfaced as the agent's emission catalogue.
- **WebBrowser** → `WebBrowserManager` with properties (`current_url`, `current_title`, `driver_alive`, `profile_path`) and functions (**`scan(url, query?)`** — the canonical entry-point, §15.7), plus companion methods `snapshot`, `navigate`, `click`, `more_results`, `filter`, and the legacy `web_query(url, query?, samples)` sample-bounded variant.
- **Database** → unified handle with **`search(query, *, cypher=False)`**, **`cypher(query)`**, **`concept(node_id | [node_ids])`** (rank-1 KG walk under signal-stream constraint §4.6.1), plus utility methods (`tfidf_retrieve`, `walk`, `nearest_chunks`, `by_provenance`, `by_url`, `iterate_pattern`, `fold`, `select`, `pop_chunk`, `collapse`, `pin_panel`, `set_visibility`, `fly_to`, `frame_all`, `focus_workspace`, `recompute_umap`).
- ~~**Editor**~~ — **DEPRECATED (§S.1)**, no longer materialised. Its `create`/`link`/`overwrite`/`delete` gestures are intrinsic to the panel scheme and route through the concept-graph mutation lifecycle (§10.2) via `/concepts` + `/concept_edges`; chrome/UI gestures (pin, hover, latch, …) are addressed through the §10.5 UI State Service mirror.

#### §9.6.1 The Typed Panel Form, Functions-As-Memory-Lookup, and Module→Recursive-Node Translation (M.2–M.5)

> "Module structures (the modules, their properties which are other modules, and functions-as-modules with functional-inverse lookup memory maps) are completely translated to recursive structures of computation graph nodes of singular values with memory reference from other nodes to build the original object model." (user, verbatim, M.2)

A materialised python_object (§9.6) renders in the editor as a **typed pure-print panel** whose rows are `name: Type = value` (M.3) — the field-tree of §4.6 with an explicit **type slot** between key and value:

```
self:WebBrowser
   NO_CHANGE_LIMIT: int = 3
   SETTLE_TIMEOUT: float = 0.25
   driver: WebDriver = {driver}
   scanner: {FunctionOutputType} = {scan}
```

Each row is a **singular-value compute node with memory references** (M.2): a literal (`3`, `0.25`), a `{reference}` to another node (`driver: WebDriver = {driver}`), or a function call as a curly-brace reference whose *type* is itself a reference (`scanner: {FunctionOutputType} = {scan}`). The object model is *reconstructed* from these references — the panel is not a stored snapshot but the recursive resolution of the node's reference graph, rendered to the depth the user has unfolded (§7.3.4).

**Properties-are-modules (M.2/M.4).** A property whose type is another class (`driver: WebDriver`) expands (right-click / hover, §7.3.4) into that class's own typed panel — a `super:BaseWebDriver` inheritance row at next rank, its typed constructor attributes (`command_executor: str | RemoteConnection`, `keep_alive: bool`, `options: BaseOptions | None`, …), and its function I/O — recursively, because a property *is* a module.

**Functions-as-memory-lookup (M.5).** A function node is a memory map from typed inputs to an inferred output type: *"forward calls linked to a function node via equality of an input on the right and an output type on the left infer output types"* (M.5). Expanding a function reference (`{scan}`) reveals its input fields (each typed, each a variable or reference) plus its output-structure field (the rendered output object), loosely linked to the function variable node:

```
scanner: {FunctionOutputTypeNodeReference} = {scan}
   some_input: SomeType = {variable_or_reference}
   anotherfunction: {AnotherFunctionNodeReference} = {anotherInputVariableRef}
   scanner_output_structure: KnownOutputStructure = <rendered output object>
```

The forward call renders the output (automatic rendering, M.9 — "similar to memory reference lookup"); the inverse is the closest-inverse lookup (§7.7) — the function's memory map read backward. This is why functions "serve more as automatic memory lookup to inputs" (M.3): a bound-input function is a lookup of its output, and an unbound-input function with a known output is an inverse lookup of its inputs. The port schema (§9.8) carries the typed I/O; the type slot in the panel form is its pure-print rendering. This whole typed panel is the reservoir's **generative readout** (§7.8) discretised into an editable object model. Full interaction spec: `docs/frontend/object_exploration.md`.

#### §9.6.2 External Reference Propagation, Type-Stripped Rendering, and Rank-1 Minimalism (N.3–N.10)

> "There should be another note in the verbatim about propagating external node references through as their own set of objects that are then recursively rendered in new panels." (user, verbatim, N.3)

A node is **both a computation-graph node and a panel** — one singular-field primitive visually restructured by context (N.2) — and authoring typically **begins in computation-graph form**. When such a node references an external functional-object (e.g. the WebBrowser's `scan`), that reference **propagates through as its own set of objects, recursively rendered in new panels** (N.3):

- **Duplicate instantiation (N.6).** The referenced external node is instantiated as a **duplicate of its original external reference** — still operationally calling the originating object (the live WebBrowser), but living as a **rank-1 component** of the referencing node. Right-clicking the reference renders its rank-1 instances inline **in the knowledge panel** (the braces are the fold marker; unfolding drops them and indents the children, §O.2). In **computation-graph form** the braces likewise mark hidden rank-1 links — hover previews them, a click instantiates the rank-1 walk as **undirected line-linked singular fields**, in node-count parity with the panel (§O.1); a reference to an already-visible node resolves to a solid link (§O.1a). The referencing node shares links to the functional-object node and its owning object.
- **Type-stripped structural rendering (N.5).** Distinct from the typed `key: Type = value` form (§9.6.1), a propagated reference may render **purely structurally over `\t` + `\n`** with **no type or I/O presentation** — `{scanner}` alone, then `url {}` / `dom {}` once unfolded, the variables stripped of types and I/O and referenced purely through the scanner's path assigned to the host node. Output slots stay blank (`{}`) until bound, or until referenced externally for inverse lookup (§7.7). The typed and type-stripped renderings are two projections of the same tree.
- **Names with spaces (N.7).** Because structure is discerned **purely by `\t` + `\n`**, field/variable names may contain spaces: `duckduckgo url`, `scan for duckduckgo url`, `chunk samples` are all valid node names.
- **`{ref}` = memory-access activation; labels optional (N.10).** Any curly-brace field — `{paginate}`, `{duckduckgo url}`, `{scan for duckduckgo url}` — is simply an **activation of a memory-access procedure elsewhere in the app**. The label and spaces beside a `{ref}` (the `url` in `url {duckduckgo url}`) are **optional and organisational** only.
- **Rank-1 minimalism; full distribution in 3D (N.7/N.8).** The 2D panel/graph shows only **rank-1 relations** — the base functions and relations that define the object (e.g. the ShadowDOM's `search` / `paginate` / `chunk`) — keeping the high-level compute perception minimal; the **full per-sample scan distribution lives in the 3D GUI** (§6, §15), not in the 2D tree. Right-clicking a `{ref}` field reveals its next rank-1 structure (N.8); selective unfolding stays slim and recursive without losing per-sample iteration (§4.6.1). The uppermost abstractions display by default.

The worked example (the DuckDuckGo walkthrough, N.4–N.9):

```
DuckDuckGo
   scanner                              ← {ref} to WebBrowser.scan, dragged-in (§7.3.4 N.4); right-click reveals rank-1
      url {duckduckgo url}
      dom {scan for duckduckgo url}     ← output-inferred type ShadowDOM, shared in the 3D GUI (N.7)
         search {}
         {paginate}
         chunk {chunk samples}          ← per-sample iteration on signal presentation (§4.6.1, N.9)

duckduckgo url
   https://www.duckduckgo.com/

scan for duckduckgo url
   search {}
   {paginate}
   chunk {chunk samples}
```

The ShadowDOM is a **simplest-possible object-oriented Python type** (N.1, §15.1) — the scan's output object — and the rank-1 tree above is the minimal set of base functions/relations defining it. Full interaction spec: `docs/frontend/object_exploration.md`.

### §9.7 Python-Library Middleware — Generalising the Materialiser (§1.2 update; §8D.4.2.6)

> "Please make sure the standardized api formats are themselves generalized into a process of importing api objects from python libraries. What this middleware is meant to do is translate the recursive object and python package/module hierarchy from a simple module that stores library imports." (user, verbatim)

The Python-API materialiser (§9.6) is generalised into a **library-imports middleware**:

1. **Input** — a *simple module that stores library imports*: a `.py` file (the workspace's `wfh_imports.py`, or any user-designated module) whose body consists of `import some_pkg` / `from some_pkg import some_class` statements. The middleware reads this module and resolves every imported symbol.
2. **Walk** — for each resolved symbol, `inspect`-walk the recursive object + package/module hierarchy: top-level packages → submodules → classes → properties + methods, depth-bounded by a configurable `max_walk_depth` (default 4) to keep the materialisation tractable for large libraries (numpy, pandas, etc.).
3. **Materialise** — every node in the walked hierarchy becomes a `python_object` / `python_property` / `python_function` ConceptNode with the same read-only no-datablock contract as the three foundational fixtures (§9.6).
4. **Edges** — the `OBJECT_HAS_PROPERTY` / `OBJECT_HAS_FUNCTION` / `FUNCTION_INPUT_TYPE` / `FUNCTION_OUTPUT_TYPE` edge family (§8D.4.2.2) extends across imported packages exactly as it does across the three fixtures. Inferred types that resolve to symbols from a *different* imported package wire to those packages' materialised trees, composing a unified type ontology (§8D.42.1) across all imports.
5. **Idempotency** — re-running the middleware over an updated `wfh_imports.py` is idempotent on stable qualified names; newly-imported symbols add their subtrees; removed-import symbols dissolve their subtrees (the deletes pass through `apply_delete_lifecycle` so undo is via rollback per §11.4). Backing-pointer version bumps (§8D.39.6) invalidate compile-cache for downstream nodes referencing the changed library.

> "We will keep it to our simple set of python-based four fundamental api objects that serve the core of our current data processing and interfacing functionality within our frontend-backend functional object design." (user, verbatim)

The three fixtures (§9.5) are the canonical first application of the middleware — they are materialised on `ensure_foundation_fixtures` from a workspace-internal "imports module" that imports `WebBrowserManager`, `Database`, and `Agent` (§S removed the former fourth, `GraphEditor`-backed `Editor`). Arbitrary user-imported libraries flow through the same middleware as additional `python_object` peer trees. The three fixtures remain the *core* — the design contracts (signal-stream §4.6.1, dialectical inversion §7.3, halo retrieval §8.2) all assume their presence; additional imports are *composable extensions* that compose through the same mechanics.

### §9.8 Port Schema On Function Nodes (§8D.4.1)

```json
{
  "ports": {
    "inputs":  [{"name": "query",      "type": "str", "required": true},
                {"name": "samples",    "type": "int", "required": false, "default": 20},
                {"name": "duration_s", "type": "int", "required": false, "default": 0}],
    "outputs": [{"name": "chunks",     "type": "list[ChunkInstance]"}]
  }
}
```

The `duration_s` input is the **time-box** of the scan (§15.10) — a first-class, user-settable functional-object property (Q.2). `duration_s = 0` means *sample-bounded* (stop at `samples`); `duration_s > 0` means *time-bounded* (scan archive.org — or any URL — for that many wall-clock seconds, then stop and finalise). It maps to the scanner's existing `max_duration` (`backend/dom/pipeline.py`, `mapper.snapshot(max_duration=…)`) — previously hard-coded, now lifted to the port so the graph editor exposes it. `ConceptEdge.source_port` / `target_port` carry the port names. Empty port fields = default rendering port. Types are **implicit** (§8D.42) and inferred **jointly** (§O.15): top-down from the API-object ontology (§O.8, where a field binds to a materialized API node), bottom-up observed-from-wiring (for user-authored / unbound slots), and sharpened by the type ontology (§15.9) — never enforced as a hard compile-time gate (mismatch is a red-tinted edge + tooltip, not a fatal error).

---

## §10 — Real-Time Streaming and Lifecycle (§11)

### §10.1 The Workspace WebSocket (§11.4)

One long-lived socket per workspace per tab: `/api/ws/workspace/{workspace_id}?resume=<seq>`. Frames are monotone-sequenced (§2.4). Frame types:

| Frame | Source | Effect on frontend |
|---|---|---|
| `chunk_added` / `chunk_replaced` / `chunk_removed` | Scanner / chunk lifecycle | Mesh add/replace/remove; TF-IDF index update telemetry |
| `chunks_partial` / `instances_indexed` | Scanner | Spine refresh |
| `umap_canonical` | Layout Service at scan-end (§9.3) | Tween chunks from preliminary to canonical positions |
| `concept_changed` | Lifecycle dispatcher (§10.2) | Re-render affected panels; refresh apparitions |
| `concept_index_update` | Concept Index Service (§8D.17) | Refresh apparition slots; update PageRank-sorted lists |
| `agent_token` | Agent transformer (§12.1) | Stream tokens into the agent panel body |
| `evolution_diff` | Evolution log (§11.4) | Append to history view; cascade scheduler notification |
| `ui_state_changed` | UI State Service (§14.2) | Mirror pinned panels, compile expansions, scroll viewport, halo focus |
| `rollout_paused` / `rollout_resumed` | Rollout coordinator (§7.5) | Update play/pause indicator; reveal edit affordances |
| `purge_workspace` | Purge handler (§6.5) | Clear scene, panels, caches, frame_seq |
| `cascade_status` | Cascade scheduler (§7.4) | Reveal per-actor fire counts |
| `done` / `error` | Various | Per-action terminator / error envelope |

**Lossy backpressure (§2.4):** drop oldest `chunks_partial` / progress frames; keep `done`, `error`, latest `umap_canonical`, latest `concept_index_update`, all `concept_changed`, all `evolution_diff`.

### §10.2 Lifecycle Dispatcher (§2.2)

```
mutation request (REST or in-process call)
        │
        ▼
apply_update_lifecycle / apply_delete_lifecycle
        │
        ├──► Kuzu write
        ├──► WS broadcast: concept_changed
        ├──► ConceptIndex upsert (§8D.17)
        ├──► output-projection schedule (§9.12)
        ├──► evolution-log diff (§11.4)
        └──► cascade scheduler nudge (§7.4)
```

Every mutation — user gesture, agent emission, REPL action, python-API materialiser, scanner-chunk projection — enters through this dispatcher. There is no second path.

### §10.3 Layout Service (§11.5)

Owns chunk-side vectorisation:

- Incremental TF-IDF on every chunk arrival.
- Joint UMAP refit at scan-end (and on `/api/recompute_umap` manual triggers, and on graph-state-change deltas with ~800 ms debounce per §9.12).
- Per-URL post-processing (centroid translation to `root_position`, bounding-radius scale, hard collider repulsion; §6.1).
- Emits `umap_canonical` to every workspace WS subscriber.
- Persists canonical coords in a per-workspace LayoutFrame (§11.1) so a reload restores the layout without re-scanning.

### §10.4 Concept Index Service (§11.6)

Owns concept-side vectorisation:

- Incremental nomic embedding on every concept's description.
- Incremental TF-IDF on every concept's rendering.
- Joint PageRank refit on cascade-settle (§7.4).
- Maintains per-card `similar_to` neighbour list (top-K by triple product).
- Emits `concept_index_update` after a settle.

### §10.5 UI State Service (§14.2)

Owns frontend mirror state. The frontend posts telemetry to `/api/ui/telemetry` and per-field REST setters; the service merges and broadcasts `ui_state_changed`. The REPL's in-place activity viewer (§11.8) consumes the same frames. Each field is owned by exactly one setter; the setter broadcasts a `ui_state_changed` frame with the full snapshot so peer surfaces (other GUI tabs, REPL viewer, agent perception) re-sync on receipt.

### §10.5.1 Mirror-Field Roster

Each field below is either wired (✓), partially wired (◐), or planned (☐). Wired means: the field exists in `UIStateService.UIState`, a REST endpoint sets it, a REPL action wraps the endpoint, an env-scenario asserts the round-trip, and the in-place viewer (§11.8) renders the field.

| Field | Shape | Owner gesture | Status | Sequence |
|---|---|---|---|---|
| `selected_id` | `str \| None` | `ui-select` | ✓ | (legacy) |
| `hovered_id` | `str \| None` | `ui-hover` | ✓ | (legacy) |
| `pinned_billboards` | `[node_id, ...]` (ordered) | `ui-pin` / `ui-unpin` | ✓ | §17.2 |
| `pinned_collapsed` | `{node_id → bool}` | `ui-collapse` | ✓ | §17.2 |
| `last_hover_rect` | `{top, left, w, h} \| None` | `ui-hover-rect` | ✓ | §17.2 |
| `last_stick_rect` | `{top, left, w, h} \| None` | `ui-pin` (captures from hover rect) | ✓ | §17.2 |
| `url_collapsed` | `{url → bool}` | `ui-url-visibility` | ✓ | (Mortegon §5) |
| `billboard_url` | `{billboard_id → url}` | `ui-register-billboard-url` | ✓ | (Mortegon §5) |
| `compile_expansions` | `{central_id → {children, expanded_at}}` | `ui-compile-expand` / `ui-compile-collapse` | ✓ | §17.3 |
| `halo_focus` | `{focal_card_id, candidates, opened_at} \| None` | `ui-halo-focus` / `ui-halo-clear` | ✓ | §17.7 |
| **`pin_chrome`** | `{panel_id → {top, left, width, height, minimised}}` | `ui-pin-move`, `ui-pin-resize`, `ui-pin-minimise`, `ui-pin-close` | ✓ | §17.12 |
| **`latch_state`** | `{card_id → "latched" \| "unlatched"}` | `ui-latch-toggle` | ✓ | §17.13 |
| **`viewport_visible_rows`** | `{ordered: [chunk_id, ...], total: N}` | `ui-viewport-spine` | ✓ | §17.14 |
| **`autocomplete_state`** | `{row_id, query, candidates, parent_card_id?} \| None` | `ui-autocomplete-open` / `ui-autocomplete-close` | ✓ | §17.15 |
| `rollout_state` | `{node_id, paused, sample_idx} \| None` | `rollout-play` / `rollout-pause` / `rollout-step` | ☐ | §17.6 (needs coordinator) |

The setters are **idempotent** (same input → same state) and **broadcast on every call** (even no-op calls emit `ui_state_changed` so peer surfaces can re-sync if they were stale). The `last_changed_at` + `last_change_kind` fields on `UIState` carry the diff metadata.

The four bolded fields are the most recently added (this session). They follow the same pattern as `halo_focus` (§17.7): backend mirror, REST setter, REPL action wrapper, env-scenario for the round-trip, viewer row in §11.8.

### §10.6 ConceptComputeNode and LangGraph (§11.7)

`ConceptComputeNode` (in `backend/services/conceptual_compute.py`) is the LangGraph node primitive. Construction binds a `concept_id` + `graph_editor` + optional `slm_client`. Callable with LangGraph's `(state) → state` signature; also exposes `.compile()` for direct REPL/REST use. Auto-classifies into the four dispatch kinds (§7.2).

`compile_subgraph_to_langgraph(focal_id, max_depth=4)` walks back-references and assembles a real `langgraph.graph.StateGraph` keyed by `concept_id`. State is a flat dict `concept_id → {rendering, raw_output, kind, ...}`. Downstream nodes read upstream renderings via the `{slug}` resolver.

A deterministic `_PlainChainApp` surrogate exists for unit-shape probes without `langgraph` — **never used in production paths** (§13.1).

---

## §11 — Persistence and the Evolution Log

### §11.1 What Gets Stored Where

| Artefact | Storage |
|---|---|
| ConceptNode + ConceptEdge | KuzuDB |
| Workspace LayoutFrame (canonical 3D coords) | Backend persistent file (per workspace) + in-memory frontend cache |
| ConceptIndex (per-card nomic + PageRank + similar_to) | Backend persistent file (per workspace) + in-memory cache |
| Edit evolution log (`EditDiff`) | KuzuDB, append-only |
| Chunk content + extraction_trie | KuzuDB |
| Persistent accessor table (§5.4 / §8.7) | KuzuDB, keyed by `(domain, pattern_hash)` |
| Image textures | In-memory `Map<url, THREE.Texture>` + IndexedDB `wfh_texture_cache.textures` (§11.2) |
| Full DOM HTML snapshots | Disk file (`snapshots/`) referenced from `DomSnapshot` records |
| Media assets | Disk file (`media/<domain>/<hash>.<ext>`) + `MediaAsset` records |

### §11.2 Image Persistence (§USER H.1)

Single-fetch path: (1) in-memory cache hit → return; (2) IndexedDB cache hit → blob → object URL → texture; (3) `fetch(proxy_url)` → blob → texture from blob's object URL + save to IDB; (4) on proxy failure, direct fetch; (5) on both failures, no-op.

`X-Image-Proxy-Note` header signals the transparent-PNG fallback; the loader **does not cache** that as a successful image. Two chunks pointing at the same URL share one `THREE.Texture`.

### §11.3 Persistent Snapshots and Merge-Conscious Timeline

Snapshots deduplicated by content hash (SHA256). Same URL + same content hash = no new record. The pipeline that builds an accumulated DOM merge-tree (§3.1–§3.5 in legacy `dom/` doc) is preserved as the scanner's intermediate form; downstream the workspace deals only in `ConceptNode`s and the persistent accessor table.

### §11.4 Append-Only Evolution Log (§8D.33)

Every mutation through the lifecycle (§10.2) leaves an `EditDiff` record:

```python
@dataclass
class EditDiff:
    edit_id:     str   # UUID; monotone-orderable by created_at
    workspace_id:str
    actor:       str   # "user" | "agent:<id>" | "cascade" | "scanner" | "rollback"
    target:      str   # concept_id | edge_id | "workspace"
    action:      str   # "create" | "modify" | "delete" | "link" | "unlink" | "rollback"
    before:      str   # JSON snapshot
    after:       str
    created_at:  str
```

Rollback applies the inverse and **records the rollback itself as a new diff**. Three scopes (§2.6):

- **Single edit:** `POST /api/evolution_log/rollback { edit_id }`.
- **Edit range:** `POST /api/evolution_log/rollback_range { from_id, to_id }`.
- **Actor scope:** `POST /api/evolution_log/rollback_actor { actor, since_ts }`.

The log grows monotonically; a rollback of a rollback is permitted (and recorded).

### §11.5 Adaptive Cleanup (§8D.31)

ConceptNodes live indefinitely while referenced (by edges, by pinned panels, by other concepts' data blocks). Unreferenced and un-pinned nodes age into "faint memory" — present in the index but not surfaced in default views. The user (and agent) can pin a faint memory to revive it. Garbage collection is opt-in via `POST /api/concepts/gc { older_than, unreferenced: true }`.

**Test-DB hygiene — the janitor (§R.9).** Distinct from in-workspace GC: `backend/services/db_janitor.py` is the ONE cleanup module over database creation in tests/probes/REPL runs, so one-off DBs with unique filenames never accrete. Surfaces: `temp_db_dir(label)` (context-managed throwaway DB dir under the single canonical `wfh_test_` prefix, guaranteed removal + atexit net), `register_for_cleanup(...)` for import-time `WFH_DB_PATH` pins, and the retention sweeps — stale temp dirs (canonical + the legacy prefix zoo) and per-workspace side-file orphans (`concept_index_*` / `evolution_log_*` / `layout_frame_*` / `ontology_frame_*`) for **test-convention workspaces only** (`ws*`/`probe_*`); `_default` and human-named workspaces are untouchable. Exposed through the stack as `POST /api/maintenance/cleanup_test_artifacts` (REPL `janitor-sweep`; the `db-janitor-hygiene` scenario). The §11.4 append-only log's external retention policy (§8D.33.6) is exactly this janitor.

---

## §12 — The Agent (§8D.27, §8D.32, §8D.37, §8D.48)

The agent is **not a separate runtime** — it is a *visible recursive computation graph* in the same editor the user composes in. The framework provides a meta-cognition tick; the agent body is authored (by the user, and by the agent itself recursively).

> "We need to integrate GPT4All nous hermes mistral 2 DPO within langgraph, and also need to be able to use live token streaming as an output from our agent function-object." (user, verbatim)

The Agent fixture (§9.5) is a Function-typed ConceptNode whose `invoke` method (§9.5.1) returns tokens as a live stream — each token reaches the editor as an `agent_token` WS frame (§10.1) that the agent panel body appends in real time. The rendering settles when the SLM finishes; downstream cascade re-fires propagate immediately (§7.4).

### §12.1 Agent Body Subgraph (§8D.27.2)

Spawning an agent produces four ConceptNodes wired together:

| Node | `type_hint` | Backing | Function |
|---|---|---|---|
| **Parameter card** | `agent_parameter` | n/a | Holds `goal`, `step_index`, `zone_of_influence`, `cascade_enabled`, `paused` |
| **Perception card** | `agent_perception` | `agent::perception::<pcid>` | Reads the parameter card + workspace apparitions; composes payload |
| **Transformer card** | `agent_transformer` | `agent::transformer::<pcid>` | Holds SLM prompt template; on tick calls real GPT4All streaming tokens |
| **Emitter card** | `agent_emitter` | `agent::emitter::<pcid>` | Parses SLM's structured action; applies via shared `ActionResolver` |

REST: `POST /api/agent/spawn { goal, name? }`. Edges: `PERCEPTION_OF`, `TRANSFORMER_OF`, `EMITTER_OF`, `PERCEIVES → parameter_card`.

### §12.2 Tick Loop — Recursion-Over-Iteration Integration Scheme (§8D.48.1; §1.1 gap-fill)

`POST /api/agent/tick { parameter_card_id }` calls `MetaCognitionTick.run_async()`:

1. **Perceive** — perception card composes payload from real apparition retrieval against the parameter card's focal (real nomic + PageRank, no stubs; §8.1).
2. **Transform** — transformer card fires real GPT4All, streams `agent_token` WS frames (§10.1).
3. **Emit** — emitter card parses structured action JSON; applies via `ActionResolver` (CreateCardAction, LinkAction, WriteFieldAction, InvokeAction, …) **through the same lifecycle dispatcher (§10.2) that user gestures use**.

Response: `{ applied: { creates: N, links: N, writes: N, ... }, tokens: [...], rationale: "..." }`.

#### §12.2.1 The Agent As Recursion-Over-Iteration Integration Scheme (§1.1)

> "The agent is then auto-corrected over the space of world perceptions as initial conditions to a recursion-over-iteration integration scheme of purely conceptual computational topologies with hard-typed functional-object python endpoints and the initial data structures as base perceptions to transform and produce the final set of computations with through the graph." (user, verbatim, §1.1)

The agent's tick (§12.2) is, formally, **one step of an integration scheme** where:

- **State** = the agent's current AgentState subgraph (perception + transformer + emitter trio + their wired data) plus the workspace's current Real-register surface (the projector's chunk set).
- **Initial conditions** = the workspace's current set of **world perceptions** — every scanner-emitted chunk + every prior agent emission projected into the manifold (§9.12). These initial conditions are the *base perceptions* the integration begins from.
- **Step function** = the perceive → transform → emit triplet, executed as a single tick.
- **Recursion** = the autoregressive halo (§8.2.2) within the perception step + the cascade scheduler's downstream re-fire (§7.4) after the emission step — each tick *recursively touches* the parts of the graph the emit step modified.
- **Iteration** = the play/pause rollout (§7.5) and the signal-stream signal-advance (§4.6.1) — outer-loop iteration over sample-bank inputs while recursion runs the per-sample compute.
- **Topology** = the "purely conceptual computational topology" the user references — the typed concept graph (§3) with its hard-typed Python endpoints (§9.6 / §9.7). The integration is *over this topology*, not over a flat parameter space.
- **Endpoints** = the three foundational fixtures (§9.5) + materialised library functions (§9.7) — the hard-typed Python endpoints that ground the imaginary's computations in real Python execution.

**Auto-correction** is realised through the comparison-surface (§6.6) feedback: the agent's emitted outputs project to the projector (§6.6.1 perimeter); the next tick's perception reads the updated projector and the apparition surface around the agent's perception focal reflects the agent's prior emissions. The integration corrects course as outputs accumulate.

The "recursion-over-iteration" framing means the scheme runs *both* loops concurrently — recursion on the graph topology, iteration on the sample bank — and the agent's auto-correction operates on both. This is what makes the agent meta-cognitive in the §8D.38 sense: it observes its own outputs in the same observation space (the projector) it perceives the world through, and adjusts via further ticks.

### §12.3 Cascade Status (§7.4)

`GET /api/agent/cascade_status` returns per-agent fire counts, last-skip reasons, paused/cascade_enabled flags. The cascade scheduler short-circuits the agent's own emissions from re-triggering its perception in the same tick (§2.7).

### §12.4 Pause / Unpause / Termination

- **Pause:** `PATCH /api/concepts/<pcid> { data: '{..., "paused": true, ...}' }` halts the scheduler.
- **Unpause:** flip `paused` back; next tick resumes from saved state.
- **Termination:** delete the parameter card. The body subgraph dissolves; the evolution log records the lineage (§11.4).

### §12.5 Self-Extension (§8D.32.2)

An agent's emitter can spawn additional ConceptNodes — including new perception/transformer/emitter trios for sub-agents — through the same `CreateCardAction` + `LinkAction` paths. The recursion is bounded by the cascade scheduler's depth gate.

### §12.6 Simultaneous User + Agent Authoring (§8D.32.3)

Both actors operate the same editor surfaces. Conflict resolution is rollback (§2.6 / §11.4), not locks. The actor field in every `EditDiff` makes attribution unambiguous.

#### §12.6.1 The Editor As Functional Object — Agent / Editor Entanglement (§1.1 Imaginary)

> "the 2D concept editor itself is one of the fundamental building-block api functional objects that the specially designed agent computation graph interacts with and entangles itself with. The ultimate role of the agent computation graph, which is seamlessly integrated in structure and layout with its auto-complete-style suggestions over the conceptual computational space of each node, whether a functional-object node with Python bindings, or a concept node created by the user/scanned from shadow DOMs in the workspace." (user, verbatim, §1.1)

The 2D editor is **not a passive surface the agent edits**; it is *itself* one of the workspace's fundamental functional objects, on equal ontological footing with Database (§9.5), WebBrowser (§9.5), and the agent's own body subgraph (§12.1). The agent's reasoning is the imaginary register's expression *of the same graph it is operating on* — the entanglement is structural, not metaphorical.

The realisation in the existing schema:

- **`GraphEditor` API surface** — the methods of `backend/services/graph_editor.py` (`create_concept`, `update_concept`, `link_concepts`, `compile_node`, `expand_subgraph`, etc.) are materialisable as a python_object ConceptNode tree (§9.6) via the Python-API materialiser. They become Function-typed concept nodes the agent reaches identically to how it reaches `Database.search` or `WebBrowser.web_query`.
- **Emitter actions ARE editor calls** — the `ActionResolver` action catalogue (`CreateCardAction`, `LinkAction`, `WriteFieldAction`, `InvokeAction`, …) is exactly the editor's mutation surface, surfaced as the agent's emit vocabulary. Every emitter action is therefore a call to a Function-typed editor method through the lifecycle dispatcher (§10.2) — the same path the user's GUI gestures take.
- **Autocomplete is the entanglement's UX expression** — when the agent (or the user) types into an editable row's name field inside the agent's own body subgraph, the autocomplete (§4.7, §17.15) ranks candidates against *all* concept nodes including the agent's own perception/transformer/emitter trio. The agent can therefore name-reference its own internal cards as it composes downstream graphs, closing the recursion.

**The entanglement is the imaginary's reflexivity**. The agent's reasoning produces imagery (concept nodes, edges, renderings) in the same surface its perception reads from. Each tick (§12.2) is a *projection from real to imaginary* followed by an *emission back into the imaginary* that — through subsequent compiles (§7.4) — propagates back to the real (output projections per §9.12). The agent's full cycle is therefore: Real (perceive) → Imaginary (transform + emit) → Imaginary (autocomplete + halo retrieval over its own emissions) → Real (output projection) → Real (next tick's perception reads the updated projector).

This reflexive structure is what makes the agent *meta-cognitive* in the §8D.38 sense: the agent's own emissions become future perception material, so the agent reasons over the graph it is participating in.

### §12.7 Autonomous Tools

> "The autonomous agent can also do the same with exposure to these node interaction tools. Our fundamental tools include things like database and web search, generative tasks (prompts and meta-prompts), retrieval, web navigation, env state edits/navigation, and other agent computation graph editor prompts." (user, verbatim)

The agent's tool surface is the **same Function-typed ConceptNode set the user sees** (§9.6): no separate tool registry. Every method on the foundation fixtures (§9.5 / §9.5.1) and every materialised python_function from a user-imported module (§9.7) is reachable from the agent's emitter via `InvokeAction { card_id, method_name, inputs }`. The action travels through the lifecycle (§10.2) and produces the same WS frames the user's manual invocation would.

The autonomy tool catalogue therefore = the materialised Python-API surface ∪ the editor's own gesture grammar (§14.2). New tools are added by importing additional Python modules; no agent-specific shim is needed.

### §12.8 Fluid Agent Simulation (Forward Reference)

> "Agentic fluid simulation: The fully autonomous endpoint. Given user-tailored context aggregated from their knowledge graphs, personal notes, and conversation history over RAG, the system instantiates a general-purpose agentic distribution fluid simulation --- teams of domain-expert SLM agents that propagate through web search, deep research, and through-DOM retrieval, expanding the user's knowledge base iteratively without human steering. Each forward propagation produces a centroidal recommendation that the user can critique or allow to auto-integrate." (user, verbatim — long-horizon goal)

The fluid simulation is the agent system's long-horizon target: many parameter-card-anchored agents running concurrently, each with its own perception/transformer/emitter trio (§12.1), composing through shared apparition surfaces (§8.2). Each propagation step is a tick (§12.2). The "centroidal recommendation" is the consensus across the agent fleet's outputs in the projector (§9.14). The mechanics are already present in §12.1–§12.6; the fluid simulation is the framework's emergent behaviour when many agents spawn simultaneously. Single-agent ticks (§16.3) are the unit-scale exercise of this loop.

---

## §13 — The No-Mocks Contract (§8D.46)

> **Production paths run real subsystems. Always.** This section is the architectural statement of the **§0 all-real-tests-for-everything mandate (§Q.1)** — read §0 first. §0 governs *tests*; §13 governs *the running system*. Together: the system always runs real, and every test verifies it running real.

> "When you go to develop code and find 'fake' or 'dummy' implementations of things like SLMs or quantized embeddings or otherwise, revert the functionalities to ensure they use the exact real python code required to properly accomplish the full task." (user, verbatim)
>
> "We want to use mistral hermes 2 dpo and our dual embedding and triple parameter (tfidf, nous embeddings 1.6, and pagerank). Please enforce the use of mistral 2 dpo everywhere. No Llama allowed. Please ensure that we use CUDA in all our LLM runs." (user, verbatim)

The SLM target is `Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf` on CUDA — across backend defaults, every probe, every REPL action, every scenario. Llama is not a fallback. The embedder is `nomic-embed-text-v1.5.f16.gguf` on CUDA. The triple-product apparition score is `pagerank · tfidf_cos · nomic_cos` (§8.1); the two embedding axes (nomic over description, TF-IDF over rendering) never mix (§8D.17.1).

### §13.1 The Four Subsystems

See §1.6 table. The fake gates are **harness-only** and explicit; no production code path sets any.

### §13.2 The Contract

1. Production backend boots with all four real (`all_real: true`).
2. The full-smoke scenario set runs with real subsystems unless a scenario explicitly opts into a fake to test the degraded path.
3. Every probe and every `env-scenario` is valid against real subsystems.
4. `GET /api/subsystem_status` reports live state; CI asserts `all_real: true` before any contract-bearing scenario runs.

### §13.3 Operator Surface

```http
GET /api/subsystem_status →
{
  "ok": true,
  "all_real": true,
  "slm":       { "backend": "gpt4all",  "model": "Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf",
                 "loaded": true,  "fake_env": false },
  "embedder":  { "backend": "nomic",    "model": "nomic-embed-text-v1.5.f16.gguf",
                 "device": "cuda", "fake_env": false },
  "selenium":  { "backend": "selenium", "loaded": true,
                 "driver_class": "WebDriver" },
  "langgraph": { "backend": "langgraph","loaded": true,
                 "has_StateGraph": true }
}
```

REPL: `subsystem-status` action wraps the endpoint; the in-place viewer (§11.8) extends with a `subsystems` row.

### §13.4 No Quiet Degradation

- GPU → CPU embedder fallback is **permitted** (still nomic; just CPU). Logged at WARNING.
- Real-backend → stub fallback is **forbidden** in production for any subsystem.
- A failed load with no fake env = 503 + cascade halts + frames stop.

### §13.5 Llama Is Forbidden (§USER A.6, K.3)

The `_FAST_HARNESS_MODEL` Llama default is **deleted**. `_resolve_model_name()` in `slm_client.py` rejects any `WFH_SLM_MODEL=*llama*` override loudly. Probes and scenarios do not set Llama overrides.

---

## §14 — REPL ↔ Frontend Two-Way Feedback

> **The REPL is the verification surface.** Every gesture has a REPL action that performs the same backend mutation the frontend would. Every frontend mutation emits telemetry the REPL reads. The REPL ↔ frontend round-trip is the integration test (§USER J.1).

The REPL is the **Symbolic register** (§1.1, §1.5) of the workspace — the layer of complete transparency over the Real (3D Projector) and the Imaginary (2D Editor). In §1.1's framing:

> "Representations that are simple to understand yet comprehensive in their meaning and the transparency and visibility in every thing that happens both statically and dynamically within our app are invaluable and abstract. […] The notion that all interactions and operations and events within our app are not only fully recorded and accounted for in our console-render of the app, our REPL, purely realizes the computation graph of the app itself within its own symbolic space that agents and humans can interact with in the terminal and see the feedback of in both the real live full-stack app, as well as the simplified effects rendered to a statically-structured console with more like a dynamic screen update to it than a regular infinite-scroll. Thus, other than its completeness, the symbolic realm hasn't got much to say on its own without external input and feedback." (user, verbatim, §1.1)

The REPL's role is therefore:

- **Total legibility** — every mutation, render, and telemetry event is captured as a typed gesture (§14.2), a REST/WS frame, a `ui_state_changed` mirror update (§10.5), and a row in the in-place activity viewer (§14.5 / §11.8). The REPL transcript IS the workspace's symbolic-register representation of itself.
- **No autonomous semantics** — the Symbolic register has no native content. Its completeness derives from its faithful mirroring of the Real and Imaginary. A REPL action that fires without effect on either the Real (projector) or the Imaginary (editor) is a bug; a Real/Imaginary state that isn't reflected in the Symbolic (telemetry + viewer) is a *severance* (§18.1).
- **Bidirectional drive** — humans AND agents interact with the workspace through this same Symbolic surface. The agent's `InvokeAction` emissions, the user's REPL `step` commands, and the GUI's gesture-driven mutations all enter the lifecycle dispatcher (§10.2) identically.
- **Static-structured dynamism** — the in-place viewer is *dynamic-screen-update* (cursor codes, in-place row refresh) rather than *infinite-scroll-log*. The structure stays fixed; the variables update. This is the Symbolic register's signature affordance: a *legible permanence* that mirrors the *transient permanence* of the live app.
- **Transcendental permanence** (§1.1 gap-fill) — the REPL **purely realises the computation graph of the app itself within its own symbolic space**. The app's full conceptual structure — the four-fixture functional-object graph (§9.5), the lifecycle dispatcher (§10.2), the cascade scheduler (§7.4), the halo retrieval (§8.2), the autoregressive feedback (§8.2.2) — is *itself* a computation graph the REPL faithfully represents. The Symbolic register is therefore not just a *log* of the app's activity but a *running representation of the app's own structure as a computation graph*. This is the transcendental property the §1.1 update names: the app's representation of itself shares the same philosophy as the thing being represented, which is the *permanence of its ultimate form* — the app is *self-similar* across the registers it composes through.

> "You should not rely on the preview to assess the completeness of your answers because the features I requested aren't present, even if you can see an image." (user, verbatim)
>
> "Note that you should not use the preview eval, and rather ensure our REPL functionality is correct in the terminal, since its the true 'preview eval' we're going for." (user, verbatim)
>
> "You must focus your development and scenario test efforts on the REPL and ensure that the REPL is only interfaced with via the frontend actions and results. This means anything you interact with in the REPL, shows up in the real frontend, and when the frontend does something and sends telemetry of what changed, that also shows up in the CLI." (user, verbatim)
>
> "Please expand on comprehensively covering the full set of possible gesture activities that should be possible as they are laid out in the design. […] All the bells and whistles should be included in at least one instance for every mentioned design feature and corresponding gesture-output interactions in our REPL" (user, verbatim)

A screenshot is **not** feature proof. The verification chain is REPL action → backend mutation → WS frame → frontend renders → telemetry → REPL reads. The gesture catalogue (§14.2) enumerates every design-mentioned gesture; each row must have a REPL action AND an env-scenario asserting the round-trip (§14.4 acceptance bar).

### §14.1 The Verification Loop

```
REPL action
   │
   ▼
backend mutation (through lifecycle dispatcher, §10.2)
   │
   ▼
WS frame broadcast (§10.1)
   │
   ┌──────────────────────────┬──────────────────────────────┐
   ▼                          ▼                              ▼
frontend renders        peer REPL tab           UI State Service mirror (§10.5)
   │                          │                              │
   ▼                          ▼                              ▼
telemetry POST          ws.frames drain               in-place viewer (§11.8)
to /api/ui/telemetry        ready for                  refreshes
   │                       env-scenario
   ▼                       assertions
ui_state_changed WS
   │
   ▼
REPL reads back the
mutation's effect
```

A screenshot is not feature proof; the verification chain is REPL action → backend mutation → WS frame → frontend renders → telemetry → REPL reads (§2.9).

### §14.2 Functional Sequences (the Gesture Catalogue)

Every design-mentioned gesture has at least one REPL action and at least one env-scenario covering it.

| Gesture | REPL action | Backend mutation | WS frame | Frontend renders | Telemetry |
|---|---|---|---|---|---|
| Hover 3D node | `ui-hover { chunk_id }` | UI State (transient) | `ui_state_changed` (debounced) | hover billboard at projected screen rect | `halo_focus` updated if halo active |
| Click 3D node (pin) | `ui-pin { chunk_id, rect }` | UI State | `ui_state_changed` | pinned panel at exact rect (§4.2) | `pinned_panels[]` adds entry |
| Drag pinned panel | `ui-pin-move { panel_id, top, left }` | UI State (§17.12) | `ui_state_changed` (kind=pin_chrome) | panel translated | `pin_chrome[panel_id].{top,left}` updated |
| Resize pinned panel | `ui-pin-resize { panel_id, width, height }` | UI State (§17.12) | `ui_state_changed` (kind=pin_chrome) | panel sized; body overflow scrolls | `pin_chrome[panel_id].{width,height}` |
| Minimise pinned panel | `ui-pin-minimise { panel_id, minimised }` | UI State (§17.12) | `ui_state_changed` (kind=pin_chrome) | body collapses | `pin_chrome[panel_id].minimised` |
| Close pinned panel | `ui-pin-close { panel_id }` | UI State `unpin` (§4.2) | `ui_state_changed` (kind=unpin) | panel removed (3D node persists) | `pinned_billboards[]` loses entry + `pin_chrome[panel_id]` cleared |
| Latch toggle | `ui-latch-toggle { card_id, latched }` | UI State (§17.13) | `ui_state_changed` (kind=latch) | slide-out side panel; equal-height contract (§4.4) | `latch_state[card_id]` flipped |
| Double-left-click compile expand (§7.3.4) | `ui-compile-expand { card_id }` | Compile pipeline (§7.1) | `concept_changed` × N children + `ui_state_changed` | simplified subgraph (§7.3) | `compile_expansions[card_id]` populated |
| Double-left-click compile collapse (§7.3.4) | `ui-compile-collapse { card_id }` | Delete child concepts (§10.2) | `concept_changed` × N + `ui_state_changed` | children dissolve; panel restores | `compile_expansions[card_id]` cleared |
| **Right-click node-fold expand (§7.3.4)** | `ui-node-expand { card_id, node_path }` | UI State inline next-rank type-graph (§9.6.1) | `ui_state_changed (kind=node_fold)` | next-rank subtree (superclass / property / function I/O) unfolds inline | `node_fold_state[card_id].expanded_paths += node_path` |
| **Right-click node-fold collapse (§7.3.4)** | `ui-node-collapse { card_id, node_path }` | UI State (§7.3.4) | `ui_state_changed (kind=node_fold)` | subtree folds; per-subtree fold state preserved (§18.32); base-node path collapses to self | `node_fold_state[card_id].expanded_paths -= node_path` |
| Type into name | `concept-rename { id, new_name }` | Lifecycle (§10.2) | `concept_changed` | header text updates | — |
| Type into description | `concept-edit-description { id, text }` | Lifecycle + nomic re-embed | `concept_changed` + `concept_index_update` | description updates; apparitions refresh | — |
| Type into data row | `concept-edit-data-row { id, path, value }` | Lifecycle + field-tree merge | `concept_changed` | data row updates; cascade re-fires downstream | — |
| Plus-sign add child | `field-tree-add-child { row_id, key, value }` | Lifecycle | `concept_changed` | new row indented one level (§4.6) | — |
| Plus-sign add sibling | `field-tree-add-sibling { row_id, key, value }` | Lifecycle | `concept_changed` | new row at same level | — |
| Autocomplete open | `ui-autocomplete-open { row_id, query, parent_card_id? }` | UI State (§17.15) + `apparition_service.completions` | `ui_state_changed` (kind=autocomplete_open) | dropdown appears under row | `autocomplete_state = {row_id, query, candidates, parent_card_id}` |
| Autocomplete close | `ui-autocomplete-close { row_id }` | UI State (§17.15) | `ui_state_changed` (kind=autocomplete_close) | dropdown dismisses | `autocomplete_state = null` |
| Autocomplete query (raw) | `concept-completions { prefix, parent_card_id? }` | Concept Index ranking (§8.1 / §4.7) | (REST only) | (mirror update via separate POST) | populated by ui-autocomplete-open |
| Compile button | `conceptual-compile { concept_id, use_slm, persist_rendering }` | `ConceptComputeNode.compile` (§7.2) | `concept_changed` | rendering pane updates; kind chip | — |
| Compile chain | `conceptual-compile-chain { focal_id, max_depth, use_slm }` | LangGraph StateGraph walk (§10.6) | `concept_changed` × N | chain renderings populate | — |
| URL eye-button | `ui-url-visibility { url, hidden }` | UI State (animate loop reads) | `ui_state_changed` | every chunk/hub of URL gets `scale=0` (§6.3) | `hidden_urls[]` updated |
| URL × button | `ui-url-purge { url }` | Purge handler (§6.5 scoped) | `purge_workspace` (scoped) | URL removed from scene + sidebar | `pinned_panels[]` drops affected |
| Domain tree click | `ui-domain-toggle { url }` | UI State | `ui_state_changed` | URL's hub collapse toggled | — |
| Result-row hover | `ui-hover-row { row_id, chunk_id }` | UI State | `ui_state_changed` | unified panel near row | `halo_focus` if applicable |
| Result-row click | `ui-row-click { chunk_id }` | UI State (set `chunkCollapseTarget=0`) + camera tween + pin | `ui_state_changed` | chunk extrudes; camera flies; panel pins | `pinned_panels[]` + `viewport_visible_rows[]` |
| Scroll retrieval list | `ui-viewport-spine { ordered, total }` | UI State (§17.14) | `ui_state_changed` (kind=viewport_spine) | `IntersectionObserver`-driven; per-row `chunkCollapseTarget` flip (§8.3) | `viewport_visible_rows = {ordered, total}` |
| Spine delta to agent | `spine-delta { popped, folded }` | `apply_spine_delta_to_active_agents` (§12.1) | `ui_state_changed` (if active agent emits) | agent zone_of_influence updated | — |
| Rollout play | `rollout-play` | Rollout coordinator (§7.5) | `rollout_resumed` | play/pause indicator | `rollout_state.paused: false` |
| Rollout pause | `rollout-pause { node_id }` | Rollout coordinator | `rollout_paused { sample_idx, current_node_id }` | edit affordances revealed on the paused node | `rollout_state.paused: true` |
| Rollout step | `rollout-step { sample_idx }` | Rollout coordinator | `rollout_paused` (next sample) | next sample's outputs visible | `rollout_state.sample_idx` |
| Halo open | `apparition-surface { card_id, k }` | `apparition_service.surface_for(card_id)` (§8.2) | (REST only; subsequent `ui_state_changed` for `halo_focus`) | halo phantoms radiate around focal | `halo_focus` |
| Apparition click → wire | `concept-edge-create { source_id, target_id, edge_type }` | Lifecycle (§10.2) | `concept_changed` × 2 | edge drawn; cascade re-fires | — |
| Agent spawn | `agent-spawn { goal, name? }` | `spawn_agent_body_subgraph` (§12.1) | `concept_changed` × 4 + edges | four cards appear wired | — |
| Agent tick | `agent-tick { parameter_card_id }` | `MetaCognitionTick.run_async` (§12.2) | `agent_token` stream + `concept_changed` × emissions | tokens stream into panel body; emissions render | — |
| Scan | `web-query { url, query?, samples }` | `WebBrowserManager.web_query` (§9.6) | `chunk_added` × N → `umap_canonical` → `done` | chunks materialise; UMAP snap; spine ready | `scan` row in viewer |
| Recompute UMAP | `recompute-umap { workspace_id? }` | Layout Service joint 6D fit (§6.1, §10.3) | `umap_canonical` (carries x,y,z,h,s,v per chunk) | chunks tween to canonical positions; HSV phase calibrates | — |
| Purge workspace | `purge-workspace { workspace_id, confirm: "erase" }` | Purge handler (§6.5) | `purge_workspace` | scene cleared; sidebar refreshes | all UI state cleared |
| Rollback edit | `evolution-rollback { edit_id }` | Rollback (§11.4) | `evolution_diff` (the rollback itself) + `concept_changed` (for restored target) | restored state renders; history shows rollback | — |
| Subsystem status | `subsystem-status` | `GET /api/subsystem_status` | (REST only) | (REPL print) | viewer's `subsystems` row |
| **Graph-mutation: create** (§S — panel gesture or agent emit; no `Editor` object) | `editor-create { name, description?, data? }` | Lifecycle (§10.2) + §17.1.1 | `concept_changed (created)` | new card materialises in editor | `evolution_diff` actor=editor |
| **Graph-mutation: link** | `editor-link { source_id, target_id, edge_type?, source_port?, target_port? }` | Lifecycle (§10.2) + §17.1.1 | `concept_changed (linked)` × 2 (source + target) | hard link drawn on commitment fan (§3.2.1) | `evolution_diff` actor=editor |
| **Graph-mutation: overwrite** | `editor-overwrite { node_id, name?, description?, data? }` | Lifecycle field-merge (§10.2) + §17.1.1 | `concept_changed (modified)` + cascade `concept_changed` × N downstream | edited field re-renders; downstream cascades fire | `evolution_diff` actor=editor |
| **Graph-mutation: delete** | `editor-delete { node_id }` | Delete-lifecycle (§10.2) + §17.1.1 | `concept_changed (deleted)` | card removed; `{var}` refs in dependents mark broken (§9.11) | `evolution_diff` actor=editor (rejected for §9.5 fixtures) |

> §S note: the four rows above are the concept-graph **mutation gestures** of the unified panel scheme (the REPL `editor-*` action names + the `actor=editor` evolution-log tag are retained verbatim as the gesture-driver/actor labels). They are **not** a Function-typed `Editor` *fixture* (removed, §9.5) — a panel edit / `{var}` auto-create / right-click compile *is* a create/link/overwrite, and they route through `/concepts` + `/concept_edges` (the same lifecycle the agent emitter uses).
| **Signal-stream advance** | `ui-signal-advance { card_id, field_path }` | Rollout coordinator (§7.5) + UI State (§17.1.2) | `ui_state_changed (kind=signal_advance)` | visible signal swaps in place in panel; cascade re-fires downstream | `signal_stream` mirror row updated |
| **pattern_map iteration** | `ui-signal-advance { card_id: pattern_map, field_path: "pattern_hash" }` | §17.1.3 | `ui_state_changed (kind=signal_advance)` | next chunk-pattern visible; golden trio + sampled chunks update | viewer `pattern-map` row |
| **WebBrowser.scan** | `web-scan { url, query? }` | `WebBrowserManager.scan` (§9.5.1) + §17.1 | `chunk_added` × N → `umap_canonical` (6D) → `pattern_map` materialises → `done` | chunks stream into projector with HSV state; pattern_map panel appears | `scan` row + `pattern_map` row |
| **Database.search** | `database-search { query, cypher? }` | `Database.search` (§9.5.1) | (REST only) | chunk result rendered as unstructured list | — |
| **Database.concept** | `database-concept { node_id [or list] }` | `Database.concept` (§9.5.1) | (REST only; subsequent signal-stream WS frames if iterated) | rank-1 KG around node rendered as panel | `signal_stream` if iterating list |
| **Agent.meta_prompt / .prompt / .output** | `agent-meta-prompt { text }`, `agent-prompt { text }`, `agent-output { schema? }` | Agent fixture's three primitives (§9.5.1) | `agent_token` stream + `concept_changed` on output | tokens stream into chain's terminal node; pydantic-validated result lands | — |
| **Library middleware materialise** | `library-import { qualified_name }` | `python_api_materialiser` middleware (§9.7) | `concept_changed` × N (one per materialised Object/Property/Function) | new peer python_object tree appears in editor | — |
| **URL-set panel reference** | (typed via `{urls_panel}` in any scan input field) | Compile resolves `{urls_panel}` via §15.9 inheritance; iteration per §17.1.4 | `ui_state_changed (signal_advance)` per URL | each URL fires its own scan signal | viewer `urls-panel` row |

The catalogue is **complete-by-design**: any new gesture introduced by code must extend this table with its REPL action, mutation, WS frame, frontend render, and telemetry contract. A feature without all five entries is not integrated (§14.4).

### §14.3 Idempotency in the REPL Loop

Every REPL action carries an optional idempotency key. Replays during a flaky run produce the same effect once. The full-smoke scenario relies on this for retry-safe pre-conditions.

### §14.4 Acceptance Bar

A feature is **complete** when:

1. It has at least one REPL action covering it (§14.2).
2. It has at least one env-scenario asserting the round-trip.
3. The full-smoke scenario set (`env-scenario --name full-smoke`) passes in both **real-stack** mode (`all_real: true`; §13.2) and **stub mode** (`WFH_FAKE_*=1`).
4. The in-place viewer (§11.8) reflects the feature's observable state without introducing a new log stream.

### §14.5 REPL In-Place Activity Viewer (§11.8)

A `watch-activity` REPL subcommand renders a **fixed-structure terminal dashboard** that updates **in place** via ANSI cursor codes (`\x1b[<n>A`, `\x1b[2K`). Six rows (extensible for advanced modes; e.g., agent, subsystems):

```
─── Workspace Activity (in-place) ─────────────────────────────────────
  scan        | <action> | <progress> | <umap status>
  retrieval   | <query>  | <hit count> | <viewport range> of <total>
  visible 3D  | [chunk:...]                          (<n>/<total>)
  hidden 3D   | [chunk:...]                          (<n>/<total>)
  pinned      | [panel:p_X → chunk:c_Y ("name")]    (<n> pinned)
  compile     | <expansion state>  central=<id>  children=<list>
─────────────────────────────────────────────────────────────────────
```

Bounded lines, identifier abbreviation after first occurrence, multi-line values flattened with `↩`. Sources per row:

| Row | Source frames / endpoints |
|---|---|
| `scan` | `chunk_added` / `chunk_removed` counts + `umap_canonical` + REST `/api/scan-status` |
| `retrieval` | REST `/api/chunk_search` (mirrored at action time) + `ui_state_changed` viewport |
| `visible 3D` | UI State `visible_chunk_ids` (spine-delta emitter; §8.3) |
| `hidden 3D` | complement of `visible 3D` against workspace chunk set |
| `pinned` | UI State `pinned_panels` |
| `compile` | UI State `compile_expansions` |

Last-write-wins per field. Viewer reads only WS broadcast + low-cadence REST polls; never queries DB directly. Scenario sub-mode accepts inline gesture commands (`s`/`S` to scroll, `c <row>` to click, `r <token>` to right-click-fold the inline type graph (§7.3.4), `D <panel>` to double-left-click-compile) so the operator can drive the use case from a single terminal.

The six rows are the **observable surface** of the lodestar use cases (§16). New observable state must extend an existing row, never spawn a parallel log stream.

---

## §15 — DOM Scanning, Distillation, and the Web Ontology

### §15.1 Selenium-Backed Scanner

`WebBrowserManager` (`backend/services/selenium_client.py`) is the singleton Selenium handle. Headful Firefox via geckodriver. The eager init in the lifespan handler resolves `fixture::web_browser::<wsid>`'s backing pointer.

Scan entry: `WebBrowserManager.web_query(url, query?, samples)` — recursive DOM scan with optional search-input discovery; implicit pagination (next-page button pressed iff more samples remain; stale pagination triggers transition back to a previous URL).

**ShadowDOM as a simplest-possible OO type (N.1).** The scan's output is a simplest-possible object-oriented Python `ShadowDOM` object whose base functions/relations (`search`, `paginate`, `chunk`) are the **rank-1 structure** surfaced in the 2D editor (§9.6.2), while the **full per-sample chunk distribution lives in the 3D projector** (§6): the 2D tree carries the minimal compute-perception, the 3D carries the distribution. The `dom` output port of a wired `scanner` reference (§9.6.2) infers the `ShadowDOM` type and shares the live object into the 3D GUI.

### §15.2 Shadow-Aware Extraction

Extraction is JS-side (`extract()` walks `document.documentElement`); shadow roots traversed recursively; serialised as `<template shadowrootmode>`. XPaths use `#shadow-root` as a path step (§USER F.1; legacy §5.3).

### §15.3 Merge-Tree Deduplication

Master tree initialised from first snapshot; subsequent snapshots merge by structural signature (`tag | id | href | src | data-id | data-index | aria-label | txt:first30chars`). Additive — never prune by content hash (legacy §3.3 caveat preserved).

### §15.4 Distillation and Chunk Emission

`ChunkBuilder._recurse_absolute_trie` walks the content tree top-down and emits one chunk per **homogeneous repeating pattern** with commutation > 1 (§4.3 legacy). Two gates:

1. Pattern has ≥ 2 members.
2. Members are *homogeneous* (same generalised child-pattern set).

Heterogeneous siblings are skipped (cross-member field pollution); homogeneous patterns emit one chunk with N members + a representative. Post-pass `filter_redundant_rollups` prunes any oversized ancestor surviving the size gate.

### §15.5 Web Ontology — Compiled-From-Scans Cards (§8D.39)

Each scan derives, persists, and surfaces:

| Card type | Backing | What it represents |
|---|---|---|
| `SearchableURL` | `searchable_url::<hash>` | A URL whose DOM exposes a search-input field; ports = (query, samples) → list[ChunkInstance] (§9.8) |
| `DetectedAccessor` | `detected_accessor::<hash>` | A field-selector observed during scan; inputs = (DomSnapshot) → value |
| `XPathPattern` | `xpath_pattern::<hash>` | A generalised xpath; inputs = (DomSnapshot) → list[accessor_mapping]; carries editable accessor table (§5.4 / §8.7) |
| `PinnedComponent` | `pinned_component::<hash>` | A user-pinned DOM subtree saved for cross-page application |
| `ChunkInstance` | `chunk::<id>` | The canonical unit chunk emitted by `ChunkBuilder` (§15.4) |

These are **peers of the foundation fixtures** (§9.5), not children of Database. They are how the workspace's empirical structure becomes graph-editable.

### §15.6 Compile Invalidation on Backing-Pointer Update (§8D.39.6)

When a backing pointer's version bumps (e.g., scanner re-detects a pattern with a refined accessor), the compile-cache for every ConceptNode referencing that pointer invalidates. Cascade re-fires affected downstream nodes (§7.4).

### §15.7 URL-Set Knowledge Panel — `{urls_panel}` Input Aggregator (§1.2.1)

The user's framing draws this directly: *"Chunk pattern ontologies over sampled patterns should also be clearly linked to their queried urls to the web-browser's scan function. So we would build a url set within a user-created knowledge panel card (note url-specific tokenization within our tfidf vectorization but not quantized transformer retrieval) including a description of the evolving set of urls in the panel card that are referenced as external variables in their fields, which are automatically created as computational graph nodes for single-key:value minimalist field editing when the fields are clicked."*

A URL-set knowledge panel is, then, a user-created concept node like any other, but its content is specialised toward holding an evolving list of URLs as a multi-line pure-print tree. The user gives it a name slug — `archive_libs`, say — and a description recording intent and provenance (what these URLs are for, where they came from, what shape the evolving set is taking). The `data` field holds the URLs themselves, one per line, with tabs available to indent grouped sub-lists when the user wants to organise URLs into clusters. Each URL is automatically materialised as a single-key:value computation graph node the moment the user clicks on it (§4.6's progressive build) — so a long list of URLs sits as plain print until the user opens any one URL for editing, at which point that URL becomes a referenceable node in the compute graph with its own `{var}` slug, and the user can grow it into a fuller panel by adding child rows. Content detection assigns the panel the type tag `url_set` (§15.9), and the URLs themselves are vectorised through the TF-IDF axis under a url-specific tokenisation rule that splits on `/`, `?`, `&`, `=`, and `.` so that scheme, host, path-segment, query-key, and query-value all become distinct tokens. The nomic (quantised transformer) retrieval path does *not* take URLs, per the user's note — URLs go through the TF-IDF axis only.

Where the URL-set panel pays off is at the scan input port. A `WebBrowser.scan` function node's `url` input accepts `{urls_panel}` as a reference, and on compile the panel resolves to the URL set; the scan is fired once per URL under the signal-stream constraint of §4.6.1, with the panel displaying the currently-iterated URL's scan as the visible signal and the play/pause stepper (§7.5) advancing through the URLs in order. The URL-set panel is the canonical pattern for multi-URL scan workflows — what the user calls *the evolving set of urls* — and the same pattern generalises to any input-type-collected panel where multiple values of one type are aggregated for iteration into a downstream function.

### §15.8 Chunk-Pattern Schema, Golden-Trio Rule, `pattern_map` Output (§1.2.1)

The user's framing again: *"The scanner would then automatically fill in the blank chunk pattern fields, which then compile into the full and completely structured tree of each chunk patterns (golden-trio pattern rule for content-precise extraction alongside the generalized xpath patterns within the chunk pattern collections that provide our sampled chunk nodes in our scan GUI). This is where our iterative minimal value rendering to inherited typed functional inputs, our automatic function call link to our typed/named output panels that produces xpath chunk pattern schemas and their most recently computed set of new samples."*

What the scanner produces, for each homogeneous repeating pattern (§15.4) it discovers during a scan, is a *chunk-pattern schema* — a typed tree carrying the pattern's identity (a hash of its generalised xpath), the URL where the pattern was first discovered (which becomes the root of the schema; subsequent visits to other URLs that match the same pattern extend the same schema rather than spawning a new one), the generalised xpath itself, an accessor map (§8.7) from field slug to relative xpath, the golden trio (§15.8.1 below), the most-recently-computed set of sampled chunks the pattern has produced, and the PageRank of the pattern within the chunk-pattern graph. The schema is automatically filled by the scanner — the operator and the agent do not author chunk patterns by hand; they materialise as outputs of `WebBrowser.scan` (§9.5.1) and they update live as further scans land.

#### §15.8.1 Golden-Trio Pattern Rule

The user names the rule directly: *"golden-trio pattern rule for content-precise extraction alongside the generalized xpath patterns"*. The golden trio for each chunk pattern is the three structurally load-bearing fields whose joint presence makes the pattern content-precise — that is, a high-precision extraction that doesn't pick up false positives from nav blocks, footers, or other repeating-but-uninteresting structural matches.

The three roles are *title*, *link*, and *content*. The title field is the highest-IDF text-bearing field across pattern members, preferred to be inside an `h1`/`h2`/`h3` or other heading-tagged subtree when one is present. The link field is an `<a href>` whose href is intra-domain and points to a resource rather than navigation, preferred to be the link the title field anchors. The content field is the longest free-text-bearing field per pattern member, preferred to be a paragraph-shaped subtree. So a pattern that produces, say, an archive.org search result card might have its title at `<h3>The Princeton Library Chronicle</h3>`, its link at `<a href="/details/library-chronicle">`, and its content at `<div class="snippet">A research collection of…</div>`, and that's the golden trio for that pattern.

The trio is co-extracted under joint-presence: a pattern member is included in the sampled chunk set if and only if all three of the trio fields resolve cleanly (non-empty after distillation). The joint-presence rule is what produces the *content-precise* sample set the user calls for — nav blocks, footers, sidebar widgets, and other repeating-but-uninteresting structural matches typically lack one or more of the trio (a footer link has a link but no title or content; a heading-only nav block has a title but no link to a resource), so they fall out of the sample set by failing the test. The trio is complementary to the generalised-xpath patterns of §5.2 — the generalised xpath defines the structural family, and the golden trio defines the content-density gate within that family — and both surface in the chunk-pattern schema's `accessor_map` as named accessors the user can reference downstream.

#### §15.8.2 The `pattern_map` Output

The user names the output panel directly: *"live updates to the structured chunk pattern schema to our name output field in our scan, like pattern_map or something that produces chunk sample queries over pageranked linked chunk vectors that have links to the chunk pattern skeletons within the recursive tree structure"*. `WebBrowser.scan`'s primary output is therefore the `pattern_map` — a typed and named output panel that materialises as a Function-output ConceptNode whose `data` field is a recursive tree of chunk-pattern-schema records, one per detected pattern, with each entry carrying the `url_root`, the generalised xpath, the golden trio, the sampled chunks, the PageRank, and a `sub_patterns` field for any nested patterns found within the parent (a card-grid pattern might have a card sub-pattern, for instance).

The `pattern_map` updates live as the scan streams: each newly-detected pattern adds a new top-level entry, each newly-sampled chunk per existing pattern appends to that pattern's `sampled_chunks`, PageRank refits incrementally over the chunk-pattern graph as new patterns and samples land, and the TF-IDF and nomic indices (§8.1) update incrementally so the chunk vectors are usable for retrieval the moment they materialise. The frontend's `pattern_map` panel displays the schema under the signal-stream constraint (§4.6.1) — when the user iterates over the `pattern_hash` keys, the visible signal is one pattern at a time, and the play/pause stepper (§7.5) advances through them. Each pattern entry carries links back to its chunk-pattern skeleton within the recursive tree structure, so the user clicks any pattern entry to descend into its chunks (each chunk being a `ChunkInstance` ConceptNode, §15.5) without ever leaving the panel anatomy.

This is what the §1.2.1 spec calls *iterative minimal value rendering to inherited typed functional inputs* — the `pattern_map` output is a structured-template tree whose values are inherited from the input types, with the URL set as the source-of-truth root, each pattern entry's `url_root` field inheriting one URL from the iteration, and the chunk samples inheriting field types per the golden trio. The whole structure composes through the typed-link inheritance of §15.9 so downstream functions consuming the `pattern_map` (a `Database.concept` walk over the sampled chunks, say, or an `Agent.prompt` whose template references golden-trio fields) inherit the fully-decomposed type chain without the user having to wire anything explicitly.

### §15.9 Type-Inclusion via Inheritance and Content-Pattern Detection (§1.2.1)

The user names the principle in §1.2.1: *"There is type-inclusion via inheritance as well with referenced passthrough of our various panel/computational graph based data structures via their content patterns."* The workspace tracks content patterns for each materialised type — URL, date, currency, email, hash, xpath, chunk instance, pattern schema, and the rest — through a combination of regex patterns for primitive types, named tree patterns for structured types (a chunk-pattern schema is itself a named tree pattern; so is the URL-set panel of §15.7; so is the agent body subgraph of §12.1), functional-link inheritance through `{var}` references (when a field's value is a `{var}` reference, the field inherits the referenced concept's type through the typed-edge chain of §3.2.1, so a `{urls_panel}` reference into a `WebBrowser.scan.url` input port means the `url` port inherits `url_set` from the panel and unpacks it under the signal-stream constraint), and passthrough composition (when a Function node's output type is itself a typed reference — the `pattern_map`, for instance, carries chunk-pattern-schema records that reference chunk instances — downstream Function nodes that consume the output inherit the fully-decomposed type chain). The library-imports middleware of §9.7 extends this type detection to any imported Python library, so `inspect`-derived types from a newly-imported module become first-class types in the inheritance graph and compose with the four-fixture types uniformly through the same typed-edge mechanisms.

**Object-instance inheritance (M.11).** Type-inclusion extends to *instances*, not only types: when the user connects a live object — say a `WebBrowser` instance — to a field in their own compute-knowledge-panel, that field inherits the *instance's* object model (its bound property values + its function memory maps), not merely the `WebBrowser` type. Right-clicking the field then expands (§7.3.4) into the bound instance's typed panel form (§9.6.1) — `driver: WebDriver = {driver}` resolving to the *actual* driver the instance holds — so the user's panel composes over a live object rather than an abstract signature. The binding is a typed `{var}` reference (§3.2.1, §4.7) whose target is the instance node; the inheritance is the recursive resolution of that reference's object model to the unfolded depth, and the connected instance is itself drivable as part of the reservoir substrate (§7.8).

**Type abstraction integrates top-down and bottom-up jointly (§O.8/§O.15).** The dominant authority is the materialized API-object ontology (§9.6) — a field bound to an API node takes the **API-declared type**, propagated downward — but this composes **jointly** with bottom-up inference observed from wiring/value (§9.8) for user-authored or unbound slots, each method applied wherever it is applicable (§O.15). The "increasing levels of type abstraction" the design seeks is *climbing the API object's ontology chain*: a field's concrete type → its declaring class → that class's superclass (`super:`), and a function's `FUNCTION_OUTPUT_TYPE` → that type's own structure. So inference is **ontology lookup + downward propagation** (the §7.7 output-type inference reads the function's API-declared output type), abstraction rising as one folds *up* the ontology and concretion as one unfolds *down* into a bound type's rank-1 structure.

### §15.10 Timed Full Scan as an Exposed Functional-Object Property (§Q.2)

> "A full scan can be run on archive.org for a set amount of time, which is an exposed property in the graph editor functional-object framework over python-exposed API objects such as SLM agents, webbrowser, database..." (user, verbatim, Q.2)

The WebBrowser fixture's `scan` (§9.5.1) and the compiled-from-scans `SearchableURL` nodes (§15.5) carry a **`duration_s` input port** (§9.8) — the **time-box** of a full scan, exposed in the graph editor exactly like `query` and `samples`. This is the Q.2 requirement: a *full* scan (not merely a sample-bounded one) that runs for **a set amount of wall-clock time** — e.g. "scan `https://archive.org/search?query=university+library` for 60 seconds" — surfaced as a **first-class, user-settable functional-object property** over the python-exposed API objects.

**Semantics.**

- `duration_s = 0` (default) → **sample-bounded**: the scan stops at `samples` chunks (the legacy behaviour, §9.5.1 / §16.1).
- `duration_s > 0` → **time-bounded**: the scan paginates and emits chunks continuously until `duration_s` wall-clock seconds elapse, then finalises (final UMAP fit, `done` frame). `samples` becomes an *upper bound* rather than the stop condition; whichever bound is hit first stops the scan. A "full scan for N seconds" sets a generous (or unbounded) `samples` and a finite `duration_s`.

**Plumbing (down-flow).** `duration_s` rides the whole stack as one value: the `scan` port schema (§9.8) → the `POST /api/web_browser/scan` + `/api/snapshot` request models (`duration_s`, `code_specs/backend/api.md`) → `trigger_snapshot(..., max_duration=duration_s)` → `mapper.snapshot(max_duration=…)` (`backend/dom/pipeline.py`, `code_specs/backend/scanner.md`) → the REPL `web-scan { url, query?, samples?, duration_s? }` action (§14.2, `code_specs/repl.md`). The previously hard-coded `max_duration=180` becomes the **default** when the port is unset, not a fixed ceiling.

**The Q.2 framing — halos over the readout.** Q.2 ties the timed scan to "ray-projected apparition similarity halos [popping] up for dynamically rendered computation graph node/knowledge panel procedural forward-inverse data structures through computation generation over conceptual reservoir readouts." Operationally: a timed `scan` node is a functional-object whose `{chunk samples}` output (rank-1 in the Imaginary, full distribution in the Real, §6.6.3) feeds the **reservoir readout** (§7.8); the readout panels are embedded into the **same blended halo search space** as data chunks (§8.1 / §O.22), so the **apparition halo** (§8.2, ray-projected per §8.2.1.1) radiates candidates against the dynamically-rendered scan-readout panel — the forward-inverse data structure (§7.7) of "scan → chunk samples → inverse-looked-up inputs → procedurally-rendered outputs." The time-box is what makes "run a *full* scan over archive.org" a bounded, repeatable operation the reservoir can iterate over (§16.4).

**Verification.** All-real (§0): `scripts/probe_live_archive_scan.py` extended to set `duration_s` and assert the scan honours the wall-clock bound against live Selenium; REPL `web-scan` with `duration_s` and the `timed-scan-duration-port` env-scenario (§14.4).

---

## §16 — Lodestar Use Cases

The design's acceptance bar. All four must hold against real subsystems on every commit (§13.2).

### §16.1 §8D.45 — Archive.org University Library (outside-in)

The workspace boots empty, with only the three foundation fixtures alive — Agent, WebBrowser, Database (§9.5; §S removed the former fourth, Editor) — and the user begins where the §1.5 Real register begins: outside, in the world the projector measures. They drop a URL-set knowledge panel onto the canvas (§15.7), give it a name like `archive_libs`, write one URL into it (`https://archive.org/details/texts`), and reference that panel as `{urls_panel}` from a `WebBrowser.scan` function node's `url` input port. They wire the scan node's `query` input to a literal `"university library"` (or to a separate concept node carrying that string), and they press compile. The scan fires per §17.1 — chunks stream into the projector at their preliminary radial positions, 6D UMAP refits land mid-scan and at scan-end (carrying both position and HSV colour per §6.1 / §8.2.1.2), the `pattern_map` output panel materialises with the chunk-pattern schemas the scanner detected (§15.8.2) and their golden trios extracted (§15.8.1), and a `umap_canonical` frame arrives on the workspace WS dual-routed per §18.1 so the frontend sees it without severance.

The retrieval result rows render in the side panel — collapsed-hidden by default per the strict §6.4 spine rule — and as the user scrolls through them, the `IntersectionObserver` flips each viewport-visible row's `chunkCollapseTarget` so only the chunks for those rows extrude radially from their doc-hub (§8.3). When the user hovers one of those rows (a Canadian university library result, say), the unified knowledge panel previews at the hover billboard rect (§4.2). When they click, the panel pins at exactly that same screen rect — the freeze-at-hover-rect contract of §4.2 — and the panel's `data-3d-node-id` carries a solid yellow **line (headless, §O.16)** back to its chunk in the projector for as long as the panel stays open. **Double-left-clicking** the panel body expands it into the simplified compute graph of §7.3 — single `name : value` children with form-fit boxes, stringless edges, `{var}` propagation through the chain — and double-left-clicking the central node again collapses everything back into the original panel (right-click is the separate rank-1 inline type-graph fold, §7.3.4 / §O.1). Halos opened on either the central panel or any of its compiled-graph children radiate around their focal as concentric circles per §8.2.1, with the projector's manifold-nearest chunks ray-projected onto the conic surface as collapsed-singular phantoms carrying their image billboards or HSV-rotating colours.

**Evidence probe:** `scripts/probe_live_archive_scan.py`.

### §16.2 §8D.47 — Concept Graph Editor Authoring (inside-out)

The user begins where the §1.5 Imaginary register begins: from the empty primitive (§5.1), with no scan yet to ground anything in the Real. They type a description into the empty — "summarise text from the web with a small language model" — and the multi-semantic-frequency-PageRank apparition surface (§8.1.1, §8.2.1) radiates candidates around the focal as concentric circles, ranked by the aggregated triple product across token / phrase / paragraph / document / pattern bands. The strongest candidates surface the Agent fixture's `meta_prompt`, `prompt`, and `output` primitives (§9.5.1), the Database fixture's `concept` function for rank-1 KG walks, and the WebBrowser fixture's `scan` function — these are the soft links on the possibility ring of §3.2.1, and the user clicks any of them to promote it to a hard link on the commitment fan.

As the user wires those primitives into a compute graph — `WebBrowser.scan(url, "summarise")` feeding its `pattern_map` output through `Database.concept(pattern_map.sampled_chunks)` into `Agent.prompt(template_with_concept_walk)` — `{var}` references in the descriptions and data fields auto-create empty primitives the user can fill in later, and concept-graph mutations — create / link (whether issued by the user via a panel gesture or by an autonomous agent through its emitter, §12.6.1; §S — no `Editor` object) — flow through the same lifecycle dispatcher (§10.2) producing the same `concept_changed` and `evolution_diff` frames the Symbolic register reads. A real LangGraph + GPT4All compile chain runs the graph — `ConceptComputeNode` instances per §10.6 routed through `langgraph.graph.StateGraph` — and the closest-inverse lookup (§7.7) fills any unwired input port automatically as the Imaginary's purely projective inverse. Inline cypher embedded in any card's data field detects and routes to real Kuzu execution (§8D.2.1); the evolution log records every step; and a rollback restores the prior state with the rollback itself recorded as a new diff (§11.4).

**Evidence probe:** `scripts/probe_live_concept_graph.py`.

### §16.3 §8D.48 — Live Agent Tick (autonomous)

The agent body subgraph spawns through `POST /api/agent/spawn` — parameter card holding `goal` / `step_index` / `paused`, perception card reading the workspace's apparition surface around the parameter card's focal, transformer card holding the SLM prompt template, emitter card wiring the concept-graph **mutation gestures** (create / link / overwrite / delete; §S — no `Editor` object) against the structured action JSON the SLM returns. Backing pointers under `agent::{kind}::<pcid>` are verified; a tick fires through `MetaCognitionTick.run_async()` per §12.2; the perception card composes payload from real apparition retrieval (§8.2 multi-frequency rank) against the parameter card's focal; the transformer card fires real GPT4All streaming `agent_token` WS frames into the agent panel body; the emitter card parses the structured action and applies each through the same lifecycle dispatcher (§10.2) the user's GUI gestures use. The four mutation gestures the emitter calls (`create_concept` / `create_concept_edge` / `update_concept` / `delete_concept`) are the same ones a user's panel gesture invokes by hand — the entanglement of §12.6.1 made operational: one mutation lifecycle, two callers.

The tick is one step of the recursion-over-iteration integration scheme of §12.2.1, with world perceptions as initial conditions and the projector's perimeter (§6.6.1) as the locus of the agent's final outputs. The token buffer holds real streamed tokens; pause/resume via parameter-card edit halts and resumes; evolution log captures `actor=agent:<id>` diffs that compose with the user's own diffs; termination via parameter-card delete dissolves the body subgraph cleanly.

**Evidence probe:** `scripts/probe_live_agent.py`.

### §16.4 §8D.49 — Unified Iterated-Compile (the synthesis)

> "Please sketch in the details of the current two activities we've dealt with already and merge them into a unified activity of applying an LLM computation with some kind of templated output via langgraph and pydantic template compilation usage, and apply recursive iterated computation of the compiled graph nodes over sampled chunks from scans of archive.org." (user, verbatim)

The synthesis combines the outside-in trajectory of §16.1 and the inside-out trajectory of §16.2 into a single recursive iterated compile, with the unified panel↔compute-graph scheme's own mutation gestures (§S — not an `Editor` fixture) orchestrating the structure as it grows. The user authors a URL-set panel (§15.7) holding two or three archive.org URLs, wires `{urls_panel}` into a `WebBrowser.scan` whose `pattern_map` output feeds a three-node langgraph + pydantic templated compute graph — a `chunk_sample` node selecting one chunk at a time from `pattern_map.<pattern_hash>.sampled_chunks` under the signal-stream constraint of §4.6.1, a `structured_prompt` node templating `Agent.meta_prompt` and `Agent.prompt` against the sampled chunk's golden-trio fields, and a `formatted_output` node calling `Agent.output(schema=PydanticType)` to get a validated structured result. The play/pause iterated rollout (§7.5) advances through chunks one at a time; the user pauses between iterations to edit the prompt template or to add a sibling row to the structured output's pydantic schema; on resume, the next iteration uses the edited template; the cascade re-fires through every dependent card with the new value.

Halos open around any compiled-graph node — the `formatted_output` node's halo carries soft links to other concepts that produce similarly-shaped pydantic outputs, the `chunk_sample` node's halo carries soft links to the original chunks via their projector-projection on the conic surface (§8.2.1) — and **double-left-clicking** either the central panel or one of the compiled-graph children flips the dialectical inversion of §7.3 between synthesis (panel form) and analysis (simplified subgraph form) (§7.3.4 / §O.1; right-click is the separate rank-1 inline fold). The three lodestar trajectories — outside-in scan, inside-out authoring, agent tick — interlock as one loop with the play loop (§8D.25) cycling around them.

**Evidence probe:** `scripts/probe_live_iterated_compile.py`.

### §16.5 The Live-Scan + DB-Cleanup REPL Probe (§1.2 update)

The user's §1.2 update closes with a hard requirement: *"live-scanning updates must be rigorously tested with proper database cleanup on real sites in our full-stack REPL test in the console."* This isn't an optional probe; it is the acceptance bar for the Real ↔ Imaginary ↔ Symbolic loop's *repeatability* over the lifetime of the workspace. What we are testing is not whether one scan works — the §16.1 archive.org lodestar probe already does that — but whether the loop can be exercised again, and again, and again on real sites without progressive degradation, which means the database has to come back cleanly between rounds and the live updates have to keep flowing through the workspace WS the whole time, not just on the first scan.

The probe lives at `scripts/probe_live_scan_with_cleanup.py` and runs as the env-scenario `live-scan-real-with-cleanup`. It begins with a fresh backend boot, confirming `all_real: true` via `GET /api/subsystem_status` (§13) — no fake gates, no stub fallbacks, just the real GPT4All on CUDA, the real nomic embedder, the real Selenium, the real LangGraph. From that baseline it purges the workspace through `POST /api/purge_workspace { confirm: "erase" }` and asserts that Kuzu reports zero ConceptNodes except for the auto-materialised foundation fixtures (§9.5) — that's the starting point, and any drift from it would already mean cleanup was incomplete on a prior session.

The first scan runs against a real archive.org URL — `https://archive.org/details/texts` with `query="university library"` — through `POST /api/snapshot`, and the probe subscribes to the workspace WS (§10.1) to watch what comes back. What it must see is `chunk_added` frames arriving on the workspace WS rather than only on the snapshot socket (the §18.1 dual-routing severance must be closed end-to-end at every scan, not just at the first one), the chunk count climbing monotonically as the scanner streams, multiple `umap_canonical` frames arriving as the LayoutFrame refits incrementally during the scan rather than only at the end, and the `pattern_map` output panel (§15.8.2) materialising with at least one chunk-pattern schema carrying a non-empty golden trio (§15.8.1). At scan settle, `Database.search("university library")` must return at least one chunk whose rendering contains the query terms, and the apparition surface around the top hit (§8.2) must return at least one soft-link candidate scoring above `min_score_threshold` — which together verify that the TF-IDF and nomic indices are alive and that the multi-frequency aggregation (§8.1.1) is producing meaningful ranks against real content.

Then the probe purges again, and this is where the cleanup contract gets enforced. The Kuzu ConceptNode count must return to the foundation-fixture baseline (the three fixtures and their materialised python trees); the LayoutFrame must be dropped; the TF-IDF index must return to empty (`/api/health` reports `tfidf_doc_count: 0` or the equivalent); the persistent accessor table (§5.4) for the scanned domain must be cleared; the on-disk Kuzu database file must shrink back to within 10% of its pre-scan baseline (so there is no orphan storage hiding inside the database file); and the trace must contain no 503s and no stub fallbacks anywhere. Any one of these failing means the workspace has accumulated state that the next round will inherit, and the next round will start from a contaminated baseline rather than a fresh one.

The final step is a re-scan — the same URL, the same query, against the freshly-cleaned workspace — and the assertion is that the chunk count rebuilds identically. A stale index would cause incremental-update mismatch here (a chunk that the prior round's index already contained would be re-indexed against stale TF-IDF vocabulary, producing slightly different rankings the second time), and the identity of the rebuild is what verifies the purge was structurally complete rather than just nominally complete. What we get, when the probe passes end-to-end, is the workspace's *demonstrated capacity* to exercise the loop repeatedly on real sites — which is what the user means by *rigorous testing*, and what the §18.1 severance, the §15 scanner contract, and the §9.5 fixture set together rely on to compose.

### §16.6 The Six Commitments The Lodestar Cases Enforce

1. **Strict spine rule (§6.4 / §8D.18.1)** — retrieval chunks collapsed-hidden by default; only scroll-viewport-visible OR pinned-panel-referenced chunks visible. No third path.
2. **Latch + form-fit + slide-out data panel (§4.4 / §8D.1.2)** — knowledge panels open latched; latch slides data block out as side panel at equal height; cards form-fit to content; empty rows hide.
3. **Compile/collapse toggle (§7.3 / §8D.2.2)** — symmetric **double-left-click** gesture on central panel-or-node (§7.3.4); expansion = simplified subgraph (one level deep); collapse = restore. Right-click is the separate inline next-rank type-graph fold (§7.3.4).
4. **Python-native Object/Property/Function trees (§9.6 / §8D.4.2)** — fixtures expand into read-only trees with `no_datablock` sentinel.
5. **Cascade is the default (§7.4 / §8D.38.4)** — compilation continuous downstream of edits/scans/agent emissions; Compile button is an affordance.
6. **REPL in-place activity viewer (§14.5 / §11.8)** — fixed six-row dashboard updates in place via ANSI cursor codes.

---

## §17 — Functional Sequences Reference

A complete enumeration of the workspace's interactive sequences, formalised as state machines. Each sequence is rooted in a **gesture** (REPL action or GUI event) and threads through the full stack to a **rendered effect** + **telemetry** (§14.2).

### §17.1 The Scan Sequence (§9.5.1 WebBrowser.scan)

```
gesture: web-scan { url, query? }   (REPL action wrapping WebBrowser.scan)
   │
   ▼  REST POST /api/web_query  (legacy route name; resolves WebBrowserManager via fixture backing pointer)
   │     ╰── alt: WebBrowser.scan invocation via Editor.compile-node of a wired scan node
   │
   ▼  WebBrowserManager.scan(url, query?) — unbounded pagination form
   │     │     (legacy WebBrowserManager.web_query(url, query?, samples) — sample-bounded form)
   │     ▼  navigates → search-input detection if query is set → recursive DOM scan with implicit pagination
   │     │
   │     ▼  per-chunk: ChunkBuilder._recurse_absolute_trie → chunk record
   │            │
   │            ▼  Layout Service: integer chunk_id assigned; preliminary radial position seeded
   │            │
   │            ▼  TF-IDF + nomic incremental indexing (§8.1.1 multi-frequency bands updated)
   │            │
   │            ▼  Scanner detects pattern → builds / extends ChunkPatternSchema in pattern_map (§15.8.2)
   │            │     │
   │            │     ▼  golden-trio extraction over pattern members (§15.8.1)
   │            │
   │            ▼  WS frame chunk_added (workspace WS + snapshot WS dual-routed per §18.1)
   │
   ▼  frontend cp/scanner.js: addNodesIncrementally → InstancedMesh add; HSV colour applied from 6D UMAP (§6.1 / §8.2.1.2)
   │
   ▼  Layout Service incremental UMAP refits land mid-scan as new chunks accumulate → emit umap_canonical frames
   │
   ▼  scan completes → final joint 6D UMAP fit over the full TF-IDF index
   │
   ▼  per-URL post-processing (centroid translation, bounding-radius scale, hard collider repulsion, HSV phase calibration)
   │
   ▼  WS frame umap_canonical (workspace-scoped) carries (x, y, z, h, s, v) per chunk
   │
   ▼  frontend tweens positions to canonical (~600 ms); HSV state stored for the camera-azimuth rotation loop
   │
   ▼  pattern_map output panel materialises as ConceptNode whose data is the chunk-pattern schema tree
   │     ╰── (signal-stream constraint per §4.6.1 — one pattern_hash visible at a time)
   │
   ▼  ui_state_changed: visible_chunk_ids, pattern_map signal, halo_chain reset
   │
   ▼  REPL viewer scan row: "<url> search=<query> | N/M chunks | UMAP@scan-end | pattern_map: <K> patterns"
```

### §17.1.1 The Editor Mutation Sequence (§9.5.1 Editor primitives)

The four Editor primitives (`create`, `link`, `overwrite`, `delete`) share one path through the lifecycle dispatcher (§10.2); the gesture differs only in which side of the dispatcher's fan-out it enters from.

```
gesture: editor-create { name, description?, data? }     (REPL action OR agent emit OR user GUI gesture)
   │     ╰── editor-link { source_id, target_id, edge_type?, source_port?, target_port? }
   │     ╰── editor-overwrite { node_id, name?, description?, data? }   (field-merge — only kwargs passed mutate)
   │     ╰── editor-delete { node_id }   (rejected for foundation fixtures §9.5)
   │
   ▼  REST POST /api/editor/<primitive>  (or in-process call from Agent emitter via ActionResolver)
   │
   ▼  apply_update_lifecycle / apply_delete_lifecycle / link create (§10.2)
   │     │
   │     ├──► Kuzu write
   │     ├──► nomic re-embed (description) + TF-IDF update (rendering on next compile)
   │     ├──► evolution_diff (actor = user|agent:<id>|cascade|editor)
   │     ├──► cascade scheduler nudge for downstream cards (§7.4)
   │     └──► WS broadcast: concept_changed (created|modified|deleted|linked)
   │
   ▼  frontend re-renders affected panels; halo apparition surface (§8.2) re-fires around the changed focal
   │
   ▼  if the change broke a {var} reference, dependent cards mark the ref as broken (§9.11 reference_invalidated)
   │
   ▼  REPL viewer: editor row updates with the latest mutation summary; halo / autocomplete rows refresh
```

### §17.1.2 The Signal-Stream Advance Sequence (§4.6.1)

```
state: a knowledge panel field carries an iterable value (Database.concept list, urls_panel, pattern_map, …)
       and the panel is currently displaying signal index i with iterable element i visible as the print form
   │
gesture: rollout-step (next sample) OR rollout-play (auto-advance) OR ui-signal-advance { card_id, field_path }
   │
   ▼  Rollout coordinator (§7.5) advances signal_index for the named field
   │
   ▼  UIStateService.set_signal_stream(card_id, field_path, signal_index=i+1)
   │
   ▼  WS ui_state_changed (kind=signal_advance) with {card_id, field_path, signal_index, signal_total}
   │
   ▼  cascade scheduler re-fires the affected card's compile (§7.4) using the new signal as the live value
   │     │
   │     ▼  downstream cards consuming the value via {var} ref see the new signal; their compiles re-fire
   │
   ▼  frontend swaps the visible print form in place — only the new signal renders; prior signals stay in storage (§4.6.1)
   │
   ▼  REPL viewer signal-stream row: "card=<id>.<field> signal=i+1 of N — <print-form-preview>"
```

### §17.1.3 The `pattern_map` Iteration Sequence (§15.8.2)

```
state: pattern_map output panel materialised from a completed scan;
       data field is a recursive ChunkPatternSchema tree;
       signal index = 0 by default → first pattern visible
   │
gesture: ui-signal-advance { card_id: pattern_map_id, field_path: "pattern_hash" }
   │     OR rollout-play (auto-advance through patterns)
   │
   ▼  signal-stream advance per §17.1.2 → next pattern_hash becomes visible
   │
   ▼  panel re-renders: golden_trio fields, sampled_chunks list, sub_patterns tree all reflect the new pattern
   │
   ▼  if the user clicks any sampled chunk in the visible pattern → fly camera to that chunk in projector (§8.5)
   │     ╰── halo opens around the focal; soft links radiate via §8.2.1 multi-freq aggregated rank
   │
   ▼  if a downstream function (Database.concept, Agent.prompt, …) consumes the pattern_map via {pattern_map}
   │     ▼  that function fires per visible pattern (signal-stream); the cascade composes recursion-over-iteration (§12.2.1)
   │
   ▼  REPL viewer pattern-map row: "pattern <hash> @ <url_root> | trio=(title, link, content) | samples=<N>"
```

### §17.1.4 The `{urls_panel}` Expansion Sequence (§15.7)

```
state: WebBrowser.scan function node's url input port is wired to {urls_panel}
       (a user-created URL-set knowledge panel per §15.7 containing N URLs)
   │
gesture: editor-overwrite { scan_node_id, data: "{ url: {urls_panel} }" }  OR compile of an already-wired scan node
   │
   ▼  compile pipeline (§7.1) resolves {urls_panel} via the typed-link inheritance of §15.9
   │     ▼  url_set type recognised; signal-stream constraint (§4.6.1) takes over
   │
   ▼  iteration: for each url in urls_panel.data, scan fires once
   │     ▼  signal_index advances per §17.1.2
   │     ▼  scan sequence (§17.1) executes against the visible url
   │     ▼  pattern_map (§15.8.2) accumulates chunk-pattern schemas across all URLs
   │     ▼  each chunk lands in projector at its 6D-UMAP position (interior for scanner-emitted; perimeter for agent outputs §6.6.1)
   │
   ▼  on iteration complete: signal_index = 0 + final aggregate pattern_map renders
   │
   ▼  REPL viewer urls-panel row: "urls_panel=<slug> | url=<i+1>/<N> visible | chunks_cumulative=<N>"
```

### §17.1.5 The Halo Ray-Projection Sequence (§8.2.1)

```
state: focal panel is open; data-3d-node-id resolves to a chunk c in the projector
   │
gesture: ui-halo-focus { focal_card_id }   (hover or click on focal opens the halo)
   │
   ▼  apparition_service.surface_for(focal_card_id) (§8.2)
   │     ▼  multi-semantic-frequency-PageRank (§8.1.1) ranks soft-link candidates against focal
   │     ▼  returns top-K candidates by aggregated triple-product across token / phrase / paragraph / document / pattern bands
   │
   ▼  Layout Service: pick K projector-nearest chunks to c using LayoutFrame coords (§9.4); attach HSV state per §8.2.1.2
   │
   ▼  frontend computes the halo's conic surface (apex at focal screen centre; lateral surface = outer ring radius)
   │     ▼  for each projector-neighbour c_i: ray = focal_centre → screen-projection(c_i.world_pos); intersect ray with cone
   │            ▼  collapsed-singular phantom placed at intersection; renders image billboard OR HSV-rotating colour
   │     ▼  for each non-projector candidate: phantom placed at (angular = nomic-direction, radial = (1 − normalised_score) · r_extent)
   │
   ▼  halo rendered: commitment fan (hard links, §3.2.1) between focal and existing targets;
   │                  possibility ring (soft links + projector-projected chunks) concentric at halo radius
   │
   ▼  WS ui_state_changed: halo_focus mirror updated; viewer halo row carries focal + candidate-name list
   │
   ▼  HSV rotation continues independently — every animate frame applies (camera_azimuth_phase + chunk_hsv_phase) to each visible phantom and chunk
   │
   ▼  on user click of a phantom: §17.7 apparition-resolve sequence runs;
   │  if the phantom was a projector-projected chunk, the click ALSO flies the camera to c_i (§8.5)
```

### §17.2 The Click-And-Stick Sequence

```
gesture: mouseenter on 3D chunk mesh
   │
   ▼  raycast → chunk_id
   │
   ▼  ui-hover REST POST (debounced)
   │
   ▼  hover billboard renders at projected screen rect (one #billboard instance)
   │
gesture: mousedown / click on chunk
   │
   ▼  capture billboard.getBoundingClientRect() → (top, left, w, h)
   │
   ▼  ui-pin REST POST { chunk_id, rect }
   │
   ▼  lifecycle (no concept mutation — pin is UI state)
   │
   ▼  UI State Service: pinned_panels[] += new entry
   │
   ▼  ui_state_changed WS frame
   │
   ▼  frontend pinBillboard → new pinned panel at exact (top, left, w, h)
   │
   ▼  hover billboard resets (frees for next preview)
   │
   ▼  REPL viewer pinned row: "[panel:p_X → chunk:c_Y (\"name\")]  (1 pinned)"
```

### §17.3 The Compile-Expand Sequence

```
gesture: double-left-click on pinned panel body
   │
   ▼  ui-compile-expand REST POST { card_id }
   │
   ▼  ConceptComputeNode.compile (§7.2) — auto-classifies dispatch kind
   │
   ▼  if data block has cypher patterns → Database.cypher → substitute result
   │
   ▼  recursive decompose: top-level keys → child ConceptNode creates keyed by <card_id>__<key>
   │     each create through lifecycle (§10.2)
   │
   ▼  lifecycle for each child:
   │     Kuzu write → WS concept_changed → ConceptIndex upsert → evolution_diff → cascade nudge
   │
   ▼  UI State Service: compile_expansions[card_id] = [child_ids]
   │
   ▼  ui_state_changed WS frame
   │
   ▼  frontend renders simplified subgraph (§7.3):
   │     central panel → name + collapse affordance
   │     children at ray-constrained positions, value-only, form-fit, stringless edges
   │
   ▼  REPL viewer compile row: "EXPANDED  central=p_X  children=[url, xpath, html_raw, ...]"
```

The **collapse** sequence is the inverse: double-left-click central → ui-compile-collapse → delete children through lifecycle → ui_state_changed → frontend restores panel.

### §17.4 The Cascade Sequence (User Edit → Downstream Re-Compile)

```
gesture: type into description field of card A
   │
   ▼  concept-edit-description REST PATCH (debounced)
   │
   ▼  lifecycle (§10.2):
   │     Kuzu write A.description
   │     ConceptIndex re-embed A.description (nomic) → update A's slot
   │     evolution_diff (action=modify, actor=user, field=description)
   │     cascade scheduler: enqueue downstream cards of A (edges where A is source)
   │     WS concept_changed for A
   │
   ▼  cascade scheduler (debounced ~800 ms):
   │     for each downstream card B that references A in description/data:
   │         ConceptComputeNode.compile(B)
   │         if B's compile uses A's rendering → re-substitution propagates
   │         actor-aware short-circuit: skip if B's actor is in active short-circuit set
   │         lifecycle for B (same fan-out)
   │
   ▼  concept_index_update WS frame (Concept Index settles)
   │
   ▼  frontend re-renders A's panel + B's panel + every other affected card
   │
   ▼  REPL: subsequent watch-activity tick reflects updated renderings
```

### §17.5 The Agent Tick Sequence

```
gesture: agent-tick { parameter_card_id }   (or scheduled cascade)
   │
   ▼  POST /api/agent/tick (resolves agent runtime via fixture backing pointer)
   │
   ▼  MetaCognitionTick.run_async:
   │     perception card:
   │         apparition_service.surface_for(parameter_card_id) (§8.2)
   │         compose payload with parameter card's goal + apparition results
   │     transformer card:
   │         SLMClient.async_stream_chat(prompt) — real GPT4All
   │         each token → WS frame agent_token { agent_id, token, partial }
   │     emitter card:
   │         parse structured action JSON from transformer output
   │         ActionResolver applies each action through lifecycle (§10.2)
   │            - CreateCardAction → create_concept
   │            - LinkAction → create_concept_edge
   │            - WriteFieldAction → update_concept
   │            - InvokeAction → ConceptComputeNode.compile on target
   │
   ▼  each lifecycle fan-out emits concept_changed + evolution_diff (actor=agent:<id>)
   │
   ▼  frontend renders new cards/edges; agent panel body shows streamed tokens + rationale
   │
   ▼  REPL viewer agent row (if active mode): "agent:X  perceive=N apparitions | tokens=M | emit: creates=3 links=2"
```

### §17.6 The Rollout Play/Pause Sequence

```
gesture: rollout-play (starts iteration over sampled chunks)
   │
   ▼  rollout coordinator: iterates samples 1..N
   │     for each sample_idx:
   │         compile chain (§7.1) using sample_idx-substituted inputs
   │         WS frame rollout_progress { sample_idx, current_node_id }
   │
gesture: rollout-pause { node_id }   (during iteration)
   │
   ▼  coordinator halts at current sample
   │
   ▼  WS frame rollout_paused { sample_idx, current_node_id }
   │
   ▼  frontend reveals edit affordances on the paused node (plus-signs, name editable, etc.)
   │
gesture: concept-edit-data-row { id, path, value }   (user edits paused node)
   │
   ▼  lifecycle (§10.2) — does NOT advance iteration
   │
gesture: rollout-play   (resume)
   │
   ▼  coordinator advances to next sample using edited node's new content
   │
   ▼  WS frame rollout_resumed
   │
   ▼  REPL viewer: rollout state row reflects sample_idx + paused flag transitions
```

### §17.7 The Apparition Resolve Sequence (Empty Primitive Authoring)

```
gesture: create empty primitive
   │
   ▼  POST /api/concepts (no name, no description)
   │
   ▼  lifecycle: empty ConceptNode created; no embeddings yet
   │
gesture: type description into empty
   │
   ▼  concept-edit-description (debounced)
   │
   ▼  lifecycle: nomic re-embed; ConceptIndex slot upsert
   │
   ▼  WS concept_index_update
   │
   ▼  frontend reads ConceptIndex slot; calls apparition-surface { empty_id, k=8 }
   │
   ▼  apparition_service.surface_for(empty_id):
   │     for each candidate in ConceptIndex:
   │         score = pagerank · tfidf_cos · nomic_cos
   │     return top-K
   │
   ▼  frontend renders halo phantoms around empty (collapsed-panel-form, name only; §8.2)
   │
gesture: click a halo phantom
   │
   ▼  concept-edge-create { source: empty_id, target: candidate_id, edge_type: DERIVED_FROM }
   │
   ▼  lifecycle (§10.2): edge created; cascade re-fires
   │
   ▼  empty inherits intent from candidate; further compiles propagate the resolved type
```

### §17.8 The Variable Auto-Creation Sequence (§8D.21.1)

```
gesture: type "{summary_seed}" into description or data of card A
   │
   ▼  lifecycle update on A
   │
   ▼  curly-brace parser detects ref "summary_seed"
   │
   ▼  if a ConceptNode with name slug "summary_seed" exists → bind {var} to it
   │  else → auto-create empty ConceptNode named "summary_seed"
   │          create RELATES_TO edge A → summary_seed
   │
   ▼  both lifecycle fan-outs occur
   │
   ▼  frontend renders the new empty + the edge; cascade re-fires A's compile (which will leave the ref literal until summary_seed has content)
```

### §17.9 The Closest-Inverse Sequence (§7.7)

```
state: function-card F has output port wired to card B, input port empty
   │
gesture: conceptual-compile { concept_id: F }
   │
   ▼  ConceptComputeNode.compile detects unwired input + connected output
   │
   ▼  apparition_service.closest_inverse(input_type_description, k=1)
   │     embeds B (observed output) into the function's output space
   │     ranks candidate inputs by cos_sim(predicted_output_for_candidate, B)
   │
   ▼  WS frame inverse_suggestion { function_id, input_port, candidate_id, score }
   │
   ▼  frontend reveals the suggestion on F's input port
   │
   ▼  user accepts → concept-edge-create → cascade re-fires forward
```

### §17.10 The Purge Sequence

```
gesture: purge-workspace { workspace_id, confirm: "erase" }
   │
   ▼  purge handler walks every concept
   │     for each: apply_delete_lifecycle (preserves per-concept evolution diff)
   │
   ▼  drop persisted LayoutFrame (in-memory + on-disk)
   │
   ▼  reset frame_seq counter to 1
   │
   ▼  WS frame purge_workspace (consolidated)
   │
   ▼  frontend removes:
   │     every hub + chunk owned by workspace
   │     every pinned panel referencing purged chunks
   │     apparition cache slots
   │     concept-index cache slots
   │     agent-token buffers
   │     frame_seq high-water marks
   │
   ▼  REPL viewer: all rows reset to empty state
```

### §17.11 The Rollback Sequence

```
gesture: evolution-rollback { edit_id }
   │
   ▼  POST /api/evolution_log/rollback { edit_id }
   │
   ▼  read EditDiff record by edit_id
   │
   ▼  compute inverse: if action="modify", restore before-snapshot; if "delete", recreate; if "create", delete
   │
   ▼  apply inverse through lifecycle (§10.2) — actor="rollback"
   │
   ▼  the rollback itself records as a new EditDiff (actor=rollback, target=original target)
   │
   ▼  WS evolution_diff frame (the rollback diff)
   │
   ▼  WS concept_changed frame (the restored target)
   │
   ▼  frontend re-renders restored target; history view appends the rollback entry
```

### §17.12 The Pin Chrome (Move / Resize / Minimise / Close) Sequence

```
state: pinned panel exists in pinned_billboards (§4.2 freeze-at-rect)
   │
gesture: drag header → ui-pin-move { panel_id, top, left }
   │
   ▼  POST /api/ui/pin_chrome { panel_id, top, left }
   │
   ▼  UIStateService.set_pin_chrome → pin_chrome[panel_id] = {top, left, width: prior.width, height: prior.height, minimised: prior.minimised}
   │
   ▼  WS ui_state_changed (kind=pin_chrome)
   │
   ▼  frontend (peer tabs / REPL viewer) read pin_chrome and re-position the panel
   │
gesture: drag corner → ui-pin-resize { panel_id, width, height }
   │
   ▼  POST /api/ui/pin_chrome { panel_id, width, height }   (only width/height fields)
   │
   ▼  setter merges over prior rect; preserves top/left/minimised
   │
gesture: click minimise → ui-pin-minimise { panel_id, minimised: true|false }
   │
   ▼  POST /api/ui/pin_chrome { panel_id, minimised }   (only minimised field)
   │
gesture: click × → ui-pin-close { panel_id }
   │
   ▼  POST /api/ui/unpin { node_id: panel_id }
   │
   ▼  UIStateService.unpin removes from pinned_billboards AND clears pin_chrome[panel_id]
   │
   ▼  REPL viewer pinned row: drops the chrome entry
```

The setter is **field-merge**: each POST carries only the fields the gesture mutates; the setter preserves the prior values for unmentioned fields. This means drag (top/left only) and resize (width/height only) and minimise (minimised only) compose naturally. The first POST for a new panel_id initialises a fresh chrome record with defaults (`top=0, left=0, width=320, height=240, minimised=false`).

### §17.13 The Latch Toggle Sequence (§4.4)

```
state: panel rendered in latched form (data block hidden, latch icon ▶)
   │
gesture: click latch → ui-latch-toggle { card_id, latched: false }
   │
   ▼  POST /api/ui/latch { card_id, latched: false }
   │
   ▼  UIStateService.set_latch → latch_state[card_id] = "unlatched"
   │
   ▼  WS ui_state_changed (kind=latch)
   │
   ▼  frontend slides data panel out (equal-height contract, §4.4)
   │
   ▼  REPL viewer latch row: "card_X: unlatched"
   │
gesture: click latch again → ui-latch-toggle { card_id, latched: true }
   │
   ▼  POST /api/ui/latch { card_id, latched: true }
   │
   ▼  latch_state[card_id] = "latched" → slide-in
```

A toggle without an explicit `latched` arg flips the current state; toggling a never-toggled card_id treats prior as "latched" (default) so the first toggle unlatches.

Read-only python-native panels (§9.6) ignore latch toggles (the latch button is hidden); the setter still records the request but the frontend's renderer never applies the slide.

### §17.14 The Viewport Spine Sequence (§6.4 / §8.3)

```
state: retrieval result list rendered; IntersectionObserver attached
   │
gesture: user scrolls → IntersectionObserver fires per row entering/leaving viewport
   │
   ▼  frontend debounces (~120 ms) the viewport set
   │
   ▼  POST /api/ui/viewport_spine { ordered: [chunk_id, ...], total: N }
   │
   ▼  UIStateService.set_viewport_spine → viewport_visible_rows = {ordered, total, updated_at}
   │
   ▼  WS ui_state_changed (kind=viewport_spine)
   │
   ▼  peer tabs / agent perception read the visible-row set
   │     (used by the agent's zone_of_influence per §12.1 — what the
   │      user is attending to becomes the agent's perception focus)
   │
   ▼  spine emitter applies chunkCollapseTarget=0 for each visible
   │  chunk; off-viewport rows fold back (chunkCollapseTarget=1)
   │
   ▼  REPL viewer retrieval row: "query='X'  viewport=N-M of T"
```

The contract: only ordered chunks currently in the scroll viewport are 3D-visible. Off-viewport rows fold back into the doc-hub (§6.4 strict default). The agent's spine-delta endpoint (`POST /api/spine_delta { popped, folded }`) writes the visible-row delta to active agents' zone_of_influence so meta-cognition reads what the user attends to — the spine is therefore *both* a 3D visibility control and an agent perception signal.

### §17.15 The Autocomplete Sequence (§4.7)

```
state: user types into an editable row's name field
   │
gesture: keystroke → ui-autocomplete-open { row_id, query, parent_card_id? }
   │
   ▼  POST /api/ui/autocomplete { row_id, query, parent_card_id? }
   │
   ▼  UIStateService.set_autocomplete → autocomplete_state = {row_id, query, parent_card_id, opened_at, candidates: []}
   │
   ▼  WS ui_state_changed (kind=autocomplete_open)
   │
   ▼  frontend separately calls GET /api/concept_completions?prefix=...&parent_card_id=...
   │     → returns ranked candidates (triple product §8.1, scoped if parent_card_id set per §4.7)
   │
   ▼  POST /api/ui/autocomplete { row_id, query, candidates: [...] }
   │     → setter merges candidates into existing record
   │
   ▼  WS ui_state_changed (kind=autocomplete_open with candidates)
   │
   ▼  REPL viewer autocomplete row: "row_X: query='db' → [Database.search, Database.cypher, ...]"
   │
gesture: user selects a candidate → ui-autocomplete-close { row_id }
   │
   ▼  POST /api/ui/autocomplete_clear { row_id }
   │
   ▼  autocomplete_state = None
   │
   ▼  WS ui_state_changed (kind=autocomplete_close)
```

Selecting a candidate inserts `{<linked_name>}` into the value (§4.7). The variable auto-creation sequence (§17.8) handles missing-target binding if the user types a slug that doesn't yet exist.

---

## §18 — Known Failure Modes (Anti-Goals)

This section is the **never-do-this** catalogue, derived verbatim from the user's bug reports. Every entry here is a feature that previously broke; the design must structurally prevent each from recurring. New code that re-introduces any of these is a regression.

### §18.1 Scan ↔ Streaming Severance (CRITICAL)

> "Live scan updates are completely broken from streaming to the frontend now (completely severed scanning vs streaming to the frontend and no live umap updates, a huge fault)." (user, verbatim)

The chunk stream and the scan-end UMAP frame both reach the frontend on the **workspace WS**, not the snapshot WS. The fix landed in routes.py + LayoutService — `recompute_and_broadcast` takes `workspace_id` not `snapshot_id`; `_ws_push` fans to both snapshot WS and workspace WS subscribers. Regression check: a real archive.org scan run via REPL must emit `chunk_added` × N → `umap_canonical` → `done` on the workspace WS, all observable by `sim_frontend.py watch` (§14.5).

### §18.2 Concentric Sphere Layouts Re-Introduced

> "I don't know why concentric sphere layouts have been re-added either. Entirely incorrect." (user, verbatim)

Top-of-doc forbidden-concepts notice is authoritative (§9). The hash-direction unit-vector placeholder of §6.1 is the *only* surviving Fibonacci-style angular sampling, and it is transient by construction (replaced by the next `umap_canonical` frame). No code path may use `fibSphereUnit` / `docShellRadius` / `clusterRadius` as the *final* position authority.

### §18.3 3D Spacing Too Close Together

> "Layout issues also in the 3D layouts with spacing too close together." (user, verbatim)
>
> "Please dynamically scale the UMAP layouts such that no image billboards are spaced closer than their total space apart between nodes, with an added safety factor." (user, verbatim)

`COLLIDER_SAFETY ≥ 2.0` on both backend (`layout_service.py`) and frontend (`cp/scanner.js`). Min pair distance `2·R·safety` ≥ 4·R centre-to-centre. The collider radius constant is **shared** between image and text billboards (§6.1). Regression: snap a screenshot of any scan + count overlapping billboards — must be zero.

### §18.4 Old Domains/URLs Persist After Purge

> "Old domains/urls that have been erased from a reset still persist in the GUI, and persist even still after removing the urls from the workspace." (user, verbatim)

The purge handler (§6.5) is **authoritative**: walks every concept through `apply_delete_lifecycle`, drops persisted LayoutFrame, resets `frame_seq`, emits one consolidated `purge_workspace` WS frame. Frontend removes every hub/chunk/pinned-panel/cache slot. The domain accordion re-fetches on `purge_workspace`; it does not rely on in-memory state.

### §18.5 Recompute UMAP Doesn't Fire Twice

> "Pressing recompute umap twice in a row doesn't re-compute the UMAP" (user, verbatim)

`/api/recompute_umap` runs unconditionally. Client-side: the `_umapInFlight` flag MUST clear in a `finally` block on the response. No client-side idempotency gate that would silently skip the second press.

### §18.6 Mouse Scroll Zoom Restricted

> "There is little to no mouse scroll zoom option, perhaps because of the constraint set to get everything in view, or for any other reason." (user, verbatim)

`maxDistance = 3 × max(|chunk.position|)` — recomputed per frame. No fixed-cap `maxDistance` that would saturate the wheel early (§6.2).

### §18.7 Stray Dotted Lines

> "There is a stray dotted line that runs out from the UI that shouldn't be there, I don't know why you're wasting time adding unnecessary things like this." (user, verbatim)
>
> "Current arrows are dotted between 2D-3D nodes and do not actually link to the 3D UI" (user, verbatim)

No SVG element in `backend/static/js/cp/` may carry `stroke-dasharray`. The 2D↔3D link arrow is a **solid yellow line** (`stroke="#ffd700"`, `stroke-width="2"`). Off-frustum nodes hide their arrow via `display:none`; they do not render a dashed placeholder.

### §18.8 Click-Pinned Panel Materialises In Wrong Place

> "Clicked node panels appear in a completely different place from where they were clicked in the 2D UI." (user, verbatim)
>
> "clicking on 3D nodes after hovering over their panel 'stick' the panels in a different place from where the node hover showed the original panel." (user, verbatim)

The freeze-at-hover-rect contract (§4.2): on click, capture `hoverBillboard.getBoundingClientRect()`, pass `(top, left, width, height)` to `pinBillboard`, set `style.{top, left, width, height}` to those values. The hover billboard then resets. Regression: REPL `ui-pin id=X stick_top=N stick_left=M ...` → `ui-state` mirror's `last_stick_rect` must equal `(top, left, width, height)` byte-for-byte (`hover-to-stick-rect-parity` env-scenario).

### §18.9 3D UI Resize Stuck While 2D Resizes

> "Main 3D UI screen resize is stuck and not resizing to the proper layout, but the 2D UI does resize successfully" (user, verbatim)

Both `window.resize` (rAF-coalesced) AND `ResizeObserver` on `#projector-panel` fire `onResize`. `setSize(w, h, updateStyle=false)` keeps `width:100%;height:100%` as the layout authority. **No no-change guard** (`if (w === lastW && h === lastH) return` is forbidden — the `updateStyle=false` setting breaks the historical ResizeObserver feedback loop at the source).

### §18.10 Images Stopped Displaying

> "Images have also stopped being displayed on nodes altogether." (user, verbatim)
>
> "Images keep having to reload and are not properly persisted in their data stores. Please make sure image assets are efficiently stored and referenced always and without interruption for the full span of their existence within a rendered layout." (user, verbatim)

Single-fetch path (§11.2): in-memory `Map<url, THREE.Texture>` → IndexedDB blob cache → proxy fetch → direct fetch. The `X-Image-Proxy-Note` transparent-PNG header is **never cached** as a successful image. Two chunks pointing at the same URL share one `THREE.Texture`.

### §18.11 Two Different Knowledge Panels (Hover vs Click)

> "Hovering over the *first* node in our 3D GUI pops our regular knowledge panel window up, but when I click it, a completely different knowledge panel appears." (user, verbatim)
>
> "We still get, for some reason, two different knowledge panels that pop up when I click on one 3D node." (user, verbatim)
>
> "There should be just one kind of node model that is dealt with when it comes to hover, preview, apparition, etc." (user, verbatim)

One template, one code path (§4). `_buildPanelDom(data, opts)` is the single anatomy renderer; hover, pin, halo phantom, compiled-graph child all call it.

### §18.12 URL Click Explodes All Nodes

> "When I click on a url in the side bar, all nodes explode outward and not minimally and dynamically with the result cards that are visible in the scroll bar at the time. When I click a URL in the retrieval sidebar that's collapsed in the 3D UI, a lot of the result nodes are collapsed unnecessarily and completely incorrectly." (user, verbatim)

URL click toggles **only that URL's chunks**, scoped to viewport-visible rows when a search is active (§8.4 / §6.4). The `IntersectionObserver` spine (§8.3) drives the viewport-visible set.

### §18.13 Hover Preview Stops After First Result

> "Hovered result previews also stop showing up after the first one is hovered (incorrectly to this mythical 'root summary' that is incorrectly or perhaps outdatedly there)." (user, verbatim)
>
> "Summaries for hovered retrieval results point to the root url with a summary, also completely incorrect functionality." (user, verbatim)

No "root summary" widget exists. One `#billboard` instance, content swapped per hover (§8.6). The unified panel (§4) renders for every hover.

### §18.14 Eye Button Doesn't Hide Chunks

> "Url scan visibility buttons in the workspace 2D sidebar on the left do not hide/reveal the scanned DOMs they are associated with." (user, verbatim)
>
> "Url DOM graphs that are collapsed should hide the nodes, including the image billboards shown." (user, verbatim)

Visibility is a **flag**, never a mesh mutation (§6.3). Animate loop reads `workspace.hidden_urls : Set[str]` every frame and writes `scale=0` for affected chunks/hubs. The mesh's intrinsic scale is never touched.

### §18.15 Compile Button Broken

> "compile button on our duplicate knowledge panel cards from our old graph compiler update […] does not work. What this means is that, while rendering is correct, it does not correctly compile the data structure into its components recursively and independent of syntax over recursive tree structures. This still needs to be implemented." (user, verbatim)

The recursive syntax-agnostic compile (§7.1) is the contract. `decompose_recursive(data_field)` handles JSON, bracketed lists, indented trees, HTML element trees, plain text — one routine, no syntax discrimination.

### §18.16 Agent Fixture Missing

> "missing 'agent' concept node" (user, verbatim)

The Agent fixture (§9.5) is present as one of the three undeletable foundation fixtures. `foundation_fixtures.ensure_foundation_fixtures(workspace_id)` always creates it on workspace boot.

### §18.17 Misplaced Nodes / Outlier Geometry

> "Some nodes are completely misplaced. I don't know whether or not this is a race condition thing or what, but there are some wildly misplaced nodes that are inconsistent with our 3D concentric sphere layout. These outliers must be included in the geometry." (user, verbatim)
>
> "The contact lens effect only happens with very large nodes." (user, verbatim)

Joint UMAP fit over the *full* TF-IDF index (§6.1 / §9.3) eliminates per-URL outlier behaviour: every chunk is placed in the same canonical frame and post-processed by hard collider repulsion. The per-URL bounding-radius scale keeps cluster diameters proportional regardless of chunk count.

### §18.18 Camera Zooms Too Far In; No Bounds

> "Camera zooms far too inwards into the dom and there are no proper bounds on the camera perspective to ensure that the entire scan is visible on the screen." (user, verbatim)

`minDistance = 0.6 × cluster_radius(orbit_target)`, `maxDistance = 3 × max(|chunk.position|)` — both recomputed per frame (§6.2). Cannot zoom inside any sphere; cannot escape to infinity.

### §18.19 Two-Panel Split (One Hover, One Click)

> "The panels with the content structure summaries are the correct ones that should actually be what clicks-and-sticks in our 2D UI." (user, verbatim)

There is no separate "content structure summary" panel — the unified panel's `data` field carries the full chunk summary (§4.1). The latch + slide-out side panel (§4.4) handles the wide content; the panel itself stays single.

### §18.20 Common Origin For All Scans

> "All scans share a common root url coordinate at the origin, which is incorrect." (user, verbatim)
>
> "if I compute a UMAP and scan a new page, I expect the UMAP that was previously computed to persist its 3D node values. Then, the new dom sphere that's dynamically updated and the UMAPped previous scan(s) aren't perturbing each other's layout." (user, verbatim)

Per-URL `root_position` + `bounding_radius` + `umap_locked` (§6.1 / §9.5). Old URL positions never move when a new URL is scanned. New URLs land at `existing_max_radius + new_radius + safety_gap` in the direction with most empty space.

### §18.21 Compact-Form Regression (Halo Showing Scores)

> "the apparition ring should be the same format as collapsed nodes" (user, verbatim)
>
> Halo phantoms must carry the candidate's **name only**. No score chips, no description preview, no rendering snippet.

The halo phantom shares the **collapsed-panel form** (§4.3) — name only, scores in slow-hover tooltip. The frontend's `_renderApparitionHalo` honours the §8.2 / §4.5 contract.

### §18.22 Foundation Fixtures Deletable / Panel Chrome (§S black-slate)

> "Fundamental objects cannot be 'X' ed out." (user, verbatim)

Under the §S black-slate design (§4.1.2) there is **no `×` button anywhere** — no panel has chrome. Fixture undeletability is enforced purely at the lifecycle layer: `apply_delete_lifecycle` rejects deletion attempts on the three fixtures (Agent / WebBrowser / Database; §9.5 — §S removed the former fourth, Editor) and on all read-only python-native function/property children. The `fixture-delete-guard` / `three-fixtures-present` env-scenario asserts the three fixtures are present and undeletable.

### §18.23 Agent Outputs Lost to Manifold Interior (§1.1, §6.6.1)

The §1.1 framing of the agent's outputs as *perimeter-encompassing* must hold geometrically. Agent-output chunks (provenance `agent-output` per §3.1, §9.12) project to the projector's outer envelope per §6.6.1, *not* to the manifold interior. If the Layout Service's UMAP fit places agent-output chunks alongside scanner-emitted chunks in the interior, the user can no longer read the Real's interior as observations and the perimeter as syntheses — the §1.5 alchemical loop closure becomes illegible. The Layout Service's per-chunk perimeter rescale is therefore part of the layout authority, not a post-hoc cosmetic. The probe in §16.5 must verify perimeter placement on every agent emission.

### §18.24 Signal-Stream Constraint Violated by Full-Iterable Rendering (§4.6.1)

When a knowledge panel field carries an iterable value, the panel renders only the currently-firing signal — the suppressed iterable elements remain in storage but stay invisible to the print form. Any rendering path that surfaces multiple iterable elements simultaneously in the same panel violates the constraint and breaks the user's mental model of *one signal at a time, the cascade fires per signal*. Common drift: a debug overlay that shows "iteration 3 of 12: [c1, c2, c3, …]" inside the panel, or a panel widget that renders all rank-1-KG nodes returned by `Database.concept(list)` as a flat list rather than as one node per advance. The §4.6.1 contract is *one signal visible*, advanced by the rollout coordinator (§7.5); the REPL viewer's `signal_stream` row is the only place where the full iterable position becomes legible.

### §18.25 Single-Frequency PageRank Persisting Behind Aggregation (§8.1.1)

The multi-semantic-frequency-PageRank aggregation of §8.1.1 activates once the workspace has accumulated K observed-utility events (default K = 32). When multi-frequency is active, the apparition surface and the empty-primitive radiation must use the aggregated rank — not the single-frequency triple product of §8.1 fallback. A stale code path that continues to call the single-frequency surface after aggregation has activated will silently produce lower-quality candidates and will not be visible without per-frequency telemetry. The `apparition_service` reports its active mode through `/api/subsystem_status` and the REPL viewer's `subsystems` row; the live-scan probe (§16.5) asserts the active mode matches the workspace's accumulated-event count.

### §18.26 Ray-Projection Mismatched HSV (§8.2.1.1, §8.2.1.2)

The §1.2.2 update specifies that collapsed-singular phantoms on the halo's conic surface carry their parent chunk's slowly-rotating HSV colour when no image billboard is attached. A drift where the phantom takes a static colour (or a different chunk's HSV) breaks the dual-semantics rule of §8.2.1.1 — the user can no longer recognise the ray-projected chunk by hue and the camera-azimuth synchronisation breaks. The phantom's renderer reads HSV state from the parent chunk's LayoutFrame 6-vector (§6.1, frontend `init.umapHsl`) and applies the same camera-azimuth phase offset (`ChunkProjector._currentHuePhase`) as the parent chunk, then converts via the pure `hslToRgb` to the phantom's left-edge accent. **REPL/render split (§6.1):** the *data* the phantom consumes — the parent chunk's HSV in `[0,1]` — is locked by `env-scenario --name 6d-umap-format` (the 6-vector frame format) and the pure conversion by `node cp/hsv_color.test.mjs`; the *continuous hue rotation of the rendered phantom* is a render-loop visual outside the Python REPL's observation surface, so no scenario asserts the rotation itself (an earlier draft referenced a `halo-ray-projection-hsv-sync` scenario that never existed — corrected here per the no-over-claim rule). A regression where the phantom takes a static colour, a different chunk's HSV, or `rgb(0,0,0)` (the prior `Vector3.r/.g/.b` undefined-field bug) is caught by eye plus the unit-tested wiring.

### §18.27 Foundation Fixture Count Drift (§9.5; §S re-baselined to THREE)

The fixture count is exactly *three* — Agent, WebBrowser, Database (§9.5). **§S removed the former fourth, `Editor`** (the §1.2 update's addition): its create/link/overwrite/delete gestures are intrinsic to the unified panel↔compute-graph scheme (§4/§7), not a Function-typed object, so materialising it is now the *anti-pattern*. The `foundation_fixtures.ensure_foundation_fixtures` must produce exactly three python_object trees (Agent/WebBrowser/Database; Database and the former Editor both backed `GraphEditor`, so the **distinct** backing-class set is what is asserted); the `fixture-delete-guard` / `three-fixtures-present` scenario must verify all three are present and undeletable; the `live-scan-real-with-cleanup` probe (§16.5) must report `concept_count` returning to the three-fixture baseline (plus their materialised member trees) on purge. A code path that re-materialises `Editor` is a §S regression.

### §18.28 Library Middleware Orphan Trees (§9.7)

When the library-imports middleware materialises a new library's Object/Property/Function tree, the tree must compose with the four-fixture types through the typed-edge ontology (§3.2.1, §8D.42.1). An orphan tree — one whose `FUNCTION_INPUT_TYPE` / `FUNCTION_OUTPUT_TYPE` edges don't connect back to any other materialised type — indicates either a type-detection failure or a stale tree from a prior import that should have been re-walked on the latest module version. The middleware's idempotency guarantee (§9.7) must hold across re-imports; on a `wfh_imports.py` change, the middleware re-walks and re-emits the affected subtrees with bumped backing-pointer versions (§15.6) so dependent compile caches invalidate. A stale orphan tree that survives a re-import is a bug.

### §18.29 `pattern_map` Output Not Live-Updating During Scan (§15.8.2)

The `pattern_map` output panel must update *live* during the scan — each newly-detected pattern adds a new top-level entry; each newly-sampled chunk per existing pattern appends to that pattern's `sampled_chunks`; PageRank refits incrementally; the TF-IDF and nomic indices update such that retrieval is usable the moment a chunk lands. A code path that delays `pattern_map` materialisation to scan-end (rather than streaming pattern detections incrementally) breaks the §1.2.1 spec of *iterative minimal value rendering* — the user cannot iterate over partial pattern_map state while the scan is still running. The §16.5 probe asserts incremental pattern_map updates with at least one `pattern_map` mutation visible before the `done` frame.

### §18.30 URL-Set Panel Iteration Fired All-At-Once (§15.7, §17.1.4)

When `{urls_panel}` references resolve into a `WebBrowser.scan` input port, the scan must fire **once per URL under the signal-stream constraint** (§4.6.1) — not in parallel, and not as a single bulk scan over the concatenated list. The iteration semantics are what allow the play/pause stepper (§7.5) to control the user's traversal of the URL set, and what let the chunk-pattern schemas (§15.8) accumulate per URL with sensible attribution to their `url_root`. A parallel-fire implementation breaks the URL-attribution of pattern schemas and breaks the user's ability to pause mid-iteration to inspect the visible URL's scan before advancing.

### §18.31 2D / 3D Coordinate Cross-Coupling (§6.6.2)

The 2D editor canvas and the 3D projector canvas share no coordinate system. The freeze-at-hover-rect pin (§4.2) captures a *screen rect*, not a 3D coordinate; the projector's continued motion of the underlying 3D chunk drives the `data-3d-node-id` solid arrow but does not drag the pinned panel; agent-output projection from 2D card to 3D chunk is one-way through the projector and does not write back to the 2D pin coordinates. Any code path that synchronises 2D pin position with 3D node motion (or vice versa) breaks the §6.6.2 separation contract and makes the round-trip illegible.

### §18.32 Panel Gesture Model Collision (§7.3.4)

The refined gesture model (§7.3.4, M.6/M.7/M.8) assigns five non-colliding gestures to the typed panel: hover = preview next rank; single-left = edit a token (borderless, blended); right-click = toggle the inline next-rank type-graph fold (preserving per-subtree fold state); right-click on the base node = collapse to the singular self node; double-left-click = panel↔graph compile. A regression that re-binds the panel↔graph compile to right-click (the pre-M baseline) collides with the inline type-graph fold and makes recursive next-rank exploration unreachable; a regression that opens an edit on right-click, or fires a compile on a single left-click, breaks the borderless smoothed-text-editor feel (M.8). The fold state must survive collapse/re-expand (M.6) — a fold that resets to fully-collapsed on every toggle loses the user's exploration context. The `node_fold_state` mirror field (§7.3.4 / §10.5) is the REPL-observable surface; the env-scenario `panel-gesture-fold-roundtrip` asserts fold-state preservation across a collapse/re-expand cycle.

### §18.33 External Reference Flooding the 2D Tree (§9.6.2)

An external reference (e.g. `{scanner}` propagated from `WebBrowser.scan`) must **duplicate-instantiate as a rank-1 component** of the host node and surface only its rank-1 relations in the 2D panel/graph (§9.6.2); the **full per-sample scan distribution belongs in the 3D GUI** (§6), not inlined into the 2D tree. A regression that eagerly expands an external reference's entire recursive object model into the 2D panel — rather than rank-1, unfolded selectively by right-click — floods the minimal compute-perception and breaks the rank-1-minimalism contract (N.7/N.8). Likewise, per-sample signal print-rendering that fires when nothing downstream references the iterable (rather than lazily on external consumption, §4.6.1 N.9) violates the conditional-rendering rule. The `node_fold_state` mirror (§7.3.4) plus the 3D chunk count are the observable surfaces; the env-scenario `external-ref-rank1-minimalism` asserts a propagated reference surfaces rank-1 only and the full distribution lands in 3D.

### §18.34 Computation-Graph Reservoir Rollout Flattened — Sync Perimeter / Static Bisector / UMAP-Coupled Links (§6.6.4, §7.8.3)

The cascaded-rollout reservoir (§7.8.1–§7.8.5) + the projector computation-graph node (§6.6.4) carry three load-bearing invariants that are each easy to regress:
- **Async perimeter, not a barrier batch (§7.8.3; P.6 / P.7).** Readout nodes settle at *different* times (differing rollout path lengths + recurrent maps back to hidden state); they must stream to the projector as **per-node delta updates** in settle-order. A regression that barrier-synchronises the perimeter — waiting for all readouts then emitting one batch, or imposing a global rollout step across subgraphs — breaks the asynchronous-output contract and stalls fast subgraphs behind slow ones.
- **Dynamic bisector, hidden centroids (§6.6.4; P.10).** The computation-graph node must be **recomputed on the linear bisector** between the input 6D-UMAP centroid and the **dynamically-updated** output centroid as readouts stream in — sliding, not pinned at compile time — and **neither centroid is rendered** (only the node). A regression that fixes the node at compile time, or draws the input/output centroids, breaks the optimal-transport reading (§7.8.4).
- **UMAP-independent link network (§6.6.4; P.8 / P.9).** The projector links (root url → chunk-sample nodes; root / click-sticked inputs + every perimeter readout → the graph node) are **plain links carrying no coordinate state**, distinct from the UMAP embedding and from the 2D editor's `link_layer`. A regression that derives the link-network node positions from UMAP, or routes these links through the 2D SVG layer, couples the embedding to the circuit and breaks the §6.6.2 separation.

Observable surfaces: the projector's per-node delta-stream order, the bisector node's moving position vs. a fixed one, and the link network's independence from `umap_canonical`. The (design-intent) env-scenario `reservoir-rollout-async-perimeter` asserts out-of-order readout deltas, a sliding bisector node, and UMAP-independent links.

### §18.35 Rank-Dominance Collapse Non-Generalized or Non-Isolating (§6.6.5, §7.3.5, §Q.3–Q.5)

The generalized rank-dominance collapse/expand gesture (§6.6.5 Real / §7.3.5 Imaginary) carries invariants that are each easy to regress:
- **3D right-click must isolate (§Q.3).** A right-click on a root URL hub (or a bisector compute node) must fold its dominated set **and hide every other node** (`scale=0`), leaving only the dominator; a second right-click restores. A regression that collapses the chunks but leaves other URLs/nodes visible, or that fails to restore on re-expand, breaks the Q.3 isolate contract.
- **Membership is rank-dominance, not ad-hoc scoping (§8.1.2).** What folds/hides must be the dominator's **dominated-set reachability** over the one `ConceptEdge` graph — not a hard-coded "this URL's chunks" list and not a PageRank threshold. PageRank is the *collapse-onto heuristic* only (§8.1.2); using it as the membership rule is the regression.
- **Generalized, not special-cased (§Q.4/§Q.5).** The *same* gesture + mirror family (`dominance_collapse`) must serve root-URL hubs **and** bisector compute nodes (Q.4: its input-output distributions) **and** the 2D panel/graph forms (§7.3.5). A second, parallel collapse path for compute nodes — or a 3D-only implementation with no 2D unification — is the regression.
- **Distinct from §18.12.** Must not be conflated with the sidebar left-click (§18.12). Different button, surface, and mirror field (§6.6.5). A regression that routes the 3D right-click through the §6.4 viewport-spine path re-introduces the §18.12 explode bug.

Observable surfaces: the `dominance_collapse` mirror, the `visible 3D` / `hidden 3D` viewer rows after a right-click, and fold-state preservation across re-expand. Env-scenario `dominance-collapse-roundtrip` (3D root-URL + bisector node) + `dominance-collapse-2d` (panel/graph parity).

### §18.36 Scan Time-Box Not Exposed / Hard-Coded `max_duration` (§15.10, §9.8, §Q.2)

The timed full scan (§15.10) requires `duration_s` to be a **first-class exposed port** end-to-end. Regressions: leaving `max_duration` hard-coded in `trigger_snapshot`/`mapper.snapshot` so the graph editor cannot set it; omitting `duration_s` from the `scan` port schema (§9.8) or the REPL `web-scan` action so the property is unreachable; or treating `duration_s` as merely an alias of `samples` (the two are independent bounds — whichever is hit first stops the scan, §15.10). Observable surface: a `web-scan { duration_s: N }` honours the wall-clock bound; env-scenario `timed-scan-duration-port` (all-real-gated against live Selenium per §0).

---

## §19 — Removed Chapters (Stubs)

The following chapters were removed during the convergence to the verbatim requirements. They are listed here so the section numbers stay stable for inbound code references and so a future contributor doesn't re-introduce them. See [`USER_REQUIREMENTS_VERBATIM.md`](USER_REQUIREMENTS_VERBATIM.md) §K for the deletion rationales.

| Section | Was | Replaced by / pointer |
|---|---|---|
| §8.3 | Graph Analytics Integration | §8.1 triple-product retrieval |
| §8D.10 | 2D concentric-with-barrier-colliders layout | 2D UMAP + ray-constrained refinement (sibling of §6.1) |
| §9.13 | Concentric-Fibonacci deprecation note | Top-of-doc forbidden-concepts notice |
| §12 (legacy) | Graph-Analytics, Algorithms, Embeddings, Evolutionary Segmentation (~1400 lines) | §8.1 triple product; §10.3 Layout Service joint UMAP |

The dom_distiller pipeline (Weisfeiler-Leman / Zhang-Shasha / PQ-Trees / BUTA / Hungarian / V-Optimal) remains as **scanner-internal** algorithms (`backend/dom/`) that produce the chunk roster; it is not a retrieval framework and does not surface in the concept editor. Its outputs are ConceptNodes per §15.5.

---

## §20 — Glossary and Cross-Reference Index

### §20.1 Canonical Terms

- **Apparition** — a candidate ConceptNode surfaced by triple-product retrieval (§8.1) around a focal panel; rendered as a name-only halo phantom (§8.2).
- **Backing pointer** — opaque string in `ConceptNode.backing_pointer` resolved by the runtime registry to live Python (§3.3).
- **Cascade** — the re-compile of downstream ConceptNodes triggered by an upstream change (§7.4). Two realized paths: the **synchronous** `{ref}`-consumer recompile (cycle-safe BFS) and the **debounced** agent-tick scheduler.
- **Click-and-stick** — the freeze-at-hover-rect mechanic that pins a panel at exactly the screen position the hover billboard was occupying (§4.2).
- **Compiled-from-scans** — peer fixtures derived by the scanner pipeline: `SearchableURL`, `DetectedAccessor`, `XPathPattern`, `PinnedComponent`, `ChunkInstance` (§15.5).
- **ConceptNode** — the universal record (§3.1).
- **Empty primitive** — a freshly-created ConceptNode with no name and no description; the universal authoring start (§5.1).
- **Evolution log** — append-only `EditDiff` table that drives rollback (§11.4).
- **Field-tree** — the editor's renderered form of the `data` field: recursive `name : value` rows with `+→` / `+↓` plus signs (§4.6).
- **Foundation fixture** — Database / WebBrowser / Agent (§9.5).
- **Halo phantom** — collapsed-panel-form name-only representation of an apparition candidate (§4.5 / §8.2).
- **Latch** — the affordance that slides the data block out as an equal-height side panel (§4.4).
- **Lifecycle** — the single mutation dispatcher every actor enters through (§10.2).
- **LayoutFrame** — the persisted per-workspace canonical-coordinate record produced by the Layout Service (§10.3).
- **Lodestar use case** — one of the four trajectories the design's acceptance bar consists of (§16).
- **Autoregressive halo** — the recursive feedback loop where clicking a halo phantom (§8.2.1) commits a hard link (§3.2.1), spawns a new focal panel, and emits a new concentric-ring halo around it; the user walks the retrieval space one click at a time (§8.2.2).
- **Click-to-edit** — the UX contract that every editable field renders in print form by default and opens into a textarea on click, returning to print on Enter / Ctrl+Enter / blur (§4.1.1).
- **Concentric-circle halo** — the polar-coordinate radiation of apparition candidates around a focal panel (§8.2.1). Inner ring = highest similarity; outer ring = lower. **Distinct from the forbidden concentric-sphere layout** (§forbidden-concepts §1) — the halo is a retrieval-score visualization, not a layout authority.
- **Dialectical inversion (compile/collapse)** — the double-left-click toggle (§7.3.4) that flips between the *synthesis* (panel form) and *analysis* (simplified subgraph) representations of the same ConceptNode record. (Right-click is the distinct inline next-rank type-graph fold.)
- **Hard link** — a committed `ConceptEdge` record in Kuzu, persistent, cascade-firing, drawn solid full-saturation (§3.2.1).
- **Imaginary register** — the 2D Concept Editor surface (§1.1, §1.5). Carrier of images of perceptions: concept nodes, halos, the agent's reasoning graph.
- **Mortegon** — the *shape of death* (Morte- + -gon) realised as the bidirectional alchemical flow between the Real (3D Projector), Imaginary (2D Editor), and Symbolic (REPL) registers (§1.1, §1.5). The Seal-of-Solomon-style dialectic between structural definite and free-flowing dynamism. See also [MORTEGON_INTEGRATION_SCHEME.md](MORTEGON_INTEGRATION_SCHEME.md) (historical analysis-plan, §O.17; its operational detail is lifted into §6.1 / §7.3.2 / §4.6 + the `frontend/` suite).
- **No-mocks contract** — real subsystems in production paths, always (§13).
- **Parameter card** — the ConceptNode that holds an agent's `goal`, `step_index`, `paused`, `cascade_enabled` (§12.1).
- **Play loop** — scan ↔ compose ↔ compile ↔ read projector ↔ revise (§16; §8D.25).
- **Provenance** — `scanner-emitted` | `graph-output` | `agent-output` | `user-authored` | `derived-from-chunk` | `committed-subgraph` (§9.12 / §3.1).
- **Read-only** — flag on python-native ConceptNodes; latch hidden, 🔒 indicator, editor refuses data edits (§9.6).
- **Real register** — the 3D Projector surface (§1.1, §1.5). Carrier of perceptual measurements: scanner-emitted chunks and computation-graph outputs in the same UMAP manifold.
- **Scale-space periphery** — the outer boundary of the concentric-circle halo (§8.2.1) where candidates with score below `min_score_threshold` fall off the visible halo entirely. Preserves the polar-coordinate proximity of high-similarity candidates near the focal.
- **Shape of death** — Mortegon's etymological gloss (§1.1): "Morte-" + "-gon". The dialectic of computation between structural definite and free-flowing dynamism.
- **Six-D UMAP** — UMAP fit producing a 6-vector per chunk: 3 position + 3 HSV-colour, with the HSV triplet slowly rotating in phase with camera azimuth (§8.2.1.2).
- **Signal-stream constraint** — under iteration, only the currently-iterated signal node is visible in the 2D panel; other iterable elements remain in storage/queue but suppressed from print rendering (§4.6.1) — for chunk iterables the full distribution lives in 3D (§O.14) and the panel renders the current instance's content per-instance (sampled from 3D or by halo-retrieval, §O.18). Governs `Database.concept` batches and play/pause rollout.
- **Soft link** — a halo-suggested apparition candidate not yet committed; lives in the in-memory apparition cache, lighter visual treatment than a hard link; vanishes when the halo closes (§3.2.1). A click promotes a soft link to a hard link. Spatially laid out on the **possibility ring** (§3.2.1) — distinct from hard links' commitment fan.
- **Spine** — the strict default-collapse rule that ONLY viewport-visible OR pinned-panel-referenced retrieval chunks are visible in 3D (§6.4 / §8.3).
- **Golden trio** — the (title, link, content) field triple that gates content-precise extraction within a chunk-pattern schema (§15.8.1).
- **`pattern_map`** — the canonical output panel of `WebBrowser.scan`; a recursive tree of `ChunkPatternSchema` records that live-updates as the scan streams (§15.8.2).
- **URL-set knowledge panel** — user-created panel that aggregates a multi-URL list under the `{urls_panel}` reference, with url-specific TF-IDF tokenisation and the signal-stream iteration constraint (§15.7).
- **Multi-semantic-frequency-PageRank** — the §1.2.2 retrieval generalisation: triple product evaluated at token / phrase / paragraph / document / pattern bands, aggregated by PageRank-weighted combination across bands (§8.1.1).
- **Library-imports middleware** — generalisation of the Python-API materialiser; reads a simple `imports.py`-style module and walks the resolved symbols' recursive package hierarchy into Object/Property/Function ConceptNode trees (§9.7).
- **Hidden-overlay button** — a transparent click target positioned over a pure-print token region; on click materialises the textarea for editing (§4.1.1). The print remains visually unadorned at rest.
- **Plus-sign right/bottom contract** — the `+→` / `+↓` affordances that appear during Edit state on the right and bottom of the singular key:value compute node, progressively building it into a full panel (§4.6).
- **Ray-projection (halo)** — the 3D-chunk → 2D-conic-surface collapse that places projector-resident manifold-neighbours on the halo's outer ring as collapsed singular nodes carrying their image billboards or HSV-rotating colour (§8.2.1.1).
- **Perimeter-encompassing placement** — agent-output chunks project to the projector's outer envelope rather than into the manifold interior; geometric expression of the Imaginary → Real return path (§6.6.1).
- **2D / 3D separation contract** — the editor canvas and the projector canvas share no coordinate system; coupling is only via click-and-stick (3D screen rect → 2D pin) and live output projection (2D card → 3D chunk) (§6.6.2).
- **Recursion-over-iteration integration scheme** — the agent's tick formalised as one step of an integration scheme over the topology of typed concept graphs grounded by hard-typed Python endpoints; world perceptions are the initial conditions (§12.2.1).
- **Transcendental permanence** — the REPL's property of representing the app's computation graph within its own symbolic space, so the app is self-similar across registers (§14).
- **Infinite self-negation and inversion** — the Mortegon's dialectical mechanism: every commitment negates prior possibilities; every possibility inverts prior commitments. The "shape of death" as a self-consuming cycle (§1.5).
- **Symbolic register** — the REPL surface (§1.1, §1.5). Carrier of representations: REPL actions, WS frames, telemetry, the in-place activity viewer. Total transparency over Real and Imaginary; no autonomous semantics.
- **Triple product** — `pagerank · tfidf_cos · nomic_cos` (§8.1).
- **UI State Service** — the backend mirror of frontend UI state used by the REPL viewer (§10.5).
- **UMAP-linear-radial force-directed hybrid** — the single 3D layout authority (§6.1).
- **Unified panel** — the one widget all surfaces render with (§4).
- **Variable auto-creation** — typing `{slug}` into description/data spawns a new empty primitive if `slug` doesn't match (§17.8 / §8D.21.1).
- **`{var}` reference** — curly-brace ref resolved at compile across name/description/data/rendering (§4.8 / §7.2).
- **`watch-activity`** — the REPL subcommand for the in-place dashboard (§14.5 / §11.8).

### §20.2 Section → Theme Index

| Theme | Sections |
|---|---|
| Vision | §1, §1.1, §1.2, §1.2.1, §1.2.2 |
| Three Registers (Mortegon) | §1.1, §1.5 |
| Real Register (3D Projector) | §1.5, §6, §6.6, §6.6.1, §6.6.2, §9.14, §15 |
| Imaginary Register (2D Editor) | §1.5, §3.2.1, §4, §4.1.1, §4.6, §4.6.1, §4.6.2, §7, §7.3, §7.7, §8, §8.2, §12.6.1 |
| Symbolic Register (REPL) | §1.5, §14, §11.7, §11.8 |
| Principles | §2 |
| Concept Model | §3 |
| Hard / Soft Links | §3.2.1, §8.2 |
| Unified Panel | §4 |
| Click-to-Edit UX (Hidden-Overlay + Shift-Enter) | §4.1.1 |
| Plus-Sign Field-Tree Growth | §4.6 |
| Signal-Stream Constraint | §4.6.1 |
| Authoring Modes | §5 |
| Empty Primitive (Multi-Freq Radiation) | §5.1 |
| 3D Projector | §6, §9 (legacy refs) |
| 6D UMAP (Position + HSV) | §6.1, §8.2.1.2 |
| Perimeter-Encompassing Agent Outputs | §6.6.1 |
| 2D / 3D Spatial Separation | §6.6.2 |
| Compilation | §7, §8D.2, §8D.14, §8D.20, §11.7 |
| Dialectical Compile/Collapse | §7.3 |
| Closest-Inverse as Projective Property | §7.7 |
| Retrieval / Apparitions | §8, §8D.43, §8D.16, §8D.17, §8D.22 |
| Multi-Semantic-Frequency-PageRank | §8.1.1 |
| Concentric-Circle Halo | §8.2.1 |
| Ray-Projection to Conic Surface | §8.2.1.1 |
| Autoregressive Halo Feedback | §8.2.2 |
| Three Foundational Fixtures (Agent / WebBrowser / Database) — §S removed Editor | §9.5, §9.5.1 |
| Python-Library Middleware | §9.7 |
| Streaming / Lifecycle | §10, §11 (in new), §11.4–§11.8 |
| Persistence / Evolution Log | §11 (in new), §8D.31, §8D.33 |
| Agent | §12, §8D.27, §8D.32, §8D.37, §8D.48 |
| Agent as Integration Scheme | §12.2.1 |
| Editor-as-Functional-Object / Agent Entanglement | §12.6.1 |
| No-Mocks Contract | §13, §8D.46 |
| REPL ↔ Frontend | §14, §11.7, §11.8 |
| Scanner / Web Ontology | §15, §8D.39 |
| URL-Set Knowledge Panel | §15.7 |
| Chunk-Pattern Schema + Golden Trio + `pattern_map` | §15.8, §15.8.1, §15.8.2 |
| Type-Inclusion via Inheritance | §15.9 |
| Lodestar Use Cases | §16, §8D.45, §8D.47, §8D.48, §8D.49 |
| Live-Scan + DB-Cleanup REPL Probe | §16.5 |
| Functional Sequences (Sequences Reference) | §17 |
| Editor Mutation Sequence | §17.1.1 |
| Signal-Stream Advance Sequence | §17.1.2 |
| `pattern_map` Iteration Sequence | §17.1.3 |
| `{urls_panel}` Expansion Sequence | §17.1.4 |
| Halo Ray-Projection Sequence | §17.1.5 |
| Known Failure Modes (Anti-Goals) | §18 |
| Removed / Forbidden | §19; top-of-doc notice |
| Glossary | §20 |

### §20.3 Code File → Section Index

| File | Sections |
|---|---|
| `backend/services/concept_lifecycle.py` | §10.2, §2.2, §17.1.1 |
| `backend/services/layout_service.py` | §10.3, §6.1 (6D UMAP), §6.6.1 (perimeter), §8.2.1.1 (ray-projection) |
| `backend/services/concept_index_service.py` | §10.4, §8.1, §8.1.1 (multi-frequency) |
| `backend/services/apparition_service.py` | §8.1, §8.1.1, §8.2, §7.7 |
| `backend/services/conceptual_compute.py` | §10.6, §7.1, §7.2 |
| `backend/services/compile_pipeline.py` | §7.1, §7.2 |
| `backend/services/graph_editor.py` | §3, §5.4, §9.5.1 Editor, §17.1.1 |
| `backend/services/slm_client.py` | §13.5, §9.5.1 Agent.meta_prompt/.prompt/.output |
| `backend/services/embedding_service.py` | §10.4, §8.1 |
| `backend/services/agent_runtime.py` | §12, §12.2.1 (integration scheme) |
| `backend/services/selenium_client.py` | §15.1, §9.5.1 WebBrowser.scan, §15.8 pattern_map |
| `backend/services/python_api_materialiser.py` | §9.6, §9.7 (library-imports middleware) |
| `backend/services/backing_registry.py` | §3.3 |
| `backend/services/backing_version.py` | §15.6, §18.28 (re-import invalidation) |
| `backend/services/evolution_log.py` | §11.4 |
| `backend/services/compiled_from_scans.py` | §15.5, §15.8 (pattern schema) |
| `backend/services/ui_state_service.py` | §10.5, §14, §4.6.1 (signal-stream), §17.1.2 |
| `backend/services/foundation_fixtures.py` | §9.5 (three fixtures; §S removed Editor), §18.27 |
| `backend/services/global_tfidf_store.py` | §10.3, §15, §15.7 (url-specific tokenisation), §8.1.1 (multi-freq bands) |
| `backend/services/rollout_coordinator.py` (planned) | §7.5, §17.1.2 signal advance |
| `backend/api/routes.py` | §10, §14 |
| `backend/api/ws_frames.py` | §10.1, §6.1 (umap_canonical carries 6-vector) |
| `backend/dom/pipeline.py` | §15.3, §15.4, §15.8 (chunk-pattern schema build) |
| `backend/dom/chunk_builder.py` | §15.4, §15.8.1 (golden-trio extraction) |
| `backend/static/js/cp/billboard.js` | §4, §4.1.1 (hidden-overlay edit buttons) |
| `backend/static/js/cp/concept_graph.js` | §4, §5, §7, §4.6 (plus-signs), §4.6.1 (signal stream display) |
| `backend/static/js/cp/scanner.js` | §10.1, §6.1, §15, §6.1 (HSV state per chunk) |
| `backend/static/js/cp/animation.js` | §6.2, §6.1 (HSV-rotation phase loop) |
| `backend/static/js/cp/search.js` | §6.4, §8.3 |
| `backend/static/js/cp/workspace.js` | §6.3, §6.5 |
| `backend/static/js/cp/sprite_manager.js` | §11.2 |
| `backend/static/js/cp/instance_manager.js` | §6.1 |
| `backend/static/js/cp/halo.js` (planned) | §8.2.1, §8.2.1.1 (ray-projection), §8.2.1.2 (HSV rotation), §17.1.5 |
| `backend/static/js/cp/telemetry.js` | §10.5, §14 |
| `scripts/sim_frontend.py` | §14 |
| `scripts/probe_live_archive_scan.py` | §16.1 |
| `scripts/probe_live_concept_graph.py` | §16.2 |
| `scripts/probe_live_agent.py` | §16.3 |
| `scripts/probe_live_iterated_compile.py` | §16.4 |
| `scripts/probe_live_scan_with_cleanup.py` (planned) | §16.5 |

---

## §21 — How To Use This Document

1. **For implementation work,** the design is canonical here + in the [`frontend/`](frontend/) suite. ([`CODEBASE_GAP_ANALYSIS.md`](CODEBASE_GAP_ANALYSIS.md) is **historical**, §O.17 — it audited the now-discarded codebase; do not implement against its code paths.)
2. **For new requirements,** capture verbatim in [`USER_REQUIREMENTS_VERBATIM.md`](USER_REQUIREMENTS_VERBATIM.md) first, then audit the code, then update the gap analysis, *then* update this doc (§2.9).
3. **For verification,** use the REPL (§14) — not screenshots. The in-place viewer (§14.5) is the operator's mirror.
4. **For the operational specifics** of the 3D ↔ 2D mortise-and-tenon, this document + the [`frontend/`](frontend/) suite are canonical; [`MORTEGON_INTEGRATION_SCHEME.md`](MORTEGON_INTEGRATION_SCHEME.md) is **historical** (§O.17), its additive detail already lifted here.
5. **Cross-references** use the `§X.Y` form. They are authoritative when made; this doc + the verbatim file + the `frontend/` suite are canonical (the historical analysis-plan docs of §O.17 no longer win on disagreement).
6. **Forbidden concepts** at the top of this document override any inline text that might predate the deletion. The notice wins.

The four lodestar use cases (§16) are the **acceptance bar**. Anything that prevents any one of them from running end-to-end against the real stack is a design or implementation gap. Anything that *enables* all four is correct.
