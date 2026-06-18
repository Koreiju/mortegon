// Phase 3 — Apparition halo render (§7 / §15.2 / HALO-01/02).
//
// The halo's MODEL (constant-similarity ray, along-line slide, z-above-slate,
// scroll re-anchor, name-only phantoms) is unit-covered by
// `backend/static/js/fe/magic_markdown_halo.test.mjs` (5/5), and the §15.1
// circular collapsed-node form is exercised in `edit.spec.js`. These are the
// LIVE-editor browser acceptance specs — they need a rendered focal field with a
// halo open (a fixture scan + a click on a collapsed node), so they are the
// build/verify targets for HALO-01/02 (un-fixme as Phase 3's live halo lands).
const { test, expect } = require("@playwright/test");

// T2/T3 / HALO-01 — clicking a COLLAPSED CIRCULAR node (§S.5) fires the apparition
// halo PROXIMAL to that node; each phantom shows the candidate NAME only (scores
// live in the `data-sim` slow-hover tooltip, never chips), and the overlay paints
// ABOVE the slate. Authored cards give a deterministic candidate pool.
test("HALO-01 clicking a collapsed node fires a halo of NAME-only phantoms", async ({ page, request }) => {
  const TS = Date.now();
  const names = [`Tarot ${TS}`, `Star ${TS}`, `Library ${TS}`];
  const ids = [];
  for (const nm of names) {
    const r = await request.post("/api/concepts", {
      data: { name: nm, data: `${nm}\n\tkind : sample\n\tnote : hello`, workspace_id: "_default" },
    });
    ids.push((await r.json()).concept_id);
  }
  try {
    await page.goto("/");
    await page.waitForFunction(() => window.__mm_ready === true, { timeout: 15000 });
    const panel = page.locator(".mm-slate", { hasText: names[0] });
    await expect(panel).toBeVisible({ timeout: 10000 });

    // collapse this panel to its circular computation-graph nodes (§15.1), then
    // click a leaf node — dispatched on the slate container so the dbl-click lands
    // on the body (not a token), which is what toggles panel⇄graph.
    await panel.evaluate((el) => el.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true })));
    await expect(page.locator(".mm-gnode").first()).toBeVisible({ timeout: 8000 });
    await page.locator(".mm-gnode").last().click();

    const phantoms = page.locator(".mm-phantom");
    await expect(phantoms.first()).toBeVisible({ timeout: 8000 });
    const info = await page.evaluate(() => {
      const ph = [...document.querySelectorAll(".mm-phantom")];
      const halo = document.querySelector(".mm-halo");
      const focal = document.querySelector(".mm-gnode");
      const fr = focal ? focal.getBoundingClientRect() : { left: 0, top: 0 };
      return {
        count: ph.length,
        nameOnly: ph.every((p) => !/\d\.\d|score|%/i.test(p.textContent)), // no score chips
        simTooltip: ph.every((p) => p.hasAttribute("data-sim")),           // scores live here
        zAbove: halo ? parseInt(getComputedStyle(halo).zIndex) > 1000 : false,
        proximal: ph.every((p) => {
          const r = p.getBoundingClientRect();
          return Math.hypot(r.left - fr.left, r.top - fr.top) < 700;        // near the focal node
        }),
      };
    });
    expect(info.count, "phantoms present").toBeGreaterThan(0);
    expect(info.nameOnly, "phantoms show NAME only — no score chips").toBe(true);
    expect(info.simTooltip, "scores live in data-sim (slow-hover tooltip)").toBe(true);
    expect(info.zAbove, "halo paints above the slate (T.4 z-order)").toBe(true);
    expect(info.proximal, "halo stays proximal to the collapsed node (§S.5)").toBe(true);
  } finally {
    for (const id of ids) await request.delete(`/api/concepts/${id}?workspace_id=_default`);
  }
});

