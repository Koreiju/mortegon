---
phase: WFH-06-served-slate-3d-real-register
verified: 2026-06-23T00:00:00Z
status: passed
score: 16/16 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 6: 3D Real Register in the Served Slate — Verification Report

**Phase Goal:** The served `/` black-slate frontend renders the full 3D Real register — UMAP-linear-radial force-directed layout converging along root-URL rays, per-URL multi-scan placement with camera framing, image billboards with single-fetch persistence, and solid (headless) 2D↔3D link arrows — bringing the legacy `cp/` 3D features into the `fe/` idiom.
**Verified:** 2026-06-23
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

The four REAL features are genuinely ported into the served `fe/projector.mjs` closure factory and wired through `editor.html`, with automated behavioral proof: the project's verification idiom (a screenshot is not feature proof) is the unit suite + the served-page Playwright e2e. Both ran green during this verification:

- `node --test backend/static/js/fe/projector.test.mjs` → **13/13 passed** (re-run live).
- `WFH_FAKE_SLM=1 WFH_FAKE_EMBEDDER=1 NO_WEBDRIVER=1 npx playwright test --config=frontend_e2e/playwright.config.js` → **30/30 passed** (re-run live). All 5 REAL projector tests EXECUTED against the served `/` page (not skipped — WebGL available): UMAP-01, REAL-01, REAL-02, REAL-03, REAL-04, plus `black_slate.spec.js`'s no-dasharray gate.

Because each behavior-dependent truth (force-step state transition + collider spacing, multi-scan non-overlap + old-root-stable + camera framing, image paint/persist/placeholder-not-cached, arrow tracking + off-frustum hide) is exercised by a passing e2e against the live served surface, all are VERIFIED on behavior, not symbol presence alone.

### Observable Truths

