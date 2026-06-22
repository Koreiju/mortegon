# Roadmap: web_fiber_haptics (Mortegon)

## Milestones

- ✅ **v1.0 Real-Stack Acceptance** — Phases 1–5 (shipped 2026-06-20) — [archive](milestones/1.0-ROADMAP.md)
- 🚧 **v3.0 Design Completeness** — Phases 6–11 (in progress) — realize every §A–§V design feature in the served `fe/` frontend
- 📋 **v2.0 Autonomy Hardening & Maintainability** — Phases 12–14 (deferred, after v3.0)

v1 proved the four lodestar use cases against real subsystems (`all_real:true`). The
2026-06-21 design→code audit (`.planning/DESIGN_COVERAGE_AUDIT.md`) found ~75% of the
binding design (§A–§V) built+verified, with the gap frontier being the **3D Real
register + deep §M/§N/§O/§P interaction mechanics** that live only in the legacy
`cp/` frontend (demoted to `/legacy`) and must be ported into the served black-slate
`fe/` surface. v3.0 closes that frontier feature-by-feature against the real stack.
v2.0 (autonomy hardening / de-monolith / perf) is deferred until after.

## Phases

- [x] **Phase 1: Honest Baseline** *(v1.0 — shipped 2026-06-15)*
- [x] **Phase 2: Black-Slate Field Editing** *(v1.0 — shipped 2026-06-18)*
- [x] **Phase 3: HTML Dedup + Halo Retrieval Render** *(v1.0 — shipped 2026-06-18)*
- [x] **Phase 4: Live Layout, Signal & Pattern** *(v1.0 — shipped 2026-06-18)*
- [x] **Phase 5: Three-Register Synthesis & Live Acceptance** *(v1.0 — shipped 2026-06-19)*
- [ ] **Phase 6: 3D Real Register in the Served Slate** *(v3.0)* - Port the UMAP-linear-radial force-directed layout, per-URL multi-scan placement + camera framing, image billboards, and solid 2D↔3D arrows into the served `fe/` projector. (REAL-01..04)
- [ ] **Phase 7: Deep Object-Exploration Gestures** *(v3.0)* - Next-rank type-graph on hover, external-reference propagation as recursive panels, drag-to-wire + double-right-delete, the DuckDuckGo walkthrough. (EXPLORE-01..04)
- [ ] **Phase 8: Halo Cone-Ray Transport + Brace States + Stepper** *(v3.0)* - Projective halo cone transport, three `{ref}` render states, 2D per-sample stepper drives 3D focus. (HALO-03/04, STEP-01)
- [ ] **Phase 9: Cascaded Recurrent Renderer Surface** *(v3.0)* - Async perimeter render + projector link-network (independent of UMAP); readouts stream to projector with HSV rotation. (CASC-01/02)
- [ ] **Phase 10: Live Streaming SLA** *(v3.0)* - Mid-scan incremental UMAP refit; ms-scan→seconds-UMAP live updates; scan-end snap. (STREAM-01; supersedes PERF-01)
- [ ] **Phase 11: Scroll-Spine Reconciliation** *(v3.0)* - Realize the scroll→3D-pop-out spine in the halo idiom, or formally fold §G.1 into §S.3. (SPINE-01)
- [ ] **Phase 12: Autonomy Hardening** *(v2.0 — deferred)* - Reliable unattended `--real` harness boot + clean-GPU preflight; Embed4All thread-safety. (HARNESS-01, PERF-02)
- [ ] **Phase 13: Maintainability** *(v2.0 — deferred)* - Split `routes.py` by register; decompose `sim_frontend.py` by action category. (MAINT-01, MAINT-02)
- [ ] **Phase 14: Performance** *(v2.0 — deferred)* - (folded into STREAM-01 if Phase 10 lands incremental refit; otherwise residual perf.) (PERF-01)

## Phase Details

### Phase 6: 3D Real Register in the Served Slate

