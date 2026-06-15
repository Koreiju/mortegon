# Frontend — Spine (FrameBus · WorkspaceStore · GestureGateway)

> **Owns:** the single inbound seam, the normalized source of truth, the single outbound seam. Modules: `fe/spine/frame_bus.ts`, `store.ts`, `gateway.ts`. Design: `FRONTEND_REDESIGN.md` §4 + `frontend/{frame_bus,workspace_store,gesture_gateway}.md`. Realises `code_constraints/frontend_rendering.md`. Wire shapes: [`../contracts.md`](../contracts.md).

---

## §1 — Responsibility

The Spine is the only place the frontend touches the network. **Truth arrives** on one WebSocket → `FrameBus` → `WorkspaceStore`. **Intent leaves** through `GestureGateway` REST. No view opens its own socket or fetch; no view writes canonical state. This is the architectural invariant the whole frontend rests on.

---

## §2 — Public Surface

```ts
// store.ts
WorkspaceStore.subscribe(selector): (next, prevKeyset) => void   // keyed for reconciliation
WorkspaceStore.applyFrame(frame): void                            // ONLY FrameBus calls this
WorkspaceStore.overlay.write(slice, key, value) / clear(key)      // optimistic echo (separate slice)
WorkspaceStore.read(slice): ReadonlyMap                           // merges overlay over canonical

// frame_bus.ts
FrameBus.connect(workspace_id, resume_seq): void

// gateway.ts
GestureGateway.send({kind, args, idempotency_key, echo?}): Promise<void>   // kind = a contracts.md §2 row
GestureGateway.telemetry(kind, snapshot): void                              // batched → /api/ui/telemetry
```

---

## §3 — Internal Logic

### §3.1 WorkspaceStore — the normalized mirror
Holds `Map`-keyed slices (`concepts, edges, index, chunks, layout, ui, tokens, evolution, cascade, seq`) — the shapes in [`../data_schemas.md`](../data_schemas.md). **Canonical mutates only from frames.** Reads merge a separate `overlay` slice (optimistic echo) over canonical; an arriving frame for the same key supersedes its echo (no merge conflict — the frame wins). `purge_workspace` resets every slice + `seq` in one transaction (one paint).

### §3.2 FrameBus — the one inbound seam
```
connect(ws_id, resume_seq):
   open WS /api/ws/workspace/{ws_id}?resume=<resume_seq>
   on frame:
     buffer if frame_seq out-of-order; apply in monotone order
     backpressure: if behind high-water, SHED oldest chunks_partial/progress;
        ALWAYS keep done, error, latest umap_canonical, latest concept_index_update, every concept_changed, every evolution_diff
     store.applyFrame(frame)        # exactly one frame → one store transaction
   on reconnect: reconnect with ?resume=<last_seq> (replays last 5 min)
```
The **only** inbound write path to the store.

### §3.3 GestureGateway — the one outbound seam
```
send({kind, args, key, echo}):
   route kind → REST (contracts.md §2) with body field idempotency_key: key
   if echo: store.overlay.write(echo.slice, echo.key, echo.value)     # optimistic
   await done/error → settle (clear echo) or rollback (clear echo, surface --accent-error)
```
A `kind` with **no catalogue row cannot be sent** — the completeness rule (§14.4): every gesture has (route, frame, mirror field, gateway kind, REPL action, scenario) or it isn't integrated. `telemetry` batches render-settled UI snapshots off the critical path (pulse.md).

---

## §4 — Dependencies

- **Calls:** the backend WS + REST (`contracts.md`); the backend lifecycle is reached only via `send`.
- **Called by:** every view subscribes to the store; every gesture handler calls `send`. FrameBus is started once at boot.

---

## §5 — Excluded

- The theme; the Symbolic-register framing of "the workspace as one socket." Only the data-flow mechanics are encoded.
