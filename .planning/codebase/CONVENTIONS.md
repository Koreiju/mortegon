# Coding Conventions

**Analysis Date:** 2026-06-20

This is a Python 3.13 FastAPI backend (`backend/`) paired with a vanilla-ESM frontend (`backend/static/js/fe/*.mjs`, served directly — no bundler for the hand-written tree) plus a bundled Milkdown editable-slate layer (`frontend_src/` → esbuild → `backend/static/js/fe/vendor/`). No linter/formatter config is checked in (no `.eslintrc`, `.prettierrc`, or `pyproject.toml` black/ruff section); a root `mypy.ini` provides light Python typing discipline. Code quality is enforced primarily through the verification surface (see TESTING.md), not static tooling.

## Naming Patterns

**Files:**
- Backend: `snake_case.py` grouped by surface — `backend/api/routes.py`, `backend/services/*.py`, `backend/dom/*.py`, `backend/mapper/*.py`, `backend/ontology/*.py`, `backend/agent/*.py`.
- Frontend (served ESM, hand-written): `snake_case.mjs` under `backend/static/js/fe/` — `magic_markdown.mjs` (model), `magic_markdown_panel.mjs` (DOM glue), `magic_markdown_halo.mjs`, `magic_markdown_gestures.mjs`, `projector.mjs`, `store.mjs`, `gateway.mjs`.
- Frontend (Milkdown build source): `frontend_src/milkdown_slate.mjs`, bundled via `npm run build:milkdown` into `backend/static/js/fe/vendor/milkdown_slate.bundle.mjs`.
- Tests co-located by suffix: `*.test.mjs` sits next to the module it tests (`magic_markdown.mjs` → `magic_markdown.test.mjs`, `magic_markdown_panel.mjs` → `magic_markdown_panel.test.mjs`); Python tests centralize in `backend/tests/test_*.py`.
- Scripts in `scripts/`: `probe_live_*.py` for real-subsystem lodestar evidence (§8D.45/47/48/49), narrower `probe_*.py` contract probes, legacy `test_*.py` offline checks predating `backend/tests/`.

**Functions (Python):** `snake_case`, verb-first — `apply_update_lifecycle`, `apply_delete_lifecycle`, `temp_db_dir`, `sweep_stale_tmp`. Private helpers prefixed `_` — `_resolve_model_name`, `_ensure_model`, `_get`, `_default`.

**Functions (JS):** `camelCase` — `panelVDom`, `renderPanel`, `advanceSignal`, `isIterable`. Pure-model functions take and return plain data/specs (no DOM); the DOM-binding entry point is conventionally named `mount`.

**Variables:** Python `snake_case`; module constants `UPPER_SNAKE` (`TEST_TMP_PREFIX`, `_PRODUCTION_MODEL`, `STUB_GATES`, `LEGACY_TMP_PREFIXES`). JS `camelCase`; exported glyph/token constants `UPPER_SNAKE` (`GLYPH_COLLAPSED`, `GLYPH_EXPANDED`, `GLYPH_NONE`).

**Types:** Python `@dataclass` classes in `PascalCase` (`ConceptNode`, `ConceptEdge`); error classes subclass a builtin and end in `Error` (`SLMUnavailableError(RuntimeError)` in `backend/services/slm_client.py:41`). No TypeScript — the frontend is plain ESM; shapes are documented in prose JSDoc-style block comments, e.g. the `{ tag, attrs, children?, text? }` element-spec convention in `backend/static/js/fe/magic_markdown_panel.mjs:28`.

## Docstring Discipline (the load-bearing convention)

Every non-trivial module/function opens with a docstring that:
1. **Cites the design-doc anchor it realises** — a `§` reference into `docs/USER_REQUIREMENTS_VERBATIM.md` or another canonical doc (`§8D.46`, `§R.9`, `§T/§U/§V`).
2. **States the contract**, not just the behavior — see the `backend/services/db_janitor.py` module docstring (quotes the verbatim user requirement before describing the implementation) and `SLMUnavailableError`'s docstring in `backend/services/slm_client.py:41-49`.
3. For frontend modules, states the model/DOM split explicitly — see `backend/static/js/fe/magic_markdown.mjs:1-22` and `backend/static/js/fe/magic_markdown_panel.mjs:1-20`.

