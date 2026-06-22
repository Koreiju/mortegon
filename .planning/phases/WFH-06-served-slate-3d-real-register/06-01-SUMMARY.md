---
phase: WFH-06-served-slate-3d-real-register
plan: 01
subsystem: frontend-3d-projector
tags: [three.js, force-directed-layout, ray-constrained-physics, playwright, node-test-runner]

# Dependency graph
requires:
  - phase: WFH-06 UI-SPEC
    provides: locked constants (COLLIDER_SAFETY=1.4, MIN_SEPARATION=2.52) and closure-factory porting pattern
provides:
  - Pure exports `computeRayDir`/`colliderRadialForce` in `fe/projector.mjs` (ray math + collider repulsion, unit-testable without a browser)
  - Closure-local ray-constrained force-directed layout step (`_stepForceDirected`) wired into the projector's `animate()` loop
  - `setNodes(coords, urlRoots)` extended signature consuming backend `url_roots` (never recomputing root_position/bounding_radius — D10)
  - WS handler + boot-fetch in `editor.html` now pass `url_roots` through (previously silently dropped — RESEARCH.md Pitfall 1)
  - Test hooks `window.__mm_proj_set_with_roots` / `window.__mm_proj_node_positions`
  - Wave-0 unit test scaffold (13/13) + e2e force-directed convergence test
affects: [WFH-06-02, WFH-06-03, WFH-06-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure array-in/array-out exports (computeRayDir, colliderRadialForce) alongside the existing buildPointArrays convention — testable in Node's built-in test runner with zero THREE.js/browser dependency"
    - "Closure-local Maps (_urlRootPositions, _nodeRayData, _positions) for per-projector-instance state — never `this.*`, matching the fe/ closure-factory shape (no class+mixin)"
    - "Ray-constrained radial sliding: each node's position is root + rayDir * radius; collider repulsion only ever adjusts `radius` (1D), never moves a node off its own backend-seeded ray"

key-files:
  created: []
  modified:
    - backend/static/js/fe/projector.mjs
    - backend/static/js/fe/projector.test.mjs
    - backend/templates/editor.html
    - frontend_e2e/projector.spec.js

key-decisions:
  - "COLLIDER_SAFETY ships as 1.4 (cp/force_layout.js line 161), not the projector.md doc's >=2.0 — MIN_SEPARATION = 2*0.9*1.4 = 2.52, verified by both unit test and e2e assertions against the exact constant, never the 2.0-derived 3.6"
  - "Rule 2 auto-add: wired url_roots through the WS umap_canonical handler and the boot /api/recompute_umap fetch in editor.html — without this the entire force step would be inert in production despite all unit tests passing, since setNodes() was only ever called with a single coords argument prior to this plan"
  - "Test isolation fix: __mm_proj_node_positions() returns every node the projector has ever rendered, including a pre-existing real-scan chunk population from editor.html's own boot fetch; the e2e force-directed test filters to its 4 seeded fixture ids before running spacing/ray assertions, rather than asserting over the full unfiltered set"

requirements-completed: [REAL-01]

# Metrics
duration: 95min
completed: 2026-06-22
status: complete
---

# Phase 6 Plan 1: Force-Directed Ray Convergence + Collider Summary

**Ported `cp/force_layout.js`'s ray-constrained force-directed layout into the served `fe/projector.mjs` closure factory — chunks slide only along their own backend-seeded UMAP ray, with hard-floor collider repulsion enforcing MIN_SEPARATION=2.52 (the shipped 1.4 safety factor, not the doc's 2.0).**

## Performance

- **Duration:** 95 min
- **Started:** 2026-06-22T22:50:00Z (approx, prior session)
- **Completed:** 2026-06-23T00:25:00Z
- **Tasks:** 3
- **Files modified:** 4 (projector.mjs, projector.test.mjs, editor.html, projector.spec.js)

