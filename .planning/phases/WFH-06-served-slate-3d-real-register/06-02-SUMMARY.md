---
phase: WFH-06-served-slate-3d-real-register
plan: 02
subsystem: frontend-3d-projector
tags: [three.js, camera-tween, orbit-controls, playwright, real-02]

# Dependency graph
requires:
  - phase: WFH-06-01
    provides: "setNodes(coords, urlRoots) extended signature; _urlRootPositions/_urlBoundingRadii Maps; url_roots already wired through editor.html's WS handler + boot fetch"
provides:
  - "frameCameraToRoot(url) — closure-internal cubic-ease (~600ms) camera tween in createProjector(), ported from cp/animation.js flyToNode/_stepCameraTween"
  - "_applyCameraBounds() — per-frame adaptive minDistance=0.6×cluster_radius / maxDistance=3.0×max(|pos|), UI-SPEC-locked multipliers, run every animate() frame"
  - "_newestUrl bookkeeping + _userInteracted flag (OrbitControls 'start' listener) — scan-end auto-frame suppressed only when BOTH the user has interacted AND the newest root is already in frustum"
  - "ResizeObserver on the projector canvas (no no-change guard), supplementing the existing window 'resize' listener"
  - "window.__mm_proj_camera_distance() test hook in editor.html"
  - "REAL-02 multi-scan e2e block in projector.spec.js: non-overlap + old-root-stability + camera-frames-newest assertions, all reading backend-emitted bounding_radii/root_position"
