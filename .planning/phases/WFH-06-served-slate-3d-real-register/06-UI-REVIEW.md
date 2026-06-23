---
phase: 6
slug: served-slate-3d-real-register
audited: 2026-06-23
baseline: 06-UI-SPEC.md (locked design contract)
screenshots: not captured (no dev server running on :8080/:3000 at audit time — code-only audit)
advisory: true
blocking: false
pillar_scores:
  copywriting: 4
  visuals: 4
  color: 3
  typography: 4
  spacing: 4
  experience_design: 3
overall_score: 22
overall_max: 24
---

# Phase 6 — UI Review

**Audited:** 2026-06-23
**Baseline:** `.planning/phases/WFH-06-served-slate-3d-real-register/06-UI-SPEC.md`
**Screenshots:** not captured — no dev server detected on `:8080` or `:3000` at audit time; this is a code-level audit against `backend/static/js/fe/projector.mjs` and `backend/templates/editor.html`.

**Audit framing:** This is a brownfield port of a THREE.js 3D projector surface, not a conventional component UI. Per the UI-SPEC, Copywriting / Typography / Registry-Safety are legitimately N/A (no new glyphs/forms rendered) and are scored on that justified basis. This review is ADVISORY (non-blocking) — the phase is already verified via unit + e2e suites (`projector.test.mjs` 13/13, `projector.spec.js` 5/5, `black_slate.spec.js` 6/6 per the SUMMARY files).

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|--------------|
| 1. Copywriting | 4/4 | N/A correctly honored — zero copy surfaces introduced; UI-SPEC's N/A rows are not silently skipped, they are explicitly absent from the implementation |
| 2. Visuals | 4/4 | Ray-constrained force layout, per-URL camera framing, shared-texture billboards, and the single link arrow are all implemented exactly per the codified algorithms, with verbatim defensive fallbacks preserved |
| 3. Color | 3/4 | Contract honored (HSV backend-rendered, `#ffd700` reserved for the arrow only, no hardcoded colors in `projector.mjs`) but `stroke-opacity="0.85"` is an undeclared addition not specified anywhere in the UI-SPEC's accent-arrow contract |
| 4. Typography | 4/4 | N/A correctly honored — zero text glyphs rendered inside the WebGL viewport; no new font-size/weight surface introduced |
| 5. Spacing | 4/4 | All locked 3D-geometric constants (`NODE_RADIUS=0.9`, `COLLIDER_SAFETY=1.4`, `MIN_SEPARATION=2.52`, camera `0.6×`/`3.0×` bounds) match the UI-SPEC exactly, verified against both unit test assertions and e2e spacing checks |
| 6. Experience Design | 3/4 | Force step, camera framing, image cache, and arrow tracking all degrade gracefully (defensive guards everywhere), but the arrow's `removeAttribute('marker-end')` call is a dead no-op that masks a latent risk if `<line>` creation logic ever changes |

**Overall: 22/24**

---

## Top Priority Fixes (Advisory — Non-Blocking)

1. **Undeclared `stroke-opacity="0.85"` on the link arrow** (`backend/static/js/fe/projector.mjs:665`) — The UI-SPEC's REAL-04 color contract specifies `stroke="#ffd700"`, `stroke-width="2"`, solid, headless — it says nothing about opacity. An 0.85 opacity is a visual softening of "the ONE saturated stroke" the spec calls out as deliberately full-strength accent. This is a minor, low-risk deviation (not a forbidden pattern, doesn't violate the no-dasharray/no-marker-end rules), but it is an unspecified value introduced without a corresponding UI-SPEC update or Assumption-log entry. **Fix:** either add `stroke-opacity: 1` to match the contract literally, or add a one-line Assumption note (mirroring how A1/A2/A3 are logged) documenting why 0.85 was chosen, so future drift-checking doesn't have to rediscover this independently.

2. **Dead `removeAttribute('marker-end')` call is a no-op that papers over (rather than guards against) marker-end ever being set** (`backend/static/js/fe/projector.mjs:667`) — the `<line>` element is created fresh via `document.createElementNS` immediately above this call (line 662), so it never has a `marker-end` attribute to remove in the first place. The call is harmless today but gives a false sense of "headless enforced here" — if a future refactor ever clones an existing SVG element (e.g. from a template with a `marker-end` already set) instead of creating fresh, this line would still pass review but the cloned element could carry a stale marker-end if the clone path bypasses this exact code path. **Fix:** either delete the dead call (it does nothing useful as currently written) or replace it with an explicit assertion/comment clarifying it is defensive-only for a hypothetical future code path, not enforcing anything against the current creation flow.

