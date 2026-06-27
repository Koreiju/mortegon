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
import { resolveGesture, Action } from "./magic_markdown_gestures.mjs";

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

// Double-right-click debounce window (Pitfall 4 / Assumption A3 — no native
// double-right DOM event exists; ~400ms matches a typical OS double-click
// interval, an implementation-discretion threshold, not design-locked).
const DOUBLE_RIGHT_MS = 400;
// Drag-classification move-threshold (px) — distinguishes a press→move→release
// drag from a press→release click with no intervening move (a few px of jitter
// tolerance, implementation discretion per the Drag-Wire Affordance Contract).
const DRAG_MOVE_PX = 4;

/** True when rootNode is a read-only python-native / foundation-fixture node
 * (🔒 gate) — mirrors the legacy cp/concept_graph.js ~line 1687 check exactly:
 * /^fixture::/.test(backing_pointer) || /^python_/.test(type_hint). */
function isReadOnlyRoot(rootNode) {
  if (!rootNode) return false;
  return /^python_/.test(rootNode.type_hint || "") || /^fixture::/.test(rootNode.backing_pointer || "");
}

/** Classify a DOM event target into the resolveGesture `target` vocabulary
 * ('dropdown' | 'ref' | 'token' | 'self' | 'body'), mirroring the existing
 * click handler's closest()-based dispatch shape exactly. */
function classifyTarget(ev, dom) {
  const drop = ev.target.closest(".mm-drop");
  if (drop) return { kind: "dropdown", el: drop };
  const gnode = ev.target.closest(".mm-gnode");
  if (gnode) return { kind: gnode === dom.firstElementChild ? "self" : "token", el: gnode };
  const text = ev.target.closest(".mm-text");
  if (text) return { kind: "token", el: text };
  const line = ev.target.closest(".mm-line");
  if (line && line.getAttribute("data-depth") === "0") return { kind: "self", el: line };
  return { kind: "body", el: null };
}

/**
 * mount(host, rootNode, opts, handlers) — render the slate (or graph) into
 * `host` and wire the gestures. `opts.mode` ('panel' | 'graph') selects the
 * representation (§V "going between" the two halves). `handlers = {
 * onToggle(path), onEdit(path), onTogglePanelGraph(), onCollapse(path),
 * onDelete(path, el), onWire(sourcePath, targetPath) }`. Re-call to re-render.
 *
 * Every handler classifies the raw DOM event then calls the SHARED
 * resolveGesture() (magic_markdown_gestures.mjs) — never an inline
 * if(button===) chain (T-07-09 / RESEARCH Don't Hand-Roll).
 */