## Accomplishments
- Pure `computeRayDir`/`colliderRadialForce` exports ported verbatim from the legacy `cp/force_layout.js` algorithm (lines 106-145, 155-200+), fully unit-tested at machine precision (13/13 in `node --test`)
- Closure-internal `_stepForceDirected` wired into the existing `animate()` `requestAnimationFrame` loop — runs every frame, no-op until a frame with `url_roots` lands
- `setNodes(coords, urlRoots)` extended signature; `editor.html`'s WS handler and boot fetch now pass `url_roots` through end-to-end (closing a gap that would otherwise leave the feature inert in production)
- Live browser verification (not just unit math): e2e test seeds a real multi-chunk frame, runs the actual `animate()` loop in a real headless Chromium tab, and confirms the rendered positions converge to the exact same equilibrium independently computed in a pure-Node simulation (within float tolerance)

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave-0 ray-math unit tests + pure computeRayDir/colliderRadialForce exports** - `3293e69` (feat, tdd)
2. **Task 2: Port the ray-constrained force step into the projector closure + animate hook** - `7bdd231` (feat, tdd)
3. **Task 3: Force-directed e2e block — rays exist + min pairwise spacing + no-Fibonacci** - `22b0c05` (test)

**Plan metadata:** (this commit, made after this SUMMARY)

## Files Created/Modified
- `backend/static/js/fe/projector.mjs` - Added `NODE_RADIUS`/`COLLIDER_SAFETY`/`MIN_SEPARATION`/`DAMPING` constants, pure `computeRayDir`/`colliderRadialForce` exports, closure-local ray-data state (`_urlRootPositions`, `_nodeRayData`, `_positions`), `_computeRayData()`, `_stepForceDirected()`, extended `setNodes(coords, urlRoots)`, new `nodePositions()` accessor, `animate()` now calls `_stepForceDirected()` every frame
- `backend/static/js/fe/projector.test.mjs` - 6 new unit tests covering the locked `COLLIDER_SAFETY=1.4`/`MIN_SEPARATION=2.52` constants, `computeRayDir` (axis-aligned, degenerate, unit-length invariant), `colliderRadialForce` (below-threshold equal-and-opposite push, at/above-threshold hard-floor zero push)
- `backend/templates/editor.html` - Added `window.__mm_proj_set_with_roots`/`window.__mm_proj_node_positions` test hooks; fixed the WS `umap_canonical` handler and the boot `/api/recompute_umap` fetch to pass `f.url_roots`/`res.url_roots` through to `projector.setNodes` (previously dropped)
- `frontend_e2e/projector.spec.js` - New `"REAL-01 force-directed: chunks converge along root-URL rays with hard collider spacing"` test: seeds 4 chunks deliberately closer than MIN_SEPARATION along near-parallel rays from a shared URL root, runs real animate frames, asserts ray-parallelism, minimum pairwise spacing >= 2.52, and non-zero radii spread (no fixed concentric/Fibonacci ring)

## Decisions Made
- `COLLIDER_SAFETY = 1.4` (UI-SPEC Assumption A1, the shipped value) — verified directly against `cp/force_layout.js` line 161, not the `projector.md` doc's `>=2.0`. `MIN_SEPARATION = 2 * 0.9 * 1.4 = 2.52`, asserted in both the unit suite and the e2e test.
- Zero client-side `SAFETY_GAP` constant (UI-SPEC Assumption A2) — the frontend never recomputes per-URL placement gap; `bounding_radius` is consumed from `url_roots`, not derived.
- Kept the legacy degenerate-ray fallback (root-not-yet-placed → origin, `[1,0,0]` unit dir, radius 0) verbatim per RESEARCH.md Open Q3, rather than optimizing it away.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Wired `url_roots` through the WS handler and boot fetch**
- **Found during:** Task 2 (porting the force step into the closure)
- **Issue:** `editor.html`'s `umap_canonical` WS handler called `projector.setNodes(f.coords)` (single arg) and the boot `/api/recompute_umap` fetch called `projector.setNodes(coords)` (single arg) — both silently dropping the backend's `url_roots` field (RESEARCH.md Pitfall 1). Without this wiring, `_umapLayoutActive` would never flip true in production and the entire REAL-01 force step would be permanently inert despite passing all unit tests.
- **Fix:** Changed both call sites to `projector.setNodes(f.coords, f.url_roots)` and `projector.setNodes(coords, res.url_roots)` respectively.
- **Files modified:** `backend/templates/editor.html`
- **Verification:** e2e test confirms the force step activates and converges correctly when `url_roots` is supplied via the same `setNodes` code path the production WS/boot-fetch now uses.
- **Committed in:** `7bdd231` (Task 2 commit)

