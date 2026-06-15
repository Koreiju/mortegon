# Feature: Signal-Stream Constraint Under Iteration

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §4.6.1 (signal-stream constraint), §1.2 verbatim (*"only the signal node that's being iterated on is visible in the 2D ui panel, so knowledge panel structures can have multiple values that are iterated over for each rollout of the computation graph with recursive firing"*), §7.5 (play/pause rollout), §17.1.2 (signal-stream advance sequence), §9.5.1 Database.concept.

**Status.** Realised (core). The `signal_stream` display state is a first-class `UIStateService` mirror field (keyed `card_id::field_path`, with `field_path` distinguishing a `pattern_map`'s `pattern_hash` stream from a `url_set`'s `url` stream), and the `RolloutCoordinator` (`backend/services/rollout_coordinator.py`) advances signal indices via `play`/`pause`/`step`/`advance`/`reset` (`/api/rollout/*` + `/api/ui/signal_*`). The 2D renders only the current signal (`concept_graph.js::_patternMapSignalPrint`/`_urlSetSignalPrint` + the ‹ i/N › steppers). Verified by `signal-stream-roundtrip`, `rollout-roundtrip`, and the `complex-interaction-walkthrough` composite in `full-smoke`. *(Reconciled to §O.14: chunk iterables are 3D-resident + referenced, the 2D renders the current signal; one cycling readout, not fan-out, §O.11.)*

---

## §1 — What the user sees

When a knowledge panel carries a field whose value is iterable — a list of chunks returned from `Database.concept(node_id_list)`, a `pattern_map` whose `pattern_hash` keys form an iteration sequence, a `{urls_panel}` reference where each URL fires a scan, or any other multi-valued field — the panel renders only *one* signal at a time. The other iterable elements stay in storage but are suppressed from the visible print rendering until the iteration advances — and for **chunk** iterables the full distribution lives **in 3D** (§O.14), the panel rendering the **current instance's content** per-instance from the queue (sampled from the 3D env or by halo-retrieval, §O.18); scalar iterables (e.g. a URL list) remain as values in the node's `data`. The play/pause stepper at the bottom of the panel advances the signal index per click; when the user pauses on a given signal, the cascade has re-fired downstream cards using that signal as the live value; the user can edit the paused signal's content and resume to use the edit on the next iteration.

The user reads one signal at a time because the panel's minimalism (the print-form tree of §4.6) would break under multi-iterable rendering — twelve `Database.concept` results stacked vertically would be unreadable. The signal-stream constraint is what lets unbounded-cardinality iterables coexist with the panel's syntactically-stripped print form.

---

## §2 — Cross-objects

| Object | Role |
|---|---|
| [`UIStateService`](../object_model/UIStateService.md) | `signal_stream` mirror field tracks `signal_index` per `(card_id, field_path)` |
| [`RolloutCoordinator`](../object_model/RolloutCoordinator.md) | Advances the signal index per play/pause step; fires cascade re-fire per signal |
| [`ConceptualCompute`](../object_model/ConceptualCompute.md) | Per-signal compile re-fire on advance |
| [`FieldTree`](../object_model/FieldTree.md) | Frontend renderer reads the signal index and renders only the current signal |
| [`Database`](../object_model/Database.md) | `Database.concept(list)` is the canonical iterable producer |
| [`PatternMap`](../object_model/PatternMap.md) | `pattern_map` iterates over `pattern_hash` keys |
| [`URLSetPanel`](../object_model/URLSetPanel.md) | `{urls_panel}` references iterate over URLs |

---

## §3 — Gestures

| Gesture | REPL action | Effect |
|---|---|---|
| Advance signal | `ui-signal-advance { card_id, field_path }` | Increment signal_index; cascade re-fires; panel re-renders new signal |
| Play | `rollout-play { card_id?, field_path? }` | Auto-advance per timer (configurable interval; default 1 s/step) |
| Pause | `rollout-pause { node_id? }` | Halt auto-advance at current signal |
| Step | `rollout-step` | Single signal advance, then re-pause |
| Reset | `ui-signal-reset { card_id, field_path }` | Return signal_index to 0 |

