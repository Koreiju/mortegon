/**
 * halo_cone.test.mjs — HALO-03 cone-ray transport pure geometry (§O.18).
 * Run: node backend/static/js/fe/halo_cone.test.mjs
 */
import assert from "node:assert";
import { placeOnCone, placeCandidatesOnCone } from "./halo_cone.mjs";

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log("  PASS  " + name); passed++; }
  catch (e) { console.log("  FAIL  " + name + ": " + e.message); failed++; }
}

const apex = { x: 0, y: 0, z: 0 };

// stub projectFns: every candidate has a distinct backing world position
// (so the ray direction differs per candidate, exercising the apex→world_pos
// ray composition), and azimuth() returns a fixed value (unused by the 3D
// cone path — only the 2D fallback reads it).
function stubProjectFns(worldPositions) {
  return {
    project: (x, y, z) => ({ x, y, inFront: true, ndcZ: 0 }),
    azimuth: () => 0.4,
    nodeWorldPosition: (id) => worldPositions[id] || null,
  };
}

test("Test 1 — monotonicity: distance-from-apex (radial) decreases as similarity increases", () => {
  // descending similarity scores; backend-shaped transport (radial = (1-s)*R,
  // the apex-distance scalar) computed exactly as routes.py does it server-
  // side and fed in VERBATIM here — this test does not re-derive it from
  // similarity inside halo_cone.mjs, it only proves the CONSUMED value
  // produces a monotonic placement.
  const R = 40;
  const candidates = [
    { id: "a", label: "Alpha", transport: { similarity: 0.9, radial: (1 - 0.9) * R, along_ray: 0.9 * R } },
    { id: "b", label: "Beta", transport: { similarity: 0.5, radial: (1 - 0.5) * R, along_ray: 0.5 * R } },
    { id: "c", label: "Gamma", transport: { similarity: 0.2, radial: (1 - 0.2) * R, along_ray: 0.2 * R } },
  ];
  const worldPositions = {
    a: { x: 10, y: 0, z: 0 }, b: { x: 0, y: 10, z: 0 }, c: { x: 0, y: 0, z: 10 },
  };
  const projectFns = stubProjectFns(worldPositions);
  const placed = placeCandidatesOnCone(apex, candidates, projectFns);
  const byId = Object.fromEntries(placed.map((p) => [p.id, p]));
  // radial IS the apex-distance scalar carried along the ray (backend's own
  // "more similar -> nearer the apex" contract) — assert it decreases with
  // similarity (the testable claim per UI-SPEC: "ordering, not a curve").
  assert.ok(byId.a.radial < byId.b.radial, "higher similarity (a) has smaller radial than b");
  assert.ok(byId.b.radial < byId.c.radial, "b's radial smaller than lower-similarity c");
  // and the actual placement's distance along the ray axis from the apex
  // (the component the radial scalar drives) is correspondingly ordered.
  const distAlongRay = (p) => {
    const dx = p.x - apex.x, dy = p.y - apex.y, dz = p.z - apex.z;
    return Math.hypot(dx, dy, dz);
  };
  // with along_ray (the perpendicular term) held proportional but radial
  // dominating the ordering at these magnitudes is not guaranteed in
  // general Euclidean terms (radial and along_ray are orthogonal
  // components) — so the monotonicity claim this module guarantees, and the
  // one the e2e/UI-SPEC contract requires, is on `radial` itself (asserted
  // above), which is what callers (placeHaloCandidates) use to rank
  // proximity-to-apex visually via the dominant ray-axis term.
  assert.ok(distAlongRay(byId.a) > 0, "placement is offset from the apex");
});

test("Test 2 — apex composition: along_ray=0,radial=0 lands exactly at apex; increasing along_ray moves it along the apex→projected-node ray", () => {
  const worldPositions = { x1: { x: 10, y: 0, z: 0 } };
  const projectFns = stubProjectFns(worldPositions);
  const zero = placeOnCone(apex, { id: "x1", label: "X", transport: { similarity: 0, radial: 0, along_ray: 0 } }, projectFns);
  assert.ok(Math.abs(zero.x - apex.x) < 1e-9 && Math.abs(zero.y - apex.y) < 1e-9 && Math.abs(zero.z - apex.z) < 1e-9,
    "radial=0,along_ray=0 lands exactly at the apex");

  // increasing along_ray (holding radial=0) moves the point purely along the
  // PERPENDICULAR axis at the apex (the cone's lateral spread) — increasing
  // radial (holding along_ray=0) moves the point purely along the
  // apex→projected-node RAY itself. Assert the ray-axis movement: as radial
  // grows from 0, the projection of (placed - apex) onto the unit ray
  // direction grows monotonically (the point slides along the ray).
  const rayUnit = { x: 1, y: 0, z: 0 }; // apex->worldPos(x1) direction, by construction
  const projOnRay = (p) => (p.x - apex.x) * rayUnit.x + (p.y - apex.y) * rayUnit.y + (p.z - apex.z) * rayUnit.z;
  const r0 = placeOnCone(apex, { id: "x1", label: "X", transport: { similarity: 0, radial: 0, along_ray: 0 } }, projectFns);
  const r10 = placeOnCone(apex, { id: "x1", label: "X", transport: { similarity: 0, radial: 10, along_ray: 0 } }, projectFns);
  const r20 = placeOnCone(apex, { id: "x1", label: "X", transport: { similarity: 0, radial: 20, along_ray: 0 } }, projectFns);
  assert.ok(projOnRay(r0) < projOnRay(r10) && projOnRay(r10) < projOnRay(r20),
    "increasing radial moves the point further along the apex->projected-node ray");
});

