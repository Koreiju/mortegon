# GOAL — The Black Markdown Slate (2026-06-13)

> **Status: GOAL / binding design.** Source: the user's `/goal` directive of 2026-06-13 (verbatim
> in `USER_REQUIREMENTS_VERBATIM.md` §T, refining §S.4/§S.5). This is an **original, self-contained
> solution** written from first principles against the requirement and the *actual current code* —
> not assembled by deferring to the design suite. The design docs (`DOMAIN_MODEL.md`,
> `docs/frontend/`) are treated as evidence of **intent that has not yet produced the right result**;
> they are reconciled to this spec (§12), not cited as the answer. The **verbatim requirements**
> (`USER_REQUIREMENTS_VERBATIM.md` §A–§T) *are* the source of truth and are cross-referenced
> throughout — including the many details earlier drafts of this goal missed (this revision folds in
> §M/§N/§O/§P/§Q/§R that bear on the slate).
>
> User's framing: *"We need a complete and original solution to this problem, not hiding behind
> what's already prima-facie in the codebase."* So this doc commits to a concrete grammar, gesture
> set, anchoring model, signal model, and strip/rebuild order.

---

## 0 — The Goal In One Paragraph

A card on the 2D editor is **one black slate**: a single editable text surface that renders the
underlying node as **one pure-print text tree** — thin silver border, completely black fill, serif
white text, **no chrome whatsoever**. There are no separate name/description/value/rendering widgets;
structure is recovered by *parsing the text* over **tabs and newlines only**, never by distinct DOM
fields. The structured datablock with its hard types lives **only under the hood** (the backend
record); the slate is its text projection, edited as a blended, borderless cursor field, round-tripped
text → parse → record → re-print. The design thesis is **recursive minimalism with memory-function
maximalism** (R.3): the slate shows the **rank-1** surface (N.14 — rank-1 minimalism is a *pro*-pattern),
and all depth — linked objects, function I/O, per-sample distributions — is folded away into memory
references (`{ref}` tokens, the only markup) and the 3D Real register. A node and a panel are the
**same record at two sizes**: a *singular-field* primitive **is** a computation-graph node; a
non-singular aggregate **is** a knowledge panel that compiles to the graph; the two representations
**commute** losslessly (R.1, N.2, O.19). Two reciprocal in-card gestures move structure across the
boundary: **internalize** (inline a `{ref}`'s target subtree) and **externalize** (lift a subtree into
its own node, leaving a `{ref}`) — applied identically to **API-object links** and **computation-graph
links**. The apparition **halo** must (a) paint *above* the slate, not behind it, and (b) track the
focal token as the slate scrolls/drags/resizes — two independent fixes. The whole frontend is stripped
to deliver this; every backend route, frame, and lifecycle hook is preserved unchanged.

---

## 1 — What Is Actually There Now (code-grounded; the thing to fix)

Fresh read of the served frontend — `backend/templates/index.html`, `backend/static/css/styles.css`,
`backend/static/js/chunk_projector.js` → `cp/*.js` (≈14,550 lines / 20 modules).

### 1.1 The card is four discrete widgets, not one slate
`cp/concept_graph.js` builds every card as a fixed skeleton
([`:1642`](backend/static/js/cp/concept_graph.js:1642)): `name-input` (:1644), `desc-input` textarea
(:1645), `value-input` textarea (:1647), `value-print` `<pre>` (:1652), `compiled-preview` div (:1653),
hidden compile/inverse buttons. Only `value` got a partial pure-print pass (`_fieldTreePrint`,
[`:1574`](backend/static/js/cp/concept_graph.js:1574)); `name`/`description` stay always-on fields and
`rendering` is a separate preview. The stuck-chunk panel (`cp/billboard.js`) is worse: a scanned
sample renders as **labelled sections** — `billboard-html`, `billboard-rendered-text`,
`billboard-fields`, page summary, media, xpath, source link
([`billboard.js:64`](backend/static/js/cp/billboard.js:64), [`:711`](backend/static/js/cp/billboard.js:711)).
The one natural text-tree (the content-structure summary `{xpath : values}`) is fractured across
boxes. This is T.1/T.2 and contradicts **E.2** (data-block components removed entirely) directly.

### 1.2 The background is not purely black
`body` is black, but over it sit the retrieval `#sidebar` + looping **`sidefall.mp4` + glass**
([`index.html:361`](backend/templates/index.html:361)) — already conceded as "known non-black residue"
yet shipped, and §S.3 marks the whole sidebar an anti-pattern — the translucent `#history-sidebar`
([`index.html:386`](backend/templates/index.html:386)), off-black tokens `--surface-elevated #0c0e10`/
`--surface-hover #15181b` ([`ui_utils.js:18`](backend/static/js/cp/ui_utils.js:18)), and dead rainbow
keyframes ([`ui_utils.js:15`](backend/static/js/cp/ui_utils.js:15)).

### 1.3 The theme fights itself (serif vs VHS monospace)
`initMaroniteTheme` forces VHS monospace `!important` on every `input`/`button`
([`ui_utils.js:41`](backend/static/js/cp/ui_utils.js:41)), while the slate (§S.4) and the card's inline
styles use Georgia serif — so the name input renders monospace and the body serif within one card.

### 1.4 The halo — TWO independent bugs (T.4, corrected)
The user is explicit: *"The slate is scrollable and the halo is behind the slate. These are two
independent factors."* They are:

1. **Z-stacking — the halo paints behind the slate.** The halo overlay is created with
   **`z-index: 9985`** ([`concept_graph.js:4010`](backend/static/js/cp/concept_graph.js:4010)) while
   every card is **`z-index: 9990`** ([`:1624`](backend/static/js/cp/concept_graph.js:1624)).
   `9985 < 9990` → phantoms near the focal are occluded by the card. Pure paint-order; nothing to do
   with scroll. *Fix:* the open halo's overlay (and its phantoms) must sit **above** the focal slate
   (and ideally above all cards while open), with `pointer-events:none` on the layer and re-enabled on
   phantoms.
