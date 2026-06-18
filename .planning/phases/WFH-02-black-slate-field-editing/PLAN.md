# Phase 2 — Black-Slate Field Editing — PLAN

> Executable plan for EDIT-01/02/03. Brownfield finish-and-verify: the §T slate
> is served at `/`; EDIT-03 is resolved to **Milkdown** (the editable layer, per
> [`docs/MILKDOWN_SLATE_GOAL.md`](../../../docs/MILKDOWN_SLATE_GOAL.md)). Every
> task's success criterion is a runnable command from
> [`.planning/TEST_MATRIX.md`](../../TEST_MATRIX.md) — never a screenshot (D1).
> Each task un-fixmes one acceptance spec; the framework (`npm run test:all`) is
> the gate, green in both stub and real modes.

**Status legend:** ☑ done · ☐ todo. **Depends on:** Phase 1 (complete).

## Tasks

### T1 — Milkdown editable surface mounts + controlled-view seam ☑ DONE
- **Surface:** `frontend_src/milkdown_slate.mjs` → `backend/static/js/fe/vendor/` (esbuild), `backend/static/js/fe/milkdown_demo.html`.
- **Steps:** `mountMilkdown(host, text, {onCommit})`; inbound `setText` replace-all (store→view); outbound `onCommit` on blur (→ gateway); black-slate styling.
- **Done-when:** `frontend_e2e/milkdown.spec.js` — mounts+renders, §S.4 black slate, inbound `setText` round-trip, outbound commit. **(4/4 green on the real backend.)**

### T2 — Recursive `{ref}` rendering in the Milkdown view ☑ DONE  (EDIT-01/02, "recursive rendering")
- **Surface:** `frontend_src/milkdown_slate.mjs` (record mode: `linesToMarkdown` + a stateless `refFoldPlugin` ProseMirror decoration) driven by `magic_markdown.mjs::renderPanel`; `backend/static/js/fe/milkdown_record_demo.html` (two-level ref chain).
- **Steps:** field-tree → nested commonmark list; the ▸/▾ glyph is a clickable `Decoration.inline` (`.mm-ref-fold[data-fold-index]`); a click toggles `expanded` and re-renders through the model via the same `setText` replace-all seam; recursion + collapse fall out of `renderPanel`.
- **Done-when:** un-fixme `milkdown.spec.js` "recursive {ref}". **(green — 5/5 incl. recursive expand→recurse→collapse-restores; browser-verified.)**

### T3 — Click-to-edit: caret-at-click, Shift-Enter, Enter-commit, Esc ☐  (EDIT-01)
- **Surface:** `magic_markdown_panel.mjs::mount` (swap the textarea path for the Milkdown field editor behind `WFH_SLATE_EDITOR=milkdown`); keymap.
- **Steps:** single-left a printed token → Milkdown edit on that field, caret at the click point; Shift-Enter soft-newline; Enter commits (fires `editor-overwrite`); Esc discards; empty rows hide.
- **Done-when:** un-fixme `edit.spec.js` EDIT-01 + `env-scenario --name click-to-edit` / `edit-field-roundtrip` green.

### T4 — `{`-autocomplete + `+→`/`+↓` field growth, lifecycle-routed ☐  (EDIT-02)
- **Surface:** Milkdown input rule for `{`; Tab/Shift-Tab/Enter keymap mapping to the §3 grammar; `gateway.mjs`.
- **Steps:** typing `{` opens autocomplete over concept names → inserts `{name}`; Tab/Shift-Tab re-parent, Enter sibling; every commit routes through `concept_lifecycle.py`.
- **Done-when:** un-fixme `edit.spec.js` EDIT-02 + `env-scenario --name editor-primitives-roundtrip` / `autocomplete-state-roundtrip` (asserts the `concept_index_update` WS frame + evolution-log entry).

### T5 — Gestures resolve over the Milkdown DOM ☑ DONE  (EDIT-01/02)
- **Surface:** `frontend_src/milkdown_slate.mjs` (`classifyTarget` + `installGestures`) wires `magic_markdown_gestures.mjs::resolveGesture` over the Milkdown container.
- **Steps:** left gestures via mousedown (fold beats the caret), right via contextmenu with a single/double debounce; `dropdown`/`ref`/`self`/`token`/`body` classification → TOGGLE_FOLD / TOGGLE_PANEL_GRAPH / DELETE_REF / COLLAPSE_TO_NODE; EDIT_TOKEN/NONE fall through to the native caret.
- **Done-when:** un-fixme `milkdown.spec.js` "gestures". **(green — single-left fold, double-left panel⇄graph, right-click fold, double-right delete all resolve over the real Milkdown DOM; browser-verified.)**

### T6 — §3 syntax round-trip identity through Milkdown ☑ DONE  (EDIT-02)
- **Surface:** `frontend_src/milkdown_slate.mjs::markdownToFieldText` (the reverse of `linesToMarkdown`) + `magic_markdown.mjs::parse`/`serialize`; `milkdown_syntax_demo.html`.
- **Steps:** `print(record) → Milkdown → read() → markdownToFieldText → parse → serialize` is identity for the §3 grammar (single root, forest, names-with-spaces, `{}` on-ramp, kv, `\_`-escape recovery, depth-2/3 nesting).
- **Done-when:** un-fixme `milkdown.spec.js` "syntax"; `magic_markdown.test.mjs` round-trip stays green. **(green — 6 grammar samples round-trip identically THROUGH a real Milkdown instance.)**

### T7 — No authoritative frontend state (EDIT-03 acceptance) ◑ CORE DONE
- **Surface:** the store↔Milkdown reconcile (`setText` is the ONLY inbound path; `store.mjs`/`gateway.mjs` unchanged).
- **Steps:** a dropped-WS reconnect re-pushes the store text and the view reconciles identically; no ProseMirror "state overhang".
- **Done-when:** un-fixme `milkdown.spec.js` "no authoritative frontend state" **(green — edit→diverge→reconnect(setText)→identical, no overhang)**. The `edit.spec.js` EDIT-03 reconnect against the served `/` editor lands with T3 (live Milkdown wiring).

## Coverage (req → task)

| Req | Tasks |
|---|---|
| EDIT-01 | T2 ☑, T3, T5 ☑ |
| EDIT-02 | T2 ☑, T4, T5 ☑, T6 ☑ |
| EDIT-03 | T1 ☑, T7 ◑ (core ☑; `/`-wiring with T3) |

## Phase gate
`npm run test:all` green in BOTH stub and real modes with every EDIT spec
un-fixme'd; `npm run test:all:real --fixture-scan` for deterministic real-stack
acceptance. T1+T2+T5+T6+T7-core done (8/8 milkdown.spec.js green). **Remaining:
T3 (live `/` editor: swap the textarea path for the Milkdown field behind
`WFH_SLATE_EDITOR=milkdown`; un-fixme `edit.spec.js` EDIT-01 + EDIT-03 reconnect)
and T4 (`{`-autocomplete + `+→`/`+↓` growth; un-fixme `edit.spec.js` EDIT-02).**
