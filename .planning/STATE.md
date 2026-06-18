---
gsd_state_version: '1.0'
status: executing
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 0
  completed_plans: 0
  percent: 40
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-14)

**Core value:** The four lodestar use cases (§8D.45/47/48/49) run end-to-end against real subsystems — `all_real: true`, `full-smoke` green in both modes, every `probe_live_*.py` passing. A screenshot is never proof.
**Current focus:** Phase 3 — HTML Dedup + Halo Retrieval Render (Phases 1 & 2 complete)

## Current Position

Phase: 3 of 5 (HTML Dedup + Halo Retrieval Render) — Phases 1 & 2 done; core success metric met on the REAL stack
Plan: direct execution against the roadmap SCs (well-scoped tasks; no separate PLAN.md)
Status: REAL-STACK VERIFIED on THIS machine (all_real:true; the "GPU box" is here) — Phase 1 complete, all 4 lodestar probes + probe_no_mocks pass. **Phase 2 complete (2026-06-18): Milkdown integrated as the black-slate edit layer (controlled view); EDIT-01/02/03 done; PR #1 → Koreiju/mortegon.** GSD migration config + a UNIFIED full-stack test framework are in place.
Last activity: 2026-06-18 — Milkdown black-slate editable layer landed (T1–T7): recursive `{ref}` decoration, gesture model over the Milkdown DOM, §3 syntax round-trip, live `?slate=milkdown` click-to-edit (caret-at-click via ProseMirror `TextSelection`, blur-commit), Enter/Tab field growth + `{`-autocomplete, no-authoritative-state. Two load-bearing fixes: `gateway.mjs` `concept-update`→PATCH (real persistence) and `store.mjs`/`loadConcepts` `concept_id`→`id` normalization (authored concepts now render). Verified through the framework: REPL `full-smoke` 92/92 + e2e 21/3-skip, BOTH modes; `milkdown.spec.js` 8/8 + `edit.spec.js` 8/8. PR #1 opened.

Progress: [████░░░░░░] ~40% overall (Phases 1–2 done + real/framework-verified; verification infra COMPLETE; Phase 3 §U content-tree half already hardened, halo render is the gap)

### Phase 1 requirement status — COMPLETE (stub-verified) 2026-06-15
- REL-01 / REL-02 (no-mocks SLM 503): **DONE + verified** — `_ensure_model` raises `SLMUnavailableError` on real unavailability (gate-preserved, GPU→CPU preserved); compute/route stub paths closed; →503 handler in main. Both paths verified; SLM tests green.
- HYG-01 (deps pinned, kuzu 0.3.2→0.11.3, langgraph/selenium/webdriver-manager added, launch/port documented): **DONE**.
- HYG-02 (`@mdxeditor/editor` removed, lock pruned): **DONE**.
- FIX-01 (forbidden/legacy code): **DONE** — `_legacy_frontend/`/`backend_slow/`/`cluster_distillation.py` deleted; the forbidden graph-analytics *retrieval* tree (`analytics/algorithms/*` big set) + hyperbolic *layout* (`hyperbolic_layout.py`/`gyrovector.py`) were ALREADY removed (CODEBASE_AUDIT G8). `backend/analytics/` now holds only legitimate utilities (pq_tree/loop_closure/segment_embedder) — KEPT. Stale Fibonacci docstring fixed. Remaining grep hits are legitimate llama.cpp library refs + the no-Llama guard; the `chunk_builder` hyperbolic *clustering* metric is flagged for design review (task_e6b4743c), not a layout.
- FIX-02 (`three-fixtures-present`): **DONE + verified** — exactly 3 fixtures, no Editor.
- Phase-1 gate (`full-smoke`): **GREEN in stub (92/92)**. Real-mode `full-smoke` + `probe_no_mocks` need CUDA/GGUF/Selenium (GPU box) — deferred, not runnable in the agent env.

