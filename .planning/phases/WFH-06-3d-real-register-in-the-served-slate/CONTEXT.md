# Phase 6 — 3D Real Register in the Served Slate — CONTEXT

> Primed from `.planning/DESIGN_COVERAGE_AUDIT.md` (not a from-scratch discuss).
> This phase **ports** the legacy `cp/` 3D Real register into the served `fe/`
> black-slate idiom — backend layout is mature; the gap is the served-frontend render.

## Goal

The served `/` frontend renders the full 3D Real register: UMAP-linear-radial
**force-directed** layout converging along root-URL rays, per-URL multi-scan
placement with camera framing, image billboards with single-fetch persistence,
and solid (headless) 2D↔3D link arrows.

## In scope (requirements)

- **REAL-01** (§B.2/§B.3) — `fe/projector.mjs` lays chunks by UMAP then converges
  force-directed along root-URL rays (chunk moves only along `r(t)` from its root);
  hard collider repulsion (zero force above `2·R·safety`, exact-correction below);
  NO concentric/Fibonacci final position.
- **REAL-02** (§B.4/§B.7/§B.8/§B.9) — per-URL `root_position`+`bounding_radius`; new
  URL lands non-overlapping at `existing_max + new_radius + safety_gap`; old URLs
  never move on a new scan; camera frames/bounds + tweens to newest root on scan-end
  (suppressed if user interacted AND root already in frustum); adaptive resize.
- **REAL-03** (§H) — image billboards in the served projector: in-mem → IndexedDB →
  proxy → direct fetch order; shared `THREE.Texture` per URL; transparent-PNG
  fallback never cached as success; collider spacing shared with text billboards.
- **REAL-04** (§I / §O.16) — every pinned panel carries `data-3d-node-id`; the
  animate loop projects the node and draws a SOLID HEADLESS line tracking the moving
  node; off-frustum hides; no dotted lines anywhere.

## As-built starting point (the reference to port FROM)

- **Backend (mature, keep):** `backend/services/layout_service.py` — 6D UMAP joint
  fit + `umap_canonical` WS frame; per-URL placement math; `recompute_umap`.
- **Legacy `cp/` (the render reference, demoted to `/legacy`):** `force_layout.js`
  (force-directed ray convergence), `sprite_manager.js` (image billboards + texture
  cache), `animation.js`/`billboard.js` (2D↔3D arrows + camera), `layout.js`.
- **Served `fe/` (the target, currently minimal):** `backend/static/js/fe/projector.mjs`
  (THREE points only, HSV, `setNodes`/`onFrame`/`azimuth`/`project`) + `editor.html`
  (boots projector, `recompute_umap`, camera-azimuth→halo coupling). `magic_markdown.mjs`
  has partial link-arrow scaffolding.

## The gap this phase closes

`fe/projector.mjs` renders chunks as flat HSV points: no force-directed ray
convergence, no per-URL multi-scan placement, no image billboards, no camera
framing/bounds, no solid 2D↔3D arrows. Port each into the `fe/` idiom (backend
computes; frontend renders — D10). Do NOT resurrect the legacy `cp/` surface; bring
its *features* into `fe/`.

## Verification gate (full real-stack inline — user choice)

- **e2e (render):** extend `frontend_e2e/projector.spec.js` — force-directed rays +
  min pairwise spacing (REAL-01); multi-scan non-overlap + camera frame (REAL-02);
  image-node paints + persists across re-render (REAL-03); solid arrow tracks node,
  no dotted (REAL-04, with `black_slate.spec` no-dotted staying green).
- **REPL:** `6d-umap-format` / `perimeter-rescale` green both modes; multi-scan
  placement telemetry.
- **probe / real-stack:** real archive.org multi-scan → live render; the consolidated
  real-stack acceptance run at milestone end.

## Out of scope

- Backend layout math (mature). The Phase 7+ gestures/halo-transport/streaming.
- Keeping the legacy `cp/` frontend (it is the porting reference only).