**Goal**: The served `/` black-slate frontend renders the full 3D Real register — UMAP-linear-radial force-directed layout converging along root-URL rays, per-URL multi-scan placement with camera framing, image billboards with single-fetch persistence, and solid (headless) 2D↔3D link arrows — bringing the legacy `cp/` 3D features into the `fe/` idiom.
**Depends on**: Phase 5
**Requirements**: REAL-01, REAL-02, REAL-03, REAL-04
**Success Criteria** (what must be TRUE):

  1. `fe/projector.mjs` lays chunks by UMAP then converges force-directed along root-URL rays with hard collider repulsion; no concentric/Fibonacci final position. Verified by a `projector.spec.js` assertion (rays + min pairwise spacing) + `env-scenario --name 6d-umap-format`/`perimeter-rescale` green.
  2. Two scans of different URLs produce non-overlapping clusters at `existing_max + new_radius + safety_gap`; re-scanning the first does not move the second; camera frames the scene and tweens to the newest root. Verified by a multi-scan e2e + REPL telemetry.
  3. Image billboards render in the served projector with shared textures and the in-mem→IndexedDB→proxy→direct fetch order; an e2e asserts an image node paints and persists across a re-render.
  4. Pinned panels draw a solid headless arrow to their `data-3d-node-id` that tracks the moving node; `black_slate.spec` (no dotted overlays) stays green + a new arrow-tracking e2e.**Plans**: 1/4 plans executed

**Wave 1**

- [x] 06-01-PLAN.md — REAL-01 force-directed ray convergence + collider (Wave-0 unit/e2e scaffold)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 06-02-PLAN.md — REAL-02 per-URL placement consumption (url_roots) + camera framing

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 06-03-PLAN.md — REAL-03 image billboards (single-fetch cache chain, shared textures)

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 06-04-PLAN.md — REAL-04 solid headless 2D↔3D arrow + data-3d-node-id + #link-layer

**UI hint**: yes

### Phase 7: Deep Object-Exploration Gestures

**Goal**: The served editor supports the §M/§N recursive type-strict object exploration — hover expands the next-rank type graph, external references propagate as recursively-rendered panels, left-click-drag wires nodes and double-right-click deletes, all at rank-1 minimalism — and the DuckDuckGo walkthrough runs end-to-end.
**Depends on**: Phase 6
**Requirements**: EXPLORE-01, EXPLORE-02, EXPLORE-03, EXPLORE-04
**Success Criteria** (what must be TRUE):

  1. Hovering a typed row (e.g. `driver: WebDriver`) expands its next-rank type graph (super-class + typed params); function rows expand to loosely-linked typed i/o. Verified by an e2e over a materialised python_object tree + `env-scenario --name ontology-walk`.
  2. An external `{ref}` propagates as its own recursively-rendered panel/instance (rank-1); verified by `editor-link` + a render e2e.
  3. Left-click-drag wires two graph nodes (target inherits i/o types); double-right-click deletes a token in panel or graph form. Verified by e2e gestures + `editor-delete`/`editor-link` telemetry.
  4. A `duckduckgo-walkthrough` env-scenario + probe runs the §N flow end-to-end against real subsystems.

**Plans**: TBD
**UI hint**: yes

### Phase 8: Halo Cone-Ray Transport + Brace States + Stepper

**Goal**: The halo transports retrieved 3D nodes along a shared cone by normalized triple-product similarity (§O.18), `{ref}`s render in three states (§O.1a), and the 2D per-sample stepper drives 3D focus one-way (§O.6).
**Depends on**: Phase 7
**Requirements**: HALO-03, HALO-04, STEP-01
**Success Criteria** (what must be TRUE):

  1. Opening a halo transports retrieved 3D nodes onto a cone (apex = 2D query element); radial+along-ray distance encodes normalized similarity; deleting a result transports the next-most-similar. Verified by `halo.spec.js` (cone transport) + `env-scenario --name apparition-mode`/`halo-chain-roundtrip`.
  2. A `{ref}` renders braced-hidden / revealed-internal / resolved-external(solid link) with panel↔graph node-count parity. Verified by an e2e over a two-level ref chain.
  3. Advancing the 2D `{chunk samples}` stepper flies/highlights the corresponding 3D chunk while 3D shows the full distribution. Verified by `env-scenario --name signal-stream-roundtrip`/`iterated-signal-rerender` + an e2e.

**Plans**: TBD
**UI hint**: yes

### Phase 9: Cascaded Recurrent Renderer Surface

**Goal**: The reservoir rollout's perimeter renders asynchronously and streams as delta updates to a projector node-edge link-network (independent of the UMAP embedding), with readouts carrying HSV rotation in passive state (§P).
**Depends on**: Phase 8
**Requirements**: CASC-01, CASC-02
**Success Criteria** (what must be TRUE):

  1. A multi-subgraph rollout emits perimeter readouts asynchronously per path length; the projector renders a link-network distinct from the UMAP layout. Verified by `env-scenario --name reservoir-rollout-async-perimeter` + a projector e2e.
  2. Readout nodes stream to the projector with HSV color rotation in passive state (non-image nodes). Verified by `env-scenario --name readout-panel-projection` + an inspect e2e.

