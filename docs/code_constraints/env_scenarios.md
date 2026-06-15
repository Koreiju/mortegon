# Code Constraint: Env-Scenario Catalogue

**Surface scope.** `scripts/sim_frontend.py` `_ENV_SCENARIOS` dict + the `full-smoke` chain + every per-feature roundtrip scenario + the live-stack probes.

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §14.4 (acceptance bar), §16 (lodestar use cases), §16.5 (live-scan + DB-cleanup probe), §13.2 (no-mocks contract).

---

## §1 — Must hold

### §1.1 Every gesture has at least one env-scenario

Per [`repl_actions.md`](repl_actions.md) §1.3, every REPL action MUST be referenced by at least one env-scenario assertion. The acceptance bar is: REPL action → backend mutation → WS frame → frontend renders → telemetry → REPL reads back.

### §1.2 Round-trip scenarios per mirror field

Each UIStateService mirror field has a `<field>-roundtrip` env-scenario:

| Scenario | Field tested |
|---|---|
| `ui-roundtrip` | select / hover / pin / unpin (legacy mirror surface) |
| `halo-focus-roundtrip` | halo_focus |
| `halo-chain-roundtrip` | halo_chain |
| `pin-chrome-roundtrip` | pin_chrome |
| `latch-toggle-roundtrip` | latch_state |
| `viewport-spine-roundtrip` | viewport_visible_rows |
| `autocomplete-state-roundtrip` | autocomplete_state |
| `edit-field-roundtrip` | editing_field |
| `signal-stream-roundtrip` | signal_stream |
| `compile-expand-collapse-roundtrip` | compile_expansions |
| `rollout-roundtrip` | rollout_state |
| `node-fold-roundtrip` | node_fold_state |

Each scenario:

1. Purges to baseline.
2. Sets the field via the REPL action.
3. Reads back via `ui-state` or via the field-specific GET.
4. Asserts the mirror matches.
5. Tests idempotency (same input → no state change but broadcast still fires).
6. Tests validation (empty/missing required fields → 400).
7. Tests purge clears the field.

### §1.3 Cross-feature scenarios per lodestar use case

Each §16 lodestar carries an evidence probe + the corresponding `live-rag`, `iterated-compile`, `live-agent`, `concept-graph-authoring` env-scenarios (planned to first-class env-scenarios in `_ENV_SCENARIOS`).

### §1.4 The mandatory live-scan probe

`live-scan-real-with-cleanup` env-scenario (and `scripts/probe_live_scan_with_cleanup.py`) MUST pass on every CI run gated by `all_real: true`. See [`live_scan_cleanup.md`](../features/live_scan_cleanup.md) for the full assertion catalogue.

### §1.5 Real-stack AND stub-mode

The `full-smoke` chain MUST pass in two modes:

- **Real-stack** — no fake gates set; `all_real: true`. CI gates require this for merge.
- **Stub mode** — `WFH_FAKE_SLM=1 WFH_FAKE_EMBEDDER=1 NO_WEBDRIVER=1` set. CI-friendly fast path for routes/lifecycle/UI-state.

### §1.6 Action-registry coverage

`env-scenario action-registry-coverage` asserts:

- Every entry in `_ACTIONS` has a valid handler signature.
- Every scenario in `_ENV_SCENARIOS` is callable (no import errors).

### §1.7 Route-coverage

`env-scenario route-coverage` asserts every REST route in `routes.py` has at least one REPL action invoking it (via the `_ROUTE_COVERAGE` map).

### §1.8 Subsystem-status assertion

Every env-scenario that depends on a real subsystem starts with a `subsystem-status` check; if `all_real != true` and the scenario requires real, the scenario fails fast with a descriptive message.

---

## §2 — Must not

### §2.1 Pass without asserting

A scenario that returns 0 without making assertions is a no-op — it provides no verification value. Every scenario asserts at least one specific property.

### §2.2 Mock the backend within an env-scenario

Env-scenarios run against the real backend. Mocking subverts the entire verification chain.

### §2.3 Skip the full-smoke chain for "isolated" features

Even features that seem isolated affect global state (PageRank, indices, evolution log). Full-smoke catches the cross-feature regressions.

### §2.4 Run env-scenarios in parallel

The lifecycle dispatcher's per-workspace serial guarantees depend on serial scenario execution. The chain runs serially.

### §2.5 Allow a scenario to leave the workspace in a non-baseline state

Every scenario purges at start AND end (or asserts the equivalent). Test-induced state pollution would skew the next scenario.

---

## §3 — Catalogue snapshot

The current `full-smoke` chain runs **83 scenarios** (86 registered in `_ENV_SCENARIOS`) — including `reservoir-rollout-async-perimeter` (the §18.34 regression signature, §6.6.4 / §7.8); `action-registry-coverage` gates that every one is callable. The categories:

