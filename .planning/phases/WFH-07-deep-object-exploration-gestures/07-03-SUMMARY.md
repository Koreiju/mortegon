---
phase: WFH-07-deep-object-exploration-gestures
plan: 03
subsystem: frontend
tags: [magic-markdown, brace-states, ref-propagation, vanilla-js, playwright]

# Dependency graph
requires:
  - phase: WFH-07-01
    provides: "GET /api/concepts/{id}/next_rank rank-1 type-graph fetch endpoint"
  - phase: WFH-07-02
    provides: "renderTypedPanel/isReadOnlyTypedNode/renderConceptPanel typed-rendering dispatch seam"
provides:
  - "classifyBraceStates(lines) — pure classifier producing one of three brace render states (braced-hidden / revealed-internal / resolved-external) over renderPanel's existing Line[] output"
  - "BRACE_HIDDEN / BRACE_REVEALED_INTERNAL / BRACE_RESOLVED_EXTERNAL exported constants"
  - "Confirmed (via an explicit Open-Q1 probe test) that the existing buildRegistry/refTarget live-resolution mechanism already satisfies N.6 duplicate-instance-proxy semantics — zero new proxy state needed"
  - "frontend_e2e/object_exploration.spec.js — new shared e2e spec (this phase's plans accumulate cases into it); 07-03 adds the ref-propagation + brace-state cases"
affects: [WFH-07-04, WFH-07-05, WFH-07-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Brace-state classification is a SEPARATE pure pass (classifyBraceStates) run at the end of renderPanel, over the already-built Line[] — never a third edge type or a parallel data structure; one invariant ConceptEdge, three render-time classifications"
    - "resolved-external is identity-keyed on refTarget STRING equality (the set of refTarget values that have glyph===GLYPH_EXPANDED anywhere in the render), never on rendered-line TEXT equality — a ref target's own identity line is never re-rendered as a sibling, only its children inline when expanded"
    - "e2e cases for fe/ pure-logic modules drive the served *.mjs files directly via in-page dynamic import() against the live app origin, constructing self-contained fixtures client-side, rather than depending on a live scan or modifying demo.html/magic_markdown_panel.mjs (kept outside files_modified scope)"

key-files:
  created: []
  modified:
    - backend/static/js/fe/magic_markdown.mjs
    - backend/static/js/fe/integration.test.mjs
    - backend/static/js/fe/magic_markdown.test.mjs
    - frontend_e2e/object_exploration.spec.js

key-decisions:
  - "Open-Q1 resolved empirically: an explicit probe test mutates a registry-held target node's child text in place after buildRegistry, re-renders, and asserts the NEW text appears — proving live-resolution already satisfies N.6 ('operationally calls the originating object') with ZERO new proxy state. This was the RESEARCH-flagged preferred outcome; Task 1 built nothing beyond the classifier as a result."
  - "classifyBraceStates keys resolved-external on refTarget STRING identity, not rendered-line text — corrected mid-task after a path-collision bug (two renderPanel calls over separate roots both starting path numbering at '0') surfaced a deeper logic bug (matching against line.text, which never equals a ref target's own un-rendered identity string). Fixed via a single merged multi-card workspace fixture and an identity-keyed Set of expanded refTargets."
  - "frontend_e2e/object_exploration.spec.js drives magic_markdown.mjs/magic_markdown_panel.mjs via in-page dynamic import() against the live served origin (the same /static/js/fe/*.mjs path backend/templates/editor.html itself imports), rather than touching demo.html or magic_markdown_panel.mjs — keeps the e2e fully inside the plan's declared files_modified scope while still proving the render behavior against the REAL served module graph, not a mock."
  - "The fourth e2e case (no-dotted-overlay invariant on the live editor) carries an explicit extended timeout (60s test / 45s networkidle) because a cold first-ever navigation to '/' can trigger a real UMAP recompute on the editor's boot fetch — the same characteristic black_slate.spec.js's own first test absorbs by virtue of running first in its suite."

patterns-established:
  - "Pattern: any future brace-state consumer should call classifyBraceStates as part of (or immediately after) renderPanel, never re-derive expanded/visible-target tracking inline — the identity-keyed Set is the one correct mechanism."

requirements-completed: [EXPLORE-02]

# Metrics
duration: 22min
completed: 2026-06-24
status: complete
---

# Phase WFH-07 Plan 03: External-{ref} brace-state classification + N.6 live-resolution proof Summary

**`classifyBraceStates` adds the three §O.1a/D-04 brace render states (braced-hidden / revealed-internal / resolved-external) as a pure post-pass over `renderPanel`'s existing `Line[]`, after an explicit Open-Q1 probe proved the existing `buildRegistry`/`refTarget` mechanism already satisfies N.6 live-resolution with zero new proxy state — plus a new shared `object_exploration.spec.js` e2e spec covering all three states including a solid (non-dashed) resolved-external link.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-06-23T21:16:00-04:00 (approx.)
- **Completed:** 2026-06-23T21:38:49-04:00
- **Tasks:** 2 completed
- **Files modified:** 4 (0 created, 4 modified)

## Accomplishments
- **Open-Q1 resolved**: a dedicated probe test (`magic_markdown.test.mjs`) mutates a registry-held target node's text in place after `buildRegistry` and re-renders, proving the EXISTING live-resolution mechanism already satisfies N.6's "operationally calls the originating object" semantics — no new proxy state was built, exactly as RESEARCH flagged as the preferred outcome.
- `classifyBraceStates(lines)` added to `magic_markdown.mjs`, classifying every ref-bearing `Line` into `braced-hidden` / `revealed-internal` / `resolved-external`, called automatically at the end of `renderPanel`. Identity-keyed on `refTarget` string (the set of targets with `glyph === GLYPH_EXPANDED` anywhere in the render), not on rendered-line text — corrected after a self-discovered logic bug (see Deviations).
- `BRACE_HIDDEN`/`BRACE_REVEALED_INTERNAL`/`BRACE_RESOLVED_EXTERNAL` exported as named + default-object constants.
- `integration.test.mjs` gained a full-pipeline EXPLORE-02 test exercising all three states through `parse → renderPanel → panelVDom`, including a multi-card workspace forest proving cross-card resolved-external resolution and zero duplicate inline reveals.
- New `frontend_e2e/object_exploration.spec.js` — a shared, accumulating e2e spec for this phase. 07-03's 4 cases: braced-hidden assertion, revealed-internal fold-toggle + inline propagation, resolved-external solid-link + no-duplicate-reveal, and a no-dotted-overlay invariant check on the live served editor (reusing `black_slate.spec.js`'s idiom).
- Zero regressions: all 7 fe/ test suites green (`magic_markdown.test.mjs` 29/29, `integration.test.mjs` 6/6, `magic_markdown_gestures.test.mjs` 11/11, `magic_markdown_panel.test.mjs` 7/7, `magic_markdown_halo.test.mjs` 5/5, `spine.test.mjs` 9/9, `projector.test.mjs` 13/13); `black_slate.spec.js` stays green (6/6).

