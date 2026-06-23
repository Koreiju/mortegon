---
phase: WFH-06-served-slate-3d-real-register
fixed_at: 2026-06-23T00:00:00Z
review_path: .planning/phases/WFH-06-served-slate-3d-real-register/06-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 4
skipped: 1
status: partial
---

# Phase WFH-06: Code Review Fix Report

**Fixed at:** 2026-06-23
**Source review:** .planning/phases/WFH-06-served-slate-3d-real-register/06-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (CR-01 + WR-01..04; the 4 INFO findings and WR-05/WR-06 were out of scope)
- Fixed: 4 (CR-01, WR-01, WR-02, WR-04)
- Skipped: 1 (WR-03)

**Final test counts (all green after every commit):**
- Unit: `node --test backend/static/js/fe/projector.test.mjs` → **13/13 passed**
- E2E: `npx playwright test --config=frontend_e2e/playwright.config.js`
  (env `WFH_FAKE_SLM=1 WFH_FAKE_EMBEDDER=1 NO_WEBDRIVER=1`) → **30/30 passed**,
  including `black_slate.spec.js` (no stroke-dasharray) and all 5 REAL projector tests.

All four fix commits are atomic, on `master`, with no `--no-verify`.

## Fixed Issues

### CR-01: Placeholder texture poisons the in-memory cache (guard only protected IndexedDB)

**Files modified:** `backend/static/js/fe/projector.mjs`
**Commit:** 4af065c
**Applied fix:** Propagated the `X-Image-Proxy-Note` decision out of `tryFetch`
as `{ tex, isPlaceholder: !!note }` and gated the in-mem `_textureCache.set`
with `if (tex && !isPlaceholder)`, symmetric with the existing IDB guard. A
transparent-PNG placeholder is now retained in NEITHER cache tier, so a later
`loadAndCacheImage(sameUrl)` re-attempts the real upstream instead of returning
a poisoned `memHit`. This makes `projector.spec.js` REAL-03 step-3
(`placeholderHits` increments on the second load) deterministically meaningful.

### WR-01: `setNodes` leaked a `PointsMaterial` on every layout frame

**Files modified:** `backend/static/js/fe/projector.mjs`
**Commit:** 5e0dffd
**Applied fix:** Added `points.material.dispose()` alongside the existing
`points.geometry.dispose()` when removing the prior points object in
`setNodes`. THREE does not GC GPU programs/uniforms without an explicit
`.dispose()`, and `setNodes` runs per `umap_canonical` WS frame and per
`__mm_rerender`, so the material (and its GPU allocation) previously leaked
every frame over a long session.

### WR-02: No in-flight dedup — concurrent loads double-fetch and double-upload

**Files modified:** `backend/static/js/fe/projector.mjs`
**Commit:** 8e03fe2
**Applied fix:** Added an `_inflight` Map (url → pending Promise). After the
`memHit` short-circuit, `loadAndCacheImage` now returns an existing in-flight
promise for the same url if present; otherwise it starts one (the original body
extracted verbatim into `_loadAndCacheImageInner`), registers it in `_inflight`,
and deletes it in a `finally`. Concurrent callers for the same url now await one
fetch + one GPU upload. Placeholders still bypass `_textureCache` (CR-01), so
they re-attempt on their next call rather than being permanently shared.

### WR-04: Off-frustum hide test missed lateral (x/y) out-of-frustum nodes

**Files modified:** `backend/static/js/fe/projector.mjs`
**Commit:** fdc5059
**Applied fix:** Added `ndcX`/`ndcY` (raw THREE NDC x/y) to `project()`'s return
and extended the `drawConcept3DLinks` hide test from depth-only
(`p.ndcZ < -1 || p.ndcZ > 1`) to all three axes, matching `_isRootInFrustum`'s
symmetric `[-1,1]` check on x/y/z. A node in front of the camera but laterally
off-canvas now hides its arrow instead of drawing to a point beyond the canvas
edge. The solid `#ffd700` / headless / no-dasharray styling is untouched
(black_slate's no-dotted gate stays green).

## Skipped Issues

### WR-03: Defensive ray-root fallback poisons `_urlRootPositions`, suppressing camera framing

**File:** `backend/static/js/fe/projector.mjs:284-296` and `:447-464`
**Reason:** skipped — every correct implementation of the fix makes the
**REAL-04** e2e (`projector.spec.js:367`) red at step (c), and the conflict is
with that test's intended behavior rather than a bug in the fix, so per the hard
gate it was reverted and left un-fixed.

Detail: I implemented the review's recommended approach (a `_realRootUrls` Set
populated only by REAL `url_roots` entries, with `newUrls` keyed off that set
instead of off `_urlRootPositions`, which the `_computeRayData` origin fallback
also writes to). It correctly restored the REAL-02 newness signal and REAL-02
stayed green. But it ALSO legitimately treats the url `""` in REAL-04 as a NEW
root: the boot sequence's 163 real-scan chunks resolve to `""` (production
frames carry no per-chunk `.url`), while boot's `url_roots` is keyed by the real
archive.org URL — so `""` genuinely is "chunks arrived before the root", the
exact WR-03 scenario. With the fix, REAL-04's `setNodes(coords, {"":...})` fires
a legitimate `frameCameraToRoot("")` ~600ms tween toward `[0,0,0]`; REAL-04
step (c) advances only ~30 frames (~0.5 s) before orbiting and then advancing
30 more, during which the still-active tween reverts the orbit, so the arrow
endpoint does not move and the assertion
`"the line endpoint moved after the camera orbited"` fails (verified
empirically: camera z goes 26.36 → -26.36 on orbit → back to +26.36 as the
tween completes).

At baseline the test passes only because the OLD origin-fallback side effect
pre-marked `""` in `_urlRootPositions` during boot, so REAL-04's `setNodes` saw
`""` as already-seen and fired no tween — i.e. the test silently depends on the
very poisoning WR-03 wants to remove. Reconciling WR-03 with REAL-04 would
require also changing REAL-04 (e.g. forcing any in-flight camera tween to
complete or be cancelled before step (c) reads the arrow), which is outside the
scope of a source-only fix and would alter a passing test's intended behavior.
Recommend a follow-up that pairs the `_realRootUrls` fix with a REAL-04 update
that settles/cancels the auto-frame tween before asserting orbit-tracking.

The reverted-fix exploration left no residue: `backend/static/js/fe/projector.mjs`
contains only CR-01, WR-01, WR-02, WR-04.

---

_Fixed: 2026-06-23_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
