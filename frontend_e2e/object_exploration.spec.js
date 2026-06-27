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

// ── 07-05 (EXPLORE-03 + EXPLORE-01-hover): the seven-gesture DOM capture wired
// into magic_markdown_panel.mjs::mount(). These cases dispatch REAL DOM events
// (contextmenu / mousedown→mousemove→mouseup / mouseover) through the SERVED
// mount() and assert the browser-level gesture→handler+effect contract end-to-
// end. The backend mutations the handlers ultimately fire (inherit_types edge
// create, edge-delete) are proven separately by 07-04's gateway unit suite
// (9/9) + test_edge_inherit_types.py (7/7) and 07-01's next_rank pytest (4/4);
// here we prove the in-browser gesture capture + render + solid-affordance.

test("hover: hovering a typed token fires the next-rank preview, and renderTypedPanel renders the type graph (super + typed params + → output)", async ({ page }) => {
  const result = await page.evaluate(async () => {
    const mm = await import("/static/js/fe/magic_markdown.mjs");
    const panelMod = await import("/static/js/fe/magic_markdown_panel.mjs");
    const { parse, renderTypedPanel } = mm;
    const { mount } = panelMod;

    // (a) mount a panel and prove hover capture: mouseover a token reports its
    // data-path so the caller can fetch /concepts/{id}/next_rank (mount itself
    // never fetches — backend computes, frontend renders, D10).
    const host = document.createElement("div");
    document.body.appendChild(host);
    const root = parse(["driver", "\tcommand_executor : str = http://127.0.0.1:4444"].join("\n"));
    const hovers = [];
    mount(host, root, { mode: "panel" }, { onHoverPreview: (p, kind) => hovers.push({ p, kind }) });
    const token = host.querySelector('.mm-text, .mm-line, .mm-drop');
    token.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));

    // (b) prove the next-rank RENDER (the type graph the hover preview shows):
    // a python-native function node renders typed input rows + a → output row.
    const fnNode = {
      type_hint: "python_function",
      data: JSON.stringify({
        signature: "(self, url: str, samples: int) -> ScanResult",
        ports: {
          inputs: [{ name: "self", type: "WebBrowser" }, { name: "url", type: "str" }, { name: "samples", type: "int" }],
          outputs: [{ name: "return", type: "ScanResult" }],
        },
      }),
    };
    const typed = renderTypedPanel(fnNode);
    return {
      hovers,
      typedTexts: typed.map((l) => l.text),
    };
  });
  expect(result.hovers.length, "mouseover a token fires onHoverPreview exactly once").toBe(1);
  expect(result.hovers[0].p, "the preview carries the hovered token's data-path").not.toBeNull();
  // the next-rank type graph: typed input rows (self is dropped) + the → output
  expect(result.typedTexts).toContain("url : str");
  expect(result.typedTexts).toContain("samples : int");
  expect(result.typedTexts.some((t) => t.startsWith("→ ") && t.includes("ScanResult")), "an inferred → output-type row is rendered").toBe(true);
});

