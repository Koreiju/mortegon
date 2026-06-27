---
phase: 7
slug: deep-object-exploration-gestures
audited: 2026-06-27
baseline: .planning/phases/WFH-07-deep-object-exploration-gestures/07-UI-SPEC.md
screenshots: not captured (no dev server running; code-level audit)
advisory: true
pillar_scores:
  copywriting: { score: na, rationale: "no-prose contract; N/A per framing" }
  visuals: 2
  color: 2
  typography: 1
  spacing: 3
  experience_design: 3
overall_excluding_na: 11/20
---

# Phase 7 — UI Review (Advisory)

**Audited:** 2026-06-27
**Baseline:** `.planning/phases/WFH-07-deep-object-exploration-gestures/07-UI-SPEC.md` (locked design contract)
**Screenshots:** not captured — no dev server detected at :3000/:5173/:8080; this is a code-level audit against `backend/static/js/fe/magic_markdown.mjs`, `magic_markdown_panel.mjs`, and `frontend_e2e/object_exploration.spec.js`.
**Status:** ADVISORY / NON-BLOCKING — phase is already complete and verified (env-scenario + e2e + live D-01 probe all green). This review surfaces gaps for a future polish pass; it does not gate phase completion.

This phase is interaction/gesture-heavy with intentionally minimal "UI" in the
conventional sense (no prose, one type size/weight per the locked contract).
Copywriting and Typography were graded per the objective's framing: Copywriting
scored N/A-with-rationale (no buttons/CTAs/empty-state prose exist by design —
correctly so); Typography is scored normally because the UI-SPEC's typography
contract is not "no typography rules" but "exactly one strict rule" (13px
monospace, weight 400) — and that rule is the one most clearly violated by the
implementation.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | N/A | Correctly copy-free per locked contract — no generic CTA/empty/error strings found, structural empty-state (`{}`) and error-state (would-be `--accent-error` underline) honored in spirit but unstyled (see Color/Typography) |
| 2. Visuals | 2/4 | The 🔒 read-only marker — the ONE glyph icon this phase's spec calls for — exists only as a behavioral gate, never rendered visibly anywhere in `panelVDom`/`graphVDom` |
| 3. Color | 2/4 | Zero CSS rules exist for `.mm-drop`/`.mm-text`/`.mm-line`/`.mm-readthrough`; hover-brighten, `{ref}` `--silver-700` underline, and `--accent-error` broken-ref states are all spec'd but **never wired into any stylesheet or inline style** |
| 4. Typography | 1/4 | `panelVDom`'s inline style sets `font-family:Georgia,'Times New Roman',serif` — directly contradicting the UI-SPEC's explicit, locked "Monospace is mandatory" contract; no 13px/line-height-1.5 rule exists anywhere on `.mm-line`/`.mm-text` |
| 5. Spacing | 3/4 | Fold-indent (16px = `INDENT_PX`) matches the spec exactly; row-gap (4px) is not explicitly set anywhere (relies on `white-space:pre` + native line-box height, an unverified approximation) |
| 6. Experience Design | 3/4 | Seven-gesture model, brace-state classifier, drag-wire, double-right delete, and 🔒 edit-gate are all real and test-covered; the gap is presentation, not behavior — the same gestures that work correctly produce a render with no visible affordance for several of the states they compute |

**Overall (excluding N/A): 11/20** (treating Typography 1 + Color 2 + Visuals 2 + Spacing 3 + Experience 3)

---

## Top Priority Fixes

1. **No stylesheet exists for any `.mm-*` class the gesture/render model produces** — user impact: hover-brighten (`--silver-700`→`--silver-300`), the `{ref}` faint underline, and the broken-ref `--accent-error` underline are all spec'd contract items with zero implementation; a user gets no visual cue that a token is hoverable, ref-linked, or in an error state. Concrete fix: add `.mm-text[data-editable]:hover`, `.mm-text .mm-ref` (or a dedicated ref span), and `.mm-line[data-broken-ref]` rules to `backend/static/css/styles.css` consuming the already-defined `--silver-700`/`--silver-300`/`--accent-error` tokens — the tokens exist, only the consuming rules are missing.

2. **`panelVDom`/`graphVDom` render serif (`Georgia,'Times New Roman',serif`), not the spec-mandated monospace** — `backend/static/js/fe/magic_markdown_panel.mjs:73,104`. This is the single most explicit, most locked typography rule in the entire UI-SPEC ("Monospace is mandatory... Do not introduce a second size or a bold weight"), and the implementation uses the wrong font family outright, with no 13px / line-height:1.5 rule set anywhere on `.mm-line` or `.mm-text`. Concrete fix: change both inline `font-family` declarations to `ui-monospace, "Cascadia Code", "JetBrains Mono", Consolas, monospace` and add `font-size:13px;line-height:1.5` to `.mm-slate`/`.mm-line`.

