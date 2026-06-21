---
gsd_state_version: '1.0'
status: verifying
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 0
  completed_plans: 0
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-14)

**Core value:** The four lodestar use cases (§8D.45/47/48/49) run end-to-end against real subsystems — `all_real: true`, `full-smoke` green in both modes, every `probe_live_*.py` passing. A screenshot is never proof.
**Current focus:** ALL 5 PHASES COMPLETE (real+stub verified 2026-06-21). Milestone v1.0 ready to close (audit → complete → cleanup).

## v1.0 Real-Stack Acceptance — 2026-06-21 (this GPU box: RTX 4070, all_real:true)

The `/gsd-autonomous` "build everything out from docs" pass closed Phases 2–5:
- **Phase 3 new code:** wrote the 3 live-halo browser specs (`frontend_e2e/halo.spec.js`, HALO-01/02) against the built `__mm_halo_*` hooks — un-fixme'd, green real+stub. Everything else across 2–5 was finish-and-verify (already built).
- **REPL `env-scenario --name all` = 95/95** in BOTH stub (`logs/full_stub_gate.log`) and real (`logs/real_gate_full.log`, `all_real=True`).
- **Playwright e2e = 24/24** in BOTH modes (incl. the 3 halo specs).
- **pytest** (stub) all green incl. §U golden 6/6 + content-tree breadth (17 passed).
- **Probes (real, all_real):** `probe_no_mocks`, `probe_live_archive_scan` (§8D.45), `probe_live_concept_graph` (§8D.47), `probe_live_agent` (§8D.48), `probe_live_iterated_compile` (§8D.49), `probe_pattern_map`, `probe_live_scan_with_cleanup` — ALL PASS.
- Dotted-overlay audit clean. Clean GPU teardown after every real run (no wedge).
- Per-phase VERIFICATION.md written under `.planning/phases/WFH-0{2..5}-*/`.

## Current Position