**When writing new code, open with a docstring naming the requirement anchor before the implementation.** This is the project's primary documentation mechanism — there is no separate API-doc generator, and `docs/code_specs/` is the line-level spec layer code is checked against.

## Import Organization

**Python:**
- `from __future__ import annotations` is the first import in modules that use forward-ref type hints (`backend/services/slm_client.py`, `scripts/run_full_stack_tests.py`, `backend/services/db_janitor.py`).
- Order: stdlib, then third-party (`kuzu`, `fastapi`, `gpt4all`), then local `backend.*` — see `backend/tests/conftest.py` and `scripts/run_full_stack_tests.py`.
- Direct sibling imports, no barrel/`__init__.py` re-export layer: `from backend import database`, `from backend.services.db_janitor import temp_db_dir, sweep_stale_tmp`.

**JS (ESM):**
- Explicit relative `.mjs` imports, no bundler/path aliases for the hand-written `fe/` tree: `import { renderPanel, renderGraph, GLYPH_EXPANDED } from "./magic_markdown.mjs";` (`backend/static/js/fe/magic_markdown_panel.mjs:22`).
- The Milkdown layer is the one deliberate bundled exception, kept separate (`frontend_src/` → esbuild → `vendor/`) from the vanilla hand-written tree it gets imported alongside.

## Error Handling — Loud Failure, Never Silent Stub Fallback (§8D.46)

**Core principle:** production paths run real subsystems; a failed real backend is a loud 503, never a quiet stub substitution.

- Each real subsystem (SLM, embedder, Selenium, LangGraph) has exactly **one** fake/skip gate, env-var controlled, checked once near construction — not scattered through call sites:
  - `WFH_FAKE_SLM=1` → `backend/services/slm_client.py` (`SLMClient.__new__`, `_fake` flag, line ~110).
  - `WFH_FAKE_EMBEDDER=1` → `backend/services/embedding_service.py:137`.
  - `NO_WEBDRIVER=1` → skips Selenium driver init at backend boot.
  - LangGraph has **no** fake gate — a missing dependency is a hard import error by design.
- When the gate is unset and the real backend fails, raise a typed exception rather than degrade. Example contract (`backend/services/slm_client.py:41-49`):
  > "§8D.46 forbids a silent real→stub fallback in production: a failed load (or a failed generation) must be LOUD. The FastAPI layer maps this to HTTP 503 and the cascade halts, rather than quietly emitting `[stub-slm]` text."
- `backend/services/embedding_service.py:272` documents the same contract: "we raise `ValueError` so FastAPI can return a clean 503."
- `GET /api/subsystem_status` is the single source of truth for `{slm, embedder, selenium, langgraph, all_real}`. New subsystems extend this report rather than introducing a parallel health surface.
- Model-override guards are loud, not silent: `_resolve_model_name()` (`backend/services/slm_client.py:65-79`) rejects any `WFH_SLM_MODEL` override containing `"llama"`, logs `logger.error`, and falls back to the production model rather than silently honoring a forbidden override.

**Pattern to follow when adding a new integration:**
```python
class XUnavailableError(RuntimeError):
    """Raised when the real X backend fails and the harness stub gate is unset."""

def _ensure_x(self):
    if self._fake:           # only the harness gate suppresses the raise
        return None
    try:
        ...load real X...
    except Exception as exc:
        raise XUnavailableError(
            f"... is required. Set WFH_FAKE_X=1 only in the harness."
        ) from exc
```
Route handlers catch the typed `*UnavailableError`/`ValueError` and translate to `HTTPException(status_code=503, ...)`.

