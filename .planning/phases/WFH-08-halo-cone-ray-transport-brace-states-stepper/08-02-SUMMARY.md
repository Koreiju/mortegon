---
phase: WFH-08-halo-cone-ray-transport-brace-states-stepper
plan: 02
subsystem: frontend
tags: [javascript, three-js, halo, cone-transport, projector, playwright, e2e]
status: complete

# Dependency graph
requires:
  - phase: WFH-08-halo-cone-ray-transport-brace-states-stepper
    plan: 01
    provides: "the live projector/halo render surface (brace-state wiring) this plan's cone transport composes around"
provides:
  - "fe/halo_cone.mjs — PURE cone-ray placement geometry: placeOnCone/placeCandidatesOnCone, consuming backend transport.{radial,along_ray} VERBATIM (D10), with a preserved 2D haloLayout fallback for non-3D-backed candidates"
  - "projector.placeHaloCandidates(apex, candidates) — render-only consumer; writes cone positions into the existing _positions bookkeeping + points-geometry buffer + image-sprite sync, so transported nodes keep their HSV/billboard identity"
  - "window.__mm_cone_positions() / window.__mm_proj_place_cone(apex, candidates) test hooks in editor.html"
  - "stub cone-ray transport e2e in halo.spec.js: monotonicity (on radial, not raw Euclidean distance) + delete-transports-next + zero-dasharray"
