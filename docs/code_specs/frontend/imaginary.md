# Spec — Frontend / Imaginary Organ (Editor · subgraph_layout)

> Deepens [`code_architecture/frontend/imaginary.md`](../../code_architecture/frontend/imaginary.md). Modules: `fe/imaginary/{editor,subgraph_layout}.ts`. Types: [`../types.md`](../types.md) (`Rect`, `XY`). Screen-pixel coords — never the 3D system (§6.6.2).
>
> **Realized form (cp/*.js).** Greenfield `fe/imaginary/*.ts`; realized in `cp/concept_graph.js` (the `ConceptGraphMixin` 2D editor — card render, ray-constrained `_rayConstrainedPosition` layout, seven-gesture model, subgraph compile/collapse) — see `frontend/editor.md`. Verified via `editor-primitives-roundtrip`, `gesture-walkthrough`, `compile-expand-collapse-roundtrip`.

---

## §1 — `Editor`

```ts
class Editor {
  pin(node: ConceptNode, rect: Rect): void           // freeze-at-rect
  reflow(changedIds: ConceptId[]): void               // keyed cascade reflow
  toggleForm(card_id: ConceptId): void                // double-left: panel ↔ graph (symmetric)
  dispatchGesture(ev: PointerEvent, target: ConceptId): void
}
```

### §1.1 The seven gestures (§7.3.4 — `dispatchGesture` routes each)
| Gesture | Action | Gateway kind |
|---|---|---|
| hover | preview billboard | `ui/hover` |
| single-left | edit (borderless) | (local edit → `concepts.patch` on commit) |
| left-drag node→node | wire + inherit | `concept_edges` (soft→hard) |
| **right-click** | **rank-1 fold (PANEL form only, §O.1)** | `ui/node_fold` |
| right-click base | collapse-to-self | `ui/compile_collapse` |
| **double-left** | **panel↔graph toggle (both directions)** | `ui/compile_expand`/`collapse` |
| double-right | delete | `concepts.delete` |

**Generalized rank-dominance collapse (§7.3.5, Q.5).** The 2D `right-click` rank-1 fold + `right-click base` collapse-to-self are the **Imaginary-register form of the same generalized rank-dominance collapse gesture** the 3D projector carries (§6.6.5; real.md). The membership rule is identical — the dominator's dominated-set over the `ConceptEdge` graph (DOMAIN §8.1.2) — and fold-state is preserved across re-expand (M.6). The only difference is the non-dominated-node visibility policy: the **3D isolates** (`scale=0` everything else); the **2D leaves siblings in place** (the editor already scopes attention to the focal). A REPL `ui-dominance-collapse` on a node folds it in every open surface that renders it (3D + 2D), keyed by node id.

### §1.2 `pin` — freeze-at-rect (§18.8)
On click, `Billboard` (membranes.md) captures `getBoundingClientRect()`; `pin(node, rect)` materialises the panel at **byte-for-byte that rect** (`top/left/width/height`), then user drag/resize/minimise field-merges into `pin_chrome` (gateway → persistence.md mirror). **One panel anatomy, one code path** — no hover/click two-panel split (forbidden).

### §1.3 Folding vs graph form (§O.1)
**Folding is panel-only.** Graph form = **undirected line links, NO folding** (membranes.md `LinkLayer`), with **node-count parity** to the panel it toggled from (every panel node ↔ a graph node). Braces are the fold marker, three states `BraceState` — a panel concern. `toggleForm` is symmetric (panel→graph and graph→panel).

### §1.4 `reflow`
Updates **only the named `changedIds`** (keyed; pulse.md `Reconciler`); open editors untouched (edit-safety); **never auto-unfolds** a collapsed node (§O.13 — fold is UI, the cascade only changes values).

---

## §2 — `SubgraphLayout`

```ts
class SubgraphLayout { place(focal_id: ConceptId, nodes: ConceptId[]): Map<ConceptId, XY> }
```
- **2D-UMAP-of-nomic recentred on the focal**, radial-DOF only, push apart along rays (planar analogue of backend/layout.md §2 / §O.17). The forbidden concentric rings / `_fibonacciPosition` are **not** implemented — ray-constrained placement around the focal card. Nomic positions come from the `index` slice (backend-supplied); the client only arranges in 2D px.

---

## §3 — Excluded
Theme; the backend layout fit; compile backend (compute.md); the Imaginary-register philosophy.
