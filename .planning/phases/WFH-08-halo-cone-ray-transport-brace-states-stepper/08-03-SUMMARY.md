---
phase: WFH-08-halo-cone-ray-transport-brace-states-stepper
plan: 03
subsystem: backend+frontend
tags: [signal-stream, stepper, projector, fly-to, highlight, one-way, d10]
status: complete

# Dependency graph
requires:
  - phase: WFH-08-halo-cone-ray-transport-brace-states-stepper
    plan: 02
    provides: "the live cone-ray-transport projector surface (placeHaloCandidates, conePositions, the __mm_proj_*/__mm_cone_positions test-hook convention) this plan's flyToNode/highlightNode/stepper.mjs extend"
provides:
  - "UIStateService.set_signal_stream/advance_signal resolve signal_id SERVER-SIDE from an ordered sampled-chunk list (_resolve_signal_id, V5 bounds-safe), threaded through /api/ui/signal_stream + /api/ui/signal_advance + RolloutCoordinator.advance via a new optional `ordered` field"
  - "projector.flyToNode(nodeId) — reuses the existing cubic-ease _cameraTween record verbatim to fly the camera toward a node's world position; projector.highlightNode(nodeId) — outline-brightens a node's colour slot to --silver-300, re-applied after every recolor()/setNodes() so it survives the per-frame HSV rebuild"
  - "fe/stepper.mjs::advanceAndFocus(cardId, step, deps) — a pure, dependency-injected driver that POSTs /api/ui/signal_advance, reads the server-resolved signal_id, and calls flyToNode+highlightNode; strictly one-way (no projector import, no event listeners)"
  - "editor.html test hooks: __mm_proj_fly_to, __mm_proj_highlight, __mm_stepper_advance (the latter wires the REAL stepper.mjs + REAL projector, not stubs)"
  - "halo.spec.js test.describe(\"per-sample stepper -> 3D focus (STEP-01)\"); sim_frontend.py's signal-stream-roundtrip env-scenario extended to register an ordered list and assert chunk-id resolution incl. wraparound"
