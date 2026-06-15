# Coding Conventions

**Analysis Date:** 2026-06-14

This is a Python 3.13 full-stack app. The backend (`backend/`) is the source of truth for conventions: FastAPI + Kuzu + GPT4All/nomic + Selenium + LangGraph. The frontend is a thick JS client (the active rebuild lives under `backend/static/` / `backend/templates/`; `_legacy_frontend/` is dead). Conventions below are Python-centric because that is where all active development happens.

## Naming Patterns

**Files:**
- Backend services: snake_case, one service per file under `backend/services/` (e.g. `concept_lifecycle.py`, `evolution_log.py`, `rollout_coordinator.py`).
- Tests: `test_<subject>.py` under `backend/tests/` (e.g. `test_concept_lifecycle_and_cascade.py`).
- Live end-to-end probes: `scripts/probe_<topic>.py` (e.g. `scripts/probe_no_mocks.py`, `scripts/probe_live_archive_scan.py`).
- One-off diagnostics: `scripts/diag_*.py` (excluded from mypy, see `mypy.ini`).

**Functions:**
- Public functions/methods: `snake_case` (e.g. `apply_update_lifecycle`, `compute_rendering_tree`, `log_edit`).
- Module-private helpers: leading underscore `_snake_case` (e.g. `_idempotency_lookup`, `_check_spawn_rate`, `_effective_db_path` in `backend/database.py`).
- Env-scenario drivers in `scripts/sim_frontend.py`: `_env_scenario_<name>` (e.g. `_env_scenario_watch_activity_mirror`).

**Variables:**
- `snake_case` for locals and module globals.
- Module-level shared state prefixed `_` and paired with a lock (e.g. `_idempotency_cache` + `_idempotency_lock` in `backend/api/routes.py`).

**Types / Classes:**
- `PascalCase` for classes and dataclasses (e.g. `ConceptDiff`, `WorkflowError`, `EditDiff`, `_StubNode`).
- Private/stub test classes prefixed `_` (e.g. `_StubNode`, `_StubGraphEditor`, `_LiveConnProxy`).
- **Domain id types are `NewType` over `str`**, suffixed `Id` — `backend/services/ids.py`: `ConceptId`, `EdgeId`, `WorkspaceId`, `ParameterCardId`, `ChunkId`, `IdempotencyKey`. These are zero-overhead at runtime but catch swapped-argument bugs at the mypy layer. New/refactored signatures should prefer them over bare `str`.

**Backing-pointer / id string schemes (data-level naming):**
- Fixtures: `fixture::<kind>::<workspace_id>` (e.g. `fixture::database::<wid>`).
- Agent backing pointers: `agent::{kind}::<pcid>`.
- Composite graph-output chunk ids: `graph__<wid>__<cid>__<sid>`.

## Code Style

**Formatting:**
- No autoformatter config detected (no black/ruff/isort config files). Style is hand-maintained: 4-space indent, ~72-char prose in docstrings, dashed comment banners (`# ---...---`) to separate sections within a module.
- `from __future__ import annotations` at the top of essentially every backend module and test (deferred annotation evaluation; required for the gradual-typing approach).

**Linting / Typing:**
- Type checking via **mypy** (`mypy.ini`), Python 3.13 target. Run: `mypy backend`.
- **Gradual-adoption strategy** (explicitly documented in `mypy.ini`): permissive global defaults (`disallow_untyped_defs = False`) with per-module tightening as surfaces migrate.
  - Hold-the-line strict modules: `backend.services.ids`, `backend.services.concept_lifecycle`, `backend.services.settings`, `backend.dom.pipeline` (these set `check_untyped_defs`/`warn_return_any`/`strict_equality`).
  - Silenced legacy modules (`ignore_errors = True`): `backend.mapper.*`, `backend.dom.web_distiller_freq`, `backend.dom.shadow_html_parser`, `backend.dom.content_tagger`, and all `backend.tests.*`.
- `show_error_codes = True` + `warn_unused_ignores = True` so `# type: ignore[code]` suppressions are surgical, not blanket.
- **Convention for adopting types:** when a module imports from `backend.services.ids`, add a matching `[mypy-backend.services.<module>]` block mirroring the `concept_lifecycle` pattern. End state is global `strict = True`.
- `.clj-kondo` / `.lsp` dirs are editor artifacts, not active to this Python codebase.

## Import Organization

Observed order (e.g. `backend/api/routes.py`, `backend/services/concept_lifecycle.py`):
1. `from __future__ import annotations`
2. Stdlib (`import json`, `import logging`, `import threading`, `import time`, `import os`)
3. Third-party (`from fastapi import ...`, `from pydantic import BaseModel`)
4. First-party `backend.*` absolute imports (e.g. `from backend.services.ids import ConceptId, EdgeId, WorkspaceId`)

