# Phase 5 — Three-Register Synthesis & Live Acceptance — CONTEXT

> Context for execution. Phase 5 is **pure verification** (no build): the backend
> is mature and the probes exist. It binds Real/Imaginary/Symbolic into the
> compose-compile-perimeter loop and proves the four lodestar use cases against
> real subsystems — the project's success metric.

## Goal

The Real (3D Projector) / Imaginary (2D editor) / Symbolic (REPL) registers form
one compose-compile-perimeter loop runnable from either the GUI or the REPL with
identical results, and all four lodestar use cases (§8D.45/47/48/49) pass
end-to-end against real subsystems — `GET /api/subsystem_status` reports
`all_real: true`.

## In scope (requirements)

- **REG-01** — a REPL action entering at any node of the loop produces the
  identical GUI-observable result (2D/3D separation maintained, WS telemetry
  mirroring register state). Verified by `complex-interaction-walkthrough`
  (rollout + halo + compile + signal coexist in one UIState envelope) and
  `cascade-reflow-roundtrip` green in both modes.
- **ACC-01** — `scripts/probe_live_scan_with_cleanup.py` passes (all_real): real
  archive.org scan → TF-IDF + nomic indices alive → real-UMAP 6D fit → purge
  cleanup contract (`layout_dropped` + `tfidf_rows_dropped`) returns the Kuzu
  ConceptNode count to the three-fixture baseline → re-scan rebuilds a comparable
  pool.
- **ACC-02** — all four lodestar live probes pass against real subsystems:
  `probe_live_archive_scan.py` (§8D.45), `probe_live_concept_graph.py` (§8D.47),
  `probe_live_agent.py` (§8D.48), `probe_live_iterated_compile.py` (§8D.49); and
  `full-smoke` green in BOTH stub and real modes.

## As-built starting point (verify, do NOT build)

- **REG-01 scenarios** — `complex-interaction-walkthrough`, `cascade-reflow-roundtrip`,
  `watch-activity-mirror` GREEN (stub, this session — all exit 0); both are in
  `full-smoke` (92/92).
- **Real subsystems present on THIS machine:** Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf
  + nomic-embed-text-v1.5.f16.gguf (`~/.cache/gpt4all`), `backend/drivers/geckodriver.exe`,
  CUDA (RTX 4070). `GET /api/subsystem_status` → `all_real: true` when the real
  backend boots (no `WFH_FAKE_*` gates).
- **Probes exist:** `scripts/probe_no_mocks.py`, `probe_live_archive_scan.py`,
  `probe_live_concept_graph.py`, `probe_live_agent.py`, `probe_live_iterated_compile.py`,
  `probe_live_scan_with_cleanup.py`. Documented as passing on this machine in a
  prior session (STATE 2026-06-15).

## The work (verification only)

1. **REG-01:** confirm the two synthesis scenarios green both modes. **(stub ✓.)**
2. **ACC-02 foundation:** boot the real backend (`python -m backend.main`, no fake
   gates) → `GET /api/subsystem_status` `all_real: true` → `probe_no_mocks.py`
   PASS (real SLM not `[stub-slm]`, real nomic 768-dim, real Selenium, LangGraph).
3. **ACC-02 lodestar:** run the four `probe_live_*.py` against the real backend.
4. **ACC-01:** `probe_live_scan_with_cleanup.py` (real archive.org scan + 6D fit +
   purge contract).

## Verification boundary (the one honest caveat)

The live probes drive **archive.org**, which bot-throttles rapid re-scans (STATE
§16.5 — the round1≈round2 repeatability assertion broke under throttling, NOT a
code regression). Space scans out; a clean single scan streams ~91 chunks. The
lighter probes (`concept_graph`, `agent`) carry no external-site dependency.

## Out of scope / Forbidden

- Any new build — Phase 5 is acceptance. Real-backend → stub fallback is FORBIDDEN
  (failures are loud 503s). No Llama as the SLM target.
