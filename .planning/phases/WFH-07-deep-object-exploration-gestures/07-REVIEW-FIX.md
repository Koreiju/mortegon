---
phase: WFH-07-deep-object-exploration-gestures
review: 07-REVIEW.md
fixed: [WR-01, WR-03]
deferred: [WR-02, WR-04, WR-05, INFO-01, INFO-02, INFO-03, INFO-04]
status: partial-fix
date: 2026-06-27
---

# Phase 7 Code-Review Fix Record

Code review (07-REVIEW.md): **0 critical, 5 warnings, 4 info.** No blocker — the
load-bearing contracts (route ordering static-before-parametric, `_inherit_io_types`
idempotency + self-edge guard, the 400 source/target validation, solid lines / no
`stroke-dasharray`, the probe's `all_real` gate with no stub fallback) all held under
review. Phase 7 was already complete + verified (07-VERIFICATION.md, passed 4/4) and the
real D-01 acceptance passed — these are advisory quality fixes.

## Fixed (2 — the correctness/safety warnings)

- **WR-03 — 🔒 gate now also refuses the destructive double-right DELETE on read-only
  nodes** (`magic_markdown_panel.mjs` contextmenu handler). The lock previously guarded
  only single-left edit; double-right could delete a row of a read-only python-native /
  fixture node. Per object_exploration.md §4, read-only nodes permit *exploration*
  (single-right fold still fires) but not deletion. Verified: panel unit 19/19 (the
  read-only cases — fold still fires — stay green); e2e 9/9; black_slate 6/6.
- **WR-01 — drag teardown on abort/restart** (`magic_markdown_panel.mjs` mousedown +
  mouseleave). A drag released *outside* the host (or a fresh mousedown over a stale
  drag) previously leaked `dragState` + an orphaned `<line>`. Now `mousedown` calls
  `teardownDrag()` before starting, and `mouseleave` tears down an in-progress drag (not
  just a not-yet-started press). Verified: e2e drag-wire case still green (solid line
  drawn during drag, torn down on mouseup).

Both fixes verified: `node magic_markdown_panel.test.mjs` 19/19; `npx playwright test
object_exploration.spec.js black_slate.spec.js` 15/15.

## Deferred (3 warnings + 4 info — lower severity, documented for a follow-up)

- **WR-02 — gateway array-send partial-failure** (`gateway.mjs`): a DELETE_REF fires
  edge-delete then value-clear sequentially with no rollback if the second fails (could
  leave a dangling `{ref}`). Rare in practice (both hit the same local backend); fixing
  it well needs a transactional/compensating-write design on `GestureGateway.send` — a
  scoped follow-up, not a phase-7 correctness gap that any test exercises.
- **WR-04 — `next_rank` ignores the `source_id` query filter** (`routes.py`): it scans up
  to 50000 edges and truncates silently rather than filtering server-side. A
  perf/completeness improvement for very large graphs (the current materialised trees are
  small); the route is functionally correct for the tested sizes.
- **WR-05 — `_inherit_io_types` re-reports already-existing (idempotent) edges as freshly
  inherited on a retry** (`routes.py`): a telemetry/reporting cosmetic — the underlying
  create is correctly deduped on the five-tuple natural key (no duplicate edges), only the
  "inherited N" count over-reports on a repeat call.
- **INFO** (4): the double-right's intentional first-click fold (codified by a test);
  `workspace_id=""` default vs `_default`; `assert_shadow_dom_present` exercised only by
  the self-test; the drag SVG-host `|| dom` fallback in panel mode (drag is graph-mode
  only). None are behavior bugs in the tested paths.

These are tracked here for a future maintenance/hardening pass; none block Phase 7, whose
goal is verified achieved.
