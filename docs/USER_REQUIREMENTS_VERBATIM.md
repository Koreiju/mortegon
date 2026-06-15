# User Requirements — Verbatim Source Of Truth

> **Status:** This file captures every binding requirement the user has stated
> across the recent sessions in their own phrasing, organised by topic. Where a
> requirement appears in the user's prompts I quote it directly. Where the user
> requested deletion of an idea (concentric spheres, graph analytics, etc.), the
> deletion intent is recorded here so future doc edits cannot silently
> re-introduce the concept. The domain model (`DOMAIN_MODEL.md`) is the design
> elaboration; this file is the source the design must converge to. When the
> two disagree, this file wins.
>
> No code changes were made when this file was authored. The companion
> `CODEBASE_GAP_ANALYSIS.md` traces each requirement to the current code path
> and the change required. *(Note §O.17: `CODEBASE_GAP_ANALYSIS.md` is now historical — it audited the now-discarded codebase; the design docs are canonical.)*

---

## A. Doc And Process Discipline (Meta)

**A.1 — Doc-first, correctness over comprehensiveness.**

> "I suggest you clear up discrepancies in our documentation along the lines
> that I'm specifying, then making sure that are also reflected in code."
>
> "I need you to pay much closer attention to the solutions you provide to
> ensure that they are correct rather than comprehensive."

The order of operations on every iteration is: (1) capture the requirement in
the doc verbatim, (2) audit the codebase against the doc, (3) produce a written
gap analysis, (4) only then change code. Comprehensiveness without correctness
is the failure mode.

**A.2 — Previous prompts must be carried forward fully and near-verbatim.**

> "Please remember to factor everything about this prompt, including the
> previous prompts' details, fully and almost verbatim in our
> @docs/DOMAIN_MODEL.md."
>
> "ensure that all my own requested details to be added are first formulated
> as close to my own forms of thinking as possible with added details that
> might be good to imply, but never replace, the original works of the
> meanings imbibed in our code within this prompt."

Doc edits may add elaboration but never displace the user's original phrasing.
The user's wording is canonical. The system's restatement is auxiliary.

**A.3 — Remove what counters the design.**

> "remove all other mention of anything that counters the focus of these
> design parameters (remove concentric sphere everywhere, remove graph
> analytics as well)."

Hard deletions, not deprecation notes that linger. The doc, the code comments,
and the surrounding scaffolding must all stop referencing concentric-sphere
layouts and graph-analytics retrieval frameworks. The Mortegon scheme's §2.1
phrasing of "no Fibonacci, no hash" applies across the project.

**A.4 — The preview is not feature proof.**

> "You should not rely on the preview to assess the completeness of your
> answers because the features I requested aren't present, even if you can
> see an image."
>
> "Note that you should not use the preview eval, and rather ensure our REPL
> functionality is correct in the terminal, since its the true 'preview
> eval' we're going for."

A screenshot showing boot wiring does not prove the feature works. Verification
runs in the REPL against the live full stack: the REPL drives gestures, the
frontend renders the result of those gestures, and the REPL reads back the
telemetry the frontend produces. Screenshots are reference artifacts only.

**A.5 — No mocks in production paths.**

> "When you go to develop code and find 'fake' or 'dummy' implementations of
> things like SLMs or quantized embeddings or otherwise, revert the
> functionalities to ensure they use the exact real python code required to
> properly accomplish the full task."

Real GPT4All, real nomic, real Selenium, real LangGraph — always. Fake gates
exist only for the harness and only by explicit env var. `WFH_FAKE_SLM=1`,
`WFH_FAKE_EMBEDDER=1`, `NO_WEBDRIVER=1` are the harness gates; production
endpoints set none of them.

**A.6 — Mistral Hermes 2 DPO + dual embedding + triple parameter.**

> "We want to use mistral hermes 2 dpo and our dual embedding and triple
> parameter (tfidf, nous embeddings 1.6, and pagerank)."
>
> "Please enforce the use of mistral 2 dpo everywhere. No Llama allowed."
>
> "Please ensure that we use CUDA in all our LLM runs."

The SLM target is `Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf` on CUDA — across
backend defaults, every probe, every REPL action, every scenario. Llama is not
a fallback. The embedder is `nomic-embed-text-v1.5.f16.gguf` on CUDA. The
triple-product apparition score is `pagerank · tfidf_cos · nomic_cos`; the two
embedding axes (nomic over description, TF-IDF over rendering) never mix.

**A.7 — Read everything; don't delegate understanding.**

> "Do not send a haiku agent or anything to review, and read everything
> yourself to keep valuable contextual information with you in-memory."

Synthesis stays in the main session. Agents are tools for narrow lookups, never
substitutes for the main thread's reading of the doc, the code, and the prompts.

---

## B. The 3D Layout — UMAP-Linear-Radial Force-Directed

**B.1 — Live scan ↔ streaming linkage.**

> "Live scan updates are completely broken from streaming to the frontend now
> (completely severed scanning vs streaming to the frontend and no live umap
> updates, a huge fault)."

Scanning and streaming are joined: a chunk that the scanner emits reaches the
frontend through the WebSocket on the same workspace, and the scan-end UMAP
fit produces a `umap_canonical` frame that the same frontend subscribes to.
There is no workspace-id mismatch, no silent broadcast drop. The user observed
the link is presently severed; the joined state is the requirement.

**B.2 — UMAP-forced-linear-radius layout replaces concentric spheres.**

> "Umap only applies at the very end. We want the UMAP-forced-linear-radius
> layout to completely replace the concentric spheres entirely."
>
> "Our 3D concentric layout is still producing very uneven spheres for very
> large nodes. I suggest you come up with an original formulation that is
> mathematically sound, or otherwise research or propose a novel way of
> dynamic layouts. I would almost suggest a simple force-directed layout
> that dynamically updates independent of the new nodes being streamed in,
> combined with a 3D UMAP re-mapper for the new, full chunk space."
>
> "we can run [UMAP] as the 3D node layout updater/initializer more directly,
> then apply force-directed layouts only along radius lengths from root url
> nodes such that simple collision boundaries are met, while chunk nodes
> (with UMAP 3D re-initialization over the full set of chunk nodes in our
> 3D gui, simply programming in the 'recompute UMAP button function'
> directly into the 3D layout initializations that are sent to the
> frontend). Then, force-directed algorithms dynamically update the lengths
> of the lines that connect the chunk nodes to their URL, such that these
> lines are traced force-directedly for all nodes initialized in the UMAP
> layout. That means that nodes are constrained to move only along the
> lines that initially traced between them and their centroided URL nodes."
>
> "This means our UMAP-linear-radial force directed layout replaces our
> concentric sphere layout updates entirely."

The single layout pipeline: UMAP places chunks (initial + every refit),
force-directed converges along root-URL rays, collider repulsion is hard. No
concentric layer indexing. No Fibonacci-as-final-position. The "Recompute
UMAP" button function *is* the layout initialiser — it fires at the tail of
every scan automatically, not just on a manual press.

**B.3 — Hard collider repulsion, not 1-sigma falloff.**

> "Please also ensure adequate repulsive forces between node boundaries that
> are very sharp, such that the repulsion doesn't persist for some 1-sigma
> distance beyond the billboard lengths, and this is what determines node
> radii distances from the root url nodes."
>
> "Layout issues also in the 3D layouts with spacing too close together."

Repulsion is hard: zero force above `2·R·safety`, exact-correction-in-one-step
below. The collider radius is a single workspace constant; image billboards
and text billboards share it. The current visible-too-close-together failure
demands the safety multiplier be raised to a value where every pair is
demonstrably separated.

**B.4 — Per-URL bounding radii drive multi-scan placement.**

> "All scans share a common root url coordinate at the origin, which is
> incorrect. I mean that the maximum bounding radius on each independent
> scan determines how far apart url scan graphs are placed from each other.
> I would like you to ensure that the camera origin is always focused on
> the most recent url being scanned, with the previous scans being
> appropriately distanced from the new scan with the combined maximum
> bounding radii between the root URL nodes."
>
> "Maximum radius colliders between DOM maps/layouts are not adequately
> updated for updates to graph layouts over new scans."
>
> "if I compute a UMAP and scan a new page, I expect the UMAP that was
> previously computed to persist its 3D node values. Then, the new dom
> sphere that's dynamically updated and the UMAPped previous scan(s) aren't
> perturbing each other's layout."

Each URL has its own `root_position` and `bounding_radius` in the workspace's
shared frame. A new URL lands at
`existing_max_radius + new_workspace_radius + safety_gap` from existing
centroids, in the direction with most empty space. Old URLs' positions never
move when a new URL is scanned. Camera tweens to the new URL's root.

**B.5 — Stable integer chunk IDs.**

> "I suggest re-computing the full 3D coordinates and tracking new indices to
> old through efficient integer data IDs for chunks that are the chunk IDs
> from our scanner, and then efficiently update all 3D coordinates for
> nodes in that manner, where the integer ids of the scanned chunk nodes
> are corresponded to the updated xyz coordinates from the appended integer
> IDs of new chunks."

Every chunk keeps its integer id permanently. UMAP coordinate updates apply by
id-lookup. The TF-IDF index, the LayoutFrame, the 2D editor's
`data-3d-node-id`, the IndexedDB texture cache all key by this id.

**B.6 — Latency rules across three streams.**

> "Please make sure that latency inconsistencies between umap updates to new
> chunks and streaming to the GUI and from the scanner are also handled
> gracefully throughout any edge cases that may arise from our initial
> focused update here."

Three streams converge at the frontend: chunk stream (WebSocket), UMAP-coord
stream (`umap_canonical` frame), and the client's force-directed loop. Chunks
arrive with a hash-direction-plus-radial-distance placeholder until UMAP
catches up. A UMAP frame replaces placeholder positions; locked chunks skip
subsequent placeholder layouts. A chunk that arrives mid-UMAP keeps its
placeholder and joins the next scan-end UMAP. The user sees a snap only at
scan-end, never mid-stream.

**B.7 — Camera bounds.**

> "Camera zooms far too inwards into the dom and there are no proper bounds
> on the camera perspective to ensure that the entire scan is visible on
> the screen."
>
> "There is little to no mouse scroll zoom option, perhaps because of the
> constraint set to get everything in view, or for any other reason."

`minDistance = 0.6 × cluster_radius(orbit_target)` recomputed per frame.
`maxDistance = 3 × max(|chunk.position|)` recomputed per frame. Scroll-zoom is
fully responsive — no cap that saturates the wheel.

**B.8 — Frame-on-scan, respect user interaction.**

> "I would like you to ensure that the camera origin is always focused on
> the most recent url being scanned"

On scan-end, camera tweens to `new_root_position` at distance
`1.8 × bounding_radius`. If the user has interacted with the camera AND the
new root is already in the view frustum, the tween is suppressed.

**B.9 — Adaptive resize.**

> "Main 3D UI screen resize is stuck and not resizing to the proper layout,
> but the 2D UI does resize successfully"

The canvas resizes from both `window.resize` (rAF-coalesced) and a
`ResizeObserver` on the 3D-panel DOM. `setSize(w, h, updateStyle=false)`
keeps `width:100%;height:100%` as the layout authority. No no-change guard —
`updateStyle=false` breaks the historical feedback loop at the source.

**B.10 — Recompute UMAP button must not silently dedupe.**

> "Pressing recompute umap twice in a row doesn't re-compute the UMAP"

A manual recompute fires the full pipeline regardless of prior state. No
client-side idempotency gate.

**B.11 — Concentric layout language is removed.**

> "I don't know why concentric sphere layouts have been re-added either.
> Entirely incorrect."

The word *concentric* does not appear as a current-architecture descriptor
anywhere in the doc or in the active code. The 2D editor's previous concentric
ring layout (§8D.10) is rewritten to the same UMAP-linear-radial idiom in 2D:
chunks land per a 2D UMAP (or its concept-graph equivalent) and a 1D
ray-constrained refinement keeps cards from overlapping. No depth-indexed
shells. No Fibonacci-as-primary.

**B.12 — No stray UI dotted lines.**

> "There is a stray dotted line that runs out from the UI that shouldn't be
> there, I don't know why you're wasting time adding unnecessary things
> like this."

Dotted leader lines, dotted 2D↔3D arrows, dotted debug overlays — all removed
unless explicitly requested. The 2D↔3D link arrow is a solid line and only
exists when the panel and node are both alive.

---

## C. The Unified Knowledge Panel

**C.1 — One panel, one anatomy, one code path.**

> "Hovering over the *first* node in our 3D GUI pops our regular knowledge
> panel window up, but when I click it, a completely different knowledge
> panel appears."
>
> "Hovering over nodes and clicking them should *stick the exact same
> knowledge panel that appeared when hovered in the exact same place where
> it was hovering*."
>
> "There should be just one kind of node model that is dealt with when it
> comes to hover, preview, apparition, etc."

The hover billboard, the click-pinned panel, the apparition-halo phantom, and
the compiled-graph child node all render from one template using one code
path. There is no second pin-panel widget. There is no separate "content
summary" panel.

