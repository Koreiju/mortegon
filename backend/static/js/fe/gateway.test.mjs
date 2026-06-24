/**
 * gateway.test.mjs — buildRequest / GestureGateway unit coverage (Phase 7
 * EXPLORE-03 / N.4 + N.13 extensions).
 * Run: node backend/static/js/fe/gateway.test.mjs
 */
import assert from "node:assert";
import { buildRequest, GestureGateway } from "./gateway.mjs";
import { Action } from "./magic_markdown_gestures.mjs";

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log("  PASS  " + name); passed++; }
  catch (e) { console.log("  FAIL  " + name + ": " + e.message); failed++; }
}
async function testAsync(name, fn) {
  try { await fn(); console.log("  PASS  " + name); passed++; }
  catch (e) { console.log("  FAIL  " + name + ": " + e.message); failed++; }
}

// ── WIRE_LINK / inherit_types (N.4) ──────────────────────────────────────

test("WIRE_LINK without inheritTypes defaults inherit_types:false in the body", () => {
  const req = buildRequest({ action: Action.WIRE_LINK, sourceId: "a", targetId: "b" });
  assert.strictEqual(req.method, "POST");
  assert.strictEqual(req.path, "/api/concept_edges");
  assert.strictEqual(req.body.inherit_types, false);
  assert.strictEqual(req.body.source_id, "a");
  assert.strictEqual(req.body.target_id, "b");
});

test("WIRE_LINK with g.inheritTypes:true carries inherit_types:true in the body", () => {
  const req = buildRequest({ action: Action.WIRE_LINK, sourceId: "a", targetId: "b", inheritTypes: true });
  assert.strictEqual(req.body.inherit_types, true);
});

test("WIRE_LINK (legacy kind string) also carries inherit_types", () => {
  const req = buildRequest({ kind: "concept-edge-create", sourceId: "a", targetId: "b", inheritTypes: true });
  assert.strictEqual(req.body.inherit_types, true);
});

// ── DELETE_REF / edge-delete completion (N.13) ───────────────────────────

test("DELETE_REF without g.edgeId falls back to value-clear-only (unchanged)", () => {
  const req = buildRequest({ action: Action.DELETE_REF, cardId: "p", path: "0.1", value: "" });
  assert.ok(!Array.isArray(req), "no backing edge → single request, not an array");
  assert.strictEqual(req.method, "POST");
  assert.strictEqual(req.path, "/api/ui/edit_close");
  assert.strictEqual(req.body.node_path, "0.1");
});

test("DELETE_REF with g.edgeId fires the edge delete AND the value-clear", () => {
  const req = buildRequest({ action: Action.DELETE_REF, cardId: "p", path: "0.1", value: "", edgeId: "edge-123" });
  assert.ok(Array.isArray(req), "a backing edge → an array of sequential requests");
  assert.strictEqual(req.length, 2);
  assert.strictEqual(req[0].method, "DELETE");
  assert.strictEqual(req[0].path, "/api/concept_edges/edge-123");
  assert.strictEqual(req[1].method, "POST");
  assert.strictEqual(req[1].path, "/api/ui/edit_close");
});

test("DELETE_REF (legacy kind string) also fires the edge delete when g.edgeId present", () => {
  const req = buildRequest({ kind: "concept-delete-ref", cardId: "p", path: "0", edgeId: "edge-9" });
  assert.ok(Array.isArray(req));
  assert.strictEqual(req[0].path, "/api/concept_edges/edge-9");
});

// ── GestureGateway.send: sequential array firing (N.13) ──────────────────

await testAsync("GestureGateway.send fires DELETE_REF's two-request array in order through fetchImpl", async () => {
  const calls = [];
  const gw = GestureGateway(null, {
    base: "http://x",
    fetchImpl: (m, url, body) => {
      calls.push({ m, url, body });
      return Promise.resolve({ ok: true });
    },
  });
  await gw.send({ action: Action.DELETE_REF, cardId: "p", path: "0", value: "", edgeId: "edge-77" });
  assert.strictEqual(calls.length, 2, "both the edge-delete and the value-clear must fire");
  assert.strictEqual(calls[0].m, "DELETE");
  assert.strictEqual(calls[0].url, "http://x/api/concept_edges/edge-77");
  assert.strictEqual(calls[1].m, "POST");
  assert.strictEqual(calls[1].url, "http://x/api/ui/edit_close");
});

await testAsync("GestureGateway.send fires DELETE_REF's single request when no edgeId (unchanged path)", async () => {
  const calls = [];
  const gw = GestureGateway(null, {
    base: "http://x",
    fetchImpl: (m, url, body) => { calls.push({ m, url, body }); return Promise.resolve({ ok: true }); },
  });
  await gw.send({ action: Action.DELETE_REF, cardId: "p", path: "0", value: "" });
  assert.strictEqual(calls.length, 1);
  assert.strictEqual(calls[0].url, "http://x/api/ui/edit_close");
});

await testAsync("GestureGateway.send posts WIRE_LINK with inherit_types in the JSON body", async () => {
  const calls = [];
  const gw = GestureGateway(null, {
    base: "http://x",
    fetchImpl: (m, url, body) => { calls.push({ m, url, body }); return Promise.resolve({ ok: true }); },
  });
  await gw.send({ action: Action.WIRE_LINK, sourceId: "a", targetId: "b", inheritTypes: true });
  assert.strictEqual(calls.length, 1);
  assert.strictEqual(calls[0].url, "http://x/api/concept_edges");
  assert.strictEqual(calls[0].body.inherit_types, true);
});

console.log(`\n${passed}/${passed + failed} passed`);
if (failed) process.exit(1);
