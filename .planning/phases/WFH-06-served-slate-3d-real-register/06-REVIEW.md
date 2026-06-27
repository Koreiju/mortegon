---
phase: WFH-06-served-slate-3d-real-register
reviewed: 2026-06-23T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - backend/static/js/fe/projector.mjs
  - backend/static/js/fe/projector.test.mjs
  - backend/templates/editor.html
  - frontend_e2e/projector.spec.js
findings:
  critical: 1
  warning: 6
  info: 4
  total: 11
status: issues_found
---

# Phase WFH-06: Code Review Report

**Reviewed:** 2026-06-23
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase WFH-06 ports the legacy `cp/` 3D Real register into the served `fe/` projector
(`projector.mjs`), with pure ray/collider math, an IndexedDB texture-cache chain, camera
auto-framing, image billboards, and the solid 2D↔3D link arrow. The pure math is clean and
well-tested. The browser-layer THREE wiring, however, has one **correctness BLOCKER in the very
guard the phase context flagged as critical** — the placeholder cache-poisoning protection only
covers IndexedDB, not the in-memory texture Map, which both poisons the in-session cache AND makes
the REAL-03 e2e assertion (step 3) fail against the code as written. Several resource-leak and
edge-case WARNINGs follow (per-frame material leak, in-flight fetch race, ray-root poisoning
suppressing camera framing, off-frustum NDC range overlap).

The backend contract was cross-checked: `backend/api/routes.py::_empty_image_response` emits
`X-Image-Proxy-Note` **only** on the placeholder path (success responses omit it), so the frontend's
`if (!note)` IDB guard is correct *as far as it goes* — the gap is the in-mem cache, not the header
read.

## Critical Issues

### CR-01: Placeholder texture poisons the in-memory cache (guard only protects IndexedDB)

**File:** `backend/static/js/fe/projector.mjs:227-248`

**Issue:** The `X-Image-Proxy-Note` guard is the phase's named anti-poisoning mechanism (Pitfall 3 /
threat T-06-06: "a placeholder is NEVER written to IDB as a successful image"). The guard is applied
**only** to the IndexedDB write (`if (!note) idbSaveBlob(...)`, line 237). But `tryFetch` returns
the placeholder texture unconditionally, and `loadAndCacheImage` then writes it to the in-memory
`_textureCache` Map unconditionally:

```js
const tryFetch = async (url) => {
  ...
  const note = resp.headers.get("X-Image-Proxy-Note");
  const blob = await resp.blob();
  const tex = await buildFromBlob(blob);
  if (!note) idbSaveBlob(originalUrl, blob); // note only gates IDB
  return tex;                                // placeholder tex returned regardless
};
...
if (tex) _textureCache.set(originalUrl, tex); // line 247: in-mem cache poisoned with placeholder
```

Consequence: the transparent-PNG placeholder is cached in memory for the session, so a later
`loadAndCacheImage(sameUrl)` returns the placeholder via the `memHit` short-circuit (line 221-222)
and **never re-attempts** the upstream image once it recovers. This is exactly the poisoning the
guard was meant to prevent — just routed through the Map instead of IDB.

This also breaks the REAL-03 e2e's own step-3 assertion. `projector.spec.js:355-358` calls
`loadAndCacheImage(PLACEHOLDER_URL)` a second time and asserts `placeholderHits` increments
(a re-fetch occurred). With the code as written, the second call hits `memHit` and returns without
any network fetch, so `placeholderHits` does **not** increment and the assertion
`toBeGreaterThan(placeholderHitsAfterFirstLoad)` fails.

**Fix:** Propagate the `note` decision out of `tryFetch` and skip the in-mem cache write for
placeholders too:

```js
const tryFetch = async (url) => {
  _netFetchCount++;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error("http " + resp.status);
  const note = resp.headers.get("X-Image-Proxy-Note");
  const blob = await resp.blob();
  const tex = await buildFromBlob(blob);
  if (!note) idbSaveBlob(originalUrl, blob);
  return { tex, isPlaceholder: !!note };
};

let tex = null, isPlaceholder = false;
try { ({ tex, isPlaceholder } = await tryFetch(toProxy(originalUrl))); }
catch (_proxyErr) {
  try { ({ tex, isPlaceholder } = await tryFetch(originalUrl)); }
  catch (_directErr) { tex = null; }
}
if (tex && !isPlaceholder) _textureCache.set(originalUrl, tex); // never cache the placeholder
return tex;
```

(Note: the returned placeholder `tex` is still painted once so the sprite resolves, but it is not
retained — matching the documented "never cached as success" contract.)

## Warnings

### WR-01: `setNodes` leaks a `PointsMaterial` on every layout frame

**File:** `backend/static/js/fe/projector.mjs:438,443`

**Issue:** On each `setNodes` call the old points object is removed and its geometry disposed, but
its **material is never disposed**:

```js
if (points) { scene.remove(points); points.geometry.dispose(); } // material leaked
...
points = new THREE.Points(geo, new THREE.PointsMaterial({ size: 2.6, vertexColors: true }));
```

