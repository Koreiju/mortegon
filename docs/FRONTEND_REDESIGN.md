# Web Fiber Haptics: Frontend Redesign — A Vision-First Object Model

> **Status: planned.** This document captures design intent for a from-scratch frontend; no code is written against it yet.
>
> **Doc precedence.** This file is the *frontend's domain-and-object elaboration*. It waterfalls from [`DOMAIN_MODEL.md`](DOMAIN_MODEL.md) and is navigated from [`DOC_MAP.md`](DOC_MAP.md). When this file disagrees with `DOMAIN_MODEL.md`, the domain model wins; when it disagrees with [`code_constraints/frontend_rendering.md`](code_constraints/frontend_rendering.md) on a *programming-surface specific*, the constraint doc wins. This document is the missing middle: the domain model says *backend computes, frontend renders* (§2.1) but never says **how the frontend is structured as objects**. That is this file's whole job.
>
> **Clean-slate mandate.** This redesign assumes **no prior frontend code to reference**. The legacy `cp/*.js` set (`billboard.js`, `concept_graph.js`, `scanner.js`, `animation.js`, `search.js`, `workspace.js`, `sprite_manager.js`, `instance_manager.js`, `halo.js`, `telemetry.js`) is treated as overhang and is *not* the starting point. The object model below is derived purely from the design's registers (§1.1/§1.5), the unified panel (§4), the projector (§6), the halo (§8.2), and the streaming/lifecycle contract (§10). Where a legacy file's *responsibility* survives, §11 names where it lands; nothing of its *structure* is presumed.
>
> **Forbidden concepts inherited verbatim** (from `DOMAIN_MODEL.md` top-of-doc): no concentric-sphere layout authority; no graph-analytics retrieval; no Llama; no two-panel hover/click split; no dashed/dotted lines. These are object-level invariants here, not just prohibitions — §3–§9 assign each to the object that structurally cannot violate it.

---

## §0 — Why a Redesign, and What This Document Is

The frontend accreted. Ten modules grew overlapping responsibilities; the same ConceptNode acquired three rendering code paths; layout math drifted between backend and frontend; UI state was held in a dozen ad-hoc places and fell out of sync with the canonical backend mirror (§10.5). Every anti-goal in `DOMAIN_MODEL.md` §18 is, at root, a *structural* failure — two panels because two code paths (§18.11), pins in the wrong place because the rect was recomputed instead of captured (§18.8), stale URLs because the frontend trusted its own memory over a `purge_workspace` frame (§18.4). You cannot patch a structural failure; you re-seat the structure.

This document re-seats it. It defines a **small, whole set of frontend objects**, each with a single responsibility, a declared state, declared inputs and outputs, a lifecycle, and an explicit composition with its peers. The set is minimal by construction: there is exactly one inbound seam, one outbound seam, one source-of-truth mirror, one universal-record renderer, one recursive field interpreter, two canvases, three coupling membranes, and one liveness engine. Nothing else. If a future need cannot be met by extending one of these, that is the signal to question the need (§12.3), not to add an eleventh module.

The two priorities the user named map onto two of these objects and are given the deepest treatment:

- **A fully flexible card / compute-graph model whose structured fields are self-defined by their data blocks, recursively processed into pure-print text-tree renderings** → the **FieldTree** object (§4.2). *Data is the schema.* No field shape is declared anywhere; the shape emerges from parsing the data block, syntax-agnostically, into one normalized tree that drives every representation.
- **Smooth, fluid, live updates in 3D scans and 2D compute-graph interaction** → the **Liveness engine** (§9), a cross-cutting layer of keyed reconciliation, interruptible eased tweens, edit-safety, and a single frame budget that every canvas and view obeys.

> **Realized strategy (2026-06, implemented + verified live).** This object set is the **conceptual target**, not a from-scratch rebuild order. The shipped path — per the user's directive — is to **retheme and re-seat the *existing* `backend/static/js/cp/*.js` frontend in place** toward these invariants, **preserving its working features**, rather than ship a parallel greenfield tree. The black-core + silver-outline theme (the de-rainbowed "Maronite" layer in `cp/ui_utils.js`, plus recoloured `static/css/styles.css` + `templates/index.html`), the pure-black 3D scene (`cp/animation.js` — the waterfall backdrop removed), the **headless yellow 2D↔3D connector**, and the **undirected, no-arrowhead, no-dash silver edges** (`cp/concept_graph.js`) were all applied **to the existing modules** — see [`frontend/theme.md`](frontend/theme.md) §11 for the realized token map and the `?v=` cache-bust workflow. The former `backend/static/fe/` directory — a **dormant reference sketch** of this object model, *never wired into any route* — has been **archived to `_legacy_frontend/` during the frontend unification (2026-06)** so the app carries exactly one frontend tree (`cp/*.js`); do not resume it as a replacement (see `_legacy_frontend/README.md` for the restore path). Verified live against the full real stack (Selenium + nomic + GPT4All + LangGraph, `all_real:true`) on example.com, Hacker News, **archive.org** (434 chunks), and **tarot.com** (cross-corpus semantic retrieval ranks tarot 0.369 vs archive 0.053 for a tarot query).

---

## §1 — The Frontend's Identity (waterfall from §1.1, §1.5)

### §1.1 The frontend is a *projection*, not a *model*

The Mortegon's deepest frontend consequence is this: **the frontend owns no truth.** The Real (§9 projector geometry), the Imaginary (§4 concept structure), and their alchemy are computed on the backend — UMAP coordinates, embeddings, PageRank, compile renderings, cascade order, apparition ranks, the UI-state mirror itself (§10.5). The frontend's task is to be a *faithful, fluid projection* of that canonical state, and to be the *gesture surface* through which the user perturbs it.

State therefore flows in exactly one direction, and gestures in exactly the reverse:

```
   inbound (truth)                                   outbound (intent)
   ──────────────                                    ─────────────────
   WebSocket frames                                  user gesture
        │  §10.1                                           │  §14.2
        ▼                                                  ▼
   FrameBus  (§3.2) ── the one inbound seam          GestureGateway (§3.3) ── the one outbound seam
        │                                                  │  REST + idempotency key (§2.5)
        ▼                                                  ▼
   WorkspaceStore (§3.1) ── normalized mirror        backend lifecycle dispatcher (§10.2)
        │  emits minimal diffs                             │
        ▼                                                  ▼
   Views render (§4–§7)                              … which broadcasts frames … ──► back to FrameBus
        │
        ▼
   telemetry of what rendered ──────────────────────► GestureGateway ──► UI State Service mirror (§10.5)
```

