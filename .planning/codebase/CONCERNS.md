# Codebase Concerns

**Analysis Date:** 2026-06-14

This codebase is a brownfield full-stack app where `docs/` is the authoritative
target and the code is iterated toward it. The dominant class of concern here is
**DESIGN↔CODE divergence** — documented goals that the code has not yet executed —
followed by **legacy/forbidden-code residue** awaiting hard deletion. Pure runtime
bugs are comparatively rare; the risk surface is structural debt and contract drift.

## Tech Debt

**DESIGN↔CODE gap — §T black-slate frontend rebuild (NOT executed):**
- Issue: The full from-scratch "one black text-tree slate per card" frontend
  (parse-recovered structure, no widgets, internalize/externalize link gestures)
  is a binding GOAL but unbuilt. The served default `/` is the new editor
  (`backend/main.py:101` → `templates/editor.html`), but the slate/halo render
  features behind it are documented as not-yet-built.
- Files: `docs/BLACK_SLATE_GOAL.md` (Status: GOAL/binding; §15.6 matrix line 555
  "the slate/dedup/halo features are documented goals, **not yet built**"),
  `backend/main.py:101-130`, `backend/templates/editor.html`.
- Impact: The shipped frontend does not yet realise the canonical object model.
  The legacy `cp/*` 3D projector is still the functional surface (demoted to
  `/legacy`, `backend/main.py:123`).
- Fix approach: Execute the §T strip per `docs/BLACK_SLATE_GOAL.md`; backend is
  intended to stay intact (V.4 in the matrix: "BACKEND EXISTS / FRONTEND UNBUILT").

**DESIGN↔CODE gap — §U HTML-dedup content-tree (NOT built):**
- Issue: HTML chunk slate bodies should render DEDUPLICATED content as a pure-text
  tree (collapse wrappers, token-set dedup, surface href/src). The exact algorithm
  and golden I/O are specified but unimplemented (realises the §E.1 HtmlStrategy).
- Files: `docs/HTML_DEDUP_CONTENT_TREE_GOAL.md`, plus the existing extraction it is
  meant to build atop (`backend/dom/content_distiller_simple.py`,
  `backend/dom/cluster_distillation.py`).
- Impact: Chunk rendering does not match the design's content-tree shape; the
  `rendered_text` path is the identified gap (per §V live verify).
- Fix approach: Build from the existing `fields` extraction, not from `html_raw`.

**DESIGN↔CODE gap — §V streaming + halo ray mechanics (FRONTEND UNBUILT):**
- Issue: Streaming SLA, circular root-field-only collapsed nodes, constant-similarity
  halo ray with along-line slide are documented goals. Backend exists; frontend does
  not render them.
- Files: `docs/BLACK_SLATE_GOAL.md` §15.6 (V.4 "BACKEND EXISTS / FRONTEND UNBUILT"),
  `backend/services/apparition_service.py` (`?ray_project=1`).
- Impact: Halo/streaming UX unverifiable end-to-end until the frontend lands.

**Monolithic route module:**
- Issue: `backend/api/routes.py` is 5,424 lines — a single file carrying the entire
  REST + WS surface, with stub paths, legacy aliases, and active routes interleaved.
- Files: `backend/api/routes.py`.
- Impact: Hard to navigate, review, and test in isolation; legacy and live paths
  are not visually separated.
- Fix approach: Split by register (scan / retrieval / concept / agent / maintenance)
  into `backend/api/` submodules.

**Oversized REPL harness:**
- Issue: `scripts/sim_frontend.py` is 9,430 lines (~160+ actions, 19 categories).
- Files: `scripts/sim_frontend.py`.
- Impact: The single most important verification surface is a monolith; a change to
  one action category risks the whole harness.

## Forbidden / Legacy Code Slated for Removal

Per `CLAUDE.md` "Forbidden Concepts (Hard Deletions)", the following must not exist
in doc or code. Residue remains:

