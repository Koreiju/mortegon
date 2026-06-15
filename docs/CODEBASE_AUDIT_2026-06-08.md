# Codebase Audit — 2026-06-08 (fresh, supersedes the historical `CODEBASE_GAP_ANALYSIS.md`)

> **Status: active.** This is the §2.9-step-3 / §O.17 fresh audit. `CODEBASE_GAP_ANALYSIS.md`
> is historical (it audited the now-discarded code). This file audits the **current** tree
> (`backend/` + `backend/static/js/cp/*.js`) against the source-of-truth chain:
> `USER_REQUIREMENTS_VERBATIM.md` (§A–§Q) → `DOMAIN_MODEL.md` (§0–§21) → `FRONTEND_REDESIGN.md`.
>
> **Method.** Every finding is grounded in (a) a verbatim/§ anchor, (b) concrete code evidence
> (`file:line`), (c) a **confidence** (HIGH = read in code; MED = partially traced; LOW = inferred),
> and (d) a **severity**. Per §A.1 the bar is *correctness over comprehensiveness* — divergences are
> stated precisely, present-and-correct items are recorded too so the picture is honest both ways.
>
> **Not yet done in this pass:** an empirical full-stack REPL run (`env-scenario full-smoke` in
> stub + real modes, the probes). The doc-layer claims of "83 scenarios green / `all_real: true`
> realised" are **unverified at audit time** and are themselves listed as a gap (§E) per the §A.4
> doctrine that doc claims are not proof.

---

## 0 — Honest executive summary

The codebase is **much more built-out than a naive read of the design churn would suggest.** The
backend implements, at the service/route level, the large majority of the §M–§Q additions:

- All **four** foundation fixtures incl. `Editor` (`foundation_fixtures.py`) — §18.27 ✓
- The **full §10.5 mirror-field roster** incl. the "planned" ones: `signal_stream`, `rollout_state`,
  `node_fold_state`, `dominance_collapse`, `pin_chrome`, `latch_state`, `viewport_visible_rows`,
  `autocomplete_state`, `compile_expansions`, `halo_focus` (`ui_state_service.py`) ✓
- `rank_dominance.py` with real dominated-set reachability (§6.6.5 / §8.1.2) ✓
- `layout_service.py` with 6-vector coords, perimeter rescale, bisector node, UMAP-independent
  link network (§6.1 / §6.6.1 / §6.6.4) ✓
- Multi-semantic-frequency band scoring in `apparition_service.py` (§8.1.1) ✓
- Halo rendering + apparition phantoms on the frontend (`concept_graph.js`) ✓
- Timed-scan `duration_s` port plumbed end-to-end (§15.10 / Q.2) ✓
- SLM = Nous-Hermes-2-DPO with a loud anti-Llama guard (`slm_client.py`) ✓

The **genuine gaps** cluster in five areas, in rough priority order:

1. **The layout authority is `TruncatedSVD`, not UMAP** — a direct doc↔code contradiction on the
   single most load-bearing visual commitment (§A.1 below). **This is the headline finding.**
2. **Forbidden-concept residue in live + test + doc surfaces** — Fibonacci-sphere layout
   (`ontology/layout_generator.py`) is live in the scanner; the frontend transient placeholder is
   concentric-shell Fibonacci, not hash-radial; README + tests still celebrate "Concentric Sphere
   layout / LAYER_SEPARATION" (§A.3 / K.1 demand hard deletion).
3. **A mandated acceptance artifact is missing** — `probe_live_scan_with_cleanup.py` (§16.5).
4. **Frontend streaming divergences** — UMAP fires scan-end-only, not incrementally mid-scan
   (§5.4 / §16.5).
5. **The empirical-verification gap** — the "green/all-real" claims are unproven at audit time
   (§A.4 / §0 mandate).

The brutally honest one-liner: **the plumbing exists; the load-bearing layout math is the wrong
algorithm, forbidden concepts were never fully deleted, and nobody has proven the all-real claims by
running them.**

---

## A — CRITICAL correctness gaps (doc↔code contradictions on load-bearing commitments)

### A.1 — Layout is TruncatedSVD, not UMAP  ·  HIGH confidence · HIGH severity

- **Requirement:** verbatim §B.2 ("a 3D **UMAP** re-mapper for the new, full chunk space"; "the
  recompute **UMAP** button function"); DOMAIN_MODEL §6.1 "UMAP-linear-radial force-directed hybrid",
  §2.3 "UMAP joint refit", §8.2.1.2 "6D UMAP"; forbidden-concepts mandates neighbour-preservation.
- **Code reality:** `layout_service.py:413` `svd = TruncatedSVD(n_components=n_comp, …)`;
  `routes.py:1511` `from sklearn.decomposition import TruncatedSVD`. The module docstring itself
  admits "UMAP-**like** projection (TruncatedSVD)" (`layout_service.py:3`, `:372`).
- **Why it matters:** TruncatedSVD is a linear projection (PCA-on-TF-IDF); it does **not** preserve
  local neighbourhoods. The entire design rests on UMAP's neighbour-preservation: §18.17 ("outliers
  must be included in the geometry") is *fixed by UMAP's joint fit*; §8.2.1.1 ray-projection assumes
  "the focal's manifold-nearest chunks"; §8.2.1.2 HSV is "determined by UMAP from the chunk's TF-IDF
  vector exactly the same way the position triplet is." SVD gives content-dissimilar chunks adjacent
  positions and vice-versa — the comparison-surface reading of §6.6 is unreliable.
- **`umap-learn` is installed** (`import umap` succeeds in this env), so this is not a dependency
  blocker — it is an unfinished swap.
- **Fix:** replace the SVD call in `LayoutService._project` (and the legacy `routes.py::recompute_umap`)
  with `umap.UMAP(n_components=6, …)` over the normalized TF-IDF matrix; keep SVD only as an
  **explicitly-logged degraded fallback** when `umap` import fails (layout fallback is more defensible
  than the §13.4 SLM no-fallback rule, but it must be loud, not silent). Re-fit must stay incremental-
  capable. **Either implement UMAP or correct every doc that says "UMAP" — the two must agree (§A.1).**

### A.2 — Frontend UMAP refit is scan-end-only, not incremental  ·  HIGH · MED severity

- **Requirement:** §5.4 step 2 "`umap_canonical` frames arrive **mid-scan and at scan-end** (§16.5
  requires incremental refits, not scan-end-only)"; §16.5 "multiple `umap_canonical` frames arriving
  as the LayoutFrame refits incrementally during the scan"; §18.29 (pattern_map must live-update).
- **Code reality:** `scanner.js:304-313` — "Incremental UMAP is deliberately NOT triggered here … UMAP
  now fires once at the 'done' event below; until then the hash-based concentric-sphere layout is the
  authoritative arrangement." This is an explicit decision to defer all UMAP to scan-end.
- **Why it matters:** the §16.5 cleanup probe asserts mid-scan refits; the live "settling" motion the
  design sells (§5.4) is absent — chunks sit in Fibonacci positions until the scan ends, then snap once.
- **Fix:** re-introduce throttled incremental refits (the comment says they were removed for jank +
  tiny-doc SVD noise — both are mitigated by real UMAP + a min-chunk gate + interruptible retarget
  tween, §9.2). Lower priority than A.1; partly *caused* by A.1 (SVD on a tiny doc count is noisy).

---

## B — Forbidden-concept residue (§A.3 / §K demand hard deletion, not lingering)

### B.1 — Fibonacci-sphere layout is LIVE in the scanner pipeline  ·  HIGH · MED severity

- **Requirement:** §K.1 / §A.3 "remove concentric sphere **everywhere**"; §18.2; forbidden-concepts.
- **Code reality:** `ontology/layout_generator.py` is a Fibonacci-sphere radial-tree generator
  (`_generate_fibonacci_sphere`, `apply_radial_tree_layout`) and is **imported live** by
  `mapper/mapper.py:64,415` and `dom_deep_serializer.py:14,308`. `test_layout_generator.py` asserts
  children sit "on the same Fibonacci sphere radius."
- **Nuance (avoid over-claim):** these coords appear to be DOM-snapshot tree coords (mapper-internal),
  likely superseded by `LayoutService` 6-vectors before the projector — but they are still active code
  computing a forbidden layout, with green tests cementing it.
- **Fix:** confirm whether mapper's radial-tree coords reach the projector; if vestigial, delete the
  module + test; if used, replace with the §6.1 hash-radial placeholder. Either way the celebratory
  test must go.