affects: [WFH-06-03, WFH-06-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cubic ease-in-out camera tween ported verbatim as closure state (_cameraTween: {t, dur, camStart, tgtStart, camEnd, tgtEnd}) stepped once per animate() frame at a fixed 1/60 dt — matches projector.mjs's existing closure-local-Map convention (no `this.*`, no class+mixin)"
    - "Per-frame _applyCameraBounds() recomputes controls.minDistance/maxDistance from the SAME _positions/_urlBoundingRadii state the force step already maintains — zero new backend reads, zero client-side placement math"
    - "Suppress-tween-if-both conditions idiom: _userInteracted (sticky boolean, set once via an OrbitControls 'start' listener) AND _isRootInFrustum(url) (NDC z/x/y range check via the existing project()-style Vector3.project(camera) pattern) — mirrors the UI-SPEC's explicit two-condition gate, not an OR"

key-files:
  created: []
  modified:
    - backend/static/js/fe/projector.mjs
    - backend/templates/editor.html
    - frontend_e2e/projector.spec.js

key-decisions:
  - "Task 1 (wire url_roots through WS handler + boot fetch) was ALREADY completed in Wave 1 (06-01) — confirmed by direct read of editor.html lines 299/338 before doing any work, rather than re-doing it. Only the missing window.__mm_proj_camera_distance() test hook (needed for Task 3's e2e) remained, so Task 1's commit in this plan is scoped to that one addition plus the UMAP-01 regression check, not a re-wire."
  - "frameCameraToRoot's viewing distance uses Math.max(12, boundingRadius * 2.2) — a UI-SPEC-consistent-but-not-explicitly-numbered framing distance (the UI-SPEC locks the camera BOUNDS formulas 0.6x/3.0x, not a separate 'how far to fly' constant; 2.2x bounding_radius keeps the framed root's sphere comfortably inside frame without re-deriving the legacy flyToNode's per-entry-type base-distance branching, which doesn't map onto URL-roots)."
  - "_applyCameraBounds runs unconditionally every animate() frame (matching cp/animation.js's own unconditional per-frame recompute, not the legacy's >1/>0.5 dead-band optimization) — UI-SPEC says 'per-frame recomputed', and projector.mjs's existing convention favors simplicity over micro-optimizing a cheap Map-iteration + two assignments."
  - "Multi-scan e2e fixture attaches a `.url` property directly onto each coords array entry (arrays are objects in JS) rather than introducing a new coords shape — mirrors _computeRayData's own `(_coords[id] && _coords[id].url) || \"\"` read exactly as already shipped in projector.mjs, so the test exercises the REAL per-chunk-url path instead of the shared \"\" fallback key the existing force-directed test uses."

requirements-completed: [REAL-02]

# Metrics
duration: 25min
completed: 2026-06-22
status: complete
---

# Phase 6 Plan 2: Per-URL Multi-Scan Placement + Camera Framing Summary

**Camera auto-framing (cubic-ease tween to newest URL root, suppressed only when the user has interacted AND the root is already in frustum) + adaptive 0.6x/3.0x orbit bounds, ported from `cp/animation.js` into `fe/projector.mjs`; multi-scan e2e proves two URLs render at distinct non-overlapping backend roots with old roots never moving.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-06-22T22:50:00Z (approx)
- **Completed:** 2026-06-22T22:57:05Z
- **Tasks:** 3
- **Files modified:** 3 (projector.mjs, editor.html, projector.spec.js)

## Accomplishments
- Confirmed Wave 1 (06-01) had already closed the `url_roots`-drop gap (the WS `umap_canonical` handler and `bootProjector()`'s boot fetch both already call `setNodes(coords, urlRoots)`); Task 1 in this plan was scoped to the one remaining piece — a `window.__mm_proj_camera_distance()` test hook — verified against a passing UMAP-01 regression run before any further work
- Ported `cp/animation.js`'s `flyToNode`/`_stepCameraTween` cubic-ease (~600ms) camera tween as closure-internal `frameCameraToRoot(url)` + `_stepCameraTween(dt)` in `projector.mjs`, wired into `setNodes`'s newest-URL bookkeeping so a fresh URL's root auto-frames the camera on scan-end
- Implemented the two-condition tween-suppression gate exactly as specified (`_userInteracted` via an `OrbitControls 'start'` listener AND `_isRootInFrustum(url)` via NDC range-check) — neither condition alone suppresses the tween
- Ported the adaptive `minDistance = 0.6 × cluster_radius` / `maxDistance = 3.0 × max(|pos|)` formulas verbatim (UI-SPEC-locked multipliers) as `_applyCameraBounds()`, run every `animate()` frame from the same backend-resolved `_positions`/`_urlBoundingRadii` state the force step already maintains — zero new backend reads, zero client placement math
- Added a `ResizeObserver` on the projector canvas (no no-change guard) alongside the existing `window.resize` listener
- New `projector.spec.js` `multi-scan` e2e block: seeds a backend-style `url_roots` frame for `urlA`, advances real animate frames, merges in a second URL (`urlB`) at a distinct non-overlapping root, and asserts (a) cluster-centroid separation ≥ sum of bounding radii, (b) `urlA`'s chunk positions are stable across the second scan, (c) the camera position/distance shifted after scan B — proving the camera framed the new root
- `node --test projector.test.mjs` (13/13), `npx playwright test projector.spec.js` (3/3: UMAP-01, force-directed, multi-scan), `black_slate.spec.js` (6/6) all green; backend `perimeter-rescale` and `6d-umap-format` REPL env-scenarios both green, confirming the backend placement contract this plan only ever consumes

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire url_roots through the WS handler + boot fetch (close the drop)** - `a23a83b` (feat) — Wave 1 had already wired both call sites; this commit adds only the `__mm_proj_camera_distance` test hook needed downstream
2. **Task 2: Camera auto-framing tween + adaptive orbit bounds** - `71aba40` (feat)
3. **Task 3: multi-scan e2e — non-overlap + old-root-stable + camera frames newest** - `fec6220` (test)

**Plan metadata:** (this commit, made after this SUMMARY)

## Files Created/Modified
- `backend/static/js/fe/projector.mjs` - Added `_userInteracted` flag (OrbitControls `'start'` listener), `_newestUrl`/`_cameraTween` closure state, `_isRootInFrustum(url)`, `frameCameraToRoot(url)` (cubic-ease tween, ~600ms), `_stepCameraTween(dt)`, `_applyCameraBounds()` (0.6x/3.0x adaptive minDistance/maxDistance); wired `_applyCameraBounds`/`_stepCameraTween` into `animate()`; `setNodes` now detects newly-seen URLs and calls `frameCameraToRoot` on scan-end (suppressed per the two-condition gate); added a `ResizeObserver` on the canvas; exported `frameCameraToRoot` on the returned projector object
- `backend/templates/editor.html` - Added `window.__mm_proj_camera_distance = () => projector.camera.position.length()` test hook alongside the existing `__mm_proj_*` hooks (url_roots wiring itself was already present from Wave 1)
- `frontend_e2e/projector.spec.js` - New `"REAL-02 multi-scan: ..."` test: two-scan fixture (urlA then urlA+urlB merged), asserts non-overlap via cluster-centroid separation against backend-emitted bounding radii, asserts urlA position stability across the second scan, asserts the camera moved after the new urlB root landed

## Decisions Made
- Task 1 scope: rather than re-wiring `url_roots` (already done in Wave 1), this plan's Task 1 commit was narrowed to the one missing piece (the camera-distance test hook), confirmed via grep + a passing UMAP-01 test run before proceeding — avoids duplicating/reverting Wave 1's work per the prompt's explicit instruction.
- `frameCameraToRoot`'s viewing distance (`Math.max(12, boundingRadius * 2.2)`) is a framing-distance choice consistent with (but not itself one of) the UI-SPEC's locked 0.6x/3.0x bounds multipliers — the UI-SPEC locks the orbit BOUNDS formulas, not a separate "how far to fly when framing a new root" constant, and the legacy `flyToNode`'s per-node-type branching (`base = entry.isDoc ? 22 : 12`) doesn't map onto URL-roots, so a single bounding-radius-relative distance was chosen instead.
- `_applyCameraBounds()` runs unconditionally every frame (no dead-band guard), matching the UI-SPEC's "per-frame recomputed" language and `projector.mjs`'s existing preference for simple unconditional per-frame functions (e.g. `_stepForceDirected`) over the legacy's `Math.abs(...) > N` micro-optimization.
- Multi-scan e2e fixture attaches `.url` directly onto each coords array (arrays are objects in JS), mirroring `_computeRayData`'s exact read pattern (`_coords[id].url`) — this exercises the real per-chunk-url code path rather than the existing force-directed test's shared `""` fallback key.

## Deviations from Plan

None - plan executed exactly as written, modulo the expected Task 1 scope-narrowing documented above (which is not a deviation from the plan's own acceptance criteria — `editor.html`'s WS branch and `bootProjector()` already called `setNodes(f.coords, f.url_roots)` / `setNodes(coords, res.url_roots)` exactly as Task 1's acceptance criteria require; this plan's Task 1 commit only had to add the camera-distance hook to satisfy Task 3's later dependency).

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- REAL-02 (per-URL multi-scan placement consumption + camera framing) is fully implemented and e2e-verified against a real rendered Chromium tab: two URLs render at distinct backend-resolved, non-overlapping roots; re-scanning never moves an old URL's root; the camera auto-frames the newest root on scan-end, correctly suppressed only when both the user-interaction and in-frustum conditions hold.
- `frameCameraToRoot` is now exported on the projector's returned object, available for `06-04`'s REAL-04 work (2D↔3D link arrow) if camera-relative framing is ever needed there, though REAL-04's arrow itself only needs `project()` (already exported, unchanged).
- No blockers. `_urlRootPositions`/`_urlBoundingRadii`/`_positions` Maps (already present from Wave 1) plus this plan's `_cameraTween`/`_userInteracted`/`_newestUrl` state give `06-03` (image billboards) and `06-04` (2D↔3D arrow) everything they need without further plumbing changes to `setNodes`.

---
*Phase: WFH-06-served-slate-3d-real-register*
*Completed: 2026-06-22*
