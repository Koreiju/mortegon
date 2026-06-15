# Object: UIStateService

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §10.5 (UI State Service), §10.5.1 (mirror-field roster), §14.2 (gesture catalogue), §14.5 (in-place activity viewer), §1.5 (Symbolic register operationalised), §17.1.1 – §17.1.5 + §17.7 + §17.12 – §17.15 (sequence diagrams for every mirrored field).

**Status.** Realised — **all §10.5.1 roster fields are wired** in `backend/services/ui_state_service.py::UIState` with a setter + `/api/ui/*` route + REPL `ui-*` action each (route-coverage green): selected, hovered, hover_rect, stick_rect, pinned_billboards, pinned_collapsed, pin_chrome, billboard_url, url_collapsed, compile_expansions, halo_focus, halo_chain, latch_state, viewport_visible_rows, editing_field, autocomplete_state, **signal_stream**, and **rollout_state** (the last two completed this pass, alongside `field_path` on the signal-stream setters). `_snapshot_locked` deep-copies every field; `last_changed_at` / `last_change_kind` carry the diff metadata. Verified by `ui-roundtrip`, `signal-stream-roundtrip`, `rollout-roundtrip`, `pin-chrome-roundtrip`, `latch-toggle-roundtrip`, `autocomplete-state-roundtrip`, `editing-field` + full-smoke.

---

## §1 — What it is

The backend mirror of the frontend's UI state. Every gesture the user (or agent) fires that affects what the frontend is showing — pinning a panel, opening a halo, advancing a signal-stream signal, opening an edit field, clicking a halo phantom — flows through a setter on this service. Each setter writes the new state and broadcasts a `ui_state_changed` WebSocket frame so peer surfaces (other GUI tabs, the agent's perception card, the REPL's in-place activity viewer) re-sync.

The §1.5 framing makes UIStateService the **Symbolic register's operational core** — it is the layer that gives the REPL its faithful, real-time view of what the user is doing in the GUI. Without UIStateService the REPL would be blind to UI state and would only see backend mutations; with it, the REPL viewer can render a six-row dashboard mirroring the visible GUI in near-real-time.

---

## §2 — Shape

### §2.1 The UIState dataclass

```python
@dataclass
class UIState:
    # Identity / focal
    selected_id:        str | None
    hovered_id:         str | None
    last_hover_rect:    dict | None       # {top, left, width, height}
    last_stick_rect:    dict | None
    # Pinned panel set
    pinned_billboards:  list[str]         # ordered insertion = click sequence
    pinned_collapsed:   dict[str, bool]   # per-pinned-id collapsed flag
    pin_chrome:         dict[str, dict]   # per-pinned-id {top, left, width, height, minimised}
    billboard_url:      dict[str, str]    # pinned-id → source URL (for URL-collapse cascade)
    # URL state
    url_collapsed:      dict[str, bool]   # per-URL collapse flag
    # Compile state
    compile_expansions: dict[str, dict]   # central_id → {children: [...], expanded_at}
    # Halo state
    halo_focus:         dict | None       # {focal_card_id, candidates: [...], opened_at}
    halo_chain:         list[str]         # autoregressive walk through focals
    # Latch / collapse
    latch_state:        dict[str, str]    # card_id → "latched" | "unlatched"
    # Spine
    viewport_visible_rows: dict | None    # {ordered: [...], total: N, updated_at}
    # Edit + autocomplete
    editing_field:      dict | None       # {card_id, field_path, value_so_far, opened_at}
    autocomplete_state: dict | None       # {row_id, query, parent_card_id, candidates, opened_at}
    # Signal-stream display state (per-field iteration position)
    signal_stream:      dict[str, dict]   # "card_id::field_path" → {signal_index, signal_total, last_advanced_at}
    # Rollout state
    rollout_state:      dict | None       # {node_id, paused: bool, sample_idx} when active
    # Diff metadata
    last_changed_at:    float
    last_change_kind:   str
```

### §2.2 Setter methods

One setter per mirror field. Each setter is **idempotent on input** (same input → same state, but always broadcasts so peer surfaces can re-sync), **field-merge where applicable** (e.g., `set_pin_chrome` merges only the kwargs passed), and **broadcasts** `ui_state_changed` with the full snapshot.

