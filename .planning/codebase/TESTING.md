# Testing Patterns

**Analysis Date:** 2026-06-14

This codebase has a distinctive, three-tier verification surface. Pytest is the *unit/integration* layer, but the **primary acceptance bar** is the `sim_frontend.py` REPL harness's `env-scenario` contract (~92-96 scenarios that must stay green in BOTH stub and real modes) plus `scripts/probe_live_*.py` end-to-end probes against real subsystems. Read CLAUDE.md "Verification Surface (§11.7 / §11.8)" alongside this doc.

## Test Framework

**Runner:**
- **pytest** + **pytest-asyncio** (`backend/test_requirements.txt`).
- Config: no dedicated `pytest.ini`/`pyproject.toml`; markers registered in `backend/tests/conftest.py::pytest_configure` (the `live` marker).
- HTTP testing via `httpx` + FastAPI `TestClient`.

**Assertion Library:** plain `assert` (pytest rewriting); probes/harness use explicit `_ok` / `_err` reporters returning exit codes.

**Run Commands:**
```bash
pip install -r backend/test_requirements.txt   # pytest pytest-asyncio httpx numpy

pytest backend/tests                            # full unit/integration suite
pytest backend/tests/test_graph_editor.py       # one file
RUN_LIVE_AGENT_TESTS=1 pytest -m live           # opt-in live (Selenium/network) tests

# REPL harness contract (the real acceptance bar):
python scripts/sim_frontend.py --backend http://127.0.0.1:8080 env-scenario --name full-smoke
python scripts/sim_frontend.py env-scenario --name <specific>
python scripts/sim_frontend.py watch-activity   # in-place 7-row dashboard

# Live end-to-end probes (real GPT4All/nomic/Selenium/LangGraph):
python scripts/probe_no_mocks.py http://127.0.0.1:8080
python scripts/probe_live_archive_scan.py
```

## Test File Organization

**Location:** separate `backend/tests/` directory (NOT co-located with source). ~45 `test_*.py` files plus `conftest.py` and a `test_kuzu_db/` subdir.

**Naming:** `test_<subject>.py`; test functions `test_<behavior>`.

**Three tiers (where each kind of test lives):**
```
backend/tests/test_*.py        # pytest unit + integration (Kuzu, FastAPI, pure-core)
scripts/sim_frontend.py        # REPL harness: ~160+ actions, 19 categories, env-scenarios
backend/tests/test_sim_env_scenarios.py   # pytest wrapper gating the NO-BACKEND scenarios
scripts/probe_*.py             # live end-to-end evidence probes (real subsystems)
scripts/test_*.py              # standalone offline pipeline/mapper checks (run directly)
```
The pytest wrapper `backend/tests/test_sim_env_scenarios.py` only wraps scenarios that run fully in-process (`_NO_BACKEND_SCENARIOS`: `action-registry-coverage`, `route-coverage`, `chunker-regression`, etc.). Backend-requiring scenarios stay in the harness and run against a live server.

## Test Structure

**Pure-in-process smoke tests** (fast, deterministic, no Kuzu/FastAPI) — preferred for logic. Example `backend/tests/test_concept_lifecycle_and_cascade.py`:
```python
from __future__ import annotations
import json, threading, time
import pytest

class _StubNode:
    """Mimics the ConceptNode dataclass surface that lifecycle + cascade read."""
    def __init__(self, *, concept_id: str, data: str = "", ...): ...

class _StubGraphEditor:
    """Just enough surface for cascade scheduler + spawn helper."""
    def get_concept(self, concept_id: str): return self.nodes.get(concept_id)
```
Pattern: hand-rolled `_Stub*` classes that mimic exactly the surface the unit-under-test reads — no mock framework. The functional-core split (`ConceptDiff.from_pre_post`) makes branches testable with zero I/O stubs.

**DB-touching tests** use session/module fixtures from `conftest.py`.

**Patterns:**
- Setup/teardown via pytest fixtures (`temp_kuzu_db`, `clean_db`, `client`).
- Stub objects via plain classes, not `unittest.mock`.
- Assertions are direct `assert`; harness scenarios return an exit code.

## Mocking

**Framework:** none for unit tests — hand-built stub classes + `monkeypatch` (used in `test_chat_service.py`, `test_fluid_engine.py`, `test_layout_recompute.py`). The `[mypy-backend.tests.*]` block sets `ignore_errors = True` precisely because tests monkeypatch and use loose `Any` shapes.

**Env-gate "fakes" (the canonical mocking mechanism) — stub vs real:** real subsystems are swapped for deterministic fakes via environment variables, NOT mock objects. This is the central testing lever:

| Subsystem | Real (production default) | Fake gate (harness-only) | Gate read at |
|---|---|---|---|
| SLM | GPT4All Nous-Hermes-2-Mistral-7B-DPO on CUDA | `WFH_FAKE_SLM=1` | `backend/services/slm_client.py` |
| Embedder | GPT4All Embed4All nomic-embed on CUDA | `WFH_FAKE_EMBEDDER=1` | `backend/services/embedding_service.py` |
| Selenium | Headful Firefox via `backend/drivers/geckodriver.exe` | `NO_WEBDRIVER=1` | `backend/main.py` |
| LangGraph | `langgraph.graph.StateGraph` | none (missing = hard error) | — |

