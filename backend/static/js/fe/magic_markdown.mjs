/**
 * magic_markdown.mjs — the "magic markdown" panel core (model + transforms).
 *
 * The black-slate knowledge panel is ONE editable text surface (no chrome)
 * that renders a node as a pure-text tree over tabs + newlines, and lets the
 * user expand the next rank of linked nodes *inline* via clickable dropdown
 * CHARACTERS in the text itself. This module is the pure logic — no DOM — so
 * it is unit-testable in Node (see magic_markdown.test.mjs). The DOM binding
 * (contenteditable overlay, click handlers, 3D coupling) layers on top.
 *
 * Realises USER_REQUIREMENTS_VERBATIM.md §T/§U/§V + the goal docs
 * (BLACK_SLATE_GOAL.md, HTML_DEDUP_CONTENT_TREE_GOAL.md):
 *   - tree over `\t` + `\n` ONLY; node NAMES MAY CONTAIN SPACES (N.7);
 *   - a node is identified by its ROOT (first) field (§V);
 *   - `{ref}` is the only markup — an activation/link to another node (N.10);
 *   - clickable dropdown chars (▸/▾) expand the next rank of a linked node
 *     INLINE, recursively (§V "pure-text dropdown within the markdown");
 *   - per-signal iteration: an iterable `{ref}` renders ONE sample (N.9).
 *
 * The two halves of the dialect (knowledge-panel form vs computation-graph
 * form) share this model; `mode` selects the projection.
 */

const TAB = "\t";
const REF_RE = /\{([^{}]+)\}/;          // first {ref}; the inside is the target's root field
const REF_RE_G = /\{([^{}]+)\}/g;

export const GLYPH_COLLAPSED = "▸"; // ▸  — has hidden rank-1 links, click to expand
export const GLYPH_EXPANDED = "▾";  // ▾  — expanded inline
export const GLYPH_NONE = "";

/** A parsed tree node: one line + its tab-nested children. */
export function node(text = "", children = []) {
  return { text, children };
}

/**
 * iterableNode(text, samples) — a node whose content is a per-instance
 * distribution (recursive-chunk iteration, N.9). Each sample is itself a node
 * (subtree); when this node is externally `{ref}`'d and expanded, the panel
 * renders ONE sample at a time (the signal), cycled by the rollout — never an
 * "N of M" overlay (§18.24). The full distribution lives in the 3D Real
 * register (O.7); the 2D holds a reference into it.
 */
export function iterableNode(text = "", samples = []) {
  return { text, children: [], samples };
}

/** True if a node carries a per-sample distribution (an iterable, N.9). */
export function isIterable(n) {
  return !!(n && Array.isArray(n.samples) && n.samples.length > 0);
}

/** Cycle the signal index for a path in a `signals` map (returns a new map). */
export function advanceSignal(signals, path, total) {
  const next = new Map(signals);
  const cur = next.get(path) || 0;
  next.set(path, total > 0 ? (cur + 1) % total : 0);
  return next;
}

/**
 * parse(text) → root node.
 * Depth = count of leading tabs. The FIRST line (depth 0) is the root (the
 * node's identity, §V); deeper lines nest by indentation. Lines that are blank
 * are skipped (no escaped-newline glyphs ever appear — multi-line values are
 * absorbed by the parent's indentation upstream, §4.1.1).
 */
export function parse(text) {
  const root = node("", []);
  const stack = [{ depth: -1, n: root }];
  const lines = String(text == null ? "" : text).split("\n");
  for (const raw of lines) {
    if (raw.trim() === "") continue;
    let depth = 0;
    while (depth < raw.length && raw[depth] === TAB) depth++;
    const content = raw.slice(depth).replace(/\s+$/, "");
    const n = node(content, []);
    while (stack.length && stack[stack.length - 1].depth >= depth) stack.pop();
    const parent = stack.length ? stack[stack.length - 1].n : root;
    parent.children.push(n);
    stack.push({ depth, n });
  }
  // A single top-level line becomes THE root (its children are its fields);
  // multiple top-level lines stay under the synthetic root (a forest / content
  // tree). This keeps "the root is the first field" true for panels while
  // letting a flat content tree (a scanned card) be a forest.
  if (root.children.length === 1) return root.children[0];
  return root;
}

