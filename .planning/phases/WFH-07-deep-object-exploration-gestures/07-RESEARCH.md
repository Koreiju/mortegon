# Phase 7: Deep Object-Exploration Gestures - Research

**Researched:** 2026-06-23
**Domain:** Brownfield port — legacy `cp/*.js` 3D-projector interaction code → served `fe/` black-slate 2D gesture/panel modules; backend type-graph endpoint design
**Confidence:** HIGH (in-repo code archaeology; nearly every claim is `[VERIFIED: codebase]` via direct file reads)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — EXPLORE-04 verification depth: REAL-SUBSYSTEM INLINE.** The DuckDuckGo §N walkthrough is verified end-to-end against REAL subsystems IN THIS PHASE (not deferred). Phase gate includes a live run: real Selenium DuckDuckGo scan + real materialiser type graph, exercised by a `duckduckgo-walkthrough` REPL env-scenario AND a `probe_live_*`-style probe asserting the §N flow (author `self=duckduckgo` referencing `scan` → drag-wire the WebBrowser scanner → reveal rank-1 `url{}`/`dom{}` → per-sample chunk iteration on `{chunk samples}`). Honor the clean-GPU lesson: confirm 0 stray python/firefox + ~0 VRAM before the real boot; drive the real backend lifecycle from the main context (NOT a verifier subagent that can wedge CUDA). Stub-backed e2e + REPL scenario must ALSO stay green (both modes) as the fast gate; the real run is the acceptance proof on top.

**D-02 — Port host: EXTEND EXISTING fe/ GESTURE MODULES.** Port the cp/ exploration features into the existing served fe/ gesture scaffolding rather than a new top-level module: `magic_markdown_gestures.mjs` (gesture dispatch), `magic_markdown_panel.mjs` (the typed `key:Type=value` panel render + fold), `gateway.mjs` (the GestureGateway action contract). Add a new fe/ module only where a clean seam genuinely requires it. The cp/ feature references to port FROM: `cp/concept_graph.js` (`_pythonNativeTypedView`, rank-1 inline fold `node_fold`), `cp/interaction.js` (the seven-gesture dispatch + non-collision rules §18.32), `cp/edge_manager.js` (drag-wire link creation + type inheritance), `cp/instance_manager.js` (instance-inheritance §9 / M.11). Do NOT resurrect the cp/ surface; bring its FEATURES into fe/.

> **RESEARCH CORRECTION (HIGH confidence, verified by direct read):** D-02's attribution of `cp/edge_manager.js` ("drag-wire link creation + type inheritance") and `cp/instance_manager.js` ("object-instance inheritance") is **factually wrong**. Both files are pure THREE.js 3D-rendering mixins (edge-line geometry rebuild / InstancedMesh pool management) with ZERO 2D gesture or type-inheritance logic. The actual legacy home of the typed-panel/fold/read-only logic the doc describes is **`cp/concept_graph.js`** (confirmed: `_pythonNativeTypedView`, the 🔒 read-only gating block, and the `node_fold` contextmenu handler all live there — see Code Examples below). There is **no legacy reference implementation anywhere** for N.4's drag-wire-creates-edge-AND-inherits-I/O-types behavior, nor for N.6/M.11's duplicate-instance-proxy semantics — these must be **designed fresh** against the `object_exploration.md` spec, not ported from existing code. Planner: do not assign tasks expecting to "port from edge_manager.js/instance_manager.js" — there is nothing there to port.

**D-03 — Type-graph data source: NEW BACKEND TYPE ENDPOINTS ALLOWED AS NEEDED.** Frontend still renders (never computes) the type graph — D10 holds — but the planner may add new backend endpoints/edges where the existing materialiser surface does not already expose what next-rank expansion needs. Start from the materialiser's existing `OBJECT_HAS_PROPERTY`/`OBJECT_HAS_FUNCTION`/`FUNCTION_INPUT_TYPE`/`FUNCTION_OUTPUT_TYPE` + inheritance edges (proven by `probe_python_api.py` transitive closure); verify against that path first, and add backend plumbing (e.g. a next-rank type-graph fetch endpoint, or instance-object-model resolution) only where a real gap exists. New backend work is in-budget for this phase; it is NOT a license to move layout/type COMPUTATION into the frontend.

**D-04 — Brace render states PULLED INTO PHASE 7.** Implement the three §O.1a brace render states in this phase, ahead of Phase 8's halo transport: braced-hidden (`{ref}` to a hidden node keeps braces), revealed-internal (right-click unfolds rank-1 fields inline; braces drop, children indent), resolved-external (`{ref}` to an already-visible node resolves to a SOLID link). The underlying graph link is identical across all three — internal/external + folded/unfolded are RENDERING choices over one invariant graph. Panel↔graph node-count parity holds (revealing in one reveals in both). The 2D↔3D solid arrow from Phase 6 (REAL-04) is the resolved-external link substrate.

**Locked-by-design (NOT re-decided — from object_exploration.md / DOMAIN_MODEL §M/§N/§O.1a / §7.3.4):**
- Seven-gesture model + §18.32 non-collision rules (button disambiguates single-left edit vs right-click fold; double-right delete vs single-right fold; left-drag wire vs left-click edit; right-click-self collapse vs right-click-child fold). Read-only python-native nodes (🔒): single-left is a no-op highlight; hover/right-click/double-left always work.
- Rank-1 minimalism as a pro-pattern (N.4/N.5): a user compute node renders TYPE-STRIPPED (purely structural over `\t`+`\n`, each field a literal / optional organising label / `{ref}`); types persist internally for inverse lookup but are NOT presented. Raw object inspection panels (§9.6.1) DO show `key:Type=value`.
- `{ref}` = activation of a memory-access procedure (N.10); names may contain spaces (tree discerned over `\t`+`\n` only); braceless = literal/label.
- Fold state persisted in `ui.node_fold_state[card_id] = { expanded_paths: [...] }`, preserved across collapse/re-expand (M.6); `panel-gesture-fold-roundtrip` env-scenario asserts it.
- Functions = memory map from typed inputs to inferred output type (M.5/M.9): forward renders output when inputs bound; inverse (closest-inverse §7.7) surfaces inputs when output known.
- Theme: black-core + silver-outline, type slot in `--text-dim`, `{ref}` faint `--silver-700` underline; no colour except the halo phantom exception zone (theme.md / field_tree.md §10).
- D10 backend-computes/frontend-renders; no-mocks/all_real contract; verification idiom = env-scenario + probe + e2e, never screenshots.

### Claude's Discretion
(None explicitly delegated beyond what D-01..D-04 already bound — CONTEXT.md is fully decision-locked for this phase via smart-discuss autonomous mode.)

