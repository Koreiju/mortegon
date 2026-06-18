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
import { Editor, rootCtx, defaultValueCtx, editorViewOptionsCtx } from "@milkdown/core";
import { commonmark } from "@milkdown/preset-commonmark";
import { getMarkdown, replaceAll } from "@milkdown/utils";

/**
 * mountMilkdown(host, fieldText, { onCommit }) → { editor, setText, read, destroy }
 * Mounts a Milkdown editor for one field's text inside `host`.
 */
export async function mountMilkdown(host, fieldText, opts = {}) {
  const { onCommit } = opts;
  let suppress = false; // guard inbound replace-all from re-firing outbound

  const editor = await Editor.make()
    .config((ctx) => {
      ctx.set(rootCtx, host);
      ctx.set(defaultValueCtx, String(fieldText == null ? "" : fieldText));
      ctx.update(editorViewOptionsCtx, (prev) => ({
        ...prev,
        attributes: { class: "mm-milkdown", spellcheck: "false" },
      }));
    })
    .use(commonmark)
    .create();

  // Outbound intent — commit the printed markdown on blur (Enter stays Milkdown's
  // until the gesture layer overrides it; the seam is the same either way).
  host.addEventListener(
    "focusout",
    () => {
      if (suppress) return;
      const md = editor.action(getMarkdown());
      if (typeof onCommit === "function") onCommit(md);
    },
    true
  );

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
  return { editor, setText, read, destroy: () => editor.destroy() };
}

// Expose on window for the served demo + Playwright acceptance probes.
if (typeof window !== "undefined") {
  window.mountMilkdown = mountMilkdown;
}