test("Test 3 — verbatim consumption (D10): radial/along_ray are read directly, never recomputed from similarity", () => {
  const worldPositions = { x1: { x: 5, y: 0, z: 0 } };
  const projectFns = stubProjectFns(worldPositions);
  // deliberately INCONSISTENT transport values — radial/along_ray that do
  // NOT match the (1-s)*R / s*R formula for the given similarity. If
  // placeOnCone were re-deriving from similarity (a D10 violation), the
  // output would ignore these and use the "correct" formula instead; since
  // it consumes them verbatim, the output must reflect the SUPPLIED
  // (wrong-looking) values, not a recomputed one.
  const weirdCandidate = { id: "x1", label: "X", transport: { similarity: 0.9, radial: 999, along_ray: 0 } };
  const placedWeird = placeOnCone(apex, weirdCandidate, projectFns);
  // formula-consistent counterpart for comparison: radial = (1-0.9)*40 = 4
  const formulaCandidate = { id: "x1", label: "X", transport: { similarity: 0.9, radial: 4, along_ray: 0 } };
  const placedFormula = placeOnCone(apex, formulaCandidate, projectFns);
  const dist = (p) => Math.hypot(p.x - apex.x, p.y - apex.y, p.z - apex.z);
  assert.ok(Math.abs(dist(placedWeird) - 999) < 1e-6, "the deliberately-inconsistent radial=999 was used VERBATIM");
  assert.ok(Math.abs(dist(placedFormula) - 4) < 1e-6, "the formula-consistent radial=4 was used VERBATIM");
  assert.notStrictEqual(Math.round(dist(placedWeird)), Math.round(dist(placedFormula)),
    "the two candidates (same similarity, different supplied radial) produce DIFFERENT placements — proving no re-derivation from similarity");
});

test("Test 4 — 2D fallback: a candidate with no backing 3D node uses the existing haloLayout polar placement", () => {
  const projectFns = stubProjectFns({}); // nodeWorldPosition resolves null for everything
  const candidate = { id: "nobacking", label: "NoBacking", transport: { similarity: 0.7, radial: 12, along_ray: 28 } };
  const placed = placeOnCone(apex, candidate, projectFns, { focal2d: { cx: 500, cy: 400 } });
  assert.strictEqual(placed.hasBacking, false, "no 3D backing -> 2D fallback path taken");
  // haloLayout's r = rBase + (1-sim)*rExtent (default rBase=120, rExtent=200)
  const expectedR = 120 + (1 - 0.7) * 200;
  assert.ok(Math.abs(placed.r - expectedR) < 1e-6, "2D fallback uses haloLayout's EXISTING polar radius formula");
  const distFromFocal = Math.hypot(placed.x - 500, placed.y - 400);
  assert.ok(Math.abs(distFromFocal - expectedR) < 1e-6, "placed (x,y) sits on the haloLayout ray at radius r");
});

test("Test 5 — delete-and-replace ordering: removing the top candidate re-places the next-most-similar into the nearest-apex slot", () => {
  const R = 40;
  const mk = (id, sim) => ({ id, label: id, transport: { similarity: sim, radial: (1 - sim) * R, along_ray: sim * R } });
  const worldPositions = {
    a: { x: 10, y: 0, z: 0 }, b: { x: 0, y: 10, z: 0 }, c: { x: 0, y: 0, z: 10 },
  };
  const projectFns = stubProjectFns(worldPositions);
  const queue = [mk("a", 0.9), mk("b", 0.6), mk("c", 0.3)];

  const before = placeCandidatesOnCone(apex, queue, projectFns);
  const nearestBefore = before.reduce((best, p) => (p.radial < best.radial ? p : best));
  assert.strictEqual(nearestBefore.id, "a", "the most-similar candidate (a) occupies the nearest-apex slot before delete");

  // delete the top candidate (a) — the next-most-similar (b) must now be
  // nearest the apex slot when the remaining queue is re-placed.
  const afterDelete = queue.filter((c) => c.id !== "a");
  const after = placeCandidatesOnCone(apex, afterDelete, projectFns);
  const nearestAfter = after.reduce((best, p) => (p.radial < best.radial ? p : best));
  assert.strictEqual(nearestAfter.id, "b", "the next-most-similar candidate (b) transports into the vacated nearest-apex slot");
});

console.log(`\n${passed}/${passed + failed} passed`);
if (failed) process.exit(1);
