---
phase: WFH-07-deep-object-exploration-gestures
plan: 01
subsystem: api
tags: [fastapi, kuzu, concept-graph, type-graph, pytest]

# Dependency graph
requires: []
provides:
  - "GET /api/concepts/{id}/next_rank — rank-1 typed-neighbor fetch endpoint over the python-native materialiser edge vocabulary"
  - "pytest coverage proving the endpoint over a real materialised python_object tree"
affects: [WFH-07-02, WFH-07-03, WFH-07-04, WFH-07-05, WFH-07-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Static-path-before-parametric route registration (next_rank registered above /concepts/{concept_id}, same ordering convention as the existing /concepts/export and /concepts/import block)"
    - "Backend reads+shapes graph data; frontend renders only (D10) — next_rank does zero type computation beyond filtering+resolving already-materialised edges"
    - "Rank-1-only traversal with explicit self-referential-edge skip as the DoS mitigation (T-07-01)"

key-files:
  created:
    - backend/tests/test_next_rank_route.py
  modified:
    - backend/api/routes.py

key-decisions:
  - "Used a dedicated GET /concepts/{id}/next_rank route (not an extension of GET /concepts/{id}) per RESEARCH Open-Q2 resolution — additive, self-documenting, zero risk to existing consumers"
  - "Test calls the route handler function directly (not via FastAPI TestClient/HTTP) with routes._get_graph_editor monkeypatched to a GraphEditor bound to a throwaway temp_db_dir Kuzu connection — avoids relying on the process-wide get_default_graph_editor() singleton's first-call binding, which conftest.py's existing fixtures don't exercise for this route family"

patterns-established:
  - "Pattern 1: description -- next_rank's edge-type filter set (_NEXT_RANK_EDGE_TYPES) is the single source of truth for the rank-1 vocabulary; any future route/feature needing the same four materialiser edge types should reuse or mirror this constant rather than re-deriving the list"

requirements-completed: [EXPLORE-01]

# Metrics
duration: 12min
completed: 2026-06-24
---

# Phase WFH-07 Plan 01: Backend rank-1 next-rank type-graph fetch endpoint Summary

**GET /api/concepts/{id}/next_rank reads the python_api_materialiser's OBJECT_HAS_*/FUNCTION_*_TYPE edges and shapes them into a rank-1 typed-neighbor list, registered ahead of the parametric /concepts/{id} route, with pytest coverage over a real materialised python_object tree.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-06-24T01:14:15Z
- **Completed:** 2026-06-24T01:18:42Z
- **Tasks:** 2 completed
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments
- Added `GET /api/concepts/{id}/next_rank` to `backend/api/routes.py`, registered as a static path above the parametric `/concepts/{concept_id}` route (RESEARCH Open-Q2 resolution)
- Endpoint filters `ConceptEdge` rows to exactly the four materialiser edge types (`OBJECT_HAS_PROPERTY`, `OBJECT_HAS_FUNCTION`, `FUNCTION_INPUT_TYPE`, `FUNCTION_OUTPUT_TYPE`), resolves each edge's target to a `ConceptNode`, skips self-referential edges, and 404s on an unknown `concept_id`
- Added `backend/tests/test_next_rank_route.py` with 4 passing tests proving the behavior against a real materialised `python_object` tree (no fake/stub of the graph layer itself — only the harness-level `WFH_FAKE_SLM`/`WFH_FAKE_EMBEDDER`/`NO_WEBDRIVER` gates are set per the plan's verify step, none of which this pure graph-read test actually exercises)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add GET /concepts/{id}/next_rank rank-1 type-graph endpoint (D-03)** - `e590dc4` (feat)
2. **Task 2: Pytest coverage for next_rank over a materialised python_object tree** - `7ecad35` (test)

**Plan metadata:** (this commit) `docs(07-01): complete plan`

## Files Created/Modified
- `backend/api/routes.py` - Added `_NEXT_RANK_EDGE_TYPES`, `_NEXT_RANK_RELATION_HINT`, and `GET /concepts/{concept_id}/next_rank` (registered above the parametric `/concepts/{concept_id}` route)
- `backend/tests/test_next_rank_route.py` - 4 pytest cases: edge-type vocabulary enforcement, known property+function presence with correct relation hints, self-referential-edge exclusion, 404 on unknown id

## Decisions Made
- **Dedicated route, not an extension of `GET /concepts/{id}`** — matches RESEARCH Open-Q2's resolution; additive and self-documenting, no risk to existing `/concepts/{id}` consumers.
- **Test seeds via `PythonAPIMaterialiser` against a `temp_db_dir`-backed Kuzu connection, then calls the route handler function directly** rather than going through `TestClient`/HTTP — the route depends on `_get_graph_editor()` → `get_default_graph_editor()`, a process-wide singleton bound to whatever `backend.database.conn` was on its *first* call in the process. None of the existing `conftest.py` fixtures (`temp_kuzu_db`, `client`) exercise that singleton path for this route family, so binding to it directly would risk cross-test pollution depending on pytest execution order. Monkeypatching `routes._get_graph_editor` to return a `GraphEditor` bound to the test's own throwaway DB connection is deterministic and matches the plan's explicitly offered alternative ("or call the route handler directly with a graph editor seeded via the materialiser").
- **pytest (not the standalone-script fallback)** — `backend/tests/conftest.py` already exists with a working `pytest_configure`/fixture setup and other backend tests run successfully under `python -m pytest`, so the RESEARCH-flagged "no pytest.ini found" uncertainty resolved to "pytest works as-is, no special config needed."

## Deviations from Plan

None - plan executed exactly as written. Both tasks' acceptance criteria were met without requiring any Rule 1-4 deviations.

## Issues Encountered

None. The one judgment call (how to seed/bind the `GraphEditor` for the test, since `_get_graph_editor()`'s singleton isn't exercised by existing fixtures) was anticipated by the plan itself ("call the route handler directly with a graph editor seeded via the materialiser") and resolved by monkeypatching — no blocking issue.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `GET /api/concepts/{id}/next_rank` is live and ready for 07-02+'s frontend hover/right-click next-rank rendering to consume.
- The `_NEXT_RANK_EDGE_TYPES` / `_NEXT_RANK_RELATION_HINT` constants in `backend/api/routes.py` are the canonical vocabulary reference for any later plan in this phase that also needs the four materialiser edge types (e.g. the typed-rendering mode in `magic_markdown.mjs`).
- No blockers for downstream plans.

---
*Phase: WFH-07-deep-object-exploration-gestures*
*Completed: 2026-06-24*

## Self-Check: PASSED

- FOUND: backend/api/routes.py
- FOUND: backend/tests/test_next_rank_route.py
- FOUND: .planning/phases/WFH-07-deep-object-exploration-gestures/07-01-SUMMARY.md
- FOUND: e590dc4 (commit exists in git log)
- FOUND: 7ecad35 (commit exists in git log)
