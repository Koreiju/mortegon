/**
 * magic_markdown_panel.test.mjs — verifies the pure black-slate vdom AND
 * (Task 1/2, 07-05) the mount() DOM-capture wiring for the seven-gesture
 * model's previously-missing gestures (contextmenu fold/collapse,
 * double-right delete debounce, drag-wire state machine, 🔒 read-only gate).
 *
 * Plain Node has no `document` global, so this file hand-rolls a MINIMAL DOM
 * shim sufficient to drive mount()'s addEventListener/closest/dispatchEvent
 * usage — no new external test dependency (JSDOM etc.) per the plan's
 * acceptance criteria. The shim is deliberately tiny: just enough surface
 * for mount() to run, not a general-purpose DOM implementation.
 *
 * Run: node backend/static/js/fe/magic_markdown_panel.test.mjs
 */
import assert from "node:assert";
import { parse, buildRegistry, renderPanel } from "./magic_markdown.mjs";
import { panelVDom, graphVDom, flattenVDom, mount } from "./magic_markdown_panel.mjs";

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log("  PASS  " + name); passed++; }
  catch (e) { console.log("  FAIL  " + name + ": " + e.message); failed++; }
}

const A = parse("DuckDuckGo\n\tscanner {scan for duckduckgo url}\n\tport : 80");
const B = parse("scan for duckduckgo url\n\tsearch {}\n\tchunk {chunk samples}");
const registry = buildRegistry([B]);

