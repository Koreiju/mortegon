---
phase: WFH-07-deep-object-exploration-gestures
plan: 06
subsystem: testing
tags: [python, repl, env-scenario, playwright, e2e, selenium, no-mocks, duckduckgo]

# Dependency graph
requires:
  - phase: WFH-07-01
    provides: "GET /concepts/{id}/next_rank — read for the real-typed-inheritance assertion"
  - phase: WFH-07-04
    provides: "EditorLinkRequest.inherit_types + gateway WIRE_LINK(inherit_types) — the drag-wire side-effect this plan's scenario/probe/e2e all drive"
  - phase: WFH-07-05
    provides: "magic_markdown_panel.mjs::mount() seven-gesture DOM capture — the drag-wire/right-click-fold gestures the e2e case exercises"
provides:
  - "duckduckgo-walkthrough REPL env-scenario (stub fast-gate, green in full-smoke 93/93) driving purge -> foundation-ensure -> author self=duckduckgo -> drag-wire-equivalent editor-link(inherit_types) -> rank-1 minimalism assertion -> ui-node-fold reveal -> {chunk samples} per-sample iteration"
  - "editor-link REPL verb extended with inherit_types kwarg (threads EditorLinkRequest.inherit_types, added by 07-04, through to the CLI/REPL layer)"
  - "scripts/probe_live_duckduckgo_walkthrough.py — real-subsystem evidence probe (all_real gate, real Selenium DuckDuckGo scan, real materialiser type inheritance, real per-sample iteration) with a --self-test behavioral gate proving the gate fires + the assertion scaffold has teeth in stub mode"
  - "duckduckgo walkthrough e2e case in object_exploration.spec.js (stub-backed §N DOM-level proof: drag-wire gesture capture, rank-1 minimalism, type-stripped rank-1 reveal, per-sample iteration, no-dasharray)"
