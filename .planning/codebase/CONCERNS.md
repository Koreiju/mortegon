# Codebase Concerns

**Analysis Date:** 2026-06-20
**Context:** Refresh after the v1 milestone (all 5 GSD phases COMPLETE; real-stack acceptance PASS — `all_real:true`, `full-smoke` 92/92 both modes, all four lodestar `probe_live_*.py` green, `probe_live_scan_with_cleanup` green). This document captures what remains a real concern going into v2 (MAINT-01/02, PERF-01/02), verified directly against code and `.planning/STATE.md`, not invented.

## How to read this document

Concerns are split by **what gates unattended autonomous verification** vs **what is safe today**:

- **Stub mode is fully deterministic and safe for autonomous agents.** `full-smoke` 92/92, e2e 26/0, no GPU/Selenium required, no flakiness observed.
- **Real-stack mode (`all_real:true`) is NOT safe for unattended autonomous runs** on the current hardware (8 GB laptop GPU) without a human first confirming a clean GPU/process state. See "Real-Stack Environment Fragility — gates autonomy" below; every item there is a hard blocker to running real-mode verification unattended.

---

## Tech Debt

**Monolithic route file:**
- Issue: `backend/api/routes.py` is ~5,425 lines — every REST endpoint in the system (concepts, edges, scan, compile, agent, ui/signal, ontology, maintenance, etc.) lives in one module.
- Files: `backend/api/routes.py`
- Impact: agent-edit friction — any change risks merge collisions and makes it hard to scope a diff to one feature; review/diff noise on routine changes; no natural seam for splitting ownership.
- Fix approach: tracked as **MAINT-01** (v2). Split by resource/feature area (concepts, edges, scan/ingestion, compile, agent, ui-signal, ontology, maintenance) into `backend/api/routes/*.py` submodules behind one router aggregator; keep one edge table / one lifecycle dispatcher contract intact across the split.

**Monolithic REPL harness:**
- Issue: `scripts/sim_frontend.py` is ~9,524 lines — the REPL harness covering ~160+ actions across 19 categories plus the `env-scenario` contract (92 scenarios) plus `watch-activity`.
- Files: `scripts/sim_frontend.py`
- Impact: same agent-edit friction as routes.py; adding one new scenario requires navigating a single huge file; risk of accidental scenario-registry corruption.
- Fix approach: tracked as **MAINT-02** (v2). Split scenario registrations and action categories into per-category modules (`scripts/repl/<category>.py`) imported into one dispatcher; preserve the single `env-scenario --name full-smoke` entry point and scenario count.

**`backend/analytics/` is load-bearing but co-located with formerly-forbidden code's old home:**
- Issue: the forbidden graph-analytics retrieval framework and hyperbolic 3D layout were removed (CODEBASE_AUDIT G8), but `backend/analytics/` still holds genuinely-used utilities (`pq_tree`, `loop_closure`, `segment_embedder` — ~620 lines total) imported by `routes.py`/`dom`/`mapper`/`chat`/`retrieval`.
- Files: `backend/analytics/` (per `.planning/STATE.md` Blockers/Concerns)
- Impact: any future cleanup pass risks re-deleting load-bearing code by pattern-matching the directory name against the forbidden-concepts list. The `chunk_builder` hyperbolic-distance *clustering* metric (a scan-time algorithm, not a layout) remains flagged for design review (task `e6b4743c`) — unresolved ambiguity between "forbidden hyperbolic layout" and "permitted hyperbolic clustering metric."
- Fix approach: keep the FIX-01 distinction documented inline (module docstrings) so future passes don't re-litigate; resolve task `e6b4743c`'s design review before any further analytics-tree edits.

**Deprecated/dual chunk-id scheme:**
- Issue: a known `c_<hash>` vs `c_<hash>_<hash>` id-scheme mismatch in the deprecated `chunk_search` retrieval path causes desync after a workspace accumulates churn from multiple scans.
- Files: `backend/services/global_tfidf_store.py`, `backend/api/routes.py` (chunk_search handlers), `backend/static/js/cp/search.js`
- Impact: `scripts/probe_live_iterated_compile.py` was observed to fail when run against a churned (multi-scan) workspace; a clean purge+scan fixes it (per `.planning/STATE.md` Phase 3 progress notes, 2026-06-15).
- Fix approach: purge to a clean baseline before iterated-compile-style live probes; longer-term, unify the id scheme so churned workspaces don't desync (not yet scheduled — no v2 ticket exists for this specifically; recommend filing one).

---

## Known Bugs

**None currently open against the v1 surface.** Full pytest suite is 336 passed / 2 skipped / 0 failed in stub mode (`.planning/STATE.md`, 2026-06-14 measurement — re-verify before relying on this number after future code changes). The "14 ledgered legacy failures" note from an earlier pass was superseded; there is no current red to normalize.

