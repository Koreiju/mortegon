---
phase: 6
slug: served-slate-3d-real-register
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-22
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `06-RESEARCH.md` § Validation Architecture. Task IDs are filled in
> after planning; the requirement→test mapping below is authoritative for Wave 0.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright `@playwright/test` 1.61.0 (e2e) + Node `node --test` (`backend/static/js/fe/*.test.mjs` pure-function units) + Python REPL `env-scenario` harness (`scripts/sim_frontend.py`) |
| **Config file** | `frontend_e2e/playwright.config.js` (e2e) / `package.json` `test:fe` script (unit) |
| **Quick run command** | `node --test backend/static/js/fe/projector.test.mjs` |
| **Full suite command** | `npm run test:e2e` AND `python scripts/sim_frontend.py env-scenario --name full-smoke` |
| **Estimated runtime** | ~5s (unit) · ~60–120s (e2e suite) · full-smoke minutes (both modes) |

---

## Sampling Rate

- **After every task commit:** Run `node --test backend/static/js/fe/projector.test.mjs` (pure ray/placement math, <5s)
- **After every plan wave:** Run `npm run test:e2e` + `python scripts/sim_frontend.py env-scenario --name 6d-umap-format` + `--name perimeter-rescale` (all must stay green)
- **Before `/gsd-verify-work`:** Full suite green in BOTH stub and `--real` modes (full real-stack inline per STATE.md verification depth)
- **Max feedback latency:** ~5s (unit), ~120s (e2e wave gate)

---

## Per-Requirement Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| REAL-01 | Chunks converge along root-URL rays; hard collider repulsion (zero force above `2·R·safety`, exact-correction below); min pairwise spacing; no Fibonacci final position | unit + e2e | `node --test backend/static/js/fe/projector.test.mjs` (ray/collider math) + `npx playwright test projector.spec.js -g "force-directed"` | ❌ W0 (extend `projector.test.mjs`; new block in `projector.spec.js`) | ⬜ pending |
| REAL-02 | Per-URL non-overlap at `existing_max + new_radius + safety_gap`; old URLs never move on a new scan; camera frames + tweens to newest root | e2e + REPL | `npx playwright test projector.spec.js -g "multi-scan"` + `python scripts/sim_frontend.py env-scenario --name perimeter-rescale` | ⚠️ partial — `perimeter-rescale` exists+green (backend contract); multi-scan e2e is ❌ W0 | ⬜ pending |
| REAL-03 | Image billboards: in-mem→IndexedDB→proxy→direct fetch order; shared `THREE.Texture` per URL; placeholder never cached; persists across re-render | e2e | `npx playwright test projector.spec.js -g "image"` (asserts IndexedDB entry survives `__mm_rerender()` with no new network request) | ❌ W0 | ⬜ pending |
| REAL-04 | Pinned panel `data-3d-node-id` drives a SOLID HEADLESS line tracking the moving node; off-frustum hides; no dotted lines | e2e | `npx playwright test projector.spec.js -g "arrow"` (new) + `npx playwright test black_slate.spec.js` (existing no-dotted regression gate, must stay green) | ⚠️ partial — `black_slate.spec.js` exists (regression gate); arrow-tracking e2e is ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky. Task-ID columns are added when the planner assigns task IDs.*

---

## Wave 0 Requirements

- [ ] `frontend_e2e/projector.spec.js` — extend with REAL-01 (ray/spacing), REAL-02 (multi-scan/camera frame), REAL-03 (image persistence), REAL-04 (arrow tracking) test blocks (currently only the UMAP-01 HSV-render test)
- [ ] `backend/static/js/fe/projector.test.mjs` — extend with pure ray-math + collider-force unit tests, mirroring the existing `buildPointArrays` test pattern
- [ ] No new live-stack probe required — REAL-01..04 ride the existing `probe_live_archive_scan.py` + `probe_live_dominance_and_timed_scan.py` (multi-scan) flows per CONTEXT.md's "consolidated real-stack acceptance run at milestone end"

---

## Manual-Only Verifications

*All phase behaviors have automated verification (Playwright DOM/computed-style assertions, Node unit tests, REPL env-scenarios). A screenshot is not feature proof — every REAL-0x claim cites an automated assertion.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (the two `❌ W0` test files above)
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s (e2e wave gate)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
