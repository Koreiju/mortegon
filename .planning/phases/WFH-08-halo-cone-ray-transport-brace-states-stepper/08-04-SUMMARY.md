---
phase: WFH-08-halo-cone-ray-transport-brace-states-stepper
plan: 04
subsystem: testing
tags: [python, probe, acceptance, halo, cone-transport, triple-product, no-mocks]
status: in-progress

# Dependency graph
requires:
  - phase: WFH-08-halo-cone-ray-transport-brace-states-stepper
    plan: 02
    provides: "HALO-03 frontend cone-ray transport (halo_cone.mjs/projector.placeHaloCandidates) consuming backend transport.{similarity,radial,along_ray} verbatim; the GET /api/apparitions/{focal_id}?transport=1 backend contract this probe asserts against"
provides:
  - "scripts/probe_live_cone_transport.py — the D-01 real-subsystem cone-transport acceptance probe: real archive.org scan -> real /api/apparitions?transport=1&ray_project=1 retrieval -> assert_cone_monotonic (radial apex-distance monotonic in real triple-product similarity) -> assert_delete_transports_next (delete top candidate, assert next-most-similar occupies the vacated nearest-apex slot)"
  - "--self-test stub-mode behavioral gate (fully in-process, no live backend, no real GPU): proves assert_all_real fires on all_real:false, and both transport assertions raise on deliberately-broken fixtures and pass on valid ones"
affects: [WFH-08-04-Task-2, halo-cone-ray-transport-acceptance]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-01 real-subsystem acceptance probe pattern (mirrors probe_live_duckduckgo_walkthrough.py / probe_live_archive_scan.py): assert_all_real BEFORE anything, real Selenium scan -> WS-watch-to-done, real retrieval call, pure assertion helpers factored out so --self-test exercises the gate + assertion teeth without booting any real subsystem or contacting a live backend"
    - "radial (not combined radial+along_ray Euclidean distance) is the authoritative cone-apex-distance metric the monotonicity claim is asserted against — consistent with 08-02's frontend decision and routes.py's own 'most-similar nearest the apex' comment; combining both components is U-shaped/non-monotonic for the backend's (1-s)*R / s*R formula"

key-files:
  created:
    - scripts/probe_live_cone_transport.py
  modified: []

key-decisions:
  - "assert_cone_monotonic/assert_delete_transports_next sort candidates by transport.similarity descending and assert non-decreasing radial, rather than asserting an exact ordering match against the API's raw candidate-array order — decouples the assertion from any incidental pre-sort the backend may or may not apply"
  - "--self-test does not require a live backend at all (unlike probe_live_duckduckgo_walkthrough.py's --self-test, which still calls a real stub /api/subsystem_status) — all three behavioral checks (all_real gate, monotonic teeth, delete-transports teeth) are exercised against in-process crafted fixtures, since the plan's verification idiom explicitly preferred this ('fully in-process — preferred')"
  - "Focal selection for the real run uses the first chunk-search hit (chunk-node concept_id) as the 2D-query-element analog, and DELETE /api/concepts/{concept_id} (the existing route, 409-guarded against fixtures) to realize the 'delete the top result' step — no new backend route needed"

requirements-completed: []  # HALO-03 stays open until Task 2's human-gated real run is approved

# Metrics
duration: ~25min
completed: 2026-06-28
---

# Phase 8 Plan 04: D-01 Cone-Transport Acceptance Probe Summary

**New `scripts/probe_live_cone_transport.py` asserts real-retrieval cone-placement monotonicity and delete-transports-next against `/api/apparitions?transport=1`, with a fully in-process `--self-test` gate proving the assertion scaffold has teeth — Task 1 only; Task 2's real-GPU run is a blocking-human checkpoint, not yet executed.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 1 of 2 (Task 2 is `checkpoint:human-verify`, `autonomous: false` — intentionally not run by this executor)
- **Files modified:** 1 (new file)

## Accomplishments

- Authored `scripts/probe_live_cone_transport.py`, modeled on `probe_live_duckduckgo_walkthrough.py` (the `--self-test` pattern) and `probe_live_archive_scan.py` (the real Selenium-scan-to-`done` watcher + chunk-search flow).
- Real-run sequence implemented end-to-end: `/api/subsystem_status` all_real gate -> trigger archive.org scan -> watch WS to `done` -> `POST /api/chunk_search` to obtain real chunk-node ids -> `GET /api/apparitions/{focal_id}?transport=1&ray_project=1` -> assert cone monotonicity -> `DELETE /api/concepts/{concept_id}` on the top candidate -> re-query -> assert delete-transports-next.
- Three pure, directly-callable assertion helpers (`assert_all_real`, `assert_cone_monotonic`, `assert_delete_transports_next`) factored out of the step functions so `--self-test` can exercise every behavioral expectation without booting any real subsystem or contacting a live backend.
- `--self-test` exits 0, proving: (a) the all_real gate raises on a stub `all_real:false` status and passes on `all_real:true`; (b) `assert_cone_monotonic` raises on a deliberately non-monotonic candidate fixture (most-similar candidate placed farthest from the apex) and passes on a monotonic one; (c) `assert_delete_transports_next` raises when the wrong candidate occupies the vacated nearest-apex slot and passes on a correctly-promoted fixture.

