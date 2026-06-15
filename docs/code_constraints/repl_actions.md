# Code Constraint: REPL Action Catalogue Contract

**Surface scope.** `scripts/sim_frontend.py` `_ACTIONS` dict + every action handler + the route-coverage env-scenario.

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §14 (REPL ↔ frontend two-way feedback), §14.2 (gesture catalogue — complete-by-design), §14.4 (acceptance bar), §14.5 (in-place activity viewer), §1.5 (Symbolic register).

---

## §1 — Must hold

### §1.1 Every design-mentioned gesture has a REPL action

The §14.2 gesture catalogue is the canonical list. Every row in it MUST have a corresponding entry in `_ACTIONS`. The REPL action's name uses the kebab-case form of the gesture.

**Test signal.** `env-scenario action-registry-coverage` asserts the action count matches `_ACTIONS` length; `env-scenario route-coverage` asserts every REST route has at least one REPL action invoking it.

### §1.2 Every REPL action has all five tuple entries

For every gesture in §14.2, the REPL action MUST cover:

1. **REPL action** (the `_ACTIONS` entry).
2. **Backend mutation** (which lifecycle function or REST endpoint it invokes).
3. **WS frame** (the broadcast it triggers).
4. **Frontend render** (what changes visibly when the frame arrives).
5. **Telemetry** (which UI state mirror field is updated).

A REPL action without all five entries is incomplete; the §14.2 catalogue MUST be extended to include it.

### §1.3 Every REPL action has an env-scenario asserting the round-trip

For every REPL action that produces backend mutation, at least one env-scenario in `_ENV_SCENARIOS` MUST exercise the action AND assert the resulting WS frame OR UI mirror update OR persisted state matches expectation.

**Test signal.** `env-scenario env-scenario-coverage` (planned) asserts every action appears in at least one scenario.

### §1.4 Idempotent REPL actions accept idempotency keys

REPL actions for mutating routes accept an optional `idempotency_key` kwarg; replays with the same key produce one effect.

**Test signal.** `env-scenario idempotency-replay`.

### §1.5 Validation errors return `_status=400`, not exceptions

REPL actions for routes with required fields return `{_status: 400, _error: "..."}` if a required field is missing. They do NOT raise Python exceptions for missing-input cases (raising is reserved for transport errors).

**Test signal.** Per-scenario `_status == 400` checks in validation steps (e.g., `halo-focus-roundtrip` step 6).

### §1.6 Read-only REPL actions are safe to call freely

REPL actions for read-only routes (GET endpoints) MUST be safe to call without side effects; the gesture catalogue marks them as "(REST only)" in the WS-frame column.

### §1.7 In-place viewer reads every mirror field

The `watch-activity` REPL subcommand renders a fixed-row block. Every UIState mirror field that any REPL action sets MUST have a corresponding row in the viewer (or be aggregated into an existing row).

**Test signal.** `env-scenario viewer-coverage` (planned) — set every mirror field; assert the viewer's rendered block contains the value.

---

## §2 — Must not

### §2.1 Skip the REPL action for a gesture under "this is internal"

If the design names a gesture, it has a REPL action. Internal-only mutations that have no REPL surface are invisible to the verification chain.

### §2.2 Use a different name in §14.2 vs `_ACTIONS`

The gesture-catalogue name and the `_ACTIONS` key are the same string (kebab-case).

### §2.3 Let an env-scenario pass without asserting the round-trip

The acceptance bar (§14.4) requires the env-scenario to assert the WS frame OR UI mirror OR persisted state, not just the HTTP status code.

### §2.4 Hardcode workspace_id in REPL actions

Workspace is derived from `_Backend.workspace_id` (which the user sets at REPL boot); the action passes the workspace through transparently.

### §2.5 Issue REPL actions that bypass the lifecycle dispatcher

Even for "fast-path" GET actions on read state — the dispatcher's broadcast invariant depends on every state-changing operation routing through it.

---

## §3 — Code anchors

| File | Responsibility |
|---|---|
| `scripts/sim_frontend.py` | `_ACTIONS` dict, action handlers, env-scenarios, route-coverage check, action-registry-coverage check |
| `scripts/sim_frontend.py` `_Backend` class | HTTP wrappers per REST endpoint that the action handlers call into |
| `scripts/sim_frontend.py` `_render_activity_block` | The in-place viewer rendering |
| `scripts/sim_frontend.py` `_activity_snapshot_from_ws_and_rest` | The viewer's state aggregation from WS + REST |

---

## §4 — Anti-goal anchors

| Constraint | Anti-goal |
|---|---|
| §1.1 (every gesture has a REPL action) | §14.4 acceptance bar |
| §1.7 (viewer reads every mirror field) | §14.5 / §18.1 (severance regression invisible if viewer doesn't read the affected mirror) |

---

## §5 — REPL action checklist for a new feature

When adding a new feature:

1. Identify the gesture (or gestures) — what does the user do?
2. Add a row to §14.2 in DOMAIN_MODEL.md with the five tuple entries.
3. Add a `_Backend.<method>` HTTP wrapper if a new REST endpoint is involved.
4. Add an `_act_<gesture>` handler in `sim_frontend.py`.
5. Register the action in `_ACTIONS`.
6. Add the route to the `_ROUTE_COVERAGE` map if a new REST route is involved.
7. Add or extend an env-scenario to assert the round-trip.
8. If the feature mirrors UI state, add a UIStateService setter + add the field to `_activity_snapshot_from_ws_and_rest` aggregation + add a row to `_render_activity_block`.
9. Run `env-scenario action-registry-coverage` + `env-scenario route-coverage` to confirm the registration.
10. Run the new env-scenario to confirm round-trip passes.

---

## §6 — Feature touchpoints

Every feature with a user-visible gesture:
- [`four_fixture_api.md`](../features/four_fixture_api.md)
- [`halo_retrieval.md`](../features/halo_retrieval.md)
- [`autoregressive_halo.md`](../features/autoregressive_halo.md)
- [`click_to_edit.md`](../features/click_to_edit.md)
- [`plus_sign_field_tree.md`](../features/plus_sign_field_tree.md)
- [`signal_stream.md`](../features/signal_stream.md)
- [`play_pause_rollout.md`](../features/play_pause_rollout.md)
- [`autocomplete.md`](../features/autocomplete.md)
- [`pattern_map.md`](../features/pattern_map.md)
- [`url_set_panel.md`](../features/url_set_panel.md)
- [`live_scan_streaming.md`](../features/live_scan_streaming.md)
- [`live_scan_cleanup.md`](../features/live_scan_cleanup.md)
- [`repl_two_way_feedback.md`](../features/repl_two_way_feedback.md)
- [`in_place_activity_viewer.md`](../features/in_place_activity_viewer.md)
- [`evolution_log_rollback.md`](../features/evolution_log_rollback.md)
- [`compile_collapse_dialectic.md`](../features/compile_collapse_dialectic.md)
- [`click_and_stick.md`](../features/click_and_stick.md)
- [`visibility_spine.md`](../features/visibility_spine.md)
