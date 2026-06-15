/**
 * projector.test.mjs — the pure part of the fe/real projector.
 * Run: node backend/static/js/fe/projector.test.mjs
 */
import assert from "node:assert";
import { buildPointArrays } from "./projector.mjs";

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log("  PASS  " + name); passed++; }
  catch (e) { console.log("  FAIL  " + name + ": " + e.message); failed++; }
}

test("buildPointArrays: one xyz triple per chunk, in id order", () => {
  const coords = { a: [1, 2, 3], b: [4, 5, 6], c: [-1, 0, 9] };
  const r = buildPointArrays(coords);
  assert.deepStrictEqual(r.ids, ["a", "b", "c"]);
  assert.strictEqual(r.count, 3);
  assert.strictEqual(r.positions.length, 9);
  assert.deepStrictEqual([...r.positions.slice(0, 3)], [1, 2, 3]);
  assert.deepStrictEqual([...r.positions.slice(3, 6)], [4, 5, 6]);
});

test("buildPointArrays: a colour per node (HSV sweep), in [0,1]", () => {
  const r = buildPointArrays({ a: [0, 0, 0], b: [1, 1, 1] });
  assert.strictEqual(r.colors.length, 6);
  for (const c of r.colors) assert.ok(c >= 0 && c <= 1, "rgb in [0,1]");
});

test("buildPointArrays: empty coords → empty arrays (no crash)", () => {
  const r = buildPointArrays({});
  assert.strictEqual(r.count, 0);
  assert.strictEqual(r.positions.length, 0);
});

test("buildPointArrays: coerces missing/garbage coords to 0", () => {
  const r = buildPointArrays({ a: [null, "x", 5] });
  assert.deepStrictEqual([...r.positions], [0, 0, 5]);
});

console.log(`\n${passed}/${passed + failed} passed`);
if (failed) process.exit(1);
