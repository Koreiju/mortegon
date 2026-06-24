// Phase 7 — deep object-exploration gestures. This is the SHARED e2e spec
// for the whole phase (07-03 adds the first cases; later 07-0x plans append
// more to this SAME file rather than creating a parallel spec).
//
// 07-03 (EXPLORE-02 + §O.1a/D-04): external-{ref} recursive-panel
// propagation across the three brace render states (braced-hidden /
// revealed-internal / resolved-external) over ONE invariant graph link.
//
// These cases drive the magic-markdown model + DOM-vdom modules DIRECTLY via
// an in-page dynamic import of the served fe/*.mjs ES modules (the same
// modules backend/templates/editor.html itself imports, served with the
// correct text/javascript MIME by backend/main.py) — proving the render
// behavior against the REAL served module graph, not a mocked harness, while
// using fixtures the test controls (rather than depending on a live scan).
const { test, expect } = require("@playwright/test");

// Builds the fixture DOM via the served fe/ modules and returns the
// browser-side state the assertions need: rendered line texts, the brace
// state per ref-bearing line, dropdown glyphs, and (for the link case) a
// rendered SOLID line element in the graph-form SVG.
async function renderRefFixture(page, { expandPrimary = false } = {}) {
  return page.evaluate(async (expand) => {
    const mm = await import("/static/js/fe/magic_markdown.mjs");
    const panelMod = await import("/static/js/fe/magic_markdown_panel.mjs");
    const { parse, buildRegistry, renderPanel, toggle } = mm;
    const { panelVDom, graphVDom, flattenVDom } = panelMod;

    // A host card with an external {ref} to "details page" (braced-hidden
    // until revealed) AND a second occurrence of the SAME ref (used by the
    // resolved-external case below).
    const host = parse([
      "catalog entry",
      "\tprimary link {details page}",
      "\tsecondary link {details page}",
    ].join("\n"));
    const details = parse([
      "details page",
      "\turl : /details/example",
      "\tmediatype : Text",
    ].join("\n"));
    const registry = buildRegistry([details]);

    let expanded = new Set();
    if (expand) {
      const collapsed = renderPanel(host, { registry, expanded });
      const primaryPath = collapsed.find((l) => l.text === "primary link {details page}").path;
      expanded = toggle(expanded, primaryPath);
    }

    const lines = renderPanel(host, { registry, expanded });
    const panelFlat = flattenVDom(panelVDom(host, { registry, expanded }));
    const graphFlat = flattenVDom(graphVDom(host, { registry, expanded }));

    // mount into a real host div so computed-style / DOM assertions work.
    const container = document.createElement("div");
    container.id = "ref-fixture-host";
    document.body.appendChild(container);
    const dom = (function realise(spec) {
      const SVG_TAGS = new Set(["svg", "line", "circle", "g", "path", "ellipse", "text"]);
      const node = SVG_TAGS.has(spec.tag)
        ? document.createElementNS("http://www.w3.org/2000/svg", spec.tag)
        : document.createElement(spec.tag);
      for (const [k, v] of Object.entries(spec.attrs || {})) node.setAttribute(k, v);
      if (spec.text != null) node.textContent = spec.text;
      for (const c of spec.children || []) node.appendChild(realise(c));
      return node;
    })(panelVDom(host, { registry, expanded }));
    container.appendChild(dom);

    return {
      lines: lines.map((l) => ({ text: l.text, glyph: l.glyph, refTarget: l.refTarget, braceState: l.braceState, source: l.source })),
      panelTexts: panelFlat.filter((e) => e.text != null).map((e) => e.text),
      drops: panelFlat.filter((e) => e.attrs && e.attrs.class === "mm-drop").map((e) => e.text),
      readthrough: panelFlat.filter((e) => e.attrs && e.attrs.class === "mm-text mm-readthrough").map((e) => e.text),
      graphLineCount: graphFlat.filter((e) => e.tag === "line").length,
    };
  }, expandPrimary);
}

test.beforeEach(async ({ page }) => {
  await page.goto("/static/js/fe/demo.html");
  await page.waitForLoadState("networkidle");
});

test("ref: an unrevealed external {ref} renders braced-hidden (braces present, ▸ glyph, no children)", async ({ page }) => {
  const state = await renderRefFixture(page, { expandPrimary: false });
  const primary = state.lines.find((l) => l.text === "primary link {details page}");
  expect(primary, "the primary ref line is present").toBeTruthy();
  expect(primary.braceState, "braced-hidden by default").toBe("braced-hidden");
  expect(primary.glyph, "▸ collapsed dropdown glyph").toBe("▸");
  expect(primary.text, "braces remain literal in the rendered text").toContain("{details page}");
  expect(state.readthrough.length, "no inline read-through children yet").toBe(0);
  expect(state.drops, "the dropdown char is rendered in the DOM").toContain("▸");
});

