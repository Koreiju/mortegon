# Deferred Items — Phase 8 (WFH-08-halo-cone-ray-transport-brace-states-stepper)

## ~~Pre-existing Playwright/baseURL environment breakage~~ — RESOLVED (was a misdiagnosis)

**Status: RESOLVED / not a real issue.** The 08-03 executor reported that "every Playwright
e2e in `frontend_e2e/` fails" (`page.goto: Cannot navigate to invalid URL`) and attributed it to
a `@playwright/test` version drift (lockfile `1.61.0` vs `package.json` `^1.49.0`). **This
diagnosis is incorrect on two counts**, confirmed by the orchestrator:

1. **No version conflict exists.** `^1.49.0` is *satisfied by* `1.61.0` (a caret range admits any
   `1.x`). The installed/lockfile `1.61.0` is the version the suite ran green against in Phases
   6/7 and earlier in Phase 8 (08-01 brace e2e 4/4, 08-02 cone e2e 3/3, black_slate 6/6).

2. **The e2e actually passes.** On a fresh stub boot (after clearing a wedged backend on `:8080`),
   the orchestrator re-ran the exact tests the executor reported as blocked:
   - `npx playwright test halo.spec.js -g "stepper"` → **PASS** (the STEP-01 case at
     `halo.spec.js:425` — advance flies/highlights the resolved 3D node, the full distribution
     stays rendered, never driven back by a 3D action).
   - `npx playwright test black_slate.spec.js` → **6/6 PASS** (no-dotted gate intact).

**Actual cause of the executor's failure:** a transient environment/baseURL artifact in the
executor's shell (most likely a wedged/half-booted stub backend left from its own pytest +
`env-scenario` runs, the same `:8080` wedge that produced a spurious 44-minute black_slate timeout
earlier this session). `page.goto("/")` resolves correctly against `baseURL http://127.0.0.1:8080`
in a clean run. **No dependency re-pin is needed; nothing is deferred.**

**Lesson:** before treating a Playwright failure as a real regression, clear any wedged backend on
`:8080` (`Stop-Process` the listener + stray python) and re-run isolated on a fresh boot.
