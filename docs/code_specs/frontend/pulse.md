# Spec — Frontend / Pulse (Reconciler · tweens · raf)

> Deepens [`code_architecture/frontend/pulse.md`](../../code_architecture/frontend/pulse.md). Modules: `fe/pulse/{reconciler,tweens,raf}.ts`. Constants: [`../constants.md`](../constants.md) §8. The cross-cutting liveness engine — one rAF for the whole app.
>
> **Realized form (cp/*.js).** Greenfield `fe/pulse/*.ts`; realized in `cp/animation.js` (the single `requestAnimationFrame` loop + the `colorMatrix` HSV spectral rotation + per-frame camera bounds) + `cp/force_layout.js` (interruptible per-frame UMAP-linear-radial convergence) + the `chunkCollapseTarget/State` tween Maps in `chunk_projector.js` — see `frontend/liveness.md`. Edit-safety via `/api/ui/edit_open|edit_close`.

---

## §1 — `Reconciler`

```ts
class Reconciler {
  diff<K>(next: Map<K, V>, prevKeyset: Set<K>): { enter: K[]; update: K[]; exit: K[] }
  apply(d, handlers: { onEnter; onUpdate; onExit }): void
}
```
- **`diff`** — `enter = next.keys \ prev`; `exit = prev \ next.keys`; `update = next ∩ prev`. Keys are **stable** (`ChunkId`, `ConceptId`). Minimal mutation — never wholesale rebuild.
- **`apply`** — call handlers per bucket; an `update` whose target is an **open-edit field is a no-op** (edit-safety, §9.4): an incoming frame never clobbers a field the user is typing in.

---

## §2 — `Tweens`

```ts
class Tweens { to(handle, target, opts?: {ms?: number}): Tween; advance(now: number): void }
```
- **`to`** — interruptible eased tween (default `TWEEN_MS`). A new `to` on a live handle **recomputes from the current interpolated value** (never restarts/snaps) — this is why a `umap_canonical` retarget mid-scan is smooth (real.md §2). No tween holds authoritative state (the store is truth; tweens only animate toward it).
- **`advance`** — step all live tweens; drop completed.

---

## §3 — `Raf` (the one loop)

```ts
class Raf { start(): void; onFrame(cb: (now: number) => void): () => void }
```
- **The single `requestAnimationFrame` loop:**
```
loop(now):
   Tweens.advance(now)
   Projector.animate()                 # real.md §1 (camera, HSV, collider, spine, perimeter)
   Reconciler.apply(diffs)             # flush enter/update/exit from keyed store subscriptions
   LinkLayer.route()                   # membranes.md (lines from projected points)
   Editor.reflow(dirtyIds)             # imaginary.md (named-card cascade reflow)
   requestAnimationFrame(loop)
batched reads THEN writes (no layout thrash); telemetry/POSTs off the critical path (spine.md)
```
- **Invariant** — exactly **one** rAF for the app; every Organ/Membrane registers an `onFrame` consumer rather than spinning its own loop → positions, lines, and panels agree every paint.

---

## §4 — Excluded
Easing-curve values (`frontend/theme.md`); the "liveness" register framing.
