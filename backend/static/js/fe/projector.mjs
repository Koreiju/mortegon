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

  function setNodes(coords) {
    _coords = coords || {};
    if (points) { scene.remove(points); points.geometry.dispose(); }
    const { positions, colors, count } = buildPointArrays(_coords, { azimuth: azimuth() });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    points = new THREE.Points(geo, new THREE.PointsMaterial({ size: 2.6, vertexColors: true }));
    scene.add(points);
    _lastColorAz = azimuth();
    return count;
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
    for (const cb of _frameCbs) { try { cb(az); } catch (e) { /* keep rendering */ } }
    renderer.render(scene, camera);
  }
  function resize() { camera.aspect = w() / h(); camera.updateProjectionMatrix(); renderer.setSize(w(), h(), false); }
  animate();
  window.addEventListener("resize", resize);
  return { scene, camera, renderer, setNodes, nodeCount, nodeColor, recolor, project, azimuth, onFrame, resize, stop: () => cancelAnimationFrame(raf) };
}

export default { buildPointArrays, createProjector };
