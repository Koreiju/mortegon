# Phase 5 — Three-Register Synthesis & Live Acceptance — PLAN

> Pure verification (no build). Each task is a runnable probe/scenario; the gate
> is `all_real: true` + every live probe + `full-smoke` green both modes.

**Status legend:** ☑ done · ◑ partial · ☐ todo. **Depends on:** Phase 4 (complete).

## Tasks

### T1 — REG-01 synthesis scenarios ☑ DONE
- **Steps:** `complex-interaction-walkthrough` (rollout + halo + compile + signal in one UIState envelope) + `cascade-reflow-roundtrip` + `watch-activity-mirror` green.
- **Done-when:** all green both modes. **(stub ✓ — all exit 0; both are in `full-smoke` 92/92.)**

### T2 — ACC-02 foundation: real subsystems load (all_real) ◑ all_real ✓; SLM-load env-blocked
- **Steps:** boot the real backend (no `WFH_FAKE_*`) → `GET /api/subsystem_status` `all_real: true` → `probe_no_mocks.py` PASS.
- **Verified 2026-06-19:** real backend booted → **`all_real: true`** (Nous-Hermes + nomic on CUDA `fake_env:false`, Selenium bound, LangGraph loaded; both GGUFs present on disk). **Real nomic retrieval CONFIRMED** — `probe_live_concept_graph` got 6 apparitions with REAL nomic cosines (0.66/0.65/…) via the backend HTTP path.
- **Env-blocked:** the **7B SLM CUDA load OOM'd transiently** (8GB laptop GPU contended by the session's chromium/Firefox/in-process embedder), then the env saturated (system MemoryError → uvicorn-reload crash-loops → Kuzu lock contention → uninterruptible wedged backend). `probe_no_mocks`'s in-process `Embed4All` also hit the known Windows native access-violation (PERF-02). **NOT a code regression** — these passed clean on 2026-06-15. Needs a fresh-boot machine.

### T3 — ACC-02 lodestar (inside-out, autonomous) ◑ env-blocked
- **Steps:** `probe_live_concept_graph.py` (§8D.47) + `probe_live_agent.py` (§8D.48).
- **Status:** `probe_live_concept_graph` ran the real path — real nomic radiation ✓, real LangGraph compile_chain ✓ — and FAILED only at the GPT4All prompt node (`rendering: ''`) because the **7B SLM never loaded** (CUDA OOM → "prompt won't work with an unloaded model"). Re-run on a fresh boot with free VRAM. Prev-passed 2026-06-15.

### T4 — ACC-02 lodestar (outside-in + synthesis, archive.org) ☐ real-stack, fresh boot
- **Steps:** `probe_live_archive_scan.py` (§8D.45) + `probe_live_iterated_compile.py` (§8D.49).
- **Status:** not attempted this session (the SLM/env block makes it moot until T2/T3 clear). Prev-passed 2026-06-15. Space scans out (archive.org throttles).

### T5 — ACC-01 live-scan-with-cleanup ☐ real-stack, fresh boot
- **Steps:** `probe_live_scan_with_cleanup.py` — purge→baseline → real scan → 6D fit → purge contract → re-scan.
- **Status:** prev-passed 2026-06-12 (first ever); the round1≈round2 assertion needs archive.org not throttling. Re-run on a fresh boot.

### T6 — full-smoke real-mode + the no-mocks contract ◑ stub ✓; real-mode fresh boot
- **Steps:** `full-smoke` green in REAL mode.
- **Status:** **STUB full-smoke 92/92 green** (this session, via the framework). REAL-mode full-smoke needs the wedged backend cleared (fresh boot). Prev real-mode `all` (95) green 2026-06-15.

## Coverage (req → task)

| Req | Tasks |
|---|---|
| REG-01 | T1 ☑ |
| ACC-01 | T5 |
| ACC-02 | T2, T3, T4, T6 |

## Phase gate
`GET /api/subsystem_status` reports `all_real: true`; the four lodestar
`probe_live_*.py` + `probe_no_mocks.py` + `probe_live_scan_with_cleanup.py` PASS;
`full-smoke` green in BOTH stub and real modes. **This is the project's success
metric — the milestone completes here.**

## Status (2026-06-19)
- **REG-01 (T1): DONE** — synthesis scenarios green (stub), in `full-smoke` 92/92.
- **ACC foundation: PARTIAL** — `all_real: true` CONFIRMED + real nomic retrieval
  CONFIRMED (real cosines via the backend). The **7B SLM live-generation probes
  (T3–T5) are environment-blocked this session**: a transient CUDA OOM on the 8GB
  laptop GPU stopped the 7B model from loading, then the long session's accumulated
  processes saturated the machine (system MemoryError → uvicorn-reload crash-loops →
  Kuzu lock contention → an uninterruptible wedged backend on :8080). These are
  ENVIRONMENT issues, not code — the same probes passed clean on 2026-06-15.
- **To finish ACC-01/02:** reboot the machine (clears the wedged python + frees
  VRAM) → `python -m backend.main` → confirm `slm.loaded` after a warm compile →
  run `probe_no_mocks.py`, the four `probe_live_*.py`, `probe_live_scan_with_cleanup.py`,
  and `run_full_stack_tests.py --real`. Space the archive.org scans out.
