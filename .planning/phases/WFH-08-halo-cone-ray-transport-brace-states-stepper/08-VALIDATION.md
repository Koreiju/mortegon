---
phase: 8
slug: halo-cone-ray-transport-brace-states-stepper
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-27
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `08-RESEARCH.md` § Validation Architecture. Task IDs are filled in
> after planning; the requirement→test mapping below is authoritative for Wave 0.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Node `node --test` (`backend/static/js/fe/*.test.mjs` units) + Playwright (`frontend_e2e/*.spec.js`) + Python REPL `env-scenario` (`scripts/sim_frontend.py`) + pytest (any backend additions) |
| **Config file** | `frontend_e2e/playwright.config.js` (self-boots stub backend) / direct `node --test` for `.mjs` |
| **Quick run command** | `node --test backend/static/js/fe/halo_cone.test.mjs backend/static/js/fe/stepper.test.mjs backend/static/js/fe/magic_markdown.test.mjs` (touched units) |
| **Full suite command** | `python -m scripts.sim_frontend --backend http://127.0.0.1:8080 env-scenario --name full-smoke` (both modes) + `npx playwright test` |
| **Estimated runtime** | <30s/unit · ~60–120s e2e · full-smoke minutes (both modes) · real cone-transport probe = live scan + real retrieval |

---

## Sampling Rate

- **After every task commit:** the touched `.mjs` unit file(s) via `node --test` + the relevant single `env-scenario --name <specific>` (no full-smoke per task)
- **After every plan wave:** `env-scenario --name full-smoke` (stub AND real) + `npx playwright test`
- **Before `/gsd-verify-work`:** full suite green both modes; the **D-01 real-subsystem cone-transport acceptance** (clean-GPU preflight → real scan → real triple-product cone placement → delete-transports-next-in), driven from the MAIN context (never a verifier subagent — avoids wedging a real CUDA/Selenium boot)
- **Max feedback latency:** <30s (unit), ~120s (e2e wave gate)

---

## Per-Requirement Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| HALO-03 | Backend cone math: radial/along-ray monotonic in normalized triple-product (already implemented `transport=True`/`manifold_nearest`) | unit (backend) | existing `apparition_service.py` coverage | ✅ existing | ⬜ pending |
| HALO-03 | Client composes `transport.{radial,along_ray}` + `azimuth()` → correct 3D cone position | unit | `node --test backend/static/js/fe/halo_cone.test.mjs` | ❌ W0 (new module) | ⬜ pending |
| HALO-03 | Stub cone-transport e2e green; delete-top → next-most-similar transports in | e2e | `npx playwright test halo.spec.js -g "cone"` | ❌ W0 | ⬜ pending |
| HALO-03 | LIVE cone-transport against REAL retrieval (D-01) | probe (real) | `python scripts/probe_live_*.py` (new) | ❌ W0 | ⬜ pending |
| HALO-04 | `classifyBraceStates` renders ▸/▾/solid-link in panel mode; `renderGraph`/`graphVDom` thread + draw `braceState` (closes Phase-7 gap) | unit | `node --test backend/static/js/fe/magic_markdown.test.mjs` | ⚠️ extend | ⬜ pending |
| HALO-04 | Panel↔graph node-count parity on ref reveal | e2e | `npx playwright test <halo|object_exploration>.spec.js -g "brace"` (file TBD — Open-Q4) | ❌ W0 | ⬜ pending |
| STEP-01 | `signal_advance` resolves to a 3D chunk id (the one real new-plumbing gap) | unit/integration | pytest (new) or fe lookup unit | ❌ W0 | ⬜ pending |
| STEP-01 | 2D stepper advance flies/highlights the 3D node ONE-WAY; 3D shows full distribution, never drives 2D back | unit + e2e | `node --test backend/static/js/fe/stepper.test.mjs` + `npx playwright test -g "stepper"` | ❌ W0 (new `flyToNode`) | ⬜ pending |
| STEP-01 | env-scenario telemetry for chunk-id resolution + 3D focus | REPL | `env-scenario --name signal-stream-roundtrip` (extend) | ⚠️ extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky. Task-ID columns added when the planner assigns them.*

---

## Wave 0 Requirements

- [ ] `backend/static/js/fe/halo_cone.test.mjs` — HALO-03 coordinate composition (new module)
- [ ] `backend/static/js/fe/stepper.test.mjs` — STEP-01 advance-and-focus driver (new module)
- [ ] extended `magic_markdown.test.mjs` cases — `panelVDom`/`graphVDom` branching on `braceState` (HALO-04)
- [ ] `scripts/probe_live_*.py` — D-01 real-retrieval cone-transport acceptance (new)
- [ ] planner decision (Open-Q4): cone/brace/stepper e2e in `halo.spec.js` vs `object_exploration.spec.js`
- [ ] possible new pytest for backend chunk-id resolution if Open-Q1 resolves backend-side

---

## Manual-Only Verifications

*All phase behaviors have automated verification (Node units, Playwright e2e, REPL env-scenarios, a live probe). A screenshot is not feature proof.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (the W0 files above)
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s (e2e wave gate)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
