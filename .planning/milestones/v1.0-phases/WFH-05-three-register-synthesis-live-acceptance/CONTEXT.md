# Phase 5 — Three-Register Synthesis & Live Acceptance — CONTEXT

> The capstone: bind the Real/Imaginary/Symbolic registers into one
> compose-compile-perimeter loop and prove all four lodestar use cases end-to-end
> against REAL subsystems (`all_real: true`). Almost entirely **verification** —
> the loop is built; this phase proves it on the real stack.

## Goal

The Real/Imaginary/Symbolic registers form one compose-compile-perimeter loop
runnable from either the GUI or the REPL with identical results, and all four
lodestar use cases (§8D.45/47/48/49) pass end-to-end against real subsystems —
the project's success metric is met.

## In scope (the project success metric)

- **SC1 (REPL = GUI)** — a REPL action entering at any node of the loop produces the
  identical GUI-observable result (2D/3D separation, WS telemetry mirroring register
  state). `env-scenario --name complex-interaction-walkthrough` (rollout + halo +
  compile + signal coexist in one UIState envelope) + `cascade-reflow-roundtrip`
  green both modes.
- **SC2 (purge round-trip)** — `scripts/probe_live_scan_with_cleanup.py` passes
  (all_real): real archive.org scan → TF-IDF + nomic indices alive → real-UMAP 6D
  fit → purge cleanup contract (`layout_dropped` + `tfidf_rows_dropped`) returns the
  Kuzu ConceptNode count to the three-fixture baseline → re-scan rebuilds a
  comparable pool.
- **SC3 (four lodestars)** — `probe_live_archive_scan.py`, `probe_live_concept_graph.py`,
  `probe_live_agent.py`, `probe_live_iterated_compile.py` all pass against real
  subsystems.
- **SC4 (no-mocks gate)** — `GET /api/subsystem_status` reports `all_real: true`;
  `env-scenario --name full-smoke` green in BOTH stub and real modes with every
  §T/§U/§V/§R scenario included.

## As-built starting point (do NOT rebuild)

- The compose-compile-perimeter loop (RolloutCoordinator + materialiser + halo +
  compile chain) — REPL-covered by `complex-interaction-walkthrough` +
  `cascade-reflow-roundtrip`.
- The four lodestar probes + `probe_no_mocks.py` + `probe_live_scan_with_cleanup.py`
  — all present in `scripts/`, last green real-stack 2026-06-15.
- `GET /api/subsystem_status` (slm/embedder/selenium/langgraph/all_real).

## Verification gate (real stack — the GPU box is THIS machine)

- **subsystem_status:** `all_real: true` (Nous-Hermes-2 CUDA, nomic CUDA,
  Selenium/Firefox, LangGraph).
- **REPL:** `complex-interaction-walkthrough`, `cascade-reflow-roundtrip`, +
  `full-smoke`/`all` green in BOTH modes.
- **probes (all_real):** `probe_no_mocks.py`, the 4 lodestar `probe_live_*.py`,
  and `probe_live_scan_with_cleanup.py`.

## Out of scope

- New capability. Phase 5 is the binding + the live acceptance proof, not new code.
- Deferred-milestone items (mid-scan UMAP refit, embedder thread-safety, route
  splits) tracked separately.
