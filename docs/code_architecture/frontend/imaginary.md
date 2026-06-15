# Frontend — Imaginary Organ (Editor · subgraph_layout)

> **Owns:** the 2D concept-graph editor canvas, the cascade reflow, and the focal-centric 2D layout. Modules: `fe/imaginary/editor.ts`, `subgraph_layout.ts`. Design: §6.6.2 / §7.3 / §7.3.4 / §9.6 / §O.1 / §O.13 / §18.8 + `frontend/{editor,compile_collapse}.md`. Realises `code_constraints/frontend_rendering.md`.

---

## §1 — Responsibility

Render the Imaginary register — pinned panels, the compiled-graph form, the result sidebar — in **screen-pixel coordinates that never share the 3D coordinate system** (§6.6.2). Reflow the named cards when the cascade recomputes. Place focal-centric subgraphs by the planar analogue of the 3D layout. Honour the seven-gesture model and the freeze-at-rect pin contract.

---

## §2 — Public Surface

```ts
Editor.pin(node, rect): void              // freeze-at-rect: materialise the panel at the EXACT screen rect (§18.8)
Editor.reflow(changedIds): void           // keyed cascade reflow of named cards only
Editor.toggleForm(card_id): void          // double-left-click panel ↔ graph (symmetric, §7.3.4 / §O.1)
SubgraphLayout.place(focal_id, nodes): Map<id, XY>
```

---

## §3 — Internal Logic

### §3.1 The seven gestures (§7.3.4 — dispatched here)
hover = preview (billboard) · single-left-click = edit (borderless) · left-click-drag node→node = wire + inherit (POST concept_edges) · **right-click = rank-1 fold (panel form ONLY, §O.1)** · right-click base = collapse-to-self · **double-left-click = panel↔graph toggle (symmetric, both directions)** · double-right-click = delete. Each maps to a `GestureGateway` kind (spine.md / `contracts.md` §2).

### §3.2 Folding vs graph form (§O.1)
**Folding is panel-only.** The graph form uses **undirected line links, no folding** (membranes.md `LinkLayer`), with **node-count parity** with the panel it toggled from — every panel node is a graph node and vice-versa. Braces are the fold/hidden marker (three states: braced-hidden / revealed-internal / resolved-external, §O.1a) — a panel concern, not a graph one.

### §3.3 Pin = freeze-at-rect (§18.8)
On click, the billboard's `getBoundingClientRect()` is captured (membranes.md) and the pinned panel materialises at **byte-for-byte the same screen rect** — the freeze-at-hover-position contract. There is **one** panel anatomy and one code path (no hover/click two-panel split — forbidden). Pin chrome (drag/resize/minimise) field-merges into the `pin_chrome` UIState slot (mirrored, persistence.md).

### §3.4 subgraph_layout + cascade reflow
`SubgraphLayout.place` = **2D-UMAP-of-nomic recentred on the focal**, radial-DOF only, push apart along rays (the planar analogue of backend/layout.md §3 / §O.17 — the forbidden concentric rings / `_fibonacciPosition` are replaced by ray-constrained placement). `reflow` updates **only the named changed cards** (keyed; pulse.md) — open editors are left untouched (edit-safety), and **the cascade never auto-unfolds** a collapsed node (§O.13).

---

## §4 — Dependencies

- **Calls:** `ConceptView.render(node, 'panel'|'child')` (cell.md), `GestureGateway.send` (spine.md), `LinkLayer` (membranes.md), `pulse/` (reconcile + tween reflow), the store.
- **Called by:** `Billboard` (hands off the rect on click → `pin`); `pulse/raf.ts` (reflow flush).

---

## §5 — Excluded

- The theme; the backend layout fit (it consumes nomic positions the backend supplies); the Imaginary-register philosophy. The compile *backend* (compute.md).