test("drag-wire: mousedown→mousemove→mouseup across graph nodes fires WIRE_LINK and draws a SOLID transient line (no dasharray)", async ({ page }) => {
  const result = await page.evaluate(async () => {
    const mm = await import("/static/js/fe/magic_markdown.mjs");
    const panelMod = await import("/static/js/fe/magic_markdown_panel.mjs");
    const { parse } = mm;
    const { mount } = panelMod;

    const host = document.createElement("div");
    document.body.appendChild(host);
    // two top-level lines → graphVDom emits two .mm-gnode nodes.
    const root = parse(["DuckDuckGo", "\tsource node", "\ttarget node"].join("\n"));
    const wires = [];
    // capture the realized graph root: mount()'s listeners live on it, so
    // events must be dispatched ON it (or a descendant) — they bubble UP to it,
    // never down from the outer host.
    const dom = mount(host, root, { mode: "graph" }, { onWire: (s, t) => wires.push({ s, t }) });
    const gnodes = dom.querySelectorAll(".mm-gnode");
    const src = gnodes[0], tgt = gnodes[gnodes.length - 1];

    src.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, button: 0, clientX: 0, clientY: 0 }));
    // move well past DRAG_MOVE_PX (4) to flip into drag mode + draw the line —
    // dispatched on a descendant of dom so it reaches dom's mousemove listener.
    src.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: 120, clientY: 80 }));

    // assert DURING the drag (before mouseup tears it down) that a transient
    // SOLID line exists with no stroke-dasharray.
    const dragLine = host.querySelector("line.mm-drag-line");
    const dash = dragLine ? (dragLine.getAttribute("stroke-dasharray") || getComputedStyle(dragLine).strokeDasharray) : "MISSING";

    tgt.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, button: 0, clientX: 120, clientY: 80 }));
    const lineAfter = host.querySelector("line.mm-drag-line");

    return {
      wires,
      srcPath: src.getAttribute("data-path"),
      tgtPath: tgt.getAttribute("data-path"),
      hadDragLine: !!dragLine,
      dash,
      removedAfter: !lineAfter,
    };
  });
  expect(result.hadDragLine, "a transient drag line is drawn during the drag").toBe(true);
  expect(/^(none|0px|0|)$/.test(result.dash), `the transient drag line is SOLID (no dasharray), got: ${result.dash}`).toBe(true);
  expect(result.wires.length, "mouseup on a different node fires WIRE_LINK once").toBe(1);
  expect(result.wires[0].s, "source path").toBe(result.srcPath);
  expect(result.wires[0].t, "target path").toBe(result.tgtPath);
  expect(result.removedAfter, "the transient line is torn down on mouseup").toBe(true);
});

test("double-right-delete: two contextmenu within the debounce window synthesize DELETE_REF (a single one folds)", async ({ page }) => {
  const result = await page.evaluate(async () => {
    const mm = await import("/static/js/fe/magic_markdown.mjs");
    const panelMod = await import("/static/js/fe/magic_markdown_panel.mjs");
    const { parse, buildRegistry } = mm;
    const { mount } = panelMod;

    // a ref-bearing line is the deletable token (a {ref} occurrence).
    const host = document.createElement("div");
    document.body.appendChild(host);
    const root = parse(["catalog", "\tlink {details}"].join("\n"));
    const details = parse(["details", "\turl : /d"].join("\n"));
    const registry = buildRegistry([details]);
    const folds = [], deletes = [];
    mount(host, root, { mode: "panel", registry, expanded: new Set() },
      { onToggle: (p) => folds.push(p), onDelete: (p) => deletes.push(p) });

    // a child token (.mm-text, classifyTarget kind "token") folds on a single
    // right-click AND deletes on a double — the root line is kind "self"
    // (collapse), so target the ref token specifically.
    const target = [...host.querySelectorAll(".mm-text")].find((e) => /details|link/.test(e.textContent)) || host.querySelector(".mm-text");
    // single right-click → fold
    target.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, button: 2 }));
    const foldsAfterSingle = folds.length;
    // immediate second right-click on the SAME target (within 400ms) → DELETE
    target.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, button: 2 }));

    return { foldsAfterSingle, foldsTotal: folds.length, deletes: deletes.length };
  });
  expect(result.foldsAfterSingle, "a single right-click resolves a fold").toBe(1);
  expect(result.deletes, "the second right-click within the window synthesizes a DELETE_REF").toBe(1);
  expect(result.foldsTotal, "the second contextmenu does NOT add a second fold (it deletes)").toBe(1);
});

