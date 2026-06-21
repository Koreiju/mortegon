---
phase: 03-html-dedup-halo-retrieval-render
plan: direct
subsystem: frontend
tags: [content-tree, halo, apparition, triple-product]
provides:
  - §U deduplicated content-tree render (golden 6/6 + corpus-hardened)
  - live name-only apparition halo (triple-product ranked, circular collapsed node)
  - 3 live halo browser acceptance specs (HALO-01/02)
affects: [phase-4-layout, phase-5-synthesis]
tech-stack:
  added: []
  patterns: [name-only-phantoms, constant-similarity-ray, no-graph-analytics-axes]
key-files:
  created: []
  modified: [frontend_e2e/halo.spec.js]
key-decisions: [triple-product-only-ranking, dotted-overlays-removed]
requirements-completed: [HTML-01, HALO-01, HALO-02]
duration: ~1h
completed: 2026-06-21
---

# Phase 3: HTML Dedup + Halo Retrieval Render Summary

**A scanned HTML chunk renders as a clean deduped content-tree, and clicking a collapsed circular node fires a name-only triple-product halo.**

## Accomplishments
- HTML-01: §U deduped content-tree from `fields`; byte-exact golden 6/6 + breadth (17 pytest passed); `syntax-agnostic-compile` HtmlStrategy arm green.
- HALO-01: name-only phantoms (scores in `data-sim` tooltip), triple-product ranked, autoregressive walk advances; REPL `apparition-mode`/`apparitions-discover-link` green real.
- HALO-02: circular root-field-only collapsed node, z-above-slate, focal re-anchor on scroll, constant-similarity ray + along-line slide on camera orbit; solid 2D↔3D arrow (dotted audit clean).

## The genuine new code
Wrote the 3 `test.fixme` halo specs in `frontend_e2e/halo.spec.js` as real browser acceptance against the built `__mm_halo_*` hooks (seed concepts; wait for the async radiation refine to settle; capture orbit before/after atomically since the projector rAF re-pins `camAngle`).

## Verification
e2e 24/24 both modes (incl. 3 halo); golden 17 pytest; `probe_pattern_map` PASS; dotted audit clean. See VERIFICATION.md.

## Next Phase Readiness
Halo + content-tree render done — Phase 4 layers live layout/signal/pattern on top.