**Archive.org rate-limiting masquerading as a repeatability failure:**
- Symptoms: `probe_live_scan_with_cleanup.py`'s round1≈round2 chunk-count repeatability assertion failed once with round1=92 vs round2=11 chunks.
- Files: `scripts/probe_live_scan_with_cleanup.py`
- Trigger: rapid successive real scans of `archive.org` within the same session — the site bot-throttles. NOT a code regression; a single clean scan reliably streams ~91-108 chunks (later reruns confirmed 108/101, per STATE.md Phase 5).
- Workaround: space out live archive.org scans; never run this probe twice back-to-back in automation without a cooldown.

---

## Real-Stack Environment Fragility — gates autonomy

These items are the practical reason **unattended autonomous real-stack (`all_real:true`) verification cannot be safely scheduled without a human gate today.** Stub mode is unaffected by all of them.

**GPU memory contention (CUDA OOM):**
- Risk: on an 8 GB laptop GPU, the 7B GPT4All SLM (`Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf`) CUDA-loads ~3.8 GiB. Concurrent load of headful Firefox/geckodriver (`backend/drivers/geckodriver.exe`) and the nomic `Embed4All` embedder can push total VRAM+RAM+handle usage over budget, causing transient CUDA OOM.
- Files: SLM loader in `backend/services/` (e.g. `slm_client.py`), `backend/services/embedding_service.py`, `backend/drivers/geckodriver.exe`
- Mitigation: a clean GPU (0 MiB VRAM, 0 python processes) is required before every real-stack run. No code-level fix exists yet; this is a hardware-headroom constraint, not a bug.
- **Gates autonomy:** yes — an autonomous agent cannot detect "is the GPU clean" without an explicit pre-flight check, and cannot safely free VRAM held by another process without risking the user's other work.

**`Embed4All` Windows native access-violation under concurrency (PERF-02, not fixed — mitigated only):**
- Risk: GPT4All's native embedder is NOT thread-safe on Windows; concurrent `embed()` calls on the same model handle raise `OSError: exception: access violation` or abort the process with a `GGML_ASSERT`.
- Files: `backend/services/embedding_service.py` (`_get_model_lock` defines a per-model-name `threading.RLock`; comments explicitly state "the native GPT4All embedder is not thread-safe... an access violation (recoverable) or GGML_ASSERT (aborts the process)"; a capped-truncation step exists ahead of the embed call as an additional mitigation)
- Mitigation in place: a re-entrant `threading.RLock` per model name serializes all `embed()` calls. This reduces but does NOT eliminate risk — the RLock only protects calls made through this code path; any other concurrent native access (e.g. a second process, or a code path that bypasses the lock) can still trigger the access violation.
- Deferred to v2 as **PERF-02**.
- **Gates autonomy:** yes — a process abort (GGML_ASSERT) during an unattended run kills the backend with no graceful recovery; an autonomous agent has no way to distinguish this from a code regression without a human checking process state.

**Wedged uninterruptible backends + orphaned Firefox processes:**
- Risk: long sessions (especially ones that hit CUDA OOM or an access violation) leave the `python -m backend.main` process in an uninterruptible state and/or orphaned Firefox/geckodriver processes running, both consuming VRAM/RAM that blocks the next clean run.
- Mitigation: `taskkill /F /PID` to force-clear wedged python; manually verify 0 MiB VRAM / 0 python processes before each real-stack run (per `.planning/STATE.md` Phase 5 "Lesson").
- **Gates autonomy:** yes — there is no automated health-check + auto-recovery in the harness; an autonomous agent would need explicit permission and tooling to forcibly kill processes, which is a destructive action outside normal agent authority.

**Port `:8080` TIME_WAIT + Kuzu file-lock contention on restart:**
- Risk: backend default port is 8080 (`backend/main.py`); after a backend exits, the socket can sit in TIME_WAIT, blocking an immediate re-bind. Kuzu's file-based store (≥0.11, nests as `kuzu_db/data.kuzu` via `backend/database.py::_effective_db_path`) can also hold a file lock across process exit if not cleanly released.
- Files: `backend/main.py`, `backend/database.py`
- Mitigation: wait for TIME_WAIT to clear, or use `--port 8081`/an alternate port; per `.planning/STATE.md` Blockers, a leftover stub Microsoft-Store-python backend has previously held port 8080 and required ending the process via Task Manager.
- **Gates autonomy:** partial — an autonomous agent can retry on an alternate port, but cannot reliably distinguish "TIME_WAIT, just wait" from "another real backend is intentionally running" without risking killing a process it doesn't own.

