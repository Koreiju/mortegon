/**
 * projector.mjs — the fe/real 3D projector (minimal): renders every chunk as a
 * node at its UMAP position (from `/api/recompute_umap` → {chunk_id:[x,y,z]}),
 * so the editor has the 3D Real register the halo transports nodes from (O.18).
 *
 * `buildPointArrays` is PURE (coords → typed arrays + id order) and
 * unit-testable in Node; `project` (world→screen) and the THREE wiring are the
 * browser layer (window.THREE, loaded by editor.html).
 */

import { placeCandidatesOnCone } from "./halo_cone.mjs";

/**
 * buildPointArrays(coords, optsOrHslToRgb) →
 *   { ids, positions:Float32Array, colors:Float32Array, count }.
 *
 * coords: `{ chunkId: [x,y,z] }` (3-vector) OR `{ chunkId: [x,y,z,h,s,v] }`
 * (the backend's canonical 6D `umap_canonical` frame, §6.1 / §11.5). The 3D
 * nodes are the only filled colour in the app (theme.md §2.5) and the frontend
 * RENDERS the backend's HSV — it does not invent it:
 *   - a **6-vector** colours from the frame's HSV channels (`p[3..5]`, in [0,1],
 *     fed as `setHSL(h,s,v)` per §11.5);
 *   - a **3-vector** falls back to the even positional HSV sweep (the bootstrap
 *     stand-in, only until a real layout frame arrives) — backward compatible.
 * `opts.azimuth` rotates the hue by the camera azimuth (UMAP-01: "HSV rotates
 * with camera azimuth") — the same azimuth the halo rays couple to. The 2nd arg
 * also accepts a bare `hslToRgb` function (legacy positional).
 */
export function buildPointArrays(coords, optsOrHslToRgb) {
  const opts = typeof optsOrHslToRgb === "function" ? { hslToRgb: optsOrHslToRgb } : (optsOrHslToRgb || {});
  const toRgb = opts.hslToRgb || _hslToRgb;
  const hueOffset = (((opts.azimuth || 0) / (Math.PI * 2)) % 1 + 1) % 1;
  const ids = Object.keys(coords || {});
  const n = ids.length;
  const positions = new Float32Array(n * 3);
  const colors = new Float32Array(n * 3);
  ids.forEach((id, i) => {
    const p = coords[id] || [0, 0, 0];
    positions[i * 3] = +p[0] || 0;
    positions[i * 3 + 1] = +p[1] || 0;
    positions[i * 3 + 2] = +p[2] || 0;
    let h, s, l;
    if (p.length >= 6) {                 // the backend's 6D frame — render its HSV
      h = +p[3] || 0; s = +p[4] || 0; l = +p[5] || 0;
    } else {                             // 3-vector — positional sweep (bootstrap stand-in)
      h = i / Math.max(1, n); s = 0.7; l = 0.6;
    }
    h = ((h + hueOffset) % 1 + 1) % 1;   // camera-azimuth hue rotation
    const [r, g, b] = toRgb(h, s, l);
    colors[i * 3] = r; colors[i * 3 + 1] = g; colors[i * 3 + 2] = b;
  });
  return { ids, positions, colors, count: n };
}

function _hslToRgb(h, s, l) {
  const k = (n) => (n + h * 12) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return [f(0), f(8), f(4)];
}

/**
 * REAL-01 force-directed ray convergence (port of `cp/force_layout.js`).
 *
 * NODE_RADIUS / COLLIDER_SAFETY / MIN_SEPARATION are the LOCKED ship values
 * (UI-SPEC Assumption A1) — `COLLIDER_SAFETY` is the shipped `1.4`, NOT the
 * doc's `≥2.0`; MIN_SEPARATION = 2 * 0.9 * 1.4 = 2.52. DAMPING is the
 * per-frame radial-force scale applied in `_stepForceDirected`.
 */
export const NODE_RADIUS = 0.9;
export const COLLIDER_SAFETY = 1.4; // ship value (cp/force_layout.js line 161) — NOT 2.0
export const MIN_SEPARATION = 2 * NODE_RADIUS * COLLIDER_SAFETY; // = 2.52
export const DAMPING = 0.3;

/**
 * computeRayDir(rootPos, umapPos) → { dir:[x,y,z], radius } — pure, array-in/
 * array-out (no THREE dependency). The ray fixes from the URL root through the
 * node's initial UMAP position; `dir` is unit length, `radius` is the initial
 * distance along the ray. Degenerate (node sits on root, `len < 0.001`)
 * mirrors `cp/force_layout.js` lines 117-126/128-144 verbatim: arbitrary
 * ray `[1,0,0]`, `radius:0`.
 */
export function computeRayDir(rootPos, umapPos) {
  const ray = [umapPos[0] - rootPos[0], umapPos[1] - rootPos[1], umapPos[2] - rootPos[2]];
  const len = Math.hypot(ray[0], ray[1], ray[2]);
  if (len < 0.001) return { dir: [1, 0, 0], radius: 0 };
  return { dir: [ray[0] / len, ray[1] / len, ray[2] / len], radius: len };
}

/**
 * colliderRadialForce(posA, posB, rayDirA, rayDirB) → { forceA, forceB } —
 * pure per-pair radial push (scalar, along each node's OWN ray direction),
 * ported from `cp/force_layout.js::_stepForceDirected` lines 178-204. Hard
 * floor: zero force at distance >= MIN_SEPARATION (no soft falloff tail);
 * below that, the exact correction `(MIN_SEPARATION - d) * 0.5` projected
 * via dot products onto each ray.
 */
