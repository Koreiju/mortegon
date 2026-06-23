---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Design Completeness
current_phase: 6
current_phase_name: 3D Real Register in the Served Slate
status: verifying
stopped_at: Completed WFH-06-04-PLAN.md
last_updated: "2026-06-23T05:10:10.597Z"
progress:
  total_phases: 9
  completed_phases: 1
  total_plans: 4
  completed_plans: 4
  percent: 11
---

# Project State

## Project Reference

See: .planning/PROJECT.md · v1.0 archive: .planning/milestones/1.0-ROADMAP.md · audit: .planning/DESIGN_COVERAGE_AUDIT.md

**Core value (v3):** Every binding design requirement (§A–§V of `docs/USER_REQUIREMENTS_VERBATIM.md`) is realized in the **served `/` black-slate frontend** and verified against real subsystems — not split between the new `fe/` surface and the legacy `cp/` one. The four lodestar use cases stay green throughout (`all_real:true`).
**Current focus:** Phase 6 — 3D Real Register in the Served Slate

## Current Position

Phase: 6 (3D Real Register in the Served Slate) — EXECUTING
Plan: 4 of 4
Status: Phase complete — ready for verification
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

**Resume file:** None

Last session: 2026-06-23T05:10:10.591Z
Stopped at: Completed WFH-06-04-PLAN.md
Next: `/gsd-autonomous` (discovers Phase 6) — discuss → plan → execute, full real-stack inline.

## Performance Metrics

| Phase | Plan | Duration | Notes |
|-------|------|----------|-------|
| Phase WFH-06 P01 | 95min | 3 tasks | 4 files |
| Phase WFH-06 P02 | 25min | 3 tasks | 3 files |
| Phase WFH-06 P03 | 70min | 3 tasks | 3 files |
| Phase WFH-06 P04 | 45min | 3 tasks | 3 files |

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
