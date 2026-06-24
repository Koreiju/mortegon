/**
 * magic_markdown.test.mjs — verifies the magic-markdown panel core.
 * Run: node backend/static/js/fe/magic_markdown.test.mjs
 */
import assert from "node:assert";
import {
  parse, serialize, rootField, buildRegistry, refTarget, refTargets,
  renderPanel, linesToText, toggle, GLYPH_COLLAPSED, GLYPH_EXPANDED,
  iterableNode, isIterable, advanceSignal, renderGraph, parentPath,
  renderTypedPanel, renderConceptPanel, isReadOnlyTypedNode,
  classifyBraceStates, BRACE_HIDDEN, BRACE_REVEALED_INTERNAL, BRACE_RESOLVED_EXTERNAL,
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

// ── typed render mode (EXPLORE-01): key:Type=value for python-native nodes,
//    type-stripped for user compute nodes (rank-1 minimalism preserved) ────

// Test 1: a python-native FUNCTION node with signature+ports.inputs/outputs
// renders "name : Type" rows (skipping the implicit "self") + a trailing
// "→ ReturnType" row.
test("renderTypedPanel: python-native function node renders typed input rows + return arrow", () => {
  const fnNode = {
    type_hint: "python_function",
    read_only: true,
    data: JSON.stringify({
      signature: "(self, url, samples)",
      ports: {
        inputs: [
          { name: "self", type: "WebBrowserManager" },
          { name: "url", type: "str" },
          { name: "samples", type: "int" },
        ],
        outputs: [{ type: "List[Chunk]" }],
      },
    }),
  };
  const lines = renderTypedPanel(fnNode, {});
  const texts = lines.map((l) => l.text);
  assert.deepStrictEqual(texts, ["url : str", "samples : int", "→ List[Chunk]"]);
});

// Test 2: a python-native OBJECT node (d.members list) returns one Line per
// member, last `::`-segment only (mirrors _pythonNativeTypedView's members map).
test("renderTypedPanel: python-native object node renders one line per member (last :: segment)", () => {
  const objNode = {
    type_hint: "python_object",
    read_only: true,
    data: JSON.stringify({
      members: [
        "WebBrowserManager::driver",
        "WebBrowserManager::scan",
        "WebBrowserManager::close",
      ],
    }),
  };
  const lines = renderTypedPanel(objNode, {});
  const texts = lines.map((l) => l.text);
  assert.deepStrictEqual(texts, ["driver", "scan", "close"]);
});

// Test 3: the existing renderPanel on a user compute node (type_hint NOT
// python_, not read_only) is UNCHANGED — no " : " type slot, no "=" type
// pair anywhere (rank-1 minimalism preserved). Driven through the new
// renderConceptPanel dispatch seam to prove the gate selects structural mode.
test("renderConceptPanel: a user compute node stays structurally type-stripped (rank-1 minimalism)", () => {
  const computeNode = {
    type_hint: "user_compute",
    read_only: false,
    value: "DuckDuckGo\n\tscanner {scan for duckduckgo url}\n\tport : 80",
  };
  const lines = renderConceptPanel(computeNode, { registry: new Map(), expanded: new Set() });
  const texts = lines.map((l) => l.text);
  // identical to calling renderPanel directly on the parsed tree
  const expected = renderPanel(parse(computeNode.value), { registry: new Map(), expanded: new Set() }).map((l) => l.text);
  assert.deepStrictEqual(texts, expected);
  // the load-bearing invariant: no " : Type = " slot leaks onto a compute node
  assert.ok(!texts.some((t) => / : .+ = /.test(t)), "no type-slot pair leaked onto a compute node");
});

// Test 4: the typed mode is selected by the gate condition only — a node with
// read_only===true but a non-python type_hint still renders typed; a node
// with neither stays structural.
test("isReadOnlyTypedNode: gate selects typed mode on read_only===true OR python_ type_hint, never a separate flag", () => {
  assert.strictEqual(isReadOnlyTypedNode({ type_hint: "python_function", read_only: false }), true);
  assert.strictEqual(isReadOnlyTypedNode({ type_hint: "user_compute", read_only: true }), true);
  assert.strictEqual(isReadOnlyTypedNode({ type_hint: "user_compute", read_only: false }), false);
  assert.strictEqual(isReadOnlyTypedNode({ backing_pointer: "fixture::database::ws1" }), true);
  assert.strictEqual(isReadOnlyTypedNode(null), false);

  // end-to-end through the dispatch seam: read_only===true + non-python type_hint
  const roNonPython = {
    type_hint: "user_compute",
    read_only: true,
    data: JSON.stringify({ members: ["X::field_a"] }),
  };
  const lines = renderConceptPanel(roNonPython, {});
  assert.deepStrictEqual(lines.map((l) => l.text), ["field_a"]);

  // neither python_ nor read_only → structural path
  const plain = { type_hint: "user_compute", read_only: false, value: "plain\n\ta : 1" };
  const plainLines = renderConceptPanel(plain, { registry: new Map(), expanded: new Set() });
  assert.deepStrictEqual(plainLines.map((l) => l.text), ["plain", "a : 1"]);
});

// Test 5 (T-07-03 defensive fallback): malformed/non-JSON data on a typed
// node renders a single verbatim structural row rather than throwing.
test("renderTypedPanel: malformed data falls back to a verbatim structural row (no throw)", () => {
  const broken = { type_hint: "python_function", read_only: true, data: "not json at all" };
  const lines = renderTypedPanel(broken, {});
  assert.deepStrictEqual(lines.map((l) => l.text), ["not json at all"]);
});

// ── §O.1a / D-04: three brace render states + N.6 duplicate-instance proxy ──
// (07-03 Task 1 — RESEARCH Open Q1: probe the EXISTING buildRegistry/refTarget
// live-resolution mechanism FIRST, before adding any new proxy state.)

// Test 1 (Open Q1 probe): a {ref} whose target node's text is mutated AFTER
// the registry is built re-resolves to the NEW text on the next renderPanel
// call — proving buildRegistry/refTarget already give N.6's "operationally
// calls the originating object" (a live proxy, not a frozen snapshot) for
// free, with ZERO new proxy state.
test("Open-Q1 probe: a {ref} re-resolves to the LIVE current node, not a frozen snapshot (N.6)", () => {
  const host = parse("host\n\tlink {scanner}");
  const target = parse("scanner\n\turl : http://old");
  const reg = buildRegistry([target]);
  const expanded = new Set([renderPanel(host, { registry: reg, expanded: new Set() })
    .find((l) => l.refTarget === "scanner").path]);

  const before = renderPanel(host, { registry: reg, expanded });
  assert.deepStrictEqual(before.filter((l) => l.source === "expanded").map((l) => l.text), ["url : http://old"]);

  // mutate the SAME target node object in place (the registry holds object
  // references, not copies) — simulating the originating object's state
  // changing between renders.
  target.children[0].text = "url : http://new";

  const after = renderPanel(host, { registry: reg, expanded });
  assert.deepStrictEqual(
    after.filter((l) => l.source === "expanded").map((l) => l.text),
    ["url : http://new"],
    "re-resolved to the NEW text — live proxy, no frozen snapshot. N.6 satisfied by existing live-registry-resolution; no new proxy state needed.",
  );
});

// Test 2: an unrevealed {ref} to a node not otherwise visible classifies as
// braced-hidden (default state — braces retained, ▸ glyph, no children).
test("brace-state: an unrevealed {ref} to a not-otherwise-visible node is braced-hidden", () => {
  const host = parse("host\n\tlink {scanner}");
  const target = parse("scanner\n\turl : http://x");
  const reg = buildRegistry([target]);
  const lines = renderPanel(host, { registry: reg, expanded: new Set() });
  const refLine = lines.find((l) => l.refTarget === "scanner");
  assert.strictEqual(refLine.glyph, GLYPH_COLLAPSED);
  assert.strictEqual(refLine.braceState, BRACE_HIDDEN);
  assert.ok(!lines.some((l) => l.source === "expanded"));
});

// Test 3: after toggle(expanded, refLine.path), the SAME {ref} classifies as
// revealed-internal — braces drop, rank-1 child lines present, source:
// "expanded".
test("brace-state: toggling a {ref} open classifies it as revealed-internal", () => {
  const host = parse("host\n\tlink {scanner}");
  const target = parse("scanner\n\turl : http://x");
  const reg = buildRegistry([target]);
  const collapsed = renderPanel(host, { registry: reg, expanded: new Set() });
  const refPath = collapsed.find((l) => l.refTarget === "scanner").path;
  const expanded = toggle(new Set(), refPath);

  const lines = renderPanel(host, { registry: reg, expanded });
  const refLine = lines.find((l) => l.refTarget === "scanner");
  assert.strictEqual(refLine.glyph, GLYPH_EXPANDED);
  assert.strictEqual(refLine.braceState, BRACE_REVEALED_INTERNAL);
  const inlined = lines.filter((l) => l.source === "expanded");
  assert.deepStrictEqual(inlined.map((l) => l.text), ["url : http://x"]);
});

// Test 4: a {ref} whose target is ALSO independently visible (revealed via
// another path) classifies as resolved-external — a solid-link marker, NOT
// a second set of inline children, NOT dashed (no stroke/line-style field is
// ever set to anything but the default solid rendering — classification is
// purely the braceState string).
test("brace-state: a {ref} whose target is independently visible elsewhere is resolved-external", () => {
  // two siblings both reference "scanner"; the FIRST is expanded (revealing
  // "scanner"'s own row as the inline child "url : http://x"). The SECOND
  // ref to the literal text "url : http://x" (i.e. a different field
  // already showing the same text the target's row shows) demonstrates the
  // independently-visible check. To keep the fixture unambiguous, model it
  // as: revealing scanner's child row makes "url : http://x" visible; a
  // second host that independently {ref}s a node whose root field IS that
  // same text resolves to resolved-external (no new inline children, no
  // dashed line — distinct from the revealed-internal line itself).
  const visibleTarget = parse("url : http://x"); // a node, root field "url : http://x"
  const host = parse("host\n\tlink {scanner}\n\talso {url : http://x}");
  const scanner = parse("scanner\n\turl : http://x");
  const reg = buildRegistry([scanner, visibleTarget]);

  const collapsedFirst = renderPanel(host, { registry: reg, expanded: new Set() });
  const scannerRefPath = collapsedFirst.find((l) => l.refTarget === "scanner").path;
  const expanded = toggle(new Set(), scannerRefPath);

  const lines = renderPanel(host, { registry: reg, expanded });
  const scannerLine = lines.find((l) => l.refTarget === "scanner");
  const alsoLine = lines.find((l) => l.refTarget === "url : http://x");
  assert.strictEqual(scannerLine.braceState, BRACE_REVEALED_INTERNAL);
  assert.strictEqual(alsoLine.braceState, BRACE_RESOLVED_EXTERNAL,
    "the {url : http://x} ref's target text is independently visible (the expanded scanner row) — solid-link marker, no inline children of its own");
  // resolved-external never produces its OWN inline children (no second
  // expansion just from being classified) and never carries a dashed marker.
  assert.ok(!lines.some((l) => l.path.startsWith(alsoLine.path + "/")),
    "resolved-external does not inline its own children");
  assert.ok(!("dashed" in alsoLine) && alsoLine.lineStyle !== "dashed",
    "no dashed marker — resolved-external is solid-only");
});

// Test 5: node-count parity — revealing a ref in the panel Line[] yields the
// same revealed node present in renderGraph's GraphNode set (O.1).
test("brace-state: node-count parity — revealing a ref in the panel reveals the same node in the graph", () => {
  const host = parse("host\n\tlink {scanner}");
  const target = parse("scanner\n\turl : http://x");
  const reg = buildRegistry([target]);
  const collapsed = renderPanel(host, { registry: reg, expanded: new Set() });
  const refPath = collapsed.find((l) => l.refTarget === "scanner").path;
  const expanded = toggle(new Set(), refPath);

  const panelLines = renderPanel(host, { registry: reg, expanded });
  const { nodes } = renderGraph(host, { registry: reg, expanded });
  assert.strictEqual(nodes.length, panelLines.length, "graph node count matches panel line count (O.1 parity)");
  const revealedPanelLine = panelLines.find((l) => l.source === "expanded");
  const revealedGraphNode = nodes.find((n) => n.id === revealedPanelLine.path);
  assert.ok(revealedGraphNode, "the revealed panel line has a matching graph node at the same path");
  assert.strictEqual(revealedGraphNode.label, revealedPanelLine.text);
});

// classifyBraceStates is also directly callable/idempotent over an
// already-rendered Line[] (used internally by renderPanel; exposed for
// panelVDom/graphVDom to call again defensively without side effects).
test("classifyBraceStates is idempotent over an already-classified Line[]", () => {
  const host = parse("host\n\tlink {scanner}");
  const target = parse("scanner\n\turl : http://x");
  const reg = buildRegistry([target]);
  const lines = renderPanel(host, { registry: reg, expanded: new Set() });
  const before = lines.map((l) => l.braceState);
  classifyBraceStates(lines);
  const after = lines.map((l) => l.braceState);
  assert.deepStrictEqual(before, after);
});

console.log(`\n${passed}/${passed + failed} passed`);
if (failed) process.exit(1);
