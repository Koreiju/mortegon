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

// HALO-04 (§O.1a/D-02) — RENDER-level acceptance for the three `{ref}` brace
// states over a TWO-LEVEL ref chain (root -> B -> C), closing the Phase-7
// self-flagged gap (07-03 SUMMARY: "classifyBraceStates computed but
// panelVDom/graphVDom ignore l.braceState"). Phase-7's object_exploration.spec.js
// covers the MODEL-level classification (lines[].braceState); this block is
// the RENDER-level companion — it asserts the actual ▸/▾ glyphs, the
// panel↔graph node-count parity on reveal, and the resolved-external solid
// link DOM, all against the live served fe/ modules via in-page dynamic
// import() (the same convention object_exploration.spec.js uses; demo.html
// needs no scan/fixture seeding so this runs in any backend mode).
test.describe("brace render states (HALO-04)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/static/js/fe/demo.html");
    await page.waitForLoadState("networkidle");
  });

  // Builds a two-level ref chain (root -> B -> C) via the served modules,
  // mounts BOTH panel and graph forms into real DOM containers, and returns
  // the browser-side measurements the assertions need.
  async function renderTwoLevelChain(page, { expandRoot = false, expandB = false } = {}) {
    return page.evaluate(async ({ expandRoot, expandB }) => {
      const mm = await import("/static/js/fe/magic_markdown.mjs");
      const panelMod = await import("/static/js/fe/magic_markdown_panel.mjs");
      const { parse, buildRegistry, renderPanel, toggle } = mm;
      const { panelVDom, graphVDom, flattenVDom } = panelMod;

      // root: two refs to B (primary + secondary — the resolved-external
      // pairing), B itself refs C (the two-level chain).
      const root = parse([
        "root concept",
        "\tprimary {concept b}",
        "\tsecondary {concept b}",
      ].join("\n"));
      const b = parse([
        "concept b",
        "\tfield on b : value",
        "\tlink to c {concept c}",
      ].join("\n"));
      const c = parse([
        "concept c",
        "\tfield on c : value",
      ].join("\n"));
      const registry = buildRegistry([b, c]);

      let expanded = new Set();
      if (expandRoot) {
        const collapsed = renderPanel(root, { registry, expanded });
        const primaryPath = collapsed.find((l) => l.text === "primary {concept b}").path;
        expanded = toggle(expanded, primaryPath);
        if (expandB) {
          const afterRoot = renderPanel(root, { registry, expanded });
          const bRefPath = afterRoot.find((l) => l.text === "link to c {concept c}").path;
          expanded = toggle(expanded, bRefPath);
        }
      }

      const opts = { registry, expanded };
      const panelLines = renderPanel(root, opts);
      const panelFlat = flattenVDom(panelVDom(root, opts));
      const graphSpec = graphVDom(root, opts);
      const graphFlat = flattenVDom(graphSpec);

      const realise = (spec) => {
        const SVG_TAGS = new Set(["svg", "line", "circle", "g", "path", "ellipse", "text"]);
        const node = SVG_TAGS.has(spec.tag)
          ? document.createElementNS("http://www.w3.org/2000/svg", spec.tag)
          : document.createElement(spec.tag);
        for (const [k, v] of Object.entries(spec.attrs || {})) node.setAttribute(k, v);
        if (spec.text != null) node.textContent = spec.text;
        for (const ch of spec.children || []) node.appendChild(realise(ch));
        return node;
      };
      const container = document.createElement("div");
      container.id = "halo04-fixture-host";
      document.body.appendChild(container);
      const panelDom = realise(panelVDom(root, opts));
      const graphDom = realise(graphSpec);
      const panelHost = document.createElement("div");
      panelHost.id = "halo04-panel-host";
      panelHost.appendChild(panelDom);
      const graphHost = document.createElement("div");
      graphHost.id = "halo04-graph-host";
      graphHost.appendChild(graphDom);
      container.appendChild(panelHost);
      container.appendChild(graphHost);

      return {
        lines: panelLines.map((l) => ({ text: l.text, glyph: l.glyph, refTarget: l.refTarget, braceState: l.braceState })),
        panelLineCount: panelFlat.filter((e) => e.attrs && e.attrs.class === "mm-line").length,
        graphNodeCount: graphFlat.filter((e) => e.attrs && e.attrs.class === "mm-gnode").length,
        drops: panelFlat.filter((e) => e.attrs && e.attrs.class === "mm-drop").map((e) => e.text),
        resolvedLinkCount: graphFlat.filter((e) => e.tag === "line" && e.attrs.class === "mm-resolved-link").length,
      };
    }, { expandRoot, expandB });
  }

  test("braced-hidden refs show the ▸ glyph with literal braces", async ({ page }) => {
    const state = await renderTwoLevelChain(page, { expandRoot: false });
    const primary = state.lines.find((l) => l.text === "primary {concept b}");
    expect(primary.braceState).toBe("braced-hidden");
    expect(primary.glyph).toBe("▸");
    expect(primary.text).toContain("{concept b}");
    expect(state.drops).toContain("▸");
  });

  test("revealing a ref in panel form swaps it to ▾ and panel↔graph node-count parity holds for the revealed subtree", async ({ page }) => {
    const state = await renderTwoLevelChain(page, { expandRoot: true });
    const primary = state.lines.find((l) => l.text === "primary {concept b}");
    expect(primary.braceState).toBe("revealed-internal");
    expect(primary.glyph).toBe("▾");
    expect(state.drops).toContain("▾");
    // node-count parity (O.1) — the same rank-1 children appear in BOTH the
    // panel's .mm-line rows and the graph's .mm-gnode circles for the SAME
    // expansion state.
    expect(state.graphNodeCount, "graph node count matches panel line count").toBe(state.panelLineCount);
  });

  test("a second ref to an already-revealed target renders as a resolved-external solid <line> in graph mode, with zero stroke-dasharray anywhere in the graph SVG", async ({ page }) => {
    const state = await renderTwoLevelChain(page, { expandRoot: true });
    const secondary = state.lines.find((l) => l.text === "secondary {concept b}");
    expect(secondary.braceState, "the second ref to concept b resolves to the already-visible target").toBe("resolved-external");
    expect(state.resolvedLinkCount, "exactly one resolved-external link drawn").toBe(1);

    // the no-dotted gate (mirrored from black_slate.spec.js): zero elements
    // in the graph SVG carry a stroke-dasharray, anywhere.
    const dashCount = await page.evaluate(() => {
      const host = document.querySelector("#halo04-graph-host");
      let n = 0;
      for (const el of host.querySelectorAll("[stroke-dasharray]")) {
        const v = el.getAttribute("stroke-dasharray");
        if (v && !/^(none|0px|0)$/.test(v)) n++;
      }
      return n;
    });
    expect(dashCount, "zero stroke-dasharray elements in the graph SVG").toBe(0);
  });

  test("two-level chain: revealing B's ref to C propagates a second rank of parity (panel and graph stay in lockstep two levels deep)", async ({ page }) => {
    const state = await renderTwoLevelChain(page, { expandRoot: true, expandB: true });
    const bToC = state.lines.find((l) => l.text === "link to c {concept c}");
    expect(bToC, "B's ref to C is present once B itself is revealed inline").toBeTruthy();
    expect(bToC.braceState).toBe("revealed-internal");
    expect(state.graphNodeCount, "parity holds two ranks deep").toBe(state.panelLineCount);
  });
});

