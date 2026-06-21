# Phase 3 — HTML Dedup + Halo Retrieval Render — CONTEXT

> Context for planning/execution. Captured from the roadmap SCs + the as-built
> code (brownfield: the §U content-tree is corpus-hardened and the §V halo model +
> live wiring already exist; this phase is **finish-and-verify**, not from-scratch).

## Goal

A scanned HTML chunk renders as a clean **deduplicated content-tree**, and clicking
a **collapsed circular node** fires a **name-only apparition halo** ranked by the
triple product `pagerank · tfidf_cos · nomic_cos` — finishing the §U/§V render gaps
on the existing backend.

## In scope (requirements)

- **HTML-01** — an HTML chunk slate body is the DEDUPLICATED content as a pure-text
  tree (collapse wrappers, token-set dedup, surface href/src), built from the
  existing `fields` extraction (NOT `html_raw`); `_try_parse_structured` is the
  single detector, `_decomposeValue` mirrors the strategy order; byte-exact §U
  golden I/O (6/6) holds.
- **HALO-01** — apparition halo phantoms show candidate **NAME only** (scores in
  slow-hover tooltips); ranking is the triple product (no graph-analytics axes);
  the autoregressive walk advances via click.
- **HALO-02** — the halo stays proximal to a **CIRCULAR root-field-only collapsed
  node** (§S.5); the constant-similarity ray supports along-line slide as the 3D
  camera orbits; soft/hard link promotion works; the 2D↔3D link arrow is solid
  (no dotted overlays).

## As-built starting point (do NOT rebuild)

- **§U content-tree (HTML-01):** `backend/dom/content_tree.py::fields_to_content_tree`
  + `_norm` (HTML-tag strip) — corpus-hardened: `scripts/breadth_content_tree_smoke.py`
  drives the REAL ruleset over **61 sites / 120,226 instances / 87,737 trees / 0
  invariant violations** (commits `bf2c9c7` international-dedup, `f5f78e7` embedded-
  HTML-leak). Backend `_try_parse_structured` / frontend `_decomposeValue` are the
  §E.1 single detector/mirror. **HTML-01 is essentially DONE — this phase VERIFIES
  it (golden 6/6 + `syntax-agnostic-compile` HtmlStrategy arm), it does not rebuild.**
- **§V halo MODEL:** `backend/static/js/fe/magic_markdown_halo.mjs` —
  `haloLayout` (pure: focal + candidates + camAngle → ray positions; `r = rBase +
  (1-sim)·rExtent` constant-similarity radius; `angle = base(i) + camAngle` slide)
  and `haloVDom` (overlay: name-only `.mm-phantom` circular nodes, `data-sim` for
  the slow-hover tooltip, ray `<line>`s, `z-index:2147483000` above the slate).
  **Unit-covered 5/5** (`magic_markdown_halo.test.mjs`).
- **§V halo WIRING (live `/`):** `editor.html::openHalo` already fires on a field
  click, runs **real `/api/radiation`** triple-product retrieval, re-anchors on
  `scroll` (capture), and couples `halo.camAngle` to the projector camera azimuth
  (`projector.onFrame`). The retrieval backend (`/api/radiation`, `/api/apparitions`,
  triple-product index) is real and tested.
- **§15.1 circular collapsed node:** the panel⇄graph circular-node form
  (`graphVDom`, `gnodeRound` 50%) is exercised in `edit.spec.js`.

## The gap (what this phase actually lands)

1. **Halo fires from a COLLAPSED CIRCULAR node** (not just any text field) and stays
   **proximal** to it (§S.5) — wire the §15.1 collapsed-node click → `openHalo`
   anchored at the node's live rect.
2. **Live-editor browser acceptance** — un-fixme the 3 `frontend_e2e/halo.spec.js`
   specs (HALO-01 name-only phantoms; HALO-02 z-order + scroll/move re-anchor;
   HALO-02 camera-orbit ray slide) against the served `/` on a fixture scan.
3. **REPL/scenario coverage** — `env-scenario --name apparition-mode` (+ a
   `halo-retrieval` scenario) asserting the triple-product ranking + autoregressive
   walk through the API/WS seam (the e2e blind spot).
4. **DOM audit** — the 2D↔3D link arrow is solid; no dotted overlays (extends the
   `black_slate.spec.js` forbidden-widget audit).
5. **Real-stack breadth** — `scripts/probe_pattern_map.py` + live archive/tarot/
   yourchineseastrology/studycli sites render clean+deduped (HTML-01 on live data).

## Verification gate (the framework — `.planning/TEST_MATRIX.md`)

Each task lands a green check in `scripts/run_full_stack_tests.py`:
- **e2e:** un-fixme `frontend_e2e/halo.spec.js` (HALO-01/02) against the served `/`;
  drive out with the Playwright MCP first, then codify (the Phase-2 idiom).
- **REPL:** `env-scenario --name apparition-mode` / `halo-retrieval` /
  `syntax-agnostic-compile` green in both modes.
- **Probe:** `scripts/probe_pattern_map.py` + live-site breadth on the real stack.
- **Gate:** `npm run test:all` green in both modes with the halo specs un-fixme'd;
  `full-smoke` stays green.

## Out of scope

- Rebuilding the content-tree extraction, the halo model, the retrieval index, or
  the projector (all built + tested).
- Phase 4 live layout/signal/pattern (separate phase).
- Backend lifecycle/index/persistence (mature; frontend renders only).

## Forbidden (must NOT re-introduce — D11)

- Graph-analytics retrieval axes (depth/subtree_size/wl_hash) — ranking is the
  triple product ONLY, the two embedding axes never mix.
- Score chips on phantoms — phantoms are NAME-only; scores live in slow-hover
  tooltips (`data-sim`).
- Dotted 2D↔3D arrows / dotted debug overlays — the link arrow is solid.
- Concentric/Fibonacci halo rings — ray-constrained placement around the focal only.
