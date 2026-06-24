---
phase: WFH-07-deep-object-exploration-gestures
plan: 04
subsystem: api
tags: [fastapi, kuzu, concept-graph, type-graph, gateway, javascript, pytest]

# Dependency graph
requires:
  - phase: WFH-07-01
    provides: "_NEXT_RANK_EDGE_TYPES / _NEXT_RANK_RELATION_HINT constants — the canonical four-edge materialiser vocabulary this plan's inheritance helper reuses"
provides:
  - "inherit_types: bool = False on EditorLinkRequest + ConceptEdgeRequest — single synchronous I/O-type-inheritance side-effect fanned through apply_edge_create_lifecycle"
  - "gateway.mjs WIRE_LINK body carries inherit_types; DELETE_REF fires DELETE /api/concept_edges/{edge_id} + value-clear when a backing edge exists (N.13)"
  - "GestureGateway.send sequential array-of-requests firing (the seam Plan 05's drag-wire / double-right-delete gestures call)"
  - "pytest + node:assert unit coverage proving both extensions"
affects: [WFH-07-05, WFH-07-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Route-level existence validation BEFORE create_concept_edge (which itself never raises for an unknown node id) — the only way to preserve '400 on invalid pair' for routes that previously relied on a dead-code ValueError catch"
    - "buildRequest may return an ARRAY of {method,path,body} when one gesture requires more than one sequential backend call (N.13); GestureGateway.send branches on Array.isArray and fires each in order through the same fetchImpl glue — buildRequest itself stays pure (no fetch inside it)"
    - "Type-inheritance side-effect reuses the exact _NEXT_RANK_EDGE_TYPES vocabulary from Plan 07-01 — never a parallel edge-type list"

key-files:
  created:
    - backend/tests/test_edge_inherit_types.py
    - backend/static/js/fe/gateway.test.mjs
    - .planning/phases/WFH-07-deep-object-exploration-gestures/deferred-items.md
  modified:
    - backend/api/routes.py
    - backend/static/js/fe/gateway.mjs

key-decisions:
  - "N.13: DELETE_REF fires BOTH DELETE /api/concept_edges/{edge_id} AND the existing value-clear edit_close when g.edgeId is present, confirmed against object_exploration.md line 60 ('delete that reference/instance, in either panel or graph form (N.13)') — deleting only the displayed value would leave the backing ConceptEdge alive, contradicting 'delete that reference/instance'. When g.edgeId is absent (a plain literal {ref}, no backing edge), the original value-clear-only behavior is preserved unchanged."
  - "Added explicit source/target existence validation (HTTPException 400) to both editor_link and create_concept_edge — graph_editor.py's create_concept_edge is idempotent and never raises ValueError for an unknown concept_id, so the plan's Test 3 acceptance criterion ('an invalid source/target pair still raises HTTPException(400)') was unsatisfiable without this addition; editor_link's existing try/except ValueError was dead code for this case, and create_concept_edge's route handler had no validation at all before this plan (Rule 2 deviation)."
  - "Inheritance reuses graph_editor.list_concept_edges + create_concept_edge directly rather than re-deriving the materialiser's edge semantics — one vocabulary, one create-edge primitive, both already lifecycle-dispatched by the caller."

patterns-established:
  - "Pattern: when a gesture must fire more than one backend call, buildRequest returns an array of {method,path,body} (never a side-effecting buildRequest); GestureGateway.send is the ONLY place that knows how to drain it sequentially."

requirements-completed: [EXPLORE-03]

# Metrics
duration: 18min
completed: 2026-06-23
status: complete
---

# Phase WFH-07 Plan 04: Edge-create I/O-type-inheritance + gateway WIRE_LINK/DELETE_REF completion Summary

**`inherit_types` flag on the edge-create path mirrors a source node's four-materialiser-edge-type I/O signature onto a newly wired target as one `apply_edge_create_lifecycle`-dispatched side-effect, and `gateway.mjs`'s `DELETE_REF` now deletes the backing `ConceptEdge` (not just the displayed value) via a new sequential-array request shape in `GestureGateway.send`.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-06-23T21:32:00-04:00 (approx, continuation session)
- **Completed:** 2026-06-23T21:50:02-04:00
- **Tasks:** 3 completed
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments
- `EditorLinkRequest` and `ConceptEdgeRequest` both gained `inherit_types: bool = False`; when true, a new `_inherit_io_types()` helper mirrors the source's `OBJECT_HAS_PROPERTY`/`OBJECT_HAS_FUNCTION`/`FUNCTION_INPUT_TYPE`/`FUNCTION_OUTPUT_TYPE` edges onto the target, with each inherited edge individually fanned through `apply_edge_create_lifecycle` (same dispatcher as the primary edge — never a parallel write path)
- `gateway.mjs`'s `WIRE_LINK` body now carries `inherit_types: !!g.inheritTypes`; its `DELETE_REF` case now returns an array of two requests (`DELETE /api/concept_edges/{edge_id}` then the existing value-clear) when `g.edgeId` is present, confirmed against `object_exploration.md` §N.13's exact wording
- `GestureGateway.send` extended to detect an array-shaped `buildRequest` return and fire each request sequentially through the same `fetchImpl` glue — `buildRequest` itself stays pure, no inline raw `fetch()` introduced anywhere
- 7/7 new pytest cases (`test_edge_inherit_types.py`) and 9/9 new node:assert cases (`gateway.test.mjs`, a file that did not exist before this plan) both pass; full backend suite + all `fe/*.test.mjs` files re-run clean with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: edge-create I/O-type-inheritance extension (N.4, GREENFIELD)** - `d29de7b` (feat)
2. **Task 2: gateway WIRE_LINK inherit_types + DELETE_REF edge-delete completion (N.13)** - `5e47703` (feat)
3. **Task 3: pytest for edge-create inheritance + gateway unit-test scaffold** - `266e343` (test)

**Plan metadata:** (this commit) `docs(07-04): complete plan`

## Files Created/Modified
- `backend/api/routes.py` - Added `inherit_types: bool = False` to `EditorLinkRequest` + `ConceptEdgeRequest`; added `_inherit_io_types(ge, source_id, target_id, workspace_id)` helper reusing `_NEXT_RANK_EDGE_TYPES`; added explicit source/target existence validation (400) to `editor_link` and `create_concept_edge`; wired the inheritance side-effect into both handlers after the primary `apply_edge_create_lifecycle` call
- `backend/static/js/fe/gateway.mjs` - `WIRE_LINK`/`concept-edge-create` case adds `inherit_types` to the body; `DELETE_REF`/`concept-delete-ref` case returns an array `[deleteEdgeReq, clearValueReq]` when `g.edgeId` is present, else the original single value-clear request; `GestureGateway.send` extended with a `_sendOne` helper + `Array.isArray(req)` branch to fire sequential requests in order
- `backend/tests/test_edge_inherit_types.py` (new) - 7 pytest cases over a `db_janitor.temp_db_dir` throwaway Kuzu DB: default-False unchanged behavior (×2 handlers), inherit_types=True copies the source's typed neighbors (×2 handlers), invalid pair 400s regardless of inherit_types (×2 handlers), inheritance fans out through `apply_edge_create_lifecycle` once per edge (spied)
- `backend/static/js/fe/gateway.test.mjs` (new) - 9 node:assert cases: WIRE_LINK inherit_types default/true/legacy-kind-string, DELETE_REF with/without `g.edgeId` (array vs single shape) + legacy-kind-string, and three `GestureGateway.send` integration cases proving the sequential array firing, the unchanged single-request fallback, and the WIRE_LINK JSON body
- `.planning/phases/WFH-07-deep-object-exploration-gestures/deferred-items.md` (new) - logs a pre-existing, out-of-scope `route-coverage` env-scenario gap (see Deviations)

## Decisions Made
- **N.13 — DELETE_REF deletes the backing edge, not just the value.** `object_exploration.md` line 60 reads "*delete* that reference/instance, in either panel or graph form (N.13)" — a reference/instance, not merely its displayed text. RESEARCH's Pitfall 1 / Assumption A2 flagged this gap; this plan resolves it by firing `DELETE /api/concept_edges/{edge_id}` alongside the existing value-clear `edit_close` call whenever the gesture carries `g.edgeId` (i.e., the `{ref}` has a backing `ConceptEdge`). A plain literal `{ref}` with no backing edge (`g.edgeId` absent) keeps the original value-clear-only path unchanged — there is no edge to delete.
- **One request, one lifecycle event (RESEARCH Open-Q3).** The inheritance side-effect runs inside the SAME `editor_link`/`create_concept_edge` handler invocation as the primary edge create, never a frontend-orchestrated two-step and never a new dedicated endpoint. Each inherited edge still gets its own `apply_edge_create_lifecycle` call (so WS/index/evolution-log fan-out fires correctly per edge), but all of it happens within the one HTTP request the gesture issued.
- **buildRequest stays pure; GestureGateway.send owns sequencing.** Rather than have `buildRequest` reach into `fetch` for the two-call DELETE_REF case, it returns a plain array of `{method,path,body}` objects; `send()` is the one place that knows how to drain either a single request or an array of them, preserving the file's stated design intent ("buildRequest is PURE... GestureGateway is the thin fetch glue").

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added source/target existence validation (400) to both edge-create routes**
- **Found during:** Task 1 (edge-create I/O-type-inheritance extension)
- **Issue:** The plan's Test 3 acceptance criterion requires "an invalid source/target pair still raises HTTPException(400)." Tracing `graph_editor.py::create_concept_edge` showed it is idempotent on the natural key and never raises `ValueError` for an unknown node id (only the unrelated legacy `create_edge` method raises for invalid `edge_type` strings). This meant `editor_link`'s existing `try/except ValueError → HTTPException(400)` wrapper was dead code for the "invalid pair" case, and `create_concept_edge`'s route handler (`POST /concept_edges`) had no 400 validation at all.
- **Fix:** Added `if ge.get_concept(req.source_id) is None or ge.get_concept(req.target_id) is None: raise HTTPException(400, ...)` to both `editor_link` and `create_concept_edge`, placed before edge creation so it is never bypassed by the `inherit_types` fast path.
- **Files modified:** `backend/api/routes.py`
- **Verification:** `test_editor_link_invalid_pair_400s_regardless_of_inherit_types` and `test_create_concept_edge_invalid_pair_400s_regardless_of_inherit_types` both pass; confirmed via grep/read of `test_concept_lifecycle_and_cascade.py`, `test_ontology_layout.py`, and `scripts/sim_frontend.py`'s `_act_editor_link` that no existing test or script relies on linking against nonexistent node ids through the route layer (they either call `ge.create_concept_edge` directly, bypassing the route, or always use valid pre-created node ids) — full backend pytest suite re-run clean (356 passed, 2 skipped, 1 pre-existing unrelated failure — see below).
- **Committed in:** `d29de7b` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Necessary for the plan's own stated acceptance criterion to be satisfiable; no scope creep — both handlers' validation logic is structurally identical and minimal.

## Issues Encountered

A full-suite regression run (`python -m pytest backend/tests/ -q`) surfaced one pre-existing, out-of-scope failure: `test_sim_env_scenarios.py::test_env_scenario_passes_offline[route-coverage]` reports `/concepts/{concept_id}/next_rank` as an uncovered route. This predates this plan — confirmed via `git show 028e283:scripts/sim_frontend.py` (the phase-plan commit, before any 07-04 task commits) that the gap already existed: Plan 07-01 added the `next_rank` route but never added it to `scripts/sim_frontend.py`'s `_env_scenario_route_coverage` allowlist. Plan 07-04 did not touch `next_rank` or that scenario, so per the executor's scope-boundary rule this was logged to `deferred-items.md` rather than fixed. All 07-04-owned tests (`test_edge_inherit_types.py` 7/7, `gateway.test.mjs` 9/9, `test_next_rank_route.py` 4/4, the rest of the backend suite, all `fe/*.test.mjs` files) are green.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `inherit_types` and the DELETE_REF edge-delete completion are live and ready for Plan 05's DOM drag-wire / double-right-delete gesture wiring to call.
- The `_inherit_io_types()` helper and the `GestureGateway.send` array-firing pattern are the canonical reference for Plan 05/06 if either needs a similar multi-call sequential gesture.
- `.planning/phases/WFH-07-deep-object-exploration-gestures/deferred-items.md` carries one pre-existing, non-blocking route-coverage gap for whoever next touches `scripts/sim_frontend.py`.
- No blockers for downstream plans.

---
*Phase: WFH-07-deep-object-exploration-gestures*
*Completed: 2026-06-23*

## Self-Check: PASSED

- FOUND: backend/api/routes.py
- FOUND: backend/static/js/fe/gateway.mjs
- FOUND: backend/static/js/fe/gateway.test.mjs
- FOUND: backend/tests/test_edge_inherit_types.py
- FOUND: .planning/phases/WFH-07-deep-object-exploration-gestures/deferred-items.md
- FOUND: .planning/phases/WFH-07-deep-object-exploration-gestures/07-04-SUMMARY.md
- FOUND: d29de7b (commit exists in git log)
- FOUND: 5e47703 (commit exists in git log)
- FOUND: 266e343 (commit exists in git log)
