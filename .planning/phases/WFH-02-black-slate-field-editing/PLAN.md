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

### T2 — Recursive `{ref}` rendering in the Milkdown view ☐  (EDIT-01/02, "recursive rendering")
- **Surface:** `frontend_src/milkdown_slate.mjs` + a `{ref}` Milkdown node/decoration driven by `magic_markdown.mjs::parse`/`renderPanel`.
- **Steps:** render `{name}` tokens with the ▸/▾ dropdown; clicking ▸ expands the next rank inline (recursively) from the store registry; ▾ collapses; fold-state preserved.
- **Done-when:** un-fixme `milkdown.spec.js` "recursive {ref}" — a `{ref}` expands the next rank inline, recursively; collapse restores.

### T3 — Click-to-edit: caret-at-click, Shift-Enter, Enter-commit, Esc ☐  (EDIT-01)
- **Surface:** `magic_markdown_panel.mjs::mount` (swap the textarea path for the Milkdown field editor behind `WFH_SLATE_EDITOR=milkdown`); keymap.
- **Steps:** single-left a printed token → Milkdown edit on that field, caret at the click point; Shift-Enter soft-newline; Enter commits (fires `editor-overwrite`); Esc discards; empty rows hide.
- **Done-when:** un-fixme `edit.spec.js` EDIT-01 + `env-scenario --name click-to-edit` / `edit-field-roundtrip` green.

### T4 — `{`-autocomplete + `+→`/`+↓` field growth, lifecycle-routed ☐  (EDIT-02)
- **Surface:** Milkdown input rule for `{`; Tab/Shift-Tab/Enter keymap mapping to the §3 grammar; `gateway.mjs`.
- **Steps:** typing `{` opens autocomplete over concept names → inserts `{name}`; Tab/Shift-Tab re-parent, Enter sibling; every commit routes through `concept_lifecycle.py`.
- **Done-when:** un-fixme `edit.spec.js` EDIT-02 + `env-scenario --name editor-primitives-roundtrip` / `autocomplete-state-roundtrip` (asserts the `concept_index_update` WS frame + evolution-log entry).

### T5 — Gestures resolve over the Milkdown DOM ☐  (EDIT-01/02)
- **Surface:** wire `magic_markdown_gestures.mjs::resolveGesture` over the Milkdown container.
- **Steps:** single/double-left, right, double-right, drag → the same actions as today (fold, panel⇄graph circular node, delete, wire) over the Milkdown DOM.
- **Done-when:** un-fixme `milkdown.spec.js` "gestures" + `edit.spec.js` §15.1 panel⇄graph stays green.

### T6 — §3 syntax round-trip identity through Milkdown ☐  (EDIT-02)
- **Surface:** `frontend_src/milkdown_slate.mjs` (custom serializer) + `magic_markdown.mjs`.
- **Steps:** `print(record) → Milkdown → edit → parse(text) → delta` is identity for the §3 grammar (tabs+newlines, names-with-spaces, `{}` on-ramp, kv-vs-multiline-by-indent).
- **Done-when:** un-fixme `milkdown.spec.js` "syntax" + `magic_markdown.test.mjs` round-trip stays green.

### T7 — No authoritative frontend state (EDIT-03 acceptance) ☐
- **Surface:** the store↔Milkdown reconcile (`store.mjs`/`gateway.mjs` unchanged).
- **Steps:** a dropped-WS reconnect rebuilds the Milkdown doc from the store identically; no ProseMirror "state overhang".
- **Done-when:** un-fixme `edit.spec.js` EDIT-03 + `milkdown.spec.js` "lifecycle + no-authoritative-state".

## Coverage (req → task)

| Req | Tasks |
|---|---|
| EDIT-01 | T2, T3, T5 |
| EDIT-02 | T2, T4, T5, T6 |
| EDIT-03 | T1 ☑, T7 |

## Phase gate
`npm run test:all` green in BOTH stub and real modes with every EDIT spec
un-fixme'd; `npm run test:all:real --fixture-scan` for deterministic real-stack
acceptance. T1 done (4/4); T2–T7 are the remaining build.
