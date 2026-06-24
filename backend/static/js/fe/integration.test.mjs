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
import {
  parse, buildRegistry, renderPanel, toggle,
  BRACE_HIDDEN, BRACE_REVEALED_INTERNAL, BRACE_RESOLVED_EXTERNAL,
} from "./magic_markdown.mjs";
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

// ── EXPLORE-02: external-{ref} recursive-panel propagation through the FULL
// pipeline (parse → renderPanel → panelVDom), proving the three §O.1a brace
// states end-to-end, not just at the renderPanel model layer.
test("EXPLORE-02: external {ref} propagates through the full vdom pipeline across all three brace states", () => {
  let expanded = new Set();
  let lines = renderPanel(CARD, { registry, expanded });
  let refLine = lines.find((l) => l.refTarget === "details page");
  assert.strictEqual(refLine.braceState, BRACE_HIDDEN, "unrevealed → braced-hidden");
  // braced-hidden propagates into the vdom: the dropdown char is ▸, no
  // inline read-through children rendered for this ref yet.
  let vdom = flattenVDom(panelVDom(CARD, { registry, expanded }));
  assert.ok(!vdom.some((e) => e.attrs && e.attrs.class === "mm-text mm-readthrough"));

  // right-click commits the fold → revealed-internal; the referenced node's
  // panel propagates in as its own recursively-rendered rank-1 fields.
  expanded = toggle(expanded, refLine.path);
  lines = renderPanel(CARD, { registry, expanded });
  refLine = lines.find((l) => l.refTarget === "details page");
  assert.strictEqual(refLine.braceState, BRACE_REVEALED_INTERNAL, "right-click commit → revealed-internal");
  const propagated = lines.filter((l) => l.source === "expanded").map((l) => l.text);
  assert.deepStrictEqual(propagated, [
    "url : /details/sim_princeton-university-library-chronicle_1950-1951_12_contents",
    "mediatype : Text",
    "reviews : 0",
  ], "the external node's rank-1 fields propagated in as the duplicate-instance proxy (N.6)");
  // the vdom reflects the propagation: a read-through (expanded) text span
  // for each propagated field, plus the dropdown char flipped to ▾.
  vdom = flattenVDom(panelVDom(CARD, { registry, expanded }));
  const readthrough = vdom.filter((e) => e.attrs && e.attrs.class === "mm-text mm-readthrough").map((e) => e.text);
  assert.deepStrictEqual(readthrough, propagated);

  // a SECOND, independent card whose ref to the SAME target ("details page")
  // sits within the SAME rendered Line[] set (e.g. a workspace-level
  // multi-card render merges both cards' lines) resolves to
  // resolved-external — a solid-link marker, never a duplicate inline copy
  // of "details page"'s fields. This exercises the cross-card visibility
  // rule the renderPanel-level brace-state tests (magic_markdown.test.mjs)
  // already prove for a single render tree; here it is the SAME classifier
  // applied to a synthetic multi-card forest (the workspace's actual
  // render shape — every card root is a top-level forest child).
  const SECOND_CARD = parse([
    "A related catalog entry",
    "\tsee {details page}",
  ].join("\n"));
  const WORKSPACE = { text: "", children: [CARD, SECOND_CARD] };
  const workspaceLines = renderPanel(WORKSPACE, { registry, expanded });
  const firstRefLine = workspaceLines.find((l) => l.refTarget === "details page" && l.glyph === "▾");
  const secondRefLine = workspaceLines.find((l) => l.refTarget === "details page" && l !== firstRefLine);
  assert.ok(firstRefLine, "the first card's revealed ref is present in the merged workspace render");
  assert.ok(secondRefLine, "the second card's ref is present in the merged workspace render");
  assert.strictEqual(firstRefLine.braceState, BRACE_REVEALED_INTERNAL);
  assert.strictEqual(secondRefLine.braceState, BRACE_RESOLVED_EXTERNAL,
    "the second card's ref to the now-revealed 'details page' target resolves to a solid link, not a duplicate inline reveal");
  assert.ok(!workspaceLines.some((l) => l.path.startsWith(secondRefLine.path + "/")),
    "resolved-external never inlines its own children — no duplicate copy of the propagated panel");
});

console.log(`\n${passed}/${passed + failed} passed`);
if (failed) process.exit(1);
