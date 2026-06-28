---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Design Completeness
current_phase: 8
current_phase_name: Halo Cone-Ray Transport + Brace States + Stepper
status: executing
stopped_at: 08-04 Task 1 complete (probe_live_cone_transport.py, 28128c7); Task 2 (D-01 real-subsystem acceptance) awaiting blocking-human main-context checkpoint
last_updated: "2026-06-28T20:54:03.615Z"
progress:
  total_phases: 9
  completed_phases: 2
  total_plans: 14
  completed_plans: 13
  percent: 31
---

# Project State

## Project Reference

See: .planning/PROJECT.md · v1.0 archive: .planning/milestones/1.0-ROADMAP.md · audit: .planning/DESIGN_COVERAGE_AUDIT.md

**Core value (v3):** Every binding design requirement (§A–§V of `docs/USER_REQUIREMENTS_VERBATIM.md`) is realized in the **served `/` black-slate frontend** and verified against real subsystems — not split between the new `fe/` surface and the legacy `cp/` one. The four lodestar use cases stay green throughout (`all_real:true`).
**Current focus:** Phase 8 — Halo Cone-Ray Transport + Brace States + Stepper

## Current Position

Phase: 8 (Halo Cone-Ray Transport + Brace States + Stepper) — EXECUTING
Plan: 4 of 4 — Task 1 complete; Task 2 (D-01 real-subsystem acceptance) awaiting blocking-human main-context checkpoint
Status: Awaiting human checkpoint
Verification depth (user choice 2026-06-21): **full real-stack inline per phase** (boot real CUDA/Firefox, probes + real full-smoke + e2e), honoring the clean-GPU preflight.

## Audit basis (2026-06-21)

`.planning/DESIGN_COVERAGE_AUDIT.md`: ~75% of §A–§V built+verified (all backend + 2D black-slate + name-only halo + the §Q/§R/§S/§T/§U families; 95/95 REPL + 7 probes + content-tree golden). **Gap frontier = the 3D Real register + deep §M/§N/§O/§P interaction mechanics living only in the legacy `cp/` frontend (demoted to `/legacy`), to be ported into the served `fe/` idiom**, plus the live-streaming SLA (§V.1) and one doc reconciliation (§G.1↔§S.3).

### v3.0 phases

- **P6 3D Real Register** (REAL-01..04) — force-directed UMAP-linear-radial layout, per-URL multi-scan placement + camera framing, image billboards, solid 2D↔3D arrows. **Largest gap — do first.**
- **P7 Deep Object-Exploration Gestures** (EXPLORE-01..04) — next-rank type-graph, external-ref propagation, drag-to-wire/double-right-delete, DuckDuckGo walkthrough.
- **P8 Halo Cone-Ray + Brace States + Stepper** (HALO-03/04, STEP-01).
- **P9 Cascaded Recurrent Renderer Surface** (CASC-01/02).
- **P10 Live Streaming SLA** (STREAM-01; supersedes PERF-01).
- **P11 Scroll-Spine Reconciliation** (SPINE-01).

## Accumulated Context

### Decisions (governing, carried forward)

- D1–D11 LOCKED (PROJECT.md). No-mocks (real GPT4All/nomic/Selenium/LangGraph; loud 503). Backend computes / frontend renders. Triple-product retrieval. Forbidden: concentric spheres, graph analytics, Llama, two-panel split, Editor fixture, retrieval sidebar, panel chrome, dotted lines.
- **[v3.0 framing, 2026-06-21]** The legacy `cp/` frontend is the *reference* for porting the 3D Real register into `fe/`, not a surface to keep. Build each §A–§V feature into the served black-slate idiom.

### Blockers / Concerns

- Real-stack env hygiene: clean GPU (≈0 MiB VRAM / 0 stray python+firefox) required before each real run; backend 8080 vs REPL 8000 (pass `--backend http://127.0.0.1:8080`); tear down with `taskkill /F /T`.
- Two frontends co-exist (`fe/` served, `cp/` at `/legacy`) — v3.0 converges the 3D register into `fe/`.

## Session Continuity

**Resume file:** 08-04-PLAN.md

Last session: 2026-06-28T20:54:03.514Z
Stopped at: 08-04 Task 1 complete (probe_live_cone_transport.py, 28128c7); Task 2 (D-01 real-subsystem acceptance) awaiting blocking-human main-context checkpoint
Next: Perform 08-04 Task 2 — the D-01 clean-GPU preflight + real-subsystem cone-transport acceptance run (`python scripts/probe_live_cone_transport.py --backend http://127.0.0.1:8080`) from the MAIN context (see 08-04-PLAN.md Task 2 how-to-verify), then resume to close out Phase 8.

## Performance Metrics

| Phase | Plan | Duration | Notes |
|-------|------|----------|-------|
| Phase WFH-06 P01 | 95min | 3 tasks | 4 files |
| Phase WFH-06 P02 | 25min | 3 tasks | 3 files |
| Phase WFH-06 P03 | 70min | 3 tasks | 3 files |
| Phase WFH-06 P04 | 45min | 3 tasks | 3 files |
| Phase WFH-07 P01 | 12min | 2 tasks | 2 files |
| Phase WFH-07 P02 | 18min | 2 tasks | 2 files |
| Phase WFH-07-deep-object-exploration-gestures P03 | 22min | 2 tasks | 4 files |
| Phase WFH-07 P04 | 18min | 3 tasks | 5 files |
| Phase WFH-07 P06 | 70min | 3 tasks | 3 files |
| Phase 08 P02 | 1 session | 3 tasks | 6 files |
| Phase WFH-08 P03 | 1 session | 4 tasks | 12 files |
| Phase WFH-08 P04 | 25min | 1 tasks | 1 files |