**Plans**: TBD
**UI hint**: yes

### Phase 10: Live Streaming SLA

**Goal**: Chunks stream and update live during a scan — mid-scan incremental joint-UMAP refit so the 3D manifold updates as chunks land (ms scans, seconds-to-ms UMAP), with the scan-end snap, never interfering with scanner chunk bookkeeping (§V.1/§B.6).
**Depends on**: Phase 9
**Requirements**: STREAM-01
**Success Criteria** (what must be TRUE):

  1. `umap_canonical` frames emit incrementally mid-scan (not only scan-end); a probe asserts mid-scan refit produces comparable coords and the chunk count climbs live.
  2. `full-smoke`/`all` stays green both modes; `probe_live_scan_with_cleanup` stays green; chunk bookkeeping ids unchanged.

**Plans**: TBD

### Phase 11: Scroll-Spine Reconciliation

**Goal**: Reconcile the §G.1 scroll-and-pop-out spine with the §S.3 retrieval-sidebar deprecation — either realize a scroll→3D-pop-out in the in-editor halo idiom, or formally fold §G.1 into §S.3 in the docs (retrieval backend intact).
**Depends on**: Phase 10
**Requirements**: SPINE-01
**Success Criteria** (what must be TRUE):

  1. Either: scrolling the in-editor result/halo list pops out only viewport-visible chunks in 3D (IntersectionObserver; off-viewport re-folds; no global show-all), verified by an e2e + REPL telemetry; OR: §G.1 is formally folded into §S.3 across the docs with a recorded rationale and the retrieval backend untouched.

**Plans**: TBD

### Phase 12: Autonomy Hardening *(v2.0 — deferred)*

**Goal**: Unattended `--real` harness boot reliably comes up `all_real:true` (WebDriver-health retry + clean-GPU/`:8080`/Kuzu-lock preflight); Embed4All Windows native crash hardened.
**Requirements**: HARNESS-01, PERF-02
**Status**: Deferred until v3.0 completes.

### Phase 13: Maintainability *(v2.0 — deferred)*

**Goal**: Split `backend/api/routes.py` by register; decompose `scripts/sim_frontend.py` by action category; tests stay green; no file > ~2,000 lines.
**Requirements**: MAINT-01, MAINT-02
**Status**: Deferred until v3.0 completes.

### Phase 14: Performance *(v2.0 — deferred)*

**Goal**: Residual performance (incremental mid-scan UMAP refit if not already delivered by Phase 10/STREAM-01).
**Requirements**: PERF-01
**Status**: Deferred; likely subsumed by Phase 10.

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1. Honest Baseline | v1.0 | direct | Complete | 2026-06-15 |
| 2. Black-Slate Field Editing | v1.0 | direct | Complete | 2026-06-18 |
| 3. HTML Dedup + Halo | v1.0 | direct | Complete | 2026-06-18 |
| 4. Live Layout/Signal/Pattern | v1.0 | direct | Complete | 2026-06-18 |
| 5. Three-Register Synthesis | v1.0 | direct | Complete | 2026-06-19 |
| 6. 3D Real Register (served) | v3.0 | 1/4 | In Progress|  |
| 7. Deep Object-Exploration Gestures | v3.0 | 0/TBD | Not started | - |
| 8. Halo Cone-Ray + Brace + Stepper | v3.0 | 0/TBD | Not started | - |
| 9. Cascaded Recurrent Renderer | v3.0 | 0/TBD | Not started | - |
| 10. Live Streaming SLA | v3.0 | 0/TBD | Not started | - |
| 11. Scroll-Spine Reconciliation | v3.0 | 0/TBD | Not started | - |
| 12. Autonomy Hardening | v2.0 | 0/TBD | Deferred | - |
| 13. Maintainability | v2.0 | 0/TBD | Deferred | - |
| 14. Performance | v2.0 | 0/TBD | Deferred | - |

---
*v1.0 archived 2026-06-20. v3.0 (Design Completeness) roadmap created 2026-06-21 from DESIGN_COVERAGE_AUDIT.md; v2.0 hardening/maint/perf deferred to phases 12–14.*
