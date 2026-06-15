# Frontend API & Feature Documentation Suite

> **Status: realised (cp/*.js).** This suite specifies the frontend in full. The *realised* frontend is the `backend/static/js/cp/` mixin suite (per the user's "update existing frontend in place" pivot, not the greenfield `fe/` sketch): each surface doc's Status now cites its implementing `cp/*.js` module(s) + the env-scenario(s) that verify its complex interactions through the REPL. The 83-scenario `full-smoke` + `route-coverage` + `action-registry-coverage` gate the gesture catalogue (`gesture_gateway.md` §5). [`../FRONTEND_REDESIGN.md`](../FRONTEND_REDESIGN.md) remains the *object-model anchor* (the greenfield vision); this suite is the *reference*.
>
> **What this suite is.** A modular, standalone set of feature/API documents for the Web Fiber Haptics frontend. Where [`../FRONTEND_REDESIGN.md`](../FRONTEND_REDESIGN.md) is the *object-model anchor* (the vision and the object tiers in one integrated statement), this suite is the *reference*: one document per surface, each complete on its own, covering **what the thing is, what it is made of, what it does with the others, its behaviours, the activities it supports, the sequences it runs, the data it consumes and produces, the results it renders, how it mirrors into the REPL, and how it wears the theme.**
>
> **Precedence.** [`../DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) wins on design intent; [`../FRONTEND_REDESIGN.md`](../FRONTEND_REDESIGN.md) wins on object boundaries; [`../code_constraints/frontend_rendering.md`](../code_constraints/frontend_rendering.md) wins on programming-surface specifics. This suite elaborates all three into per-surface reference detail and must not contradict them.

---

## §0 — How To Read This Suite

Each document is self-contained: you can read any one without the others and come away with the complete specification of that surface. Cross-references (by `§X.Y` into `DOMAIN_MODEL.md`, or by filename into this suite and the object docs) carry the *rationale*; the *behaviour* is restated locally so the doc stands alone.

Read in this order on a first pass; thereafter jump to whichever surface you are building or verifying:

1. **[`theme.md`](theme.md)** — the visual system. Read first; **every** other doc applies it.
2. **[`architecture.md`](architecture.md)** — the projection thesis, the object tiers, the one data-flow loop.
3. **The Spine** — [`frame_bus.md`](frame_bus.md), [`workspace_store.md`](workspace_store.md), [`gesture_gateway.md`](gesture_gateway.md).
4. **The Cell** — [`concept_view.md`](concept_view.md), [`field_tree.md`](field_tree.md), [`compile_collapse.md`](compile_collapse.md), [`object_exploration.md`](object_exploration.md).
5. **The Real canvas** — [`projector.md`](projector.md), [`scan_streaming.md`](scan_streaming.md).
6. **The Imaginary canvas** — [`editor.md`](editor.md).
7. **The Membranes** — [`billboard.md`](billboard.md), [`halo.md`](halo.md), [`link_layer.md`](link_layer.md).
8. **Feature surfaces** — [`retrieval_and_sidebar.md`](retrieval_and_sidebar.md), [`pattern_map_and_url_set.md`](pattern_map_and_url_set.md), [`agent_and_rollout.md`](agent_and_rollout.md).
9. **Cross-cutting** — [`liveness.md`](liveness.md), [`repl_mirroring.md`](repl_mirroring.md).

---

## §1 — The Document Catalogue

| Doc | Surface | Owns |
|---|---|---|
| [`theme.md`](theme.md) | Visual system | The dark-minimal stainless-steel-over-black token set, outline spec, typography, states, motion, the 3D-exception zone |
| [`architecture.md`](architecture.md) | Orientation | The pure-projection thesis; object tiers; data-flow loop; the eight load-bearing invariants |
| [`frame_bus.md`](frame_bus.md) | Spine — inbound | The single workspace WebSocket; every frame type; sequencing; resume; backpressure |
| [`workspace_store.md`](workspace_store.md) | Spine — state | The normalized mirror; every slice and shape; selectors; reset; the optimistic-echo overlay |
| [`gesture_gateway.md`](gesture_gateway.md) | Spine — outbound | Every gesture → REST mapping; idempotency; optimistic echo; telemetry posting |
| [`concept_view.md`](concept_view.md) | Cell | The one panel anatomy; the four modes; chrome; latch + form-fit; the close-button fixture rule |
| [`field_tree.md`](field_tree.md) | Cell | The recursive data→pure-print interpreter; parse/print/project/edit/serialize; plus-signs; click-to-edit; `{var}`; signal-stream |
| [`compile_collapse.md`](compile_collapse.md) | Cell | The double-left-click synthesis↔analysis dialectic in the frontend |
| [`object_exploration.md`](object_exploration.md) | Cell | Recursive type-strict & reference exploration of object models; the five-gesture model; typed `key:Type=value` panels; functions-as-memory-lookup; fold-state preservation; instance inheritance; reservoir readout |
| [`projector.md`](projector.md) | Real | The Three.js scene; chunk field; placement states; animate-loop invariants; camera; perimeter; visibility flags |
| [`scan_streaming.md`](scan_streaming.md) | Real | The live scan pipeline; incremental add; interruptible UMAP tween; HSV; image textures |
| [`editor.md`](editor.md) | Imaginary | The 2D canvas; pins; freeze-at-rect; wiring; the cascade reflow; subgraph layout |
| [`billboard.md`](billboard.md) | Membrane | Hover preview; the freeze-at-rect capture; the one billboard instance |
| [`halo.md`](halo.md) | Membrane | Concentric-circle radiation; ray-projection to the conic surface; HSV phantoms; autoregression |
| [`link_layer.md`](link_layer.md) | Membrane | Solid hard/soft links; commitment fan vs possibility ring; the 2D↔3D yellow arrow |
| [`retrieval_and_sidebar.md`](retrieval_and_sidebar.md) | Feature | Result list; IntersectionObserver spine; URL sidebar; eye/×/click; hidden flags |
| [`pattern_map_and_url_set.md`](pattern_map_and_url_set.md) | Feature | The `pattern_map` output panel; golden trio; the `{urls_panel}` aggregator |
| [`agent_and_rollout.md`](agent_and_rollout.md) | Feature | The agent body subgraph render; token stream; play/pause iterated rollout |
| [`liveness.md`](liveness.md) | Cross-cut | The Reconciler; the interruptible tween scheduler; edit-safety; the one frame budget |
| [`repl_mirroring.md`](repl_mirroring.md) | Cross-cut | Telemetry completeness; the in-place activity viewer; the severance rule |

---

## §2 — The Standard Document Template

Every surface doc below follows the same eleven-section template so the suite is uniform and each doc is provably complete. A doc is *done* when all eleven sections are non-trivially filled.

1. **Identity** — what the thing is, in one paragraph, and which object (per `FRONTEND_REDESIGN.md`) implements it.
2. **Structure** — what it is made of: DOM/scene structure, the state it owns (transient only), the data shapes it reads from the store.
3. **Composition** — what it does *with the others*: which objects it depends on, which depend on it, and through which seam.
4. **Behaviours** — the rules and invariants it must hold, including the anti-goals it structurally prevents.
5. **Activities** — the user/agent gestures it supports, each named to its `gesture_gateway.md` kind and `DOMAIN_MODEL.md` §14.2 catalogue row.
6. **Sequences** — the state machines: gesture → effect → settled state, threaded through the seams.
7. **Data** — the exact shapes in and out: frames consumed, REST sent, store slices read/written.
8. **Results** — what renders, and what telemetry is emitted.
9. **REPL mirroring** — how the surface appears in the Symbolic register: which mirror field, which `watch-activity` row, which REPL action drives it.
10. **Theme** — how the stainless-steel-over-black system (`theme.md`) renders *this* surface specifically.
11. **References** — the `DOMAIN_MODEL.md` §-anchors and peer docs.

---

## §3 — Conventions

- **`§X.Y`** alone refers to `DOMAIN_MODEL.md`. Section refs within a suite doc (`§2.3`) are local to that doc.
- **Object names** (`FrameBus`, `WorkspaceStore`, `GestureGateway`, `ConceptView`, `FieldTree`, `Projector`, `Editor`, `Billboard`, `Halo`, `LinkLayer`, `Reconciler`) are the `FRONTEND_REDESIGN.md` objects and are capitalised.
- **Gesture kinds** (`ui-pin`, `concept-edit-data-row`, …) are `gesture_gateway.md` / §14.2 catalogue identifiers, in code font.
- **Frame types** (`concept_changed`, `umap_canonical`, …) are §10.1 WS frames, in code font.
- **Mirror fields** (`pinned_billboards`, `halo_focus`, …) are §10.5 UI-state fields, in code font.
- **Theme tokens** (`--steel-300`, `--bg-void`, …) are `theme.md` identifiers.

---

## §4 — The Through-Line

Two requirements thread every doc and are never localised to one:

- **REPL mirroring** (the Symbolic register, §14). Every surface that renders or accepts a gesture has a §9 *REPL mirroring* section. The rule is absolute: *what you render, you report* — a surface state invisible to the REPL is a severance (§18.1). [`repl_mirroring.md`](repl_mirroring.md) is the cross-cutting account; each doc carries its own slice.
- **The theme** (dark-minimal, stainless steel over black). Every surface has a §10 *Theme* section. The rule is absolute: *steel hairlines over black everywhere, except 3D nodes and billboards, which alone carry saturated colour and imagery.* [`theme.md`](theme.md) is the system; each doc carries its application.
