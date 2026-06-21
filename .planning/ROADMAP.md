# Roadmap: web_fiber_haptics

## Milestones

- ✅ **v1.0 Live Acceptance** — Phases 1–5 (shipped 2026-06-21) — [archive](milestones/v1.0-ROADMAP.md)
- 📋 **v2.0 Maintainability & Performance** — planned (deferred items below)

## Phases

<details>
<summary>✅ v1.0 Live Acceptance (Phases 1–5) — SHIPPED 2026-06-21</summary>

The four lodestar use cases (§8D.45/47/48/49) run end-to-end against real
subsystems (`all_real: true`); REPL `env-scenario --name all` 95/95 + Playwright
e2e 24/24 green in BOTH stub and real modes; 7 live probes pass. Full detail:
[milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md),
[milestones/v1.0-MILESTONE-AUDIT.md](milestones/v1.0-MILESTONE-AUDIT.md).

- [x] Phase 1: Honest Baseline — completed 2026-06-21 (real-verified)
- [x] Phase 2: Black-Slate Field Editing — completed 2026-06-21 (real+stub)
- [x] Phase 3: HTML Dedup + Halo Retrieval Render — completed 2026-06-21 (real+stub)
- [x] Phase 4: Live Layout, Signal & Pattern — completed 2026-06-21 (real+stub)
- [x] Phase 5: Three-Register Synthesis & Live Acceptance — completed 2026-06-21 (real acceptance)

</details>

### 📋 v2.0 Maintainability & Performance (Planned)

Deferred from v1.0 (carried in PROJECT.md / the v1.0 requirements archive):

- [ ] MAINT-01: split monolithic `backend/api/routes.py` (~5,400 lines) by register
- [ ] MAINT-02: decompose `scripts/sim_frontend.py` (~9,430 lines)
- [ ] PERF-01: incremental mid-scan UMAP refit (currently scan-end-only)
- [ ] PERF-02: harden non-thread-safe GPT4All `Embed4All` beyond the RLock mitigation
- [ ] (tech debt) wire `/api/ui/signal_advance` (SIG-01) into the served `/` editor — currently driven only from legacy `cp/concept_graph.js`

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1. Honest Baseline | v1.0 | direct | Complete | 2026-06-21 |
| 2. Black-Slate Field Editing | v1.0 | direct | Complete | 2026-06-21 |
| 3. HTML Dedup + Halo Retrieval Render | v1.0 | direct | Complete | 2026-06-21 |
| 4. Live Layout, Signal & Pattern | v1.0 | direct | Complete | 2026-06-21 |
| 5. Three-Register Synthesis & Live Acceptance | v1.0 | direct | Complete | 2026-06-21 |

---
*v1.0 shipped 2026-06-21 — see [MILESTONES.md](MILESTONES.md). Next: `/gsd-new-milestone` for v2.0.*
