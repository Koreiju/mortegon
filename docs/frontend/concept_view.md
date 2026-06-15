# ConceptView — The One Panel Anatomy

> **Status: realised (cp/*.js); greenfield object form in `FRONTEND_REDESIGN.md` §4.1.** The single-renderer role is carried by `cp/concept_graph.js` (the 2D card: name/description/value rows, latch, read-only 🔒 fixtures, pattern_map/url_set signal views) + `cp/billboard.js` (the pinned panel). Verified by `unified-node-view-states`, `latch-toggle-roundtrip`, `pin-chrome-roundtrip`.

---

## §1 — Identity

`ConceptView` renders a single ConceptNode (§3.1) in one of four representational *modes*, using one DOM-building routine. Mode is a parameter, never a fork — this is the structural guarantee against the §18.11 two-panel regression. The hover preview, the click-pinned panel, the halo phantom, and the compiled-graph child are all the same code path producing variants of one body skeleton. One record, one renderer, three (four with `collapsed`) modes.

---

## §2 — Structure

**`render(node, mode, hostRect?) → element`** builds the same body skeleton and elides per mode.

**Modes:**
| Mode | Shows | Used by |
|---|---|---|
| `panel` | four canonical rows (`name`, `description`, `value`/field-tree, `rendering`) + user rows + chrome | `editor.md` pinned panel |
| `collapsed` | name + read-only/🔒 indicator only | newly-pinned default; `billboard.md` hover default |
| `phantom` | **name only** (scores in `title` tooltip) | `halo.md` candidate |
| `child` | **value only** (name implicit from position) | `compile_collapse.md` child |

**The four canonical rows are themselves `FieldTree` rows** with reserved key slugs (`field_tree.md` §2), so the anatomy is a `FieldTree` with a default starting shape — there is no special canonical-row widget. `value` is the `data` field rendered as the field-tree; `rendering` is read-only (Compile output, §7.1). For python-native / typed nodes the field-tree renders the **typed `key : Type = value` form** with inline next-rank type-graph exploration (`object_exploration.md`, §9.6.1).

**Owns (transient only):** which field is in edit; caret position; live drag/resize deltas (echoed via `gesture_gateway.md`). Everything persistent — `name`, `data`, `ui_state`, latch, pin chrome — is read from `WorkspaceStore` (`workspace_store.md`).

---

## §3 — Composition

| Peer | Through |
|---|---|
| `FieldTree` (`field_tree.md`) | renders the `value`/`data` row tree and the canonical rows |
| `Editor` (`editor.md`) | instantiates `panel`/`child` views and positions them |
| `Halo` (`halo.md`) | instantiates `phantom` views |
| `Billboard` (`billboard.md`) | instantiates the `collapsed` hover preview |
| `WorkspaceStore` | reads `concepts[id]`, `ui.latch_state`, `ui.pinned_collapsed`, `ui.pin_chrome` |
| `GestureGateway` | sends rename/edit/latch/collapse/pin-chrome gestures |

All four instantiators call the *same* `render` (frontend_rendering §1.1).

---

## §4 — Behaviours

1. **One anatomy, mode-parameterised** (§18.11). No per-mode DOM routine.
2. **Collapsed by default (§4.3).** A newly-pinned panel and a hover preview render `collapsed` (name + 🔒-or-none); hover/click expands; debounced blur re-collapses.
3. **Latch + form-fit + slide-out (§4.4).** Latched (default) shows `name`/`description`/`rendering`; the field-tree `value` is loaded but hidden (latch glyph ▶). Unlatch slides the field-tree out as an **equal-height** joined side panel (latch glyph ◀); both halves resize in lockstep. Each `<pre>` form-fits to its longest line up to `600px` latched / `800px` unlatched; **empty rows hide entirely**; minimum = header strip. **Long-field rendering (§O.4):** field *names* (keys) forward-truncate at ~20 chars + `…` (front kept; full name on slow-hover); *values* render in full (multiline, never truncated) — form-fit governs value width, the truncation governs name width. Same rule on chunk-sample trees (§15.8). **Deduplicated value aliases (§O.17, lifted from MORTEGON §1.1):** when several keys resolve to the *same* value, the value prints once and the extra alias names render as `↳`-prefixed continuation rows beneath it — minimal print, no lost key→value mapping; alias names forward-truncate per §O.4.
4. **Close-button fixture rule (§9.5, §18.22).** The `×` button is **omitted** for the four foundation fixtures (Agent, WebBrowser, Database, Editor) and any read-only python-native child; those render the 🔒 indicator and **hide the latch** (§9.6).
5. **Read-only fields don't edit (§4.1.1, frontend_rendering §2.9).** `rendering` and python-native fields do not enter edit on click; the click briefly highlights to signal the constraint.
6. **Re-click raises, never duplicates (§4.2).** A second pin gesture on the same node raises z-order and un-minimises the existing panel.

---

## §5 — Activities

| Activity | Gesture | Effect |
|---|---|---|
| Pin a node | `ui-pin` | new `panel` view at the frozen rect (`billboard.md`, `editor.md`) |
| Expand/collapse panel | `ui-collapse` | toggle `pinned_collapsed[id]` |
| Latch toggle | `ui-latch-toggle` | slide field-tree in/out (§4) |
| Move / resize / minimise / close | `ui-pin-move/-resize/-minimise/-close` | chrome update (field-merge, §17.12) |
| Rename | `concept-rename` | header text; backend propagates `{old}→{new}` (§4.1) |
| Edit description / field | (delegated to `field_tree.md`) | per-field edit |
| Double-left-click body | `ui-compile-expand`/`-collapse` | dialectic (`compile_collapse.md`) |
| Right-click token | `ui-node-expand`/`-collapse` | inline next-rank type-graph fold (`object_exploration.md`, §7.3.4) |
| Hover | `ui-hover` | expand preview; open halo if applicable (`halo.md`) |

---

## §6 — Sequences

### §6.1 Pin (freeze-at-rect, §4.2)
```
billboard visible → click → capture billboard.getBoundingClientRect()
   → gateway ui-pin {chunk_id, rect}
   → ui_state_changed (pinned_billboards += , last_stick_rect = rect)
   → Editor instantiates ConceptView('panel', node, rect)
   → style.{top,left,width,height} = rect exactly (byte-for-byte, §18.8)
   → billboard resets
```
### §6.2 Latch (§4.4)
```
click latch → gateway ui-latch-toggle {card_id, latched:false}
   → ui_state_changed (latch) → latch_state[card_id]="unlatched"
   → field-tree slides out as equal-height side panel; both halves resize together
```

---

## §7 — Data

**Reads:** `concepts[id]` (the ConceptNode), `ui.latch_state[id]`, `ui.pinned_collapsed[id]`, `ui.pin_chrome[id]`. **Sends:** rename/edit/latch/collapse/pin-chrome gestures (`gesture_gateway.md` §5.1–§5.2). **Renders:** the four canonical rows via `FieldTree`; chrome per mode.

---

## §8 — Results

A panel/collapsed/phantom/child DOM element reflecting the node. Telemetry: pin → `pinned_billboards`+`last_stick_rect`; latch → `latch_state`; collapse → `pinned_collapsed`; chrome → `pin_chrome` (all §10.5).

---

## §9 — REPL Mirroring

Every ConceptView state is a §10.5 mirror field, so the REPL viewer's `pinned` row reflects `[panel:p_X → chunk:c_Y ("name")] (N pinned)` (§11.8), and `ui-latch-toggle`/`ui-pin-*` REPL actions drive the same panels a user would. The freeze-at-rect parity is asserted by the `hover-to-stick-rect-parity` env-scenario (§18.8): the mirror's `last_stick_rect` equals the captured rect byte-for-byte.

---

## §10 — Theme

Panel fill `--bg-panel`, border `--steel-700` hairline at rest, `--steel-100` 2px on focus (`theme.md` §4). Header: the per-id hash hue (§4.1) is **reinterpreted** as a steel-brightness offset on the header's bottom hairline — a machined ID tell, identity without colour (`theme.md` §5). Latch/minimise/close glyphs `--steel-500`, `--steel-300` on hover. The latch slide-out shares one steel outline across both joined halves (one bounding edge). Read-only/fixture panels: `--steel-900` border, 🔒 in `--text-lock`, no latch. No shadow; elevation is the brightened border on focus. The `value`/field-tree body is `--bg-recess` (see `field_tree.md` §10).

---

## §11 — References

- `DOMAIN_MODEL.md`: §4 (unified panel), §4.1 (anatomy), §4.1.1 (click-to-edit), §4.2 (freeze-at-rect), §4.3 (collapsed default), §4.4 (latch/form-fit), §4.5 (three representations), §9.5/§18.22 (fixture close-button).
- Object doc: [`../object_model/KnowledgePanel.md`](../object_model/KnowledgePanel.md) (reconcile to this).
- Peers: `field_tree.md`, `compile_collapse.md`, `object_exploration.md`, `billboard.md`, `halo.md`, `editor.md`.
