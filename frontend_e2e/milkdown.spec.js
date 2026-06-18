// Milkdown black-slate editable layer — acceptance (docs/MILKDOWN_SLATE_GOAL.md).
//
// Verifies the controlled-view seam against the served demo (the bundled Milkdown
// editor): it renders, is the black slate, accepts inbound replace-all (store →
// view), reads markdown back, fires the outbound commit on blur, and (record mode)
// expands recursive {ref} dropdowns inline. The full gesture model, the §3 syntax
// round-trip, and the no-authoritative-state guard are the next steps (fixme below).
const { test, expect } = require("@playwright/test");

const DEMO = "/static/js/fe/milkdown_demo.html";
const RECORD_DEMO = "/static/js/fe/milkdown_record_demo.html";

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

// T2 / §3.2 — recursive {ref} rendering in the Milkdown view. The record-mode
// demo seeds a TWO-LEVEL ref chain (CARD → {details page} → {acme press}); the
// ▸/▾ dropdown is a clickable ProseMirror decoration; expansion is computed by
// magic_markdown.mjs::renderPanel and pushed through the same setText seam.
test("recursive {ref} — a {ref} expands the next rank inline, recursively; collapse restores", async ({ page }) => {
  await page.goto(RECORD_DEMO);
  await page.waitForFunction(() => window.__milk_ready === true, { timeout: 10000 });

  const folds = page.locator(".mm-ref-fold");
  // rest: exactly one collapsed dropdown (the {details page} ref)
  await expect(folds).toHaveCount(1);
  await expect(folds.first()).toHaveText("▸");
  const txt = () => page.evaluate(() => window.__milk_text());
  expect(await txt()).not.toContain("mediatype"); // a DETAILS child — hidden at rest

  // expand level 1 → the target's rank-1 children inline; glyph flips ▸→▾; the
  // nested {acme press} ref now surfaces as a second, still-collapsed dropdown.
  await page.locator('.mm-ref-fold[data-fold-index="0"]').click();
  await expect(page.locator('.mm-ref-fold[data-fold-index="0"]')).toHaveText("▾");
  expect(await txt()).toContain("mediatype");
  await expect(folds).toHaveCount(2);
  await expect(page.locator('.mm-ref-fold[data-fold-index="1"]')).toHaveText("▸");
  expect(await txt()).not.toContain("ACME Press"); // PUBLISHER child — still hidden

  // expand level 2 (recursive) → PUBLISHER's children inline beneath the inlined ref
  await page.locator('.mm-ref-fold[data-fold-index="1"]').click();
  expect(await txt()).toContain("ACME Press");
  expect(await txt()).toContain("Princeton, NJ");
  expect(await page.evaluate(() => window.__milk_expanded())).toEqual(["0.1", "0.1/2"]);

  // collapse the root ref → the whole inlined subtree (both ranks) disappears
  await page.locator('.mm-ref-fold[data-fold-index="0"]').click();
  await expect(folds).toHaveCount(1);
  await expect(folds.first()).toHaveText("▸");
  expect(await txt()).not.toContain("mediatype");
  expect(await txt()).not.toContain("ACME Press");
});
test.fixme("gestures — single/double/right/double-right resolve over the Milkdown DOM (fold, panel⇄graph, delete)", async () => {});
test.fixme("syntax — the §3 tab/newline+{ref} grammar round-trips print→Milkdown→parse identically", async () => {});
test.fixme("lifecycle + no-authoritative-state — commit routes through concept_lifecycle; reconnect re-renders identically", async () => {});