### Deferred Ideas (OUT OF SCOPE)
- Halo cone-ray transport by normalized triple-product similarity (§O.18) — Phase 8 (HALO-03/04).
- 2D per-sample `{chunk samples}` stepper driving 3D focus one-way (§O.6) — Phase 8 (STEP-01).
- Cascaded recurrent renderer / readout perimeter / bisector projector node (§7.8/§P) — Phase 9.
- Deep multi-hop reference auto-resolution UX (object_exploration.md §1 "Remaining") — beyond rank-1; only rank-1 minimalism is in scope here.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXPLORE-01 | Hover expands the next-rank type graph (super-class + typed constructor params); function rows expand to loosely-linked typed input/output fields; output types inferred by i/o equality. (§M.4/§M.5) | `python_api_materialiser.py` already produces all needed edges (`OBJECT_HAS_PROPERTY`/`OBJECT_HAS_FUNCTION`/`FUNCTION_INPUT_TYPE`/`FUNCTION_OUTPUT_TYPE`); `cp/concept_graph.js`'s `_pythonNativeTypedView` is the reference rendering algorithm; gap = no GET endpoint to fetch rank-1 neighbors by edge-type, and `fe/magic_markdown.mjs` has zero `key:Type=value` rendering mode. See Architecture Patterns + Don't Hand-Roll. |
| EXPLORE-02 | External node references propagate as their own recursively-rendered panels (rank-1 minimalism, a PRO-pattern); a `{ref}` is a duplicate instance that operationally calls the originating object. (§N.3/§N.6/§N.7/§N.14) | `integration.test.mjs` already proves rank-1 inline-fold-on-right-click works for an EXTERNAL `{ref}` token end-to-end at the pure-model level (`renderPanel`+`toggle`+`buildRegistry`). Gap = no duplicate-instance-proxy semantics anywhere (N.6) — this is greenfield design within fe/, no legacy precedent. See Common Pitfalls + Open Questions. |
| EXPLORE-03 | Left-click-drag wires nodes in graph form (target inherits i/o types); double-right-click deletes a token reference/instance in panel or graph form. (§N.4/§N.13) | `resolveGesture` already classifies `WIRE_LINK`/`DELETE_REF`; `gateway.mjs`'s `buildRequest` already maps `WIRE_LINK`→`POST /api/concept_edges` and `DELETE_REF`→`POST /api/ui/edit_close`. Gaps: (a) NO DOM mousedown/mousemove/mouseup drag-state machine exists in `magic_markdown_panel.mjs::mount()`; (b) NO contextmenu/dblclick(right) handlers exist either, so right-click/double-right never reach the resolver in the browser; (c) backend `editor_link`/`POST /concept_edges` create a plain edge with NO type-inheritance side effect (verified, `EditorLinkRequest` has no type fields); (d) `DELETE_REF`→`edit_close` only clears a value, it does not delete the underlying `ConceptEdge` row — likely needs to ALSO call `DELETE /concept_edges/{edge_id}` for N.13 to be a true delete. See Architecture Patterns + Don't Hand-Roll + Common Pitfalls. |
| EXPLORE-04 | The DuckDuckGo walkthrough runs end-to-end (REPL scenario + probe): author `self=duckduckgo` referencing `scan`, drag-wire the WebBrowser scanner, reveal rank-1 `url{}`/`dom{}`, per-sample chunk iteration on `{chunk samples}`. (§N.2–§N.10) | No `duckduckgo-walkthrough` REPL scenario or `probe_live_*` exists yet (Wave 0 gap, confirmed by grep). `node-fold-roundtrip` scenario + `editor-link`/`editor-delete`/`ui-dominance-collapse` REPL actions are the closest existing patterns to model from. `magic_markdown.mjs`'s `iterableNode`/`advanceSignal` already implements N.9 per-sample iteration at the model level. See Validation Architecture + Code Examples. |
</phase_requirements>

## Summary

This phase is almost entirely **in-repo code archaeology**, not external-library research: every relevant subsystem already exists in this codebase, either as a working reference (the legacy `cp/concept_graph.js`, which the planner should consult instead of the CONTEXT.md-cited `edge_manager.js`/`instance_manager.js`) or as a partially-built target (`fe/magic_markdown_gestures.mjs` + `fe/magic_markdown_panel.mjs` + `fe/gateway.mjs` + `fe/store.mjs`).

The single most important finding: **the pure-logic gesture resolver (`resolveGesture` in `magic_markdown_gestures.mjs`) and the action-to-request mapper (`buildRequest` in `gateway.mjs`) already implement ALL SEVEN gestures correctly at the unit level** (proven by passing tests in `magic_markdown_gestures.test.mjs` and `integration.test.mjs`). The actual gap for EXPLORE-01..03 is downstream: (1) `magic_markdown_panel.mjs::mount()` only wires `click` and `dblclick` — it has **no `contextmenu`, no double-right-click, and no drag (`mousedown`/`mousemove`/`mouseup`) DOM event capture at all**, so right-click-fold, double-right-delete, and drag-wire gestures never reach the already-correct resolver in a real browser; (2) `magic_markdown.mjs`'s rendering model has **no `key:Type=value` typed rendering mode** anywhere — it is purely structural by design (correct for rank-1-minimalism compute nodes, but EXPLORE-01's "raw object inspection panel" needs a net-new typed-line rendering path); (3) the backend has **no rank-1 type-graph fetch endpoint** and **no I/O-type-inheritance side effect on edge creation** — both are real, scoped gaps that justify D-03's "new backend endpoints allowed."