export function mount(host, rootNode, opts = {}, handlers = {}) {
  host.innerHTML = "";
  const isGraph = opts.mode === "graph";
  const dom = realise(isGraph ? graphVDom(rootNode, opts) : panelVDom(rootNode, opts));
  const readOnly = isReadOnlyRoot(rootNode);

  dom.addEventListener("click", (ev) => {
    const drop = ev.target.closest(".mm-drop");
    if (drop) { handlers.onToggle && handlers.onToggle(drop.getAttribute("data-path")); ev.stopPropagation(); return; }
    const gnode = ev.target.closest(".mm-gnode");
    if (gnode && gnode.getAttribute("data-glyph")) {
      handlers.onToggle && handlers.onToggle(gnode.getAttribute("data-path")); return;
    }
    const text = ev.target.closest('.mm-text[data-editable="1"]');
    if (text) {
      // 🔒 gate — read-only nodes refuse single-left edit (no-op highlight);
      // exploration gestures (contextmenu/dblclick/hover) are left intact.
      if (readOnly) return;
      const { action } = resolveGesture({ button: "left", clicks: 1, target: "token", mode: opts.mode });
      if (action === Action.EDIT_TOKEN) handlers.onEdit && handlers.onEdit(text.getAttribute("data-path"));
    }
  });
  // double-left on the body (not a token/node) → panel ⇄ graph (M.7 / §V)
  dom.addEventListener("dblclick", (ev) => {
    if (ev.target.closest(".mm-drop, .mm-gnode, .mm-text")) return;
    const { action } = resolveGesture({ button: "left", clicks: 2, target: "body", mode: opts.mode });
    if (action === Action.TOGGLE_PANEL_GRAPH) handlers.onTogglePanelGraph && handlers.onTogglePanelGraph();
  });

  // ── right-click: single-right fold/collapse, double-right delete ────────
  // Pitfall 4 — no native double-right DOM event; manual timestamp debounce
  // over consecutive contextmenu events on the SAME target synthesizes
  // {clicks:2}.
  let lastRight = { ts: 0, el: null };
  dom.addEventListener("contextmenu", (ev) => {
    ev.preventDefault();
    const { kind, el } = classifyTarget(ev, dom);
    if (kind === "body") return;
    const now = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
    const isDoubleRight = lastRight.el === el && (now - lastRight.ts) <= DOUBLE_RIGHT_MS;
    if (isDoubleRight) {
      lastRight = { ts: 0, el: null }; // consume — a third click starts a fresh pair
      // 🔒 gate (WR-03): a read-only python-native / fixture node permits
      // exploration (single-right fold above) but REFUSES the destructive
      // double-right delete — the lock protects the node's rows from removal.
      if (readOnly) return;
      const { action } = resolveGesture({ button: "right", clicks: 2, target: kind, mode: opts.mode });
      if (action === Action.DELETE_REF) {
        const path = el.getAttribute("data-path");
        handlers.onDelete && handlers.onDelete(path, el);
      }
      return;
    }
    lastRight = { ts: now, el };
    const { action } = resolveGesture({ button: "right", clicks: 1, target: kind, mode: opts.mode });
    if (action === Action.COLLAPSE_TO_NODE) {
      handlers.onCollapse && handlers.onCollapse(el.getAttribute("data-path"));
    } else if (action === Action.TOGGLE_FOLD) {
      handlers.onToggle && handlers.onToggle(el.getAttribute("data-path"));
    }
  });

  // ── drag-wire (graph form): mousedown on a .mm-gnode → mousemove past the
  // move-threshold flips into drag mode (renders a transient SOLID line, no
  // dash, per the Drag-Wire Affordance Contract) → mouseup on another
  // .mm-gnode wires the link (inheritTypes:true, N.4); mouseup on empty
  // canvas discards (no edge, no error). Torn down on every mouseup
  // (success or discard) — no per-frame accumulation (T-07-10).
  let dragState = null; // { sourceEl, sourcePath, startX, startY, dragging, lineEl }
  function teardownDrag() {
    if (dragState && dragState.lineEl && dragState.lineEl.parentNode) {
      dragState.lineEl.parentNode.removeChild(dragState.lineEl);
    }
    dragState = null;
  }
  dom.addEventListener("mousedown", (ev) => {
    if (ev.button !== 0) return; // left button only
    const gnode = ev.target.closest(".mm-gnode");
    if (!gnode) return;
    if (dragState) teardownDrag(); // WR-01: drop any stale drag (+ orphan line) before starting a new one
    dragState = {
      sourceEl: gnode, sourcePath: gnode.getAttribute("data-path"),
      startX: ev.clientX, startY: ev.clientY, dragging: false, lineEl: null,
    };
  });
  dom.addEventListener("mousemove", (ev) => {
    if (!dragState) return;
    const dx = ev.clientX - dragState.startX, dy = ev.clientY - dragState.startY;
    if (!dragState.dragging && Math.hypot(dx, dy) < DRAG_MOVE_PX) return;
    dragState.dragging = true;
    // transient SOLID line (no stroke-dasharray) from source to pointer —
    // the only live visual feedback during the gesture (Forbidden Concepts:
    // no dashed/dotted lines anywhere).
    if (!dragState.lineEl) {
      const svgHost = dom.querySelector("svg.mm-edges") || dom;
      const line = document.createElementNS(SVG_NS, "line");
      line.setAttribute("class", "mm-drag-line");
      line.setAttribute("stroke", "var(--slate-border,#c0c0c0)");
      line.setAttribute("stroke-width", "1");
      svgHost.appendChild(line);
      dragState.lineEl = line;
    }
    const srcRect = dragState.sourceEl.getBoundingClientRect();
    const hostRect = dom.getBoundingClientRect();
    dragState.lineEl.setAttribute("x1", String(srcRect.left + srcRect.width / 2 - hostRect.left));
    dragState.lineEl.setAttribute("y1", String(srcRect.top + srcRect.height / 2 - hostRect.top));
    dragState.lineEl.setAttribute("x2", String(ev.clientX - hostRect.left));
    dragState.lineEl.setAttribute("y2", String(ev.clientY - hostRect.top));
  });
  dom.addEventListener("mouseup", (ev) => {
    if (!dragState) return;
    const wasDragging = dragState.dragging;
    const sourcePath = dragState.sourcePath;
    teardownDrag();
    if (!wasDragging) return; // press→release with no move stays a click/edit
    const targetGnode = ev.target.closest(".mm-gnode");
    if (!targetGnode || targetGnode.getAttribute("data-path") === sourcePath) return; // empty canvas / same node — discard, no error
    const { action } = resolveGesture({ button: "left", drag: true, target: "token", mode: opts.mode });
    if (action === Action.WIRE_LINK) {
      handlers.onWire && handlers.onWire(sourcePath, targetGnode.getAttribute("data-path"));
    }
  });
  // a drag released/aborted outside the host tears down cleanly (WR-01): an
  // IN-PROGRESS drag leaving the host removes its transient line + clears state
  // (not just a not-yet-started press), so no orphaned <line> accumulates.
  dom.addEventListener("mouseleave", () => { if (dragState) teardownDrag(); });

  // ── hover next-rank preview (EXPLORE-01 / Hover-Preview Contract) ───────
  // Hovering a token/ref/self target previews the SAME rank-1 subtree a
  // right-click would commit, but ephemerally — this is NOT one of
  // resolveGesture's click-based Actions (there is no button press), so it
  // is wired directly as its own pair of handlers rather than synthesizing a
  // fake gesture through the resolver. mount() never fetches /next_rank
  // itself (backend computes, frontend renders) — it only classifies the
  // hovered target and reports {path, el} to the caller, which resolves
  // path→concept_id and calls the gateway; mount() then renders whatever
  // preview payload the caller hands back via a re-call (handlers.onHover
  // is fire-only; the caller owns committing a transient overlay).
  // Un-hover collapses the preview UNLESS it was already committed by a
  // right-click in the same interaction — committed state (fold/expanded)
  // persists independently of hover and is never torn down here.
  let hoveredEl = null;
  dom.addEventListener("mouseover", (ev) => {
    const { kind, el } = classifyTarget(ev, dom);
    if (kind === "body" || !el) return;
    if (hoveredEl === el) return; // already previewing this exact target
    hoveredEl = el;
    handlers.onHoverPreview && handlers.onHoverPreview(el.getAttribute("data-path"), kind);
  });
  dom.addEventListener("mouseout", (ev) => {
    const { kind, el } = classifyTarget(ev, dom);
    if (!hoveredEl || (el && el === hoveredEl)) {
      // only fire un-hover once the pointer has actually left the previously
      // hovered target (the related target check keeps a move WITHIN the
      // same token from flickering the preview off and back on).
      const related = ev.relatedTarget && ev.relatedTarget.closest ? ev.relatedTarget.closest(".mm-drop, .mm-gnode, .mm-text, .mm-line") : null;
      if (related === hoveredEl) return;
      const leftPath = hoveredEl ? hoveredEl.getAttribute("data-path") : null;
      hoveredEl = null;
      if (leftPath != null) handlers.onHoverEnd && handlers.onHoverEnd(leftPath);
    }
  });

  host.appendChild(dom);
  return dom;
}

export default { panelVDom, graphVDom, flattenVDom, mount };