| Setter | Mirror field | Sequence |
|---|---|---|
| `select(workspace_id, node_id)` | `selected_id` | (legacy) |
| `hover(workspace_id, node_id)` | `hovered_id` | (legacy) |
| `pin(workspace_id, node_id, *, collapsed, stick_rect)` | `pinned_billboards` + `pinned_collapsed` + `last_stick_rect` | §17.2 |
| `unpin(workspace_id, node_id)` | clears `pinned_billboards` + `pinned_collapsed` + `pin_chrome` for the id | §17.2 |
| `set_collapsed(workspace_id, node_id, collapsed)` | `pinned_collapsed[id]` | (sticky-collapse contract) |
| `set_hover_rect(workspace_id, rect)` | `last_hover_rect` | §17.2 |
| `set_url_collapsed(workspace_id, url, collapsed)` | `url_collapsed[url]` + computes affected billboards | (Mortegon §5 cascade) |
| `register_billboard_url(workspace_id, billboard_id, url)` | `billboard_url[id]` | (Mortegon §5) |
| `compile_expand(workspace_id, central_id, children)` | `compile_expansions[central_id]` | §17.3 |
| `compile_collapse(workspace_id, central_id)` | clears `compile_expansions[central_id]` | §17.3 |
| `set_halo_focus(workspace_id, focal_card_id, candidates?)` | `halo_focus` | §17.7 |
| `clear_halo_focus(workspace_id)` | clears `halo_focus` | §17.7 |
| `push_halo_chain(workspace_id, focal_card_id)` | appends to `halo_chain` (consecutive-duplicate no-op) | (autoregressive halo) |
| `clear_halo_chain(workspace_id)` | clears `halo_chain` | (purge / explicit dismiss) |
| `set_pin_chrome(workspace_id, panel_id, *, top, left, width, height, minimised)` | `pin_chrome[panel_id]` (field-merge) | §17.12 |
| `set_latch(workspace_id, card_id, *, latched)` | `latch_state[card_id]` (toggle if `latched is None`) | §17.13 |
| `set_viewport_spine(workspace_id, ordered, total)` | `viewport_visible_rows` | §17.14 |
| `set_autocomplete(workspace_id, row_id, query, *, parent_card_id, candidates?)` | `autocomplete_state` | §17.15 |
| `clear_autocomplete(workspace_id)` | clears `autocomplete_state` | §17.15 |
| `set_editing_field(workspace_id, card_id, field_path, *, value_so_far)` | `editing_field` (preserves `opened_at` on same-field updates) | (click-to-edit) |
| `clear_editing_field(workspace_id)` | clears `editing_field` | (commit / blur) |
| `set_signal_stream(workspace_id, card_id, field_path, signal_index)` | `signal_stream["card_id::field_path"]` | §17.1.2 |
| `clear_signal_stream(workspace_id, card_id, field_path)` | removes the signal_stream slot | (iteration done / purge) |

### §2.3 Read methods

| Method | Purpose |
|---|---|
| `get_state(workspace_id)` | Return the full snapshot (for REST `/api/ui/state` GET) |
| `view_state(workspace_id, node_id)` | One-shot `{state, collapsed, pinned, hovered}` per the §UnifiedNodeView model |
| `get_hidden_billboards(workspace_id)` | List of pinned billboards currently hidden by URL-collapse cascade |
| `list_workspaces()` | All workspaces with active state |

---

## §3 — Lifecycle

### §3.1 Setter flow

Every setter:

1. Acquires the per-workspace lock.
2. Mutates the field on the in-memory `UIState` instance.
3. Updates `last_changed_at` and `last_change_kind`.
4. Snapshots the state.
5. Releases the lock.
6. Calls `_emit(kind, workspace_id, snapshot)` to broadcast.