`setNodes` runs on every `umap_canonical` WS frame (`editor.html:308`) and on every
`__mm_rerender` (`editor.html:425`), so a `PointsMaterial` (and its GPU program/uniform allocation)
leaks per frame over a long session. THREE materials are not GC-collected for GPU resources without
`.dispose()`.

**Fix:** `if (points) { scene.remove(points); points.geometry.dispose(); points.material.dispose(); }`
— or hoist the material to a single closure-level instance reused across frames.

### WR-02: No in-flight dedup — concurrent loads of the same URL double-fetch and double-upload

**File:** `backend/static/js/fe/projector.mjs:220-248`

**Issue:** `_textureCache` holds only *resolved* textures, never pending promises. `loadAndCacheImage`
awaits (idb load, then fetch) between the `memHit` check (221) and the cache write (247). Two
overlapping calls for the same URL — e.g. two successive `spawnImageBillboards`/`setNodes` frames, or
a `__mm_proj_image` followed quickly by a re-render — both miss `memHit`, both issue real `fetch()`
calls, and both `buildFromBlob` (two GPU texture uploads), defeating the "single GPU upload" intent
documented at lines 488-494. The intra-call `byUrl` grouping only dedups *within one*
`spawnImageBillboards` invocation.

**Fix:** Cache the in-flight promise, not just the resolved texture:

```js
const _inflight = new Map(); // url → Promise<THREE.Texture|null>
async function loadAndCacheImage(originalUrl) {
  const memHit = _textureCache.get(originalUrl);
  if (memHit) return memHit;
  if (_inflight.has(originalUrl)) return _inflight.get(originalUrl);
  const p = (async () => { /* ...existing idb+fetch body... */ })();
  _inflight.set(originalUrl, p);
  try { return await p; } finally { _inflight.delete(originalUrl); }
}
```

### WR-03: Defensive ray-root fallback poisons `_urlRootPositions`, silently suppressing camera framing

**File:** `backend/static/js/fe/projector.mjs:284-296` and `:447-464`

**Issue:** When a chunk's `url` has no entry in `_urlRootPositions` yet, `_computeRayData` *inserts*
an origin placeholder into the map (line 290-291):

```js
let rootVec = _urlRootPositions.get(url);
if (!rootVec) {
  rootVec = new THREE.Vector3(0, 0, 0);
  _urlRootPositions.set(url, rootVec.clone()); // mutates the map as a side effect
}
```

If a later `setNodes` arrives carrying that URL's *real* `url_roots`, the "is this URL new?" check in
`setNodes` keys off the same map:

```js
if (!_urlRootPositions.has(url)) newUrls.push(url); // already has(url) → not "new"
```

Because the origin placeholder already populated the map, `has(url)` is true, the URL is **not**
added to `newUrls`, and the scan-end `frameCameraToRoot(newestUrl)` auto-frame for that URL never
fires (lines 460-464). Positions still end up correct (line 452 overwrites the placeholder), but the
REAL-02 camera-framing requirement is silently skipped for any URL whose chunks landed one frame
ahead of its root — the exact "url_roots momentarily behind coords" case the fallback was written to
survive (line 288-289 comment).

**Fix:** Track *placed* roots separately from *real* roots, e.g. a `_realRootUrls` Set populated only
in `setNodes`, and compute `newUrls` against that set rather than against `_urlRootPositions` (which
the ray fallback also writes to). Or have `_computeRayData` use a transient local origin without
persisting it into `_urlRootPositions`.

### WR-04: Off-frustum hide test misses lateral (x/y) out-of-frustum nodes

**File:** `backend/static/js/fe/projector.mjs:600-607,664-673`

**Issue:** `drawConcept3DLinks` hides the arrow only when `p.ndcZ < -1 || p.ndcZ > 1` (depth range).
It never tests the projected `x`/`y` NDC range. A node that is in front of the camera but far to the
side or above/below the viewport (NDC x or y outside [-1,1]) still passes the hide test, so the arrow
is drawn to a point off the visible canvas — `x2 = rect.left + p.x` can land far outside the canvas
rect. `_isRootInFrustum` (line 356-361) correctly checks all three axes (`v.x`, `v.y`, `v.z` each in
[-1,1]); `drawConcept3DLinks` does not, despite the same intent. The arrow can therefore point at
empty space beyond the canvas edge instead of hiding.

