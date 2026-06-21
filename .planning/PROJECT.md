# web_fiber_haptics

## What This Is

A single-operator, on-device, full-stack "ontological warp" workspace. The operator scans the live web (real Selenium/Firefox), retrieves chunks via a triple-product index (PageRank · TF-IDF · nomic), and authors a typed concept/compute graph that renders as a live 3D UMAP-radial manifold (Real register), a 2D black-slate markdown editor (Imaginary register), and a REPL harness (Symbolic register). A real on-device SLM agent (GPT4All Nous-Hermes-2) ticks against the workspace. It is built and used by one person; there is no team, no multi-tenant surface, no auth.

## Core Value

The four lodestar use cases (§8D.45/47/48/49) run end-to-end **against real subsystems** — `GET /api/subsystem_status` reports `all_real: true`, `env-scenario --name full-smoke` is green in BOTH stub and real modes, and every `scripts/probe_live_*.py` passes. A screenshot is never proof; the live REPL/probe against the full stack is.

## Requirements

> Full checkable list with categories, v2, out-of-scope, and per-phase traceability lives in `.planning/REQUIREMENTS.md`. The roadmap is `.planning/ROADMAP.md`. This section is the digest.

### Validated

<!-- Already built and confirmed working per CLAUDE.md "What Always Holds" + the codebase map. Brownfield baseline — do NOT rebuild. -->

- ✓ Single lifecycle dispatcher (`concept_lifecycle.py`) — every mutation routes through WS broadcast → ConceptIndex upsert → output projection → evolution log → cascade nudge.
- ✓ Two progressive vectorization pipelines (chunk-side TF-IDF incremental + UMAP joint; concept-side nomic incremental + PageRank joint), axes never mixed.
- ✓ Triple-product retrieval index (`pagerank · tfidf_cos · nomic_cos`) on `retrieval_service.py` / `chunk_retrieval.py`.
- ✓ One ConceptNode + one ConceptEdge Kuzu schema; `edge_type` union enum; new capability is a peer fixture / compiled-from-scans / Python-API tree.
- ✓ Live Selenium scan streaming → chunk emission → scan-end joint UMAP 6D fit → `umap_canonical` WS frame.
- ✓ Monotone per-workspace WS frame seq with `?resume=<seq>` replay; lossy backpressure; idempotency keys; append-only evolution log with three rollback scopes.
- ✓ Real LangGraph + GPT4All compile chain; real agent tick streaming real tokens.
- ✓ `env-scenario --name full-smoke` green in both modes (92/92 per MEMORY); live probes passing; `db_janitor` test-DB hygiene.
- ✓ The §T black-slate frontend (`backend/static/js/fe/*.mjs`) and §U HTML-dedup content-tree (`backend/dom/content_tree.py`, §U golden 6/6) are largely built and are the default served surface at `/` (legacy projector demoted to `/legacy`).

**Shipped in v1.0 (Live Acceptance, 2026-06-21 — all real-stack verified):**
- ✓ REL-01 / REL-02 — no-mocks SLM 503 on real-load failure; CPU real→real preserved (`probe_no_mocks` PASS) — v1.0
- ✓ FIX-01 / FIX-02 — exactly three fixtures (no Editor); mutation gestures route through the lifecycle — v1.0
- ✓ HYG-01 / HYG-02 — forbidden/legacy code deleted; deps pinned; `@mdxeditor/editor` removed — v1.0
- ✓ EDIT-01 / EDIT-02 / EDIT-03 — black-slate field editing through the one lifecycle; Milkdown controlled view; no authoritative frontend state — v1.0
- ✓ HTML-01 — §U deduplicated content-tree from `fields`; golden 6/6 — v1.0
- ✓ HALO-01 / HALO-02 — name-only triple-product apparition halo; circular collapsed node; constant-similarity ray slide; solid 2D↔3D arrow (3 live e2e specs) — v1.0
- ✓ UMAP-01 — 6D `umap_canonical` fit + camera-coupled HSV (frontend renders only) — v1.0
- ✓ SIG-01 — one-signal-at-a-time rollout via `RolloutCoordinator`, per-sample cascade re-fire — v1.0 (GUI driver currently legacy-only; see v2 tech debt)
- ✓ PAT-01 — live `pattern_map` ConceptNode; golden-trio gate; accretive; PageRank on the Kuzu graph — v1.0
- ✓ REG-01 — three-register compose-compile-perimeter loop, REPL=GUI — v1.0
- ✓ ACC-01 / ACC-02 — `probe_live_scan_with_cleanup` + all four lodestar probes pass; `all_real: true`; full-smoke green both modes — v1.0

