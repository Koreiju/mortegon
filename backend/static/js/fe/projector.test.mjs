/**
 * projector.test.mjs — the pure part of the fe/real projector.
 * Run: node backend/static/js/fe/projector.test.mjs
 */
import assert from "node:assert";

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log("  PASS  " + name); passed++; }
  catch (e) { console.log("  FAIL  " + name + ": " + e.message); failed++; }
}

// WR-2 (teeth) — `createProjector` requires `window.THREE` + a real canvas
// (it is otherwise only exercised by Playwright e2e). A minimal fake THREE
// shim, covering exactly the API surface `createProjector` touches, lets
// `placeHaloCandidates` run as a genuine Node unit test rather than a
// regression-only re-check of the pre-existing pure exports. This shim is
// installed BEFORE importing projector.mjs (createProjector reads
// `window.THREE` at CALL time, not at import time, so a plain top-level
// `global.window` assignment before the dynamic import below suffices).
class FakeVector3 {
  constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; }
  set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; }
  clone() { return new FakeVector3(this.x, this.y, this.z); }
  copy(v) { this.x = v.x; this.y = v.y; this.z = v.z; return this; }
  add(v) { this.x += v.x; this.y += v.y; this.z += v.z; return this; }
  sub(v) { this.x -= v.x; this.y -= v.y; this.z -= v.z; return this; }
  multiplyScalar(s) { this.x *= s; this.y *= s; this.z *= s; return this; }
  normalize() {
    const len = Math.hypot(this.x, this.y, this.z) || 1;
    this.x /= len; this.y /= len; this.z /= len; return this;
  }
  lengthSq() { return this.x * this.x + this.y * this.y + this.z * this.z; }
  lerpVectors(a, b, t) {
    this.x = a.x + (b.x - a.x) * t; this.y = a.y + (b.y - a.y) * t; this.z = a.z + (b.z - a.z) * t; return this;
  }
  // project(camera) — the only camera-projection behavior createProjector's
  // `project()` needs from a real THREE.Vector3; returns NDC-like coords
  // deterministically derived from world position (good enough for a unit
  // test that never asserts exact screen pixels, only id/position bookkeeping).
  project() { return { x: this.x / 100, y: this.y / 100, z: 0 }; }
}
class FakeBufferAttribute { constructor(array, itemSize) { this.array = array; this.itemSize = itemSize; this.needsUpdate = false; } }
class FakeBufferGeometry {
  constructor() { this.attributes = {}; }
  setAttribute(name, attr) { this.attributes[name] = attr; return this; }
  dispose() {}
}
class FakePoints { constructor(geo, mat) { this.geometry = geo; this.material = mat; } }
class FakePointsMaterial { dispose() {} }
class FakeScene { constructor() { this.children = []; } add(o) { this.children.push(o); } remove(o) { this.children = this.children.filter((c) => c !== o); } }
class FakeColor { constructor() {} }
class FakeCamera { constructor() { this.position = new FakeVector3(0, 0, 140); this.aspect = 1; } updateProjectionMatrix() {} }
class FakeRenderer { constructor() { this.domElement = {}; } setSize() {} render() {} }
class FakeSpriteMaterial { constructor(opts) { Object.assign(this, opts); } dispose() {} }
class FakeSprite { constructor(mat) { this.material = mat; this.position = new FakeVector3(); this.scale = { set() {} }; } }

global.window = global.window || {};
global.window.THREE = {
  Vector3: FakeVector3,
  BufferAttribute: FakeBufferAttribute,
  BufferGeometry: FakeBufferGeometry,
  Points: FakePoints,
  PointsMaterial: FakePointsMaterial,
  Scene: FakeScene,
  Color: FakeColor,
  PerspectiveCamera: FakeCamera,
  WebGLRenderer: FakeRenderer,
  SpriteMaterial: FakeSpriteMaterial,
  Sprite: FakeSprite,
  TextureLoader: class { load() {} },
};
global.window.addEventListener = () => {};
global.requestAnimationFrame = global.requestAnimationFrame || (() => 0);
global.cancelAnimationFrame = global.cancelAnimationFrame || (() => {});

const { buildPointArrays, computeRayDir, colliderRadialForce, MIN_SEPARATION, COLLIDER_SAFETY, createProjector } =
  await import("./projector.mjs");

function fakeCanvas() {
  return { clientWidth: 800, clientHeight: 600, width: 800, height: 600, getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 600 }) };
}

