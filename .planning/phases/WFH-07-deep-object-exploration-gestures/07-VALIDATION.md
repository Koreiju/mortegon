---
phase: 7
slug: deep-object-exploration-gestures
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-23
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `07-RESEARCH.md` § Validation Architecture. Task IDs are filled in
> after planning; the requirement→test mapping below is authoritative for Wave 0.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Node built-in `assert` + custom `test()` harness (`backend/static/js/fe/*.test.mjs` pure-logic) + Playwright (`frontend_e2e/*.spec.js`) + Python REPL `env-scenario` (`scripts/sim_frontend.py`); pytest for any backend additions (confirm config during planning — no `pytest.ini`/`pyproject[tool.pytest]` found) |
| **Config file** | `frontend_e2e/playwright.config.js` (self-boots stub backend via `scripts/_serve_for_tests.py`, `WFH_FAKE_SLM=1 WFH_FAKE_EMBEDDER=1 NO_WEBDRIVER=1`, reuses :8080 if up) |
| **Quick run command** | `node backend/static/js/fe/magic_markdown_gestures.test.mjs` (and the other touched `.test.mjs` files) — each <30s |
| **Full suite command** | `python -m scripts.sim_frontend env-scenario --name full-smoke --backend http://127.0.0.1:8080` (both modes) + `npm run test:e2e` |
| **Estimated runtime** | <30s/unit · ~60–120s e2e · full-smoke minutes (both modes) · real DuckDuckGo probe = live Selenium scan |

---

## Sampling Rate

- **After every task commit:** Run the specific `.test.mjs` file(s) touched (<30s)
- **After every plan wave:** `python -m scripts.sim_frontend env-scenario --name full-smoke` (stub AND real) + `npm run test:e2e`
- **Before `/gsd-verify-work`:** Full suite green stub AND real; the `duckduckgo-walkthrough` REPL scenario AND its `probe_live_*` counterpart pass against REAL subsystems (D-01), clean-GPU pre-flight verified immediately beforehand
- **Max feedback latency:** <30s (unit), ~120s (e2e wave gate)

---

## Per-Requirement Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| EXPLORE-01 | Hover reveals next-rank type graph (super-class + typed params); function rows show typed I/O (output inferred by i/o equality) | unit + e2e | `node backend/static/js/fe/magic_markdown.test.mjs` (extend, typed render) + `npx playwright test object_exploration.spec.js -g "hover"` (new) + `env-scenario --name ontology-walk` | ❌ W0 (typed-render unit + e2e net-new) | ⬜ pending |
| EXPLORE-02 | External `{ref}` propagates as recursively-rendered rank-1 panel; duplicate-instance proxy (N.6) | unit + e2e | `node backend/static/js/fe/integration.test.mjs` (fold-propagation already covered; extend for duplicate-instance) + new ref-propagation e2e | ⚠️ partial — model fold-loop covered; duplicate-instance + e2e ❌ W0 | ⬜ pending |
| EXPLORE-03 | Drag-wire creates edge + inherits I/O types (N.4); double-right deletes ref/instance (N.13); fold-state preserved (M.6) | unit + REPL + e2e | `node backend/static/js/fe/magic_markdown_gestures.test.mjs` + `magic_markdown_panel.test.mjs` (new DOM-capture cases) + REPL `editor-link`/`editor-delete` + `panel-gesture-fold-roundtrip` + new drag-wire/delete e2e | ⚠️ partial — resolver-level cases exist; DOM-capture + backend type-inheritance + e2e ❌ W0 | ⬜ pending |
| EXPLORE-04 | DuckDuckGo §N walkthrough end-to-end against REAL subsystems (D-01) | REPL env-scenario + live probe | `python -m scripts.sim_frontend env-scenario --name duckduckgo-walkthrough` (stub fast-gate) + `python scripts/probe_live_duckduckgo_walkthrough.py` (REAL acceptance) | ❌ W0 — neither scenario nor probe exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky. Task-ID columns added when the planner assigns them.*

---

## Wave 0 Requirements

- [ ] `frontend_e2e/object_exploration.spec.js` — new e2e (hover-type-graph, ref-propagation, drag-wire+delete, brace-state)
- [ ] typed `key:Type=value` render-mode unit cases in `magic_markdown.test.mjs` (or new `magic_markdown_typed.test.mjs`)
- [ ] `magic_markdown_panel.test.mjs` cases for the new `mount()` DOM handlers (contextmenu, double-right debounce, drag state machine) — confirm DOM harness/JSDOM need during planning
- [ ] `duckduckgo-walkthrough` REPL env-scenario in `scripts/sim_frontend.py` (model from `_env_scenario_node_fold_roundtrip`)
- [ ] `scripts/probe_live_duckduckgo_walkthrough.py` (model from `probe_python_api.py` assertions + `probe_live_archive_scan.py` real-Selenium pattern)
- [ ] Backend: rank-1 type-graph fetch endpoint + test coverage (D-03)
- [ ] Backend: edge-create I/O-type-inheritance extension + test coverage (D-03; `EditorLinkRequest` currently has no type/ports/inherit field — N.4 has no server impl today)

---

## Manual-Only Verifications

*All phase behaviors have automated verification (Node unit, Playwright e2e DOM/computed-style, REPL env-scenarios, live probe). A screenshot is not feature proof — every EXPLORE-0x claim cites an automated assertion.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (the W0 files above)
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s (e2e wave gate)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
