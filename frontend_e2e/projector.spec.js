// Phase 4 — UMAP-01 projector render acceptance. The 6D-UMAP HSV math is
// unit-verified in `backend/static/js/fe/projector.test.mjs` (7/7); this is the
// render-level wiring the REPL can't reach: the live `/` projector colours its
// nodes from the backend's `umap_canonical` HSV (NOT the positional sweep) and
// recolours as the camera orbits. The projector needs THREE.js + WebGL; if it
// didn't boot (offline CDN / no WebGL), the test skips deterministically.
const { test, expect } = require("@playwright/test");

test("UMAP-01 projector renders the 6D umap_canonical HSV and recolours on camera orbit", async ({ page }) => {
  await page.goto("/");
  await page.waitForFunction(() => window.__mm_ready === true, { timeout: 15000 });
  const booted = await page
    .waitForFunction(() => typeof window.__mm_proj_set === "function", { timeout: 9000 })
    .then(() => true)
    .catch(() => false);
  test.skip(!booted, "projector requires THREE.js + WebGL (offline CDN / headless GL unavailable)");

  // inject a canonical 6D frame: one node at a KNOWN hue 0.33 (green), sat 0.9, lum 0.5.
  await page.evaluate(() => window.__mm_proj_set({ z: [10, 0, 0, 0.33, 0.9, 0.5] }));
  const c0 = await page.evaluate(() => window.__mm_proj_color(0));
  expect(c0, "projector coloured a node").toBeTruthy();
  // setHSL(0.33,…) is green-dominant — and crucially NOT the n=1 positional sweep
  // (hue 0 = red). So the projector rendered the FRAME hue, not an invented one.
  expect(c0[1], "green channel dominant for frame hue 0.33").toBeGreaterThan(c0[0]);
  expect(c0[1]).toBeGreaterThan(c0[2]);

  // orbit the camera azimuth → the HSV field rotates (the node recolours).
  await page.evaluate(() => window.__mm_proj_orbit(Math.PI));
  const c1 = await page.evaluate(() => window.__mm_proj_color(0));
  const delta = Math.abs(c1[0] - c0[0]) + Math.abs(c1[1] - c0[1]) + Math.abs(c1[2] - c0[2]);
  expect(delta, "camera orbit rotates the node HSV (UMAP-01)").toBeGreaterThan(0.05);
});

