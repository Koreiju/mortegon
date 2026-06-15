/**
 * magic_markdown_gestures.test.mjs — the gesture→transformation map (V.5).
 * Run: node backend/static/js/fe/magic_markdown_gestures.test.mjs
 */
import assert from "node:assert";
import { resolveGesture, Action } from "./magic_markdown_gestures.mjs";

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log("  PASS  " + name); passed++; }
  catch (e) { console.log("  FAIL  " + name + ": " + e.message); failed++; }
}

const A = (g) => resolveGesture(g).action;

test("single-left a token → edit (borderless, M.8)", () => {
  assert.strictEqual(A({ button: "left", clicks: 1, target: "token" }), Action.EDIT_TOKEN);
});
test("single-left the dropdown char → toggle fold", () => {
  assert.strictEqual(A({ button: "left", clicks: 1, target: "dropdown" }), Action.TOGGLE_FOLD);
});
test("right-click a {ref} → internalize⇄externalize inline fold (M.6)", () => {
  assert.strictEqual(A({ button: "right", clicks: 1, target: "ref" }), Action.TOGGLE_FOLD);
});
test("right-click self → rank-dominance collapse to circular node (S.5)", () => {
  assert.strictEqual(A({ button: "right", clicks: 1, target: "self" }), Action.COLLAPSE_TO_NODE);
});
test("double-left the body → panel ⇄ graph (M.7)", () => {
  assert.strictEqual(A({ button: "left", clicks: 2, target: "body" }), Action.TOGGLE_PANEL_GRAPH);
  assert.strictEqual(A({ button: "left", clicks: 2, target: "self" }), Action.TOGGLE_PANEL_GRAPH);
});
test("left-drag node→node → wire link + inherit I/O (N.4)", () => {
  assert.strictEqual(A({ button: "left", drag: true, target: "token", mode: "graph" }), Action.WIRE_LINK);
});
test("double-right a {ref} → delete (N.13)", () => {
  assert.strictEqual(A({ button: "right", clicks: 2, target: "ref" }), Action.DELETE_REF);
});

// ── non-collision: the same target resolves differently by button/clicks ────
test("non-collision: left vs right on the same {ref} target", () => {
  assert.notStrictEqual(
    A({ button: "left", clicks: 1, target: "ref" }),   // EDIT
    A({ button: "right", clicks: 1, target: "ref" }),  // FOLD
  );
});
test("non-collision: single vs double right on a {ref}", () => {
  assert.strictEqual(A({ button: "right", clicks: 1, target: "ref" }), Action.TOGGLE_FOLD);
  assert.strictEqual(A({ button: "right", clicks: 2, target: "ref" }), Action.DELETE_REF);
});
test("double-left on a token falls back to edit (not a stuck no-op)", () => {
  assert.strictEqual(A({ button: "left", clicks: 2, target: "token" }), Action.EDIT_TOKEN);
});
test("clicking empty body does nothing", () => {
  assert.strictEqual(A({ button: "left", clicks: 1, target: "body" }), Action.NONE);
});

console.log(`\n${passed}/${passed + failed} passed`);
if (failed) process.exit(1);
