# Phase 3 — HTML Dedup + Halo Retrieval Render — CONTEXT

> Brownfield **finish-and-verify** (not from-scratch). The §U deduplicated
> content-tree (`backend/dom/content_tree.py`) and the §V halo model
> (`backend/static/js/fe/magic_markdown_halo.mjs` + the live wiring in
> `backend/templates/editor.html`) are already built and corpus-hardened. This
> phase converts that browser-verified work into the project's REPL/probe/e2e
> verification idiom and closes the remaining live-halo browser-acceptance gap.

## Goal

A scanned HTML chunk renders as a clean deduplicated content-tree, and clicking a
collapsed circular node fires a NAME-only apparition halo ranked by the triple
product `pagerank · tfidf_cos · nomic_cos` — finishing the §U/§V render gaps on
the existing backend.

## In scope (requirements EDIT-/§U/§V)

- **SC1 (§U content-tree)** — HTML chunk body = deduplicated content as a pure-text
  tree (collapsed wrappers, token-set dedup, surfaced href/src) built from `fields`
  not `html_raw`; byte-exact §U golden I/O (6/6) holds; `env-scenario --name
  syntax-agnostic-compile` exercises the HtmlStrategy arm green in both modes.
- **SC2 (halo retrieval)** — clicking a collapsed node fires a halo whose phantoms
  show candidate NAME only (scores in slow-hover tooltips), ranked by the triple
  product with no graph-analytics axes; the autoregressive walk advances on click.
  `env-scenario --name apparition-mode` / `halo-retrieval` green.
- **SC3 (halo render contract)** — halo stays proximal to a CIRCULAR
  root-field-only collapsed node (§S.5); constant-similarity ray + along-line
  slide; soft/hard link promotion; the 2D↔3D arrow is solid (DOM audit finds no
  dotted overlays).
- **SC4 (real-stack breadth)** — `scripts/probe_pattern_map.py` and the live
  archive/tarot/yourchineseastrology/studycli sites render clean+deduped against
  the real stack.

## As-built starting point (do NOT rebuild)

- `backend/dom/content_tree.py` — `fields_to_content_tree`; golden 6/6 + breadth
  corpus (61 sites / 0 invariant violations, `scripts/breadth_content_tree_smoke.py`),
  unicode dedup tokenizer fixed (`bf2c9c7`), embedded-HTML leak fixed (`f5f78e7`).
- `backend/static/js/fe/magic_markdown_halo.mjs` — pure `haloLayout`
  (constant-similarity ray, along-line slide, camAngle) + `haloVDom` (name-only
  circular phantoms, z-above-slate). Unit-covered 5/5 (`magic_markdown_halo.test.mjs`).
- `backend/templates/editor.html` — the LIVE wiring: `openHalo`/`renderHalo`,
  scroll re-anchor (T.4 #2), projector-azimuth coupling (`onFrame → halo.camAngle`),
  and the `__mm_open_halo` / `__mm_halo_state` / `__mm_halo_rotate` test hooks.
- Backend retrieval (`/api/radiation`, triple-product index) — mature.

## The gap this phase closes

The live halo had NO browser-acceptance coverage — `frontend_e2e/halo.spec.js`
carried 3 `test.fixme` placeholders. This phase writes those 3 specs (HALO-01
name-only phantoms; HALO-02 z-order + focal re-anchor; HALO-02 constant-similarity
ray + along-line slide on camera orbit) against the served `/` editor.

## Verification gate (the framework — `.planning/TEST_MATRIX.md`)

- **e2e:** un-fixme HALO-01/02 in `frontend_e2e/halo.spec.js`, green in both modes.
- **REPL:** `syntax-agnostic-compile`, `apparition-mode`, `halo-retrieval`,
  `apparitions-discover-link` green in `env-scenario --name all` (both modes).
- **pytest:** `test_content_tree.py` (golden 6/6) + `test_content_tree_breadth.py`.
- **probe:** `scripts/probe_pattern_map.py` against the real stack.
- **DOM audit:** no `dashed`/`dotted` overlays in fe/editor/css.

## Out of scope

- Rebuilding content_tree / the halo model / the retrieval backend (all built).
- Phase 4 live-layout/signal/pattern render (separate phase).