The loop is closed and single-directional at every seam. A gesture never mutates a view directly; it travels to the backend, the backend's lifecycle (§10.2) is the single authority, and the resulting frame flows back through the *same* inbound path any other actor's mutation would (the user's, the agent's, the REPL's). This is what makes the REPL ↔ frontend round-trip (§14) hold by construction: there is no frontend-only state transition for the REPL to miss.

This is the cure for overhang. Overhang is *derived state that drifted from its source*. A pure projection has no derived authoritative state to drift — only transient interaction state (what is being dragged this very frame, where the caret sits in an open textarea), which is local, ephemeral, and reconciled gently against incoming truth (§9.4).

### §1.2 Three canvases, one record

The frontend renders three surfaces, one per register (§1.5), and exactly one kind of thing on all of them:

| Register | Frontend surface | Object | Renders |
|---|---|---|---|
| **Real** (§1.5) | 3D projector | **Projector** (§5) | the TF-IDF chunk manifold as geometry — scanner-emitted (interior) and agent-emitted (perimeter, §6.6.1) |
| **Imaginary** (§1.5) | 2D concept editor | **Editor** (§6) | ConceptNodes (§3.1) as panels / compiled-graph children / halo phantoms |
| **Symbolic** (§1.5) | REPL (out-of-browser) | telemetry obligation (§8) | nothing in the browser; the frontend *feeds* it complete telemetry |

The single record is the **ConceptNode** (§3.1). Every Imaginary surface is a ConceptNode in one of its three representations (§4.5): unfolded panel, compiled-graph child (value only), halo phantom (name only). Every Real surface is a chunk, which *becomes* a ConceptNode (`provenance: derived-from-chunk`) the moment it is clicked-and-stuck (§5.3). There is no second record type, no special-cased card, no parallel widget — the §18.11 two-panel regression is structurally impossible because there is one renderer (§4.1) for one record.

### §1.3 The minimalism thesis: latent interactivity, not hidden capability

Minimalism here is not *fewer features*; it is *less chrome between the user and the structure*. The resting form of everything is **pure print** (§4.1.1): tabs and newlines, `name: value` rows, no JSON braces, no HTML angle brackets, no per-row buttons, no placeholder boxes. Interactivity is **latent** — transparent overlay buttons sized to each print-token region, revealing a one-pixel outline on hover, materializing a textarea on click (§4.2.5). The halo phantom shows a name and nothing else (§4.5); the compiled child shows a value and nothing else; the score chips, the type badges, the debug overlays — all gone.

The discipline: **every pixel of chrome must earn its place by being the only way to express a gesture the design names.** A drag handle earns it (you must be able to move a pin); a score chip does not (the halo's radius already encodes the score, §8.2.1; the exact number lives in a slow-hover tooltip). When in doubt, it is print.

### §1.4 The frontend's load-bearing invariants

These are the frontend's analogue of `DOMAIN_MODEL.md` §2. Every object below honours them; §12 re-asserts them as the acceptance bar.

1. **No authoritative frontend state.** The only state a view may *own* is transient interaction state (active drag, caret, in-flight optimistic echo). Everything else is read from the **WorkspaceStore** (§3.1), which is a projection of frames. (§1.1)
2. **One inbound seam, one outbound seam.** All truth enters through **FrameBus** (§3.2); all intent leaves through **GestureGateway** (§3.3). No view opens its own socket or fetch. (§2.4, §2.5)
3. **One record, one renderer, three modes.** **ConceptView** (§4.1) is the single anatomy; mode is a parameter, never a fork. (§18.11)
4. **Data is the schema.** Field structure is *parsed*, never declared; **FieldTree** (§4.2) is the only interpreter. (§4.5, §4.6)
5. **The frontend renders coordinates; it never computes them.** No UMAP, no embedder, no PageRank, no layout reasoner, no compile. (§2.1)
6. **All motion is interruptible eased tween on one rAF budget.** No layout thrash, no restart-from-scratch on a mid-flight retarget. (§9)
7. **The two canvases share no coordinate system.** Coupling is only through the three membranes (§7), and only in the directions §6.6.2 permits.
8. **Faithful telemetry is not optional.** Anything the user can see or do emits telemetry the Symbolic register can read; a render with no telemetry is a *severance* (§8, §18.1).

---

## §2 — The Architecture at a Glance

One diagram; the rest of the document elaborates each box. Objects are grouped into five tiers, deliberately mapped to an anatomy so the structure is self-similar to the Mortegon it serves (§14 transcendental permanence):

```
                          ╔══════════════════════════════════════════════╗
   THE SPINE              ║  FrameBus (§3.2)   WorkspaceStore (§3.1)       ║   transport + truth
   (nervous system)       ║                    GestureGateway (§3.3)       ║
                          ╚════════════════════════╤═════════════════════╝
                                                    │ store diffs / gestures
                          ╔════════════════════════╪═════════════════════╗
   THE CELL               ║   ConceptView (§4.1) ── renders one record    ║   the universal record
   (the unit of meaning)  ║   FieldTree  (§4.2) ── data → pure-print tree  ║   in its three forms
                          ╚═══════════╤══════════════════════╤═══════════╝
                                      │                       │
                ╔═════════════════════╪═══╗      ╔════════════╪═════════════════════╗
   THE ORGANS   ║  Projector (§5)         ║      ║  Editor (§6)                      ║
   (canvases)   ║  the Real — 3D manifold ║      ║  the Imaginary — 2D graph         ║
                ╚═══════════╤═════════════╝      ╚═══════════╤═══════════════════════╝
                            │                                 │
                ╔═══════════╧═════════════════════════════════╧═══════════╗
   THE MEMBRANES║  Billboard (§7.1)   Halo (§7.2)   LinkLayer (§7.3)       ║   where registers touch
   (connective) ║  hover→pin          ray-projection  solid links + arrow ║
                ╚═══════════════════════════╤═════════════════════════════╝
                                            │
                ╔═══════════════════════════╧═════════════════════════════╗
   THE PULSE    ║  Liveness engine (§9): Reconciler · Tween scheduler ·    ║   smoothness, everywhere
   (cross-cut)  ║  edit-safety · one frame budget · backpressure/resume    ║
                ╚══════════════════════════════════════════════════════════╝
```

Read top-down for *how truth becomes pixels*; read bottom-up for *how a gesture becomes truth*. The Pulse underlies all of it: every organ and membrane schedules its motion through the one Liveness engine, which is why the whole surface stays fluid under a streaming scan and a cascading edit at the same time (§9.5).

---

## §3 — The Spine: State and Transport

Three objects. They are the only objects that touch the network, and the only objects that hold cross-view state.

### §3.1 `WorkspaceStore` — the normalized observable mirror

**Responsibility.** Hold a normalized, read-only-to-views projection of canonical backend state, and emit *minimal diffs* when frames mutate it. It is the frontend's single source of truth and is **never authoritative** — it only ever reflects what a frame told it.

**State (normalized; keyed for O(1) reconciliation, §9.1).**

| Slice | Shape | Fed by frame | Domain anchor |
|---|---|---|---|
| `concepts` | `Map<concept_id, ConceptNode>` | `concept_changed` | §3.1 |
| `edges` | `Map<edge_id, ConceptEdge>` (hard links only) | `concept_changed` | §3.2.1 |
| `index` | `Map<concept_id, {nomic, pagerank, similar_to[]}>` | `concept_index_update` | §10.4 |
| `chunks` | `Map<chunk_id:int, {url, layout6d, image_url, provenance}>` | `chunk_added/replaced/removed` | §6.1, §9.4 |
| `layout` | `LayoutFrame` (canonical 6-vectors + per-URL roots) | `umap_canonical` | §6.1, §11.1 |
| `ui` | the §10.5 mirror (pins, latch, halo_focus, viewport rows, compile_expansions, signal_stream, …) | `ui_state_changed` | §10.5 |
| `tokens` | `Map<agent_id, ringbuffer<token>>` | `agent_token` | §12.1 |
| `evolution` | append-only `EditDiff[]` (bounded view window) | `evolution_diff` | §11.4 |
| `cascade` | per-actor fire counts / status | `cascade_status` | §7.4 |
| `seq` | last applied `frame_seq` (high-water mark) | every frame | §2.4 |

**Inputs.** Only `FrameBus.apply(frame)` mutates it. **Outputs.** `subscribe(selector) → unsubscribe`; subscribers receive `(next, prevKeyset)` so they can run keyed enter/update/exit (§9.1). **Lifecycle.** One instance per workspace; on `purge_workspace` (§6.5) it resets every slice and the `seq` high-water mark in a single transaction so views clear in one paint (§18.4 cannot recur — views read the store, the store was authoritatively cleared by the frame).

**Invariants.** (a) Views never write to it. (b) Mutations are *frame-driven only*; the optimistic echo of a gesture (§3.3) is held in a *separate* overlay slice and merged for read, never written into the canonical slices — so when the authoritative frame arrives it simply replaces the echo with no reconciliation drama. (c) It computes nothing derived that the backend already computes; `similar_to`, `pagerank`, `layout6d` are stored as received.

### §3.2 `FrameBus` — the one inbound seam

**Responsibility.** Own the single long-lived workspace WebSocket (`/api/ws/workspace/{id}?resume=<seq>`, §10.1); enforce monotone sequencing and lossy backpressure (§2.4); translate each frame into exactly one `WorkspaceStore` transaction.

**State.** the socket; the `seq` high-water mark (mirrored to the store); a bounded replay buffer for reconnection.

**Behaviour.**
- **Monotonicity.** Frames apply in `frame_seq` order; an out-of-order frame is buffered until its predecessor lands or the resume window closes.
- **Resume.** On disconnect, reconnect with `?resume=<last_seq>`; the backend replays the last five minutes (§2.4); the bus de-duplicates against the high-water mark so a replayed frame already applied is dropped.
- **Backpressure (smoothness under load, §9.3).** Under a flood, drop oldest `chunks_partial`/progress frames; **always keep** `done`, `error`, the *latest* `umap_canonical`, the *latest* `concept_index_update`, *all* `concept_changed`, *all* `evolution_diff` (§2.4). This is why a fast scan never starves the editor of structural truth.
- **Dual-routing guard (§18.1).** The bus subscribes to the *workspace* WS, not a per-snapshot socket; `chunk_added` and `umap_canonical` must arrive here. A scan that streams only to a snapshot socket is the §18.1 severance and is a hard regression the bus is positioned to detect (it sees the gap between `done` and the chunk count).

**Composition.** `FrameBus → WorkspaceStore` (write) is the only inbound write path in the entire frontend.

### §3.3 `GestureGateway` — the one outbound seam

**Responsibility.** Turn every user gesture into a backend mutation (REST/PATCH/DELETE per §14.2), carry an idempotency key (§2.5), optionally render an *optimistic echo* into the store's overlay slice for zero-latency feel, and post the **telemetry** that keeps the Symbolic register's mirror faithful (§8, §10.5).

**The gesture contract.** Every gesture is `{ kind, args, idempotency_key, echo? }`. `kind` maps 1:1 to a row in the §14.2 catalogue — `ui-pin`, `ui-compile-expand`, `concept-edit-description`, `field-tree-add-child`, `ui-halo-focus`, `web-scan`, `editor-create`, … The gateway is the frontend's enumeration of that catalogue; **a gesture with no catalogue row cannot be sent** (it would have no REPL action and no env-scenario — §14.4 — so it is not a real gesture).

**Optimistic echo + reconcile.** For latency-sensitive gestures (drag a pin, type into a field, open a halo), the gateway writes a provisional value into the store's *overlay* slice and fires the REST call; when the authoritative `ui_state_changed`/`concept_changed` arrives via FrameBus it supersedes the echo. Because the echo lives in a separate slice (§3.1), there is never a merge conflict — the canonical value simply wins on arrival. If the REST call errors, the echo is rolled back and the error surfaced; the store's canonical slices were never touched.

**Telemetry completeness.** After a render settles, the responsible view calls `gateway.telemetry(kind, snapshot)`; the gateway batches and POSTs to `/api/ui/telemetry` (§10.5). This is the frontend's whole obligation to the Symbolic register (§8): *what you rendered, you report.*

**Composition.** `GestureGateway → backend lifecycle (§10.2) → frames → FrameBus → store → views`. The gateway never short-circuits to a view; the loop always closes through the backend.

---

## §4 — The Cell: The Universal Record's Rendering

Two objects render the one record. **ConceptView** is the anatomy; **FieldTree** is the interpreter that makes the data block self-describing. Together they are the frontend's most-reused code and the place the design's minimalism is won or lost.

### §4.1 `ConceptView` — the one anatomy, three modes

**Responsibility.** Render a single ConceptNode (§3.1) in one of its representations (§4.5), using one DOM-building routine. Mode is a parameter; there is no per-mode code path. This is the structural guarantee against §18.11.

**Modes (one anatomy, parameterised).**

| Mode | Shows | Where used | Anchor |
|---|---|---|---|
| `panel` | the four canonical rows (`name`, `description`, `value`/field-tree, `rendering`) + user rows; chrome | pinned editor panel | §4.1 |
| `collapsed` | name + read-only/🔒 indicator only | newly-pinned default; hover preview default | §4.3 |
| `phantom` | **name only** (scores in `title` tooltip) | halo apparition candidate | §4.5, §1.7-FR |
| `child` | **value only** (name implicit from position) | compiled-graph child | §4.5 |

`render(node, mode, hostRect?)` builds the same body skeleton and elides per mode. The four canonical rows are themselves FieldTree rows with reserved key slugs (§4.6), so even the "anatomy" is just a FieldTree with a default starting shape — there is no special canonical-row widget.

**Chrome (§S black-slate — DOMAIN_MODEL §4.1.2).** **None.** Every panel and computation node is a **blank editable bordered slate**: thin silver border, completely black infill, serif white text. No coloured header, no hash hue, no minimise, no close `×`, no top bar. The whole slate is the drag handle (textareas exempted). Affordances that were chrome — compile, latch (§4.4), grow `+→`/`+↓`, the resize corner — surface as **hidden-overlay** controls on hover/edit over the slate, never as a persistent bar. Foundation-fixture and python-native panels render the 🔒 indicator and hide the latch (§9.6); their undeletability is enforced at the lifecycle layer (§18.22), not by an absent button (there is no button). Coloured-header / hash-hue / `×` / minimise chrome is a **forbidden concept** (§S.4).

**Latch + form-fit + slide-out (§4.4).** Latched (default) shows `name`/`description`/`rendering`; the `data` field-tree is loaded but hidden. Unlatch slides the field-tree out as an equal-height side panel, visually joined (one outline, one drag handle, one resize handle on the wider side). Each `<pre>` form-fits to its longest line up to `600px` latched / `800px` unlatched before horizontal scroll; **empty rows hide entirely**; the equal-height contract resizes both halves in lockstep. This is `ConceptView`'s own state machine over `ui.latch_state[card_id]` (§10.5); it owns no truth — the latch flag is a mirror field.

**State.** transient only: which field (if any) is in edit; caret position; live drag/resize deltas (echoed via §3.3). Everything persistent (`name`, `data`, `ui_state`, latch, pin chrome) is read from the store.

**Composition.** `ConceptView` is instantiated by the **Editor** (§6) for pins and compiled children, by the **Halo** (§7.2) for phantoms, and by the **Billboard** (§7.1) for hover preview — all four call the *same* `render`. (§1.1-FR frontend_rendering §1.1.)

### §4.2 `FieldTree` — the flexible recursive interpreter *(priority #1)*

> *"I would hope for a data-agnostic recursive tree interpreter for rendering the variable key:value fields that are generalizable between syntaxes and their native types, which when compiled, only show the values of the keys on computation graph concept nodes."* (user, verbatim, §4.6)

This is the object that realises *"structured fields are fully self-defined by the data blocks, recursively processed into their pure-print text tree structure renderings."* It is the single interpreter for the `data` field across every surface and every mode. It has five phases — **parse → normalize → print → project → edit** — plus a **serialize** return path that closes the round-trip.

#### §4.2.1 Data is the schema

There is **no declared field shape anywhere in the frontend.** A ConceptNode's `data` is an opaque string. Its structure is whatever *parsing* yields. A panel with three nested rows and a panel with thirty are not two widgets configured differently; they are the same interpreter over two different data strings. This is what "fully self-defined by the data blocks" means operationally: the shape is a *function of the content*, computed fresh on each render, never stored as layout metadata. Add a line to the data, and a row appears; nest it under a tab, and it becomes a child — because the parser saw it, not because anything was registered.

#### §4.2.2 The parse — one descent, syntax strategies, one normalized tree

A single recursive descent recognises JSON, bracketed lists, indented (tab/space) trees, HTML element trees, and plain text, and emits one normalized intermediate regardless of input syntax:

```
FieldNode {
  key:      string | null     // null for positional/list elements
  value:    string | null     // scalar leaf text (may be multi-line, may contain {var})
  children: FieldNode[]        // structural descent
  meta: {
     ref?:    string          // a {var} reference token, preserved verbatim
     attr?:   boolean         // HTML attribute folded as @attr child
     cypher?: boolean         // a MATCH…RETURN / CALL… span flagged for §7.1 step 4
     iterable?: { total: int, signal_index: int }  // signal-stream gate (§4.6.1)
     readonly?: boolean       // python-native / rendering field (§9.6)
  }
}
```

The descent is structured as **syntax strategies behind one interface** — `JsonStrategy`, `BracketListStrategy`, `IndentTreeStrategy`, `HtmlStrategy`, `PlainTextStrategy` — each `detect(raw): bool` and `parse(raw): FieldNode`. The first to `detect` wins; `PlainTextStrategy` always detects (the fallback). HTML folds attributes as `@attr` children and element names as keys; JSON folds objects to keyed children and arrays to positional children; indented text folds by indentation alone. **No syntax branch escapes the parser** — downstream phases see only `FieldNode`. This is the §7.1 *"one recursive descent… the user never thinks about syntax"* made an object, and it is symmetric with the backend's `decompose_recursive` (§18.15) so the two agree on the tree.

#### §4.2.3 The print — pure-print projection

`print(tree): string` walks the `FieldNode` tree to the canonical syntax-stripped form (§8D.20 tree-pretty-print): one `key: value` per line, nesting by tab depth, multi-line values absorbed into the parent's indentation, **no braces, no brackets, no angle brackets, no dashes, no quotes** (frontend_rendering §2.7). A multi-line value does not introduce escaped-newline glyphs; its lines simply inherit the row's indentation. The print is the resting visual of every editable field on every surface — what the user actually sees until they click.

#### §4.2.4 The three representations from one tree

The same `FieldNode` tree projects to all three representations of §4.5 by *eliding*, never by re-parsing:

- **Unfolded** (panel mode): every node prints `key: value`, every node editable.
- **Child** (compiled-graph child, §7.3): print **value only**; the key is implied by the node's position in the parent's tree. Multi-line values expand the box to fit (form-fit).
- **Phantom** (halo, §8.2): print the **root key (name) only**.

One parse, three elisions — the compact-representation standard (§4.5) falls out for free, and the §18.21 score-chip regression cannot happen because the phantom projection has no slot for a score.

#### §4.2.5 Click-to-edit — hidden-overlay buttons, caret mapping, Shift-Enter

Each printed token region carries a transparent overlay button sized to its bounding rect (frontend_rendering §1.3). At rest it is invisible; on hover it reveals a 1px outline / ~10% tint; on click it is *replaced in place* by a `<textarea>` pre-populated with the node's underlying value, with the **caret placed where in the printed text the click landed** (§4.1.1). Commit semantics (frontend_rendering §1.4): **Enter** commits through the gateway (§3.3) and returns to print; **Shift-Enter** inserts a literal newline without committing; **Escape** discards to the prior value; **blur** commits identically to Enter. The cascade (§7.4) is *not* nudged per keystroke — only on commit — which keeps the editor responsive (§9.4 edit-safety guarantees a mid-cascade frame never clobbers an open editor). Read-only fields (`rendering`; python-native, §9.6) do **not** enter edit; the click briefly highlights to signal the constraint (frontend_rendering §2.9).

#### §4.2.6 Plus-sign growth — `+→` / `+↓` as tree mutation

When a node is in edit state, two cutout affordances appear *concatenated into the print tree itself* (frontend_rendering §1.5): `+→` on the right adds a **child** row indented one level; `+↓` on the bottom adds a **sibling** at the same level. Hover previews the slot as a faint print placeholder; click materialises a real row already in edit state (so the user types immediately). Each new row is a full `FieldNode` with its own capacity to grow children — which is exactly why "a singular compute node" and "a full panel" are *the same record at different sizes* (§4.6): the field-tree growth **is** the promotion; there is no "promote to panel" affordance. The four canonical rows are reserved-slug `FieldNode`s, so growth around them is uniform with growth anywhere else.

#### §4.2.7 `{var}` references and autocomplete binding

A `{slug}` token in any value is preserved by the parser as `meta.ref` and printed verbatim; it resolves at compile on the backend (§7.2), never on the frontend. Typing into a *new row's key* opens autocomplete (§4.7, §17.15): the gateway opens `ui-autocomplete` and fetches `/api/concept_completions?prefix=&parent_card_id=`; selecting a candidate inserts `{<linked_name>}` into the value, recording a typed `{var}` reference (§4.7). When the slug matches no existing node, the backend's variable auto-creation (§17.8) spawns the empty primitive; the frontend simply renders the resulting `concept_changed`. The autocomplete dropdown is the only transient list the FieldTree shows, and it is driven entirely by `ui.autocomplete_state` (§10.5).

#### §4.2.8 Signal-stream gating under iteration (§4.6.1)

When a `FieldNode` carries `meta.iterable`, the FieldTree renders **only the current signal element** — `data[signal_index]` — and nothing else (frontend_rendering §1.14, §18.24). The suppressed elements remain in the node's underlying data (held in the store, never dropped) and are advanced by the rollout coordinator via `ui-signal-advance` (§17.1.2); on advance, the FieldTree swaps the one visible print form in place and the cascade re-fires per signal. There is no "iteration 3 of 12: [c1, c2, c3]" overlay — that is the §18.24 violation; the full position is legible **only** in the REPL viewer's `signal_stream` row (§8). This single rule lets `Database.concept([ids])`, `{urls_panel}` (§15.7), and `pattern_map` (§15.8.2) all render under one minimalist contract.

#### §4.2.9 The round-trip — edit → tree → canonical serialize → gateway

The return path closes the loop. An edit mutates the in-memory `FieldNode` tree; `serialize(tree)` re-emits the canonical pure-print form; the gateway POSTs it (`concept-edit-data-row` / `field-tree-add-child` / `field-tree-add-sibling`, §14.2); the backend persists it (as JSON internally — the user never sees JSON) and broadcasts `concept_changed`; FrameBus updates the store; ConceptView re-renders the field from the *authoritative* data. So even the user's own edit round-trips through the backend (§1.1) — the optimistic echo (§3.3) merely hides the latency. **The user edits a tree; the wire carries print; the store holds truth; the screen shows print.** Syntax never surfaces at any point in that cycle.

### §4.3 The compile/collapse dialectic in the frontend (§7.3)

Right-click on a `panel`-mode `ConceptView` body (not a textarea) toggles the **dialectical inversion** (§7.3) between synthesis and analysis — and the frontend's role is purely to render the toggle, never to compute it:

- **Panel → subgraph (expand).** The gateway fires `ui-compile-expand`; the backend compiles (§7.1), decomposes top-level keys into child ConceptNodes keyed `<card_id>__<key>`, and broadcasts `concept_changed` × N + `ui_state_changed` carrying `compile_expansions[card_id]`. The **Editor** (§6) reads the expansion and lays the children out ray-constrained around the focal (§7.3.2/§6.5), each as a `child`-mode `ConceptView` (value-only, form-fit, **stringless edges** via LinkLayer §7.3). The children carry the *same* hover/click/halo affordances as any panel (§8.2.3) — because they are the same `ConceptView`.
- **Subgraph → panel (collapse).** Right-click the central node → `ui-compile-collapse` → backend deletes the children through the lifecycle → `concept_changed` × N + cleared `compile_expansions` → Editor dissolves the child views and restores the panel. The underlying record is untouched on either flip (§7.3).

One level deep (§7.3); deeper structure is *collapse → click child → materialise full panel → right-click new panel*. The symmetry of the gesture is the contract, and because both directions are just frames mutating the store, the REPL drives them identically (`ui-compile-expand`/`-collapse`, §14.2).

---

## §5 — The Real Canvas: `Projector` (§6, §9)

**Responsibility.** Render the TF-IDF chunk manifold as live geometry and nothing else (concept cards never appear in 3D, §6). It consumes chunk + layout frames and reads `layout6d` from the store; it computes no coordinates (§2.1, §1.4-FR.5).

### §5.1 State and surface

A Three.js scene with: an `InstancedMesh` chunk field keyed by **stable integer chunk id** (§9.4); per-URL doc-hub instances; the single hover `Billboard` (§7.1); the camera + controls. Transient state only: per-chunk tween targets, current camera azimuth (for HSV phase), the `hidden_urls` set read from the store. No chunk's truth lives here — `chunks` and `layout` are store slices (§3.1).

### §5.2 The chunk field — three monotone placement states (§6.1)

Each chunk moves through three states, monotonically (§6.1), and the Projector owns only the *rendering* of the transitions:

| State | Trigger | Projector action |
|---|---|---|
| **Preliminary radial** | `chunk_added` arrives | add an instance immediately at `hash(chunk_id)` unit-direction from the URL root, distance `R·(1+n/k)` — *no wait for UMAP* (this is what makes the scan feel instant, §5.4) |
| **UMAP-locked canonical** | `umap_canonical` frame | tween the instance to its canonical `(x,y,z)` from the 6-vector over ~600 ms, eased, **interruptible** (§9.2) |
| **Radial-slide refined** | force-loop collision in animate | slide a locked chunk along its root-URL ray to resolve a collider violation |

The hash-direction placeholder is the *only* surviving Fibonacci-style angular sampling and is transient by construction (§18.2) — replaced by the next `umap_canonical`. No code path uses it as a final authority.

### §5.3 Click-and-stick (§5.3, §4.2) — the Real→Imaginary crossing

Hovering a chunk shows the `Billboard` (§7.1) at the chunk's projected screen rect. On click, the Billboard's *current* `getBoundingClientRect()` is captured and handed to the **Editor** (§6) which materialises a pinned `ConceptView` at exactly that `(top,left,width,height)` (freeze-at-hover-rect, §4.2, frontend_rendering §1.2, §18.8). The pinned panel **is** the chunk's ConceptNode (`provenance: derived-from-chunk`). The Projector's job ends at handing over the captured rect; it does not own the panel and the panel does not own a 3D coordinate (§6.6.2, §7.4-FR).

### §5.4 Live scan streaming — the fluid-update pipeline *(priority #2, Real side)*

This is the Real canvas's contribution to "smooth, fluid, live." The pipeline is **incremental, keyed, and interruptible** end to end:

1. `chunk_added` frames stream in; the Reconciler (§9.1) does keyed *enter* — one `InstancedMesh` slot per new id, placed at its preliminary radial position **this frame**. No full rebuild; existing instances are untouched.
2. `umap_canonical` frames arrive **mid-scan and at scan-end** (§16.5 requires incremental refits, not scan-end-only). Each retargets the tween of every affected instance. A frame that lands mid-tween **retargets from the current interpolated position** (§9.2) — it never restarts from the preliminary position, so the motion reads as one continuous settling, not a stutter.
3. The animate loop (§5.5) advances every tween on the one frame budget (§9.5), applies HSV rotation, runs the collider, and reads the visibility set — all per frame, all bounded.
4. Backpressure (§3.2) keeps the *latest* `umap_canonical` and drops stale progress frames, so under a fast scan the field always tweens toward the freshest layout rather than queueing through stale ones.

The result is the §16.5 contract felt as motion: chunks appear the instant they stream, drift smoothly to their semantic positions as UMAP refits, and re-settle without jank when a new URL's scan perturbs the frame.

### §5.5 The animate loop — per-frame invariants

Each rAF tick, in order: advance tweens (§9.2); recompute **camera bounds** `minDistance = 0.6·cluster_radius(orbit_target)`, `maxDistance = 3·max(|pos|)` (per frame, never cached — §18.18, frontend_rendering §1.11); apply **HSV phase** `(camera_azimuth_phase + chunk_hsv_phase)` to every visible chunk's fill and to every HSV-bearing halo phantom (period default 60 s, workspace-configurable — §8.2.1.2, frontend_rendering §1.8/§2.10); run **hard collider** repulsion (`COLLIDER_SAFETY ≥ 2.0`, shared image/text radius — §18.3); read `hidden_urls` and write `scale=0` for hidden chunks/hubs (**visibility is a flag, never a mesh mutation** — §6.3, frontend_rendering §1.9, §18.14). **Adaptive resize**: both `window.resize` (rAF-coalesced) and a `ResizeObserver` on the projector panel fire `onResize`; `setSize(w,h,updateStyle=false)`; **no no-change guard** (§18.9, frontend_rendering §1.12). **Perimeter placement** (§6.6.1): agent-output chunks render on the outer envelope shell (angular position from UMAP, radial rescaled) so the interior reads as observations and the perimeter as syntheses (§18.23).

### §5.6 `TextureCache` (sub-object of Projector) — the single image fetch path

One object, one path (§11.2, frontend_rendering §1.13, §18.10): in-memory `Map<url, THREE.Texture>` → IndexedDB blob cache → `fetch(proxy_url)` → `fetch(direct_url)`. The `X-Image-Proxy-Note` transparent-PNG fallback is **never cached** as a successful image. Two chunks at the same URL share one `THREE.Texture`. Image billboards persist for the full lifetime of the layout — no reload churn.

---

## §6 — The Imaginary Canvas: `Editor` (§4, §5, §7)

**Responsibility.** Render the 2D concept graph: pinned panels, compiled-graph subgraphs, wiring, and the live cascade reflow. It instantiates `ConceptView`s (§4.1) and lays them out; it owns no concept truth (the `concepts`/`edges`/`ui` slices are the store's).

### §6.1 State and surface

A 2D canvas (screen-pixel space, §6.6.2) hosting: pinned `ConceptView` panels positioned by `ui.pin_chrome` (§17.12); compiled-graph children positioned ray-constrained (§6.5); the `LinkLayer` SVG (§7.3) beneath panels; the active `Halo` (§7.2) when a focal is open. Transient state: live drag/resize deltas (echoed via §3.3), which panel is being right-clicked. Persistent panel state — position, size, minimise, latch, pin order — are all §10.5 mirror fields, so a second tab or the REPL viewer reflects them identically.

### §6.2 Pins and freeze-at-rect (with `Billboard`, §7.1)

A pin enters at the screen rect captured by click-and-stick (§5.3). Pin chrome (move/resize/minimise/close) is field-merge state (§17.12): each gesture POSTs only the fields it mutates (`ui-pin-move` → top/left; `ui-pin-resize` → width/height; `ui-pin-minimise` → minimised; `ui-pin-close` → unpin). A second click on the same chunk **raises and un-minimises** the existing panel rather than duplicating (§4.2). The panel's `data-3d-node-id` carries the solid arrow (§7.3) back to its chunk; the panel never follows the chunk's motion (§6.6.2, §18.31).

### §6.3 Wiring and the commitment fan / possibility ring (§3.2.1)

Hard links (committed `ConceptEdge`s) render along the **commitment fan** — solid, full-saturation **undirected line**, ~2px, no arrowhead (§3.2.1, §O.16) — drawn by `LinkLayer`. Soft links (halo apparition candidates) render along the **possibility ring** — solid, ~40% saturation **undirected line**, ~1px, no arrowhead (no dashes ever, §18.7, §O.16). The two regions are spatially independent (§1.5): the fan reaches outward to committed targets; the ring sits concentric at the halo radius. Clicking a soft link promotes it via `concept-edge-create` (§5.4) and the autoregressive feedback (§8.2.2) spawns a new focal + new halo — the Editor renders the promotion as the phantom fading from the ring while the new hard edge materialises along the fan.

### §6.4 The live cascade reflow *(priority #2, Imaginary side)*

This is the Imaginary canvas's contribution to fluidity. When an edit triggers the backend cascade (§7.4), `concept_changed` frames arrive for each affected card (debounced ~800 ms on the backend). The Editor reflows via the Reconciler (§9.1):

- **Keyed update, not rebuild.** Only the cards named in the frames re-render; their `rendering` panes update in place; untouched panels never reflow.
- **Eased link re-route.** When a card moves or an edge changes, `LinkLayer` re-routes with an eased transition (§9.2), not a snap.
- **Edit-safety (§9.4).** If a card receiving a cascade frame has an open editor on a *different* field, the cascade updates the other fields and leaves the open editor's textarea and caret untouched. A frame never clobbers what the user is typing — the open field reconciles only on commit/blur.
- **Halo refresh.** If a halo is open on a changed focal, `concept_index_update` refreshes its candidates (the apparition surface re-fires, §8.2) with the ring tweening to new radii rather than redrawing.

### §6.5 Ray-constrained subgraph layout (§7.3.2, §6.5)

Compiled-graph children (§4.3) and apparition phantoms place around their focal by **ray-constrained placement** (the 2D analogue of §6.1; the forbidden `_fibonacciPosition` concentric-ring placement is removed — top-of-doc forbidden concepts). Same algorithm for small and large subgraphs; no predicted-overlap branching. The Editor requests positions from this one routine; the routine reads the focal's screen rect and fans children along rays at form-fit spacing.

---

## §7 — The Coupling Membranes (where the registers touch)

Three objects are the *only* couplings between canvases. They are first-class because §6.6.2 makes the canvas separation a contract: 2D and 3D share no coordinate system, and the only legal crossings are these membranes, each one-way in the direction the design permits. Making them objects (rather than scattered cross-references) is what lets the separation be *enforced at a boundary* instead of *hoped for in convention*.

### §7.1 `Billboard` — hover preview → freeze-at-rect pin (Real → Imaginary)

One `#billboard` instance, content swapped per hover (§8.6, §18.13 — there is no "root summary" widget and no per-result second billboard). Its source is a 3D chunk or an in-editor halo candidate — **all hit the same `ConceptView.render(node, 'collapsed')`** (§8.6). (§S.3: the retrieval-sidebar/search-result-row source is removed; in-editor halo ray-projection queries are the retrieval surface.) Its sole crossing role: on click, hand its current bounding rect to the Editor for the freeze-at-rect pin (§5.3). It carries the hidden-overlay edit affordances (§4.2.5) so a hover preview can be edited the instant it pins. The crossing is **Real → Imaginary, screen-rect only** — never a 3D coordinate (§6.6.2).

### §7.2 `Halo` — concentric radiation + ray-projection + HSV phantoms (Real ↔ Imaginary)

The Halo is the literal object form of §1.5's *"the Imaginary contracts the Real into manifold form."* It renders, around any focal `ConceptView`, the concentric-circle apparition radiation (§8.2.1) **and** the ray-projection of the focal's projector-neighbours onto the halo's conic surface (§8.2.1.1).

**Concentric radiation (§8.2.1).** Candidates from `apparition_service.surface_for(card_id)` (the frontend fetches; it never ranks — §2.1) place at polar coordinates around the focal: angular by nomic direction, radial by `r = r_focal + r_inner + (1 − normalized_score)·r_extent`. Below `min_score_threshold` (default 0.3) candidates fall off the visible halo (scale-space periphery). Each phantom is a `ConceptView` in `phantom` mode — **name only** (§4.5, frontend_rendering §1.7, §18.21).

**Ray-projection (§8.2.1.1).** When the focal's `data-3d-node-id` resolves to a projector chunk, the focal's manifold-nearest chunks (positions read from the store's `layout` slice — the frontend reads, never computes) project onto the cone whose apex is the focal-panel centre and whose lateral surface is the halo's outer ring. Each projector-neighbour lands as a **collapsed singular node** carrying its image billboard (via `TextureCache`, §5.6) or its **slowly-rotating HSV colour** read from the chunk's 6-vector — and rotated **in lockstep with the parent chunk** by the same camera-azimuth phase (§8.2.1.2, frontend_rendering §1.8/§1.15, §18.26). This is the Real ↔ Imaginary superposition made visible: every phantom is simultaneously a soft-link candidate by rank and a manifold-neighbour by geometry.

**Autoregression (§8.2.2).** A phantom click commits a hard link, spawns a new focal `ConceptView`, and opens a new Halo around it — the Editor renders the recursion one click at a time. The Halo is re-entrant: halos open on compiled-graph children identically (§8.2.3), because the apparition surface is uniform across all ConceptNode kinds.

### §7.3 `LinkLayer` — solid links + the 2D↔3D arrow

One SVG layer beneath the panels. Draws: hard-link commitment fan and soft-link possibility ring (§6.3); compiled-graph **stringless edges** (§7.3); and the **2D↔3D link arrow** — a single **solid yellow** line (`stroke="#ffd700"`, `stroke-width="2"`, **never** `stroke-dasharray` — §18.7, frontend_rendering §1.6/§2.3) from a pinned panel to its chunk's projected screen position. The arrow updates per frame from the 3D node's projected position (it is the one place a 3D coordinate is *read* into 2D space) but it **drives nothing** — it does not move the panel (§6.6.2, §18.31). Off-frustum nodes set their arrow `display:none`; they never render a dashed placeholder (§18.7).

### §7.4 The separation contract, enforced at the object boundary (§6.6.2)

The three membranes are the complete set of legal crossings, each one-way:

| Crossing | Membrane | Direction | What crosses |
|---|---|---|---|
| pin a chunk | Billboard (§7.1) | Real → Imaginary | a screen rect (not a 3D coord) |
| ray-project neighbours | Halo (§7.2) | Real → Imaginary (read) | chunk world-positions + HSV, read into a 2D cone |
| draw the link arrow | LinkLayer (§7.3) | Real → Imaginary (read) | a 3D node's projected screen point, for drawing only |
| project an output | (backend §9.12) | Imaginary → Real | a 2D card emits a chunk that lands at perimeter coords |

There is **no** Imaginary → Real *coordinate* write on the frontend (output projection is a backend step, §9.12) and **no** Real → Imaginary write that moves a pin. Any code that synchronises 2D pin position to 3D motion violates §18.31 — and with the crossings localised to three objects, such code has nowhere to hide.

---

## §8 — The Symbolic Seam: Telemetry Completeness (§14)

The REPL (the Symbolic register, §1.5/§14) runs outside the browser. The frontend's entire obligation to it is **faithful, complete telemetry**: *what you rendered, you report.* After any render settles, the responsible view calls `GestureGateway.telemetry(kind, snapshot)` (§3.3) which feeds the UI State Service mirror (§10.5); the REPL's in-place viewer (§14.5/§11.8) reads the same frames.

The contract (§14): **a Real or Imaginary state not reflected in the Symbolic is a severance** (§18.1). Concretely — a pin must emit `pinned_panels` + `pin_chrome`; a latch toggle must emit `latch_state`; a scroll must emit `viewport_visible_rows`; a halo open must emit `halo_focus`; a compile-expand must emit `compile_expansions`; a signal advance must emit `signal_stream`. The §10.5.1 mirror-field roster is the checklist; every field a view can change must have a setter the view calls. The frontend adds **no parallel log stream** — new observable state extends an existing §11.8 viewer row (§14.4.4). Because every gesture already round-trips through the gateway → backend → frame (§1.1), the telemetry is largely *automatic*: the same frame that updates the store updates the mirror. The seam's only standing duty is to ensure no view mutates a mirror-able value without routing it through a setter.

---

## §9 — Liveness and Fluidity: The Cross-Cutting Pulse *(priority #2)*

Every organ and membrane schedules its motion through one engine. This is why a streaming scan (§5.4) and a cascading edit (§6.4) stay smooth *simultaneously* — they share a budget and a discipline rather than competing rAF loops.

### §9.1 The `Reconciler` — keyed enter/update/exit, minimal mutation

Store subscriptions deliver `(next, prevKeyset)`; the Reconciler diffs by key (concept_id, chunk_id, edge_id) and emits the minimal mutation set: **enter** (new key → create DOM/mesh node), **update** (changed value → patch in place), **exit** (missing key → remove). Nothing is ever torn down and rebuilt wholesale. This is what makes a 500-chunk scan add the 501st chunk without touching the first 500, and a cascade re-render one card without reflowing the canvas. It is the structural opposite of the legacy "re-render the world on any change" pattern that bred the overhang.

### §9.2 The tween scheduler — interruptible, eased, rAF-driven

All motion — chunk settling (§5.2), camera frame-on-scan (§6.2-domain), link re-route (§6.4), halo radius changes (§6.4), HSV phase (§5.5) — is an eased tween advanced once per frame. Tweens are **interruptible and retargeting**: a new target mid-flight recomputes from the *current interpolated value*, never restarting from the origin (§5.4 step 2). This single property is the difference between "settles smoothly" and "stutters on every refit." No tween holds authoritative state; the target is always read from the store, the position is transient.

### §9.3 Backpressure and resume — smoothness under load

The FrameBus rules (§3.2) are a liveness mechanism: dropping stale progress frames while keeping structural truth means the render budget is spent on the *freshest* state, not on draining a backlog. Resume (`?resume=<seq>`) means a dropped connection re-syncs without a full reload — the store is patched from the replay, the Reconciler applies the delta, and the canvases tween from where they were.

### §9.4 Edit-safety — never clobber an open editor

An open textarea (§4.2.5) is transient interaction state owned by its `ConceptView` (§4.1). Incoming `concept_changed` frames reconcile *around* it: other fields of the same card update; the open field's textarea value and caret are left alone until the user commits or blurs, at which point the commit is the reconciliation. This is enforced in the Reconciler's update path (an open-edit field is a no-op target for frame-driven updates) and is what lets the cascade run continuously (§7.4 default) without fighting the user's typing.

### §9.5 The frame budget — one rAF, no layout thrash

There is exactly one `requestAnimationFrame` loop. Per tick it: advances tweens, runs the Projector animate invariants (§5.5), flushes the Reconciler's queued mutations, and re-routes any dirty links — then yields. Reads and writes are batched to avoid layout thrash (measure-then-mutate, never interleaved). Telemetry (§8) and gesture POSTs (§3.3) are debounced/batched off the critical path. The budget is the reason the answer to "is it fast enough?" is structural, not incidental.

---

## §10 — Activity Flows (end-to-end object choreography)

Each flow shows the objects composing through a complete gesture; each maps to a §17 functional sequence. These are the proof that the object set is *whole* — every named gesture is expressible as a path through these objects with no gap.

### §10.1 Outside-in: scan → live 3D → spine → click-and-stick → compile → halo (§16.1)

`GestureGateway.web-scan` (§3.3) → backend → `chunk_added` × N stream into `FrameBus` → `WorkspaceStore.chunks` grows → `Projector` Reconciler enters instances at preliminary radial (§5.2) → `umap_canonical` frames tween them to canonical 6D (§5.4) with HSV applied (§5.5) → `pattern_map` ConceptNode materialises, rendered by `ConceptView`+`FieldTree` under signal-stream (§4.2.8) → retrieval rows render collapsed-hidden (§8.3); scroll fires `ui-viewport-spine` (§17.14) → `Projector` extrudes only viewport chunks → hover a row → `Billboard` previews (§7.1) → click → freeze-at-rect pin into `Editor` (§5.3) → right-click → compile-expand → `Editor` lays out `child`-mode views (§4.3) → hover a child → `Halo` radiates with ray-projected HSV phantoms (§7.2).

### §10.2 Inside-out: empty primitive → radiation → wire → {var} → compile chain (§16.2)

`GestureGateway` creates an empty primitive → type a description → `concept-edit-description` → backend re-embeds, broadcasts `concept_index_update` → `Editor` opens a `Halo` whose candidates are the multi-frequency apparition surface (§8.2.1, fetched not computed) → click a phantom (Agent.prompt, Database.concept, WebBrowser.scan) → `concept-edge-create` promotes soft→hard along the commitment fan (§6.3), autoregresses a new focal+halo (§7.2) → type `{var}` refs → autocomplete binds (§4.2.7) or auto-creates (§17.8) → right-click compile → the backend LangGraph chain runs (§10.6); the frontend renders the resulting renderings via `FieldTree`; closest-inverse suggestions (§7.7) surface on unwired ports as soft links the user accepts.

### §10.3 Agent tick → token stream → emissions render (§16.3)

`agent-spawn` → four ConceptViews (parameter/perception/transformer/emitter) appear wired (§12.1) → `agent-tick` → `agent_token` frames stream into `WorkspaceStore.tokens` → the transformer `ConceptView`'s body appends tokens live (a ring-buffer render, §3.1) → the emitter's structured actions apply through the lifecycle and broadcast `concept_changed` for each emission → the `Editor` Reconciler renders new cards/edges; agent-output chunks land at the projector perimeter (§5.5, §6.6.1). The agent's emissions are *Editor calls* (§12.6.1) — they enter the same store the user's edits do, so the frontend renders user and agent authorship identically (attribution is the `evolution_diff` actor, §11.4).

### §10.4 Signal-stream iterated rollout — play/pause (§16.4, §7.5)

A `pattern_map` or `{urls_panel}` or `Database.concept([ids])` field renders one signal (§4.2.8). `rollout-play` advances the signal index per step (`ui-signal-advance`, §17.1.2); the `FieldTree` swaps the visible print form in place; the cascade re-fires per signal (§6.4). `rollout-pause` reveals edit affordances on the paused node (plus-signs, §4.2.6); an edit between iterations changes the next iteration's input; `rollout-play` resumes with the edited content. The full iteration position is legible only in the REPL viewer's `signal_stream` row (§8) — never as an in-panel overlay (§18.24).

### §10.5 Coverage

Every row of the §14.2 gesture catalogue is a path through these objects; every §17.x sequence has a frontend choreography above or a trivial composition of them (purge → store reset §3.1; rollback → `concept_changed` re-render §6.4; pin chrome → §6.2; latch → §4.1). If a future gesture cannot be expressed as such a path, the object set is incomplete and §12.3 governs the extension.

---

## §11 — Module Layout (the fresh tree; what dissolves)

A clean directory, one module per object, no overlapping responsibilities. (Path is illustrative — `backend/static/js/fe/` to signal the break from legacy `cp/`; the actual location is a code-time decision.)

```
fe/
  spine/
    frame_bus.js        §3.2   the one inbound seam
    store.js            §3.1   normalized observable mirror
    gateway.js          §3.3   the one outbound seam + telemetry + idempotency
  cell/
    concept_view.js     §4.1   the one anatomy, three modes
    field_tree.js       §4.2   the recursive data→pure-print interpreter
    field_strategies.js §4.2.2 JSON / list / indent / HTML / plaintext parsers
  real/
    projector.js        §5     Three.js scene + animate invariants
    chunk_field.js      §5.2   InstancedMesh, stable ids, placement states
    texture_cache.js    §5.6   single image fetch path
  imaginary/
    editor.js           §6     2D canvas, pins, cascade reflow
    subgraph_layout.js  §6.5   ray-constrained placement
  membranes/
    billboard.js        §7.1   hover preview → freeze-at-rect
    halo.js             §7.2   concentric radiation + ray-projection + HSV
    link_layer.js       §7.3   solid links + 2D↔3D arrow
  pulse/
    reconciler.js       §9.1   keyed enter/update/exit
    tweens.js           §9.2   interruptible eased scheduler
    raf.js              §9.5   the one frame budget
```

**Legacy dissolution** — every legacy responsibility lands in exactly one new home; no structure carries over:

| Legacy `cp/` | Responsibility | New home |
|---|---|---|
| `billboard.js` | `_buildPanelDom`; hover; pin | split: anatomy → `concept_view.js` (§4.1); hover/pin → `billboard.js` membrane (§7.1) |
| `concept_graph.js` | panels; plus-signs; field-tree; signal-stream | split: tree → `field_tree.js` (§4.2); canvas/layout → `editor.js` (§6) |
| `scanner.js` | chunk add; HSV per chunk | `chunk_field.js` (§5.2) + store `chunks` slice (§3.1) |
| `animation.js` | camera bounds; resize; HSV phase; arrow | `projector.js` animate (§5.5) + `raf.js` (§9.5) + `link_layer.js` (§7.3) |
| `search.js` | result list; spine; row click | `editor.js` result list + `ui-viewport-spine` gesture (§10.1); store-driven |
| `workspace.js` | URL list; eye toggle; hidden set | `editor.js` URL list + store `ui.url_*` slices; visibility flag in `projector.js` (§5.5). (§S.3: the standalone retrieval *sidebar* surface is removed; URL visibility controls remain, retrieval is the in-editor halo.) |
| `sprite_manager.js` | image fetch; IDB cache | `texture_cache.js` (§5.6) |
| `instance_manager.js` | InstancedMesh management | `chunk_field.js` (§5.2) |
| `halo.js` (planned) | halo; ray-projection; HSV | `halo.js` membrane (§7.2) |
| `telemetry.js` | telemetry posting | folded into `gateway.js` (§3.3, §8) |

The collapse from "ten modules with cross-cutting state" to "objects with one seam each" is the redesign's whole structural claim.

---

## §12 — Composition with the Doc Chain and the Acceptance Bar

### §12.1 Where this doc sits

This file is the frontend's **domain+object anchor**, an elaboration of `DOMAIN_MODEL.md` that **supersedes** the historical [`MORTEGON_INTEGRATION_SCHEME.md`](MORTEGON_INTEGRATION_SCHEME.md) on frontend specifics (§O.17; Mortegon's additive operational detail is lifted into the design docs). Its **standalone reference suite** is [`frontend/`](frontend/) — 20 per-surface docs (one per object/feature, each with identity / structure / composition / behaviours / activities / sequences / data / results / REPL mirroring / theme), indexed by [`frontend/README.md`](frontend/README.md) and themed by [`frontend/theme.md`](frontend/theme.md) (dark-minimal stainless-steel-over-black). This doc is the anchor; the suite is the detail. The existing `object_model/` frontend component docs ([`KnowledgePanel.md`](object_model/KnowledgePanel.md), [`FieldTree.md`](object_model/FieldTree.md), [`Halo.md`](object_model/Halo.md), [`Billboard.md`](object_model/Billboard.md), [`Projector.md`](object_model/Projector.md), [`PatternMap.md`](object_model/PatternMap.md), [`URLSetPanel.md`](object_model/URLSetPanel.md)) should be **reconciled to the object set here** — `KnowledgePanel.md` → `ConceptView` (§4.1); `FieldTree.md` → §4.2; `Halo.md` → §7.2; `Billboard.md` → §7.1; `Projector.md` → §5. The three new Spine objects (`WorkspaceStore`, `FrameBus`, `GestureGateway`) and the Pulse objects (`Reconciler`, tween scheduler) have **no current object doc** and should get one when this redesign is adopted (per DOC_MAP §5.2). `code_constraints/frontend_rendering.md` is downstream and authoritative on programming-surface specifics; this doc's §3–§9 are consistent with its §1 must-hold list by construction (each constraint is assigned to an owning object above).

### §12.2 The frontend acceptance bar

A frontend feature is complete when (mirroring §14.4): (1) the gesture exists as a `GestureGateway` kind = a §14.2 catalogue row with a REPL action; (2) an env-scenario asserts the REPL→backend→frame→render→telemetry round-trip; (3) `full-smoke` passes in real-stack and stub mode; (4) the §11.8 viewer reflects the observable state with no new log stream. **A screenshot is never proof** (§2.9) — verification is the REPL round-trip, which this architecture makes total because every gesture and every render route through the two seams (§1.1, §8).

### §12.3 What this structure forbids (and why each anti-goal cannot recur)

The object set is chosen so each §18 anti-goal is *structurally* impossible, not merely *currently avoided*:

| Anti-goal | Structural prevention |
|---|---|
| §18.11 two panels | one `ConceptView`, mode is a parameter (§4.1) |
| §18.8 pin in wrong place | `Billboard` captures the rect; `Editor` sets it byte-for-byte (§5.3, §7.1) |
| §18.4 stale URLs after purge | views read the store; `purge_workspace` clears the store in one transaction (§3.1) |
| §18.1 scan/stream severance | one `FrameBus` on the workspace WS; it sees the chunk-gap (§3.2) |
| §18.7 dotted lines | `LinkLayer` is the only line-drawer and emits no `stroke-dasharray` (§7.3) |
| §18.21 halo score chips | `phantom` mode has no score slot (§4.2.4) |
| §18.24 full-iterable render | `FieldTree` renders one signal; the rest stay in the store (§4.2.8) |
| §18.31 2D/3D coupling | crossings localised to three membranes, each one-way (§7.4) |
| §18.2 concentric-sphere layout | `Projector` renders coordinates it never computes (§5.1); placeholder is transient (§5.2) |
| overhang generally | no authoritative frontend state to drift (§1.1, §1.4) |

### §12.4 The single sentence

The frontend is a **fluid, faithful projection of canonical state through one inbound seam and one outbound seam, rendering one record in three forms via one data-self-defining interpreter, across two coordinate-separate canvases joined by three one-way membranes, all moving on one interruptible frame budget** — minimal because there is nothing in it that the design did not name, and whole because every gesture the design names is a path through it.
