// milkdown_slate.mjs — the Milkdown black-slate editable layer (SOURCE).
//
// Bundled by esbuild → backend/static/js/fe/vendor/milkdown_slate.bundle.mjs
// (offline-served; Milkdown is npm/ProseMirror, not single-file ESM). See
// docs/MILKDOWN_SLATE_GOAL.md.
//
// CONTROLLED VIEW (D10 — frontend is a pure projection, store is sole truth):
//   * inbound  truth  : `setText(text)` replace-all from a concept_changed frame
//                       — Milkdown's ProseMirror doc is DERIVED, never the record.
//   * outbound intent : `onCommit(markdown)` on blur — the slate fires
//                       editor-overwrite through the gateway carrying the text.
//   * reconnect-re-render identity (EDIT-03) falls out of setText being the only
//     way truth enters the view.
//
// TWO MOUNT SHAPES, ONE ENTRY POINT (`mountMilkdown`):
//   * TEXT mode    — `mountMilkdown(host, "plain field text", { onCommit })`:
//                    the field's raw text, edited directly (T1 / EDIT-01 commit).
//   * RECORD mode  — `mountMilkdown(host, { record, registry, signals }, {...})`:
//                    a parsed node rendered as the §3 field-tree (nested markdown
//                    list), with the recursive `{ref}` dropdown (▸/▾) wired as a
//                    clickable ProseMirror decoration. Expansion is computed by
//                    `magic_markdown.mjs::renderPanel` (the model) and pushed back
//                    through the SAME `setText` replace-all seam — Milkdown only
//                    renders what the model computes (§2.5 of the goal doc).
import { Editor, rootCtx, defaultValueCtx, editorViewOptionsCtx } from "@milkdown/core";
import { commonmark } from "@milkdown/preset-commonmark";
import { getMarkdown, replaceAll, $prose } from "@milkdown/utils";
import { Plugin, PluginKey } from "@milkdown/prose/state";
import { Decoration, DecorationSet } from "@milkdown/prose/view";
// The model is the single source of truth for {ref} resolution + recursion;
// esbuild inlines it from the served fe/ tree (no duplicate logic).
import { renderPanel, toggle } from "../backend/static/js/fe/magic_markdown.mjs";
// The gesture model (the SAME pure resolver the custom slate uses) classifies a
// DOM gesture; the Milkdown DOM just feeds it a target descriptor (T5 / §3.3).
import { Action, resolveGesture } from "../backend/static/js/fe/magic_markdown_gestures.mjs";

const GLYPHS = "▸▾"; // ▸ ▾

/**
 * linesToMarkdown(lines) → markdown text. Renders renderPanel's flat Line[] as a
 * nested commonmark bullet list: depth-0 lines are paragraphs (the node root),
 * deeper lines are `- ` items indented two spaces per rank. A foldable line keeps
 * its leading ▸/▾ glyph as literal text so the decoration can make it clickable
 * and `getMarkdown` round-trips it. A blank line separates a paragraph block from
 * an adjacent list block (commonmark hygiene).
 */
export function linesToMarkdown(lines) {
  const out = [];
  let prev = null;
  for (const l of lines) {
    if (prev !== null && ((prev === 0 && l.depth >= 1) || (prev >= 1 && l.depth === 0))) out.push("");
    const g = l.glyph ? l.glyph + " " : "";
    if (l.depth <= 0) out.push(g + l.text);
    else out.push("  ".repeat(l.depth - 1) + "- " + g + l.text);
    prev = l.depth;
  }
  return out.join("\n");
}

