// Phase 2 — Black-Slate Field Editing (§T / §M.8 / §15.1).
//
// PASSING specs run against the served demo reference (`static/js/fe/demo.html`),
// which renders real static slates and wires the full gesture model
// (magic_markdown_gestures.mjs). FIXME specs are the executable acceptance for
// the LIVE `/` editor build targets (textarea+caret, `{`-autocomplete, `+→`/`+↓`)
// — un-fixme them as EDIT-01/02 land. This is the render-level coverage the REPL
// (API/WS seam) cannot reach.
const { test, expect } = require("@playwright/test");

const DEMO = "/static/js/fe/demo.html";

test.beforeEach(async ({ page }) => {
  await page.goto(DEMO);
  await page.waitForFunction(() => window.__mm_ready === true);
});

test("§M.8 single-left a token fires the borderless click-to-edit gesture", async ({ page }) => {
  await page.locator('.mm-text[data-editable="1"]').first().click();
  await expect(page.locator("#status")).toContainText("edit token");
});

test("inline {ref} expansion — clicking the ▸ dropdown reveals the next rank", async ({ page }) => {
  const before = await page.locator(".mm-line").count();
  await page.locator(".mm-drop").first().click();
  expect(await page.locator(".mm-line").count()).toBeGreaterThan(before);
});

test("§M.6 right-click a dropdown folds/unfolds inline (fold-state gesture)", async ({ page }) => {
  const before = await page.locator(".mm-line").count();
  await page.locator(".mm-drop").first().click({ button: "right" });
  expect(await page.locator(".mm-line").count()).not.toBe(before);
});

test("§15.1 panel ⇄ graph dialectic — circular nodes + undirected edges, symmetric", async ({ page }) => {
  expect((await page.evaluate(() => window.__mm_state())).mode).toBe("panel");
  await page.evaluate(() => window.__mm_toggleMode());
  const graph = await page.evaluate(() => window.__mm_state());
  expect(graph.mode).toBe("graph");
  expect(graph.gnodes.length, "computation-graph nodes").toBeGreaterThan(0);
  expect(graph.edges, "undirected edges").toBeGreaterThan(0);
  expect(parseFloat(graph.gnodeRound), "§15.1 circular node (border-radius)").toBeGreaterThan(0);
  await page.evaluate(() => window.__mm_toggleMode());
  expect((await page.evaluate(() => window.__mm_state())).mode, "symmetric flip").toBe("panel");
});

// --- Phase 2 build targets in the LIVE `/` editor (un-fixme as EDIT-01/02 land) ---
// Each needs a rendered panel from a (fixture) scan; the demo logs the gesture,
// the served editor performs the textarea swap.
test.fixme("EDIT-01 click-to-edit swaps a textarea with the caret at the click point", async () => {
  // click a printed token in the served editor → expect a <textarea> focused,
  // selectionStart matching the click column; Shift-Enter soft-newline; Enter commits.
});
test.fixme("EDIT-02 `{` opens autocomplete over concept names; selecting inserts {name}", async () => {});
test.fixme("EDIT-02 Tab/Shift-Tab re-parent, Enter adds a sibling (+→/+↓ field growth)", async () => {});
test.fixme("EDIT-03 no authoritative frontend state — a dropped-WS reconnect re-renders the slate identically", async () => {});