## Task Commits

Each task was committed atomically:

1. **Task 1: Author probe_live_cone_transport.py — real-retrieval cone assertions + --self-test gate** - `28128c7` (feat)

**Task 2 (checkpoint:human-verify, blocking-human, autonomous:false):** NOT executed by this run — awaiting the main-context human-gated real-subsystem acceptance run. See `## CHECKPOINT` returned to the orchestrator for the exact steps.

## Files Created/Modified

- `scripts/probe_live_cone_transport.py` - the D-01 real-subsystem cone-transport acceptance probe (real run) plus its `--self-test` stub behavioral gate.

## Decisions Made

- `radial` (not combined `radial`+`along_ray` Euclidean apex distance) is the metric asserted monotonic in `transport.similarity` — matches 08-02's frontend resolution of the same question and `routes.py`'s own "most-similar nearest the apex" comment; the combined Euclidean distance is U-shaped/non-monotonic for the backend's `(1-s)*R`/`s*R` formula.
- `assert_cone_monotonic`/`assert_delete_transports_next` sort by `transport.similarity` and compare `radial` ordering rather than asserting an exact match against the raw API candidate-array order, decoupling the assertion from any incidental backend pre-sort.
- `--self-test` requires zero live backend contact (a stricter "fully in-process" interpretation of the plan's verification idiom, which explicitly preferred this over a stub-backend dependency) — all three behavioral expectations are proven against crafted in-process fixtures.
- Real-run focal selection uses the first real chunk-search hit (a real chunk-node `concept_id`) as the 2D-query-element analog; "delete the top result" is realized via the existing `DELETE /api/concepts/{concept_id}` route (already fixture-guarded with a 409), requiring no new backend surface.

## Deviations from Plan

None — Task 1 executed exactly as written. The plan's `<read_first>` line numbers for `probe_live_duckduckgo_walkthrough.py` (110-119, 222-234, 396-465) and the `08-PATTERNS.md` line range (228-238) were consulted; both matched the plan's description (the `assert_all_real`/teeth-checking helper shape and the real-scan-watch-to-`done` flow).

## Issues Encountered

### Task 2 — D-01 REAL-SUBSYSTEM ACCEPTANCE: **RESOLVED 2026-06-29** ✅

The follow-up landed both fixes below; the probe now exits 0 against the real stack
(`all_real:true`): real archive.org scan (160 chunks) → §8D.45 click-and-stick of the
top 5 retrieved `rendered_text` chunks into concept cards → `GET /api/apparitions/{focal}
?transport=1&ray_project=1` returns **4 real candidates with DISTINCT triple-product
scores** (0.6645 / 0.6379 / 0.5520 / 0.3286) → monotonic radial (0.0 / 1.60 / 6.77 /
20.22) → `DELETE /api/concepts/{top}` → re-query promotes the next-most-similar into the
apex (radial 0.0). Stub gates stay green: `--self-test` exit 0, full-smoke **93/93**,
`halo.spec.js -g "cone"` **3/3**, forward/inverse pytest 6/6, env-scenario offline 8/8.

**Two root causes, both fixed:**
1. **Backend (`apparition_service.py`)** — `apparitions_for_focal` `return []`-early when the
   focal had no ConceptIndex slot, *before* the `ray_project` augmentation. Now a non-concept
   (raw-manifold) focal still honors `ray_project` → `manifold_nearest`. Plus `manifold_nearest`
   resolves the `"" ↔ "_default"` default-workspace alias pair (the scan stores the frame under
   the literal `"_default"`; apparition callers default to `""`), so a frame keyed under one no
   longer silently empties the cone for a caller using the other.
2. **Probe flow (`probe_live_cone_transport.py`)** — was the dominant cause. The §O.18 halo opens
   on a stuck **concept** (the §8D.45 click-and-stick), NOT a raw chunk; `apparitions_for_focal`
   ranks the concept index (concept↔concept), so a raw chunk focal can never have concept
   candidates. The probe now sticks the real retrieved chunk `rendered_text` as concept cards
   (real nomic + tf-idf), opens the halo on one, and deletes a real (deletable) concept — exactly
   the outside-in lodestar. Hypothesis 2's "id-scheme mismatch" was a red herring (the
   `chunk_search` ids ARE in the `umap_canonical` coords); the real miss was the concept-slot
   early-return, confirmed live.

---
<details><summary>Original failure record (2026-06-27) — kept for the diagnostic trail</summary>

### Task 2 — D-01 REAL-SUBSYSTEM ACCEPTANCE: **FAILED** (run 2026-06-27, main context, clean-GPU)

The orchestrator ran the real acceptance from the main context (clean-GPU preflight → `python app.py`
→ `all_real:true`: gpt4all on CUDA, nomic, **real Selenium loaded** → `probe_live_cone_transport.py`).
The probe **FAILED at step 5**: after a successful real archive.org scan (103 real chunks streamed
to `done`, 5 real chunk ids from `chunk_search`), `GET /api/apparitions/{focal}?transport=1&ray_project=1`
returned **0 candidates** — so the cone had nothing to transport and monotonicity could not be asserted.

