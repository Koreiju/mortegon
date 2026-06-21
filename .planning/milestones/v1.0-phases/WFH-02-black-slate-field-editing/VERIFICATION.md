# Phase 2 — Black-Slate Field Editing — VERIFICATION

> Goal-backward verification (the gsd-verifier artifact, authored directly — the
> phase was planned by hand after the planner agent hit session limits). Checks the
> **codebase delivers the phase goal**, not merely that tasks were checked off.
> Date: 2026-06-18. Verdict: **PASS** (with deviations recorded + justified).

## Phase goal (restated)

> "A user can edit any field of the black-slate panel in place, and every mutation
> commits through the one lifecycle dispatcher with the frontend holding **no
> authoritative state** — finishing the §T click-to-edit gap on the already-served
> slate." (EDIT-01/02/03; edit layer resolved to **Milkdown**, controlled view.)

## Success-criterion verdicts

### SC1 — click-to-edit a row, caret at the click, grow the tree, commit/discard — ✅ MET
- **Evidence:** `frontend_e2e/edit.spec.js` EDIT-01 (live `/?slate=milkdown`): create card → renders as a black slate → single-left the `body` field → a focused `.mm-milkdown` contenteditable mounts with the **caret in the clicked field** (asserted via `__mm_caret_line()` = "body : hello world", not the doc end) → type → **blur commits** (API poll shows `hello world EDITED`) → re-open → **Esc discards** (`DISCARDME` absent). Green ×2 (deterministic).
- **Mechanism:** `editor.html::enterMilkdownEdit` (behind the `?slate=milkdown` flag); caret placed via `milkdown_slate.mjs::placeCaretInField` (ProseMirror `TextSelection` — a raw DOM Range is overridden on focus).
- **Deviation (justified):** commit is on **blur**, not Enter. Enter/Tab are reserved for §3 field growth (SC2). This is the consistent unified tree-edit model and is MORE correct than per-keystroke commit (the cascade fires on commit, §8D.38.4). Caret lands at **field granularity** (end of the clicked field), not exact pixel column — the meaningful "where the click fell."

### SC2 — field-tree growth (`+→`/`+↓`) + `{`-autocomplete, lifecycle-routed — ✅ MET
- **Evidence:** `edit.spec.js` EDIT-02 ×2 — Enter adds a sibling row, Tab re-parents one rank deeper (persisted at `\tsecond : 2` / `\t\tchild : 3`); typing `{`+prefix pops concept names and selecting inserts `{Target Node …}` into the value, committed.
- **Lifecycle routing:** `env-scenario --name edit-field-roundtrip` (extended this phase) drives the gateway's real commit path (`concept-update` → `PATCH /api/concepts/{id}` → `apply_update_lifecycle`) and asserts (a) the data PERSISTS and (b) the append-only evolution log records the card's `modify` diff. Green in `full-smoke`.
- **Mechanism:** field growth is ProseMirror's native commonmark list keymap (no custom code); `installAutocomplete` is the `{` popup; `markdownToFieldText` maps the new list structure back to §3 tab depth on commit.

### SC3 — edit-layer = Milkdown behind `mount`, controlled view, no authoritative state — ✅ MET
- **Decision:** resolved to **Milkdown** (user override 2026-06-17, `docs/MILKDOWN_SLATE_GOAL.md`), superseding the "stay custom / CM6" lean. The `magic_markdown` model + `store.mjs`/`gateway.mjs` are unchanged — the bundle reuses `renderPanel`/`parse`/`resolveGesture`; Milkdown replaces only the edit/decoration layer.
- **No-authoritative-state proof:** `milkdown.spec.js` "no authoritative frontend state" (edit → diverge → reconnect via `setText` → identical, zero ProseMirror overhang) AND `edit.spec.js` EDIT-03 (corrupt the live `/` DOM → `__mm_rerender` re-derives from the store → identical, corruption erased).
- **Controlled-view seam:** inbound `setText` replace-all is the only truth path; outbound is blur-commit. The ~790 KB bundle loads lazily ONLY behind `?slate=milkdown`; the default served editor is untouched.

### SC4 — `full-smoke` green in both modes with the editing scenarios — ✅ MET
- **Evidence:** `python scripts/run_full_stack_tests.py --only repl --repl-scope full-smoke --only e2e` → REPL `full-smoke` **92/92** (incl. the extended `edit-field-roundtrip`) + Playwright e2e **21 passed / 3 skipped** (only Phase-3 HALO fixmes) — **ALL GREEN**. `node --test backend/static/js/fe/*.test.mjs` green.

## Cross-cutting goal check (goal-backward)

- **"edit any field in place"** — ✅ the whole card opens as one editable Milkdown surface seeded from the §3 field text; any field is editable, the clicked one gets the caret.
- **"commits through the one lifecycle dispatcher"** — ✅ `concept-update` PATCH → `apply_update_lifecycle` (WS broadcast + ConceptIndex + evolution log + cascade nudge). Verified the gateway's prior `edit_close` mapping was only a UI beacon and never persisted — fixed.
- **"frontend holds no authoritative state"** — ✅ proven twice (Milkdown reconnect identity + live `/` re-render erases DOM corruption).

## Incidental fixes delivered (beyond the SCs)

- `store.mjs` + `loadConcepts`: `concept_id → id` normalization. **Authored concepts never rendered** in the editor before this (the wire payload keys by `concept_id`, the store read `c.id`) — a latent blocker to editing them at all.

## Gaps / follow-ups (non-blocking, tracked)

- Caret-at-click is field-granular, not exact-column (acceptable; noted in PLAN).
- Milkdown is opt-in via `?slate=milkdown`; promoting it to the default surface is a deliberate future flip (keeps the custom path as a fallback during the transition).
- Real-mode `full-smoke` for the editing scenarios runs the same code path as stub (frontend-only changes); no separate GPU-box step required for Phase 2.

## Verdict

**PASS.** All four success criteria met against the running stack; the phase goal
(in-place editing, lifecycle-routed commit, no authoritative frontend state) holds.
Shipped as PR #1 → Koreiju/mortegon.