**Path aliases:**
- No `__init__.py` at the repo root; modules are addressed as `backend.<sub>.<mod>` via the absolute repo path on `sys.path` (`mypy.ini` sets `explicit_package_bases` + `namespace_packages`). Scripts/probes bootstrap this manually:
  ```python
  ROOT = Path(__file__).resolve().parents[1]
  if str(ROOT) not in sys.path:
      sys.path.insert(0, str(ROOT))
  ```

## Error Handling

**Structured HTTP errors (§14.2):** `backend/api/errors.py` defines `WorkflowError(code, message, http_status, retryable, retry_after_ms, context)` registered via `register_workflow_error_handler(app)`, emitting a canonical envelope:
```json
{"error": {"code": ..., "message": ..., "retryable": ..., "retry_after_ms": ..., "context": ...}}
```

**Loud-failure contract (§8D.46 — non-negotiable):** production subsystem failures surface as **503 + halted cascade**, NEVER a silent stub substitution. Real-backend → stub fallback is forbidden in production. See `backend/services/slm_client.py` (sets `self._fake` only when `WFH_FAKE_SLM` is set; otherwise a failed model load is loud).

**Secondary-subsystem hiccups are swallowed-and-logged:** the lifecycle chain helpers in `backend/services/concept_lifecycle.py` each swallow internal errors and emit a tagged warning so a downstream broadcast/index/projection failure never blocks the **primary** mutation. This is the deliberate exception to "fail loud" — it applies only to non-primary side effects.

**Idempotency keys on every mutation route:** clients supply `idempotency_key` (UUID) on PATCH/POST; `backend/api/routes.py` caches via `_idempotency_lookup` / `_idempotency_store` (TTL `settings.idempotency_ttl_sec`, lock-guarded `_idempotency_cache`). Retries within the window replay the cached response — mutations are retry-safe by construction.

## Logging

**Framework:** stdlib `logging`. Each module declares `logger = logging.getLogger(__name__)` at top (see `backend/api/routes.py`, `backend/services/concept_lifecycle.py`).

**Durable log mirror:** `app.py` installs a `_Tee` file-like proxy over stdout/stderr so EVERYTHING (prints, logging, uvicorn access, mapper profiler) lands in `logs.txt` next to the script while still showing on the live console.

**Operator dashboard, not log-spam:** new observable state must extend an existing row of the `watch-activity` seven-row dashboard (scan / retrieval / visible 3D / hidden 3D / pinned / compile / subsystems) in `scripts/sim_frontend.py`, updating **in place** via ANSI cursor codes — it must NOT spawn a parallel append-only log stream (CLAUDE.md "What Always Holds" #4). ANSI is gated off on Windows (`os.name != "nt"`).

## Comments

**When to Comment:** modules carry substantial module docstrings that (a) state the purpose, (b) cite the governing spec section (`§8D.44`, `§14.2`, `§R.9`), and (c) explain *why* (rationale, the bug a fix prevents). This citation-to-spec convention is load-bearing — the `docs/` chain is the source of truth and code references back into it.

**Inline comments** explain non-obvious decisions and historical bug context (e.g. the `_LiveConnProxy` docstring in `conftest.py` explains the test-isolation closed-connection failure it fixes). Avoid restating *what* the code does; state *why*.

## Function & Module Design

**Functional-core / imperative-shell split:** decision logic is pulled into pure functions so each branch is unit-testable with no I/O stubs. Canonical example: `ConceptDiff` (frozen dataclass) in `backend/services/concept_lifecycle.py` classifies a mutation once via `ConceptDiff.from_pre_post(...)`; the side-effect chain (broadcast → index → projection → log → cascade) reads from the diff rather than re-deriving heuristics inline.

**Dataclasses for records:** `@dataclass` / `@dataclass(frozen=True)` for value objects (`ConceptDiff`, `EditDiff`, the one `ConceptNode` record §8D.44). Frozen for immutable classifications.

**One dispatcher, one code path (architectural non-negotiable):** every concept mutation routes through `backend/services/concept_lifecycle.py::apply_update_lifecycle` / `apply_delete_lifecycle` so REST handlers (`routes.py`) and the agent's `ActionResolver` (`agent_runtime`) stay on a single path. Do NOT add a parallel mutation route.

**Append-only evolution log:** `backend/services/evolution_log.py` records every edit as a provenance-tagged `EditDiff` (JSONL persisted). Rollback (`rollback_single`, `rollback_range`, `rollback_actor_since`) is itself recorded as a new edit — the log only ever grows.

**Singletons via classmethod gate:** services like `SLMClient` (`backend/services/slm_client.py`) use a `cls._instance` lazy singleton that reads env gates once at construction.

**Singular extension over special-casing:** new capability is one more peer fixture / one more compiled-from-scans node / one more Python-API materialised tree — never a special-cased card type with its own table (CLAUDE.md "What Always Holds" #5).

---

*Convention analysis: 2026-06-14*