| Category | Scenarios |
|---|---|
| Harness self-check | `action-registry-coverage`, `route-coverage`, `routes-list-shape`, `actions-by-category-coverage`, `chunker-regression`, `chunker-edge-cases` |
| Live backend, no embedder | `app-info-shape`, `route-mount-smoke`, `graph-schema-shape`, `health-perf`, `purge-requires-confirm`, `fixture-delete-guard`, `ui-roundtrip`, `halo-focus-roundtrip`, `pin-chrome-roundtrip`, `latch-toggle-roundtrip`, `viewport-spine-roundtrip`, `autocomplete-state-roundtrip`, `edit-field-roundtrip`, `halo-chain-roundtrip`, `scan-streaming-routes-to-workspace-ws`, `spine-delta-emits`, `telemetry-roundtrip`, `workspace-isolation` |
| Read-only shape probes | `mapper-empty-shape`, `analytics-empty-shape`, `cascade-status-empty`, `agent-reviews-empty`, `evolution-log-shape`, `node-details-404`, `session-reconcile-empty`, `chunk-search-empty`, `search-hybrid-empty`, `concepts-export-shape` |
| Unified node view / Mortegon §1 | `agent-fixture-present`, `fixtures-undeletable`, `sticky-starts-collapsed`, `passive-stays-collapsed`, `hover-to-stick-rect-parity`, `unified-node-view-states`, `ui-collapse-toggle`, `url-collapse-cascade`, `compile-fuses-inverse`, `gesture-walkthrough`, `complex-interaction-walkthrough`, `cascade-reflow-roundtrip` (§8D.38.4 downstream auto-recompile, single + transitive), `cascade-workspace-isolation` (§1.10 — the cascade is workspace-scoped), `cascade-cycle-safety` (mutual {ref} cycle terminates — visited-set + depth-cap) (composite: rollout + halo + compile + signal-stream coexist in one UIState envelope without interference — the §8D.25 play loop verified end-to-end through the REPL) |
| W31 ConceptComputeNode | `compute-plain-rendering`, `compute-ref-substitution`, `compute-pydantic-structured`, `compute-python-entry`, `compute-chain-compilation`, `compute-prompt-slm-stub`, `compute-rendering-persisted`, `scanner-to-concept-roundtrip`, `scanner-compute-pipeline`, `slm-pydantic-direct` |
| Live backend + embedder | `warmup`, `concept-lifecycle`, `edge-roundtrip`, `idempotency-replay`, `evolution-rollback` (§11.4 single + edit-range + actor scopes), `upload-graph-roundtrip`, `chat-session-create`, `compiled-xpath-pattern-create`, `agentic-instantiate-shape`, `purge-and-rebuild` |
| **§1.2-update scenarios (realised)** | `signal-stream-roundtrip`, `rollout-roundtrip`, `node-fold-roundtrip`, `pattern-map-live-update`, `urls-panel-iteration`, `editor-primitives-roundtrip`, `library-middleware-roundtrip`, `agent-three-primitives-chain`, `database-concept-signal-stream`, `6d-umap-format`, `perimeter-rescale`, `compile-expand-collapse-roundtrip`, `watch-activity-mirror`, `apparition-mode-roundtrip` — all green in `full-smoke`. `live-scan-real-with-cleanup` is realised + gated on `all_real` (skips gracefully in stub per §1.5; the real path is `probe_live_archive_scan.py`). |
| **Reservoir rollout (§7.8 / §6.6.4) — realised** | `reservoir-rollout-async-perimeter` — the cascaded-rollout reservoir overlay (`POST /api/compute_graph/layout`): readout-perimeter recompute (`readout_nodes` §7.8.2) + input sources (`input_nodes` §7.8.1) + the §7.8.5 advancing abstraction front + the **bisector** compute-graph node **sliding** as the output centroid moves (`place_compute_graph_node`, §6.6.4) + the **coordinate-free** projector link network (`compute_projector_links`). **Regression signature for anti-goal §18.34.** Part A is end-to-end over HTTP (green in both modes); Part B unit-verifies the bisector-slide math in-process (the `perimeter-rescale` precedent, since 6D coords aren't reachable over HTTP in stub). The async-per-readout out-of-order delta-stream (§7.8.3) is verified in the same scenario as it lands. |

### §3.1 Planned / design-intent scenarios (NOT in the current 83-count)

*(None currently pending — `reservoir-rollout-async-perimeter` has graduated from this table into the realised catalogue above and into `full-smoke`, §3; see the offline probe `scripts/probe_reservoir_rollout.py`.)*

A scenario listed here would have its code design exist (the §-refs) but its implementation + env-scenario pending; it would **not** count toward the realised total above, and would join `full-smoke` only once green in both modes (§1.5).

---

## §4 — Anti-goal anchors

Every §18 anti-goal MUST be covered by at least one env-scenario assertion (its "regression signature"). The mapping lives in [`README.md`](README.md) §4.

---

## §5 — Code anchors

| File | Responsibility |
|---|---|
| `scripts/sim_frontend.py` `_ENV_SCENARIOS` | Scenario registry |
| `scripts/sim_frontend.py` `_env_scenario_full_smoke` | Chain runner |
| `scripts/probe_live_*.py` | Standalone live-stack probes |

---

## §6 — Feature touchpoints

Every feature has a corresponding env-scenario; see the §3 catalogue.
