# Phase 6: 3D Real Register in the Served Slate — Pattern Map

**Mapped:** 2026-06-22
**Files analyzed:** 4 (1 modify, 1 likely-modify, 2 modify-test)
**Analogs found:** 4 / 4

This is a brownfield PORT. RESEARCH.md (06-RESEARCH.md) already did the heavy
algorithm-extraction work; this file re-verifies the exact analog files/line
numbers directly against the source tree and packages the excerpts the
planner needs, file-by-file, with the two locked discrepancy resolutions
(A1 `COLLIDER_SAFETY=1.4`, A2 `SAFETY_GAP` deferred to backend) restated
at point of use so no plan can silently drift from them.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/static/js/fe/projector.mjs` | component (3D render closure-factory) | event-driven (WS frame → render) + transform (coords→geometry) | `backend/static/js/cp/force_layout.js` + `cp/sprite_manager.js` + `cp/animation.js` | role-match (legacy is class+mixin; fe/ is closure-factory — algorithm ports verbatim, shape doesn't) |
| `backend/static/js/fe/magic_markdown_panel.mjs` (REAL-04 attribute authorship) OR new SVG host in `backend/templates/editor.html` | component / template | request-response (DOM attr set at pin-time) + event-driven (per-frame redraw) | `backend/static/js/cp/concept_graph.js::_drawConcept3DLinks` (draw loop) + `cp/billboard.js` (`data-3d-node-id` convention, attribute-setting site) | role-match — `magic_markdown_panel.mjs` does NOT yet set `data-3d-node-id` (confirmed by grep, 0 matches); this is new authorship, not extension |
| `backend/static/js/fe/projector.test.mjs` | test (pure-function unit) | transform (pure math in/out) | itself (existing `buildPointArrays` test block) | exact — same file, same pattern, just add more `test(...)` blocks |
| `frontend_e2e/projector.spec.js` | test (Playwright e2e) | request-response (page load → DOM/canvas assertion) | itself (existing UMAP-01 test) + `frontend_e2e/black_slate.spec.js` (no-dotted regression pattern) + `frontend_e2e/halo.spec.js` (skip-if-WebGL-unavailable pattern) | exact — same file, same skip-gate idiom, add more `test(...)` blocks |
| `backend/templates/editor.html` | config/wiring (WS handler + boot fetch) | event-driven (WS message dispatch) | itself, line ~296 WS handler + `bootProjector()` | exact — confirmed gap: `f.url_roots` exists on the frame object today but is never read |

**Confirmed file count vs. CONTEXT/RESEARCH:** matches the four files named in
the phase brief exactly (`projector.mjs` MODIFY, link-arrow layer
CREATE/extend, `projector.test.mjs` MODIFY, `projector.spec.js` MODIFY) plus
one router-level wiring touch in `editor.html` that both research and this
pass independently confirm is required (the WS handler drops `url_roots`
today) and one open authorship decision for `data-3d-node-id` (see below).

---

## Pattern Assignments

### `backend/static/js/fe/projector.mjs` (component, event-driven + transform)

**Current state (full file read, 136 lines):** closure factory
`createProjector(canvas, opts)` returning `{ scene, camera, renderer,
setNodes, nodeCount, nodeColor, recolor, project, azimuth, onFrame, resize,
stop }`. `setNodes(coords)` takes ONLY `coords` — `url_roots` is not a
parameter today. `animate()` runs `requestAnimationFrame`, calls
`controls.update()`, throttled `recolor()`, then user `_frameCbs`, then
`renderer.render()`. This is the exact slot REAL-01's `stepForceDirected`
and REAL-04's `drawConcept3DLinks` hook into (either as a registered
`onFrame` callback or inlined directly in `animate()`).

**Analog 1 — REAL-01 ray/collider step:** `backend/static/js/cp/force_layout.js`

Imports/shape pattern (lines 1-38) — class+mixin shape; PORT THE ALGORITHM
ONLY, not the `ForceLayoutMixin`/`this.*` shape (fe/ has no class):
```javascript
// Source: cp/force_layout.js lines 25-38 — DO NOT port this shape
export const ForceLayoutMixin = {
    _initForceLayout() {
        this._urlRootPositions = new Map();   // url → THREE.Vector3
        this._urlBoundingRadii = new Map();   // url → number
        this._umapLayoutActive = false;
        this._nodeRayData = new Map();
    },
    ...
```
Port target shape — closure-local `Map`s instead of `this.*`, matching
`projector.mjs`'s existing `_coords`/`_lastColorAz` closure-var convention
(lines 80-81 of `projector.mjs`).

Ray derivation (lines 106-145, `_computeRayData`) — port near-verbatim,
including the defensive root-not-yet-placed fallback (lines 117-126):
```javascript
// Source: cp/force_layout.js lines 128-144
const nodePos = init.position.clone();
const ray = nodePos.clone().sub(rootPos);
const rayLen = ray.length();
if (rayLen < 0.001) {
    ray.set(1, 0, 0);              // degenerate: node sits on root
} else {
    ray.normalize();
}
this._nodeRayData.set(nodeId, { rayDir: ray, radius: rayLen, rootPos: rootPos.clone() });
```

Collider step (lines 155-200+, `_stepForceDirected`) — **the load-bearing
constants, verbatim from line 160-162**:
```javascript
// Source: cp/force_layout.js lines 160-162 — LOCKED VALUES (UI-SPEC A1)
const NODE_RADIUS = 0.9;
const SAFETY = 1.4;                              // NOT 2.0 — ship value, not doc value
const MIN_SEPARATION = 2 * NODE_RADIUS * SAFETY; // = 2.52
```
Pairwise repulsion projected onto each node's OWN ray (lines 178-200):
```javascript
// Source: cp/force_layout.js lines 178-200
for (let a = 0; a < nodes.length; a++) {
    for (let b = a + 1; b < nodes.length; b++) {
        const na = nodes[a], nb = nodes[b];
        const dist = /* 3D distance */;
        if (dist >= MIN_SEPARATION) continue;
        if (dist < 0.001) continue;
        const pushTotal = (MIN_SEPARATION - dist) * 0.5;
        const dotA = -(ux * na.rayData.rayDir.x + uy * na.rayData.rayDir.y + uz * na.rayData.rayDir.z);
        const dotB =  (ux * nb.rayData.rayDir.x + uy * nb.rayData.rayDir.y + uz * nb.rayData.rayDir.z);
        // accumulate into radialForces.get(id), then apply with DAMPING=0.3,
        // clamp radius to >= 0.5, reposition along rootPos + rayDir*radius
    }
}
```
**Error/edge handling:** early-return guard `if (!_umapLayoutActive ||
_nodeRayData.size === 0) return;` (line 156-157) and `if (nodes.length < 2)
return;` (line 172) — port both guards verbatim; they are the difference
between "no-op until first real layout frame" and a crash on an empty Map.

### `backend/static/js/fe/projector.mjs` (REAL-02 — consume, never recompute)

**Analog:** `cp/force_layout.js::_computeUrlRootPosition` (lines 45-99) is
explicitly NOT a port target (Anti-Pattern, RESEARCH.md). The frontend's job
is `setNodes(coords, urlRoots)` bookkeeping only.

**A2 resolution restated:** the legacy constant `SAFETY_GAP = 5.0` (line 63)
must NOT be ported into `fe/projector.mjs` at all — zero client-side
`SAFETY_GAP` constant. The backend's `DEFAULT_SAFETY_GAP = 12.0`
(`layout_service.py`) is the sole authority; `fe/` only ever reads the
already-resolved `root_position`/`bounding_radius` per URL key inside
`umap_canonical.url_roots`. Do not write a `SAFETY_GAP` constant of any
value into the ported file.

**Wire contract to consume:** `backend/api/ws_frames.py::build_umap_canonical`
emits `{ coords, url_roots: { url: { root_position:[x,y,z], bounding_radius:r } }, removed_ids, provenance }`.

**Camera framing analog:** `cp/animation.js` lines 753-798 (adaptive bounds,
not re-read this pass — RESEARCH.md already extracted the exact multipliers
and confirmed them against UI-SPEC, which is the authoritative numeric
source — `minDistance = 0.6 × cluster_radius`, `maxDistance = 3.0 ×
max(|pos|)`). Port these two formulas verbatim; do not re-derive.

### `backend/static/js/fe/projector.mjs` (REAL-03 — image billboards)

**Analog:** `backend/static/js/cp/sprite_manager.js` (full file, 498 lines)

IndexedDB schema — port the EXACT DB/store name so existing users' cached
images carry over (lines 313-330):
```javascript
// Source: cp/sprite_manager.js lines 317-322
const req = indexedDB.open('wfh_texture_cache', 1);
req.onupgradeneeded = (ev) => {
    const db = ev.target.result;
    if (!db.objectStoreNames.contains('textures')) {
        db.createObjectStore('textures', { keyPath: 'url' });
    }
};
```

Single-fetch chain — port verbatim, including the load-bearing
`X-Image-Proxy-Note` cache-poisoning guard (lines 398-434):
```javascript
// Source: cp/sprite_manager.js lines 398-434 — _loadAndCacheImage
async _loadAndCacheImage(originalUrl) {
    const cachedTex = await this._idbLoadTexture(originalUrl).catch(() => null);
    if (cachedTex) return cachedTex;
    const toProxy = (absUrl) => { /* same-origin passthrough else /api/image_proxy?url=... */ };
    const buildFromBlob = (blob) => new Promise((resolve, reject) => {
        const objUrl = URL.createObjectURL(blob);
        const loader = new THREE.TextureLoader();
        loader.load(objUrl, (tex) => { URL.revokeObjectURL(objUrl); resolve(tex); },
            undefined, (err) => { URL.revokeObjectURL(objUrl); reject(err); });
    });
    const tryFetch = async (url) => {
        const resp = await fetch(url);
        if (!resp.ok) throw new Error('http ' + resp.status);
        const note = resp.headers.get('X-Image-Proxy-Note');   // <-- read BEFORE caching decision
        const blob = await resp.blob();
        const tex  = await buildFromBlob(blob);
        if (!note) this._idbSaveBlob(originalUrl, blob);       // never cache the placeholder as success
        return tex;
    };
    try { return await tryFetch(toProxy(originalUrl)); }
    catch (_proxyErr) { /* fall through to direct fetch, then give up */ }
}
```
**Error handling pattern:** every IDB operation wraps in `try { ... } catch
(_) { resolve(null); }` — IDB failures degrade silently to "use network",
never throw. Texture decode failures (`loader.load`'s error callback) reject
the promise, which the `tryFetch` chain catches and falls through to the
next fetch strategy.

**Billboard scale constants (UI-SPEC, locked, not re-derived):** base size
`1.0` primary / `0.55` secondary, aspect-corrected via
`sprite.scale.set(baseSize*aspect, baseSize, 1)` (if `aspect>=1`, else
transpose) — `cp/sprite_manager.js`/`cp/animation.js` line 105 region.

### REAL-04 — 2D↔3D link arrow (NEW authorship, not extension)

**Open question resolved by this pass:** grepped `magic_markdown_panel.mjs`
for `data-3d-node-id` → **0 matches**. CONTEXT.md's "existing convention"
language refers to the LEGACY `cp/` convention only (`cp/billboard.js`,
`cp/concept_graph.js`). The served `fe/` surface has never set this
attribute. Planner must treat attribute-authorship (at pin-time, inside
whichever module owns pin logic — likely `magic_markdown_panel.mjs`) as an
explicit REAL-04 subtask, not an assumed precondition.

**Analog — draw loop:** `backend/static/js/cp/concept_graph.js::_drawConcept3DLinks`
(lines 5479-5578+, read directly this pass):
```javascript
// Source: cp/concept_graph.js lines 5507-5544
const cards = document.querySelectorAll('.concept-card[data-3d-node-id]');
if (!cards.length) {
    const stale = group.querySelectorAll('line');
    stale.forEach(el => el.parentNode.removeChild(el));
    return;
}
cards.forEach(card => {
    const nodeId = card.dataset['3dNodeId'] || card.getAttribute('data-3d-node-id');
    const worldPos = this._getNodePosition(nodeId);
    if (!worldPos) return;
    const projected = worldPos.clone().project(this.camera);
    const canvas = this.renderer && this.renderer.domElement;
    const rect = canvas.getBoundingClientRect();        // <-- canvas-relative, NOT window.innerWidth (Pitfall 4)
    if (projected.z < -1 || projected.z > 1) {           // off-frustum
        const existing = card.__concept3dLine;
        if (existing) existing.setAttribute('visibility', 'hidden');
        return;
    }
    const x2 = rect.left + (projected.x *  0.5 + 0.5) * rect.width;
    const y2 = rect.top  + (-projected.y * 0.5 + 0.5) * rect.height;
    // nearest-edge anchor math (lines 5546-5566) — clip against card rect toward (x2,y2)
});
```
**Line styling — solid, headless (lines 5571-5576):**
```javascript
// Source: cp/concept_graph.js lines 5571-5576
line.setAttribute('stroke', '#eef0f2');     // REAL-04/UI-SPEC: use '#ffd700' (--accent-arrow) instead
line.setAttribute('stroke-width', '2');
line.setAttribute('stroke-opacity', '0.85');
// Solid — no dasharray.
line.removeAttribute('marker-end');         // headless connector (no arrowheads)
```
**Note:** legacy uses `#eef0f2` (silver) + arrowhead marker on OTHER concept
edges in the same file (lines 2713/2805 show `stroke-dasharray` used
elsewhere for different edge kinds — those are NOT this pattern, do not
copy them). REAL-04's color is locked by UI-SPEC to `--accent-arrow
#ffd700`, headless (no marker-end), and this is the ONLY place in the whole
app permitted to render that hue.

**Host element gap:** `editor.html` has no SVG overlay host today (the
legacy reference uses `#concept-edges` which doesn't exist in `editor.html`).
RESEARCH.md's Code Examples section gives the exact new-element pattern
(append `<svg id="link-layer">` following the existing `haloHost` div-append
convention, `z-index:1` between `#projector` (`z-index:0`) and `#grid`
(`z-index:2`)).

### `backend/static/js/fe/projector.test.mjs` (test, transform)

**Analog:** itself — existing `buildPointArrays` test block (lines 1-68,
full file read). Pattern: plain `assert` + hand-rolled `test(name, fn)`
runner with pass/fail counters, no test framework. Extend by exporting new
pure functions from `projector.mjs` (e.g. `computeRayDir`) and adding
`test("...", () => { ... })` blocks in the same file, same style:
```javascript
// Source: projector.test.mjs lines 8-12 (the runner) — reuse verbatim
function test(name, fn) {
  try { fn(); console.log("  PASS  " + name); passed++; }
  catch (e) { console.log("  FAIL  " + name + ": " + e.message); failed++; }
}
```
RESEARCH.md's suggested pure export shape for the ray math:
```javascript
export function computeRayDir(rootPos, umapPos) {
  const ray = [umapPos[0]-rootPos[0], umapPos[1]-rootPos[1], umapPos[2]-rootPos[2]];
  const len = Math.hypot(...ray);
  if (len < 0.001) return { dir: [1,0,0], radius: 0 };
  return { dir: ray.map(v => v/len), radius: len };
}
```
Mirror the existing `near()` approx-equal helper (line 31) for any
float-precision assertions on collider math.

### `frontend_e2e/projector.spec.js` (test, request-response)

**Analog:** itself — existing UMAP-01 test (full file, 32 lines). Pattern:
`page.goto("/")` → `waitForFunction(window.__mm_ready)` → conditional
`test.skip(!booted, "...")` if THREE/WebGL didn't boot → `page.evaluate()`
to drive the projector via `window.__mm_proj_*` test hooks → assert on
returned values:
```javascript
// Source: frontend_e2e/projector.spec.js lines 9-16 — the skip-gate idiom, reuse for ALL new blocks
const booted = await page
  .waitForFunction(() => typeof window.__mm_proj_set === "function", { timeout: 9000 })
  .then(() => true)
  .catch(() => false);
test.skip(!booted, "projector requires THREE.js + WebGL (offline CDN / headless GL unavailable)");
```
New test hooks will be needed on `window` for REAL-01..04 (e.g.
`window.__mm_proj_set_with_roots`, `window.__mm_proj_node_positions`,
`window.__mm_proj_image_loaded`, arrow-line query via plain DOM
`page.locator('#link-layer line')`) — follow the existing `__mm_proj_*`
naming convention already used by `__mm_proj_set` / `__mm_proj_color` /
`__mm_proj_orbit`.

**Secondary analog — no-dotted regression gate:** `frontend_e2e/black_slate.spec.js`
(lines 1-60, targeted read in RESEARCH.md pass) — already asserts no
`stroke-dasharray` project-wide via DOM inspection; REAL-04's arrow must not
break this. Pattern: query all SVG `line`/`path` elements and assert
`getComputedStyle(el).strokeDasharray === 'none'` (or attribute absent).

---

## Shared Patterns

### Backend computes, frontend renders (D10) — applies to ALL four files
**Source:** `backend/services/layout_service.py::_per_url_postprocess` /
`_allocate_new_root`; `backend/api/ws_frames.py::build_umap_canonical`
**Apply to:** `projector.mjs` REAL-01/02 — never recompute `root_position`,
`bounding_radius`, or UMAP coordinates client-side. The frontend's force
step (`_stepForceDirected`) is the ONE permitted client-side animation
math — it operates on the backend's UMAP-fit seed, never re-derives it.

### IndexedDB cross-session cache convention — REAL-03
**Source:** `cp/sprite_manager.js` lines 313-330 (`wfh_texture_cache`/`textures`)
**Apply to:** `projector.mjs` image billboard loader — reuse the EXACT
DB/store name so a returning user's cache transfers to the new `fe/` surface
with zero migration.

### Canvas-relative screen projection — REAL-04 (and reusable for REAL-02 camera math)
**Source:** `cp/concept_graph.js` line 5534 (`canvas.getBoundingClientRect()`)
and `projector.mjs`'s own existing `project(x,y,z)` helper (lines 110-113)
**Apply to:** the link-arrow drawer must call the SAME `project()` function
`projector.mjs` already exports for the halo's ray-transport (§V.4) — do not
write a parallel NDC→px conversion. Convert NDC→CSS px against the canvas's
`getBoundingClientRect()`, never `window.innerWidth/innerHeight` (Pitfall 4).

### Solid/headless line styling — REAL-04, hard project-wide rule
**Source:** `cp/concept_graph.js` lines 5571-5576; `CLAUDE.md` Forbidden Concepts
**Apply to:** any new `<line>` in the link-layer SVG — `stroke="#ffd700"`,
`stroke-width="2"`, no `stroke-dasharray`, `removeAttribute('marker-end')`.
Verified by `black_slate.spec.js`'s existing no-dotted DOM assertion, which
must stay green.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `#link-layer` SVG host element in `backend/templates/editor.html` | template/config | n/a (static markup) | No existing SVG overlay host in `editor.html` today; nearest precedent is the `haloHost` div-append pattern (JS-created, not template-authored) — RESEARCH.md's Code Examples section supplies the exact markup, this is a "port the convention, not a file" case |
| `data-3d-node-id` attribute-setting call site | wiring (pin-time side effect) | event-driven | Confirmed absent from `magic_markdown_panel.mjs` by direct grep (0 matches) — this is genuinely new code, the legacy `cp/billboard.js` line ~863 attribute-set is the only reference, and it sets the attribute inside a different (class-based) pin-card constructor that doesn't map 1:1 onto `fe/`'s pin logic shape |

## Metadata

**Analog search scope:** `backend/static/js/cp/` (force_layout.js, sprite_manager.js,
animation.js, concept_graph.js, billboard.js), `backend/static/js/fe/`
(projector.mjs, projector.test.mjs, magic_markdown_panel.mjs), `frontend_e2e/`
(projector.spec.js, black_slate.spec.js, halo.spec.js), `backend/templates/editor.html`,
`backend/api/ws_frames.py`, `backend/services/layout_service.py`.
**Files scanned:** 12 read/grepped directly this pass (cross-checked against
RESEARCH.md's 20-source list); line numbers re-verified against live source,
not copied blind from RESEARCH.md.
**Pattern extraction date:** 2026-06-22
**Locked discrepancy resolutions carried forward (do not re-litigate):**
- A1: `COLLIDER_SAFETY = 1.4` (shipped value, `force_layout.js` line 161) — NOT the doc's `≥2.0`.
- A2: zero client-side `SAFETY_GAP` constant — defer entirely to backend `url_roots.bounding_radius`; do not port the legacy `5.0` or the backend's `12.0` into `fe/`.
