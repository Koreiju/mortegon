# Editor — The Imaginary Canvas

> **§S (2026-06-12).** "Editor" here = the **2D concept-graph canvas** (the Imaginary register), which is
> design-current. NOT the deprecated `Editor` *fixture* (§S.1, removed — `object_model/Editor.md`). The
> canvas's create/link/overwrite/delete gestures are intrinsic to the unified panel↔compute-graph scheme.
> **Black-slate design (§S.4 / DOMAIN_MODEL §4.1.2):** every panel and computation node is a blank editable
> bordered slate — thin silver border, black infill, serif white text, **no chrome** (no header, `×`,
> minimiser, top bar). A gesture collapses a panel into its parent field computation node; clicking a
> collapsed node fires the §8.2 halo, which stays proximal to the central node (§S.5).

> **Status: realised (cp/*.js); greenfield object form in `FRONTEND_REDESIGN.md` §6.** The 2D concept-graph surface is carried by `cp/concept_graph.js` (the `ConceptGraphMixin` overlay: card render, seven-gesture model §7.3.4, ray-constrained apparition halo, `{var}` autocomplete, edge wiring). Its mutation gestures route through the concept-graph mutation lifecycle (`/concepts` + `/concept_edges`; the `/api/editor/*` routes remain as gesture-drivers, `actor="editor"`). Verified by `editor-primitives-roundtrip`, `gesture-walkthrough`, `edge-roundtrip`.

---

## §1 — Identity

`Editor` renders the 2D concept graph — the **Imaginary register** (§1.5): pinned panels, compiled-graph subgraphs, wiring, halos, and the live cascade reflow. It instantiates `ConceptView`s (`concept_view.md`) and lays them out; it owns no concept truth (the `concepts`/`edges`/`ui` slices belong to `WorkspaceStore`). Its coordinate system is **screen pixels** and shares nothing with the Projector's metric 3D space (§6.6.2); the only crossings are the membranes (`billboard.md`, `halo.md`, `link_layer.md`).

---

## §2 — Structure

A 2D canvas (`--bg-void`) hosting: pinned `ConceptView` panels positioned by `ui.pin_chrome`; compiled-graph children positioned ray-constrained (`subgraph_layout`); the `LinkLayer` SVG beneath panels; the active `Halo` when a focal is open.

**Owns (transient):** live drag/resize deltas (echoed via `gesture_gateway.md`); which panel is being right-clicked; the in-progress wire (drag from a port). **Reads from `WorkspaceStore`:** `concepts`, `edges` (hard links), `index` (for halo/autocomplete), `ui.pinned_billboards`, `ui.pin_chrome`, `ui.pinned_collapsed`, `ui.latch_state`, `ui.compile_expansions`, `ui.halo_focus`.

Persistent panel state — position, size, minimise, latch, pin order — are all §10.5 mirror fields, so a second tab or the REPL viewer reflects them identically.

---

## §3 — Composition

| Peer | Through |
|---|---|
| `ConceptView` (`concept_view.md`) | every panel and compiled child |
| `Billboard` (`billboard.md`) | hands over the frozen rect on click-and-stick |
| `Halo` (`halo.md`) | radiates around the active focal panel |
| `LinkLayer` (`link_layer.md`) | hard/soft links, stringless compile edges, the 2D↔3D arrow |
| `Reconciler` / tweens (`liveness.md`) | keyed panel reflow; eased link re-route |
| `GestureGateway` | pin-chrome, wiring, compile, edit gestures |

---

## §4 — Behaviours

1. **Screen-pixel coordinates only (§6.6.2, §18.31).** Pins are anchored to screen rects; the 3D node's continued motion drives the `LinkLayer` arrow but **never** drags the panel.
2. **Freeze-at-rect pin (§4.2, §18.8).** A pin materialises at exactly the rect the `Billboard` captured at click time (`concept_view.md` §6.1).
3. **Re-click raises, never duplicates (§4.2).** A second pin on the same node raises z-order + un-minimises.
4. **Cascade is the default (§7.4).** Renderings update continuously downstream of edits/scans/agent emissions; the Compile button is an affordance for forced sync, not the primary trigger.
5. **Edit-safety (`liveness.md` §4).** A cascade frame updates a card's other fields and leaves an open editor's textarea + caret untouched until commit/blur.
6. **Hard vs soft layout is spatially independent (§1.5, §3.2.1).** Hard links fan outward (commitment fan); soft links sit concentric at the halo radius (possibility ring) — handled by `LinkLayer` + `Halo`.
7. **Ray-constrained subgraph layout (§7.3.2, §6.5).** Compiled children and apparition phantoms place along rays from the focal; the forbidden `_fibonacciPosition` concentric-ring placement is removed (top-of-doc forbidden concepts). The placement is the **planar analogue of the 3D layout** (lifted from MORTEGON §6.4, §O.17): a **2D UMAP of the cards' nomic vectors recentred on the focal** sets each card's azimuth; each card's only degree of freedom is its radial distance along the focal→UMAP ray; overlap is resolved by pushing cards apart **along their rays, never tangentially**.
8. **Singular-primitive aspect decides node vs panel (§O.19).** A *singular-field* primitive renders as a computation-graph **node**; a non-singular aggregate renders as a **knowledge panel** that compiles to graph form (double-left-click, §7.3.4) — the graph is built of singular-field nodes, the panel is their aggregation. Iterables root to base nodes and update referencing panels from the root down; recursive chunk iteration fires only on external `{ref}` (§4.6.1 / §O.19).

---

## §5 — Activities

| Activity | Gesture | Effect |
|---|---|---|
| Pin a chunk | `ui-pin` | new panel at frozen rect |
| Move / resize / minimise / close | `ui-pin-*` | chrome update (field-merge) |
| Edit any field | `concept-edit-*`, `field-tree-*` | per-field edit (`field_tree.md`) |
| Double-left-click body | `ui-compile-expand/-collapse` | dialectic (`compile_collapse.md`) |
| Right-click token | `ui-node-expand/-collapse` | inline next-rank type-graph fold (`object_exploration.md`, §7.3.4) |
| Draw an edge (left-click-drag node→node) | `concept-edge-create` | hard link on the commitment fan; target **inherits** source I/O types + object model (N.4, `object_exploration.md` §5.1) |
| Delete a token ref/instance (double-right-click) | `editor-delete` | reference/instance removed, in panel or graph form (N.13) |
| Open halo | `ui-halo-focus` | radiation around the focal (`halo.md`) |
| Click soft link | `concept-edge-create` | promote soft→hard; autoregress (`halo.md`) |

---

## §6 — Sequences

### §6.1 The live cascade reflow (the fluid 2D update)
```
edit commits (field_tree.md §8) → backend cascade (§7.4, debounced ~800 ms)
   → concept_changed × affected cards
   → FrameBus → store
   → Reconciler UPDATE only the named cards (untouched panels never reflow)
   → renderings re-render in place; LinkLayer re-routes edges eased (liveness.md §2)
   → open halo (if any) refreshes candidates on concept_index_update; ring tweens to new radii
   → edit-safety: any open editor on a different field is left alone
   → no auto-unfold (§O.13): the cascade recomputes values on already-revealed nodes; it does NOT reveal hidden {ref}s — only an explicit walk does (§O.9) — so the visible graph stays at the chosen rank-1 depth
```
### §6.2 Wiring a hard link
```
drag from source port → drop on target → gateway concept-edge-create {source_id, target_id, edge_type?}
   → concept_changed × 2 → edge added to store.edges → LinkLayer draws a solid full-steel undirected line (no arrowhead, §O.16) on the commitment fan → cascade re-fires
```

---

## §7 — Data

**Reads:** `concepts`, `edges`, `index`, the `ui.*` panel/halo/compile slices. **Sends:** `ui-pin-*`, `concept-edge-create`, `ui-compile-*`, edit gestures, `ui-halo-focus/-clear`. **Receives:** `concept_changed`, `concept_index_update`, `ui_state_changed`.

---

## §8 — Results

A living 2D graph: steel-framed panels at their pinned rects, value-only children fanned around expanded focals, solid hard/soft links, halos radiating on demand, renderings updating as the cascade fires. Telemetry: `pinned_billboards`, `pin_chrome`, `compile_expansions`, `halo_focus`, `latch_state` (§10.5).

---

## §9 — REPL Mirroring

The Editor's entire observable state is §10.5 mirror fields, feeding the viewer's `pinned` and `compile` rows (§11.8). Every Editor gesture has a REPL action (`ui-pin`, `concept-edge-create`, `ui-compile-expand`, `ui-halo-focus`, …) that produces identical frames; a REPL-driven pin or wire renders in every open tab, and a frontend pin or wire updates the viewer. The cascade reflow is observable as `concept_changed`×N in the REPL after an edit action (§17.4).

---

## §10 — Theme

Canvas `--bg-void`. Panels float as steel-framed cards (`--bg-panel` + `--steel-700` hairline; `--steel-100` 2px on focus; no shadow — `theme.md` §3). Compiled children: `--bg-panel` value boxes, stringless `--steel-700` edges. Hard links `--steel-300` 2px filled-arrow; soft links `--steel-700` 1px hollow-arrow; the 2D↔3D arrow `--accent-arrow` yellow (`link_layer.md`). The active halo's rings are `--steel-700` arcs. The whole Imaginary plane is steel-on-black; **no element here breaks the monochrome** (the exception zone is the Projector only). Reflow motion is eased steel-box translation + link re-route over the Pulse budget.

---

## §11 — References

- `DOMAIN_MODEL.md`: §4 (panels), §5 (authoring), §7 (compilation), §7.3 (dialectic), §7.4 (cascade), §6.6.2 (canvas separation), §8.2 (halo); anti-goals §18.8/§18.11/§18.31.
- Peers: `concept_view.md`, `field_tree.md`, `compile_collapse.md`, `billboard.md`, `halo.md`, `link_layer.md`, `liveness.md`.