/** serialize(node) → text. Exact inverse of parse (round-trip identity). */
export function serialize(n, depth = 0) {
  const out = [];
  const emit = (m, d) => {
    if (m.text !== "" || d >= 0) {
      if (d >= 0) out.push(TAB.repeat(d) + m.text);
    }
    for (const c of m.children) emit(c, d + 1);
  };
  // If n is a synthetic root (empty text), its children start at depth 0.
  if (n.text === "" && depth === 0) {
    for (const c of n.children) emit(c, 0);
  } else {
    emit(n, depth);
  }
  return out.join("\n");
}

/** The node's identity = its root (first) field text (§V). */
export function rootField(n) {
  if (!n) return "";
  if (n.text) return n.text;
  return n.children.length ? n.children[0].text : "";
}

/**
 * buildRegistry(nodes) → Map<rootField, node>. Each node is identified by its
 * root field, so a `{ref}` naming that field resolves to the whole node.
 */
export function buildRegistry(nodes) {
  const reg = new Map();
  for (const n of nodes) {
    const key = rootField(n);
    if (key) reg.set(key, n);
  }
  return reg;
}

/** The first `{ref}` target in a line's text, or null. */
export function refTarget(text) {
  const m = REF_RE.exec(text || "");
  return m ? m[1].trim() : null;
}

/** All `{ref}` targets in a line (a line may carry several). */
export function refTargets(text) {
  const out = [];
  let m;
  REF_RE_G.lastIndex = 0;
  while ((m = REF_RE_G.exec(text || "")) !== null) out.push(m[1].trim());
  return out;
}

/**
 * renderPanel(rootNode, opts) → Line[].
 *
 * Walks the node's field tree and produces flat render lines. A field whose
 * text references another node (`{ref}`) that EXISTS in the registry and has
 * rank-1 children gets a clickable dropdown character:
 *   - collapsed (▸): the link is present but its rank-1 fields are hidden;
 *   - expanded (▾): the target's rank-1 children are inlined beneath it at
 *     depth+1, each itself recursively renderable (the pure-text dropdown).
 *
 * opts = {
 *   registry: Map<rootField,node>,     // resolves {ref} targets
 *   expanded: Set<string>,             // expanded paths (which dropdowns are open)
 *   signals?: Map<string, number>,     // per-signal index for iterable refs (N.9)
 *   mode?: 'panel' | 'graph',          // dialect half (shared model; §V)
 *   maxDepth?: number,                 // recursion guard (cycles)
 * }
 *
 * Line = { depth, text, glyph, refTarget|null, path, source: 'own'|'expanded' }
 * `path` is a stable dotted address used as the expand/collapse toggle key.
 */