affects: [WFH-07-06-task4-checkpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "editor-link's inherit_types kwarg is the SAME backend request field 07-04 added (EditorLinkRequest.inherit_types) threaded through the REPL/CLI layer that 07-04/07-05 left unexposed — never a second route or duplicate side-effect."
    - "purge_workspace does NOT call ensure_foundation_fixtures() — only the WS-connect bootstrap path does. Any scenario/probe that purges and then needs the materialised python-native trees (the 'scanner') must explicitly call POST /api/foundation/ensure (mirrored by the REPL's foundation-ensure action) right after the purge."
    - "Live probes factor their load-bearing assertions as pure, directly-callable helpers (assert_all_real / assert_shadow_dom_present / assert_min_chunks) so a --self-test flag can exercise the gate's teeth in stub mode, independent of any real subsystem boot."

key-files:
  created:
    - scripts/probe_live_duckduckgo_walkthrough.py
  modified:
    - scripts/sim_frontend.py
    - frontend_e2e/object_exploration.spec.js

key-decisions:
  - "Chose to extend the existing editor-link REPL verb with an inherit_types kwarg rather than add a new ui-wire-link verb, since the backend already exposes the drag-wire side-effect as a single EditorLinkRequest field (07-04) — no new route/verb needed."
  - "Used the live-scan WS chunk count (chunks_seen) to size the {chunk samples} signal_stream total in the real probe, rather than a hardcoded sample count, so the per-sample iteration assertion tracks whatever the real DuckDuckGo scan actually returns."
  - "The e2e's drag-wire fixture asserts only the in-browser WIRE_LINK gesture capture (mousedown->mousemove->mouseup) — the backend inherit_types mutation itself stays proven by 07-04's gateway/edge-inherit unit suites, consistent with 07-05's established e2e scoping."

requirements-completed: [EXPLORE-04]

# Metrics
duration: ~70min
completed: 2026-06-27
status: complete
---

# Phase WFH-07 Plan 06: DuckDuckGo §N Walkthrough (Tasks 1-3) Summary

**Tasks 1-3 of the EXPLORE-04 DuckDuckGo §N walkthrough are built and verified green (stub REPL scenario + full-smoke 93/93, live-probe self-test, and a 9/9 e2e suite); Task 4 (the clean-GPU real-subsystem acceptance run) is a blocking-human checkpoint and was deliberately NOT executed by this agent.**

## Performance

- **Duration:** ~70 min (Tasks 1-3 only)
- **Tasks:** 3 of 4 completed (Task 4 deferred to human checkpoint)
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- **Task 1** — `duckduckgo-walkthrough` REPL env-scenario in `scripts/sim_frontend.py`, modeled on `_env_scenario_node_fold_roundtrip`: purge → `foundation-ensure` → author `self=duckduckgo` referencing `{scan}` → drag-wire-equivalent `editor-link(inherit_types=true)` onto the materialised WebBrowser python-object tree → asserts rank-1 minimalism (no typed colon-slot on DuckDuckGo's own data block) while `next_rank` still resolves the inherited scanner internally → `ui-node-fold` reveal + `ui-state.node_fold_state` assertion → `{chunk samples}` per-sample iteration via `signal_stream`/`signal_advance` (exact modulo-wrap `[1, 2, 0]`). Extended the `editor-link` REPL verb (CLI action + `_Backend.editor_link`) with an `inherit_types` kwarg. Registered in both `_ENV_SCENARIOS` and `_full_smoke_chain()` — full-smoke now passes 93/93 in stub mode (was 92/92 before this plan).
- **Task 2** — `scripts/probe_live_duckduckgo_walkthrough.py`, modeled on `probe_live_archive_scan.py`: gates on `/api/subsystem_status.all_real == True` before anything else, triggers a real Selenium DuckDuckGo scan, watches the per-snapshot WS through `done`, locates the real materialised WebBrowser python-object tree, authors `self=duckduckgo`, drag-wires via `POST /api/editor/link(inherit_types=true)`, asserts ≥1 real `OBJECT_HAS_*`/`FUNCTION_*_TYPE` neighbor via `GET /concepts/{id}/next_rank`, asserts rank-1 minimalism on DuckDuckGo's own data block, and drives `{chunk samples}` per-sample iteration over the real scanned distribution. Factored `assert_all_real`, `assert_shadow_dom_present`, and `assert_min_chunks` as pure, directly-callable helpers. The `--self-test` flag proves in STUB mode, in-process: (a) the `all_real` gate fires (a real stub `all_real:false` status makes `assert_all_real` raise, caught as the expected outcome) and (b) the assertion scaffold has teeth (`assert_shadow_dom_present`/`assert_min_chunks` each raise on empty fixtures and pass on minimal valid ones). Exits 0.
- **Task 3** — A `duckduckgo walkthrough` e2e case appended to `frontend_e2e/object_exploration.spec.js`, driving the served `fe/*.mjs` modules via in-page dynamic `import()` against the stub backend: a real `mousedown`→`mousemove`→`mouseup` drag-wire gesture onto a DuckDuckGo/scanner graph fixture fires `WIRE_LINK` with a SOLID transient line; the collapsed panel presents NO typed colon-slot (rank-1 minimalism, N.4/N.5); right-click `{scanner}` reveals its rank-1 `url{}`/`dom{}` fields type-stripped at every rank; `{chunk samples}` per-sample iteration via the `advanceSignal` model cycles three samples and wraps back to the first. Asserts no `stroke-dasharray` anywhere on the page (Forbidden Concepts guard). `object_exploration.spec.js` is 9/9 and `black_slate.spec.js` stays 6/6.

## Task Commits

Each task was committed atomically:

1. **Task 1: duckduckgo-walkthrough REPL env-scenario** - `526bdf1` (feat)
2. **Task 2: probe_live_duckduckgo_walkthrough.py** - `7346dac` (feat)
3. **Task 3: duckduckgo walkthrough e2e case** - `915c35b` (test)

_Task 4 (clean-GPU real-subsystem acceptance run) is a `checkpoint:human-verify` with `gate="blocking-human"` — not executed; see CHECKPOINT below._

## Files Created/Modified

- `scripts/sim_frontend.py` - new `_env_scenario_duckduckgo_walkthrough`, `editor-link` extended with `inherit_types`, registered in `_ENV_SCENARIOS` + `_full_smoke_chain`
- `scripts/probe_live_duckduckgo_walkthrough.py` - new live-subsystem evidence probe with `--self-test` behavioral gate
- `frontend_e2e/object_exploration.spec.js` - new stub-backed `duckduckgo walkthrough` e2e case

## Decisions Made

- Extended `editor-link` with `inherit_types` instead of adding a new `ui-wire-link` verb — the backend already exposes the drag-wire side-effect as a single `EditorLinkRequest` field (07-04); no new route/verb needed.
- Discovered (and worked around) that `purge_workspace` does NOT call `ensure_foundation_fixtures()` — only the WS-connect bootstrap path does. Both the REPL scenario and the live probe now explicitly call `POST /api/foundation/ensure` (mirrored by the REPL's pre-existing `foundation-ensure` action) immediately after any purge that needs the materialised WebBrowser python-object tree.
- Confirmed `signal_advance`'s exact modulo-wrap semantics by reading `UIStateService.advance_signal()` directly (`new_index = (cur + step) % max(total, 1)`), enabling a precise `[1, 2, 0]` assertion in Task 1's scenario rather than a loose multi-policy check.
- The e2e's drag-wire fixture proves only the in-browser gesture capture (mousedown→mousemove→mouseup → `WIRE_LINK`); the backend's `inherit_types` mutation itself stays proven by 07-04's gateway/edge-inherit unit suites — consistent with 07-05's established e2e scoping (browser proves gesture + intent, backend tests prove mutation).

## Deviations from Plan

None — plan executed exactly as written for Tasks 1-3. All deviations were resolved inline as part of normal task execution (Rule 3 — auto-fix blocking issues) rather than tracked as separate items, since each was directly required to make the task's own verification command pass:

### Auto-fixed Issues

**1. [Rule 3 - Blocking] purge_workspace doesn't re-materialise foundation python trees**
- **Found during:** Task 1 (writing the scenario's scanner-lookup step)
- **Issue:** After `purge(confirm=erase)`, `concept-list` returned only the bare fixtures with no materialised WebBrowser python-object tree, because `ensure_foundation_fixtures()` is called only from the WS-connect bootstrap handler, never from `purge_workspace`.
- **Fix:** Added an explicit `_env_step(env, "foundation-ensure")` call immediately after `purge` in the new scenario, using the pre-existing `POST /api/foundation/ensure` route + its REPL mirror (`foundation-ensure` action) — no new plumbing needed. Applied the same pattern in Task 2's probe (`step_locate_scanner`).
- **Files modified:** scripts/sim_frontend.py, scripts/probe_live_duckduckgo_walkthrough.py
- **Verification:** Re-ran the scenario; the scanner node is now found among the concepts list post-purge.
- **Committed in:** 526bdf1 (Task 1), 7346dac (Task 2)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary for the scenario/probe to function at all post-purge; no scope creep — used only pre-existing routes/REPL actions.

## Issues Encountered

- An initial e2e fixture put the iterable `{ref}` target's sibling fields (`search {}` / `{paginate}`) on the iterable node's own `.children`, but `renderPanel`'s inline-expansion path for an iterable target draws ONLY from the current sample's children, never the target's own `.children` — those siblings never rendered. Fixed by moving `search {}` / `{paginate}` onto the `scanner` node itself (as true rank-1 siblings of `url {duckduckgo url}` / `dom {scan for duckduckgo url}`), matching the canonical §N tree shape exactly. Resolved before any commit; not a deviation from the committed plan.

## User Setup Required

None - no external service configuration required for Tasks 1-3 (stub-mode only). Task 4 requires the operator to perform the clean-GPU preflight and real-subsystem run manually — see CHECKPOINT below.

## Next Phase Readiness

Tasks 1-3 give Phase 7 a complete stub-mode fast gate for EXPLORE-04: the REPL scenario, the probe's self-test, and the e2e case are all green and wired into `full-smoke`. The real-subsystem acceptance proof (Task 4) is gated behind a human-verify checkpoint per D-01 (clean-GPU preflight discipline) and must be run from the MAIN context, never a subagent. Once Task 4 is approved, Phase WFH-07 (Deep Object-Exploration Gestures) is complete and the project can proceed to Phase 6 (3D Real Register) or whichever phase the roadmap schedules next.

---
*Phase: WFH-07-deep-object-exploration-gestures*
*Completed: 2026-06-27 (Tasks 1-3; Task 4 awaiting human checkpoint)*

## Self-Check: PASSED

- FOUND: scripts/probe_live_duckduckgo_walkthrough.py
- FOUND: scripts/sim_frontend.py
- FOUND: frontend_e2e/object_exploration.spec.js
- FOUND commit: 526bdf1
- FOUND commit: 7346dac
- FOUND commit: 915c35b