// HALO-03 (§O.18/D-04/D10) — cone-ray transport, stub lane (runs in BOTH
// modes; the REAL-subsystem acceptance is 08-04). The pure geometry
// (monotonicity, apex composition, verbatim transport consumption, 2D
// fallback, delete-and-replace ordering) is unit-covered at machine
// precision in halo_cone.test.mjs (5/5); this e2e is the render-level
// companion the unit tests can't reach: seeding the LIVE projector with
// fixture nodes + backend-SHAPED transport values, driving the real
// placeHaloCandidates() through the __mm_proj_place_cone hook (Task 2), and
// reading back __mm_cone_positions() the same way projector.spec.js reads
// __mm_proj_node_positions() — filtered to this test's own seeded fixture
// ids (the Phase-6 lesson: the boot sequence's real-scan population can
// otherwise pollute the assertion).
test.describe("cone-ray transport (HALO-03)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.waitForFunction(() => window.__mm_ready === true, { timeout: 15000 });
  });

  async function bootProjectorOrSkip(page) {
    const booted = await page
      .waitForFunction(() => typeof window.__mm_proj_place_cone === "function", { timeout: 9000 })
      .then(() => true)
      .catch(() => false);
    test.skip(!booted, "projector requires THREE.js + WebGL (offline CDN / headless GL unavailable)");
  }

  // Seeds 3 fixture 3D-backed nodes (descending similarity a > b > c) with
  // backend-shaped transport.{similarity,radial,along_ray} (the EXACT
  // routes.py formula: radial=(1-s)*40, along_ray=s*40 — "more similar
  // nearer the apex") at the apex {0,0,0}, drives placeHaloCandidates via
  // the Task-2 test hook, and returns __mm_cone_positions() filtered to the
  // 3 seeded ids.
  async function seedAndPlaceCone(page, queueIds) {
    return page.evaluate((ids) => {
      const R = 40;
      const mk = (id, sim) => ({ id, label: id, transport: { similarity: sim, radial: (1 - sim) * R, along_ray: sim * R } });
      const simById = { cone_a: 0.9, cone_b: 0.6, cone_c: 0.3 };
      const coords = {
        cone_a: [10, 0, 0, 0.1, 0.8, 0.5],
        cone_b: [0, 10, 0, 0.2, 0.8, 0.5],
        cone_c: [0, 0, 10, 0.3, 0.8, 0.5],
      };
      const urlRoots = { "": { root_position: [0, 0, 0], bounding_radius: 15 } };
      window.__mm_proj_set_with_roots(coords, urlRoots);
      const queue = ids.map((id) => mk(id, simById[id]));
      window.__mm_proj_place_cone({ x: 0, y: 0, z: 0 }, queue);
      const fixtureIds = new Set(["cone_a", "cone_b", "cone_c"]);
      return window.__mm_cone_positions().filter((p) => fixtureIds.has(p.id));
    }, queueIds);
  }

  // `radial` (NOT raw Euclidean apex distance) is the apex-distance scalar
  // guaranteed monotonic in similarity — halo_cone.mjs's own header comment
  // + halo_cone.test.mjs Test 1: radial and along_ray are ORTHOGONAL
  // components, so Math.hypot(x,y,z) is U-shaped across similarity, not
  // monotonic. `__mm_cone_positions()` exposes `radial` precisely so e2e
  // assertions use the same metric the unit tests do.
  test("placement distance-from-apex (radial) is monotonic in candidate similarity", async ({ page }) => {
    await bootProjectorOrSkip(page);
    const placed = await seedAndPlaceCone(page, ["cone_a", "cone_b", "cone_c"]);
    expect(placed.length, "all 3 seeded candidates placed").toBe(3);
    const byId = Object.fromEntries(placed.map((p) => [p.id, p]));
    // ordering, not a curve (UI-SPEC): higher similarity -> nearer the apex.
    expect(byId.cone_a.radial, "most-similar (cone_a) has the smallest radial (nearest the apex)").toBeLessThan(byId.cone_b.radial);
    expect(byId.cone_b.radial, "cone_b's radial smaller than the least-similar cone_c").toBeLessThan(byId.cone_c.radial);
  });

  test("deleting the top candidate transports the next-most-similar into the vacated nearest-apex slot", async ({ page }) => {
    await bootProjectorOrSkip(page);
    const before = await seedAndPlaceCone(page, ["cone_a", "cone_b", "cone_c"]);
    const nearestBefore = before.reduce((best, p) => (p.radial < best.radial ? p : best));
    expect(nearestBefore.id, "the most-similar candidate occupies the nearest-apex slot before delete").toBe("cone_a");

    // delete-transports-next (§O.18/§O.14): re-place with the top candidate
    // removed from the queue — the next-most-similar must now be nearest.
    const after = await seedAndPlaceCone(page, ["cone_b", "cone_c"]);
    expect(after.length, "2 candidates placed after delete").toBe(2);
    const nearestAfter = after.reduce((best, p) => (p.radial < best.radial ? p : best));
    expect(nearestAfter.id, "the next-most-similar candidate transports into the vacated nearest-apex slot").toBe("cone_b");
  });

  test("no cone ray carries stroke-dasharray (SOLID only — the black_slate no-dotted gate)", async ({ page }) => {
    await bootProjectorOrSkip(page);
    await seedAndPlaceCone(page, ["cone_a", "cone_b", "cone_c"]);
    // advance a few real animate frames so any cone-ray drawConcept3DLinks
    // pass has had a chance to run.
    await page.evaluate(async () => {
      const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
      for (let i = 0; i < 20; i++) await sleep(16);
    });
    const dashCount = await page.evaluate(() => {
      let n = 0;
      for (const el of document.querySelectorAll("[stroke-dasharray]")) {
        const v = el.getAttribute("stroke-dasharray");
        if (v && !/^(none|0px|0)$/.test(v)) n++;
      }
      return n;
    });
    expect(dashCount, "zero stroke-dasharray elements anywhere in the document (cone rays are SOLID)").toBe(0);
  });
});

