# Design Assessment — Established Markdown Editor vs. the Custom Magic-Markdown Slate (2026-06-14)

> **⚠️ DECISION OVERRIDE (2026-06-17): the user chose MILKDOWN for the editable
> slate layer**, superseding this doc's CM6 lean / Milkdown-rejection (§2/§3
> below). The binding spec is now [`MILKDOWN_SLATE_GOAL.md`](MILKDOWN_SLATE_GOAL.md).
> This assessment's engineering caveat still holds and governs the build: Milkdown
> rides ProseMirror's authoritative AST, so the integration must keep the frontend
> a pure projection (D10) by running Milkdown as a *controlled view* with the
> `WorkspaceStore` as sole truth (the no-authoritative-state mitigation is
> `MILKDOWN_SLATE_GOAL.md` §2; the EDIT-03 acceptance is reconnect-re-render
> identity). EDIT-03 = **Milkdown**, not "custom vs CM6".

> **Status: design assessment / decision input.** Triggered by the user's request to evaluate
> CodeMirror 6, Milkdown, and BlockNote (and the already-installed MDXEditor) for the §T Black-Slate
> 2D computation-panel editor. Grounded in the *actual current code* — `backend/static/js/fe/` is a
> working custom editor served at `/` — and the binding invariants in
> [`BLACK_SLATE_GOAL.md`](BLACK_SLATE_GOAL.md) (§T), [`USER_REQUIREMENTS_VERBATIM.md`](USER_REQUIREMENTS_VERBATIM.md)
> (§S/§T/§V), and `CLAUDE.md` ("backend computes; frontend renders").

## 0 — The decision in one paragraph

The slate is **not a markdown surface** — its grammar is *tabs + newlines only*, with `{ref}` as the
**only** markup (no `#`, `*`, lists, tables, links, HTML, YAML, JSON). It is **one text buffer ↔ one
backend record**, with the frontend holding **no authoritative state**. Those two facts eliminate the
three rich-text/WYSIWYG options: **Milkdown**, **BlockNote**, and **MDXEditor** are all
document-authoritative editors (ProseMirror/Lexical) built to render *markdown/blocks* — exactly the
competency the slate forbids, and exactly the state-ownership the architecture forbids. Only
**CodeMirror 6** is structurally aligned: a single-buffer text editor with an *externally controllable,
immutable* state and a decoration engine that renders-at-rest / reveals-raw-on-interaction **without
mutating the document** — which is precisely the slate's behaviour. The recommendation is therefore
**not** "adopt an editor framework" but the narrower, higher-ROI move: **keep the custom model
(`magic_markdown.mjs`) and the store/gateway seam, and adopt CodeMirror 6 only as the in-slate
text-edit + decoration layer**, replacing the hand-rolled `contenteditable`/`textarea` swap. Staying
fully custom (status quo) is the defensible alternative if the hand-rolled caret/IME/undo layer is not
causing pain.

## 1 — What the editor layer must satisfy (from the goal + invariants)

| # | Requirement | Source |
|---|---|---|
| I1 | **No authoritative frontend state.** Store is the only truth; edits round-trip text→REST→backend→`concept_changed`→re-render. | CLAUDE.md; BLACK_SLATE §4 |
| I2 | **Single text buffer per card** over `\t`+`\n`; names may contain spaces; `{ref}` is the only markup. | §3 (N.7, N.10) |
| I3 | **Rest = rendered text-tree; interaction = raw token**, WITHOUT mutating the doc string. | §3 (M.8), the agent's "decoration" insight |
| I4 | **Borderless blended click-to-edit**, caret lands where the click fell; `Enter`/blur commit, `Shift-Enter` soft-newline, `Esc` discard. | §3 (M.8) |
| I5 | **Custom gesture set** — right-click internalize/externalize, double-left panel⇄graph, double-right delete, left-drag wire, `{`-autocomplete. | §5 (M.6, N.4, E.5) |
| I6 | **Inline recursive `{ref}` expansion** (`▸/▾`) of the next rank, fold-state preserved. | §3/§4 (O.1, M.6) |
| I7 | **Dual representation** — the same record renders as a rectangular panel *or* a **circular graph node**; double-left flips. | §15.1 (V.5) |
| I8 | **Halo + 3D** — ray-projected phantoms above the slate, token-anchored, camera-coupled. | §7/§15.2 |

**Critical scoping fact:** I7 (circular node), I8 (halo/3D), and the projector are **outside any text
editor's remit** — they are SVG/WebGL already implemented in `magic_markdown_panel.mjs::graphVDom`,
`magic_markdown_halo.mjs`, `projector.mjs`. Any editor library can only ever cover the **panel-text
sliver** (I2–I6). This caps the upside of adopting one.

## 2 — Per-API tractability

### CodeMirror 6 — **structurally aligned (recommended substrate for the edit layer)**
- **State authority (I1): excellent.** CM6's `EditorState` is immutable and fully driven by
  transactions *you* dispatch; it has no opinion about where truth lives. You intercept `dispatch`,
  fire the gateway, and `setState` from the `concept_changed` frame. This is the documented "controlled
  editor" pattern — no framework fight.
- **Single buffer + custom grammar (I2): native.** CM6 is a *code* editor; arbitrary non-markdown
  grammars are the normal case. The tab-tree + `{ref}` parse is a thin `ViewPlugin`/`MatchDecorator`
  (or a small Lezer grammar if wanted) — your existing `parse()`/`renderPanel()` can drive it directly.