For EXPLORE-04, the REPL/probe infrastructure pattern is well-established (`node-fold-roundtrip` scenario, `editor-link`/`editor-delete` actions, `probe_python_api.py`'s assertion style) but the specific `duckduckgo-walkthrough` scenario and its `probe_live_*` counterpart do not exist yet — this is pure Wave-0 net-new work following an existing, well-proven template.

**Primary recommendation:** Treat this phase as three layers of net-new wiring over already-correct pure logic — (1) DOM event capture for right-click/double-right-click/drag in `magic_markdown_panel.mjs::mount()`, (2) a new typed-rendering mode in `magic_markdown.mjs`/`magic_markdown_panel.mjs` for raw-object panels, (3) two new backend endpoints (rank-1 type-graph fetch; edge-create with I/O-type-inheritance) — plus one net-new REPL scenario + probe for EXPLORE-04. Do not budget time hunting for drag-wire/instance-inheritance code in `cp/edge_manager.js` or `cp/instance_manager.js` — it does not exist there.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Seven-gesture intent resolution (button/clicks/target → action) | Browser / Client | — | Pure function of DOM event metadata; `resolveGesture` already correct and stateless — no backend round-trip needed to classify a gesture. |
| DOM event capture (mousedown/mousemove/mouseup, contextmenu, dblclick-right) | Browser / Client | — | `mount()`'s job; pure DOM wiring, zero business logic. |
| Type-graph next-rank data (which edges/nodes a node's rank-1 neighbors are) | API / Backend | Database / Storage | D10: type-graph traversal is computation over the ConceptEdge table — must stay backend. `python_api_materialiser.py` already writes the edges; a backend route must read+shape them for the frontend to render. |
| Typed-line rendering (`key:Type=value` vs type-stripped) | Browser / Client | — | Pure presentation choice over already-fetched data — rendering, not computation; belongs in `magic_markdown.mjs`/`magic_markdown_panel.mjs`. |
| I/O-type inheritance on drag-wire (N.4) | API / Backend | — | Requires reading the source node's `ports.inputs`/`outputs` (or materialiser edges) and writing them onto the target — a graph mutation with derived data, not a pure rendering decision; belongs server-side per D10, gated through the existing lifecycle dispatcher. |
| Duplicate-instance proxy semantics (N.6) | API / Backend | Browser / Client (render only) | "Operationally calls the originating object" implies the backend resolves what a duplicate instance's behavior actually is (which backing pointer it proxies to); frontend only renders the resulting panel. |
| Fold-state persistence (`ui.node_fold_state`) | API / Backend | Browser / Client (cache) | Already correctly built: `ui_state_service.py` owns the authoritative dict; `store.mjs` mirrors it via WS frames — standard backend-source-of-truth/frontend-cache split, already matches D10. |
| Brace render-state selection (braced-hidden / revealed-internal / resolved-external) | Browser / Client | API / Backend (fold state + visibility flags) | The three states are a pure rendering decision over backend-supplied facts (is target node visible? is the ref folded?) — classic D10 split, no new backend logic needed beyond what visibility/fold state already provides. |
| Resolved-external solid 2D↔3D link line | Browser / Client | — | Phase 6's `projector.mjs` REAL-04 substrate already computes/draws this; Phase 7 reuses it unchanged. |
| DuckDuckGo scan trigger + chunk streaming | API / Backend | Database / Storage | `WebBrowserManager`/scan WS pipeline already backend-owned; Phase 7 only consumes its output through the existing `{chunk samples}` iterable model. |

## Standard Stack

No new external packages are required for this phase. This is a pure in-repo extension of existing modules (`fe/*.mjs`, `backend/api/routes.py`, `backend/services/*.py`) using the project's existing stack (vanilla ESM JS frontend, FastAPI backend, Kuzu graph store). The Package Legitimacy Gate is **N/A** — explicitly stated below.

## Package Legitimacy Audit

**N/A — this phase installs no external packages.** All work extends existing in-repo modules. No `npm install` / `pip install` is anticipated. If the planner discovers a need for a new dependency during planning, the Package Legitimacy Gate must be run at that time; as of this research pass, no such need was identified.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────── Browser (served fe/, editor.html) ───────────────────────────┐
│                                                                                            │
│  mouse/keyboard event  ──▶  magic_markdown_panel.mjs::mount()                            │
│                              │  (TODAY: click + dblclick only)                            │
│                              │  (GAP: contextmenu, double-right, drag NOT captured)        │
│                              ▼                                                            │
│                       magic_markdown_gestures.mjs::resolveGesture(g)                      │
│                              │  {button, clicks, target, drag, mode} → Action             │
│                              │  (ALREADY CORRECT for all 7 actions)                        │
│                              ▼                                                            │
│                       gateway.mjs::buildRequest(action, ...)                              │
│                              │  Action → {method, path, body}                             │
│                              │  (ALREADY CORRECT mapping; 2 backend gaps found, see below) │
│                              ▼                                                            │
│                       fetch(path, {method, body})  ──────────────────┐                    │
│                                                                       │                    │
│  WS frame  ◀── store.mjs::applyFrame(state, frame) ◀──────── WS  ◀───┤                    │
│       │                                                              │                    │
│       ▼                                                              │                    │
│  magic_markdown.mjs::renderPanel/renderGraph(node, {registry,        │                    │
│       expanded, ...}) → Line[] / GraphNode[]                         │                    │
│       │  (GAP: no key:Type=value typed-line mode for raw objects)    │                    │
│       ▼                                                              │                    │
│  magic_markdown_panel.mjs::panelVDom/graphVDom → DOM                 │                    │
│       │                                                              │                    │
│       ▼                                                              │                    │
│  projector.mjs (Phase 6 REAL-04) — solid 2D↔3D link line             │                    │
│       (reused unchanged for resolved-external brace state)           │                    │
└────────────────────────────────────────────────────────────────────────┼───────────────────┘
                                                                          │
┌──────────────────────────────── Backend (FastAPI, backend/api/routes.py) ─────────────────┘
│
│  POST /concept_edges  ──▶ create_concept_edge ──▶ apply_edge_create_lifecycle
│       (GAP: no I/O-type-inheritance side effect on the new edge's target node — N.4)
│
│  POST /ui/node_fold ──▶ ui_state_service.set_node_fold  (ALREADY CORRECT, matches spec)
│
│  POST /ui/edit_close ──▶ clears a value  (DELETE_REF maps here; N.13 needs edge delete too)
│
│  (GAP — NEW endpoint needed) GET /api/concepts/{id}/next_rank
│       → filter ConceptEdge rows by source_id + edge_type ∈
│         {OBJECT_HAS_PROPERTY, OBJECT_HAS_FUNCTION, FUNCTION_INPUT_TYPE, FUNCTION_OUTPUT_TYPE}
│         → resolve target ConceptNodes → return rank-1 typed neighbor list
│
│  python_api_materialiser.py ──▶ writes OBJECT_HAS_*/FUNCTION_*_TYPE edges (ALREADY BUILT)
│
│  WebBrowserManager (selenium_client.py) ──▶ real scan ──▶ chunk WS stream (ALREADY BUILT,
│       reused unchanged by EXPLORE-04's DuckDuckGo walkthrough)
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

No new top-level directories. Extend in place:

```
backend/static/js/fe/
├── magic_markdown.mjs            # EXTEND: add typed-line (key:Type=value) render mode
├── magic_markdown_gestures.mjs   # NO CHANGE EXPECTED — already correct
├── magic_markdown_panel.mjs      # EXTEND: mount() — add contextmenu, double-right, drag handlers
├── gateway.mjs                   # EXTEND: WIRE_LINK body may need an "inherit_types" flag;
│                                 #         DELETE_REF may need to also fire a concept_edges DELETE
├── store.mjs                     # LIKELY NO CHANGE — node_fold_state already flows via ui_state_changed
├── projector.mjs                 # NO CHANGE — REAL-04 solid link reused as-is for resolved-external
└── magic_markdown_halo.mjs       # NO CHANGE EXPECTED — composes independently per CONTEXT.md

backend/
├── api/routes.py                 # ADD: GET /concepts/{id}/next_rank (or similar; planner decides
│                                 #      route shape); EXTEND: POST /concept_edges or /editor/link
│                                 #      with optional type-inheritance step (N.4)
└── services/
    ├── python_api_materialiser.py   # NO CHANGE EXPECTED — edges already correct/idempotent
    └── ui_state_service.py          # NO CHANGE EXPECTED — node_fold_state already correct

scripts/
├── sim_frontend.py               # ADD: duckduckgo-walkthrough env-scenario (+ supporting REPL
│                                 #      actions if any new backend endpoint needs a verb)
└── probe_live_duckduckgo_walkthrough.py   # ADD: new probe, modeled on probe_python_api.py /
                                            #      probe_live_archive_scan.py patterns

frontend_e2e/
└── object_exploration.spec.js    # ADD: hover-type-graph, ref-propagation, drag-wire+delete,
                                   #      brace-state e2e coverage (none exist today)
```

### Pattern 1: Gesture resolution is already a pure, fully-tested function — do not touch it

**What:** `resolveGesture({button, clicks, target, drag, mode})` in `magic_markdown_gestures.mjs` returns one of seven `Action` enum values via simple conditional branching on event metadata, with no DOM or network dependency.

**When to use:** Any new DOM handler the planner adds (contextmenu, drag, double-right) should call this SAME function with the correctly-populated event-metadata object — never duplicate gesture-classification logic inline in the new handlers.

**Example:**
```javascript
// Source: backend/static/js/fe/magic_markdown_gestures.mjs (verified, existing code)
export const Action = {
  EDIT_TOKEN: "edit_token", TOGGLE_FOLD: "toggle_fold",
  COLLAPSE_TO_NODE: "collapse_to_node", TOGGLE_PANEL_GRAPH: "toggle_panel_graph",
  WIRE_LINK: "wire_link", DELETE_REF: "delete_ref", NONE: "none",
};
export function resolveGesture(g = {}) {
  const { button = "left", clicks = 1, target = "body", mode = "panel", drag = false } = g;
  if (button === "left" && drag) return { action: Action.WIRE_LINK };
  if (button === "left") {
    if (clicks === 2) {
      if (target === "body" || target === "self") return { action: Action.TOGGLE_PANEL_GRAPH };
      return resolveGesture({ ...g, clicks: 1 });
    }
    if (target === "dropdown") return { action: Action.TOGGLE_FOLD };
    if (target === "ref" || target === "token") return { action: Action.EDIT_TOKEN };
    return { action: Action.NONE };
  }
  if (button === "right") {
    if (clicks === 2) {
      if (target === "ref" || target === "token") return { action: Action.DELETE_REF };
      return { action: Action.NONE };
    }
    if (target === "self") return { action: Action.COLLAPSE_TO_NODE };
    if (target === "ref" || target === "dropdown" || target === "token") return { action: Action.TOGGLE_FOLD };
    return { action: Action.NONE };
  }
  return { action: Action.NONE };
}
```

### Pattern 2: The legacy typed-view + read-only-gating reference lives in `cp/concept_graph.js`, NOT `edge_manager.js`/`instance_manager.js`

**What:** The actual prior-art rendering algorithm for EXPLORE-01's "raw object inspection panel shows `key:Type=value`" requirement.

**When to use:** When implementing the new typed-line rendering mode in `magic_markdown.mjs`/`magic_markdown_panel.mjs`.

**Example:**
```javascript
// Source: backend/static/js/cp/concept_graph.js (verified, existing legacy code, lines ~1366-1393)
// _pythonNativeTypedView(rawData) — parses materialiser JSON (d.signature, d.ports.inputs/outputs),
// renders "name: Type" lines + "→ ReturnType" for functions, or a member list for objects.

// Read-only 🔒 gating (verified, ~lines 1684-1708):
const ro = /^fixture::/.test(node.backing_pointer || "") || /^python_/.test(node.type_hint || "");
// → renders a 🔒 span, sets readOnly=true on inputs, hides the "add row" grow-affordance,
//   and calls _pythonNativeTypedView() when type_hint starts with "python_".
```

**Port guidance:** Re-implement this ALGORITHM (parse signature/ports JSON → typed lines) as a pure function inside `magic_markdown.mjs` (e.g. `renderTypedPanel(node, opts)`), not as a literal copy-paste — the legacy version operates on THREE.js card DOM nodes and Babylon-era data shapes; the port target is the `Line[]`/vdom model `magic_markdown.mjs` already uses for `renderPanel`.

### Pattern 3: Backend fold-state infrastructure is fully built and correct — verify, don't rebuild

**What:** `UIState.node_fold_state: Dict[str, Dict[str, Any]]` exactly matches the doc's `{card_id: {expanded_paths: [...], updated_at: epoch}}` shape.

**Example:**
```python
# Source: backend/services/ui_state_service.py (verified, existing code, ~lines 149-198)
def set_node_fold(self, workspace_id, card_id, field_path, *, expanded=True):
    """Toggles field_path in/out of node_fold_state[card_id]['expanded_paths'];
    removes the card_id entry entirely once its list empties; stamps updated_at;
    emits a 'node_fold' broadcast event."""
```

```python
# Source: backend/api/routes.py line 4384-4394 (verified, existing route)
@router.post("/ui/node_fold")
def ui_node_fold(req: UINodeFoldRequest):
    svc = get_ui_state_service(broadcast=_ws_push)
    snap = svc.set_node_fold(req.workspace_id, req.card_id, req.field_path, expanded=bool(req.expanded))
    return {"ok": True, "state": snap.to_dict(), "node_fold_state": snap.node_fold_state}
```

**Addressing-scheme nuance (important for planner):** The legacy `cp/concept_graph.js` node_fold handler addresses fold state by the **literal `{ref}` token TEXT** (regex-matched from `caretRangeFromPoint`, passed as `field_path: tok`). `object_exploration.md` §8 and `fe/magic_markdown.mjs`'s existing `renderPanel` instead produce a **structural dotted/slash path** (e.g. `"0.0/1"`) via its `path` field on each rendered `Line`. The backend schema (`expanded_paths: [...]`) is agnostic to which scheme is used — it just stores strings. **Recommendation: use the existing `fe/` `path` scheme, not legacy token-text** — `gateway.mjs`'s `Action.TOGGLE_FOLD` → `/api/ui/node_fold` mapping already passes `g.path` as `node_path`, so this is the path of least resistance and avoids a second addressing scheme entering the codebase.

### Anti-Patterns to Avoid
- **Hunting for drag-wire/instance-inheritance logic in `cp/edge_manager.js` or `cp/instance_manager.js`:** confirmed these files are pure THREE.js 3D-geometry mixins (edge-line rebuild, InstancedMesh pooling) with no 2D gesture or type-inheritance code whatsoever. There is nothing to port from them for N.4/N.6/M.11 — design fresh against the doc spec.
- **Duplicating gesture-classification logic in new DOM handlers:** always call the existing `resolveGesture()`, never inline new `if (button === ...)` branches elsewhere.
- **Inventing a second fold-state addressing scheme:** use the existing `fe/` structural `path`, not legacy token-text matching.
- **Computing type-graph traversal in the frontend:** D10 — any "which nodes does X relate to by edge-type Y" computation belongs in a backend route, even if it feels like "just filtering."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gesture classification (button/clicks/target → action) | A new switch/if-chain in the DOM handler | `resolveGesture()` (already exists, already tested) | Avoids drift between the documented §18.32 non-collision matrix and a second ad-hoc implementation. |
| Request shaping per action | Inline `fetch()` calls scattered in handlers | `gateway.mjs`'s `buildRequest(gesture)` / `GestureGateway(store, opts).send` | Centralizes the action→HTTP mapping; existing tests already cover most of it. |
| Fold-state storage/toggle semantics | A new fe/-local fold-state cache | `ui_state_service.py::set_node_fold` (backend authoritative) + `store.mjs`'s existing `ui_state_changed` merge | Backend is already correct and matches the doc's exact dict shape; re-deriving it client-side would desync from WS-pushed truth. |
| Type-graph edge production (materialiser) | A new walker that re-inspects Python objects from the frontend or a second backend service | `python_api_materialiser.py` (already produces `OBJECT_HAS_*`/`FUNCTION_*_TYPE` edges, proven idempotent + transitively-closed by `probe_python_api.py`) | D10 + avoiding duplicate graph-writers; the materialiser is the single source of type-graph truth. |
| Per-sample iterable advance (N.9 `{chunk samples}`) | A new iteration/cursor model | `magic_markdown.mjs`'s existing `iterableNode`/`isIterable`/`advanceSignal` | Already implements exactly this; EXPLORE-04 only needs to drive it with real DuckDuckGo chunk data, not reinvent it. |

**Key insight:** Nearly every "hand-roll" risk in this phase is the temptation to re-derive logic that already exists correctly somewhere in the repo (pure gesture resolution, request building, fold-state, iteration) because the planner hasn't yet wired the DOM/HTTP glue around it. The actual net-new work is narrow: DOM event capture, one new rendering mode, and (at most) two backend endpoints/extensions.

## Common Pitfalls

### Pitfall 1: Treating `DELETE_REF`'s existing mapping as a complete delete
**What goes wrong:** `gateway.mjs` currently maps `Action.DELETE_REF` → `POST /api/ui/edit_close`, which clears a **value** (a data edit). N.13 describes deleting "that reference/instance" — if the `{ref}` also corresponds to a `ConceptEdge` record (e.g. created via drag-wire), the edge row survives a value-clear.
**Why it happens:** `edit_close` was originally built for the EDIT_TOKEN flow (close an in-place text edit), and `DELETE_REF` was mapped onto it because it's the closest existing verb, not because it's semantically complete.
**How to avoid:** When implementing EXPLORE-03's double-right-delete, check whether the deleted `{ref}` corresponds to a `ConceptEdge`; if so, also fire `DELETE /api/concept_edges/{edge_id}` (route already exists, confirmed in routes.py). Decide and document this explicitly rather than leaving a silent partial-delete.
**Warning signs:** A REPL/e2e test that deletes a wired reference and then finds the edge still present in `list_concept_edges`.

### Pitfall 2: Assuming `editor_link`/`POST /concept_edges` already does type inheritance
**What goes wrong:** N.4 requires the drag-wire target to inherit the source's I/O types + object model. The existing `editor_link` backend handler (verified, `routes.py` ~5110-5149) and `EditorLinkRequest` Pydantic model (verified, ~5043-5051) only accept `source_id`/`target_id`/`edge_type` (default `RELATES_TO`) — there is **no type-inheritance side effect** anywhere in this path today.
**Why it happens:** `editor_link`/`/concept_edges` were built as a generic edge-creation primitive (correctly routed through the lifecycle dispatcher) before N.4's specific inheritance requirement existed.
**How to avoid:** This is exactly the kind of gap D-03 anticipates. Plan a deliberate extension point — either a new request field (e.g. `inherit_types: bool`) on the existing edge-create path, or a dedicated new endpoint that wraps edge-create + a type-copy step reading the source node's `ports`/materialiser edges and writing equivalent edges/fields onto the target.
**Warning signs:** A drag-wire e2e test where the target panel never gains the source's typed fields after the wire completes.

### Pitfall 3: Building a parallel typed-rendering path that breaks rank-1 minimalism
**What goes wrong:** EXPLORE-01 needs `key:Type=value` rendering for RAW OBJECT panels, but N.4/N.5 require USER COMPUTE NODES to stay type-stripped. If the new typed-rendering mode is wired in as the default for `renderPanel`, it will leak types onto every compute-node panel, violating the locked rank-1-minimalism pattern.
**Why it happens:** It's tempting to add one universal "show types" flag rather than gating it specifically on `type_hint` starting with `python_` (the same gate the legacy 🔒 read-only logic already uses).
**How to avoid:** Gate the new typed-rendering mode on the SAME condition the legacy read-only check uses (`/^python_/.test(node.type_hint||'')` or `read_only:true` + `no_datablock:true`), not on a separate flag, so the two concerns (read-only-ness and typed-rendering) stay coupled the way the legacy reference implementation couples them.
**Warning signs:** A user-authored compute node panel unexpectedly showing `field:str=value` instead of plain `field: value`.

### Pitfall 4: Missing the double-right-click DOM event entirely
**What goes wrong:** Browsers don't natively fire a "double-right-click" event the way `dblclick` fires for left-clicks. The existing `mount()` only listens for `contextmenu` (which fires once per right-click) and ordinary `dblclick` (left-button only, per the DOM spec). A correct double-right-click detector needs manual timestamp-based debouncing on consecutive `contextmenu` events.
**Why it happens:** It's easy to assume `dblclick` covers all double-click cases; it does not — `dblclick` is left-button-only per the DOM UIEvent spec.
**How to avoid:** Implement double-right detection as a small stateful helper (track last `contextmenu` timestamp + target; if a second `contextmenu` fires on the same target within a threshold — e.g. 400ms — synthesize `{button:"right", clicks:2, target}` and call `resolveGesture`).
**Warning signs:** Right-clicking twice quickly only ever triggers the single-right-click fold action, never delete.

### Pitfall 5: Wedging CUDA/Selenium during the EXPLORE-04 real-subsystem verification
**What goes wrong:** Per the project's documented env lesson (MEMORY.md, STATE.md), long Claude sessions can leave stray python/firefox processes and non-zero VRAM that wedge the next real backend boot (uninterruptible CUDA/Selenium hangs).
**Why it happens:** Previous real-subsystem probes were sometimes run from a verifier subagent context that couldn't be cleanly torn down.
**How to avoid:** D-01 already mandates: confirm 0 stray python/firefox + ~0 VRAM before the real boot, and drive the real backend lifecycle from the MAIN context, not a verifier subagent. Use `taskkill /F /T` for teardown (per STATE.md's documented blocker note) and `--backend http://127.0.0.1:8080` for the REPL (port mismatch with REPL's 8000 default).
**Warning signs:** A real-mode backend boot that hangs indefinitely on Selenium/CUDA init with no error.

## Code Examples

### The complete existing test proving the gesture+fold loop already works end-to-end (pure logic)
```javascript
// Source: backend/static/js/fe/integration.test.mjs (verified, existing, PASSING)
test("the full loop: right-click the {ref} → fold action → expand inline", () => {
  let expanded = new Set();
  let lines = renderPanel(CARD, { registry, expanded });
  const refLine = lines.find((l) => l.refTarget === "details page");
  assert.strictEqual(refLine.glyph, "▸");

  const { action } = resolveGesture({ button: "right", clicks: 1, target: "ref" });
  assert.strictEqual(action, Action.TOGGLE_FOLD);

  expanded = toggle(expanded, refLine.path);
  lines = renderPanel(CARD, { registry, expanded });
  const inlined = lines.filter((l) => l.source === "expanded").map((l) => l.text);
  assert.deepStrictEqual(inlined, [
    "url : /details/sim_princeton-university-library-chronicle_1950-1951_12_contents",
    "mediatype : Text",
    "reviews : 0",
  ]);
});
```
This is the EXPLORE-02 rank-1 external-ref propagation pattern, already proven at the model level — the planner's job is wiring real `contextmenu` DOM events to call exactly this same path, not re-deriving the fold-expand logic.

### Existing `mount()` signature — the exact extension point for new DOM handlers
```javascript
// Source: backend/static/js/fe/magic_markdown_panel.mjs (verified, existing)
// mount(host, rootNode, opts, handlers) wires:
//   - click on .mm-drop, .mm-gnode, .mm-text[data-editable]
//   - dblclick on body
// GAP: no contextmenu, no double-right debounce, no mousedown/mousemove/mouseup drag state.
```

### Existing backend edge-create path (no type-inheritance side effect — confirmed gap for N.4)
```python
# Source: backend/api/routes.py ~5110-5149 (verified, existing)
@router.post("/editor/link")
def editor_link(req: EditorLinkRequest):
    ge = _get_graph_editor()
    edge = ge.create_concept_edge(
        source_id=req.source_id, target_id=req.target_id,
        edge_type=req.edge_type or "RELATES_TO", workspace_id=req.workspace_id or "",
    )
    from backend.services.concept_lifecycle import apply_edge_create_lifecycle
    edge_dict = apply_edge_create_lifecycle(edge, ge, workspace_id=req.workspace_id or "", push_fn=_ws_push)
    return {"ok": True, "edge": edge_dict or _edge_to_dict(edge)}
# EditorLinkRequest fields (verified): source_id, target_id, edge_type, workspace_id, idempotency_key
# — NO type/ports/inherit field exists. N.4's "target inherits source's I/O types + object model"
# has no server-side implementation today.
```

### Existing REPL scenario pattern to model `duckduckgo-walkthrough` from
```python
# Source: scripts/sim_frontend.py ~7780-7806 (verified, existing, PASSING in both stub/real modes)
def _env_scenario_node_fold_roundtrip(env: FrontendEnv) -> int:
    _env_step(env, "purge", confirm="erase")
    card = _env_step(env, "editor-create", name="fold_card", data='{"summary": "see {detail} for more"}')
    cid = (card.get("response") or {}).get("concept_id")
    _env_step(env, "ui-node-fold", card=cid, field="detail", expanded=True)
    st = (_env_step(env, "ui-state").get("response") or {}).get("state") or {}
    nf = (st.get("node_fold_state") or {}).get(cid) or {}
    if "detail" not in (nf.get("expanded_paths") or []):
        _err(f"node_fold expand did not record the path: {nf}")
        return 1
    # ... collapse + assert cleared ...
    _ok("node-fold expand/collapse roundtrip OK (§7.3.4 inline fold)")
    return 0
```
The `duckduckgo-walkthrough` scenario should follow this exact shape: `purge` → `editor-create` (author `self=duckduckgo`) → a drag-wire-equivalent REPL action (likely `editor-link` extended, or a new `ui-wire-link` verb if D-03's type-inheritance endpoint needs its own REPL action) → `ui-node-fold` to reveal rank-1 `url{}`/`dom{}` → assert against `ui-state` → (for the real-subsystem probe variant) trigger a real scan via the existing scan-trigger route and assert chunk iteration via the `{chunk samples}` iterable model.

## State of the Art

| Old Approach (legacy `cp/`) | Current/Target Approach (served `fe/`) | When Changed | Impact |
|--------------------------|----------------------------------------|---------------|--------|
| `cp/concept_graph.js`'s contextmenu handler addresses fold state by literal `{ref}` token text via `caretRangeFromPoint` | `fe/magic_markdown.mjs`'s `renderPanel` produces a structural `path` per line, already wired through `gateway.mjs`'s `TOGGLE_FOLD`→`/api/ui/node_fold` mapping | This phase (recommended) | Avoids a second fold-addressing scheme; the legacy approach is GUI-coordinate-dependent (caret-based) and fragile, the fe/ approach is structural and robust to layout changes. |
| THREE.js 3D card DOM + Babylon-era data shapes for typed-view rendering (`_pythonNativeTypedView`) | Pure `Line[]`/vdom model rendering in `magic_markdown.mjs`/`magic_markdown_panel.mjs` | This phase (recommended) | Decouples typed rendering from any 3D/THREE.js dependency — the served fe/ is a pure 2D DOM+vdom surface. |

**Deprecated/outdated:**
- `cp/*.js` 2D interaction code generally: superseded by the fe/ gesture scaffolding; `cp/` is demoted to `/legacy` and is reference-only per project-wide v3.0 framing (STATE.md).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A new `GET /api/concepts/{id}/next_rank`-shaped endpoint (exact route name/shape left to planner) is the right granularity for D-03's backend gap, rather than client-side filtering of `GET /concepts/{id}` + `list_concept_edges` | Architecture Patterns, Don't Hand-Roll | If the planner instead does client-side filtering, it may violate the spirit of D10 ("frontend renders never computes") depending on how much logic the filter embeds — low risk since simple filtering by edge_type is widely considered "rendering," but worth flagging as a judgment call rather than a hard rule. |
| A2 | `DELETE_REF` should fire both `/api/ui/edit_close` (existing) AND `DELETE /api/concept_edges/{edge_id}` (when a backing edge exists) to satisfy N.13 | Common Pitfalls (Pitfall 1) | If N.13 is meant to ONLY clear the literal text reference (not the underlying edge), adding an edge-delete could be a destructive over-reach; the planner/discuss-phase should confirm this with the user or re-derive from `object_exploration.md` §N.13's exact wording before implementing. |
| A3 | Double-right-click should be detected via a manual timestamp-debounce on consecutive `contextmenu` events (no native double-right DOM event exists) | Common Pitfalls (Pitfall 4) | This is standard DOM behavior (verifiable via MDN/spec, not project-specific) — low risk, but the exact debounce threshold (this research suggests ~400ms, matching typical OS double-click intervals) is a free implementation choice, not a locked decision. |
| A4 | The new typed-rendering mode should gate on the same `type_hint`-starts-with-`python_` / `read_only:true` condition the legacy 🔒 logic uses, rather than a new independent flag | Common Pitfalls (Pitfall 3) | Low risk — this directly follows the locked rank-1-minimalism design (compute nodes type-stripped, raw object panels typed) and the one existing legacy precedent; an independent flag would only be wrong if some future raw-object node should NOT be read-only while still being typed, which is not described anywhere in the docs. |

**If this table is empty:** N/A — table is populated above.

## Open Questions (RESOLVED)

1. **Exact shape of the duplicate-instance-proxy semantics (N.6)**
   - What we know: N.6 says "a `{ref}` is a duplicate instance that operationally calls the originating object" — i.e., the duplicate isn't a copy, it's a live proxy.
   - What's unclear: Whether this needs new backend state (e.g. a `proxy_of` field on the ConceptNode, or a dedicated edge type) or can be expressed purely as "render every `{ref}` occurrence by re-resolving the registry at render time" (which `fe/magic_markdown.mjs`'s existing `buildRegistry`/`refTarget` mechanism may already give for free, since it always resolves `{ref}` to the live current node, not a frozen snapshot).
   - Recommendation: The planner should re-read `object_exploration.md` §N.6/§N.7/§N.14 closely during planning and test whether the EXISTING registry-resolution mechanism already satisfies "operationally calls the originating object" before building anything new — this may be a zero-backend-work item disguised as a hard one.
   - RESOLVED: absorbed into **07-03 Task 1** — its Test 1 is an explicit Open-Q1 probe that FIRST tests whether the existing `buildRegistry`/`refTarget` live-resolution already satisfies N.6 ("re-resolves to the NEW text on the next renderPanel call, not a frozen snapshot") BEFORE building any new proxy state; new proxy state is added only if that test fails, and the finding (live-resolution preferred = zero new code) is recorded in the 07-03 SUMMARY.

2. **Exact backend route shape for the next-rank type-graph fetch (D-03)**
   - What we know: The data needed (rank-1 typed neighbors via `OBJECT_HAS_PROPERTY`/`OBJECT_HAS_FUNCTION`/`FUNCTION_INPUT_TYPE`/`FUNCTION_OUTPUT_TYPE` edges) is fully present in the ConceptEdge table; no existing route shapes it for single-node rank-1 consumption.
   - What's unclear: Whether to add a new dedicated route (`GET /api/concepts/{id}/next_rank`) or extend an existing one (e.g. a query param on `GET /concepts/{id}`).
   - Recommendation: Default to a new dedicated route — it's additive (no risk of breaking existing `GET /concepts/{id}` consumers) and self-documenting; the planner should confirm naming convention against the existing `/ui/*` and `/concepts/*` route families during plan-writing.
   - RESOLVED: absorbed into **07-01** — the plan adds a dedicated `GET /api/concepts/{id}/next_rank` route (registered as a static path BEFORE the parametric `/concepts/{concept_id}` route), filtering ConceptEdge rows to exactly the four materialiser edge types; no extension of the existing parametric route.

3. **Whether `WIRE_LINK`'s backend mapping needs a new endpoint or an extension flag on `/concept_edges`/`/editor/link`**
   - What we know: Neither existing edge-create path does type inheritance; `gateway.mjs` currently sends a plain `POST /api/concept_edges` body.
   - What's unclear: Whether type-inheritance should be a synchronous side-effect of edge creation (single request) or a separate follow-up call the frontend makes after the edge is created.
   - Recommendation: Prefer a single synchronous side-effect (one request, one lifecycle event) for consistency with the "cascade is the default" architectural principle (CLAUDE.md) — avoids a frontend-orchestrated two-step sequence that could partially fail.
   - RESOLVED: absorbed into **07-04** — an optional `inherit_types` flag on the existing edge-create path (`EditorLinkRequest` / `POST /concept_edges`) triggers a SINGLE synchronous I/O-type-inheritance side-effect inside the same handler, fanned out through the existing `apply_edge_create_lifecycle` dispatcher (one request, one lifecycle event); no frontend-orchestrated two-step sequence and no new dedicated endpoint.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Backend, REPL, probes | Assume ✓ (existing project, unverified this session — prior phases ran successfully) | — | — |
| Node.js | fe/ `.test.mjs` files (run via `node file.mjs`) | Assume ✓ (existing `.test.mjs` files run this way per their own header comments) | — | — |
| Selenium / geckodriver | EXPLORE-04 real DuckDuckGo scan (D-01) | Assume ✓ (project has `backend/drivers/geckodriver.exe` per CLAUDE.md; prior phases' probes used it successfully) | — | `NO_WEBDRIVER=1` harness-only stub gate exists but is FORBIDDEN as a production substitute per no-mocks contract — D-01 explicitly requires the real run |
| GPT4All (SLM + Embed4All) on CUDA | EXPLORE-04 real materialiser/type-graph walkthrough, if any SLM-backed step is involved | Assume ✓ (documented in CLAUDE.md as the production default; prior phases' `all_real:true` runs succeeded) | `Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf` | `WFH_FAKE_SLM=1`/`WFH_FAKE_EMBEDDER=1` harness-only; forbidden in the D-01 acceptance run |
| Clean GPU state (0 stray python/firefox, ~0 VRAM) | D-01's real-subsystem boot | **Must be verified fresh immediately before the real run** — not a static fact, a pre-flight check | — | None — D-01 explicitly calls this out as a hard precondition with no fallback; the planner must include an explicit pre-flight verification task |

**Missing dependencies with no fallback:**
- Clean-GPU pre-flight state is NOT something this research session can verify (it's a runtime condition at execution time, not an install-time fact) — the planner MUST add an explicit verification task immediately before the EXPLORE-04 real-subsystem run, per D-01.

**Missing dependencies with fallback:**
- None identified beyond the standard harness-only fake gates (`WFH_FAKE_SLM`, `WFH_FAKE_EMBEDDER`, `NO_WEBDRIVER`), which are explicitly forbidden as substitutes for the D-01 acceptance proof but remain valid for the "stub-backed e2e + REPL scenario must ALSO stay green" fast-gate path D-01 also requires.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Node built-in `assert` + custom `test()` harness (fe/ pure-logic tests, e.g. `magic_markdown_gestures.test.mjs`); pytest (backend, inferred from `.planning/config.json`'s `nyquist_validation:true` and prior-phase conventions — no `pytest.ini`/`pyproject.toml` `[tool.pytest]` section found this session, confirm during planning); Playwright (`frontend_e2e/*.spec.js`); REPL `scripts/sim_frontend.py env-scenario --name <x>` |
| Config file | `frontend_e2e/playwright.config.js` (verified: self-boots a stub backend via `scripts/_serve_for_tests.py` with `WFH_FAKE_SLM=1 WFH_FAKE_EMBEDDER=1 NO_WEBDRIVER=1`, reuses an existing server if already running on 8080) |
| Quick run command | `node backend/static/js/fe/magic_markdown_gestures.test.mjs` (and the other `.test.mjs` files individually) — each runs in well under 30s |
| Full suite command | `python -m scripts.sim_frontend env-scenario --name full-smoke --backend http://127.0.0.1:8080` (both stub and real modes per CLAUDE.md); `npx playwright test` from `frontend_e2e/` (`npm run test:e2e`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXPLORE-01 | Hover reveals next-rank type graph (super-class + typed params); function rows show typed I/O | unit + e2e | `node backend/static/js/fe/magic_markdown.test.mjs` (extend); new `frontend_e2e/object_exploration.spec.js` (hover-type-graph case) | ❌ Wave 0 — typed-rendering unit cases + e2e spec both net-new |
| EXPLORE-02 | External `{ref}` propagates as recursively-rendered rank-1 panel; duplicate-instance proxy | unit (model already covers fold-propagation) + e2e | `node backend/static/js/fe/integration.test.mjs` (extend for duplicate-instance case); new e2e ref-propagation case | ⚠️ Partial — fold-propagation covered by existing `integration.test.mjs`; duplicate-instance-proxy is ❌ Wave 0 |
| EXPLORE-03 | Drag-wire creates edge + inherits I/O types; double-right deletes ref/instance | unit + REPL + e2e | `node backend/static/js/fe/magic_markdown_gestures.test.mjs` (drag/double-right cases already exist at resolver level — verify they cover the NEW DOM-capture layer once built); REPL `editor-link`-derived scenario; new e2e drag-wire+delete spec | ⚠️ Partial — resolver-level cases exist (`magic_markdown_gestures.test.mjs`); DOM-capture + backend type-inheritance + e2e are ❌ Wave 0 |
| EXPLORE-04 | DuckDuckGo walkthrough end-to-end against real subsystems | REPL env-scenario + live probe | `python -m scripts.sim_frontend env-scenario --name duckduckgo-walkthrough --backend http://127.0.0.1:8080` (stub fast-gate); `python scripts/probe_live_duckduckgo_walkthrough.py` (real acceptance, per D-01) | ❌ Wave 0 — neither the scenario nor the probe exists yet |

### Sampling Rate
- **Per task commit:** Run the specific `.test.mjs` file(s) touched (e.g. `node backend/static/js/fe/magic_markdown.test.mjs`) — each completes in well under 30s.
- **Per wave merge:** `python -m scripts.sim_frontend env-scenario --name full-smoke` (both stub and real modes per the project's standing contract) + `npm run test:e2e` from `frontend_e2e/`.
- **Phase gate:** Full suite green (stub AND real per D-01) before `/gsd-verify-work`; the `duckduckgo-walkthrough` REPL scenario AND its `probe_live_*` counterpart must both pass against real subsystems as the explicit D-01 acceptance proof, with the clean-GPU pre-flight verified immediately beforehand.

### Wave 0 Gaps
- [ ] `frontend_e2e/object_exploration.spec.js` — new e2e spec covering hover-type-graph, ref-propagation, drag-wire+delete, brace-state (none of these exist in `frontend_e2e/` today — confirmed by grep across all `.spec.js` files)
- [ ] New unit-test cases in `magic_markdown.test.mjs` (or a new `magic_markdown_typed.test.mjs`) for the `key:Type=value` typed-rendering mode
- [ ] New unit-test cases in `magic_markdown_panel.test.mjs` for the new `mount()` DOM handlers (contextmenu, double-right debounce, drag state machine) — likely requires a lightweight DOM shim/JSDOM-style harness if `mount()` tests currently rely on a real `document`; verify existing test setup during planning
- [ ] `duckduckgo-walkthrough` REPL env-scenario in `scripts/sim_frontend.py` (model from `_env_scenario_node_fold_roundtrip`)
- [ ] `scripts/probe_live_duckduckgo_walkthrough.py` — new probe (model from `scripts/probe_python_api.py`'s assertion style + `scripts/probe_live_archive_scan.py`'s real-Selenium-scan pattern)
- [ ] Backend: new rank-1 type-graph fetch endpoint + its own test coverage (no existing test targets a not-yet-built route)
- [ ] Backend: edge-create type-inheritance extension + its own test coverage

## Security Domain

This phase has no new authentication, session, or access-control surface — it extends existing gesture/render/edge-create code paths within an already-trusted single-workspace editor context. No new external input parsing beyond what `/concept_edges`, `/editor/link`, and the new rank-1-fetch endpoint already validate via existing Pydantic request models.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Out of scope — no auth changes in this phase. |
| V3 Session Management | No | Out of scope. |
| V4 Access Control | No | Out of scope — no new role/permission surface; fixture undeletability already enforced at the lifecycle layer (existing, unaffected). |
| V5 Input Validation | Yes | Existing Pydantic `BaseModel` request classes (`EditorLinkRequest`, `UINodeFoldRequest`, etc.) already validate request shape; any NEW endpoint/field added for D-03 must follow the same pattern — a typed Pydantic request model, not raw dict parsing. |
| V6 Cryptography | No | Out of scope — no new secrets/crypto surface. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unbounded recursive `{ref}` resolution (a node referencing itself, directly or via a cycle) causing infinite render loops or stack overflow | Denial of Service | The locked **rank-1 minimalism** design already bounds this (only ONE rank is revealed per gesture, never deep recursive auto-expansion) — the planner must ensure the new typed-rendering/fold code does not silently introduce deep auto-recursion; the existing `buildRegistry`/`refTarget` model resolves by lookup, not by walking, which is inherently cycle-safe at the data layer, but the NEW typed next-rank fetch endpoint should still guard against self-referential edges if it ever walks beyond rank-1. |
| Drag-wire creating edges between nodes across workspace boundaries (a malformed `source_id`/`target_id` pair) | Tampering | Existing `create_concept_edge` already raises `ValueError`→`HTTPException(400)` on invalid edges (verified in `editor_link`'s try/except); the new type-inheritance extension must preserve this validation rather than bypassing it for a "fast path." |

## Sources

### Primary (HIGH confidence — `[VERIFIED: codebase]`, direct file reads this session)
- `backend/static/js/fe/magic_markdown_gestures.mjs` + `.test.mjs` — gesture resolver, fully read, tests passing
- `backend/static/js/fe/magic_markdown_panel.mjs` — panel/graph vdom + mount(), fully read
- `backend/static/js/fe/magic_markdown.mjs` — core model (parse/serialize/renderPanel/renderGraph/iterable), fully read
- `backend/static/js/fe/gateway.mjs` — GestureGateway/buildRequest, fully read
- `backend/static/js/fe/store.mjs` — WorkspaceStore/applyFrame, fully read
- `backend/static/js/fe/integration.test.mjs` — end-to-end pure-logic loop test, fully read, passing
- `backend/static/js/cp/concept_graph.js` — `_pythonNativeTypedView`, 🔒 gating, legacy node_fold handler, read selectively (lines 1340-1969 + grep hits)
- `backend/static/js/cp/interaction.js` — 3D mouse interaction mixin, fully read
- `backend/static/js/cp/edge_manager.js` — fully read, confirmed NOT drag-wire logic
- `backend/static/js/cp/instance_manager.js` — fully read, confirmed NOT instance-inheritance logic
- `backend/services/python_api_materialiser.py` — fully read
- `backend/services/ui_state_service.py` — read selectively (lines 149-198, 794-948)
- `backend/api/routes.py` — grepped for all route names; read `/editor/create`, `/editor/link`, `/editor/overwrite`, `/editor/delete`, `/agent/spawn` in full (5075-5294); read `/ui/node_fold` (4384-4394)
- `scripts/sim_frontend.py` — read `_env_scenario_node_fold_roundtrip`, `_env_scenario_dominance_collapse_roundtrip`, `_env_scenario_compile_expand_collapse_roundtrip`, `_act_editor_create/link/overwrite/delete`, `_act_ui_dominance_collapse`
- `scripts/probe_python_api.py` — grepped structure (class/def names) to confirm probe-authoring pattern
- `frontend_e2e/playwright.config.js` — fully read
- `.planning/phases/WFH-07-deep-object-exploration-gestures/07-CONTEXT.md` — fully read
- `.planning/phases/WFH-07-deep-object-exploration-gestures/07-UI-SPEC.md` — fully read (prior session)
- `.planning/REQUIREMENTS.md` — fully read
- `.planning/STATE.md` — fully read
- `.planning/config.json` — grepped, confirmed `nyquist_validation: true`
- `docs/frontend/object_exploration.md` — fully read (prior session, §1-§14)

### Secondary (MEDIUM confidence)
- None — this phase required no external web/docs lookups; all claims trace to direct in-repo verification.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: N/A — no new packages
- Architecture: HIGH — every claim about existing fe/ and backend code traces to a direct file read this session; the CONTEXT.md misattribution was caught and corrected against the actual file contents
- Pitfalls: HIGH — each pitfall is grounded in a specific, verified gap (e.g. `EditorLinkRequest`'s exact field list, `mount()`'s exact wired-event list) rather than speculation
- Validation architecture: HIGH for what exists (verified via grep/read); MEDIUM for the exact pytest config (no `pytest.ini`/`pyproject.toml` `[tool.pytest]` section was found this session — flagged for the planner to confirm)

**Research date:** 2026-06-23
**Valid until:** Stable — this is in-repo code archaeology of a slow-moving internal codebase, not a fast-moving external dependency; valid until the next phase's code changes alter the files cited (effectively until Phase 7 itself is implemented, since this research becomes stale the moment its own gaps are closed).
