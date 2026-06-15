# WorkspaceStore — The Normalized Mirror

> **Status: realised (cp/*.js); greenfield object form in `FRONTEND_REDESIGN.md` §3.1.** The normalized-mirror role is carried by the `ChunkProjector` instance state in `chunk_projector.js` (`dataMap`, `initialNodeData`, `nodeInstanceMap`, `_pinnedPanels`, `chunkCollapseTarget/State`) + `cp/workspace.js` (workspaces, file-tree, per-workspace isolation) — populated from frames, never authoritative (the backend lifecycle is). Verified by `workspace-isolation`, `session-reconcile-empty`.

---

## §1 — Identity

`WorkspaceStore` holds a normalized, read-only-to-views projection of canonical backend state and emits *minimal diffs* when frames mutate it. It is the only cross-view state in the frontend. It is **never authoritative**: it only reflects what a frame told it (`FrameBus`, `frame_bus.md`). Views subscribe to slices and re-render on diff; they never write to it. A gesture's optimistic echo lives in a *separate overlay* slice (§5), so the canonical slices never carry un-confirmed state.

---

## §2 — Structure

**Owns:** the normalized slices below, keyed for O(1) reconciliation (`liveness.md` §1), plus a subscription registry. **Writers:** `FrameBus` only (canonical slices); `GestureGateway` only (the overlay slice). **Readers:** every view, via `subscribe(selector) → (next, prevKeyset) → unsubscribe`.

### §2.1 The slices

| Slice | Shape | Fed by | Anchor |
|---|---|---|---|
| `concepts` | `Map<concept_id, ConceptNode>` | `concept_changed` | §3.1 |
| `edges` | `Map<edge_id, ConceptEdge>` (hard links only) | `concept_changed` | §3.2.1 |
| `index` | `Map<concept_id, {nomic_ref, pagerank, similar_to:[{id,score}]}>` | `concept_index_update` | §10.4 |
| `chunks` | `Map<chunk_id:int, {url, layout6d:[x,y,z,h,s,v], image_url?, provenance}>` | `chunk_*` | §6.1, §9.4 |
| `layout` | `{ per_chunk: Map<id,6vec>, per_url: Map<url,{root,radius,locked,hidden,accessors}> }` | `umap_canonical` | §6.1, §11.1 |
| `ui` | the §10.5 mirror snapshot (§3 below) | `ui_state_changed` | §10.5 |
| `tokens` | `Map<agent_id, RingBuffer<token>>` | `agent_token` | §12.1 |
| `evolution` | `EditDiff[]` (bounded window) | `evolution_diff` | §11.4 |
| `cascade` | `Map<actor, {fires, last_skip}>` | `cascade_status` | §7.4 |
| `seq` | `int` high-water mark | every frame | §2.4 |

### §2.2 The ConceptNode shape (as the store holds it, §3.1)

```
ConceptNode { concept_id, name, description, data, rendering,
              linked_nodes_json, backing_pointer, pagerank,
              provenance, workspace_id, layout_xy, ui_state, type_hint,
              created_at, updated_at }
```
The store holds it verbatim as received; it computes nothing derived (no client-side embeddings, ranks, or layout — §2.1). `data` is an opaque string the `FieldTree` (`field_tree.md`) parses at render time; the store never parses it.

---

## §3 — The `ui` slice (the §10.5 mirror roster)

The store's `ui` slice is the local copy of the UI State Service mirror. Every field maps to a gesture (`gesture_gateway.md`) and a `watch-activity` row (`repl_mirroring.md`).

| `ui` field | Shape | Owner gesture |
|---|---|---|
| `selected_id` / `hovered_id` | `str \| null` | `ui-select` / `ui-hover` |
| `pinned_billboards` | `[node_id, …]` (ordered) | `ui-pin` / `ui-unpin` |
| `pinned_collapsed` | `{node_id → bool}` | `ui-collapse` |
| `last_hover_rect` / `last_stick_rect` | `{top,left,w,h} \| null` | `ui-hover-rect` / `ui-pin` |
| `pin_chrome` | `{panel_id → {top,left,width,height,minimised}}` | `ui-pin-move/-resize/-minimise/-close` |
| `latch_state` | `{card_id → "latched"\|"unlatched"}` | `ui-latch-toggle` |
| `url_collapsed` | `{url → bool}` | `ui-domain-toggle` |
| `hidden_urls` | `Set<url>` | `ui-url-visibility` |
| `compile_expansions` | `{central_id → {children:[…], expanded_at}}` | `ui-compile-expand/-collapse` |
| `node_fold_state` | `{card_id → {expanded_paths:[node_path,…]}}` | `ui-node-expand/-collapse` (§9.6.1, inline type-graph fold) |
| `halo_focus` | `{focal_card_id, candidates:[…], opened_at} \| null` | `ui-halo-focus/-clear` |
| `viewport_visible_rows` | `{ordered:[chunk_id,…], total}` | `ui-viewport-spine` |
| `autocomplete_state` | `{row_id, query, candidates, parent_card_id?} \| null` | `ui-autocomplete-open/-close` |
| `signal_stream` | `{ "card_id::field_path" → {signal_index, total} }` | `ui-signal-advance` |
| `rollout_state` | `{node_id, paused, sample_idx} \| null` | `rollout-play/-pause/-step` |
| `last_changed_at` / `last_change_kind` | diff metadata | (any setter) |

Setters are idempotent and broadcast on every call (even no-ops) so peer surfaces re-sync (§10.5). The store simply replaces its `ui` snapshot when `ui_state_changed` arrives.

---

## §4 — Behaviours

1. **Views never write canonical slices.** Only `FrameBus` does. A view that needs to change state sends a gesture (`gesture_gateway.md`); the change returns as a frame.
2. **Frame-driven only.** Canonical slices mutate solely from frames; the optimistic echo is in the overlay (§5).
3. **No derived authority.** `similar_to`, `pagerank`, `layout6d`, `rendering` are stored as received; the store recomputes none of them (§2.1, §1.4-FR.5).
4. **Atomic purge (§6.5, §18.4).** A `purge_workspace` frame resets every slice and the `seq` high-water mark in one transaction, so views clear in one paint and no stale URL/chunk/pin survives. This is the structural defeat of §18.4 — views read the store; the store was authoritatively emptied.
5. **Bounded windows.** `evolution` and `tokens` are bounded ring buffers; full history is server-side (§11.4) and fetched on demand by the history view.
6. **Keyed for reconciliation.** Every collection is a `Map` keyed by stable id so the Reconciler (`liveness.md` §1) can diff enter/update/exit without scanning.

---

## §5 — The optimistic-echo overlay

For latency-sensitive gestures (`gesture_gateway.md` §4), the gateway writes a provisional value into a *separate* `overlay` slice; reads merge `overlay` over canonical. When the authoritative frame arrives via `FrameBus`, it replaces the canonical value and the overlay entry is cleared. Because the echo is never written into canonical slices, there is **no merge conflict**: the canonical value simply wins on arrival. On gesture error (`done`/`error` frame), the overlay entry is rolled back; canonical was never touched.

---

## §6 — Activities & Sequences

The store has no gestures of its own; its sequences are write (from FrameBus) and read (subscriptions):

```
write:  FrameBus.applyFrame(frame) → store.applyFrame → mutate slice → notify subscribers(selector hit)
read:   view.subscribe(selector) → receive (next, prevKeyset) → Reconciler diff → render
echo:   gateway.echo(slice, key, value) → overlay[key]=value → notify → (later) frame supersedes → overlay.delete(key)
reset:  purge_workspace frame → clear all slices + seq → notify all → views render empty
```

---

## §7 — Data

**In:** the full frame roster (`frame_bus.md` §7). **Out:** slice diffs to subscribers; merged reads (canonical + overlay). The store neither sends REST nor receives it; that is the gateway's job.

---

## §8 — Results

The store's "result" is a coherent, normalized, subscribable mirror. Observable correctness: any two surfaces (two tabs, a tab + the REPL viewer) reading the same slice see identical state, because both derive from the same frames and the store holds no per-surface authority.

---

## §9 — REPL Mirroring

The `ui` slice (§3) is the local copy of the very mirror the REPL reads server-side (§10.5). This symmetry is the backbone of REPL parity: a REPL action sets a mirror field server-side → `ui_state_changed` → the store's `ui` slice updates → the view re-renders; and a frontend gesture sets the same field → same frame → the REPL viewer updates. Neither side holds a private copy that could diverge (`repl_mirroring.md`).

---

## §10 — Theme

The store has no surface. (It carries the `layout6d` HSV vectors that the Projector renders as the theme's exception zone, and the `ui` fields the chrome renders steel-on-black — but the rendering lives in the view docs.)

---

## §11 — References

- `DOMAIN_MODEL.md`: §3.1 (ConceptNode), §3.2.1 (edges/hard links), §10.5 / §10.5.1 (mirror roster), §6.5 (purge), §2.4 (seq).
- Object doc: [`../object_model/UIState.md`](../object_model/UIState.md).
- Peers: `frame_bus.md`, `gesture_gateway.md`, `repl_mirroring.md`.
