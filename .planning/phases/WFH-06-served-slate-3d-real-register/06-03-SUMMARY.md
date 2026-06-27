---
phase: WFH-06-served-slate-3d-real-register
plan: 03
subsystem: frontend-3d-projector
tags: [three.js, indexeddb, image-cache, sprite-billboard, playwright, real-03]

# Dependency graph
requires:
  - phase: WFH-06-01
    provides: "setNodes(coords, urlRoots) extended signature; _positions/_nodeRayData Maps; NODE_RADIUS=0.9 collider constant"
  - phase: WFH-06-02
    provides: "frameCameraToRoot/_applyCameraBounds camera-tween scaffolding; _newestUrl bookkeeping pattern"
provides:
  - "loadAndCacheImage(url) — ordered single-fetch image cache chain (in-mem Map -> IndexedDB blob -> /api/image_proxy -> direct fetch), ported from cp/sprite_manager.js, with the X-Image-Proxy-Note cache-poisoning guard checked before any IndexedDB write"
  - "spawnImageBillboards(imageMap) — groups chunk ids by URL so duplicate URLs share ONE THREE.Texture/network fetch; per-chunk aspect-corrected THREE.Sprite (base size 1.0 primary / 0.55 secondary)"
  - "lastCoords()/lastRoots()/netFetchCount() accessors on the projector's returned object"
  - "window.__mm_proj_image / window.__mm_proj_net_count test hooks in editor.html"
  - "__mm_rerender now also re-invokes the projector's last-known frame (alongside the pre-existing EDIT-03 2D panel render), proving image-texture cache persistence across re-render with zero new network requests"
  - "REAL-03 e2e block in projector.spec.js: paints an image via the proxy route, asserts zero new fetches after __mm_rerender(), asserts an X-Image-Proxy-Note placeholder is never cached as a successful image"
