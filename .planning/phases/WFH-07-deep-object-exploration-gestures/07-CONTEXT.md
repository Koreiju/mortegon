# Phase 7: Deep Object-Exploration Gestures - Context

**Gathered:** 2026-06-23
**Status:** Ready for planning
**Mode:** Smart-discuss (autonomous) — design is locked in the docs; this captures the
port decisions. Like Phase 6, this is a brownfield PORT of a cp/-realised feature into
the served fe/ idiom, NOT a from-scratch design.

<domain>
## Phase Boundary

Port the §M/§N recursive type-strict object-exploration surface — already realised in the
legacy `cp/*.js` core — into the served `/` black-slate `fe/` editor. The seven-gesture
model (hover→next-rank preview, single-left edit, right-click rank-1 fold, right-click-self
collapse, double-left panel↔graph, left-drag wire+inherit, double-right delete) drives a
`name:Type=value` typed panel whose tokens are navigable handles into the next rank of the
object's type graph. External `{ref}`s propagate as their own recursively-rendered panels at
rank-1 minimalism. The DuckDuckGo §N walkthrough runs end-to-end. Covers EXPLORE-01..04.

In scope: EXPLORE-01 hover next-rank type-graph expansion (super-class + typed params;
function rows → typed I/O, output inferred by i/o equality); EXPLORE-02 external-`{ref}`
recursive-panel propagation (rank-1 minimalism, duplicate-instance proxy); EXPLORE-03
left-click-drag wire (target inherits I/O types + object model) + double-right-click delete
(panel or graph form); EXPLORE-04 the DuckDuckGo walkthrough; fold-state preservation (M.6);
**and (pulled in from Phase 8 per decision D-04) the three §O.1a brace render states**
(braced-hidden / revealed-internal / resolved-external) over the one invariant graph.

Out of scope (stays Phase 8): halo cone-ray transport by triple-product similarity (§O.18)
and the 2D per-sample stepper driving 3D focus (§O.6). Phase 7 builds the underlying
ref/fold graph + brace-state rendering those features render over, not the cone transport or
stepper themselves.
</domain>

<decisions>
## Implementation Decisions

### D-01 — EXPLORE-04 verification depth: REAL-SUBSYSTEM INLINE (user choice)
The DuckDuckGo §N walkthrough is verified end-to-end against REAL subsystems IN THIS PHASE
(not deferred to milestone-end). The phase gate includes a live run: real Selenium DuckDuckGo
scan + real materialiser type graph, exercised by a `duckduckgo-walkthrough` REPL env-scenario
AND a `probe_live_*` style probe asserting the §N flow (author `self=duckduckgo` referencing
`scan` → drag-wire the WebBrowser scanner → reveal rank-1 `url{}`/`dom{}` → per-sample chunk
iteration on `{chunk samples}`). Honor the clean-GPU lesson: confirm 0 stray python/firefox +
~0 VRAM before the real boot; drive the real backend lifecycle from the main context (NOT a
verifier subagent that can wedge CUDA). Stub-backed e2e + REPL scenario must ALSO stay green
(both modes) as the fast gate; the real run is the acceptance proof on top.

### D-02 — Port host: EXTEND EXISTING fe/ GESTURE MODULES (user choice)
Port the cp/ exploration features into the existing served fe/ gesture scaffolding rather than
a new top-level module: `magic_markdown_gestures.mjs` (gesture dispatch), `magic_markdown_panel.mjs`
(the typed `key:Type=value` panel render + fold), `gateway.mjs` (the GestureGateway action
contract). Add a new fe/ module only where a clean seam genuinely requires it. The cp/ feature
references to port FROM: `cp/concept_graph.js` (`_pythonNativeTypedView`, rank-1 inline fold
`node_fold`), `cp/interaction.js` (the seven-gesture dispatch + non-collision rules §18.32),
`cp/edge_manager.js` (drag-wire link creation + type inheritance), `cp/instance_manager.js`
(instance-inheritance §9 / M.11). Do NOT resurrect the cp/ surface; bring its FEATURES into fe/.

### D-03 — Type-graph data source: NEW BACKEND TYPE ENDPOINTS ALLOWED AS NEEDED (user choice)
Frontend still renders (never computes) the type graph — D10 holds — but the planner may add
new backend endpoints/edges where the existing materialiser surface does not already expose
what next-rank expansion needs. Start from the materialiser's existing `OBJECT_HAS_PROPERTY`/
`OBJECT_HAS_FUNCTION`/`FUNCTION_INPUT_TYPE`/`FUNCTION_OUTPUT_TYPE` + inheritance edges (proven by
`probe_python_api.py` transitive closure); verify against that path first, and add backend
plumbing (e.g. a next-rank type-graph fetch endpoint, or instance-object-model resolution) only
where a real gap exists. New backend work is in-budget for this phase; it is NOT a license to
move layout/type COMPUTATION into the frontend.

### D-04 — Brace render states PULLED INTO PHASE 7 (user choice)
Implement the three §O.1a brace render states in this phase, ahead of Phase 8's halo transport:
braced-hidden (`{ref}` to a hidden node keeps braces), revealed-internal (right-click unfolds
rank-1 fields inline; braces drop, children indent), resolved-external (`{ref}` to an
already-visible node resolves to a SOLID link). The underlying graph link is identical across
all three — internal/external + folded/unfolded are RENDERING choices over one invariant graph.
Panel↔graph node-count parity holds (revealing in one reveals in both). The 2D↔3D solid arrow
from Phase 6 (REAL-04) is the resolved-external link substrate.