### Active

<!-- v1.0 frontier all shipped + validated (see above). Active is now the v2.0 candidate set (Maintainability & Performance). A fresh .planning/REQUIREMENTS.md is created by /gsd-new-milestone. -->

**v2.0 — Maintainability & Performance (planned):**
- [ ] MAINT-01: Split the monolithic `backend/api/routes.py` (~5,400 lines) by register (scan / retrieval / concept / agent / maintenance) into `backend/api/` submodules.
- [ ] MAINT-02: Decompose `scripts/sim_frontend.py` (~9,430 lines) so a change to one action category does not risk the whole harness.
- [ ] PERF-01: Incremental joint UMAP refit during streaming chunk arrival (currently scan-end-only).
- [ ] PERF-02: Harden the non-thread-safe GPT4All `Embed4All` handle beyond the per-model RLock + evict-and-reload mitigation.
- [ ] (tech debt, from v1.0 audit) Wire `/api/ui/signal_advance` (SIG-01) into the served `/` editor — currently driven only from legacy `backend/static/js/cp/concept_graph.js`; if the `cp/` path is retired, the GUI loses its iterable-advance driver.

### Out of Scope

- Concentric Fibonacci spheres as 3D layout — FORBIDDEN (D2/D11); the layout is the UMAP-linear-radial force-directed hybrid only.
- Graph-analytics retrieval framework (depth, subtree_size, branching_factor, cluster_id, wl_hash, `backend/analytics/`) — FORBIDDEN (D3/D11); retrieval is the triple product only.
- Llama as an SLM target — FORBIDDEN (D9); production and harness both run Nous-Hermes-2-DPO.
- Two-panel hover/click split — FORBIDDEN (D4); one unified knowledge-panel anatomy, one code path.
- The `Editor` fourth foundational fixture — REMOVED (D7/§S.1); gestures are panel-scheme intrinsics.
- The standalone retrieval sidebar (`#sidebar`/`#rs-latch`) — REMOVED (§S.3); in-editor halos subsume it.
- Panel/node chrome (coloured header, hash hue, ×, minimiser, top bar) — REMOVED (§S.4); black-slate design only.
- Stray dotted UI lines / dotted debug overlays — REMOVED (D11); the 2D↔3D arrow is solid.
- Real-backend → stub fallback in production — FORBIDDEN (D9); failures are loud (503 + halted cascade).
- BlockNote / MDXEditor, and ANY editor that owns document state — rejected. **Milkdown is adopted** (EDIT-03, user override 2026-06-17, `docs/MILKDOWN_SLATE_GOAL.md`) ONLY as the in-slate edit layer behind a controlled-view seam (store = sole truth); it must never become authoritative frontend state.
- Multi-user / auth / team / sprint artifacts — single-operator app by design.
- Rebuilding already-working backend (lifecycle, dual pipelines, retrieval index, Kuzu persistence, scan streaming, WS framing) — brownfield baseline is preserved.
- Deferred to v2: splitting the monolithic `routes.py` / `sim_frontend.py` (MAINT-01/02); incremental mid-scan UMAP refit + embedder thread-safety hardening (PERF-01/02).

## Current State

**v1.0 Live Acceptance shipped 2026-06-21.** All 18 v1 requirements validated on the real stack (`all_real: true`): REPL `env-scenario --name all` 95/95 + Playwright e2e 24/24 green in BOTH stub and real modes; the four lodestar probes + `probe_no_mocks` + `probe_pattern_map` + `probe_live_scan_with_cleanup` all pass. The project's core success metric — the four lodestar use cases run end-to-end against real subsystems — is **met**. Next: v2.0 Maintainability & Performance (`/gsd-new-milestone`).

## Context

