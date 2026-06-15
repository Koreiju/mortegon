# FieldTree — The Flexible Recursive Interpreter

> **Status: realised (cp/*.js); greenfield object form in `FRONTEND_REDESIGN.md` §4.2.** The recursive-interpreter role is carried by `cp/concept_graph.js`: `_fieldTreePrint` (JSON data → pure-print tab tree, no braces/quotes), the `<pre class="concept-value-print">` click-to-edit display layer, the §6.1 Tab/auto-indent keydown, the §6.2 `+→`/`+↓` plus-signs (`_growRow`), and the §7.3.4 right-click-token inline fold (`node_fold`). The data block is self-defining; empty rows hide. Verified by `edit-field-roundtrip`, `node-fold-roundtrip`. This is the most-reused renderer in the suite.

---

## §1 — Identity

`FieldTree` is the data-agnostic recursive tree interpreter for the `data` field across every surface and every `ConceptView` mode (`concept_view.md`). It realises the user's requirement directly: *structured fields are fully self-defined by the data blocks, recursively processed into their pure-print text-tree structure renderings.* There is **no declared field shape anywhere in the frontend** — a card's structure is whatever *parsing* its data string yields, computed fresh on each render. Add a line to the data and a row appears; nest it under a tab and it becomes a child — because the parser saw it, not because anything was registered.

It runs six phases: **parse → normalize → print → project → edit → serialize**. The first four produce the rendering; the last two close the round-trip back through the backend.

---

## §2 — Structure

**The normalized intermediate** — one node type regardless of input syntax:

```
FieldNode {
  key:      string | null        // null for positional/list elements
  value:    string | null        // scalar leaf text (may be multi-line, may contain {var})
  children: FieldNode[]          // structural descent
  path:     string               // dotted address within the card, e.g. "ports.inputs.0.name"
  meta: {
    ref?:      string            // a {var} reference token, preserved verbatim
    type?:     string            // strict type annotation (the type slot, §9.6.1); may itself be a {ref}
    attr?:     boolean           // an HTML attribute, folded as an @attr child
    cypher?:   boolean           // a MATCH…RETURN / CALL… span, flagged for backend §7.1 step 4
    iterable?: { total:int, signal_index:int }   // signal-stream gate (§7)
    readonly?: boolean           // python-native field or the `rendering` row (§9.6)
  }
}
```

**The four canonical rows** (`name`, `description`, `value`, `rendering`) are `FieldNode`s with reserved key slugs and a default starting shape; the user grows arbitrary rows around them (§5). **Owns (transient):** the parsed tree for the current render; which node is in edit; caret offset; the live edit textarea. **Reads:** `concepts[id].data` (opaque string), `ui.signal_stream`, `ui.autocomplete_state` from `WorkspaceStore`.

---

## §3 — Phase 1: Parse — one descent, syntax strategies, one tree

A single recursive descent recognises JSON, bracketed lists, indented (tab/space) trees, HTML element trees, and plain text, emitting one `FieldNode` tree regardless of input syntax. The greenfield design factors this into **strategies behind one interface** (`field_strategies.js`):

| Strategy | `detect(raw)` | `parse(raw)` | Realised? |
|---|---|---|---|
| `JsonStrategy` | parses as JSON | objects → keyed children; arrays → positional children; scalars → `value` leaves | **yes** — `_fieldTreePrint` (concept_graph.js): `{`/`[` prefix → `JSON.parse` → recursive tab-tree walk |
| `BracketListStrategy` | `[a, b, c]`-shaped | positional children, no keys | **yes** (via the JSON `[…]` array path of `_fieldTreePrint`) |
| `PlainTextStrategy` | always (fallback) | a single `value` leaf | **yes** — non-`{`/`[` input is returned verbatim (passthrough) |
| `IndentTreeStrategy` | leading tab/space structure | fold by indentation depth alone | **greenfield** — not yet realised (indented non-JSON is passed through, not re-folded) |
| `HtmlStrategy` | tag-shaped | element name → key; attributes → `@attr` children | **greenfield** — not yet realised |

The first to `detect` wins; `PlainTextStrategy` always detects. **No syntax branch escapes the parser** — downstream phases see only `FieldNode`. **Realised state:** the parse is inline in `cp/concept_graph.js::_fieldTreePrint` (JSON-or-passthrough), NOT a separate `field_strategies.js` module; the IndentTree/Html strategies are design intent for when non-JSON authored structure needs re-folding. This is symmetric with the backend's `decompose_recursive` (§7.1, §18.15) so the two agree on the tree; the frontend parses for *rendering*, the backend parses for *compile*, and they produce the same structure.

**Key-value vs multiline by consistent tabs; `{}` on-ramp (§O.20).** Within a parent `FieldNode`, `IndentTreeStrategy` distinguishes a **key-value** child (inline value) from a **multiline** child (key = primary key; its value is the consistently-tab-indented block beneath it) purely by indentation — no syntax markers. A new field's on-ramp is a **spaces-bearing key beside a singular empty `{}`** (the unbound `{ref}` slot, §O.1 / §9.6.2). This is what lets **pydantic templates** be authored as field-trees rather than JSON schema (§O.20 / §7.2): inferred field names, `{var}` content, Tab/Shift-Enter handlers (§6.1).

`{var}` tokens are captured into `meta.ref` and left in the `value` verbatim; cypher spans set `meta.cypher` (rendered as plain text on the frontend — execution is backend-only, §7.1).

---

## §4 — Phase 2/3: Normalize & Print — the pure-print projection

**Normalize** flattens redundant wrappers, attaches `path` addresses, and marks `meta.iterable` where a value is an unbounded-cardinality collection (§7). **Print** (`print(tree) → string`) walks the tree to the canonical syntax-stripped form (§8D.20 tree-pretty-print):

- one `key : value` per line (or `key : Type = value` for typed nodes — the **type slot**, §9.6.1 / `object_exploration.md`); nesting by **tab depth**;
- multi-line values absorbed into the parent's indentation — **no escaped-newline glyphs**;
- **no braces, no brackets, no angle brackets, no dashes, no quotes** (frontend_rendering §2.7);
- positional (keyless) children print their value only, indented under the parent.

The print is the resting visual of every editable field on every surface — what the user sees until they click. It is rendered in **monospace** (`theme.md` §5) because tree alignment depends on a fixed advance width.

---

## §5 — Phase 4: Project — three representations from one tree

The same `FieldNode` tree projects to all three representations of §4.5 by **eliding, never re-parsing**:

| Representation | Projection | Used in mode |
|---|---|---|
| **Unfolded** | every node prints `key : value`; every node editable | `panel` |
| **Child** | print **value only**; key implied by tree position; box form-fits the value | `child` |
| **Phantom** | print the **root key (name) only** | `phantom` |

One parse, three elisions — the compact-representation standard (§4.5) is free, and the §18.21 score-chip regression is impossible because the `phantom` projection has no slot for a score.

---

## §6 — Phase 5: Edit — hidden-overlay buttons, caret mapping, plus-signs

### §6.1 Click-to-edit (§4.1.1, frontend_rendering §1.3/§1.4)
Each printed token region carries a **transparent overlay button** sized to its bounding rect. At rest it is invisible; on hover its silver outline brightens to `--steel-300` (no fill tint — everything stays black, `theme.md` §4); on click it is *replaced in place* by a `<textarea>` pre-populated with the node's value, **caret placed where the click landed** in the printed text. Commit: **Enter** commits via `gesture_gateway.md` and returns to print; **Shift-Enter** inserts a literal newline without committing; **Escape** discards to the prior value; **blur** commits identically to Enter. The cascade (§7.4) is *not* nudged per keystroke — only on commit (edit-safety, `liveness.md` §4). Read-only nodes (`meta.readonly`) do not enter edit; the click briefly highlights (frontend_rendering §2.9). **Single-left-click edits; right-click is reserved for the inline next-rank type-graph fold** (`object_exploration.md` §4–§5, §7.3.4) — the two never collide because the edit targets a token's interior while the fold toggles its subtree; double-left-click on the panel body is the panel↔graph compile (`compile_collapse.md`). Multiline editing within a single field uses **intelligent Shift+Enter and Tab parsing** (N.12) — Tab indents, Shift+Enter inserts a newline, and the editor auto-indents over the tree structure the way a markdown editor does, so multi-curly-brace template references stay manageable without surfacing escaped-newline glyphs in the print form.

### §6.2 Plus-sign growth (§4.6, frontend_rendering §1.5)
When a node is in edit state, two cutout affordances appear *concatenated into the print tree itself*: **`+→`** (right) adds a **child** row indented one level; **`+↓`** (bottom) adds a **sibling** at the same level. Hover previews the slot as a faint print placeholder; click materialises a real row **already in edit state** (the user types immediately). Each new row is a full `FieldNode` with its own capacity to grow children — which is exactly why a singular compute node and a full panel are *the same record at different sizes* (§4.6): field-tree growth **is** the promotion; there is no "promote to panel" affordance.

---

## §7 — Signal-stream gating under iteration (§4.6.1, frontend_rendering §1.14)

When a `FieldNode` carries `meta.iterable`, `FieldTree` renders **only the current signal element** — `data[signal_index]` from `ui.signal_stream["card_id::path"]` — and nothing else. The suppressed elements remain in the node's underlying data (held in `WorkspaceStore`, never dropped) and are advanced by the rollout coordinator via `ui-signal-advance` (`agent_and_rollout.md`); on advance, `FieldTree` swaps the one visible print form in place and the cascade re-fires per signal. **No "iteration 3 of 12: [c1,c2,c3]" overlay** — that is the §18.24 violation; the full position is legible only in the REPL viewer's `signal_stream` row (§9). This one rule lets `Database.concept([ids])`, `{urls_panel}` (`pattern_map_and_url_set.md`), and `pattern_map` all render under one minimalist contract.

**Iteration ⟺ external `{ref}` (§O.19).** Recursive chunk iteration (the per-instance signal-stream) is applied **only** when the iterable is externally referenced via `{curly brace}` — inline-rendered content is never iterated. The iterable is rooted at its base node, so a referencing panel dynamically updates from the root source down to its fields (§O.19).

---

## §8 — Phase 6: Serialize — the round-trip

An edit mutates the in-memory `FieldNode` tree; **`serialize(tree)`** re-emits the canonical pure-print form; the gateway POSTs it (`concept-edit-data-row` / `field-tree-add-child` / `field-tree-add-sibling`); the backend persists it (as JSON internally — the user never sees JSON) and broadcasts `concept_changed`; `FrameBus` updates the store; `ConceptView` re-renders the field from the **authoritative** data. Even the user's own edit round-trips through the backend (§1.1-FR); the optimistic echo (`gesture_gateway.md` §4) merely hides the latency. **The user edits a tree; the wire carries print; the store holds truth; the screen shows print** — syntax never surfaces at any point.

---

## §9 — Activities, Sequences, Data, Results

**Activities/gestures:** `concept-edit-data-row`, `field-tree-add-child`, `field-tree-add-sibling`, `concept-edit-description`, `concept-rename`, `ui-autocomplete-open/-close`, `ui-signal-advance`.

**Edit sequence:**
```
click print token → overlay button → textarea (caret at click offset)
   type … (Shift-Enter newline; {var} typed verbatim; autocomplete on key field §6/§4.7)
   Enter/blur → serialize(tree) → gateway concept-edit-data-row {id, path, value}
   → concept_changed → store → re-render print  (cascade re-fires downstream, §7.4)
```
**Data in:** `concepts[id].data` (string), `ui.signal_stream`, `ui.autocomplete_state`. **Data out:** the serialized pure-print data via the edit gestures.
**Results:** the printed/edited field; downstream cascade renderings update via `editor.md` §6.4.

---

## §9.1 `{var}` references & autocomplete (§4.7, §17.15)

A `{slug}` in any value is preserved by the parser (`meta.ref`), printed verbatim, and resolved at compile on the backend (§7.2) — never on the frontend. A `{ref}` is an **activation of a memory-access procedure elsewhere in the app** (N.10): it resolves another node/instance and renders its value or rank-1 structure in place. The text **beside** a `{ref}` is an **optional organising label** (not part of the reference), and because the tree is discerned over `\t` + `\n` only, **node names may contain spaces** (`scan for duckduckgo url` is one name). A braceless token is a literal/label; the braced form is the activation (`object_exploration.md` §5.1). Typing into a *new row's key* opens autocomplete: `ui-autocomplete-open` + `GET /api/concept_completions?prefix=&parent_card_id=`; selecting a candidate inserts `{<linked_name>}` into the value. When the slug matches no node, the backend's variable auto-creation (§17.8) spawns the empty primitive; the frontend renders the resulting `concept_changed`. Scoped completions (inside a python-bound card) restrict to the object's properties/functions and their `FUNCTION_INPUT/OUTPUT_TYPE` chain (§4.7).

---

## §10 — Theme

Pure-print is **monospace `--text-primary`** over a `--bg-recess` body (`theme.md`). The `:` separator is `--text-dim`. Hover on a token: the silver outline brightens to `--steel-300` (no tint, no fill — everything stays black; the reveal is the edge catching light, `theme.md` §4). Edit textarea: `--bg-edit` fill, `--steel-100` 2px border. Plus-signs `+→`/`+↓`: `--steel-500` glyphs, `--steel-100` on hover, rendered inline in the print so they read as part of the tree. `{var}` tokens: `--text-primary` with a faint `--steel-700` underline to mark them as references without colour. Broken `{var}` (backend-flagged): `--accent-error` underline. Read-only rows: `--text-lock`, no hover reveal. **No JSON/HTML/YAML glyphs ever appear** (frontend_rendering §2.7) — the steel-on-black print is the only form.

---

## §11 — References

- `DOMAIN_MODEL.md`: §4.5 (compact representation / data dissolves), §4.6 (plus-sign field-tree), §4.6.1 (signal-stream), §4.1.1 (click-to-edit), §4.7 (autocomplete), §4.8 (`{var}`), §7.1 (recursive syntax-agnostic compile), §8D.20 (tree-pretty-print), §17.8 (variable auto-creation), §18.15/§18.24 (anti-goals).
- Object doc: there is no `object_model/FieldTree.md` (it was never created — superseded by this suite per `object_model/README.md`). This doc is canonical for the FieldTree surface.
- Peers: `concept_view.md`, `compile_collapse.md`, `object_exploration.md` (the typed `key:Type=value` exploration + five-gesture model), `agent_and_rollout.md`, `pattern_map_and_url_set.md`.