**Anti-pattern (forbidden):** catching a real-backend failure and quietly returning stub output without the env gate being set. `backend/services/conceptual_compute.py:452,469` comments explicitly mark the one sanctioned "swallow to stub" branch as gated by `WFH_FAKE_SLM` — do not add new unconditional swallow-to-stub branches elsewhere.

## Logging

**Framework:** stdlib `logging`, `logger = logging.getLogger(__name__)` per module (`backend/services/slm_client.py:38`).

**Patterns:**
- `logger.info` for expected harness-mode notices (`"SLMClient: WFH_FAKE_SLM set; using stub responses."`).
- `logger.error` for rejected/guarded configuration (the forbidden Llama-override rejection).
- The REPL harness (`scripts/sim_frontend.py`) and `scripts/run_full_stack_tests.py` use `print(..., flush=True)` with banner formatting (`"=" * 72`) for human-readable tier/summary output rather than `logging` — intentional, since this is operator-facing CLI output, not application logging.

## Comments

- Comment density is high and intentional: comments anchor code to the requirements doc (`§` references) and explain *why*, not *what*. `backend/services/db_janitor.py`'s module docstring quotes the verbatim user requirement before describing the implementation.
- Inline comments flag non-obvious invariants, e.g. `backend/services/conceptual_compute.py:452` marking exactly which swallow-to-stub branch is sanctioned and why.

**JSDoc-style (frontend):** Block comments (`/** ... */`) above exported functions describe params/return shape in prose rather than formal `@param`/`@returns` tags — `backend/static/js/fe/magic_markdown.mjs:36-47` (`iterableNode`, `isIterable`).

## Function Design

**Size:** Frontend model-layer functions (`magic_markdown.mjs`) are short and single-purpose. Backend service functions can be longer when implementing a documented multi-step algorithm (e.g. `_ensure_model`'s load → device-fallback → raise sequence in `backend/services/slm_client.py`).

**Parameters:** JS favors an options object over long positional lists — `panelVDom(rootNode, opts = {})`. Python favors dataclasses or explicit env-resolution functions over many positional args.

**Return Values:** Functions with two legitimate failure modes (harness-stub vs real-unavailable) return `None` for the harness path and **raise** for the real-unavailable path — never collapsed into one sentinel. See `_ensure_model`'s documented contract (`backend/services/slm_client.py:121-132`).

## Module Design — Pure-Model vs DOM-Glue Split (the standout frontend convention)

Every interactive frontend surface is split into two files:
- A **pure logic/model module**, zero DOM dependency, unit-testable in plain Node — `backend/static/js/fe/magic_markdown.mjs` (parse/render/transform), `backend/static/js/fe/projector.mjs` (model side of the 3D/2D projector).
- A **thin DOM-glue module** that turns the model's plain-object "vdom" spec into real DOM nodes and wires events — `backend/static/js/fe/magic_markdown_panel.mjs`: `panelVDom` is pure, `mount` is the only DOM-touching function.

When adding a new interactive frontend feature: write the transform/decision logic as pure functions over plain objects, add a matching `*.test.mjs`, and keep DOM-touching code in a separate `_panel`/`_halo`-style sibling module that imports the model. This is the pattern to extend, not deviate from.

**Exports (JS):** Named exports only; no default exports observed (`export function node(...)`, `export const GLYPH_COLLAPSED = ...`). No barrel/index re-export files anywhere in `backend/static/js/fe/`.

**Barrel Files:** Not used in Python or JS. Modules import each other directly by relative/dotted path.

## Commit Convention

Conventional-commit prefixes are used consistently: `feat(...)`, `fix(...)`, `docs(gsd): ...`, `chore(...)` — see recent history (`feat(projector): Phase 4 UMAP-01 ...`, `docs(gsd): Phase 5 plan + REG-01 done ...`). Use a `scope` matching the touched subsystem (`projector`, `phase3`, `gsd`, etc.).

---

*Convention analysis: 2026-06-20*