**C.2 — Freeze-at-hover-rect on click.**

> "Clicked node panels appear in a completely different place from where
> they were clicked in the 2D UI."
>
> "clicking on 3D nodes after hovering over their panel 'stick' the panels
> in a different place from where the node hover showed the original
> panel."

On click, the hover billboard's current screen `(top, left)` rect is captured
and the new pinned panel materialises at exactly that rect. The hover
billboard then resets so the next hover can preview a different node.

**C.3 — Multi-pin draggable resizable minimisable.**

> "I can open multiple nodes' knowledge panels at a time."
>
> "When I go to stick the combined node editor/knowledge panel to the 2D
> editor gui, I should be able to then click, drag, *and* resize the
> panels."
>
> "ensure that these knowledge panels are both draggable, and also have a
> minimizer button, similar to our logging panel. This persisted multi-node
> selection and dragging and minimizing gives us the 'click-and-stick'
> effect."

Each pinned panel is independently draggable (header is the drag handle),
resizable (CSS `resize: both`, outer `overflow: hidden`, body `overflow:
auto`), minimisable (collapses body, leaves header), and closeable
(`×` button unpins; underlying 3D node persists). Clicking the same chunk
twice raises the existing panel's z-order and un-minimises it.

**C.4 — Stuck panels start collapsed.**

> "Sticked node panels should also start collapsed. The apparition ring
> should be the same format as collapsed nodes."
>
> "Panels that stick in the GUI that aren't being immediately hovered over
> or clicked should stay collapsed + minimized."

A newly pinned panel renders in collapsed form. The apparition halo phantom
shares this collapsed form. Hovering or clicking the panel expands it; moving
away re-collapses.

**C.5 — Foundational fixtures cannot be `×`'d out.**

> "Fundamental objects cannot be 'X' ed out."

Database, WebBrowser, Agent. The `×` button is absent on these panels.

**C.6 — Concept graph computation nodes mimic the same gestures.**

> "Concept graph computation nodes should mimic the same hover/click to
> expand both graph links + details + apparitions in the fused gestures."

A computation-graph node hover and click follow the same anatomy and the same
gesture as a chunk node. Halo apparitions fire on hover. Compile/collapse
fires on right-click.

**C.7 — Right-click toggle: panel ↔ compiled graph.**

> "When right clicked again, they fold back into the original knowledge
> panel with the collapsed, latchable sliding hidden data block and the
> remaining three fields displayed normally."

A right-click on the panel's central node toggles between the collapsed
knowledge panel (name + description + rendering visible; data field hidden
behind the latch) and the expanded compiled graph (the data field's
syntax-agnostic decomposition rendered as children, each child showing only
its value). A second right-click folds back. The underlying ConceptNode record
is untouched by either flip.

**C.8 — Latchable sliding data block.**

> "fold back into the original knowledge panel with the collapsed, latchable
> sliding hidden data block and the remaining three fields displayed
> normally."

The data field is not inline. A latch button on the panel slides the data
block out as a side panel at equal height. The base panel shows name +
description + rendering. The latch is hidden on read-only python-native
fixture panels (which carry a 🔒 indicator instead).

**C.9 — Curly-brace references span description and data and rendering.**

> "In the world of the base modules, their objects are referenced by the
> curly braces, which link two objects together. We shall introduce curly
> brace linking between nodes into the description as well for this
> reason."

`{slug-shaped-ref}` resolves on Compile from any editable section (name,
description, data, rendering). Cycle-safe recursion. Unresolved refs stay
literal.

---

## D. Apparition Halo — Name-Only Compact Standard

**D.1 — Apparition halo shows only the name.**

> "There are various details mentioned perhaps elsewhere in the docs on the
> interaction properties and user experience activities on
> interactive/dynamic retrieval halo properties of apparition nodes, which
> literally should just display the name without anything else. This is a
> compact representation standard everywhere in the concept computation
> graph compilations in terms of representations."

The halo phantom carries the candidate's **name only**. No score chips, no
description preview, no rendering excerpt. Scores live in slow-hover tooltips.

**D.2 — Compiled-graph children show only the value.**

> "ensure to accomplish each and every task I set you out to do from the
> culmination of all prompts of my own throughout this chat. […] please
> document in minimal naming scheme in compiled form everywhere without
> even the monotonous 'name' field."
>
> "I would hope for a data-agnostic recursive tree interpreter for rendering
> the variable key:value fields that are generalizable between syntaxes
> and their native types, which when compiled, only show the values of the
> keys on computation graph concept nodes."

In the compiled-graph view, every child shows only its value. The "name"
field is implicit from structural position. Multi-line values expand the box
to fit.

**D.3 — Halo radiates from any focal panel.**

> "The advance in our framework comes from how primitives are represented
> and interacted with. Our 2D concept graph compilation editor begins with
> the base universal primitive 'empty' node. This empty node shows all
> possible functional links extending from the empty node for the user to
> select and play around with. As the user types in descriptions and
> values, these fields are embedded via quantized SLM transformer and
> retrieval is applied to all nodes in the database, showing optional new
> functional objects radiating around the primary empty primitive node.
> Once the first object is created, the retrieval over suggested linked
> nodes enables the user to quickly link new functional objects and route
> new signals through the conceptual computation graph."

The empty primitive is the universal start. Description and value embed under
the SLM transformer; retrieval radiates candidates around the focal panel.
Selecting a candidate creates the link and wires the signal.

**D.4 — PageRank-weighted retrieval on description+rendering jointly.**

> "Also, when we begin our concept graph editor with an empty node, we
> perform pagerank-weighted retrieval over the rest of the saved nodes in
> our semantic graph database using description and rendered value fields
> jointly, or just one or the other if one field is empty."

The triple product `pagerank · tfidf_cos · nomic_cos` is the retrieval rank.
Description goes through nomic; rendered value goes through TF-IDF. The two
axes never mix.

---

## E. Compute Graph + Compile

**E.1 — Recursive syntax-agnostic compile.**

> "compile button on our duplicate knowledge panel cards from our old graph
> compiler update […] does not work. What this means is that, while
> rendering is correct, it does not correctly compile the data structure
> into its components recursively and independent of syntax over recursive
> tree structures. This still needs to be implemented."
>
> "I would hope for a data-agnostic recursive tree interpreter for rendering
> the variable key:value fields that are generalizable between syntaxes
> and their native types"
>
> "The API object python bindings vs static knowledge cards both imported
> from the scanner 3D GUI vs custom templates generated from langgraph
> pydantic and by the user in the graph editor and so on call for a much
> more integrated recursive compilation and rendering scheme in terms of
> the very structurality of how knowledge cards are presented and
> organized."

One recursive descent. JSON, bracketed lists, indented trees, HTML element
trees, plain text — all handled by the same routine. Top-level entries
decompose into child concept cards keyed by `<panel_id>__<key>`. The parent's
section becomes `{child_key}` references. The next Compile press substitutes
through the children.

**E.2 — Data-block components are removed.**

> "This means that data block components are removed entirely for editable
> text-only object fields that interface with multiple syntaxes of data
> objects themselves."

There is no JSON textarea, no schema-shaped data widget. The data field is a
field-tree of key:value rows. The latch (C.8) is how the user opens it as a
side panel.

**E.3 — Plus signs grow the field tree.**

> "We can add horizontal (Parent-child) and vertical (neighbor) field with
> plus signs that appear and link as cutout templates to the real field
> that appears when either plus sign is then hovered over and clicked."

Each row exposes `+→` (horizontal — adds a child to the right) and `+↓`
(vertical — adds a sibling below). The plus signs render as cutout templates;
hovering them previews the slot they will create; clicking materialises the
slot.

**E.4 — Each node is name + value; values can be multiline with `{var}`.**

> "Each node has a name and a value, could be numerical and singular, could
> be multiline with curly brace references."

Numerical-singular and multiline-with-`{var}` are both valid. The renderer
shows the field-tree's tab-and-newline indentation; the value's `{var}` refs
are live links to other concept nodes.

**E.5 — Auto-complete over linked structures within python-bound objects.**

> "I would hope for a data-agnostic recursive tree interpreter for rendering
> the variable key:value fields that are generalizable between syntaxes
> and their native types, which when compiled, only show the values of the
> keys on computation graph concept nodes. […] This means auto-complete
> over nodes is structured as such between linked structures within the
> python-bound object card frameworks"

Typing in a row's name field offers completions from existing concept node
names. Selecting a completion inserts `{linked_name}` into the value. Inside
a python-bound object card (Database, WebBrowser, Agent, or any materialised
python_object), the completion list is scoped to the object's
properties/functions and recursively through their linked types.

**E.6 — Functions infer input and output types as they emerge.**

> "Functions as concept node graphs infer input and output types as they
> emerge. Both input and output variable objects can be referenced through
> recursive templates to other points in the API (python package). These
> i/o types can then also be templated with pydantic and prompt parsing in
> langgraph for SLM interaction with regular api objects fluidly. In our
> new computation graph editor, if we have a function that takes input
> variables and compile the graph, the function node calls forward and
> outputs its own types (which are inferred upon output to be the object
> model of the output). Then, if/when we compile our graph with functional
> nodes, where we assign a concept node/graph to the output but not the
> input, we use a closest-inverse lookup to find the closest/most related
> set of input nodes."

A function-node's output type is inferred from its output value's object
model. If the user wires an output to a concept node without binding the
input, closest-inverse lookup over nomic-similarity supplies the most-related
input candidate. The inverse is automatic — compilation applies forward call
and inverse closest-lookup in one pass.

**E.7 — Play / pause iterated rollout edit.**

> "pressing 'play/pause' can enable the user to edit the computation graph
> at various phases of the rollout when selecting different nodes within
> it to edit and either add or update data structures (including
> computation graph/knowledge template rendering scheme addition,
> modification, variable referencing and linking in multiline string
> fields as normal)."

Play runs the compilation as a recursive rollout over sampled chunks (or
sampled inputs). Pause halts at the current node; the user edits and
re-resumes. Selecting a different node localises edit context to that node's
sample of the rollout.

**E.8 — Recursive chunking is downstream-SLM-friendly.**

> "The idea would be for the computation graph to abstract from the data
> itself by applying recursive chunking over large outputs like DOM scans,
> where chunks are standardized as knowledge object types as a downstream
> task for an SLM."

Outputs that exceed a chunk size are recursively chunked; each chunk becomes
a downstream input the SLM can process. The compute graph composes over
chunks, not over raw payloads.

**E.9 — Diff-consistent state under sample iteration.**

> "We ensure our state is diff-consistent such that when we roll back our
> recursion computation to a new sample in an early node, we re-localize
> our context to support recursion over that one computation node for all
> computation nodes."

Rolling back the rollout to an early sample re-localises the entire
downstream context. Sample iteration draws from a generalised-forward-
truncated bank of xpath patterns; context-aware yield sampling re-renders the
templates per sample.

**E.10 — Token streaming from the SLM agent.**

> "We need to integrate GPT4All nous hermes mistral 2 DPO within langgraph,
> and also need to be able to use live token streaming as an output from
> our agent function-object."

Real GPT4All under LangGraph. Token streaming reaches the agent function-
object as live output. The agent's token buffer surfaces in the panel body.

**E.11 — Intermediate rendered nodes are visible.**

> "in our computation graph (2D), we see the intermediate rendered nodes as
> the signal itself passes through each object in our computation graph
> over function calls and memory references to existing data that
> functions haven't generated."

Every intermediate value renders as a child node with only its value visible
(D.2). The graph's structural backbone shows the function flow; the children
show the data that flowed through.

---

## F. The Three (And A Half) Base API Objects

**F.1 — WebBrowser.**

> "Web browser API object [web_query(str: url, ?str: query), int: samples]
> -> recursive DOM scan with search fields (hence the ? in 'query' for if
> search fields are not immediately available prior to a full scan, and
> note pagination is implicit to the scan of the page, in which the
> discovered pagination button for the next page is pressed iff there are
> still more samples to be drawn... Until there is completely stale
> pagination and we transition back to a previous url if/when we click
> pagination buttons)"

`web_query(url, ?query, samples)` is the signature. The recursive DOM scan
discovers search fields if any; pagination is implicit — the next-page
button is pressed iff more samples remain; on stale pagination we transition
back to a previous URL.

**F.2 — Database (Graph Database API).**

> "Graph Database API Object [search(str: semantic_query), cypher(str:
> cypher_query)]"

`search(semantic_query)` is TF-IDF + nomic dual retrieval. `cypher(query)` is
real Kuzu Cypher. The database is the unified storage substrate (persistence
+ TF-IDF + concept graph + web ontology + meta-cognition surface).

**F.3 — Agent.**

> "Agent API object [agent(str: meta prompt, str: prompt, str:
> ?pydantic_output_template)] where the pydantic output template is
> optional, and meant for data structure verbosity on outputs, but isn't
> required to enforce graph compilation over artifacts like JSON (to
> start)"