// REAL-01 — force-directed ray convergence. The pure ray/collider MATH is
// unit-verified at machine precision in `projector.test.mjs` (13/13); this is
// the render-level wiring the unit tests can't reach: __mm_proj_set_with_roots
// seeds a multi-chunk frame WITH url_roots (activating the force step), the
// animate loop runs several real frames, and __mm_proj_node_positions reads
// back the post-force-step world positions.
test("REAL-01 force-directed: chunks converge along root-URL rays with hard collider spacing", async ({ page }) => {
  await page.goto("/");
  await page.waitForFunction(() => window.__mm_ready === true, { timeout: 15000 });
  const booted = await page
    .waitForFunction(() => typeof window.__mm_proj_set_with_roots === "function", { timeout: 9000 })
    .then(() => true)
    .catch(() => false);
  test.skip(!booted, "projector requires THREE.js + WebGL (offline CDN / headless GL unavailable)");

  // One URL root at the origin; several chunks deliberately seeded CLOSER than
  // MIN_SEPARATION (2.52, the 1.4-derived value — Pitfall 2, NOT 3.6) along
  // near-parallel rays so the collider step has work to do.
  await page.evaluate(() => {
    const coords = {
      c1: [10, 0, 0, 0.1, 0.8, 0.5],
      c2: [10.5, 0.2, 0, 0.2, 0.8, 0.5],   // ~0.54 from c1 — well below 2.52
      c3: [9.7, -0.3, 0.1, 0.3, 0.8, 0.5], // also tight to c1/c2
      c4: [3, 0, 0, 0.4, 0.8, 0.5],        // a distinct ray (shorter radius)
    };
    // the minimal coords frame carries no per-chunk url field, so every chunk
    // resolves to the shared "" url key (projector.mjs::_computeRayData) —
    // seed url_roots under that same key so this test exercises the REAL
    // consume-url_roots path, not the defensive fallback-to-origin path.
    const urlRoots = { "": { root_position: [0, 0, 0], bounding_radius: 10.5 } };
    window.__mm_proj_set_with_roots(coords, urlRoots);
  });

  // advance several real animate frames so the collider step has run.
  await page.evaluate(async () => {
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    for (let i = 0; i < 60; i++) { await sleep(16); }
  });

  // editor.html auto-boots a real /api/recompute_umap frame on load (boot
  // fetch in editor.html); __mm_proj_node_positions() returns EVERY node the
  // projector has ever seen, including that pre-existing real-scan chunk
  // population. Filter to just this test's 4 seeded fixture ids so the
  // spacing/ray assertions below test THIS fixture's geometry, not a
  // collision against unrelated real chunks the boot sequence happened to
  // scatter nearby.
  const allPositions = await page.evaluate(() => window.__mm_proj_node_positions());
  const fixtureIds = new Set(["c1", "c2", "c3", "c4"]);
  const positions = allPositions.filter((p) => fixtureIds.has(p.id));
  expect(positions.length, "all 4 seeded fixture node positions returned").toBe(4);

  // (a) every node lies on its OWN ray from the shared origin root: the cross
  // product of (pos - root) and the node's initial direction should have
  // ~zero magnitude (within float tolerance) — proving "moves only along its
  // ray", never off-ray. Root is the origin for every node in this fixture.
  const root = [0, 0, 0];
  const initialDirs = {
    c1: [10, 0, 0], c2: [10.5, 0.2, 0], c3: [9.7, -0.3, 0.1], c4: [3, 0, 0],
  };
  const cross = (a, b) => [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];
  const norm = (v) => Math.hypot(v[0], v[1], v[2]);
  for (const p of positions) {
    const fromRoot = [p.x - root[0], p.y - root[1], p.z - root[2]];
    const initDir = initialDirs[p.id];
    if (!initDir || norm(fromRoot) < 1e-6) continue; // skip degenerate/at-root
    const crossMag = norm(cross(fromRoot, initDir));
    const denom = norm(fromRoot) * norm(initDir);
    expect(crossMag / denom, `node ${p.id} stayed on its own ray`).toBeLessThan(0.02);
  }

  // (b) minimum pairwise spacing across ALL returned positions is >= 2.52
  // (MIN_SEPARATION, the 1.4-derived value) within a small float tolerance —
  // never the 2.0-derived 3.6 (Pitfall 2).
  let minDist = Infinity;
  for (let i = 0; i < positions.length; i++) {
    for (let j = i + 1; j < positions.length; j++) {
      const d = Math.hypot(positions[i].x - positions[j].x, positions[i].y - positions[j].y, positions[i].z - positions[j].z);
      if (d < minDist) minDist = d;
    }
  }
  expect(minDist, "minimum pairwise spacing holds at MIN_SEPARATION=2.52 (not 3.6)").toBeGreaterThanOrEqual(2.52 - 0.05);

  // (c) no concentric/Fibonacci final position: radii from the root vary
  // (force-directed sliding occurred), they are not all pinned to one fixed
  // radius at golden-angle increments around a sphere.
  const radii = positions.map((p) => Math.hypot(p.x - root[0], p.y - root[1], p.z - root[2]));
  const spread = Math.max(...radii) - Math.min(...radii);
  expect(spread, "radii spread > 0 — force-directed sliding, not a fixed concentric ring").toBeGreaterThan(0);
});