affects: [WFH-08-03, WFH-08-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure-geometry / thin-render-glue split (08-PATTERNS convention): halo_cone.mjs is THREE-free, dependency-injected ({project, azimuth, nodeWorldPosition}), unit-testable in plain Node — mirrors magic_markdown_halo.mjs::haloLayout's exact shape."
    - "radial is the apex-distance scalar GUARANTEED monotonic in similarity; along_ray is an orthogonal perpendicular offset. Raw Euclidean distance from the apex (Math.hypot(x,y,z)) combining both components is U-shaped, NOT monotonic — verified numerically (s=0.0->40.00, s=0.5->28.28, s=1.0->40.00) for the backend's own (1-s)*R / s*R formula. Both halo_cone.test.mjs and the e2e assert ordering on `radial` itself, never on combined Euclidean apex distance. This is documented inline in halo_cone.mjs's header comment for future readers."
    - "createProjector() requires window.THREE + a real canvas and was previously only exercised by Playwright e2e. projector.test.mjs now installs a minimal hand-rolled THREE shim (Vector3/BufferGeometry/BufferAttribute/Points/Scene/Camera/Renderer/Sprite) covering exactly the API surface createProjector touches, letting placeHaloCandidates run as a genuine Node unit test (the WR-2 'teeth' requirement) rather than a regression-only re-check of the pre-existing pure exports."
    - "Cone-transported nodes are EXISTING 3D-backed nodes that simply move — placeHaloCandidates writes into the SAME _positions Map + points-geometry buffer + _imageSprites the force-directed step already uses, so HSV/image identity is preserved for free (no separate render path)."

key-files:
  created:
    - backend/static/js/fe/halo_cone.mjs
    - backend/static/js/fe/halo_cone.test.mjs
  modified:
    - backend/static/js/fe/projector.mjs
    - backend/static/js/fe/projector.test.mjs
    - backend/templates/editor.html
    - frontend_e2e/halo.spec.js

decisions:
  - "Resolved the radial/along_ray monotonicity-vs-Euclidean-distance contradiction by treating `radial` (the backend's own apex-distance scalar, per routes.py's comment 'most-similar nearest the apex') as the authoritative metric for the monotonicity contract; `along_ray` is a perpendicular lateral offset that does not enter into that claim. Exposed `radial`/`alongRay` on the __mm_cone_positions test-hook records so e2e/consumer code asserts on the same metric the unit tests do."
  - "Built world-space ray composition (apex -> nodeWorldPosition(id)) rather than screen-space projection inside halo_cone.mjs, since projecting both endpoints through the same camera commutes with taking the ray in world space first — this keeps the module THREE-free per D-04 while satisfying the §O.18 apex->screen-projection(candidate.world_pos) contract."

# Metrics
metrics:
  duration: "~1 session (continuation)"
  completed: 2026-06-28
---

# Phase 8 Plan 02: HALO-03 cone-ray transport Summary

Frontend-only wiring of the §O.18 halo cone-ray transport: a new pure-geometry `fe/halo_cone.mjs`
module places retrieved 3D nodes on a shared cone whose apex is the 2D query element's screen
position, consuming the backend's normalized triple-product similarity (`transport.{radial,
along_ray}`) VERBATIM per D10, plus a `projector.placeHaloCandidates` render function that moves
existing 3D-backed nodes onto the cone while preserving their HSV/image identity.

## What was built

- **Task 1** — `backend/static/js/fe/halo_cone.mjs`: exports `placeOnCone(apex, candidate,
  projectFns, opts)` and `placeCandidatesOnCone(apex, candidates, projectFns, opts)`. For a
  candidate with a backing 3D node, the ray is `apex -> nodeWorldPosition(id)` (world-space
  equivalent of the §O.18 apex->screen-projection(world_pos) contract); the candidate is placed
  at `apex + ray_unit*radial + perp_unit*along_ray`, both consumed verbatim from the backend's
  `transport` object — never recomputed from `similarity`. Candidates without a 3D backing fall
  back to the existing `haloLayout` 2D polar placement, unchanged. `halo_cone.test.mjs` covers
  all 5 plan-mandated behaviors (monotonicity, apex composition, D10 verbatim consumption, 2D
  fallback, delete-and-replace ordering) — 5/5 passing.
- **Task 2** — `projector.mjs::placeHaloCandidates(apex, candidates)`: delegates all placement
  math to `halo_cone.placeCandidatesOnCone`, wiring the projector's own live `{project, azimuth,
  nodeWorldPosition}` closures; writes the resulting positions into the existing `_positions` Map,
  the live points-geometry buffer, and any attached image sprite, so transported nodes keep their
  HSV 6-vector fill or image billboard. Exposed via the export object plus a new `conePositions()`
  accessor. `editor.html` gained `window.__mm_cone_positions()` and `window.__mm_proj_place_cone()`
  test hooks, following the existing `__mm_proj_*` convention. `projector.test.mjs` gained a
  minimal hand-rolled THREE shim so `createProjector` (previously e2e-only) can run as a genuine
  Node unit test, plus the WR-2 "teeth" case asserting `placeHaloCandidates` places exactly the
  given ids and removes no existing node from `_positions` — 14/14 passing.
- **Task 3** — `frontend_e2e/halo.spec.js` gained `test.describe("cone-ray transport (HALO-03)")`:
  seeds 3 fixture 3D-backed nodes with backend-shaped transport values, drives the real
  `placeHaloCandidates` via the Task-2 hooks, and asserts (1) apex-distance (`radial`) monotonic in
  similarity, (2) deleting the top candidate transports the next-most-similar into the vacated
  nearest-apex slot, (3) zero `stroke-dasharray` anywhere in the document. Runs in the stub lane
  (both modes); fixture ids filtered per the Phase-6 lesson. 3/3 passing.

## Verification (automated — no screenshots)

- `node --test backend/static/js/fe/halo_cone.test.mjs backend/static/js/fe/projector.test.mjs`
  → **5/5 + 14/14**, both green.
- `npx playwright test --config=frontend_e2e/playwright.config.js halo.spec.js -g "cone"` → **3/3**.
- `npx playwright test --config=frontend_e2e/playwright.config.js halo.spec.js` (full file) →
  **10/10** — no regression to HALO-01/02/04.
- `npx playwright test --config=frontend_e2e/playwright.config.js black_slate.spec.js` →
  **6/6**, green (no-dotted/black-slate gate untouched).
- `npx playwright test --config=frontend_e2e/playwright.config.js projector.spec.js` →
  **5/5**, green (no regression to UMAP-01/REAL-01/02/03/04).
- The REPL `env-scenario --name apparition-mode` / `halo-chain-roundtrip` / `full-smoke` checks
  listed in the plan's `<verification>` section were **not run this session** — no backend was
  running at completion time, and these checks are supplementary (not gated by any task's
  `<verify>` block). Deferred to the orchestrator/next session if full-stack re-verification is
  desired before merge.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] e2e cone-distance assertion used raw Euclidean apex distance instead of `radial`**
- **Found during:** Task 3, first e2e run.
- **Issue:** The first draft of the cone-ray transport e2e asserted monotonicity on
  `Math.hypot(p.x, p.y, p.z)` (raw Euclidean distance from the apex). Since `radial` and
  `along_ray` are orthogonal components, combining them this way produces a U-shaped (non-monotonic)
  curve across similarity — confirmed by the failing test run (cone_a's combined distance was
  LARGER than cone_b's, despite cone_a being more similar). This mirrors the same math resolved
  during Task 1's design (see Decisions above) but had not yet been propagated to the test-hook
  payload or the e2e assertions.
- **Fix:** Added `radial`/`alongRay` fields to `__mm_cone_positions()`'s returned records in
  `projector.mjs`, and rewrote both e2e assertions (monotonicity + delete-transports-next) to
  compare `p.radial` instead of `Math.hypot(p.x, p.y, p.z)` — the same metric `halo_cone.test.mjs`
  already asserts on.
- **Files modified:** `backend/static/js/fe/projector.mjs`, `frontend_e2e/halo.spec.js`.
- **Commit:** `221a3c8`.

## Known Stubs

None — no stub patterns (hardcoded empty values flowing to UI, placeholder text, unwired data
sources) found in any file created or modified by this plan.

## Threat Flags

None — the only new consumption is a read-only path over the EXISTING `/apparitions?transport=1`
route (T-08-05 in the plan's threat model, pre-existing, accepted). No new endpoints, no new auth
paths, no new schema.

## Next-plan readiness (08-03 / 08-04)

The cone-ray transport render surface (`placeHaloCandidates`, `__mm_cone_positions`,
`__mm_proj_place_cone`) is live and unit+e2e verified in the stub lane. 08-03 (STEP-01
`flyToNode`/`highlightNode` + `stepper.mjs`) and 08-04 (the D-01 REAL-subsystem cone-transport
probe + `--self-test`) build on this same projector/halo surface — 08-04 specifically needs a
running real backend to exercise the REAL `/apparitions?transport=1` path end-to-end, which this
plan's stub-lane e2e deliberately does not attempt (per the plan's own Task-3 scope: "Keep this
fully inside the stub lane... the REAL-subsystem assertion is 08-04").

## Self-Check: PASSED

- FOUND: backend/static/js/fe/halo_cone.mjs
- FOUND: backend/static/js/fe/halo_cone.test.mjs
- FOUND: backend/static/js/fe/projector.mjs (placeHaloCandidates present)
- FOUND: backend/static/js/fe/projector.test.mjs (WR-2 teeth case present)
- FOUND: backend/templates/editor.html (__mm_cone_positions / __mm_proj_place_cone hooks present)
- FOUND: frontend_e2e/halo.spec.js (cone-ray transport (HALO-03) describe block present)
- FOUND commit 97eab6e (Task 1: halo_cone.mjs + halo_cone.test.mjs)
- FOUND commit 41d7e98 (Task 2: placeHaloCandidates wiring)
- FOUND commit 221a3c8 (Task 3: stub cone-ray transport e2e)
