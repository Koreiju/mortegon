# Object: RolloutCoordinator (Backend Service)

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §7.5 (play/pause iterated rollout), §17.1.2 (signal-stream advance sequence), §4.6.1 (signal-stream constraint), §7.6 (recursive chunking + diff-consistent state), §12.2.1 (recursion-over-iteration integration scheme), §7.8 (reservoir readout); review clarifications §O.9 (lazy reveal-as-it-walks), §O.11 (one cycling readout, not fan-out), §O.13 (cascade recomputes, never auto-unfolds), §O.14 (chunks live in 3D; 2D references them).

**Status.** Realised (core) — `backend/services/rollout_coordinator.py::RolloutCoordinator` drives the iteration over the `UIStateService` `signal_stream` + new `rollout_state` mirror fields (§2.4). `play` / `pause` / `step` / `reset` are wired at `POST /api/rollout/{play,pause,step}` + `POST /api/ui/signal_reset` (+ the `rollout-{play,pause,step}` / `ui-signal-reset` REPL actions), and `advance` is `POST /api/ui/signal_advance`. `field_path` threads through so a `pattern_map`'s `pattern_hash` stream and a `url_set`'s `url` stream are distinguishable. Verified by the `rollout-roundtrip` scenario (play→`paused=False`, step×2→`idx=2`, pause holds, reset→`idx=0`) in full-smoke. The per-interval auto-advance *cadence* is frontend/REPL-driven (the backend owns state + the advance primitive — appropriate for a single-user on-device app), and the **§3.1-step-4 per-sample cascade re-fire is realised frontend-side**: `concept_graph.js::_stepSample` swaps the card's value to the active sample and calls `_scheduleConceptSync` → PATCH → `apply_update_lifecycle`, so downstream `{ref}` consumers recompute on each step. The **§3.3 diff-consistent sample-boundary rollback is wired**: every `advance` (incl. via `step`) records a `sample_boundary` EvolutionLog diff (`target="rollout:<card_id>::<field_path>"`, `before/after` = `{signal_index, signal_total}`), and `EvolutionLog._apply_reverse` gained a `rollout:` branch that **re-seats the signal-stream cursor** on rollback — so reverting a sample boundary restores the iteration index alongside the data. Verified live: 2 steps → idx 2, rollback the last boundary → `signal_index` re-seated to 1 (`action: signal-reseated`); full-smoke 70/70 (incl. `evolution-rollback` + `rollout-roundtrip`). Frontend surface: [`../frontend/agent_and_rollout.md`](../frontend/agent_and_rollout.md) (play/pause control) + [`../frontend/field_tree.md`](../frontend/field_tree.md) (per-signal render).

---

## §1 — What it is

The **iteration driver** of the workspace. Where `ConceptLifecycle` is the *mutation* funnel and `ConceptualCompute` is the *per-node compile* primitive, `RolloutCoordinator` is the **outer loop**: it advances the *signal index* of any iterable-bearing field one element at a time, fires the per-sample compile re-fire downstream, and emits the `rollout_*` / `signal_advance` frames the GUI and REPL read. It is the operational realisation of the **"iteration" half of the recursion-over-iteration integration scheme** (§12.2.1) — recursion is the cascade walking the graph topology per sample; iteration is this coordinator stepping the sample bank.

In the §7.8 reservoir framing, the RolloutCoordinator is what **drives the reservoir over successive samples**: each step feeds the next perception (the next chunk signal) into the typed graph, and the generative readout re-renders for that sample. In the §1.5 register framing it sits in the **Symbolic↔Imaginary seam** — every advance is a `ui_state_changed (signal_advance)` the REPL reads (§14) and a re-render the editor shows.

A **full rollout** runs this advance out to the graph's **readout nodes** — the final-most recursive unfolded nodes forming the **perimeter / spherical hypersurface** (§7.8.2). Subgraphs with **differing rollout path lengths** — and recurrent maps that fold the perimeter back onto hidden-state nodes — settle at different times, so perimeter readouts are emitted **asynchronously**: each settled readout is a per-node **delta** to the projector stream (§7.8.3, §6.6.4), not a barrier-synchronised batch. The `rollout_*` frames therefore carry **no global step barrier** across subgraphs, and out-of-order readout arrival is expected (§10.2 sequencing; P.6 / P.7).

It owns **no truth** that survives a reload beyond the iteration index (a UI-state mirror field); the sample bank itself lives where the data lives — **chunk content in 3D** (§O.14), scalar iterables in the node's `data`.

---

## §2 — Shape

### §2.1 Per-rollout state