`agent(meta_prompt, prompt, ?pydantic_output_template)`. The pydantic
template is optional. Output schema enforcement is opt-in, not mandatory.

**F.4 — EnvState is absorbed; AgentState is a subgraph not a fixture.**

> "Env State (all the rendered nodes in the 3D projector/layout) / Agent
> State (the amalgamated 2D computation graph of the agent acting in the
> 3D Env State, which we also want to construct ourselves and autonomously
> simultaneously in the graph editor); this object is invisible to show
> its 2D computation graph inside"

EnvState collapses into Database (the 3D projector is the rendering surface
on the unified TF-IDF index). AgentState is the live computation subgraph
visible in the 2D editor; it is not a separate fixture card. The three
fixtures are Database, WebBrowser, and Agent — the latter being the
meta-cognition tick + emitter catalogue, with the agent's body subgraph
authored by the user (and by the agent itself, recursively).

**F.5 — Each base object decomposes into Object/Property/Function nodes.**

> "Each of these base objects have properties, methods, and names, and can
> each be broken down into our conceptual node compilation editor as a
> graph that links methods and properties back to their class node, where
> methods are open links with phantom/imperative node outputs and
> properties have value fields filled in their conceptual nodes."

The python-native materialiser projects each base object into a concept tree
with `python_object`, `python_property`, and `python_function` nodes.
Functions carry input-type and output-type ports; their output is a phantom
node that materialises when the function fires. Properties carry filled
value fields.

**F.6 — Read-only sentinel on materialised python-native nodes.**

> "missing 'agent' concept node"

The agent concept node is present as a foundational fixture. Its function
children are read-only (🔒 indicator, no latch, no edit). The function body
is never rendered as a data block.

---

## G. Retrieval — Scroll Spine + URL Toggles

**G.1 — Scroll-and-pop-out spine.**

> "Retrieval has fallen back to a stale functionality, not a dynamic
> scroll-and-pop-out when nodes are collapsed over their urls. When chunk
> nodes are collapsed over their urls, and I go to scroll over retrieval
> results, I want an 'expanding spine' kind of effect between scrolling
> over 2D and seeing 3D nodes pop out from being folded into their url
> nodes. As I scroll, only the results that are immediately visible in the
> bar should be popped out as nodes."

Chunks default to collapsed-into-hub. An IntersectionObserver on the result
list flips `chunkCollapseTarget = 0` for the rows currently in the scroll
viewport. Off-viewport rows fold back. There is no global "show all" and no
third path.

**G.2 — URL sidebar click toggles only that URL's chunks, scoped to viewport.**

> "When I click on a url in the side bar, all nodes explode outward and not
> minimally and dynamically with the result cards that are visible in the
> scroll bar at the time. When I click a URL in the retrieval sidebar
> that's collapsed in the 3D UI, a lot of the result nodes are collapsed
> unnecessarily and completely incorrectly."

URL click toggles only that URL's chunks. When a search is active, the
toggle is scoped to the viewport-visible rows for that URL. Other URLs are
untouched.

**G.3 — URL eye-button flips a hidden flag the animate loop honours.**

> "Url scan visibility buttons in the workspace 2D sidebar on the left do
> not hide/reveal the scanned DOMs they are associated with."
>
> "Url DOM graphs that are collapsed should hide the nodes, including the
> image billboards shown."

The eye button flips a per-URL `hidden` boolean. The animate loop reads the
set every frame and forces `scale=0` on every chunk and hub of every hidden
URL. The mesh's intrinsic scale is never touched.

**G.4 — Hover preview uses the unified panel; no "root summary".**

> "Summaries for hovered retrieval results point to the root url with a
> summary, also completely incorrect functionality. We need the full
> knowledge panels, the same ones combined from our two that exist
> currently. Hovered result previews also stop showing up after the first
> one is hovered (incorrectly to this mythical 'root summary' that is
> incorrectly or perhaps outdatedly there)."

Hover over a result row shows the unified knowledge panel for that result,
positioned near the row. No "root summary." One billboard instance; content
swapped per hover.

**G.5 — Old domains/URLs do not survive reset.**

> "Old domains/urls that have been erased from a reset still persist in the
> GUI, and persist even still after removing the urls from the workspace."

`POST /api/purge_workspace` is authoritative: walks every concept, fires
delete-lifecycle for each, drops the persisted LayoutFrame, resets the
frame_seq counter, emits one consolidated `purge_workspace` WS frame. The
frontend removes every hub, chunk, pinned panel referring to a purged chunk,
apparition cache entry, concept-index cache slot, agent-token buffer, and
frame_seq high-water mark for the workspace.

**G.6 — Click a search result row → fly + pin.**

> "When I click on a url in the side bar […]" / "Click on an .instance-row
> […]"

Row click sets `chunkCollapseTarget=0`, flies the camera to the chunk's 3D
position, and pins the chunk's unified panel.

---

## H. Images

**H.1 — Image persistence — single-fetch path.**

> "Images keep having to reload and are not properly persisted in their data
> stores. Please make sure image assets are efficiently stored and
> referenced always and without interruption for the full span of their
> existence within a rendered layout."
>
> "Images have also stopped being displayed on nodes altogether."

In-memory cache, IndexedDB blob cache, proxy fetch, direct fetch — in that
order. The `X-Image-Proxy-Note` transparent-PNG fallback is never cached as
a successful image. Two chunks pointing at the same image URL share one
`THREE.Texture`. The presently-missing-images failure demands an audit of the
loader path and the cache key.

**H.2 — Image-billboard spacing under UMAP.**

> "Please dynamically scale the UMAP layouts such that no image billboards
> are spaced closer than their total space apart between nodes, with an
> added safety factor."

The collider radius constant is shared by image and text billboards. The
UMAP post-processing pass guarantees every pair is at least
`2 · R_collider · safety` apart along their connecting vector.

---

## I. The 2D ↔ 3D Link Arrows

> "I would also like to see hard-filled-in 2D lines linking the 2D
> stickable draggable knowledge panels and their 3D node correspondences.
> I want this to dynamically update so as to track the full moving
> structure of the 3D with the static of the 2D stuck cards."
>
> "Current arrows are dotted between 2D-3D nodes and do not actually link
> to the 3D UI, likely cause the 3D UI doesn't resize correctly as the 2D
> one"

Every pinned panel carries `data-3d-node-id="<chunk-id>"`. The animate loop
calls `_drawConcept3DLinks` every frame, projects the node's world position
to screen, and draws a **solid** yellow SVG arrow from the panel's nearest
border to the projected screen point. Off-frustum nodes hide their arrow.
No dotted lines anywhere.

---

## J. REPL ↔ Frontend Liveness

**J.1 — REPL is the verification surface.**

> "Note that you should not use the preview eval, and rather ensure our
> REPL functionality is correct in the terminal, since its the true
> 'preview eval' we're going for."
>
> "You must focus your development and scenario test efforts on the REPL
> and ensure that the REPL is only interfaced with via the frontend
> actions and results. This means anything you interact with in the REPL,
> shows up in the real frontend, and when the frontend does something and
> sends telemetry of what changed, that also shows up in the CLI."

Every gesture has a REPL action that performs the same backend mutation the
frontend would. Every frontend mutation emits telemetry the REPL reads. The
REPL ↔ frontend round-trip is the integration test: REPL action → backend
mutation → WS frame → frontend renders → frontend telemetry → REPL reads
back.

**J.2 — Gesture coverage is comprehensive.**

> "Please expand on comprehensively covering the full set of possible
> gesture activities that should be possible as they are laid out in the
> design. […] All the bells and whistles should be included in at least
> one instance for every mentioned design feature and corresponding
> gesture-output interactions in our REPL"

Every design-mentioned gesture has at least one REPL action and at least
one env-scenario covering it. The gesture catalogue includes: hover, click,
drag, resize, minimise, close, right-click compile/collapse, latch toggle,
plus-sign field-tree growth, scroll-spine, URL eye-toggle, URL × delete,
domain-tree click, result-row hover/click, halo apparition surface, link
arrow draw, camera tween-on-scan, multi-pin stack, foundation-fixture
delete-guard, autocomplete-on-name-field, play/pause iterated rollout.

**J.3 — RAG application is a fully-wired scenario.**

> "automating a simple rag application by wiring up a real scan, our
> database, and our SLM."

One scenario: real Selenium scan → real chunks in real Kuzu+TF-IDF →
real `Database.search` call → real `Agent.invoke` with a templated prompt
referencing the search results → real GPT4All Nous Hermes 2 DPO answer →
output reaches the frontend.

**J.4 — Compile cards to graphs and back again.**

> "you may also wish to write some repl test cases on being able to compile
> cards to graphs and back again with right clicks, as well as halo
> interactions over hovering with compiled computation graph nodes as
> well."

REPL actions exist for: right-click compile-expand, right-click
compile-collapse, hover over compiled-graph node, halo apparition surface on
compiled-graph node. Each captures the frontend's UI state mirror and
verifies the round-trip.

**J.5 — Iterated compile over sampled chunks.**

> "Please sketch in the details of the current two activities we've dealt
> with already and merge them into a unified activity of applying an LLM
> computation with some kind of templated output via langgraph and
> pydantic template compilation usage, and apply recursive iterated
> computation of the compiled graph nodes over sampled chunks from scans
> of archive.org."

One scenario unifies §8D.45 + §8D.47 + §8D.48 — scan archive.org, author a
three-node langgraph+pydantic templated compute graph
(`chunk_sample` + `structured_prompt` + `formatted_output`), iterate over N
sampled chunks, play/pause between iterations, right-click compile/collapse
on the compiled nodes.

---

## K. What Is Removed

**K.1 — Concentric Fibonacci spheres** (forbidden):

- §9 / §9.1 / §9.13 concentric layout references → removed
- §8D.10 "2D Concept-Graph Layout: Concentric with Barrier Colliders" →
  rewritten as a 2D UMAP+ray-constrained layout
- `fibSphereUnit`, `docShellRadius`, `clusterRadius` as the **primary**
  layout authority → removed from code (they may survive only as the
  pre-UMAP hash-direction placeholder of B.6, never as a final position)
- MORTEGON §2 / §6.4 mentions of Fibonacci as primary layout → rewritten

**K.2 — Graph analytics** (forbidden):

- §8.3 "Graph Analytics Integration" → removed
- §12 "Graph Analytics: Algorithms, Embeddings, and Evolutionary
  Segmentation" → removed (the entire 1400-line chapter)
- Per-node `wl_hash`, `subtree_size`, `branching_factor`, `cluster_id`,
  `pattern_frequency`, `content_density` columns in the knowledge panel →
  removed
- Auto-fit hyperparameter search → removed
- Per-section mentions woven through §1, §6, §11 → removed

**K.3 — Llama** (forbidden):

- `WFH_SLM_MODEL=Llama-3.2-1B-Instruct-Q4_0.gguf` as a probe default →
  removed
- Llama as a fallback when CUDA fails → removed (the failure is loud, not
  silent)
- The `_FAST_HARNESS_MODEL` constant is deleted (or renamed; the harness
  uses Nous Hermes too)

**K.4 — Two-panel hover/click split** (forbidden):

- Any rendering path that produces a different panel on click than on
  hover → removed
- Any "content summary" widget separate from the unified panel → removed
- Any "root summary" tooltip on result-row hover → removed

**K.5 — Concentric concept-graph rings** (forbidden):

- 2D editor's concentric ring `_fibonacciPosition` → rewritten as
  ray-constrained placement around the focal card
- Per-anchor index counters that distribute children around concentric
  rings → rewritten

---

## L. Acceptance Bar

The design is met when:

1. `GET /api/subsystem_status` reports `all_real: true` with
   `slm.model = "Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf"`,
   `slm.device = "cuda"`, `embedder.device = "cuda"`,
   `selenium.singleton_bound = true`, `langgraph.has_StateGraph = true`.
2. The frontend renders chunks live as they stream from the scanner. A
   scan-end UMAP fit emits `umap_canonical`; the frontend tweens chunks
   into the canonical positions; the user sees a single snap at
   scan-end, never mid-stream.
3. Two scans of different URLs produce two non-overlapping clusters with
   the configured `safety_gap`. The camera tweens to the second URL.
   Re-scanning the first does not move the second URL's chunks.
4. Hovering a 3D node shows the unified panel; clicking it spawns the
   pinned panel at the exact same screen rect. The hover billboard
   resets. Repeat clicks raise the existing panel.
5. The retrieval result list's IntersectionObserver pops chunks out of
   their hub only for viewport-visible rows; scrolling past re-folds
   them; clicking a URL toggles only that URL's chunks; the eye button
   hides every chunk and hub of the URL.
6. Right-clicking a panel central node expands it into the compiled
   graph (children show value only). Right-clicking again folds back
   into the panel (name + description + rendering visible; data hidden
   behind the latch). The compile is syntax-agnostic: JSON, indented
   tree, HTML, plain text all handled.
7. Typing in a new row's name field offers completions over linked
   concept-node names. Selecting one inserts `{linked_name}` into the
   value. `+→` and `+↓` plus signs add child and sibling rows in the
   field-tree.
