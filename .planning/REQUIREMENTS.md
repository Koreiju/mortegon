# Requirements: web_fiber_haptics (Mortegon) — v2.0

**Defined:** 2026-06-20
**Milestone:** v2.0 Autonomy Hardening & Maintainability
**Core Value:** Mortegon is **turnkey for GSD autonomous, continuous build/test** from
the design docs + current code — *unattended* real-stack verification is reliable, and
the codebase is agent-edit-friendly. (v1's product success metric — `all_real: true`,
full-smoke 92/92 both modes, the four lodestar probes — stays green throughout.)

> **Brownfield note.** v1.0 shipped the product to its real-stack acceptance bar
> (see `milestones/v1.0-REQUIREMENTS.md`). v2 is a **hardening + maintainability**
> milestone: it does not add product features; it removes the two things gating
> *unattended* GSD autonomy — real-stack verification reliability and monolith
> edit-friction — plus one deferred perf item. The validated v1 baseline is recorded
> in PROJECT.md "Validated"; requirements below describe the v2 gap frontier only.

## v2 Requirements

### Autonomy Hardening (the unattended-real-stack enabler)

- [ ] **HARNESS-01**: `scripts/run_full_stack_tests.py --real` reliably boots an
  `all_real:true` backend and runs **real-mode full-smoke 92/92 through the harness**
  (not only against a manually-booted `python -m backend.main`). Add a WebDriver-health
  retry + a preflight that requires a clean GPU (≈0 MiB VRAM / 0 stray python+firefox),
  clears `:8080` TIME_WAIT, and resolves Kuzu file-lock contention before bind. The
  `--real` harness must not silently come up degraded (`all_real:false`). (Phase 6;
  REQ-autonomy-real-verify; unblocks `/gsd-autonomous` real-stack acceptance.)
- [ ] **PERF-02**: GPT4All `Embed4All` Windows native instability (the access-violation
  under sustained concurrency) is hardened beyond the per-model RLock — e.g. evict-and-
  reload on fault + serialized/process-isolated embed — so `probe_no_mocks.py` and the
  lodestar probes run repeatably without a native crash on a clean GPU. (Phase 6;
  REQ-embedder-stability; carried from v1 deferred PERF-02.)

### Maintainability (agent-edit friction)

- [ ] **MAINT-01**: Split `backend/api/routes.py` (~5,425 lines) by register (scan /
  retrieval / concept / agent / maintenance) into `backend/api/` submodules; the route
  surface and behaviour are unchanged. full-smoke + e2e stay green. No resulting source
  file > ~2,000 lines. (Phase 7; carried from v1 deferred MAINT-01.)
- [ ] **MAINT-02**: Decompose `scripts/sim_frontend.py` (~9,524 lines) so a change to one
  action category does not risk the whole harness; `env-scenario --name all` stays green.
  No resulting source file > ~2,000 lines. (Phase 7; carried from v1 deferred MAINT-02.)

### Performance

- [ ] **PERF-01**: Incremental joint-UMAP refit during streaming chunk arrival (currently
  scan-end-only); `umap_canonical` frames emit incrementally mid-scan; full-smoke stays
  green; a probe asserts the mid-scan refit. (Phase 8; carried from v1 deferred PERF-01.)

## Out of Scope (v2)

| Feature | Reason |
|---------|--------|
| New product features / surfaces | v2 is hardening + maintainability only; the v1 forbidden-concepts list (D11) still holds |
| Rebuilding the working backend/frontend | Brownfield baseline is preserved, not rebuilt |
| Replacing GPT4All / nomic / Selenium / LangGraph | The no-mocks contract (§8D.46) stands; PERF-02 hardens, does not replace |
| Multi-user / auth / team | Single-operator on-device app by design |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HARNESS-01 | Phase 6 | Pending |
| PERF-02 | Phase 6 | Pending |
| MAINT-01 | Phase 7 | Pending |
| MAINT-02 | Phase 7 | Pending |
| PERF-01 | Phase 8 | Pending |

**Coverage:** v2 requirements: 5 total · mapped to phases: 5 · unmapped: 0 ✓

---
*Requirements defined: 2026-06-20 (v2.0, after v1.0 milestone archival).*
