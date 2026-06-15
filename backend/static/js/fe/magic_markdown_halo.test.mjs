/**
 * magic_markdown_halo.test.mjs — the apparition halo ray mechanics (§V.4/O.18).
 * Run: node backend/static/js/fe/magic_markdown_halo.test.mjs
 */
import assert from "node:assert";
import { haloLayout, haloVDom } from "./magic_markdown_halo.mjs";

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log("  PASS  " + name); passed++; }
  catch (e) { console.log("  FAIL  " + name + ": " + e.message); failed++; }
}

const focal = { cx: 500, cy: 400 };
const cands = [
  { id: "a", label: "Alpha", similarity: 0.9 },
  { id: "b", label: "Beta", similarity: 0.5 },
  { id: "c", label: "Gamma", similarity: 0.2 },
];

test("constant-similarity ray: more similar → nearer the focal apex", () => {
  const p = haloLayout(focal, cands);
  const byId = Object.fromEntries(p.map((x) => [x.id, x]));
  assert.ok(byId.a.r < byId.b.r && byId.b.r < byId.c.r, "r decreases with similarity");
});

test("the radius is CONSTANT in camAngle (depends only on similarity)", () => {
  const p0 = haloLayout(focal, cands, { camAngle: 0 });
  const p1 = haloLayout(focal, cands, { camAngle: 1.1 });
  for (let i = 0; i < cands.length; i++) {
    assert.ok(Math.abs(p0[i].r - p1[i].r) < 1e-9, "r unchanged by camAngle (constant-similarity ray)");
  }
});

test("updating angle + along-line slide: camAngle rotates every phantom by the same delta", () => {
  const d = 0.7;
  const p0 = haloLayout(focal, cands, { camAngle: 0 });
  const p1 = haloLayout(focal, cands, { camAngle: d });
  for (let i = 0; i < cands.length; i++) {
    assert.ok(Math.abs((p1[i].angle - p0[i].angle) - d) < 1e-9, "angle advances by camAngle delta");
    // the phantom slid along its (constant-r) ray to the new angle
    const r1 = Math.hypot(p1[i].cx - focal.cx, p1[i].cy - focal.cy);
    assert.ok(Math.abs(r1 - p0[i].r) < 1e-6, "slid along the SAME-radius ray");
  }
});

test("positions sit on the candidate's ray from the focal", () => {
  const p = haloLayout(focal, cands);
  for (const x of p) {
    const r = Math.hypot(x.cx - focal.cx, x.cy - focal.cy);
    assert.ok(Math.abs(r - x.r) < 1e-6, "cx/cy are on the ray at radius r");
  }
});

test("haloVDom: one ray + one circular name-only phantom per candidate, above the slate", () => {
  const v = haloVDom(focal, cands);
  assert.ok(/z-index:\s*214748/.test(v.attrs.style), "halo layer is above the slate (T.4 z-order)");
  const svg = v.children.find((c) => c.attrs && c.attrs.class === "mm-halo-rays");
  const rays = svg.children.filter((c) => c.tag === "line");
  const phantoms = v.children.filter((c) => c.attrs && c.attrs.class === "mm-phantom");
  assert.strictEqual(rays.length, cands.length);
  assert.strictEqual(phantoms.length, cands.length);
  for (const ph of phantoms) {
    assert.ok(/border-radius/.test(ph.attrs.style), "phantom is circular");
    assert.strictEqual(typeof ph.text, "string");                 // name-only
    assert.ok(["Alpha", "Beta", "Gamma"].includes(ph.text));      // the candidate's name/root field
    assert.ok(!("score" in ph.attrs));                            // no score chip (D.1)
  }
});

console.log(`\n${passed}/${passed + failed} passed`);
if (failed) process.exit(1);