3. **`#link-layer`'s full-viewport SVG host has zero element-count bound** — `drawConcept3DLinks` caches `<line>` elements per card via a `WeakMap` (good — update not recreate), and early-outs to a stale-line sweep when zero `[data-3d-node-id]` cards exist (T-06-10's accepted DoS disposition). However there is no upper bound on simultaneous pinned-panel count feeding into the per-frame `querySelectorAll("[data-3d-node-id]")` + `getBoundingClientRect()` calls — every mounted panel cell (not just pinned ones) carries `data-3d-node-id` (editor.html:156, in the unconditional `render()` loop), so the link-layer projects and (until off-frustum-hidden) draws a line for **every rendered panel**, not just "pinned" panels as the UI-SPEC's REAL-04 section implies ("every pinned panel that has a 3D-resident node carries a `data-3d-node-id` attribute"). In the current implementation every mounted card gets the attribute regardless of pin state, which is broader than the spec's stated scope. **Fix:** either gate `data-3d-node-id` authorship to only pinned panels (matching the spec's literal language), or update the UI-SPEC/CONTEXT to reflect that this phase intentionally broadened scope to "every mounted panel," since as-built every panel — pinned or not — will draw an arrow to its 3D node once one exists, which could visually flood the viewport with lines as panel count grows.

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)
No copy surfaces are introduced anywhere in `projector.mjs` or the projector-related portions of `editor.html`. Verified via grep: zero string literals resembling CTA/empty/error copy inside the 3D-specific code paths (`_stepForceDirected`, `frameCameraToRoot`, `spawnImageBillboards`, `drawConcept3DLinks`). The UI-SPEC's N/A declaration is honored, not skipped — there is no placeholder "no chunks loaded" message rendered in the WebGL canvas, consistent with the black-slate minimalism the spec calls out (`06-UI-SPEC.md` Copywriting Contract section, "no 'no data' placeholder text appears in the viewport"). Pre-existing 2D editor copy (the `#bar` hint text, autocomplete UI) is out of this phase's scope and untouched.

### Pillar 2: Visuals (4/4)
All four REAL-0x visual contracts are implemented per the codified algorithm:
- REAL-01 (`projector.mjs:299-370`): `_computeRayData`/`_stepForceDirected` mirror the locked ray-constrained collider algorithm verbatim, including the defensive root-not-yet-placed origin fallback (lines 307-313) that the SUMMARY explicitly calls out as intentionally preserved rather than optimized away.
- REAL-02 (`projector.mjs:384-449`): `frameCameraToRoot`/`_stepCameraTween`/`_applyCameraBounds` implement the cubic-ease tween and adaptive `0.6×`/`3.0×` bounds exactly, with the two-condition suppression gate (`_userInteracted && _isRootInFrustum`) implemented as an AND, not an OR, matching the spec's explicit requirement (line 487: `const suppress = _userInteracted && _isRootInFrustum(_newestUrl);`).
- REAL-03 (`projector.mjs:534-588`): `spawnImageBillboards` groups by exact URL before fetching, sharing one `THREE.Texture` per URL across multiple `THREE.Sprite` instances; base sizes `1.0`/`0.55` with aspect correction match the spec verbatim (lines 556-561).
- REAL-04 (`projector.mjs:603-677`): `drawConcept3DLinks` projects via the shared `project()` helper (no parallel NDC→px logic), uses `getBoundingClientRect()` canvas-relative px (not `window.innerWidth`), and computes a nearest-edge anchor — matching the legacy port's intended visual behavior.

No Fibonacci/concentric final-position code exists anywhere in `_computeRayData`/`_stepForceDirected` — the only positional fallback is the degenerate single-point case (`radius:0`), not a sweep.

### Pillar 3: Color (3/4)
The 60/30/10 contract (`#000000` viewport background / silver structural elements / `#ffd700` accent) is honored at the code level:
- `scene.background = new THREE.Color(0x000000)` (line 119) — true black, matching the dominant 60% role.
- Chunk/billboard fill is exclusively backend-rendered HSV (`buildPointArrays`, lines 27-51) — the frontend never invents a hue sweep except the documented 3-vector bootstrap fallback (lines 43-44), which is explicitly scoped as transient.
- `#ffd700` (line 663) is the only hardcoded hex literal inside `projector.mjs`'s drawing logic, and it is applied to exactly one element type (the link-layer `<line>`) — no other element in the file carries a saturated color.
- **Deduction:** `stroke-opacity="0.85"` (line 665) is an undeclared modification of the "ONE saturated stroke" contract. The UI-SPEC's Color section states the accent is "reserved EXCLUSIVELY for the 2D↔3D link arrow" at full `#ffd700` — it does not authorize a softened-opacity variant, and no Assumption (A1/A2/A3) was logged for this choice the way the COLLIDER_SAFETY discrepancy (A1) was. This is a minor, non-blocking but real spec-drift instance.

