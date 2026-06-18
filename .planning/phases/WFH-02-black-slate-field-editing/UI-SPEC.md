# Phase 2 — Black-Slate Field Editing — UI-SPEC

> Design contract for the Milkdown editable slate (EDIT-01/02/03). Verified by the
> Playwright tier (`frontend_e2e/edit.spec.js` + `milkdown.spec.js`) — the
> contract values below are the e2e assertions. No new design system: this
> extends the existing §S.4 black-slate tokens.

## 1 — Design tokens (the only palette)

| Token | Value | Use |
|---|---|---|
| `--slate-fill` | `#000` / `rgb(0,0,0)` | card infill (verified) |
| `--slate-border` | `#c0c0c0` / `rgb(192,192,192)` | 1px rest / 2px focus, solid (verified) |
| `--slate-text` | `#fff` / `rgb(255,255,255)`, **Georgia serif** | all slate text (verified) |
| `--ref-glyph` | `--slate-border` | the ▸/▾ dropdown character |
| 2D↔3D connector | the one yellow stroke | only non-silver 2D stroke |

No greys, glass, video, shadow, glow, blur, or monospace. No chrome (header, ×,
minimiser, top bar). The only filled colour in the app is the 3D chunk HSV.

## 2 — Interaction states (rest ⇄ interact, the §T thesis)

| State | Appearance | Trigger |
|---|---|---|
| **Rest** | the node as a pure-print text-tree (tabs+newlines), `{ref}` as `name` + ▸ glyph; rendered, not raw | default |
| **Editing a field** | borderless blended Milkdown cursor field on the clicked token, caret at the click point; otherwise fully blended into the slate | single-left a token (M.8) |
| **Expanded `{ref}`** | the target's rank-1 children indented inline; glyph ▸→▾ | click ▸ / right-click (M.6) |
| **Graph (circular node)** | the record as a black-fill/silver-stroke disc showing only the root field | double-left body (§15.1) |
| **Halo open** | name-only phantoms above the slate (Phase 3) | click a collapsed node |

Editing is **borderless and blended** — "a purely smoothed text editor without
special borders around each interactive token" (M.8). Commit on Enter/blur
(cascade fires on commit, not per keystroke); Shift-Enter soft-newline; Esc
discards. Empty rows hide entirely.

## 3 — The 6 UI quality pillars (gsd-ui-checker dimensions)

1. **Visual hierarchy** — one text-tree per card; depth by tab indent only; the
   root field is the title (column-0 line); rank-1 minimalism (N.14) — deeper
   structure appears only on expand.
2. **Consistency** — every panel AND computation node is the same black slate,
   one CSS rule; the Milkdown view inherits the exact tokens (`.mm-milkdown`).
3. **Accessibility** — `spellcheck="false"`; the editable region is a real
   contenteditable (Milkdown/ProseMirror) → caret/IME/selection/keyboard-nav for
   free; read-only API nodes (🔒) refuse single-left edit (no-op).
4. **Responsiveness/states** — rest/editing/expanded/graph/halo each have a
   defined appearance (§2); fold-state is preserved across collapse/re-expand
   (M.6); a dropped-WS reconnect re-renders identically (no authoritative state).
5. **Feedback** — caret lands where the click fell; the ▸/▾ glyph reflects
   fold-state; commit is silent (the cascade re-renders from the store).
6. **Polish** — no layout shift on enter-edit (blended, not a box); multi-line
   values absorb into the parent indent (no escaped-`\n` glyph); `{ref}` is the
   only markup ever shown.

## 4 — Verification (the contract = the e2e assertions)

- `milkdown.spec.js`: black-slate tokens (✓), editable surface (✓), inbound/
  outbound seam (✓); recursive `{ref}`, gestures, syntax, lifecycle (fixme → un-fixme per PLAN T2–T7).
- `edit.spec.js`: §M.8 click-to-edit, §M.6 fold, §15.1 panel⇄graph circular (✓);
  EDIT-01 caret/textarea, EDIT-02 autocomplete/`+→`/`+↓`, EDIT-03 reconnect (fixme).
- Gate: `npm run test:all` green both modes. A screenshot is never the proof.

## 5 — Safety gate (ui_safety_gate)

Changes touch only `backend/static/*` + `frontend_src/` + `frontend_e2e/`. No
backend route/frame/lifecycle edit. The §11 DOM audit (no forbidden widgets, no
chrome, pure black) must stay green (`black_slate.spec.js`).
