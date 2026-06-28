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

// The three §O.1a brace render states (D-04) over ONE invariant graph link —
// a rendering classification, never a second/third edge record.
export const BRACE_HIDDEN = "braced-hidden";
export const BRACE_REVEALED_INTERNAL = "revealed-internal";
export const BRACE_RESOLVED_EXTERNAL = "resolved-external";

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
  classifyBraceStates(lines);
  return lines;
}

/**
 * classifyBraceStates(lines) — mutates each ref-bearing Line in place, adding
 * a `braceState` field: one of BRACE_HIDDEN / BRACE_REVEALED_INTERNAL /
 * BRACE_RESOLVED_EXTERNAL (§O.1a / D-04, 07-UI-SPEC "Three Brace Render
 * States"). This is a CLASSIFICATION over the already-rendered Line[] — it
 * reads `expanded`-driven glyph/source facts `renderPanel` already computed
 * plus cross-line visibility, and never recomputes fold state or mutates the
 * registry/graph. One invariant graph link, three render states:
 *
 *   - revealed-internal: THIS ref line is itself open (glyph === ▾, i.e. the
 *     user expanded it here) — braces drop, rank-1 children inline beneath it
 *     (the existing renderPanel expansion; classifyBraceStates does not
 *     duplicate that walk, it only labels the line that triggered it).
 *   - resolved-external: the SAME target (by identity, i.e. the same
 *     `refTarget` string) is ALREADY revealed-internal at a DIFFERENT path in
 *     this render — i.e. some other ref to the same node already committed
 *     the reveal, so this occurrence draws a solid link to that already-
 *     visible node instead of duplicating its rank-1 fields a second time.
 *   - braced-hidden: the default — an unrevealed ref to a target that is
 *     neither expanded-here nor resolved-elsewhere (this also covers refs to
 *     unregistered/never-revealed targets — braces stay literal).
 *
 * Precedence: revealed-internal is checked first (a line that is itself open
 * always shows its own inline children, even if the SAME target is also
 * revealed at another path) so the panel never shows BOTH an inline reveal
 * AND a redundant solid-link marker for the line that triggered the reveal.
 */