**2. [Rule 1 - Bug, caught during verification, fixed in test code not production code] Test-isolation bug in the e2e fixture**
- **Found during:** Task 3 verification (`npx playwright test projector.spec.js -g "force-directed"`)
- **Issue:** The first e2e test draft asserted minimum pairwise spacing over `window.__mm_proj_node_positions()` unfiltered. `editor.html` auto-boots a real `/api/recompute_umap` frame on page load, populating the projector with ~160 pre-existing real-scan chunk positions before the test's 4-chunk fixture is injected. `nodePositions()` returns every node the projector has ever rendered (by design — it is a debug/test accessor, not scoped to the latest `setNodes` call), so the unfiltered spacing check was comparing distances between unrelated leftover chunks, not the test's own fixture. This produced a flaky-looking failure (`minDist: 1.5687...` regardless of frame count) that looked like a production convergence bug but was a test-fixture bug.
- **Investigation:** Independently re-implemented `computeRayDir`/`colliderRadialForce`/`_stepForceDirected` in a standalone Node script and ran 500 iterations against the exact same 4-chunk fixture; it converged to `c1-c2: 2.518`, `c1-c3: 2.518` (both within the 0.05 float tolerance of 2.52). Then re-ran the live e2e test filtering `__mm_proj_node_positions()` to just `c1`-`c4`, which produced the identical converged positions (`c1: x=10.0768`, `c2: x=12.5836,y=0.2397`, `c3: x=7.5709,y=-0.2342,z=0.0781`, `c4: x=3`) — confirming the production force-step math is correct and the bug was purely in the test's filtering.
- **Fix:** Added `const fixtureIds = new Set(["c1","c2","c3","c4"]); positions = allPositions.filter(p => fixtureIds.has(p.id));` before the spacing/ray assertions; reduced the wait loop from 240 to 60 animate-frame iterations (since convergence completes well within that budget once isolated to the fixture).
- **Files modified:** `frontend_e2e/projector.spec.js`
- **Verification:** `npx playwright test --config=frontend_e2e/playwright.config.js projector.spec.js` — both UMAP-01 and the new force-directed test pass; `npx playwright test --config=frontend_e2e/playwright.config.js black_slate.spec.js` — all 6 tests pass (no-dotted regression included).
- **Committed in:** `22b0c05` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug found+fixed during verification)
**Impact on plan:** Both fixes were necessary for correctness — the first makes the shipped feature actually reachable in production; the second makes the e2e test actually test what it claims to test. No scope creep; no architectural changes.

## Issues Encountered
- Initial e2e test runs failed with `page.goto: Protocol error: Cannot navigate to invalid URL` — root cause was invoking `npx playwright test` without `--config=frontend_e2e/playwright.config.js`; Playwright was not resolving `use.baseURL` from the project's config without the explicit flag in this environment. Resolved by always passing `--config=frontend_e2e/playwright.config.js` explicitly.
- The stub backend (`scripts/_serve_for_tests.py` with `WFH_FAKE_SLM=1 WFH_FAKE_EMBEDDER=1 NO_WEBDRIVER=1`) took ~13s to become responsive on `:8080` even with fake-subsystem env flags — booted manually in the background for direct `npx playwright test --config=...` invocation rather than relying on the config's own `webServer` auto-boot (which also works, confirmed via the passing `reuseExistingServer: true` path).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- REAL-01 (force-directed ray convergence + hard collider spacing) is fully implemented, unit-tested (13/13), and e2e-verified against a real rendered Chromium tab — ready for 06-02 (per-URL multi-scan placement + camera framing), which will build on the now-functional `url_roots`-driven ray system.
- No blockers. The `_urlRootPositions`/`_urlBoundingRadii` Maps already store everything a per-URL camera-framing feature would need (root position + bounding radius per URL), so 06-02 should be a straightforward consumer of this plan's state.

---
*Phase: WFH-06-served-slate-3d-real-register*
*Completed: 2026-06-22*

## Self-Check: PASSED

All claimed files verified present on disk:
- `backend/static/js/fe/projector.mjs` — FOUND
- `backend/static/js/fe/projector.test.mjs` — FOUND
- `backend/templates/editor.html` — FOUND
- `frontend_e2e/projector.spec.js` — FOUND
- `.planning/phases/WFH-06-served-slate-3d-real-register/06-01-SUMMARY.md` — FOUND

All claimed commits verified present in git log:
- `3293e69` (Task 1) — FOUND
- `7bdd231` (Task 2) — FOUND
- `22b0c05` (Task 3) — FOUND
