// Milkdown black-slate editable layer — acceptance (docs/MILKDOWN_SLATE_GOAL.md).
//
// Verifies the controlled-view seam against the served demo (the bundled Milkdown
// editor): it renders, is the black slate, accepts inbound replace-all (store →
// view), reads markdown back, and fires the outbound commit on blur. Recursive
// {ref} + the full gesture model are the next build steps (fixme below).
const { test, expect } = require("@playwright/test");

const DEMO = "/static/js/fe/milkdown_demo.html";

test.beforeEach(async ({ page }) => {
  await page.goto(DEMO);
  await page.waitForFunction(() => window.__milk_ready === true, { timeout: 10000 });
});

test("Milkdown mounts + renders the field content (editable surface)", async ({ page }) => {
  const ed = page.locator(".mm-milkdown");
  await expect(ed).toHaveCount(1);
  await expect(ed).toHaveAttribute("contenteditable", "true");
  await expect(ed).toContainText("Princeton University Library Chronicle");
});

test("§S.4 black slate — black fill · silver border · serif white", async ({ page }) => {
  const s = await page.locator("#host").evaluate((el) => {
    const cs = getComputedStyle(el);
    return { fill: cs.backgroundColor, border: cs.borderColor, font: cs.fontFamily, color: cs.color };
  });
  expect(s.fill).toBe("rgb(0, 0, 0)");
  expect(s.border).toBe("rgb(192, 192, 192)");
  expect(s.color).toBe("rgb(255, 255, 255)");
  expect(s.font.toLowerCase()).toMatch(/serif|georgia/);
});

test("inbound truth — setText (store → view) replaces the doc; read() round-trips", async ({ page }) => {
  await page.evaluate(() => window.__milk_setText("Replaced by the store\n\n- one\n- two"));
  await expect(page.locator(".mm-milkdown")).toContainText("Replaced by the store");
  const md = await page.evaluate(() => window.__milk_read());
  expect(md).toContain("Replaced by the store");
  expect(md).toMatch(/one/);
});

test("outbound intent — editing + blur fires onCommit with the markdown", async ({ page }) => {
  const ed = page.locator(".mm-milkdown");
  await ed.click();
  await page.keyboard.type(" EDITED");
  await page.locator("#host").evaluate((el) => el.blur());
  await ed.evaluate((el) => el.blur());
  await page.locator("body").click({ position: { x: 5, y: 5 } });
  await page.waitForTimeout(200);
  const committed = await page.evaluate(() => window.__milk_lastCommit());
  expect(committed, "onCommit markdown").toBeTruthy();
  expect(committed).toContain("EDITED");
});

// --- next build steps (MILKDOWN_SLATE_GOAL §3/§4; un-fixme as they land) ---
test.fixme("recursive {ref} — a {ref} expands the next rank inline, recursively", async () => {});
test.fixme("gestures — single/double/right/double-right resolve over the Milkdown DOM (fold, panel⇄graph, delete)", async () => {});
test.fixme("syntax — the §3 tab/newline+{ref} grammar round-trips print→Milkdown→parse identically", async () => {});
test.fixme("lifecycle + no-authoritative-state — commit routes through concept_lifecycle; reconnect re-renders identically", async () => {});
