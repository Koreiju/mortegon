/**
 * magic_markdown_panel.mjs — the black-slate DOM projection of the
 * magic-markdown model (magic_markdown.mjs).
 *
 * `panelVDom` is PURE (model → a plain element spec), so it is unit-testable
 * in Node without a DOM. `mount` is the thin `document` glue that realises the
 * spec and wires the two gestures the spec exposes (click a dropdown char →
 * toggle; click a text token → edit). This keeps the magic in testable logic
 * and the DOM binding trivial.
 *
 * The slate (BLACK_SLATE_GOAL.md §3, USER_REQUIREMENTS_VERBATIM §S.4/§T/§V):
 *   - ONE editable text surface, thin silver border, black fill, serif white;
 *   - NO chrome — no header, no title bar, no buttons, no ×/minimise;
 *   - each field line is plain text with depth indentation (tabs);
 *   - a field that links to a hidden node shows a clickable dropdown CHARACTER
 *     (▸/▾) in-text; clicking it expands the next rank inline (the model does
 *     the expansion, this just renders + toggles);
 *   - text tokens are click-to-edit (borderless, M.8) — marked editable here,
 *     the textarea swap is done in `mount`.
 */

import { renderPanel, renderGraph, GLYPH_EXPANDED } from "./magic_markdown.mjs";

const INDENT_PX = 16; // one tab depth
const SVG_NS = "http://www.w3.org/2000/svg";
const SVG_TAGS = new Set(["svg", "line", "circle", "g", "path", "ellipse", "text"]);

/** A tiny element spec: { tag, attrs, children?, text? }. */
function el(tag, attrs = {}, children = []) {
  return { tag, attrs, children };
}
function txt(tag, attrs, text) {
  return { tag, attrs, text };
}

/**
 * panelVDom(rootNode, opts) → element spec for the whole slate.
 * opts is the renderPanel opts (registry, expanded, signals, mode).
 */
export function panelVDom(rootNode, opts = {}) {
  const lines = renderPanel(rootNode, opts);
  const lineEls = lines.map((l) => {
    const children = [];
    if (l.glyph) {
      // the clickable dropdown CHARACTER, in-text
      children.push(txt("span", {
        class: "mm-drop",
        role: "button",
        "data-path": l.path,
        "data-open": l.glyph === GLYPH_EXPANDED ? "1" : "0",
        "aria-label": l.glyph === GLYPH_EXPANDED ? "collapse" : "expand",
      }, l.glyph));
    }
    // the field text — click-to-edit (borderless), marked editable unless
    // it is an inlined (read-through) line from an expanded external node.
    children.push(txt("span", {
      class: "mm-text" + (l.source === "expanded" ? " mm-readthrough" : ""),
      "data-path": l.path,
      "data-editable": l.source === "own" ? "1" : "0",
    }, l.text));
    return el("div", {
      class: "mm-line",
      "data-path": l.path,
      "data-depth": String(l.depth),
      style: `padding-left:${l.depth * INDENT_PX}px`,
    }, children);
  });
  return el("div", {
    class: "mm-slate",
    // the one black-slate contract; no chrome children anywhere
    style: "background:#000;color:#fff;border:1px solid var(--slate-border,#c0c0c0);" +
           "font-family:Georgia,'Times New Roman',serif;border-radius:6px;" +
           "padding:8px 10px;white-space:pre;",
  }, lineEls);
}

/**
 * graphVDom(rootNode, opts) → element spec for the computation-graph half of
 * the dialect (§V / §15.1): each visible field is a **minimalist circular
 * node** carrying ONLY its text (root-most field), laid out by depth × order,
 * joined by undirected silver lines (no arrowheads, O.16). Node-count parity
 * with the panel (O.1). No titles, no bars, no buttons.
 */