// Commonmark backslash-escapable punctuation (CommonMark §2.4). Milkdown's
// serializer escapes these in text (e.g. `sim\_princeton`); the §3 grammar is
// raw, so we unescape on the way back.
const MD_ESCAPE_RE = /\\([\\`*_{}\[\]()#+\-.!>~|"'$&%^=:;?/<,@])/g;

/**
 * markdownToFieldText(md) → §3 tab/newline field text. The exact reverse of
 * `linesToMarkdown` (modulo commonmark's loose-list blank lines, `*`-vs-`-`
 * bullet choice, and backslash escapes that Milkdown's serializer introduces).
 * A nested commonmark bullet list maps back to tab depth: a top-level `- x` is
 * depth 1, every two leading spaces is one deeper rank; a non-bullet line is
 * depth 0 (the node root). Fold glyphs are stripped. This is the outbound-commit
 * transformer — `print(record) → Milkdown → read() → markdownToFieldText → parse`
 * is identity for the §3 grammar (T6 / EDIT-02).
 */
export function markdownToFieldText(md) {
  const out = [];
  for (const raw of String(md == null ? "" : md).split("\n")) {
    if (raw.trim() === "") continue;
    const m = /^(\s*)([-*+])\s+(.*)$/.exec(raw);
    let depth, content;
    if (m) {
      const indent = m[1].replace(/\t/g, "  ").length;
      depth = Math.floor(indent / 2) + 1; // a top-level bullet is rank 1
      content = m[3];
    } else {
      depth = 0;
      content = raw.replace(/^\s+/, "");
    }
    content = content.replace(/^[▸▾]\s+/, "").replace(MD_ESCAPE_RE, "$1").replace(/\s+$/, "");
    out.push("\t".repeat(depth) + content);
  }
  return out.join("\n");
}

const foldKey = new PluginKey("mm-ref-fold");

// A stateless ProseMirror plugin: it decorates the leading ▸/▾ glyph of every
// foldable line (in document order) as a clickable `<span class="mm-ref-fold"
// data-fold-index="k">`. The k-th such glyph maps to the k-th foldable render
// path (both are DFS order), so a click resolves to exactly one {ref} toggle.
function refFoldPlugin() {
  return $prose(() => new Plugin({
    key: foldKey,
    props: {
      decorations(state) {
        const decos = [];
        let k = 0;
        state.doc.descendants((node, pos) => {
          if (node.isTextblock) {
            const txt = node.textContent;
            const lead = txt.length - txt.replace(/^\s+/, "").length;
            const ch = txt[lead];
            if (ch && GLYPHS.indexOf(ch) >= 0) {
              const from = pos + 1 + lead;
              decos.push(
                Decoration.inline(from, from + 1, {
                  class: "mm-ref-fold",
                  nodeName: "span",
                  "data-fold-index": String(k),
                })
              );
              k++;
            }
          }
          return true;
        });
        return DecorationSet.create(state.doc, decos);
      },
    },
  }));
}

/**
 * classifyTarget(host, el) → the gesture-model target descriptor for a DOM node
 * inside the Milkdown view: 'dropdown' (the ▸/▾ fold glyph), 'ref' (a line whose
 * text carries a `{ref}`), 'self' (the root field — the node's identity line),
 * 'token' (any other editable text line), or 'body' (the bare container). This is
 * the ONLY Milkdown-specific glue; the action is decided by the shared resolver.
 */
export function classifyTarget(host, el) {
  if (!el || !el.closest) return "body";
  if (el.closest(".mm-ref-fold")) return "dropdown";
  const block = el.closest("li, p");
  if (!block || !host.contains(block)) return "body";
  if (/\{[^}]+\}/.test(block.textContent || "")) return "ref";
  // the root field is the first textblock (depth 0) of the rendered tree
  const firstBlock = host.querySelector(".mm-milkdown p, .mm-milkdown li");
  if (block === firstBlock) return "self";
  return "token";
}

// installGestures(host, { onFold, onAction }) — routes EVERY left/right/double
// gesture over the Milkdown DOM through `resolveGesture` (the shared model). Left
// gestures go via mousedown so a fold beats ProseMirror's caret; right gestures
// go via contextmenu (menu suppressed) with a single/double debounce so a
// double-right deletes rather than first folding. EDIT_TOKEN / NONE fall through
// to Milkdown's native contenteditable (caret placement) untouched.
function installGestures(host, { onFold, onAction }) {
  const fire = (action, ctx) => {
    if (action === Action.TOGGLE_FOLD && ctx.foldIndex != null) onFold(ctx.foldIndex);
    if (action !== Action.NONE && typeof onAction === "function") onAction(action, ctx);
  };
  host.addEventListener(
    "mousedown",
    (ev) => {
      if (ev.button !== 0) return; // left only; right is handled on contextmenu
      const target = classifyTarget(host, ev.target);
      const clicks = ev.detail >= 2 ? 2 : 1;
      const { action } = resolveGesture({ button: "left", clicks, target, mode: "panel" });
      if (action === Action.EDIT_TOKEN || action === Action.NONE) return; // native caret
      ev.preventDefault();
      ev.stopPropagation();
      const fold = ev.target.closest && ev.target.closest(".mm-ref-fold");
      fire(action, { target, foldIndex: fold ? parseInt(fold.getAttribute("data-fold-index"), 10) : null });
    },
    true
  );
  let rTimer = null, rCount = 0, rTarget = null, rFold = null;
  host.addEventListener(
    "contextmenu",
    (ev) => {
      ev.preventDefault();
      rCount += 1;
      rTarget = classifyTarget(host, ev.target);
      const fold = ev.target.closest && ev.target.closest(".mm-ref-fold");
      rFold = fold ? parseInt(fold.getAttribute("data-fold-index"), 10) : null;
      if (rTimer) clearTimeout(rTimer);
      rTimer = setTimeout(() => {
        const clicks = rCount >= 2 ? 2 : 1;
        const { action } = resolveGesture({ button: "right", clicks, target: rTarget, mode: "panel" });
        fire(action, { target: rTarget, foldIndex: rFold });
        rTimer = null; rCount = 0; rTarget = null; rFold = null;
      }, 220);
    },
    true
  );
}

/**
 * mountMilkdown(host, source, opts) → { editor, setText, read, destroy, ... }
 * `source` is a string (TEXT mode) or `{ record, registry, signals }` (RECORD mode).
 */
export async function mountMilkdown(host, source, opts = {}) {
  const { onCommit } = opts;
  const isRecord = !!(source && typeof source === "object" && source.record);
  let record = isRecord ? source.record : null;
  let registry = isRecord ? source.registry || new Map() : new Map();
  let signals = isRecord ? source.signals || new Map() : new Map();
  let expanded = new Set();
  let foldPaths = []; // foldIndex → render path, rebuilt every render (DFS order)
  let suppress = false; // guard inbound replace-all from re-firing outbound

  function computeText() {
    if (!isRecord) return String(source == null ? "" : source);
    const lines = renderPanel(record, { registry, expanded, signals });
    foldPaths = lines.filter((l) => l.glyph).map((l) => l.path);
    return linesToMarkdown(lines);
  }

  const builder = Editor.make()
    .config((ctx) => {
      ctx.set(rootCtx, host);
      ctx.set(defaultValueCtx, computeText());
      ctx.update(editorViewOptionsCtx, (prev) => ({
        ...prev,
        attributes: { class: "mm-milkdown", spellcheck: "false" },
      }));
    })
    .use(commonmark);
  if (isRecord) builder.use(refFoldPlugin());
  const editor = await builder.create();

  function setText(text) {
    suppress = true;
    try {
      editor.action(replaceAll(String(text == null ? "" : text)));
    } finally {
      suppress = false;
    }
  }
  function read() {
    return editor.action(getMarkdown());
  }
  // The §3 field text the view currently holds (commit/round-trip surface).
  function readFieldText() {
    return markdownToFieldText(read());
  }

  // Recursive {ref} (RECORD mode): a click on a ▸/▾ glyph toggles that ref's
  // expansion and re-renders through the model — never an in-place doc edit.
  function toggleFold(foldIndex) {
    const path = foldPaths[foldIndex];
    if (path == null) return;
    expanded = toggle(expanded, path);
    setText(computeText());
  }
  const { onAction } = opts;
  if (isRecord) {
    installGestures(host, {
      onFold: toggleFold,
      onAction: typeof onAction === "function" ? onAction : null,
    });
  } else if (typeof onCommit === "function") {
    // Outbound intent (TEXT mode) — commit the printed markdown on blur.
    host.addEventListener(
      "focusout",
      () => {
        if (suppress) return;
        onCommit(editor.action(getMarkdown()));
      },
      true
    );
  }

  return {
    editor,
    setText,
    read,
    readFieldText,
    destroy: () => editor.destroy(),
    // RECORD-mode introspection (for the gesture layer + Playwright acceptance):
    getExpanded: () => new Set(expanded),
    toggleFold,
    setRecord: (next, nextRegistry) => {
      record = next;
      if (nextRegistry) registry = nextRegistry;
      setText(computeText());
    },
  };
}

// Expose on window for the served demo + Playwright acceptance probes.
if (typeof window !== "undefined") {
  window.mountMilkdown = mountMilkdown;
  window.markdownToFieldText = markdownToFieldText;
  window.linesToMarkdown = linesToMarkdown;
}
