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

  // Recursive {ref} (RECORD mode): a click on a ▸/▾ glyph toggles that ref's
  // expansion and re-renders through the model — never an in-place doc edit.
  function toggleFold(foldIndex) {
    const path = foldPaths[foldIndex];
    if (path == null) return;
    expanded = toggle(expanded, path);
    setText(computeText());
  }
  if (isRecord) {
    host.addEventListener(
      "mousedown",
      (ev) => {
        const el = ev.target && ev.target.closest && ev.target.closest(".mm-ref-fold");
        if (!el) return;
        ev.preventDefault();
        ev.stopPropagation();
        const idx = parseInt(el.getAttribute("data-fold-index"), 10);
        if (!Number.isNaN(idx)) toggleFold(idx);
      },
      true
    );
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
}