**Port drift between backend default and REPL default:**
- Risk: `backend/main.py` defaults to port 8080; `scripts/sim_frontend.py`'s `--backend` CLI default is `http://localhost:8000` (env override `WFH_BACKEND_URL`). Running the REPL without `--backend http://127.0.0.1:8080` silently talks to nothing (or to the wrong service) on the default port.
- Files: `backend/main.py`, `scripts/sim_frontend.py` (argparse default for `--backend`)
- Mitigation: always pass `--backend http://127.0.0.1:8080` as a global flag BEFORE the subcommand, or set `WFH_BACKEND_URL`.
- **Gates autonomy:** low risk if documented and followed, but an autonomous agent invoking the REPL without reading this constraint first will get silent connection failures rather than a clear error.

**`run_full_stack_tests.py --real` harness's own backend boot is flaky:**
- Risk: the harness's automated backend boot has a flaky Selenium health check that intermittently fails, causing the harness-launched backend to report `all_real:false` even when a manually-booted backend on the same machine would report `all_real:true`.
- Files: `scripts/run_full_stack_tests.py`
- Mitigation (documented, not a code fix): do NOT rely on `python scripts/run_full_stack_tests.py --real` for real-mode verification. Instead, manually boot `python -m backend.main` (no fake-env gates) and run `full-smoke`/probes directly against it.
- Deferred to v2 as a named follow-up: "harden the `run_full_stack_tests.py --real` harness Selenium boot" (`.planning/STATE.md` Next).
- **Gates autonomy:** yes — this is the single biggest concrete blocker to a *fully automated* real-stack run: the one harness designed to automate the boot-and-verify sequence cannot be trusted to self-report correctly, so a human must currently run the boot-and-verify steps by hand and read the `/api/subsystem_status` output directly.

**Frontend ES-module caching masks source changes in long-lived browser sessions:**
- Risk: a browser tab left open across a code change can serve stale ES modules from cache, making it look like a fix didn't take effect (a verification gotcha, not a runtime bug).
- Files: any `backend/static/js/**/*.mjs` module served at `/`
- Mitigation: hard-refresh / new tab / disable cache when manually re-verifying frontend changes in a long-lived session.
- **Gates autonomy:** no direct gate (this affects human manual verification more than automated test runs, since Playwright specs launch fresh browser contexts), but worth flagging if an autonomous agent is ever asked to drive a persistent browser session for verification.

---

## Security Considerations

**No env-var leak vectors found in the explored surface.** `.env`-style secrets were not located in tracked files. The GGUF model path / CUDA device selection are configured via plain env vars (`WFH_SLM_MODEL`, `WFH_SLM_DEVICE`, `WFH_EMBEDDER_DEVICE`, `WFH_DB_PATH`) with no embedded credentials.

**`WFH_FAKE_SLM` / `WFH_FAKE_EMBEDDER` / `NO_WEBDRIVER` are harness-only env knobs:**
- Risk: if any of these were accidentally set in a production deployment, the system would silently run on deterministic stubs instead of the real subsystems — directly violating the no-mocks contract (§8D.46).
- Files: SLM/embedder service modules in `backend/services/`, backend boot path (`backend/main.py`)
- Mitigation: `GET /api/subsystem_status` reports `all_real` and CI is supposed to assert this before contract-bearing scenarios run (per CLAUDE.md). No code-level guard prevents these env vars from being set in production beyond operator discipline.
- Recommendation: consider an explicit production-mode assertion at boot that hard-fails if any `WFH_FAKE_*` or `NO_WEBDRIVER` var is set and a "production" flag is also set, rather than relying purely on operator discipline.

---

## Performance Bottlenecks

**Embedder concurrency serialization (see PERF-02 above):**
- Problem: the per-model RLock serializes ALL `embed()` calls system-wide, meaning concurrent scan-time chunk embedding and concept-side nomic embedding compete for the same lock even though they're conceptually independent pipelines.
- Files: `backend/services/embedding_service.py`
- Cause: native GPT4All `Embed4All` is not thread-safe on Windows; the lock is the only available mitigation.
- Improvement path: tracked as v2 PERF-02. Investigate a process-pool or queue-based embedding worker to avoid serializing within one process, or batch embed calls to amortize lock-acquisition overhead.

**No incremental mid-scan UMAP refit (PERF-01, deferred to v2):**
- Problem: per `.planning/STATE.md` Deferred Items, UMAP joint-fit for chunk layout currently refits at scan-end rather than incrementally as chunks stream in.
- Files: backend layout/projection service (UMAP fit logic per the architectural "Layout Service" component described in CLAUDE.md)
- Cause: incremental UMAP refit is a known harder algorithmic problem (re-fitting without full recompute); not yet implemented.
- Improvement path: tracked as v2 **PERF-01**. No further detail captured in this pass beyond the existing deferral.

---

## Fragile Areas