- **Brownfield, doc-driven.** `docs/` is the authoritative target; code is iterated toward it. Source-of-truth precedence: `docs/USER_REQUIREMENTS_VERBATIM.md` (supreme) → `DOMAIN_MODEL.md` → `FRONTEND_REDESIGN.md` + `docs/frontend/` → `DOC_MAP.md`. `MORTEGON_INTEGRATION_SCHEME.md` and `CODEBASE_GAP_ANALYSIS.md` are historical/superseded.
- **The frontier is finish-and-verify, not build.** Backend is mature; the §T black-slate editor and §U HTML-dedup content-tree are built and served at `/`. The remaining §T/§U/§V work is the REPL-driven verification matrix, two open live bugs (retrieval id-scheme mismatch `c_<hash>` vs `c_<hash>_<hash>` at the scanner-bookkeeping boundary — "do not interfere"; the noetic per-workspace scan nav anomaly), and the §E.1 HtmlStrategy arm — plus the no-mocks remediation and forbidden-code deletion.
- **Verification idiom.** Three tiers: pytest (`backend/tests/`), the `env-scenario` REPL contract (`scripts/sim_frontend.py`, ~92-96 scenarios, both modes), and `scripts/probe_live_*.py` E2E probes (`all_real:true`). Every phase carries a named scenario / probe / `all_real` criterion.
- **Editor edit-layer decision (resolved 2026-06-17 — Milkdown).** `docs/MILKDOWN_SLATE_GOAL.md` supersedes the CM6 lean in `docs/EDITOR_INTEGRATION_ASSESSMENT.md`: **Milkdown** is the in-slate edit/decoration layer behind `mount`, kept a CONTROLLED VIEW (store = sole truth, inbound replace-all / outbound commit, reconnect-re-render identity). The `magic_markdown` model + store/gateway seam stay unchanged. A scoped Phase 2 sub-task, not a from-scratch editor build. `@mdxeditor/editor` removed.
- **Known sharp edges:** GPT4All native embedder is not thread-safe (RLock-guarded in `embedding_service.py`); two entry points (`app.py` vs `backend/main.py`); backend port 8080 vs REPL default 8000 (pass `--backend http://127.0.0.1:8080`); kuzu version drift (`requirements.txt` 0.3.2 vs docs ≥0.11 file-based); unpinned langgraph/selenium/webdriver_manager; 14 ledgered legacy test failures; stale `fixture::editor` can survive in `_default` Kuzu DB.

## Constraints

- **Tech stack**: Python 3.13 FastAPI (`backend/main.py`, port 8080) + custom vanilla-ESM 3D/2D frontend (Three.js r128 + `backend/static/js/fe/*.mjs`). Windows 11 + CUDA. Kuzu graph DB. GPT4All (SLM + nomic embedder), Selenium/Firefox (`geckodriver.exe`), LangGraph. — The on-device single-operator architecture is fixed.
- **Architecture**: Backend computes (layout, embeddings, PageRank); frontend renders only — no UMAP runtime, no embedding fitter client-side. (D10)
- **Lifecycle**: One dispatcher chokepoint for every mutation; append-only evolution log; idempotency keys; optimistic concurrency (last-write-wins, rollback is the conflict tool). (D10)
- **Schema**: One ConceptNode dataclass, one ConceptEdge table; `type_hint` is a naming convention, not a discriminator. (D8)
- **Reliability**: No-mocks contract — real subsystems always in production; `WFH_FAKE_*` gates are harness-only; failures are loud 503s. (D9)
- **Process**: Doc-first — capture requirement verbatim → audit code → record gap → only then change code. A screenshot is not feature proof. (D1)
- **Performance**: Native embedder serialized via per-model RLock (Windows access-violation mitigation, not a fix).

## Key Decisions

<!-- D1–D11 are LOCKED project decisions per the ADR source-of-truth (USER_REQUIREMENTS_VERBATIM, precedence 0). -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| D1 — Doc-first, correctness over comprehensiveness | A screenshot is not feature proof; the REPL/probe against the live full stack is | ✓ Locked |
| D2 — 3D layout is UMAP-linear-radial force-directed (concentric spheres FORBIDDEN) | UMAP places chunks, force-directed converges along root-URL rays, hard-collider repulsion | ✓ Locked |
| D3 — Retrieval ranks by triple product `pagerank · tfidf_cos · nomic_cos` (graph-analytics FORBIDDEN) | The two embedding axes (nomic/description, TF-IDF/rendering) never mix | ✓ Locked |
| D4 — One unified knowledge-panel model | One anatomy, one code path; pinned panel freezes at the hover screen rect | ✓ Locked |
| D5 — Strict retrieval scroll-spine | Chunks collapsed-hidden by default; only scroll-visible OR pinned-referenced visible; no third path | ✓ Locked |
| D6 — Data-agnostic recursive compile | One syntax-agnostic descent; data block dissolves into the field-tree; `+→`/`+↓` growth | ✓ Locked |
| D7 — THREE foundational fixtures (§S; Editor removed) | Database/WebBrowser/Agent only; mutation gestures are panel-scheme intrinsics | ✓ Locked |
| D8 — One ConceptNode record, one ConceptEdge table | `edge_type` is the union enum; never two edge tables | ✓ Locked |
| D9 — No-mocks contract (no Llama; no stub fallback in production) | Real subsystems always; failures are loud 503s | ✓ Locked |
| D10 — Backend computes, frontend renders | Layout/embeddings/PageRank are backend services; frontend has no UMAP/embedding runtime | ✓ Locked |
| D11 — Forbidden concepts (hard deletions) | Concentric spheres, graph analytics, Llama, two-panel split, dotted lines, concept rings, Editor fixture, retrieval sidebar, panel chrome | ✓ Locked |