export function colliderRadialForce(posA, posB, rayDirA, rayDirB) {
  const dx = posB[0] - posA[0], dy = posB[1] - posA[1], dz = posB[2] - posA[2];
  const dist = Math.hypot(dx, dy, dz);
  if (dist >= MIN_SEPARATION || dist < 0.001) return { forceA: 0, forceB: 0 };
  const ux = dx / dist, uy = dy / dist, uz = dz / dist;
  const pushTotal = (MIN_SEPARATION - dist) * 0.5;
  const dotA = -(ux * rayDirA[0] + uy * rayDirA[1] + uz * rayDirA[2]);
  const dotB = (ux * rayDirB[0] + uy * rayDirB[1] + uz * rayDirB[2]);
  return { forceA: pushTotal * dotA, forceB: pushTotal * dotB };
}

/**
 * createProjector(canvas, opts) — a minimal THREE points scene (browser only).
 * Returns { setNodes(coords)→count, project(x,y,z)→{x,y,inFront}, nodeCount(),
 * camera }. `project` maps a world position to screen px (for the halo's 3D
 * ray-transport).
 */
export function createProjector(canvas, opts = {}) {
  const THREE = window.THREE;
  if (!THREE) throw new Error("THREE not loaded");
  const w = () => canvas.clientWidth || canvas.width || 800;
  const h = () => canvas.clientHeight || canvas.height || 600;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x000000);
  const camera = new THREE.PerspectiveCamera(60, w() / h(), 0.1, 8000);
  camera.position.set(0, 0, 140);
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setSize(w(), h(), false);
  let controls = null;
  if (THREE.OrbitControls) { controls = new THREE.OrbitControls(camera, canvas); controls.enableDamping = true; }
  let points = null;
  let _coords = {};        // the last frame's coords, kept for azimuth recolour
  let _lastColorAz = null;
  let _lastUrlRoots = null; // the last urlRoots passed to setNodes — REAL-03 __mm_rerender support

  // REAL-03 — image billboard texture cache chain. Port of
  // cp/sprite_manager.js lines 313-434 verbatim in structure: in-memory Map
  // (fastest, per-session) → IndexedDB blob (cross-session, same DB/store
  // name as the legacy code so an existing user's cache carries over with
  // zero migration) → /api/image_proxy fetch (CORS-bypass tier, tried
  // first on a cache miss) → direct fetch (last-resort fallback). The
  // X-Image-Proxy-Note response header marks the proxy's transparent-PNG
  // placeholder fallback (returned with HTTP 200, never a non-ok status) —
  // it is read BEFORE the caching decision so a placeholder is NEVER
  // written to IDB as a "successful" image (Pitfall 3 / threat T-06-06).
  const _textureCache = new Map(); // url (string) → THREE.Texture, in-mem, per-session
  const _inflight = new Map();      // url → Promise<THREE.Texture|null> — in-flight dedup (WR-02)
  let _idbPromise = null;
  let _netFetchCount = 0; // incremented on every REAL network fetch() the loader issues (test hook)

  function idbOpen() {
    if (_idbPromise) return _idbPromise;
    _idbPromise = new Promise((resolve) => {
      try {
        const req = indexedDB.open("wfh_texture_cache", 1);
        req.onupgradeneeded = (ev) => {
          const db = ev.target.result;
          if (!db.objectStoreNames.contains("textures")) {
            db.createObjectStore("textures", { keyPath: "url" });
          }
        };
        req.onsuccess = (ev) => resolve(ev.target.result);
        req.onerror = () => resolve(null);
        req.onblocked = () => resolve(null);
      } catch (_) { resolve(null); }
    });
    return _idbPromise;
  }

  function buildFromBlob(blob) {
    return new Promise((resolve, reject) => {
      const objUrl = URL.createObjectURL(blob);
      const loader = new THREE.TextureLoader();
      loader.load(objUrl, (tex) => {
        try { URL.revokeObjectURL(objUrl); } catch (_) {}
        resolve(tex);
      }, undefined, (err) => {
        try { URL.revokeObjectURL(objUrl); } catch (_) {}
        reject(err);
      });
    });
  }

  async function idbLoadTexture(url) {
    const db = await idbOpen();
    if (!db) return null;
    return new Promise((resolve) => {
      try {
        const tx = db.transaction("textures", "readonly");
        const store = tx.objectStore("textures");
        const r = store.get(url);
        r.onsuccess = () => {
          const rec = r.result;
          if (!rec || !rec.blob) { resolve(null); return; }
          buildFromBlob(rec.blob).then(resolve).catch(() => resolve(null));
        };
        r.onerror = () => resolve(null);
      } catch (_) { resolve(null); }
    });
  }

  async function idbSaveBlob(url, blob) {
    try {
      if (!blob || blob.size < 32) return;
      const db = await idbOpen();
      if (!db) return;
      const tx = db.transaction("textures", "readwrite");
      tx.objectStore("textures").put({ url, blob, ts: Date.now() });
    } catch (_) { /* IDB is best-effort */ }
  }

  function toProxy(absUrl) {
    try {
      const u = new URL(absUrl, window.location.href);
      if (u.protocol === "data:" || u.protocol === "blob:") return absUrl;
      if (u.origin === window.location.origin) return absUrl;
      return `/api/image_proxy?url=${encodeURIComponent(u.href)}`;
    } catch (_) { return absUrl; }
  }

  // loadAndCacheImage(originalUrl) — the ordered single-fetch chain:
  // in-mem Map → IndexedDB blob → proxy fetch → direct fetch. Every IDB op
  // already degrades to null on failure (never throws); a fetch failure at
  // any network tier falls through to the next tier, and total failure
  // resolves null (no image — no crash).
  async function loadAndCacheImage(originalUrl) {
    const memHit = _textureCache.get(originalUrl);
    if (memHit) return memHit;
    // WR-02 — dedup concurrent loads of the SAME url so two overlapping
    // callers (e.g. successive setNodes/spawnImageBillboards frames) await
    // ONE fetch + ONE GPU upload rather than racing two. Placeholders are
    // never written to _textureCache (CR-01), so a placeholder url falls
    // through to a fresh in-flight fetch on its NEXT call (preserving the
    // re-attempt contract) — only the concurrent in-flight window is shared.
    const pending = _inflight.get(originalUrl);
    if (pending) return pending;
    const p = _loadAndCacheImageInner(originalUrl);
    _inflight.set(originalUrl, p);
    try { return await p; }
    finally { _inflight.delete(originalUrl); }
  }

  async function _loadAndCacheImageInner(originalUrl) {
    const idbHit = await idbLoadTexture(originalUrl).catch(() => null);
    if (idbHit) { _textureCache.set(originalUrl, idbHit); return idbHit; }

    const tryFetch = async (url) => {
      _netFetchCount++;
      const resp = await fetch(url);
      if (!resp.ok) throw new Error("http " + resp.status);
      // Read the proxy-fallback note BEFORE deciding to cache — never
      // cache a transparent-PNG placeholder as a successful image
      // (Pitfall 3 / threat T-06-06). `isPlaceholder` is propagated out so
      // the in-mem Map write is gated symmetrically with the IDB write — a
      // placeholder must poison NEITHER cache tier.
      const note = resp.headers.get("X-Image-Proxy-Note");
      const blob = await resp.blob();
      const tex = await buildFromBlob(blob);
      if (!note) idbSaveBlob(originalUrl, blob); // fire-and-forget; never the placeholder
      return { tex, isPlaceholder: !!note };
    };

    let tex = null, isPlaceholder = false;
    try { ({ tex, isPlaceholder } = await tryFetch(toProxy(originalUrl))); }
    catch (_proxyErr) {
      try { ({ tex, isPlaceholder } = await tryFetch(originalUrl)); }
      catch (_directErr) { tex = null; isPlaceholder = false; }
    }
    // The placeholder tex is still returned (painted once so the sprite
    // resolves), but it is NOT retained in the in-mem Map — a later
    // loadAndCacheImage(sameUrl) re-attempts the real upstream rather than
    // short-circuiting on a poisoned memHit (matches the IDB guard above).
    if (tex && !isPlaceholder) _textureCache.set(originalUrl, tex);
    return tex;
  }

  // REAL-02 — camera auto-framing (consume-only: never recomputes
  // root_position/bounding_radius — D10/A2). `_userInteracted` flips true the
  // moment the user drags/zooms the OrbitControls; this suppresses the
  // scan-end auto-frame tween once the user is actively navigating a root
  // that's already in view (UI-SPEC REAL-02 — both conditions required).
  let _userInteracted = false;
  if (controls && typeof controls.addEventListener === "function") {
    controls.addEventListener("start", () => { _userInteracted = true; });
  }
  let _newestUrl = null;          // url → bookkeeping for the scan-end auto-frame target
  let _cameraTween = null;        // { t, dur, camStart, tgtStart, camEnd, tgtEnd }

  // REAL-01/REAL-02 — ray-constrained force-directed layout state (closure-
  // local, NOT `this.*` — fe/ has no class+mixin shape, port the algorithm
  // only). D10: backend computes root_position/bounding_radius/UMAP fit; this
  // closure only consumes them and slides nodes along their own backend-seeded
  // rays (the ONE permitted client-side animation math).
  const _urlRootPositions = new Map();   // url → THREE.Vector3
  const _urlBoundingRadii = new Map();   // url → number
  let _umapLayoutActive = false;         // true once a real frame w/ roots has landed
  const _nodeRayData = new Map();        // nodeId → { rayDir:Vector3(unit), radius, rootPos:Vector3 }
  const _positions = new Map();          // nodeId → THREE.Vector3 (current animate-loop world position)

  // _computeRayData() — derive each chunk's ray (root → initial UMAP position)
  // via the pure computeRayDir export. Mirrors cp/force_layout.js lines
  // 106-145 verbatim, INCLUDING the defensive root-not-yet-placed fallback to
  // the origin (lines 117-126) — do NOT optimize it away (RESEARCH Open Q3).
  function _computeRayData() {
    _nodeRayData.clear();
    const ids = Object.keys(_coords || {});
    for (const id of ids) {
      const p = _coords[id] || [0, 0, 0];
      const umapPos = [+p[0] || 0, +p[1] || 0, +p[2] || 0];
      const url = (_coords[id] && _coords[id].url) || "";
      let rootVec = _urlRootPositions.get(url);
      if (!rootVec) {
        // URL root not yet placed — defensive fallback to origin (verbatim
        // port of cp/ lines 117-126; cheap, prevents NaN/crash if url_roots
        // is momentarily behind coords in a frame).
        rootVec = new THREE.Vector3(0, 0, 0);
        _urlRootPositions.set(url, rootVec.clone());
      }
      const rootPos = [rootVec.x, rootVec.y, rootVec.z];
      const { dir, radius } = computeRayDir(rootPos, umapPos);
      _nodeRayData.set(id, { rayDir: new THREE.Vector3(dir[0], dir[1], dir[2]), radius, rootPos: rootVec.clone() });
      _positions.set(id, new THREE.Vector3(umapPos[0], umapPos[1], umapPos[2]));
    }
  }

  // _stepForceDirected(dt) — per-animate-frame ray-constrained collider
  // repulsion, ported from cp/force_layout.js::_stepForceDirected (lines
  // 155-200+). Early-return guards verbatim. Pairwise repulsion accumulates
  // radial deltas via the pure colliderRadialForce helper; DAMPING scales the
  // per-frame correction; radius clamps >= 0.5; reposition along
  // rootPos + rayDir*radius, written into both _positions and the THREE
  // points geometry position attribute.
  function _stepForceDirected(dt) {
    if (!_umapLayoutActive || _nodeRayData.size === 0) return;
    const ids = [..._nodeRayData.keys()];
    if (ids.length < 2) return;

    const radialForces = new Map();
    ids.forEach((id) => radialForces.set(id, 0));

    for (let a = 0; a < ids.length; a++) {
      for (let b = a + 1; b < ids.length; b++) {
        const idA = ids[a], idB = ids[b];
        const rdA = _nodeRayData.get(idA), rdB = _nodeRayData.get(idB);
        const posA = _positions.get(idA), posB = _positions.get(idB);
        const { forceA, forceB } = colliderRadialForce(
          [posA.x, posA.y, posA.z], [posB.x, posB.y, posB.z],
          [rdA.rayDir.x, rdA.rayDir.y, rdA.rayDir.z], [rdB.rayDir.x, rdB.rayDir.y, rdB.rayDir.z],
        );
        radialForces.set(idA, radialForces.get(idA) + forceA);
        radialForces.set(idB, radialForces.get(idB) + forceB);
      }
    }

    let moved = 0;
    radialForces.forEach((deltaR, id) => {
      if (Math.abs(deltaR) < 0.001) return;
      const rd = _nodeRayData.get(id);
      rd.radius = Math.max(0.5, rd.radius + deltaR * DAMPING);
      const newPos = rd.rootPos.clone().add(rd.rayDir.clone().multiplyScalar(rd.radius));
      _positions.set(id, newPos);
      moved++;
    });

    if (moved > 0 && points) {
      const ids2 = Object.keys(_coords || {});
      const attr = points.geometry.attributes.position;
      ids2.forEach((id, i) => {
        const pos = _positions.get(id);
        if (!pos) return;
        attr.array[i * 3] = pos.x; attr.array[i * 3 + 1] = pos.y; attr.array[i * 3 + 2] = pos.z;
      });
      attr.needsUpdate = true;
    }
  }

  // _isRootInFrustum(url) — NDC z-range check (the same off-frustum test
  // `project()` already uses for the halo's ray-transport) on a URL's root
  // position. Used ONLY to decide whether to suppress the scan-end
  // auto-frame tween (REAL-02 — suppressed when the user has interacted AND
  // the root is already in view); never used to gate rendering itself.
  function _isRootInFrustum(url) {
    const rootVec = _urlRootPositions.get(url);
    if (!rootVec) return false;
    const v = rootVec.clone().project(camera);
    return v.z >= -1 && v.z <= 1 && v.x >= -1 && v.x <= 1 && v.y >= -1 && v.y <= 1;
  }

  // frameCameraToRoot(url) — REAL-02 scan-end camera auto-frame. Tweens the
  // camera position + OrbitControls target to frame the given URL's root
  // over ~600ms with a cubic ease (ported from cp/animation.js
  // flyToNode/_stepCameraTween, lines 205-268/325-335). Interruptible: a new
  // call simply replaces the in-flight tween's start point with the
  // camera's CURRENT (possibly mid-tween) position. Suppressed by the
  // caller (setNodes) when the user has interacted AND the root is already
  // in frustum — this function itself always tweens once invoked.
  function frameCameraToRoot(url) {
    if (!controls) return false;
    const rootVec = _urlRootPositions.get(url);
    if (!rootVec) return false;
    const boundingRadius = _urlBoundingRadii.get(url) || 0;
    // Viewing distance: frame the root's bounding sphere with a little
    // headroom, mirroring flyToNode's "base distance, never below a floor"
    // shape (cp/animation.js lines 243-248).
    const viewDist = Math.max(12, boundingRadius * 2.2);
    const curTarget = controls.target.clone();
    const curCam = camera.position.clone();
    const dir = curCam.clone().sub(curTarget);
    if (dir.lengthSq() < 1e-6) dir.set(0, 0.4, 1);
    dir.normalize().multiplyScalar(viewDist);
    const camEnd = rootVec.clone().add(dir);
    const tgtEnd = rootVec.clone();
    _cameraTween = {
      t: 0, dur: 0.6,
      camStart: camera.position.clone(),
      tgtStart: controls.target.clone(),
      camEnd, tgtEnd,
    };
    return true;
  }

  // flyToNode(nodeId) — STEP-01 (§O.6/§O.7/§O.11): the node-id-keyed sibling
  // of frameCameraToRoot(url). Swaps `_urlRootPositions.get(url)` for
  // `nodeWorldPosition(nodeId)` (the SAME per-frame Map lookup
  // drawConcept3DLinks already uses) and builds the IDENTICAL `_cameraTween`
  // record shape, so it shares the existing interruptible cubic ease
  // (`_stepCameraTween`, below) VERBATIM — never a new easing curve. Framing
  // distance reuses frameCameraToRoot's own "base distance, never below a
  // floor" heuristic (cp/animation.js's flyToNode lines 243-248): a node has
  // no per-node bounding radius, so the floor alone (no radius term) frames
  // it at a fixed comfortable distance. Returns false (no-op) if the node's
  // world position is unknown — never throws.
  function flyToNode(nodeId) {
    if (!controls) return false;
    const nodeVec = nodeWorldPosition(nodeId);
    if (!nodeVec) return false;
    const viewDist = 12; // the same floor frameCameraToRoot uses when boundingRadius is 0
    const curTarget = controls.target.clone();
    const curCam = camera.position.clone();
    const dir = curCam.clone().sub(curTarget);
    if (dir.lengthSq() < 1e-6) dir.set(0, 0.4, 1);
    dir.normalize().multiplyScalar(viewDist);
    const camEnd = nodeVec.clone().add(dir);
    const tgtEnd = nodeVec.clone();
    _cameraTween = {
      t: 0, dur: 0.6,
      camStart: camera.position.clone(),
      tgtStart: controls.target.clone(),
      camEnd, tgtEnd,
    };
    return true;
  }

  // _stepCameraTween(dt) — per-animate-frame cubic ease-in-out lerp, ported
  // verbatim from cp/animation.js::_stepCameraTween (lines 325-335).
  function _stepCameraTween(dt) {
    if (!_cameraTween) return;
    const tw = _cameraTween;
    tw.t += dt;
    const u = Math.min(1, tw.t / tw.dur);
    const e = u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
    camera.position.lerpVectors(tw.camStart, tw.camEnd, e);
    if (controls) controls.target.lerpVectors(tw.tgtStart, tw.tgtEnd, e);
    if (u >= 1) _cameraTween = null;
  }

  // _applyCameraBounds() — REAL-02 per-frame adaptive orbit bounds, ported
  // verbatim from cp/animation.js lines 753-798 (UI-SPEC-locked multipliers):
  //   minDistance = 0.6 × cluster_radius (largest URL bounding_radius seen)
  //   maxDistance = 3.0 × max(|pos|) over every CURRENT node world position
  // Consumes only backend-resolved bounding_radius/positions — never
  // recomputes placement (D10/A2).
  function _applyCameraBounds() {
    if (!controls) return;
    let maxAbsPos = 0;
    _positions.forEach((p) => {
      const r = Math.sqrt(p.x * p.x + p.y * p.y + p.z * p.z);
      if (r > maxAbsPos) maxAbsPos = r;
    });
    let clusterRadius = 0;
    _urlBoundingRadii.forEach((r) => { if (r > clusterRadius) clusterRadius = r; });
    const wantMax = Math.max(60, maxAbsPos * 3.0);
    const wantMin = Math.max(2, clusterRadius * 0.6);
    controls.maxDistance = wantMax;
    controls.minDistance = wantMin;
  }

  // setNodes(coords, urlRoots) — REAL-02: consume (never recompute) the
  // backend's url_roots. For each url, store root_position/bounding_radius;
  // then re-derive ray data (_computeRayData) and seed _positions from the
  // UMAP coords. The second arg is OPTIONAL — the existing single-arg call
  // path (and the WS `setNodes(f.coords)` call) stays backward compatible.
  function setNodes(coords, urlRoots) {
    _coords = coords || {};
    if (urlRoots) _lastUrlRoots = urlRoots; // remember for lastRoots()/__mm_rerender
    // Dispose BOTH the geometry AND the material of the prior points object —
    // THREE does not GC GPU programs/uniforms without an explicit .dispose().
    // setNodes runs per umap_canonical WS frame + per __mm_rerender, so a
    // leaked PointsMaterial accumulates over a long session (WR-01).
    if (points) { scene.remove(points); points.geometry.dispose(); points.material.dispose(); }
    const { positions, colors, count } = buildPointArrays(_coords, { azimuth: azimuth() });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    points = new THREE.Points(geo, new THREE.PointsMaterial({ size: 2.6, vertexColors: true }));
    scene.add(points);
    _lastColorAz = azimuth();
    _applyHighlightOverlay(); // STEP-01 — re-apply any active highlight on the fresh colour buffer
    if (urlRoots) {
      const newUrls = [];
      for (const url in urlRoots) {
        if (!_urlRootPositions.has(url)) newUrls.push(url); // first time we've seen this URL's root
        const entry = urlRoots[url] || {};
        const rp = entry.root_position || [0, 0, 0];
        _urlRootPositions.set(url, new THREE.Vector3(+rp[0] || 0, +rp[1] || 0, +rp[2] || 0));
        _urlBoundingRadii.set(url, +entry.bounding_radius || 0);
      }
      _computeRayData();
      _umapLayoutActive = _nodeRayData.size > 0;
      // REAL-02 — scan-end camera auto-frame: tween to the newest URL's
      // root, UNLESS the user has interacted with the camera AND that root
      // is already in frustum (both conditions required — UI-SPEC).
      if (newUrls.length) {
        _newestUrl = newUrls[newUrls.length - 1];
        const suppress = _userInteracted && _isRootInFrustum(_newestUrl);
        if (!suppress) frameCameraToRoot(_newestUrl);
      }
    }
    return count;
  }

  // nodePositions() — read accessor for the current animate-loop world
  // positions (post force-step). Exposed so editor.html's
  // window.__mm_proj_node_positions test hook can read closure-internal state
  // without leaking the Maps themselves.
  function nodePositions() {
    return [..._positions.entries()].map(([id, v]) => ({ id, x: v.x, y: v.y, z: v.z }));
  }
  // lastCoords()/lastRoots() — the most recent setNodes() arguments, exposed
  // so editor.html's window.__mm_rerender can re-invoke setNodes with the
  // SAME frame (re-deriving the render from already-known state, never
  // re-fetching) — proving a re-render reuses cached image textures with
  // zero new network requests (REAL-03).
  function lastCoords() { return _coords; }
  function lastRoots() { return _lastUrlRoots; }
  // netFetchCount() — the number of REAL network fetch() calls the image
  // loader has issued since boot (test hook for the no-new-request-on-
  // re-render assertion).
  function netFetchCount() { return _netFetchCount; }

  // REAL-03 — image billboard sprites. `_imageSprites` is keyed by chunk id
  // (one THREE.Sprite per image-bearing chunk); `_chunkImageUrl` remembers
  // which URL each chunk currently renders so a re-render of the SAME chunk
  // at the SAME URL reuses the existing sprite/texture instead of refetching
  // (textures persist for the layout lifetime — UI-SPEC). Two chunks at the
  // SAME url share ONE THREE.Texture instance via `_textureCache` above
  // (single GPU upload) but each gets its OWN Sprite (own position/scale).
  const _imageSprites = new Map();   // chunkId → THREE.Sprite
  const _chunkImageUrl = new Map();  // chunkId → url (last spawned from)

  // spawnImageBillboards(imageMap) — imageMap: { chunkId: imageUrl }. Image
  // URLs are NOT carried by the production umap_canonical frame today (no
  // image-URL field on build_umap_canonical — confirmed by grep); this is an
  // explicit caller-supplied map (the __mm_proj_image test hook, or — once a
  // future frame field exists — whatever extracts it upstream). Group by URL
  // first so two chunks at one URL resolve to ONE loadAndCacheImage() call
  // and share the returned texture (no duplicate GPU upload); each chunk
  // still gets its own Sprite positioned at its OWN current _positions world
  // position, participating in the SAME _positions/_nodeRayData bookkeeping
  // the force step uses (shared NODE_RADIUS=0.9 collider, no separate
  // spacing constant for image nodes).
  function spawnImageBillboards(imageMap) {
    if (!imageMap) return;
    const byUrl = new Map(); // url → [chunkId, ...]
    for (const chunkId in imageMap) {
      const url = imageMap[chunkId];
      if (!url) continue;
      if (_chunkImageUrl.get(chunkId) === url && _imageSprites.has(chunkId)) continue; // already spawned, reuse
      let arr = byUrl.get(url);
      if (!arr) { arr = []; byUrl.set(url, arr); }
      arr.push(chunkId);
    }
    byUrl.forEach((chunkIds, url) => {
      loadAndCacheImage(url).then((tex) => {
        if (!tex) return;
        const img = tex.image || {};
        const iw = img.width || 1, ih = img.height || 1;
        const aspect = (iw > 0 && ih > 0) ? iw / ih : 1;
        chunkIds.forEach((chunkId, idx) => {
          // a chunk may have been removed from the scene while the fetch
          // was in flight — skip stale spawns defensively.
          const pos = _positions.get(chunkId);
          if (!pos) return;
          const isPrimary = idx === 0;
          const baseSize = isPrimary ? 1.0 : 0.55;
          const material = new THREE.SpriteMaterial({ map: tex, transparent: true });
          const sprite = new THREE.Sprite(material);
          if (aspect >= 1) sprite.scale.set(baseSize * aspect, baseSize, 1);
          else sprite.scale.set(baseSize, baseSize / aspect, 1);
          sprite.position.copy(pos);
          // existing sprite for this chunk (e.g. a prior URL) is replaced —
          // dispose its material only (the shared Texture itself is NOT
          // disposed; other sprites/chunks may still reference it).
          const prior = _imageSprites.get(chunkId);
          if (prior) { scene.remove(prior); prior.material.dispose(); }
          scene.add(sprite);
          _imageSprites.set(chunkId, sprite);
          _chunkImageUrl.set(chunkId, url);
        });
      }).catch(() => { /* loadAndCacheImage already resolves null on failure; defensive only */ });
    });
  }

  // _syncImageSpritePositions() — keep every image sprite glued to its
  // chunk's current animate-loop world position (post force-step), mirroring
  // how the THREE.Points buffer attribute is kept in sync in
  // _stepForceDirected. Cheap (Map iteration + Vector3 copy); run every
  // animate() frame so a sprite never visibly lags behind its collider-moved
  // node.
  function _syncImageSpritePositions() {
    if (_imageSprites.size === 0) return;
    _imageSprites.forEach((sprite, chunkId) => {
      const pos = _positions.get(chunkId);
      if (pos) sprite.position.copy(pos);
    });
  }

  // REAL-04 — solid headless 2D↔3D link arrow. Port of
  // cp/concept_graph.js::_drawConcept3DLinks (lines 5479-5578), closure-
  // scoped (no `this.*`). For every DOM element carrying [data-3d-node-id],
  // project its CURRENT world position (post force-step, so the line tracks
  // the moving node) through the camera via the SAME project() helper the
  // halo's ray-transport uses (no parallel NDC→px conversion), and draw/hide
  // a solid <line> in `svgHost`. Off-frustum hide tests the TRUE [-1,1] NDC
  // z-range (project()'s new `ndcZ` field) — NOT the weaker near/far-only
  // `inFront` flag. The line is `#ffd700` (--accent-arrow, the ONLY yellow
  // in the app), stroke-width 2, NO stroke-dasharray (solid), and
  // `removeAttribute('marker-end')` (headless — no arrowheads). Cached per
  // card via a WeakMap so frames update rather than recreate the element.
  const _cardLines = new WeakMap(); // card element → <line> element
  function drawConcept3DLinks(svgHost) {
    if (!svgHost) return;
    const cards = document.querySelectorAll("[data-3d-node-id]");
    if (!cards.length) {
      // T-06-09/T-06-10 — nothing to draw: wipe stale lines, cheap early-out.
      const stale = svgHost.querySelectorAll("line");
      stale.forEach((el) => el.parentNode.removeChild(el));
      return;
    }
    const canvas = renderer && renderer.domElement;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    cards.forEach((card) => {
      const nodeId = card.getAttribute("data-3d-node-id");
      const worldPos = nodeId ? nodeWorldPosition(nodeId) : null;
      if (!worldPos) {
        // T-06-09 — a data-3d-node-id pointing at a non-existent node: skip/
        // hide this card's line (port of cp/'s `if (!worldPos) return` guard).
        const existing = _cardLines.get(card);
        if (existing) existing.setAttribute("visibility", "hidden");
        return;
      }
      const p = project(worldPos.x, worldPos.y, worldPos.z);
      // Off-frustum hide: the TRUE [-1,1] NDC test on ALL three axes (NOT the
      // near/far-only `inFront` flag) — matching _isRootInFrustum's symmetric
      // x/y/z check. WR-04: the depth-only test let a node in front of the
      // camera but far to the side or above/below the viewport (NDC x or y
      // outside [-1,1]) still draw an arrow to an off-canvas point. The
      // solid/headless/no-dasharray styling below is unchanged.
      if (p.ndcZ < -1 || p.ndcZ > 1 || p.ndcX < -1 || p.ndcX > 1 || p.ndcY < -1 || p.ndcY > 1) {
        const existing = _cardLines.get(card);
        if (existing) existing.setAttribute("visibility", "hidden");
        return;
      }
      // project() already returns CSS px relative to the CANVAS rect (its
      // w()/h() are canvas.clientWidth/clientHeight) — but the canvas itself
      // may not be at (0,0) in the viewport, so offset by the canvas rect's
      // own top/left (Pitfall 4 — canvas-relative, not window.innerWidth).
      const x2 = rect.left + p.x;
      const y2 = rect.top + p.y;
      // nearest card-edge anchor toward the projected point (verbatim port).
      const cr = card.getBoundingClientRect();
      const cx = cr.left + cr.width / 2;
      const cy = cr.top + cr.height / 2;
      const dx = x2 - cx, dy = y2 - cy;
      let x1, y1;
      if (Math.abs(dx) * cr.height >= Math.abs(dy) * cr.width && dx !== 0) {
        x1 = dx >= 0 ? cr.right : cr.left;
        const t = (x1 - cx) / dx;
        y1 = cy + dy * t;
      } else if (dy !== 0) {
        y1 = dy >= 0 ? cr.bottom : cr.top;
        const t = (y1 - cy) / dy;
        x1 = cx + dx * t;
      } else {
        x1 = cx; y1 = cy;
      }
      let line = _cardLines.get(card);
      if (!line) {
        line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("stroke", "#ffd700");        // --accent-arrow, the ONLY yellow permitted
        line.setAttribute("stroke-width", "2");
        line.setAttribute("stroke-opacity", "0.85");
        // Solid — no dasharray (hard project-wide rule, T-06-11).
        line.removeAttribute("marker-end");             // headless connector — no arrowheads
        svgHost.appendChild(line);
        _cardLines.set(card, line);
      }
      line.setAttribute("visibility", "visible");
      line.setAttribute("x1", x1);
      line.setAttribute("y1", y1);
      line.setAttribute("x2", x2);
      line.setAttribute("y2", y2);
    });
  }

  // HALO-03 — cone-ray transport render (§O.18 / D-04). `_lastConePositions`
  // backs the `window.__mm_cone_positions` test hook (mirrors the existing
  // `nodePositions`/`__mm_proj_node_positions` pattern). Cleared to an empty
  // array on boot so the hook always returns SOMETHING before any halo opens.
  let _lastConePositions = [];
  function conePositions() { return _lastConePositions; }

  // placeHaloCandidates(apex, candidates) — RENDER-only consumer of
  // halo_cone.mjs's pure geometry. `apex` is the focal's live world position
  // ({x,y,z}); `candidates` is the retrieval queue
  // ([{id, label, transport:{similarity,radial,along_ray}}, ...]) from
  // `/apparitions?transport=1`. Delegates ALL placement math to
  // `placeCandidatesOnCone` (D10 — this function never recomputes
  // similarity/distance); it only WRITES the returned positions into the
  // existing `_positions` bookkeeping + the live points-geometry buffer, so
  // each transported node keeps its EXISTING HSV/image-billboard identity
  // (the projector exception zone, UI-SPEC) — it is the SAME node, just
  // moved. Candidates with no 3D backing (the halo_cone 2D fallback) are
  // recorded in `_lastConePositions` for the test hook but have no points-
  // buffer entry to move (they render via the existing 2D haloVDom overlay,
  // unchanged). Any cone ray drawn in 3D must reuse `drawConcept3DLinks`'s
  // no-dasharray/headless idiom (SOLID only) — this function draws no lines
  // itself; a future caller wiring cone rays into `svgHost` does so via that
  // SAME helper, never a new dashed-line path.
  function placeHaloCandidates(apex, candidates) {
    const projectFns = { project, azimuth, nodeWorldPosition };
    const placed = placeCandidatesOnCone(apex, candidates, projectFns);
    const ids2 = Object.keys(_coords || {});
    const idIndex = new Map(ids2.map((id, i) => [id, i]));
    const attr = points ? points.geometry.attributes.position : null;
    for (const p of placed) {
      if (!p.hasBacking) continue; // 2D-fallback candidate — nothing to move in the points buffer
      const newPos = new THREE.Vector3(p.x, p.y, p.z);
      _positions.set(p.id, newPos);
      const i = idIndex.get(p.id);
      if (attr && i != null) {
        attr.array[i * 3] = p.x; attr.array[i * 3 + 1] = p.y; attr.array[i * 3 + 2] = p.z;
      }
      // keep an image billboard (if any) glued to the transported position —
      // mirrors _syncImageSpritePositions' Map-iteration/Vector3-copy idiom.
      const sprite = _imageSprites.get(p.id);
      if (sprite) sprite.position.copy(newPos);
    }
    if (attr) attr.needsUpdate = true;
    // `radial` is included alongside x/y/z because it is the apex-distance
    // scalar that is GUARANTEED monotonic in similarity (halo_cone.mjs's own
    // header comment + halo_cone.test.mjs Test 1) — raw Euclidean distance
    // from the apex is NOT, since radial/along_ray are orthogonal
    // components (a callers-beware note repeated here so e2e/consumer code
    // asserts ordering on `radial`, not `Math.hypot(x,y,z)`).
    _lastConePositions = placed.map((p) => ({
      id: p.id, x: p.x, y: p.y, z: p.z, similarity: p.similarity, radial: p.radial, alongRay: p.alongRay, hasBacking: !!p.hasBacking,
    }));
    return _lastConePositions;
  }

  // highlightNode(nodeId) / STEP-01 (§O.6/UI-SPEC Contract C, Assumption A5)
  // — outline-BRIGHTEN to --silver-300 (#b8c0c8 -> 0.7216,0.7529,0.7843),
  // applied to that ONE node's existing colour-buffer slot. NOT a new fill
  // colour (the silver-300 token is the existing accent-reserved
  // hover/focus affordance, never a new hue), NOT a pulse. CRITICAL (the
  // one-way + full-distribution invariant, D-03/§O.6): this NEVER hides,
  // removes, or subsets any other node — `_positions` and every other
  // node's colour slot stay untouched; only this one node's colour entry
  // changes. `_highlightedNodeId` is remembered so `recolor()`'s per-frame
  // HSV-rotation rebuild (which otherwise overwrites the WHOLE colour
  // buffer from `_coords`) re-applies the highlight on top, every frame —
  // the highlight survives camera orbit.
  const SILVER_300 = [0xb8 / 255, 0xc0 / 255, 0xc8 / 255];
  let _highlightedNodeId = null;
  function _applyHighlightOverlay() {
    if (!points || _highlightedNodeId == null) return;
    const ids = Object.keys(_coords || {});
    const i = ids.indexOf(_highlightedNodeId);
    if (i < 0) return;
    const attr = points.geometry.attributes.color;
    attr.array[i * 3] = SILVER_300[0];
    attr.array[i * 3 + 1] = SILVER_300[1];
    attr.array[i * 3 + 2] = SILVER_300[2];
    attr.needsUpdate = true;
  }
  function highlightNode(nodeId) {
    if (!nodeWorldPosition(nodeId)) return false;
    _highlightedNodeId = nodeId;
    _applyHighlightOverlay();
    return true;
  }

  // UMAP-01 — HSV rotates with camera azimuth: recolour the existing nodes when
  // the camera orbits (positions unchanged; only the hue field rotates).
  function recolor() {
    if (!points) return;
    const { colors } = buildPointArrays(_coords, { azimuth: azimuth() });
    const attr = points.geometry.attributes.color;
    attr.array.set(colors);
    attr.needsUpdate = true;
    _applyHighlightOverlay(); // re-apply on top — the highlight survives the per-frame HSV rebuild
  }
  function nodeColor(i = 0) {
    if (!points) return null;
    const c = points.geometry.attributes.color.array;
    return [c[i * 3], c[i * 3 + 1], c[i * 3 + 2]];
  }
  function nodeCount() { return points ? points.geometry.attributes.position.count : 0; }
  // project(x,y,z) → { x, y, inFront, ndcZ }. `inFront` is the legacy near/far-
  // only check (v.z < 1) the halo's ray-transport already relies on — kept
  // UNCHANGED for backward compatibility. `ndcZ` is the raw THREE NDC z (the
  // SAME value `v.z`), additive: REAL-04's off-frustum hide needs the TRUE
  // `[-1,1]` frustum test, which `inFront` alone cannot express (it only
  // rejects points beyond the far/near plane on one side).
  function project(x, y, z) {
    const v = new THREE.Vector3(x, y, z).project(camera);
    // ndcX/ndcY/ndcZ are the raw THREE NDC components; REAL-04's off-frustum
    // hide needs the TRUE [-1,1] frustum test on ALL three axes (matching
    // _isRootInFrustum), not just depth (WR-04). x/y stay the canvas-px
    // mapping the halo's ray-transport already consumes (unchanged).
    return { x: (v.x * 0.5 + 0.5) * w(), y: (-v.y * 0.5 + 0.5) * h(), inFront: v.z < 1, ndcX: v.x, ndcY: v.y, ndcZ: v.z };
  }
  // nodeWorldPosition(nodeId) — the current animate-loop world position
  // (post force-step) for a single node, or null if unknown. REAL-04's
  // drawConcept3DLinks reads this every frame so the arrow tracks the moving
  // node (mirrors cp/concept_graph.js::_getNodePosition usage).
  function nodeWorldPosition(nodeId) {
    return _positions.get(nodeId) || null;
  }
  // camera azimuth — the halo couples its ray angle to this so the rays update
  // as the user orbits the 3D scene (§V.4 "ray angle that updates as it's
  // traced between the sticked panel and the retrieved nodes in 3D GUI").
  function azimuth() { return Math.atan2(camera.position.x, camera.position.z); }
  function onFrame(cb) { _frameCbs.push(cb); }
  const _frameCbs = [];
  let raf = 0;
  function animate() {
    raf = requestAnimationFrame(animate);
    // REAL-02 — adaptive orbit bounds, recomputed every frame from the
    // backend's resolved roots/positions (never recomputed placement).
    _applyCameraBounds();
    // REAL-02 — scan-end camera auto-frame tween (cubic ease, ~600ms).
    _stepCameraTween(1 / 60);
    if (controls) controls.update();
    const az = azimuth();
    // UMAP-01 — recolour the node HSV field as the camera orbits (throttled).
    if (_lastColorAz === null || Math.abs(az - _lastColorAz) > 0.05) { _lastColorAz = az; recolor(); }
    // REAL-01 — ray-constrained collider step; slides nodes along their
    // backend-seeded rays only (no-op until the first frame w/ url_roots).
    _stepForceDirected();
    // REAL-03 — keep image billboards glued to their chunk's current
    // (possibly collider-moved) world position every frame.
    _syncImageSpritePositions();
    for (const cb of _frameCbs) { try { cb(az); } catch (e) { /* keep rendering */ } }
    renderer.render(scene, camera);
  }
  function resize() { camera.aspect = w() / h(); camera.updateProjectionMatrix(); renderer.setSize(w(), h(), false); }
  animate();
  window.addEventListener("resize", resize);
  // REAL-02 — adaptive resize: a ResizeObserver on the canvas itself, in
  // addition to the window 'resize' listener above, so the projector tracks
  // a shrinking/growing canvas even when the WINDOW dimensions don't change
  // (e.g. a side panel opening). No no-change guard (UI-SPEC "Adaptive
  // resize") — every observed resize re-runs setSize + updateProjectionMatrix.
  if (typeof ResizeObserver === "function") {
    const ro = new ResizeObserver(() => resize());
    ro.observe(canvas);
  }
  return {
    scene, camera, renderer, setNodes, nodeCount, nodeColor, recolor, project, azimuth, onFrame, resize,
    nodePositions, frameCameraToRoot, lastCoords, lastRoots,
    spawnImageBillboards, loadAndCacheImage, netFetchCount,
    nodeWorldPosition, drawConcept3DLinks,
    placeHaloCandidates, conePositions,
    flyToNode, highlightNode,
    stop: () => cancelAnimationFrame(raf),
  };
}

export default { buildPointArrays, createProjector };