| #   | Truth (Roadmap SC / plan must_have)                                                                 | Status     | Evidence |
| --- | -------------------------------------------------------------------------------------------------- | ---------- | -------- |
| 1   | (SC1/REAL-01) Chunks lay by UMAP then converge force-directed along root-URL rays; never off-ray   | ✓ VERIFIED | `_computeRayData`+`_stepForceDirected` (projector.mjs:299-370) seed `_positions` and slide each node along `rootPos + rayDir*radius`; REAL-01 e2e (projector.spec.js:40) asserts every node parallel to its `rayDir` — passed |
| 2   | (REAL-01) Pairwise chunk distance never settles below MIN_SEPARATION once force active              | ✓ VERIFIED | `colliderRadialForce` hard floor at MIN_SEPARATION=2.52; unit test + REAL-01 e2e min-spacing assertion against 2.52 — passed |
| 3   | (REAL-01) Above MIN_SEPARATION the collider exerts zero force (no soft falloff)                     | ✓ VERIFIED | `colliderRadialForce` returns `{forceA:0,forceB:0}` for `dist >= MIN_SEPARATION` (projector.mjs:99); unit test "zero push at/above MIN_SEPARATION" — passed |
| 4   | (REAL-01) No chunk settles at a Fibonacci/concentric angular position once umap_canonical applied   | ✓ VERIFIED | No `_fibonacciPosition` in projector.mjs; REAL-01 e2e asserts radii spread > 0 (force sliding, not a fixed ring) — passed |
| 5   | (SC2/REAL-02) Each URL's chunks cluster at its backend root; a second URL lands non-overlapping     | ✓ VERIFIED | `setNodes` consumes `url_roots[url].root_position/bounding_radius` (projector.mjs:471-479); REAL-02 e2e centroid separation >= 12 — passed |
| 6   | (REAL-02) Re-scanning the first URL does not move the second URL's root (old roots never move)       | ✓ VERIFIED | REAL-02 e2e asserts urlA's a1/a2/a3 moved < 1.0 across scan B — passed |
| 7   | (SC2/REAL-02) On scan-end the camera tweens to frame the newest root (unless interacted AND in-frustum) | ✓ VERIFIED | `frameCameraToRoot`+`_stepCameraTween` (cubic ease ~600ms); suppress = `_userInteracted && _isRootInFrustum` (projector.mjs:487); REAL-02 e2e asserts camera shifted toward urlB after scan B — passed |
| 8   | (REAL-02) url_roots from WS umap_canonical AND boot /api/recompute_umap both reach the projector     | ✓ VERIFIED | editor.html:308 `setNodes(f.coords, f.url_roots)`; editor.html:347 `setNodes(coords, res.url_roots)` — line-296 drop closed |
| 9   | (SC3/REAL-03) An image chunk paints a THREE.Sprite billboard textured from its image URL             | ✓ VERIFIED | `spawnImageBillboards` creates `THREE.Sprite`+`SpriteMaterial({map:tex})` (projector.mjs:558-559); REAL-03 e2e asserts paint — passed |
| 10  | (REAL-03) Two chunks at the same URL share one THREE.Texture instance (single GPU upload)            | ✓ VERIFIED | `byUrl` grouping → one `loadAndCacheImage` per URL; `_textureCache` Map + `_inflight` dedup (WR-02 fix); REAL-03 e2e — passed |
| 11  | (REAL-03) Fetch order in-mem → IDB → proxy → direct; cached texture survives re-render, zero new net | ✓ VERIFIED | `loadAndCacheImage`/`_loadAndCacheImageInner` order (projector.mjs:221-269); REAL-03 e2e asserts `netFetchCount` unchanged after `__mm_rerender` — passed |
| 12  | (REAL-03) X-Image-Proxy-Note placeholder is never cached as a successful image                       | ✓ VERIFIED | `note` read before caching; `if(!note) idbSaveBlob` AND `if(tex && !isPlaceholder) _textureCache.set` (CR-01 fix, projector.mjs:251-268); REAL-03 e2e step-3 placeholder-not-cached — passed |
| 13  | (SC4/REAL-04) Every mounted panel cell carries data-3d-node-id equal to its concept/chunk id          | ✓ VERIFIED | editor.html:156 `cell.setAttribute("data-3d-node-id", id)` at mount; REAL-04 e2e pins a card and finds the line — passed |
| 14  | (REAL-04) Per frame a solid SVG line connects each pinned panel to its 3D node's projected screen pos | ✓ VERIFIED | `drawConcept3DLinks` invoked per `onFrame` (editor.html:361); draws `<line>` to `project()`ed px; REAL-04 e2e — passed |
| 15  | (REAL-04) The line tracks the moving node (follows the force-step position each frame)               | ✓ VERIFIED | reads `nodeWorldPosition(nodeId)` (post force-step `_positions`); REAL-04 e2e orbits camera, asserts endpoint moved — passed |
| 16  | (SC4/REAL-04) Off-frustum NDC z∉[-1,1] hides; line solid #ffd700, headless, no stroke-dasharray       | ✓ VERIFIED | hide test on ndcX/Y/Z (WR-04 fix, projector.mjs:632); stroke `#ffd700`, no dasharray, `removeAttribute("marker-end")`; REAL-04 e2e + black_slate.spec no-dasharray gate — passed |

**Score:** 16/16 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `backend/static/js/fe/projector.mjs` | Pure ray/collider exports + closure force step + camera framing + image cache chain + drawConcept3DLinks | ✓ VERIFIED | All symbols present (computeRayDir, colliderRadialForce, _stepForceDirected, frameCameraToRoot, loadAndCacheImage, spawnImageBillboards, drawConcept3DLinks); 763 lines, no stubs |
| `backend/static/js/fe/projector.test.mjs` | Ray-math + collider unit tests | ✓ VERIFIED | 13/13 pass; COLLIDER_SAFETY=1.4 / MIN_SEPARATION=2.52 asserted |
| `frontend_e2e/projector.spec.js` | force-directed + multi-scan + image + arrow e2e blocks | ✓ VERIFIED | 5 test blocks present (UMAP-01 + REAL-01..04), all pass against served `/` |
| `backend/templates/editor.html` | url_roots wiring + data-3d-node-id + #link-layer + test hooks | ✓ VERIFIED | `setNodes(f.coords, f.url_roots)` WS + boot; setAttribute at mount; #link-layer SVG; all `__mm_proj_*` hooks |

### Key Link Verification