**Fibonacci / concentric-sphere layout residue:**
- Files: `backend/ontology/layout_generator.py` (docstring line 14 references the
  contrast with "global concentric shells"), and forbidden-term hits across
  `backend/api/routes.py`, `backend/mapper/mapper.py`, `backend/mapper/pattern_trie.py`,
  `scripts/probe_use_case.py`, `scripts/sim_frontend.py`.
- Risk: The audit (`docs/CODEBASE_AUDIT_2026-06-08.md` §A.3) flagged Fibonacci-sphere
  layout as live in the scanner. Verify each hit is now an inert comment/anti-reference
  vs. a live placeholder.
- Fix approach: Grep `fibonacci|concentric|hyperbolic` and delete live code paths;
  reduce any remaining mentions to deprecation banners only.

**Graph-analytics retrieval residue:**
- Files: `backend/analytics/loop_closure.py` + `backend/analytics/algorithms/`,
  `backend/tests/test_loop_closure.py`, hits in `backend/mapper/`.
- Risk: Retrieval must rank by the triple product `pagerank · tfidf_cos · nomic_cos`
  ONLY (`CLAUDE.md`). The `analytics/` tree (loop_closure, segment_embedder, algorithms)
  is the forbidden graph-analytics framework family.
- Fix approach: Confirm `analytics/` is dead (no import from the retrieval path) and
  delete; keep retrieval on `backend/services/retrieval_service.py` /
  `chunk_retrieval.py` only.

**Deprecated DOM distillation module:**
- Files: `backend/dom/cluster_distillation.py` (header line 3 "DEPRECATED",
  retained only for the legacy entry point), 1,014 lines.
- Impact: Dead-ish weight kept alive for a legacy caller; the §U content-tree work
  should supersede it.

**`backend_slow/` parallel tree (13 MB):**
- Files: `backend_slow/` (api/dom/mapper/static/templates) — the historical scanner
  implementation. Only referenced as a comment pointer (`backend/dom/scanner.py:407`
  "see backend_slow/dom/scanner.py for the historical impl"), never imported.
- Impact: 13 MB of unreachable code in-repo; confuses navigation and grep.
- Fix approach: Delete `backend_slow/` once the comment pointer is removed.

**`_legacy_frontend/` (264 KB):**
- Files: `_legacy_frontend/` (chunk_projector.monolith.js, fe/, index_fe.html). Not
  served and not referenced from `backend/` or `app.py`.
- Impact: Dead frontend artifact.
- Fix approach: Delete after confirming nothing in docs links to it as reference.

**Legacy `cp/*` 3D projector still served at `/legacy`:**
- Files: `backend/static/js/cp/*.js` (17 files, 769 KB), `backend/main.py:123`,
  `backend/templates/index.html`.
- Impact: Intentionally retained "for reference + the 3D chunk field until the
  projector is folded into the editor" — not forbidden, but transitional debt that
  doubles the frontend surface until §T lands.

**Deprecated `Editor` 4th fixture:**
- Status: Removed in §S (three fixtures: Database, WebBrowser, Agent). Residual risk
  is migration data, not code: a stale `fixture::editor` node can survive in the
  `_default` Kuzu DB and needs force-delete (per MEMORY §S note). Verify
  `backend/services/foundation_fixtures.py` emits exactly three.
- Files: `backend/services/foundation_fixtures.py`, `kuzu_db/`.

## Known Bugs / Fragile Paths

**Native embedder is not thread-safe:**
- Symptoms: Concurrent retrieval/chunker calls against the same `Embed4All` handle
  corrupt llama.cpp's compute graph → access violation (recoverable) or GGML_ASSERT
  (aborts the process).
- Files: `backend/services/embedding_service.py:259-300` (`_safe_embed`).
- Trigger: Parallel `embed()` on one model handle.
- Workaround: Per-`model_name` RLock + evict-and-reload-on-CPU retry-once. This is a
  mitigation around a native-library defect, not a fix; the reload-once path is
  inherently fragile under sustained concurrency.

**Stale `fixture::editor` in default DB:**
- Symptoms: Old `_default` workspaces carry a deprecated Editor fixture node.
- Files: `kuzu_db/`, `backend/services/foundation_fixtures.py`.
- Workaround: Force-delete the node (documented in MEMORY §S).

