/**
 * integration.test.mjs — the magic-markdown panel as a whole: the full
 * interaction loop composed from every module, exercised end-to-end in Node.
 *
 *   content_tree text → parse → renderPanel → panelVDom            (render)
 *   user gesture → resolveGesture → action → toggle expanded set   (intent)
 *   → re-render → the dropdown expands inline                      (effect)
 *
 * This is the closest Node-verifiable proxy for "the panel works": the data
 * the backend produces (§U content tree) flows through the model, the
 * black-slate vdom, and the gesture resolver, and a simulated click drives the
 * in-text dropdown expansion that pulls in an externally-referenced node.
 * Run: node backend/static/js/fe/integration.test.mjs
 */
import assert from "node:assert";
import { parse, buildRegistry, renderPanel, toggle } from "./magic_markdown.mjs";
import { panelVDom, flattenVDom } from "./magic_markdown_panel.mjs";
import { resolveGesture, Action } from "./magic_markdown_gestures.mjs";

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log("  PASS  " + name); passed++; }
  catch (e) { console.log("  FAIL  " + name + ": " + e.message); failed++; }
}

// The real §U content tree (from the live archive.org Princeton card), authored
// as a panel that links out to a "details" node by its root field.
const CARD = parse([
  "Princeton University Library Chronicle 1950 - 1951: Vol 12",
  "\tlink {details page}",          // an external reference (by the node's root field)
  "\tvolume : 12",
].join("\n"));

const DETAILS = parse([
  "details page",
  "\turl : /details/sim_princeton-university-library-chronicle_1950-1951_12_contents",
  "\tmediatype : Text",
  "\treviews : 0",
].join("\n"));

const registry = buildRegistry([DETAILS]);

test("render: the panel shows the card as a black slate with a ▸ dropdown char", () => {
  const all = flattenVDom(panelVDom(CARD, { registry, expanded: new Set() }));
  assert.strictEqual(all[0].attrs.class, "mm-slate");
  const drops = all.filter((e) => e.attrs && e.attrs.class === "mm-drop");
  assert.strictEqual(drops.length, 1);
  assert.strictEqual(drops[0].text, "▸");
});

test("the full loop: right-click the {ref} → fold action → expand inline", () => {
  // 1. find the ref line + its dropdown path
  let expanded = new Set();
  let lines = renderPanel(CARD, { registry, expanded });
  const refLine = lines.find((l) => l.refTarget === "details page");
  assert.ok(refLine, "the {details page} ref is present");
  assert.strictEqual(refLine.glyph, "▸");

  // 2. the user RIGHT-CLICKS the ref token → the gesture resolver says TOGGLE_FOLD
  const { action } = resolveGesture({ button: "right", clicks: 1, target: "ref" });
  assert.strictEqual(action, Action.TOGGLE_FOLD);

  // 3. apply: toggle the dropdown path open
  expanded = toggle(expanded, refLine.path);

  // 4. re-render → the referenced node's fields are inlined one rank deeper
  lines = renderPanel(CARD, { registry, expanded });
  const inlined = lines.filter((l) => l.source === "expanded").map((l) => l.text);
  assert.deepStrictEqual(inlined, [
    "url : /details/sim_princeton-university-library-chronicle_1950-1951_12_contents",
    "mediatype : Text",
    "reviews : 0",
  ]);
  // the dropdown char is now ▾ in the vdom
  const drop = flattenVDom(panelVDom(CARD, { registry, expanded }))
    .find((e) => e.attrs && e.attrs.class === "mm-drop");
  assert.strictEqual(drop.text, "▾");
});

test("collapse is symmetric: right-click again folds it back", () => {
  const refPath = renderPanel(CARD, { registry }).find((l) => l.refTarget === "details page").path;
  let expanded = toggle(new Set(), refPath);           // open
  expanded = toggle(expanded, refPath);                // close (resolveGesture → TOGGLE_FOLD again)
  const lines = renderPanel(CARD, { registry, expanded });
  assert.ok(!lines.some((l) => l.source === "expanded"), "folded back to the slate");
});

test("double-left the body → panel⇄graph transform is dispatched", () => {
  const { action } = resolveGesture({ button: "left", clicks: 2, target: "body" });
  assert.strictEqual(action, Action.TOGGLE_PANEL_GRAPH);
});

test("the rendered slate never contains JSON/HTML/xpath markup (pure text)", () => {
  const refPath = renderPanel(CARD, { registry }).find((l) => l.refTarget === "details page").path;
  const all = flattenVDom(panelVDom(CARD, { registry, expanded: new Set([refPath]) }));
  const texts = all.filter((e) => e.text != null).map((e) => e.text).join("\n");
  assert.ok(!/[<>]|@href|text\(\)|#shadow-root|[{][^}]*[}][}]/.test(texts.replace(/\{[^{}]+\}/g, "")),
    "no html/xpath/json leakage (only {ref} braces remain as markup)");
});

console.log(`\n${passed}/${passed + failed} passed`);
if (failed) process.exit(1);