```python
@dataclass
class RolloutState:
    rollout_id:    str
    workspace_id:  str
    card_id:       str            # the node whose field is being iterated
    field_path:    str            # dotted path of the iterable field (e.g. "dom.chunk")
    signal_index:  int            # the currently-visible element (the "signal", §4.6.1)
    signal_total:  int            # cardinality of the iterable
    paused:        bool
    current_node_id: str | None   # node the user paused on (edit context, §7.5)
    sample_source: str            # "chunk_3d" (sampled per-instance from the 3D env) | "halo" (halo-retrieval selection, §O.18) | "scalar" (value in data) | "concept_ids"
    readout_card_id: str | None   # the single cycling readout node (§O.11), if a downstream link consumes the iterable
    interval_ms:   int = 1000     # auto-advance period when playing
    created_at:    str
```

The state is **transient / UI-mirror**, not Kuzu-persisted (§5). One `RolloutState` per `(card_id, field_path)`; the keyed set is the source for the `signal_stream` mirror (§10.5).

### §2.2 API surface

```python
class RolloutCoordinator:
    def play(self, card_id, field_path, *, interval_ms=1000) -> RolloutState   # POST /api/rollout/play
    def pause(self, *, node_id=None) -> RolloutState                            # POST /api/rollout/pause
    def step(self, card_id, field_path) -> RolloutState                         # POST /api/rollout/step
    def advance(self, card_id, field_path, *, signal_index=None) -> RolloutState# POST /api/ui/signal_advance
    def reset(self, card_id, field_path) -> RolloutState                        # POST /api/ui/signal_reset
```

`advance` is the single-step primitive; `play` is `advance` on a timer; `step` is one `advance` then re-pause. The agent operates the rollout through the **same** surface (§12) — no agent-specific path.

### §2.3 WS frames emitted

| Frame | When | Carries |
|---|---|---|
| `rollout_resumed` | `play` | `{rollout_id, card_id, field_path}` |
| `rollout_paused` | `pause` / `step` settle | `{rollout_id, sample_idx, current_node_id}` |
| `ui_state_changed (kind=signal_advance)` | every `advance` | `{card_id, field_path, signal_index, signal_total}` |

### §2.4 Mirror fields owned (§10.5)

- `signal_stream` : `{ "card_id::field_path" → {signal_index, total} }`
- `rollout_state` : `{node_id, paused, sample_idx} | null`

These are the REPL-observable surface (`agent_and_rollout.md` §9; `repl_mirroring.md`).

---

## §3 — Lifecycle

### §3.1 The advance step (the core)

```
advance(card_id, field_path):
  1. s = state[card_id::field_path]; s.signal_index = (given) or s.signal_index + 1
  2. resolve the new signal element and RENDER ITS CONTENT per-instance (§O.14 corrected — content is rendered for the current sample, not merely referenced):
        sample_source == "chunk_3d"   → sample the next-up chunk from the 3D env per-instance; render its structured-field content
        sample_source == "halo"       → take the next-up node from the halo retrieval-similarity queue (§O.18); render its content
                                         (deleting a halo result advances to the next-most-similar, dynamic re-render)
        sample_source == "scalar"     → the element is a value in the node's data (e.g. a URL string)
        sample_source == "concept_ids"→ the element is a node id (Database.concept batch); render its rank-1 KG
     (The full iterable distribution still lives in 3D; only the CURRENT instance is rendered, §4.6.1.)
  3. UIStateService.set_signal_stream(card_id, field_path, signal_index, signal_total)  → ui_state_changed
  4. cascade re-fire PER SIGNAL (§7.4): ConceptualCompute.compile on the affected card using the new signal as the
     live value; downstream cards consuming it via {ref} recompute (recursion-over-iteration, §12.2.1)
  5. if a downstream link consumes the iterable, its output renders in the SINGLE readout_card_id (§O.11) —
     never one node per sample; per-sample outputs accumulate as the full distribution in 3D (§O.7/§O.14)
  6. drive 3D focus (§O.6): the corresponding 3D chunk flies/highlights (one-way 2D→3D); the projector keeps the full set
  7. the editor swaps ONLY the current signal's print form in place (§4.6.1); suppressed elements stay referenced
```

### §3.2 Play / pause / step / resume (§7.5)

- **Play** — `advance` on `interval_ms` until paused or `signal_index == signal_total − 1`.
- **Pause** — halt at the current sample; the editor reveals edit affordances (plus-signs, name editable) on `current_node_id`. Because compile is **lazy reveal-as-it-walks** (§O.9), Pause freezes at the *walk frontier* — the nodes revealed so far stay visible at their rank-1 depth (§O.13: the cascade recomputes values but does **not** auto-unfold hidden `{ref}`s).
- **Edit while paused** — a `concept-edit-*` / `field-tree-*` mutation on the paused node goes through `ConceptLifecycle`; it does **not** advance the iteration.
- **Resume** — the next sample uses the edited node's new content.

### §3.3 Diff-consistent rollback (§7.6)

The evolution log (§11.4) records every **sample boundary** as the rollout advances, so a rollback (§2.6) restores both the data state *and* the iteration index together. Rolling back to an early sample **re-localises the entire downstream context** (§8D.9): the coordinator re-seats `signal_index`, and the cascade re-fires from there over the generalised-forward-truncated bank.