### Locked-by-design (NOT re-decided — from object_exploration.md / DOMAIN_MODEL §M/§N/§O.1a / §7.3.4)
- Seven-gesture model + §18.32 non-collision rules (button disambiguates single-left edit vs
  right-click fold; double-right delete vs single-right fold; left-drag wire vs left-click edit;
  right-click-self collapse vs right-click-child fold). Read-only python-native nodes (🔒):
  single-left is a no-op highlight; hover/right-click/double-left always work.
- Rank-1 minimalism as a pro-pattern (N.4/N.5): a user compute node renders TYPE-STRIPPED
  (purely structural over `\t`+`\n`, each field a literal / optional organising label / `{ref}`);
  types persist internally for inverse lookup but are NOT presented. Raw object inspection panels
  (§9.6.1) DO show `key:Type=value`.
- `{ref}` = activation of a memory-access procedure (N.10); names may contain spaces (tree
  discerned over `\t`+`\n` only); braceless = literal/label.
- Fold state persisted in `ui.node_fold_state[card_id] = { expanded_paths: [...] }`, preserved
  across collapse/re-expand (M.6); `panel-gesture-fold-roundtrip` env-scenario asserts it.
- Functions = memory map from typed inputs to inferred output type (M.5/M.9): forward renders
  output when inputs bound; inverse (closest-inverse §7.7) surfaces inputs when output known.
- Theme: black-core + silver-outline, type slot in `--text-dim`, `{ref}` faint `--silver-700`
  underline; no colour except the halo phantom exception zone (theme.md / field_tree.md §10).
- D10 backend-computes/frontend-renders; no-mocks/all_real contract; verification idiom =
  env-scenario + probe + e2e, never screenshots.
</decisions>

<code_context>
## Existing Code Insights

### Reusable assets (served fe/, the port TARGET — extend these per D-02)
- `backend/static/js/fe/magic_markdown_gestures.mjs` (+ .test.mjs) — existing gesture dispatch scaffolding
- `backend/static/js/fe/magic_markdown_panel.mjs` (+ .test.mjs) — pinned typed-panel render + fold host (Phase 6 added `data-3d-node-id` here)
- `backend/static/js/fe/gateway.mjs` — the GestureGateway action contract (ui-node-expand/-collapse, ui-compile-expand/-collapse, concept-edge-create, halo-focus)
- `backend/static/js/fe/store.mjs` — WorkspaceStore (concepts/edges/index/ui.node_fold_state)
- `backend/static/js/fe/magic_markdown_halo.mjs` — halos on blank/text fields (M.10 / §O.3 gating); composes with exploration
- `backend/static/js/fe/projector.mjs` — Phase 6's 2D↔3D solid link (resolved-external brace substrate, D-04)

### The cp/ feature reference (port FROM — do NOT resurrect the surface)
- `cp/concept_graph.js` — `_pythonNativeTypedView`, rank-1 inline `node_fold`, the 🔒 read-only rule
- `cp/interaction.js` — seven-gesture dispatch + non-collision rules (§18.32)
- `cp/edge_manager.js` — drag-wire link creation + I/O-type inheritance (N.4)
- `cp/instance_manager.js` — object-instance inheritance (M.11 / §9 / §15.9)

### Backend (consume first; extend per D-03 only where a real gap exists)
- the PythonAPIMaterialiser — `OBJECT_HAS_*` / `FUNCTION_*_TYPE` + inheritance edges (probe_python_api.py proves transitive closure)
- closest-inverse lookup (§7.7) for unbound-input functions
- WebBrowser fixture `scan`/`scanner` (the DuckDuckGo walkthrough's real scanner)

### Verification surface
- REPL `scripts/sim_frontend.py` env-scenarios: `node-fold-roundtrip` / `panel-gesture-fold-roundtrip` (fold preservation), `editor-link` / `editor-delete` (gesture telemetry), `ontology-walk`, plus the NEW `duckduckgo-walkthrough` (EXPLORE-04)
- Playwright `frontend_e2e/` — extend with hover-type-graph, ref-propagation render, drag-wire+delete, brace-state, and DuckDuckGo e2e
- probe — a `probe_python_api.py`-adjacent / new `probe_live_*` for the EXPLORE-04 real-subsystem run (D-01)
</code_context>

<specifics>
## Specific Ideas

The DuckDuckGo §N walkthrough is the canonical acceptance example (object_exploration.md §5.1):
begin in graph form → left-drag the WebBrowser `scanner` onto `DuckDuckGo` (inherits I/O types +
object model, N.4) → final panel presents NO types (`DuckDuckGo / {scanner}`) → right-click
`{scanner}` reveals type-stripped rank-1 `url{}`/`dom{}` → bind inputs by reference (names may
have spaces) → call completes to a ShadowDOM whose full per-sample distribution lives in the 3D
Real register while the 2D node stays rank-1 → `chunk {chunk samples}` per-sample iteration only
fires when a downstream link externally references the recursively-chunked iterable (N.9).
EXPLORE-01's worked example: hovering `driver: WebDriver = {driver}` previews the WebDriver object
model (super:BaseWebDriver + typed attrs), each attr itself right-click-expandable to a further rank.
</specifics>

<deferred>
## Deferred Ideas

- Halo cone-ray transport by normalized triple-product similarity (§O.18) — Phase 8 (HALO-03/04).
- 2D per-sample `{chunk samples}` stepper driving 3D focus one-way (§O.6) — Phase 8 (STEP-01).
- Cascaded recurrent renderer / readout perimeter / bisector projector node (§7.8/§P) — Phase 9.
- Deep multi-hop reference auto-resolution UX (object_exploration.md §1 "Remaining") — beyond rank-1; only rank-1 minimalism is in scope here.
</deferred>