8. The empty primitive surfaces apparitions ranked by
   `pagerank · tfidf_cos · nomic_cos`; the halo phantom carries only
   the candidate's name.
9. The RAG scenario (J.3) completes end-to-end against real subsystems
   with the frontend visible and the REPL driving each step.
10. The doc and the code agree on every requirement in this file.

---

## M. Recursive Type-Strict Object Exploration, Reservoir Readout, and the Refined Panel Gesture Model

> Source: the user's prompt of 2026-05-30. Captured verbatim-first per A.1, design-space
> only ("regardless of any code specs and completely independent of our existing frontend
> codebase"). Elaboration: `DOMAIN_MODEL.md` §7.8 (reservoir), §7.3.4 (gesture model),
> §9.6.1 (typed panel form / functions-as-lookup), §15.9 (instance inheritance), §18.32
> (gesture-fidelity anti-goal). Full interaction-mechanics spec:
> `docs/frontend/object_exploration.md`.

**M.1 — The 3D map is the world-distribution; the compute graph is a reservoir with a generative readout.**

> "we should carefully analyze the way our functional python api objects interface with our
> perceptions from our 3D map. Our 3D map is our world-distribution from sources like shadow
> DOM scans and the peripheral generated outputs of our final output layers of the computation
> graph. Then, our computation graph becomes a reservoir computer with a generative readout
> property. The perceptions that are provided to the reservoir are then mapped to a readout of
> the reservoir dynamics in strict-typed data structures that are inlaid with the way in which
> we parse conceptual computation graphs within our 2D ui editor." (user, verbatim)

**M.2 — Module structures translate to recursive computation-graph nodes of singular values with memory references.**

> "Module structures (the modules, their properties which are other modules, and
> functions-as-modules with functional-inverse lookup memory maps) are completely translated to
> recursive structures of computation graph nodes of singular values with memory reference from
> other nodes to build the original object model." (user, verbatim)

**M.3 — The base panel form for a Python API module; functions as automatic memory lookup; right-click compiles the next level of recursive syntax tree.**

> "this is the most basic and essential representation type that has many different aggregated
> type and function call rules, where functions serve more as automatic memory lookup to inputs.
> In our case, forward calls to functions of an object can be compactly represented as curly
> brace calls to external computation nodes, or when these tokens are right clicked (hovered
> within their mini-card box bounds), they compile the next level of recursive syntax tree that
> can be dynamically typed and dynamically render next-rank inheritance and links via recursively
> chunking over syntax trees of abstract forms (computation graphs)." (user, verbatim)

```
_____________________________________________________
||   self:WebBrowser                               ||
||      NO_CHANGE_LIMIT:  int = 3                  ||
||      SETTLE_TIMEOUT: float = 0.25               ||
||      ...                                        ||
||      driver: WebDriver = {driver}               ||
||      scanner: {FunctionOutPutType} = {scan}     ||
||      ...                                        ||
||_________________________________________________||
```

**M.4 — Hover expands the next-rank type graph (superclass + properties).**

> (the `driver: WebDriver = {driver}` row, on hover, expands to the `WebDriver` object model —
> `super:BaseWebDriver` plus the constructor's typed parameters: `command_executor`,
> `keep_alive`, `file_detector`, `options`, `locator_converter`, `web_element_cls`,
> `client_config`.) (user, verbatim ASCII)

**M.5 — Functions expand to loosely-linked typed input/output fields; output types inferred by input/output equality.**

> "The next-rank type graph options (type graph as in any and all links, whether superclass,
> function, property, etc linked to the main node). I think I already mentioned this but forward
> calls linked to a function node via equality of an input on the right and an output type on the
> left infer output types. When the function compiles or renders what are in the curly braces,
> multiple input and output fields can be shown loosely linked to the function variable node"
> (user, verbatim)

```
scanner: {FunctionOutPutTypeNodeReference} = {scan}
   some_input_variable_name: SomeType = {could be variable or reference to another node}
   some_other_input: SomeOtherType = {typed_variable_reference}
   anotherfunction: {AnotherFunctionNodeReference} = {anotherInputVariableRef}
   scanner_output_structure: KnownOutputStructure = Rendered output object from function
```

**M.6 — Right-click expands/collapses next-rank links with fold-state preservation; right-clicking the base node collapses to the singular self node.**

> "So, right clicking each node, whether a variable key, a strict type, or a value in either base
> or reference form, expands the next-rank links (i.e. abstraction, reference, etc). These cards
> can be dynamically right clicked to expand and collapse. They can even be displayed in the most
> base form in the 2D editor as you see now, with organized blended-in interactive token fields
> of a base recursive structure with the referential properties we're looking for. If a node
> within the card is right clicked after it was expanded, the expanded tree(s) contract again but
> preserve at which levels the subtrees were folded and unfolded when the user right clicks the
> token within the panel form. If the base node of the panel is right-clicked, it can also
> contract into the singular self:WebBrowser node, for example." (user, verbatim)

**M.7 — Double-left-click compiles the panel into computation-graph form (which keeps the right-click fold, in graph space).**

> "If a panel is double left clicked, it is compiled into computation graph form, which has
> similar folding over right click properties, but in graph space with pure links between nodes
> via memory and functional and module references and what have you." (user, verbatim)

**M.8 — Single-left-click edits a token as a blended, borderless cursor field (a smoothed text editor).**

> "Single left clicks are reserved for inputting text in cursor-blinking fields that are otherwise
> still fully blended in with the background, so the presentation is like a purely smoothed text
> editor without special borders around each selective and interactive token." (user, verbatim)

**M.9 — Function calls auto-render like memory-reference lookup; user types are built from base API object types via langgraph/pydantic templates.**

> "Function calls with those types of nodes have an automatic rendering property about them,
> similar to memory reference lookup otherwise for object models and references between more
> abstract types that the user might create out of base API object types via langgraph pydantic
> templates and the like." (user, verbatim)

**M.10 — Halos persist for completely blank fields; sticked apparitions become referenceable compute graphs.**

> "We don't sacrifice our retrieval halos either for completely blank fields. Halos are meant to
> emerge apparition nodes that are semantically similar to the task at hand such that they
> themselves could be 'clicked and sticked' to the UIX while the retrieval queries from the
> fields of the edited knowledge panels change. However, the sticked halo retrieval nodes can
> still then be compiled as their own computation graphs and their unique variable names within
> their fields can be dynamically recursed over and referenced in the knowledge panel that the
> user builds." (user, verbatim)

**M.11 — Play/pause runs computations; object-instance inheritance via field connection.**

> "We have a 'play/pause' button in the top right corner of our 2D editor that we can use to run
> computations." (user, verbatim)
>
> "...as well as object instance inheritance if the user were to connect a WebBrowser object to
> one of the fields in their own computation-knowledge panel." (user, verbatim)

**M.12 — This is design-space only.**

> "set a full analysis of this new idea as your /goal to bring all of this into our current design
> space within our documentation regardless of any code specs and completely independent of our
> existing frontend codebase." (user, verbatim)

---

## N. Object-Oriented DOM Types, External Reference Propagation, and the DuckDuckGo Walkthrough

> Source: the user's prompt of 2026-05-30 (the DuckDuckGo scan walkthrough). Captured verbatim-first
> per A.1, design-space only. Elaboration: `DOMAIN_MODEL.md` §9.6.2 (external reference propagation /
> type-stripped rendering / names-with-spaces / `{ref}`-as-memory-access / rank-1 minimalism), §7.3.4
> (left-click-drag wire + double-right-click delete), §4.6.1 (conditional per-sample signal), §4.1.1
> (shift+`\n` / `\t` smart parsing), §15 (ShadowDOM OO type), §8.8 (retrieval-driven scan feedback).
> Suite: `docs/frontend/object_exploration.md`, `field_tree.md`, `editor.md`, `pattern_map_and_url_set.md`.

**N.1 — Stick to simplest-possible object-oriented Python types for DOM scans.**

> "Let's note that we stick to object-oriented python types (simplest possible) for our DOM scans and
> their structures." (user, verbatim)

**N.2 — A node is both computation and panel (one singular-field primitive); authoring begins in graph form.**

> "I create a new node that is technically both computation and panel-based as a singular field
> primitive that is simply visually restructured in regards to its context graph. This node is the url
> for duckduckgo search. I then create another node called 'name: self = duckduckgo' that references the
> scan function node (a functional-object) in which the 'scan' function of the webbrowser is referenced
> as a field in the duckduckgo node. I envision this beginning with everything in computation graph
> form." (user, verbatim)

**N.3 — Propagate external node references through as their own set of objects, recursively rendered in new panels. (Explicitly requested verbatim note.)**

> "There should be another note in the verbatim about propagating external node references through as
> their own set of objects that are then recursively rendered in new panels." (user, verbatim)

**N.4 — Left-click-drag in graph form links nodes; the target inherits input-output types and object models.**

> "This would mean that in graph form, I could hover over one node, then left click and drag from the
> one node to the other node. So, I could hover over the WebBrowser's scanner functional-object node,
> and drag it to link with the 'duckduckgo', which then inherits input-output types and object models:"
> (user, verbatim)

```
DuckDuckGo
   {scanner} --> hovered, no type presentations in final rendered knowledge panel this time, rendered purely structurally over \t + \n
```

**N.5 — Type-stripped purely-structural rendering over `\t` + `\n`; output slots blank until bound or inverse-referenced.**