**Fix:** Either clamp the endpoint to the canvas rect, or extend the hide test to the lateral axes
(matching `_isRootInFrustum`): hide when `p.ndcX`/`p.ndcY` (add them to `project()`'s return) fall
outside [-1,1]. If off-canvas-but-on-axis arrows are acceptable by design, document that explicitly —
as written it contradicts the symmetric frustum test the rest of the file uses.

### WR-05: IndexedDB write is fire-and-forget with no `tx.oncomplete`/`onerror` — silent data loss & unhandled rejection risk

**File:** `backend/static/js/fe/projector.mjs:196-204,237`

**Issue:** `idbSaveBlob` issues `store.put(...)` and returns immediately without awaiting
`tx.oncomplete`. It is also called fire-and-forget (`idbSaveBlob(originalUrl, blob)` at line 237,
return value discarded). Two problems: (1) if the transaction aborts (quota exceeded, blocked
upgrade), the failure is swallowed silently and the texture is silently never cached cross-session —
the "cross-session cache carries over" guarantee (lines 133-136) is best-effort with no observability;
(2) an aborted/errored IDB transaction that is not handled can surface as an unhandled
`error`/`abort` event. The `try/catch` only catches the *synchronous* `transaction()` call, not the
async transaction lifecycle.

**Fix:** Resolve on `tx.oncomplete`, attach `tx.onerror`/`tx.onabort` handlers, and (optionally) make
`idbSaveBlob` awaitable so failures are at least loggable:

```js
return new Promise((resolve) => {
  const tx = db.transaction("textures", "readwrite");
  tx.oncomplete = () => resolve(true);
  tx.onerror = tx.onabort = () => resolve(false);
  tx.objectStore("textures").put({ url, blob, ts: Date.now() });
});
```

### WR-06: `drawConcept3DLinks` writes unitless coordinate attributes; sub-pixel float strings each frame

**File:** `backend/static/js/fe/projector.mjs:643-646`

**Issue:** `line.setAttribute("x1", x1)` etc. pass raw floats (e.g. `412.7390843`). SVG accepts these,
but: (a) the values are full-precision floats stringified every frame (60fps) producing long DOM
attribute churn; more importantly (b) `x1`/`y1` are computed from `getBoundingClientRect()` of the
card and `rect.left + p.x` for the canvas — these are **viewport** coordinates, while `#link-layer` is
`position: fixed; inset: 0` (`editor.html:17`), so the SVG user-space origin is the viewport top-left.
That happens to align here, but it is an unstated coupling: if `#link-layer` were ever given a
transform, padding, or non-zero offset, every arrow would be mis-placed with no guard. There is no
`viewBox`/coordinate-system assertion tying the SVG space to viewport px.

**Fix:** Round to integers/one-decimal when writing (`x1.toFixed(1)`), and add a brief invariant
comment (or a `viewBox="0 0 innerWidth innerHeight"` set on resize) documenting that `#link-layer`
user-space must equal viewport px. Low risk today; brittle to future layout changes.

## Info

### IN-01: `ResizeObserver` is created but never disconnected; `resize` window listener never removed

**File:** `backend/static/js/fe/projector.mjs:710,716-719,725`

**Issue:** `createProjector` registers `window.addEventListener("resize", resize)` and a
`ResizeObserver` on the canvas, but the returned `stop()` only `cancelAnimationFrame(raf)` — it does
not `removeEventListener` or `ro.disconnect()`. For the single long-lived projector in `editor.html`
this never matters, but `stop()` reads as a teardown and is incomplete; a future multi-projector or
hot-reload caller would leak listeners/observers. Consider disconnecting both in `stop()`.

### IN-02: Per-frame `new THREE.Vector3` allocations in `project()` and the force step

**File:** `backend/static/js/fe/projector.mjs:334,671`

**Issue:** `project()` allocates a fresh `THREE.Vector3` per call, and `drawConcept3DLinks` calls it
once per pinned card per frame; `_stepForceDirected` allocates `rootPos.clone()` +
`rayDir.clone().multiplyScalar(...)` per moved node per frame. (Performance is out of v1 scope, noted
only as a GC-pressure smell for the 60fps animate loop — a reusable scratch vector would remove it.)
Not a correctness issue.

### IN-03: `_computeRayData` reads `_coords[id].url` assuming array-with-property shape

**File:** `backend/static/js/fe/projector.mjs:284`

**Issue:** `const url = (_coords[id] && _coords[id].url) || ""` relies on each coord being an array
that *also* carries a `.url` expando (set by the test fixtures at `projector.spec.js:150,186` via
`a.url = url`). The production `umap_canonical` frame (`backend/api/ws_frames.py`) ships plain
`[x,y,z,h,s,v]` arrays with **no** `.url` field, so every production chunk resolves to the shared `""`
root key and the multi-URL ray separation only exists under the test hook. This matches the
documented "image URLs are NOT carried by the production frame today" caveat (lines 498-501) but means
REAL-02's per-URL placement is, in production, single-root until the backend adds a per-chunk url
field. Worth an explicit TODO/contract note so it isn't mistaken for a live multi-URL path.

### IN-04: `azimuth()` recolor throttle can desync after a non-orbiting camera move

**File:** `backend/static/js/fe/projector.mjs:404,696-698`

**Issue:** `recolor()` is gated on azimuth delta > 0.05 (line 698). The camera-frame tween
(`_stepCameraTween`, line 404) moves `camera.position` along an arbitrary vector; if a tween changes
position without changing `atan2(x, z)` by > 0.05 (e.g. a mostly-radial dolly), the HSV field is not
refreshed even though the view changed. Cosmetic only (hue lags one threshold step), but the throttle
assumes azimuth is the sole color-relevant camera parameter.

---

_Reviewed: 2026-06-23_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