test("fold-preservation: collapsing a parent and re-expanding restores a nested fold (M.6)", async ({ page }) => {
  const restored = await page.evaluate(async () => {
    const mm = await import("/static/js/fe/magic_markdown.mjs");
    const { parse, buildRegistry, renderPanel, toggle } = mm;
    // a host whose {ref} target itself contains a nested {ref}, so there is a
    // rank-2 fold whose state must survive a rank-1 collapse/re-expand.
    const host = parse(["root", "\touter {mid}"].join("\n"));
    const mid = parse(["mid", "\tinner {leaf}"].join("\n"));
    const leaf = parse(["leaf", "\tval : 1"].join("\n"));
    const registry = buildRegistry([mid, leaf]);

    let expanded = new Set();
    const pathOf = (exp, text) => renderPanel(host, { registry, expanded: exp }).find((l) => l.text === text)?.path;
    const hasLeaf = (exp) => renderPanel(host, { registry, expanded: exp }).some((l) => l.text === "val : 1");
    // "outer {mid}" is a stable rank-1 line — its path is constant regardless
    // of expansion, so capture it once and toggle it consistently.
    const outerPath = pathOf(new Set(), "outer {mid}");
    expanded = toggle(expanded, outerPath);                 // open outer (rank-1)
    const innerPath = pathOf(expanded, "inner {leaf}");     // now visible
    expanded = toggle(expanded, innerPath);                 // open inner (rank-2)
    const beforeHasInner = hasLeaf(expanded);               // both open → leaf visible
    expanded = toggle(expanded, outerPath);                 // collapse outer (inner's fold state RETAINED in the set)
    const afterCollapseHasInner = hasLeaf(expanded);        // subtree hidden
    expanded = toggle(expanded, outerPath);                 // re-expand outer
    const afterReexpandHasInner = hasLeaf(expanded);        // M.6: inner restored
    return { beforeHasInner, afterCollapseHasInner, afterReexpandHasInner };
  });
  expect(restored.beforeHasInner, "the rank-2 leaf is visible when both folds are open").toBe(true);
  expect(restored.afterCollapseHasInner, "collapsing the parent hides the nested subtree").toBe(false);
  expect(restored.afterReexpandHasInner, "re-expanding restores the nested fold (M.6 preservation)").toBe(true);
});

// ── 07-06 (EXPLORE-04 / §N): the DuckDuckGo walkthrough, driven against the
// STUB backend (no real subsystems). Mirrors the §N canonical example
// (docs/frontend/object_exploration.md §5.1): author self=duckduckgo,
// drag-wire the (stub) WebBrowser scanner with inherit_types, assert the
// panel shows "DuckDuckGo / {scanner}" with NO types, right-click {scanner}
// reveals type-stripped rank-1 url{}/dom{}, and advance the {chunk samples}
// iterator asserting per-sample focus changes.