2. **Anchor — the halo does not track the scrollable slate.** The slate has a scroll region (the
   pinned panel's body `overflow:auto`; `.ks-pre{max-height:180px;overflow:auto}`,
   [`index.html:214`](backend/templates/index.html:214)). `_populateHalo` anchors to a *once-computed*
   `focalCard.getBoundingClientRect()` ([`:4042`](backend/static/js/cp/concept_graph.js:4042)) and
   re-anchors **only on `window` resize** ([`:4026`](backend/static/js/cp/concept_graph.js:4026)) —
   never on the slate's internal scroll, the card's drag, or per frame (whereas link edges/arrows
   re-project every frame). *Fix:* anchor to the live rect of the **focal token** (the field that
   opened the halo) and re-anchor on the slate `scroll`, card move/resize, viewport resize, and the
   shared rAF tick while open. (Residue: phantom-style comment still says "dashed blue / solid green",
   [`:4079`](backend/static/js/cp/concept_graph.js:4079), pre-§O.16.)

**Diagnosis.** The frontend was *retrofitted* toward the slate (serif, black fill, header removed)
over a form skeleton. A slate is not a form with chrome hidden — it is a different object (one text
buffer ↔ one record). The retrofit cannot converge; a clean strip + rebuild (T.8) is right.

---

## 2 — The Organizing Thesis & The Node≡Panel Identity

**Thesis (R.3): recursive minimalism with memory-function maximalism.** Every surface is the
*minimal* text that conveys the rank-1 structure; everything beyond rank-1 — object models, function
I/O, per-sample distributions, subgraphs — is **maximal under the hood**, reachable by reference and
by gesture but never shown unsolicited. **Rank-1 minimalism is a pro-pattern (N.14):** the 2D node
deliberately stays at rank-1; the full per-sample distribution and deep object model live in the 3D
Real register (O.7) and are *folded* in 2D until the user reveals them.

**The node≡panel identity (N.2, O.19, R.1, C.6/C.7).** A slate has exactly one underlying record. Its
representation is decided by its **singular-primitive aspect**:
- a **singular-field primitive** (one field/value) **IS a computation-graph node** (rendered as the
  value-only black slate);
- a **non-singular aggregate** (multiple fields) **IS a knowledge panel** that *compiles to* the graph.

Authoring may **begin in graph form** (N.2). The panel↔graph dialectic must **commute (R.1):** an edit
made in either representation round-trips losslessly into the other, and flipping representation order
never changes the record. Field-tree growth *is* promotion — adding a row to a singular node makes it
an aggregate; there is no separate "promote to panel" affordance (E.3, E.4). This identity is why
internalize/externalize (§5) is the *only* structural operation: it moves a subtree across the
node/panel boundary while preserving the record.

---

## 3 — The Slate Grammar (the "specialized editor-specific syntaxes", T.5)

**Structure is carried by tabs and newlines ONLY (N.7).** There are no key/value/type punctuation
*requirements*; the parser discerns the tree purely over `\t` + `\n`. Consequences:

- **Names may contain spaces (N.7, N.10).** `scan for duckduckgo url` is one node name. The parser
  never splits on spaces.
- **`{ref}` is the ONLY markup (N.10, O.2).** A `{name}` token = *an activation of a memory-access
  procedure elsewhere in the app* — a link to another node/instance. The text **beside** a `{ref}` is
  an **optional organising label**, not part of the reference. No JSON braces, HTML angle brackets,
  YAML dashes, or quotes ever appear in the slate.
- **A new field's on-ramp is `name {}` (O.20)** — a key beside a singular empty `{}` (the unbound ref
  slot), exactly how the scanner represents functional-objects (`url {}`, `dom {}`).
- **Key-value vs multiline is inferred by consistent tabs, no syntax markers (O.20).** Within a parent,
  a child with an inline value is key-value; a child whose value is the consistently-tab-indented block
  beneath it is multiline (its key is the primary key to that block). Multiline values absorb into the
  parent indent — **no escaped-`\n` glyph is ever printed**.

The canonical regions are recovered **by position**, not by separate fields: the **name** is the
title (the column-0 line); the **description** is the prose beneath it before the first structured
row; the **data** is the indented tree; the **rendering** is the read-only compiled tail. `{ref}`
linking is honoured in **all** of these regions (C.9 — name, description, data, rendering). Compiled
child slates drop even the title (D.2 — value only; name implicit from position).

**Typed vs type-stripped rendering (M.3 vs N.5 — a hard distinction):**
- A **raw materialised API object** (WebBrowser/Database/Agent and their property/function trees,
  §F.5) renders **typed**: `key : Type = value`, e.g. `driver : WebDriver = {driver}`. Read-only (🔒);
  the function body is never projected as a data block (F.6).
- A **user compute node** renders **type-stripped**: purely structural over `\t`+`\n`, each line a
  literal, an optional label, or a `{ref}` — *no types shown* (N.5). Types/I/O persist **internally**
  for inverse lookup, but are not presented (rank-1 minimalism, N.14).
- Type inference is **joint (O.15):** top-down from the API ontology where a field binds to a
  materialised node (O.8), bottom-up from wiring/value for unbound slots, with ontology sharpening
  in between. No single direction is exclusive.

**Markdown editor gestures restructure the graph (R.5, N.12).** Editing the text with **dashes,
tabs, numbers, and newlines-with-trailing-text** restructures the computation graph (the other side
of the dialectic) accordingly — `Tab`/`Shift-Tab` re-parent; `Enter` adds a sibling; `Shift-Enter`
is a soft newline inside a value; `- ` / `1. ` make positional (keyless) children. Multiline editing
uses **smart Shift-Enter / Tab auto-indent like a markdown editor** (N.12) so multi-`{ref}` templates
stay manageable. These gestures are the realisation of E.3's `+→`/`+↓` field growth — keystrokes, not
buttons.

**Editing is borderless and blended (M.8).** A single-left-click on a printed token opens it for edit
**in place** as a cursor-blinking field that is *otherwise fully blended into the slate* — "a purely
smoothed text editor without special borders around each selective and interactive token." The caret
lands where the click fell. `Enter`/blur commit (cascade fires on commit, not per keystroke);
`Shift-Enter` soft-newline; `Esc` discards. Read-only tokens refuse edit (no-op highlight).

