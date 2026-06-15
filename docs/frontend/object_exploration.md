# Object Exploration — Recursive Type-Strict & Reference Navigation

> **Status: realised (cp/*.js core); elaborates `DOMAIN_MODEL.md` §7.3.4 / §9.6.1 / §7.8 / §15.9 / §18.32, §M verbatim.** The recursive type-strict exploration is carried by `cp/concept_graph.js`: `_pythonNativeTypedView` (signature → `key:Type` + `→ReturnType` rows for `python_function`/`python_property`/`python_object` trees), the read-only 🔒 fixture/python-native rule (no ×, no edit), and the §7.3.4 **right-click-token inline fold** (`node_fold` — rank-1 reference reveal without leaving the panel). The type ontology it walks is the materialiser's `OBJECT_HAS_*` / `FUNCTION_*_TYPE` edges (`PythonAPIMaterialiser.md`). Verified by `node-fold-roundtrip` + `probe_python_api.py` (transitive type closure). Remaining: deep multi-hop reference auto-resolution UX.

---

## §1 — Identity

This surface is how a materialised Python-API object (§9.6) — and, by the same machinery, any typed user node — is **explored** in the 2D editor: a `name: Type = value` pure-print panel whose every token is a navigable handle into the next rank of the object's type graph (superclass, properties-as-modules, function I/O, reference targets). Exploration is recursive and **type-strict**: each unfold resolves one more rank of the real object model, reconstructed from memory references (M.2). The panel is not a snapshot; it is the **generative readout** of the reservoir (§7.8) discretised into an editable, foldable object model.

The defining contract is the **seven-gesture model** (§7.3.4): hover previews, single-left edits, **left-click-drag wires a link (and inherits the source's I/O types + object model)**, right-click folds rank-1 links (knowledge-panel form only, §O.1), right-click-on-self collapses the whole panel, double-left-click toggles panel↔graph (a panel becomes a graph; a graph node returns to its containment panel), and **double-right-click deletes** a token reference/instance. The exploration *reads* the object; editing, wiring, compiling, deleting, and halo retrieval compose on top of it.

---

## §2 — Structure

The exploration surface is a `panel`-mode `ConceptView` (`concept_view.md`) whose body is a `FieldTree` (`field_tree.md`) extended with a **type slot**: each row is `key : Type = value` rather than `key : value`. The `Type` and the `value` may each be a literal or a `{reference}` token (M.3).

**Owns (transient):** the per-node fold state for the current render (which `node_path`s are unfolded and to what depth); the hover-preview overlay; the active edit textarea + caret. **Reads from `WorkspaceStore`:** `concepts[id]` (the node + its `data`/type metadata), `edges` (typed links: `OBJECT_HAS_PROPERTY`, `OBJECT_HAS_FUNCTION`, `FUNCTION_INPUT_TYPE`, `FUNCTION_OUTPUT_TYPE`, super/inheritance), `index` (for halos on blank fields), and `ui.node_fold_state[id]` (the persisted fold state, §8).

**Canonical base form (M.3):**
```
self:WebBrowser
   NO_CHANGE_LIMIT: int = 3
   SETTLE_TIMEOUT: float = 0.25
   ...
   driver: WebDriver = {driver}
   scanner: {FunctionOutputType} = {scan}
   ...
```
Rows are singular-value compute nodes with memory references (M.2). `{driver}`, `{scan}`, `{FunctionOutputType}` are references resolved from the store; literals (`3`, `0.25`) render inline. The object model is *reconstructed* from these references to the unfolded depth — never stored as a flat blob.

---

## §3 — Composition

| Peer | Through |
|---|---|
| `ConceptView` (`concept_view.md`) | hosts the typed panel; the panel↔graph double-left-click toggle |
| `FieldTree` (`field_tree.md`) | renders the `key:Type=value` rows; the type slot; the edit path |
| `WorkspaceStore` (`workspace_store.md`) | `concepts`, `edges` (typed links), `index`, `ui.node_fold_state` |
| `GestureGateway` (`gesture_gateway.md`) | `ui-node-expand/-collapse`, `ui-compile-expand/-collapse`, edit + halo gestures |
| `Halo` (`halo.md`) | halos fire on text-input fields (incl. blank); pure-`{ref}` fields fire none; mixed = whole resolved field (§7, §O.3) |
| `compile_collapse.md` | double-left-click panel↔graph compile (§6) |
| `Editor` (`editor.md`) | hosts the panel + the graph form; instance-inheritance wiring (§9) |
| backend materialiser (§9.6) / closest-inverse (§7.7) | supply the type graph + function memory maps; the frontend *renders*, never computes the types |

---

## §4 — Behaviours: the seven-gesture model (§7.3.4, M.3–M.8, N.4/N.13)

| Gesture | Target | Effect |
|---|---|---|
| **Hover** | a typed field / `{token}` (within its mini-card box bounds) | *preview* the next-rank expansion transiently; un-hover collapses the preview unless it was committed by a right-click (M.3/M.4) |
| **Single left-click** | a token (key / strict type / value) | *edit* it as a blended, borderless, cursor-blinking field — a smoothed text editor with no per-token chrome (M.8; §4.1.1) |
| **Right-click** | a token (key / strict type / value, base or reference form) | *toggle expand/collapse over rank-1 links* to the directly-linked nodes, **inline in the knowledge-panel form** (folding is panel-only — §O.1), preserving per-subtree fold state (M.6) |
| **Right-click** | the base / self node (`self:WebBrowser`) | *collapse the entire panel to the singular self node*; re-expand restores the prior fold state (M.6) |
| **Double left-click** | the panel body / base node — or, in graph form, a graph node | *panel → graph form*, and *graph node → its containment panel*; the toggle is **symmetric in both representations** (M.7) |
| **Left-click-drag** (graph form) | from one node onto another | *wire a link*; the target **inherits the source's input-output types and object model** (N.4) and duplicate-instantiates the source as a rank-1 component (§5.1); in panel form, the drag drops onto a field |
| **Double-right-click** | a token reference / instance in rendered print | *delete* that reference/instance, in either panel or graph form (N.13) |

**Non-collision rules (§18.32):**
- Single-left and right-click never both fire on one press; single-left targets *inside* a token's bounds (edit), right-click targets the same token (fold) — distinguished by button, not position.
- Double-left targets the panel body / base region *outside* any editable token, so it never races a token edit.
- A right-click on the base/self node is the collapse-to-self; a right-click on a child token folds that child. Same button, target disambiguates.
- Read-only python-native nodes (§9.6): single-left is a no-op highlight (editing refused); hover/right-click/double-left all work (exploration always permitted).
- Left-click-*drag* (press → move → release between nodes) is distinct from a single-left *click* (edit): the drag wires + inherits (N.4); the click edits in place.
- Double-right-click (delete, N.13) is distinct from single-right-click (rank-1 fold): the double deletes the token reference/instance; the single folds.

---

## §5 — The next-rank type graph (M.5, M.6)

Right-click (or hover-preview) on a node materialises its **rank-1 links** — any-and-all nodes one rank off the node — as an indented subtree, **in the knowledge-panel form**, recursively chunking the abstract syntax tree (M.3) one rank at a time. The link kinds:

| Next-rank link | Renders as | Backend edge (§9.6) |
|---|---|---|
| **Superclass / inheritance** | a `super:BaseWebDriver` row at the child rank | inheritance edge |
| **Property (a module)** | the property's own `key:Type=value` subtree (recursive) | `OBJECT_HAS_PROPERTY` |
| **Function I/O** | typed input fields + an inferred output-structure field (§6) | `OBJECT_HAS_FUNCTION` + `FUNCTION_INPUT_TYPE` / `FUNCTION_OUTPUT_TYPE` |
| **`{reference}` target** | the referenced node's panel form, resolved | typed `{var}` edge (§3.2.1) |

**Hover-expanded example (M.4)** — hovering `driver: WebDriver = {driver}` previews the `WebDriver` object model:
```
driver: WebDriver = {driver}            ← hovered / right-clicked
   super:BaseWebDriver
   command_executor: str | RemoteConnection = 'http://127.0.0.1:4444'
   keep_alive: bool = True
   file_detector: FileDetector | None = None
   options: BaseOptions | list[BaseOptions] | None = None
   locator_converter: LocatorConverter | None = None
   web_element_cls: type[WebElement] | None = None
   client_config: ClientConfig | None = None
scanner: {FunctionOutputType} = {scan}
```
Properties-are-modules (M.2): `WebDriver`'s own rows can themselves be right-clicked to expand a further rank, recursively, to arbitrary depth.

---

## §5.1 — External-Reference Propagation & The Type-Stripped Compute Node (N.3–N.10)

When a user compute node references an external functional-object — e.g. a `duckduckgo` node referencing the WebBrowser's `scan`/`scanner` — the reference **propagates through as its own set of objects, recursively rendered in new panels** (N.3). Three rules govern it:

1. **Duplicate-instance proxy (N.6).** The referenced functional-object is instantiated as a **duplicate** proxying operational calls to the originating object, materialised as a **rank-1 component** of the referencing node. It behaves identically in panel form (a field of the node) and graph form (a link from the node to both the `scanner` functional-object and the `WebBrowser` object).
2. **Type-stripped, purely-structural rendering (N.4/N.5).** Unlike the *raw* object's typed inspection panel (§9.6.1, `key : Type = value`), a *user compute node's* rendering presents **no types** — purely structural over tabs + newlines, each field a literal, an optional organising label, or a `{ref}`. Types/IO persist internally for inverse lookup (§6) but are not presented. This is rank-1 minimalism as a **pro-pattern** (§18.32 guards its inverse).
3. **`{ref}` = memory-access activation (N.10).** A curly-brace field is *an activation of a memory-access procedure elsewhere in the app*; the text beside it is an **optional organising label**; **names may contain spaces** (the tree is discerned over `\t` + `\n` only). A braceless token is a literal/label; `{paginate}` is the activation.

**The DuckDuckGo walkthrough — the canonical example (N.4–N.9).** Begin in graph form; left-click-drag the WebBrowser's `scanner` node onto `DuckDuckGo` (the target inherits I/O types + object model, N.4). The final panel presents **no types**:
```
DuckDuckGo
   {scanner}                          ← purely structural, no type presentation (N.4)
```
Right-click `{scanner}` → its rank-1 structure unfolds, type/IO-stripped; outputs blank until bound or inverse-referenced (N.5):
```
DuckDuckGo
   scanner
      url {}
      dom {}                          ← arbitrary output type, blank unless externally referenced for inverse lookup
```
Bind inputs by reference (names may have spaces, N.7); the call completes to a **ShadowDOM** object — a simplest-possible OO Python type (N.1) — whose **full per-sample distribution lives in the 3D Real register**, while the 2D node stays at **rank-1** (the base functions/relations defining the ShadowDOM, N.7):
```
DuckDuckGo
   scanner
      url {duckduckgo url}
      dom {scan for duckduckgo url}

duckduckgo url
   https://www.duckduckgo.com/

scan for duckduckgo url
   search {}
   {paginate}
   chunk {chunk samples}              ← per-sample signal iteration (N.9)
```
Right-clicking a `{ref}` reveals its next rank-1 structure; selective unfolding keeps the slim minimalist tree without losing per-sample iteration (N.8). **Per-sample signal print-rendering is shown only when a downstream compute link externally references the recursively-chunked iterable** (N.9) — otherwise the node rests at its rank-1 abstraction. The full scan distribution is the Real register's concern (`projector.md`, `scan_streaming.md`); the 2D compute graph constrains perception to rank-1 (N.7, §18.32). This rank-1-in-the-Imaginary / full-distribution-in-the-Real split is the structural meaning of *rank-1 minimalism as a pro-pattern*.

**The brace-reveal works in both forms (§O.1).** The `{…}` braces are the **fold/hidden marker** (§O.2) in *both* panel and graph: they mark a node whose rank-1 links aren't all revealed. In the **panel**, right-click unfolds the rank-1 fields inline (braces drop, children indent). In **computation-graph form**, **hover previews** the rank-1 links and a **click instantiates the rank-1 walk** as visible nodes joined by **undirected line links**; graph form has no *independent* fold state and stays in **node-count parity** with the panel (revealing in one reveals in both). A `{ref}` to an already-visible node resolves to a **solid link**; a `{ref}` to a hidden node keeps its braces. These are the three brace states — **braced-hidden / revealed-internal / resolved-external** (§O.1a) — with the underlying graph link identical across all three. So the internal/external and folded/unfolded distinctions are *rendering* choices over one invariant graph.

**Iterables root to base nodes; iteration only on external `{ref}`; singular-primitive decides kind (§O.19).** An iterable recursive chunk is *sourced to its base/root node*; a panel referencing it **dynamically updates from the root source down to its fields** as the root changes. **Recursive chunk iteration applies only when the content is externally referenced via `{curly brace}`** — inline-rendered content is not iterated (§4.6.1). And the **singular-primitive aspect** decides kind: a singular-field primitive IS a computation-graph **node**; a non-singular aggregate is a **knowledge panel** that compiles to the graph (§4.6 / §7.3.4). 3D nodes hovered in base-UMAP *or* transported-halo form (§O.18) show their knowledge-panel representation; a click sticks it into the 2D for graph integration (§4.2 / §5.3).

---

## §6 — Functions as memory-lookup (M.3, M.5, M.9)

A function node is a **memory map from typed inputs to an inferred output type**: *"forward calls linked to a function node via equality of an input on the right and an output type on the left infer output types"* (M.5). Expanding a function reference reveals its input fields (each typed, each a variable or reference) plus its output-structure field, loosely linked to the function variable node:

**Function-expanded example (M.5):**
```
scanner: {FunctionOutputTypeNodeReference} = {scan}     ← hovered + clicked
   some_input_variable_name: SomeType = {variable or reference to another node}
   some_other_input: SomeOtherType = {typed_variable_reference}
   anotherfunction: {AnotherFunctionNodeReference} = {anotherInputVariableRef}
   scanner_output_structure: KnownOutputStructure = <rendered output object from function>
```

- **Forward (automatic rendering, M.9).** When inputs are bound, the function *renders its output* into `scanner_output_structure` — "automatic rendering... similar to memory reference lookup" (M.9). The property's declared type (`scanner: {FunctionOutputType}`) is *inferred* from the function's output type (M.5: input-on-the-right ↔ output-type-on-the-left equality).
- **Inverse (closest-inverse lookup, §7.7).** When the output is known but an input is unbound, the function's memory map is read backward — the closest-inverse retrieval (§7.7) surfaces the most-related input nodes. This is why "functions serve more as automatic memory lookup to inputs" (M.3): a bound-input function looks up its output; an unbound-input function with a known output inverse-looks-up its inputs.

The port schema (§9.8) is the typed I/O behind this; the panel's type slot is its pure-print rendering. User-authored types (langgraph/pydantic templates over base API types, M.9) expand identically — a pydantic output model renders as a typed subtree the same way a Python class does.

---

## §7 — Halos on blank fields; sticked apparitions as compute graphs (M.10)

Exploration never sacrifices retrieval. **Halos fire even on completely blank fields** (M.10): an empty `value` (or a new row's empty key) opens an apparition halo (`halo.md`) keyed by the surrounding panel's task context — the candidates are nodes semantically similar to the task at hand. As the user edits the panel's fields, the halo's retrieval query updates and the apparitions re-radiate. **Gating (§O.3):** a halo fires only from a field carrying rendered literal text (a blank/in-progress *text* field counts); a **pure-`{ref}`** field fires *no* halo (it is already bound); a field mixing text and `{ref}` queries the **whole resolved field** (the text plus the resolved ref content).

A sticked apparition (click-and-stick from the halo, §8.2.2) becomes a first-class node: it can itself be **compiled into its own computation graph** (double-left-click, §6), and **its unique field variable names can be recursed over and referenced** (`{var}`) in the panel the user is building (M.10). So halo retrieval and object exploration compose: a stuck candidate is explored and referenced by exactly the same five gestures (§4) as any other node.

---

## §8 — Fold-state preservation (M.6, §18.32)

Fold state is **persisted and preserved** across collapse/re-expand cycles (M.6): *"If a node within the card is right clicked after it was expanded, the expanded tree(s) contract again but preserve at which levels the subtrees were folded and unfolded."*

- The fold state is the set of unfolded `node_path`s for a card, held in `ui.node_fold_state[card_id] = { expanded_paths: [...] }` (a §10.5 mirror field, so it round-trips through the REPL, §9).
- Collapsing a parent hides its subtree but **retains** each descendant's expanded/collapsed flag; re-expanding the parent restores the descendants to exactly the fold levels they held.
- Right-clicking the base/self node collapses the whole panel to `self:WebBrowser` while retaining the entire fold tree; re-expanding restores it intact.
- A regression that resets folds to fully-collapsed on every toggle is the §18.32 anti-goal; the `panel-gesture-fold-roundtrip` env-scenario asserts preservation.

---

## §9 — Object-instance inheritance (M.11, §15.9)

When the user connects a **live object instance** — e.g. a `WebBrowser` instance — to a field in their own compute-knowledge-panel, the field inherits the *instance's* object model, not merely the type:

- The field's type slot resolves to `WebBrowser` and its value to the bound instance (a typed `{var}` reference whose target is the instance node, §3.2.1).
- Right-clicking the field expands (§4) into the **instance's** typed panel — `driver: WebDriver = {driver}` resolving to the *actual* driver the instance holds, its real `NO_CHANGE_LIMIT`, etc. — so the user's panel composes over a live object rather than an abstract signature.
- The inheritance is the recursive resolution of that reference's object model to the unfolded depth; the connected instance is itself drivable as part of the reservoir substrate (§7.8).

This is type-inclusion via inheritance (§15.9) extended to instance level: the same typed-edge mechanism that lets `{urls_panel}` inherit `url_set` lets a field inherit a whole live `WebBrowser`.

---

## §10 — Play/pause; running computations (M.11)

A **play/pause** control in the top-right corner of the 2D editor runs the computation (M.11) — it is the rollout coordinator's surface (`agent_and_rollout.md`, §7.5). Exploration and computation compose: the user explores/edits the typed panels (this doc), then presses play to drive the reservoir (§7.8) over sampled inputs under the signal-stream constraint, pausing to edit a node mid-rollout and resuming with the edited content. Play/pause does not change the gesture model; it is the trigger that turns the explored, authored graph into a running readout.

### §10.1 The full rollout → readout perimeter → projector (§7.8.1–§7.8.5, §6.6.4, P)

Pressing play drives a **cascaded render-compile rollout** (§7.8.1 / §7.8.2): inputs assembled by **inverse lookup over generalized chunk samples** (§7.8.1, the §7.7 forward-inverse read on the input side) cascade through the graph until the **readout nodes** — the *final-most recursive unfolded nodes*, the graph's **perimeter / spherical hypersurface** — settle (§7.8.2). Because subgraphs have differing rollout path lengths and **recurrent maps** fold the perimeter back onto hidden-state nodes, the perimeter settles **asynchronously**, and each readout streams to the 3D projector as a **delta update** to the network map (§7.8.3), landing on the perimeter (§6.6.1) and — in **passive state** (no image billboard) — rotating physically + in HSV (§6.1 / §8.2.1.2). On the projector side the whole graph collapses to a single **bisector node** placed between the (hidden) input and output centroids — hub of a **UMAP-independent link network** tying root urls / click-sticked inputs and every perimeter readout to it (§6.6.4); clicking it opens/closes this graph in the editor. As the user adds complexity the **abstraction front** (the readout perimeter) advances past nodes that were previously terminal (§7.8.5) — yesterday's readout becomes today's hidden state. The whole loop is the **iterated information-space procedural renderer** / optimal-transport dialectic of §7.8.4.

---

## §11 — Activities, Sequences, Data, Results

### §11.1 Activities (gestures)
| Activity | Gesture | Effect |
|---|---|---|
| Preview next rank | (hover) | transient subtree preview (M.3/M.4) |
| Edit a token | `concept-edit-data-row` / `concept-rename` (single-left) | borderless cursor field (M.8) |
| Expand a node inline | `ui-node-expand { card_id, node_path }` (right-click) | next-rank subtree unfolds; `node_fold_state` += path |
| Collapse a node inline | `ui-node-collapse { card_id, node_path }` (right-click) | subtree folds; fold state preserved; base path = collapse-to-self |
| Compile to graph form | `ui-compile-expand { card_id }` (double-left) | panel → node-link graph (`compile_collapse.md`) |
| Collapse graph form | `ui-compile-collapse { card_id }` (double-left) | graph → panel |
| Halo on text field (incl. blank) | `ui-halo-focus { focal_card_id }` | apparitions on text-input fields; none on pure-`{ref}` (§7, §O.3) |
| Connect an instance | `concept-edge-create` | instance inheritance (§9) |
| Run | `rollout-play` / `rollout-pause` | drive the readout (§10) |

### §11.2 Sequence — recursive inline exploration
```
right-click `driver: WebDriver = {driver}`
   → gateway ui-node-expand { card_id, node_path:"driver" }
   → ui_state_changed (kind=node_fold) → node_fold_state[card_id].expanded_paths += "driver"
   → FieldTree resolves WebDriver's type graph from store.edges (OBJECT_HAS_PROPERTY / super / function I/O)
   → renders the indented super + typed-attribute subtree inline (M.4)
right-click `options: ... = None` (a child of driver)
   → ui-node-expand { node_path:"driver.options" } → next rank of BaseOptions unfolds (recursive)
right-click `driver` again
   → ui-node-collapse { node_path:"driver" } → subtree hides; "driver.options" flag retained
   → re-expand restores driver AND driver.options to prior fold levels (§8, M.6)
right-click `self:WebBrowser`
   → ui-node-collapse { node_path:"" } → whole panel collapses to the self node; full fold tree retained
double-left-click panel body
   → ui-compile-expand { card_id } → panel → graph form; double-left a graph node → its containment panel (compile_collapse.md)
```

### §11.3 Data
**Reads:** `concepts[id]` (node + type metadata), `edges` (typed links), `index` (blank-field halos), `ui.node_fold_state[id]`. **Sends:** `ui-node-expand/-collapse`, `ui-compile-expand/-collapse`, edit + halo + edge-create gestures. **Receives:** `ui_state_changed (node_fold)`, `concept_changed`, `concept_index_update`.

### §11.4 Results
A recursively-explorable typed object panel: each rank resolved on demand from the real type graph, fold state preserved, functions rendering their outputs (or inverse-looking-up inputs), blank fields radiating halos, connected instances inheriting their live object models, and a double-left-click flip to graph form. The panel is the reservoir's generative readout (§7.8), editable and foldable.

---

## §12 — REPL Mirroring

The new gestures are §10.5-mirrored so the Symbolic register stays faithful (`repl_mirroring.md`):
- `ui-node-expand` / `ui-node-collapse` set `node_fold_state[card_id] = { expanded_paths: [...] }`; frame `ui_state_changed (kind=node_fold)`. The REPL drives the same inline exploration a user's right-click would, and the viewer can reflect the current fold tree (an extensible `node-fold` row).
- The panel↔graph compile keeps the existing `compile` row (`compile_collapse.md` §9).
- The `panel-gesture-fold-roundtrip` env-scenario asserts that a REPL `ui-node-expand` then `ui-node-collapse` then re-expand restores the fold state byte-for-byte (§8, §18.32).
- Halos-on-blank and instance inheritance ride the existing `halo_focus` and `edges`/`concept_changed` mirrors (`halo.md` §9, `editor.md` §9).

The completeness rule holds: every exploration state the user can reach is reportable via `node_fold_state`, so a fold the user opened is never invisible to the REPL (§18.1).

---

## §13 — Theme

The typed panel is **black-core + silver-outline** (`theme.md`): black fill, a silver-outlined border, and **black glyphs traced by a silver outline** — monospace pure-print (`field_tree.md` §10). The **type slot** (`: int`, `: WebDriver`, `: {FunctionOutputType}`) renders in `--text-dim` (a dimmer silver outline) so types recede behind keys and values without colour; reference tokens (`{driver}`, `{scan}`) carry a faint `--silver-700` underline marking them navigable. The five gestures express in silver only: **hover brightens the token's silver outline** (no tint, no fill — everything stays black); the inline rank-1 fold indents under the parent with `--silver-900` guide lines (structure felt, not seen); the borderless edit field (M.8) is the imperceptible `--black-edit` lift with a `--silver-100` caret and **no border** — the "purely smoothed text editor without special borders around each selective and interactive token." Collapse-to-self shows only the `self:` row. Read-only nodes: `--silver-900` outline, 🔒, type slot in `--text-lock`. No element here breaks the black-and-silver — exploration is entirely an Imaginary-plane activity; the only filled colour reachable from it is a halo phantom that ray-projects a 3D chunk (`halo.md`, the exception zone).

---

## §14 — References

- `DOMAIN_MODEL.md`: §7.3.4 (gesture model), §9.6.1 (typed panel form / functions-as-lookup), §7.8 + §7.8.1–§7.8.5 (reservoir readout + cascaded rollout to the readout perimeter, async delta-stream, optimal-transport renderer, advancing abstraction front), §6.6.4 (bisector compute-graph node + projector link network), §7.7 (closest-inverse), §9.6 (python-native trees), §9.8 (port schema), §15.9 (instance inheritance), §8.2 (halo), §7.5 (play/pause); anti-goal §18.32.
- `USER_REQUIREMENTS_VERBATIM.md` §M (the verbatim source + canonical ASCII) + §P (the cascaded-rollout / readout-perimeter / bisector-node extension, 2026-06-06).
- Peers: `concept_view.md`, `field_tree.md`, `compile_collapse.md`, `halo.md`, `editor.md`, `agent_and_rollout.md`, `gesture_gateway.md`, `workspace_store.md`, `repl_mirroring.md`.
