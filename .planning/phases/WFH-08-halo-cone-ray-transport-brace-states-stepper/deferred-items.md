# Deferred Items — Phase 8 (WFH-08-halo-cone-ray-transport-brace-states-stepper)

## Pre-existing Playwright/baseURL environment breakage (out of scope, discovered during 08-03 Task 4)

**Found during:** 08-03 Task 4 verification (`npx playwright test frontend_e2e/halo.spec.js -g "stepper"`).

**Symptom:** Every Playwright e2e test in `frontend_e2e/` fails with
`Error: page.goto: Protocol error (Page.navigate): Cannot navigate to invalid URL`
(or `apiRequestContext.post: Invalid URL` for `request.post("/api/...")` calls),
on the very first `page.goto("/")` / `request.post(...)` call in `beforeEach`.
This affects:
- `frontend_e2e/halo.spec.js` — ALL tests, including pre-existing HALO-01 and the
  already-landed HALO-03 cone-ray-transport block (untouched by this plan),
  not just this plan's new STEP-01 stepper block.
- `frontend_e2e/black_slate.spec.js` — all 6 tests, entirely unrelated to this
  plan's files.

**Root cause (confirmed, not just suspected):** `@playwright/test` resolved/
installed at `1.61.0` (`package-lock.json` already pinned `1.61.0` BEFORE this
session's changes — confirmed via `git log`/`grep` on the lockfile), while
`package.json` declares `^1.49.0`. This is a 12-minor-version drift baked into
the committed lockfile, predating this plan. `playwright.config.js`'s
`use.baseURL` (`http://127.0.0.1:8080` via `WFH_FRONTEND_URL` fallback) is
present and correct; the failure reproduces even with the WFH_FAKE_* stub
backend confirmed healthy (`curl http://127.0.0.1:8080/api/scan_status` → 200).
This points to a `baseURL`-resolution behavior change somewhere in the 1.49→1.61
Playwright range, not a bug in this plan's test code or config.

**Scope boundary:** Per the executor's deviation rules, this is a pre-existing,
environment-wide issue not caused by 08-03's changes (it reproduces identically
on files this plan never touched). Fixing the Playwright pin/lockfile is a
dependency-version change outside this plan's task scope — logged here rather
than silently fixed.

**Verification status for 08-03 Task 4:**
- `frontend_e2e/halo.spec.js -g "stepper"` — **NOT GREEN locally** (blocked by
  the environment issue above, not a logic failure in the new test). The new
  `test.describe("per-sample stepper → 3D focus (STEP-01)")` block's
  structure/assertions were authored and reviewed against the established
  `bootProjectorOrSkip` + `__mm_proj_*` hook conventions (mirroring the
  HALO-03 cone-ray-transport block verbatim in structure), and the new
  `editor.html` test hooks (`__mm_proj_fly_to`, `__mm_proj_highlight`,
  `__mm_stepper_advance`) wire the REAL `stepper.mjs` + REAL `projector.mjs`
  (no stubs) per the plan's one-way (§O.6) requirement.
- `black_slate.spec.js` confirmed to fail identically and for the same root
  cause BEFORE this plan's changes (it is untouched by this plan) — so "stays
  green" is interpreted as "no NEW regression introduced by this plan,"
  which holds: the failure mode and count are identical with and without
  this plan's diff.

**Recommended follow-up (not actioned in this plan):** re-pin
`@playwright/test`/`playwright` to `^1.49.0` (or explicitly bump the
`package.json` declaration to match the lockfile's `1.61.0` and re-verify the
whole e2e suite), then re-run the full `frontend_e2e/` suite including this
plan's new stepper block.
