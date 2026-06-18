// Phase 2 — Black-Slate Field Editing (§T / §M.8 / §15.1).
//
// PASSING specs run against the served demo reference (`static/js/fe/demo.html`),
// which renders real static slates and wires the full gesture model
// (magic_markdown_gestures.mjs). FIXME specs are the executable acceptance for
// the LIVE `/` editor build targets (Milkdown contenteditable + caret-at-click,
// `{`-autocomplete, `+→`/`+↓`) — un-fixme them as EDIT-01/02 land. The edit layer
// is Milkdown behind `mount` as a controlled view (docs/MILKDOWN_SLATE_GOAL.md);
// the editable surface is a ProseMirror contenteditable, not a raw <textarea>.
// This is the render-level coverage the REPL (API/WS seam) cannot reach.
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
// T3 / EDIT-01 — against the LIVE served `/` editor (Milkdown opt-in via
// ?slate=milkdown). An authored card is created over the real API, renders as a
// black slate, and single-left on a printed token opens a focused Milkdown
// editable surface for the whole card; Enter commits the full §3 data through the
// lifecycle (PATCH → apply_update_lifecycle, persisted), Esc discards.
test("EDIT-01 click-to-edit opens a focused Milkdown surface; blur commits through the lifecycle, Esc discards", async ({ page, request }) => {
  const NAME = "EDIT01 Card " + Date.now(); // unique → unambiguous panel match
  const create = await request.post("/api/concepts", {
    data: { name: NAME, data: `${NAME}\n\tbody : hello world\n\tport : 80`, workspace_id: "_default" },
  });
  const { concept_id } = await create.json();
  // scope every locator to THIS card's panel — the shared `_default` workspace
  // may hold other cards, and click/poll must target the same one.
  const panel = page.locator(".mm-slate", { hasText: NAME });
  const token = () => panel.locator('.mm-text[data-editable="1"]', { hasText: "body : hello world" });
  try {
    await page.goto("/?slate=milkdown");
    await page.waitForFunction(() => window.__mm_ready === true, { timeout: 15000 });
    await expect(token()).toBeVisible({ timeout: 10000 });

    // single-left a printed token → the Milkdown editable surface mounts, focused
    await token().click();
    const ed = page.locator(".mm-edit-host .mm-milkdown");
    await expect(ed).toHaveCount(1);
    await expect(ed).toHaveAttribute("contenteditable", "true");
    await expect(ed).toBeFocused();

    // the surface mounts with a caret at the end; edit, then blur (click outside)
    // commits through the lifecycle (the surface closes, the value persists).
    // (Enter / Tab are reserved for §3 field growth — EDIT-02 — so commit is blur.)
    await page.keyboard.type(" EDITED");
    await page.locator("#bar").click();
    await expect(page.locator(".mm-edit-host")).toHaveCount(0);
    await expect.poll(async () => (await (await request.get(`/api/concepts/${concept_id}`)).json()).data)
      .toContain("EDITED");

    // re-open and Esc discards (no further mutation)
    await expect(token()).toBeVisible({ timeout: 10000 });
    await token().click();
    const ed2 = page.locator(".mm-edit-host .mm-milkdown");
    await expect(ed2).toHaveCount(1);
    await expect(ed2).toBeFocused();
    await page.keyboard.type(" DISCARDME");
    await page.keyboard.press("Escape");
    await expect(page.locator(".mm-edit-host")).toHaveCount(0);
    const after = (await (await request.get(`/api/concepts/${concept_id}`)).json()).data;
    expect(after).not.toContain("DISCARDME");
  } finally {
    await request.delete(`/api/concepts/${concept_id}?workspace_id=_default`);
  }
});
// T4 / EDIT-02 — `{`-autocomplete binds to an existing concept name (the §3
// typed-linking on-ramp): typing `{` over the Milkdown surface pops the concept
// names; selecting one inserts `{<name>}` into the value, committed via the
// lifecycle on blur.
test("EDIT-02 `{` opens autocomplete over concept names; selecting inserts {name}", async ({ page, request }) => {
  const TS = Date.now();
  const TARGET = "Target Node " + TS;
  const AUTHOR = "Author Card " + TS;
  const targetId = (await (await request.post("/api/concepts", {
    data: { name: TARGET, data: `${TARGET}\n\tkind : place`, workspace_id: "_default" } })).json()).concept_id;
  const authorId = (await (await request.post("/api/concepts", {
    data: { name: AUTHOR, data: `${AUTHOR}\n\tlink : here`, workspace_id: "_default" } })).json()).concept_id;
  const panel = page.locator(".mm-slate", { hasText: AUTHOR });
  const token = () => panel.locator('.mm-text[data-editable="1"]', { hasText: "link : here" });
  try {
    await page.goto("/?slate=milkdown");
    await page.waitForFunction(() => window.__mm_ready === true, { timeout: 15000 });
    await expect(token()).toBeVisible({ timeout: 10000 });
    await token().click();
    await expect(page.locator(".mm-edit-host .mm-milkdown")).toBeFocused();

    // typing `{` + a prefix pops the concept names filtered to the target
    await page.keyboard.type(" {Target");
    await expect.poll(() => page.evaluate(() => window.__mm_ac_open && window.__mm_ac_open())).toBe(true);
    const items = await page.evaluate(() => window.__mm_ac_items());
    expect(items.join("|"), "autocomplete offers the target concept").toContain(TARGET);

    // Enter selects → inserts {TARGET}; blur commits through the lifecycle
    await page.keyboard.press("Enter");
    await page.locator("#bar").click();
    await expect.poll(async () => (await (await request.get(`/api/concepts/${authorId}`)).json()).data)
      .toContain(`{${TARGET}}`);
  } finally {
    await request.delete(`/api/concepts/${targetId}?workspace_id=_default`);
    await request.delete(`/api/concepts/${authorId}?workspace_id=_default`);
  }
});
// T4 / EDIT-02 — §3 field-tree growth in the live Milkdown surface: Enter adds a
// sibling row (+↓), Tab re-parents one rank deeper (+→). These ARE ProseMirror's
// native list keymap (the commonmark preset), and markdownToFieldText maps the
// new list structure back to §3 tab depth on commit.
test("EDIT-02 Tab/Shift-Tab re-parent, Enter adds a sibling (+→/+↓ field growth)", async ({ page, request }) => {
  const NAME = "Grow Card " + Date.now();
  const create = await request.post("/api/concepts", {
    data: { name: NAME, data: `${NAME}\n\tfirst : 1`, workspace_id: "_default" },
  });
  const { concept_id } = await create.json();
  const panel = page.locator(".mm-slate", { hasText: NAME });
  const token = () => panel.locator('.mm-text[data-editable="1"]', { hasText: "first : 1" });
  try {
    await page.goto("/?slate=milkdown");
    await page.waitForFunction(() => window.__mm_ready === true, { timeout: 15000 });
    await expect(token()).toBeVisible({ timeout: 10000 });
    await token().click();
    await expect(page.locator(".mm-edit-host .mm-milkdown")).toBeFocused();

    // caret at end of "first : 1": Enter → sibling (+↓), then Enter+Tab → child (+→)
    await page.keyboard.press("Enter");
    await page.keyboard.type("second : 2");
    await page.keyboard.press("Enter");
    await page.keyboard.press("Tab");
    await page.keyboard.type("child : 3");
    await page.locator("#bar").click(); // blur commits

    await expect(page.locator(".mm-edit-host")).toHaveCount(0);
    await expect.poll(async () => (await (await request.get(`/api/concepts/${concept_id}`)).json()).data)
      .toContain("child : 3");
    const data = (await (await request.get(`/api/concepts/${concept_id}`)).json()).data;
    expect(data, "sibling at rank 1").toContain("\tsecond : 2");
    expect(data, "re-parented one rank deeper").toContain("\t\tchild : 3");
  } finally {
    await request.delete(`/api/concepts/${concept_id}?workspace_id=_default`);
  }
});
// T7 / EDIT-03 — no authoritative frontend state on the live `/` slate: the panel
// is a pure projection of the store. Corrupt the live DOM (divergence), then
// re-derive from the store (exactly what a dropped-WS reconnect bootstrap does) —
// the slate re-renders IDENTICALLY, the corruption leaves no trace.
test("EDIT-03 no authoritative frontend state — a dropped-WS reconnect re-renders the slate identically", async ({ page, request }) => {
  const NAME = "Recon Card " + Date.now();
  const concept_id = (await (await request.post("/api/concepts", {
    data: { name: NAME, data: `${NAME}\n\tbody : hello world\n\tport : 80`, workspace_id: "_default" } })).json()).concept_id;
  const panel = page.locator(".mm-slate", { hasText: NAME });
  try {
    await page.goto("/?slate=milkdown");
    await page.waitForFunction(() => window.__mm_ready === true, { timeout: 15000 });
    await expect(panel).toBeVisible({ timeout: 10000 });
    const s0 = await panel.innerText();

    // diverge: mutate a live DOM row directly (a frontend-owned-state bug would
    // persist this). Corrupt a NON-identifying line so the panel locator (the
    // NAME row) still resolves.
    await panel.locator(".mm-line").nth(1).evaluate((el) => { el.textContent = "CORRUPTED ROW"; });
    expect(await panel.innerText()).toContain("CORRUPTED");

    // reconnect: re-derive the whole grid from the store (the bootstrap re-render)
    await page.evaluate(() => window.__mm_rerender());
    const s1 = await panel.innerText();
    expect(s1, "reconnect re-render is identical").toBe(s0);
    expect(s1).not.toContain("CORRUPTED");
  } finally {
    await request.delete(`/api/concepts/${concept_id}?workspace_id=_default`);
  }
});