test("buildPointArrays: one xyz triple per chunk, in id order", () => {
  const coords = { a: [1, 2, 3], b: [4, 5, 6], c: [-1, 0, 9] };
  const r = buildPointArrays(coords);
  assert.deepStrictEqual(r.ids, ["a", "b", "c"]);
  assert.strictEqual(r.count, 3);
  assert.strictEqual(r.positions.length, 9);
  assert.deepStrictEqual([...r.positions.slice(0, 3)], [1, 2, 3]);
  assert.deepStrictEqual([...r.positions.slice(3, 6)], [4, 5, 6]);
});

test("buildPointArrays: a colour per node (HSV sweep), in [0,1]", () => {
  const r = buildPointArrays({ a: [0, 0, 0], b: [1, 1, 1] });
  assert.strictEqual(r.colors.length, 6);
  for (const c of r.colors) assert.ok(c >= 0 && c <= 1, "rgb in [0,1]");
});

// approx-equal for Float32Array channels (32-bit rounding).
const near = (a, b, eps = 1e-5) => assert.ok(Math.abs(a - b) < eps, `${a} ≈ ${b}`);

// UMAP-01 — the projector RENDERS the backend's 6D HSV (it does not invent it).
test("buildPointArrays: a 6-vector renders the FRAME hsv (not the sweep)", () => {
  // pass-through converter so the colours ARE the (h,s,l) fed to setHSL
  const r = buildPointArrays({ a: [1, 2, 3, 0.42, 0.8, 0.4] }, { hslToRgb: (h, s, l) => [h, s, l] });
  assert.deepStrictEqual([...r.positions], [1, 2, 3]);
  near(r.colors[0], 0.42); near(r.colors[1], 0.8); near(r.colors[2], 0.4); // colour = p[3..5]
});

test("buildPointArrays: camera azimuth rotates the hue (UMAP-01)", () => {
  const id = (h, s, l) => [h, s, l];
  const a0 = buildPointArrays({ a: [0, 0, 0, 0.1, 1, 0.5] }, { hslToRgb: id, azimuth: 0 });
  const a1 = buildPointArrays({ a: [0, 0, 0, 0.1, 1, 0.5] }, { hslToRgb: id, azimuth: Math.PI }); // offset 0.5
  near(a0.colors[0], 0.1);                         // no azimuth → frame hue
  near(a1.colors[0], 0.6);                         // azimuth π → hue + 0.5
  near(a1.colors[1], 1); near(a1.colors[2], 0.5);  // s,l unchanged by azimuth
});

test("buildPointArrays: a 3-vector keeps the positional sweep (backward compatible)", () => {
  const r = buildPointArrays({ a: [0, 0, 0], b: [1, 1, 1] }, { hslToRgb: (h, s, l) => [h, s, l] });
  near(r.colors[0], 0); near(r.colors[1], 0.7); near(r.colors[2], 0.6);   // node 0: hue i/n=0
  near(r.colors[3], 0.5); near(r.colors[4], 0.7); near(r.colors[5], 0.6); // node 1: hue i/n=1/2
});

test("buildPointArrays: empty coords → empty arrays (no crash)", () => {
  const r = buildPointArrays({});
  assert.strictEqual(r.count, 0);
  assert.strictEqual(r.positions.length, 0);
});

test("buildPointArrays: coerces missing/garbage coords to 0", () => {
  const r = buildPointArrays({ a: [null, "x", 5] });
  assert.deepStrictEqual([...r.positions], [0, 0, 5]);
});

// REAL-01 — ray-math (computeRayDir) and collider-force (colliderRadialForce)
// pure unit tests. COLLIDER_SAFETY must be the SHIPPED value 1.4 (UI-SPEC A1),
// never the doc's 2.0 — MIN_SEPARATION must evaluate to 2.52.

test("COLLIDER_SAFETY is the shipped value 1.4 (not the doc's 2.0); MIN_SEPARATION = 2.52", () => {
  near(COLLIDER_SAFETY, 1.4);
  near(MIN_SEPARATION, 2.52);
});

test("computeRayDir: simple axis-aligned ray, unit dir + correct radius", () => {
  const r = computeRayDir([0, 0, 0], [3, 0, 0]);
  assert.deepStrictEqual(r.dir, [1, 0, 0]);
  near(r.radius, 3);
});

test("computeRayDir: degenerate (node sits on root) → arbitrary unit ray, radius 0", () => {
  const r = computeRayDir([1, 2, 3], [1, 2, 3]);
  assert.deepStrictEqual(r.dir, [1, 0, 0]);
  assert.strictEqual(r.radius, 0);
});

test("computeRayDir: returned dir is unit length for non-degenerate input", () => {
  const r = computeRayDir([1, 1, 1], [4, 5, 7]);
  const len = Math.hypot(r.dir[0], r.dir[1], r.dir[2]);
  near(len, 1, 1e-6);
  near(r.radius, Math.hypot(3, 4, 6));
});

