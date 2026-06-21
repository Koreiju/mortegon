# web_fiber_haptics — Living Retrospective

## Milestone: v1.0 — Live Acceptance

**Shipped:** 2026-06-21
**Phases:** 5 | **Plans:** direct (no separate PLANs — brownfield finish-and-verify)

### What Was Built
- Honest no-mocks baseline (503 on real-load failure; three fixtures; forbidden/legacy code deleted; deps pinned).
- Black-slate field editing through the one lifecycle dispatcher, with Milkdown as a controlled view (no authoritative frontend state).
- §U deduplicated HTML content-tree + a name-only triple-product apparition halo (3 new live browser specs).
- Live 6D-UMAP/HSV projection, one-signal-at-a-time rollout, live `pattern_map` node.
- The three-register compose-compile-perimeter loop, proven by all four lodestar use cases end-to-end against real subsystems.

### What Worked
- **Real-stack-first verification.** The clean GPU baseline (0 VRAM / 0 stray python) check before each real boot prevented the "wedged backend" failure mode entirely.
- **The unified test framework (`run_full_stack_tests.py`)** boots ONE managed backend and tears it down with `taskkill /F /T` — running REPL `all` + e2e + probes in one invocation made "both modes" verification cheap and reliable.
- **Reading the e2e fixmes as the precise gap list.** The only genuine new code (3 halo specs) fell straight out of the existing `__mm_halo_*` hooks; everything else was finish-and-verify.

### What Was Inefficient
- **Stale memory vs on-disk ROADMAP.** Recalled memory claimed "v1 complete / v2 phases 6–8"; the on-disk `.planning/` (re-bootstrapped 2026-06-14) was the truth. Reconciling against `roadmap.analyze` first (not memory) is the lesson.
- **Halo e2e flakes took 3 iterations:** isolated DB starts empty (seed concepts), the async `/api/radiation` refine races the assertions (wait for stabilization), and the projector rAF re-pins `camAngle` (capture orbit before/after atomically). All three are real headless-browser timing traps.

### Patterns Established
- **Drive real-stack verification from the main context, never a verifier subagent** — the main agent controls the GPU/backend lifecycle and can guarantee clean teardown; a wedged CUDA subagent cannot be killed cleanly.
- **`--fixture-scan` for deterministic REPL scans** (local `test_packages/`) avoids archive.org throttling; reserve real archive.org probes for the lodestar set and space them out.

### Key Lessons
- A screenshot is never proof (D1) — every SC closed with a named `env-scenario` / `probe_live_*.py` / `all_real:true`, green in BOTH modes.
- The clean-GPU precondition is load-bearing for any real-stack run on this box.

### Cost Observations
- One main-context session; one integration-checker subagent.
- Two long real-backend runs (the consolidated gate + the scan-cleanup probe), each torn down clean.

---

## Cross-Milestone Trends

| Milestone | Phases | Real-stack acceptance | Notable |
|-----------|--------|------------------------|---------|
| v1.0 Live Acceptance | 5 | all_real:true; 95/95 REPL + 24/24 e2e both modes; 7 probes pass | finish-and-verify; 1 genuine new deliverable (halo e2e) |
