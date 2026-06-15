# Frontend — Membranes (Billboard · Halo · LinkLayer)

> **Owns:** the three one-way 2D↔3D couplings. Modules: `fe/membranes/billboard.ts`, `halo.ts`, `link_layer.ts`. Design: §4.2 / §4.5 / §6.6.2 / §8.2.2 / §O.3 / §O.16 / §O.18 / §18.7 + `frontend/{billboard,halo,link_layer}.md`. Realises `code_constraints/frontend_rendering.md`. The couplings are the **only** places Real and Imaginary touch — each strictly **one-way**.

---

## §1 — Responsibility

Couple the two registers without merging them: `Billboard` (Real→Imaginary, screen-rect only), `Halo` (similarity transport along a cone), `LinkLayer` (the only line-drawer — undirected, no arrowheads, no dashes). The visual rules here are load-bearing theme invariants (`frontend/theme.md`): **no arrowheads, no `stroke-dasharray` anywhere**; the only hue outside 3D nodes is the yellow 2D↔3D connector.

---

## §2 — Public Surface

```ts
Billboard.showHover(chunk_id): void                 // swap content (ConceptView 'collapsed'), position at hit
Billboard.onClick(): void                           // capture rect → Editor.pin → reset
Halo.open(focal_card_id): void; Halo.delete(result_id): void
LinkLayer.route(): void                             // per-frame line redraw (driven by pulse/raf.ts)
```

---

## §3 — Internal Logic

### §3.1 Billboard (Real→Imaginary, §4.2)
One `#billboard` element; content swapped per hover via `ConceptView.render(node,'collapsed')` (cell.md). On click it captures `getBoundingClientRect()` and hands **only that screen rect** to `Editor.pin` (imaginary.md §3.3), then resets. Screen-rect is the entire payload — no 3D coordinate crosses into the editor (§6.6.2).

### §3.2 Halo — cone-ray-similarity transport (§O.18)
```
open(focal_card_id):
   candidates = store.read('index')[focal].apparitions   // backend-scored (retrieval.md §3.1/§3.2)
   render concentric radiation of name-only phantoms (ConceptView 'phantom', cell.md)
   for each retrieved 3D node (transport coords supplied by backend surface_for_projector):
       apex = the 2D query element ; radial + along-ray distance ← normalized similarity
       angular ← camera-view projection along the cone surface normal ; HSV rotates with parent
   gating: text-input fields fire the halo; pure-{ref} fields do NOT (§O.3)
   delete(result) → drop it, pull the next-most-similar from the ranked queue
   click a phantom → autoregression (re-center the halo on it, §8.2.2)
```
The Halo **renders** the transport; the **coords come from the backend** (the frontend computes no similarity).

### §3.3 LinkLayer — the only line-drawer (§O.16 / §18.7)
Draws every link: hard `--steel-300`/2px, soft `--steel-700`/1px — **undirected lines, no arrowheads** (hard/soft by brightness + weight, never glyph); stringless compile edges. The **2D↔3D connector** is a solid **yellow** (`#ffd700`) **headless** line, recomputed per frame from the 3D node's `Projector.project(...)` point (real.md) — it **drives nothing** (purely indicative, §6.6.2). **No `stroke-dasharray` anywhere** (dotted/dashed lines forbidden, §18.7).

---

## §4 — Dependencies

- **Calls:** `ConceptView` (cell.md), `Editor.pin` (imaginary.md), `Projector.project` (real.md), the store (apparitions + transport coords), `GestureGateway` (halo open/delete, wire promote).
- **Called by:** `pulse/raf.ts` (LinkLayer routes per frame; billboard follows hover); the projector's raycast feeds hover hits.

---

## §5 — Excluded

- The theme token values (`frontend/theme.md`); the similarity scoring (backend/retrieval.md). The register-coupling philosophy.