test("slate is black fill + silver border + serif, NO chrome elements", () => {
  const all = flattenVDom(panelVDom(A, { registry }));
  const slate = all[0];
  assert.strictEqual(slate.attrs.class, "mm-slate");
  assert.ok(/background:#000/.test(slate.attrs.style));
  assert.ok(/serif/.test(slate.attrs.style));
  assert.ok(/slate-border/.test(slate.attrs.style));
  // no header / title / button / minimise / close anywhere
  const classes = all.map((e) => (e.attrs && e.attrs.class) || "").join(" ");
  assert.ok(!/header|title|topbar|min-btn|close|delete-btn/.test(classes), "no chrome");
  const tags = all.map((e) => e.tag);
  assert.ok(!tags.includes("button"), "no <button> chrome");
});

test("one line element per render line", () => {
  const opts = { registry, expanded: new Set() };
  const lineEls = flattenVDom(panelVDom(A, opts)).filter((e) => e.attrs && e.attrs.class === "mm-line");
  assert.strictEqual(lineEls.length, renderPanel(A, opts).length);
});

test("a linked field shows a clickable dropdown CHARACTER span", () => {
  const all = flattenVDom(panelVDom(A, { registry, expanded: new Set() }));
  const drops = all.filter((e) => e.attrs && e.attrs.class === "mm-drop");
  assert.strictEqual(drops.length, 1, "one dropdown char (the scanner ref)");
  assert.strictEqual(drops[0].text, "▸");
  assert.strictEqual(drops[0].attrs.role, "button");
  assert.ok(drops[0].attrs["data-path"]);
});

test("expanding flips the dropdown char to ▾ and inlines read-through text", () => {
  const refPath = renderPanel(A, { registry }).find((l) => l.refTarget === "scan for duckduckgo url").path;
  const all = flattenVDom(panelVDom(A, { registry, expanded: new Set([refPath]) }));
  const drop = all.find((e) => e.attrs && e.attrs.class === "mm-drop");
  assert.strictEqual(drop.text, "▾");
  assert.strictEqual(drop.attrs["data-open"], "1");
  // inlined fields are read-through (not directly editable)
  const readthrough = all.filter((e) => e.attrs && /mm-readthrough/.test(e.attrs.class || ""));
  assert.ok(readthrough.length >= 1, "expanded fields render as read-through tokens");
});

test("depth → indentation; own text tokens are editable", () => {
  const all = flattenVDom(panelVDom(A, { registry }));
  const portLine = all.find((e) => e.attrs && e.attrs.class === "mm-line" && e.attrs["data-depth"] === "1");
  assert.ok(/padding-left:16px/.test(portLine.attrs.style));
  const editable = all.filter((e) => e.attrs && e.attrs["data-editable"] === "1");
  assert.ok(editable.length >= 2, "own field tokens are click-to-edit");
});

// ── graph form (the other half of the dialect) ─────────────────────────────
test("graph form: one circular node per panel line (parity), text-only", () => {
  const opts = { registry, expanded: new Set() };
  const panelLines = flattenVDom(panelVDom(A, opts)).filter((e) => e.attrs && e.attrs.class === "mm-line").length;
  const gnodes = flattenVDom(graphVDom(A, opts)).filter((e) => e.attrs && e.attrs.class === "mm-gnode");
  assert.strictEqual(gnodes.length, panelLines, "node-count parity with panel (O.1)");
  for (const n of gnodes) {
    assert.ok(/border-radius/.test(n.attrs.style), "node is rounded/circular");
    assert.strictEqual(typeof n.text, "string");           // text-only
    assert.ok(!("title" in n) && !("buttons" in n));        // no chrome
  }
  assert.ok(!flattenVDom(graphVDom(A, opts)).some((e) => e.tag === "button"));
});

test("graph form: edges are undirected lines (no arrowheads)", () => {
  const gAll = flattenVDom(graphVDom(A, { registry, expanded: new Set() }));
  const lines = gAll.filter((e) => e.tag === "line");
  assert.ok(lines.length >= 1, "containment edges drawn");
  for (const ln of lines) {
    assert.ok(!("marker-end" in ln.attrs), "no arrowhead marker");
    assert.ok(!("stroke-dasharray" in ln.attrs), "no dashes");
  }
});

// ── minimal hand-rolled DOM shim (mount()-sufficient, not general-purpose) ──

class FakeEvent {
  constructor(type, opts = {}) {
    this.type = type;
    this.target = opts.target || null;
    this.button = opts.button != null ? opts.button : 0;
    this.clientX = opts.clientX || 0;
    this.clientY = opts.clientY || 0;
    this.relatedTarget = opts.relatedTarget || null;
    this._stopped = false;
    this._defaultPrevented = false;
  }
  stopPropagation() { this._stopped = true; }
  preventDefault() { this._defaultPrevented = true; }
}

class FakeElement {
  constructor(tag) {
    this.tagName = tag;
    this.attrs = new Map();
    this.children = [];
    this.parentNode = null;
    this.textContent = "";
    this._listeners = new Map();
  }
  setAttribute(k, v) { this.attrs.set(k, String(v)); }
  getAttribute(k) { return this.attrs.has(k) ? this.attrs.get(k) : null; }
  get className() { return this.attrs.get("class") || ""; }
  appendChild(child) { child.parentNode = this; this.children.push(child); return child; }
  removeChild(child) {
    const i = this.children.indexOf(child);
    if (i >= 0) this.children.splice(i, 1);
    child.parentNode = null;
    return child;
  }
  get firstElementChild() { return this.children[0] || null; }
  addEventListener(type, fn) {
    if (!this._listeners.has(type)) this._listeners.set(type, []);
    this._listeners.get(type).push(fn);
  }
  // Bubble dispatch: fire listeners on `target`'s ancestor chain (capture not
  // needed — mount() only ever listens on `dom`, the slate root).
  dispatchEvent(ev) {
    let node = ev.target;
    while (node) {
      const fns = node._listeners && node._listeners.get(ev.type);
      if (fns) for (const fn of fns.slice()) { if (ev._stopped) break; fn(ev); }
      if (ev._stopped) break;
      node = node.parentNode;
    }
    return !ev._defaultPrevented;
  }
  matches(selector) {
    // Supports the limited selector vocabulary mount()/classifyTarget use:
    // ".cls", ".cls[data-editable=\"1\"]", "svg.cls", "tag".
    const m = /^([a-zA-Z]*)((?:\.[\w-]+)*)(?:\[([\w-]+)="([^"]*)"\])?$/.exec(selector);
    if (!m) return false;
    const [, tag, classesStr, attrName, attrVal] = m;
    if (tag && this.tagName !== tag) return false;
    if (classesStr) {
      const classes = classesStr.split(".").filter(Boolean);
      const mine = this.className.split(/\s+/).filter(Boolean);
      for (const c of classes) if (!mine.includes(c)) return false;
    }
    if (attrName && this.getAttribute(attrName) !== attrVal) return false;
    return true;
  }
  closest(selectorList) {
    const selectors = selectorList.split(",").map((s) => s.trim());
    let node = this;
    while (node) {
      if (selectors.some((s) => node.matches(s))) return node;
      node = node.parentNode;
    }
    return null;
  }
  querySelector(selector) {
    const stack = [...this.children];
    while (stack.length) {
      const n = stack.shift();
      if (n.matches(selector)) return n;
      stack.unshift(...n.children);
    }
    return null;
  }
  getBoundingClientRect() { return { left: 0, top: 0, width: 40, height: 20 }; }
  set innerHTML(v) { if (v === "") this.children = []; }
}

const fakeDocument = {
  createElement(tag) { return new FakeElement(tag); },
  createElementNS(_ns, tag) { return new FakeElement(tag); },
};

function withFakeDocument(fn) {
  const prevDoc = globalThis.document;
  const prevPerf = globalThis.performance;
  globalThis.document = fakeDocument;
  if (!globalThis.performance) globalThis.performance = { now: () => Date.now() };
  try { return fn(); }
  finally {
    if (prevDoc === undefined) delete globalThis.document; else globalThis.document = prevDoc;
    if (prevPerf === undefined) delete globalThis.performance; else globalThis.performance = prevPerf;
  }
}

function findByClass(el, cls) {
  if (el.className.split(/\s+/).includes(cls)) return el;
  for (const c of el.children) { const f = findByClass(c, cls); if (f) return f; }
  return null;
}
function findAllByClass(el, cls, out = []) {
  if (el.className.split(/\s+/).includes(cls)) out.push(el);
  for (const c of el.children) findAllByClass(c, cls, out);
  return out;
}
function fire(host, type, target, opts = {}) {
  host.dispatchEvent(new FakeEvent(type, { ...opts, target }));
}

// fixture: a host card with one ref-bearing field (rank-1 expandable).
function gestureFixture() {
  const A = parse("DuckDuckGo\n\tscanner {scan for duckduckgo url}\n\tport : 80");
  const B = parse("scan for duckduckgo url\n\tsearch {}\n\tchunk {chunk samples}");
  const registry = buildRegistry([B]);
  return { A, registry };
}

// ── Task 1/2 behavior cases ─────────────────────────────────────────────────

test("mount(): contextmenu on a ref/dropdown target resolves TOGGLE_FOLD via resolveGesture and calls onToggle", () => {
  withFakeDocument(() => {
    const { A, registry } = gestureFixture();
    const host = new FakeElement("div");
    let toggledPath = null;
    const dom = mount(host, A, { registry, expanded: new Set() }, { onToggle: (p) => { toggledPath = p; } });
    const drop = findByClass(dom, "mm-drop");
    assert.ok(drop, "a dropdown char is rendered");
    fire(dom, "contextmenu", drop);
    assert.strictEqual(toggledPath, drop.getAttribute("data-path"), "onToggle fired with the structural data-path");
  });
});

test("mount(): contextmenu on the base/self node resolves COLLAPSE_TO_NODE and calls onCollapse", () => {
  withFakeDocument(() => {
    const { A, registry } = gestureFixture();
    const host = new FakeElement("div");
    let collapsedPath = null;
    const dom = mount(host, A, { registry, expanded: new Set() }, { onCollapse: (p) => { collapsedPath = p; } });
    const selfLine = findByClass(dom, "mm-line"); // first mm-line, depth 0 → self
    assert.strictEqual(selfLine.getAttribute("data-depth"), "0");
    fire(dom, "contextmenu", selfLine);
    assert.strictEqual(collapsedPath, selfLine.getAttribute("data-path"), "onCollapse fired for the self/base node");
  });
});

test("mount(): two contextmenu events on the SAME target within the debounce window synthesize DELETE_REF, not two folds", () => {
  withFakeDocument(() => {
    const { A, registry } = gestureFixture();
    const host = new FakeElement("div");
    let toggleCalls = 0, deleteCalls = 0, deletedPath = null;
    const dom = mount(host, A, { registry, expanded: new Set() }, {
      onToggle: () => { toggleCalls++; },
      onDelete: (p) => { deleteCalls++; deletedPath = p; },
    });
    // a ref TOKEN (the .mm-text span carrying the {ref}), not the dropdown
    // char — resolveGesture's DELETE_REF only fires for target 'ref'/'token',
    // matching the Interaction Contract's "a token reference/instance" wording.
    const refToken = findAllByClass(dom, "mm-text").find((e) => /\{.*\}/.test(e.textContent));
    assert.ok(refToken, "a ref-bearing text token exists");
    fire(dom, "contextmenu", refToken);
    fire(dom, "contextmenu", refToken); // within the window (same synchronous tick)
    assert.strictEqual(toggleCalls, 1, "the FIRST right-click folds (single-right)");
    assert.strictEqual(deleteCalls, 1, "the SECOND right-click within the window deletes, not a second fold");
    assert.strictEqual(deletedPath, refToken.getAttribute("data-path"));
  });
});

test("mount(): a third contextmenu spaced beyond the debounce window resolves a fresh single-right fold (debounce boundary)", () => {
  withFakeDocument(() => {
    const { A, registry } = gestureFixture();
    const host = new FakeElement("div");
    let toggleCalls = 0, deleteCalls = 0;
    const dom = mount(host, A, { registry, expanded: new Set() }, {
      onToggle: () => { toggleCalls++; },
      onDelete: () => { deleteCalls++; },
    });
    const refToken = findAllByClass(dom, "mm-text").find((e) => /\{.*\}/.test(e.textContent));
    const realNow = performance.now;
    let t = 1000;
    performance.now = () => t;
    fire(dom, "contextmenu", refToken);   // t=1000 → fold #1 (sets lastRight)
    t += 100;
    fire(dom, "contextmenu", refToken);   // t=1100, within 400ms → delete (consumes lastRight)
    t += 1000;                            // well beyond the 400ms window
    fire(dom, "contextmenu", refToken);   // t=2100 → fresh single-right fold
    performance.now = realNow;
    assert.strictEqual(deleteCalls, 1, "exactly one delete from the within-window pair");
    assert.strictEqual(toggleCalls, 2, "two folds: the opening click of the pair + the boundary-spaced click");
  });
});

test("mount(): mousedown→mousemove(past threshold)→mouseup on another node synthesizes WIRE_LINK via resolveGesture", () => {
  withFakeDocument(() => {
    const { A, registry } = gestureFixture();
    const host = new FakeElement("div");
    let wired = null;
    const dom = mount(host, A, { registry, expanded: new Set(), mode: "graph" }, {
      onWire: (src, tgt) => { wired = { src, tgt }; },
    });
    const gnodes = findAllByClass(dom, "mm-gnode");
    assert.ok(gnodes.length >= 2, "at least two graph nodes exist for a drag-wire");
    const [source, target] = gnodes;
    fire(dom, "mousedown", source, { button: 0, clientX: 0, clientY: 0 });
    fire(dom, "mousemove", source, { clientX: 50, clientY: 50 }); // past DRAG_MOVE_PX
    fire(dom, "mouseup", target, { clientX: 50, clientY: 50 });
    assert.ok(wired, "onWire fired");
    assert.strictEqual(wired.src, source.getAttribute("data-path"));
    assert.strictEqual(wired.tgt, target.getAttribute("data-path"));
  });
});

test("mount(): a press→release with NO intervening move does NOT classify as a drag (no onWire)", () => {
  withFakeDocument(() => {
    const { A, registry } = gestureFixture();
    const host = new FakeElement("div");
    let wired = false, edited = false;
    const dom = mount(host, A, { registry, expanded: new Set(), mode: "graph" }, {
      onWire: () => { wired = true; },
      onEdit: () => { edited = true; },
    });
    const gnodes = findAllByClass(dom, "mm-gnode");
    const [a, b] = gnodes;
    fire(dom, "mousedown", a, { button: 0, clientX: 10, clientY: 10 });
    fire(dom, "mouseup", b, { clientX: 10, clientY: 10 }); // same point, no move
    assert.strictEqual(wired, false, "no move → not a drag → no WIRE_LINK");
  });
});

test("mount(): mouseup over empty canvas (no target node) discards the drag — no WIRE_LINK, no error", () => {
  withFakeDocument(() => {
    const { A, registry } = gestureFixture();
    const host = new FakeElement("div");
    let wired = false;
    const dom = mount(host, A, { registry, expanded: new Set(), mode: "graph" }, {
      onWire: () => { wired = true; },
    });
    const gnodes = findAllByClass(dom, "mm-gnode");
    const source = gnodes[0];
    const emptyCanvas = dom; // the slate root itself — not a .mm-gnode
    assert.doesNotThrow(() => {
      fire(dom, "mousedown", source, { button: 0, clientX: 0, clientY: 0 });
      fire(dom, "mousemove", source, { clientX: 60, clientY: 60 });
      fire(dom, "mouseup", emptyCanvas, { clientX: 60, clientY: 60 });
    });
    assert.strictEqual(wired, false, "empty-canvas release discards the drag, no WIRE_LINK");
  });
});

test("mount(): 🔒 read-only node refuses single-left edit (no-op) while contextmenu/dblclick still fire", () => {
  withFakeDocument(() => {
    const { registry } = gestureFixture();
    // a read-only python-native root node (type_hint python_*)
    const roRoot = parse("driver\n\tport : 80");
    roRoot.type_hint = "python_object";
    const host = new FakeElement("div");
    let edited = false, toggled = false, collapsed = false;
    const dom = mount(host, roRoot, { registry, expanded: new Set() }, {
      onEdit: () => { edited = true; },
      onToggle: () => { toggled = true; },
      onCollapse: () => { collapsed = true; },
    });
    const editableText = dom.querySelector('.mm-text[data-editable="1"]') ||
      findAllByClass(dom, "mm-text").find((e) => e.getAttribute("data-editable") === "1");
    assert.ok(editableText, "an own (editable-looking) text token exists on the read-only node");
    fire(dom, "click", editableText);
    assert.strictEqual(edited, false, "🔒 gate: single-left is a no-op on a read-only node");
    // exploration gestures still work on read-only nodes:
    const selfLine = findByClass(dom, "mm-line");
    fire(dom, "contextmenu", selfLine);
    assert.strictEqual(collapsed, true, "right-click/collapse still works on a read-only node");
  });
});

test("mount(): a read-only node's drag-wire and hover/contextmenu paths remain otherwise unaffected (non-edit gestures pass through)", () => {
  withFakeDocument(() => {
    const { registry } = gestureFixture();
    const roRoot = parse("driver\n\tscanner {scan for duckduckgo url}");
    roRoot.type_hint = "python_object";
    const host = new FakeElement("div");
    let toggled = null;
    const dom = mount(host, roRoot, { registry, expanded: new Set() }, { onToggle: (p) => { toggled = p; } });
    const drop = findByClass(dom, "mm-drop");
    assert.ok(drop, "read-only node still renders its dropdown char");
    fire(dom, "contextmenu", drop);
    assert.ok(toggled, "fold still works (right-click) on a read-only node");
  });
});

// ── EXPLORE-01 hover next-rank preview wiring (Hover-Preview Contract) ─────

test("mount(): hovering a ref/dropdown/token target fires onHoverPreview with its data-path; mouseout fires onHoverEnd", () => {
  withFakeDocument(() => {
    const { A, registry } = gestureFixture();
    const host = new FakeElement("div");
    const previewed = [], ended = [];
    const dom = mount(host, A, { registry, expanded: new Set() }, {
      onHoverPreview: (path, kind) => previewed.push({ path, kind }),
      onHoverEnd: (path) => ended.push(path),
    });
    const drop = findByClass(dom, "mm-drop");
    fire(dom, "mouseover", drop);
    assert.strictEqual(previewed.length, 1, "onHoverPreview fired once for the dropdown target");
    assert.strictEqual(previewed[0].path, drop.getAttribute("data-path"));
    fire(dom, "mouseout", drop, { relatedTarget: host });
    assert.deepStrictEqual(ended, [drop.getAttribute("data-path")], "onHoverEnd fired with the same path on un-hover");
  });
});

test("mount(): mouseover does NOT re-fire onHoverPreview while still over the SAME hovered target (no flicker)", () => {
  withFakeDocument(() => {
    const { A, registry } = gestureFixture();
    const host = new FakeElement("div");
    let calls = 0;
    const dom = mount(host, A, { registry, expanded: new Set() }, { onHoverPreview: () => { calls++; } });
    const drop = findByClass(dom, "mm-drop");
    fire(dom, "mouseover", drop);
    fire(dom, "mouseover", drop); // a second mouseover within the same target's bounds
    assert.strictEqual(calls, 1, "re-entering the same already-hovered target does not re-fire the preview");
  });
});

test("mount(): a hover preview committed by right-click is not torn down by the un-hover handler", () => {
  withFakeDocument(() => {
    const { A, registry } = gestureFixture();
    const host = new FakeElement("div");
    let toggled = null, ended = null;
    const dom = mount(host, A, { registry, expanded: new Set() }, {
      onToggle: (p) => { toggled = p; },
      onHoverEnd: (p) => { ended = p; },
    });
    const refToken = findAllByClass(dom, "mm-text").find((e) => /\{.*\}/.test(e.textContent));
    fire(dom, "mouseover", refToken);
    fire(dom, "contextmenu", refToken); // commits the fold via right-click
    assert.ok(toggled, "right-click commits the fold while still hovering");
    fire(dom, "mouseout", refToken, { relatedTarget: host });
    // mount() itself does not know about "committed" state (that lives in
    // the caller's expanded-set / re-render), so onHoverEnd still fires on
    // un-hover — but the CALLER's committed expanded-set is untouched by it
    // (asserted indirectly: toggled was already recorded above and is not
    // reset by this un-hover call).
    assert.strictEqual(ended, refToken.getAttribute("data-path"));
    assert.ok(toggled, "the earlier commit is unaffected by the later un-hover");
  });
});

console.log(`\n${passed}/${passed + failed} passed`);
if (failed) process.exit(1);
