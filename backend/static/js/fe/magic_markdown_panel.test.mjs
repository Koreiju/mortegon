/**
 * magic_markdown_panel.test.mjs — verifies the pure black-slate vdom.
 * Run: node backend/static/js/fe/magic_markdown_panel.test.mjs
 */
import assert from "node:assert";
import { parse, buildRegistry, renderPanel } from "./magic_markdown.mjs";
import { panelVDom, graphVDom, flattenVDom } from "./magic_markdown_panel.mjs";

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log("  PASS  " + name); passed++; }
  catch (e) { console.log("  FAIL  " + name + ": " + e.message); failed++; }
}

const A = parse("DuckDuckGo\n\tscanner {scan for duckduckgo url}\n\tport : 80");
const B = parse("scan for duckduckgo url\n\tsearch {}\n\tchunk {chunk samples}");
const registry = buildRegistry([B]);

test("slate is black fill + silver border + serif, NO chrome elements", () => {
  const all = flattenVDom(panelVDom(A, { registry }));
  const slate = all[0];
  assert.strictEqual(slate.attrs.class, "mm-slate");
  assert.ok(/background:#000/.test(slate.attrs.style));
  assert.ok(/serif/.test(slate.attrs.style));
  assert.ok(/slate-border/.test(slate.attrs.style));
  // no header / title / button / minimise / close anywhere
  const classes = all.map((e) => (e.attrs && e.attrs.class) || "").join(" ");
  assert.ok(!/header|title|topbar|min-btn|close|delete-btn/.test(classes), "no chrome");
  const tags = all.map((e) => e.tag);
  assert.ok(!tags.includes("button"), "no <button> chrome");
});

test("one line element per render line", () => {
  const opts = { registry, expanded: new Set() };
  const lineEls = flattenVDom(panelVDom(A, opts)).filter((e) => e.attrs && e.attrs.class === "mm-line");
  assert.strictEqual(lineEls.length, renderPanel(A, opts).length);
});

test("a linked field shows a clickable dropdown CHARACTER span", () => {
  const all = flattenVDom(panelVDom(A, { registry, expanded: new Set() }));
  const drops = all.filter((e) => e.attrs && e.attrs.class === "mm-drop");
  assert.strictEqual(drops.length, 1, "one dropdown char (the scanner ref)");
  assert.strictEqual(drops[0].text, "▸");
  assert.strictEqual(drops[0].attrs.role, "button");
  assert.ok(drops[0].attrs["data-path"]);
});

test("expanding flips the dropdown char to ▾ and inlines read-through text", () => {
  const refPath = renderPanel(A, { registry }).find((l) => l.refTarget === "scan for duckduckgo url").path;
  const all = flattenVDom(panelVDom(A, { registry, expanded: new Set([refPath]) }));
  const drop = all.find((e) => e.attrs && e.attrs.class === "mm-drop");
  assert.strictEqual(drop.text, "▾");
  assert.strictEqual(drop.attrs["data-open"], "1");
  // inlined fields are read-through (not directly editable)
  const readthrough = all.filter((e) => e.attrs && /mm-readthrough/.test(e.attrs.class || ""));
  assert.ok(readthrough.length >= 1, "expanded fields render as read-through tokens");
});

test("depth → indentation; own text tokens are editable", () => {
  const all = flattenVDom(panelVDom(A, { registry }));
  const portLine = all.find((e) => e.attrs && e.attrs.class === "mm-line" && e.attrs["data-depth"] === "1");
  assert.ok(/padding-left:16px/.test(portLine.attrs.style));
  const editable = all.filter((e) => e.attrs && e.attrs["data-editable"] === "1");
  assert.ok(editable.length >= 2, "own field tokens are click-to-edit");
});

// ── graph form (the other half of the dialect) ─────────────────────────────
test("graph form: one circular node per panel line (parity), text-only", () => {
  const opts = { registry, expanded: new Set() };
  const panelLines = flattenVDom(panelVDom(A, opts)).filter((e) => e.attrs && e.attrs.class === "mm-line").length;
  const gnodes = flattenVDom(graphVDom(A, opts)).filter((e) => e.attrs && e.attrs.class === "mm-gnode");
  assert.strictEqual(gnodes.length, panelLines, "node-count parity with panel (O.1)");
  for (const n of gnodes) {
    assert.ok(/border-radius/.test(n.attrs.style), "node is rounded/circular");
    assert.strictEqual(typeof n.text, "string");           // text-only
    assert.ok(!("title" in n) && !("buttons" in n));        // no chrome
  }
  assert.ok(!flattenVDom(graphVDom(A, opts)).some((e) => e.tag === "button"));
});

test("graph form: edges are undirected lines (no arrowheads)", () => {
  const gAll = flattenVDom(graphVDom(A, { registry, expanded: new Set() }));
  const lines = gAll.filter((e) => e.tag === "line");
  assert.ok(lines.length >= 1, "containment edges drawn");
  for (const ln of lines) {
    assert.ok(!("marker-end" in ln.attrs), "no arrowhead marker");
    assert.ok(!("stroke-dasharray" in ln.attrs), "no dashes");
  }
});

console.log(`\n${passed}/${passed + failed} passed`);
if (failed) process.exit(1);
