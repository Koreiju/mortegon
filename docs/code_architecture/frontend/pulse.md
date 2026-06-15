# Frontend — Pulse (Reconciler · tweens · raf)

> **Owns:** the cross-cutting liveness engine — keyed reconciliation, interruptible tweens, and the single animation loop. Modules: `fe/pulse/reconciler.ts`, `tweens.ts`, `raf.ts`. Design: §5.4 / §5.5 / §9.4 + `frontend/liveness.md`. Realises `code_constraints/frontend_rendering.md`. Pulse is what makes the projection **fluid** under streaming frames.

---

## §1 — Responsibility

Turn a stream of store updates into minimal, smooth DOM/scene mutations: diff keyed collections (enter/update/exit), interpolate every position change (never snap), and run **exactly one** `requestAnimationFrame` loop for the whole app. No view holds authoritative state; Pulse never reads the network.

---

## §2 — Public Surface

```ts
Reconciler.diff(next: Map, prevKeyset: Set): { enter, update, exit }
Tweens.to(handle, target, opts): Tween          // interruptible; retargets from current value
Tweens.advance(now): void                       // step all live tweens
Raf.start(): void                               // the ONE loop
Raf.onFrame(cb): void                           // register a per-frame consumer (projector, link layer, reflow)
```

---

## §3 — Internal Logic

### §3.1 Reconciler — keyed, minimal (§9.4)
From `(next, prevKeyset)` (the store's keyed subscription, spine.md) it computes enter/update/exit and applies the **minimal** mutation — never a wholesale rebuild. Keys are stable (integer `chunk_id` for chunks, `concept_id` for cards) so adding the 501st item doesn't touch the first 500. **Open-edit fields are no-op update targets** (edit-safety): an incoming frame never clobbers a field the user is typing in.

### §3.2 Tweens — interruptible (§5.4)
Every position/scale/opacity change goes through a tween. A **new target mid-flight recomputes from the current interpolated value** (never restarts, never snaps) — this is why a `umap_canonical` retarget mid-scan is smooth (real.md §3.2). No tween holds authoritative state; the store remains the truth, the tween only animates toward it.

### §3.3 raf — the one loop (§5.5)
```
Raf loop (once per frame):
   Tweens.advance(now)
   Projector.animate()                 # real.md §3.1 (camera, HSV, collider, spine, perimeter)
   flush Reconciler enter/update/exit
   LinkLayer.route()                    # membranes.md (redraw lines from projected points)
   Editor.reflow(dirty)                 # imaginary.md (named-card cascade reflow)
   yield
batched reads then writes (no layout thrash); telemetry + POSTs are OFF the critical path (spine.md gateway)
```
Exactly one rAF for the app — the projector, link layer, reconciler flush, and editor reflow all ride it, so the frame is coherent (positions, lines, and panels agree every paint).

---

## §4 — Dependencies

- **Calls:** `Projector` (real.md), `LinkLayer` (membranes.md), `Editor.reflow` (imaginary.md), the store's keyed subscriptions (spine.md).
- **Called by:** boot (`Raf.start`); every Organ/Membrane registers an `onFrame` consumer rather than spinning its own loop.

---

## §5 — Excluded

- The theme/easing curve *values* (`frontend/theme.md`); the register philosophy of "liveness." Only the reconcile/tween/loop mechanics are encoded.
