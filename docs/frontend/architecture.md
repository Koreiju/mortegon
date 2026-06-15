# Architecture — The Pure-Projection Frontend

> **Status: realised (cp/*.js).** Standalone orientation for the suite. The greenfield object treatment is in [`../FRONTEND_REDESIGN.md`](../FRONTEND_REDESIGN.md); the **realised** frontend is the `backend/static/js/cp/` mixin suite assembled onto the `ChunkProjector` instance in `chunk_projector.js` (Object.assign of UiUtils · EdgeManager · InstanceManager · Media · SpriteManager · NodeLoader · Billboard · Workspace · Interaction · Animation · Search · Scanner · ConceptGraph · ForceLayout · Telemetry mixins). Pure-projection holds: every gesture round-trips through the backend (`_mirrorUi`), no frontend-only state transition — so the REPL reconstructs full Imaginary+Real state from frames + telemetry (`repl_mirroring.md`).

---

## §1 — Identity

The frontend is a **pure projection of canonical backend state** and the **gesture surface** through which the user perturbs that state. It owns no truth. The Real (3D geometry, `projector.md`), the Imaginary (concept structure, `editor.md`), and the alchemy between them are computed on the backend — UMAP coordinates, embeddings, PageRank, compile renderings, cascade order, apparition ranks, and the UI-state mirror itself (§10.5). The frontend renders what frames tell it and sends gestures that become frames.

This is the cure for the legacy "overhang": overhang is *derived state that drifted from its source*. A pure projection has no derived authoritative state to drift — only transient interaction state (the active drag this frame, the caret in an open textarea), which is local, ephemeral, and reconciled gently against incoming truth.

---

## §2 — Structure: the object tiers

Five tiers, mapped to an anatomy so the architecture is self-similar to the Mortegon it serves (§14).

| Tier | Objects | Role |
|---|---|---|
| **Spine** | `FrameBus`, `WorkspaceStore`, `GestureGateway` | Transport + the single source-of-truth mirror |
| **Cell** | `ConceptView`, `FieldTree` | The one record rendered in its three forms via one self-describing interpreter |
| **Organs** | `Projector` (Real), `Editor` (Imaginary) | The two coordinate-separate canvases |
| **Membranes** | `Billboard`, `Halo`, `LinkLayer` | The only three couplings between canvases, each one-way |
| **Pulse** | `Reconciler`, tween scheduler, frame budget | Cross-cutting liveness — smoothness everywhere |

Each suite doc specifies one object (or one tightly-coupled feature built from objects).

---

## §3 — The one data-flow loop

State flows one way; gestures flow the reverse; both close through a single seam each.

```
   INBOUND (truth)                              OUTBOUND (intent)
   WebSocket frames (§10.1)                     user / agent gesture (§14.2)
        │                                              │
        ▼                                              ▼
   FrameBus ─────────── one inbound seam        GestureGateway ──── one outbound seam
        │  (frame_bus.md)                              │  REST + idempotency (gesture_gateway.md)
        ▼                                              ▼
   WorkspaceStore ───── the only truth          backend lifecycle dispatcher (§10.2)
        │  (workspace_store.md)                        │
        ▼                                              ▼
   Views render (Cell / Organs / Membranes)     … broadcasts frames … ──► FrameBus (loop closes)
        │
        ▼
   telemetry of what rendered ─────────────────► GestureGateway ──► UI State Service (§10.5) ──► REPL
```

A gesture never mutates a view directly. It travels to the backend, the backend's lifecycle (§10.2) is the single authority, and the resulting frame flows back through the *same* inbound path any other actor's mutation would (user, agent, REPL). This is why the REPL ↔ frontend round-trip holds by construction: there is no frontend-only transition for the REPL to miss (`repl_mirroring.md`).

---

## §4 — Behaviours: the eight load-bearing invariants

Every suite doc honours these; they are the frontend's analogue of §2.

1. **No authoritative frontend state.** Views own only transient interaction state; everything else reads from `WorkspaceStore`.
2. **One inbound seam, one outbound seam.** All truth enters via `FrameBus`; all intent leaves via `GestureGateway`. No view opens its own socket or fetch.
3. **One record, one renderer, three modes.** `ConceptView` is the single anatomy; mode is a parameter, never a fork (§18.11).
4. **Data is the schema.** Field structure is parsed, never declared; `FieldTree` is the only interpreter (§4.5, §4.6).
5. **The frontend renders coordinates; it never computes them.** No UMAP, embedder, PageRank, layout reasoner, or compile on the client (§2.1).
6. **All motion is interruptible eased tween on one rAF budget.** No layout thrash; no restart-from-scratch on a mid-flight retarget (`liveness.md`).
7. **The two canvases share no coordinate system.** Coupling is only through the three membranes, only in the directions §6.6.2 permits.
8. **Faithful telemetry is not optional.** Anything the user can see or do emits telemetry the REPL can read; a render with no telemetry is a severance (§18.1).

---

## §5 — Activities, Sequences, Data, Results (where they live)

This orientation doc does not enumerate gestures; each surface doc does. The complete gesture catalogue is §14.2 (mirrored by `gesture_gateway.md`); the complete sequence set is §17 (each surface doc carries its own); the complete frame roster is §10.1 (`frame_bus.md`); the complete mirror-field roster is §10.5 (`workspace_store.md`).

---

## §6 — REPL Mirroring

The whole frontend is, in the Symbolic register's terms, *one half of a mirror*: every gesture and every render route through the two seams (§3), and the seams emit telemetry. `repl_mirroring.md` is the cross-cutting account; each surface doc's §9 carries its slice. The architectural guarantee: because there is no frontend-only state transition, the REPL can reconstruct the full Imaginary + Real state from frames + telemetry alone.

---

## §7 — Theme

The architecture itself has no surface, but it dictates the theme's scope: the **Imaginary canvas and all chrome are steel-over-black** (`theme.md`), and the **Real canvas is black ground with HSV/imagery nodes** — the one exception. The tier mapping makes the exception precise: the *Organs* tier's Projector is the only object that renders the exception zone; every other object (Spine has no surface; Cell, the Editor, the Membranes) renders steel-on-black.

---

## §8 — References

- [`../FRONTEND_REDESIGN.md`](../FRONTEND_REDESIGN.md) — the deep object treatment this doc summarises.
- `DOMAIN_MODEL.md`: §1.1/§1.5 (registers), §2 (principles), §6.6.2 (canvas separation), §10 (streaming/lifecycle), §14 (REPL).
- Every other doc in this suite.
