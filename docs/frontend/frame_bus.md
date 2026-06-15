# FrameBus — The Single Inbound Seam

> **Status: realised (cp/*.js); greenfield object form in `FRONTEND_REDESIGN.md` §3.2.** The single inbound WebSocket seam is carried by `chunk_projector.js` + `cp/scanner.js` (the WS connect + frame dispatch: `chunk_added`, `chunk_instances_partial`, `umap_canonical`, `concept_changed`, `ui_state_changed`, `spine_delta`, `done`/`error`, with `?resume=<seq>` replay). Monotone per-workspace `frame_seq`. The REPL's `_WSDrain` mirrors the same stream. Verified by `spine-delta-emits`, `telemetry-roundtrip`, `session-reconcile-empty`.

---

## §1 — Identity

`FrameBus` owns the single long-lived workspace WebSocket and is the *only* path by which canonical truth enters the frontend. It receives monotone-sequenced frames (§10.1), enforces ordering and lossy backpressure (§2.4), de-duplicates on reconnect, and translates each frame into exactly one `WorkspaceStore` transaction. No view, canvas, or membrane opens its own socket; they all read the store that FrameBus feeds.

---

## §2 — Structure

**Owns (transient):**
- `socket` — one `WebSocket` to `/api/ws/workspace/{workspace_id}?resume=<seq>` (§10.1).
- `seq` — last applied `frame_seq` high-water mark (mirrored to the store's `seq` slice).
- `reorderBuffer` — small heap of out-of-order frames awaiting their predecessor.
- `replayWindow` — the last-5-minutes buffer reference used to drop already-applied frames after a resume.
- `state` — `connecting | open | draining | reconnecting | closed`.

**Reads:** nothing from the store (it writes only). **Writes:** every store slice, via `WorkspaceStore.applyFrame(frame)` — the single inbound write path in the whole frontend.

---

## §3 — Composition

| Peer | Relationship |
|---|---|
| `WorkspaceStore` (`workspace_store.md`) | FrameBus is its only writer; one frame → one store transaction |
| `GestureGateway` (`gesture_gateway.md`) | The loop's other seam; a gesture's effect returns here as a frame |
| Backend WS router (§10.1, `ws_frames.py`) | The producer of frames; FrameBus is the consumer |
| Every view | Downstream of the store; never talks to FrameBus directly |

---

## §4 — Behaviours

1. **Monotonicity (§2.4).** Frames apply in `frame_seq` order. A frame with `seq > expected+1` is held in `reorderBuffer` until its predecessor lands or the resume window closes; a frame with `seq ≤ high-water` is dropped (already applied).
2. **One frame, one transaction.** A frame never produces a partial store update; the store mutation is atomic so views never observe a half-applied frame.
3. **Lossy backpressure (§2.4) — keep structure, drop progress.** Under flood, drop oldest `chunks_partial`/progress frames; **always keep** `done`, `error`, the *latest* `umap_canonical`, the *latest* `concept_index_update`, *all* `concept_changed`, *all* `evolution_diff`. This guarantees the editor never starves of structural truth during a fast scan (`liveness.md` §3).
4. **Resume, not reload (§2.4).** On disconnect, reconnect with `?resume=<high-water>`; the backend replays the last five minutes; FrameBus de-dupes against the high-water mark.
5. **Dual-routing guard (§18.1).** FrameBus subscribes to the *workspace* WS, never a per-snapshot socket. `chunk_added` and `umap_canonical` must arrive here; a scan whose chunks reach only a snapshot socket is the §18.1 severance and is observable as a gap between the streaming chunk count and the `done` frame.
6. **No interpretation.** FrameBus does not render, does not derive, does not compute; it routes. All meaning is in the store and the views.

---

## §5 — Activities

FrameBus has no user gestures; it is driven by the wire. Its "activities" are lifecycle transitions:

| Activity | Trigger | Effect |
|---|---|---|
| Connect | Workspace open / tab focus | Open socket with `?resume=<seq>` (0 on first connect) |
| Apply | Frame arrives in order | One `WorkspaceStore` transaction |
| Buffer | Frame arrives out of order | Hold in `reorderBuffer` |
| Shed | Backpressure threshold crossed | Drop oldest progress frames per §4.3 |
| Reconnect | Socket drops | Re-open with resume; de-dupe replay |
| Reset | `purge_workspace` frame | Apply the consolidated clear, then continue |

---

## §6 — Sequences

### §6.1 Normal frame application
```
frame arrives → check seq
   seq == expected      → applyFrame(frame); seq = frame.seq; drain reorderBuffer
   seq >  expected       → reorderBuffer.push(frame)
   seq <= high-water     → drop (duplicate)
```

### §6.2 Reconnect + resume
```
socket closes → state=reconnecting
   reopen ?resume=<high-water>
   backend replays last 5 min of frames
   each replayed frame: seq <= high-water → drop;  else applyFrame
   state=open; views patch from the delta (Reconciler, liveness.md §1)
```

### §6.3 Backpressure shed
```
inbound rate > budget → state=draining
   keep queue: [done, error, latest umap_canonical, latest concept_index_update,
                all concept_changed, all evolution_diff]
   drop: oldest chunks_partial / progress frames
   rate normalises → state=open
```

---

## §7 — Data: the complete inbound frame roster (§10.1)

Every frame type FrameBus handles and the store slice it writes:

| Frame | Source | Store effect | Consumed by |
|---|---|---|---|
| `chunk_added` / `chunk_replaced` / `chunk_removed` | Scanner / chunk lifecycle | `chunks` slice add/replace/remove | `projector.md`, `scan_streaming.md` |
| `chunks_partial` / `instances_indexed` | Scanner | `chunks` progress (sheddable) | `scan_streaming.md` |
| `spine_delta` | Retrieval spine (`routes.py`) | `chunks` visibility (scroll-viewport extrude/hide) | `retrieval_and_sidebar.md`, `projector.md` — handled in `cp/search.js` |
| `umap_canonical` | Layout Service at refit (§9.3) | `layout` slice (6-vectors + per-URL roots) | `projector.md` (tween) |
| `concept_changed` | Lifecycle dispatcher (§10.2) | `concepts` / `edges` slices | `concept_view.md`, `editor.md` |
| `concept_index_update` | Concept Index Service (§10.4) | `index` slice (nomic + pagerank + similar_to) | `halo.md`, autocomplete |
| `agent_token` | Agent transformer (§12.1) | `tokens` ring-buffer | `agent_and_rollout.md` |
| `evolution_diff` | Evolution log (§11.4) | (no frontend view yet — REPL-consumed only) | `repl_mirroring.md` (the realized frontend has no `evolution_diff` handler; the dedicated history view is planned) |
| `ui_state_changed` | UI State Service (§10.5) | `ui` slice (full snapshot) | every view (pins, latch, halo, viewport, **rollout**, …) — handled in `cp/concept_graph.js` |
| rollout (paused/resumed) | Rollout coordinator (§7.5) | `ui.rollout_state` | realized as `ui_state_changed` with `kind ∈ {rollout_paused, rollout_resumed, rollout}` — **NOT** a separate top-level frame (see `ws_frames.md` §1.4); consumed via the `ui_state_changed` handler |
| `purge_workspace` | Purge handler (§6.5) | **resets every slice in one transaction** | every view (`workspace_store.md` §4) |
| `cascade_status` | Cascade scheduler (§7.4) | `cascade` slice | `repl_mirroring.md` |
| `done` / `error` | Various | per-action terminator / `--accent-error` envelope | the awaiting gesture (`gesture_gateway.md`) |

---

## §8 — Results

FrameBus produces no pixels; its result is a correctly-ordered, de-duplicated, backpressure-shaped stream of `WorkspaceStore` transactions. Its observable correctness is: (a) the store's `seq` advances monotonically; (b) no view ever sees an out-of-order or duplicate effect; (c) a fast scan never blocks structural frames.

---

## §9 — REPL Mirroring

FrameBus is the frontend end of the same wire the REPL's `sim_frontend.py` reads (§14). The Symbolic register's guarantee depends on FrameBus's fidelity: every frame the REPL emits as a verification (e.g. after a `web-scan` action) must arrive here in order, and every frame that arrives here is one the REPL could also observe. The `seq` high-water mark is the shared cursor that lets `?resume=<seq>` replay for both a reconnecting tab and a REPL re-attach.

---

## §10 — Theme

FrameBus has no surface and no theme application. (Its downstream store and views carry the steel-over-black theme; see their docs.)

---

## §11 — References

- `DOMAIN_MODEL.md`: §10.1 (frame roster), §2.4 (sequencing + backpressure + resume), §18.1 (severance).
- `code_constraints/ws_frames.md`, `code_constraints/streaming.md`.
- Peers: `workspace_store.md`, `gesture_gateway.md`, `repl_mirroring.md`.
