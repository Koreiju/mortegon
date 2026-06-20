# Roadmap: web_fiber_haptics (Mortegon)

## Milestones

- ✅ **v1.0 Real-Stack Acceptance** — Phases 1–5 (shipped 2026-06-20) — [archive](milestones/1.0-ROADMAP.md)
- 🚧 **v2.0 Autonomy Hardening & Maintainability** — Phases 6–8 (in progress)

v1 hardened the honest baseline and finished-and-verified the §T/§U/§V/§R frontend
surfaces (Milkdown edit layer, HTML-dedup halo render, 6D-UMAP/HSV projector, live
signal/pattern), proving all four lodestar use cases against real subsystems
(`all_real: true`; full-smoke 92/92 both modes; e2e 26/0). v2 makes the project
**turnkey for GSD autonomous build/test**: reliable *unattended* real-stack
verification, and agent-friendly (de-monolithed) code.

## Phases

- [x] **Phase 1: Honest Baseline** *(v1.0 — shipped 2026-06-15)* - No-mocks SLM 503, three fixtures, forbidden/legacy-code deletion, dependency hygiene.
- [x] **Phase 2: Black-Slate Field Editing** *(v1.0 — shipped 2026-06-18, PR #1)* - Milkdown controlled-view edit layer (EDIT-01/02/03).
- [x] **Phase 3: HTML Dedup + Halo Retrieval Render** *(v1.0 — shipped 2026-06-18)* - Content-tree corpus-clean + collapsed-node apparition halo.
- [x] **Phase 4: Live Layout, Signal & Pattern** *(v1.0 — shipped 2026-06-18)* - 6D-UMAP/HSV projector + one-signal rollout + live pattern_map.
- [x] **Phase 5: Three-Register Synthesis & Live Acceptance** *(v1.0 — shipped 2026-06-19)* - REG-01 + the four lodestar real-stack probes.
- [ ] **Phase 6: Autonomy Hardening** *(v2.0)* - Make unattended real-stack verification reliable: fix the `--real` harness backend-boot + clean-GPU preflight; harden the GPT4All Embed4All Windows native crash.
- [ ] **Phase 7: Maintainability** *(v2.0)* - De-monolith for surgical agent edits: split `routes.py` by register; decompose `sim_frontend.py` by action category.
- [ ] **Phase 8: Performance** *(v2.0)* - Incremental joint-UMAP refit during streaming chunk arrival (currently scan-end-only).

## Phase Details

### Phase 1: Honest Baseline

**Goal**: The brownfield baseline tells the truth — no quiet stub substitution, exactly three fixtures, no forbidden/legacy code, unambiguous launch/dependency story.
**Requirements**: REL-01, REL-02, FIX-01, FIX-02, HYG-01, HYG-02 — all DONE (v1.0)
**Status**: ✅ Complete (2026-06-15). Detail: `milestones/1.0-ROADMAP.md`.

### Phase 2: Black-Slate Field Editing

**Goal**: A user can edit any field of the black-slate panel in place; every mutation commits through the one lifecycle dispatcher with the frontend holding no authoritative state.
**Requirements**: EDIT-01, EDIT-02, EDIT-03 — all DONE (v1.0; Milkdown controlled view)
**Status**: ✅ Complete (2026-06-18, PR #1). Detail: `milestones/1.0-ROADMAP.md`.

### Phase 3: HTML Dedup + Halo Retrieval Render

**Goal**: A scanned HTML chunk renders as a clean deduplicated content-tree; clicking a collapsed circular node fires a name-only apparition halo ranked by the triple product.
**Requirements**: HTML-01, HALO-01, HALO-02 — all DONE (v1.0)
**Status**: ✅ Complete (2026-06-18). Detail: `milestones/1.0-ROADMAP.md`.

### Phase 4: Live Layout, Signal & Pattern

**Goal**: During a live scan the workspace renders a 6D-UMAP manifold with camera-coupled HSV, advances iterables one signal at a time, and materialises a live `pattern_map` node.
**Requirements**: UMAP-01, SIG-01, PAT-01 — all DONE (v1.0)
**Status**: ✅ Complete (2026-06-18). Detail: `milestones/1.0-ROADMAP.md`.

### Phase 5: Three-Register Synthesis & Live Acceptance

**Goal**: The Real/Imaginary/Symbolic registers form one compose-compile-perimeter loop runnable both ways, and all four lodestar use cases pass against real subsystems.
**Requirements**: REG-01, ACC-01, ACC-02 — all DONE (v1.0; `all_real:true`, full-smoke 92/92 both modes)
**Status**: ✅ Complete (2026-06-19). Detail: `milestones/1.0-ROADMAP.md`.

### Phase 6: Autonomy Hardening

**Goal**: `/gsd-autonomous` can verify against the real stack UNATTENDED. The `run_full_stack_tests.py --real` backend-boot reliably comes up `all_real:true` (today its Selenium health flakes → `all_real:false`); the GPT4All Embed4All Windows native crash is hardened beyond the per-model RLock.
**Depends on**: Phase 5
**Requirements**: HARNESS-01, PERF-02
**Success Criteria** (what must be TRUE):
  1. `npm run test:all:real` brings up `all_real:true` through the harness and runs real-mode `full-smoke` 92/92 — not only against a manually-booted `python -m backend.main`.
  2. The `--real` boot has a WebDriver-health retry + a preflight that requires a clean GPU (≈0 MiB VRAM / 0 stray python+firefox), clears `:8080` TIME_WAIT, and resolves Kuzu file-lock contention; it never silently degrades to `all_real:false`.
  3. `probe_no_mocks.py` + the four lodestar `probe_live_*.py` run repeatably on a clean GPU with no GPT4All `Embed4All` access-violation under sustained concurrency.
**Plans**: TBD

### Phase 7: Maintainability

**Goal**: De-monolith so agents (and humans) edit surgically. Split `backend/api/routes.py` (~5,425 lines) by register (scan/retrieval/concept/agent/maintenance); decompose `scripts/sim_frontend.py` (~9,524 lines) by action category.
**Depends on**: Phase 6
**Requirements**: MAINT-01, MAINT-02
**Success Criteria** (what must be TRUE):
  1. `routes.py` is split into `backend/api/` submodules with the route surface + behaviour unchanged; `full-smoke` + e2e stay green.
  2. `sim_frontend.py` is decomposed so a change to one action category does not risk the whole harness; `env-scenario --name all` stays green.
  3. No resulting source file in the split surfaces exceeds ~2,000 lines.
**Plans**: TBD

### Phase 8: Performance

**Goal**: Incremental joint-UMAP refit during streaming chunk arrival (currently scan-end-only), so the 3D manifold updates live as chunks land.
**Depends on**: Phase 7
**Requirements**: PERF-01
**Success Criteria** (what must be TRUE):
  1. `umap_canonical` frames emit incrementally mid-scan (not only at scan-end joint fit).
  2. `full-smoke` stays green; a probe asserts the mid-scan refit produces comparable coords.
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Honest Baseline | v1.0 | direct | Complete | 2026-06-15 |
| 2. Black-Slate Field Editing | v1.0 | direct | Complete | 2026-06-18 |
| 3. HTML Dedup + Halo | v1.0 | direct | Complete | 2026-06-18 |
| 4. Live Layout/Signal/Pattern | v1.0 | direct | Complete | 2026-06-18 |
| 5. Three-Register Synthesis | v1.0 | direct | Complete | 2026-06-19 |
| 6. Autonomy Hardening | v2.0 | 0/TBD | Not started | - |
| 7. Maintainability | v2.0 | 0/TBD | Not started | - |
| 8. Performance | v2.0 | 0/TBD | Not started | - |

---
*v1.0 archived 2026-06-20. v2.0 roadmap created 2026-06-20.*
