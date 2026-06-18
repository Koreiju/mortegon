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

### T3 — Click-to-edit: focused Milkdown surface, Enter-commit, Esc ☑ DONE  (EDIT-01)
- **Surface:** `backend/templates/editor.html` `onEdit` → `enterMilkdownEdit` behind `?slate=milkdown` (the browser-side equivalent of `WFH_SLATE_EDITOR=milkdown`; the bundle loads lazily, default path 100% unchanged); the gateway gains a `concept-update` → `PATCH /api/concepts/{id}` mapping (the real persistence path; `edit_close` is only the UI-mirror beacon).
- **Steps:** single-left a printed token → the whole card opens as a focused Milkdown surface (caret placed at end); Enter commits the full §3 data through the lifecycle (PATCH → `apply_update_lifecycle`, persisted); Esc discards; background WS re-renders are suppressed while editing.
- **Also fixed:** authored concepts never rendered — the wire payload keys by `concept_id` but `store.applyFrame`/`loadConcepts` read `c.id`; normalized centrally in `store.mjs` (+ `loadConcepts`).
- **Done-when:** un-fixme `edit.spec.js` EDIT-01. **(green ×2 — create→render→click→focused Milkdown→type→Enter persists; re-open→Esc discards; browser-verified. Caret-at-click *column* + `env-scenario click-to-edit` lifecycle-mirror assertion are the remaining refinements.)**

### T4 — `{`-autocomplete + `+→`/`+↓` field growth, lifecycle-routed ☑ DONE  (EDIT-02)
- **Surface:** `editor.html` `installAutocomplete` (a `{`-driven concept-name popup over the Milkdown contenteditable, inserting `{<name>}` via `insertText`); field growth is ProseMirror's native commonmark list keymap (Enter = sibling `+↓`, Tab = sink `+→`); commit → `concept-update` PATCH (T3).
- **Steps:** typing `{`+prefix pops the concept names → Enter/click inserts `{name}`; Enter adds a sibling row, Tab re-parents one rank deeper; `markdownToFieldText` maps the new list structure back to §3 tab depth; blur commits through the lifecycle.
- **Done-when:** un-fixme `edit.spec.js` EDIT-02 ×2. **(green — autocomplete inserts `{Target Node …}`; Enter-sibling + Tab-reparent persist at the right `\t` depth; both verified against the live `/` editor.)**

### T5 — Gestures resolve over the Milkdown DOM ☑ DONE  (EDIT-01/02)
- **Surface:** `frontend_src/milkdown_slate.mjs` (`classifyTarget` + `installGestures`) wires `magic_markdown_gestures.mjs::resolveGesture` over the Milkdown container.
- **Steps:** left gestures via mousedown (fold beats the caret), right via contextmenu with a single/double debounce; `dropdown`/`ref`/`self`/`token`/`body` classification → TOGGLE_FOLD / TOGGLE_PANEL_GRAPH / DELETE_REF / COLLAPSE_TO_NODE; EDIT_TOKEN/NONE fall through to the native caret.
- **Done-when:** un-fixme `milkdown.spec.js` "gestures". **(green — single-left fold, double-left panel⇄graph, right-click fold, double-right delete all resolve over the real Milkdown DOM; browser-verified.)**

### T6 — §3 syntax round-trip identity through Milkdown ☑ DONE  (EDIT-02)
- **Surface:** `frontend_src/milkdown_slate.mjs::markdownToFieldText` (the reverse of `linesToMarkdown`) + `magic_markdown.mjs::parse`/`serialize`; `milkdown_syntax_demo.html`.
- **Steps:** `print(record) → Milkdown → read() → markdownToFieldText → parse → serialize` is identity for the §3 grammar (single root, forest, names-with-spaces, `{}` on-ramp, kv, `\_`-escape recovery, depth-2/3 nesting).
- **Done-when:** un-fixme `milkdown.spec.js` "syntax"; `magic_markdown.test.mjs` round-trip stays green. **(green — 6 grammar samples round-trip identically THROUGH a real Milkdown instance.)**

### T7 — No authoritative frontend state (EDIT-03 acceptance) ☑ DONE
- **Surface:** the store↔Milkdown reconcile (`setText` is the ONLY inbound path) + the live `/` slate (`__mm_rerender` re-derives the grid from the store).
- **Steps:** a dropped-WS reconnect re-pushes the store text and the view reconciles identically; no ProseMirror "state overhang"; the live slate is a pure projection (DOM corruption is erased by a store re-render).
- **Done-when:** un-fixme `milkdown.spec.js` "no authoritative frontend state" **(green — edit→diverge→reconnect(setText)→identical)** AND `edit.spec.js` EDIT-03 **(green — corrupt the live DOM → `__mm_rerender` → identical, corruption gone)**.

## Coverage (req → task)

| Req | Tasks |
|---|---|
| EDIT-01 | T2 ☑, T3 ☑, T5 ☑ |
| EDIT-02 | T2 ☑, T4 ☑, T5 ☑, T6 ☑ |
| EDIT-03 | T1 ☑, T7 ☑ |

## Phase gate
`npm run test:all` green in BOTH stub and real modes with every EDIT spec
un-fixme'd; `npm run test:all:real --fixture-scan` for deterministic real-stack
acceptance. **ALL of T1–T7 done.** milkdown.spec.js 8/8 + edit.spec.js 8/8 (every EDIT-01/02/03
spec un-fixme'd); full e2e **21 passed / 3 skipped** (only the Phase-3 HALO fixmes
remain); fe/ unit tests green; no regressions. Remaining refinements (non-blocking):
caret-at-click *column*, and the `env-scenario click-to-edit` REPL-mirror assertion
(the persistence already routes through `apply_update_lifecycle`).
