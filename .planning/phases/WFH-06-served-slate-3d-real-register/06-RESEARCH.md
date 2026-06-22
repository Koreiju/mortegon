# Phase 6: 3D Real Register in the Served Slate — Research

**Researched:** 2026-06-22
**Domain:** THREE.js force-directed layout port (vanilla ES module, no build step) + WS-driven backend layout consumption
**Confidence:** HIGH (this is a brownfield port — every algorithm is read directly from the existing `cp/` source and the existing `layout_service.py`; the only LOW-confidence items are the two backend/frontend algorithm discrepancies flagged below)

## Summary

This phase ports four `cp/` legacy THREE.js features into `fe/projector.mjs`: force-directed ray convergence, per-URL multi-scan placement + camera framing, image billboards with texture caching, and solid 2D↔3D link arrows. The backend (`layout_service.py`) already computes and broadcasts everything the *placement* requirements (REAL-02) need — `url_roots` with `root_position` + `bounding_radius` ride inside the `umap_canonical` WS frame and the `/api/recompute_umap` REST response. **The entire gap is frontend rendering** — `fe/projector.mjs` currently only consumes `coords` (position + HSV) and ignores `url_roots` entirely.

Two load-bearing discrepancies were found between the *legacy frontend's* algorithm and the *current backend's* algorithm for the same responsibility (per-URL placement), both of which the planner must explicitly resolve rather than silently picking one:

1. **Backend `SAFETY_GAP` is `12.0`** (`layout_service.py::DEFAULT_SAFETY_GAP`), not the `5.0` the legacy `cp/force_layout.js` line 63 used and not the UI-SPEC's reference framing. The backend has already diverged from the legacy reference ("doubled from 6.0 for clearer URL separation"). Since REAL-02 says "lands non-overlapping at `existing_max + new_radius + safety_gap`" without pinning a numeric value, and the backend OWNS this placement math (backend computes, frontend renders — D10), **the frontend must defer to whatever `bounding_radius`/`root_position` the backend emits**, not recompute its own placement with the legacy `5.0` constant. The frontend's job for REAL-02 is to *consume* `url_roots`, never to re-derive root positions itself.
2. **Backend root-candidate search uses 9 axis-aligned/diagonal directions** (`_allocate_new_root`), not the legacy's 12-point golden-angle Fibonacci-sphere sampling (`_computeUrlRootPosition`). This is backend-internal and invisible to the frontend (the frontend only ever receives the resolved `root_position`), so it does **not** violate the "no Fibonacci final position" rule — chunk positions are still UMAP-fit, never Fibonacci-placed. No frontend action needed; documented so the planner doesn't try to port `_computeUrlRootPosition`'s candidate search into `fe/` (it would be dead code — the backend already resolved the root before the frame ships).

REAL-01's collider/ray-convergence algorithm, by contrast, has **no backend equivalent at all** — `_stepForceDirected`'s per-frame ray-constrained repulsion is pure client-side animation math operating on the backend's UMAP-fit initial positions. This (and REAL-03/REAL-04, which are 100% client-rendering features) port near-verbatim from `cp/force_layout.js` / `cp/sprite_manager.js` / `concept_graph.js::_drawConcept3DLinks` into `fe/projector.mjs`, adjusted for the served idiom's `window.THREE` global + ESM export shape (no mixin-prototype pattern needed — `fe/projector.mjs` is a closure-based factory, not a class).

