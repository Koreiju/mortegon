/**
 * spine.test.mjs — WorkspaceStore + GestureGateway (the fe/ spine).
 * Run: node backend/static/js/fe/spine.test.mjs
 */
import assert from "node:assert";
import { createStore } from "./store.mjs";
import { buildRequest, GestureGateway } from "./gateway.mjs";
import { Action } from "./magic_markdown_gestures.mjs";

let passed = 0, failed = 0;
const TESTS = [];
function test(name, fn) { TESTS.push({ name, fn }); }

// ── store: frames fold into truth ───────────────────────────────────────────
test("applyFrame: concept_changed upserts; concept_deleted removes", () => {
  const s = createStore();
  s.applyFrame({ type: "concept_changed", concept: { id: "a", name: "Alpha", data: "x : 1" } });
  assert.strictEqual(s.concept("a").name, "Alpha");
  s.applyFrame({ type: "concept_changed", concept: { id: "a", data: "x : 2" } });
  assert.strictEqual(s.concept("a").data, "x : 2");
  assert.strictEqual(s.concept("a").name, "Alpha", "merge, not replace");
  s.applyFrame({ type: "concept_deleted", id: "a" });
  assert.strictEqual(s.concept("a"), undefined);
});

test("applyFrame: edges + ui_state_changed", () => {
  const s = createStore();
  s.applyFrame({ type: "edges", edges: [{ source: "a", target: "b" }] });
  assert.strictEqual(s.getState().edges.length, 1);
  s.applyFrame({ type: "ui_state_changed", ui: { mode: { a: "graph" } } });
  assert.deepStrictEqual(s.getState().ui.mode, { a: "graph" });
});

test("subscribe fires on frame application", () => {
  const s = createStore();
  let n = 0; s.subscribe(() => n++);
  s.applyFrame({ type: "concept_changed", concept: { id: "a" } });
  assert.strictEqual(n, 1);
});

test("registry: concepts resolve by their ROOT field (for {ref} pull-in)", () => {
  const s = createStore();
  s.applyFrame({ type: "concept_changed", concept: { id: "d", name: "details page", data: "url : /x\nmediatype : Text" } });
  const reg = s.registry();
  assert.ok(reg.has("details page"), "node keyed by its root field");
  assert.strictEqual(reg.get("details page").children.length, 2);
});

test("panelText: content_tree preferred for scanned chunks", () => {
  const s = createStore();
  s.applyFrame({ type: "concept_changed", concept: { id: "c", content_tree: "/details/x\nTitle Here", data: "ignored" } });
  assert.ok(s.panelText("c").startsWith("/details/x"));
});

// ── gateway: gestures → backend mirror routes (pure mapping) ─────────────────
test("buildRequest maps the resolver Actions to /api/ui/* + concept routes", () => {
  assert.deepStrictEqual(buildRequest({ action: Action.TOGGLE_FOLD, cardId: "p", path: "0.1", expanded: true }),
    { method: "POST", path: "/api/ui/node_fold", body: { card_id: "p", node_path: "0.1", expanded: true, workspace_id: "_default" } });
  assert.strictEqual(buildRequest({ action: Action.COLLAPSE_TO_NODE, cardId: "p" }).path, "/api/ui/dominance_collapse");
  assert.strictEqual(buildRequest({ action: Action.WIRE_LINK, sourceId: "a", targetId: "b" }).path, "/api/concept_edges");
});

test("buildRequest: panel⇄graph direction depends on current mode", () => {
  assert.strictEqual(buildRequest({ action: Action.TOGGLE_PANEL_GRAPH, cardId: "p", mode: "panel" }).path, "/api/ui/compile_expand");
  assert.strictEqual(buildRequest({ action: Action.TOGGLE_PANEL_GRAPH, cardId: "p", mode: "graph" }).path, "/api/ui/compile_collapse");
});

test("buildRequest: unknown gesture → null (no spurious request)", () => {
  assert.strictEqual(buildRequest({ action: "nope" }), null);
});

test("GestureGateway.send: posts via fetchImpl and folds returned frames into the store", async () => {
  const s = createStore();
  const calls = [];
  const gw = GestureGateway(s, {
    base: "http://x",
    fetchImpl: (m, url, body) => { calls.push({ m, url, body }); return Promise.resolve({ frames: [{ type: "concept_changed", concept: { id: "p", data: "edited" } }] }); },
  });
  await gw.send({ action: Action.EDIT_TOKEN, cardId: "p", path: "0", value: "edited" });
  assert.strictEqual(calls.length, 1);
  assert.strictEqual(calls[0].url, "http://x/api/ui/edit_close");
  assert.strictEqual(s.concept("p").data, "edited", "returned frame folded into store");
});

(async () => {
  for (const { name, fn } of TESTS) {
    try { await fn(); console.log("  PASS  " + name); passed++; }
    catch (e) { console.log("  FAIL  " + name + ": " + e.message); failed++; }
  }
  console.log(`\n${passed}/${passed + failed} passed`);
  if (failed) process.exit(1);
})();