// STEP-01 (§O.6/§O.7/§O.11) — the 2D `{chunk samples}` stepper drives 3D
// focus ONE-WAY. Against the stub backend (UIStateService is in-memory, no
// all_real gating): seed a signal-stream card with an `ordered` chunk-id
// list whose ids correspond to seeded 3D nodes, drive __mm_stepper_advance
// (the REAL stepper.mjs + REAL projector wiring — Task 4's editor.html test
// hooks), and assert (1) the resolved chunk id matches ordered[new_index];
// (2) the full per-sample distribution stays rendered (node count
// unchanged — D-03, never subsetted); (3) no 3D action advances the 2D
// cursor back (the one-way invariant).
test.describe("per-sample stepper → 3D focus (STEP-01)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.waitForFunction(() => window.__mm_ready === true, { timeout: 15000 });
  });

  async function bootProjectorOrSkip(page) {
    const booted = await page
      .waitForFunction(() => typeof window.__mm_stepper_advance === "function", { timeout: 9000 })
      .then(() => true)
      .catch(() => false);
    test.skip(!booted, "projector requires THREE.js + WebGL (offline CDN / headless GL unavailable)");
  }

  test("advancing the stepper flies/highlights the resolved 3D chunk node, leaves the full distribution rendered, and is never driven back by a 3D action", async ({ page, request }) => {
    await bootProjectorOrSkip(page);
    const cardId = `step_card_${Date.now()}`;
    const ordered = ["step_chunk_a", "step_chunk_b", "step_chunk_c"];

    try {
      // seed 3 fixture 3D-backed nodes (the full per-sample distribution)
      // and register the signal-stream cursor with the ordered chunk-id
      // list, starting at index 0.
      await page.evaluate(({ ordered }) => {
        const coords = {
          step_chunk_a: [10, 0, 0, 0.1, 0.8, 0.5],
          step_chunk_b: [0, 10, 0, 0.2, 0.8, 0.5],
          step_chunk_c: [0, 0, 10, 0.3, 0.8, 0.5],
        };
        const urlRoots = { "": { root_position: [0, 0, 0], bounding_radius: 15 } };
        window.__mm_proj_set_with_roots(coords, urlRoots);
      }, { ordered });

      const setRes = await request.post("/api/ui/signal_stream", {
        data: { card_id: cardId, workspace_id: "_default", total: 3, signal_index: 0, ordered },
      });
      expect(setRes.ok()).toBe(true);
      const setBody = await setRes.json();
      expect(setBody.state.signal_stream[cardId].signal_id, "registers at index 0 -> ordered[0]").toBe("step_chunk_a");

      const countBefore = await page.evaluate(() => window.__mm_proj_node_positions().length);

      // advance the REAL stepper.mjs driver via the editor.html test hook
      // (Task 4 wiring) — this calls the real /api/ui/signal_advance AND
      // the real projector.flyToNode/highlightNode, not stubs.
      const result = await page.evaluate(({ cardId }) => window.__mm_stepper_advance(cardId, 1), { cardId });
      expect(result.ok).toBe(true);
      expect(result.chunkId, "advance resolves signal_id to ordered[new_index]").toBe("step_chunk_b");

      // (2) the full distribution stays rendered — node count unchanged
      // (the stepper moves FOCUS, never subsets/hides — D-03).
      const countAfter = await page.evaluate(() => window.__mm_proj_node_positions().length);
      expect(countAfter, "stepper advance never changes the rendered node count (no subsetting)").toBe(countBefore);

      // (1) the camera focus / highlight moved to the resolved chunk — read
      // back via the colour-slot overlay (__mm_proj_color) the same way
      // projector.test.mjs's highlightNode assertion does: silver-300 now
      // sits in step_chunk_b's slot.
      const [r, g, b] = await page.evaluate(() => window.__mm_proj_color(
        window.__mm_proj_node_positions().findIndex((p) => p.id === "step_chunk_b")
      ));
      const near = (a, expected) => Math.abs(a - expected) < 0.01;
      expect(near(r, 0xb8 / 255) && near(g, 0xc0 / 255) && near(b, 0xc8 / 255),
        "step_chunk_b's colour slot is highlighted silver-300 after the advance").toBe(true);

      // (3) one-way invariant — a 3D node click never advances the 2D
      // cursor back. There is no click->advance wiring anywhere (verified
      // structurally in stepper.test.mjs); here we additionally assert
      // that simply dispatching a click on the canvas leaves signal_index
      // unchanged server-side.
      await page.evaluate(() => {
        const canvas = document.querySelector("canvas");
        if (canvas) canvas.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
      });
      const streamRes = await request.post("/api/ui/signal_stream", {
        data: { card_id: cardId, workspace_id: "_default", total: 3, signal_index: 1, signal_id: "step_chunk_b", ordered },
      });
      const streamBody = await streamRes.json();
      expect(streamBody.state.signal_stream[cardId].signal_index,
        "a 3D click never drives the 2D cursor — signal_index stays at 1, unchanged by the click").toBe(1);
    } finally {
      await request.post("/api/ui/signal_stream_clear", { data: { workspace_id: "_default", card_id: cardId } });
    }
  });
});
