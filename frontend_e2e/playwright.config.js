// Playwright config for the served magic-markdown frontend — the §T black slate
// at http://127.0.0.1:8080/ (backend/templates/editor.html + fe/*.mjs).
//
// These e2e tests verify RENDER-level acceptance (DOM structure, computed
// styles, real interactions) that the REPL / env-scenario contract structurally
// cannot reach — the REPL exercises the API + WebSocket seam; Playwright drives
// the actual served browser. Run a real (or stub) backend on 8080 first:
//   WFH_FAKE_SLM=1 WFH_FAKE_EMBEDDER=1 NO_WEBDRIVER=1 python -m backend.main
// then:  npm run test:e2e
const { defineConfig, devices } = require("@playwright/test");
const path = require("path");

const BASE = process.env.WFH_FRONTEND_URL || "http://127.0.0.1:8080";

module.exports = defineConfig({
  testDir: ".",
  testMatch: "*.spec.js",
  timeout: 30000,
  expect: { timeout: 8000 },
  fullyParallel: false, // single shared backend (port 8080, Kuzu _default) — serialize
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: BASE,
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  // Self-boot a STUB backend when none is running; reuse an existing one (e.g.
  // booted by scripts/run_full_stack_tests.py). Stub is sufficient for render —
  // run the orchestrator with --real for the all_real stack. This is what makes
  // `npm run test:e2e` self-contained.
  webServer: {
    command: `${process.env.PYTHON || "python"} scripts/_serve_for_tests.py`,
    cwd: path.join(__dirname, ".."),
    url: `${BASE}/api/scan_status`,
    reuseExistingServer: true,
    timeout: 120000,
    env: { WFH_FAKE_SLM: "1", WFH_FAKE_EMBEDDER: "1", NO_WEBDRIVER: "1" },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
