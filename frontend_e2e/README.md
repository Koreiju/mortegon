# Frontend E2E (Playwright) — render-level verification

The `env-scenario` REPL contract verifies the **API + WebSocket seam** (gesture →
route → frame → store). It does **not** render a browser, so it cannot check the
§T/§U/§V *render*: black-slate styling, no-chrome DOM audit, caret-at-click,
halo paint above the slate, panel⇄graph toggle, the 3D projector. These
Playwright specs cover exactly that gap — turning "browser-verified" milestones
into **scriptable DOM/style/interaction assertions** (not screenshots-as-proof).

This is the render-level **sample** in the Planning Granularity Contract: a
Playwright `*.spec.js` assertion is the named check for a `code_constraints`
*frontend-render* task, complementary to the `env-scenario` for the seam.

## Setup (one time)

```bash
npm install                 # installs @playwright/test (devDependency)
npx playwright install chromium
```

## Run

```bash
# 1) start a backend on 8080 (stub is fine for render/DOM; real for live data)
WFH_FAKE_SLM=1 WFH_FAKE_EMBEDDER=1 NO_WEBDRIVER=1 python -m backend.main
# 2) in another shell:
npm run test:e2e
# or point at another origin:
WFH_FRONTEND_URL=http://127.0.0.1:8080 npm run test:e2e
```

## Two ways to drive the browser

| Use | Tool | When |
|---|---|---|
| **Scripted, CI / GSD-verifier** | these `*.spec.js` (Bash-runnable: `npm run test:e2e`) | the durable named check a frontend task is gated on |
| **Interactive / exploratory** | the `playwright` **MCP server** (`.mcp.json`) | an agent (or you) driving the live UI to discover assertions, debug a gesture, inspect computed styles |

GSD's `gsd-verifier` runs Bash, not MCP browser tools — so the **scripted** specs
are what it executes; the MCP server is for interactive driving during
discuss/spec (e.g. a `gsd-ui-researcher`) and manual debugging.

## Notes

- `workers: 1`, `fullyParallel: false` — the single shared backend (port 8080,
  Kuzu `_default`, Firefox singleton) cannot serve parallel browser contexts
  mutating the same workspace. Same shared-stack rule as the GSD executors.
- The "absence" specs (§11.1/§11.2) are content-agnostic and pass on any load.
  The slate-style + interaction specs self-skip on an empty workspace — scan a
  URL first (`web-scan` / a `probe_live_*`) so panels exist, then re-run.
- These are intentionally a thin starter. Fill in per-phase render criteria as
  Phase 2 (caret/IME, `+→`/`+↓`, `{`-autocomplete) and Phase 3 (halo z-order +
  token-anchored re-anchor, circular collapsed node) land.
