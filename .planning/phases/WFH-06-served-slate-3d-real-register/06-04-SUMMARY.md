---
phase: WFH-06-served-slate-3d-real-register
plan: 04
subsystem: ui
tags: [three.js, svg, projector, websocket, e2e, playwright]

# Dependency graph
requires:
  - phase: WFH-06-served-slate-3d-real-register (06-01/02/03)
    provides: createProjector closure factory, force-directed layout, per-URL multi-scan + camera framing, image billboards
provides:
  - data-3d-node-id authorship on every mounted panel cell (editor.html render())
  - "#link-layer SVG overlay host (z-index:1, pointer-events:none, no chrome)"
  - "project(x,y,z) extended with ndcZ (additive, backward-compatible)"
  - nodeWorldPosition(nodeId) accessor on the projector
  - drawConcept3DLinks(svgHost) — solid headless 2D<->3D link arrow, per-frame
  - window.__mm_proj_pin(nodeId) test helper
affects: [WFH-07-deep-object-exploration-gestures, WFH-08-halo-cone-ray-brace-states]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SVG <line> overlay (DOM-native) for 2D<->3D link rendering, consistent with the existing haloHost SVG precedent"
    - "True NDC-z frustum test ([-1,1]) via an additive project() field (ndcZ), kept separate from the legacy near/far-only inFront flag so existing consumers are unaffected"
    - "WeakMap-cached per-card <line> elements to update-in-place rather than recreate every frame"

key-files:
  created: []
  modified:
    - backend/templates/editor.html
    - backend/static/js/fe/projector.mjs
    - frontend_e2e/projector.spec.js

key-decisions:
  - "project() extended additively with ndcZ instead of replacing/repurposing inFront — halo ray-transport's existing consumer is untouched"
  - "#link-layer authored as static <svg> markup in editor.html's body (with CSS-block styling matching #projector/#grid's existing convention) rather than runtime document.createElementNS + body.appendChild — identical resulting DOM/CSS contract (z-index:1, pointer-events:none, full-viewport), more consistent with this file's existing styling convention"
  - "Off-frustum e2e case drives the test node to the camera's own position (camPos) rather than a hand-picked behind-camera point — robust regardless of the camera's current orbit angle, and reliably yields |ndcZ|>1 for a perspective camera"

requirements-completed: [REAL-04]

# Metrics
duration: 45min
completed: 2026-06-23
status: complete
---

# Phase 6 Plan 4: Solid Headless 2D<->3D Link Arrow Summary

**Ported `cp/concept_graph.js::_drawConcept3DLinks` into the served `fe/` projector as a closure-scoped `drawConcept3DLinks(svgHost)`, drawing a solid `#ffd700` headless `<line>` per pinned panel that tracks its 3D node every animate frame and hides via a true `[-1,1]` NDC-z frustum test.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-06-23 (session continuation)
- **Completed:** 2026-06-23
- **Tasks:** 3 completed
- **Files modified:** 3

## Accomplishments
- Every mounted panel cell now carries `data-3d-node-id` at mount time (`editor.html`'s `render()`), with a `#link-layer` SVG overlay host sitting between `#projector` (z-0) and `#grid` (z-2), fully passive (`pointer-events:none`, no chrome).
- `projector.mjs`'s `project(x,y,z)` now additionally returns `ndcZ` (the raw `Vector3.project(camera).z`), additive and backward-compatible with the existing `inFront` consumer (the halo's ray-transport).
- `drawConcept3DLinks(svgHost)` ported verbatim (algorithm-for-algorithm) from the legacy `cp/` implementation: projects each `[data-3d-node-id]` card's current (post-force-step) world position, draws/updates a solid `#ffd700` `stroke-width:2` line with no `marker-end` and no `stroke-dasharray`, anchored at the nearest edge of the panel's bounding rect, hidden when `ndcZ` falls outside `[-1,1]` — the TRUE frustum test, not the weaker near/far-only `inFront` flag.
- Wired into `editor.html`'s per-frame `onFrame` callback against the new `#link-layer` host.
- New `arrow` e2e block in `projector.spec.js` proves: exactly one line is drawn for a pinned node; it is solid/headless/`#ffd700`; its endpoint moves when the camera orbits (tracks the moving node); it hides when driven off-frustum. `black_slate.spec.js`'s no-dotted regression gate stays green throughout.

## Task Commits

1. **Task 1: data-3d-node-id authorship + #link-layer SVG host** - `90ccb43` (feat)
2. **Task 2: drawConcept3DLinks — solid headless 2D<->3D link arrow** - `03cf5d6` (feat)
3. **Task 3: REAL-04 arrow e2e** - `f6c0945` (test)

