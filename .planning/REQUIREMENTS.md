# Requirements: web_fiber_haptics — v3.0 Design Completeness

**Defined:** 2026-06-21 (from `.planning/DESIGN_COVERAGE_AUDIT.md`)
**Core Value:** Every binding design requirement (§A–§V of `docs/USER_REQUIREMENTS_VERBATIM.md`) is realized in the **served `/` black-slate frontend** and verified against real subsystems — not split between the new `fe/` surface and the legacy `cp/` one. The four lodestar use cases stay green throughout.

> **Audit basis.** ~75% of §A–§V is already built+verified (all backend + the 2D black-slate + the name-only halo + the §Q/§R/§S/§T/§U families). The v3.0 frontier is the **3D Real register + the deep §M/§N/§O/§P interaction mechanics** that live only in the legacy `cp/` frontend (demoted to `/legacy`) and must be ported into the served `fe/` idiom, plus the live-streaming SLA and one doc reconciliation. Full per-section status: `.planning/DESIGN_COVERAGE_AUDIT.md`.

## v3 Requirements

### Phase 6 — 3D Real Register in the Served Slate (§B / §H / §I)

- [x] **REAL-01**: `fe/` projector renders the UMAP-linear-radial **force-directed** layout — chunks converge along root-URL rays with hard collider repulsion (zero force above `2·R·safety`, exact-correction below); no concentric/Fibonacci as a final position. (§B.2/§B.3)
- [x] **REAL-02**: Per-URL multi-scan placement — each URL has its own `root_position`+`bounding_radius`; a new URL lands non-overlapping at `existing_max + new_radius + safety_gap`; old URLs never move on a new scan; camera frames/bounds the scene and tweens to the newest root on scan-end (respecting user interaction). (§B.4/§B.7/§B.8/§B.9)
- [x] **REAL-03**: Image billboards render in the served projector — single-fetch persistence (in-mem → IndexedDB → proxy → direct), shared `THREE.Texture` per URL, transparent-PNG fallback never cached as success, collider spacing shared with text billboards. (§H.1/§H.2)
- [x] **REAL-04**: Solid (headless) 2D↔3D link arrows — every pinned panel carries `data-3d-node-id`; the animate loop projects the node and draws a solid line that tracks the moving 3D node; off-frustum hides; no dotted lines anywhere. (§I / §O.16)

### Phase 7 — Deep Object-Exploration Gestures (§M / §N)

- [x] **EXPLORE-01**: Hover expands the next-rank type graph (super-class + typed constructor params); function rows expand to loosely-linked typed input/output fields; output types inferred by i/o equality. (§M.4/§M.5)
- [x] **EXPLORE-02**: External node references propagate as their own recursively-rendered panels (rank-1 minimalism, a PRO-pattern); a `{ref}` is a duplicate instance that operationally calls the originating object. (§N.3/§N.6/§N.7/§N.14)
- [x] **EXPLORE-03**: Left-click-drag wires nodes in graph form (target inherits i/o types); double-right-click deletes a token reference/instance in panel or graph form. (§N.4/§N.13)
- [x] **EXPLORE-04**: The DuckDuckGo walkthrough runs end-to-end (REPL scenario + probe): author `self=duckduckgo` referencing `scan`, drag-wire the WebBrowser scanner, reveal rank-1 `url{}`/`dom{}`, per-sample chunk iteration on `{chunk samples}`. (§N.2–§N.10)

### Phase 8 — Halo Cone-Ray Transport + Brace States + 2D→3D Stepper (§O.1a / §O.6 / §O.18)

- [ ] **HALO-03**: Halo cone-ray transport — retrieved 3D nodes are transported along a shared cone whose apex is the 2D query element; normalized triple-product similarity sets the radial+along-ray distance; camera view sets angular placement; deleting a result transports the next-most-similar. (§O.18)
- [ ] **HALO-04**: Three `{ref}` render states — braced-hidden (hover-preview/reveal-instantiate), revealed-internal (inline rank-1), resolved-external (solid line to an already-visible node); node-count parity between panel and graph forms. (§O.1/§O.1a/§O.2)
- [ ] **STEP-01**: The 2D per-sample stepper drives 3D focus one-way — advancing `{chunk samples}` in 2D flies/highlights the corresponding chunk in 3D; the 3D always shows the full per-sample distribution. (§O.6/§O.7/§O.11)

### Phase 9 — Cascaded Recurrent Renderer Surface (§P)

- [ ] **CASC-01**: The reservoir rollout's perimeter (final-most readout nodes) renders asynchronously per subgraph rollout-path-length, streamed as delta updates to a projector node-edge **link network** rendered independent of the UMAP embedding. (§P.3/§P.6/§P.7/§P.8)
- [ ] **CASC-02**: Readouts stream to the 3D projector with physical + HSV color-representation rotation in passive state (for nodes without image billboards). (§P.4)

### Phase 10 — Live Streaming SLA (§V.1 / §B.6)

- [ ] **STREAM-01**: Mid-scan incremental joint-UMAP refit — chunks stream and update live (scans in ms via mutation observers; UMAP seconds-to-ms for updates); 3-stream latency handled (placeholder → UMAP snap at scan-end, never mid-stream); never interfere with the scanner's chunk bookkeeping. (Supersedes the deferred PERF-01.) (§V.1/§B.6)

### Phase 11 — Scroll-Spine Reconciliation (§G.1)

- [ ] **SPINE-01**: Reconcile the §G.1 scroll-and-pop-out spine with the §S.3 sidebar deprecation — realize a scroll→3D-pop-out in the in-editor halo idiom (IntersectionObserver flips only viewport-visible rows; off-viewport re-fold; no global show-all), or formally fold §G.1 into §S.3 in the docs with the retrieval backend intact. (§G.1/§G.6/§S.3)

## Deferred → v2.0 (Autonomy Hardening & Maintainability), after v3.0

| Req | Item |
|-----|------|
| HARNESS-01 | Reliable unattended `--real` harness boot + clean-GPU preflight |
| PERF-02 | GPT4All Embed4All Windows thread-safety hardening |
| MAINT-01 | Split `routes.py` by register |
| MAINT-02 | Decompose `sim_frontend.py` by action category |

## Out of Scope

Same forbidden-concepts list as v1.0 (D2/D3/D9/D11): concentric Fibonacci spheres, graph-analytics retrieval, Llama, two-panel split, Editor fixture, retrieval sidebar, panel chrome, dotted lines, real→stub fallback. The legacy `cp/` frontend is the *reference* for porting, not a surface to keep — v3.0 brings its features into `fe/`.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REAL-01 | 6 | Complete |
| REAL-02 | 6 | Complete |
| REAL-03 | 6 | Complete |
| REAL-04 | 6 | Complete |
| EXPLORE-01 | 7 | Complete |
| EXPLORE-02 | 7 | Complete |
| EXPLORE-03 | 7 | Complete |
| EXPLORE-04 | 7 | Complete |
| HALO-03 | 8 | Pending |
| HALO-04 | 8 | Pending |
| STEP-01 | 8 | Pending |
| CASC-01 | 9 | Pending |
| CASC-02 | 9 | Pending |
| STREAM-01 | 10 | Pending |
| SPINE-01 | 11 | Pending |

**Coverage:** 15 v3 requirements across 6 phases; mapped 15; unmapped 0 ✓

---
*v3.0 requirements derived 2026-06-21 from DESIGN_COVERAGE_AUDIT.md (§A–§V gap frontier).*