> (the `{scanner}` field has "no type presentations in final rendered knowledge panel this time,
> rendered purely structurally over \t + \n"; when right-clicked: "variables purely stripped of types
> and io, referenced purely through the scanner's referenced path assigned to the DuckDuckGo node";
> "dom {} ---> arbitrary output types and still blank, unless referenced externally for inverse
> lookup".) (user, verbatim ASCII)

```
DuckDuckGo
   scanner --> hovered + right clicked
      url {} ---> variables purely stripped of types and io, referenced purely through the scanner's referenced path assigned to the DuckDuckGo node
      dom {} ---> arbitrary output types and still blank, unless referenced externally for inverse lookup
```

**N.6 — The reference is a duplicate instance that operationally calls the originating object, as a rank-1 component; works in panel and graph form.**

> "The `scanner` is instantiated as a duplicate of its original external reference in terms of
> operational calls to the originating object, this time as a rank-1 component of the DuckDuckGo node
> within its knowledge panel form, but this should also work with computation graph form where the
> DuckDuckGo node shares a link to the scanner functional-object, as well as the WebBrowser object. So,
> when the externally referenced node is hovered + right clicked , the externally linked variable is
> referenced and renders its instances in the panel, or the DuckDuckGo computation graph." (user, verbatim)

**N.7 — Variable names can have spaces; rank-1 in 2D, full per-sample distribution in 3D; ShadowDOM is the output-inferred type shared in the 3D GUI.**

> "where the variable names can have spaces since we are simply discerning tree structures recursively
> over tab and newlines, we get the immediate call to the scanner function to complete the external
> reference variable which is a ShadowDOM object that is shared in our 3D GUI, but here we are only
> worried about rank-1 relations so that we can represent the full set of the scan in the 3D GUI at the
> per-sample distribution, while we constrain our high-level compute perception to the base functions
> and relations to objects that define our ShadowDOM object, like the following:" (user, verbatim)

```
DuckDuckGo
   scanner --> hovered + right clicked
      url {duckduckgo url}
      dom {scan for duckduckgo url}

duckduckgo url
   https://www.duckduckgo.com/

scan for duckduckgo url
   search {}
   paginate
   chunk {chunk samples} --> follows per-sample iteration on signal presentation in the graph/panels
```

**N.8 — Right-clicking `{ref}` fields reveals rank-1 structure; slim selective unfolding preserves per-sample iteration; patterns compile dynamically alongside scans; uppermost abstractions shown by default.**

> "Variable assignment to structured and type-independent fields becomes very intuitive, and note that
> right-clicking nodes with curly brace references in the computation graph (or knowledge panel) is what
> then make the next rank-1 structures of each field visible, and also enable a slim minimalist unfolding
> recursion selectively over structures without missing the per-sample iteration and per-instance signal
> presentation in the computation graph. So that means all the computation graph patterns are compiled
> dynamically along with shadow DOM scans. It also means that the upper-most abstractions are displayed.
> The user can select the externally referenced fields themselves to explore the recursive structures
> within the signal-iteration-over-recursive-chunks form that our computation graph takes." (user, verbatim)

**N.9 — Per-sample signal print-rendering is only needed when external computation links reference recursively-chunked iterables.**

> "Per-sample signal print-rendering is only done or needed if any computation links are externally
> referencing these nodes with recursively-chunked iterables." (user, verbatim)

```
DuckDuckGo
   scanner --> hovered + right clicked
      url {duckduckgo url}
      dom {scan for duckduckgo url} --> hovered + clicked
         search {}
         {paginate}
         chunk {chunk samples}

duckduckgo url
   https://www.duckduckgo.com/

scan for duckduckgo url
   search {}
   {paginate}
   chunk {chunk samples} --> follows per-sample iteration on signal presentation in the graph/panels
```

**N.10 — Any `{curly brace}` field is an activation to a memory-access procedure elsewhere; labels/spaces beside refs are optional and organisational.**

> "Note that singular fields with curly braces around them like 'paginate', but also really any curly
> brace field, really just means an activation to a memory access procedure somewhere else in the app.
> The names and spaces beside the curly brace references are optional and there to organize the various
> components of concept nodes." (user, verbatim)

**N.11 — Running db-vector + cypher-vector search; SLM critique + intelligent similarity threshold spawns new scan instances; bridges compute graphs and agents into a unified conceptual program model; alternative = query panel/graph with halo retrieval as context localiser.**

> "Then, I can simply search or keep a running search of the most relevant chunks over a global
> perspective by doing similar for constructing our db vector and cypher-vector searches. This then
> enables dynamic computation for both scanning and RAG-based tasks that link back to which new urls to
> scan according to how well each search result chunk is evaluated by a language model that decides the
> critique of similarity from a logical and through-process based standpoint, so a kind of intelligent
> threshold on semantic similarity that decides which results to follow up on with their own scan
> instances. This bridges the gap between computation graphs and agent-based workflows through a unified
> conceptual program model. I should note an alternative approach would be to use a novel query
> panel/graph as a basis and its halo retrieval as a context localizer." (user, verbatim)

**N.12 — Minimal structure/parsing; smart shift+`\n` / `\t` multiline parsing (like Claude's markdown auto-indent); template multi-curly-brace referencing bridges API objects and LM generation; all share the base recursive-tree + per-signal-sample structure.**

> "Note that our knowledge panels of our computation graphs can be just as minimally and simply
> structured and parsed as I have provided here. I should also note that multiline entries in singular
> fields are managed with intelligent parsing of shift+\n and \t actions, similar to how claude
> automatically indents over markdown characters and gestures. Then, the template-based multi-curly-brace
> referencing and iteration becomes a little more manageable for bridging the soft gap between regular
> API functional-objects and language model based object transformation and generation within arbitrary
> recursive structure types that all share the same base structure inside, recursive trees with
> per-signal sample iteration rendering in their computation graph and knowledge panel instances." (user, verbatim)

**N.13 — Double-right-click deletes a token reference/instance in rendered print (panel or graph form).**

> "I should also note that double-right-clicking deletes abstractly structured token references or
> instances in rendered print in their computation graph or knowledge panel forms." (user, verbatim)

**N.14 — Rank-1 minimalism is a PRO-pattern, not an anti-pattern (extremely important).**

> "Rank-1 minimalism is a pro-pattern, not an anti-pattern, for our 2D GUI. This last point is
> extremely important to remember." (user, verbatim)

---

## O. Review-Session Clarifications (2026-05-30)

> Source: the user's answers and refinements during the step-by-step design review of 2026-05-30.
> Binding. Elaboration: `DOMAIN_MODEL.md` §7.3.4 / §9.6.2 (O.1, O.1a, O.2), §8.2.4 (O.3), §4.6 (O.4),
> §8.8 / §9.5.1 (O.5). Suite: `docs/frontend/object_exploration.md`, `field_tree.md`, `halo.md`,
> `compile_collapse.md`, `editor.md`.

**O.1 — Curly-brace reveal works in BOTH knowledge-panel and computation-graph forms; the two stay in node-count parity.**

> "The nodes in the computation graph are the singular fields with line-drawn links (undirected)
> between each singular field in graph form. Rendering to knowledge panel card works a little
> different, where curly brace variables can be interacted with to have their rank-1 links rendered
> in the next tree level as per the examples. … Computation graph form folds should actually likely
> be excluded and reflect the same amount of nodes as are shown in knowledge panels." (user, verbatim, Q1)
>
> "rank-1 renderings should allow for the new set of hidden (internally referenced) nodes to be
> revealed in either case using our curly brace notation. … nodes with curly braces in computation
> graphs represent nodes that don't immediately reveal all their rank-1 links. … the curly braces on
> nodes in the computation graph are still kept to signify their affinity with currently hidden
> nodes … The hover action still shows the rank-1 links to other nodes, and clicking instantiates the
> rank-1 walk expansion as part of the visible context in the computation graph itself." (user, verbatim)

Curly braces mark a node with **hidden (not-yet-revealed) rank-1 links** in *both* forms. In the **knowledge panel**, revealing unfolds the hidden node's rank-1 fields inline (indented tree). In **computation-graph form**, the braces mark nodes whose rank-1 links aren't all visible; **hover previews** the rank-1 links, and a **click instantiates the rank-1 walk** as new visible nodes joined by **undirected line links**. Graph form has **no independent fold state** — it stays in **node-count parity** with the panel (revealing in one reveals in both).

**O.1a — Three brace states (the internal/external differentiation, integrated).** A `{ref}` renders in one of three states; the underlying full-graph link is identical in all three:
- **Braced-hidden** — target's rank-1 links not yet revealed; shows `{name}`; hover previews, reveal instantiates.
- **Revealed-internal** — target's rank-1 fields unfolded inline (panel) / its walk instantiated (graph); braces drop on the revealed node (its children may themselves be braced).
- **Resolved-external (solid link)** — target is a node *already visible elsewhere* in the 2D GUI; rendered as a **solid line link** to it rather than re-revealed inline.

**O.2 — The curly braces are the marker.** A folded/hidden reference renders `{name}`; revealing drops the braces and shows its rank-1 set (no extra glyph; consistent with the black-core / silver-outline theme).

**O.3 — Halo gating: text-input fields only; mixed fields query the whole resolved field.** Halos fire only from fields carrying rendered literal text input (including blank / in-progress text fields); a pure-`{ref}` field fires no halo. A field mixing literal text and `{ref}` tokens queries the **whole resolved field** — the text plus the resolved content of the embedded refs.

**O.4 — Long-field rendering: names forward-truncate (~20 chars + …, full on hover); values always full.** Variable names forward-truncate at ~20 characters with an ellipsis (front kept, tail elided); full name on slow-hover. Values render in full (multiline, never truncated). Extends to chunk-sample tree rendering (§15.8).

**O.5 — The Database node exposes rank-1 ontology nodes; keep/delete builds cypher queries; halos discover new cypher fields.**

> "The database node also exposes its rank-1 ontology nodes, and enables recursive chunking over
> rank-1 walks over linked ontology nodes, which are kept or deleted for a given set of retrieval or
> cypher queries in the 2D GUI, and these kept/deleted fields are used to build over a cypher query
> from multiple semantic retrieval runs over rendered text nodes. So here, retrieval halos still serve
> the purpose of discovering new cypher fields to aggregate and walk through." (user, verbatim)

The Database node surfaces its **rank-1 ontology nodes**, walkable recursively (rank-1 walks over linked ontology nodes, recursively chunked). The user **keeps or deletes** (double-right-click, N.13) ontology fields per retrieval/cypher query; the kept set **assembles a cypher query** built up from **multiple semantic-retrieval runs over rendered-text nodes** (O.3). **Retrieval halos discover new cypher fields** to aggregate and walk — bridging semantic retrieval (`Database.search`) and structured graph query (`Database.cypher`) within one node (§8.8).

**O.6 — 2D per-sample stepper drives 3D focus (one-way).** A rank-1 node's `{chunk samples}` shows one signal at a time in 2D; the 3D Real shows the full per-sample distribution. Advancing the 2D signal flies/highlights the corresponding chunk in 3D. The 2D stepper drives the 3D focus; the 3D always shows the full set. (Review Q.)

**O.7 — Chunks live in 3D; the 2D node holds a reference.** Running a scan streams the full per-sample chunk distribution into the 3D Real (interior); the 2D node stays rank-1 (the ShadowDOM's base functions/relations) and its `{chunk samples}` is a **reference into the 3D-resident set**, not a duplicate copied into the 2D data. (Review Q.)

**O.8 — Type abstraction is top-down from the API objects.** Types are authoritative at the materialized API-object ontology and propagate **downward** to the fields bound to them; a user field's type is the API-declared type it binds to (not value-derived). "Increasing levels of type abstraction" = climbing the API object's ontology chain (super-class; `FUNCTION_OUTPUT_TYPE` → that type's structure). (Review Q.)

**O.9 — Compile is lazy reveal-as-it-walks.** Compiling/running a graph follows `{ref}`s **on demand as the computation reaches them**, revealing each braced-hidden node in the GUI as it is walked. Running the graph progressively unfolds it; the reveal mechanic (§O.1) and the compile traversal are the *same* walk. (Review Q.)

**O.10 — Pause freezes at the walk frontier.** During an iterated rollout, Pause keeps the nodes revealed so far visible (at rank-1), shows the current per-sample signal, and lets the user edit any revealed node; Resume continues the walk + iteration from there (diff-consistent, §7.5/§7.6). (Review Q.)

**O.11 — Per-sample iteration uses one readout node that cycles the signal.** A function iterating over `{chunk samples}` shows the current sample's output in a *single* readout node (signal-stream §4.6.1); the per-sample outputs accumulate as the full distribution in 3D (§O.7); the 2D stays rank-1. (Review Q.)

**O.12 — The generative readout lives as a 2D rank-1 node + a 3D distribution.** A type-stripped readout node in the 2D graph holds the current output; per-sample / agent outputs land in 3D (perimeter for agent outputs, §6.6.1); the 2D `{output}` is a reference into the 3D set (mirrors §O.7). (Review Q.)

**O.13 — Reveal only on the active walk; the background cascade stays within the frontier.** An explicit play/compile walk reveals nodes as it goes (§O.9); a background cascade (§7.4) recomputes downstream values but does **not** auto-unfold hidden nodes — the visible graph stays at the user's chosen rank-1 depth (rank-1 minimalism preserved, §N.14). (Review Q.)

**O.14 (corrected) — iterables render the current instance's content per-instance from a memory queue; samples come from the 3D env per-instance OR by halo-retrieval selection (negates the over-strict "references-only, never content" framing; B1 + correction).** All chunks still *live* in 3D (the full distribution, via retrieval or scan), but the 2D is **not** restricted to bare references. For the general case of a **rank-N object** whose recursive chunking returns iterable structures, the field renders the **next-up instance's content** per-instance (the visible signal, §4.6.1), **selectively** by which instance is next in that referenced variable's **memory queue** — content *is* rendered for the current sample. The sample for the current instance is sourced **either** by sampling a chunk from the 3D env on a per-instance basis **or** by halo-retrieval (the three retrieval metrics, §8.1) + selection. Deleting a halo result advances to the **next-most-similar** sample in the retrieval-similarity queue and the rendering updates dynamically (§O.18). (As the graph computes, data over all nodes still updates iteratively over samples and recursively through compute steps. This **supersedes** the earlier "chunks live in 3D; the 2D only ever holds references, never content" over-statement — that was overkill.) (Review B1 + 2026-05-30 correction.)

**O.15 — Type inference/abstraction is joint, not exclusively top-down (refines §O.8; B2).** Both/all methods of inferring or abstracting types are integrated **jointly**, each applied wherever/whenever it is applicable: **top-down** from the API-object ontology (§O.8, where a field binds to a materialized API node), **bottom-up** observed-from-wiring/value (§9.8, for user-authored or unbound slots), and the type-ontology sharpening (§15.9) in between. No single direction is exclusive. (Review B2.)

**O.16 — No arrowheads; links are undirected lines (refines §O.1; B3).** Graph-form links between singular fields are **undirected plain lines** — **no arrowheads anywhere**. The hard-link / soft-link distinction is carried by **stroke brightness + weight only** (no arrowhead glyph). The 2D↔3D connector is a **solid yellow line with no head** (§18.7). (Review B3.)

**O.17 — `MORTEGON_INTEGRATION_SCHEME.md` and `CODEBASE_GAP_ANALYSIS.md` are deprecated as active specs; reframed as historical analysis-plan, with additive design details lifted into the design docs (goal of 2026-05-30).** Both are analysis/plan artifacts (an operational 3D↔2D scheme; an old-code gap audit) now **superseded** by `DOMAIN_MODEL.md` + the `docs/frontend/` suite + §M/§N/§O. Their **additive, non-contradictory** operational details are lifted into the design docs as features: (a) the UMAP layout normalization — target-sphere fit (`TARGET_RADIUS` default 25) + hard Lagrange-style collider pass + the 1D-radial force reduction (a chunk moves only along `r(t)` from its root) → §6.1 / `frontend/projector.md` + `frontend/scan_streaming.md`; (b) the 2D concept-graph layout as a **2D-UMAP-of-nomic-vectors recentred on the focal**, radial-DOF-only (mirrors §6.1 in 2D) → §7.3.2 / `frontend/editor.md`; (c) the `↳` **continuation row for deduplicated value aliases** + forward-truncated field names → §4.6 / `frontend/field_tree.md` (consistent with §O.4). **Outdated — flagged do-not-implement:** the multi-section contenteditable panel anatomy (MORTEGON §1.1 → dissolved field-tree, §4.5/§9.6.1); the *arrowhead* 2D↔3D "arrow" (MORTEGON §6.3 → headless line, §O.16); the `cp/*.js` file surfaces + implementation order (MORTEGON §11/§12 → `FRONTEND_REDESIGN.md` §11; redesign assumes no prior frontend code); and every old-code-path gap/fix in `CODEBASE_GAP_ANALYSIS` (the audited code is being replaced). (Goal 2026-05-30.)

**O.18 — Halo cone-ray-similarity transport: 3D nodes are transported along a shared cone by retrieval similarity (supersedes the §8.2.1.1 ray-projection where they conflict).** Total retrieval similarity (the triple product, §8.1) is a **spatial-distance localization** from each 3D node to the **2D query element** — the "stuck" node primitive, or one of its singular-field / computation-graph primitives (the element that can render to a knowledge panel or compile to singular fields + links in graph form). That 2D query element is the **focus/apex** of ray projections over a **common cone** whose focal line is the 2D panel camera's. The **normalized similarity of all halo-visible retrieved nodes** models the **radial distance each 3D node is transported along the cone** — both the radial *and* the along-ray distance (after normalization) encode similarity (more similar → nearer the apex) — enabling *projective-enabled state proximity*. Depending on **camera view**, a node's **angular placement** is the projected line of its intersection along the **shared cone surface normal**; so 3D billboards are **transported from their original positions** onto the cone at positions encoding their similarity to the 2D query, their halo span in 3D proximity varying by radial distance along the focal line. Deleting a halo result transports in the **next-most-similar** sample from the retrieval-similarity queue, dynamically re-rendering (§O.14). This **supersedes** the earlier "project the focal's manifold-nearest neighbours onto the cone" framing: the halo transports any *retrieval-similar* 3D node (by the three metrics), not only the 3D-geometric nearest. (User note 2026-05-30.)

**O.19 — 3D retrieval ↔ knowledge-panel hover/stick; iterables rooted at base/root nodes; the singular-primitive aspect determines node-vs-panel; recursive chunk iteration only on external `{ref}` (clarifies §O.14, 2026-05-30).** Retrieval runs over the **3D representations** — chunk billboards + the rotating HSV from the 4–6 UMAP dims (§6.1 / §8.2.1.2). Hovering a 3D node — in **either base-UMAP layout or retrieval-halo (transported, §O.18) form** — shows its **knowledge-panel representation** of the chunk; clicking it **sticks** that panel into the 2D, where the user integrates it with the computation-graph builder via the knowledge-panel interactions (recursive, syntax- and source-invariant functional-object trees, §4.2 / §5.3). **Recursive chunk property:** iterables are **sourced to their base/root nodes**, so a panel that references an iterable recursive chunk **dynamically updates from the root sources down to its fields** as the root changes — while still honouring the switch between a **`{curly brace}` external reference** (an in-memory computation node) and **rendering the content inline within the knowledge panel** (§O.1). The retrieval halo also fires for **singular-primitive field representations with links in computation-graph form** (§8.2.3). **The singular-primitive aspect of a 2D element determines its kind:** a *singular primitive* (one field) IS a **computation-graph node**; a non-singular aggregate is a **knowledge panel** that *compiles to* a computation-graph representation (§4.6 / §7.3.4). **Recursive chunk iteration is applied ONLY when content is externally referenced via `{curly brace}`** in a panel or node (§4.6.1); inline-rendered content is not iterated. (User clarification 2026-05-30.)

**O.20 — Agent outputs are processed downstream via pydantic templates exposed in the minimalist text pattern; key-value vs multiline fields are inferred by consistent tabs; a variable key (spaces allowed) beside a singular empty `{}` is the field starting point (2026-05-30).** Agent outputs (the generative readout, §7.8) are processed **downstream internally via pydantic templates** that are **included in the input knowledge panels / computation-graph compilations** of the consuming node (the §7.2 `structured` dispatch). Those pydantic templates are **exposed within the minimalist text-based pattern itself** — not as raw JSON schema — with **inferred field/variable names**, `{curly brace}` references for content, and **markdown-typing handlers for Tab and Shift-Enter** (N.12); a *singular panel* authored this way compiles intelligently into computation-graph form (§7.3.4) and is fed by **structured chunk samples from the scanner** (§15.8). A new field's **key-value scheme uses a variable key (spaces allowed, §O.10) beside a singular empty `{}`** as its starting point — exactly how the scanner represents functional-objects (e.g. `url {}` / `dom {}`, §9.6.2). Within one **super-field (parent node)**, the editor **implicitly infers** whether a child is a **key-value** field (a singular value) or a **multiline** field — whose **key is the primary key to the multiline data, denoted by consistent tabs** beneath it — purely from indentation in the editable-yet-naked text input field (no syntax markers; the FieldTree indent parse, §4.2). (User note 2026-05-30.)

**O.21 — Pydantic template handling/tooling lives on the main Agent node, as a `template` functional-object that parses input prompts and output simultaneously over the meta_prompt → prompt → output scheme (2026-05-30).** The pydantic-template handling and tooling of §O.20 are **connected to the main Agent node**: the Agent fixture (§9.5.1) carries a **`template` node / functional-object** (a member of its python_object tree, §9.6) that **parses templates for both directions at once** — filling the **input prompts** (resolving `{var}` content into `meta_prompt` + `prompt`) *and* **parsing the output** (the pydantic output schema given to `output`) — across the **prompt–metaprompt–generation scheme** of the current Agent API object. So the same template engine that templates the input prompts also shapes/validates the structured output; the pydantic tooling is **bound to the agent**, not a free-floating tool, and is authored in the minimalist field-tree pattern (§O.20), not raw JSON schema. (User note 2026-05-30.)

**O.22 — Dynamic vectorization of knowledge-panel partitions; one blended search space over data ⊕ computation; the panel embedding deviates (same render → both models, max of cos sims) (2026-05-30).** We **dynamically vectorize the state space of knowledge-panel partitions** by their **internal memory** — what is **curly-brace externally referenced** (a function) vs what is **explicitly rendered as a rank-1 step** inline (§O.19) — with the **computation graph remaining isomorphic to the knowledge-panel containment bounds** (one graph node ≅ one panel partition). The **dynamic embeddings of all panels** in the compute-graph context — **including iterable chunks**, functional-objects, and whole computation **subgraphs** — are included in the **same** embedding search / retrieval set over halos. So we can search for **functional-objects and abstract computation subgraphs that accomplish a pre-designed task** (e.g. a specialized research agent with its knowledge panel rendered + vectorized): **search over data space seamlessly blends with search over the space of computational tasks.** **Crucial embedding deviation:** because knowledge panels are far more dynamically structured, the two embedding models **deviate** from the strict §8D.17.1 axis separation — we embed **rendered panel chunks** (following iterable-recursion sampling rules) using the **same render for both quantized (nomic) and TF-IDF** vectorization, then take the **max of the two cosine similarities — each min-max normalized to [0, 1] over its own space** — when linking to the third (PageRank) metric: `pagerank · max(minmax(nomic_cos), minmax(tfidf_cos))`, where `minmax` is min-max normalization to [0, 1] over each cosine's own distribution. (Raw cosine spaces at their **independent scales can be biased**, so both must be min-max normalized *before* the max — otherwise whichever space has the larger raw range would dominate. Scan chunks keep the separated axes; this is the panel-specific application.) (User note 2026-05-30.)

---

## P. Cascaded Computation Graphs as a Recurrent Procedural Information-Space Renderer (2026-06-06)

> Source: the user's prompt of 2026-06-06 (the `/goal` integration directive). Binding; captured
> verbatim-first per A.1. **Extends §M** (the reservoir-readout seed, M.1) with the full cascaded
> render-compile rollout, the input-side inverse lookup, the asynchronous perimeter, the projector-space
> link network, and the bisector computation-graph node. Elaboration: `DOMAIN_MODEL.md` §7.8.1–§7.8.5
> (the reservoir rollout + procedural renderer), §6.6.4 (the bisector node + projector link network),
> §6.6.1 (perimeter), §7.7 (forward-inverse), §7.4 (cascade), §7.5 (rollout), §15.8 (xpath chunk
> patterns). Suite: `docs/frontend/object_exploration.md`, `projector.md`, `editor.md`.

**P.1 — Full integration over cascaded computation graphs: real functional-object links, cascaded render-compile chains through the graph, recursive-iterative over manifold structured inputs.**

> "Let's go for our full integration over cascaded computation graphs with real functional-object links
> and cascaded render-compile chains through the computation graph with our recursive-iterative approach
> for manifold structured data inputs..." (user, verbatim)

**P.2 — Inputs come from xpath chunk-pattern-linked inverse lookups over generalized chunk samples, with downstream iterative renderings to the readout nodes.**

> "...for manifold structured data inputs from xpath chunk pattern linked inverse lookups over generalized
> chunk samples with downstream iterative renderings to the readout nodes..." (user, verbatim)

**P.3 — Readout nodes = the final-most recursive unfolded nodes for a full rollout = the perimeter / spherical (hyper)surface of input-output rendered panels.**

> "...the readout nodes (final-most recursive unfolded nodes for a full rollout, the perimeter/spherical
> (hyper) surface of input-output rendered panels...)" (user, verbatim)

**P.4 — Readouts stream as updates to the 3D embedding projector, with physical + color (HSV) representation rotation in passive state (for nodes without image billboards).**

> "...that are then streamed as updates to our 3D embedding projector with physical and color representation
> rotation in passive state (for nodes without image billboards)." (user, verbatim)

**P.5 — The forward-inverse integrated graph query + function calls with inverse lookups are an iterated information-space procedural rendering scheme for partially recurrent mappings between iterated input samples — all the way to the output knowledge-panel / computation-graph dialectic representation, used to procedurally render the final output datatypes given the array of iterable inputs.**

> "Note that our forward-inverse integrated graph query and function calls with inverse lookups are
> essentially an iterated information space procedural rendering scheme for partially recurrent mappings
> between iterated input samples, all the way to the output knowledge panel/computation graph dialectic
> representation that are then used to procedurally render the final output datatypes given the array of
> iterable inputs." (user, verbatim)

**P.6 — Recurrent computation time and perimeter output may be asynchronous — depending on compute-graph-operation time relativity between subgraphs with differing rollout path lengths over recurrent maps back to hidden-state nodes of intermediate mappings.**

> "Note that recurrent computation time and output at the perimeter may also be asynchronous depending on
> compute-graph-operation time relativity between subgraphs that have differing rollout path lengths over
> recurrent maps back to nodes in the hidden state of intermediate mappings within the computation graph."
> (user, verbatim)

**P.7 — Perimeter output-sampling times are rendered and sent to an embedding-projector stream as delta updates to the network map within the projector.**

> "So times of output sampling over the perimeter of the computation graph, rendered and sent to an
> embedding-projector stream as delta updates to the network map within our projector." (user, verbatim)

**P.8 — Root urls link to the chunk-sample nodes; input-node roots / click-sticked 3D nodes used in the 2D graph (e.g. urls) link — in a projector node-edge network rendering independent of the UMAP embedding — to the computation graph itself.**

> "Note that our root urls have links to the chunk sample nodes. The roots of the input nodes, or otherwise
> click-sticked nodes from 3D that are then used in the 2D computation graph, such as urls, are then linked
> in a node-edge network rendering (independent of the UMAP embedding project, simply links between nodes in
> the projector) to the computation graph itself." (user, verbatim)

**P.9 — All perimeter output nodes also link to the full computation-graph node in the editor.**

> "Then, all perimeter output nodes to the graph are then also linked to the full computation graph node in
> the editor." (user, verbatim)

**P.10 — The computation-graph node sits on the linear bisector between the centroid of all input UMAP xyzhsv coordinates and the dynamically-updated output xyz coordinates; the two centroids are hidden, the computation-graph node is shown, and clicking it opens/closes computation graphs in the editor.**

> "The computation graph is simply the node along the linear bisector between the centroid of all input UMAP
> xyzhsv coordinates and the dynamically updated output xyz coordinates. The two input and output centroids
> are not shown, but the computation graph node itself is, which can be clicked to open and close computation
> graphs in the editor." (user, verbatim)

**P.11 — The dialectic computation-graph representation for purely unstructured procedural rendering over input and output knowledge is an optimal transport between semantically complex yet linked knowledge — a procedural renderer that recurrently evolves over the input information and its recurrent hidden-state representations.**

> "This shows that our dialectic computation graph representation scheme for purely unstructured procedural
> rendering over input and output knowledge serves as an optimal transported between semantically complex yet
> linked knowledge. In other ways, a procedural renderer that recurrently evolves over the space of the input
> information it's given, and it's recurrent hidden state representations." (user, verbatim)

**P.12 — Hidden-state and perimeter nodes are smoothly differentiated during iterative construction/testing over smaller graphs (so the user sees outputs at the utmost abstractive layer); as complexity grows, the abstraction front of the reservoir's perimeter extends beyond the intermediate nodes that were experimented with.**

> "The hidden state representations and perimeter nodes are smoothly differentiated between during iterative
> construction and testing over smaller computation graphs by the user, so that they can see outputs at the
> utmost abstractive layer. As they build more complexity into the computation graph, the abstraction front of
> the reservoir's perimeter extends beyond the intermediate nodes that were experimented with." (user, verbatim)

## Q. All-Real Tests Everywhere, Timed Scans as Exposed Properties, and the Generalized Rank-Dominance Collapse Gesture (2026-06-07)

> Source: the user's prompt of 2026-06-07 (the `/goal` directive). Binding; captured verbatim-first per A.1.
> **Strengthens §K.1 / §L (the No-Mocks Contract, `DOMAIN_MODEL.md` §13)** to an unconditional *all-real
> tests for everything* mandate, and **adds two feature clarifications** that down-flow from `DOMAIN_MODEL.md`
> through `docs/code_specs/` to code. Elaboration: `DOMAIN_MODEL.md` §0 (the all-real banner), §13 (no-mocks),
> §6.6.5 + §7.3.5 (the generalized rank-dominance collapse gesture), §8.1.2 (rank-dominance vs PageRank),
> §15.10 + §9.8 (the timed-scan `duration_s` port). Suite: `projector.md`, `compile_collapse.md`,
> `gesture_gateway.md`, `WebBrowser.md`, `code_specs/backend/scanner.md`, `code_specs/repl.md`.

**Q.1 — We need an all-real test implemented with real models, webbrowser, langgraph. We need all-real tests for everything. This must be a prominent statement at the domain-model level, flowing down to the code specs and the code implementations.**

> "We need an all-real test implemented with real models, webbrowser, langgraph. We need all-real tests for
> everything. Please make this a prominent statement in our affected documentation at the domain model level
> (i.e. @docs/DOMAIN_MODEL.md and rest of @docs, downflow to @docs/code_specs, and then code implementations)."
> (user, verbatim)

**Q.2 — A full scan can be run on archive.org for a set amount of time, exposed as a property in the graph-editor functional-object framework over python-exposed API objects (SLM agents, webbrowser, database), where the ray-projected apparition-similarity halos pop up for dynamically rendered computation-graph node / knowledge-panel procedural forward-inverse data structures through computation generation over conceptual-reservoir readouts.**

> "A full scan can be run on archive.org for a set amount of time, which is an exposed property in the graph
> editor functional-object framework over python-exposed API objects such as SLM agents, webbrowser, database,
> where the ray-projected apparition similarity halos pop up for dynamically rendered computation graph
> node/knowledge panel procedural forward-inverse data structure through computation generation over conceptual
> reservoir readouts. Make sure to elaborate the concepts linked in our design docs, specs, and codebase before
> running necessary updates through the fully integrated stack tests via REPL." (user, verbatim)

**Q.3 — A root url node can be right-clicked to collapse its chunk samples in embedding-projector space. When the collapse occurs, all other nodes disappear except the url node, which can be right-clicked again to re-expand/unfold its containing structures.**

> "A root url node can be right clicked to collapse its chunk samples in embedding projector space. When the
> collapse occurs, all other nodes disappear except the url node, which can be right-clicked again to
> re-expand/unfold its containing structures." (user, verbatim)

**Q.4 — When the computation graph is instantiated in the 3D GUI projector through the input-output dual-hidden-distribution-centroid linear-midpoint method (the §P.10 bisector node), the right-click feature must apply to its input-output distributions in the 3D projector.**

> "Please make sure that when the computation graph is instantiated in our 3D GUI projector through the
> input-output dual-hidden-distribution-centroid linear midpoint method that we can apply the right-click
> feature to its input-output distributions in the 3D projector." (user, verbatim)

**Q.5 — This right-click expand/collapse around nodes (collapsed nodes hidden/temporarily disappeared) is a generalized gesture in the 3D GUI (as well as 2D — check whether that is implemented in the docs) that adheres to rank-dominance definitions of collapsing hierarchies through complex computation graphs.**

> "Please ensure this right click to expand collapse around nodes (with collapsed nodes hidden/temporarily
> disappeared) is a generalized gesture in 3D gui (as well as 2D, which also may or may not be implemented from
> the docs... check for this) that adheres to rank dominance definitions of collapsing hierarchies through
> complex computation graphs." (user, verbatim)

**Q.6 — The user believes (uncertain) the rank-dominance measure/indexing over structures is the same one used in the PageRank term of the generalized retrieval tool for halos and DB search; this must be checked.**

> "I think this is the same sort of measure or indexing over structures that is used in our pagerank term of our
> generalized retrieval tool for halos and db search, but I can't be too sure... so please check for that as
> well." (user, verbatim)

> **Finding (Q.6 resolution, recorded against the verbatim per A.1).** Rank-dominance and PageRank are computed
> over the **same** `ConceptEdge` graph (the one-edge-table invariant, `DOMAIN_MODEL.md` §3.2 / §8.1) but are
> **distinct measures**: PageRank is the stationary-distribution **centrality/flow** weight used multiplicatively
> in the retrieval triple product (§8.1); **rank-dominance** is the **structural containment/reachability
> ordering** (a dominator relation over the compute/containment DAG) that defines *which* descendant nodes a
> collapse hides. They are **aligned but not identical** — a collapse root (a root url, a bisector compute-graph
> node) tends to be a high-PageRank hub *because* it dominates many chunk-sample / readout nodes, so PageRank
> serves as the **collapse-onto heuristic** (which node to fold a hierarchy onto) while the dominated-set
> reachability defines collapse **membership** (what disappears). Full statement: §8.1.2.

## R. Commuting the Node-Panel Dual Representation, Full DB Ontology in the 3D UMAP GUI, Markdown Tree Gestures, and Test-DB Garbage Cleanup (2026-06-11)

> Source: the user's prompt of 2026-06-11 (the `/goal` directive). Binding; captured verbatim-first per A.1.
> **Extends §C/§E (the panel↔graph dialectic), §F (the API functional-objects), §P (the recurrent procedural
> renderer + readout perimeter), and §J/§Q.1 (REPL liveness + all-real tests)**, and adds a new test-hygiene
> mandate (R.9). Elaboration targets: `DOMAIN_MODEL.md` §4 (panel anatomy), §6 (projector), §7 (compute graph),
> §7.7 (forward-inverse), §7.8 (rollout/readouts), §11 (REPL), §13 (no-mocks). Audit:
> `CODEBASE_AUDIT_2026-06-08.md` §R addendum.

**R.1 — Integrate a new functionality that commutes the node-panel dual-representation UI/X.**

> "I'd like you to read through our lengthy @docs, integrate a new functionality that commutes the node-panel
> dual-representation UI/X." (user, verbatim)

The panel↔computation-graph dialectic must be **commutative**: edits made in either representation (the
unfolded panel's field-tree, or the decomposed computation-graph children) round-trip losslessly into the
other; flipping representation order never changes the resulting record.

**R.2 — Full database ontology mapped to the 3D UMAP GUI: the full set of DB functional-objects AND scanned webpage chunk structures.**

> "Build out a fully functional new set of features that allows for the full database ontology mapped to our
> 3D umap GUI, which integrates our full set of DB functional-objects and scanned webpage chunk structures."
> (user, verbatim)

**R.3 — The overall design aim: recursive minimalism with memory-function maximalism.**

> "The overall aim for the design of our app is recursive minimalism with memory-function maximalism." (user,
> verbatim)

**R.4 — Data objects dynamically constructed from embedding-graph interaction schemes; 2D-editor inputs downflow to the mirrored 3D nodes for input and peripheral-only output data — project only the outermost computation nodes, as rendered panel versions with clean-text tree structures, that have no succeeding links in the computation-graph representation.**

> "What this means is that data objects can be dynamically constructed from various embedding-graph interaction
> schemes that update with user inputs to the 2D editor, which has downflow effects with the mirrored set of 3D
> nodes for input and peripheral-only output data (that is, project only the outermost computation nodes in the
> form of their rendered panel versions with clean-text tree structures that don't have any succeeding links in
> the computation graph representation)." (user, verbatim)

**R.5 — Markdown-like tree-editing gestures restructure the computation graph (the other side of the dialectic) accordingly: dashes, tabs, numbers, and newlines with trailing text that aren't other newlines.**

> "Note that there are also missing features in markdown-like interactions that, when tree structures are
> modified with markdown editor gestures like dashes, tabs, numbers, and newlines with trailing text that
> aren't other newlines, the structure of the computation graph, the other side of the dialectic representation
> scheme, updates accordingly." (user, verbatim)

**R.6 — External memory creation through curly-brace variable references, and forward-call inverse-lookup functional maps that reflect their full state space of mappings in the database.**

> "The computation graph also has special features that integrate external memory creation through curly brace
> variable references and forward-call inverse-lookup functional maps that reflect their full state space of
> mappings in the database." (user, verbatim)

**R.7 — Dynamic signal rendering of structures over iteration on recursive-chunked tree-like structures within the dialectic graph-panel rendering scheme itself; asynchronous recurrence over these structures in computation-graph-walk time is a recognised design influence.**

> "Dynamic signal rendering of structures over iteration on recursive-chunked tree-like structures within the
> dialected graph-panel rendering scheme itself is also present, along with a recognition in terms of design
> influence of asynchronous recurrence over these structures in computation-graph-walk time." (user, verbatim)

**R.8 — Backend, frontend, and REPL fully and properly integrated; no cheating in tests with one-off empty mocks; REPL mirrors of frontend mutations are the only hard-verification of frontend behavior.**

> "Please make sure that the backend, frontend, and REPL are fully, properly: No cheating in your tests as
> one-off empty mocks, the fully integrated system with REPL mirrors of frontend mutations only to hard-verify
> the proper frontend behavior." (user, verbatim)

**R.9 — Simple garbage cleanup modules over database creation (and such) when running tests, so there is no explosion of one-off databases with different filenames.**

> "Please also build in very important and simple garbage cleanup modules over database creation and such when
> running tests so that we don't get an explosion of one-off databases with different filenames." (user,
> verbatim)

## S. Editor Fixture Deprecation, Retrieval-Sidebar Deprecation, and the Black-Slate Minimalist Panel/Node Design (2026-06-12)

> Source: the user's prompt of 2026-06-12 (the `/goal` continuation directive). Binding; captured
> verbatim-first per A.1. **Deprecates** the fourth foundational fixture (the graph-editor node, §9.5 /
> §18.27) and the retrieval sidebar (§8.3), and **adds** a load-bearing visual design constraint for the
> 2D editor's panels and computation nodes. Doc trickle-down is the stated first priority. Elaboration
> targets: `DOMAIN_MODEL.md` §9.5 (fixtures), §12.1 (AgentState authoring), §8.3 (retrieval),
> `FRONTEND_REDESIGN.md` + `docs/frontend/`, the forbidden-concepts list.

**S.1 — The fourth foundational fixture (the graph-editor node) is a deprecation / anti-pattern: in-node editing and syntax parsing over markdown-gestured recursive text structures does this implicitly within the computation-graph framework, so all of its functionality can be safely erased and subsumed by the new unified knowledge-panel syntax-computation-graph scheme.**

> "I've been going over our @docs/DOMAIN_MODEL.md L.md while you have been working diligently, and I've
> found a deprecation and anti-pattern: our fourth foundational fixture, the graph editor node. Our in-node
> editing and syntax parsing over markdown-gestured recursive text structures does this implicitly within
> our computation graph framework. So all of its functionality can safely be erased and subsumed by our new
> unified knowledge panel syntax-computation-graph scheme." (user, verbatim)

**S.2 — Watch out for updating things implied by this, e.g. the semantics behind "AgentState is a live computation subgraph (§12.1), authored by the user (§5) and by the agent itself via Editor calls".**

> "Watch out for updating things that are implied by this, like the semantics behind 'AgentState is a live
> computation subgraph (§12.1), authored by the user (§5) and by the agent itself via Editor calls'." (user,
> verbatim)

**S.3 — The retrieval sidebar is another anti-pattern, because in-editor halo queries with ray projections subsume it.**

> "I should also note that another anti-pattern is our retrieval sidebar because in-editor halo queries with
> ray projections subsume this." (user, verbatim)

**S.4 — A new minimalist design constraint for the graph editor: thin-silver border and completely black infill with serif white text — minimalism and intrigue within the unknown. The knowledge-panel half of the dialectic graph-editor structure is only this blank editable bordered slate; computation nodes are similar. Nothing other than the black slate — no x, no minimizer, no top bar whatsoever.**

> "A new minimalist design constraint for our graph editor is thin-silver border and completely black infill
> with serif white text. It gives a sense of minimalism and intrigue within the unknown. Present in the
> design of the knowledge panel half of the dialectic graph editor structure, there is only this blank
> editable bordered slate. There are similar for computation nodes. Nothing other than the black slate. No x,
> no minimizer, no top bar whatsoever." (user, verbatim)

**S.5 — One of the gestures collapses panels into their parent field computation nodes. This design constraint must be present everywhere. That way, clicking on collapsed-node forms of larger panel structures hidden in the editor allows the halos to retrieve and remain proximal to the central node while abstracting over semantic-space content and distribution complexity.**

> "I forget which gesture, but I think one of the gestures dictates collapsing panels into their parent field
> computation nodes. If this design constraint is not present, please make it present everywhere. That way,
> clicking on collapsed-node forms of larger panel structures hidden in the editor allows the halos to
> retrieve and remain proximal to the central node while abstracting over semantic space content and
> distribution complexity." (user, verbatim)

## T. The Black Markdown Slate — Single Content-Only Text-Tree Card, Datablock Connections Under-The-Hood, In-Card Internalize/Externalize Gestures (2026-06-13)

> Source: the user's prompt of 2026-06-13 (a `/goal` directive refining §S.4/§S.5). Binding; captured
> verbatim-first per A.1. **Supersedes the structured-field card structure**: the card is no longer a
> name-input + description-textarea + data-textarea + rendering-preview stack with a black skin — it is a
> SINGLE black markdown slate that renders a pure text-tree from its underlying datablock, edited with
> markdown editor gestures. Elaboration targets: `DOMAIN_MODEL.md` §4 (panel anatomy), §4.1.1
> (click-to-edit), §4.5 (compact representation), §4.6 (markdown gestures / field-tree growth), §7.3.4
> (panel↔graph gestures), §8.2 (halo); `FRONTEND_REDESIGN.md` + `docs/frontend/`.

**T.1 — What is currently in the frontend is not the singular markdown plate that was requested, and the background is not purely black. There are still structured fields in the cards, not a singular black markdown slate that renders pure text-tree structures from its underlying datablocks with hard types.**

> "What is currently in our frontend is not the singular markdown plate that was requested, and the
> background is not purely black. There are currently still structured fields in our cards present on their
> current versions, not a singular black markdown slate that renders pure text tree structures from its
> underlying datablocks with hard types." (user, verbatim)

**T.2 — A card that 'sticks' to the 2D editor UI should literally be just the panel summary from the scanned-rendered sample.**

> "i.e. a card that 'sticks' to the 2D editor UI should literally be just the panel summary from the
> scanned-rendered sample." (user, verbatim)

**T.3 — The aim is full visibility and access to the base elements through a completely minimal, content-only panel that gets graph-editor treatment.**

> "The aim here is to have full visibility and access to the base elements through a completely minimal and
> content-only kind of panel that gets graph editor treatment." (user, verbatim)

**T.4 — Halos aren't responding to the scrollable panel of the card (a bug to fix).**

> "We also see that halos aren't responding to the scrollable panel of the card." (user, verbatim)

**T.5 — The panel-version is a tree-structured graph editor that is completely in-text and parsed with specialized editor-specific syntaxes.**

> "You can envision the panel-version as a tree-structured graph editor that is completely in-text and
> parsed with specialized editor-specific syntaxes." (user, verbatim)

**T.6 — The card should be literally a black markdown slate with the data-block connections only under-the-hood.**

> "What the card should be is literally a black markdown slate with these data block connections (only
> under-the-hood)." (user, verbatim)