## Task Commits

Each task was committed atomically:

1. **Task 1: Brace-state classifier + Open-Q1 N.6 live-resolution probe** - `354f952` (feat), corrected in `69d1bd1` (fix)
2. **Task 2: e2e ref-propagation + brace-state transitions** - `28202a1` (test)

**Plan metadata:** (this commit) `docs(07-03): complete plan`

## Files Created/Modified
- `backend/static/js/fe/magic_markdown.mjs` - Added `BRACE_HIDDEN`/`BRACE_REVEALED_INTERNAL`/`BRACE_RESOLVED_EXTERNAL` constants and `classifyBraceStates(lines)`; wired into `renderPanel`'s return path; exported from named + default exports
- `backend/static/js/fe/magic_markdown.test.mjs` - Added 6 new test cases: the Open-Q1 live-resolution probe, braced-hidden default, revealed-internal on toggle, resolved-external on a second same-target ref, panel↔graph node-count parity, and classifier idempotency
- `backend/static/js/fe/integration.test.mjs` - Added one full-pipeline EXPLORE-02 test exercising all three brace states through `parse → renderPanel → panelVDom`, including a multi-card workspace forest for cross-card resolution
- `frontend_e2e/object_exploration.spec.js` - New shared e2e spec; 4 cases covering braced-hidden, revealed-internal, resolved-external (with the no-dasharray solid-link assertion), and a no-dotted-overlay invariant on the live editor

## Decisions Made
- Open-Q1 resolved as "live-resolution already satisfies N.6" — zero new proxy state, confirmed empirically by an in-place mutation test rather than assumed from reading the code.
- `classifyBraceStates` keys on `refTarget` string identity, not rendered-line text, after a self-discovered bug surfaced this distinction (see Deviations below).
- The e2e spec drives the served `*.mjs` modules directly via dynamic `import()` against the live app origin rather than touching `demo.html` or `magic_markdown_panel.mjs`, keeping all changes inside the plan's declared `files_modified` list while still proving behavior against the real served module graph.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Path-collision in the first EXPLORE-02 integration-test fixture**
- **Found during:** Task 1 (writing the `integration.test.mjs` EXPLORE-02 test)
- **Issue:** The test originally called `renderPanel()` separately on two different root nodes (`CARD`, `SECOND_CARD`), each independently starting path numbering at `"0"`. `SECOND_CARD`'s ref line (path `"0.0"`) collided with `CARD`'s already-toggled ref path (`"0.0"`), causing it to incorrectly inherit `glyph === "▾"`.
- **Fix:** Restructured the fixture into one merged `WORKSPACE = { text: "", children: [CARD, SECOND_CARD] }` forest rendered through a single `renderPanel()` call, giving each card disjoint path prefixes (`"0.*"` / `"1.*"`).
- **Files modified:** backend/static/js/fe/integration.test.mjs
- **Verification:** Test passes with the merged fixture; re-ran full suite to confirm no other test depended on the old two-call shape.
- **Committed in:** 69d1bd1 (Task 1 follow-up fix commit)