### §3.4 Termination

A rollout ends when the iterable is exhausted, when `reset` returns it to 0, or when the owning card is deleted (the `RolloutState` is dropped; `signal_stream[card_id::field_path]` cleared).

---

## §4 — Peer interactions

| Peer | Relationship |
|---|---|
| [`UIStateService`](UIStateService.md) | owns the `signal_stream` + `rollout_state` mirror fields this service sets; broadcasts `ui_state_changed` |
| [`ConceptualCompute`](ConceptualCompute.md) | the per-sample compile re-fire on each advance (§3.1 step 4) |
| [`ConceptLifecycle`](ConceptLifecycle.md) | edits-while-paused and compile write-backs funnel through it; sample boundaries become `EvolutionLog` diffs |
| [`LayoutService`](LayoutService.md) | supplies the 3D-resident chunk set the `chunk_refs` source references (§O.14); the advance drives 3D focus (§O.6) |
| [`ApparitionService`](ApparitionService.md) / [`Halo`](Halo.md) | a per-sample focal can open a halo; the autoregressive walk composes with iteration |
| `AgentRuntime` (planned) | the agent's tick operates the rollout through the same API (§12.2.1 outer loop) |
| Frontend [`agent_and_rollout.md`](../frontend/agent_and_rollout.md) | the play/pause control (top-right of the 2D editor, M.11) binds to `play`/`pause`/`step` |
| Frontend [`field_tree.md`](../frontend/field_tree.md) | renders only the current signal (§4.6.1); the suppressed elements stay referenced |
| Frontend [`pattern_map_and_url_set.md`](../frontend/pattern_map_and_url_set.md) | `pattern_hash` iteration and `{urls_panel}` per-URL iteration are both this coordinator |

---

## §5 — Persistence

- **Iteration index** — UI-mirror state (`signal_stream`), persisted only as far as the §10.5 mirror is (per-workspace snapshot for resume); not a Kuzu record.
- **Sample bank** — the full iterable distribution lives in 3D (§O.14); the **current instance's content is rendered per-instance** in 2D (not merely referenced — §O.14 corrected), sourced by 3D-env sampling **or** halo-retrieval selection (§O.18). Scalar iterables live in the node's `data` (§4.6.1); concept-id batches resolve against the live edge table. Only the current instance is materialised in the panel; the rest stay queued.
- **Sample boundaries** — appended to the `EvolutionLog` (§11.4) so diff-consistent rollback restores data + index together (§3.3).

---

## §6 — Anti-patterns

| Anti-pattern | Why forbidden | Guard |
|---|---|---|
| Rendering the full iterable in the panel | §18.24 / §4.6.1 — one signal visible at a time | `field_tree.md` renders `signal_index` only; the rest stay referenced |
| Fan-out: one output node per sample | §O.11 — per-sample outputs accumulate in 3D, the 2D shows one cycling readout | `readout_card_id` is a single node; per-sample results project to 3D (§O.7) |
| Auto-unfolding hidden `{ref}`s on cascade re-fire | §O.13 / §18.33 — the cascade recomputes values, never reveals; rank-1 minimalism | advance fires compile (values) but never `ui-node-expand` |
| Materialising the **whole** iterable's content in the 2D panel at once | §18.24 / §4.6.1 — only the *current* instance renders (per-instance from the queue, §O.14); the full distribution lives in 3D | the panel renders `signal_index` only; deleting a halo result advances the queue (§O.18) |
| Parallel-firing `{urls_panel}` instead of per-URL signal-stream | §18.30 / §17.1.4 | one `advance` per URL; never a bulk concatenated scan |
| Advancing without a per-sample cascade re-fire | breaks recursion-over-iteration (§12.2.1) — downstream wouldn't see the new signal | step 4 of §3.1 is mandatory |

---

## §7 — Cross-references

- Domain: §7.5, §7.6, §4.6.1, §12.2.1, §7.8, §17.1.2; review §O.9 / §O.11 / §O.13 / §O.14.
- Features: [`../features/signal_stream.md`](../features/signal_stream.md) (the user-visible constraint this drives).
- Frontend suite: [`../frontend/agent_and_rollout.md`](../frontend/agent_and_rollout.md), [`../frontend/field_tree.md`](../frontend/field_tree.md), [`../frontend/pattern_map_and_url_set.md`](../frontend/pattern_map_and_url_set.md), [`../frontend/scan_streaming.md`](../frontend/scan_streaming.md).
- Code constraints: [`../code_constraints/frontend_rendering.md`](../code_constraints/frontend_rendering.md) §1.14 (signal-stream render).
- Peers: [`UIStateService.md`](UIStateService.md), [`ConceptualCompute.md`](ConceptualCompute.md) (planned), [`ConceptLifecycle.md`](ConceptLifecycle.md), [`LayoutService.md`](LayoutService.md).