| From | To | Via | Status |
| ---- | -- | --- | ------ |
| editor.html | projector.mjs | `setNodes(f.coords, f.url_roots)` (WS) + `setNodes(coords, res.url_roots)` (boot) | ✓ WIRED — line-296 drop closed |
| projector.mjs | backend url_roots contract | consumes `root_position`/`bounding_radius`, never recomputes (D10/A2: no SAFETY_GAP) | ✓ WIRED |
| editor.html | projector.mjs | `onFrame(() => drawConcept3DLinks(linkLayer))` reading `[data-3d-node-id]` | ✓ WIRED |
| projector.mjs | /api/image_proxy + IndexedDB | `toProxy()` → `/api/image_proxy?url=`; `indexedDB.open("wfh_texture_cache",1)` store `textures`; reads `X-Image-Proxy-Note` | ✓ WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Pure ray/collider math | `node --test backend/static/js/fe/projector.test.mjs` | 13/13 passed | ✓ PASS |
| Full served-page render suite (incl. 5 REAL tests) | `npx playwright test --config=frontend_e2e/playwright.config.js` (fake-stack env) | 30/30 passed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| REAL-01 | 06-01 | Force-directed ray convergence + hard collider; no Fibonacci | ✓ SATISFIED | Truths 1-4; unit + REAL-01 e2e |
| REAL-02 | 06-02 | Per-URL multi-scan placement + camera framing | ✓ SATISFIED | Truths 5-8; REAL-02 e2e |
| REAL-03 | 06-03 | Image billboards, single-fetch persistence, placeholder-not-cached | ✓ SATISFIED | Truths 9-12; REAL-03 e2e |
| REAL-04 | 06-04 | Solid headless 2D↔3D arrow, off-frustum hide | ✓ SATISFIED | Truths 13-16; REAL-04 e2e + black_slate gate |

All four phase requirement IDs are declared (one per plan frontmatter), present in REQUIREMENTS.md (lines 12-15, marked [x] Complete), and satisfied with code+test evidence. No orphaned requirements (REQUIREMENTS.md maps exactly REAL-01..04 to phase 6).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No TBD/FIXME/XXX/HACK/TODO in any modified file | — | None |
| — | — | No `SAFETY_GAP`, no `ForceLayoutMixin`, no `Object.assign(prototype)`, no real `stroke-dasharray` attribute (only explanatory comments) | — | None — prohibitions held |

No blocker or warning anti-patterns. The one code-review BLOCKER (CR-01 placeholder cache poisoning) was fixed (commit 4af065c) and is confirmed in source (projector.mjs:251-268, in-mem write gated by `!isPlaceholder`); 3 warnings fixed (WR-01/02/04). WR-03 (an edge-case camera-frame-suppression warning on the REAL-04 `""`-URL boot path) was deferred with a recorded rationale in 06-REVIEW-FIX.md — it requires a coordinated REAL-04 test change (settle/cancel the auto-frame tween before asserting orbit-tracking), out of scope for a source-only fix. This does NOT block the goal: the REAL-02 camera-framing truth (#7) is independently proven by the REAL-02 multi-scan e2e (distinct `.url` roots, step-c assertion passes), and the REAL-04 arrow-tracking truth (#15) passes as written. WR-03 is a known, documented limitation with a follow-up recommendation, not an unachieved must-have.

### Gaps Summary

No gaps. All 4 roadmap success criteria and all 16 derived/plan must-have truths are verified against the codebase with passing automated tests run live during this verification. The served `fe/projector.mjs` genuinely renders all four REAL features (force-directed rays, per-URL multi-scan + camera framing, image billboards with single-fetch persistence, solid headless 2D↔3D arrows) and the legacy `cp/` features are ported into the closure-factory `fe/` idiom (no class+mixin shape).

**Scope note (honest deferral, not a gap):** Per 06-CONTEXT.md's verification gate, this phase's gate is the stub-backed e2e + unit + REPL scenarios (all green). The full real-stack (`all_real:true`) acceptance — image billboards painting from a real archive.org scan (REAL-03 production data path, since `umap_canonical` carries no image-URL field today) and the per-URL ray separation under production frames (chunks resolve to the shared `""` root absent a per-chunk `.url` field, IN-03) — is explicitly deferred to the milestone-end consolidated run (rides `probe_live_archive_scan.py` + `probe_live_dominance_and_timed_scan.py`). This is the documented phase contract, not a missed deliverable.

---

_Verified: 2026-06-23_
_Verifier: Claude (gsd-verifier)_