The `_emit` call passes through `broadcast(0, frame)` where `broadcast` is the `_ws_push` callable wired at service construction. The frame is `{type: "ui_state_changed", workspace_id, kind, state: snapshot.to_dict()}`. The kind disambiguates which setter fired so peer surfaces can react selectively (the REPL viewer's `editing` row only needs to refresh on `kind="edit_open"` / `"edit_close"`).

### §3.2 Purge

`clear_workspace(workspace_id)` is called by the purge handler. It pops the workspace's UIState entry, then emits `_emit("clear", workspace_id, UIState())` so peer surfaces reset. All field-level state is cleared atomically.

### §3.3 Idempotency

Setters broadcast even on no-op calls (same input → same state). This is intentional — peer surfaces that missed prior broadcasts can re-sync on any subsequent call. The REPL drain reads every broadcast; the viewer's last-write-wins state machine handles redundant updates without divergence.

### §3.4 Concurrency

The per-workspace lock serialises setter calls within a workspace. Cross-workspace calls are independent. The broadcast is best-effort; broadcast failures do not propagate to the setter caller (the caller's mutation always succeeds locally even if the WS broadcast queue is dead).

---

## §4 — Persistence

UIStateService is **in-memory only**. State does not survive backend restart; the workspace state must be re-established by the frontend (on reconnect, the frontend re-posts its current state via the appropriate setters). The viewer's REST poll on `/api/ui/state` is the reconcile path for cases where the WS broadcast was missed.

The non-persistence is deliberate — UI state is transient by nature; persisting it would require complex stale-state cleanup on backend restart that adds no value.

---

## §5 — Peer interactions

| Peer | Interaction |
|---|---|
| [`ConceptLifecycle.md`](ConceptLifecycle.md) | Receives `concept_changed` broadcasts; some setters fire on `concept_changed` events to keep mirrors in sync |
| [`RolloutCoordinator.md`](RolloutCoordinator.md) | Calls `set_signal_stream` on every signal advance |
| [`AgentRuntime.md`](AgentRuntime.md) | Agent perception card reads `get_state` to know what the user is attending to (the active halo focal, the visible signal stream, the pinned panels) |
| [`ApparitionService.md`](ApparitionService.md) | On `set_halo_focus`, ApparitionService's `surface_for_projector` may be invoked to populate the candidates field |
| Frontend (`telemetry.js`, `concept_graph.js`, `billboard.js`, `halo.js`) | Frontend POSTs to the setters; reads the broadcasts; renders accordingly |
| [`sim_frontend.py` (REPL)](../code_constraints/repl_actions.md) | Every REPL `ui-*` action calls a setter; the in-place activity viewer reads broadcasts |

---

## §6 — Cross-references

- Feature touchpoints — every Imaginary-register feature has a mirror field here: [`features/click_and_stick.md`](../features/click_and_stick.md), [`features/click_to_edit.md`](../features/click_to_edit.md), [`features/halo_retrieval.md`](../features/halo_retrieval.md), [`features/autoregressive_halo.md`](../features/autoregressive_halo.md), [`features/signal_stream.md`](../features/signal_stream.md), [`features/in_place_activity_viewer.md`](../features/in_place_activity_viewer.md), etc.
- Code constraints — [`api_routes.md`](../code_constraints/api_routes.md) (`/api/ui/*` endpoint shapes), [`ws_frames.md`](../code_constraints/ws_frames.md) (`ui_state_changed` frame schema), [`repl_actions.md`](../code_constraints/repl_actions.md) (REPL action coverage of every setter).
- Sequence reference — DOMAIN_MODEL §17.1.2 (signal-stream), §17.2 (click-and-stick), §17.7 (halo), §17.12 (pin chrome), §17.13 (latch), §17.14 (viewport spine), §17.15 (autocomplete).

---

## §7 — Anti-patterns (must-not)

| Anti-pattern | Why forbidden | Guard |
|---|---|---|
| Persisting UI state to disk | UI state is transient; persistence introduces stale-state-on-restart hazards | Service is in-memory only; reconcile is via REST poll + frontend re-post |
| Skipping the broadcast on a no-op setter call | Peer surfaces lose the chance to re-sync; the §14 two-way feedback breaks | Setters always broadcast |
| Letting two setters race without the per-workspace lock | State divergence between concurrent gestures | Per-workspace lock serialises within workspace |
| Letting a broadcast failure propagate to the setter caller | Broadcasts are best-effort; the mutation always succeeds locally | The `_emit` swallows exceptions |
| Carrying agent-specific state in UIState | UIState is the user-and-agent-shared mirror; agent-specific state belongs in the agent body subgraph | Agent body cards carry their own state via ConceptNode data fields |
| Mutating `halo_chain` outside `push_halo_chain` / `clear_halo_chain` | The consecutive-duplicate guard belongs in the setter | All chain mutations go through the two setters |
| Letting `signal_stream` slots accumulate without bounds | A long-running workspace with many fields iterated over would grow the map indefinitely | Slots are GC'd on workspace purge; explicit `clear_signal_stream` is called when iteration completes |
| Treating `last_change_kind` as authoritative for sequencing | The `frame_seq` on the WS broadcast is authoritative; `last_change_kind` is informational | Peer surfaces order updates by `frame_seq` |