**T.7 — Make note of in-card gestures to internalize and externalize API object links AND computation graph links.**

> "Please also make note of in-card gestures to internalize and externalize API object links *and*
> computation graph links." (user, verbatim)

**T.8 — Recommendation: completely strip out the frontend while leaving the important backend links more or less perfectly intact for bookkeeping, while the frontend reflects the minimal-text tree structures with markdown editor gestures and properties.**

> "I recommend completely stripping out the frontend while leaving our important backend links more or less
> perfectly intact for bookkeeping, while our frontend reflects the minimal-text tree structures with
> markdown editor gestures and properties. I suggest you set this edit as a /goal in that you very carefully
> go over our graph editor design with these requirements in mind. I would also recommend you include any
> verbatim requirements here that should also be expected as reflected in our documentation but may not be
> so." (user, verbatim)

## U. The HTML Chunk Card Renders Its Deduplicated Content As A Pure-Text Tree (2026-06-13)

> Source: the user's prompt of 2026-06-13 (a `/goal` directive, the second of the day). Binding;
> captured verbatim-first per A.1. **Defines exactly what the HTML chunk slate (§T, §C, §G) renders:**
> the chunk's *deduplicated content*, presented as a **pure-text tree that reflects the tree structure
> of the HTML after deduplication**. This is the concrete realisation of T.2 ("a card that 'sticks' to
> the 2D editor should literally be just the panel summary from the scanned-rendered sample") and of
> the long-deferred **HtmlStrategy** of the §E.1 syntax-agnostic compile. The user demands it be built
> "exactly and perfectly" and **reflected everywhere — design docs AND codebase — explicit and
> all-encompassing**, affecting every related feature. Goal doc: `docs/HTML_DEDUP_CONTENT_TREE_GOAL.md`.
> Elaboration targets: `DOMAIN_MODEL.md` §4.1 / §4.5 / §7.1 (HTML compile strategy) / §8D.20
> (tree-pretty-print) / the scanner section; `docs/frontend/field_tree.md` (HtmlStrategy realised),
> `billboard.md`, `concept_view.md`, `scan_streaming.md`; `docs/code_specs/backend/scanner.md`;
> `backend/mapper/chunk_render.py`, `backend/dom/`.

**U.1 — The HTML chunk card presents its deduplicated content in a pure-text tree format that reflects the tree structure of the HTML (after deduplication).**

> "The html chunk card should have its deduplicated content presented in a pure-text tree format that
> reflects the tree structure of the html (after deduplication)." (user, verbatim)

**U.2 — The worked example (binding golden I/O).** Given this HTML (one archive.org search-result `<article>`, with declarative shadow DOM, nested wrappers, repeated text, and content-bearing attributes):

```html
<article aria-posinset="4" aria-setsize="200" data-cell-index="3" data-rendered="">
      <tile-dispatcher enablehoverpane=""><template shadowrootmode="open"><div>
      <a aria-describedby="link-aria-description" href="/details/princetonuniver01librgoog" aria-label="Princeton University Library : American Library Association visit, June 29, 1916" aria-haspopup="dialog">
        <item-tile><template shadowrootmode="open"><div>
        <div>
          <div>
      <image-block><template shadowrootmode="open"><div>
        <item-image><template shadowrootmode="open"><div>
      <img alt="" src="https://archive.org/services/img/princetonuniver01librgoog"/>
    </div></template>
        </item-image>
      </div></template>
      </image-block>
            <div>
              <h3 title="Princeton University Library : American Library Association visit, June 29, 1916">
                Princeton University Library : American Library Association visit, June 29, 1916
              </h3>
            </div>
      <div>
        <span title="Princeton University Library">
          by Princeton University Library
        </span>
      </div>
          </div>
      <tile-stats><template shadowrootmode="open"><div>
        <p>
          Item Stats
        </p>
        <ul>
      <li>
        <p>Mediatype:</p>
        <tile-mediatype-icon><template shadowrootmode="open"><div title="Text">
        <p>Text</p>
      </div></template></tile-mediatype-icon>
      </li>
      <li title="450 all-time views">
        <p>
          <span>all-time views:</span>
          450
        </p>
      </li>
      <li title="0 favorites">
        <p>
          <span>favorites:</span>
          0
        </p>
      </li>
      <li title="0 reviews">
        <p>
          <span>reviews:</span>
          0
        </p>
      </li>
        </ul>
      </div></template>
      </tile-stats>
        </div>
      </div></template>
            </item-tile>
      </a>
      <div>
        Press Down Arrow to preview item details
      </div>
      </div></template>
      </tile-dispatcher>
            </article>
```

> Becomes, on the markdown, something like:

```markdown
/details/princetonuniver01librgoog
https://archive.org/services/img/princetonuniver01librgoog
Princeton University Library : American Library Association visit, June 29, 1916
by Princeton University Library
Item Stats
Mediatype: Text
450 all-time views
0 favorites
0 reviews
Press Down Arrow to preview item details
```

**U.3 — Build it exactly and perfectly, before proceeding; reflect it everywhere (design docs AND codebase); explicit and all-encompassing.**

> "Before doing anything else, make it a /goal to build out this functionality exactly and perfectly
> before we proceed. You must reflect this everywhere; design docs and codebase. This must be explicit
> and all encompassing. This will affect every portion of related features and functionality." (user,
> verbatim)