---

## §4 — State machine — signal advance

```
state: panel field X has iterable value with N signals; signal_index = i; signal i is visible
   │
gesture: ui-signal-advance OR rollout-play timer tick OR rollout-step
   │
   ▼
RolloutCoordinator increments signal_index → i+1 (modulo N if looping)
   │
   ▼
UIStateService.set_signal_stream(card_id, field_path, i+1)
   │
   ▼
WS ui_state_changed (kind=signal_advance) carries {card_id, field_path, signal_index, signal_total}
   │
   ▼
cascade scheduler enqueues compile re-fire for the field's card with the new visible signal as the live value
   │
   ▼  for each downstream card consuming the value via {var}:
   ▼  the cascade re-fires its compile with the new signal substituted
   │
   ▼
frontend swaps the visible print form in place — only signal i+1 renders; signals 0..i and i+2..N-1 remain in storage
   │
   ▼
REPL viewer signal-stream row: "card=<id>.<field> signal=i+1 of N — <print-form-preview-truncated>"
```

---

## §5 — WS frames + telemetry

| Frame | Carries |
|---|---|
| `ui_state_changed` (kind=signal_advance) | `signal_stream[card_id::field_path] = {signal_index, signal_total, last_advanced_at}` |
| `concept_changed` (cascade re-fire) | The downstream card's new rendering value (which now reflects the new signal) |
| `rollout_paused` | Emitted on pause; carries `{node_id, sample_idx}` |
| `rollout_resumed` | Emitted on play resume |

REPL viewer rows: `signal_stream` row shows the active signal per `(card_id, field_path)`.

---

## §6 — Acceptance bar

The signal-stream feature is realised when:

- A `Database.concept(node_id_list)` invocation produces an iterable field; the panel shows only one rank-1 KG at a time.
- `ui-signal-advance` REPL action updates the signal_index and the mirror; the panel re-renders.
- The `pattern_map` output panel (§15.8.2) iterates over `pattern_hash` keys under the same constraint.
- The `{urls_panel}` expansion (§17.1.4) fires scan once per URL via signal-stream advances.
- `rollout-play` / `rollout-pause` / `rollout-step` REPL actions drive the iteration.
- The suppressed iterable elements remain accessible via direct REPL inspection of the underlying ConceptNode's `data` field — the constraint is purely a display rule.
- An env-scenario `signal-stream-roundtrip` asserts the above.

---

## §7 — Anti-goals

| Anti-goal | DOMAIN_MODEL §18 |
|---|---|
| Full-iterable rendering (showing all signals at once in the panel) | §18.24 |
| URL-set panel iteration parallel-fire (firing scan over all URLs in parallel rather than per-signal) | §18.30 |

---

## §8 — Code constraints

- [`backend_services.md`](../code_constraints/backend_services.md) — RolloutCoordinator singleton + advance behaviour.
- [`frontend_rendering.md`](../code_constraints/frontend_rendering.md) — FieldTree renderer reads signal_index, renders only the current.
- [`ws_frames.md`](../code_constraints/ws_frames.md) — `ui_state_changed (kind=signal_advance)` frame schema.
- [`repl_actions.md`](../code_constraints/repl_actions.md) — `ui-signal-advance` + `rollout-play / pause / step` actions.

---

## §9 — Cross-features

- [`play_pause_rollout.md`](play_pause_rollout.md) — the user-facing play/pause control.
- [`pattern_map.md`](pattern_map.md) — `pattern_map` iterates under this constraint.
- [`url_set_panel.md`](url_set_panel.md) — `{urls_panel}` fires per-signal.
- [`agent_integration_scheme.md`](agent_integration_scheme.md) — the agent's recursion-over-iteration loop composes through this.
- [`four_fixture_api.md`](four_fixture_api.md) — `Database.concept(list)` is the canonical iterable producer.