editor.html's surrounding 2D chrome colors (`#9ae6b4`, `#c0414a`, `#6b7280`, `#c0c0c0`) are all out of this phase's scope (pre-existing black-slate theme tokens, not introduced by REAL-01..04) and are not counted against this phase's color budget.

### Pillar 4: Typography (4/4)
No new text rendering is introduced inside the WebGL viewport by any of the four REAL-0x plans. `editor.html`'s HUD bar (`#bar`, 11px monospace) and panel typography predate this phase and are unmodified by the projector-related diffs. The `#link-layer` SVG host carries zero `<text>` elements — only `<line>`. This matches UI-SPEC Assumption A2 ("zero in-canvas text is added by REAL-01..04") exactly.

### Pillar 5: Spacing (4/4)
All locked geometric constants verified present and correct in `projector.mjs`:
- `NODE_RADIUS = 0.9` (line 68)
- `COLLIDER_SAFETY = 1.4` (line 69) — correctly the shipped legacy value per Assumption A1, not the doc's `≥2.0`
- `MIN_SEPARATION = 2 * NODE_RADIUS * COLLIDER_SAFETY` evaluates to `2.52` (line 70), and the e2e test (`frontend_e2e/projector.spec.js:118`) asserts against `2.52`, explicitly noting "not 3.6" inline — proving the test itself guards against silent re-derivation toward the doc's `2.0` value.
- Camera bounds `minDistance = 0.6 × cluster_radius` / `maxDistance = 3.0 × max(|pos|)` implemented verbatim in `_applyCameraBounds` (lines 436-449), with floor clamps (`Math.max(2, …)` / `Math.max(60, …)`) that are a defensive addition beyond the literal spec text but do not contradict it (the spec only specifies the multipliers, not floor behavior, so this is a reasonable, undocumented-but-harmless implementation choice — not penalized here since it doesn't change behavior in the populated-scene case the multipliers govern).
- Billboard base sizes `1.0`/`0.55` (lines 556-557) match exactly.
- `SAFETY_GAP` (5.0, per-URL placement gap) does not appear anywhere in `projector.mjs` — correctly absent per Assumption A2 (backend owns this constant; the frontend never recomputes per-URL placement).

### Pillar 6: Experience Design (3/4)
State coverage is strong: every async/IO path (`idbOpen`, `idbLoadTexture`, `loadAndCacheImage`, `toProxy`) degrades to `null`/fallback rather than throwing, matching the spec's no-mocks-adjacent resilience expectations for a render-only surface. The X-Image-Proxy-Note cache-poisoning guard is correctly checked before any cache write on both the in-memory Map and IndexedDB tiers (lines 254, 268), closing the exact gap the UI-SPEC calls out. The off-frustum hide for the link arrow correctly tests the TRUE `[-1,1]` NDC range on all three axes (lines 632, citing a documented WR-04 fix for an x/y-blind-spot bug caught during the port) rather than the weaker `inFront` flag alone — this is a genuine quality signal, not just contract compliance.

**Deductions:**
- The dead `removeAttribute('marker-end')` no-op (finding #2 above) is a code-quality smell that could mask a future regression path.
- `data-3d-node-id` is authored on every mounted panel cell unconditionally (`editor.html:156`), not gated to "pinned" panels as the UI-SPEC's REAL-04 prose states ("every pinned panel that has a 3D-resident node"). This means the link-layer will draw an arrow to every visible panel's 3D node, not just ones the user has explicitly pinned — a behavioral broadening relative to the spec's stated scope that has UX implications (more lines on screen than the spec implies) the SUMMARY does not call out as a deliberate decision.

---

## Files Audited
- `backend/static/js/fe/projector.mjs` (full read — 762 lines)
- `backend/templates/editor.html` (full read — 440 lines)
- `.planning/phases/WFH-06-served-slate-3d-real-register/06-UI-SPEC.md`
- `.planning/phases/WFH-06-served-slate-3d-real-register/06-CONTEXT.md`
- `.planning/phases/WFH-06-served-slate-3d-real-register/06-01-PLAN.md`
- `.planning/phases/WFH-06-served-slate-3d-real-register/06-04-PLAN.md`
- `.planning/phases/WFH-06-served-slate-3d-real-register/06-01-SUMMARY.md`
- `.planning/phases/WFH-06-served-slate-3d-real-register/06-02-SUMMARY.md`
- `.planning/phases/WFH-06-served-slate-3d-real-register/06-03-SUMMARY.md`
- `.planning/phases/WFH-06-served-slate-3d-real-register/06-04-SUMMARY.md`
- `frontend_e2e/projector.spec.js` (grep-level: COLLIDER_SAFETY/MIN_SEPARATION assertions)
- `frontend_e2e/black_slate.spec.js` (grep-level: no-dotted assertion)
