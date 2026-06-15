# Liveness — The Cross-Cutting Pulse

> **Status: realised (cp/*.js); greenfield Pulse tier in `FRONTEND_REDESIGN.md` §9.** The pulse role is carried by `cp/animation.js` (the single `requestAnimationFrame` loop driving both canvases) + `cp/force_layout.js` (the interruptible per-frame layout convergence toward `umap_canonical`) + the per-chunk `chunkCollapseTarget`/`chunkCollapseState` tween Maps in `chunk_projector.js`. Edit-safety: edits route through `/api/ui/edit_open`/`edit_close` so the reconciler doesn't clobber an open field. Realises the *smooth, fluid, live updates* requirement; exercised live via `scan-streaming-routes-to-workspace-ws` + the `watch-activity` viewer.

---

## §1 — Identity

Liveness is not a surface; it is the discipline every organ and membrane schedules its motion through. One engine, four mechanisms: **keyed reconciliation** (minimal mutation), **interruptible eased tweens** (smooth, retargeting motion), **edit-safety** (never clobber an open editor), and **one frame budget** (no layout thrash). It is why a streaming scan (`scan_streaming.md`) and a cascading edit (`editor.md` §6.4) stay smooth *simultaneously* — they share a budget and a discipline rather than competing rAF loops.

---

## §2 — The four mechanisms

### §2.1 The Reconciler — keyed enter/update/exit
Store subscriptions deliver `(next, prevKeyset)` (`workspace_store.md`). The Reconciler diffs by key (`concept_id`, `chunk_id`, `edge_id`) and emits the minimal mutation set:
- **enter** — new key → create the DOM node / InstancedMesh slot;
- **update** — changed value → patch in place;
- **exit** — missing key → remove.

Nothing is torn down and rebuilt wholesale. Adding the 501st chunk does not touch the first 500; a cascade re-renders one card without reflowing the canvas. This is the structural opposite of the legacy "re-render the world on any change" pattern that bred the overhang.

### §2.2 The interruptible tween scheduler
All motion — chunk settling (`projector.md` §4), camera frame-on-scan, link re-route (`link_layer.md`), halo radius changes (`halo.md`), HSV phase, theme edge-brighten (`theme.md` §6) — is an eased tween advanced once per frame. Tweens are **interruptible and retargeting**: a new target mid-flight recomputes from the *current interpolated value*, never restarting from the origin. This single property is the difference between "settles smoothly" and "stutters on every UMAP refit." No tween holds authoritative state; the target is read from the store, the position is transient.

### §2.3 Edit-safety — never clobber an open editor
An open textarea (`field_tree.md` §6) is transient interaction state owned by its `ConceptView`. Incoming `concept_changed` frames reconcile *around* it: other fields of the same card update; the open field's textarea value + caret are left untouched until commit/blur, at which point the commit is the reconciliation. Enforced in the Reconciler's update path (an open-edit field is a no-op target for frame-driven updates). This is what lets the cascade run continuously (`editor.md`, §7.4 default) without fighting the user's typing.

### §2.4 The one frame budget
Exactly one `requestAnimationFrame` loop. Per tick: advance tweens → run the Projector animate invariants (`projector.md` §5) → flush the Reconciler's queued mutations → re-route dirty links → yield. Reads and writes are batched (measure-then-mutate, never interleaved) to avoid layout thrash. Telemetry (`repl_mirroring.md`) and gesture POSTs (`gesture_gateway.md`) are debounced/batched off the critical path.

---

## §3 — Composition

| Mechanism | Serves |
|---|---|
| Reconciler | `Projector` (chunk field), `Editor` (panels), `LinkLayer` (edges), `Halo` (phantoms), agent token ring |
| Tween scheduler | every animated transition in every canvas/membrane |
| Edit-safety | `ConceptView` / `FieldTree` open editors during cascade |
| Frame budget | the single rAF all of the above share |

Backpressure + resume (`frame_bus.md` §4) are the *inbound* half of liveness: they keep the render budget spent on the freshest state, never on draining a stale backlog.

---

## §4 — Behaviours

1. **Minimal mutation only.** No wholesale rebuilds; keyed enter/update/exit (§2.1).
2. **All motion is one interruptible eased tween on one budget.** No spring, no bounce, no parallax; retarget, never restart (§2.2, §2.4).
3. **An open editor is sacrosanct.** Frame-driven updates never touch it (§2.3).
4. **One rAF, batched reads/writes.** No layout thrash; off-critical-path telemetry/POSTs (§2.4).
5. **Smoothness is structural, not incidental.** A scan + a cascade + a halo open at once all settle within the one budget because they share the Reconciler and the scheduler.

---

## §5 — Sequences

### §5.1 Concurrent scan + edit (the proof)
```
one rAF tick:
   chunk_added×k arrived  → Reconciler ENTER k InstancedMesh slots (preliminary radial)
   umap_canonical arrived → tween scheduler RETARGET affected chunks from current pos
   concept_changed (card A) → Reconciler UPDATE A's rendering; LinkLayer re-route A's edges eased
   card B has an open editor → edit-safety leaves B's textarea + caret untouched
   advance all tweens; apply HSV phase; run collider; flush mutations; yield
```
Both the scan and the edit progress in the same tick; neither blocks the other.

---

## §6 — Data

Liveness reads the store's diffs (via subscriptions) and the per-frame projection; it sends nothing. Its "data" is the keyset diff `(next, prevKeyset)` and the tween targets read from `chunks`/`layout`/`edges`.

---

## §7 — Results

A surface that is live under load: chunks pop in and settle smoothly, refits retarget without stutter, cascades reflow only what changed, halos open without freezing the scan, and typing is never clobbered. No jank, no full-rebuild flashes, no dropped frames from thrash.

---

## §8 — REPL Mirroring

Liveness has no mirror field of its own — it is a rendering concern. Its REPL-relevant guarantee: because motion is frame-driven from store diffs (not from local timers holding state), the *settled* state the REPL reads back via telemetry always matches what a frame produced. A tween in flight is transient and never reported as truth; only committed store values are mirrored (`repl_mirroring.md`). This is why a REPL assertion taken after `done` is deterministic despite the smooth motion in between.

---

## §9 — Theme

Liveness renders no surface but enforces the theme's motion budget (`theme.md` §6): edge-brighten transitions (120 ms eased) and sheen-on-hover share the same scheduler and budget as geometry tweens, so the steel never flickers and the void never moves. The only continuous motion is the HSV rotation of 3D nodes (the exception zone) and the eased settling of geometry — both on this one budget.

---

## §10 — References

- `DOMAIN_MODEL.md`: §2.4 (backpressure/resume), §6.1 (tween states), §7.4 (cascade), §9.3 (UMAP refit); anti-goals §18.2 (no restart-from-scratch), §18.9 (resize).
- `FRONTEND_REDESIGN.md` §9.
- Peers: `projector.md`, `scan_streaming.md`, `editor.md`, `frame_bus.md`, `workspace_store.md`.