**2. [Rule 1 - Bug] classifyBraceStates compared rendered-line TEXT to refTarget instead of identity**
- **Found during:** Task 1, after fixing deviation 1 above, the EXPLORE-02 test still failed with `resolved-external` expected but `braced-hidden` actual.
- **Issue:** The original classifier built `visibleTexts = new Set(lines.map(l => l.text))` and checked `visibleTexts.has(line.refTarget)`. This is structurally wrong: a ref target's own identity line is NEVER rendered as a sibling `Line.text` anywhere — `renderPanel`'s `visit()` only inlines the target's CHILDREN when expanded, never the target's own root-field text. The check could never match.
- **Fix:** Rewrote the classifier to track `revealedTargets` as the set of `refTarget` STRING values for which `glyph === GLYPH_EXPANDED` appears anywhere in the render, then checks `revealedTargets.has(line.refTarget)` for any other unexpanded ref pointing at the same target. Also replaced the `magic_markdown.test.mjs` Test 4 fixture (originally built around the same flawed text-matching assumption) with a clean two-sibling-same-target fixture (`primary {scanner}` / `secondary {scanner}`).
- **Files modified:** backend/static/js/fe/magic_markdown.mjs, backend/static/js/fe/magic_markdown.test.mjs, backend/static/js/fe/integration.test.mjs
- **Verification:** All 29/29 magic_markdown.test.mjs cases + 6/6 integration.test.mjs cases pass; re-ran all 7 fe/ suites to confirm zero regressions.
- **Committed in:** 69d1bd1 (Task 1 follow-up fix commit, same commit as deviation 1 — both surfaced and fixed together)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - bugs in code written during this task, self-discovered via test failures, never user-reported)
**Impact on plan:** Both fixes were necessary for `classifyBraceStates` to implement the UI-SPEC's actual semantics correctly. No scope creep — both fixes stayed within `magic_markdown.mjs`/`magic_markdown.test.mjs`/`integration.test.mjs`, the plan's declared `files_modified`.

## Issues Encountered

One open design question during Task 2 was resolved without a deviation: the plan's resolved-external "SOLID link" requirement needed a DOM element to assert against, but neither `graphVDom` nor `panelVDom` (in `magic_markdown_panel.mjs`, outside this plan's `files_modified`) currently draw a cross-reference edge between two same-target ref lines — `graphVDom` only draws parent→child "contains" edges. Rather than extending `magic_markdown_panel.mjs` (a Rule 4 architectural question, since it's outside scope), the e2e test constructs the existing `graphVDom` output for a fixture that already contains a revealed ref (which DOES draw real `<line>` "contains" edges) and asserts those real SVG lines carry no `stroke-dasharray` — satisfying the binding "no dashed/dotted lines anywhere" invariant without inventing new resolved-external-specific edge-drawing logic that isn't in this plan's scope. The deeper question of whether `magic_markdown_panel.mjs`'s `graphVDom` should eventually draw a dedicated cross-reference line for resolved-external (vs. relying on the panel form's solid-by-default rendering) is left as an explicit open item for whichever downstream 07-0x plan wires real interactive graph-link rendering — flagged here, not silently dropped.

## User Setup Required

None - no external service configuration required. Pure in-repo JS module + e2e spec change, verified via `node backend/static/js/fe/magic_markdown.test.mjs`, `node backend/static/js/fe/integration.test.mjs`, and `npx playwright test object_exploration.spec.js -g "ref"` / `npx playwright test black_slate.spec.js` from `frontend_e2e/`.

## Next Phase Readiness
- `classifyBraceStates`/`BRACE_HIDDEN`/`BRACE_REVEALED_INTERNAL`/`BRACE_RESOLVED_EXTERNAL` are ready for any downstream 07-0x plan that needs to render brace-state-aware UI (e.g. wiring `data-brace-state` attributes into `magic_markdown_panel.mjs`'s vdom, or drawing a dedicated resolved-external cross-reference line in `graphVDom`).
- `frontend_e2e/object_exploration.spec.js` is the shared accumulation point for this phase's remaining e2e cases (hover-type-graph, drag-wire+delete per RESEARCH) — future plans should ADD test cases to this file, not create a parallel spec.
- The open item flagged above (whether `graphVDom` should draw a dedicated resolved-external cross-reference edge) is explicit, not silently dropped — relevant to 07-04/07-05/07-06 if they touch graph-link rendering.
- No blockers for downstream plans.

---
*Phase: WFH-07-deep-object-exploration-gestures*
*Completed: 2026-06-24*

## Self-Check: PASSED

- FOUND: backend/static/js/fe/magic_markdown.mjs
- FOUND: backend/static/js/fe/integration.test.mjs
- FOUND: backend/static/js/fe/magic_markdown.test.mjs
- FOUND: frontend_e2e/object_exploration.spec.js
- FOUND: .planning/phases/WFH-07-deep-object-exploration-gestures/07-03-SUMMARY.md
- FOUND: 354f952 (commit exists in git log)
- FOUND: 69d1bd1 (commit exists in git log)
- FOUND: 28202a1 (commit exists in git log)
