# Spec — Frontend / Membranes (Billboard · Halo · LinkLayer)

> Deepens [`code_architecture/frontend/membranes.md`](../../code_architecture/frontend/membranes.md). Modules: `fe/membranes/{billboard,halo,link_layer}.ts`. Constants: [`../constants.md`](../constants.md) §8. The three one-way 2D↔3D couplings.
>
> **Realized form (cp/*.js).** Greenfield `fe/membranes/*.ts`; realized in `cp/billboard.js` (hover billboard + freeze-at-rect pin), `cp/concept_graph.js` (`_renderApparitionHalo`/`_populateHalo`, `_drawConceptEdges`/`_edgeStyleForType` — solid, no dashes/arrowheads §O.16, the `#ffd700` 2D↔3D arrow), `cp/edge_manager.js` (3D edge lines) — see `frontend/{billboard,halo,link_layer}.md`. Verified via `hover-to-stick-rect-parity`, `halo-focus-roundtrip`, `edge-roundtrip`.

---

## §1 — `Billboard` (Real→Imaginary, screen-rect only)

```ts
class Billboard { showHover(chunk_id: ChunkId): void; onClick(): void; reset(): void }
```
- **`showHover`** — swap the single `#billboard` content to `ConceptView.render(node, COLLAPSED)` (cell.md); position at the projector hit (real.md `raycastHover`). Fires `ui/hover`.
- **`onClick`** — `rect = el.getBoundingClientRect()`; `Editor.pin(node, rect)` (imaginary.md §1.2); `reset()`. **Only the screen rect** crosses into the editor — no 3D coordinate (§6.6.2).

---

## §2 — `Halo` (cone-ray-similarity transport, §O.18)

```ts
class Halo { open(focal_card_id: ConceptId): void; delete(result_id: ConceptId): void; close(): void }
```
- **`open` algorithm:**
```
cands = store.index[focal].apparitions          # backend-scored (retrieval.md), incl. RayTransport
render concentric radiation of name-only phantoms (ConceptView PHANTOM)
for c in cands with c.transport:                 # coords from backend; client only RENDERS
    place the 3D node at radial=c.transport.radial, along the focal cone ray=along_ray,
        angular=c.transport.angular (camera-view projection along cone surface normal); HSV rotates with parent
gating: fire only on text-input fields; pure-{ref} fields do NOT open a halo (§O.3)
fire ui/halo
```
- **`delete`** — drop the result; pull the **next-most-similar** from the ranked `cands` queue (already ranked, retrieval.md §3.2). Click a phantom → autoregression (re-center halo on it, §8.2.2).

---

## §3 — `LinkLayer` (the only line-drawer)

```ts
class LinkLayer { route(): void }      // per-frame redraw (pulse/raf.ts)
```
- **`route` (per frame):** for each edge → draw an **undirected line, NO arrowhead**: hard `--steel-300`/`LINK_HARD_PX`, soft `--steel-700`/`LINK_SOFT_PX` (hard/soft by brightness+weight, never glyph, §O.16). Stringless compile edges. The **2D↔3D connector** = solid **`CONNECTOR_HEX`** (`#ffd700`) headless line from `Projector.project(node3d)` (real.md) — recomputed each frame, **drives nothing** (purely indicative, §6.6.2).
- **Invariant** — **no `stroke-dasharray` anywhere**; no arrowheads (assertion, errors.md §3). The only hue outside 3D nodes is this connector.

---

## §4 — Excluded
Theme token values (`frontend/theme.md`); similarity scoring (backend/retrieval.md); the register-coupling philosophy.
