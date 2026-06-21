# Phase 4 — Live Layout, Signal & Pattern — CONTEXT

> Context for planning/execution. Captured from the roadmap SCs + the as-built
> code. The BACKEND of Phase 4 is built + scenario-green; the gap is a **frontend
> render gap** in the 3D projector (UMAP-01) — finish-and-verify, mostly verify
> for SIG-01/PAT-01 and a focused build for the projector's 6D-HSV consumption.

## Goal

During a live scan the workspace renders a 6D-UMAP manifold with camera-coupled
HSV, advances iterables one signal at a time with the cascade re-firing per
sample, and materialises a live `pattern_map` node — finishing the §R/§11.5
live-render gaps.

## In scope (requirements)

- **UMAP-01** — LayoutService emits a 6-vector `umap_canonical` WS frame on
  scan-end joint fit; **HSV rotates with camera azimuth across Projector, Halo
  phantoms, and type-only readout nodes**; the frontend renders only (no client
  UMAP runtime).
- **SIG-01** — panels render ONLY one iterable signal at a time, advanced via
  play/pause/step; `signal_stream` mirror holds the index; `/api/ui/signal_advance`
  routes through `RolloutCoordinator` and recompiles the `{ref}`-consumers per
  sample, across pattern_map / url_set / Database.concept iterables.
- **PAT-01** — a live `pattern_map` ConceptNode materialises during a WebBrowser
  scan and updates in place under signal-stream; the golden-trio joint-presence
  gate holds; a second scan accretes into the same peer node; PageRank traverses
  the same Kuzu ConceptEdge graph.

## As-built starting point

- **Backend (built + scenario-green, this session against the stub):**
  - UMAP-01 — `6d-umap-format` (LayoutService coords are 6-vectors; HSV channels
    3..5 content-derived in [0,1]) + `perimeter-rescale` GREEN. `LayoutService.
    _embed_6d` (real UMAP, loud TruncatedSVD degrade) + `build_umap_canonical`
    (6-vector frame) exist; `/api/recompute_umap` returns **3-vectors** (position
    only) — the HSV is on the WS frame.
  - SIG-01 — `iterated-signal-rerender`, `signal-stream-roundtrip`,
    `database-concept-signal-stream`, `urls-panel-iteration` GREEN. The
    `RolloutCoordinator` + `signal_stream` UIState mirror + `/api/ui/signal_advance`
    are built.
  - PAT-01 — `pattern-map-live-update` GREEN + `scripts/probe_pattern_map.py`
    PASS (golden-trio gate + accretive merge + PageRank over the Kuzu edge graph).
- **Frontend projector:** `backend/static/js/fe/projector.mjs` —
  `buildPointArrays(coords)` reads ONLY `p[0..2]` (xyz) and fabricates an **even
  HSV sweep** (`toRgb(i/n, 0.7, 0.6)`), explicitly commented "a stand-in for the
  6D-UMAP HSV until the layout frame carries per-chunk hsv." The colors are NOT
  camera-azimuth-coupled. `editor.html::bootProjector` boots from
  `/api/recompute_umap` (3D) and does NOT consume the `umap_canonical` WS frame.

## The gap (what this phase actually lands)

1. **Projector renders the backend's 6D HSV (UMAP-01):** `buildPointArrays`
   consumes `p[3..5]` (h,s,v in [0,1]) as the node colour when the coord is a
   6-vector (sweep fallback for 3-vectors → backward compatible); the editor
   consumes the `umap_canonical` WS frame and feeds its 6D coords to the projector.
2. **HSV rotates with camera azimuth (UMAP-01):** `createProjector` recolours on
   camera-azimuth change (hue offset by azimuth), so orbiting the scene rotates
   the colour field — the same azimuth the halo rays already couple to.
3. **Verify SIG-01 / PAT-01:** the scenarios are green; confirm + keep them green
   in `full-smoke`. (No new backend build — these are verification.)

## Verification gate (the framework — `.planning/TEST_MATRIX.md`)

- **Unit:** `projector.test.mjs` — un-skip/add: a 6-vector coord uses the frame's
  HSV (not the sweep); an azimuth offset rotates the hue; 3-vectors still sweep.
- **REPL:** `6d-umap-format`, `perimeter-rescale`, `iterated-signal-rerender`,
  `signal-stream-roundtrip`, `database-concept-signal-stream`, `urls-panel-iteration`,
  `pattern-map-live-update` green both modes; `probe_pattern_map.py` PASS.
- **e2e:** a projector spec asserts the live `/` projector colours nodes from a
  (injected) 6D `umap_canonical` frame and recolours on camera azimuth — the
  render-level UMAP-01 acceptance the REPL can't reach.
- **Gate:** `npm run test:all` green both modes; `full-smoke` stays green.

## Out of scope

- The backend layout/rollout/pattern services (built + scenario-green).
- Client-side UMAP runtime (FORBIDDEN — backend computes, frontend renders).
- Phase 5 synthesis (separate phase).

## Forbidden (D11)

- Client-side UMAP/embedding runtime — the frontend renders the backend's frame.
- Concentric/Fibonacci 3D layout — the projector renders the UMAP-linear-radial
  positions the backend computes.