`SLMClient` reads `WFH_FAKE_SLM` once at singleton construction (`self._fake`), and the stub path prefixes output with `[stub-slm]` so tests can assert real vs stub. **The contract: `env-scenario --name full-smoke` must be green in BOTH the no-gate (real) and `WFH_FAKE_*=1` (stub) modes.**

**What to Mock:** external heavyweight subsystems — only via the env-gate fakes above. Internal collaborators are stubbed with minimal `_Stub*` classes.

**What NOT to Mock:** in production NOTHING is faked — real-backend→stub fallback is forbidden (§8D.46). Live probes assert this via `GET /api/subsystem_status` → `all_real: true` (`scripts/probe_no_mocks.py` checks each subsystem reports its real backend AND smoke-calls it: SLM output must not begin `[stub-slm]`, embedder must return a non-fake 768-dim vector, etc.).

## Fixtures and Factories

Defined in `backend/tests/conftest.py`:
- `temp_kuzu_db` (session) — throwaway Kuzu DB via `db_janitor.temp_db_dir("conftest_session")`; overrides `backend.database.DB_PATH`, inits schema, yields a `_LiveConnProxy`.
- `clean_db` — wipes `DomNode`s before a test.
- `client` (module) — FastAPI `TestClient(app)` context.
- `_LiveConnProxy` — delegates to the *current* `backend.database` connection, reopening lazily; fixes a full-suite ordering bug where the app lifespan's `close_db()` closed a connection earlier fixtures had handed out.

**Test-DB hygiene (§R.9) — mandatory:** never `tempfile.mkdtemp` a throwaway DB directly. Use `backend/services/db_janitor.py` (`temp_db_dir(label)` ctx-manager, or `register_for_cleanup(new_temp_db_path(label))`). One canonical `wfh_test_` prefix. `conftest.py::pytest_sessionfinish` runs `sweep_stale_tmp(max_age_hours=24.0)` at session end; `POST /api/maintenance/cleanup_test_artifacts` collects strays. `_default` and human-named workspaces are never swept.

## Coverage

**Requirements:** no coverage-percentage gate. Coverage is enforced *behaviorally* by the env-scenario contract and the live probes — the bar is "every lodestar use case runs end-to-end against real subsystems on every commit," not a line %.

- `env-scenario --name full-smoke` must stay green (stub + real). Prior states: suite 310/0, full-smoke 92/92 both modes (per MEMORY).
- `RUN_LIVE_AGENT_TESTS=1` gates the network/Selenium `@pytest.mark.live` tests (skipped on CI; see `backend/tests/test_agent_loop.py`).
- 14 pre-existing legacy test failures are ledgered (per MEMORY), not yet fixed.

## Test Types

**Unit (pure-in-process):** stub-class + functional-core tests, no Kuzu/FastAPI (e.g. `test_concept_lifecycle_and_cascade.py`). Fast and deterministic.

**Integration:** DB-touching (`temp_kuzu_db`) + FastAPI `TestClient` (`test_api_endpoints.py`, `test_graph_editor.py`, `test_agent_loop.py`).

**Scenario contract:** `env-scenario` flows in `scripts/sim_frontend.py` (`_ENV_SCENARIOS` + `_ACTIONS`) — multi-step UIState envelope roundtrips driven via REST + WS (e.g. `syntax-agnostic-compile`, `cascade-reflow-roundtrip`, `watch-activity-mirror`, `three-fixtures-present`).

**Live E2E probes:** `scripts/probe_live_*.py` — real Selenium scan → real TF-IDF/nomic retrieval → real LangGraph+GPT4All compile, asserting `all_real:true`. These are the §8D.45/47/48/49 acceptance artifacts. A screenshot is explicitly NOT feature proof; the probe is.

## Common Patterns

**Async testing:** pytest-asyncio; the FastAPI app + WS frames are driven through `TestClient` and the harness's WS tail.

**Stub-vs-real assertion:**
```python
out = SLMClient.instance().generate_text("ping")
assert not out.startswith("[stub-slm]")   # proves the real model ran
```

**Path bootstrap in scripts/probes (required before backend imports):**
```python
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

**Backend/port alignment for the harness:** backend default port is 8080 (`backend/main.py`) but the REPL defaults to `http://localhost:8000` — pass `--backend http://127.0.0.1:8080` (global flag, BEFORE the subcommand) or set `WFH_BACKEND_URL`.

**Windows console UTF-8 (probes):** `sys.stdout.reconfigure(encoding="utf-8")` so `→`/`§` glyphs print; ANSI dashboard codes are gated off when `os.name == "nt"`.

---

*Testing analysis: 2026-06-14*
