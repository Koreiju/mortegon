# Spec — Frontend / Spine (FrameBus · WorkspaceStore · GestureGateway)

> Deepens [`code_architecture/frontend/spine.md`](../../code_architecture/frontend/spine.md). Modules (greenfield object form): `fe/spine/{frame_bus,store,gateway}.ts`. Types mirror [`../types.md`](../types.md) (same field names). Constants: [`../constants.md`](../constants.md) §7/§8. The only network seam.
>
> **Realized form (cp/*.js).** This spec is the GREENFIELD object model (`fe/spine/*.ts`); the *realized* frontend is the `backend/static/js/cp/` mixin suite (the user's "update cp/ in place" pivot — there is no `fe/` tree). The three roles map to:
> - **WorkspaceStore** → `ChunkProjector` instance state in `chunk_projector.js` (`dataMap`, `nodeInstanceMap`, `initialNodeData`, `_pinnedPanels`, `chunkCollapseTarget/State`) + `cp/workspace.js` (per-workspace isolation) — see `frontend/workspace_store.md`.
> - **FrameBus** → the WS connect + frame dispatch in `chunk_projector.js` + `cp/scanner.js` (handles `chunk_*`/`umap_canonical`/`concept_changed`/`ui_state_changed`/`spine_delta`/`purge_workspace`) — see `frontend/frame_bus.md`.
> - **GestureGateway** → `cp/interaction.js::_mirrorUi(path, body)` (the single outbound seam) + per-view handlers in `cp/concept_graph.js`/`billboard.js`/`search.js` — see `frontend/gesture_gateway.md`.
> The §1–§3 algorithms below are the contract these realized modules honor (verified through the REPL by `route-coverage` + `action-registry-coverage` + the 82-scenario `full-smoke`); the `.ts` signatures are the design shape, not literal realized symbols.

---

## §1 — `WorkspaceStore`

```ts
type Slices = {
  concepts: Map<ConceptId, ConceptNode>; edges: Map<EdgeId, ConceptEdge>;
  index: Map<ConceptId, IndexSlot>; chunks: Map<ChunkId, Chunk>;
  layout: { per_chunk: Map<ChunkId, Vec6>; per_url: Map<string, UrlRoot> };
  ui: UIState; tokens: Map<ConceptId, string[]>; evolution: EditDiff[];
  cascade: Map<string, {fires:number;skips:number}>; seq: number;
};
class WorkspaceStore {
  subscribe<T>(selector: (s: Slices) => T): (next: T, prevKeyset: Set<string>) => void
  applyFrame(frame: Frame): void                      // ONLY FrameBus calls this
  read<K extends keyof Slices>(slice: K): Readonly<Slices[K]>
  overlay: { write(slice, key, value): void; clear(key): void }
}
```
- **`applyFrame`** — switch on `frame.type` (types.md §7); update exactly the affected slice(s); set `seq = frame.frame_seq`. Pure reducer — **no network, no side effects**. `purge_workspace` → reset all slices + `seq=0` in one transaction.
- **`read`** — merges `overlay` over canonical (overlay = optimistic echoes). An arriving frame for an echoed key supersedes the echo (frame wins; clear the overlay key).
- **Invariant** — canonical mutates **only** via `applyFrame` (assertion: no other writer, errors.md §3 frontend analogue). Subscriptions are **keyed** (return changed keyset) so `Reconciler` mutates minimally (pulse.md).

---

## §2 — `FrameBus`

```ts
class FrameBus { connect(workspace_id: WorkspaceId, resume_seq: number | null): void }
```
- **Algorithm:**
```
open WS /api/ws/workspace/{id}?resume=<resume_seq>
onmessage(frame):
   if frame.frame_seq != expected: buffer; reorder; apply contiguous prefix in order
   if queueDepth > WS_BACKPRESSURE_HIGHWATER: drop oldest sheddable (chunks_partial/progress);
        KEEP done|error|latest umap_canonical|latest concept_index_update|every concept_changed|every evolution_diff
   store.applyFrame(frame)                       # exactly one frame → one store transaction
onclose: reconnect with ?resume=<store.seq>      # replays ≤ WS_RESUME_WINDOW; else full re-sync (errors.md §2)
```
- **Post** — the store is always a prefix-consistent view; the **only** inbound write path.

---

## §3 — `GestureGateway`

```ts
class GestureGateway {
  send(g: { kind: GestureKind; args: object; idempotency_key: IdemKey; echo?: {slice; key; value} }): Promise<void>
  telemetry(kind: string, snapshot: object): void
}
```
- **`send` algorithm:** map `kind` → REST route (contracts.md §2) with an `idempotency_key` body field; if `echo`, `store.overlay.write(echo)` immediately (optimistic); `await` the route; on the matching frame / `done` → clear the echo (the frame already reconciled); on `error` → clear the echo + surface `--accent-error` (theme). 
- **`telemetry`** — batch render-settled UI snapshots, flush every `TELEMETRY_BATCH_MS` to `POST /api/ui/telemetry` — **off the critical path** (pulse.md never blocks on it).
- **Invariant (completeness, §14.4)** — `GestureKind` is a closed union; a kind with no route **cannot compile**. Every kind ↔ (route, frame, mirror field, REPL action, scenario).

---

## §4 — Excluded
The theme; the Symbolic-register "one socket" framing. Exact REST/WS shapes live in types.md §7 + contracts.md.