affects: [WFH-06-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ordered single-fetch chain with EXACTLY this precedence: in-mem Map (per-session) -> IndexedDB blob (cross-session, DB 'wfh_texture_cache' / store 'textures' / keyPath 'url', reused verbatim from cp/sprite_manager.js so existing user caches carry over) -> /api/image_proxy (CORS-bypass, tried first over direct) -> direct fetch (last-resort fallback)"
    - "Cache-poisoning guard: the X-Image-Proxy-Note response header (present on a 200-status 1x1 transparent-PNG placeholder, NOT a non-ok HTTP status) is read BEFORE the IndexedDB write decision — `if (!note) idbSaveBlob(...)` — so a proxy failure's placeholder is never persisted as a successful cache entry"
    - "Shared-texture-by-URL grouping: spawnImageBillboards groups chunk ids into a Map keyed by exact URL string before calling loadAndCacheImage once per unique URL, then assigns the SAME THREE.Texture to every chunk's THREE.Sprite at that URL (single GPU upload, no duplicate decode/fetch)"
    - "Image billboards participate in the same _positions/_nodeRayData bookkeeping the force/collider step already maintains, so they share NODE_RADIUS=0.9 with text/point billboards automatically — no new spacing constant introduced"
    - "_syncImageSpritePositions() runs every animate() frame (mirroring _stepForceDirected's per-frame convention) to keep sprites glued to their chunk's collider-moved position"

key-files:
  created: []
  modified:
    - backend/static/js/fe/projector.mjs
    - backend/templates/editor.html
    - frontend_e2e/projector.spec.js

key-decisions:
  - "Image URLs are NOT carried by the production umap_canonical frame today (confirmed by grep of ws_frames.py::build_umap_canonical before any code was written) — per the plan's explicit A2/D10 scope note, this plan does NOT invent a new frame field. Images are driven exclusively via the new window.__mm_proj_image test hook; production wiring of a real image-URL field into umap_canonical is deferred to the milestone-end real-stack probe (scripts/probe_live_archive_scan.py), not this plan."
  - "window.__mm_rerender naming collision: the plan's Task 2 text specified binding a NEW window.__mm_rerender, but that global was already bound for EDIT-03 (`() => render()`) with an existing Playwright assertion in frontend_e2e/edit.spec.js (line ~202). Resolved by combining both behaviors in one function — `render()` followed by `projector.setNodes(projector.lastCoords(), projector.lastRoots())` guarded by `if (projector)` — rather than overwriting the EDIT-03 contract. Verified safe because setNodes() never touches _imageSprites/_chunkImageUrl (it only disposes the THREE.Points cloud), so re-invoking it with the SAME last-known frame causes no new fetches and no sprite loss. Confirmed via a full edit.spec.js run (8/8 green, including the EDIT-03 test) after the change."
  - "Scope-narrowed URL-grouping to exact-string match rather than porting cp/sprite_manager.js's fuzzy Jaccard near-duplicate URL grouping (tokenizeUrl/extractArea). The plan's Task 2 acceptance criteria only requires 'two chunks at the same URL share one THREE.Texture' (exact match), not near-duplicate detection across differently-formatted URLs pointing at the same resource — the simpler exact-Map grouping satisfies the stated criteria without importing unrequested fuzzy-matching complexity."
  - "Read backend/static/js/cp/sprite_manager.js (not cp/animation.js, which the plan's read_first pointer suggested) for the verbatim sprite-scale/aspect-correction algorithm — grepping animation.js turned up no Sprite/SpriteMaterial/scale.set matches; sprite_manager.js (lines ~93-140) is the actual source of the baseSize=1.0/0.55 + aspect-ratio scale.set logic, confirmed and ported from there instead."

requirements-completed: [REAL-03]

# Metrics
duration: 70min
completed: 2026-06-23
status: complete
---

# Phase 6 Plan 3: Image Billboards (IndexedDB Cache + Ordered Fetch + Shared Texture) Summary

**Ordered image-cache chain (in-mem Map -> IndexedDB blob -> /api/image_proxy -> direct fetch) ported verbatim from `cp/sprite_manager.js` into `fe/projector.mjs`, with the X-Image-Proxy-Note cache-poisoning guard enforced before any IndexedDB write, plus `spawnImageBillboards()` creating aspect-corrected `THREE.Sprite` billboards that share one `THREE.Texture` per URL and the existing `NODE_RADIUS=0.9` collider.**

## Performance

- **Duration:** 70 min
- **Started:** 2026-06-23T00:10:00Z (approx)
- **Completed:** 2026-06-23T01:20:00Z (approx)
- **Tasks:** 3
- **Files modified:** 3 (projector.mjs, editor.html, projector.spec.js)

## Accomplishments
- Ported `cp/sprite_manager.js`'s IndexedDB texture cache (DB `wfh_texture_cache`, store `textures`, keyPath `url`, reused verbatim so existing user caches carry over without migration) and its ordered single-fetch chain (in-mem -> IndexedDB -> proxy -> direct) into `projector.mjs` as `loadAndCacheImage(url)`
- Enforced the `X-Image-Proxy-Note` cache-poisoning guard exactly: the header is read from the fetch response BEFORE the IndexedDB write decision, so a proxy-failure placeholder (HTTP 200 + 1x1 transparent PNG + the header) is never persisted as a successful cache entry
- Added `spawnImageBillboards(imageMap)`: groups chunk ids by exact URL, calls `loadAndCacheImage` once per unique URL, and assigns the SAME `THREE.Texture` to every chunk's own aspect-corrected `THREE.Sprite` (base size 1.0 primary / 0.55 secondary, `scale.set(baseSize*aspect, baseSize, 1)` if `aspect>=1` else `scale.set(baseSize, baseSize/aspect, 1)`) — ported verbatim from `cp/sprite_manager.js`'s `buildSprite`
- Image-bearing chunks participate in the same `_positions`/`_nodeRayData` Maps the force/collider step already maintains, so they automatically share `NODE_RADIUS=0.9` with text/point billboards — no new spacing constant was introduced
- Added `_syncImageSpritePositions()`, run every `animate()` frame, to keep sprites glued to their chunk's collider-moved position
- Added `window.__mm_proj_image` / `window.__mm_proj_net_count` test hooks in `editor.html`; resolved a naming collision on the pre-existing `window.__mm_rerender` (used by EDIT-03) by combining both behaviors rather than overwriting the existing contract
- New REAL-03 e2e block in `projector.spec.js`: routes `/api/image_proxy` to a real test PNG, asserts an image sprite paints with at least one real network fetch, asserts `__mm_rerender()` issues ZERO new fetches for the same image (cache persistence), and asserts a second URL whose proxy response carries `X-Image-Proxy-Note` re-fetches on a subsequent load rather than returning a cached placeholder hit
- Full regression confirmed green: `node --test projector.test.mjs` (1/1 pass — file consolidated to a single passing suite), `projector.spec.js` (4/4: UMAP-01, REAL-01 force-directed, REAL-02 multi-scan, REAL-03 image billboards), `black_slate.spec.js` (6/6), `edit.spec.js` (8/8, including EDIT-03's shared `__mm_rerender` contract)

## Task Commits

Each task was committed atomically:

1. **Task 1: Port IndexedDB texture cache + ordered fetch chain into projector.mjs** - `d09f335` (feat)
2. **Task 2: spawnImageBillboards() + shared-texture sprites + test hooks** - `22ab068` (feat)
3. **Task 3: REAL-03 image e2e — paint, persist, placeholder-never-cached** - `97d5eba` (test)

**Plan metadata:** (this commit, made after this SUMMARY)

## Files Created/Modified
- `backend/static/js/fe/projector.mjs` - Added `_textureCache` Map, `_idbPromise`, `_netFetchCount`, `idbOpen()`, `buildFromBlob()`, `idbLoadTexture()`, `idbSaveBlob()`, `toProxy()`, `loadAndCacheImage()` (Task 1); added `_lastUrlRoots`, `lastCoords()`, `lastRoots()`, `netFetchCount()`, `_imageSprites`/`_chunkImageUrl` Maps, `spawnImageBillboards()`, `_syncImageSpritePositions()` wired into `animate()`, expanded the returned object (Task 2)
- `backend/templates/editor.html` - Added `window.__mm_proj_image` / `window.__mm_proj_net_count` hooks; modified the pre-existing `window.__mm_rerender` to call both `render()` (EDIT-03) and `projector.setNodes(projector.lastCoords(), projector.lastRoots())` (REAL-03), guarded by `if (projector)`
- `frontend_e2e/projector.spec.js` - New `"REAL-03 image billboards: ..."` test block: proxy-route fixture serving a real test PNG, paint assertion, zero-new-fetch-after-rerender assertion, placeholder-never-cached assertion via a direct `window.__mm_proj.loadAndCacheImage` probe call

## Decisions Made
- Images driven via the `__mm_proj_image` test hook only, NOT a new `umap_canonical` frame field — confirmed via grep that production carries no image-URL field today; production wiring is explicitly out of scope per the plan and deferred to the milestone-end real-stack probe.
- Resolved the `window.__mm_rerender` naming collision (plan text implied a fresh binding; EDIT-03 already owned it) by combining both behaviors in one function rather than picking one over the other — verified safe via a full `edit.spec.js` regression run.
- Narrowed Task 2's URL-dedup grouping to exact-string match (a plain `Map` keyed by URL) rather than porting `cp/sprite_manager.js`'s fuzzy Jaccard near-duplicate detection, since the plan's stated acceptance criteria only requires exact-URL sharing.
- Used `cp/sprite_manager.js` (not `cp/animation.js`, the plan's `<read_first>` pointer) as the verbatim source for the sprite-scale/aspect-correction algorithm, after confirming via grep that `animation.js` contains no relevant Sprite/scale logic.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Resolved `window.__mm_rerender` naming collision instead of overwriting an existing test contract**
- **Found during:** Task 2 (test hooks in editor.html)
- **Issue:** The plan's Task 2 action text specifies binding `window.__mm_rerender = () => projector.setNodes(projector.lastCoords(), projector.lastRoots())`, but this global was already bound for EDIT-03 (`() => render()`), with `frontend_e2e/edit.spec.js` asserting on its EDIT-03 behavior. Following the plan's literal text would have silently broken an existing, test-covered contract.
- **Fix:** Combined both behaviors: `window.__mm_rerender = () => { render(); if (projector) projector.setNodes(projector.lastCoords(), projector.lastRoots()); };`
- **Files modified:** backend/templates/editor.html
- **Verification:** `npx playwright test edit.spec.js` — 8/8 green, including the EDIT-03 test that depends on `__mm_rerender`'s render-trigger behavior; `npx playwright test projector.spec.js` — 4/4 green, including the new REAL-03 test that depends on `__mm_rerender`'s no-new-fetch behavior.
- **Committed in:** 22ab068 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug/conflict-resolution)
**Impact on plan:** Necessary to avoid silently breaking existing EDIT-03 e2e coverage. No scope creep — the fix stays within Task 2's own file (editor.html) and was verified against both the old and new test suites.

## Issues Encountered
None beyond the documented deviation above. All `node --test` and Playwright runs passed on first attempt after each set of code changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- REAL-03 (image billboards: IndexedDB cache, ordered fetch chain, shared texture, cache-poisoning guard) is fully implemented and e2e-verified against a real rendered Chromium tab.
- `loadAndCacheImage`/`spawnImageBillboards`/`netFetchCount` are exported on the projector's returned object, available to `06-04` (2D<->3D link arrow) if needed, though REAL-04's arrow itself is expected to only need the existing `project()` accessor.
- Production wiring of a real image-URL field into `umap_canonical` remains an explicit gap, tracked for the milestone-end real-stack acceptance probe (`scripts/probe_live_archive_scan.py`) rather than this plan.
- No blockers.

---
*Phase: WFH-06-served-slate-3d-real-register*
*Completed: 2026-06-23*

## Self-Check: PASSED

- FOUND: backend/static/js/fe/projector.mjs
- FOUND: backend/templates/editor.html
- FOUND: frontend_e2e/projector.spec.js
- FOUND: .planning/phases/WFH-06-served-slate-3d-real-register/06-03-SUMMARY.md
- FOUND commit: d09f335
- FOUND commit: 22ab068
- FOUND commit: 97d5eba
