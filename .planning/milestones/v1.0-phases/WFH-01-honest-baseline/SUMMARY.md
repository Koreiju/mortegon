---
phase: 01-honest-baseline
plan: direct
subsystem: reliability
tags: [no-mocks, fixtures, hygiene, dependencies]
provides:
  - SLM 503-on-real-failure (no silent stub fallback)
  - exactly three foundation fixtures (no Editor)
  - forbidden/legacy code hard-deleted
  - pinned deps + documented launch/port
affects: [all-phases]
tech-stack:
  added: [kuzu==0.11.3, langgraph, selenium, webdriver-manager]
  patterns: [loud-failure-503, three-fixture-flat-ontology]
key-files:
  created: []
  modified: [backend/services/slm_client.py, backend/api/routes.py, requirements.txt, CLAUDE.md]
key-decisions: [D9-no-mocks, D7-three-fixtures, D3/D11-forbidden-code]
requirements-completed: [REL-01, REL-02, FIX-01, FIX-02, HYG-01, HYG-02]
duration: prior
completed: 2026-06-21
---

# Phase 1: Honest Baseline Summary

**The brownfield baseline tells the truth — no quiet stub substitution, exactly three fixtures, no forbidden/legacy code, unambiguous launch.**

## Accomplishments
- REL-01/02: `_ensure_model` raises `SLMUnavailableError` on real-load failure; CPU real→real preserved; `probe_no_mocks` PASS.
- FIX-01/02: exactly three fixtures (agent/web_browser/database); no `fixture::editor`; mutation gestures route through the lifecycle.
- HYG-01: `_legacy_frontend/`, `backend_slow/`, `cluster_distillation.py`, graph-analytics retrieval + hyperbolic layout removed; no Llama.
- HYG-02: deps pinned, `@mdxeditor/editor` removed, launch/port documented.

## Verification
`probe_no_mocks` PASS (real); REPL `all` 95/95 both modes; pytest green. See VERIFICATION.md.

## Next Phase Readiness
Baseline truthful — Phases 2–5 build on it.