## Security Considerations

**SLM/embedder model auto-download enabled:**
- Risk: `GPT4All(..., allow_download=True)` (`backend/services/slm_client.py:131,148`)
  will fetch model weights from the network at runtime if absent — a supply-chain /
  availability surface.
- Files: `backend/services/slm_client.py:131,148`.
- Current mitigation: Model name is pinned (Nous-Hermes-2-DPO) with a loud anti-Llama
  guard (`slm_client.py:55-62`).
- Recommendations: Pin to a verified local cache; gate download behind an explicit flag.

**Headful Selenium runtime:**
- Risk: Live Firefox via vendored `backend/drivers/geckodriver.exe` scans arbitrary
  user-supplied URLs (the design's core feature). Untrusted-page DOM is parsed by the
  distillation pipeline.
- Files: `backend/services/selenium_client.py`, `backend/dom/scanner.py`,
  `backend/drivers/geckodriver.exe` (intentionally vendored, per `.gitignore`).
- Current mitigation: None beyond Selenium's process boundary.
- Recommendations: Treat scanned DOM as untrusted; ensure no eval of page-derived
  strings in the distillation path.

**Secrets:** No `.env` / credential files detected in the tree. No API keys observed
in source (all subsystems are local GPT4All / Selenium). Good.

## No-Mocks Contract Violations ("no quiet stub fallback in production")

The §8D.46 contract requires real-backend → stub fallback to be **forbidden in
production** (failure = 503 + halted cascade, never silent stub).

**VIOLATION — SLM streaming path silently degrades to stub:**
- Problem: `SLMClient._ensure_model()` sets `self._fake = True` and returns `None` on
  real load failure (`backend/services/slm_client.py:158`), after which
  `async_stream_chat` (`:173-177`) and other generation paths emit deterministic stub
  text instead of raising 503. This is the exact "quiet stub substitution" the
  contract names as the anti-pattern.
- Files: `backend/services/slm_client.py:114-159` (`_ensure_model`), `:165-188`
  (`async_stream_chat`), `:302` (`subsystem_status` reports `"stub"`).
- Impact: A dead GGUF in production yields fabricated SLM output rather than a loud
  503. Contrast with the embedder, which correctly raises `ValueError` → clean 503
  (`backend/services/embedding_service.py:300`).
- Fix approach: On non-harness load failure (i.e. `WFH_FAKE_SLM` unset), raise instead
  of setting `_fake`; reserve the stub path strictly for `WFH_FAKE_SLM=1`. The CPU
  fallback at `:140-152` is fine (real→real, permitted); only the terminal
  `_fake = True` at `:158` is the violation.

**Compute endpoint stub-on-import-failure:**
- Problem: `_make_slm_for_compute` (`backend/api/routes.py:3224-3235`) swallows an
  SLMClient construction failure and returns `None`, after which the compute node
  "falls back to its deterministic stub." Same anti-pattern at the route layer.
- Files: `backend/api/routes.py:3224-3235`, `:3201`, `:5363` (agent tick "emits a
  stub action" if SLM unavailable).
- Fix approach: Distinguish harness mode from production; in production let the failure
  surface as 503.

**Subsystem-status guard is correct:** `GET /api/subsystem_status`
(`backend/api/routes.py:3568+`) reports `all_real` and explicitly documents that
`backend == "stub"`/`"fake"` in production is a contract violation. The guard exists;
the SLM code path is what breaks it.

## Performance Bottlenecks

**Scan-end-only UMAP refit (vs. incremental):**
- Problem: The audit (`docs/CODEBASE_AUDIT_2026-06-08.md` §0 item 4) flagged UMAP
  firing scan-end-only rather than incrementally mid-scan (§5.4/§16.5). Verify current
  `LayoutService` incremental capability.
- Files: `backend/services/layout_service.py`.
- Improvement path: Incremental joint refit during streaming chunk arrival.

**Loud SVD degradation under UMAP-unavailable:**
- Problem: `LayoutService` uses real `umap-learn` when present, degrading loudly to
  `TruncatedSVD` (`backend/services/layout_service.py:61-80`). SVD does not preserve
  local neighbourhoods — if it ever silently engages, the comparison-surface reading
  of §6.6 is unreliable.
- Files: `backend/services/layout_service.py:61-80,413`.
- Note: This is now the intended loud-fallback (audit headline §A.1 was since fixed,
  per MEMORY), but confirm the degrade path is actually loud at runtime.

## Test Coverage Gaps

**Empirical-verification debt (historical, per audit):**
- The audit (`docs/CODEBASE_AUDIT_2026-06-08.md` §0/§A.4) noted "green/all-real"
  claims were unproven at audit time. MEMORY records subsequent full-smoke 92/92 in
  both modes and live probes green (incl. first §16.5 pass). Concern is keeping these
  green as §T/§U/§V land — the slate/dedup/halo features are unbuilt, so their
  scenarios cannot yet assert real frontend rendering.
- Files: `scripts/sim_frontend.py` (`env-scenario`), `scripts/probe_live_*.py`.

**Ledgered legacy test failures:**
- MEMORY (§R integration) records "14 pre-existing legacy test failures ledgered."
  These are tolerated known-failures, not green. Locate and either fix or formally
  delete with the legacy code they cover.
- Files: `backend/tests/` (notably `test_loop_closure.py` if `analytics/` is deleted),
  `scripts/test_*.py`.
- Risk: Ledgered failures normalise red; a real regression can hide among them.

**Frontend has minimal automated tests:**
- Only `backend/static/js/cp/hsv_color.test.mjs` observed. The §T slate frontend will
  need its own test surface.

## Large Runtime Artifacts In-Repo

All are gitignored (`.gitignore` "Runtime data & artifacts") and NOT git-tracked — good.
Disk-footprint / hygiene notes only:
- `kuzu_db/` — 3.1 MB (per-workspace Kuzu store; can hold stale `fixture::editor`).
- `snapshots/` — 2.6 MB (scan snapshots).
- `logs/` — 348 KB; `logs.txt` — 2.3 MB (the `app.py` Tee mirror, `app.py:19+`).
- `node_modules/` — 58 MB (gitignored).
- Test-DB hygiene is handled by `backend/services/db_janitor.py` (canonical `wfh_test_`
  prefix, `POST /api/maintenance/cleanup_test_artifacts`). Risk: tests that bypass the
  janitor (`tempfile.mkdtemp` directly) leak side-files — enforce janitor use (§R.9).

## Dependencies at Risk

**GPT4All native binding (Windows access violations):**
- Risk: The non-thread-safe `Embed4All` handle causes native crashes
  (`backend/services/embedding_service.py:259+`). The binding is load-bearing and
  fragile on Windows.
- Impact: Process aborts under concurrent embedding without the RLock guard.
- Migration plan: None forced; the guard contains it. Monitor for GGML_ASSERT aborts.

**Two entry points (`app.py` vs `backend/main.py`):**
- Risk: `app.py` (root, 7.4 KB, stdout Tee + path setup) and `backend/main.py` (the
  FastAPI app + routes) are both present. Ambiguous which is canonical for deploy.
- Files: `app.py`, `backend/main.py`.
- Recommendation: Document the canonical launch command (note `CLAUDE.md`: backend
  default port 8080 in `main.py`, but REPL defaults to 8000 — a known mismatch
  requiring `--backend http://127.0.0.1:8080`).

## Missing Critical Features (per documented goals)

- §T black-slate frontend render — UNBUILT (`docs/BLACK_SLATE_GOAL.md`).
- §U HTML-dedup content-tree — UNBUILT (`docs/HTML_DEDUP_CONTENT_TREE_GOAL.md`).
- §V halo ray slide + circular collapsed nodes (frontend) — UNBUILT.
- These three block the canonical "one black slate per card" UX that the entire
  frontend redesign chain (`docs/FRONTEND_REDESIGN.md`, `docs/frontend/`) targets.

---

*Concerns audit: 2026-06-14*
