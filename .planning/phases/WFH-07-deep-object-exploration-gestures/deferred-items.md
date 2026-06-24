# Deferred Items — Phase WFH-07

## route-coverage env-scenario missing `/concepts/{concept_id}/next_rank`

- **Found during:** Plan 07-04 full-suite regression check (`backend/tests/test_sim_env_scenarios.py::test_env_scenario_passes_offline[route-coverage]`)
- **Pre-existing since:** Plan 07-01 (commit `e590dc4`, "feat(07-01): add GET /concepts/{id}/next_rank rank-1 type-graph endpoint") added the route but did not update `scripts/sim_frontend.py`'s `_env_scenario_route_coverage` allowlist. Confirmed present at `028e283` (the phase-plan commit, before any 07-04 task commits) via `git show 028e283:scripts/sim_frontend.py`.
- **Why deferred, not fixed:** Out of scope for Plan 07-04 per the executor's scope boundary rule — only auto-fix issues directly caused by the CURRENT task's changes. `next_rank`'s registration is Plan 07-01's responsibility, not 07-04's (07-04 added `inherit_types` to two existing routes + the gateway WIRE_LINK/DELETE_REF cases; it did not add or change `next_rank`).
- **Symptom:** `route-coverage` scenario reports `1 uncovered route(s): /concepts/{concept_id}/next_rank` and returns exit code 1.
- **Suggested fix (for whoever picks this up):** add `/concepts/{concept_id}/next_rank` to the static-path allowlist/coverage set in `scripts/sim_frontend.py::_env_scenario_route_coverage`, alongside the other static-path-before-parametric routes it already tracks.
- **Verified non-blocking for 07-04:** `backend/tests/test_edge_inherit_types.py` (7/7), `backend/static/js/fe/gateway.test.mjs` (9/9), and the full backend pytest suite minus this one scenario (356 passed, 2 skipped) are all green. `test_next_rank_route.py` (4/4) also passes — the route itself works, only the coverage scenario's allowlist is stale.