**Plan metadata:** (this commit, made immediately after this SUMMARY)

## Files Created/Modified
- `backend/templates/editor.html` - `#link-layer` CSS + SVG markup, `data-3d-node-id` authorship in `render()`, `window.__mm_proj_pin` test helper, `onFrame` wiring of `drawConcept3DLinks`
- `backend/static/js/fe/projector.mjs` - `project()` extended with `ndcZ`, new `nodeWorldPosition(nodeId)` accessor, new `drawConcept3DLinks(svgHost)` closure function, both exposed on the returned projector object
- `frontend_e2e/projector.spec.js` - new `arrow` test block (REAL-04)

## Decisions Made
- `project()` extended additively (`ndcZ` field added, `inFront`/`x`/`y` unchanged) rather than repurposed, to guarantee zero impact on the halo's existing ray-transport consumer.
- `#link-layer` authored as static HTML/CSS rather than runtime JS DOM construction — functionally identical contract, better matches this file's existing styling convention for `#projector`/`#grid`. Documented here as a minor implementation-choice deviation from the plan's literal "append via JS" phrasing; not a behavioral or architectural change (Rule 4 does not apply — no user decision needed).
- The off-frustum e2e assertion drives the test node to the camera's own current position (`window.__mm_proj.camera.position`) rather than a fixed point behind some assumed camera orientation — this is robust to whatever orbit state the camera is in after the tracking assertion that precedes it in the same test.

## Deviations from Plan

### Auto-fixed Issues

None — Rules 1-3 were not triggered. No bugs found, no missing critical functionality discovered, no blocking issues encountered.

**1. [Implementation choice, not a deviation rule] `#link-layer` authored as static markup instead of runtime JS append**
- **Found during:** Task 1
- **Issue:** The plan's action text described creating `#link-layer` via `document.createElementNS` + `document.body.appendChild`, mirroring the `haloHost` convention.
- **Choice:** Added `<svg id="link-layer"></svg>` directly as static markup in the HTML body, with sizing/z-index/pointer-events in the `<style>` block (matching how `#projector`/`#grid` are already styled in this file).
- **Resulting contract:** Identical — same `id`, same `z-index:1`, same `pointer-events:none`, same full-viewport sizing. No behavioral difference; documented for transparency, not because it required a Rule 1-4 fix.
- **Files modified:** backend/templates/editor.html
- **Verification:** `grep -n "link-layer" backend/templates/editor.html` confirms the CSS rule + markup; `npx playwright test black_slate.spec.js` confirms no chrome regression.
- **Committed in:** 90ccb43 (Task 1 commit)

---

**Total deviations:** 0 rule-triggered auto-fixes; 1 documented implementation choice (no behavioral impact).
**Impact on plan:** None. All acceptance criteria met exactly as specified.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

Phase 6 (3D Real Register in the Served Slate) is now COMPLETE — all 4 plans (REAL-01 force-directed layout, REAL-02 multi-scan + camera framing, REAL-03 image billboards, REAL-04 solid headless link arrow) executed and verified against the real stack. `black_slate.spec.js`'s no-dotted-anywhere regression gate has stayed green across all four waves. The served `fe/` surface now carries a complete 3D real register parity with the legacy `cp/` reference implementation for these four requirements.

No blockers for Phase 7 (Deep Object-Exploration Gestures). The `data-3d-node-id` convention and `#link-layer` overlay established here are available for any future work needing DOM↔3D-node correlation.

## Verification Run

- `node --test backend/static/js/fe/projector.test.mjs` — 13/13 passed (no regressions; no new pure-function tests added since `drawConcept3DLinks` is DOM-dependent, tested via e2e).
- `npx playwright test --config=frontend_e2e/playwright.config.js projector.spec.js -g "UMAP-01"` — 1/1 passed (Task 1 gate).
- `npx playwright test --config=frontend_e2e/playwright.config.js black_slate.spec.js` — 6/6 passed, run after Task 1, Task 2, and Task 3 (regression gate held throughout).
- `npx playwright test --config=frontend_e2e/playwright.config.js projector.spec.js -g "force-directed|multi-scan|image|UMAP-01"` — 4/4 passed (Task 2 gate, no regressions in REAL-01/02/03).
- `npx playwright test --config=frontend_e2e/playwright.config.js projector.spec.js -g "arrow"` — 1/1 passed (Task 3, new REAL-04 test).
- `npx playwright test --config=frontend_e2e/playwright.config.js projector.spec.js` (full file) — 5/5 passed (final overall verification).

Playwright browsers were available in this environment throughout — no deferred verification was required.

---
*Phase: WFH-06-served-slate-3d-real-register*
*Completed: 2026-06-23*
