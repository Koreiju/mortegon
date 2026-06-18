# GOAL — Milkdown as the Black-Slate Editable Layer (2026-06-17)

> **Status: GOAL / binding design directive.** Source: the user's directive of
> 2026-06-17 — *"enforce integrating Milkdown for our slates … the editable left
> side is really what I'm looking for … as long as recursive rendering and our
> gestures and syntax work okay in practical tests with the real full-stack and
> integration with Playwright."*
>
> **This OVERRIDES the EDIT-03 recommendation** in
> [`EDITOR_INTEGRATION_ASSESSMENT.md`](EDITOR_INTEGRATION_ASSESSMENT.md) (which
> leaned CM6 and listed Milkdown under "rejected"). The user has weighed the
> trade-off and chosen **Milkdown** for the in-slate edit experience. The
> assessment's caveat still governs the engineering: Milkdown sits on ProseMirror,
> which keeps an authoritative internal AST, so the integration MUST keep the
> frontend a pure projection (D10) by treating Milkdown as a *controlled* view —
> the `WorkspaceStore` remains the sole truth.

## 0 — The goal in one paragraph

A black-slate card's **editable surface** is a **Milkdown** instance: at rest it
renders the node as the pure-print text-tree (tabs+newlines, `{ref}` the only
markup, §3 of `BLACK_SLATE_GOAL.md`); on interaction it reveals the native source
for borderless in-place editing — the "rendered at rest, syntax on interact"
behaviour Milkdown gives natively. The **recursive `{ref}` rendering**, the
**gesture model** (single-left edit, ▸/▾ fold, right-click fold, double-left
panel⇄graph, double-right delete), and the **tab/newline+`{ref}` syntax** all
keep working exactly as today — Milkdown replaces only the *edit/decoration*
layer behind `mount`, not the model, store, gateway, gestures, halo, or projector.

## 1 — Scope (focused, per the user)

**In:** the editable slate surface — Milkdown mounted as the in-card editor.
- "The editable left side is really what I'm looking for. That's all." — the
  priority is the Milkdown-powered editable source/rest-render surface.
- Recursive rendering: `{ref}` tokens expand the next rank inline (the ▸/▾
  dropdown), recursively, in the Milkdown view.
- Gestures: the full `magic_markdown_gestures.mjs` model still resolves over the
  Milkdown DOM (single/double left, right, double-right, drag).
- Syntax: the §3 grammar (tabs+newlines, names-with-spaces, `{}` on-ramp,
  kv-vs-multiline-by-indent) round-trips through Milkdown unchanged.

**Out:** rebuilding the model/store/gateway/projector/halo; replacing the
rendered 3D register; changing any backend route, frame, or lifecycle.

## 2 — Integration approach (keep the frontend a pure projection — D10)

Milkdown is a *controlled* view bound to one node's text; the store is truth.

1. **Edit layer behind `mount`.** `magic_markdown_panel.mjs::mount` swaps the
   per-field textarea for a Milkdown `Editor` instance scoped to that field's
   text. `panelVDom` (the pure spec) is unchanged; only the DOM glue changes —
   keeping "magic in testable logic, DOM binding trivial."
2. **Inbound truth (store → view).** The `Reconciler`/store pushes the
   authoritative text from a `concept_changed` WS frame into Milkdown via a
   replace-all transaction. Milkdown's ProseMirror doc is **derived**, never the
   source of record.
3. **Outbound intent (view → store).** Milkdown's `dispatch`/listener is
   intercepted: on commit (Enter/blur) the slate fires `editor-overwrite` /
   `concept-edit-data-row` through `gateway.mjs` carrying the printed text
   (never JSON), exactly as the §9 one-way seam already does.
4. **No-authoritative-state proof.** A dropped-WS reconnect re-renders the slate
   identically (the Milkdown doc is rebuilt from the store) — this is the
   EDIT-03 acceptance and the hard guard against ProseMirror "state overhang."
5. **Recursive `{ref}` + tab-tree as Milkdown nodes.** The `{ref}` token and the
   tab-indented tree render via custom Milkdown node/decoration plugins driven by
   `magic_markdown.mjs::parse`/`renderPanel` (reuse the existing model — Milkdown
   only renders what the model computes).

## 3 — Acceptance (practical tests, real full stack + Playwright)

Verified through the unified framework (`scripts/run_full_stack_tests.py`) — the
same gate the rest of the project uses. Un-fixme the EDIT specs in
`frontend_e2e/edit.spec.js` against the Milkdown slate:

1. **Editable surface** — single-left a printed token → Milkdown enters edit on
   that field, caret at the click point; Shift-Enter soft-newline; Enter commits
   through the lifecycle; Esc discards. (`edit.spec.js` EDIT-01.)
2. **Recursive rendering** — a `{ref}` expands the next rank inline (▸→▾),
   recursively, in the Milkdown view; collapse restores. (Playwright + the live
   `/` editor on a fixture scan.)
3. **Gestures** — every left/right/double click resolves to the same action as
   today over the Milkdown DOM (fold, panel⇄graph circular node, delete, wire).
4. **Syntax** — the §3 tab/newline+`{ref}` grammar round-trips: `print(record) →
   Milkdown → edit → parse(text) → delta` is identity (the existing
   `magic_markdown.test.mjs` round-trip stays green).
5. **Lifecycle routing** — every commit routes through `concept_lifecycle.py`
   (the `concept_index_update` WS frame + evolution-log entry), asserted by
   `env-scenario --name click-to-edit` / `edit-field-roundtrip`.
6. **No authoritative frontend state** — reconnect-re-render identity (EDIT-03).
7. **Gate** — `npm run test:all` green in BOTH stub and real (`all_real`) modes
   with the Milkdown slate live; `npm run test:all:real --fixture-scan` for the
   deterministic real-stack acceptance.

## 4 — Build order

1. Add `@milkdown/*` (+ ProseMirror) deps; a build/bundle step for the `fe/`
   tier (Milkdown is not single-file ESM like the current vanilla modules — needs
   bundling or an import-map/CDN ESM shim served from `backend/static`).
2. A `fe/milkdown_slate.mjs` adapter: `mountMilkdown(host, fieldText, { onCommit })`
   bound to one field; replace-all on inbound; intercept commit on outbound.
3. Wire it behind `magic_markdown_panel.mjs::mount` (feature-flag `WFH_SLATE_EDITOR=milkdown`
   so the custom path stays as fallback during the transition).
4. Custom Milkdown plugins for `{ref}` + the tab-tree, driven by the existing
   `magic_markdown.mjs` model.
5. Un-fixme `frontend_e2e/edit.spec.js` specs one per capability; run on the real
   stack via the framework.

## 5 — Doc reconciliation

- `EDITOR_INTEGRATION_ASSESSMENT.md` §3: record this override (Milkdown chosen by
  the user; the no-authoritative-state mitigation is §2 above).
- Roadmap EDIT-03: "custom vs CM6" → **Milkdown**, with the §2 controlled-view
  contract as the binding constraint.
- Verification lives in `.planning/TEST_MATRIX.md` (Phase 2 row) unchanged — the
  Milkdown slate is verified by the SAME runnable commands.