3. **The 🔒 read-only glyph is never rendered** — `isReadOnlyRoot()` in `magic_markdown_panel.mjs:159-162` gates editing correctly (confirmed by `magic_markdown_panel.test.mjs:361-378`), but no code path in `panelVDom`/`graphVDom` emits the 🔒 character or any other visible read-only marker into the DOM/vdom output (`grep` for `🔒`/`mm-lock`/`text-lock` across `fe/` returns zero hits outside test/comment text). User impact: a python-native/fixture node looks identical to an editable node until the user tries to click-to-edit and silently nothing happens — no affordance, no feedback. Concrete fix: in `panelVDom`, when `isReadOnlyRoot(rootNode)` (or per-row, if read-only is row-granular), prepend `🔒 ` to the row text or add a `.mm-lock` span styled per the UI-SPEC's `--text-lock`/`--silver-900` outline tier (Assumption A3 in the UI-SPEC already flags `--text-lock` as an open seam — this is the same gap, now confirmed to also be missing on the consuming side, not just the token-definition side).

4. **(Secondary) `--accent-arrow` reuse for 3D-backed resolved-external links is unimplemented** — the UI-SPEC's resolved-external state (Color section, `data-3d-node-id` branch) is fully unaddressed in `graphVDom`'s edge-drawing (`magic_markdown_panel.mjs:108-114` draws every edge identically with `var(--slate-border)`, no branch on brace state or 3D-backing at all). This was explicitly flagged as an open item in 07-03's own SUMMARY ("graphVDom should eventually draw a dedicated cross-reference line for resolved-external... left as an explicit open item") — confirmed still open at the implementation layer, not silently dropped, but also not fixed.

5. **(Minor) Row-gap (4px) has no explicit CSS rule** — relies on `white-space:pre` and the browser's native line-box metrics rather than an explicit `margin`/`gap` value, so the actual rendered gap is whatever the monospace-vs-serif font's line-height happens to produce — doubly unreliable given finding #2 (wrong font family entirely).

---

## Detailed Findings

### Pillar 1: Copywriting (N/A)
No prose CTA/empty/error strings were found in `magic_markdown.mjs` or `magic_markdown_panel.mjs` (grep for `Submit|Click Here|OK|Cancel|Save|No data|No results|went wrong|try again` — zero hits). This correctly honors the contract's "deliberately copy-free... structural/gestural, not textual" framing. The would-be empty-state (`{}`) and error-state (broken-ref underline) are structural per spec, but their VISUAL realization is absent — that gap is captured under Color/Typography, not double-counted here.

### Pillar 2: Visuals (2/4)
- The seven-gesture model itself has clear behavioral hierarchy (hover preview, single-left edit, right-click fold/collapse, double-right delete, drag-wire) — `magic_markdown_panel.mjs:190-355` — this is real and well-structured.
- BLOCKER-adjacent gap: the 🔒 glyph — explicitly named in the UI-SPEC as "the only glyph icon ... no other iconography in this phase" — is computed (`isReadOnlyRoot`) but never rendered (confirmed via grep, zero hits for the emoji or any lock-class outside comments/tests). A locked node and an editable node are visually indistinguishable.
- The dropdown ▸/▾ glyphs ARE rendered (`magic_markdown_panel.mjs:47-53`, `aria-label` correctly set to "expand"/"collapse") — this part of the Visuals contract is honored.
- No focal point / hierarchy differentiation exists beyond depth-based indentation; this is consistent with the spec's "hierarchy via outline intensity" design, but since outline-intensity CSS rules don't exist (Pillar 3), the intended hierarchy mechanism is currently inert.

### Pillar 3: Color (2/4)
- `backend/static/css/styles.css` defines all the required tokens (`--silver-300`, `--silver-700`, `--silver-900`, `--accent-error`, `--accent-arrow`) — confirmed present at lines 14/18/20/35.
- Zero CSS selectors reference `.mm-drop`, `.mm-text`, `.mm-line`, `.mm-readthrough`, or any `mm-*` class anywhere in `styles.css` (grep confirms zero matches). The entire `.mm-*` rendering surface is styled exclusively via inline styles embedded in `magic_markdown_panel.mjs`, and those inline styles cover only background/color/border/font-family/padding for the slate container and graph nodes — none of the per-state requirements (hover-brighten, ref-underline, error-underline, lock-outline) exist in either location.
- This means the entire "Accent reserved for hover-outline-brighten, active-edit-outline, edit-caret" contract (UI-SPEC Color section) has zero implementation to audit against — not a violation of the 60/30/10 split (nothing is mis-applied), but a complete absence of the intended accent usage.

