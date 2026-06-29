---
phase: WFH-08-halo-cone-ray-transport-brace-states-stepper
plan: 01
subsystem: frontend
tags: [javascript, dom, svg, brace-states, playwright, e2e]

# Dependency graph
requires:
  - phase: WFH-07-deep-object-exploration-gestures
    provides: "classifyBraceStates (already-correct classification) — this plan RENDERS its output, closing the Phase-7 self-flagged 'computed but not rendered' gap"
provides:
  - "renderGraph threads `braceState` onto each graph node (it dropped it before); magic_markdown.test.mjs unit cases"
  - "panelVDom branches the dropdown glyph on braceState (▸ braced-hidden --silver-700 / ▾ revealed-internal --silver-300) + data-brace-state attr"
  - "graphVDom draws the resolved-external cross-ref link: a SOLID <line> from the second-occurrence node to the revealed-internal node sharing the same refTarget — no stroke-dasharray, no marker-end (§O.16); color --accent-arrow when the target is 3D-backed else --silver-300"
  - "HALO-04 brace e2e in halo.spec.js (braced-hidden glyph, reveal ▾ + panel↔graph node-count parity, resolved-external solid line + zero-dasharray, two-level chain parity)"
affects: [WFH-08-02, WFH-08-03, WFH-08-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HALO-04 was a TWO-POINT WIRING fix, not new logic: classifyBraceStates (Phase 7) was already correct; the gap was renderGraph dropping braceState + panelVDom/graphVDom never branching on it. No similarity/classification logic changed."
    - "The resolved-external link REUSES graphVDom's exact existing in-graph <line> idiom (containment edges) — only stroke color + endpoint selection differ; the no-stroke-dasharray / no-marker-end (headless) invariant holds, so black_slate.spec.js stays green."
    - "One invariant graph, three render states: revealing a ref in panel reveals it in graph (node-count parity), asserted both unit (flattenVDom attr scans) and e2e (two-level chain)."

key-files:
  created: []
  modified:
    - backend/static/js/fe/magic_markdown.mjs
    - backend/static/js/fe/magic_markdown_panel.mjs
    - backend/static/js/fe/magic_markdown.test.mjs
    - backend/static/js/fe/magic_markdown_panel.test.mjs
    - frontend_e2e/halo.spec.js
---

# Plan 08-01 Summary — HALO-04 brace-state render wiring

## What was built

Rendered the three §O.1a `{ref}` brace states VISUALLY, closing the gap Phase 7's own UI audit
self-flagged ("classifyBraceStates computed but panelVDom/graphVDom ignore l.braceState; the
resolved-external solid link has no graphVDom drawing"):

- **Task 1** — `magic_markdown.mjs::renderGraph` now threads `braceState` onto each graph node
  (it dropped it before); unit cases assert node-count parity across all three states.
- **Task 2** — `magic_markdown_panel.mjs::panelVDom` selects the dropdown glyph by braceState
  (▸ braced-hidden / ▾ revealed-internal) with a `data-brace-state` attr; `graphVDom` draws the
  resolved-external cross-ref link as a SOLID `<line>` (no dasharray, no marker-end) to the
  revealed-internal node sharing the same `refTarget`, colored `--accent-arrow` when the target
  is 3D-backed else `--silver-300`.
- **Task 3** — HALO-04 e2e in `halo.spec.js`: braced-hidden ▸ + literal braces; reveal → ▾ +
  panel↔graph node-count parity; a second ref to an already-revealed target → resolved-external
  solid `<line>` with zero `stroke-dasharray` anywhere in the graph SVG; a two-level chain
  keeping panel and graph in lockstep two ranks deep.

## Verification (automated — no screenshots)

- `node --test backend/static/js/fe/magic_markdown.test.mjs backend/static/js/fe/magic_markdown_panel.test.mjs`
  → **33/33 + 24/24** (both files per WR-1 — the panel render cases live in
  `magic_markdown_panel.test.mjs` and would have silently never run on the single-file verify).
- `npx playwright test halo.spec.js -g "brace"` → **4/4**.
- `black_slate.spec.js` → green (§S.4 black-fill/silver-border/serif-white + the §11/D11 no-dotted
  gate). NOTE: a first run reported the §S.4 case failing after a **44-minute** wall-clock — that
  was a wedged stub-backend boot, not a regression; an isolated re-run on a fresh boot passed in
  9.0s (08-01 never touches the `.mm-slate` element style the test checks; it only changes child
  `.mm-drop` glyph color + adds the resolved link).

## Deviations / resume notes

- **Executor cut off mid-plan; closed out by the orchestrator.** The Tasks-1+2 commits
  (`4071ccf`, `e883550`) landed before a session-limit interruption; the Task-3 e2e was authored
  but uncommitted. The orchestrator verified both committed tasks (units green), confirmed the
  uncommitted Task-3 e2e passes (4/4) + black_slate stays green, then committed Task 3 and wrote
  this SUMMARY. No work duplicated.

## Next-plan readiness (08-02)

The brace-render layer is live; 08-02 (HALO-03 cone transport, `fe/halo_cone.mjs` + the projector
render) and 08-03/04 build on the same projector/halo surface. The resolved-external link's
3D-backed color path (`--accent-arrow`) is ready for the cone-transported nodes 08-02 places.