**Visual contract (pure black, T.1, §S.4).** One CSS rule for the pinned panel, the editor card, and
the value-only node: `--slate-fill #000` (no greys, glass, or video), `--slate-border #c0c0c0` (1px
rest / 2px focus, no shadow/glow/blur), `--slate-text #fff` **serif** (one font, no monospace/VHS).
The only filled colour in the app is the 3D chunk HSV; the only 2D non-silver stroke is the one yellow
2D↔3D connector (I, O.16).

---

## 4 — Under-The-Hood: text ↔ record, brace states, commutativity

"Data block connections (only under-the-hood)" (T.6) = `ConceptEdge` rows between records, surfaced in
the slate *only* as `{ref}` tokens (N.10). Committing a slate edit POSTs the **printed text** (never
JSON); the backend parses it, diffs the record, reconciles edges for every `{ref}` (create on
appearance, delete on removal), persists (JSON internally — never surfaced), and broadcasts
`concept_changed`; the slate re-prints from the authoritative record (even the user's own edit
round-trips; an optimistic echo hides latency). The slate's parser and the backend's decomposition
agree on the tree, so panel↔graph **commutes (R.1)**.

**The three brace states (O.1a) — one underlying edge, three renderings:**
1. **Braced-hidden** — `{name}`; target's rank-1 links not yet revealed. Hover previews; reveal
   instantiates.
2. **Revealed-internal** — the target's rank-1 fields are unfolded inline (panel) / its walk is
   instantiated (graph); braces drop on the revealed node (its children may stay braced).
3. **Resolved-external (solid link)** — the target is a node already visible elsewhere on the canvas;
   drawn as a **solid undirected line** to it (no arrowhead, O.16) instead of re-revealing inline.

Graph form has **no independent fold state** and stays in **node-count parity** with the panel —
revealing in one reveals in both (O.1). Links are **undirected lines; hard/soft differ by brightness +
weight only; no arrowheads anywhere** (O.16).

---

## 5 — In-Card Gestures: Internalize / Externalize (T.7 — the core synthesis)

The user asked specifically to *"make note of in-card gestures to internalize and externalize API
object links **and** computation graph links."* **Internalize and externalize are one reciprocal pair
on a link, and they are the only way structure crosses the node↔panel boundary.**

> A link is a hidden subtree. **Internalize** = pull it *into* this slate inline.
> **Externalize** = push a subtree *out* into its own node, leaving a `{ref}` behind.
> They are lossless inverses (R.1) and move a node between the three brace states (O.1a).

| Operation | Text effect | Record effect | Applies to |
|---|---|---|---|
| **Internalize** a `{ref}` | `{name}` → `name` + target's rank-1 children indented beneath (braced-hidden → revealed-internal) | none structural — reveals the existing edge's target rank-1 (N.8) | API-object links AND compute links |
| **Externalize** a subtree | `key`+subtree → `key : {newname}` (braced-hidden) | new node created from the subtree; parent's edge repointed at it (E.1: child keyed `<panel_id>__<key>`) | API-object links AND compute links |

**On the two link kinds the user named:**
- **Computation-graph links** — `{ref}` to another user/compute node. Externalizing the *whole* slate
  is the panel→graph compile (M.7); internalizing a graph node back is graph→panel. Same reciprocal
  pair.
- **API-object links** — `{ref}` to a materialised python object/property/function (read-only, typed).
  Internalize unfolds the object's next rank of typed structure inline, recursively (M.3, M.4: e.g.
  `driver : WebDriver = {driver}` → `command_executor : str = …`, `options : … = None`, …).
  Externalizing onto an API subtree creates a **duplicate-instance proxy** (N.6): a rank-1 component
  that proxies operational calls to the origin and **inherits its I/O types + object model** (N.4) —
  so a user node carries the real signature without copying source. Function output types are inferred
  from input-on-the-right / output-on-the-left equality (M.5, E.6); an unbound input with a known
  output triggers **closest-inverse lookup** (E.6, §7.7).

**The full gesture surface (mouse + keyboard), for the slate:**

