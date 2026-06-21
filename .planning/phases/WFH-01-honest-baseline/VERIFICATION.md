---
status: passed
phase: 1
verified: 2026-06-21
mode: real + stub (both)
---

# Phase 1 — Honest Baseline — VERIFICATION

Backfilled to the GSD artifact idiom. Phase 1 was completed + stub-verified
2026-06-15; re-confirmed on the REAL stack 2026-06-21 (`all_real: true`).

## Success criteria / requirements

| Req | Verdict | Evidence |
|----|---------|----------|
| REL-01 — SLM real-load failure raises 503 (no silent `_fake=True`/`[stub-slm]`) | ✅ PASS | `slm_client.py::_ensure_model` raises `SLMUnavailableError`; compute/route/agent stub paths closed; `probe_no_mocks.py` PASS (real SLM output, not `[stub-slm]`) |
| REL-02 — CPU real→real device override preserved; only terminal `_fake` removed | ✅ PASS | `probe_no_mocks.py` PASS real-mode; `subsystem_status.slm.fake_env=false`, device cuda |
| FIX-01 — exactly THREE `python_object` fixtures (agent/web_browser/database); no `fixture::editor` | ✅ PASS | REPL `three-fixtures-present` / `fixtures-undeletable` green in `all` 95/95 both modes |
| FIX-02 — stale `fixture::editor` force-deleted; mutation gestures route through `/concepts`+`/concept_edges` | ✅ PASS | REPL `editor-primitives-roundtrip` (mutation-gesture) green; no Editor fixture present |
| HYG-01 — forbidden/legacy code hard-deleted (`_legacy_frontend/`, `backend_slow/`, `cluster_distillation.py`, graph-analytics retrieval, hyperbolic layout); no Llama | ✅ PASS | trees removed (STATE.md FIX-01); `backend/analytics/` holds only utilities (pq_tree/loop_closure/segment_embedder); no-Llama guard intact |
| HYG-02 — deps pinned (kuzu 0.11.3, langgraph/selenium/webdriver-manager); launch+port documented; `@mdxeditor/editor` removed | ✅ PASS | `requirements.txt` pinned; CLAUDE.md launch/port doc; lockfile pruned (STATE.md HYG-02) |

## Gate

`probe_no_mocks` PASS (real); REPL `all` 95/95 both modes; pytest green.
**Verdict: PASS (both modes).**
