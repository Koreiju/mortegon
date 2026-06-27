# Design → Code Coverage Audit (§A–§V)

**Date:** 2026-06-21
**Source of truth:** `docs/USER_REQUIREMENTS_VERBATIM.md` (§A–§V) + `docs/DOMAIN_MODEL.md` + flow-down (`features/`, `object_model/`, `code_constraints/`, `code_architecture/`, `code_specs/`).
**Method:** map each binding requirement cluster to the live code + the verification surface (env-scenario registry ~95 green, 7 probes, e2e 26, pytest), per the project's doc-first discipline (§A.1).

## KEY FINDING — two frontends; the served `/` 3D register is minimal

The verification surface (REPL `env-scenario --name all` 95/95, probes, content-tree) shows the **backend** comprehensively realizes the design: lifecycle, dual vectorization, triple-product retrieval, compile (syntax-agnostic + closest-inverse), agent tick + token stream, scan streaming, layout 6D UMAP, pattern_map, rollout/reservoir, dominance-collapse, ontology projection, db hygiene. That half is **done**.

The **frontend is split**:
- **`backend/static/js/fe/*.mjs`** — the NEW black-slate surface served at `/` (v1.0 §S/§T/§U/§V). Realizes: the 2D Imaginary register (black slate, Milkdown edit, field-tree, markdown gestures, panel↔graph), the name-only halo (`magic_markdown_halo.mjs`), and a **minimal points projector** (`projector.mjs`: HSV points only).
- **`backend/static/js/cp/*.js`** — the LEGACY frontend, demoted to `/legacy`. Holds the RICH 3D Real register: image billboards (`sprite_manager.js`), force-directed layout (`force_layout.js`), the 2D↔3D solid arrows (`animation.js`/`billboard.js`), scanner/scroll-spine (`scanner.js`).

**The gap frontier is therefore: the rich 3D Real register + the deep §M/§N/§O interaction mechanics are NOT ported into the served `/` (`fe/`) black-slate idiom.** "Build every single thing out" = realize each §B/§C/§H/§I/§M/§N/§O/§P feature in the served frontend and verify it (REPL where it reaches; e2e/Playwright for render fidelity), feature by feature.

## Per-section coverage

Legend: ✅ verified · 🟡 partial (backend/format done, render-fidelity or sub-feature gap) · 🔴 gap (little/no coverage in the served surface) · ♻ evolved/superseded by a later section.

