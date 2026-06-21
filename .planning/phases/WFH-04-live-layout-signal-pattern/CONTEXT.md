# Phase 4 — Live Layout, Signal & Pattern — CONTEXT

> Brownfield **finish-and-verify**. The 6D-UMAP layout service, the
> `RolloutCoordinator` one-signal-at-a-time iteration, and the live `pattern_map`
> ConceptNode materialiser are already built. This phase verifies the live-render
> path against the project's REPL/probe idiom on the real stack.

## Goal

During a live scan the workspace renders a 6D-UMAP manifold with camera-coupled
HSV, advances iterables one signal at a time with the cascade re-firing per sample,
and materialises a live `pattern_map` node — finishing the §R/§11.5 live-render gaps.

## In scope (requirements §R/§11.5)

- **SC1 (6D-UMAP + HSV)** — LayoutService emits a 6-vector `umap_canonical` WS frame
  on scan-end joint fit; HSV rotates with camera azimuth across Projector, halo
  phantoms, and type-only readout nodes (frontend renders only). `env-scenario
  --name 6d-umap-format` / `perimeter-rescale` green both modes.
- **SC2 (one-signal rollout)** — a panel renders only ONE iterable signal at a time;
  play/pause/step via `/api/ui/signal_advance` routes through `RolloutCoordinator`
  and recompiles the `{ref}`-consumers per sample across pattern_map / url_set /
  Database.concept iterables. `env-scenario --name iterated-signal-rerender` /
  `signal-stream` / `urls-panel-iteration` green.
- **SC3 (live pattern_map)** — a live `pattern_map` ConceptNode materialises during
  a WebBrowser scan and updates in place under signal-stream; golden-trio
  joint-presence gate holds; a second scan accretes into the same peer node;
  PageRank traverses the same Kuzu ConceptEdge graph. `env-scenario --name
  pattern-map-live-update` green + `scripts/probe_pattern_map.py` passing.
- **SC4 (gate)** — `env-scenario --name full-smoke` green both modes with all
  live-render scenarios included.

## As-built starting point (do NOT rebuild)

- `backend/services/layout_service.py` (real UMAP 6D joint fit; `umap_canonical`
  WS frame) + `backend/static/js/fe/projector.mjs` (HSV sweep, camera azimuth).
- `RolloutCoordinator` (signal_advance, per-sample cascade re-fire) — REPL-covered
  by `iterated-signal-rerender` / `signal-stream` / `urls-panel-iteration`.
- The `pattern_map` materialiser — `scripts/probe_pattern_map.py` drives the real
  DOM pipeline (golden-trio gate, second-scan accretion, PageRank on the Kuzu graph).

## Verification gate

- **REPL:** `6d-umap-format`, `perimeter-rescale`, `iterated-signal-rerender`,
  `signal-stream`, `urls-panel-iteration`, `pattern-map-live-update` green in
  `env-scenario --name all` (both modes).
- **probe:** `scripts/probe_pattern_map.py`.
- **gate:** `full-smoke` / `all` green both modes.

## Out of scope

- The Phase 3 halo/content-tree render; the Phase 5 register synthesis (separate).
- Mid-scan incremental UMAP refit (PERF-01, deferred to a later milestone).
