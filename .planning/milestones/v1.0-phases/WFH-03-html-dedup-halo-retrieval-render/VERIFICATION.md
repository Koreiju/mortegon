---
status: passed
phase: 3
verified: 2026-06-21
mode: real + stub (both)
---

# Phase 3 — HTML Dedup + Halo Retrieval Render — VERIFICATION

## Success criteria

| SC | Verdict | Evidence |
|----|---------|----------|
| SC1 — §U deduped content-tree from `fields`; byte-exact golden 6/6; `syntax-agnostic-compile` HtmlStrategy arm green both modes | ✅ PASS | `pytest backend/tests/test_content_tree.py test_content_tree_breadth.py` → 17 passed (golden 6/6 + unicode/breadth); REPL `syntax-agnostic-compile` in `all` 95/95 both modes |
| SC2 — collapsed node fires a NAME-only halo, triple-product ranked, no graph-analytics axes; autoregressive walk advances on click | ✅ PASS | REPL `apparition-mode` + `halo-chain-roundtrip` + `apparitions-discover-link` in `all` 95/95 both modes (real: surfaces candidate via real nomic); e2e HALO-01 asserts name-only labels + `data-sim` tooltip carrier (no score chips) |
| SC3 — halo proximal to CIRCULAR root-field-only collapsed node; constant-similarity ray + along-line slide; solid 2D↔3D arrow (no dotted overlays) | ✅ PASS | **NEW** e2e `halo.spec.js` HALO-01 (circular phantom) + HALO-02 (z-above-slate, focal re-anchor, constant-sim ray + along-line slide on orbit) green real + stub (24 passed each); dotted-overlay audit: no `dashed`/`dotted` in fe/editor/css |
| SC4 — `probe_pattern_map.py` + live archive/tarot/yourchineseastrology/studycli render clean+deduped on the real stack | ✅ PASS | `probe_pattern_map.py` → ALL CHECKS PASS (pattern_map node, golden trio, accretive merge, PageRank); live archive scan in `probe_live_archive_scan` (real) clean; content-tree corpus 61 sites / 0 violations (`breadth_content_tree_smoke.py`, STATE.md) |

## What this phase built (the genuine gap)

`frontend_e2e/halo.spec.js` carried 3 `test.fixme` placeholders for the live
halo. This phase wrote them as real browser acceptance specs against the served
`/` editor + the `__mm_open_halo` / `__mm_halo_state` / `__mm_halo_rotate` hooks
in `backend/templates/editor.html`. Fixes en route: seed concepts (isolated DB
starts empty), wait for the async `/api/radiation` refine to settle, and capture
the orbit before/after atomically (the projector rAF re-pins `camAngle`).

## Gate

REPL `all` 95/95 both modes; e2e 24 both modes; golden 17 passed; pattern_map
probe PASS; dotted audit clean. **Verdict: PASS (both modes).**