## V. Real-Time Scan→UMAP Streaming SLA, Multi-Site Scan Verification, Halo Ray-Projection Mechanics, and the Circular Minimal Computation Node (2026-06-13)

> Source: the user's prompt of 2026-06-13 (a `/goal` directive: "document, align, and verify"). Binding;
> captured verbatim-first per A.1. **Extends §B (streaming/UMAP), §D/§O.18 (halo ray-projection), §T/§U
> (the slate + dedup content tree), §J/§Q.1/§R.8 (REPL-mirrored all-real verification).** This is a
> verify-against-the-live-stack directive; the named features must be engineered into code per the
> minimalist design. Goal docs: `BLACK_SLATE_GOAL.md`, `HTML_DEDUP_CONTENT_TREE_GOAL.md`, and the
> verification matrix therein.

**V.1 — The full set of scanned chunks must stream real-time to UMAP and update live in real-time. Scans in milliseconds (mutation observers); UMAP a few seconds initially but seconds-to-milliseconds for updates streamed to the frontend. Do not interfere with the scanner's chunk bookkeeping mechanics.**

> "Test and verify that the full set of chunks that are scanned are streamed real-time to our UMAP and
> are updated live in real-time as well. The scans should be in milliseconds since we have mutation
> observers. The umap might be a few seconds initially, but has to be in the seconds to milliseconds
> region for updates streamed to the frontend. Make sure not to interfere with our chunk bookkeeping
> mechanics in our scanner." (user, verbatim)

