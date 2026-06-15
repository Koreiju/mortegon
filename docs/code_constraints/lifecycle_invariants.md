# Code Constraint: Lifecycle Invariants

**Surface scope.** `backend/services/concept_lifecycle.py` (the dispatcher) + every caller that mutates a ConceptNode or ConceptEdge.

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §2.2 (one lifecycle dispatcher), §10.2 (dispatcher fan-out), §17.1.1 (Editor mutation sequence), §18 (anti-goals across actors).

**Owner object.** [`ConceptLifecycle`](../object_model/ConceptLifecycle.md).

---

## §1 — Must hold

### §1.1 One dispatcher

Every mutation of any ConceptNode or ConceptEdge MUST pass through `apply_update_lifecycle` or `apply_delete_lifecycle`. There is no second mutation path.

- Direct `kuzu_connection.execute(INSERT|UPDATE|DELETE ...)` outside `concept_lifecycle.py` and `graph_editor.py` internals is forbidden.
- The three foundational fixtures (Agent, WebBrowser, Database) all call into the same dispatcher when materialising their function trees. (§S removed the former fourth, Editor; the create/link/overwrite/delete gestures still route through this dispatcher, just not as a fixture.)
- The agent's emitter (via ActionResolver), the scanner (via WebBrowser.scan), the python-API materialiser, the compile pipeline's variable-auto-creation, and the user's GUI gestures all converge on the dispatcher.

**Test signal.** `env-scenario action-registry-coverage` confirms every mutation REPL action calls into the dispatcher; `env-scenario lifecycle-roundtrip` (planned) traces a single mutation through the fan-out.

### §1.2 Atomic Kuzu + EvolutionLog

The Kuzu write and the EvolutionLog `EditDiff` append MUST happen in one transaction. If either fails, both roll back. The WS broadcast happens AFTER the transaction commits.

**Test signal.** Crash-injection test (planned) — kill the EvolutionLog append mid-transaction; assert Kuzu rolls back.

### §1.3 Broadcast after commit

The `concept_changed` (or `concept_index_update`, or `ui_state_changed`) WS frame MUST be emitted after the Kuzu transaction commits. Peer surfaces never see a state the persistence layer hasn't committed.

**Test signal.** Race-condition probe (planned) — subscribe two WS clients; mutate; assert both see the change AFTER the next `GET /api/concepts/<id>` reflects it.

### §1.4 Cascade after broadcast

The cascade scheduler nudge MUST happen after the broadcast. Downstream cards re-compile against post-commit, post-broadcast state, never pre-commit state.

**Test signal.** Cascade-timing probe (planned).

### §1.5 Idempotency

Mutations MUST accept an optional `idempotency_key`. Replays with the same key within 5 minutes MUST return the original EditDiff without re-applying.

**Test signal.** `env-scenario idempotency-replay` — three identical POSTs with the same key produce one EditDiff.

### §1.6 Fixture delete guard

`apply_delete_lifecycle` MUST reject deletes targeting any concept whose `backing_pointer` starts with `fixture::`. Returns `EditDiff(action="rejected", _reason="foundation_fixture_undeletable")`.

**Test signal.** `env-scenario fixture-delete-guard` — deletes all three fixtures (§S) + a sample materialised member; asserts each is rejected.

### §1.7 Actor-aware cascade short-circuit

The cascade scheduler MUST tag each re-fire with the originating `actor`. If the originating actor's perception is active (agent body subgraph mid-tick for the same `pcid`), the re-fire is short-circuited.

**Test signal.** Agent-self-loop probe (planned) — spawn agent; emit `WriteFieldAction` on parameter card; assert the cascade does NOT re-trigger the same agent's perception in the same tick.

### §1.8 Full fan-out on every mutation

Every mutation MUST run the full fan-out (Kuzu write → EvolutionLog → WS broadcast → ConceptIndex upsert → projection schedule → cascade nudge), even if some steps are no-ops for the specific change kind.

**Test signal.** Code review: no early-return in the dispatcher body.

### §1.9 Provenance preservation

The `provenance` field MUST be set per the calling actor. The canonical §8D.44 schema enumerates `user-authored | agent-authored | derived-from-chunk | committed-subgraph`; the realized code also emits `ray-projected` for the in-memory apparition ray-projection tag. The actor→value mapping as realized:

| Actor | Provenance |
|---|---|
| User via GUI/REPL | `user-authored` |
| Agent via emitter ActionResolver | `agent-authored` |
| Agent subgraph-commit (`agent_runtime` commit op) | `committed-subgraph` |
| Compile pipeline variable-auto-creation | `derived-from-chunk` (if data refs a chunk) / `user-authored` (otherwise) |
| Scanner chunks (WebBrowser.scan → output projection) | `derived-from-chunk` |
| Python-API materialiser (`python_api_materialiser`) | `derived-from-chunk` (auto-materialised, read-only — NOT user-typed) |
| Apparition ray-projection (`apparition_service`) | `ray-projected` (in-memory projection tag) |

Note the two distinct "materialiser" senses: the agent's **subgraph-commit** writes `committed-subgraph` (turning a live subgraph into a reusable node), whereas the **python-API materialiser** writes `derived-from-chunk`. There is no `scanner-emitted` value — scanner-derived nodes share the `derived-from-chunk` tag with compile/chunk-derived nodes.

Provenance MUST be preserved across overwrites; the original-actor metadata is recoverable from EvolutionLog.

**Test signal.** Provenance assertion in `env-scenario foundation-ensure` + `live-scan-real-with-cleanup`.

---

## §2 — Must not

### §2.1 Bypassing the dispatcher

Direct mutations via `kuzu_connection.execute()`, `kuzu_session.write()`, or any other path that skips `apply_update_lifecycle` / `apply_delete_lifecycle`. Includes any "performance optimisation" path that batches without going through the dispatcher per record.

**Anti-goal anchor.** §18 (all anti-goals depend on the dispatcher's uniformity).

### §2.2 Skipping the EvolutionLog append for "trivial" changes

Every mutation produces an EditDiff. Rollback over any subset of the history depends on the diff being present for every mutation.

**Anti-goal anchor.** §11.4 evolution-log contract.

### §2.3 Letting the WS broadcast precede the Kuzu commit

Peer surfaces would see optimistic state that may roll back; the §1.5 Symbolic-register transparency would carry false signal.

### §2.4 Calling `apply_delete_lifecycle` on a foundation fixture

Even via a "manual cleanup" path or a test scenario.

**Anti-goal anchor.** §18.22, §18.27.

### §2.5 Coalescing many mutations into one EditDiff

Granular rollback is the conflict-resolution tool (§2.6). Bulk operations produce one EditDiff per atomic primitive, not one diff for the whole batch.

### §2.6 Letting an agent emitter re-trigger its own perception

Breaks the integration scheme convergence (§12.2.1).

**Anti-goal anchor.** §2.7 actor-aware short-circuit.

### §2.7 Hardcoding fixture `concept_id`s in callers

The `concept_id` is opaque; only `backing_pointer` is the stable identifier for foundation fixtures. Use `BackingRegistry.resolve(...)`.

---

## §3 — Code anchors

| File | Responsibility |
|---|---|
| `backend/services/concept_lifecycle.py` | `apply_update_lifecycle`, `apply_delete_lifecycle`, fan-out, fixture-delete-guard, idempotency cache |
| `backend/services/graph_editor.py` | Editor primitive implementations that call into the dispatcher |
| `backend/services/agent_runtime.py` | ActionResolver routes emitter actions through Editor → dispatcher |
| `backend/services/python_api_materialiser.py` | Materialiser uses Editor → dispatcher |
| `backend/dom/pipeline.py` + scanner | Scanner uses Editor → dispatcher per emitted chunk |
| `backend/api/routes.py` | Every mutation REST endpoint goes through Editor → dispatcher |

---

## §4 — Anti-goal anchors

| Constraint | Anti-goal |
|---|---|
| §1.1 (one dispatcher) | §18.1 (severance), §18 (every anti-goal depends on dispatcher uniformity) |
| §1.6 (fixture delete guard) | §18.22 (fixtures deletable), §18.27 (fixture count drift) |
| §1.7 (actor-aware short-circuit) | (no specific §18; the §12 integration scheme convergence depends on it) |

---

## §5 — Feature touchpoints

Every feature touching mutation:
- [`four_fixture_api.md`](../features/four_fixture_api.md)
- [`halo_retrieval.md`](../features/halo_retrieval.md) (soft-to-hard promotion)
- [`autoregressive_halo.md`](../features/autoregressive_halo.md)
- [`click_to_edit.md`](../features/click_to_edit.md) (commit on Enter)
- [`pattern_map.md`](../features/pattern_map.md) (incremental schema build)
- [`live_scan_streaming.md`](../features/live_scan_streaming.md) (chunk emission)
- [`evolution_log_rollback.md`](../features/evolution_log_rollback.md)
- [`agent_integration_scheme.md`](../features/agent_integration_scheme.md)
