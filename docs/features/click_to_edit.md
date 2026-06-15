# Feature: Click-To-Edit (Hidden-Overlay Buttons + Shift-Enter)

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §4.1.1 (click-to-edit-then-Enter), §4.6 (plus-signs on right and bottom), §4.6.2 (three-rules synthesis), §1.1 (Imaginary register's seamless distribution), §1.2.1 verbatim (*"hidden buttons overtop the various layout sections, when clicked, become editable fields. Shift-enter rules for multilines value fields should also be followed"*).

**Status.** Realised. The pure-print display (`<pre class="concept-value-print">`) + click-to-edit overlay, the Tab/Shift-Enter multiline keydown handling, and the `+→`/`+↓` plus-signs (`_growRow`) are carried by `cp/concept_graph.js` (the §6 FieldTree edit phase, `frontend/field_tree.md`). Single-left edits a token; Enter/blur commits through the lifecycle; Shift-Enter inserts a newline; read-only (🔒) fields don't enter edit. Verified by `edit-field-roundtrip` (full-smoke). *(The recursive multi-syntax parse is JSON-or-passthrough today; the Indent/HTML strategies are greenfield, field_tree.md §3.)*

---

## §1 — What the user sees

The user sees a panel whose resting form is pure print — tabs and newlines, no JSON braces, no HTML angle brackets, no YAML dashes, no chevrons or placeholder boxes or any per-row chrome. The print is unadorned. When the user moves the cursor over the print, transparent button regions (positioned to match the print tokens' bounding rects) reveal a subtle hover indicator — a 1-pixel outline, a barely-visible background tint at around ten percent opacity — so the user knows the region is interactive without that knowledge breaking the minimalist rendering.

A click on a print token replaces it in place with a textarea pre-populated with the underlying value; focus moves into the textarea; the caret respects the click coordinate inside the printed text. The user types. Shift-Enter inserts a literal newline. Enter commits the value through the lifecycle (no per-keystroke cascade; the commit-on-Enter is the cascade trigger). Escape discards and returns to the prior print. Blur (clicking elsewhere) commits identically to Enter.

When the field is in edit state, plus-sign cutout templates appear on the right (`+→`, for adding a child row indented one level) and on the bottom (`+↓`, for adding a sibling row at the same nesting level) of the singular key:value compute node. Clicking either plus materialises a real editable row in edit state, and the user types immediately — the print form re-renders with the new row included once the new row commits.

Tabs and newlines in multi-line value fields integrate seamlessly into the parent tree's indentation in the print form — the user never sees escaped-newline glyphs or quoting. The same contract holds across every editable field on every concept node — foundation fixtures, scan-spawned chunks, user-created cards, compiled-graph children, halo phantoms promoted via apparition click.

The §1.1 framing: editing is an *opening* into the imaginary's editable field, not a syntax-laden form. The print is unadorned; the interactivity is latent.

---

## §2 — Cross-objects

| Object | Role |
|---|---|
| [`KnowledgePanel`](../object_model/KnowledgePanel.md) | The container whose print + edit states this feature governs |
| [`FieldTree`](../object_model/FieldTree.md) | The recursive editable tree; plus-signs grow it |
| [`UIStateService`](../object_model/UIStateService.md) | `editing_field` mirror field tracks which field is currently in edit state |
| [`ConceptLifecycle`](../object_model/ConceptLifecycle.md) | Commits the field change through `apply_update_lifecycle` |
| [`Editor`](../object_model/Editor.md) | The `Editor.overwrite` primitive is the commit path |
| [`ConceptNode`](../object_model/ConceptNode.md) | The record whose fields are being edited |

---

## §3 — Gestures

| Gesture | REPL action | Effect |
|---|---|---|
| Open edit | `ui-edit-open { card_id, field_path, value_so_far }` | Records the open in UIState; frontend swaps print → textarea |
| Commit edit | `ui-edit-close` (after editor-overwrite to update the value) | Records the close; frontend swaps textarea → print |
| Add right child (plus-sign) | (frontend gesture; calls editor-overwrite under the hood) | New child row materialises in edit state |
| Add bottom sibling (plus-sign) | (frontend gesture; calls editor-overwrite under the hood) | New sibling row materialises in edit state |
| Cancel edit | `ui-edit-close` (without editor-overwrite first) | Discards changes; print returns at prior value |

---

## §4 — State machine — edit cycle

```
state: panel field renders as pure print; transparent overlay button covers the print region
   │
gesture: click on overlay button
   │
   ▼
frontend swaps print token → textarea pre-populated with current value
   ▼  focus enters textarea
   ▼  caret position respects click coordinate
   ▼  plus-signs appear on right (+→ for child) and bottom (+↓ for sibling)
   │
   ▼
POST /api/ui/edit_open { card_id, field_path, value_so_far }
   │
   ▼
UIStateService.set_editing_field → editing_field = {card_id, field_path, value_so_far, opened_at}
   │
   ▼
WS ui_state_changed (kind=edit_open) → peer surfaces see what's being edited
   │
   ▼
user types; per-keystroke value_so_far updates may post if cadence-throttled
   ▼  Shift-Enter inserts a literal newline; cascade DOES NOT fire
   ▼  click on a plus-sign → materialise new row in edit state
   │
gesture: Enter (commit) OR blur OR click elsewhere
   │
   ▼
Editor.overwrite(card_id, {field_path: new_value}) — enters lifecycle dispatcher
   │
   ▼  Kuzu write + concept_changed + evolution_diff + cascade nudge
   │
   ▼
POST /api/ui/edit_close
   │
   ▼
UIStateService.clear_editing_field → editing_field = null
   │
   ▼
frontend swaps textarea → print; the new value renders in print form (tabs + newlines integrated into parent tree's indentation)
   │
   ▼
REPL viewer editing row updates to "(no field open)"

cancel path (Escape):
   ▼  no Editor.overwrite call
   ▼  POST /api/ui/edit_close
   ▼  frontend swaps textarea → print at prior value
```

---

## §5 — WS frames + telemetry

| Frame | Carries |
|---|---|
| `ui_state_changed` (kind=edit_open) | `editing_field = {card_id, field_path, value_so_far, opened_at}` |
| `ui_state_changed` (kind=edit_close) | `editing_field = null` |
| `concept_changed` (modified) | The committed value on the affected ConceptNode |
| `concept_index_update` | The re-embedded nomic vector if `description` was edited |

REPL viewer `editing` row shows the active edit in `card_id.field_path  value=<preview>` form; `(no field open)` when idle.

---

## §6 — Acceptance bar

The click-to-edit feature is realised when:

- `edit-field-roundtrip` env-scenario passes — open seeds `opened_at`, same-field updates preserve `opened_at`, close clears, validation rejects empty card_id / field_path, purge clears.
- Every editable field across panels (name, description, data field-tree rows, compiled-graph children, halo phantoms after promotion) shows a hidden-overlay button on hover that activates edit on click.
- The print form never shows JSON braces, HTML angle brackets, YAML dashes, or escaped-newline glyphs — the renderer integrates tabs and newlines into the parent tree's indentation.
- Shift-Enter in a multi-line field inserts a literal newline without committing; Enter commits.
- Plus-signs appear on right (child) and bottom (sibling) of a single key:value node when it's in edit state; clicking either materialises a new row in edit state.
- Read-only python-native nodes (§9.6) do NOT enter edit on click; the field briefly highlights to signal the read-only constraint.
- REPL viewer `editing` row reflects the active field accurately.

---

## §7 — Anti-goals

| Anti-goal | DOMAIN_MODEL §18 |
|---|---|
| Print form leaking JSON / HTML / YAML syntax | (no specific §18; the §1.2.1 spec is the contract) |
| Per-keystroke cascade re-fire | (anti-pattern; cascade fires on commit, not per char) |
| Read-only fields entering edit on click | (§9.6 read-only contract violation) |

---

## §8 — Code constraints

- [`frontend_rendering.md`](../code_constraints/frontend_rendering.md) — hidden-overlay button placement; print-form preservation; Shift-Enter semantics.
- [`api_routes.md`](../code_constraints/api_routes.md) — `/api/ui/edit_open` + `/api/ui/edit_close` shapes.
- [`lifecycle_invariants.md`](../code_constraints/lifecycle_invariants.md) — commit routes through `Editor.overwrite` → dispatcher.
- [`repl_actions.md`](../code_constraints/repl_actions.md) — `ui-edit-open` + `ui-edit-close` actions.

---

## §9 — Cross-features

- [`plus_sign_field_tree.md`](plus_sign_field_tree.md) — the plus-signs that appear in edit state.
- [`autocomplete.md`](autocomplete.md) — typing in a row's name field surfaces completions.
- [`signal_stream.md`](signal_stream.md) — fields that carry iterables show only one signal at a time; editing a paused signal flows through this feature.
- [`three_register_model.md`](three_register_model.md) — editing is the Imaginary register's primary UX expression.
