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
const SYNTAX_DEMO = "/static/js/fe/milkdown_syntax_demo.html";

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
// T5 / §3.3 — the FULL gesture model resolves over the Milkdown DOM. The same
// pure `resolveGesture` the custom slate uses classifies a target the Milkdown
// DOM feeds it; left gestures fire on mousedown (a fold beats the caret), right
// gestures on contextmenu with a single/double debounce. We drive the installed
// handlers with real MouseEvents and assert the dispatched action per gesture.
test("gestures — single/double/right/double-right resolve over the Milkdown DOM (fold, panel⇄graph, delete)", async ({ page }) => {
  await page.goto(RECORD_DEMO);
  await page.waitForFunction(() => window.__milk_ready === true, { timeout: 10000 });

  // single-left on the ▸ fold glyph → TOGGLE_FOLD (and it functionally expands)
  await page.locator('.mm-ref-fold[data-fold-index="0"]').click();
  expect(await page.evaluate(() => window.__milk_expanded())).toContain("0.1");
  expect(await page.evaluate(() => window.__milk_gestures().map((g) => g.action))).toContain("toggle_fold");

  const recorded = await page.evaluate(async () => {
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    const host = document.getElementById("host");
    const refLine = [...host.querySelectorAll("li, p")].find((b) => /\{[^}]+\}/.test(b.textContent));
    window.__milk_gestures_clear();
    // double-left on the body → TOGGLE_PANEL_GRAPH
    host.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, button: 0, detail: 2 }));
    // single right-click on a {ref} line → (debounced) TOGGLE_FOLD
    refLine.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, button: 2, detail: 1 }));
    await sleep(300);
    // double right-click on a {ref} line → DELETE_REF
    refLine.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, button: 2, detail: 1 }));
    refLine.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, button: 2, detail: 2 }));
    await sleep(300);
    return window.__milk_gestures();
  });
  const byTarget = Object.fromEntries(recorded.map((g) => [g.target + ":" + g.action, true]));
  expect(byTarget["body:toggle_panel_graph"], "double-left body → panel⇄graph").toBe(true);
  expect(byTarget["ref:toggle_fold"], "right-click ref → fold").toBe(true);
  expect(byTarget["ref:delete_ref"], "double-right ref → delete").toBe(true);
});

// T6 / §3.4 — the §3 tab/newline+{ref} grammar round-trips THROUGH a real
// Milkdown instance: print(record) → Milkdown → read() → markdownToFieldText →
// parse → serialize is identity (modulo commonmark's `*` bullets, loose-list
// blank lines, and backslash escapes, which markdownToFieldText reverses).
test("syntax — the §3 tab/newline+{ref} grammar round-trips print→Milkdown→parse identically", async ({ page }) => {
  await page.goto(SYNTAX_DEMO);
  await page.waitForFunction(() => window.__milk_ready === true, { timeout: 10000 });
  const SAMPLES = [
    "DuckDuckGo\n\tscanner {scan for duckduckgo url}\n\tport : 80", // single root + {ref} (spaces) + kv
    "line a\nline b\n\tchild : 1\nline c",                          // forest / flat content tree
    "scan for duckduckgo url\n\tsearch {}",                         // names with spaces + empty {} on-ramp
    "Report\n\tnote : a_b_c with under_scores\n\tpath : src/utils/foo.ts", // escape-recovery (\_)
    "Root\n\tparent\n\t\tchild a : 1\n\t\tchild b : 2\n\tsibling : x",    // depth-2 nesting
    "Tree\n\ta\n\t\tb\n\t\t\tc : deep",                            // depth-3 nesting
  ];
  for (const s of SAMPLES) {
    const r = await page.evaluate((text) => window.__milk_roundtrip(text), s);
    expect(r.roundtrip, `round-trip mismatch for:\n${s}\nmarkdown:\n${r.markdown}`).toBe(r.original);
  }
});
// T7 / §2.4 / EDIT-03 — no authoritative frontend state. The ONLY way truth
// enters the controlled view is `setText` (store → view). After the user edits
// the live ProseMirror doc (state diverges), a dropped-WS reconnect re-pushes the
// store text and the view reconciles IDENTICALLY — zero ProseMirror "overhang".
// (The companion guarantee, that a commit routes through concept_lifecycle.py, is
// asserted at the API/WS seam by `env-scenario --name click-to-edit`.)
test("no authoritative frontend state — reconnect (setText) re-renders identically, no overhang", async ({ page }) => {
  const r0 = await page.evaluate(() => window.__milk_read()); // store truth (stabilized)
  const ed = page.locator(".mm-milkdown");
  await ed.click();
  await page.keyboard.type(" LOCAL OVERHANG");
  expect(await page.evaluate(() => window.__milk_read()), "view diverged").toContain("LOCAL OVERHANG");

  await page.evaluate((t) => window.__milk_setText(t), r0); // the reconnect re-push
  const r1 = await page.evaluate(() => window.__milk_read());
  expect(r1, "reconnect re-render is identical to the store truth").toBe(r0);
  expect(r1).not.toContain("LOCAL OVERHANG"); // the local edit left no overhang
});