**Diagnosis (live, against the real backend — multiple focal variants all returned 0):**
- chunk-node focal (`c_c3360b9`, the probe's own choice) → 0; *without* `transport` → also 0.
- a freshly-created concept focal (`"university library"` with a real description) → 0.
- the pre-existing `RealEmbedProbe` concept focal → 0.
- after a successful `POST /api/recompute_umap` (status: success) → still 0.

**Root mechanism** (`apparition_service.py`): `apparitions_for_focal` scores candidates from the
**concept index** (concept↔concept triple-product). A fresh archive.org scan creates **chunks, not
concepts**, so the concept index is nearly empty → 0 concept candidates. The scanned chunks can only
enter the halo via `ray_project` → `manifold_nearest`, which the code itself documents returns
"**Empty when no layout frame / focal coords exist**" (apparition_service.py:462) — and it returned
empty here even for a scanned-chunk focal and even after a manifold rebuild.

**Two open hypotheses (need investigation — NOT resolved this run):**
1. **Probe-flow incomplete (likely partial cause).** The §8D.45 lodestar flow is scan → **click-and-stick
   a retrieved chunk into a concept card** (which gives it concept-index presence + manifold coords) →
   *then* the halo fires on that stuck card. The probe skipped the click-and-stick and used a raw
   chunk id as the focal, so there was never a valid manifold-placed concept focal.
2. **Backend `manifold_nearest` gap (also implicated).** A *scanned chunk* focal — which IS in the
   `umap_canonical` manifold the scan built — still produced an empty `manifold_nearest` even after
   `recompute_umap`, suggesting an id-scheme mismatch (chunk_search ids vs layout-frame ids) or a
   layout-frame-availability/wiring issue between LayoutService and apparition_service.

**Impact:** HALO-03's REAL-SUBSYSTEM acceptance (D-01) is **UNMET** and stays open. Everything else in
Phase 8 is green: HALO-04 brace render (08-01), the HALO-03 *frontend* cone placement (08-02, stub e2e
3/3 + halo_cone 5/5), STEP-01 (08-03, pytest 4/4 + node + full-smoke 93/93 + stepper e2e), and this
probe's `--self-test` behavioral gate. The gap is specifically the real backend retrieval that feeds
the cone — exactly what D-01 real-inline acceptance exists to surface.

**Recommended next step (a focused follow-up phase/debug, not a quick inline fix):** decide whether the
cone transports stuck-concept apparitions (then the probe must click-and-stick a chunk first) and/or fix
`manifold_nearest` to resolve a scanned-chunk focal's layout coords; then re-run `probe_live_cone_transport.py`.

</details>

## User Setup Required

None - no external service configuration required. (Task 2 itself requires the standing real-subsystem GPU/Selenium environment per STATE.md's existing env discipline, not a new setup.)

## Known Stubs

None — `probe_live_cone_transport.py` is a test/acceptance script, not application code; it contains no hardcoded empty values flowing into UI rendering, no placeholder text, and no unwired data sources. Its real-run path performs zero stub fallback per the no-mocks contract (assert_all_real raises rather than degrading).

## Threat Flags

None — the probe is a read path over the EXISTING `/api/apparitions?transport=1` route plus the EXISTING `DELETE /api/concepts/{concept_id}` route (both pre-existing, the latter already fixture-guarded). No new endpoints, no new auth paths, no new schema. T-08-09/T-08-10 (the plan's own threat register) are the ones this probe itself mitigates via `--self-test`'s teeth checks and the `assert_all_real` gate.

## Next Phase Readiness

Task 1's artifact (`scripts/probe_live_cone_transport.py`) is complete, committed, and self-test-verified. **Task 2 is a blocking-human, main-context-only checkpoint (`autonomous: false`) and was deliberately NOT run by this executor** — a wedged CUDA/Selenium boot hangs an agent, per the plan's own `<action>` text and the standing Phase 7 D-01 precedent (07-06 Task 4). See the `## CHECKPOINT` returned to the orchestrator for the exact main-context steps (clean-GPU preflight, real backend boot on :8080, fast-gate re-check, the real probe run, teardown).

HALO-03 (the requirement this plan targets) stays **not yet marked complete** in REQUIREMENTS.md/ROADMAP.md until Task 2 is approved — `requirements-completed` is intentionally empty in this summary's frontmatter.

## Self-Check: PASSED

- FOUND: scripts/probe_live_cone_transport.py
- FOUND commit 28128c7 (Task 1: probe_live_cone_transport.py)
- VERIFIED: `python -c "import ast; ast.parse(open('scripts/probe_live_cone_transport.py').read())"` — clean parse.
- VERIFIED: `WFH_FAKE_SLM=1 WFH_FAKE_EMBEDDER=1 NO_WEBDRIVER=1 python scripts/probe_live_cone_transport.py --self-test --backend http://127.0.0.1:8080` — exits 0, all behavioral expectations held (all_real gate fires; both transport assertions have teeth).