**V.2 — Run scans; verify all cards on the page are scanned and retrievable correctly, and rendered as recursive text correctly when retrieved/displayed — in their content-ful and minimal form, using ONLY the deduplicated content (but still all of it in the HTML chunk) with valid content detection from the EXISTING ruleset. The existing content-extraction ruleset must be used and the extracted content deduplicated (dedup is added on top; do not deviate from the current scan-chunk recursive-iterative routines).**

> "Please run our scans and verify all the cards on the page are scanned and retrievable correctly, and
> are rendered as recursive text correctly when retrieved and displayed in their content-ful and minimal
> form, using only the deduplicated content (but still all of it in the html chunk with a valid content
> detection from our existing ruleset). You should make sure the existing content extraction ruleset is
> used and that the content extracted is deduplicated." (user, verbatim)

**V.3 — Verify on these websites:** `https://ww.archive.org`, `https://www.tarot.com`, `https://noetic.org/` (all content, including all types of embedded media, extractable — do not deviate from the current ruleset and scan-chunk recursive-iterative routines), `https://www.yourchineseastrology.com/horoscope/`, `https://studycli.org/chinese-culture/traditional-chinese-medicine/`.

> "Test and verify this on the following websites: https://ww.archive.org / https://www.tarot.com /
> https://noetic.org/ (make sure all content, including all types of embedded media, are extractable
> here, such that we don't deviate from our current ruleset and scan-chunk recursive-iterative routines)
> / https://www.yourchineseastrology.com/horoscope/ /
> https://studycli.org/chinese-culture/traditional-chinese-medicine/" (user, verbatim)

**V.4 — Use the REPL and the auto-halo retrieval with ray projection and dynamic along-line sliding, with a CONSTANT retrieval-similarity ray projection and a ray ANGLE that updates as it is traced between the 'sticked' panel and the retrieved nodes in the 3D GUI in COLLAPSED computational-node form.**

> "Make sure to use the REPL, the auto-halo retrieval with ray projection and dynamic along-line sliding
> with a constant retrieval similarity ray projection and a ray angle that updates as it's traced between
> the 'sticked' panel and the retrieved nodes in 3D GUI in collapsed computational node form." (user,
> verbatim)

**V.5 — Representations and gestures must be correctly engineered into code per the minimalist design with custom syntax parsing/actions: click gestures navigate the hidden links within a text-tree entry; navigation goes between knowledge-panel/text-tree fields in markdown and the minimalist computation-graph CIRCULAR nodes whose root-most field is the ONLY text in the node. No fancy titles or upper bars with buttons. Right/left/double clicks define transformations and navigations between these representations.**

> "We need to make sure that our representations and gestures are correctly engineered into code as per
> the minimalist design with custom syntax parsing/actions, along with our click gestures that help
> navigate the hidden links within a text-tree entry, as well as going between knowledge panel/text tree
> fields in markdown and the minimalist computation graph circular nodes with the root most field being
> the *only* text in the node. No fancy titles or upper bars with buttons. All gestures with right and
> left clicks and double-clicks are supposed to define transformations and navigations between these
> representations." (user, verbatim)

**V.6 — /goal: document, align, and verify all of these implied requirements, fixes, and updates.**

> "/goal document, align, and verify all of these implied requirements, fixes, and updates" (user, verbatim)