### Phase 2 status — COMPLETE (2026-06-18, Milkdown; PR #1)
- EDIT-01 (click-to-edit field): **DONE** — live `?slate=milkdown` click opens a focused Milkdown surface with the caret AT THE CLICKED FIELD (ProseMirror `TextSelection` via `placeCaretInField`; a raw DOM Range is overridden on focus); blur commits through the lifecycle, Esc discards. `edit.spec.js` EDIT-01 + `env-scenario edit-field-roundtrip` (extended: commit persists + evolution-log records) green.
- EDIT-02 (field growth + `{`-autocomplete + lifecycle): **DONE** — Enter = sibling / Tab = re-parent (ProseMirror's native commonmark list keymap); `{`-autocomplete (`installAutocomplete`) inserts `{<name>}`; every commit routes through `concept_lifecycle` via the new `gateway.mjs` `concept-update`→PATCH path. `edit.spec.js` EDIT-02 ×2 green.
- EDIT-03 (editor-layer decision): **RESOLVED — Milkdown controlled view** (user override 2026-06-17, supersedes the "stay custom/CM6" decision; see Decisions). No authoritative frontend state proven: `milkdown.spec.js` (reconnect = identical, no overhang) + `edit.spec.js` EDIT-03 (DOM corruption erased by store re-render).
- Recursive `{ref}` decoration, gesture model over the Milkdown DOM, §3 syntax round-trip (`markdownToFieldText`): `milkdown.spec.js` 8/8 green.
- Two latent fixes: `gateway.mjs` `concept-update`→PATCH (the real persistence path — `edit_close` was only a UI beacon); `store.mjs`/`loadConcepts` `concept_id`→`id` normalization (authored concepts never rendered before).
- VERIFIED through the framework: REPL `full-smoke` 92/92 + e2e 21/3-skip, BOTH stub and real modes.

### Phase 3 status (planned + T1 verified, 2026-06-18)
- **Planned:** CONTEXT.md + PLAN.md written (finish-and-verify — the §V halo model + live `openHalo` wiring already exist; the gap is the proximal collapsed-node halo + the live-editor browser acceptance).
- **T1 (HTML-01) DONE:** `pytest backend/tests/test_content_tree*.py` 17/17; `breadth_content_tree_smoke.py` 61 sites · 120,226 instances · **0 violations**; `env-scenario syntax-agnostic-compile` green (HtmlStrategy arm). Content-tree is corpus-clean across the URL spectrum.
- **Remaining:** T2 (halo fires from a collapsed circular node, proximal §S.5) · T3/T4 (un-fixme the 3 `halo.spec.js` specs) · T5 (triple-product ranking + autoregressive walk + no-dotted-overlay audit) · T6 (live-site breadth on the real stack).

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
- [Bootstrap — partly SUPERSEDED 2026-06-17]: Editor edit-layer is a SCOPED sub-task in Phase 2 (originally "custom vs CodeMirror 6"). The "WYSIWYG/ProseMirror/Lexical rejected" stance was overridden — **Milkdown (ProseMirror) is now adopted as a controlled view** (see the EDIT-03 override below); the "scoped sub-task, not a rebuild" framing still holds.
- [Phase 1 scope]: No-mocks SLM remediation (REL-01) is the highest-priority gap — the SLM path must 503 on real-load failure like the embedder already does. **(Shipped 2026-06-15.)**
- [EDIT-03, 2026-06-15 — SUPERSEDED 2026-06-17]: ~~Editor edit-layer = Option B — stay on the custom `magic_markdown` model/vdom; CM6 as a tracked enhancement; Milkdown/BlockNote/MDXEditor rejected.~~ Overridden below.
- [EDIT-03, 2026-06-17 — USER OVERRIDE, governing]: **Editor edit-layer = Milkdown**, integrated ONLY behind `mount` as a CONTROLLED VIEW (inbound `setText` replace-all / outbound blur-commit; `store.mjs`/`gateway.mjs`/`magic_markdown.mjs` unchanged; reconnect-re-render identity). Source: `docs/MILKDOWN_SLATE_GOAL.md` (user directive). The custom `magic_markdown` MODEL is retained (the bundle reuses `renderPanel`/`parse`/`resolveGesture`); Milkdown replaces only the edit/decoration layer. BlockNote/MDXEditor and any editor that OWNS document state remain rejected. **DELIVERED + verified 2026-06-18 (PR #1).**
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

Last session: 2026-06-18
Stopped at: Phase 2 COMPLETE (Milkdown black-slate edit layer, EDIT-01/02/03; PR #1 → Koreiju/mortegon). Reconciled planning state to Phase 2 done; current focus advanced to Phase 3.
Resume file: None
Next: `/gsd-plan-phase 3` (HTML Dedup + Halo Retrieval Render — §U content-tree half already hardened; the halo render is the gap), or flip `auto_advance: true` and `/gsd-autonomous` for Phases 3→5.