test("ref: toggling the fold reveals rank-1 child lines inline (revealed-internal, braces drop)", async ({ page }) => {
  const state = await renderRefFixture(page, { expandPrimary: true });
  const primary = state.lines.find((l) => l.text === "primary link {details page}");
  expect(primary.braceState, "revealed-internal after the fold commits").toBe("revealed-internal");
  expect(primary.glyph, "▾ expanded dropdown glyph").toBe("▾");
  // the referenced node's rank-1 fields propagated in as read-through lines
  // (the duplicate-instance proxy, N.6) — braces drop, children render
  // inline beneath the parent.
  expect(state.readthrough).toEqual(["url : /details/example", "mediatype : Text"]);
  expect(state.drops).toContain("▾");
});

test("ref: a SECOND occurrence of an already-revealed {ref} resolves to resolved-external (solid link, no duplicate reveal, no dasharray)", async ({ page }) => {
  const state = await renderRefFixture(page, { expandPrimary: true });
  const secondary = state.lines.find((l) => l.text === "secondary link {details page}");
  expect(secondary.braceState, "the second occurrence resolves to the already-visible target").toBe("resolved-external");
  // resolved-external never duplicates the propagated panel a second time —
  // exactly ONE set of read-through children exists for "details page"
  // across the whole render (asserted above: readthrough has exactly 2
  // entries, not 4), and the secondary line itself carries no "expanded"
  // children of its own.
  expect(state.lines.filter((l) => l.source === "expanded").length).toBe(2);

  // no-dasharray / no-dotted invariant (reuses the black_slate.spec.js idiom):
  // any line/path/polyline rendered anywhere on the page (including this
  // fixture's graph-form SVG, mounted separately below) must be solid.
  const dashCheck = await page.evaluate(async () => {
    const panelMod = await import("/static/js/fe/magic_markdown_panel.mjs");
    const mm = await import("/static/js/fe/magic_markdown.mjs");
    const { parse, buildRegistry, renderPanel, toggle } = mm;
    const host = parse(["catalog entry", "\tprimary link {details page}", "\tsecondary link {details page}"].join("\n"));
    const details = parse(["details page", "\turl : /details/example", "\tmediatype : Text"].join("\n"));
    const registry = buildRegistry([details]);
    const collapsed = renderPanel(host, { registry, expanded: new Set() });
    const primaryPath = collapsed.find((l) => l.text === "primary link {details page}").path;
    const expanded = toggle(new Set(), primaryPath);
    const graphSpec = panelMod.graphVDom(host, { registry, expanded });
    const realise = (spec) => {
      const SVG_TAGS = new Set(["svg", "line", "circle", "g", "path", "ellipse", "text"]);
      const node = SVG_TAGS.has(spec.tag)
        ? document.createElementNS("http://www.w3.org/2000/svg", spec.tag)
        : document.createElement(spec.tag);
      for (const [k, v] of Object.entries(spec.attrs || {})) node.setAttribute(k, v);
      if (spec.text != null) node.textContent = spec.text;
      for (const c of spec.children || []) node.appendChild(realise(c));
      return node;
    };
    const container = document.createElement("div");
    container.id = "ref-fixture-graph-host";
    document.body.appendChild(container);
    container.appendChild(realise(graphSpec));
    return true;
  });
  expect(dashCheck).toBe(true);

  const bad = await page.evaluate(() => {
    const out = [];
    for (const el of document.querySelectorAll("#ref-fixture-graph-host line, #ref-fixture-graph-host path, #ref-fixture-graph-host polyline")) {
      const da = getComputedStyle(el).strokeDasharray;
      if (da && !/^(none|0px|0)$/.test(da)) out.push(`stroke-dasharray=${da}`);
    }
    return out;
  });
  expect(bad, `dashed/dotted lines found in the ref fixture's graph form:\n${bad.join("\n")}`).toEqual([]);
});

test("ref: black_slate.spec's no-dotted-overlay invariant stays satisfied on the served editor", async ({ page }) => {
  // a cold first-ever navigation to "/" can trigger a real UMAP recompute on
  // the editor's boot fetch (the same characteristic black_slate.spec.js's
  // own first test absorbs); allow extra time before the load-state wait so
  // this case is stable whether it runs first-in-process or after warmup.
  test.setTimeout(60000);
  await page.goto("/");
  await page.waitForLoadState("networkidle", { timeout: 45000 });
  const bad = await page.evaluate(() => {
    const out = [];
    for (const el of document.querySelectorAll("line, path, polyline")) {
      const da = getComputedStyle(el).strokeDasharray;
      if (da && !/^(none|0px|0)$/.test(da)) out.push(`stroke-dasharray=${da}`);
    }
    return out;
  });
  expect(bad, `dotted/dashed overlays found on the live editor:\n${bad.join("\n")}`).toEqual([]);
});