### B.2 — Frontend transient placeholder is concentric-shell Fibonacci, not hash-radial  ·  HIGH · MED

- **Requirement:** §6.1 "Preliminary radial … placed at **`hash(chunk_id)` unit-direction** from URL
  root, distance `R·(1+n/k)`"; §18.2 "the hash-direction unit-vector placeholder … is the **only**
  surviving Fibonacci-style angular sampling."
- **Code reality:** `cp/layout.js` `fibSphereUnit` / `docShellRadius` / `clusterRadius` are the
  preliminary `layOutNode` path; `scanner.js:310` calls the "hash-based **concentric-sphere** layout"
  the "authoritative arrangement" until scan-end; `chunk_projector.js:65-69` exports
  `fibSphereUnit`/`docShellRadius` as statics; `routes.py:1415-1433` comments describe layout as
  "Fibonacci-style hash placement on **two concentric shells** … lives ENTIRELY on the frontend."
- **Why it matters:** the design permits a hash-**direction** + radial-distance transient, but the
  code uses Fibonacci-sphere distribution + concentric **shells** — the exact forbidden form, and
  `routes.py` declares the frontend Fibonacci the layout authority (contradicting §2.1 "backend
  computes layout").
- **Fix:** replace the preliminary placement with pure `hash(chunk_id)` unit-direction + `R·(1+n/k)`
  radial distance; delete the `fibSphereUnit`/`docShellRadius`/`clusterRadius` exports; rewrite the
  `routes.py` comment to stop declaring the frontend the layout authority.

### B.3 — README + tests + comments still celebrate concentric layout  ·  HIGH · LOW severity (doc), trivial fix

- **Code reality:** `README.md` "Testing Protocol" — "validation confirming dot-product proximities
  inside the **Concentric Sphere** layout functions. Asserts spherical layers rigidly match specific
  `LAYER_SEPARATION` constants." This is stale + contradicts the forbidden list the *same README* later
  prints.
- **Fix:** rewrite the README testing section to describe the UMAP-linear-radial layout + the real
  test surface; remove `LAYER_SEPARATION`/concentric language.

### B.4 — Dead forbidden-adjacent modules still present  ·  HIGH · LOW severity

- `ontology/hyperbolic_layout.py`, `ontology/gyrovector.py`, `ontology/analytics_models.py` exist with
  tests but are **not** imported in live paths (only self + tests). §K.2 targets the *retrieval*
  graph-analytics framework; these are layout/analytics overhang.
- **Note (NOT a violation):** `node_registry.py` uses `wl_hash` for **stable-id/change-detection**
  (MUTATED detection), not retrieval ranking — this is fine; §K.2 forbids wl_hash as a *retrieval
  feature*, not as an identity key.
- **Fix:** delete the dead modules + their tests (low risk; reduces forbidden-concept surface).

---

## C — Missing mandated artifacts

### C.1 — `probe_live_scan_with_cleanup.py` is absent  ·  HIGH · MED-HIGH severity

- **Requirement:** §16.5 names it the mandatory live-scan + DB-cleanup acceptance probe;
  `env_scenarios.md` §1.4 "MUST pass on every CI run gated by `all_real: true`"; §20.3 lists it
  (planned). The cleanup *repeatability* contract (purge → re-scan → identical rebuild; on-disk Kuzu
  shrinks back within 10%) is tested **nowhere**.
- **Code reality:** `scripts/` has `probe_live_archive_scan.py` (one scan) but no cleanup/repeatability
  probe. CLAUDE.md claims `live-scan-real-with-cleanup` is "realised" — **unsubstantiated** (no file).
- **Fix:** author `scripts/probe_live_scan_with_cleanup.py` per the §16.5 assertion catalogue (fresh
  boot → assert `all_real` → purge → baseline → scan → assert workspace-WS chunk routing + incremental
  umap + non-empty golden trio → `Database.search` hit → purge → assert full cleanup → re-scan →
  identical rebuild). Wire as env-scenario `live-scan-real-with-cleanup`.

---

## D — Other divergences (MED/LOW, partially traced)

- **D.1 — Compile syntax coverage (MED).** `compile_pipeline.compute_rendering_tree` + cypher detection
  handle JSON / indented-tree / plain-text / cypher (§7.1 steps 1–5). **HTML element-tree** decomposition
  (§7.1 "HTML element trees") is not clearly present in the backend tree-printer — needs a targeted
  read of `_tree_print` + the data parser. Confidence MED.
- **D.2 — Real-UMAP HSV (depends on A.1).** §8.2.1.2 HSV is "jointly the UMAP fit." With SVD, coords[3:6]
  are SVD components 3–5, not UMAP HSV — so the HSV semantics are SVD-derived. Fixed transitively by A.1.
- **D.3 — `routes.py` is 5272 lines.** Not a design violation per se, but it concentrates §10/§14 plus
  layout/scan/compile glue in one module; `code_architecture` envisions service decomposition. LOW.

---

## H — The Card ⇄ Computation-Graph update (§4 / §7.3 / §7.3.4 / §M / §N / §O / §P)

This is the heart of the Imaginary register and was under-covered in the first pass (operator
flagged it). Audited precisely below. **Much of it is implemented** — credit first, then the real gaps.

### H.0 — Verified PRESENT (do not "fix")

- **Plus-sign field-tree growth** `+→` / `+↓` (§4.6) — `concept_graph.js:1621-1659`.
- **Click-to-edit pure-print field-tree** (§4.1.1) — `concept_graph.js:1826`; JSON→tab-tree print at `:1536`.
- **Right-click `{ref}` inline rank-1 node-fold** (§7.3.4 / §O.1) → `/api/ui/node_fold` — `concept_graph.js:1855-1894`; backend `set_node_fold` + `node_fold_state` mirror (`ui_state_service.py:798`).
- **Double-left-click → panel↔graph compile** (§7.3.4) — `concept_graph.js:2192-2196` (fires the Compile path).
- **Double-right-click delete** (§N.13) — `concept_graph.js:2118-2122`.
- **Port-drag edge wiring** (§N.4 analogue) — `concept_graph.js:2224-2246` (`_beginPortDrag`).
- **Compile-expand/collapse mirror** (§7.3) — `ui_state_service.py:404/426`, routes `:3723/:3737`.
- **JSON→child-card decomposition** with `{slug}` round-trip — `concept_graph.js:3150-3210` (`_decomposeJsonValue`).
- **Generalized rank-dominance collapse** (§6.6.5 / §7.3.5) — frontend `interaction.js:320-370`
  calls `/api/ui/dominance_collapse`; `animation.js:599` + `scanner.js:470` honour the isolate;
  backend route `:4278` + `rank_dominance.py`. **This is wired end-to-end** (I had it as unverified).

### H.1 — The reservoir compute-graph projector overlay is BACKEND-ONLY  ·  HIGH · HIGH severity

- **Requirement:** §6.6.4 / §P.8–P.10 — a compiled computation graph appears in the **3D projector** as
  a single **bisector node** on the line between the input-UMAP centroid and the dynamically-updated
  output centroid; **clicking it opens/closes the graph in the 2D editor** (P.10); a **UMAP-independent
  link network** ties root-urls → chunk-samples and inputs/readouts → the graph node (P.8/P.9); the
  **readout perimeter** streams **async per-node deltas** (§7.8.2/§7.8.3). §18.34 is its regression.
- **Code reality:** the **backend is built** — `POST /api/compute_graph/layout` (`routes.py:4128`),
  `place_compute_graph_node` / `compute_projector_links` / `readout_nodes` / `stream_readout_deltas`
  (`layout_service.py`). **The frontend never calls `/api/compute_graph/layout` and renders no bisector
  node** — the only frontend reference is a *comment* (`scanner.js:481`). So the computation graph's
  entire 3D representation (the node you click to open/close it, the link circuit, the perimeter) is
  invisible. `probe_reservoir_rollout.py` exercises the backend overlay over HTTP, but no GUI surface
  consumes it.
- **Fix:** frontend work in `chunk_projector.js`/`scanner.js`/`interaction.js`: on compile of a graph,
  `POST /api/compute_graph/layout`, instantiate the bisector node mesh at the returned coords, draw the
  link network (separate from the UMAP `InstancedMesh`), wire its click to `ui-compile-expand` of the
  2D graph, and apply readout-delta frames to slide the node + perimeter. **Needs browser runtime
  verification** — defer to the post-G1 verified pass; do not build blind.

### H.2 — Frontend compile decomposition is JSON-only, not syntax-agnostic  ·  HIGH · MED-HIGH severity

- **Requirement:** §7.1 / §18.15 — "one recursive descent … JSON, bracketed lists, indented trees,
  HTML element trees, plain text — the user never thinks about syntax." §4.2.2 FieldTree "syntax
  strategies behind one interface."
- **Code reality:** `_decomposeJsonValue` (`concept_graph.js:3186`) bails unless the value starts with
  `{` or `[` ("If the value is plain text / HTML / not valid JSON → leave it alone"). So an indented
  field-tree, an HTML element tree, or a plain-text block does **not** decompose into child cards. The
  backend `compute_rendering_tree` does syntax-stripped *rendering* (`compile_pipeline.py:332`), but the
  *decompose-into-graph-children* on the frontend is JSON-gated — exactly the §18.15 "compile doesn't
  decompose recursively independent of syntax" bug the user reported.
- **Fix:** route decomposition through the §4.2.2 strategy set (indent-tree / HTML / list / plain),
  symmetric with the backend tree parse, so the panel→subgraph flip is syntax-agnostic. Frontend logic
  + runtime verification.

### H.3 — Ray-constrained placement is CORRECT; only stale Fibonacci naming/comments remain  ·  HIGH · LOW severity

- **Requirement:** §K.5 / §18.2 / §7.3.2 — ray-constrained placement around the focal, not concentric
  rings.
- **Code reality (CORRECTED on closer read):** `addConceptNode` actually places via
  `this._rayConstrainedPosition({anchorId})` (`concept_graph.js:1287`) — the **prescribed §7.3.2
  algorithm by name**. The "Fibonacci-ring placement" docstring (`:1280`), the local var `fib`, and the
  "golden-angle layout … per-anchor ring position" comment (`:3206`) are **stale Fibonacci
  comments/naming around already-ray-constrained behaviour** — forbidden-concept *doc* residue (B.3
  family), **not** a live ring layout. (One verification TODO: read `_rayConstrainedPosition`'s body to
  confirm it is genuinely radial-DOF, not a ring under a misleading name.)
- **Fix:** rename `fib`→`pos`, replace the Fibonacci/golden-angle comments with §7.3.2 language. Trivial,
  doc-residue only. **DONE 2026-06-08** — verified `_rayConstrainedPosition` is a genuine radial fan of
  8 rays (not a ring); renamed the var and rewrote both stale comments (`addConceptNode` docstring +
  the `_decomposeJsonValue` child-spawn comment) to §7.3.2/§K.5 language.

### H.4 — Compiled-graph child renders FULL-PANEL, not value-only  ·  HIGH · MED severity

- **Requirement:** §4.2.4 / §4.5 / §8D.2.2.1 — the **compiled-graph child shows VALUE ONLY** (name
  implicit from position; stringless edges; form-fit). The halo phantom shows NAME only. "Mode is a
  parameter, never a fork" (§4.1 / §18.11).
- **Code reality (CONFIRMED):** `_decomposeJsonValue` spawns children via `addConceptNode`
  (`:3205`), and `addConceptNode` → `_createConceptCard` builds the **same full concept card** as any
  node (header, chrome, all rows) — there is **no `child`/value-only render mode**. So compiled-graph
  children render as full named panels, violating the compact-representation standard (§4.5). (The halo
  *phantom* name-only render does exist separately via `_renderApparitionHalo`, so the gap is
  specifically the **value-only child** mode.)
- **Fix:** add a `child` render mode (value-only, name-from-position, stringless edges) to the single
  card builder as a *parameter*, not a second code path (§18.11). Frontend + runtime verification.

### H.5 — Card-compute-graph summary

The **2D editor gesture grammar is largely present** (plus-signs, click-to-edit, node-fold, compile,
delete, wiring, dominance-collapse, **ray-constrained placement**). The card↔computation-graph **real
gaps** are: (H.1) the **3D projector representation of the compute graph is backend-only / unrendered**
— the single biggest miss (the P.10 bisector node + UMAP-independent link network + async readout
perimeter); (H.2) compile decomposition is **JSON-only**, not syntax-agnostic (§18.15); (H.4) compiled
children render **full-panel, not value-only** (§4.5/§8D.2.2.1). H.3 turned out to be **only stale
Fibonacci comments around already-correct ray-constrained code** — fixed this pass. H.1/H.2/H.4 are
frontend-side and runtime-gated — they join G4/G6 in the post-verification pass.

---

## E — The empirical-verification gap (a first-class finding per §A.4 / §0)

The design's own doctrine (§A.4: "a screenshot is not feature proof"; §0: "a green stub run is necessary
but never sufficient … every commit must also be green against the four real subsystems with
`all_real: true`") means **doc claims of completeness are not evidence.** At audit time the following are
**asserted by docs but unverified by this pass:**

- `env-scenario full-smoke` green in **stub** mode (83 scenarios).
- `env-scenario full-smoke` green in **real** mode with `all_real: true`.
- The five `probe_live_*.py` pass end-to-end against the real stack.
- `/api/subsystem_status` reports `all_real: true` on a real boot.

**This is the highest-leverage next action**: run the offline self-checks + stub full-smoke (fast,
no GPU/network) to get ground truth, then a real-stack probe. Until then, the "realised/green" markers
across the docs are claims, not proof.

---

## F — Verified PRESENT-and-correct (honest credit; do not "fix")

- Four fixtures incl. Editor + undeletable guard (`foundation_fixtures.py`, §9.5/§18.22/§18.27).
- Full mirror-field roster incl. signal_stream/rollout/node_fold/dominance (`ui_state_service.py`, §10.5).
- `rank_dominance.py` dominated-set reachability (§6.6.5/§8.1.2).
- Bisector node + UMAP-independent link network + perimeter rescale (`layout_service.py`, §6.6.1/§6.6.4).
- Multi-frequency band scoring (`apparition_service.py`, §8.1.1).
- Halo radiation + phantoms, forbidden-spiral-avoiding radial fan (`concept_graph.js`, §8.2).
- `duration_s` timed-scan port plumbed (`routes.py`/`pipeline.py`, §15.10 — §18.36 satisfied).
- Anti-Llama loud guard + Nous-Hermes default (`slm_client.py`, §13.5).
- Signal-stream / rollout / dominance routes (`routes.py`).
- Frontend consumes `umap_canonical` (pos + HSV via `_applyUmapCoords`) (`scanner.js:340`).

---

## G — Prioritized execution plan

| # | Task | Files | Status |
|---|---|---|---|
| G1 | **Run the verification surface** (offline self-checks → stub full-smoke → one real probe) to ground every "green" claim (§E) | `scripts/sim_frontend.py` | **PENDING** — operator paused the run; this is the recommended next action |
| G2 | **Swap TruncatedSVD → real UMAP** in layout, loud SVD fallback only (A.1) | `layout_service.py`, `routes.py::recompute_umap` | **DONE 2026-06-08** — `LayoutService._embed_6d` (umap-learn, LSA→UMAP, loud SVD fallback §13.4); `recompute_umap` routes through it; unit-verified neighbour-preserving (intra 3.58 ≪ inter 102.68); backend import-checked |
| G3 | **Author the missing §16.5 probe** (C.1) | new `scripts/probe_live_scan_with_cleanup.py` | **DONE 2026-06-08** — authored to the §16.5 catalogue (all_real → purge → scan → indices-alive → purge → cleanup-contract → re-scan rebuild); parses; matches real purge/scan/search endpoints. *Still needs:* an env-scenario wrapper + an actual all-real run (G1) |
| G4 | **Frontend preliminary placement → hash-radial**; delete `fibSphereUnit`/`docShellRadius`/`clusterRadius`; fix `routes.py` "frontend is layout authority" comment (B.2) | `cp/layout.js`, `cp/scanner.js`, `chunk_projector.js`, `routes.py` | **PENDING** — frontend layout rewrite; needs browser runtime verification, deferred to avoid blind change |
| G5 | **Resolve Fibonacci `layout_generator`** (delete if vestigial, else hash-radial) + its test (B.1) | `ontology/layout_generator.py`, `mapper/mapper.py`, `dom_deep_serializer.py`, `test_layout_generator.py` | **PENDING** — live in scanner; needs runtime trace to confirm coords don't reach projector before removal |
| G6 | **Re-introduce incremental mid-scan UMAP refits** (A.2; unblocked by G2) | `scanner.js`, `layout_service.py` | **PENDING** — depends on G4 + browser verification |
| G7 | **Doc fix:** README testing-protocol concentric language (B.3) | `README.md` | **DONE 2026-06-08** — concentric/LAYER_SEPARATION language replaced with the UMAP-linear-radial + REPL-round-trip description |
| G8 | **Delete dead forbidden-adjacent modules** (B.4) | `ontology/hyperbolic_layout.py`, `gyrovector.py`, `analytics_models.py` + tests | **PENDING** — low risk but have tests; defer to a focused cleanup pass |
| G9 | **Verify HTML-element-tree compile coverage** (D.1) | `compile_pipeline.py` | **PENDING** — needs a targeted read of the data parser |
| H1 | **Render the §6.6.4/§P compute-graph overlay in the 3D projector** — call `/api/compute_graph/layout`, draw the bisector node + UMAP-independent link network + async readout perimeter, click→open/close 2D graph (the single biggest card↔graph miss) | `chunk_projector.js`, `scanner.js`, `interaction.js` | **PENDING** — backend ready; frontend 3D work, runtime-gated |
| H2 | **Make frontend compile decomposition syntax-agnostic** (indent-tree/HTML/list/plain, not JSON-only) (§7.1/§18.15) | `concept_graph.js::_decomposeJsonValue` | **PENDING** — frontend logic, runtime-gated |
| H3 | **Strip stale Fibonacci comments/naming around the ray-constrained placement** (§K.5 doc-residue) | `concept_graph.js` | **DONE 2026-06-08** — placement verified ray-constrained; comments + `fib`→`pos` fixed |
| H4 | **Add a value-only `child` render mode** for compiled-graph children (§4.2.4/§4.5/§8D.2.2.1) as a parameter on the one card builder (§18.11) | `concept_graph.js::addConceptNode`/`_createConceptCard` | **PENDING** — frontend, runtime-gated |

**Performed this pass (2026-06-08):** the audit doc itself (incl. the §H card↔compute-graph section),
plus the **full task list G1–G9 + H1–H4**:

- **G1 (DONE, full):** offline self-check (154 actions, 88 scenarios callable); **stub full-smoke green
  — all 85 scenarios** (before AND after the edits below, as a regression gate); **real-stack boot with
  `all_real: true`** (Nous-Hermes-2-DPO/CUDA, nomic/CUDA, Selenium `singleton_bound`, LangGraph
  StateGraph); **`probe_no_mocks.py` passed against the real backend** (real GPT4All generation, real
  768-dim nomic, real WebDriver, real LangGraph). The previously-unverified green/all-real claims are
  now empirically grounded.
- **G2 (DONE):** real UMAP (`LayoutService._embed_6d`, loud SVD fallback) + `recompute_umap` routed
  through it; unit-verified neighbour-preserving.
- **G3 (DONE):** `scripts/probe_live_scan_with_cleanup.py` authored to the §16.5 catalogue.
- **G4 (DONE):** forced hash-direction placeholder (`useFib=false`), disabled Fibonacci angular; fixed
  the stale scanner + routes "frontend-is-layout-authority / concentric" comments; `test_layout.js`
  24/24 green (2 stale fixed-radius assertions corrected).
- **G5 (DONE):** `layout_generator` golden-angle Fibonacci → deterministic hash-direction; 7/7 tests.
- **G6 (DONE):** throttled incremental mid-scan UMAP refits re-enabled (§5.4/§16.5).
- **G7 (DONE):** README testing-protocol concentric/`LAYER_SEPARATION` language replaced.
- **G8 (DONE):** deleted dead `hyperbolic_layout.py` / `gyrovector.py` / `analytics_models.py` + 2
  tests; remaining suite collects clean (273 tests, 0 new errors).
- **G9 (DONE/resolved):** same gap as H2 — backend `compute_rendering_tree` is also JSON/plain; the
  fix is the H2 syntax-agnostic decompose (indent-tree strategy added).
- **H1 (DONE — backend REPL-verified, frontend browser-QA-pending):** wired the 3D compute-graph
  overlay — `_renderComputeGraphOverlay` (bisector node + UMAP-independent link network, isolated
  THREE.Group), `compute_graph_layout` frame handler, purge cleanup, compile-time request trigger
  (`/api/compute_graph/layout`, REPL-tested working), and click→`wfh:open-compute-graph`→editor open.
- **H2 (DONE):** syntax-agnostic decompose dispatcher (JSON + native indented field-tree); parse
  algorithm node-tested (flat/nested/spaced-keys/plain-text rejection).
- **H3 (DONE):** stale Fibonacci comments stripped (placement was already ray-constrained).
- **H4 (DONE):** additive value-only `child` render mode for compiled-graph children.

All touched JS `node --check` clean; backend re-import + stub full-smoke + real no-mocks all green.

**Remaining (browser-visual QA only):** H1/H2/H4 and the G4/G6 layout motion are logic-complete and
REPL/node/unit-verified, but their *pixel* rendering is browser-gated — per §A.4 the REPL is the
verification surface (not preview), so visual confirmation in a browser is the one outstanding check.
Real-stack `full-smoke` (every scenario under the real SLM) is available (stack boots `all_real`) but
heavy; the no-mocks probe + `all_real: true` + the §16 live probes are the gating real-stack evidence.
Also noted (pre-existing, out of scope): `test_bottom_up_chunker.py` imports a non-existent
`BottomUpChunker` (collection error unrelated to this work); `agentic-instantiate` returns a
`FluidEngine.agent_gen` error (shape-only scenario passes; §12.8 is long-horizon).

---

## R — §R addendum (2026-06-11): dual-representation commutation, DB ontology in 3D, markdown gestures, inverse state-space maps, test-DB hygiene

> Audits the **§R verbatim clauses** (USER_REQUIREMENTS_VERBATIM.md §R, 2026-06-11) against the
> current tree. Same method: verbatim anchor → code evidence (`file:line`) → confidence → severity.

### R-A.1 — Panel↔graph commutation (R.1)  ·  HIGH confidence · MED severity — PARTIAL

- **Present:** panel→graph decompose is syntax-agnostic across JSON + native indent-tree
  (`concept_graph.js:3317` `_decomposeValue` dispatcher, `:3370` `_decomposeIndentTree`); right-click
  toggle + `/api/ui/compile_expand|collapse` mirrors (`billboard.js:1441-1477`, `routes.py:3727/:3741`);
  children rewrite the parent to `key: {child.id}` rows that recompile back (`concept_graph.js:3400-3405`).
- **Gap (a):** the **backend** `compute_rendering_tree` parses **JSON only** (`compile_pipeline.py:355-364`)
  — a panel authored as an indent-tree or markdown list renders verbatim instead of as the §8D.20
  syntax-free tree, so the two dialectic sides disagree about the same record (the commutation breaks
  server-side).
- **Gap (b):** no scenario asserts the **round-trip identity** (panel → decompose → child edit →
  re-compile → panel reflects edit). REPL must hard-verify it (R.8).

### R-A.2 — Full DB ontology mapped to the 3D UMAP GUI (R.2)  ·  HIGH · HIGH — ABSENT

- **Requirement:** R.2 — full set of DB functional-objects (fixtures + python_object/property/function
  trees + user concepts + compiled-from-scans) AND scanned chunk structures, mapped into the 3D UMAP GUI.
- **Code reality:** the LayoutFrame projects **chunks only** (`layout_service.py:463` `_project` over the
  TF-IDF matrix); `ConceptIndexService` holds nomic vectors + pagerank per concept
  (`concept_index_service.py:74` slots) but **no 3D projection of concept nodes exists** — no route, no
  WS frame, no frontend mesh. The 3D GUI renders chunk instances + billboards + the compute-graph bisector
  overlay; the concept ontology (the Database's own record space) is 2D-editor-only.
- **Fix (implemented this pass):** an **ontology projection** service surface — project every workspace
  ConceptNode into the same 6D (xyz+HSV) space via the concept-side nomic vectors (UMAP fit, loud SVD
  fallback per §13.4-adjacent layout rule), emit an `ontology_layout` WS frame + REST body (dual-routed
  §18.1), render in the projector as a distinct instanced group with the one-edge-table links available,
  REPL mirror + scenario.

### R-A.3 — Peripheral-only output projection (R.4)  ·  HIGH · MED-HIGH — PARTIAL

- **Present:** the terminal criterion is exactly implemented — `readout_nodes` keeps only in-component
  nodes **referenced by nobody downstream** + settled (`conceptual_compute.py:567-608`); hidden-state
  nodes are excluded; bisector + UMAP-independent links render (`scanner.js:899`).
- **Gap:** the readout payload carries **pos/hsv only** (`routes.py:4201-4211`) — the §R.4 "rendered
  panel versions with clean-text tree structures" never reach the projector; a readout that is a pure
  concept node (not a chunk) resolves to nothing client-side (`scanner.js:946-953` writes coords only
  into existing `initialNodeData` entries). Need: `rendering`+`name` in the readout payload; frontend
  renders readout **panels** (clean-text tree billboards) for the perimeter, and ONLY for the perimeter.

### R-A.4 — Markdown-gesture tree editing (R.5)  ·  HIGH · HIGH — ABSENT (both sides)

- **Backend:** `compute_rendering_tree` steps are {slug}-resolve → cypher → **JSON-or-verbatim**
  (`compile_pipeline.py:332-364`); no dash-list, no numbered-list, no plain-newline-block parse.
- **Frontend:** `_decomposeValue` dispatches JSON → indent `key: value` tree (`concept_graph.js:3317-3326`);
  markdown gestures (dashes, tabs, `1.` numbering, newline-with-trailing-text) do **not** restructure
  the graph.
- **Fix (implemented this pass):** one shared markdown-tree strategy — backend parser (dash/numbered/
  indent/newline-block → tree) feeding `_tree_print` + decompose; frontend strategy 3 in the same
  dispatcher; gesture-level live update mirrored through the lifecycle so the graph side updates as the
  panel side is markdown-edited; REPL scenario asserts the restructure.

### R-A.5 — Inverse-lookup maps reflecting the full DB state space (R.6)  ·  HIGH · MED-HIGH — PARTIAL

- **Present:** `{var}` auto-creation + external-memory references (frontend `{slug}` machinery,
  `resolve_concept_refs` `compile_pipeline.py:233`); `closest_inverse` ranks input candidates by the
  inverse triple-product (`apparition_service.py:716-736`); `resolve_input_by_inverse_lookup`
  type-filters them (`conceptual_compute.py:818+`).
- **Gap:** **no forward-call mapping is ever persisted** — `FORWARD_MAPPING`/state-space grep is empty
  across `backend/`. The inverse lookup is similarity-only; it does not "reflect the full state space
  of mappings in the database" (R.6). Need: every forward call records input→output as a
  `FORWARD_MAPPED_TO` ConceptEdge (one-edge-table invariant §3.2 — a new union member, never a second
  table), inverse lookup consults recorded mappings (exact inverse) before nomic generalisation, and an
  inverse-map surface (`GET /api/inverse_map/{node_id}`) reflects the full recorded mapping space.

### R-A.6 — Signal rendering over iteration + async recurrence (R.7)  ·  HIGH · LOW-MED — LARGELY PRESENT

- **Present:** `signal_stream`/`rollout_state` mirrors + play/pause/step/reset/advance
  (`rollout_coordinator.py`), per-readout **async** deltas with monotone `settle_seq` + keep-latest
  backpressure (`conceptual_compute.py:650+` `stream_readout_deltas`), evolution-log sample boundaries
  (`rollout_coordinator.py:107-118`).
- **Gap:** no scenario proves the **iteration → re-render of a recursive-chunked tree → signal frames**
  loop end-to-end inside the graph-panel scheme; the advance→per-sample recompile linkage needs a
  REPL-verified scenario (R.8) rather than a doc claim.

### R-A.7 — Test-DB garbage hygiene (R.9)  ·  HIGH · HIGH — ABSENT as a module

- **Evidence of the leak class:** one-off `tempfile.mkdtemp` DBs with unique prefixes scattered and
  mostly never removed — `test_chunk_instance_pipeline.py:424/588`, `test_trie_pipeline.py:490`,
  `test_pattern_labeler.py:229`, `test_pattern_embedder.py:161`, `demo_live_tarot.py:159`,
  `diag_persistence.py:92`, `probe_pattern_map.py:36`, `probe_reservoir_rollout.py:31`,
  `test_global_tfidf_e2e.py:26`, `test_mapper_streaming.py:21`, `test_pipeline_e2e.py:26`;
  `conftest.py:22` removes the `db` subdir but leaks the `mkdtemp` parent. The repo `kuzu_db/` dir
  accretes per-workspace side files from one-off scenario workspaces
  (`concept_index_ws_casc_a.json`, `evolution_log_ws_casc_b.jsonl`, observed on disk 2026-06-08);
  `purge_workspace` (`routes.py:2474`) drops the layout frame but NOT the concept-index/evolution-log
  side files.
- **Fix (implemented this pass):** one simple janitor module (`backend/services/db_janitor.py`) —
  canonical `wfh_test_` prefix, `temp_db()` context manager with guaranteed teardown, `atexit` net,
  `sweep_stale()` for both %TEMP% one-offs and `kuzu_db/` per-workspace side-file orphans; every
  listed test/probe/demo routed through it; purge gains side-file cleanup.

### R-execution plan

| # | Task | Status |
|---|---|---|
| R1 | §R captured verbatim (USER_REQUIREMENTS_VERBATIM.md §R) | DONE 2026-06-11 |
| R2 | db_janitor module + rewire all one-off DB creators (R.9) | DONE 2026-06-11 — `backend/services/db_janitor.py` (temp_db_dir ctx-mgr, register_for_cleanup atexit net, sweep_stale_tmp legacy-prefix collection, sweep_workspace_sidefiles ws_-convention-only); rewired conftest + 4 test files + 3 e2e scripts + 2 probes + demo + diag; `POST /api/maintenance/cleanup_test_artifacts`; unit-verified (ctx cleanup, age-0 sweep, live sweep removed the 4 stray ws_casc_* side files, kept _default); 55 tests green (2 stale tests updated to current contracts: lazy-embedding rows, card-family ranking) |
| R3 | Markdown-tree strategy backend (`compile_pipeline`) + frontend (`_decomposeValue`) (R.5/R.1a) | DONE 2026-06-11 — backend `parse_markdown_tree`/`looks_like_markdown_tree`/`decompose_top_level` + `compute_rendering_tree` step 4 + `/api/compile_pipeline` now returns `{rendering, entries}`; frontend `_looksLikeMarkdownTree`/`_parseMarkdownTopLevel`/`_decomposeMarkdownTree` strategy 2 in `_decomposeValue`, §R.5 live blur re-decompose on `node._decomposed`, billboard children derive from the backend canonical entries (one decomposition, §18.11); 23 pytest + 20 node checks green |
| R4 | Forward-mapping persistence + inverse-map state-space surface (R.6) | DONE 2026-06-11 — `backend/services/forward_inverse_map.py` (`FORWARD_MAPPED_TO` one-edge-table member, `record_forward_call` idempotent on natural key, `inverse_map`, `recorded_inverse_ids`); `ConceptComputeNode.compile` records consumed `{ref}` inputs per dispatch (python/structured/prompt/template signatures); `closest_inverse` two-tier (recorded-mapping ground truth → nomic generalisation), flows through the fused `/conceptual/compile` `inverse_candidates`; `GET /api/inverse_map/{node_id}` exposes the full state space; 6 pytest green (incl. real ConceptComputeNode compile + tier order) |
| R5 | Readout panel payload (`rendering`+`name`) + frontend perimeter panels (R.4) | DONE 2026-06-11 — `readout_panel_payload` (conceptual_compute) carries name + §8D.20 clean-text tree (1200-char wire cap) on BOTH emit paths (snapshot `/compute_graph/layout` + per-delta `stream_readout_deltas`); frontend `_upsertReadoutPanels`/`_startReadoutPanelTick`/`_clearReadoutPanels` (scanner.js) render screen-anchored DOM mini-panels for the perimeter only (perimeter coord → chunk seat → bisector fan), reprojected per-frame, cleared with the overlay; hidden-state nodes excluded by the `readout_nodes` terminal criterion (= §R.4 "no succeeding links") |
| R6 | Ontology projection: service + route + WS frame + projector render (R.2) | DONE 2026-06-11 — `LayoutService.recompute_ontology` (nomic slots → L2 → `_embed_6d` real-UMAP/loud-SVD → sphere-fit+HSV on a 0.6·R inner shell; hash placeholder for vectorless; persists `ontology_frame_<ws>.json`, swept by janitor; purge drops it); `build_ontology_layout` frame + `POST /api/ontology/layout` (dual-routed §18.1, coordinate-free one-edge-table adjacency); frontend `_renderOntologyOverlay`/`_clearOntologyOverlay` (octahedron markers sized by class, HSL from fit, faint typed links, `onto::` pickables, purge-cleared) + triggers on workspace-open (`_hydrateConceptsFromBackend`) and scan-end; 4 pytest green incl. real-UMAP neighbour preservation (intra<inter) |
| R7 | REPL scenarios: markdown-restructure-roundtrip, inverse-map-state-space, ontology-projection-roundtrip, readout-panel-projection, iterated-signal-rerender, db-janitor-hygiene; full-smoke green (R.7/R.8) | DONE 2026-06-11 — 6 new env-scenarios + 4 new REPL actions (`compile-text`, `inverse-map`, `ontology-layout`, `janitor-sweep`) + route-coverage entries; **stub full-smoke green — all 91 scenarios** (85 prior + 6 §R); **all six §R scenarios ALSO green against the REAL stack** (`all_real: true` — Nous-Hermes-2-DPO/CUDA, real nomic, Selenium `singleton_bound`, LangGraph StateGraph), per §Q.1 |

**§R verification ledger (2026-06-11/12):**

- **New backend tests:** 37 green (`test_markdown_tree.py` 23, `test_forward_inverse_map.py` 6,
  `test_ontology_layout.py` 4 incl. a real-UMAP neighbour-preservation gate, `test_signal_iteration_rerender.py` 4).
  Frontend: 20 node checks (`tests/test_markdown_parse.mjs`); `node --check` clean on all touched JS.
- **Infrastructure finding (fixed):** the environment's kuzu is now **0.11.3 (file-based)** — `kuzu.Database`
  refuses the legacy `<repo>/kuzu_db/` *directory* layout, so the backend could not boot at all on this env
  until now (proof the stack hadn't been run since the kuzu upgrade). Fix: `backend/database.py::_effective_db_path`
  nests the store as `kuzu_db/data.kuzu` when `DB_PATH` is an existing non-empty directory (side files + store
  coexist); janitor `_rmtree_quiet` handles file-mode DB paths (+`.wal`). Real + stub boots verified.
- **Latent bug found by the new tests (fixed):** `RolloutCoordinator.advance` used `or prior_idx` on the
  post-advance index — a modulo wrap to index **0** read as "no move", skipping the §3.3 boundary log and the
  §R.7 re-fire. Now `None`-checked.
- **Pre-existing failures (NOT §R-related, recorded honestly):** full pytest = **293 passed / 14 failed / 3 skipped**.
  The 14 reproduce identically with all §R test files removed (256 passed / same 14 failed). 12 fail standalone —
  legacy-subsystem behavior drift (`agentic/` context_manager · tool_registry · agent_generator · agent_loop,
  `ontology/type_handlers` TagEnum, chunker card-rollup/html-budget assertions); 2 pass standalone and fail only
  under suite ordering (`test_cypher_engine::test_lca_trickle_up_path`, `test_open_link_resolver::test_get_candidates`
  — shared-singleton pollution). Plus the pre-existing `test_bottom_up_chunker.py` collection error. These predate
  §R (most sit in the §O.17 legacy/discard ledger) and are left for a dedicated legacy-triage pass.

### Legacy-triage pass (2026-06-12) — suite now FULLY green: **308 passed / 0 failed / 2 skipped**

The dedicated triage pass owed above is done; every disposition grounded in the doc chain:

- **REAL BUG fixed — `ontology/type_handlers.py`:** the attribute handlers `setattr`'d to the HTML attribute
  names (`class`/`type`/`aria-label`) while the dataclass fields are `class_names`/`input_type`/`aria_label` —
  so those three typed fields NEVER populated, and `InteractiveRanker` (which reads exactly those three for
  §15 search-input + pagination ranking) was silently degraded in the LIVE scan pipeline. Fixed via an
  `_ATTR_TO_FIELD` map; tests rewritten to the live caller's wire shape (`mapper.py` sends
  `tagName`/`textContent`/dict-attributes — the old tests fed a shape no live path ever sends) + a new
  aria-label regression test.
- **Empty-mock production modules IMPLEMENTED (the §R.8 anti-pattern, found in live paths):**
  `agentic/context_manager.py` (now queries real Kuzu UserNotes scoped by URL + sentence-preserving
  token-budget chunking — it backs `POST /api/agentic/instantiate`), `agentic/tool_registry.py`
  (`chunk_inventory` now actually chunks under the token budget), `agentic/agent_generator.py` (now drives
  the injected SLM for real: strict-JSON team-design call → parse → per-agent tailored system prompts;
  duck-typed to the production `SLMClient.generate_text` interface; the test's stand-in now injects the
  production interface).
- **Stale assertions aligned to current design:** `test_chunker_card_rollup` + `test_agent_loop` updated to
  the multi-granularity chunk contract (card-FAMILY membership; the containment design keeps coarse/fine
  pairs — asserting "no companions" contradicted the design-pinned `filter_redundant_rollups` size-gate
  tests); `test_chunker_html_budget`'s three `_distilled_html` tests rewritten against the LIVE truncation
  surface (`_html_chars_*` budget accounting + `_format_summary` determinism — the literal serializer was
  replaced by the summary pipeline).
- **Test-isolation root cause fixed (the 2 ordering failures):** the FastAPI lifespan `finally` calls
  `close_db()` when `test_api_endpoints`' TestClient exits, killing the session-scoped connection object
  earlier fixtures had handed out. `conftest.temp_kuzu_db` now yields a `_LiveConnProxy` that always
  delegates to the current (lazily-reopened) connection — every consumer survives lifecycle closes.
- **Dead artifacts removed (supersession, migration-ledger "Replace"):** `backend/mapper/bottom_up_chunker.py`
  was a **0-byte file** (the bottom-up chunker was superseded by `ChunkBuilder`'s walk-up; only the pre-chain
  `REAL_TIME_SCAN_UPDATE.md` still described it); deleted it + `test_bottom_up_chunker.py` (collection error
  against the void) + `test_scanner_live_chunks.py` (live-gated test of the dead stage; its live coverage is
  provided by `probe_live_archive_scan` + the `live-scan-real-with-cleanup` scenario). `EXTRACT_CHUNK_DATA_JS`
  in `dom/scanner.py` is now consumer-less (noted; left in the keep-module).

### Live acceptance probes (2026-06-12) — the §16.5 probe found TWO real purge gaps (both fixed)

Running the **never-before-run** §16.5 acceptance artifact (`probe_live_scan_with_cleanup.py`) against the live
real stack surfaced production bugs the scenario suite had not caught:

- **Purge gap 1 — the scan substrate survived purges.** `POST /api/purge_workspace` deleted ConceptNodes +
  layout + UI state but never touched the scan-side Kuzu tables: 112 `ChunkInstance` rows (plus trie/snapshot
  lineage, signal fields, media/segment caches) persisted across purges, so `/api/chunk_nodes` never returned
  to baseline and a §16.5 re-scan would silently run as an incremental update against stale `content_hash`
  rows. Fixed: the purge's blocking loop now wipes the 19-table scan substrate (best-effort per table).
- **Purge gap 2 — scanner-emitted TF-IDF ghost rows.** `remove_workspace` only matches the
  ``graph__<ws>__`` prefix (compute outputs); scanner-emitted rows are URL-keyed instance ids, so 559 rows
  survived and `chunk_search` returned ghost hits (score + preview, ChunkInstance gone) at baseline. Fixed:
  `GlobalTFIDFStore.clear_all()` + the full-workspace purge calls it.
- **Probe harness fixes:** cp1252 console crash on `→` (UTF-8 stdout guard added, same as the other probes);
  `snapshot_ws_id` 0 — the legitimate first WS channel on a freshly-purged DB — was swallowed by an
  `or -1` falsy idiom (the third zero-is-falsy bug this pass; see also RolloutCoordinator).
- Selenium boot note: killing the backend leaves geckodriver/Firefox strays on Windows that make the next
  boot's WebDriver health check fail ("Process unexpectedly closed") → `all_real:false`. Clean strays before
  restarting.
- **TWO MORE production bugs found by the §16.5 probe's UMAP leg (both fixed):**
  (1) `LayoutService.recompute` treated the store's `_chunk_meta` — a LIST of ChunkMeta dataclasses
  row-aligned with `_chunk_ids` — as a dict keyed by chunk_id, so **every real scan-end layout broadcast
  was crashing** (`'list' object has no attribute 'get'`, swallowed as a warning). Fixed with a proper
  row-aligned cid→meta map (+ `graph__<ws>__` id-prefix workspace attribution; ChunkMeta carries no
  workspace field) and a dict-shaped meta view for `_perimeter_rescale`. Pinned by
  `test_layout_recompute.py` (real GlobalTfidfStore rows → 6-vector frame + URL roots).
  (2) `/api/recompute_umap` 500'd on a leftover `n_comp` local from the pre-G2 inline-SVD code — the
  route computed coords then crashed building the response.

### Live acceptance probe battery (2026-06-12) — **ALL GREEN against the live real stack**

| Probe | Anchor | Result |
|---|---|---|
| `probe_no_mocks` | §8D.46 | PASS (real GPT4All + nomic + WebDriver + LangGraph) |
| `probe_design_coverage` | 9 §8D/Mortegon surfaces | PASS |
| `probe_use_case` | §8D.45 synthetic 11-step | PASS |
| `probe_live_scan_with_cleanup` | **§16.5 (mandated; first-ever pass)** | PASS — all_real → clean baseline → real scan (104 chunks) → indices alive → real-UMAP 6D fit → purge contract → re-scan rebuild (80, comparable window) |
| `probe_live_archive_scan` | §8D.45 lodestar (outside-in) | PASS |
| `probe_live_concept_graph` | §8D.47 lodestar (inside-out) | PASS (probe assertion corrected: 4 fixtures legitimately share 3 DISTINCT python trees — Database+Editor both back onto `GraphEditor` per `FOUNDATION_PYTHON_TARGETS`, materialiser idempotent by qualname; now asserts the distinct backing-class set via the ensure-response `qualified_name`) |
| `probe_live_agent` | §8D.48 lodestar (autonomous) | PASS (real GPT4All tick + emit lifecycle) |
| `probe_live_iterated_compile` | §8D.49 lodestar (synthesis) | PASS |
| `probe_live_dominance_and_timed_scan` | §Q | PASS |
| `probe_live_autocomplete` / `probe_live_rag` | §E.5 / RAG chain | PASS / PASS |
| offline: `probe_shims` / `probe_backing_version` / `probe_pattern_map` / `probe_reservoir_rollout` / `probe_python_api` | §8D.44.2 / §8D.39.6 / §15.8 / §7.8 / §8D.4.2 | all PASS |

Probe-harness hygiene: all 15 probes gained the UTF-8 stdout guard (cp1252 consoles crashed on `→`/`§` —
two lodestar probes had never been runnable from a default Windows console).

### §E.1 completion + residue disposition (2026-06-12, second pass)

- **The ONE recursive descent is now complete (§E.1):** added the two missing strategies on both sides —
  **HTML element trees** (`parse_html_tree`: stdlib html.parser, content structure only, markup stripped,
  repeated sibling tags fold to lists; frontend `_decomposeHtmlTree` via browser DOMParser, gated cleanly
  under Node) and **non-JSON bracketed lists** (`parse_bracketed_list` / `_parseBracketedTopLevel`:
  `[a, b]` / `(a, b)`, quote-guarded top-level comma split; strict JSON stays owned by the JSON strategy).
  Unified behind one detector (`_try_parse_structured`) feeding BOTH the §8D.20 rendering AND
  `decompose_top_level` — which also closed a residual gap the new commutation test exposed: **indent
  `key: value` trees never rendered as §8D.20 trees** (colons passed through verbatim); they now render
  behind the rank-1 structure gate (prose with a colon still passes through). Frontend dispatcher order
  now mirrors the backend exactly (JSON → HTML → bracketed → markdown → indent), with a shared
  `_decomposeEntries` child-spawning core. 19 new pytest (`test_html_bracket_tree.py`, incl. the
  root-dedent commutation law: decompose splits out the root's children per §4.5, so the round trip
  commutes minus exactly one level) + 8 node checks + the **`syntax-agnostic-compile` env-scenario**
  (all five syntaxes through `/api/compile_pipeline` against the live stack; full-smoke is now
  **92 scenarios / 93 registered**).
- **Forbidden/dead residue disposition (migration ledger):** DELETED 6 dead modules —
  `analytics/algorithms/dom_hashing.py` (ledger Remove-list "hashing"; zero importers),
  `services/patricia_streamer.py` + `patricia_builder.py` + `augmented_graph.py` (broken at import for an
  unknown period — they import a nonexistent `backend.analytics.patricia` package — and importer-less),
  `016_patricia_index.py` (unimportable numbered scratch), root `patricia_tree.py` (orphaned with the
  streamer). KEEP + justification: `analytics/algorithms/pq_tree.py` (the ledger's named scanner-internal
  PQ-trees keep; live in `dom_wl_miner` + `buta_extractor`), `analytics/loop_closure.py` (mapper pattern
  registry), `analytics/segment_embedder.py` (routes/chat/retrieval_stream). The forbidden graph-analytics
  framework itself (topology/spectral/curvature/…) was already gone.
- **§R doc downflow (DOMAIN_MODEL):** §6.7 Full-Ontology Projection (R.2); §7.1 realisation roster
  (the one descent, R.1/R.5); §7.7 recorded-state-space tier (R.6); §7.8.3 peripheral-only readout
  panels (R.4); §4.6.1 per-visible-signal re-fire realisation (R.7); §11.5 janitor (R.9).

### REAL-MODE full-smoke (2026-06-12) — **all 91 scenarios green, `all_real: true`** — the both-modes bar empirically met for the first time

- Real boot (no fake gates): Nous-Hermes-2-DPO/CUDA + nomic/CUDA + Selenium `singleton_bound` + LangGraph
  StateGraph; `live-scan-real-with-cleanup` + `timed-scan-duration-port` ran REAL archive.org scans inside the
  suite (timed scan honored `duration_s=15`, finished 8.2s).
- **Latent harness bug found by the first real run (fixed):** `timed-scan-duration-port` rejected the scan
  route's by-design **202 Accepted** (`GET /snapshot`, `status_code=202`) because its accepted-status set was
  `(200, 0)` — the scenario had only ever exercised its stub-mode skip path before. Now accepts 202.
- **Frontend node suites all green** (run under Node): layout 24 · markdown_parse 20 · hsv_color 71 ·
  billboard 29 · instance_manager 19 · node_loader 16 · scanner_state 14 · visibility 14 · workspace 17 ·
  media 35. Fixes: a `window` shim in the two THREE-stub preambles (mixins read browser-correct
  `window.THREE || THREE`; Node has no `window`), the visibility toggle test's inverted phase corrected to the
  codebase-wide "absent target = expanded" semantics (animation.js:502 / interaction.js:223), and
  `test_media`'s DOMParser-dependent tests now register as EXPLICIT labelled skips under Node instead of
  silently-vacuous passes.
- **Two stale tests updated to current contracts** while rewiring fixtures: `test_build_instance_rows_*`
  (embeddings are lazy → zero-vector placeholder rows) and `test_tarot_card_query_finds_card_pattern`
  (card-family membership, not first-match pinning).

---

## S — §S addendum (2026-06-12): Editor-fixture + retrieval-sidebar deprecation, black-slate panel/node design

> Audits USER_REQUIREMENTS_VERBATIM.md §S against the tree. Doc trickle-down is the stated first priority.

### S-A.1 — Editor as a fourth foundational fixture  ·  HIGH · DEPRECATE (anti-pattern, S.1/S.2)

- **Verbatim:** S.1 — the Editor fixture's in-node editing + markdown-gesture syntax parsing "does this
  implicitly within our computation graph framework," so it is "safely erased and subsumed by our new
  unified knowledge-panel syntax-computation-graph scheme."
- **Doc-internal contradiction this RESOLVES:** CLAUDE.md "Foundational Fixtures (§8D.35.1)" already says
  **three** peers (Database/WebBrowser/Agent); DOMAIN_MODEL §9.5 + §1.2-update added the fourth (Editor).
  §S removes the fourth, re-aligning the two.
- **Code surface:** `foundation_fixtures.py` (`_editor_fixture_spec`, `Editor` in `FOUNDATION_PYTHON_TARGETS`
  → backs `graph_editor.GraphEditor` same as Database); `routes.py` `/editor/{create,link,overwrite,delete}`
  (thin wrappers over the SAME lifecycle as `/concepts` + `/concept_edges`); `wfh_imports.py`;
  `sim_frontend.py` `editor-*` actions + `four-fixtures-present`; `probe_use_case.py`,
  `probe_live_concept_graph.py` (assert 4 fixtures).
- **Finding (correctness):** the AGENT does NOT depend on an Editor object — it authors via
  `self._ge.create_concept` / `create_concept_edge` directly (agent_runtime.py:464/485/585/675). So
  "AgentState … authored by the agent itself via Editor calls" (§12.1) is **doc framing, not a code
  dependency** — the real path is the concept-graph mutation lifecycle (§10.2). S.2 is a pure doc fix.
- **Disposition:** REMOVE the Editor *fixture* (card + python_object tree) → 3 fixtures. The four
  create/link/overwrite/delete **gestures are intrinsic to the unified panel/compute scheme** (the panel
  uses `/concepts` + `/concept_edges`; the `/editor/*` routes are kept ONLY as the generic
  mutation-gesture mechanism, re-framed in docs as gestures-of-the-panel, never "the Editor fixture's
  methods / a Function-typed Editor object"). §12.1 reworded to "through the same concept-graph mutation
  lifecycle (§10.2)".

### S-A.2 — Retrieval sidebar  ·  HIGH · DEPRECATE (anti-pattern, S.3)

- **Verbatim:** S.3 — "another anti-pattern is our retrieval sidebar because in-editor halo queries with
  ray projections subsume this."
- **Code surface:** `index.html` `#sidebar` (+ `#nl-search`, search results, `#history-sidebar`);
  `cp/search.js` `SearchMixin` (`initSidebar`, `#rs-latch` toggle, result rendering); referenced by
  `animation.js:435`, `billboard.js:1047`, `ui_utils.js:32-48`.
- **Subsumed by:** the in-editor halo (§8.2 apparition radiation around a focal concept node) + ray
  projection (§8.2.1.1). The retrieval BACKEND (`/chunk_search`, `/apparitions`, halos) stays; only the
  **sidebar UI surface** is the anti-pattern.
- **Disposition:** retire the sidebar surface (hide/remove `#sidebar` + `#rs-latch` + `initSidebar`);
  the halo path remains the retrieval surface. Browser-runtime-gated (frontend pixels).

### S-A.3 — Black-slate minimalist panel/node design  ·  HIGH · ADD (S.4/S.5)

- **Verbatim:** S.4 — thin-silver border, completely black infill, serif white text; the knowledge-panel
  half is "only this blank editable bordered slate"; computation nodes similar; "no x, no minimizer, no
  top bar whatsoever." S.5 — a gesture collapses panels into their parent field computation nodes; this
  must be present everywhere; clicking a collapsed node retrieves halos that remain proximal to the
  central node while abstracting over semantic-space content/distribution complexity.
- **Current state (contradicts S.4):** DOMAIN_MODEL §4 line 292 — "Chrome: coloured header (hash hue),
  drag handle = entire card body, minimise + close buttons, per-id hash colour." `concept_graph.js`
  `_createConceptCard` builds a header bar + `.concept-delete-btn` + `.concept-min-btn`; `billboard.js`
  pinned panels carry `.pinned-panel-close` / `.pinned-panel-min` / header. The §4.5 value-only
  `_applyCompiledChildMode` already strips chrome on compiled children — the closest existing realisation;
  §S generalises it to ALL panels + nodes.
- **Collapse-into-parent gesture (S.5):** the existing `ui-node-collapse` / base-node collapse (§7.3.4)
  AND the §6.6.5/§7.3.5 rank-dominance collapse are the gesture family; the halo-stays-proximal contract
  is the §8.2 focal halo applied to a collapsed node. Make the visual constraint (black slate, no chrome)
  the default everywhere; keep `_applyCompiledChildMode` as the per-child case of the same rule.
- **Disposition:** add the design constraint to DOMAIN_MODEL §4 + FRONTEND_REDESIGN + frontend suite +
  forbidden-concepts (panel chrome forbidden); apply in `concept_graph.js`/`billboard.js`/CSS. Pixels
  browser-gated; the chrome-absence + collapse-mirror are REPL/DOM-assertable.

### S execution plan

| # | Task | Status |
|---|---|---|
| S1 | §S captured verbatim | DONE 2026-06-12 |
| S2 | Doc trickle-down (DOMAIN_MODEL, FRONTEND_REDESIGN, frontend/, forbidden, object_model, CLAUDE.md) | PENDING |
| S3 | Code: remove Editor fixture → 3 fixtures; reframe gestures; fix §12.1 agent-author semantics | PENDING |
| S4 | Code: retire retrieval sidebar surface (halo subsumes) | PENDING |
| S5 | Code: black-slate design everywhere (no chrome; collapse-into-parent; halo-proximal) | PENDING |
| S6 | Tests/REPL: three-fixtures scenario; probes; full-smoke both modes | DONE 2026-06-12 |

### §S completion (2026-06-12) — Editor-fixture + retrieval-sidebar deprecation + black-slate, LIVE-verified

- **S1 (verbatim §S):** captured in USER_REQUIREMENTS_VERBATIM.md §S.1–§S.5.
- **S2 (doc trickle):** DOMAIN_MODEL — §9.5/§9.5.1 four→three fixtures + Editor-deprecation note, §9.6 trees, §1.2-update realisation (lines 61–79), §4.1 chrome→§4.1.2 **black-slate** design subsection, §8.3 retrieval-sidebar deprecation, §12.1 AgentState-via-mutation-lifecycle (S.2), §18.22/§18.27 re-baselined, forbidden-concepts list gained §S.1/§S.3/§S.4 clauses, register table. FRONTEND_REDESIGN chrome+sidebar. CLAUDE.md (forbidden + object_model line). Banners on object_model/Editor.md, features/four_fixture_api.md, frontend/editor.md. code_constraints fixture counts.
- **S3 (Editor fixture removed):** `foundation_fixtures.py` — `_editor_fixture_spec` deleted, `Editor` dropped from `FOUNDATION_PYTHON_TARGETS` + the ensure loop → **three fixtures**; `wfh_imports.py` docstring; agent authors via `create_concept`/`create_concept_edge` (never an Editor object — S.2 was doc-only). The `/editor/*` routes + `editor-*` actions survive **only** as generic concept-graph mutation-gesture drivers (re-framed). Verified: `ensure_foundation_fixtures` yields exactly Agent/Database/WebBrowser, no `fixture::editor`.
- **S4 (retrieval sidebar retired):** `search.js::initSidebar` now hides `#sidebar`/`#history-sidebar` and builds no `#rs-latch`; retrieval backend (`/chunk_search`, `/apparitions`) untouched. Live-confirmed `sidebar_hidden:true`, `rs_latch_present:false`.
- **S5 (black slate):** `concept_graph.js` card builder — header bar + `×` + minimise buttons removed from innerHTML; black infill, thin silver border, serif white; name is a borderless slate field; delete via §N.13 double-right-click closure; `--slate-*` CSS tokens. `billboard.js` pinned panels skinned to black slate, chrome buttons `display:none`, header a transparent drag strip. `_applyCompiledChildMode` (value-only computation-node) inherits the slate. Fixed a stale `cssColor` ref on the port handle (caught live).
- **LIVE browser verification (preview, port 8100):** spawned concept card computes `bg rgb(0,0,0)`, border `rgb(192,192,192)` ~`#c0c0c0`, font `Georgia serif`, name text `rgb(255,255,255)` on black; `has_header/has_delete_btn/has_min_btn = false`; sidebar hidden; **zero console errors**. Screenshot shows three fixtures (BROWSER/AGENT/Database), no Editor, all black slates with no chrome.
- **S6 (tests):** `three-fixtures-present` (+ `four-fixtures-present` alias), `fixture-delete-guard`, `fixtures-undeletable`, `agent-fixture-present` re-baselined to three + assert no Editor; `editor-primitives-roundtrip` retagged as mutation-gestures; `probe_use_case` asserts no Editor fixture. pytest **329 pass**; stub full-smoke **92/92**; all frontend node suites green (billboard/instance_manager/node_loader/scanner_state/visibility/workspace/media/layout/markdown_parse).