- **Rest-render / reveal-raw (I3): native and battle-tested.** `Decoration.replace` with a `WidgetType`
  swaps printed tokens for styled DOM at rest; on cursor-enter/hover you drop the decoration for that
  range to reveal raw text. This is exactly how Obsidian Live Preview works — CM6 is the proven engine
  for I3.
- **Borderless edit + caret (I4): this is the strongest reason to adopt CM6.** Caret-at-click, IME/mobile
  input, selection, soft-newline, undo/history, and accessibility are CM6's core competency — and
  precisely where hand-rolled `contenteditable` slates bleed.
- **Custom gestures (I5): low friction.** `EditorView.domEventHandlers` lets you own
  `mousedown`/`contextmenu`/`dblclick`; CM6 has no built-in right-click menu to suppress.
- **Inline `{ref}` expansion (I6): fits the decoration/widget model**, though the recursion logic stays
  in `magic_markdown.mjs` (unchanged).
- **Cost:** add `@codemirror/*` deps (no framework — stays vanilla/ESM, consistent with `fe/*.mjs`);
  rewrite the `mount` glue in `magic_markdown_panel.mjs` to build decorations from `renderPanel()` and
  route `dispatch`→gateway. **Medium effort, low invariant risk, high payoff on I4.**

### Milkdown — **misaligned (not recommended)**
- ProseMirror-based **WYSIWYG markdown** editor with an **authoritative internal AST**. Violates I1 by
  default: you'd run a constant PM-doc↔store reconciliation to demote PM to a view (fighting the
  framework). Its headline value (pretty markdown rendering, slash-commands) is **wasted** — the slate
  forbids markdown syntax (I2). You'd disable most of what you adopt and inherit PM's node-schema
  overhead. The custom grammar (tabs/`{ref}`) maps poorly onto PM's block schema.

### BlockNote — **least aligned (not recommended)**
- A Notion-style **block** editor on ProseMirror. Assumes typed blocks + authoritative state — the
  opposite of "one tab-indented text buffer with no frontend truth" (I1, I2). The block model and the
  circular-node dialectic (I7) don't map; you'd be bending the framework end-to-end.

### MDXEditor (`@mdxeditor/editor` — already in `package.json`) — **mismatch; recommend removing**
- MDX (**markdown + JSX**) on **Lexical**, **React**-first. Triple mismatch: (a) MDX/markdown vs the
  tab+`{ref}` grammar (I2); (b) Lexical's authoritative `EditorState` vs I1; (c) pulls in **React**,
  whereas `fe/*.mjs` is framework-free vanilla ESM. Its presence in deps looks like an earlier probe
  the custom build superseded. **Remove it** unless React is adopted wholesale (it is not).

## 3 — Recommendation & integration plan

**Recommended: Option A — custom model + CodeMirror 6 edit layer.**

Keep, unchanged:
- `store.mjs` (sole truth), `gateway.mjs` (gesture→route→frame) — the §9 one-way seam.
- `magic_markdown.mjs` (parse/print/`{ref}`/signals) — the grammar logic (already 18/18 tested).
- `magic_markdown_gestures.mjs`, `magic_markdown_halo.mjs`, `projector.mjs`, `graphVDom` — the
  gesture/halo/3D/circular-node layers editors can't cover (I5–I8).

Replace only the edit surface:
- In `magic_markdown_panel.mjs`, swap the `mount` contenteditable/textarea swap for a CM6 `EditorView`
  whose **decorations are derived from `renderPanel()`** (rest-render via `Decoration.replace` widgets;
  reveal-raw by dropping the decoration under the cursor) and whose **`dispatch` is intercepted** →
  `gateway.buildRequest('editor-overwrite'|'concept-edit-data-row', text)` → backend → `concept_changed`
  → `store` → `EditorState` reconfigure.
- Keep `panelVDom` as the pure-spec test seam; CM6 lives only behind `mount`, preserving the
  "magic in testable logic, DOM binding trivial" design.

**Acceptance (extends BLACK_SLATE §11):** print/parse round-trip identity unchanged; no authoritative
frontend state (a dropped WS reconnect re-renders identically); caret-at-click + soft-newline + `{`-
autocomplete behave in the borderless field; the §11 DOM audit still finds one editable region and no
chrome.

**Alternative: Option B — stay fully custom (status quo).** Justified because the editor covers only
I2–I6 while I1/I5/I7/I8 dominate the design and already work. Choose B if the hand-rolled caret/IME/undo
is not a pain point; choose A when borderless click-to-edit, IME, multi-line indent, and undo start
costing more than the CM6 integration would.

**Not recommended:** Milkdown, BlockNote, MDXEditor — markdown/block WYSIWYG frameworks whose document
authority and markdown competency both conflict with the slate's core design.

## 4 — Doc-reconciliation / next-step hooks
- This assessment feeds the §T phase of the GSD roadmap (`.planning/ROADMAP.md`): the §T frontend work
  is largely **built** (custom `fe/` tree, served at `/`); the editor-layer decision (A vs B) is a
  scoped sub-task, not a from-scratch build.
- If Option A is chosen: add `@codemirror/{state,view,language}` to `package.json`; remove
  `@mdxeditor/editor`.
- Verification remains REPL/scenario + live-browser per §V (a render is not proof).
