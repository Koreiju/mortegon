# Billboard — Hover Preview & Freeze-At-Rect Capture

> **Status: realised (cp/*.js); greenfield object form in `FRONTEND_REDESIGN.md` §7.1.** The hover→pin membrane is carried by `cp/billboard.js`: `showBillboard` (hover preview + `/api/ui/hover_rect`), the freeze-at-hover-rect pin (`/api/ui/pin` at the exact billboard screen rect), drag/resize/minimise (`/api/ui/pin_chrome`), unpin, and the dblclick panel↔graph compile toggle. Verified by `hover-to-stick-rect-parity`, `pin-chrome-roundtrip`.

---

## §1 — Identity

`Billboard` is the single `#billboard` instance whose content is swapped per hover, and whose one structural job at the canvas boundary is: **on click, hand its current bounding rect to the `Editor` so a pinned panel materialises at exactly that screen position** (freeze-at-hover-rect, §4.2). It is a coupling membrane — Real → Imaginary, **screen-rect only**, never a 3D coordinate (§6.6.2). There is no second billboard, no "root summary" widget, no per-result preview variant (§18.11, §18.13).

---

## §2 — Structure

**One** `#billboard` DOM element rendered by `ConceptView.render(node, 'collapsed')` (`concept_view.md`) — name + 🔒-or-none by default, expandable on hover. It carries the hidden-overlay edit affordances (`field_tree.md` §6) so a hover preview can be edited the instant it pins.

**Owns (transient):** the current hover source + node; the live screen rect; whether it is expanded. **Reads:** `concepts[hovered_id]` (or the chunk's derived node), `ui.hovered_id`, `ui.last_hover_rect`.

---

## §3 — Composition

| Peer | Through |
|---|---|
| `Projector` (`projector.md`) | a 3D chunk hover positions the billboard at the projected screen rect |
| `retrieval_and_sidebar.md` | a sidebar row or result row hover swaps the same billboard's content |
| `ConceptView` (`concept_view.md`) | renders the billboard body (`collapsed` mode) — same code path as pins |
| `Editor` (`editor.md`) | receives the captured rect on click → freeze-at-rect pin |
| `GestureGateway` | `ui-hover`, `ui-hover-rect`, `ui-pin` |

---

## §4 — Behaviours

1. **One instance, content swapped (§8.6, §18.13).** Source can be a 3D node, sidebar row, or search-result row — **all hit the same `ConceptView.render(…, 'collapsed')`**. No second billboard ever spawns.
2. **Freeze-at-rect capture (§4.2, §18.8).** On click, capture `getBoundingClientRect()` → `(top,left,width,height)`; hand to the Editor which sets the pin's style to those exact values byte-for-byte; then **reset** the billboard so the next hover previews a different node.
3. **Update in place between nodes (§4.2).** Moving the mouse between 3D nodes updates the same billboard's content + position; it does not spawn or stack.
4. **Screen-rect only (§6.6.2).** The crossing carries a viewport rect, never a 3D coord; the pin does not follow the 3D node afterward (§18.31).
5. **Collapsed default (§4.3).** The hover preview is `collapsed` (name only); hover expands; debounced leave re-collapses.

---

## §5 — Activities

| Activity | Gesture | Effect |
|---|---|---|
| Hover a 3D node | `ui-hover {chunk_id}` + `ui-hover-rect` | billboard renders at projected rect |
| Hover a sidebar/result row | `ui-hover-row {row_id, chunk_id}` | same billboard, content swapped |
| Click (pin) | `ui-pin {chunk_id, rect}` | freeze-at-rect → Editor pins; billboard resets |

---

## §6 — Sequences

```
mouseenter 3D chunk → raycast → chunk_id
   → gateway ui-hover (debounced) → ui_state_changed (hovered_id, last_hover_rect)
   → billboard renders ConceptView('collapsed') at projected screen rect
mousemove between nodes → billboard content + position update in place
click → capture billboard.getBoundingClientRect() = (top,left,w,h)
   → gateway ui-pin {chunk_id, rect}
   → ui_state_changed (pinned_billboards += , last_stick_rect = rect)
   → Editor pins ConceptView('panel') at exact rect (§18.8)
   → billboard resets (frees for next preview)
   → REPL viewer pinned row: "[panel:p_X → chunk:c_Y (\"name\")] (1 pinned)"
```

---

## §7 — Data

**Reads:** `concepts[hovered_id]` / chunk-derived node, `ui.hovered_id`, `ui.last_hover_rect`. **Sends:** `ui-hover`, `ui-hover-rect`, `ui-hover-row`, `ui-pin`. **Receives:** `ui_state_changed` (hover + stick rects).

---

## §8 — Results

A single previewing billboard at the hovered source's screen rect; on click, a pinned panel at exactly that rect and a reset billboard. Telemetry: `hovered_id`, `last_hover_rect`, then `pinned_billboards` + `last_stick_rect` (§10.5).

---

## §9 — REPL Mirroring

`last_hover_rect` and `last_stick_rect` are §10.5 mirror fields. The freeze-at-rect parity is asserted by the `hover-to-stick-rect-parity` env-scenario (§18.8): a REPL `ui-pin id=X stick_top=N stick_left=M …` must produce a `last_stick_rect` equal to the captured rect byte-for-byte. The REPL `ui-hover`/`ui-pin` actions drive the same single billboard a user would, and the viewer's `pinned` row reflects the resulting pin.

---

## §10 — Theme

The billboard body is a `collapsed` `ConceptView`: `--bg-panel`, `--steel-700` hairline, name in `--text-primary` sans, 🔒 in `--text-lock` when read-only (`theme.md`). When the hovered source is a 3D chunk, the billboard frame is steel-on-black even though the chunk behind it is HSV — the billboard chrome is *not* the exception zone (only the 3D node and any image texture it shows are). On hover-expand, the border brightens to `--steel-300`; no shadow.

---

## §11 — References

- `DOMAIN_MODEL.md`: §4.2 (freeze-at-rect), §4.3 (collapsed), §8.6 (hover uses unified panel), §6.6.2 (separation); anti-goals §18.8/§18.11/§18.13/§18.31.
- Object doc: [`../object_model/Billboard.md`](../object_model/Billboard.md) (reconcile to this).
- Peers: `projector.md`, `editor.md`, `concept_view.md`, `retrieval_and_sidebar.md`.