## Planning Granularity Contract

Pins GSD's agent/task/step grain onto the `DOC_MAP.md` altitude ladder so plans
sample **finely enough to be verifiable but not so finely they become
`code_specs` (over-sampled) nor so coarsely they restate design docs (aliased /
under-sampled)**. This is the Nyquist criterion: sample each requirement at the
minimum resolution that reconstructs its behaviour. Enforced by
`workflow.nyquist_validation: true` + `/gsd-validate-phase`.

| GSD grain | DOC_MAP altitude | Definition | Sample (verification) |
|---|---|---|---|
| **Agent** (spawned workstream) | register / surface | ONE independent, non-colliding workstream (e.g. a backend service surface vs the frontend slate); spawn only when there is no shared mutable state | n/a — a bundle of tasks |
| **Task** | `code_constraints/` (must-hold / must-not) | advance ONE programming-surface constraint to a verifiable state | exactly ONE named project-idiom check: an `env-scenario`, a `probe_live_*.py`, or `all_real: true` |
| **Step** | `code_specs/` (typed fn + pre/post) | ONE atomic commit — one function/contract/file change that compiles and passes its local check | the commit's own green check |

**DO** — a task names the `code_constraints` surface it touches **and** its single
acceptance scenario/probe.
**DON'T (too general / aliased)** — a task that restates a `DOMAIN_MODEL`/feature
paragraph with no surface and no named check.
**DON'T (too specific / oversampled)** — a task that inlines `code_specs`
pre/post-conditions, or splits one commit's function across multiple tasks.

**Sampling-adequacy gate:** every `REQ-*` must map to ≥1 named scenario/probe (no
aliased requirement); `/gsd-validate-phase` + the `gsd-nyquist-auditor` fill gaps
and flag over-decomposed plans.

**Shared-stack rule (why agents don't run concurrently here):** verification runs
against the SINGLE real backend (port 8080, Kuzu `_default`, headful Firefox
singleton), so executor agents run **sequentially** (`workflow.use_worktrees:
false`) — parallel worktrees would collide on the port / DB / driver. Agents
sample *breadth* (independent surfaces); they do not run concurrently against the
live stack. Per-agent isolation, when needed, uses the `db_janitor` `wfh_test_`
temp-DB convention + a distinct `workspace_id`, never a second backend on 8080.

**Frontend-render sampling (the REPL's blind spot):** the `env-scenario` contract
verifies the API/WebSocket *seam* only — it does not render a browser. Render-level
criteria (the §11 black-slate DOM audit, caret-at-click, `{`-autocomplete, halo
z-order + token-anchored re-anchor, panel⇄graph toggle, projector) sample via
`frontend_e2e/*.spec.js` **Playwright** assertions (Bash-runnable `npm run
test:e2e`, so `gsd-verifier` executes them; the `playwright` MCP server in
`.mcp.json` is for *interactive* driving by `gsd-ui-researcher` / debugging). A
§T/§U/§V frontend task names a Playwright spec as its acceptance — never a
screenshot (D1).

**Model sampling (fan-out vs decision):** `.planning/config.json` `model_overrides`
routes the high-volume fan-out / structured-sampling agents (codebase-mapper,
doc-classifier→Haiku, doc-synthesizer, researcher, pattern-mapper,
**nyquist-auditor**, ui-researcher) to **Sonnet** so the FULL gate chain
(research + plan-check + verifier + nyquist + ui + post-planning-gaps) runs at a
higher sample rate for affordable cost; the fan-in *judgment* agents (planner,
plan-checker, roadmapper, verifier) stay on **Opus**. Higher sampling = run every
quality gate, cheaply — not N parallel planners.

---
*Last updated: 2026-06-21 after v1.0 (Live Acceptance) milestone — all 18 v1 requirements validated on the real stack; moved to Validated; Active is now the v2.0 Maintainability & Performance candidate set. Brownfield bootstrap baseline: 2026-06-14.*