## Decisions

- [Phase ?]: COLLIDER_SAFETY ships as 1.4 (cp/force_layout.js line 161), not the doc's >=2.0 — MIN_SEPARATION = 2.52, verified by unit + e2e assertions
- [Phase WFH-06]: url_roots wired through editor.html's WS handler and boot fetch (Rule 2 auto-add) — without this the REAL-01 force step would be inert in production despite passing unit tests
- [Phase WFH-06]: e2e force-directed test filters __mm_proj_node_positions() to its own 4 seeded fixture ids before asserting spacing — the accessor returns every node the projector has ever rendered, including editor.html's own boot-fetch real-scan population
- [Phase ?]: WFH-06-02: Task 1 scope narrowed to camera-distance test hook only — url_roots already wired by Wave 1
- [Phase ?]: WFH-06-02: frameCameraToRoot uses Math.max(12, boundingRadius * 2.2) as a framing-distance heuristic, distinct from the UI-SPEC-locked 0.6x/3.0x orbit bounds multipliers
- [Phase ?]: WFH-06-02: _applyCameraBounds runs unconditionally every animate() frame, no dead-band guard, matching projector.mjs's existing per-frame convention
- [Phase WFH-06]: Resolved window.__mm_rerender naming collision (EDIT-03 vs REAL-03) by combining both behaviors rather than overwriting the existing contract
- [Phase WFH-06]: Images driven via __mm_proj_image test hook only — production umap_canonical carries no image-URL field today; deferred to milestone-end real-stack probe
- [Phase ?]: project() extended additively with ndcZ rather than repurposing inFront, to avoid impacting the halo's existing ray-transport consumer
- [Phase ?]: REAL-04 link arrow is #ffd700 solid headless: stroke-width:2, no marker-end, no stroke-dasharray, hides via true NDC-z [-1,1] frustum test (not the weaker inFront near/far flag)
- [Phase ?]: WFH-07-01: Used a dedicated GET /concepts/{id}/next_rank route (not an extension of GET /concepts/{id}) per RESEARCH Open-Q2 resolution
- [Phase ?]: WFH-07-01: next_rank test monkeypatches routes._get_graph_editor to a GraphEditor bound to a temp_db_dir Kuzu connection rather than relying on the process-wide get_default_graph_editor() singleton
- [Phase WFH-07]: WFH-07-02: renderConceptPanel added as a new dispatch seam (not an overload of renderPanel's signature) to avoid breaking 18 existing callers that always pass a parsed tree node
- [Phase WFH-07]: WFH-07-02: magic_markdown_panel.mjs NOT modified — panelVDom/mount have no ConceptNode-shaped input path today; wiring renderConceptPanel into the DOM-vdom layer is left to the downstream plan consuming the next_rank endpoint
- [Phase ?]: Open-Q1 resolved: existing buildRegistry/refTarget live-resolution already satisfies N.6 duplicate-instance-proxy semantics — zero new proxy state built — Confirmed empirically via an in-place mutation probe test, not assumed from reading code
- [Phase ?]: classifyBraceStates keys resolved-external on refTarget string identity, not rendered-line text — A ref target's own identity line is never re-rendered as a sibling; only its children inline when expanded, so text-matching could never succeed
- [Phase ?]: object_exploration.spec.js drives fe/*.mjs modules via in-page dynamic import() against the live served origin rather than modifying demo.html or magic_markdown_panel.mjs — Keeps the e2e fully inside the plan's declared files_modified scope while still proving behavior against the real served module graph
- [Phase WFH-07]: N.13: DELETE_REF deletes the backing ConceptEdge (DELETE /api/concept_edges/{edge_id}) alongside the value-clear when g.edgeId is present, confirmed against object_exploration.md section N.13 wording
- [Phase WFH-07]: Inheritance side-effect runs inside the same edge-create request, fanned through apply_edge_create_lifecycle per inherited edge (Open-Q3: one request, one lifecycle event)
- [Phase WFH-07]: Added explicit source/target existence validation (400) to editor_link and create_concept_edge since graph_editor.create_concept_edge never raises for unknown node ids
- [Phase ?]: WFH-07-06: extended editor-link with inherit_types kwarg rather than adding a new ui-wire-link verb -- backend already exposes the drag-wire side-effect as a single EditorLinkRequest field (07-04)
- [Phase ?]: WFH-07-06: purge_workspace does not call ensure_foundation_fixtures() -- only the WS-connect bootstrap path does; scenario/probe must explicitly call POST /api/foundation/ensure after any purge needing the materialised python trees
- [Phase ?]: WFH-07-06: Task 4 (clean-GPU real-subsystem acceptance run) is a blocking-human checkpoint per D-01 -- not auto-executed; awaiting human approval
- [Phase ?]: radial (not raw Euclidean apex distance) is the apex-distance scalar guaranteed monotonic in similarity for cone-ray transport; along_ray is an orthogonal perpendicular offset
- [Phase ?]: Cone-ray composition built in world-space (apex -> nodeWorldPosition(id)) rather than screen-space, since projecting both endpoints through the same camera commutes with taking the ray in world space first -- keeps halo_cone.mjs THREE-free per D-04
- [Phase WFH-08]: STEP-01: signal_id resolved server-side from an ordered chunk-id list (_resolve_signal_id), never client-side, per D10
- [Phase WFH-08]: stepper.mjs receives flyToNode/highlightNode via injected deps (no static projector.mjs import) to keep the one-way (2D->3D) invariant structurally provable
- [Phase WFH-08]: WFH-08-04: Task 1 (probe_live_cone_transport.py) complete+committed (28128c7); Task 2 (D-01 real-subsystem acceptance) is a blocking-human main-context checkpoint, deliberately not executed by the auto executor
