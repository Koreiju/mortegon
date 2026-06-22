/**
 * projector.mjs — the fe/real 3D projector (minimal): renders every chunk as a
 * node at its UMAP position (from `/api/recompute_umap` → {chunk_id:[x,y,z]}),
 * so the editor has the 3D Real register the halo transports nodes from (O.18).
 *
 * `buildPointArrays` is PURE (coords → typed arrays + id order) and
 * unit-testable in Node; `project` (world→screen) and the THREE wiring are the
 * browser layer (window.THREE, loaded by editor.html).
 */

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

  // setNodes(coords, urlRoots) — REAL-02: consume (never recompute) the
  // backend's url_roots. For each url, store root_position/bounding_radius;
  // then re-derive ray data (_computeRayData) and seed _positions from the
  // UMAP coords. The second arg is OPTIONAL — the existing single-arg call
  // path (and the WS `setNodes(f.coords)` call) stays backward compatible.
  function setNodes(coords, urlRoots) {
    _coords = coords || {};
    if (points) { scene.remove(points); points.geometry.dispose(); }
    const { positions, colors, count } = buildPointArrays(_coords, { azimuth: azimuth() });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    points = new THREE.Points(geo, new THREE.PointsMaterial({ size: 2.6, vertexColors: true }));
    scene.add(points);
    _lastColorAz = azimuth();
    if (urlRoots) {
      for (const url in urlRoots) {
        const entry = urlRoots[url] || {};
        const rp = entry.root_position || [0, 0, 0];
        _urlRootPositions.set(url, new THREE.Vector3(+rp[0] || 0, +rp[1] || 0, +rp[2] || 0));
        _urlBoundingRadii.set(url, +entry.bounding_radius || 0);
      }
      _computeRayData();
      _umapLayoutActive = _nodeRayData.size > 0;
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
  // UMAP-01 — HSV rotates with camera azimuth: recolour the existing nodes when
  // the camera orbits (positions unchanged; only the hue field rotates).
  function recolor() {
    if (!points) return;
    const { colors } = buildPointArrays(_coords, { azimuth: azimuth() });
    const attr = points.geometry.attributes.color;
    attr.array.set(colors);
    attr.needsUpdate = true;
  }
  function nodeColor(i = 0) {
    if (!points) return null;
    const c = points.geometry.attributes.color.array;
    return [c[i * 3], c[i * 3 + 1], c[i * 3 + 2]];
  }
  function nodeCount() { return points ? points.geometry.attributes.position.count : 0; }
  function project(x, y, z) {
    const v = new THREE.Vector3(x, y, z).project(camera);
    return { x: (v.x * 0.5 + 0.5) * w(), y: (-v.y * 0.5 + 0.5) * h(), inFront: v.z < 1 };
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
    if (controls) controls.update();
    const az = azimuth();
    // UMAP-01 — recolour the node HSV field as the camera orbits (throttled).
    if (_lastColorAz === null || Math.abs(az - _lastColorAz) > 0.05) { _lastColorAz = az; recolor(); }
    // REAL-01 — ray-constrained collider step; slides nodes along their
    // backend-seeded rays only (no-op until the first frame w/ url_roots).
    _stepForceDirected();
    for (const cb of _frameCbs) { try { cb(az); } catch (e) { /* keep rendering */ } }
    renderer.render(scene, camera);
  }
  function resize() { camera.aspect = w() / h(); camera.updateProjectionMatrix(); renderer.setSize(w(), h(), false); }
  animate();
  window.addEventListener("resize", resize);
  return { scene, camera, renderer, setNodes, nodeCount, nodeColor, recolor, project, azimuth, onFrame, resize, nodePositions, stop: () => cancelAnimationFrame(raf) };
}

export default { buildPointArrays, createProjector };
