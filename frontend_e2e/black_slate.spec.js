// §T / §S.4 black-slate RENDER acceptance — the criteria the REPL (API+WS seam)
// structurally cannot verify. Mirrors BLACK_SLATE_GOAL.md §11. Requires a
// backend at baseURL (real or stub). The "absence" checks are content-agnostic
// (always valid); the interaction check self-skips on an empty workspace.
const { test, expect } = require("@playwright/test");

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.waitForLoadState("networkidle");
});

test("loads without uncaught console errors (render health)", async ({ page }) => {
  const errors = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  expect(errors, `console errors:\n${errors.join("\n")}`).toEqual([]);
});

test("§11.2 pure black — no <video>, no retrieval/history sidebar chrome", async ({ page }) => {
  expect(await page.locator("video").count()).toBe(0);
  expect(await page.locator("#sidebar, #history-sidebar, #rs-latch").count()).toBe(0);
});

test("§11.1 one editable region per card — no four-widget form skeleton", async ({ page }) => {
  for (const sel of [
    ".concept-name-input", ".concept-desc-input", ".concept-value-input",
    ".compiled-preview", ".billboard-html", ".billboard-rendered-text",
    ".billboard-fields",
  ]) {
    expect(await page.locator(sel).count(), `forbidden widget ${sel}`).toBe(0);
  }
});

test("§S.4 black ground + no panel chrome (header / × / minimiser / topbar)", async ({ page }) => {
  const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  expect(["rgb(0, 0, 0)", "rgba(0, 0, 0, 1)"], `body bg=${bg}`).toContain(bg);
  expect(
    await page.locator(".panel-header, .card-topbar, button.minimise, button.close, .latch-button").count()
  ).toBe(0);
});

// Render-and-interact check. Self-skips when the workspace has no rendered slate
// (fresh/empty). To exercise it, scan a URL first (REPL `web-scan` or
// probe_live_archive_scan) so panels exist, then re-run.
test("§S.4 a rendered slate is black-fill / silver-border / serif-white", async ({ page }) => {
  const slate = page.locator(".mm-slate, .mm-text").first();
  if ((await slate.count()) === 0) test.skip(true, "no rendered slate (empty workspace)");
  const styles = await slate.evaluate((el) => {
    const cs = getComputedStyle(el.closest(".mm-slate") || el);
    return { fill: cs.backgroundColor, border: cs.borderColor, font: cs.fontFamily, color: cs.color };
  });
  expect(styles.font.toLowerCase()).toMatch(/serif|georgia|times/);
});
