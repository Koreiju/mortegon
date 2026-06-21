# Testing Patterns

**Analysis Date:** 2026-06-20

This codebase has a distinctive, **four-tier** verification surface, and it is the project's standout asset. Pytest is the unit/integration layer; the **primary acceptance bar** is the `sim_frontend.py` REPL harness's `env-scenario` contract (92-96 scenarios, green in BOTH stub and real modes); Playwright e2e covers render-level DOM acceptance the REPL structurally cannot reach; the fe unit tests (`node --test`) cover the vanilla-ESM frontend's pure model layer. All four run unified under `npm run test:all`. Read CLAUDE.md "Verification Surface (§11.7 / §11.8)" alongside this doc — CLAUDE.md is the requirements-anchor source, this doc is the how-to-run reference.

## Unified Full-Stack Test Framework — Entry Point

`scripts/run_full_stack_tests.py` (`npm run test:all` / `npm run test:all:real`) is THE single entry point. It boots **one** managed backend (stub by default, the all_real CUDA stack with `--real`), optionally isolated via `backend/services/db_janitor.py` (`--no-isolated` to use the operator's real `kuzu_db`), waits for readiness, and runs every backend-dependent tier against that SAME server before tearing it down — so the REPL contract and the Playwright suite exercise the same stack.

| Tier | What | Backend needed |
|---|---|---|
| `pytest` | `backend/tests/` (`-q -p no:cacheprovider`) | no |
| `repl` | `sim_frontend.py env-scenario --name <scope>` — `all` (default, ~95 scenarios) or `full-smoke` (curated 92-scenario chain) | yes |
| `e2e` | Playwright `frontend_e2e/*.spec.js` — render-level DOM acceptance | yes |
| `probes` (`--real` only) | `probe_no_mocks.py` + the four `probe_live_*.py` lodestars | yes, real |

```bash
npm run test:all                                                # stub: pytest + repl(all) + e2e
npm run test:all:real                                           # all_real CUDA stack + repl + e2e + live probes
python scripts/run_full_stack_tests.py --only e2e               # one tier
python scripts/run_full_stack_tests.py --only repl --only e2e   # several tiers
python scripts/run_full_stack_tests.py --no-pytest --port 8090  # custom port, skip pytest
python scripts/run_full_stack_tests.py --real --fixture-scan    # deterministic acceptance: serves test_packages/ locally, no archive.org throttle
python scripts/run_full_stack_tests.py --only repl --repl-scope full-smoke   # curated 92-scenario subset
```

Exit code 0 = every selected tier green. STUB_GATES (`WFH_FAKE_SLM=1`, `WFH_FAKE_EMBEDDER=1`, `NO_WEBDRIVER=1`) are applied automatically in stub mode and stripped in `--real` mode (`scripts/run_full_stack_tests.py:42,58-64`). The per-requirement → command mapping + fast/acceptance/real-vs-stub run policy live in [`.planning/TEST_MATRIX.md`](../TEST_MATRIX.md) — consult that for `gsd-verifier` usage. The `@playwright/mcp` server (`.mcp.json`) drives the live UI interactively for discovering/debugging new e2e specs.

**v1 milestone result (2026-06-19, per project memory):** real-stack acceptance PASS — `all_real:true` + `probe_no_mocks` + all 4 lodestar `probe_live_*.py` + `scan_with_cleanup` + full-smoke 92/92 in BOTH modes + e2e 26/0 failing.

**Critical environment lesson:** a clean GPU (0 VRAM used, 0 lingering Python processes) is required before real-mode runs — long dev sessions wedge backends because CUDA/Selenium handles are uninterruptible. The `--real` harness's own Selenium boot is flaky under load; prefer running `full-smoke` directly against an already-booted real backend over nesting it inside the orchestrator when debugging.

## Tier 1 — pytest (`backend/tests/`)

**Runner:** pytest + pytest-asyncio (`backend/test_requirements.txt`). No dedicated `pytest.ini`/`pyproject.toml` `[tool.pytest]` section; the `live` marker is registered in `backend/tests/conftest.py::pytest_configure`. HTTP testing via FastAPI `TestClient` (httpx-backed).

**Assertion style:** plain `assert` (pytest rewriting). Harness/probes use explicit `_ok(...)` / `_err(...)` reporter helpers that print and set exit codes, rather than pytest assertions.

**Run commands:**
```bash
pip install -r backend/test_requirements.txt    # pytest pytest-asyncio httpx numpy

pytest backend/tests                             # full unit/integration suite
pytest backend/tests/test_graph_editor.py        # one file
RUN_LIVE_AGENT_TESTS=1 pytest -m live            # opt-in live (Selenium/network) tests, skipped otherwise
```

**Location:** centralized `backend/tests/` (NOT co-located with source) — ~45 `test_*.py` files plus `conftest.py` and a `test_kuzu_db/` fixture-data subdir. Naming: `test_<subject>.py`; functions `test_<behavior>`.

**Structure — pure-in-process smoke tests (preferred for logic):** Example `backend/tests/test_concept_lifecycle_and_cascade.py`:
```python
class _StubNode:
    """Mimics the ConceptNode dataclass surface that lifecycle + cascade read."""
    def __init__(self, *, concept_id: str, data: str = "", ...): ...

class _StubGraphEditor:
    """Just enough surface for cascade scheduler + spawn helper."""
    def get_concept(self, concept_id: str): return self.nodes.get(concept_id)
```
Pattern: hand-rolled `_Stub*` classes mimicking exactly the surface the unit-under-test reads — **no mock framework**. The functional-core split (`ConceptDiff.from_pre_post`) keeps branches testable with zero I/O.

**DB-touching tests** use the session/module fixtures defined in `conftest.py` (see Fixtures section below).

**Mocking:** none for unit tests beyond hand-built `_Stub*` classes + `monkeypatch` (used in `test_chat_service.py`, `test_fluid_engine.py`, `test_layout_recompute.py`). `mypy.ini`'s `[mypy-backend.tests.*]` block sets `ignore_errors = True` precisely because tests monkeypatch and use loose `Any` shapes.

## Tier 2 — REPL Harness Contract (`scripts/sim_frontend.py`)

**~9,500 lines.** ~160+ actions across 19 categories, exposed as both a low-level action CLI and a high-level `env-scenario` registry (`_ENV_SCENARIOS`). Each project requirement maps to a named scenario.

```bash
python scripts/sim_frontend.py --backend http://127.0.0.1:8080 env-scenario --name full-smoke   # curated 92-scenario chain
python scripts/sim_frontend.py --backend http://127.0.0.1:8080 env-scenario --name all          # ~95: full-smoke + every other registered scenario
python scripts/sim_frontend.py --backend http://127.0.0.1:8080 env-scenario --name <specific>   # one named scenario
python scripts/sim_frontend.py watch-activity      # in-place ANSI seven-row dashboard (scan/retrieval/visible-3D/hidden-3D/pinned/compile/subsystems)
```

**`full-smoke` (`scripts/sim_frontend.py:8407-8530`)** is the ordered chain: fast/no-embedder scenarios first, then heavier ones; `_env_scenario_full_smoke` runs them in sequence and fails loud naming exactly which of the N scenarios broke. **`all` (`:8535+`)** computes `full-smoke`'s chain PLUS every other registered `_ENV_SCENARIOS` entry not already in it — drift-resistant because the extras are computed at run time from the registry, not hand-maintained.

**Backend/port alignment gotcha:** backend default port is 8080 (`backend/main.py`); the REPL's own default is `http://localhost:8000`. Always pass `--backend http://127.0.0.1:8080` (a **global** flag, placed BEFORE the subcommand) or set `WFH_BACKEND_URL`, or scenarios will silently 404/timeout against the wrong port.

**§E.1/§R/§S scenario families** (representative, all must stay green per CLAUDE.md): `syntax-agnostic-compile`, `markdown-restructure-roundtrip`, `inverse-map-state-space`, `ontology-projection-roundtrip`, `readout-panel-projection`, `iterated-signal-rerender`, `db-janitor-hygiene`, `three-fixtures-present` (formerly `four-fixtures-present`, kept as alias), `editor-primitives-roundtrip`, `cascade-reflow-roundtrip`, `complex-interaction-walkthrough`, `signal-stream`, `rollout`, `node-fold`, `compile-expand-collapse`, `watch-activity-mirror`, `pattern-map-live-update`, `urls-panel-iteration`, `library-middleware`, `perimeter-rescale`, `apparition-mode`, `database-concept-signal-stream`, `6d-umap-format`, `agent-three-primitives-chain`, plus `live-scan-real-with-cleanup` (all_real-gated, skips in stub).

**Pytest wrapper for no-backend scenarios:** `backend/tests/test_sim_env_scenarios.py` wraps ONLY the scenarios in `_NO_BACKEND_SCENARIOS` that run fully in-process (`action-registry-coverage`, `route-coverage`, `chunker-regression`, etc.). Backend-requiring scenarios stay exclusively in the harness, run against a live server.

## Tier 3 — Playwright e2e (`frontend_e2e/`)

```bash
npm run test:e2e                              # self-boots a stub backend if none running
WFH_FRONTEND_URL=http://127.0.0.1:8080 npx playwright test -c frontend_e2e/playwright.config.js
```

**Specs (`frontend_e2e/`):** `black_slate.spec.js`, `edit.spec.js`, `halo.spec.js`, `milkdown.spec.js`, `projector.spec.js` — 26 passing as of the v1 milestone.

**Config (`frontend_e2e/playwright.config.js`):**
- Targets the served magic-markdown frontend at `http://127.0.0.1:8080/` (`backend/templates/editor.html` + `backend/static/js/fe/*.mjs`).
- `fullyParallel: false`, `workers: 1` — single shared backend (port 8080, Kuzu `_default`) means tests must serialize.
- `webServer` self-boots `scripts/_serve_for_tests.py` with `WFH_FAKE_SLM=1 WFH_FAKE_EMBEDDER=1 NO_WEBDRIVER=1` and `reuseExistingServer: true` — this is what makes bare `npm run test:e2e` self-contained AND lets it transparently reuse a backend already booted by `run_full_stack_tests.py`.
- These tests verify render-level acceptance (DOM structure, computed styles, real interactions) that the REPL/`env-scenario` contract structurally cannot reach — the REPL exercises the API + WebSocket seam; Playwright drives the actual served browser.

## Tier 4 — Frontend Unit Tests (`node --test`)

```bash
npm run test:fe                                          # node --test backend/static/js/fe/*.test.mjs
node --test backend/static/js/fe/magic_markdown.test.mjs # one file
```

**Files:** `magic_markdown.test.mjs`, `magic_markdown_panel.test.mjs`, `magic_markdown_gestures.test.mjs`, `magic_markdown_halo.test.mjs`, `projector.test.mjs`, `spine.test.mjs`, `integration.test.mjs` — all co-located in `backend/static/js/fe/` next to the module they test.

**Why this tier exists and is fast/reliable:** the pure-model-vs-DOM-glue split (see CONVENTIONS.md) means most logic (`panelVDom`, `parse`, `renderPanel`, gesture transforms) is plain-data-in/plain-data-out and testable in bare Node — no DOM, no browser, no backend. Only the thin `mount`-style DOM glue is left untested at this tier (covered instead by Playwright).

## Live End-to-End Probes (`scripts/probe_live_*.py` + `probe_no_mocks.py`)

These are the §8D.45/47/48/49 acceptance artifacts — **a screenshot is explicitly NOT feature proof; the probe is** (CLAUDE.md Process Discipline). Each asserts against real GPT4All/nomic/Selenium/LangGraph, not fakes.

```bash
python scripts/probe_no_mocks.py http://127.0.0.1:8080          # §8D.46 contract: every subsystem reports real, not stub
python scripts/probe_live_archive_scan.py                       # §8D.45 outside-in: real Selenium scan → retrieval → pin → compile
python scripts/probe_live_concept_graph.py                      # §8D.47 inside-out: author/wire/compile/rollback a concept subgraph
python scripts/probe_live_agent.py                               # §8D.48 autonomous: spawn agent body, real GPT4All tick + token stream
python scripts/probe_live_iterated_compile.py                    # §8D.49 synthesis: 3-node templated compute graph, iterated real compile
python scripts/probe_live_scan_with_cleanup.py                   # §16.5: purge baseline → scan → UMAP fit → purge contract → re-scan
python scripts/probe_live_dominance_and_timed_scan.py             # §Q: timed scan + rank-dominance node-collapse over the real PageRank graph
python scripts/breadth_content_tree_smoke.py                      # §U content-tree dedup breadth smoke across multiple live sites
```

`run_full_stack_tests.py`'s `probes` tier (real mode only) runs exactly: `probe_no_mocks.py`, `probe_live_archive_scan.py`, `probe_live_concept_graph.py`, `probe_live_agent.py`, `probe_live_iterated_compile.py` (`scripts/run_full_stack_tests.py:43-49`).

**`probe_no_mocks.py` is the §8D.46 contract gate.** It checks `GET /api/subsystem_status` reports `all_real: true` AND smoke-calls each subsystem to confirm the output is genuinely real (e.g. SLM output must NOT begin with the `[stub-slm]` prefix the fake path emits; embedder must return a non-fake 768-dim vector).

## The No-Mocks Contract (§8D.46) — Stub vs Real

Real subsystems are swapped for deterministic fakes via **environment-variable gates**, never mock objects. This is the central testing lever the whole framework pivots on.

| Subsystem | Real (production default) | Fake gate (harness-only) | Gate read at |
|---|---|---|---|
| SLM | GPT4All `Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf` on CUDA — **no Llama allowed** | `WFH_FAKE_SLM=1` | `backend/services/slm_client.py` (singleton construction) |
| Embedder | GPT4All Embed4All `nomic-embed-text-v1.5.f16.gguf` on CUDA | `WFH_FAKE_EMBEDDER=1` | `backend/services/embedding_service.py:137` |
| Selenium | Headful Firefox via `backend/drivers/geckodriver.exe` | `NO_WEBDRIVER=1` | backend boot (`backend/main.py`) |
| LangGraph | `langgraph.graph.StateGraph` | none — missing import is a hard error | — |

`GET /api/subsystem_status` reports `{slm, embedder, selenium, langgraph, all_real}`. **The contract: `env-scenario --name full-smoke` (and `all`) must be green in BOTH the no-gate (real) mode AND the `WFH_FAKE_*=1` (stub) mode** — this is checked on every commit per CLAUDE.md "What Always Holds Across Iterations."

**What to mock:** ONLY the four heavyweight external subsystems above, and only via their env-gate fakes. Internal collaborators are stubbed with minimal hand-rolled `_Stub*` classes, never a mock framework.

**What NOT to mock:** in production, NOTHING is faked. Real-backend-fails → quiet-stub-fallback is forbidden; a failed load is a loud `HTTPException(503)` (see CONVENTIONS.md Error Handling). `WFH_EMBEDDER_DEVICE=cpu` is a real-to-real device override (CPU embedding is still real, not a fake) — it stays inside the no-mocks lane.

## Fixtures and Factories

Defined in `backend/tests/conftest.py`:
- `temp_kuzu_db` (session-scoped) — throwaway Kuzu DB via `db_janitor.temp_db_dir("conftest_session")`; overrides `backend.database.DB_PATH`, calls `database.init_db()`, yields a `_LiveConnProxy`.
- `clean_db` — wipes `DomNode` rows before a test (`MATCH (n:DomNode) DETACH DELETE n;`).
- `client` (module-scoped) — FastAPI `TestClient(app)` context.
- `_LiveConnProxy` — delegates to the *current* `backend.database` connection, reopening lazily if something else closed it mid-session. Fixes a full-suite-ordering bug: the app lifespan's `finally` calls `close_db()` when a `TestClient` context exits, which previously closed the session-scoped connection earlier fixtures had already handed to tests.

## Test-DB Hygiene (§R.9) — Mandatory Pattern

Never `tempfile.mkdtemp` a throwaway DB directly. Use `backend/services/db_janitor.py`:
- `temp_db_dir(label)` — context manager; guaranteed `rmtree` on exit + an `atexit` net behind it.
- `register_for_cleanup(new_temp_db_path(label))` — for import-time `WFH_DB_PATH` pins where a context manager can't wrap the lifetime (some probes must set the env var before importing the backend).
- One canonical prefix: `TEST_TMP_PREFIX = "wfh_test_"`. A `LEGACY_TMP_PREFIXES` tuple (`kuzu_inst_test_`, `kuzu_sig_test_`, `wfh_e2e_`, etc.) exists ONLY so sweeps can collect strays from older runs — never add new call sites with these.
- `sweep_stale_tmp(max_age_hours=...)` — removes stale one-off temp DB dirs (canonical + legacy prefixes). Called automatically by `conftest.py::pytest_sessionfinish`.
- `sweep_workspace_sidefiles()` — removes per-workspace side files (`concept_index_<ws>.json`, `evolution_log_<ws>.jsonl`, `layout_frame_<ws>.json`) but ONLY for test-convention workspace ids matching `_TEST_WS_RE` (`ws`, `ws_<slug>`, `probe_<slug>_<timestamp>`) — `_default` and any human-named workspace are never swept.
- `POST /api/maintenance/cleanup_test_artifacts` exposes the sweep over HTTP for the live-scan-with-cleanup probe/scenario.
- kuzu ≥ 0.11 is file-based: when `WFH_DB_PATH` points at an existing non-empty directory (the legacy `kuzu_db/` artifact layout), the store nests as `<path>/data.kuzu` (`backend/database.py::_effective_db_path`) — a fresh/file path is used directly.

## Coverage

No coverage-percentage gate. Coverage is enforced **behaviorally**: the bar is "every lodestar use case runs end-to-end against real subsystems on every commit," not a line %.

- `env-scenario --name full-smoke` (and `all`) must stay green in both stub and real modes — this is the actual coverage gate.
- `RUN_LIVE_AGENT_TESTS=1` gates the network/Selenium `@pytest.mark.live` tests (skipped by default; see `backend/tests/test_agent_loop.py`).
- Per project memory, prior full-suite states: pytest 310/0, full-smoke 92/92 both modes, e2e 26/0; a small number of pre-existing legacy test failures were ledgered historically and have since been resolved as part of the v1 milestone closure — re-verify before assuming zero outstanding failures.

## Common Patterns

**Stub-vs-real assertion:**
```python
out = SLMClient.instance().generate_text("ping")
assert not out.startswith("[stub-slm]")   # proves the real model ran, not the fake
```

**Path bootstrap in scripts/probes (required before backend imports):**
```python
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

**Async testing:** pytest-asyncio; the FastAPI app + WS frames are driven through `TestClient` and the harness's own WS-tail logic.

**Windows console UTF-8 (probes/orchestrator):** `sys.stdout.reconfigure(encoding="utf-8")` so `→`/`§`/`▸`/`▾` glyphs print correctly (`scripts/run_full_stack_tests.py:36-39`); ANSI dashboard codes in `watch-activity` are gated off when `os.name == "nt"` where they'd otherwise corrupt terminal output.

**Subprocess process-group teardown (Windows):** backend processes booted by the orchestrator use `subprocess.CREATE_NEW_PROCESS_GROUP` and are killed via `taskkill /F /T /PID <pid>` on `nt` (vs `terminate()`/`wait()`/`kill()` elsewhere) — see `kill_backend()` in `scripts/run_full_stack_tests.py:95-105`.

---

*Testing analysis: 2026-06-20*
