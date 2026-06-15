/**
 * magic_markdown.test.mjs — verifies the magic-markdown panel core.
 * Run: node backend/static/js/fe/magic_markdown.test.mjs
 */
import assert from "node:assert";
import {
  parse, serialize, rootField, buildRegistry, refTarget, refTargets,
  renderPanel, linesToText, toggle, GLYPH_COLLAPSED, GLYPH_EXPANDED,
  iterableNode, isIterable, advanceSignal, renderGraph, parentPath,
} from "./magic_markdown.mjs";

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log("  PASS  " + name); passed++; }
  catch (e) { console.log("  FAIL  " + name + ": " + e.message); failed++; }
}

// ── grammar: parse/serialize round-trip (tabs+newlines only) ──────────────
test("round-trip: single-root panel", () => {
  const text = "DuckDuckGo\n\tscanner {scan for duckduckgo url}\n\tport : 80";
  assert.strictEqual(serialize(parse(text)), text);
});
test("round-trip: forest / flat content tree", () => {
  const text = "line a\nline b\n\tchild : 1\nline c";
  assert.strictEqual(serialize(parse(text)), text);
});
test("names may contain spaces (tree over tabs+newlines only)", () => {
  const n = parse("scan for duckduckgo url\n\tsearch {}");
  assert.strictEqual(rootField(n), "scan for duckduckgo url");
  assert.strictEqual(n.children[0].text, "search {}");
});

// ── refs ──────────────────────────────────────────────────────────────────
test("refTarget / refTargets extract {ref} (spaces ok)", () => {
  assert.strictEqual(refTarget("dom {scan for duckduckgo url}"), "scan for duckduckgo url");
  assert.deepStrictEqual(refTargets("a {x} b {y z}"), ["x", "y z"]);
  assert.strictEqual(refTarget("no ref here"), null);
});

// ── the magic: in-text dropdown expansion of an external node ────────────────
const A = parse("DuckDuckGo\n\tscanner {scan for duckduckgo url}");
const B = parse("scan for duckduckgo url\n\tsearch {}\n\t{paginate}\n\tchunk {chunk samples}");
const C = parse("chunk samples\n\turl : https://duckduckgo.com\n\ttitle : DuckDuckGo");
const registry = buildRegistry([B, C]);

test("collapsed: a {ref} to a registered node shows the ▸ dropdown char", () => {
  const lines = renderPanel(A, { registry, expanded: new Set() });
  const refLine = lines.find((l) => l.refTarget === "scan for duckduckgo url");
  assert.ok(refLine, "ref line present");
  assert.strictEqual(refLine.glyph, GLYPH_COLLAPSED);
  // nothing inlined while collapsed
  assert.ok(!lines.some((l) => l.source === "expanded"));
});

test("expanded: ▾ char + the target's rank-1 fields inlined at depth+1", () => {
  // expand the scanner ref line (its path)
  const collapsed = renderPanel(A, { registry, expanded: new Set() });
  const refPath = collapsed.find((l) => l.refTarget === "scan for duckduckgo url").path;
  const lines = renderPanel(A, { registry, expanded: new Set([refPath]) });
  const refLine = lines.find((l) => l.path === refPath);
  assert.strictEqual(refLine.glyph, GLYPH_EXPANDED);
  const inlined = lines.filter((l) => l.source === "expanded");
  const texts = inlined.map((l) => l.text);
  assert.deepStrictEqual(texts, ["search {}", "{paginate}", "chunk {chunk samples}"]);
  // inlined one level deeper than the ref line
  assert.ok(inlined.every((l) => l.depth === refLine.depth + 1));
});

test("recursive: expanding an inlined ref pulls the next rank too", () => {
  const c0 = renderPanel(A, { registry, expanded: new Set() });
  const p1 = c0.find((l) => l.refTarget === "scan for duckduckgo url").path;
  const c1 = renderPanel(A, { registry, expanded: new Set([p1]) });
  // the inlined "chunk {chunk samples}" references node C
  const p2 = c1.find((l) => l.refTarget === "chunk samples").path;
  const c2 = renderPanel(A, { registry, expanded: new Set([p1, p2]) });
  const deep = c2.filter((l) => l.source === "expanded" && l.text.startsWith("url :"));
  assert.strictEqual(deep.length, 1, "C's url field inlined");
  assert.strictEqual(deep[0].text, "url : https://duckduckgo.com");
});

test("a {ref} to an UNREGISTERED node has no dropdown (braced-hidden stays literal)", () => {
  const lines = renderPanel(B, { registry, expanded: new Set() });
  const pag = lines.find((l) => l.text === "{paginate}");
  assert.strictEqual(pag.glyph, "");          // 'paginate' not in registry
});

