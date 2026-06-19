# Phase 5 — Three-Register Synthesis & Live Acceptance — PLAN

> Pure verification (no build). Each task is a runnable probe/scenario; the gate
> is `all_real: true` + every live probe + `full-smoke` green both modes.

**Status legend:** ☑ done · ◑ partial · ☐ todo. **Depends on:** Phase 4 (complete).

## Tasks

### T1 — REG-01 synthesis scenarios ☑ DONE
- **Steps:** `complex-interaction-walkthrough` (rollout + halo + compile + signal in one UIState envelope) + `cascade-reflow-roundtrip` + `watch-activity-mirror` green.
- **Done-when:** all green both modes. **(stub ✓ — all exit 0; both are in `full-smoke` 92/92.)**

### T2 — ACC-02 foundation: real subsystems load (all_real) ☑ DONE
- **Steps:** boot the real backend (no `WFH_FAKE_*`) → `GET /api/subsystem_status` `all_real: true` → `probe_no_mocks.py` PASS.
- **VERIFIED 2026-06-19 (clean GPU):** `all_real: true` (Nous-Hermes + nomic on CUDA `fake_env:false`, Selenium bound, LangGraph loaded). **`probe_no_mocks.py` ALL CHECKS PASS** — real SLM (real generation, not `[stub-slm]`), real nomic (cuda, 768-dim, 768 nonzero), real Selenium, real LangGraph.

### T3 — ACC-02 lodestar (inside-out, autonomous) ☑ DONE
- **Steps:** `probe_live_concept_graph.py` (§8D.47) + `probe_live_agent.py` (§8D.48).
- **VERIFIED 2026-06-19:** **both ALL CHECKS PASS.** concept_graph — real nomic radiation, real LangGraph compile_chain, **real GPT4All in-chain** ("University libraries play a crucial role in safeguarding…"), closest-inverse (real cosines), inline cypher executed on Kuzu, rollback. agent — real meta-cognition tick (11.5s) + real streamed tokens + spawn/emit lifecycle.

### T4 — ACC-02 lodestar (outside-in + synthesis, archive.org) ☑ DONE
- **Steps:** `probe_live_archive_scan.py` (§8D.45) + `probe_live_iterated_compile.py` (§8D.49).
- **VERIFIED 2026-06-19:** **both ALL CHECKS PASS.** archive_scan — live Selenium archive.org scan (143 chunks), real retrieval ("Princeton University Library Chronicle 1940-11"), real LangGraph + GPT4All compile. iterated_compile — 3-node templated graph, real GPT4All per iteration ×3, halo + compile/collapse round-trip (5 real-cosine candidates).

### T5 — ACC-01 live-scan-with-cleanup ☑ DONE
- **Steps:** `probe_live_scan_with_cleanup.py` — purge→baseline → real scan → 6D fit → purge contract → re-scan.
- **VERIFIED 2026-06-19:** **[PASS] §16.5.** purge→baseline (`layout_dropped` + `tfidf_rows_dropped=155`) → real scan (107 chunks) → TF-IDF+nomic alive → **real UMAP 6D fit** → cleanup contract → **round1=108 / round2=101 chunks repeatability verified** (archive.org cooperated).

### T6 — full-smoke real-mode + the no-mocks contract ☑ DONE
- **Steps:** `full-smoke` green in REAL mode.
- **VERIFIED 2026-06-19:** **REAL-mode `full-smoke` — all 92 scenarios OK** against a direct `python -m backend.main` backend reporting `all_real: true` (SLM/embedder `fake_env:false`, Selenium loaded). STUB full-smoke also 92/92.
- **Harness note (follow-up, non-blocking):** `run_full_stack_tests.py --real` booted a degraded backend this session (Selenium health flaked → `all_real:false` → real-gated scenarios failed); the e2e tier passed 26/0. Running full-smoke directly against a manually-booted real backend is the reliable path. The harness's real-backend Selenium boot wants hardening (a WebDriver health retry / Firefox-lock cleanup before bind).

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

## Status (2026-06-19 — PHASE 5 COMPLETE; milestone success metric MET)
- **REG-01 (T1): DONE** — synthesis scenarios green; `full-smoke` 92/92 both modes.
- **ACC-02: DONE** — `probe_no_mocks.py` + all four lodestar `probe_live_*.py` ALL
  CHECKS PASS against `all_real: true` (real Nous-Hermes generation, real nomic,
  real Selenium archive.org scans, real LangGraph + Kuzu) + **real-mode full-smoke
  92/92**.
- **ACC-01: DONE** — `probe_live_scan_with_cleanup.py` [PASS] §16.5 (real 6D fit +
  purge contract + round1/round2 repeatability).
- **The project's success metric is MET:** `all_real: true`; `full-smoke` green in
  BOTH stub (92/92) and real (92/92) modes; all four lodestar probes pass.
- **Note:** an earlier attempt this session was environment-blocked (transient CUDA
  OOM on the 8 GB laptop GPU + long-session resource churn → a wedged backend). Once
  the machine settled to a clean GPU, every probe + real-mode full-smoke passed — it
  was never a code issue.
- **To finish ACC-01/02:** reboot the machine (clears the wedged python + frees
  VRAM) → `python -m backend.main` → confirm `slm.loaded` after a warm compile →
  run `probe_no_mocks.py`, the four `probe_live_*.py`, `probe_live_scan_with_cleanup.py`,
  and `run_full_stack_tests.py --real`. Space the archive.org scans out.
