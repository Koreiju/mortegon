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
