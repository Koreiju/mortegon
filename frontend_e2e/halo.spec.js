// Phase 3 — Apparition halo render (§7 / §15.2 / HALO-01/02).
//
// The halo's MODEL (constant-similarity ray, along-line slide, z-above-slate,
// scroll re-anchor, name-only phantoms) is unit-covered by
// `backend/static/js/fe/magic_markdown_halo.test.mjs` (5/5), and the §15.1
// circular collapsed-node form is exercised in `edit.spec.js`. These are the
// LIVE-editor browser acceptance specs — they seed concepts, open the served `/`
// editor, fire a halo on a focal field, and assert the §V.4 / §T.4 render contract
// through the `window.__mm_halo_*` hooks editor.html exposes. This is the
// render-level coverage the REPL (API/WS seam) cannot reach.
const { test, expect } = require("@playwright/test");

// Seed a few uniquely-named concepts (single-line data → the store's instant
// candidate label is the concept NAME, the name-only render), open the served `/`
// editor so `loadConcepts` populates the store, then fire a halo on the first
// focal field. Returns the created ids for cleanup. (The served `/` on an isolated
// test DB starts empty — the passing edit.spec.js specs seed the same way.)
async function seedAndOpenHalo(page, request) {
  const TS = Date.now();
  const names = [`Halo Alpha ${TS}`, `Halo Beta ${TS}`, `Halo Gamma ${TS}`, `Halo Delta ${TS}`];
  const ids = [];
  for (const name of names) {
    const res = await request.post("/api/concepts", { data: { name, data: name, workspace_id: "_default" } });
    ids.push((await res.json()).concept_id);
  }
  await page.goto("/");
  await page.waitForFunction(() => window.__mm_ready === true, { timeout: 15000 });
  await page.waitForFunction(() => document.querySelector("#grid .mm-line") !== null, { timeout: 15000 });
  await page.evaluate(() => window.__mm_open_halo());
  await expect
    .poll(() => page.evaluate(() => window.__mm_halo_state().phantoms), { timeout: 10000 })
    .toBeGreaterThan(0);
  // The instant store candidates are refined async by /api/radiation, which
  // re-renders the halo with a new candidate set. Wait until that settles (two
  // consecutive identical reads) so per-test baselines are taken on a stable halo.
  let prev = null;
  await expect
    .poll(async () => {
      const cur = await page.evaluate(() =>
        [...document.querySelectorAll(".mm-phantom")].map((p) => p.getAttribute("data-sim")).join(","));
      const stable = cur.length > 0 && cur === prev;
      prev = cur;
      return stable;
    }, { timeout: 10000, intervals: [250, 250, 250] })
    .toBe(true);
  return ids;
}

async function cleanup(request, ids) {
  for (const id of ids) await request.delete(`/api/concepts/${id}?workspace_id=_default`);
}

test("HALO-01 clicking a collapsed node fires a halo of NAME-only phantoms", async ({ page, request }) => {
  // fire a halo from a focal field → expect phantoms each showing ONLY the
  // candidate name (no score chips; scores live in data-sim for slow-hover
  // tooltips, never in the rendered label).
  const ids = await seedAndOpenHalo(page, request);
  try {
    const st = await page.evaluate(() => window.__mm_halo_state());

    expect(st.phantoms, "halo radiated phantoms").toBeGreaterThan(0);
    for (const p of st.positions) {
      expect(p.label.trim().length, "phantom shows a name").toBeGreaterThan(0);
      // name-only: no score chip text (no "score", no percentage, no multi-place decimal)
      expect(p.label, "no score chip in the phantom label").not.toMatch(/score|\d+%|\b0?\.\d{2,}\b/i);
    }
    // §15.1 / §S.5 — each phantom is a collapsed CIRCULAR node (border-radius 50%)
    expect(st.circular, "phantom is a circular collapsed node").toBe(true);
    // the score is carried for the tooltip in data-sim, NOT painted into the label
    const sims = await page.evaluate(() =>
      [...document.querySelectorAll(".mm-phantom")].map((p) => p.getAttribute("data-sim")));
    expect(sims.length).toBe(st.phantoms);
    for (const s of sims) expect(Number.isFinite(parseFloat(s)), "data-sim holds the similarity").toBe(true);
  } finally {
    await cleanup(request, ids);
  }
});

test("HALO-02 phantoms paint ABOVE the slate (z-order) and re-anchor to the focal token", async ({ page, request }) => {
  const ids = await seedAndOpenHalo(page, request);
  try {
    const st = await page.evaluate(() => window.__mm_halo_state());

    // T.4 fix #1 — the halo overlay paints ABOVE the slate (z-order)
    const slateZ = parseInt(st.slateZ, 10);
    expect(parseInt(st.haloZ, 10), "halo z-index is above the slate").toBeGreaterThan(
      Number.isFinite(slateZ) ? slateZ : 0);

    // T.4 fix #2 — re-anchor on scroll: when the focal token's live rect moves, the
    // scroll listener re-renders and the phantoms TRACK the focal rect (they are not
    // pinned to a stale card rect). Shift the grid → fire scroll → positions move.
    const moved = await page.evaluate(() => {
      const before = window.__mm_halo_state().positions.map((p) => p.top);
      const grid = document.getElementById("grid");
      grid.style.transform = "translateY(140px)";   // moves the focal token's live rect
      window.dispatchEvent(new Event("scroll"));     // editor.html re-anchors on scroll (capture)
      const after = window.__mm_halo_state().positions.map((p) => p.top);
      grid.style.transform = "";
      return { before, after };
    });
    expect(moved.after.join("|"), "phantoms re-anchored to the moved focal rect").not.toBe(
      moved.before.join("|"));
  } finally {
    await cleanup(request, ids);
  }
});

test("HALO-02 constant-similarity ray + along-line slide as the 3D camera orbits", async ({ page, request }) => {
  const ids = await seedAndOpenHalo(page, request);
  try {
    // Orbit the camera azimuth: §V.4 couples halo.camAngle to the projector
    // azimuth via projector.onFrame → `halo.camAngle = az; renderHalo()`. The
    // `__mm_halo_rotate` hook drives that SAME synchronous render path. Capture
    // before → rotate → capture after ATOMICALLY in one evaluate, so the next
    // rAF frame (which re-pins camAngle to the static camera azimuth) cannot
    // overwrite the orbited state before we read it.
    const r = await page.evaluate(() => {
      const snap = () => ({
        pos: window.__mm_halo_state().positions.map((p) => `${p.left},${p.top}`),
        sims: [...document.querySelectorAll(".mm-phantom")].map((p) => p.getAttribute("data-sim")),
      });
      const before = snap();
      window.__mm_halo_rotate(0.8); // orbit signal → synchronous renderHalo
      const after = snap();
      return { before, after };
    });

    // along-line slide — the phantoms move as the ray angle rotates
    expect(r.after.pos.join("|"), "phantoms slid along their rays on orbit").not.toBe(
      r.before.pos.join("|"));
    // constant-similarity ray — the radial similarity (data-sim → fixed r) is invariant
    // under the orbit (only the angle changes), so every data-sim is unchanged
    expect(r.after.sims, "similarity (radial distance) is constant across the orbit").toEqual(
      r.before.sims);
  } finally {
    await cleanup(request, ids);
  }
});