### Pillar 4: Typography (1/4)
- `magic_markdown_panel.mjs:73`: `font-family:Georgia,'Times New Roman',serif` on the panel slate container.
- `magic_markdown_panel.mjs:104`: same serif stack on graph nodes, plus `font-size:12px` (not the spec's locked 13px) — graph nodes are the ONLY place a font-size is set at all; the panel form (`.mm-line`/`.mm-text`) has no font-size declared anywhere, inheriting from whatever wraps the slate.
- The UI-SPEC's Typography section is unusually explicit and locked: "Monospace is mandatory... Only one font size (13px) and one weight (400) exist in this surface — this is intentional, not an omission... Do not introduce a second size or a bold weight." The implementation violates the font-family rule outright and never establishes the 13px/400/1.5 baseline the spec treats as load-bearing for the entire outline-intensity hierarchy mechanism.
- Pre-existing: this serif styling predates Phase 7 (confirmed via `git log` — last touched in the pre-GSD onboarding commit `5beda40`; none of 07-02/07-03/07-04/07-05's commits touch `panelVDom`/`graphVDom`'s styling). Phase 7 plans added significant new render logic (`renderTypedPanel`, `classifyBraceStates`) without correcting or even flagging this pre-existing contract violation, despite the UI-SPEC for THIS phase explicitly re-asserting the monospace requirement as binding.

### Pillar 5: Spacing (3/4)
- Fold-indent: `INDENT_PX = 16` (`magic_markdown_panel.mjs:25`), applied via `padding-left:${l.depth * INDENT_PX}px` (line 66) — exact match to the UI-SPEC's `fold-indent: 16px` token.
- Row-gap (4px, per spec): no explicit CSS or inline rule sets a 4px gap between `.mm-line` rows; the rows rely on `white-space:pre` and the container's natural block flow. Given the font-family defect (Pillar 4), the actual visual row-gap is unverifiable from code alone and likely does not match 4px exactly (serif line-height metrics differ from the spec's monospace-at-13px/1.5 baseline the 4px figure was presumably tuned against).
- Fold guide lines (`--silver-900`, "felt, not seen" per spec) are entirely absent — no CSS or SVG draws any guide line for nested fold levels; only `padding-left` creates the visual indent, with no accompanying divider.

### Pillar 6: Experience Design (3/4)
- All seven gestures are implemented and unit/e2e-tested: hover preview (`onHoverPreview`/`onHoverEnd`, lines 332-351), single-left edit with 🔒 gate (lines 203-211), right-click fold/collapse/double-right-delete via timestamp debounce (lines 224-250), double-left panel↔graph toggle (lines 213-217), drag-wire with SOLID transient line + 4px move threshold (lines 258-311). This is a strong, correctly-scoped implementation of the interaction contract — confirmed independently by `magic_markdown_panel.test.mjs` (19/19) and `object_exploration.spec.js` (9/9 per 07-05/07-06 SUMMARYs).
- The brace-state classifier (`classifyBraceStates`, `magic_markdown.mjs:259-281`) correctly computes all three §O.1a states and is well-tested, but (per Pillar 2/3 findings) the computed `braceState` value is never consumed by `panelVDom`/`graphVDom` to differentiate rendering — `panelVDom` (lines 41-76) reads `l.glyph`/`l.source`/`l.text` but never reads `l.braceState` at all. The model computes a three-way distinction the DOM layer doesn't render any differently (beyond the glyph, which is a separate, correctly-wired field). This is a real seam: the resolved-external state's defining visual feature (a SOLID link to the already-visible node) has no `graphVDom` implementation drawing that cross-reference edge — confirmed as an explicitly-flagged-but-unresolved open item in 07-03's own SUMMARY.
- No regressions in error-state handling for gesture rejection (e.g., drag onto same node, empty-canvas drop) — these discard cleanly per spec, matching the "not an error" contract for abandoned drags.
- Deducting 1 point (not more) because the GESTURE/STATE LOGIC is sound and well-verified; the gap is specifically that computed states (`braceState`, read-only) don't reach the render layer — a presentation wiring gap, not a behavioral one.

---

## Files Audited

- `.planning/phases/WFH-07-deep-object-exploration-gestures/07-UI-SPEC.md`
- `.planning/phases/WFH-07-deep-object-exploration-gestures/07-CONTEXT.md`
- `.planning/phases/WFH-07-deep-object-exploration-gestures/07-01-SUMMARY.md` through `07-06-SUMMARY.md`
- `backend/static/js/fe/magic_markdown.mjs` (495 lines — full read)
- `backend/static/js/fe/magic_markdown_panel.mjs` (357 lines — full read)
- `frontend_e2e/object_exploration.spec.js` (partial read, lines 1-120)
- `backend/static/css/styles.css` (targeted grep — token definitions + `.mm-*`/page-url/history-clear selectors)
- `git log` history for `backend/static/js/fe/magic_markdown_panel.mjs` (confirms serif font-family predates Phase 7)

