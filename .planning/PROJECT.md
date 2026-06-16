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

### Active

<!-- Gap-oriented frontier. The near-done §T/§U/§V work is FINISH-AND-VERIFY (convert browser-verified work into the REPL/probe idiom), not build-from-scratch. REQ-IDs match .planning/REQUIREMENTS.md. -->

**Phase 1 — Honest Baseline:**
- [ ] REL-01 / REL-02: No-mocks SLM remediation — real-load failure raises 503 (cascade halts) instead of `_fake=True` + `[stub-slm]`; CPU real→real fallback preserved (`slm_client.py`, `_make_slm_for_compute`, agent tick).
- [ ] FIX-01 / FIX-02: Exactly THREE foundational fixtures (Agent, WebBrowser, Database); no `fixture::editor` anywhere; stale `_default` Editor node swept; mutation gestures intrinsic to the panel↔compute-graph scheme.
- [ ] HYG-01 / HYG-02: Hard-delete forbidden/legacy code (`backend/analytics/`, `backend_slow/`, `_legacy_frontend/`, deprecated `cluster_distillation.py`, Fibonacci/concentric residue, Llama refs); pin `langgraph`/`selenium`/`webdriver_manager`, resolve kuzu drift, document launch + port alignment, remove `@mdxeditor/editor`.

**Phase 2 — Black-Slate Field Editing (§T):**
- [ ] EDIT-01 / EDIT-02: Pure-print panels; hover overlay → textarea on click (caret-at-click); Shift-Enter multiline; Enter commits through the lifecycle; `+→`/`+↓` field-tree growth; `{`-autocomplete; empty rows hide.
- [ ] EDIT-03: Resolve the in-slate edit-layer decision (custom vs CodeMirror 6 per `docs/EDITOR_INTEGRATION_ASSESSMENT.md`); if CM6, integrate ONLY behind `mount` (rest-render/reveal-raw, caret/IME/undo), `store`/`gateway`/`magic_markdown` unchanged; no authoritative frontend state.

**Phase 3 — HTML Dedup + Halo Retrieval Render (§U/§V):**
- [ ] HTML-01: HTML chunk slate body = deduplicated content as a pure-text tree (collapse wrappers, token-set dedup, surface href/src) built from `fields`; §U golden 6/6; one detector / mirrored strategy order.
- [ ] HALO-01 / HALO-02: Apparition halo — candidate-name-only phantoms, triple-product ranking, autoregressive click-walk, circular root-field-only collapsed node, constant-similarity ray slide, soft/hard promotion, solid 2D↔3D arrow.

**Phase 4 — Live Layout, Signal & Pattern (§R/§11.5):**
- [ ] UMAP-01: 6D UMAP fit (3D manifold + camera-azimuth-rotated HSV) across Projector, Halo phantoms, readout nodes; frontend renders only.
- [ ] SIG-01: Signal-stream — one iterable signal at a time, play/pause/step rollout, cascade re-fires per visible signal across pattern_map / url_set / Database.concept.
- [ ] PAT-01: Live `pattern_map` ConceptNode materialises during scan and updates in place; golden-trio gate; second scan accretes into the same peer; PageRank over the same Kuzu graph.

**Phase 5 — Three-Register Synthesis & Live Acceptance:**
- [ ] REG-01: Real/Imaginary/Symbolic registers bound by the compose-compile-perimeter loop runnable both ways (REPL or GUI); 2D/3D separation; WS telemetry mirroring; purge returns to the three-fixture baseline.
- [ ] ACC-01 / ACC-02: `live-scan-real-with-cleanup` probe passes; all four lodestar live probes pass; `all_real: true`; `full-smoke` green in both modes with §T/§U/§V/§R scenarios included.

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
- WYSIWYG/ProseMirror/Lexical editors (Milkdown/BlockNote/MDXEditor) — rejected (`docs/EDITOR_INTEGRATION_ASSESSMENT.md`); the slate is not markdown and holds no authoritative state.
- Multi-user / auth / team / sprint artifacts — single-operator app by design.
- Rebuilding already-working backend (lifecycle, dual pipelines, retrieval index, Kuzu persistence, scan streaming, WS framing) — brownfield baseline is preserved.
- Deferred to v2: splitting the monolithic `routes.py` / `sim_frontend.py` (MAINT-01/02); incremental mid-scan UMAP refit + embedder thread-safety hardening (PERF-01/02).

## Context

- **Brownfield, doc-driven.** `docs/` is the authoritative target; code is iterated toward it. Source-of-truth precedence: `docs/USER_REQUIREMENTS_VERBATIM.md` (supreme) → `DOMAIN_MODEL.md` → `FRONTEND_REDESIGN.md` + `docs/frontend/` → `DOC_MAP.md`. `MORTEGON_INTEGRATION_SCHEME.md` and `CODEBASE_GAP_ANALYSIS.md` are historical/superseded.
- **The frontier is finish-and-verify, not build.** Backend is mature; the §T black-slate editor and §U HTML-dedup content-tree are built and served at `/`. The remaining §T/§U/§V work is the REPL-driven verification matrix, two open live bugs (retrieval id-scheme mismatch `c_<hash>` vs `c_<hash>_<hash>` at the scanner-bookkeeping boundary — "do not interfere"; the noetic per-workspace scan nav anomaly), and the §E.1 HtmlStrategy arm — plus the no-mocks remediation and forbidden-code deletion.
- **Verification idiom.** Three tiers: pytest (`backend/tests/`), the `env-scenario` REPL contract (`scripts/sim_frontend.py`, ~92-96 scenarios, both modes), and `scripts/probe_live_*.py` E2E probes (`all_real:true`). Every phase carries a named scenario / probe / `all_real` criterion.
- **Editor edit-layer decision (just authored).** `docs/EDITOR_INTEGRATION_ASSESSMENT.md` — keep the custom `magic_markdown` model + store/gateway seam; optionally adopt CodeMirror 6 as ONLY the in-slate edit + decoration layer (rest-render/reveal-raw, caret/IME/undo); alternative is stay fully custom. Folded as a scoped sub-task in Phase 2, not a from-scratch editor build. Remove `@mdxeditor/editor`.
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

---
*Last updated: 2026-06-15 — added the Planning Granularity Contract + `.planning/config.json` (granularity `standard`, nyquist gate on, sequential executors for the shared real stack). Brownfield bootstrap baseline: 2026-06-14.*