// shared setup: 3 authored cards = a deterministic candidate pool; open the halo
// on a collapsed circular (graph-mode) leaf node.
async function seedCards(request, ts) {
  const names = [`Tarot ${ts}`, `Star ${ts}`, `Library ${ts}`];
  const ids = [];
  for (const nm of names) {
    const r = await request.post("/api/concepts", {
      data: { name: nm, data: `${nm}\n\tkind : sample\n\tnote : hello`, workspace_id: "_default" },
    });
    ids.push((await r.json()).concept_id);
  }
  return { names, ids };
}
async function openHaloOnLeaf(page, firstName) {
  const panel = page.locator(".mm-slate", { hasText: firstName });
  await expect(panel).toBeVisible({ timeout: 10000 });
  await panel.evaluate((el) => el.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true })));
  await expect(page.locator(".mm-gnode").first()).toBeVisible({ timeout: 8000 });
  await page.locator(".mm-gnode").last().click();
  await expect(page.locator(".mm-phantom").first()).toBeVisible({ timeout: 8000 });
}

test("HALO-02 phantoms paint ABOVE the slate (z-order) and re-anchor to the focal on scroll", async ({ page, request }) => {
  await page.setViewportSize({ width: 700, height: 320 }); // force a scrollable page
  const { names, ids } = await seedCards(request, Date.now());
  try {
    await page.goto("/");
    await page.waitForFunction(() => window.__mm_ready === true, { timeout: 15000 });
    await openHaloOnLeaf(page, names[0]);

    // T.4 fix #1 — the overlay paints above the slate
    const zAbove = await page.evaluate(() => {
      const h = document.querySelector(".mm-halo");
      return h ? parseInt(getComputedStyle(h).zIndex) > 1000 : false;
    });
    expect(zAbove, "halo z-index above the slate").toBe(true);

    // T.4 fix #2 — scroll → phantoms track the focal's LIVE rect (move together)
    const m = await page.evaluate(async () => {
      const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
      const f0 = document.querySelector(".mm-gnode").getBoundingClientRect().top;
      const p0 = document.querySelector(".mm-phantom").getBoundingClientRect().top;
      window.scrollBy(0, 100);
      await sleep(150);
      const f1 = document.querySelector(".mm-gnode").getBoundingClientRect().top;
      const p1 = document.querySelector(".mm-phantom").getBoundingClientRect().top;
      return { scrolled: Math.round(window.scrollY), fd: Math.round(f1 - f0), pd: Math.round(p1 - p0) };
    });
    expect(m.scrolled, "page scrolled").toBeGreaterThan(0);
    expect(m.pd, "phantom moved with the scroll").not.toBe(0);
    expect(Math.abs(m.fd - m.pd), "phantom re-anchored to the focal (moved with it)").toBeLessThan(8);
  } finally {
    for (const id of ids) await request.delete(`/api/concepts/${id}?workspace_id=_default`);
  }
});

// The constant-similarity-ray GEOMETRY (r depends only on similarity, angle =
// base + camAngle, slide stays on the same-radius ray) is unit-verified at machine
// precision in `magic_markdown_halo.test.mjs` (5/5). This e2e verifies the LIVE
// COUPLING the unit test can't reach: orbiting the camera azimuth re-renders the
// halo so the phantoms slide.
test("HALO-02 camera orbit slides the phantoms along their rays (live azimuth→halo coupling)", async ({ page, request }) => {
  const { names, ids } = await seedCards(request, Date.now());
  try {
    await page.goto("/");
    await page.waitForFunction(() => window.__mm_ready === true, { timeout: 15000 });
    await openHaloOnLeaf(page, names[0]);
    const slid = await page.evaluate(async () => {
      const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
      await sleep(700); // let radiation settle so the candidate set is stable
      const pos = () => Object.fromEntries([...document.querySelectorAll(".mm-phantom")].map((p) => {
        const r = p.getBoundingClientRect();
        return [p.textContent, { x: r.left, y: r.top }];
      }));
      const before = pos();
      window.__mm_halo_rotate(0.9); // orbit the camera azimuth
      await sleep(150);
      const after = pos();
      const shared = Object.keys(before).filter((k) => k in after);
      return shared.length > 0 && shared.some((k) => Math.hypot(after[k].x - before[k].x, after[k].y - before[k].y) > 8);
    });
    expect(slid, "camera orbit slides the phantoms (live coupling)").toBe(true);
  } finally {
    for (const id of ids) await request.delete(`/api/concepts/${id}?workspace_id=_default`);
  }
});