**Primary recommendation:** Port `_stepForceDirected`/`_computeRayData` (REAL-01) and `_drawConcept3DLinks` (REAL-04) near-verbatim as closure-internal functions inside `createProjector()`; consume (don't recompute) `url_roots` from `umap_canonical` for REAL-02; port the single-fetch image loader chain from `sprite_manager.js` (REAL-03) keeping the exact in-mem → IDB → proxy → direct order and the `X-Image-Proxy-Note` no-cache-on-fallback rule.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| UMAP 6D fit (position + HSV) | API/Backend | — | `layout_service.py::_project`; backend computes, frontend renders (D10) |
| Per-URL root_position + bounding_radius | API/Backend | — | `layout_service.py::_per_url_postprocess` / `_allocate_new_root`; already shipped in `umap_canonical.url_roots` |
| Force-directed ray convergence (REAL-01) | Browser/Client | — | Pure per-frame animation state (collider repulsion along a ray); no backend persistence, recomputed every reload from the UMAP seed |
| Camera framing/tween (REAL-02) | Browser/Client | — | OrbitControls + THREE.Camera state; inherently a render-loop concern |
| Image billboard fetch/cache (REAL-03) | Browser/Client | CDN/Static (`/api/image_proxy`) | Texture decode + IndexedDB persistence is client-only; the proxy route (already built) is the CORS-bypass tier |
| 2D↔3D link arrow (REAL-04) | Browser/Client | — | Pure derived render state from `pinned_billboards` + per-frame `project()`; "drives nothing" per UI-SPEC |
| `data-3d-node-id` attribute authorship | Frontend Server (template render) | Browser/Client (DOM attr already set by `magic_markdown_panel.mjs`/pin logic) | Set once at panel-mount time; read every frame by the arrow drawer |

## Package Legitimacy Audit

Not applicable — this phase introduces **zero new npm/registry dependencies**. THREE.js (r128, CDN `<script>` global) and OrbitControls (r0.128.0, CDN `<script>` global) are already wired into `editor.html` (and `index.html`) identically; no version change, no new package. `package.json` deps (`@milkdown/*`, `@playwright/test`, `esbuild`) are unrelated to this phase's surface. `[VERIFIED: codebase]` — confirmed via direct read of `backend/templates/editor.html` lines 39-40 and `backend/templates/index.html` lines 418-419: both load `https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js` + `https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js`.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| THREE.js | r128 (pinned, CDN global `window.THREE`) | 3D scene, camera, sprites, points/lines geometry | Already the locked version for both `cp/` and `fe/` surfaces — no migration risk; matching version eliminates API-shape mismatches between the legacy reference and the port target `[VERIFIED: codebase — editor.html L39-40, index.html L418-419]` |
| THREE.OrbitControls (examples/js, r0.128.0) | r0.128.0 | Camera orbit/zoom/pan, `getAzimuthalAngle()` | Same CDN bundle already loaded by `editor.html`; `fe/projector.mjs` already instantiates it conditionally (`if (THREE.OrbitControls)`) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `indexedDB` (browser native) | n/a | Cross-session texture blob cache | REAL-03 — exact same `wfh_texture_cache` DB/`textures` store the legacy code already uses; reuse the same DB name so a user's already-cached images carry over |
| `THREE.TextureLoader` | bundled with THREE r128 | Decode blob → GPU texture | REAL-03 single-fetch path |
| `THREE.Sprite` / `THREE.SpriteMaterial` | bundled with THREE r128 | Billboards (always face camera) | REAL-03 — legacy uses `Sprite`, not a manual quad; port the same primitive (UI-SPEC's "Sprite scale before aspect correction" language matches `Sprite.scale.set`) |
| SVG `<line>` (native DOM, not THREE) | n/a | 2D↔3D link arrow | REAL-04 — the legacy arrow is an SVG overlay (`concept-edges` SVG group), not a THREE.Line; the served `fe/` surface must add an equivalent SVG (or canvas) overlay layer since `editor.html` currently has no SVG host element for this |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `THREE.Sprite` billboards | `THREE.Points` with a custom shader/texture atlas | Atlas approach is faster at scale (1000s of images) but throws away per-image aspect-ratio correction and the existing legacy code path; not worth the rewrite for this port-scoped phase |
| SVG line overlay for the arrow | A `THREE.Line` drawn in the same WebGL scene, projected to a screen-space plane | The legacy reference and the existing `magic_markdown.mjs` halo-ray scaffolding both use SVG/DOM overlays for screen-space lines (consistency with `haloVDom`'s SVG approach in the same file); SVG is also what `black_slate.spec`'s no-dotted assertion already checks against (`stroke-dasharray` is an SVG/CSS attribute) |

**Installation:** None — no new packages. THREE r128 + OrbitControls r0.128.0 are already CDN-loaded by `editor.html`.

**Version verification:** `[VERIFIED: codebase]` — both `editor.html` and `index.html` load identical CDN URLs (`three.js/r128/three.min.js`, `three@0.128.0/examples/js/controls/OrbitControls.js`); confirmed via direct grep, no `npm view` applicable (CDN script tags, not npm packages).

## Architecture Patterns

### System Architecture Diagram

```
Selenium scan / scan-end
        │
        ▼
backend/services/layout_service.py
  ._project()  ──► 6D vector per chunk [x,y,z,h,s,v]  (UMAP fit, HSV norm'd [0,1])
  ._per_url_postprocess() ──► translates chunk coords so each URL's centroid
                              sits at its root_position; computes bounding_radius
                              (NEW url → _allocate_new_root: candidate search,
                               EXISTING url → root_position is REUSED, never moved)
        │
        ▼
backend/api/ws_frames.py::build_umap_canonical()
  { coords: {chunk_id: [x,y,z,h,s,v], ...},
    url_roots: {url: {root_position:[x,y,z], bounding_radius:r}, ...},
    removed_ids: [...], provenance: {...} }
        │
        ├──────────────► WS broadcast (scan-end, every connected client)
        └──────────────► REST response (/api/recompute_umap, manual trigger)
        │
        ▼
backend/templates/editor.html  (WS onmessage / bootProjector fetch)
  if (f.type === "umap_canonical") projector.setNodes(f.coords)   ◄── GAP: url_roots dropped here today
        │
        ▼
backend/static/js/fe/projector.mjs::createProjector()
  setNodes(coords)                — THIS PHASE extends to also accept url_roots
        │
        ├─► buildPointArrays()         — pure: coords → typed position/color arrays  [EXISTS]
        ├─► _initForceLayout()         — NEW: per-URL root/radius bookkeeping, ray data map
        ├─► _computeRayData()          — NEW: ray = (umapPos - rootPos), normalized
        ├─► _stepForceDirected(dt)     — NEW: per-frame collider repulsion projected onto each node's own ray
        ├─► _spawnImageBillboards()    — NEW: in-mem → IDB → proxy → direct fetch chain → THREE.Sprite
        ├─► _frameCameraToRoot(url)    — NEW: tween camera to newest URL's root_position (REAL-02 scan-end hook)
        └─► (per animate-loop frame)
              ├─ recolor()              — EXISTS (azimuth-driven HSV rotation)
              ├─ _stepForceDirected()   — NEW, runs every frame once active
              └─ _drawConcept3DLinks()  — NEW: for every DOM node with [data-3d-node-id],
                                           project(world pos) → screen; draw/hide an SVG <line>
        │
        ▼
DOM: pinned panels (magic_markdown_panel.mjs sets data-3d-node-id) ◄── arrow tracks these
SVG overlay (NEW host element needed in editor.html, e.g. #link-layer svg)
```

### Recommended Project Structure

No new files — extend the existing module in place (it is small, 136 lines, and the legacy reference is already organized as cohesive mixins matching these exact responsibilities):

```
backend/static/js/fe/
├── projector.mjs            # extend: add ForceLayout + SpriteManager + LinkArrow
│                             #   logic as internal functions inside createProjector()
│                             #   (NOT separate mixin files — fe/ has no class+mixin
│                             #   pattern; cp/'s ChunkProjector class+mixin shape does
│                             #   not apply here, createProjector() is a closure factory)
├── projector.test.mjs       # extend: unit tests for the now-PURE helpers
│                             #   (buildPointArrays already follows this pattern —
│                             #   factor _computeRayData / ray-math into pure exports
│                             #   the same way, so Node can unit-test them like
│                             #   hsv_color.test.mjs does for cp/hsv_color.js)
└── magic_markdown.mjs        # NO direct change required — data-3d-node-id is set
                              #   by magic_markdown_panel.mjs (pin logic), already
                              #   scaffolded per CONTEXT.md; projector.mjs reads it
backend/templates/
└── editor.html               # add: an SVG host element for the link-arrow overlay
                              #   (e.g. <svg id="link-layer">), and pass url_roots
                              #   through to projector.setNodes on WS umap_canonical
```

### Pattern 1: Ray-constrained force-directed step (REAL-01)
**What:** Each chunk node may move only along the 1D ray from its URL's root through its initial UMAP position. Pairwise collider repulsion is computed in 3D but the resulting push is *projected onto each node's own ray direction* before being applied — so two nodes never leave their rays, they only slide along them.
**When to use:** Every animate-loop frame, once the first `umap_canonical` frame has arrived (`_umapLayoutActive` gate).
**Example (port target — adapt closure vars, not `this.*`):**
```javascript
// Source: backend/static/js/cp/force_layout.js (verbatim algorithm, ported to closure scope)
const NODE_RADIUS = 0.9;
const COLLIDER_SAFETY = 1.4; // see Assumption A1 — UI-SPEC codifies the SHIPPED value
const MIN_SEPARATION = 2 * NODE_RADIUS * COLLIDER_SAFETY;

function stepForceDirected(dt) {
  if (!_umapLayoutActive || _nodeRayData.size === 0) return;
  const nodes = [];
  _nodeRayData.forEach((rayData, nodeId) => {
    nodes.push({ id: nodeId, rayData, pos: _positions.get(nodeId) });
  });
  const radialForces = new Map();
  nodes.forEach(n => radialForces.set(n.id, 0));
  for (let a = 0; a < nodes.length; a++) {
    for (let b = a + 1; b < nodes.length; b++) {
      const na = nodes[a], nb = nodes[b];
      const d = na.pos.distanceTo(nb.pos);
      if (d >= MIN_SEPARATION || d < 0.001) continue;
      const pushTotal = (MIN_SEPARATION - d) * 0.5;
      // project push onto each node's OWN ray direction (key invariant)
      const sep = nb.pos.clone().sub(na.pos).normalize();
      const dotA = -sep.dot(na.rayData.rayDir);
      const dotB = sep.dot(nb.rayData.rayDir);
      radialForces.set(na.id, radialForces.get(na.id) + pushTotal * dotA);
      radialForces.set(nb.id, radialForces.get(nb.id) + pushTotal * dotB);
    }
  }
  const DAMPING = 0.3;
  radialForces.forEach((deltaR, id) => {
    if (Math.abs(deltaR) < 0.001) return;
    const rd = _nodeRayData.get(id);
    rd.radius = Math.max(0.5, rd.radius + deltaR * DAMPING);
    _positions.set(id, rd.rootPos.clone().add(rd.rayDir.clone().multiplyScalar(rd.radius)));
  });
}
```

### Pattern 2: Consume backend url_roots, never recompute placement (REAL-02)
**What:** `setNodes(coords, urlRoots)` reads the backend's already-resolved `root_position`/`bounding_radius` per URL; the frontend's only job is bookkeeping (which root is "newest" for camera framing) and ray-data derivation, NOT independent root placement.
**When to use:** Every `umap_canonical` frame and the `/api/recompute_umap` boot fetch.
**Example:**
```javascript
// Source: backend/api/ws_frames.py::build_umap_canonical (url_roots contract)
function setNodes(coords, urlRoots) {
  _coords = coords || {};
  const newUrls = [];
  if (urlRoots) {
    for (const url in urlRoots) {
      if (!_urlRootPositions.has(url)) newUrls.push(url); // first time we've seen this URL's root
      _urlRootPositions.set(url, new THREE.Vector3(...urlRoots[url].root_position));
      _urlBoundingRadii.set(url, urlRoots[url].bounding_radius);
    }
  }
  // ... rebuild points geometry from coords (existing buildPointArrays) ...
  computeRayData(); // re-derive rays now that roots may have shifted/added
  if (newUrls.length) frameCameraToRoot(newUrls[newUrls.length - 1]); // REAL-02 camera tween
}
```

### Pattern 3: Single-fetch image cache chain (REAL-03)
**What:** in-mem `Map` → IndexedDB blob → proxy fetch (same-bytes-to-IDB) → direct fetch fallback. The proxy's `X-Image-Proxy-Note` header marks a transparent-PNG placeholder response, which must NEVER be written to the IDB cache as a success.
**When to use:** Every image billboard candidate URL, deduplicated by Jaccard-similarity URL grouping first.
**Example:**
```javascript
// Source: backend/static/js/cp/sprite_manager.js::_loadAndCacheImage (verbatim port target)
async function loadAndCacheImage(originalUrl) {
  const cachedTex = await idbLoadTexture(originalUrl).catch(() => null);
  if (cachedTex) return cachedTex;
  const tryFetch = async (url) => {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error('http ' + resp.status);
    const note = resp.headers.get('X-Image-Proxy-Note'); // present ⇒ placeholder fallback
    const blob = await resp.blob();
    const tex = await buildFromBlob(blob); // THREE.TextureLoader via createObjectURL
    if (!note) idbSaveBlob(originalUrl, blob); // never cache the placeholder as success
    return tex;
  };
  try { return await tryFetch(toProxy(originalUrl)); }
  catch (_e) { try { return await tryFetch(originalUrl); } catch (_e2) { return null; } }
}
```

### Pattern 4: Solid headless 2D↔3D link arrow (REAL-04)
**What:** Per animate-loop frame, for every DOM element carrying `[data-3d-node-id]`, project that node's current world position through the camera; if in NDC z-range `[-1,1]` draw/update a solid SVG `<line>` from the element's border (toward the projected point) to the projected screen point; otherwise hide the line. No `marker-end`, no `stroke-dasharray`.
**When to use:** Every animate frame, gated by an early-out when zero pinned elements exist.
**Example:**
```javascript
// Source: backend/static/js/cp/concept_graph.js::_drawConcept3DLinks (verbatim port target;
// NDC z out-of-range = off-frustum hide; "Solid — no dasharray" + "headless connector
// (no arrowheads)" comments are load-bearing — REAL-04 hard-forbids both)
function drawConcept3DLinks() {
  const cards = document.querySelectorAll('[data-3d-node-id]');
  if (!cards.length) { /* hide stale lines, early-out */ return; }
  cards.forEach((card) => {
    const nodeId = card.getAttribute('data-3d-node-id');
    const worldPos = nodePositionFor(nodeId); // current animate-loop position, post force-step
    if (!worldPos) return;
    const projected = worldPos.clone().project(camera);
    if (projected.z < -1 || projected.z > 1) { hideLine(card); return; } // off-frustum
    const x2 = ...; const y2 = ...; // NDC → CSS px against canvas.getBoundingClientRect()
    const { x1, y1 } = nearestCardEdgeTowards(card, x2, y2);
    drawOrUpdateLine(card, x1, y1, x2, y2, { stroke: '#ffd700', strokeWidth: 2 }); // accent-arrow
  });
}
```

### Anti-Patterns to Avoid
- **Recomputing per-URL root placement client-side:** REAL-02's `root_position`/`bounding_radius` are backend-owned (D10: backend computes, frontend renders). Porting `_computeUrlRootPosition`'s 12-point golden-angle search into `fe/` would create a second, divergent source of truth and likely disagree with the backend's 9-direction `_allocate_new_root` result the moment a second URL is scanned. Consume `url_roots`, never recompute it.
- **Re-introducing the legacy `ChunkProjector` class+mixin pattern:** `cp/`'s `ForceLayoutMixin`/`SpriteManagerMixin`/`AnimationMixin` are `Object.assign`-style prototype mixins onto a `ChunkProjector` class. `fe/projector.mjs` is a closure factory (`createProjector(canvas, opts)` returning a plain object of functions) — port the *algorithms*, not the *class shape*. Mixing both patterns in one file will confuse future maintainers and break the existing `buildPointArrays`/`createProjector` export contract that `projector.test.mjs` already unit-tests.
- **Hardcoding `SAFETY_GAP = 5.0` (legacy) instead of trusting the backend's `12.0`:** see Assumptions Log A2. The frontend never needs this constant at all once it consumes `url_roots` — flag for removal from the port, not a value to copy.
- **THREE.Line for the 2D↔3D arrow:** the existing halo-ray and `concept-edges` SVG precedent (and `black_slate.spec`'s DOM-level no-dotted assertion, which inspects `stroke-dasharray` on SVG/CSS) means the arrow MUST be a DOM/SVG element, not a WebGL line — Playwright's e2e checks need to read it via `getComputedStyle`/`getAttribute`, which only works cleanly on DOM nodes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-URL non-overlap placement | A new client-side placement algorithm | The backend's `url_roots` (already computed, already broadcast) | D10 backend-computes/frontend-renders; backend has ALREADY diverged from the legacy reference's constants (`SAFETY_GAP=12.0` not `5.0`) — re-deriving client-side guarantees mismatch |
| Image blob persistence | A custom cache-eviction scheme | The exact `indexedDB.open('wfh_texture_cache', 1)` schema already in `cp/sprite_manager.js` | Reusing the same DB name means a returning user's already-cached scan images load instantly even on first visit to the NEW `fe/` surface — no migration needed, same browser storage |
| Screen-space line tracking a moving 3D point | A THREE.js raycasting/sprite-billboard hack | `Vector3.project(camera)` → NDC → CSS px (exactly what `_drawConcept3DLinks` and `projector.mjs`'s existing `project()` helper both already do) | `project()` is already exported by `createProjector()` for the halo's ray-transport (§V.4) — REAL-04 reuses the SAME function, not a parallel implementation |
| Camera auto-framing math | A custom FOV/distance solver | The legacy `frameAllInstances`/`flyToNode` AABB+bounding-sphere+cubic-ease approach | Already tuned against the real cluster scale in production; the `0.6× / 3.0×` adaptive-bounds constants are already locked in the UI-SPEC table — re-deriving them risks drifting from the contract |

**Key insight:** Every "don't hand-roll" item in this phase is "don't re-derive something the backend or the legacy `cp/` reference has already solved correctly" — this phase is a port, and the single biggest planning risk is treating it as new-feature design instead of careful translation.

## Common Pitfalls

### Pitfall 1: Treating `umap_canonical.coords` 6-vector and `url_roots` as independent/optional
**What goes wrong:** A naive port wires `setNodes(coords)` exactly as today and silently drops `url_roots` because the WS handler in `editor.html` line 296 currently does `if (f.type === "umap_canonical" && projector && f.coords) { projector.setNodes(f.coords); return; }` — `f.url_roots` is right there on the same frame object and is simply never read.
**Why it happens:** The existing minimal projector was built before REAL-01..04 existed; `url_roots` was added to the backend frame for the legacy `cp/` consumer and the served `fe/` consumer was never updated to match.
**How to avoid:** The `editor.html` WS handler AND the `bootProjector()` REST-fetch path BOTH need updating to pass `res.url_roots` (REST) / `f.url_roots` (WS) into `projector.setNodes(coords, urlRoots)`.
**Warning signs:** `projector.spec.js`'s multi-scan assertion shows both URLs' chunks landing at/near the origin (i.e., `url_roots` exists in the network payload but never reached the camera/ray math).

### Pitfall 2: Porting `COLLIDER_SAFETY` as `2.0` (the doc) instead of `1.4` (the shipped code)
**What goes wrong:** If the planner/executor "fixes" the discrepancy by reading only `projector.md`'s prose, the ported collider spacing becomes ~43% larger than what the legacy reference actually renders, and `projector.spec.js`'s minimum-pairwise-spacing assertion (if it asserts an exact multiple) will fail or silently pass a looser bound that doesn't match production behavior.
**Why it happens:** `docs/frontend/projector.md` §5 and `force_layout.js` line 161 disagree (Assumption A1, already logged in `06-UI-SPEC.md`).
**How to avoid:** UI-SPEC's A1 resolution already says: port the SHIPPED value `1.4`. The planner should add a one-line doc-reconciliation task (update `projector.md` to say `1.4`, not a code change) rather than changing the ported constant.
**Warning signs:** A test asserting `minSeparation === 2 * 0.9 * 2.0 = 3.6` when the ported code uses `2 * 0.9 * 1.4 = 2.52`.

### Pitfall 3: Image proxy placeholder poisoning the cache
**What goes wrong:** If the port's fetch-chain caches the proxy's transparent-PNG fallback response as if it were a real image (skipping the `X-Image-Proxy-Note` header check), every subsequent IndexedDB load for that URL returns the 1×1 placeholder forever — silently breaking image billboards for that URL until the IDB entry is manually cleared.
**Why it happens:** It's an easy line to drop in a port — `if (!note) this._idbSaveBlob(...)` looks like a no-op guard unless you know WHY it's there.
**How to avoid:** Port `tryFetch`'s exact structure (read `note` BEFORE deciding to cache); add an explicit e2e/REPL assertion that a known-404 image URL never becomes a "successful" cache hit on second load.
**Warning signs:** An image billboard shows a blank/transparent sprite on the SECOND scan of a URL that successfully showed an image on the FIRST scan within the same session (cache-then-fail flips to cache-then-always-fail).

### Pitfall 4: Arrow drawn from THREE-world projection without canvas-relative offset
**What goes wrong:** `Vector3.project(camera)` returns NDC coordinates relative to the FULL viewport; converting to CSS px must use the **canvas's** `getBoundingClientRect()`, not `window.innerWidth/innerHeight`, or the arrow lands at the wrong screen position whenever the canvas isn't full-viewport (e.g., side panels open).
**Why it happens:** `editor.html`'s `#projector` canvas is currently `position: fixed; inset: 0` (full-bleed), so this bug is latent — it would only surface if/when the served layout adds a side panel that shrinks the canvas. The legacy reference (`concept_graph.js::_drawConcept3DLinks`) already does this correctly (`canvas.getBoundingClientRect()`), so PORT the exact computation rather than assuming full-viewport.
**How to avoid:** Copy the legacy's `rect = canvas.getBoundingClientRect()` + `x2 = rect.left + (projected.x*0.5+0.5)*rect.width` pattern verbatim.
**Warning signs:** Arrow endpoint visibly offset from the rendered node when the browser window isn't square, or when devtools/sidebars change the canvas's effective rect.

## Code Examples

### Building the SVG link-layer host (new — editor.html currently has none)
```html
<!-- Source: pattern matches the existing haloHost approach already in editor.html
     (document.createElement('div'); document.body.appendChild(haloHost);) — the
     link-arrow layer should follow the SAME "append a fixed-position overlay div/svg
     to body, above the canvas (z-index), below/alongside the panel grid" convention -->
<svg id="link-layer" style="position:fixed;inset:0;z-index:1;pointer-events:none;width:100vw;height:100vh;">
  <!-- <line> elements appended/updated here per animate frame -->
</svg>
```
`z-index:1` sits above `#projector` (`z-index:0`) and below `#grid` (`z-index:2`) per the existing `editor.html` stacking convention (lines 13-14) — panels must remain clickable above the arrow.

### projector.test.mjs extension pattern (pure-function testability)
```javascript
// Source: backend/static/js/fe/projector.test.mjs (existing pattern) — REAL-01's ray
// math should be factored as a pure export the same way buildPointArrays already is,
// so it is unit-testable in Node without a browser/WebGL context.
export function computeRayDir(rootPos, umapPos) {
  const ray = [umapPos[0]-rootPos[0], umapPos[1]-rootPos[1], umapPos[2]-rootPos[2]];
  const len = Math.hypot(...ray);
  if (len < 0.001) return { dir: [1,0,0], radius: 0 };
  return { dir: ray.map(v => v/len), radius: len };
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `cp/` Fibonacci concentric-sphere bootstrap layout as a FINAL position | UMAP-linear-radial force-directed hybrid; Fibonacci permitted ONLY as transient pre-UMAP placeholder | Pre-v1.0 (CLAUDE.md Forbidden Concepts, already locked) | This phase must not regress this — REAL-01 explicitly re-asserts "no concentric/Fibonacci as a final position" |
| `cp/`'s 12-point golden-angle root-candidate search (client-side) | Backend's 9-direction `_allocate_new_root` (server-side) | Backend `layout_service.py` already shipped this independently of the `cp/` port | The frontend never needs the candidate-search code at all — only the resolved `root_position` |
| `SAFETY_GAP = 5.0` (legacy client constant) | `DEFAULT_SAFETY_GAP = 12.0` (backend constant, "doubled from 6.0") | Backend-side change, already live | Confirms backend is the sole authority for this value; frontend must not hardcode either number |

**Deprecated/outdated:**
- The `cp/` `ChunkProjector` class + `Object.assign(ChunkProjector.prototype, Mixin)` pattern: superseded by `fe/`'s closure-factory (`createProjector`) pattern. Do not reintroduce the class+mixin shape.
- `cp/`'s dashed `_extraConnectorsMesh` (dashed THREE.LineSegments for extra-image-sprite connectors, `animation.js` line 829: `transparent: true, opacity: 0.35` — note this is a SEPARATE concern from the 2D↔3D arrow and is not itself dashed via `stroke-dasharray`, but it IS a different, fainter connector style). REAL-03/REAL-04 scope is the PRIMARY image billboard + the 2D↔3D arrow; the extra-sprite radial connector lines are out of this phase's explicit requirements (not named in REAL-01..04) — flag as a possible follow-on, do not silently port it as if it were required.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `COLLIDER_SAFETY` should port as the shipped `1.4`, not the doc's `≥2.0` (carried forward from `06-UI-SPEC.md`'s own A1, re-verified here against `force_layout.js` line 161) | Common Pitfalls #2, Standard Stack | If wrong, collider spacing in the ported `fe/` projector won't visually match the legacy reference's actual on-screen density, and any e2e assertion hardcoding `1.4`-derived `MIN_SEPARATION` would need updating |
| A2 | The frontend needs ZERO client-side `SAFETY_GAP` constant because the backend's `url_roots.bounding_radius` already encodes the placement; porting `_computeUrlRootPosition`'s candidate-search is unnecessary dead code | Don't Hand-Roll, Anti-Patterns | If the backend's `url_roots` were ever found to be insufficiently granular (e.g., missing on first frame before any chunks land), the frontend might need a temporary client-side placeholder placement — but no evidence of this gap was found in `ws_frames.py`/`layout_service.py` |
| A3 | The 2D↔3D link arrow's screen-overlay element should be a NEW `<svg id="link-layer">` host appended to `editor.html`, following the existing `haloHost` div-append convention, rather than reusing/extending `magic_markdown.mjs`'s "partial 2D↔3D link-arrow scaffolding" mentioned in CONTEXT.md (no such scaffolding was found in `magic_markdown.mjs` itself — it may live in `magic_markdown_panel.mjs` or `magic_markdown_halo.mjs`, neither of which was read in this research pass) | Code Examples, System Architecture Diagram | If `magic_markdown_panel.mjs` already has partial arrow-drawing code, the port should EXTEND it rather than add a parallel implementation — planner should grep `magic_markdown_panel.mjs` and `magic_markdown_halo.mjs` for `data-3d-node-id` / `link-layer` / arrow-drawing logic before assigning this task |
| A4 | Camera `minDistance`/`maxDistance` adaptive-bounds formulas (`0.6× cluster_radius`, `3.0× max(|pos|)`) port directly from `animation.js` lines 765/794 without modification, since the UI-SPEC table already locks these exact multipliers | Standard Stack, Architecture Patterns | Low risk — UI-SPEC already codifies these as locked contract values, not open for this research to second-guess |

**If this table is empty:** N/A — see entries above.

## Open Questions

1. **Where exactly does `magic_markdown.mjs`'s "partial 2D↔3D link-arrow scaffolding" (mentioned in the phase's `<key_source_files_to_map>`) actually live?**
   - What we know: `magic_markdown.mjs` (284 lines, fully read this session) contains the field-tree/render-panel/render-graph model — NO arrow/SVG/3D-link code of any kind. `data-3d-node-id` is referenced in legacy `billboard.js`/`concept_graph.js` only.
   - What's unclear: Whether `magic_markdown_panel.mjs` (referenced in `editor.html`'s imports but not read this session) or `magic_markdown_halo.mjs` carries partial arrow logic, or whether the phrase in CONTEXT.md refers to the halo's ray-transport (`§V.4`, which IS in `magic_markdown.mjs`'s sibling import chain via `editor.html`'s `realiseHalo`/`haloVDom` calls) being mistaken for the 2D↔3D arrow.
   - Recommendation: Planner's first REAL-04 task should be a 10-minute grep/read of `magic_markdown_panel.mjs` for `data-3d-node-id` before writing the arrow-drawing task, to confirm whether this is new code or an extension.

2. **Does the served `editor.html` pin panel ever call something equivalent to `card.dataset['3dNodeId'] = data.id` today?**
   - What we know: The CONTEXT.md states "every pinned panel carries `data-3d-node-id` (existing convention)" as if already wired in `fe/`. This research did not find that line in `magic_markdown.mjs` (the file explicitly named in `<key_source_files_to_map>`).
   - What's unclear: Whether "existing convention" means "exists in `cp/`'s `billboard.js`/`concept_graph.js` only" (legacy) or whether the served `fe/` pin logic (likely in `magic_markdown_panel.mjs`, not read) already sets this attribute.
   - Recommendation: Same grep as Open Question 1 resolves both; if `magic_markdown_panel.mjs` does NOT yet set `data-3d-node-id`, that attribute-setting becomes an explicit REAL-04 subtask, not an assumed precondition.

3. **Should the force-directed step run for EVERY chunk node, or only chunks belonging to URLs whose `url_roots` entry has already arrived?**
   - What we know: `_stepForceDirected` early-returns if `_nodeRayData` is empty; `_computeRayData` falls back to `(0,0,0)` root if a URL's root isn't yet placed (legacy line 117-126).
   - What's unclear: In the served `fe/` idiom, does a chunk ever render BEFORE its URL's `url_roots` entry exists (e.g., mid-scan streaming before scan-end UMAP fires)? If so the ray-fallback-to-origin behavior needs the same defensive fallback ported.
   - Recommendation: Mirror the legacy's defensive fallback verbatim (don't optimize it away) — it is cheap and prevents a NaN/crash if `url_roots` is momentarily behind `coords` in a frame.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| THREE.js (CDN) | All of REAL-01..04 | ✓ (already loaded by `editor.html`) | r128 | none needed — already wired |
| OrbitControls (CDN) | REAL-02 camera framing | ✓ (already loaded by `editor.html`) | r0.128.0 | none needed |
| `/api/image_proxy` route | REAL-03 cross-origin image fetch | ✓ (`backend/api/routes.py:1898`, `X-Image-Proxy-Note` header confirmed) | n/a (existing route) | none needed |
| `/api/recompute_umap` route | REAL-02 boot fetch | ✓ (`backend/api/routes.py:1490`, already returns `url_roots` via `build_umap_canonical`) | n/a (existing route) | none needed |
| IndexedDB (browser native) | REAL-03 cross-session cache | ✓ (standard browser API; legacy code already has graceful `catch(_) { resolve(null) }` degradation if unavailable) | n/a | falls back to in-mem cache + proxy/direct re-fetch every session |
| Playwright (`@playwright/test`) | e2e verification | ✓ `^1.49.0` declared in `package.json`; `1.61.0` confirmed installed | 1.61.0 | none needed |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — every dependency this phase needs is already present and wired.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright `@playwright/test` 1.61.0 (config: `frontend_e2e/playwright.config.js`) + Node's built-in `node --test` for pure-function unit tests (`backend/static/js/fe/*.test.mjs`) + the Python REPL `env-scenario` harness (`scripts/sim_frontend.py`) |
| Config file | `frontend_e2e/playwright.config.js` (e2e) / `package.json`'s `test:fe` script (unit) |
| Quick run command | `node --test backend/static/js/fe/projector.test.mjs` (unit, < 5s) |
| Full suite command | `npm run test:e2e` (Playwright, self-boots a stub backend on 8080) AND `python scripts/sim_frontend.py env-scenario --name full-smoke` (REPL, both stub and `--real` modes) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REAL-01 | Rays exist per chunk-to-root; min pairwise spacing holds; no Fibonacci final position | unit + e2e | `node --test backend/static/js/fe/projector.test.mjs` (ray math) + `npx playwright test projector.spec.js -g "force-directed"` | ❌ Wave 0 (extend `projector.test.mjs`; add new test block in `projector.spec.js`) |
| REAL-02 | Per-URL non-overlap; old URLs never move; camera frames/tweens to newest root | e2e + REPL | `npx playwright test projector.spec.js -g "multi-scan"` + `python scripts/sim_frontend.py env-scenario --name perimeter-rescale` (existing, backend-only — confirms `url_roots` math) | ❌ Wave 0 (e2e is new; `perimeter-rescale` REPL scenario already exists and passes today, confirming backend contract) |
| REAL-03 | Single-fetch order; shared Texture per URL; placeholder never cached; persists across re-render | e2e | `npx playwright test projector.spec.js -g "image"` (new) — must assert `window.indexedDB` entry survives a `window.__mm_rerender()` call without a new network request | ❌ Wave 0 |
| REAL-04 | Solid line tracks moving node; off-frustum hides; no dotted; `black_slate.spec` stays green | e2e | `npx playwright test projector.spec.js -g "arrow"` (new) + `npx playwright test black_slate.spec.js` (existing, must stay green — already asserts no `stroke-dasharray` project-wide via DOM inspection patterns) | ❌ Wave 0 for the arrow-specific test; `black_slate.spec.js` itself EXISTS and is a regression gate, not new |

### Sampling Rate
- **Per task commit:** `node --test backend/static/js/fe/projector.test.mjs` (pure-function ray/placement math, <5s)
- **Per wave merge:** `npm run test:e2e` (full Playwright suite against stub backend) + `python scripts/sim_frontend.py env-scenario --name 6d-umap-format` + `--name perimeter-rescale` (both already green; must stay green)
- **Phase gate:** Full real-stack inline per `STATE.md`'s verification-depth choice — `python scripts/run_full_stack_tests.py --real` (probes + real full-smoke + e2e), honoring the clean-GPU preflight noted in `STATE.md`'s Blockers/Concerns.

### Wave 0 Gaps
- [ ] `frontend_e2e/projector.spec.js` — extend with REAL-01 (ray/spacing), REAL-02 (multi-scan/camera), REAL-03 (image persistence), REAL-04 (arrow tracking) test blocks; the file currently only has the UMAP-01 HSV-render test (32 lines, fully read this session)
- [ ] `backend/static/js/fe/projector.test.mjs` — extend with pure ray-math unit tests (`computeRayDir`, collider-force calculation) mirroring the existing `buildPointArrays` test pattern (not read directly this session but referenced by the existing `projector.spec.js` comment: "the 6D-UMAP HSV math is unit-verified in `backend/static/js/fe/projector.test.mjs` (7/7)")
- [ ] A live-stack probe script equivalent to `scripts/probe_live_archive_scan.py` does NOT need a NEW probe per CONTEXT.md's verification gate ("the consolidated real-stack acceptance run at milestone end") — REAL-01..04 ride on the EXISTING `probe_live_archive_scan.py` + `probe_live_dominance_and_timed_scan.py` (multi-scan) flows; no new probe script required, only e2e + REPL scenario coverage

## Project Constraints (from CLAUDE.md)

- **Backend computes; frontend renders.** Non-negotiable (D10). This phase's frontend code must NEVER recompute `root_position`/`bounding_radius`/UMAP fit — only consume and render what `layout_service.py` already emits.
- **No-mocks contract (§8D.46).** `all_real: true` required at milestone-end acceptance; this phase's verification gate is explicitly "full real-stack inline" per `STATE.md` — every e2e/REPL check must also be confirmed green against the real Selenium+CUDA stack, not just the stub.
- **Forbidden Concepts — no concentric Fibonacci spheres as a FINAL layout position.** REAL-01 explicitly re-asserts this; the bootstrap/transient Fibonacci placeholder remains permitted ONLY until `umap_canonical` arrives.
- **Forbidden Concepts — no dotted/dashed lines anywhere.** REAL-04's arrow AND the existing `black_slate.spec`'s no-dotted assertion (`stroke-dasharray`) must both stay satisfied; this is a hard project-wide rule, not scoped to this phase alone.
- **Forbidden Concepts — no panel chrome.** Any new DOM element this phase adds (e.g., the `#link-layer` SVG host) must not introduce a header/×/minimiser/topbar on any panel; the arrow overlay is a passive render layer with `pointer-events:none`, never an interactive chrome element.
- **Verification idiom = env-scenario + probe + e2e, NOT screenshots.** "A screenshot is not feature proof." Every REAL-0x acceptance claim in the eventual PLAN.md must cite an automated assertion (Playwright DOM/computed-style check, REPL env-scenario, or live probe), never a visual screenshot as the sole evidence.
- **`WFH_SLM_MODEL` / Llama ban, CUDA defaults, etc.** Not directly load-bearing for this phase (no SLM/embedder interaction in REAL-01..04), but the real-stack acceptance run at milestone end inherits the full no-mocks contract regardless of phase scope.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REAL-01 | `fe/` projector renders UMAP-linear-radial force-directed layout: chunks converge along root-URL rays with hard collider repulsion (zero force above `2·R·safety`, exact-correction below); no concentric/Fibonacci as final position. | `cp/force_layout.js::_computeRayData`/`_stepForceDirected` read in full and reproduced as Pattern 1; `COLLIDER_SAFETY` discrepancy resolved per UI-SPEC A1 (port `1.4`); pure-function port path documented for unit-testability. |
| REAL-02 | Per-URL multi-scan placement: each URL has `root_position`+`bounding_radius`; new URL lands non-overlapping at `existing_max + new_radius + safety_gap`; old URLs never move; camera frames/tweens to newest root on scan-end. | Confirmed backend (`layout_service.py::_per_url_postprocess`/`_allocate_new_root`) ALREADY computes and broadcasts this via `umap_canonical.url_roots`; frontend gap is purely "consume `url_roots`, frame the camera" (Pattern 2); `SAFETY_GAP` discrepancy (backend `12.0` vs legacy `5.0`) resolved by deferring entirely to backend value (Assumption A2). Camera adaptive-bounds formulas confirmed verbatim in `animation.js` lines 753-798 and locked in UI-SPEC. |
| REAL-03 | Image billboards: in-mem → IndexedDB → proxy → direct fetch order; shared `THREE.Texture` per URL; transparent-PNG fallback never cached as success; collider spacing shared with text billboards. | `cp/sprite_manager.js` read in full (498 lines); exact fetch-chain, IDB schema (`wfh_texture_cache`/`textures`), Jaccard URL-dedup, and `X-Image-Proxy-Note` no-cache-on-placeholder rule documented in Pattern 3 and Pitfall 3; `/api/image_proxy` route confirmed present server-side with the matching header. |
| REAL-04 | Every pinned panel carries `data-3d-node-id`; animate loop projects the node and draws a SOLID HEADLESS line tracking the moving node; off-frustum hides; no dotted lines. | `cp/concept_graph.js::_drawConcept3DLinks` read in full and reproduced verbatim as Pattern 4 (solid `<line>`, `removeAttribute('marker-end')`, NDC z-range off-frustum hide, canvas-relative `getBoundingClientRect()` math); `data-3d-node-id` convention confirmed in `cp/billboard.js` line 863; Open Questions 1-2 flag the unverified claim that `fe/`'s pin logic already sets this attribute. |
</phase_requirements>

## Sources

### Primary (HIGH confidence)
- `backend/static/js/cp/force_layout.js` (full read, 310 lines) — REAL-01/REAL-02 reference algorithm
- `backend/static/js/cp/sprite_manager.js` (full read, 498 lines) — REAL-03 reference algorithm
- `backend/static/js/cp/animation.js` (full read, 847 lines) — camera framing/tween, frustum culling, animate-loop composition
- `backend/static/js/cp/hsv_color.js` (full read, 160 lines) — HSV color math (already ported into `fe/projector.mjs`'s `buildPointArrays`)
- `backend/static/js/cp/concept_graph.js` lines 3810-5607 (targeted read) — REAL-04 reference algorithm (`_drawConcept3DLinks`)
- `backend/static/js/cp/billboard.js` lines 850-900, 1570-1600 (targeted read) — `data-3d-node-id` convention, arrow anchor-point math
- `backend/static/js/fe/projector.mjs` (full read, 136 lines) — current served projector, the port TARGET
- `backend/static/js/fe/magic_markdown.mjs` (full read, 284 lines) — confirmed NO arrow scaffolding present (resolves/raises Open Questions 1-2)
- `backend/templates/editor.html` (full read, 387 lines) — served app boot sequence, WS handler, `bootProjector()`
- `backend/services/layout_service.py` lines 600-719, 790-925 (targeted read) — `_project`, `_per_url_postprocess`, `_allocate_new_root` (confirms backend already owns REAL-02's data)
- `backend/api/ws_frames.py` lines 195-270 (targeted read) — `build_umap_canonical` wire contract confirming `url_roots` schema
- `backend/api/routes.py` lines 1490-1637, 1898-1935, 2053-2064 (targeted read) — `/api/recompute_umap`, `/api/image_proxy`, `X-Image-Proxy-Note`
- `frontend_e2e/projector.spec.js` (full read, 32 lines) — existing e2e pattern (UMAP-01 HSV render test)
- `frontend_e2e/black_slate.spec.js` lines 1-60 (targeted read) — existing no-dotted/no-chrome regression gate REAL-04 must not break
- `frontend_e2e/halo.spec.js` lines 1-40 (targeted read) — existing halo e2e pattern for reference
- `frontend_e2e/playwright.config.js` (full read) — e2e harness boot/config
- `.planning/phases/WFH-06-served-slate-3d-real-register/06-CONTEXT.md` (full read) — phase scope, as-built starting point
- `.planning/phases/WFH-06-served-slate-3d-real-register/06-UI-SPEC.md` (full read) — locked visual/interaction contracts, Assumptions A1-A3
- `.planning/REQUIREMENTS.md` (full read) — REAL-01..04 acceptance criteria
- `.planning/STATE.md` (full read) — verification depth, env hygiene blockers
- `CLAUDE.md` (full read, project root) — Forbidden Concepts, no-mocks contract, architectural non-negotiables
- `package.json` (full read) — confirms no THREE npm dependency (CDN-only), Playwright 1.49.0 declared
- `scripts/sim_frontend.py` lines 7558-7977, 8456-8640 (targeted grep+read) — `6d-umap-format`/`perimeter-rescale` env-scenario implementations, confirming backend contract already passes

### Secondary (MEDIUM confidence)
- None — all findings in this research trace to direct codebase reads (HIGH confidence by the project's own provenance rules, since this is a brownfield port where the "documentation" IS the source code).

### Tertiary (LOW confidence)
- None. The two discrepancies flagged (Assumptions A1/A2) are not LOW-confidence findings per se — they are confirmed, verbatim-quoted disagreements between two HIGH-confidence sources (legacy code vs. current backend code / legacy code vs. design doc), surfaced for the planner to make an explicit decision rather than inherit silently.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, exact CDN URLs/versions confirmed via direct file read on both `editor.html` and `index.html`
- Architecture: HIGH — every algorithm in this research was read directly from the shipping legacy source and the shipping backend source, not inferred or summarized from docs
- Pitfalls: HIGH — all four pitfalls are concrete, named code-level traps found by diffing the legacy reference against the current `fe/` target line-by-line (e.g., the dropped `url_roots` field, the `X-Image-Proxy-Note` cache-poisoning guard)

**Research date:** 2026-06-22
**Valid until:** 2026-07-22 (30 days — this is a stable, closed-source-tree port with no external API/version churn risk; the only volatility is if `layout_service.py`'s `DEFAULT_SAFETY_GAP`/`_allocate_new_root` changes again before this phase executes, which the planner should re-check with a quick grep at execution time)
