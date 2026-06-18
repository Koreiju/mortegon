# Phase 2 — Black-Slate Field Editing — CONTEXT

> Context for `gsd-planner`. Captured directly from the roadmap SCs + the design
> decisions + the *as-built* code (brownfield: the §T editor is largely built;
> this phase is **finish-and-verify**, not from-scratch).

## Goal

A user can edit any field of the black-slate panel in place, and every keystroke
commits through the one lifecycle dispatcher with the frontend holding **no
authoritative state** — finishing the §T click-to-edit gap on the already-served
slate (`backend/static/js/fe/magic_markdown*.mjs`, default surface at `/`).

## In scope (requirements)

- **EDIT-01** — pure-print rows; single-left a printed token → a borderless
  textarea with the **caret at the click point**; Shift-Enter soft-newline; Enter
  commits through the lifecycle; Esc discards; empty rows hide.
- **EDIT-02** — `+→` (parent→child) / `+↓` (sibling) field-tree growth via
  keystrokes (Tab/Shift-Tab re-parent, Enter sibling, per §3); `{`-autocomplete
  over existing concept names inserts `{<name>}`; every mutation routes through
  `concept_lifecycle.py` (asserted by the `concept_index_update` WS frame +
  evolution-log entry).
- **EDIT-03** — record the edit-layer decision (custom vs CodeMirror 6 per
  `docs/EDITOR_INTEGRATION_ASSESSMENT.md`); if CM6, integrate ONLY behind `mount`
  (rest-render/reveal-raw, caret/IME/undo), with `store.mjs` / `gateway.mjs` /
  `magic_markdown.mjs` unchanged; **no authoritative frontend state** (a dropped-WS
  reconnect re-renders the slate identically).

## Locked decisions (from PROJECT.md + the assessment)

- D10 — backend computes, frontend renders. The slate holds no authoritative
  state; edit → REST → lifecycle → `concept_changed` WS → re-render.
- EDIT-03 recommendation — **keep the custom `magic_markdown` model + store/gateway
  seam**; CM6 is optional, ONLY as the in-slate edit+decoration layer (the win is
  caret/IME/undo). Milkdown/BlockNote/MDXEditor rejected. `@mdxeditor/editor`
  already removed.
- Slate grammar — tabs+newlines only; `{ref}` the only markup; §S.4 black-slate
  visual contract (already passing in e2e).

## As-built starting point (do NOT rebuild)

- `magic_markdown.mjs` (parse/print/`{ref}`/signals), `magic_markdown_panel.mjs`
  (`panelVDom` + `mount` — the click handler already detects the edit gesture and
  calls `onEdit`; the **textarea swap is the gap**), `magic_markdown_gestures.mjs`
  (`resolveGesture` — EDIT_TOKEN/TOGGLE_FOLD/TOGGLE_PANEL_GRAPH/…), `store.mjs`,
  `gateway.mjs`. 57 fe/ unit tests green.
- **Already verified (e2e, green):** §M.8 click-to-edit *gesture* fires, inline
  `{ref}` dropdown expansion, §M.6 right-click fold, §15.1 panel⇄graph circular
  dialectic (`frontend_e2e/edit.spec.js`).

## Verification gate (the framework — see `.planning/TEST_MATRIX.md`)

Each task lands a green check in `scripts/run_full_stack_tests.py`:
- **e2e (the render-level gate, the REPL's blind spot):** un-fixme the EDIT-01/02/03
  specs in `frontend_e2e/edit.spec.js` against the served `/` editor — drive them
  out with the `@playwright/mcp` server, then codify. Each fixme is the acceptance
  for its task.
- **REPL:** `env-scenario --name click-to-edit` / `edit-field-roundtrip` /
  `editor-primitives-roundtrip` / `autocomplete-state-roundtrip` assert the
  mutation routes through the lifecycle (the WS frame + evolution-log entry).
- **gate:** `npm run test:all` green in both modes; the slate's no-authoritative-
  state property proven by the reconnect-re-render e2e (EDIT-03).

## Out of scope

- Rebuilding the editor model / store / gateway / projector / halo (built).
- The Phase 3 halo render (separate phase).
- Backend lifecycle/index/persistence (mature; untouched — frontend renders only).