test("duckduckgo walkthrough: drag-wire inherit_types yields a NO-TYPES panel, right-click reveals type-stripped url{}/dom{}, and {chunk samples} per-sample iteration advances (§N)", async ({ page }) => {
  const result = await page.evaluate(async () => {
    const mm = await import("/static/js/fe/magic_markdown.mjs");
    const panelMod = await import("/static/js/fe/magic_markdown_panel.mjs");
    const { parse, buildRegistry, renderPanel, toggle, iterableNode, advanceSignal } = mm;
    const { mount } = panelMod;

    // (1) author self=duckduckgo referencing {scanner} — purely structural,
    // no type presentation per N.4/N.5.
    const duckduckgo = parse(["DuckDuckGo", "\t{scanner}"].join("\n"));

    // (2) the (stub) WebBrowser scanner's rank-1 structure: a function-shaped
    // node whose OWN fields are type-stripped (N.5 — outputs blank unless
    // bound/inverse-referenced); a downstream {ref} ("scan for duckduckgo
    // url") supplies the iterable chunk distribution (N.9).
    const scanForUrl = node_with_samples();
    function node_with_samples() {
      const samples = [
        parse(["chunk", "\ttitle : sample one"].join("\n")),
        parse(["chunk", "\ttitle : sample two"].join("\n")),
        parse(["chunk", "\ttitle : sample three"].join("\n")),
      ];
      return iterableNode("scan for duckduckgo url", samples);
    }
    const scanner = parse([
      "scanner",
      "\tsearch {}",
      "\t{paginate}",
      "\turl {duckduckgo url}",
      "\tdom {scan for duckduckgo url}",
    ].join("\n"));
    const duckduckgoUrl = parse(["duckduckgo url", "\thttps://www.duckduckgo.com/"].join("\n"));

    const registry = buildRegistry([scanner, duckduckgoUrl, scanForUrl]);

    // (3) drag-wire-equivalent: mount DuckDuckGo in graph mode and fire a
    // real mousedown->mousemove->mouseup drag onto a node representing the
    // scanner, asserting WIRE_LINK fires (the gateway issues the real
    // inherit_types:true /api/editor/link request — proven by 07-04's
    // gateway unit suite; this e2e proves the gesture capture itself).
    const wireHost = document.createElement("div");
    document.body.appendChild(wireHost);
    const wireRoot = parse(["DuckDuckGo", "\t{scanner}", "\tscanner"].join("\n"));
    const wires = [];
    const wireDom = mount(wireHost, wireRoot, { mode: "graph" }, { onWire: (s, t) => wires.push({ s, t }) });
    const gnodes = wireDom.querySelectorAll(".mm-gnode");
    const src = gnodes[gnodes.length - 1]; // the "scanner" node
    const tgt = gnodes[0];                 // the "DuckDuckGo" root node
    src.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, button: 0, clientX: 0, clientY: 0 }));
    src.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: 50, clientY: 50 }));
    const dragLine = wireHost.querySelector("line.mm-drag-line");
    const dragDash = dragLine ? (dragLine.getAttribute("stroke-dasharray") || getComputedStyle(dragLine).strokeDasharray) : "MISSING";
    tgt.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, button: 0, clientX: 50, clientY: 50 }));

    // (4) panel render — DuckDuckGo presents NO types (rank-1 minimalism,
    // N.4/N.5): purely structural text, never a `key : Type = value` slot.
    const collapsedLines = renderPanel(duckduckgo, { registry, expanded: new Set() });
    const panelTexts = collapsedLines.map((l) => l.text);

    // (5) right-click {scanner} (single right-click -> TOGGLE_FOLD) reveals
    // its rank-1 structure inline, braces dropping, still type-stripped.
    const panelHost = document.createElement("div");
    document.body.appendChild(panelHost);
    let expanded = new Set();
    const folds = [];
    const panelDom = mount(panelHost, duckduckgo, { mode: "panel", registry, expanded },
      { onToggle: (p) => folds.push(p) });
    const scannerToken = [...panelHost.querySelectorAll(".mm-text")].find((e) => /scanner/.test(e.textContent));
    scannerToken.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, button: 2 }));
    expanded = toggle(expanded, folds[0]);
    const revealedLines = renderPanel(duckduckgo, { registry, expanded });
    const revealedTexts = revealedLines.map((l) => l.text);

    // (6) reveal url{}/dom{} themselves (rank-2: expand "scanner"'s own
    // {duckduckgo url} and {scan for duckduckgo url} refs) — still
    // type-stripped at every rank.
    const urlLine = revealedLines.find((l) => l.text === "url {duckduckgo url}");
    const domLine = revealedLines.find((l) => l.text === "dom {scan for duckduckgo url}");
    let expanded2 = toggle(expanded, urlLine.path);
    expanded2 = toggle(expanded2, domLine.path);
    const fullyRevealed = renderPanel(duckduckgo, { registry, expanded: expanded2 });
    const fullyRevealedTexts = fullyRevealed.map((l) => l.text);

    // (7) {chunk samples} per-sample iteration (N.9, advanceSignal model):
    // the iterable "scan for duckduckgo url" target renders ONE sample at a
    // time; advancing the signal index changes which sample's fields inline.
    const domPath = domLine.path;
    let signals = new Map();
    const sampleAt = (sigMap) => {
      const ls = renderPanel(duckduckgo, { registry, expanded: expanded2, signals: sigMap });
      return (ls.find((l) => l.text === "title : sample one")
        || ls.find((l) => l.text === "title : sample two")
        || ls.find((l) => l.text === "title : sample three") || {}).text;
    };
    const sample0 = sampleAt(signals);
    signals = advanceSignal(signals, domPath, 3);
    const sample1 = sampleAt(signals);
    signals = advanceSignal(signals, domPath, 3);
    const sample2 = sampleAt(signals);
    signals = advanceSignal(signals, domPath, 3);
    const sample3 = sampleAt(signals); // wraps back to sample0's content

    return {
      panelTexts, revealedTexts, fullyRevealedTexts,
      hadDragLine: !!dragLine, dragDash, wires,
      srcPath: src.getAttribute("data-path"), tgtPath: tgt.getAttribute("data-path"),
      sample0, sample1, sample2, sample3,
    };
  });

  // -- (3) drag-wire gesture capture --
  expect(result.hadDragLine, "a transient drag line is drawn during the drag-wire gesture").toBe(true);
  expect(/^(none|0px|0|)$/.test(result.dragDash), `the drag-wire line is SOLID (no dasharray), got: ${result.dragDash}`).toBe(true);
  expect(result.wires.length, "the drag from scanner onto DuckDuckGo fires WIRE_LINK once").toBe(1);
  expect(result.wires[0].s).toBe(result.srcPath);
  expect(result.wires[0].t).toBe(result.tgtPath);

  // -- (4) rank-1 minimalism: DuckDuckGo's panel carries NO typed colon-slot --
  expect(result.panelTexts).toContain("{scanner}");
  for (const t of result.panelTexts) {
    expect(t, `DuckDuckGo's own panel text must carry no typed colon-slot: ${t}`).not.toMatch(/\w+\s*:\s*\w+\s*=/);
  }

  // -- (5) right-click reveal: {scanner} unfolds inline, still type-stripped --
  expect(result.revealedTexts).toContain("url {duckduckgo url}");
  expect(result.revealedTexts).toContain("dom {scan for duckduckgo url}");
  for (const t of result.revealedTexts) {
    expect(t, `revealed scanner fields must stay type-stripped: ${t}`).not.toMatch(/\w+\s*:\s*\w+\s*=/);
  }

  // -- (6) rank-2 reveal of url{}/dom{} stays type-stripped --
  expect(result.fullyRevealedTexts.some((t) => /https:\/\/www\.duckduckgo\.com\//.test(t)), "the duckduckgo url's literal value is reachable").toBe(true);
  expect(result.fullyRevealedTexts).toContain("search {}");
  expect(result.fullyRevealedTexts).toContain("{paginate}");

  // -- (7) {chunk samples} per-sample iteration advances and wraps --
  expect(result.sample0, "sample 0 is the first chunk").toBe("title : sample one");
  expect(result.sample1, "advancing the signal moves to the second chunk").toBe("title : sample two");
  expect(result.sample2, "advancing again moves to the third chunk").toBe("title : sample three");
  expect(result.sample3, "a fourth advance wraps back to the first chunk").toBe("title : sample one");

  // -- Forbidden Concepts guard: no stroke-dasharray anywhere on the page --
  const bad = await page.evaluate(() => {
    const out = [];
    for (const el of document.querySelectorAll("line, path, polyline")) {
      const da = getComputedStyle(el).strokeDasharray;
      if (da && !/^(none|0px|0)$/.test(da)) out.push(`stroke-dasharray=${da}`);
    }
    return out;
  });
  expect(bad, `dashed/dotted lines found anywhere on the page during the duckduckgo walkthrough:\n${bad.join("\n")}`).toEqual([]);
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