| § | Cluster | Status | Evidence / Gap |
|---|---------|--------|----------------|
| A | Process · no-mocks · Hermes-2/nomic/CUDA · triple product | ✅ | `probe_no_mocks`, `all_real:true`, `subsystem_status` |
| B | 3D UMAP-linear-radial force-directed layout | 🟡 | Backend `layout_service` 6D fit + `6d-umap-format`/`recompute-umap`/`perimeter-rescale` ✅. **Gap (served fe/):** force-directed ray convergence (B.2), hard collider (B.3), per-URL multi-scan placement + camera framing (B.4/B.7/B.8), resize (B.9), 3-stream latency snap (B.6) — present in legacy `cp/`, NOT in `fe/projector.mjs` (points-only) |
| C | Unified knowledge panel | 🟡♻ | `compile-expand-collapse`/`latch-toggle`/`pin-chrome` ✅; black_slate+edit e2e ✅. §S.4 supersedes C.3 chrome (no ×/minimiser). **Gap:** freeze-at-hover-rect (C.2) + multi-pin drag/resize in the served surface |
| D | Apparition halo — name-only | ✅ | `halo.spec.js` HALO-01/02, `apparition-mode`, triple-product rank |
| E | Compute graph + compile | ✅ | `syntax-agnostic-compile`, `closest-inverse`, `compile-fuses-inverse`, `conceptual-compile-chain`, rollout play/pause, `autocomplete-state`, cascade |
| F | Three base API objects + python-native materialiser | ✅ | `three-fixtures-present`, `probe_python_api`, web_query/search/cypher/agent signatures |
| G | Retrieval scroll-spine + URL toggles | ♻🔴 | Sidebar DEPRECATED by §S.3 (halos subsume). Retrieval backend ✅, `purge-and-rebuild` ✅. **Gap:** the scroll→3D-pop-out spine (G.1) has no served-surface realization (was sidebar-bound) |
| H | Images — persistence + billboard spacing | 🔴 | Only in legacy `cp/sprite_manager.js`. `fe/projector.mjs` renders no image billboards → **genuine gap in served `/`** |
| I | 2D↔3D solid link arrows | 🟡 | `black_slate.spec` asserts NO dotted overlays ✅. **Gap:** the solid arrow that tracks a moving 3D node (`_drawConcept3DLinks`) is legacy-only; not in `fe/` |
| J | REPL ↔ frontend liveness | ✅ | `telemetry-roundtrip`, compile round-trips, iterated compile, RAG pipeline |
| L | Acceptance bar (10 criteria) | 🟡 | Crit. 1/6/7/8/9 ✅ (scenarios); crit. 2/3/4/5 depend on the §B/§C/§G render gaps above |
| M | Recursive type-strict exploration · reservoir readout · refined gestures | 🟡 | `reservoir-rollout-async-perimeter`, `node-fold`, `readout-panel-projection` ✅. **Gap:** hover-expands-next-rank-type-graph (M.4/M.5), single-left borderless edit fidelity (M.8) in served surface |
| N | OO DOM types · external-ref propagation · DuckDuckGo walkthrough | 🟡🔴 | `editor-link`/`editor-delete`/`apparitions-discover-link` ✅. **Gap:** external-ref propagation as recursively-rendered panels (N.3), left-click-drag wire (N.4), double-right-click delete (N.13) at render level; no end-to-end DuckDuckGo walkthrough scenario |
| O | Review clarifications (brace states, halo cone-ray, stepper, panel-embed) | 🟡 | `inverse-map`/`closest-inverse`/`halo-chain`/`signal-stream` ✅; O.22 max-cos in `apparition_service` ✅. **Gap:** 3-state brace render (O.1a), halo cone-ray transport (O.18), 2D-stepper-drives-3D-focus (O.6) at render fidelity |
| P | Cascaded recurrent renderer · perimeter · bisector node | 🟡 | `reservoir-rollout-async-perimeter`, `perimeter-rescale`, `dominance-collapse` (bisector) ✅ (backend). **Gap:** async perimeter + projector link-network render in served surface |
| Q | All-real · timed scan · rank-dominance collapse | ✅ | `timed-scan-duration-port`, `dominance-collapse`, `ui-dominance-collapse` (Q.3/Q.4/Q.5) |
| R | Node-panel commute · full DB ontology in 3D · markdown gestures · db cleanup | ✅ | `markdown-restructure`, `ontology-projection`, `inverse-map-state-space`, `readout-panel-projection`, `iterated-signal-rerender`, `db-janitor` |
| S | Editor/sidebar deprecation · black slate | ✅ | `three-fixtures-present`, `black_slate.spec` (§S.4 chrome-free) |
| T | Black markdown slate | ✅ | `black_slate.spec`, `edit.spec` (Milkdown); T.7 internalize/externalize gestures 🟡 |
| U | HTML dedup content-tree | ✅ | content_tree golden 6/6 + breadth, `syntax-agnostic-compile` HtmlStrategy |
| V | Streaming SLA · multi-site · halo ray · circular node | 🟡 | halo ray + circular node ✅ (`halo.spec`); V.3 corpus ✅ (`breadth_content_tree_smoke`). **Gap:** live ms-scan→seconds-UMAP streaming SLA (V.1) = mid-scan refit (overlaps PERF-01); live multi-site render verify |

## Gap clusters → proposed feature phases

The gaps concentrate cleanly. Proposed feature-structured roadmap (each phase = a design feature-area, verified by named scenario + Playwright e2e + probe where applicable):

1. **3D Real register in the served slate (§B/§H/§I)** — port UMAP-linear-radial force-directed convergence, per-URL multi-scan placement + camera framing/bounds, hard collider, image billboards, solid 2D↔3D arrows into `fe/projector.mjs` + `editor.html`. The single largest gap.
2. **Deep object-exploration gestures (§M/§N)** — hover-expands-next-rank-type-graph, external-ref propagation as recursive panels, left-click-drag wire, double-right-click delete, single-left borderless edit; the DuckDuckGo walkthrough as an end-to-end scenario+probe.
3. **Halo cone-ray transport + brace-state render + 2D↔3D stepper (§O.1a/O.6/O.18)** — the projective halo transport in 3D, 3-state `{ref}` render, 2D per-sample stepper drives 3D focus.
4. **Cascaded recurrent renderer surface (§P)** — async perimeter + projector link-network render (backend exists; surface it).
5. **Live streaming SLA (§V.1/§B.6)** — mid-scan incremental UMAP refit + the ms-scan→seconds-UMAP snap (this IS the deferred PERF-01).
6. **Retrieval scroll-spine reconciliation (§G.1)** — decide: realize scroll→3D-pop-out in the halo idiom, or formally fold §G.1 into §S.3's halo-subsumes-sidebar (doc reconciliation).

## Recommendation

- **~75% of the design is built+verified** (all backend + the 2D black-slate + halo-model + the §Q/§R/§S/§T/§U families). The genuine build frontier is the **served-frontend 3D Real register + deep interaction mechanics** (phases 1–4 above), plus the live-streaming SLA (phase 5) and one doc reconciliation (phase 6).
- **This is a real build milestone, not just verification** — phases 1–3 are net-new frontend work in the `fe/` idiom.
- **Verification depth:** these gaps are overwhelmingly **render-fidelity** (3D layout, billboards, arrows, gestures) — best verified by **Playwright e2e + REPL telemetry**, with **one consolidated real-stack acceptance pass at the end** (the lodestars already pass real-stack; per-phase CUDA boots add little for render work). Recommend **stub-fast per phase + real-stack acceptance at the end**.