export function classifyBraceStates(lines) {
  // The set of refTarget identities that are revealed-internal SOMEWHERE in
  // this render (i.e. some other ref-bearing line, at its own path, has
  // already committed the fold for that target) — the resolved-external
  // precondition per §O.1a: "the moment the referenced node becomes visible
  // by any other path".
  const revealedTargets = new Set(
    lines.filter((l) => l.refTarget != null && l.glyph === GLYPH_EXPANDED).map((l) => l.refTarget),
  );
  for (const line of lines) {
    if (line.refTarget == null) continue;
    if (line.glyph === GLYPH_EXPANDED) {
      line.braceState = BRACE_REVEALED_INTERNAL;
      continue;
    }
    if (revealedTargets.has(line.refTarget)) {
      line.braceState = BRACE_RESOLVED_EXTERNAL;
      continue;
    }
    line.braceState = BRACE_HIDDEN;
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
    braceState: l.braceState, // §O.1a render-state classification (HALO-04)
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

/**
 * isReadOnlyTypedNode(conceptNode) → boolean.
 *
 * The SAME gate the legacy `cp/concept_graph.js` 🔒 read-only check uses
 * (object_exploration.md §9.6.1 / §8D.4.2), re-implemented here as the single
 * source of truth for "does this node render in typed `key:Type=value` form."
 * Never introduce a second/independent "show types" flag (RESEARCH Pitfall 3 /
 * Assumption A4) — typed-rendering and read-only-ness stay coupled exactly as
 * the legacy reference couples them.
 */
export function isReadOnlyTypedNode(conceptNode) {
  if (!conceptNode) return false;
  const backingPointer = conceptNode.backing_pointer || "";
  const typeHint = conceptNode.type_hint || "";
  return (
    /^fixture::/.test(backingPointer) ||
    /^python_/.test(typeHint) ||
    conceptNode.read_only === true
  );
}

/**
 * renderTypedPanel(conceptNode, opts) → Line[].
 *
 * Re-implements `cp/concept_graph.js::_pythonNativeTypedView` as a pure
 * function over the SAME `Line[]` shape `renderPanel` produces
 * (`{depth,text,glyph,refTarget,path,source}`), for raw object-inspection
 * panels (python-native nodes / read-only fixtures) — EXPLORE-01's typed
 * `key : Type = value` rendering contract (07-UI-SPEC.md "Type-Slot Row
 * Rendering Contract"). `conceptNode` is the backend ConceptNode shape
 * (`{type_hint, read_only, backing_pointer, data, value}`), NOT a parsed
 * `magic_markdown` tree node — this function does its OWN JSON parse of the
 * node's data/value, mirroring `_pythonNativeTypedView`'s `d.signature` /
 * `d.ports.inputs`/`outputs` / `d.members` shapes.
 *
 * - A function node (`d.signature` present): one row per input parameter
 *   (`"name : Type"`, value omitted when none is known), skipping the
 *   implicit `self` parameter, plus a trailing `"→ ReturnType"` row when an
 *   output type is known (from `d.ports.outputs[0]` or a `-> Type` signature
 *   suffix when `d.ports.inputs` is absent).
 * - An object node (`d.members` present): one row per member, taking only the
 *   last `::`-delimited segment (mirroring `_pythonNativeTypedView`'s
 *   `String(mm).split('::').pop()`).
 * - Malformed/non-JSON data: a single structural fallback row carrying the
 *   raw text verbatim (T-07-03 — defensive, no recursive walk, no throw).
 *
 * opts.maxDepth is accepted for signature symmetry with renderPanel but is
 * unused — this view is rank-1-only by construction (one flat row per
 * parameter/member, no further recursion), which is itself the DoS
 * mitigation (T-07-03).
 */
export function renderTypedPanel(conceptNode, opts = {}) {
  const raw = (conceptNode && (conceptNode.data ?? conceptNode.value)) ?? "";
  const lines = [];

  let parsed = null;
  try {
    parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
  } catch (_) {
    parsed = null;
  }

  const pushTypedRow = (path, name, type, value) => {
    const typeText = type || "?";
    const text = value != null && value !== ""
      ? `${name} : ${typeText} = ${value}`
      : `${name} : ${typeText}`;
    lines.push({ depth: 0, text, glyph: GLYPH_NONE, refTarget: refTarget(text), path, source: "own" });
  };

  if (parsed && parsed.signature) {
    const sig = String(parsed.signature);
    const inputs = parsed.ports && Array.isArray(parsed.ports.inputs) ? parsed.ports.inputs : null;
    let idx = 0;
    if (inputs) {
      inputs.forEach((p) => {
        if (p && p.name && p.name !== "self") {
          pushTypedRow(String(idx), p.name, p.type || p.type_ref || p.annotation || "?", p.value);
          idx++;
        }
      });
    } else {
      const m = sig.match(/^\(([^)]*)\)/);
      if (m) {
        m[1]
          .split(",")
          .map((s) => s.trim())
          .filter((s) => s && s !== "self")
          .forEach((s) => {
            // signature-string fallback parse: "name: Type" or bare "name"
            const parts = s.split(":");
            const name = (parts[0] || s).trim();
            const type = parts.length > 1 ? parts.slice(1).join(":").trim() : "?";
            pushTypedRow(String(idx), name, type, null);
            idx++;
          });
      }
    }
    let out = "";
    if (parsed.ports && Array.isArray(parsed.ports.outputs) && parsed.ports.outputs[0]) {
      const o = parsed.ports.outputs[0];
      out = o.type || o.type_ref || o.annotation || "";
    }
    if (!out) {
      const mo = sig.match(/->\s*(.+)$/);
      if (mo) out = mo[1].trim();
    }
    if (out) {
      lines.push({ depth: 0, text: `→ ${out}`, glyph: GLYPH_NONE, refTarget: null, path: String(idx), source: "own" });
    }
    return lines;
  }

  if (parsed && Array.isArray(parsed.members)) {
    parsed.members.forEach((mm, i) => {
      const text = String(mm).split("::").pop();
      lines.push({ depth: 0, text, glyph: GLYPH_NONE, refTarget: refTarget(text), path: String(i), source: "own" });
    });
    return lines;
  }

  // Defensive structural fallback (T-07-03): malformed/non-JSON data renders
  // as a single verbatim row rather than throwing or recursing.
  lines.push({ depth: 0, text: String(raw), glyph: GLYPH_NONE, refTarget: null, path: "0", source: "own" });
  return lines;
}

/**
 * renderConceptPanel(conceptNode, opts) → Line[].
 *
 * The single dispatch seam between the typed render mode and the existing
 * structural `renderPanel`: gated on EXACTLY `isReadOnlyTypedNode` (the same
 * condition the legacy 🔒 read-only check uses), never a separate "show
 * types" flag (RESEARCH Pitfall 3). Python-native / read-only nodes route
 * through `renderTypedPanel`; every other node (in particular user compute
 * nodes, N.4/N.5) takes the UNCHANGED structural `renderPanel` path over its
 * parsed field tree — rank-1 minimalism, type-stripped.
 *
 * `conceptNode` is the backend ConceptNode shape. For the structural path,
 * its `value`/`data` text is parsed via `parse()` exactly as the rest of this
 * module already does.
 */
export function renderConceptPanel(conceptNode, opts = {}) {
  if (isReadOnlyTypedNode(conceptNode)) {
    return renderTypedPanel(conceptNode, opts);
  }
  const text = (conceptNode && (conceptNode.value ?? conceptNode.data)) ?? "";
  const tree = parse(text);
  return renderPanel(tree, opts);
}

export default {
  node, iterableNode, isIterable, advanceSignal,
  parse, serialize, rootField, buildRegistry,
  refTarget, refTargets, renderPanel, renderGraph, parentPath, linesToText, toggle,
  GLYPH_COLLAPSED, GLYPH_EXPANDED,
  isReadOnlyTypedNode, renderTypedPanel, renderConceptPanel,
  classifyBraceStates, BRACE_HIDDEN, BRACE_REVEALED_INTERNAL, BRACE_RESOLVED_EXTERNAL,
};
