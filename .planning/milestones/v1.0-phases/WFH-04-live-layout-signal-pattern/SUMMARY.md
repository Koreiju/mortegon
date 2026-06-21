---
phase: 04-live-layout-signal-pattern
plan: direct
subsystem: layout
tags: [umap-6d, hsv, rollout, signal-stream, pattern-map]
provides:
  - 6D umap_canonical WS frame + camera-coupled HSV (frontend renders only)
  - one-signal-at-a-time rollout with per-sample cascade re-fire
  - live pattern_map ConceptNode (golden-trio gate, accretive, PageRank)
affects: [phase-5-synthesis]
tech-stack:
  added: []
  patterns: [backend-computes-frontend-renders, rollout-coordinator]
key-files:
  created: []
  modified: []
key-decisions: [D2-umap-radial-layout, D10-no-client-umap]
requirements-completed: [UMAP-01, SIG-01, PAT-01]
duration: prior
completed: 2026-06-21
---

# Phase 4: Live Layout, Signal & Pattern Summary

**During a live scan the workspace renders a 6D-UMAP manifold with camera-coupled HSV, advances iterables one signal at a time, and materialises a live pattern_map node.**

## Accomplishments
- UMAP-01: 6-vector `umap_canonical` WS frame on scan-end joint fit; HSV rotates with camera azimuth; real 6D UMAP fit confirmed live (`probe_live_scan_with_cleanup`, coords=117).
- SIG-01: one iterable signal at a time; `signal_advance` routes through `RolloutCoordinator`, recompiles `{ref}`-consumers per sample.
- PAT-01: live `pattern_map` ConceptNode; golden-trio gate; second scan accretes into the same peer; PageRank on the Kuzu ConceptEdge graph.

## Verification
REPL `6d-umap-format`/`perimeter-rescale`/`iterated-signal-rerender`/`signal-stream`/`urls-panel-iteration`/`pattern-map-live-update` green in `all` 95/95 both modes; `probe_pattern_map` PASS. See VERIFICATION.md.

## Next Phase Readiness
Live render done — Phase 5 binds the registers + proves the lodestars.