| Gesture | Target | Effect | Verbatim |
|---|---|---|---|
| **Single left-click** | a printed token | edit in place — borderless blended cursor field | M.8 |
| **Right-click** | a `{ref}` / typed field | **internalize ⇄ externalize-inline**: toggle the target's rank-1 fold, fold-state preserved | M.6, N.8, O.1 |
| **Right-click** | the title / self line | **rank-dominance collapse**: fold the whole slate to its title (value-only node), hiding its dominated subtree; re-expand restores fold state | M.6, S.5, Q.3/Q.5 |
| **Double left-click** | slate body (not a token) | panel ⇄ graph (externalize-all / internalize-all), symmetric | M.7, C.7 |
| **Left-click-drag** | token → node (graph) / → field (panel) | externalize as a wired link; target inherits source I/O types + object model | N.4, N.6 |
| **Double right-click** | a `{ref}` / instance | delete that link/instance (record edge removed) | N.13 |
| **Hover** | a token | transient next-rank preview (no commit); opens the halo on text fields | M.4, O.3 |
| **Type `{`** | a value / new key | autocomplete over node names (scoped to a python-bound object's properties/functions when inside one); selecting inserts `{name}`; unknown name auto-creates the node | E.5, §9.1 |

**Fold-state preservation (M.6, extremely important):** internalizing then collapsing then
re-expanding restores the *exact* prior inline depth per subtree. A reset-to-collapsed on every toggle
is the anti-goal. Non-collision: single-left targets a token interior (edit); right-click the same
token (fold); double-left targets body outside tokens (compile); drag is press-move-release between
nodes (wire); double-right deletes. Read-only API nodes refuse single-left edit but allow
hover/right-click/drag exploration.

**Rank-dominance collapse is one generalized gesture in 2D and 3D (Q.3/Q.5/S.5).** Right-clicking a
*dominator* (a root-url node, a bisector compute-graph node, or any panel's self line) collapses its
**rank-dominated descendant set** — in 2D it folds to the value-only node; in 3D it hides every
dominated chunk/readout except the dominator, re-expandable by a second right-click. Rank-dominance is
the structural containment/reachability ordering over the `ConceptEdge` graph; it is *aligned with but
distinct from* the PageRank term of retrieval (Q.6 finding: PageRank is the collapse-onto heuristic;
the dominated set defines collapse membership).

**The Database node is special (O.5):** it exposes its **rank-1 ontology nodes**, walkable recursively;
the user **keeps/deletes** ontology fields (double-right-click, N.13) per query, and the kept set
**assembles a cypher query** built from multiple semantic-retrieval runs — so retrieval halos
*discover new cypher fields* on the very same node that runs `Database.search` and `Database.cypher`
(F.2). Internalize/externalize on the Database slate has this cypher-building semantics.

---

## 6 — Signal-Stream: per-sample iteration & the 2D↔3D reference (N.9, O.6/7/11/12/14/19)

A rank-1 node may reference an **iterable** (e.g. `chunk {chunk samples}`). The slate must render this
minimally:

- **One readout node cycles the signal (N.9, O.11).** When an iterable is rendered, the slate shows
  **only the current sample's content** in a single readout — never an `"iteration 3 of 12: [c1,c2,c3]"`
  overlay (an anti-goal). The full position is legible only in the REPL viewer's signal row.
- **Iteration applies ONLY on external `{ref}` to a recursively-chunked iterable (N.9, O.19).** Inline
  content is *not* iterated. The iterable is rooted at its base node; a referencing panel **dynamically
  updates from the root down to its fields** as the root changes (O.19).
- **Chunks live in 3D; the 2D holds a reference (O.6, O.7, O.12).** The full per-sample distribution
  streams into the 3D Real register; the 2D node stays rank-1 and its `{chunk samples}` is a reference
  *into* the 3D-resident set, not a copied duplicate. Advancing the 2D signal **flies/highlights the
  corresponding 3D chunk** (one-way 2D→3D drive). The generative readout is a type-stripped 2D rank-1
  node + a 3D distribution (O.12).
- **Sample source (O.14, corrected):** the current instance's content is rendered per-instance from a
  memory queue, sourced **either** by sampling a chunk from the 3D env **or** by halo-retrieval +
  selection; deleting a halo result advances to the next-most-similar sample (O.18). Content *is*
  rendered for the current sample (not bare references) — superseding the over-strict "references only"
  framing.

This is the §P recurrent procedural renderer at the slate layer: the readout perimeter (the
outermost nodes with no succeeding links, R.4/P.3) projects into 3D as clean-text panel renderings;
the bisector compute-graph node (P.10) is the 3D handle that opens/closes the editor graph.

---

## 7 — The Halo (gating, transport, scoring) — and the two T.4 fixes

**The empty primitive radiates the halo as you type (D.3).** A fresh slate is the universal empty
primitive; as the user types description/value, those fields embed and retrieval radiates candidates
around the focal. Selecting a candidate wires the link (soft→hard) and may autoregress (D.3, §8.2.2).

**Gating (O.3).** A halo opens only from a field carrying **rendered literal text** (a blank /
in-progress *text* field counts). A **pure-`{ref}`** field opens *no* halo (already bound). A field
mixing text and `{ref}` queries the **whole resolved field** (the text + the resolved ref content).

**Name-only phantoms (D.1).** Each phantom shows the candidate's **name only** — no score chips, no
preview; scores live in slow-hover tooltips.

**Cone-ray transport (O.18).** The focal 2D element is the apex of a cone; halo-visible 3D nodes are
transported along it by **retrieval similarity** (the triple product) — normalized similarity sets both
radial and along-ray distance (more similar → nearer the apex); angular placement is the projected
intersection along the shared cone normal (camera-dependent); transported phantoms carry the chunk's
HSV/image and rotate with the camera.

**Panel-chunk scoring deviates (O.22).** When the halo retrieves over **rendered panels / subgraphs**
(not raw scan chunks), embed the same render for **both** nomic and TF-IDF and rank by
`pagerank · max(minmax(nomic_cos), minmax(tfidf_cos))` (each cosine min-max normalized to [0,1] over
its own distribution *before* the max). Scan chunks keep the separated axes (description→nomic,
rendering→TF-IDF; A.6/D.4). This lets search over data space blend with search over the space of
computational tasks (functional-objects + subgraphs are embedded too).

**The two T.4 fixes (independent):**
1. **Z-order:** the open halo overlay + its phantoms must paint **above** the focal slate (raise the
   overlay z-index above the cards; keep `pointer-events:none` on the layer, re-enabled per phantom).
2. **Anchor/scroll:** anchor to the live **focal-token** rect (not the static card rect) and re-anchor
   on the slate `scroll`, card drag/resize, viewport resize, and the shared rAF tick *while open* —
   the same cadence the edges/arrows already use. The phantom *set* refetches only when the query text
   changes; scroll-tracking is pure geometry. This also satisfies §S.5 ("a collapsed node keeps its
   halo proximal") — a collapsed slate is a one-line focal token the halo anchors to.

---

## 8 — Pure Black (remove every non-black 2D source)

Remove: the retrieval `#sidebar` + `sidefall.mp4`/`waterfall.mp4` + glass (§S.3), the
`#history-sidebar` timeline, the off-black `--surface-elevated`/`--surface-hover` tokens, the rainbow
keyframes, and the VHS-monospace `!important` rules. Keep one black ground + the `--slate-*` contract
(§3). After the strip, every 2D pixel is black / silver / serif-white / (the one) yellow connector;
the only filled colour anywhere is the 3D chunk HSV.

---

## 9 — Backend Links To Preserve (T.8 — "leave backend links perfectly intact")

The strip touches **only** `backend/static/*` + `backend/templates/index.html`. No backend edit is in
scope. The contract the rebuilt slate keeps speaking (138 routes in `backend/api/routes.py`; ≈70
consumed), grouped:

- **Records & edges:** `GET/POST /api/concepts`, `/api/concepts/{id}`, `/api/concept_edges`, `/api/edges`,
  `/api/foundation/ensure`.
- **Scan & chunks:** `/api/snapshot`, `/api/scan_status`, `/api/chunk_nodes`, `/api/chunk_details(_batch)`,
  `/api/chunk_search`, `/api/image_proxy`, `/api/map/snapshots`. (Timed scan: the `web_query` `duration_s`
  exposed port, Q.2/§15.10.)
- **Retrieval & halo:** `/api/apparitions`, `/api/radiation`, `/api/closest_inverse/{id}`,
  `/api/ontology/layout`, `/api/ontology_walk/`, `/api/pattern_instances/`.
- **Compile & compute:** `/api/conceptual/compile`, `/api/compile_pipeline`, `/api/compute_graph/layout`,
  `/api/recompute_umap`.
- **UI mirror (every gesture):** `/api/ui/{pin,unpin,hover,hover_rect,select,collapse,latch,edit_open,
  edit_close,compile_expand,compile_collapse,dominance_collapse,node_fold,halo_focus,halo_clear,
  halo_chain_push,halo_chain_clear,autocomplete,autocomplete_clear,signal_advance,signal_stream,
  signal_stream_clear,url_visibility,viewport_spine,register_billboard_url,pin_chrome,telemetry}`.
- **Agent & rollout:** `/api/agent/{spawn,tick,fork,tokens/,cascade_status,reviews/resolve}`,
  `/api/rollout/{play,pause}`.
- **Evolution & ws:** `/api/evolution_log(/rollback)`, `/api/health`, `WS /api/ws/workspace/{id}`,
  `WS /api/ws/nodes/{id}`.

The rebuilt frontend keeps the **one-way data-flow seam** (WS frames → store → slate; gesture →
gateway → route → frames) and computes no UMAP/embeddings/PageRank/compile (backend-owned). REPL
mirrors of frontend mutations are the only hard-verification of frontend behaviour (R.8, J.1).

---

## 10 — The Strip-And-Rebuild Plan

**Principle:** strip the view layer to zero; keep the backend contract whole; build the slate fresh
from §2–§7. `cp/*.js` and the partial greenfield `_legacy_frontend/fe/` are **API-seam reference only**,
not a card design to port.

### 10.1 Remove (view layer only)
- `backend/static/js/cp/*`, `backend/static/js/chunk_projector.js`.
- The form/section markup + inline `<style>` + `#sidebar`/`<video>` + `#history-sidebar` in `index.html`.
- `sidefall.mp4`, `waterfall.mp4`, the VHS font, rainbow keyframes; the sidebar/section/chrome CSS in
  `styles.css` (keep `--slate-*` + black ground + projector canvas).

### 10.2 Keep (untouched)
- The entire `backend/` Python tree (routes, services, lifecycle, scanner, layout, retrieval, compile,
  agent, persistence, WS frames).
- The `--slate-*` tokens + black ground; the 3D projector behaviour (chunk HSV is the only colour),
  re-expressed in the new module.

### 10.3 Build (the minimal view), in order
1. **Seam** — one inbound `FrameBus` (WS → normalized store) + one outbound `Gateway` (gesture →
   route → frame); store is the only truth; views own only transient interaction state.
2. **Slate core** — `print(record) → text` / `parse(text) → delta` on the §3 grammar (tab+newline
   tree, names-with-spaces, `{}` on-ramp, kv-vs-multiline-by-indent, typed vs type-stripped), with a
   **round-trip identity** test, and the borderless blended click-to-edit overlay (M.8).
3. **Gestures** — the §5 internalize/externalize + edit + compile + delete + autocomplete +
   rank-dominance collapse set, firing the §9 `/api/ui/*` mirror routes; fold-state preserved (M.6).
4. **Signal-stream** — the §6 single-readout iteration + 2D↔3D reference + signal-advance drive.
5. **Projector** — the 3D canvas + scan-streaming + texture cache (only filled colour); the bisector
   compute-graph node (P.10); rank-dominance collapse in 3D (Q.3/Q.5).
6. **Membranes** — hover→pin (stuck chunk → slate of its content-structure tree at the frozen rect,
   C.2), the halo with **both** §7 fixes, the silver undirected link layer + the one yellow 2D↔3D
   connector.
7. **Pulse** — one rAF loop driving edge re-route, halo re-anchor, tweens, keyed reconcile.

### 10.4 Order of work
Doc-first (this goal + §12 reconciliation) → seam + slate core (round-trip green) → replace card path
(one slate per node; stuck chunk = content-structure tree) → gestures + signal-stream → projector +
membranes + halo fixes → strip dead surfaces → REPL/scenario verification (a later pass; this turn is
analysis + design only).

---

## 11 — Acceptance Criteria

1. **One editable region per card.** DOM audit finds zero `concept-name-input`/`-desc-input`/
   `-value-input`/`-compiled-preview`/`billboard-html`/`-rendered-text`/`-fields`. Each card is one slate.
2. **Pure black.** No `<video>`, no `#sidebar`/`#history-sidebar`, no off-black tokens, no VHS/rainbow.
3. **Print/parse round-trip identity** on the §3 grammar — incl. **names with spaces**, the `name {}`
   on-ramp, kv-vs-multiline-by-indent, typed API vs type-stripped user nodes.
4. **A stuck chunk** is one content-structure text-tree (the "panel summary"), with
   html_raw/rendered_text internalizable under `{ref}`, not permanent sections. For **HTML** chunks
   this tree is the **deduplicated content tree** specified exactly in
   [`HTML_DEDUP_CONTENT_TREE_GOAL.md`](HTML_DEDUP_CONTENT_TREE_GOAL.md) (§U) — that doc's golden I/O is
   the binding test for the chunk slate body, and it realises the §E.1 HtmlStrategy.
5. **Internalize/externalize round-trip is lossless** and **commutes** (R.1) on API-object and
   compute-graph links alike; fold state persists across collapse/re-expand (M.6).
6. **Rank-1 minimalism holds (N.14):** the 2D node rests at rank-1; deeper structure appears only on
   internalize; iteration shows one readout sample (N.9), never an "N of M" overlay.
7. **The halo (both factors):** paints **above** the slate (no occlusion) **and** tracks the focal
   token through slate-scroll, card-drag, and resize.
8. **Backend untouched:** every route/frame/lifecycle in §9 responds exactly as before; the diff is
   confined to `backend/static/*` + `index.html`.

---

## 12 — Doc-Reconciliation Ledger (make the docs reflect this, per the user's ask)

§T is the verbatim. These existing-doc statements **contradict the slate and must be reconciled to
this spec** (residue from before §S/§T):

| Doc | Stale statement | Reconcile to |
|---|---|---|
| `DOMAIN_MODEL.md` §4.2 | pinned panel has "minimise, close (×), Compile" chrome | no chrome (§4.1.2 / §S.4); compile/collapse are gestures |
| `DOMAIN_MODEL.md` §4.4 | "latch button … between resize and close" / slide-out data panel | no buttons; data is *in* the slate; internalize/externalize replaces latch |
| `docs/frontend/concept_view.md` §2/§4 | four canonical rows as a body skeleton; "four foundation fixtures (… Editor)"; close-button/latch rules | one slate (one text region); **three** fixtures (Editor removed, §S.1); no buttons |
| `docs/frontend/halo.md` | anchored to focal panel centre; re-populate on resize only | anchor to focal **token** rect; raise z-order above slate; re-anchor on rAF/scroll/drag (§7, T.4) |
| `docs/frontend/theme.md` §11 | `sidefall.mp4` "retained … the one non-black 2D element" | removed; pure black, no video/sidebar (§S.3) |
| `docs/frontend/retrieval_and_sidebar.md` | a retrieval sidebar surface | removed; in-editor halos are the only retrieval surface (§S.3) |
| `object_model/Editor.md` | the Editor fixture | deprecated (§S.1); gestures intrinsic to the slate |
| `field_tree.md` / `object_exploration.md` | colon/JSON-leaning parse; types on user nodes | tab+newline-only tree, names-with-spaces (N.7); user nodes type-stripped (N.5); `{}` on-ramp (O.20) |

These are targets for the doc-first trickle-down, on the user's go-ahead — executed explicitly, not by
treating those docs as the design.

---

## 13 — Verbatim Coverage Map (the §A–§T details this goal now carries)

So nothing load-bearing is dropped again: **C.7/C.9** (`{ref}` spans all sections; panel↔graph
right-click) → §3/§4; **E.1–E.11** (recursive compile, data-blocks-removed, plus-sign growth,
name+value singular/multiline, autocomplete scoping, function I/O inference, play/pause rollout,
recursive chunking, diff-consistent samples, token streaming, intermediate nodes visible) → §2/§3/§5/§6;
**F.5/F.6** (Object/Property/Function trees; read-only sentinel) → §3/§5; **M.1–M.11** (reservoir
readout, singular-value translation, typed base form, hover/right-click fold, borderless edit, halos on
blank, instance inheritance) → §2/§3/§5/§7; **N.1–N.14** (OO DOM types, node≡panel, external-ref
propagation, left-drag inherit, type-stripped structural render, duplicate-instance proxy,
names-with-spaces, rank-1-in-2D/full-in-3D, selective unfold, per-sample only-on-external-ref,
`{ref}`=memory-access, smart markdown parse, double-right delete, **rank-1 pro-pattern**) → §2/§3/§5/§6;
**O.1–O.22** (brace states, halo gating, long-field truncation, Database cypher, 2D↔3D stepper, type
abstraction joint, lazy reveal-as-walks, no arrowheads, cone-ray transport, `{}` on-ramp, panel
embedding deviation) → §3/§4/§5/§6/§7; **P.1–P.12** (cascaded recurrent renderer, readout perimeter,
bisector node, abstraction front) → §6; **Q.1–Q.6** (all-real, timed scan port, rank-dominance collapse
in 2D+3D) → §5/§9; **R.1–R.9** (commute the dual representation, full DB ontology in 3D, recursive
minimalism + memory maximalism, peripheral-only output, markdown gestures restructure the graph,
external memory via `{ref}` + inverse maps, signal rendering over iteration, REPL-only verification,
db janitor) → §2/§3/§5/§6.

---

## 14 — Traceability

- Verbatim source: `USER_REQUIREMENTS_VERBATIM.md` §A–§V (this goal cross-references the binding
  details; §T/§U/§V are the 2026-06-13 directives).
- This doc is the **authoritative design** for the rebuild; where it diverges from the design suite,
  this doc wins and the suite is reconciled (§12).
- Verification is the REPL / scenario harness (§V mandate); the §V matrix (§15) tracks build status.

---

## 15 — §V Refinements: Circular Minimal Node, Halo Ray Mechanics, Streaming SLA, Verification Matrix

The §V directive (2026-06-13) adds three engineering refinements and a verify-against-the-live-stack
mandate. They sharpen, not replace, §2–§7.

### 15.1 The computation node is a CIRCLE showing only the root-most field (V.5)
A computation-graph node renders as a **circle whose only text is its root-most field** — the
value-only collapsed slate (§C1 / D.2), now explicitly *circular*. **No title, no upper bar, no
buttons** — a black-fill / silver-outline disc with the single root field in serif white. This is the
graph-form pole of the node≡panel identity (§2): the panel is the rectangular aggregate slate; the node
is the circular singular primitive; double-left flips between them. Multi-line root values grow the
circle to fit; everything below rank-1 is folded (a `{ref}` is one glyph on the disc, hover/click
reveals). The circular node is the minimal terminus of "recursive minimalism" (R.3).

### 15.2 Halo ray-projection: constant-similarity ray, dynamic along-line slide, updating angle (V.4)
Refines §7 / O.18. The auto-halo retrieves and **ray-projects** each retrieved 3D node toward the
**sticked panel** as the apex. Three mechanics made explicit:
- **Constant retrieval-similarity ray** — each retrieved node rides a ray whose *similarity is fixed*
  (the triple-product value); the node's position along the ray *encodes* that constant similarity.
- **Dynamic along-line sliding** — as the scene/camera moves, the node **slides along its ray** to
  preserve the constant-similarity mapping (more-similar = nearer the apex), so the depth cue stays
  truthful frame to frame.
- **Updating ray angle** — the **ray angle updates continuously as it is traced between the sticked
  panel and the retrieved node**, which is rendered in **collapsed computational-node form** (the §15.1
  circle). So a halo phantom is a circular collapsed node on the far end of a live, angle-tracking,
  constant-similarity ray. This is the precise form of the §7 cone-ray transport + the two T.4 fixes
  (the ray must paint above the slate and re-anchor to the focal token every frame).

### 15.3 Gestures define transformations/navigations between representations (V.5)
Every right / left / double click is a **transformation or navigation between representations**, not a
chrome action (there is no chrome). The three representations and the moves between them:
```
   KNOWLEDGE PANEL  ⇄  TEXT-TREE FIELD  ⇄  CIRCULAR NODE
   (rect aggregate)    (markdown tree)     (singular, root-field-only)
```
- single-left = edit a text-tree token in place (borderless, M.8);
- right-click a `{ref}` = navigate the **hidden link inside the text-tree entry** (internalize/
  externalize, §5) — "click gestures help navigate the hidden links within a text-tree entry";
- right-click self / dominator = collapse to the circular node (rank-dominance, §5);
- double-left = panel ⇄ graph (rect aggregate ⇄ circular node), symmetric;
- double-right = delete a link/instance.
Custom syntax parsing (the §3 grammar) + these gestures ARE the editor; nothing else.

### 15.4 Streaming SLA (V.1) — backend pipeline, must hold, do not touch bookkeeping
- The **full set** of scanned chunks streams to the frontend **real-time** and updates **live**.
- **Scan emission is millisecond-scale** (mutation-observer driven); the **initial UMAP** may take a
  few seconds, but **UMAP update frames pushed to the frontend must be in the seconds-to-milliseconds
  region**.
- **Do not interfere with the scanner's chunk bookkeeping mechanics** (stable integer chunk ids §B.5,
  the id→coord lookup, the dedup-logging accounting). The dedup *content tree* (§U) is a **rendering**
  derived from the already-bookkept chunk; it must not alter chunk identity, counts, or ordering.

### 15.5 Existing content-extraction ruleset is authoritative; dedup is additive (V.2)
The §U content tree **uses the existing content-detection ruleset** (the scan-chunk recursive-iterative
routines, `backend/dom/*`, `mapper/chunk_render.py`) to decide *what is content / a card*; the new work
adds **deduplication on top** and the **tree print**. It must **not deviate** from the current ruleset
or routines — every card the existing pipeline detects must still be scanned, retrievable, and now
rendered as the deduplicated recursive text. **All embedded media types** (V.3, noetic.org) remain
extractable exactly as today; the dedup tree surfaces their `src`/`href` as content lines (§U §2.1).

### 15.6 Verification Matrix (§V) — requirement → REPL surface → BUILD STATUS
Honest status as of 2026-06-13 (the slate/dedup/halo features are documented goals, **not yet built**;
verifying them requires building them first — A.4: a render is not proof):

| # | Requirement | REPL / probe surface | Status |
|---|---|---|---|
| V.1 | full chunk set streams real-time to UMAP; ms scans; sec-to-ms UMAP updates | `scan_streaming_routes_to_workspace_ws`, `live_scan_real_with_cleanup`, `watch-activity` | **EXISTS** — verify timing live |
| V.1 | no interference with chunk bookkeeping | `probe_live_scan_with_cleanup.py`, id-stability assertions | **EXISTS** — must stay green after §U |
| V.2 | all cards scanned + retrievable | real scan + `/api/chunk_search` count vs page card count | **EXISTS (extraction)** — verify completeness per site |
| V.2 | cards rendered as **deduplicated recursive text** (content tree) | `test_content_tree.py` (§U golden) + live real-fields | **BUILT + VERIFIED** — `backend/dom/content_tree.py`; byte-exact §U golden (6/6) + real Princeton card |
| V.2 | existing ruleset used; content deduplicated, additive | content_tree over the existing `fields`; `/api/chunk_details` derived | **BUILT + VERIFIED** — additive; no bookkeeping touched |
| V.3 | 5 sites (archive/tarot/noetic/yourchineseastrology/studycli), all media | per-site scan + content_tree dedup/clean assertions | **VERIFIED (content tree)** — archive(161)/tarot(24)/yourchineseastrology(54)/studycli(101) all clean+deduped, no xpath/HTML leakage; noetic media-extraction mechanism confirmed (+ open noetic-nav bug); data-URI compaction confirmed on real data |
| V.4 | halo: constant-similarity ray, along-line slide, updating angle, circular collapsed nodes | `halo-focus-roundtrip`, `apparitions?ray_project=1`, frontend render | **BACKEND EXISTS / FRONTEND UNBUILT** |
| V.5 | circular minimal node; gestures = representation transforms; no chrome | `magic_markdown*.test.mjs` (model/vdom/gestures) | **MODEL BUILT + VERIFIED (29 js tests)** / live mount pending |

### 15.7 Build progress (the magic-markdown panel, 2026-06-13 — bottom-up, verifiable)
The greenfield `fe/` tree is begun, model-first, each layer Node/py-tested (40 tests green):
| Module | Role | Test |
|---|---|---|
| `backend/dom/content_tree.py` | §U `fields_to_content_tree` dedup transform (additive, over existing `fields`) | `backend/tests/test_content_tree.py` 6/6 + live real-fields |
| `backend/api/routes.py` (edit) | `/api/chunk_details(+_batch)` emit derived `content_tree` | compiles; additive |
| `backend/static/js/fe/magic_markdown.mjs` | panel MODEL: parse/serialize (tabs+newlines, names-with-spaces), `{ref}`, `renderPanel` in-text dropdown ▸/▾ recursive expansion, per-signal iteration, `renderGraph` (circular text-only nodes, parity) | `magic_markdown.test.mjs` 18/18 |
| `backend/static/js/fe/magic_markdown_panel.mjs` | pure `panelVDom` (black-slate spec: dropdown-char spans, editable tokens, depth indent, **no chrome**) + thin `mount` glue | `*_panel.test.mjs` 5/5 |
| `backend/static/js/fe/magic_markdown_gestures.mjs` | `resolveGesture` — every L/R/double click → a transformation between representations (V.5) | `*_gestures.test.mjs` 11/11 |
| `backend/static/js/fe/integration.test.mjs` | the whole loop composed: render → gesture → fold → inline expand → collapse | 5/5 |
| `backend/static/js/fe/magic_markdown_panel.mjs` `graphVDom` | the computation-graph half: circular text-only nodes + undirected edges, parity | in `*_panel.test.mjs` 7/7 |
| `backend/static/js/fe/demo.html` (+ `serve_demo.py`) | a SERVED panel, **browser-verified, BOTH halves + transition** | live: black slate (bg #000, 1px silver border, serif white); ▸→▾ dropdown expands the referenced node inline; symmetric collapse; **double-toggle goes between markdown panel ⇄ graph form (4 circular nodes + 3 edges, parity) and back**; no chrome; no console errors |

**Browser-verified milestone (2026-06-13):** the served magic-markdown panel renders the content tree as a
black slate; the in-text dropdown CHARACTER expands an externally-referenced node (by its root field)
inline; and the editor **goes between** the markdown-panel and computation-graph (circular text-only node)
halves — all confirmed via DOM computed-styles + state probes in the live preview (not screenshot-as-proof).

| `backend/static/js/fe/store.mjs` | WorkspaceStore — frames→truth; `registry()` resolves `{ref}` by root field; `panelText`/`node` selectors | `spine.test.mjs` 9/9 |
| `backend/static/js/fe/gateway.mjs` | `buildRequest` (gesture → `/api/ui/*` + concept routes) + `GestureGateway` (folds frames) | `spine.test.mjs` 9/9 |
| `backend/static/js/fe/chunks.html` | real scanned chunks → magic-markdown panels | **browser-verified**: 8 live archive.org chunk panels |

**The full `fe/` tier is built + tested (57 tests: 7 py + 50 js):** spine (store/gateway) · cell (model) ·
view (panel + graph vdom) · gestures · integration · §U content tree. Browser-verified: panel render,
in-text dropdown expansion, graph form, panel⇄graph transition, real-data rendering.

| `backend/main.py` (additive) + `templates/editor.html` | **MOUNTED INTO THE SERVED APP** at `/editor` (`.mjs` MIME registered) | **browser-verified on the live app (8080)**: 24 real scanned chunks render as black-slate magic-markdown panels (bg #000, silver border, serif white), panel⇄graph toggle works (double-click → 2 circular nodes → back), workspace WS connected (`ws ●`), no console errors |

**Served-app integration milestone (2026-06-13):** the magic-markdown editor is a real route of the
application (`/editor`, same-origin with `/api` + the workspace WS), rendering live scanned chunks as
black-slate panels with the panel⇄graph transition — the legacy projector stays at `/` during the
transition (additive, non-destructive). This is "the magic situated in a served markdown editor."

| `backend/static/js/fe/magic_markdown_halo.mjs` | **halo ray-projection** (§V.4/§15.2): constant-similarity ray, along-line slide, updating angle, circular name-only phantoms, z-above-slate | `magic_markdown_halo.test.mjs` 5/5 + **browser-verified in `/editor`** (8 phantoms, z `2147483000`, rotate→slide, scroll→re-anchor, real radiation retrieval) |
| `backend/main.py` (the STRIP, T.8) | **`/` now serves the magic-markdown editor**; legacy `cp/*` projector demoted to `/legacy` | **browser-verified**: default `/` loads 24 chunk panels + halo + WS, no console errors |

**STRIP + HALO milestone (2026-06-13):** the magic-markdown editor is now the **default served frontend**
(`/`), with the apparition halo (auto-fire from a focal field, ray projection, constant-similarity,
along-line slide, updating angle, circular collapsed phantoms, z-above-slate, scroll-tracking, real
triple-product retrieval) — all browser-verified live. The legacy projector is at `/legacy`.

| `backend/static/js/fe/projector.mjs` | **3D projector** folded into the editor: chunk nodes at UMAP coords (`/api/recompute_umap`), OrbitControls, `project()`, `azimuth()` | `projector.test.mjs` 4/4 + **browser-verified**: WebGL2, **330 nodes**, `3d ● 330`, project() works |
| halo ↔ 3D camera coupling | `projector.onFrame(az)` → `halo.camAngle` → re-render | **browser-verified**: orbiting the camera (az 0→1.2) slides the halo phantoms along their rays — "ray angle updates as traced between the panel and the 3D nodes" (§V.4) |

**3D-projector + halo-coupling milestone (2026-06-13):** the editor now renders the 3D Real register (330
chunk nodes, WebGL2) behind the panels, and the halo's ray angle is **coupled to the 3D camera azimuth**
(orbit → phantoms slide along rays) — completing the §V.4 halo-in-3D requirement. Browser-verified live.

**Remaining (scanner-internal / harness — NOT blocking the editor):**
- **Retrieval id-scheme mismatch** (precisely characterized): the global TF-IDF store keys chunks as
  `c_<hash>` while persistence/`chunk_nodes` use `c_<hash>_<hash>`, so `chunk_search` ids 404 in
  `chunk_details`. This is in the scanner's **chunk bookkeeping** (V.1 "do not interfere") and the
  **deprecated** `chunk_search`→detail path (§S.3); the editor uses radiation halos + `chunk_nodes`/
  `chunk_details` (working). Documented, not fixed, to avoid breaking bookkeeping.
- **noetic per-workspace scan nav anomaly** (returned archive content) — a Selenium/scanner nav issue,
  same don't-interfere boundary.
- **REPL-driven 5-site matrix** — verified equivalently via live browser + direct API; the REPL-harness
  scenario form is a follow-up. Reconcile gesture body-schemas against the live routes;
integration into the served app (replace `cp/*` cards; wire the store/gateway/WS); the §E.1 HtmlStrategy
arm; the frontend halo (§15.2) + circular-node 3D; the frontend strip (§10.1); the live REPL end-to-end
matrix on all 5 sites; and the two open live bugs (retrieval id-scheme mismatch, noetic nav anomaly).