export function renderPanel(rootNode, opts = {}) {
  const registry = opts.registry || new Map();
  const expanded = opts.expanded || new Set();
  const maxDepth = opts.maxDepth == null ? 24 : opts.maxDepth;
  const lines = [];

  const signals = opts.signals || new Map();

  function visit(n, depth, path, source, refStack) {
    const tgt = refTarget(n.text);
    const target = tgt != null ? registry.get(tgt) : null;
    const iter = isIterable(target);
    // an iterable target is expandable if it has any samples; a regular target
    // if it has rank-1 children.
    const hasHidden = target != null &&
      (iter ? target.samples.length > 0 : (target.children && target.children.length > 0));
    const isOpen = hasHidden && expanded.has(path);
    let glyph = GLYPH_NONE;
    if (hasHidden) glyph = isOpen ? GLYPH_EXPANDED : GLYPH_COLLAPSED;
    const line = { depth, text: n.text, glyph, refTarget: tgt, path, source };
    if (iter) {
      // per-signal iteration metadata — for the REPL/rollout, NOT a panel
      // overlay (§18.24 / N.9). The panel shows only the current sample.
      line.iterable = true;
      line.signalIndex = signals.get(path) || 0;
      line.signalTotal = target.samples.length;
    }
    lines.push(line);
    // 1) own children (the authored field tree)
    n.children.forEach((c, i) => {
      visit(c, depth + 1, path + "." + i, "own", refStack);
    });
    // 2) expanded ref → inline the next rank (recursive, cycle/depth-guarded).
    //    For an iterable, inline ONLY the current sample's fields (N.9).
    if (isOpen && depth < maxDepth && !refStack.includes(tgt)) {
      const nextStack = refStack.concat(tgt);
      let inlineChildren;
      if (iter) {
        const idx = signals.get(path) || 0;
        const sample = target.samples[idx % target.samples.length];
        inlineChildren = (sample && sample.children) || [];
      } else {
        inlineChildren = target.children;
      }
      inlineChildren.forEach((c, i) => {
        visit(c, depth + 1, path + "/" + i, "expanded", nextStack);
      });
    }
  }

  if (rootNode && rootNode.text === "" && rootNode.children) {
    // synthetic root / content forest: render each top-level field
    rootNode.children.forEach((c, i) => visit(c, 0, String(i), "own", []));
  } else if (rootNode) {
    visit(rootNode, 0, "0", "own", []);
  }
  return lines;
}

/** The parent path of a render path ("0.0/1" → "0.0"; "0" → null). */
export function parentPath(path) {
  const idx = Math.max(path.lastIndexOf("."), path.lastIndexOf("/"));
  return idx < 0 ? null : path.slice(0, idx);
}

/**
 * renderGraph(rootNode, opts) → { nodes, edges } — the computation-graph half
 * of the dialect (§V). The SAME model as renderPanel; `mode` is just the
 * projection. Each field becomes a **minimalist circular node** carrying ONLY
 * its text (the root-most field) — no title, no bar, no buttons (V.5). Nodes
 * stay in **node-count parity** with the panel (O.1): one node per visible
 * field line. Containment is drawn as undirected line links (no arrowheads,
 * O.16); a `{ref}` node keeps its dropdown glyph so it can instantiate the
 * rank-1 walk on click, exactly as the panel folds inline.
 */
export function renderGraph(rootNode, opts = {}) {
  const lines = renderPanel(rootNode, opts);
  const nodes = lines.map((l) => ({
    id: l.path,
    label: l.text,            // text-only; the circular node's sole content
    depth: l.depth,
    glyph: l.glyph,           // ▸/▾ if it links to a hidden/expanded node
    refTarget: l.refTarget,
    iterable: !!l.iterable,
    signalIndex: l.signalIndex,
    signalTotal: l.signalTotal,
  }));
  const present = new Set(lines.map((l) => l.path));
  const edges = [];
  for (const l of lines) {
    const p = parentPath(l.path);
    if (p != null && present.has(p)) {
      edges.push({ from: p, to: l.path, kind: "contains" });
    }
  }
  return { nodes, edges };
}

/** Render Line[] back to display text (glyph + tabs + text), for inspection/DOM. */
export function linesToText(lines) {
  return lines
    .map((l) => (l.glyph ? l.glyph + " " : "") + TAB.repeat(l.depth) + l.text)
    .join("\n");
}

/** Toggle a dropdown path in an `expanded` set (returns a new set). */
export function toggle(expanded, path) {
  const next = new Set(expanded);
  if (next.has(path)) next.delete(path);
  else next.add(path);
  return next;
}

export default {
  node, iterableNode, isIterable, advanceSignal,
  parse, serialize, rootField, buildRegistry,
  refTarget, refTargets, renderPanel, renderGraph, parentPath, linesToText, toggle,
  GLYPH_COLLAPSED, GLYPH_EXPANDED,
};