Phase: 5 of 5 COMPLETE — milestone v1.0 success metric MET on the REAL stack
Plan: direct execution against the roadmap SCs (well-scoped tasks; no separate PLAN.md)
Status: REAL-STACK VERIFIED on THIS machine (all_real:true; the "GPU box" is here) — Phase 1 complete, all 4 lodestar probes + probe_no_mocks pass. GSD migration config + a UNIFIED full-stack test framework are in place.
Last activity: 2026-06-15 — `scripts/run_full_stack_tests.py` (`npm run test:all`) boots ONE managed backend and runs pytest + the **complete REPL registry** (`env-scenario --name all` = 95 of 96 scenarios, not just full-smoke's 92) + Playwright `frontend_e2e`, unified summary. **PROVEN ALL GREEN in BOTH stub AND real (all_real) modes** — stub: pytest + repl(all, real-only scenarios skip) + 5 e2e; real: repl(all=95, every scenario executes incl `apparitions-discover-link` surfacing B via real nomic). Backend torn down cleanly both runs. Added `all` (extracted `_full_smoke_chain`, drift-resistant extras, clean-baseline purge; `apparitions-discover-link` gated on all_real per §1.5). Plus `.planning/config.json` (model fan-out → Sonnet/Haiku + nyquist gate + granularity contract), Playwright MCP (`.mcp.json`) + `frontend_e2e/` suite (5/5).

Progress: [███░░░░░░░] ~30% overall (Phase 1 done + real-verified; verification infra COMPLETE; Phase 2 backend verified)

### Phase 1 requirement status — COMPLETE (stub-verified) 2026-06-15
- REL-01 / REL-02 (no-mocks SLM 503): **DONE + verified** — `_ensure_model` raises `SLMUnavailableError` on real unavailability (gate-preserved, GPU→CPU preserved); compute/route stub paths closed; →503 handler in main. Both paths verified; SLM tests green.
- HYG-01 (deps pinned, kuzu 0.3.2→0.11.3, langgraph/selenium/webdriver-manager added, launch/port documented): **DONE**.
- HYG-02 (`@mdxeditor/editor` removed, lock pruned): **DONE**.
- FIX-01 (forbidden/legacy code): **DONE** — `_legacy_frontend/`/`backend_slow/`/`cluster_distillation.py` deleted; the forbidden graph-analytics *retrieval* tree (`analytics/algorithms/*` big set) + hyperbolic *layout* (`hyperbolic_layout.py`/`gyrovector.py`) were ALREADY removed (CODEBASE_AUDIT G8). `backend/analytics/` now holds only legitimate utilities (pq_tree/loop_closure/segment_embedder) — KEPT. Stale Fibonacci docstring fixed. Remaining grep hits are legitimate llama.cpp library refs + the no-Llama guard; the `chunk_builder` hyperbolic *clustering* metric is flagged for design review (task_e6b4743c), not a layout.
- FIX-02 (`three-fixtures-present`): **DONE + verified** — exactly 3 fixtures, no Editor.
- Phase-1 gate (`full-smoke`): **GREEN in stub (92/92)**. Real-mode `full-smoke` + `probe_no_mocks` need CUDA/GGUF/Selenium (GPU box) — deferred, not runnable in the agent env.

### Phase 2 status (backend-side verified 2026-06-15)
- EDIT-01 (click-to-edit field): backend `edit-field-roundtrip` **green** (editing_field lifecycle). Frontend caret-at-click already browser-verified (BLACK_SLATE_GOAL §15.7).
- EDIT-02 (field growth + `{`-autocomplete + lifecycle): `editor-primitives-roundtrip` + `autocomplete-state-roundtrip` **green**; mutations route through `concept_lifecycle`.
- EDIT-03 (editor-layer decision): **DECIDED — Option B (stay custom now; CM6 as tracked enhancement)**, see Decisions below.
- `unified-node-view-states` + `compile-expand-collapse-roundtrip` (§8D.2.2) **green**.
- REMAINING: live-browser re-verification of caret/IME/multiline in the served `/` editor; `full-smoke` stays green (it does, stub).

### Phase 3 progress (§U content-tree breadth, 2026-06-15)
- **Fixed a real correctness bug for the URL spectrum:** the §U dedup tokenizer was ASCII-only (`[a-z0-9]+`) → non-Latin text (CJK/Cyrillic/accented) produced an EMPTY token-set, so duplicate international titles never collapsed and accented Latin mis-split ("Amélie"→am+lie). Now `[^\W_]+` (Unicode word runs); ASCII golden unchanged. +4 international tests; suite 340/2-skip/0-fail. Commit `bf2c9c7`.
- Content-tree `fields_to_content_tree` reviewed for breadth: dedup subsumption, URL/text ordering, colon-join, data-URI compaction all sound; `srcset` multi-URL splitting intentionally NOT added (robust srcset parsing is fragile; one verbose URL line is not incorrect).
- **Breadth verification BUILT + AUTHORITATIVE:** `scripts/breadth_content_tree_smoke.py` now drives the REAL extraction ruleset offline (`backend/dom/pipeline.run_pipeline(render_instances=True)` over each saved `source.html` — no Selenium/GPU, since the live JS engine only extracts the static DOM and the chunking/fielding is Python). It surfaced + I fixed a real §U bug: raw HTML (tracking iframe/img pixels, noscript/style blobs the ruleset captured as text leaves) leaked verbatim into the content tree (266 violations / 21 sites). Fix: `content_tree._norm` strips HTML tags. **Authoritative verdict: 61 sites · 120,226 instances · 87,737 content-trees · 0 invariant violations** (commit `f5f78e7`).
- **Two real §U breadth bugs found + fixed this pass:** ASCII-only dedup tokenizer — international titles never collapsed (`bf2c9c7`); embedded-HTML value leak (`f5f78e7`). content_tree breadth is now corpus-hardened.
- **LIVE-VERIFIED on the real stack (2026-06-15 — THIS machine IS the CUDA/Firefox box; earlier "needs the GPU box" deferral was wrong):** booted the real backend (`python -m backend.main`, no fake gates) → `GET /api/subsystem_status` reports **`all_real: true`** (Nous-Hermes-2 on CUDA, nomic on CUDA, Selenium/Firefox bound, LangGraph).
  - `scripts/probe_no_mocks.py` **PASS** — real SLM generation (not `[stub-slm]`), real nomic 768-dim, real Selenium, real LangGraph → confirms **REL-01/02 on the REAL path** (the no-mocks fix doesn't break real generation).
  - `scripts/probe_live_archive_scan.py` **PASS** — live §8D.45 end-to-end: real Selenium scan of archive.org → 10 chunks → real retrieval ("Princeton University Library Chronicle 1942-11") → real LangGraph compile → real GPT4All generation → collapse/unpin. Phase 1 changes did NOT break the live pipeline.
  - **LIVE content-tree breadth:** real scans of Wikipedia/Library (128 trees), news.ycombinator (3), gutenberg top (150) → **0 content_tree invariant violations** on live JS-engine-extracted fields. The §U render is clean on live data too, not just the static corpus.
- **ALL FOUR LODESTAR PROBES PASS on the real stack (2026-06-15) — core success metric MET:** `probe_live_archive_scan` (§8D.45) ✓, `probe_live_concept_graph` (§8D.47) ✓, `probe_live_agent` (§8D.48) ✓, `probe_live_iterated_compile` (§8D.49 — halo with real nomic cosines + triple-product, compile/collapse round-trip) ✓. Phase 5 SC3 satisfied.
- **§16.5 `probe_live_scan_with_cleanup`: cleanup contract PASS** (purge→baseline, TF-IDF+nomic indices alive, **real UMAP 6D fit**, `layout_dropped` + `tfidf_rows_dropped`); the only failing assertion is round1≈round2 repeatability, which broke because **archive.org bot-throttled the rapid re-scan** (round1=92 vs round2=11 chunks) — external rate-limit, not a code regression (a clean single scan streams ~91 chunks). Re-run when not hammering the site.
- **Two non-regression test-state notes:** (1) `probe_live_iterated_compile` fails if the workspace was churned by intervening scans (accumulated TF-IDF desyncs the deprecated `chunk_search` path — the known `c_<hash>` vs `c_<hash>_<hash>` id-scheme mismatch); a clean purge+scan fixes it. (2) live scans of archive.org throttle under rapid succession — space them out.
- **Remaining (live-BROWSER only):** Phase 2 caret/IME + Phase 3 halo paint render verification (needs a human/automated browser; the backend/extraction/retrieval/compile paths are all real-verified).

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: -

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table (D1–D11, LOCKED per the ADR source-of-truth `docs/USER_REQUIREMENTS_VERBATIM.md`, precedence 0).
Recent decisions affecting current work:

- [Bootstrap]: Standard granularity (no config.json) → 5 phases derived gap-first; backend baseline preserved, frontend §T/§U/§V are finish-and-verify not rebuild.
- [Bootstrap]: Editor edit-layer is a SCOPED sub-task in Phase 2 (custom vs CodeMirror 6 per `docs/EDITOR_INTEGRATION_ASSESSMENT.md`); WYSIWYG/ProseMirror/Lexical options rejected.
- [Phase 1 scope]: No-mocks SLM remediation (REL-01) is the highest-priority gap — the SLM path must 503 on real-load failure like the embedder already does. **(Shipped 2026-06-15.)**
- [EDIT-03, 2026-06-15]: **Editor edit-layer = Option B — stay on the custom `magic_markdown` model/vdom for now; do NOT adopt CodeMirror 6 yet.** Rationale: the custom black-slate editor is already built, tested (57 tests), and browser-verified as the served `/` frontend; "finish-and-verify, not rebuild." CM6 (Option A, behind `mount` only) remains the RECOMMENDED enhancement — adopt it when the hand-rolled caret/IME/undo/borderless-edit layer starts costing more than the integration (per `docs/EDITOR_INTEGRATION_ASSESSMENT.md`). Milkdown/BlockNote/MDXEditor stay rejected.
- [FIX-01 resolution, 2026-06-15]: `backend/analytics/` is KEPT (utilities only; the forbidden retrieval framework + hyperbolic layout were already removed in G8). The `chunk_builder` hyperbolic-distance *clustering* metric is a scan-time algorithm, NOT the forbidden 3D layout — kept, flagged for design review (task_e6b4743c).

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

[Issues that affect future work]

- GPT4All `Embed4All` is not thread-safe on Windows (RLock-guarded mitigation, not a fix) — sustained concurrency can still abort. Deferred to v2 (PERF-02).
- Full pytest suite is 336 passed / 2 skipped / 0 FAILED in stub mode (2026-06-14) — better than the prior "14 ledgered failures" note implied; no red to normalise.
- backend/analytics/ is LOAD-BEARING (imported by routes/dom/mapper/chat/retrieval) — NOT a blanket-deletable forbidden tree. FIX-01 must surgically separate the forbidden graph-analytics RETRIEVAL features from the still-used utilities (pq_tree, segment_embedder, loop_closure) and remove only the matching tests.
- Backend port 8080 vs REPL default 8000 — always pass `--backend http://127.0.0.1:8080` (global flag, before the subcommand) when running the harness.
- **Verification boundary (environment).** Backend wiring/lifecycle for ALL phases is stub-verified: `env-scenario --name full-smoke` is **92/92 green (stub)** and it composes every registered scenario (incl. the Phase 3–5 ones: 6d-umap-format, iterated-signal-rerender, pattern-map-live-update, syntax-agnostic-compile, apparition-mode, halo-focus, ontology-projection, readout-panel-projection, dominance-collapse, url-collapse-cascade, …). What each finish-and-verify phase still needs is (a) **real-stack `all_real`** verification (real GPT4All compile, real nomic, real Selenium scan, real-UMAP 6D fit) via `probe_live_*.py` + real-mode `full-smoke`, and (b) **live-browser** re-verification of the §T/§U/§V render — neither runnable in the agent env (no CUDA/GGUF/headful Firefox). Run these on the GPU box: `python app.py` then `python scripts/probe_no_mocks.py http://127.0.0.1:8080`, `probe_live_scan_with_cleanup.py`, and the four lodestar `probe_live_*.py`.
- A leftover stub backend (Microsoft Store python) may be holding port 8080 from a verification run; if `python app.py` can't bind, end the `python.exe` in Task Manager or use `--port 8081`.

## Deferred Items

Items acknowledged and carried forward (tracked as v2 in REQUIREMENTS.md):

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Maintainability | Split monolithic routes.py / sim_frontend.py (MAINT-01/02) | Deferred (v2) | 2026-06-14 |
| Performance | Incremental mid-scan UMAP refit; embedder thread-safety (PERF-01/02) | Deferred (v2) | 2026-06-14 |

## Session Continuity

Last session: 2026-06-14
Stopped at: Wrote the complete planning set (PROJECT, REQUIREMENTS, ROADMAP, STATE) from ingest intel.
Resume file: None