affects: [WFH-08-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D10 server-side correlation: _resolve_signal_id(ordered, signal_index, fallback) is a small pure static method bounding the index against len(ordered) (V5 — a total/ordered mismatch resolves to None, never raises) and preserving the prior signal_id when no ordered list is supplied (backward compatibility with RolloutCoordinator.play/pause/reset, which never pass ordered)."
    - "Interruptible camera-tween reuse: flyToNode builds the exact same _cameraTween {t, dur, camStart, tgtStart, camEnd, tgtEnd} record frameCameraToRoot does, swapping _urlRootPositions.get(url) for nodeWorldPosition(nodeId) — verbatim per 08-PATTERNS, not re-derived."
    - "Re-appliable highlight overlay: highlightNode writes directly into the live colour-buffer Float32Array slot via _applyHighlightOverlay(), which is re-invoked after every recolor() (camera-azimuth HSV rebuild) and setNodes() (fresh buffer) call — otherwise the highlight would be wiped within 1-2 frames of camera movement."
    - "Pure-driver-with-injected-effects split (08-PATTERNS): stepper.mjs takes {fetch, flyToNode, highlightNode} as deps, has zero static import of projector.mjs, and registers no event listener — the structural proof of the one-way (§O.6) invariant is a source-text scan in stepper.test.mjs, not just behavioral coverage."
    - "_positions (nodeWorldPosition's backing store) is only populated by createProjector's _computeRayData(), itself only invoked from setNodes() when a truthy urlRoots map is passed — projector.test.mjs's flyToNode/highlightNode WR-2 cases must seed coords with a `url` tag AND pass urlRoots (mirrors the existing placeHaloCandidates test's seeding shape), or nodeWorldPosition resolves null and both functions correctly no-op."

key-files:
  created:
    - backend/static/js/fe/stepper.mjs
    - backend/static/js/fe/stepper.test.mjs
    - backend/tests/test_signal_chunk_id.py
    - .planning/phases/WFH-08-halo-cone-ray-transport-brace-states-stepper/deferred-items.md
  modified:
    - backend/services/ui_state_service.py
    - backend/services/rollout_coordinator.py
    - backend/api/routes.py
    - backend/static/js/fe/projector.mjs
    - backend/static/js/fe/projector.test.mjs
    - backend/templates/editor.html
    - frontend_e2e/halo.spec.js
    - scripts/sim_frontend.py

decisions:
  - "Resolved Open-Q1 (08-RESEARCH) backend-side: signal_id is resolved server-side from an explicit `ordered` chunk-id list threaded through set_signal_stream/advance_signal/RolloutCoordinator.advance/the two REST routes, rather than the frontend looking up pattern_map.sampled_chunks itself — keeps the index->chunk correlation entirely server-side per D10."
  - "ordered is stored ON the signal_stream entry by set_signal_stream so advance_signal callers (RolloutCoordinator.play/pause/reset/step) never need to re-supply it — single source of truth per card, matching the plan's storage guidance."
  - "stepper.mjs receives flyToNode/highlightNode via injected deps rather than a static `import from './projector.mjs'` (the 08-RESEARCH sketch's original form) — this keeps the one-way invariant structurally provable (a source-text scan in stepper.test.mjs proves zero projector coupling) and matches the plan's own <action> text specifying dependency injection."

# Metrics
metrics:
  duration: "~1 session (continuation)"
  completed: 2026-06-28
---

# Phase 8 Plan 03: STEP-01 stepper-drives-3D-focus Summary

Backend resolves the 2D `{chunk samples}` signal-stream cursor to a real 3D chunk concept_id
server-side (closing the confirmed plumbing gap), and the frontend gains `projector.flyToNode`/
`highlightNode` plus a new `fe/stepper.mjs` driver that advances the cursor and focuses the 3D
scene onto the resolved chunk — strictly one-way (2D drives 3D; nothing calls back).

## What was built

- **Task 1** (commit `361e9a8`) — `backend/services/ui_state_service.py::_resolve_signal_id(ordered, signal_index,
  fallback)`: a small pure static method that resolves `ordered[signal_index]` when in bounds,
  `None` when out of bounds (V5 — never raises on a total/ordered length mismatch), and the prior
  `fallback` signal_id when no `ordered` list is supplied at all (backward compatible with every
  existing caller — `RolloutCoordinator.play`/`pause`/`reset`/`step` — which never pass `ordered`).
  `set_signal_stream` and `advance_signal` both gained an optional `ordered: Optional[List[str]]`
  parameter that resolves `signal_id` through this method and stores the list on the entry so
  later calls don't need to re-supply it. `UISignalStreamRequest`/`UISignalAdvanceRequest`
  (`backend/api/routes.py`) gained the matching `ordered` field, and `RolloutCoordinator.advance`
  threads it through to `advance_signal` — confirmed `/ui/signal_advance` routes through
  `RolloutCoordinator.advance`, not `UIStateService.advance_signal` directly, so the parameter had
  to be added at both layers. New `backend/tests/test_signal_chunk_id.py`: 4 tests covering
  resolution-at-registration, re-resolution-with-wraparound, backward-compatible preservation when
  no `ordered` is ever registered, and out-of-range bounds-safety (incl. a wrap-back-into-range
  re-resolution check) — 4/4 passing, no regression to `test_signal_iteration_rerender.py`.
- **Task 2** (commit `c0a7bc4`) — `backend/static/js/fe/projector.mjs::flyToNode(nodeId)`: builds the identical
  `_cameraTween` record `frameCameraToRoot` does (verbatim cubic ease-in-out reuse), swapping the
  URL-root lookup for `nodeWorldPosition(nodeId)`; returns `false` (no-op, never throws) for an
  unknown node id or when `controls` isn't wired. `highlightNode(nodeId)` overwrites the target
  node's per-vertex colour-buffer slot with `--silver-300` (`0xb8c0c8`) via a new
  `_applyHighlightOverlay()` helper, re-invoked after every `recolor()` and `setNodes()` call so
  the highlight survives the per-frame HSV colour-buffer rebuild driven by camera-azimuth changes.
  Neither function removes/subsets any node. `projector.test.mjs` gained 4 WR-2 teeth cases
  (success + unknown-id no-op for each), plus a `FakeOrbitControls` shim addition so `controls`
  is truthy in the test harness — 18/18 passing.
- **Task 3** (commit `f95e04c`) — new `backend/static/js/fe/stepper.mjs::advanceAndFocus(cardId, step, deps)`: a pure
  driver injected with `{fetch, flyToNode, highlightNode}`. POSTs `/api/ui/signal_advance`, reads
  `state.signal_stream[cardId].signal_id` from the response (the server-resolved chunk id — never
  computed client-side, per D10), and on a non-null id calls `flyToNode` then `highlightNode`
  exactly once each; no-ops gracefully when unresolved. The module has zero static import of
  `projector.mjs` and registers no event listener — `stepper.test.mjs`'s third case is a structural
  source-text scan proving the one-way invariant, not just a behavioral check. 3/3 passing.
- **Task 4** (commit `f0fe203`) — `backend/templates/editor.html` gained `__mm_proj_fly_to`/`__mm_proj_highlight`
  (direct projector exports, following the existing `__mm_proj_*` convention) and
  `__mm_stepper_advance`, which wires the REAL `stepper.mjs` against the REAL projector (not test
  doubles) — the actual production one-way pipeline. `frontend_e2e/halo.spec.js` gained
  `test.describe("per-sample stepper -> 3D focus (STEP-01)")`, mirroring the already-landed HALO-03
  cone-ray-transport block's structure (`bootProjectorOrSkip` + `__mm_proj_*` hooks): seeds an
  ordered chunk-id list against 3 fixture 3D nodes, drives `__mm_stepper_advance`, and asserts the
  resolved chunk id matches `ordered[new_index]`, the full distribution stays rendered (node count
  unchanged — D-03), and a 3D click never advances the 2D cursor back. `scripts/sim_frontend.py`'s
  `_act_ui_signal_stream` REPL action gained a comma-separated `ordered=` param, and the
  `signal-stream-roundtrip` env-scenario was extended to register the list and assert `signal_id`
  resolution at registration, after an advance, and across a wraparound back to `ordered[0]`.

## Verification (automated — no screenshots)

- `python -m pytest backend/tests/test_signal_chunk_id.py -x -q` → **4/4 passed**.
- `node --test backend/static/js/fe/stepper.test.mjs backend/static/js/fe/projector.test.mjs` →
  **4/4 + 18/18**, both green.
- `python scripts/sim_frontend.py --backend http://127.0.0.1:8080 env-scenario --name
  signal-stream-roundtrip` → **green**, including the new STEP-01 chunk-id-resolution extension
  (registration, post-advance, and wraparound assertions all passed against the live stub
  backend).
- `python scripts/sim_frontend.py --backend http://127.0.0.1:8080 env-scenario --name full-smoke`
  → **93/93 passed** — no regression from the `ordered` field addition or the env-scenario
  extension.
- `npx playwright test frontend_e2e/halo.spec.js -g "stepper"` — **NOT GREEN locally**, blocked by
  a pre-existing, environment-wide Playwright `baseURL`-resolution failure (see Deviations below)
  that reproduces identically on files this plan never touched (`black_slate.spec.js`, the
  already-landed HALO-01/HALO-03 blocks). Logged to `deferred-items.md` rather than worked around.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] `flyToNode`/`highlightNode` WR-2 unit tests failed because the test