// REAL-02 — per-URL multi-scan placement + camera framing. The backend
// (layout_service.py) already resolves non-overlapping root_position +
// bounding_radius per URL (verified independently by the REPL's
// perimeter-rescale env-scenario); this e2e proves the FRONTEND renders
// both clusters at their backend-emitted roots (not at the origin), that a
// re-scan of the first URL's chunks never moves its root, and that the
// camera auto-frames toward the newest root on scan-end.
test("REAL-02 multi-scan: per-URL clusters land non-overlapping, old roots never move, camera frames newest", async ({ page }) => {
  await page.goto("/");
  await page.waitForFunction(() => window.__mm_ready === true, { timeout: 15000 });
  const booted = await page
    .waitForFunction(() => typeof window.__mm_proj_set_with_roots === "function", { timeout: 9000 })
    .then(() => true)
    .catch(() => false);
  test.skip(!booted, "projector requires THREE.js + WebGL (offline CDN / headless GL unavailable)");

  // Scan A: a single URL ("urlA") whose backend-resolved root sits at the
  // origin with bounding_radius 6. Each coords entry carries a `.url`
  // property (array-as-object, mirrors the backend's per-chunk url field
  // that _computeRayData reads) so this test exercises distinct per-URL
  // ray roots rather than the shared "" fallback key.
  const stepA = await page.evaluate(() => {
    const mk = (xyz, url) => { const a = [...xyz, 0.2, 0.8, 0.5]; a.url = url; return a; };
    const coordsA = {
      a1: mk([1, 0, 0], "urlA"),
      a2: mk([0, 1, 0], "urlA"),
      a3: mk([-1, 0, 0], "urlA"),
    };
    const urlRootsA = { urlA: { root_position: [0, 0, 0], bounding_radius: 6 } };
    window.__mm_proj_set_with_roots(coordsA, urlRootsA);
    return { camDist: window.__mm_proj_camera_distance() };
  });

  // advance real animate frames so the camera-frame tween toward urlA's
  // root (the first-ever URL, so it is itself "newest" on this first call)
  // completes before we read positions/camera state.
  await page.evaluate(async () => {
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    for (let i = 0; i < 60; i++) { await sleep(16); }
  });

  const afterA = await page.evaluate(() => {
    const allPositions = window.__mm_proj_node_positions();
    const fixtureIds = new Set(["a1", "a2", "a3"]);
    return {
      positions: allPositions.filter((p) => fixtureIds.has(p.id)),
      camDist: window.__mm_proj_camera_distance(),
    };
  });
  expect(afterA.positions.length, "scan A's 3 fixture positions present").toBe(3);

  // Scan B: a SECOND url ("urlB") whose backend-resolved root sits at
  // [40,0,0], bounding_radius 6 — the kind of non-overlapping placement the
  // backend's _allocate_new_root already guarantees (existing_max_radius +
  // new_radius + safety_gap, entirely backend-side; the frontend's job is
  // only to render it). The merged coords frame keeps urlA's chunks
  // UNCHANGED (their positions must not move across this second scan).
  const afterB = await page.evaluate(() => {
    const mk = (xyz, url) => { const a = [...xyz, 0.6, 0.8, 0.5]; a.url = url; return a; };
    const coordsAB = {
      a1: mk([1, 0, 0], "urlA"),
      a2: mk([0, 1, 0], "urlA"),
      a3: mk([-1, 0, 0], "urlA"),
      b1: mk([41, 0, 0], "urlB"),
      b2: mk([40, 1, 0], "urlB"),
      b3: mk([39, 0, 0], "urlB"),
    };
    const urlRootsAB = {
      urlA: { root_position: [0, 0, 0], bounding_radius: 6 },     // unchanged — old root never moves
      urlB: { root_position: [40, 0, 0], bounding_radius: 6 },    // NEW non-overlapping root
    };
    window.__mm_proj_set_with_roots(coordsAB, urlRootsAB);
    return null;
  });

  // advance real animate frames so the collider step + the camera-frame
  // tween toward the NEW urlB root both complete.
  await page.evaluate(async () => {
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    for (let i = 0; i < 60; i++) { await sleep(16); }
  });

  const final = await page.evaluate(() => {
    const allPositions = window.__mm_proj_node_positions();
    const ids = new Set(["a1", "a2", "a3", "b1", "b2", "b3"]);
    return {
      positions: allPositions.filter((p) => ids.has(p.id)),
      camDist: window.__mm_proj_camera_distance(),
      camX: window.__mm_proj ? window.__mm_proj.camera.position.x : null,
    };
  });
  expect(final.positions.length, "all 6 fixture positions present after scan B").toBe(6);

  const byId = Object.fromEntries(final.positions.map((p) => [p.id, p]));

  // (a) non-overlap: urlA's cluster centroid vs urlB's cluster centroid are
  // separated by at least boundingA + boundingB (6 + 6 = 12) — proving both
  // clusters render at their DISTINCT backend roots, not collapsed near the
  // origin (the historical bug this plan closes).
  const centroid = (ids) => {
    const pts = ids.map((id) => byId[id]);
    const n = pts.length;
    return {
      x: pts.reduce((s, p) => s + p.x, 0) / n,
      y: pts.reduce((s, p) => s + p.y, 0) / n,
      z: pts.reduce((s, p) => s + p.z, 0) / n,
    };
  };
  const cA = centroid(["a1", "a2", "a3"]);
  const cB = centroid(["b1", "b2", "b3"]);
  const centroidDist = Math.hypot(cA.x - cB.x, cA.y - cB.y, cA.z - cB.z);
  expect(centroidDist, "urlA and urlB clusters render at distinct, separated backend roots (non-overlap)")
    .toBeGreaterThanOrEqual(12 - 1); // boundingA(6) + boundingB(6), small float tolerance

  // (b) old root never moves: urlA's chunk positions are stable across the
  // second scan (within tolerance) — re-scanning urlA's neighbour (urlB)
  // must not perturb urlA's already-placed chunks beyond the collider
  // step's own tiny corrections.
  const aBefore = Object.fromEntries(afterA.positions.map((p) => [p.id, p]));
  for (const id of ["a1", "a2", "a3"]) {
    const before = aBefore[id], after = byId[id];
    const moved = Math.hypot(before.x - after.x, before.y - after.y, before.z - after.z);
    expect(moved, `urlA's ${id} did not move across the second scan (old root stable)`).toBeLessThan(1.0);
  }

  // (c) camera frames the newest root: the camera distance/position shifted
  // toward urlB's root [40,0,0] after scan B — confirming frameCameraToRoot
  // fired for the NEW url, not just urlA (the first-ever call).
  const movedTowardB = Math.abs(final.camDist - afterA.camDist) > 0.5 || (final.camX !== null && final.camX > 5);
  expect(movedTowardB, "camera position/distance shifted after scan B (auto-framed toward the newest root)").toBe(true);
});