test("colliderRadialForce: two nodes below MIN_SEPARATION produce equal-and-opposite radial pushes", () => {
  // two nodes 1.0 apart along the x-axis, each riding its own ray along +x.
  const posA = [0, 0, 0], posB = [1, 0, 0];
  const rayDirA = [1, 0, 0], rayDirB = [1, 0, 0];
  const { forceA, forceB } = colliderRadialForce(posA, posB, rayDirA, rayDirB);
  assert.notStrictEqual(forceA, 0);
  assert.notStrictEqual(forceB, 0);
  // pushTotal = (2.52 - 1) * 0.5 = 0.76; dotA = -1 (sep is +x, rayDirA is +x → -1*0.76);
  // dotB = +1 (sep is +x, rayDirB is +x → +1*0.76). Equal magnitude, opposite sign.
  near(forceA, -0.76);
  near(forceB, 0.76);
  near(Math.abs(forceA), Math.abs(forceB));
});

test("colliderRadialForce: two nodes at/above MIN_SEPARATION produce zero push (hard floor, no falloff)", () => {
  const posA = [0, 0, 0], posB = [MIN_SEPARATION, 0, 0];
  const { forceA, forceB } = colliderRadialForce(posA, posB, [1, 0, 0], [1, 0, 0]);
  assert.strictEqual(forceA, 0);
  assert.strictEqual(forceB, 0);
  // well above MIN_SEPARATION too — confirms no soft falloff tail
  const far = colliderRadialForce([0, 0, 0], [50, 0, 0], [1, 0, 0], [1, 0, 0]);
  assert.strictEqual(far.forceA, 0);
  assert.strictEqual(far.forceB, 0);
});

// WR-2 (teeth) — HALO-03: placeHaloCandidates places EXACTLY the given
// candidate ids (readable via the conePositions()/__mm_cone_positions hook
// surface) AND removes NO existing node from `_positions`. This exercises
// the NEW export, not just pre-existing regressions; the full geometry
// monotonicity teeth live in halo_cone.test.mjs + the e2e (-g "cone").
test("placeHaloCandidates: places exactly the given candidate ids and removes no existing node", () => {
  const projector = createProjector(fakeCanvas());
  const mkCoord = (arr, url) => Object.assign([...arr], { url });
  const coords = {
    keep1: mkCoord([1, 0, 0, 0.1, 0.8, 0.5], "u1"),
    keep2: mkCoord([0, 1, 0, 0.2, 0.8, 0.5], "u1"),
    cone_a: mkCoord([10, 0, 0, 0.3, 0.8, 0.5], "u1"),
    cone_b: mkCoord([0, 10, 0, 0.4, 0.8, 0.5], "u1"),
  };
  const urlRoots = { u1: { root_position: [0, 0, 0], bounding_radius: 50 } };
  projector.setNodes(coords, urlRoots);
  const before = new Set(projector.nodePositions().map((p) => p.id));
  assert.strictEqual(before.size, 4, "all 4 seeded nodes present before placeHaloCandidates");

  const apex = { x: 0, y: 0, z: 0 };
  const candidates = [
    { id: "cone_a", label: "A", transport: { similarity: 0.9, radial: 4, along_ray: 36 } },
    { id: "cone_b", label: "B", transport: { similarity: 0.5, radial: 20, along_ray: 20 } },
  ];
  const placed = projector.placeHaloCandidates(apex, candidates);

  // exactly the given ids were placed.
  assert.strictEqual(placed.length, 2);
  assert.deepStrictEqual(placed.map((p) => p.id).sort(), ["cone_a", "cone_b"]);

  // the test hook surface (conePositions(), the function __mm_cone_positions
  // wraps) reflects the same placement.
  const hookPositions = projector.conePositions();
  assert.deepStrictEqual(hookPositions.map((p) => p.id).sort(), ["cone_a", "cone_b"]);

  // no existing node was removed — all 4 original ids are still present.
  const after = new Set(projector.nodePositions().map((p) => p.id));
  assert.strictEqual(after.size, 4, "no existing node removed by placeHaloCandidates");
  for (const id of before) assert.ok(after.has(id), `${id} still present after placeHaloCandidates`);

  // the untouched candidates (keep1/keep2) did not move.
  const beforePos = Object.fromEntries(projector.nodePositions().map((p) => [p.id, p]));
  assert.strictEqual(beforePos.keep1.x, 1);
  assert.strictEqual(beforePos.keep2.y, 1);
});

console.log(`\n${passed}/${passed + failed} passed`);
if (failed) process.exit(1);