**`backend/api/routes.py` (5,425 lines) and `scripts/sim_frontend.py` (9,524 lines):**
- Files: `backend/api/routes.py`, `scripts/sim_frontend.py`
- Why fragile: single-file size makes it easy to introduce an unrelated regression while editing a nearby unrelated route/scenario; no enforced internal module boundaries.
- Safe modification: before editing, grep for the specific route/scenario name first to scope the read; after editing, always re-run the full `full-smoke` 92/92 (stub) gate, not just the touched scenario, since there's no structural isolation preventing cross-talk.
- Test coverage: full-smoke + e2e suites do cover this surface end-to-end, which is the main reason fragility hasn't yet produced regressions — the coverage is broad even though the file structure is not modular.

**Real-stack process lifecycle (backend + Selenium + CUDA):**
- Files: `backend/main.py`, `backend/drivers/geckodriver.exe`, `backend/database.py`
- Why fragile: no automated supervisor restarts a wedged process; recovery is manual (`taskkill /F /PID`, wait for TIME_WAIT, confirm 0 VRAM).
- Safe modification: never chain multiple real-stack probe runs back-to-back without an explicit clean-state check between them; always run `GET /api/subsystem_status` first to confirm `all_real:true` before trusting any probe result.
- Test coverage: stub mode has full coverage and zero process-lifecycle fragility (no CUDA/Selenium dependency); real-stack mode has been proven to pass (all four lodestar probes + cleanup probe), but only ever as a human-supervised, one-at-a-time sequence — never as an automated unattended batch.

---

## Scaling Limits

**Single-GPU, single-machine real-stack ceiling:**
- Current capacity: one 7B SLM + one embedder + one headful browser instance fit (barely) in 8 GB VRAM when nothing else is competing.
- Limit: any concurrent real-stack workload (e.g. two scans, or a scan + an agent tick, both wanting SLM/embedder access simultaneously) risks OOM or the access-violation failure mode described above.
- Scaling path: not in scope for v1/v2 per current roadmap; would require either a bigger GPU, model quantization changes, or moving to a queued single-consumer architecture for SLM/embedder access (the RLock already partially forces this, but at the cost of throughput).

---

## Dependencies at Risk

**None newly identified this pass.** `kuzu` was already bumped 0.3.2 → 0.11.3 (HYG-01, done) and its file-based nesting behavior (`kuzu_db/data.kuzu`) is understood and documented (`backend/database.py::_effective_db_path`). `@mdxeditor/editor` was already removed (HYG-02, done). No other dependency-risk items surfaced in this pass.

---

## Missing Critical Features

**None identified as blocking v1.** The four lodestar use cases (§8D.45/47/48/49) all pass on the real stack; this is a "what's fragile/debt" audit, not a feature-gap audit (see `.planning/codebase/` other docs and `REQUIREMENTS.md` for feature scope).

---

## Test Coverage Gaps

**Real-mode `full-smoke` and live probes have no automated unattended runner (see harness flakiness above):**
- What's not tested automatically: the real-stack acceptance gate currently requires a human to manually boot the backend and read `/api/subsystem_status` before trusting any `probe_live_*.py` result, because `run_full_stack_tests.py --real`'s own boot health-check is flaky.
- Files: `scripts/run_full_stack_tests.py`, `scripts/probe_live_archive_scan.py`, `scripts/probe_live_concept_graph.py`, `scripts/probe_live_agent.py`, `scripts/probe_live_iterated_compile.py`, `scripts/probe_live_scan_with_cleanup.py`, `scripts/probe_live_dominance_and_timed_scan.py`, `scripts/probe_no_mocks.py`
- Risk: a future regression in real-stack behavior could go undetected for longer than a stub-only regression, since real-stack verification cadence is gated by human availability and a clean-GPU precondition rather than CI.
- Priority: **High** for any plan to schedule autonomous/unattended real-stack verification; **Low** for day-to-day stub-mode development, which is unaffected.

**`chunk_builder` hyperbolic-distance clustering metric — unresolved design-review flag:**
- What's not tested: there is no test asserting the boundary between "permitted hyperbolic clustering metric" (kept) and "forbidden hyperbolic 3D layout" (removed) — the distinction currently lives only in a deferred design-review task (`e6b4743c`), not in an automated guard.
- Files: `backend/analytics/` (chunk_builder hyperbolic-distance logic), forbidden-concepts guard tests under `backend/tests/`
- Risk: a future contributor (human or agent) could reintroduce a hyperbolic *layout* by extending the still-present hyperbolic *clustering* code, since no automated test currently distinguishes the two.
- Priority: **Medium** — recommend adding an explicit regression test asserting the clustering metric is never wired into any layout/coordinate-assignment path before closing task `e6b4743c`.

---

*Concerns audit: 2026-06-20*