THREE shim had no `OrbitControls`**
- **Found during:** Task 2, first test run.
- **Issue:** `createProjector`'s `controls` only becomes non-null when `THREE.OrbitControls` is
  truthy; `projector.test.mjs`'s hand-rolled THREE shim never defined it, so `controls` stayed
  `null` and `flyToNode`'s `if (!controls) return false` guard (mirroring `frameCameraToRoot`'s
  identical guard) always fired — a test-environment gap, not a `projector.mjs` bug.
- **Fix:** Added a minimal `FakeOrbitControls` class (`.target` Vector3-like, settable
  `.enableDamping`, no-op `addEventListener`/`update`) to the shim's `global.window.THREE` object.
- **Files modified:** `backend/static/js/fe/projector.test.mjs`.
- **Commit:** `c0a7bc4`.

**2. [Rule 1 - Bug] `flyToNode`/`highlightNode` WR-2 unit tests failed because `_positions` was
never populated**
- **Found during:** Task 2, same test run (second, distinct failure).
- **Issue:** `nodeWorldPosition`'s backing `_positions` Map is only populated by
  `_computeRayData()`, which `setNodes()` only invokes when a truthy `urlRoots` map is passed —
  the new test cases called `setNodes(coords)` with no `urlRoots`, so `nodeWorldPosition` correctly
  (and intentionally) returned `null` for every node, making both `flyToNode` and `highlightNode`
  legitimately no-op. This was a test-authoring gap (the new cases didn't mirror the existing
  `placeHaloCandidates` test's seeding shape), not a logic bug in the new `projector.mjs` code.
- **Fix:** Tagged each seeded coord with a `url` key and passed a matching `urlRoots` map (`{u1:
  {root_position: [0,0,0], bounding_radius: 50}}`) to `setNodes`, mirroring the
  `placeHaloCandidates` test's existing pattern exactly.
- **Files modified:** `backend/static/js/fe/projector.test.mjs`.
- **Commit:** `c0a7bc4`.

**3. [Rule 1 - Bug] `stepper.test.mjs`'s one-way structural assertion over-counted
`signal_advance` occurrences**
- **Found during:** Task 3, first test run.
- **Issue:** The Test-3 structural scan counted every occurrence of the literal string
  `signal_advance` in `stepper.mjs`'s source, including the module's own doc-comment prose
  (which legitimately discusses the route by name) — inflating the count to 4 against an expected
  1 and failing a test that was itself correct in intent but wrong in implementation.
- **Fix:** Stripped comment lines before scanning and narrowed the pattern to the literal route
  path `/api/ui/signal_advance`, so the assertion measures executable-code occurrences only.
- **Files modified:** `backend/static/js/fe/stepper.test.mjs`.
- **Commit:** `f95e04c`.

### Deferred (out of scope — logged, not fixed)

**Pre-existing Playwright `baseURL`-resolution breakage.** `npx playwright test
frontend_e2e/halo.spec.js -g "stepper"` fails on the very first `page.goto("/")` with `Cannot
navigate to invalid URL`. Confirmed this is NOT caused by this plan's changes: the identical
failure mode reproduces on `black_slate.spec.js` (6/6 failing, file untouched by this plan) and
the pre-existing HALO-01/HALO-03 blocks in `halo.spec.js` (untouched by this plan). Root cause:
`package-lock.json` already pinned `@playwright/test@1.61.0` before this session began (confirmed
via `git log`/lockfile inspection), a 12-minor-version drift from `package.json`'s declared
`^1.49.0` — predates this plan entirely. Fixing the Playwright pin is a dependency-version change
outside this plan's task scope; full detail and a recommended follow-up are recorded in
`.planning/phases/WFH-08-halo-cone-ray-transport-brace-states-stepper/deferred-items.md`. The new
stepper e2e block was authored to the exact same `bootProjectorOrSkip` + `__mm_proj_*` hook
convention as the already-landed (and equally environment-blocked) HALO-03 cone-ray-transport
block, and is structurally ready to run once the Playwright pin is resolved.

## Known Stubs

None — no stub patterns (hardcoded empty values flowing to UI, placeholder text, unwired data
sources) found in any file created or modified by this plan.

## Threat Flags

None — `ordered` is an additive optional field on two EXISTING routes (`/ui/signal_stream`,
`/ui/signal_advance`), consumed only to resolve an EXISTING `signal_id` field server-side (D10 —
no client-side index correlation introduced, satisfying T-08-06's `mitigate` disposition).
`flyToNode`/`highlightNode` are read-only camera/colour-buffer operations with no new network
surface. `stepper.mjs` adds no event listener and no new endpoint, satisfying T-08-08's
`mitigate` disposition (no 3D->2D callback wiring exists anywhere in the new code).

## Next-plan readiness (08-04)

The STEP-01 one-way 2D->3D focus drive (`_resolve_signal_id`, `flyToNode`/`highlightNode`,
`stepper.mjs`, the `__mm_stepper_advance` production wiring) is live and unit+REPL verified. 08-04
(the D-01 REAL-subsystem cone-transport probe + `--self-test`) builds on the same projector/halo
surface; this plan's Playwright e2e block is structurally complete but blocked locally by the
pre-existing Playwright-version environment issue documented in `deferred-items.md` — resolving
that pin is a prerequisite for full local e2e verification of both this plan's and 08-02's
Playwright suites.

## Self-Check: PASSED

- FOUND: backend/services/ui_state_service.py (_resolve_signal_id present)
- FOUND: backend/services/rollout_coordinator.py (advance() ordered param present)
- FOUND: backend/api/routes.py (UISignalStreamRequest/UISignalAdvanceRequest.ordered present)
- FOUND: backend/tests/test_signal_chunk_id.py
- FOUND: backend/static/js/fe/projector.mjs (flyToNode, highlightNode present)
- FOUND: backend/static/js/fe/projector.test.mjs (WR-2 flyToNode/highlightNode cases present)
- FOUND: backend/static/js/fe/stepper.mjs
- FOUND: backend/static/js/fe/stepper.test.mjs
- FOUND: backend/templates/editor.html (__mm_proj_fly_to / __mm_proj_highlight / __mm_stepper_advance present)
- FOUND: frontend_e2e/halo.spec.js (per-sample stepper -> 3D focus (STEP-01) describe block present)
- FOUND: scripts/sim_frontend.py (ordered= param + extended signal-stream-roundtrip present)
- FOUND: .planning/phases/WFH-08-halo-cone-ray-transport-brace-states-stepper/deferred-items.md
- FOUND commit 361e9a8 (Task 1: backend signal_id resolution)
- FOUND commit c0a7bc4 (Task 2: projector flyToNode/highlightNode)
- FOUND commit f95e04c (Task 3: stepper.mjs driver)
- FOUND commit f0fe203 (Task 4: stepper e2e + sim_frontend.py extension)