test("cycle guard: self-reference does not loop forever", () => {
  const S = parse("loop\n\tself {loop}");
  const reg = buildRegistry([S]);
  const open = renderPanel(S, { registry: reg, expanded: new Set() });
  const p = open.find((l) => l.refTarget === "loop").path;
  // expand repeatedly along the same target — must terminate
  const lines = renderPanel(S, { registry: reg, expanded: new Set([p, p + "/0"]) });
  assert.ok(lines.length < 50, "terminates (no infinite expansion)");
});

test("toggle flips a dropdown path", () => {
  let e = new Set();
  e = toggle(e, "0.0"); assert.ok(e.has("0.0"));
  e = toggle(e, "0.0"); assert.ok(!e.has("0.0"));
});

// ── per-signal iteration (N.9): one sample at a time, no "N of M" overlay ────
const ITER = iterableNode("chunk samples", [
  parse("s0\n\turl : https://a\n\ttitle : Alpha"),
  parse("s1\n\turl : https://b\n\ttitle : Beta"),
  parse("s2\n\turl : https://c\n\ttitle : Gamma"),
]);
const P = parse("Report\n\tchunk {chunk samples}");
const regIter = buildRegistry([ITER]);

test("iterable: expanded ref inlines ONLY the current sample's fields", () => {
  const c0 = renderPanel(P, { registry: regIter, expanded: new Set() });
  const refPath = c0.find((l) => l.refTarget === "chunk samples").path;
  // signal index 0
  let lines = renderPanel(P, { registry: regIter, expanded: new Set([refPath]),
                               signals: new Map([[refPath, 0]]) });
  let inlined = lines.filter((l) => l.source === "expanded").map((l) => l.text);
  assert.deepStrictEqual(inlined, ["url : https://a", "title : Alpha"]);
  // advance to signal index 2
  lines = renderPanel(P, { registry: regIter, expanded: new Set([refPath]),
                           signals: new Map([[refPath, 2]]) });
  inlined = lines.filter((l) => l.source === "expanded").map((l) => l.text);
  assert.deepStrictEqual(inlined, ["url : https://c", "title : Gamma"]);
});

test("iterable: ref line carries signal meta for the REPL, not a panel overlay", () => {
  const lines = renderPanel(P, { registry: regIter, expanded: new Set() });
  const refLine = lines.find((l) => l.refTarget === "chunk samples");
  assert.strictEqual(refLine.iterable, true);
  assert.strictEqual(refLine.signalTotal, 3);
  // the visible panel text shows NO "1 of 3" — only the ref token itself
  assert.ok(!/\d+\s*of\s*\d+/i.test(linesToText(lines)));
});

test("advanceSignal cycles 0→1→2→0", () => {
  const path = "x";
  let s = new Map([[path, 0]]);
  s = advanceSignal(s, path, 3); assert.strictEqual(s.get(path), 1);
  s = advanceSignal(s, path, 3); assert.strictEqual(s.get(path), 2);
  s = advanceSignal(s, path, 3); assert.strictEqual(s.get(path), 0);
});

test("isIterable distinguishes a distribution from a plain node", () => {
  assert.ok(isIterable(ITER));
  assert.ok(!isIterable(parse("plain\n\ta : 1")));
});

// ── graph half of the dialect: minimal circular nodes, parity with panel ────
test("graph form: node-count parity with the panel (O.1)", () => {
  const opts = { registry, expanded: new Set() };
  const panel = renderPanel(A, opts);
  const { nodes } = renderGraph(A, opts);
  assert.strictEqual(nodes.length, panel.length);
});

test("graph form: each node carries ONLY text — no chrome fields (V.5)", () => {
  const { nodes } = renderGraph(A, { registry });
  for (const n of nodes) {
    assert.strictEqual(typeof n.label, "string");
    // a minimalist node: no title/header/button keys
    assert.ok(!("title" in n) && !("buttons" in n) && !("header" in n));
  }
});

test("graph form: containment is a spanning tree (each non-root has one parent edge)", () => {
  const opts = { registry, expanded: new Set([
    renderPanel(A, { registry }).find((l) => l.refTarget === "scan for duckduckgo url").path,
  ]) };
  const { nodes, edges } = renderGraph(A, opts);
  const roots = nodes.filter((n) => parentPath(n.id) === null ||
    !nodes.some((m) => m.id === parentPath(n.id)));
  // edges = nodes - roots (a forest of spanning trees)
  assert.strictEqual(edges.length, nodes.length - roots.length);
});

test("panel↔graph are projections of ONE model (same expansion → parity holds)", () => {
  const refPath = renderPanel(A, { registry }).find((l) => l.refTarget === "scan for duckduckgo url").path;
  const opts = { registry, expanded: new Set([refPath]) };
  const panel = renderPanel(A, opts);
  const { nodes } = renderGraph(A, opts);
  assert.strictEqual(nodes.length, panel.length);
  // labels match the panel line texts in order (same underlying nodes)
  assert.deepStrictEqual(nodes.map((n) => n.label), panel.map((l) => l.text));
});

console.log(`\n${passed}/${passed + failed} passed`);
if (failed) process.exit(1);
