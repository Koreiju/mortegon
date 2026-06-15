# Code Architecture — Frontend Suite (greenfield)

> **Status: planned (greenfield).** Built fresh from [`../../FRONTEND_REDESIGN.md`](../../FRONTEND_REDESIGN.md) (object model) + the [`../../frontend/`](../../frontend/) design suite (per-surface reference). The legacy `cp/*.js` is **not** a reference — it is replaced ([`../migration.md`](../migration.md)). Each doc carries: responsibility · public surface (signatures) · internal logic · dependencies · realises (`code_constraints/frontend_rendering.md`) · excluded. The **theme** ([`../../frontend/theme.md`](../../frontend/theme.md)) is referenced, never restated.

---

## §1 — The One Data-Flow Loop (the architectural invariant)

The frontend **owns no truth**; it is a fluid projection of canonical backend state + the gesture surface.

```
frames (WS) → FrameBus → WorkspaceStore → Views render            (truth, one way)
gesture → GestureGateway → backend lifecycle → frames → FrameBus  (intent, the reverse)
render-settled → GestureGateway.telemetry → /api/ui/telemetry     (Symbolic mirror)
```
Single inbound seam (FrameBus), single outbound seam (GestureGateway), single source of truth (WorkspaceStore). The only state a view owns is **transient interaction state** (active drag, caret, in-flight echo). Backend computes; the frontend never runs UMAP / embeddings / PageRank / compile.

---

## §2 — Module Tree (`fe/`, the `FRONTEND_REDESIGN.md` §11 layout)

```
fe/
  spine/      frame_bus  store  gateway        → spine.md
  cell/       concept_view  field_tree  field_strategies   → cell.md
  real/       projector  chunk_field  texture_cache        → real.md
  imaginary/  editor  subgraph_layout                      → imaginary.md
  membranes/  billboard  halo  link_layer                  → membranes.md
  pulse/      reconciler  tweens  raf                       → pulse.md
```

| Doc | Tier | Owns |
|---|---|---|
| [`spine.md`](spine.md) | Spine | the single inbound seam, the normalized store, the single outbound seam |
| [`cell.md`](cell.md) | Cell | the one record renderer (4 modes) + the data-self-defining field-tree interpreter |
| [`real.md`](real.md) | Organ (Real) | the 3D projector + scan-streaming pipeline + image cache |
| [`imaginary.md`](imaginary.md) | Organ (Imaginary) | the 2D editor canvas + cascade reflow + subgraph layout |
| [`membranes.md`](membranes.md) | Membranes | the three one-way 2D↔3D couplings (hover→pin, halo transport, links) |
| [`pulse.md`](pulse.md) | Pulse | the cross-cutting liveness engine (keyed reconcile, tweens, one rAF) |

---

## §3 — Reading Order

`spine.md` (how truth + intent flow) → `cell.md` (the universal record's rendering) → `real.md` + `imaginary.md` (the two canvases) → `membranes.md` (how they couple) → `pulse.md` (what keeps it fluid). Cross-cutting: [`../migration.md`](../migration.md) (the `cp/` → `fe/` map) and [`../../frontend/theme.md`](../../frontend/theme.md) (the visual system).