export function graphVDom(rootNode, opts = {}) {
  const { nodes, edges } = renderGraph(rootNode, opts);
  const X0 = 24, Y0 = 24, DX = 210, DY = 70;
  const pos = new Map();
  const nodeEls = nodes.map((n, i) => {
    const label = (n.glyph ? n.glyph + " " : "") + n.label;
    const w = Math.max(64, Math.min(220, label.length * 8 + 24));
    const h = 48;
    const x = X0 + n.depth * DX;
    const y = Y0 + i * DY;
    pos.set(n.id, { cx: x + w / 2, cy: y + h / 2 });
    const round = w <= h + 24 ? "50%" : "24px"; // circle for short text, pill otherwise
    return txt("div", {
      class: "mm-gnode",
      "data-path": n.id,
      "data-glyph": n.glyph || "",
      style: `position:absolute;left:${x}px;top:${y}px;width:${w}px;height:${h}px;` +
        `display:flex;align-items:center;justify-content:center;text-align:center;` +
        `background:#000;color:#fff;border:1px solid var(--slate-border,#c0c0c0);` +
        `border-radius:${round};font-family:Georgia,'Times New Roman',serif;font-size:12px;` +
        `padding:2px 8px;box-sizing:border-box;overflow:hidden;`,
    }, label);
  });
  const lineEls = edges.map((e) => {
    const a = pos.get(e.from), b = pos.get(e.to);
    return el("line", {
      x1: String(a.cx), y1: String(a.cy), x2: String(b.cx), y2: String(b.cy),
      stroke: "var(--slate-border,#c0c0c0)", "stroke-width": "1", opacity: "0.7",
    });
  });
  const height = Y0 + nodes.length * DY + 24;
  const width = X0 + (Math.max(0, ...nodes.map((n) => n.depth)) + 1) * DX;
  const svg = el("svg", {
    class: "mm-edges",
    style: `position:absolute;left:0;top:0;width:${width}px;height:${height}px;pointer-events:none;`,
  }, lineEls);
  return el("div", {
    class: "mm-graph",
    style: `position:relative;width:${width}px;height:${height}px;`,
  }, [svg, ...nodeEls]);
}

/** Collect every element spec (depth-first) for inspection/testing. */
export function flattenVDom(spec, out = []) {
  out.push(spec);
  for (const c of spec.children || []) flattenVDom(c, out);
  return out;
}

// ── thin DOM glue (not unit-tested; trivial) ───────────────────────────────

/** Realise an element spec into a real DOM node (browser only, SVG-aware). */
function realise(spec) {
  const node = SVG_TAGS.has(spec.tag)
    ? document.createElementNS(SVG_NS, spec.tag)
    : document.createElement(spec.tag);
  for (const [k, v] of Object.entries(spec.attrs || {})) node.setAttribute(k, v);
  if (spec.text != null) node.textContent = spec.text;
  for (const c of spec.children || []) node.appendChild(realise(c));
  return node;
}

/**
 * mount(host, rootNode, opts, handlers) — render the slate (or graph) into
 * `host` and wire the gestures. `opts.mode` ('panel' | 'graph') selects the
 * representation (§V "going between" the two halves). `handlers = {
 * onToggle(path), onEdit(path), onTogglePanelGraph() }`. Re-call to re-render.
 */
export function mount(host, rootNode, opts = {}, handlers = {}) {
  host.innerHTML = "";
  const isGraph = opts.mode === "graph";
  const dom = realise(isGraph ? graphVDom(rootNode, opts) : panelVDom(rootNode, opts));
  dom.addEventListener("click", (ev) => {
    const drop = ev.target.closest(".mm-drop");
    if (drop) { handlers.onToggle && handlers.onToggle(drop.getAttribute("data-path")); ev.stopPropagation(); return; }
    const gnode = ev.target.closest(".mm-gnode");
    if (gnode && gnode.getAttribute("data-glyph")) {
      handlers.onToggle && handlers.onToggle(gnode.getAttribute("data-path")); return;
    }
    const text = ev.target.closest('.mm-text[data-editable="1"]');
    if (text) { handlers.onEdit && handlers.onEdit(text.getAttribute("data-path")); }
  });
  // double-left on the body (not a token/node) → panel ⇄ graph (M.7 / §V)
  dom.addEventListener("dblclick", (ev) => {
    if (ev.target.closest(".mm-drop, .mm-gnode, .mm-text")) return;
    handlers.onTogglePanelGraph && handlers.onTogglePanelGraph();
  });
  host.appendChild(dom);
  return dom;
}

export default { panelVDom, graphVDom, flattenVDom, mount };
