# Phase 8: Halo Cone-Ray Transport + Brace States + Stepper - Research

**Researched:** 2026-06-28
**Domain:** Brownfield frontend realization — THREE.js 3D projector geometry, panel/graph render-state wiring, one-way 2D→3D focus drive. Built on Phase 6 (`projector.mjs`) and Phase 7 (`classifyBraceStates`).
**Confidence:** HIGH

## Summary

This is a narrow-scope brownfield phase. All three requirements (HALO-03, HALO-04, STEP-01)
have most of their hard computation **already implemented server-side or in a sibling
frontend module** — the phase's real job is wiring, not invention.

- **HALO-03** — the cone-transport math (`radial = (1-s)·R`, `along_ray = s·R`, normalized
  against the candidate-set max score) is **already implemented** in
  `backend/api/routes.py::get_apparitions` (the `transport=True` branch) and in
  `backend/services/apparition_service.py::manifold_nearest` (the ray-projected variant).
  The remaining work is frontend-only: fetch `transport.{similarity,radial,along_ray}` from
  `/apparitions/{focal_id}?transport=1`, read `projector.azimuth()` for the angular axis,
  combine into a 3D scene position, and render the existing phantom/candidate visuals at
  that position instead of (or in addition to) the existing 2D-only `haloLayout` ray.
- **HALO-04** — `classifyBraceStates` in `magic_markdown.mjs` already produces correct
  `braceState` per line (proven by Phase 7's unit tests). The confirmed gap is exactly two
  places: `renderGraph` drops `braceState` when building graph nodes, and neither
  `panelVDom` nor `graphVDom` branch on it. This phase wires the existing classification
  into the two renderers and adds the resolved-external solid-link draw to `graphVDom`,
  reusing the proven `#link-layer` / `drawConcept3DLinks` no-dasharray idiom from Phase 6.
- **STEP-01** — the backend cursor primitive (`UIStateService.signal_stream` /
  `advance_signal`, routed through `POST /api/ui/signal_advance` →
  `RolloutCoordinator.advance()` for cascade re-fire) already exists and is fully tested
  (`signal-stream-roundtrip`, `iterated-signal-rerender` env-scenarios). What's missing is
  the **chunk-id linkage**: today's `signal_stream` entry carries `card_id` +
  `signal_index` + `total` but no pointer to which 3D-rendered chunk that index
  corresponds to, and there is no frontend caller that turns an advance into a 3D
  fly/highlight. `projector.mjs::frameCameraToRoot` proves the camera-tween pattern
  (URL-keyed only) but a node-id-keyed sibling is new code.

**Primary recommendation:** Treat this phase as three independent wiring tasks, each anchored
to one already-working half of a round-trip (backend transport math / Phase-7 classification /
Phase-4 signal cursor) — write the missing frontend (or thin backend) half, do not
re-derive math that already exists.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Triple-product similarity scoring | API/Backend | Database (TF-IDF/nomic/PageRank indices) | D10 — already computed in `apparition_service.py`; frontend never re-derives |
| Cone radial/along-ray transport values | API/Backend | — | Already implemented in `routes.py::get_apparitions` (`transport=True`); pure function of the backend score, no per-frame state |
| Cone angular placement (camera azimuth) | Browser/Client | — | Inherently camera-state-dependent; `projector.mjs::azimuth()` already exists and is explicitly deferred to the client by the route's own docstring |
| Cone-position → THREE.js scene coords | Browser/Client | — | New: combines backend radial/along_ray + client azimuth into an actual `Vector3`; THREE.js scene math belongs in the projector module |
| Brace-state classification (`braceState`) | Browser/Client | — | Already computed in `magic_markdown.mjs::classifyBraceStates` (pure function over parsed lines) — a rendering-layer concern, not backend |
| Brace-state visual rendering (glyphs/link draw) | Browser/Client | — | `panelVDom`/`graphVDom` are DOM/SVG rendering — client-only by definition |
| Signal-stream cursor (index/total/pause) | API/Backend | — | Already implemented (`UIStateService.signal_stream`); persisted server-side so REPL/GUI share one source of truth |
| Cascade re-fire on signal advance | API/Backend | — | `RolloutCoordinator.advance()` — already wired; out of this phase's scope to touch |
| Sample → 3D chunk-id resolution | API/Backend | Browser/Client (consumption) | New: the existing `signal_stream` entry has no `chunk_id`; resolving "which chunk is sample N" needs either a backend field addition or a frontend lookup against `pattern_map.sampled_chunks` — backend-favored per D10 (no client-side data correlation) |
| 3D camera fly-to / highlight on focus | Browser/Client | — | `projector.mjs::frameCameraToRoot` proves the THREE.js camera-tween pattern; a node-id-keyed variant is new client code |

## Standard Stack

No new third-party libraries. This phase extends existing in-repo modules only:

### Core (existing, reused — no new installs)
| Module | Role | Why reused, not replaced |
|--------|------|---------------------------|
| `backend/static/js/fe/projector.mjs` | THREE.js scene/camera/`project()`/`azimuth()`/`frameCameraToRoot` | Phase 6's projector already owns all 3D scene math; cone placement and fly-to are additive functions in this module per D-04 |
| `backend/static/js/fe/magic_markdown.mjs` | `classifyBraceStates`, `renderPanel`, `renderGraph`, `panelVDom`, `graphVDom` | Phase 7's classification is correct; only the render wiring is new |
| `backend/static/js/fe/magic_markdown_halo.mjs` | `haloLayout` (2D ray placement), `__mm_halo_*` test hooks | The cone transport extends/wraps this for the 3D case per CONTEXT D-04 |
| `backend/static/js/fe/magic_markdown_panel.mjs` | `mount()`, `#link-layer` SVG solid-line idiom | Reused verbatim for HALO-04's resolved-external link — same no-dasharray idiom Phase 6 used for the 2D↔3D arrow |
| `backend/services/apparition_service.py` | `manifold_nearest`, triple-product scoring | Already correct; HALO-03 only adds the `transport=True` consumption path on the client |
| `backend/services/ui_state_service.py` | `signal_stream` dict, `advance_signal` | Already correct; STEP-01 needs a chunk-id linkage addition, not a rewrite |
| `backend/services/rollout_coordinator.py` | `RolloutCoordinator.advance()` | Untouched — cascade re-fire already correct; STEP-01 only consumes its response |

### New modules (per D-04, port host decision)
| Module | Purpose | When to Use |
|--------|---------|-------------|
| `backend/static/js/fe/halo_cone.mjs` (new) | Combine backend `transport.{radial,along_ray}` + `projector.azimuth()` into 3D cone coordinates; render/update cone-placed candidates | HALO-03 |
| `backend/static/js/fe/stepper.mjs` (new) | Drive `POST /api/ui/signal_advance`, resolve the active sample to a 3D chunk id, call the projector's fly-to/highlight | STEP-01 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `halo_cone.mjs` module | Inline cone math directly into `magic_markdown_halo.mjs` | Rejected by D-04 — user explicitly chose new dedicated module(s) over cramming into existing ones |
| New `stepper.mjs` module | Extend `projector.mjs` directly with stepper logic | D-04 prefers new surface where a clean seam exists; `frameCameraToRoot` is the seam projector.mjs exposes, stepper.mjs is the caller |
| Backend `chunk_id` field addition to `signal_stream` | Frontend-side lookup against `pattern_map.sampled_chunks` by index | Backend field addition is cleaner (D10: backend owns data correlation) but D-03 explicitly allows either; planner should pick based on which avoids client-side guessing of array ordering |

**Installation:** None — no new packages.

**Package Legitimacy Audit:** **Not applicable.** This phase adds zero new third-party
dependencies (npm or pip). All work is new/extended in-repo ES modules and Python service
methods. No `package-legitimacy check` run was needed.

## Architecture Patterns

### System Architecture Diagram

```
                         2D EDITOR (served fe/)
   ┌─────────────────────────────────────────────────────────────────┐
   │  magic_markdown.mjs                                             │
   │  renderPanel(node) ──> lines[] (each carries .braceState)       │
   │       │                                                          │
   │       ├──> panelVDom(lines)   [HALO-04: branch on braceState]   │
   │       │      ▸ braced-hidden  → glyph + literal {braces}        │
   │       │      ▾ revealed-internal → inline rank-1 children       │
   │       │      resolved-external → <a> / clickable cross-ref      │
   │       │                                                          │
   │       └──> renderGraph(node) ──> graphVDom(nodes)                │
   │              [HALO-04: thread braceState through; draw the      │
   │               resolved-external SOLID link via #link-layer]      │
   │                                                                   │
   │  magic_markdown_halo.mjs — haloLayout (2D ray placement, existing)│
   │       │ opens on focal click ──> GET /apparitions/{focal_id}    │
   │       │                            ?transport=1                  │
   │       ▼                                                          │
   │  halo_cone.mjs (NEW)                                             │
   │       reads: candidate.transport.{similarity,radial,along_ray}  │
   │              projector.azimuth()                                 │
   │       computes: 3D Vector3 cone position per candidate           │
   │       calls: projector.placeHaloCandidates(positions)  (new fn)  │
   │                                                                   │
   │  stepper.mjs (NEW)                                               │
   │       on {chunk samples} advance gesture:                        │
   │         POST /api/ui/signal_advance {card_id, step}              │
   │         resolve signal_index -> chunk_id  (new backend field OR  │
   │             lookup against pattern_map.sampled_chunks[idx])      │
   │         calls: projector.flyToNode(chunk_id) (new fn, sibling    │
   │             of frameCameraToRoot but node-id-keyed)               │
   └─────────────────────────────────────────────────────────────────┘
                         │ fetch                      │ fetch
                         ▼                             ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │  BACKEND (routes.py)                                             │
   │                                                                   │
   │  GET /apparitions/{focal_id}?transport=1                         │
   │     apparition_service.apparitions_for_focal()                  │
   │       triple-product score = pagerank · tfidf_cos · nomic_cos    │
   │     ──> per-candidate transport = {similarity, radial, along_ray}│
   │         (ALREADY IMPLEMENTED — routes.py lines ~ get_apparitions)│
   │                                                                   │
   │  POST /api/ui/signal_advance                                     │
   │     RolloutCoordinator.advance(workspace_id, card_id, field_path)│
   │       -> UIStateService.advance_signal (cursor + cascade re-fire)│
   │     (ALREADY IMPLEMENTED)                                        │
   │     [STEP-01 gap: response carries signal_index, NOT chunk_id —  │
   │      planner must decide where chunk_id resolution lives]        │
   └─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │  3D PROJECTOR (projector.mjs, THREE.js scene)                    │
   │     project(), azimuth(), frameCameraToRoot(url)  [existing]     │
   │     placeHaloCandidates(positions)  [NEW — HALO-03 consumer]     │
   │     flyToNode(nodeId) + highlightNode(nodeId)  [NEW — STEP-01]   │
   │     drawConcept3DLinks()  [existing — reused pattern for the     │
   │         resolved-external link's 3D-aware variant if the target  │
   │         node is in 3D, not just 2D]                              │
   └─────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
backend/static/js/fe/
├── projector.mjs              # existing — add placeHaloCandidates(), flyToNode(), highlightNode()
├── magic_markdown.mjs         # existing — wire braceState into panelVDom/graphVDom; thread through renderGraph
├── magic_markdown_halo.mjs    # existing — haloLayout 2D path untouched; cone path delegates to halo_cone.mjs
├── magic_markdown_panel.mjs   # existing — #link-layer reused as-is for resolved-external link draw
├── halo_cone.mjs              # NEW — HALO-03 cone-coordinate computation (backend transport + client azimuth)
├── stepper.mjs                # NEW — STEP-01 advance-and-focus driver
├── gateway.mjs                # existing — add buildRequest cases if new gesture verbs are introduced (e.g. "ui-signal-advance" already maps via env-scenario action names; confirm gateway.mjs has matching case or add one)
└── store.mjs                  # existing — confirm whether new state slices needed for cone candidate positions / active stepper sample (open question below)
```

### Pattern 1: Cone-Transport Coordinate Composition (HALO-03)
**What:** Combine a backend-computed radial/along-ray pair with a client-computed angular
value into one 3D position on the cone surface.
**When to use:** Whenever rendering apparition-halo candidates that should appear in the 3D
projector rather than (or in addition to) the existing 2D ray overlay.
**Example:**
```python
# Source: backend/api/routes.py (existing, get_apparitions, transport=True branch)
# [VERIFIED: codebase read 2026-06-27]
_CONE_R = 40.0
smax = max((r.score for r in results), default=0.0) or 1.0
for r in results:
    s = (r.score / smax) if smax else 0.0
    r.transport = {
        "similarity": round(s, 6),
        "radial": round((1.0 - s) * _CONE_R, 4),
        "along_ray": round(s * _CONE_R, 4),
    }
```
```js
// halo_cone.mjs (NEW — sketch, not yet written)
// Source: pattern derived from projector.mjs::azimuth() + the backend transport contract above
import { azimuth, apexScreenToWorld } from "./projector.mjs";

export function placeOnCone(apexWorldPos, candidate, index, total) {
  const { radial, along_ray } = candidate.transport;
  const theta = azimuth() + (index / Math.max(total, 1)) * Math.PI * 2;
  // along_ray extends from the apex along the cone's axis; radial is the
  // perpendicular offset at that point along the axis — exact basis vectors
  // depend on how the apex's "axis" is defined (likely the camera forward
  // vector, or the ray from apex to scene origin — OPEN QUESTION, see below).
  return {
    x: apexWorldPos.x + Math.cos(theta) * radial,
    y: apexWorldPos.y + Math.sin(theta) * radial,
    z: apexWorldPos.z + along_ray,
  };
}
```

### Pattern 2: Brace-State-Aware Rendering (HALO-04)
**What:** Branch panel/graph line rendering on the already-classified `braceState`.
**When to use:** Every render path that turns a `Line` (from `renderPanel`/`renderGraph`)
into DOM/SVG — currently `panelVDom` and `graphVDom`.
**Example:**
```js
// Source: backend/static/js/fe/magic_markdown.mjs (existing, confirmed via direct read)
// [VERIFIED: codebase read 2026-06-27]
export function classifyBraceStates(lines) {
  const revealedTargets = new Set(
    lines.filter((l) => l.refTarget != null && l.glyph === GLYPH_EXPANDED).map((l) => l.refTarget),
  );
  for (const line of lines) {
    if (line.refTarget == null) continue;
    if (line.glyph === GLYPH_EXPANDED) { line.braceState = BRACE_REVEALED_INTERNAL; continue; }
    if (revealedTargets.has(line.refTarget)) { line.braceState = BRACE_RESOLVED_EXTERNAL; continue; }
    line.braceState = BRACE_HIDDEN;
  }
  return lines;
}
```
```js
// panelVDom (sketch of the missing branch — NOT yet written)
function renderLine(line) {
  switch (line.braceState) {
    case BRACE_HIDDEN:
      return el("span", { class: "mm-brace-hidden" }, `▸ {${line.refTarget}}`);
    case BRACE_REVEALED_INTERNAL:
      return el("span", { class: "mm-brace-revealed" }, "▾ " /* + inline children, existing path */);
    case BRACE_RESOLVED_EXTERNAL:
      return el("a", { class: "mm-brace-resolved", href: `#${line.refTarget}`,
                        onClick: () => scrollToOrHighlight(line.refTarget) }, line.text);
    default:
      return el("span", {}, line.text); // non-ref line, unchanged
  }
}
```
```js
// graphVDom resolved-external link draw — reuse the EXACT no-dasharray idiom
// Source: backend/static/js/fe/projector.mjs::drawConcept3DLinks (existing pattern to mirror)
// [VERIFIED: codebase read 2026-06-27]
// existing pattern: WeakMap-cached <line>, true NDC [-1,1] frustum test, no marker-end
svgLine.setAttribute("stroke", "#ffd700");
svgLine.setAttribute("stroke-width", "2");
// NEVER: svgLine.setAttribute("stroke-dasharray", ...)
```

### Pattern 3: One-Way Signal-Stream-to-3D-Focus Drive (STEP-01)
**What:** Advance the existing backend cursor, resolve the active sample to a chunk id,
fly the 3D camera / highlight that node — never the reverse direction.
**When to use:** The `{chunk samples}` stepper gesture in the 2D panel.
**Example:**
```python
# Source: backend/api/routes.py (existing — confirmed via direct read)
# [VERIFIED: codebase read 2026-06-27]
@router.post("/ui/signal_advance")
def ui_signal_advance(req: UISignalAdvanceRequest):
    from backend.services.rollout_coordinator import get_rollout_coordinator
    rc = get_rollout_coordinator(broadcast=_ws_push)
    snap = rc.advance(req.workspace_id, req.card_id, req.field_path or "", step=int(req.step))
    return {"ok": True, "state": snap.to_dict()}
```
```js
// stepper.mjs (NEW — sketch)
import { flyToNode, highlightNode } from "./projector.mjs";

export async function advanceAndFocus(cardId, step, resolveChunkId) {
  const res = await fetch("/api/ui/signal_advance", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ card_id: cardId, step, workspace_id: "_default" }),
  });
  const { state } = await res.json();
  const entry = state.signal_stream[cardId];
  // resolveChunkId is the OPEN QUESTION seam: either entry.chunk_id (if the
  // backend is extended to carry it) or a lookup against
  // pattern_map.sampled_chunks[entry.signal_index] fetched separately.
  const chunkId = resolveChunkId(entry);
  if (chunkId) { flyToNode(chunkId); highlightNode(chunkId); }
  // 3D NEVER sends anything back to the 2D stepper — one-way only (D-03/§O.6).
}
```

### Anti-Patterns to Avoid
- **Re-deriving triple-product similarity client-side:** The score is already computed
  server-side (`apparition_service.py`). HALO-03 must consume `transport.{radial,along_ray}`
  verbatim, never recompute `pagerank · tfidf_cos · nomic_cos` in JS (violates D10).
- **Three separate edge types for the three brace states:** §O.1a is explicit — one
  invariant ConceptEdge, three render states. Do not add `BRACED_EDGE` / `REVEALED_EDGE` /
  `RESOLVED_EDGE` as distinct backend edge types.
- **Dashed/dotted lines for the resolved-external link:** Forbidden project-wide. Always
  `stroke-dasharray` absent; reuse the `#ffd700` solid pattern from `drawConcept3DLinks`.
- **3D driving the 2D stepper back:** STEP-01 is explicitly one-way. Do not wire any
  camera-orbit or node-click handler in `projector.mjs` to call back into `signal_advance`.
- **Subsetting the 3D distribution on stepper advance:** The 3D scene must always render
  every chunk sample; the stepper only changes camera focus / highlight state, never
  filters/hides non-active samples.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Triple-product similarity scoring | A JS re-implementation of pagerank·tfidf·nomic | `GET /apparitions/{focal_id}` (existing) | Already correct, already tested, D10 forbids frontend computation |
| Cone radial/along-ray math | A new client-side formula | `routes.py::get_apparitions`'s `transport=True` branch (existing) | Identical math already implemented and normalizes against `smax` correctly |
| Camera-tween easing | A new easing curve for fly-to-node | `projector.mjs::_stepCameraTween`'s existing cubic ease-in-out (`u<0.5 ? 4u³ : 1-(-2u+2)³/2`) | Proven, already interruptible via tween-restart; STEP-01's `flyToNode` should mirror this exactly, just keyed by node id instead of URL |
| Signal cursor persistence/cascade re-fire | A new frontend-only iteration counter | `UIStateService.signal_stream` + `RolloutCoordinator.advance()` (existing) | Already shared with the REPL mirror; a frontend-only counter would desync from REPL/GUI parity (§11.8 contract) |
| Brace-state classification logic | A new classifier in the render layer | `magic_markdown.mjs::classifyBraceStates` (existing) | Proven correct by Phase 7's unit tests; the gap is rendering, not classification |

**Key insight:** Every piece of "hard" logic this phase needs (similarity scoring, cone
math, brace classification, cursor persistence, cascade re-fire) was built in an earlier
phase. The risk in this phase is *not* under-building — it's accidentally re-deriving
already-correct logic in the wrong tier, which would violate D10 and create two sources of
truth.

## Common Pitfalls

### Pitfall 1: `renderGraph` silently drops `braceState`
**What goes wrong:** Graph-mode nodes render with no resolved-external link and no
hidden/revealed glyph distinction, even though `renderPanel`'s underlying lines already
carry the correct `braceState`.
**Why it happens:** `renderGraph` builds its `nodes[]` array by destructuring specific
fields off each `Line` (`id, label, depth, glyph, refTarget, iterable, signalIndex,
signalTotal`) and `braceState` was never added to that field list.
**How to avoid:** Add `braceState: l.braceState` to the destructured node shape in
`renderGraph`, then branch on it in `graphVDom`.
**Warning signs:** A node-count-parity test passes (same number of nodes panel vs graph)
but a visual/attribute assertion on `.mm-brace-resolved` or similar class fails only in
graph mode.

### Pitfall 2: `frameCameraToRoot` is URL-keyed, not node-id-keyed
**What goes wrong:** Naively reusing `frameCameraToRoot(url)` for STEP-01's per-chunk
fly-to will frame the camera to an entire URL's root cluster, not the individual chunk.
**Why it happens:** Phase 6 only needed root-URL framing (REAL-02); no per-node fly-to
existed because nothing needed it yet.
**How to avoid:** Write a new `flyToNode(nodeId)` sibling function that looks up that
specific node's world position (reuse the `nodeWorldPosition()` helper already used by
`drawConcept3DLinks`) and tweens the camera to it, following the *same* interruptible
tween pattern (`_cameraTween.camStart` replacement) as `_stepCameraTween`.
**Warning signs:** e2e assertion that the camera ends up near the *specific* chunk's
position (not just the URL root cluster's centroid) fails by a large margin.

### Pitfall 3: `signal_stream` has no chunk-id field — frontend cannot resolve focus target
**What goes wrong:** STEP-01's stepper advances the cursor correctly but has nothing to
pass to `flyToNode`/`highlightNode`, because `UIStateService.signal_stream[card_id]` only
carries `{card_id, total, signal_index, signal_id, field_path, paused, updated_at}` — no
3D node/chunk id.
**Why it happens:** `signal_stream` was built (Phase 4/§R) purely for panel-side per-sample
rendering (`renderPanel`'s `signals` map); no consumer needed a 3D-pointer before now.
**How to avoid:** Per D-03, the planner must choose one of: (a) extend the backend
`signal_stream` entry (or the `/ui/signal_advance` response) with a `chunk_id` field
resolved server-side from `pattern_map.<hash>.sampled_chunks[signal_index]`, or (b) have the
frontend separately fetch the `pattern_map` data and index into `sampled_chunks` by
`signal_index`. Option (a) keeps data correlation in the backend (consistent with D10);
flag this explicitly as a planning decision, not a research-time assumption.
**Warning signs:** `signal_id` (which DOES exist on the entry) might already BE the chunk
id in some cases — verify whether `signal_id` is populated with a chunk concept_id before
assuming new backend work is needed. This was not confirmed in this research session
(`signal_id` is accepted as an optional param to `set_signal_stream` but no caller in the
read code populates it with an actual chunk id) — **flagged as Open Question 1**.

### Pitfall 4: `halo.spec.js` vs `object_exploration.spec.js` e2e placement is ambiguous
**What goes wrong:** Phase 7's established convention places new deep-interaction e2e cases
in `object_exploration.spec.js`; the 08-UI-SPEC.md / 08-CONTEXT.md verification-surface
notes name `halo.spec.js` as the extension target for HALO-03's cone-transport e2e. Picking
the wrong file inconsistently fragments the e2e suite across phases.
**Why it happens:** `halo.spec.js` is topically named for halo features (correct for
HALO-03/04 on its face) but Phase 7 set a precedent of accumulating *all* deep-gesture e2e
in one file regardless of topic.
**How to avoid:** Planner should explicitly decide and state which file new Phase 8 e2e
cases land in — likely `halo.spec.js` for HALO-03 (topically exact) and either file for
HALO-04/STEP-01. Document the choice in the plan rather than letting the implementing task
guess.
**Warning signs:** Two parallel e2e files both claiming to test the same brace-state or
stepper behavior, or a missing case because the implementer assumed the other file already
covered it.

## Code Examples

### Existing cone-transport backend computation (verbatim, confirmed)
```python
# Source: backend/api/routes.py — get_apparitions
# [VERIFIED: codebase read 2026-06-27]
@router.get("/apparitions/{focal_id}")
def get_apparitions(focal_id: str, workspace_id: str = "", k: int = 10,
                     min_score: float = 0.0, transport: bool = False, ray_project: bool = False):
    svc = _get_apparition_service()
    results = svc.apparitions_for_focal(focal_id, workspace_id=workspace_id, k=int(k),
                                         min_score=float(min_score), ray_project=bool(ray_project))
    if transport and results:
        _CONE_R = 40.0
        smax = max((r.score for r in results), default=0.0) or 1.0
        for r in results:
            if getattr(r, "ray_projected", False) and r.transport:
                continue
            s = (r.score / smax) if smax else 0.0
            r.transport = {
                "similarity": round(s, 6),
                "radial": round((1.0 - s) * _CONE_R, 4),
                "along_ray": round(s * _CONE_R, 4),
            }
    return {"focal_id": focal_id, "candidates": [r.to_dict() for r in results]}
```
Docstring/comment in the codebase explicitly states angular placement is "camera-computed
on the client" — this is the authoritative confirmation of the frontend/backend split for
HALO-03.

### Existing camera azimuth + tween pattern (verbatim, confirmed)
```js
// Source: backend/static/js/fe/projector.mjs
// [VERIFIED: codebase read 2026-06-27]
function azimuth() { return Math.atan2(camera.position.x, camera.position.z); }

// frameCameraToRoot(url) tweens via a 0.6s cubic ease-in-out:
// u < 0.5 ? 4*u*u*u : 1 - Math.pow(-2*u+2, 3) / 2
// interruptible by replacing _cameraTween.camStart with the current position
```

### Existing signal-stream cursor (verbatim, confirmed)
```python
# Source: backend/services/ui_state_service.py
# [VERIFIED: codebase read 2026-06-27]
def advance_signal(self, workspace_id, card_id, *, step=1, field_path=""):
    with self._lock:
        st = self._states.setdefault(workspace_id, UIState())
        entry = dict(st.signal_stream.get(card_id) or {})
        total = int(entry.get("total") or 0)
        cur = int(entry.get("signal_index") or 0)
        new_index = (cur + int(step)) % max(total, 1) if total > 0 else cur + int(step)
        entry.update({"card_id": card_id, "total": total, "signal_index": new_index,
                      "field_path": field_path or entry.get("field_path", "") or "",
                      "updated_at": time.time()})
        st.signal_stream[card_id] = entry
        snap = self._stamp(st, workspace_id, "signal_advance")
    self._emit("signal_advance", workspace_id, snap)
    return snap
```
Note: no `chunk_id` in the entry shape — confirms Pitfall 3.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| 2D-only halo ray placement (`haloLayout`) | 3D cone transport for candidates that have a backing 3D node | This phase (HALO-03) | The 2D `haloLayout` path is NOT removed — it remains for candidates without a 3D presence; cone transport is additive |
| `classifyBraceStates` computed-but-unused | Wired into both render paths | This phase (HALO-04) | Closes the Phase-7 self-flagged gap; no data-model change, render-layer only |
| Signal cursor with no 3D pointer | (after this phase) signal cursor resolvable to a 3D chunk id | This phase (STEP-01) | First phase where the 2D iteration affordance has any 3D consequence |

**Deprecated/outdated:** Nothing in this phase deprecates prior work — it is purely
additive wiring on top of Phases 4, 6, and 7.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The cone's "axis" for `along_ray` placement is the ray from the 2D query element's projected screen position outward along the camera's view direction (i.e., apex-to-camera-forward) — DOMAIN_MODEL §O.18 was not read verbatim in this session, only CONTEXT.md's paraphrase | Pattern 1 / Architecture Patterns | If the actual basis is different (e.g., apex-to-scene-origin, or apex-to-original-3D-node-position), the cone shape will look visually wrong even though radial/along_ray values are numerically correct — **must verify against `docs/DOMAIN_MODEL.md` §O.18 directly before implementation** |
| A2 | `signal_id` in `UIStateService.set_signal_stream`'s optional param is NOT currently populated with a chunk concept_id by any caller read in this session — assumed to need new plumbing rather than already containing the answer | Pitfall 3 | If some caller (not found in this session's reads) already populates `signal_id` with the chunk id, STEP-01's "new backend work" shrinks to zero — re-grep all `set_signal_stream(` call sites before planning new backend fields |
| A3 | `store.mjs` (WorkspaceStore) does not yet need new state slices for cone candidate positions or active stepper sample — based on not having read the actual caller/mount code that wires the existing 2D halo into `editor.html`'s render loop | Recommended Project Structure | If the existing halo IS store-mediated (not direct fetch-and-render), the new cone/stepper modules may need to follow the same store-slice pattern instead of managing local state — verify by reading `editor.html`'s halo-open handler before finalizing module boundaries |
| A4 | The `halo.spec.js` vs `object_exploration.spec.js` e2e file choice was not resolved in this research — documented as Pitfall 4 / Open Question, deliberately left to planner+human, not assumed one way | Pitfall 4 / Open Questions | Wrong guess fragments e2e coverage tracking across files; low risk (cosmetic/organizational, not functional) |

## Open Questions

1. **Where does chunk-id resolution for the stepper live?**
   - What we know: `signal_stream` entries have `signal_index`/`total`/`card_id` but no
     chunk pointer; `pattern_map.<hash>.sampled_chunks[]` holds the actual chunk
     references per CONTEXT/docs (`pattern_map_and_url_set.md`).
   - What's unclear: Whether to (a) extend the backend response to include a resolved
     `chunk_id` per advance, or (b) have the frontend fetch `pattern_map` separately and
     index by `signal_index`.
   - Recommendation: Planner should default to (a) — a backend-side resolution keeps data
     correlation server-side per D10 and avoids the frontend assuming `sampled_chunks`
     ordering matches `signal_index` ordering (an assumption that could silently break if
     the two arrays diverge during live streaming).

2. **What exact 3D basis does the cone's `along_ray` axis use?**
   - What we know: Radial/along-ray values are backend-computed and normalized; apex =
     2D query element's screen position; angular = camera azimuth.
   - What's unclear: The precise 3D vector the "ray" itself runs along (apex→camera-forward
     vs apex→scene-origin vs apex→some canonical direction) — `docs/DOMAIN_MODEL.md` §O.18
     was not read verbatim this session (only CONTEXT.md's summary of it).
   - Recommendation: Planner/implementer MUST read `docs/DOMAIN_MODEL.md` §O.18 directly
     (and `docs/frontend/halo.md` / `docs/frontend/projector.md` in full) before writing
     `halo_cone.mjs` — this is a precise-geometry detail that this research flagged but did
     not fully resolve.

3. **Does the resolved-external link in graph mode need a 3D-aware variant, or is the 2D
   `#link-layer` SVG sufficient?**
   - What we know: The 2D `#link-layer` solid-line idiom exists and is proven
     (`magic_markdown_panel.mjs`); `drawConcept3DLinks` in `projector.mjs` is a separate
     3D-scene-aware variant used for the 2D↔3D pinned-panel arrow (REAL-04).
   - What's unclear: HALO-04's resolved-external link connects two graph-mode NODES (both
     in the 2D editor's SVG graph), so the 2D `#link-layer` is almost certainly sufficient
     and `drawConcept3DLinks` is NOT needed for this specific link — but this was not
     100% confirmed by reading the graph-mode DOM structure directly.
   - Recommendation: Default to the 2D `#link-layer` idiom (simpler, already in the same
     SVG namespace as `graphVDom`'s output); only reach for `drawConcept3DLinks` if a
     resolved-external target is itself a 3D-only node (unlikely given both ends are
     graph-mode children of the SAME panel-expansion).

4. **Does `store.mjs` need new state slices for cone candidate positions / active stepper
   sample?**
   - What we know: `store.mjs` already holds `signal_stream` state (mirrored from backend
     frames); the existing 2D halo's render wiring into `editor.html` was not read this
     session.
   - What's unclear: Whether the existing halo bypasses the store (direct fetch+render) or
     goes through it.
   - Recommendation: Planner's first task for HALO-03/STEP-01 should include a quick read
     of `editor.html`'s halo-open and stepper-gesture handlers to confirm the existing
     wiring pattern before deciding whether `halo_cone.mjs`/`stepper.mjs` need new store
     slices or can manage local module state.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| GPT4All SLM (Nous-Hermes-2-Mistral-7B-DPO) | D-01 real-retrieval acceptance run | Not probed this session — assumed available per CLAUDE.md production contract | — | None (no-mocks contract forbids fallback) |
| nomic embedder (Embed4All) | Triple-product retrieval (already backend-side, unaffected by this phase's new code) | Not probed this session | — | None |
| Selenium / geckodriver | D-01's real scan step | Not probed this session | — | None |
| THREE.js (browser-side, already vendored) | All projector work | Assumed present — Phase 6 already depends on it | Not re-verified this session | — |

**Missing dependencies with no fallback:** None identified as newly required by this
phase — all real-subsystem dependencies (GPT4All/nomic/Selenium) were already required by
Phase 6/7 and are unchanged by Phase 8's scope. The D-01 real-subsystem acceptance run must
be preceded by the clean-GPU preflight (0 stray python/firefox, ~0 VRAM) per CLAUDE.md
discipline — this is a process requirement, not a missing tool.

**Missing dependencies with fallback:** None — this phase introduces no new external tool
dependency; stub-mode (`WFH_FAKE_SLM=1` etc.) remains the harness-only fast-gate fallback
exactly as in prior phases.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend unit/integration) + Node's built-in `node:test` (frontend `.mjs` unit tests, e.g. `magic_markdown.test.mjs`) + Playwright (`frontend_e2e/*.spec.js`) + the custom REPL harness (`scripts/sim_frontend.py` env-scenarios) |
| Config file | `pytest.ini`/`pyproject.toml` (backend, not re-verified this session — assumed per existing convention); `frontend_e2e/playwright.config.js` (assumed present, not re-read); no separate config for `node:test` `.mjs` files (run directly via `node --test`) |
| Quick run command | `node --test backend/static/js/fe/magic_markdown.test.mjs backend/static/js/fe/magic_markdown_halo.test.mjs backend/static/js/fe/projector.test.mjs` (new/touched unit files only) |
| Full suite command | `python scripts/sim_frontend.py --backend http://127.0.0.1:8080 env-scenario --name full-smoke` (REPL contract) + `npx playwright test frontend_e2e/halo.spec.js` (or wherever new e2e lands) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HALO-03 | Cone radial/along-ray values are monotonic in normalized triple-product score (unit, backend math — already covered) | unit | existing backend test suite for `apparition_service.py` (not individually re-confirmed; assumed covered since `transport=True` is existing code) | ✅ existing |
| HALO-03 | Client combines `transport.{radial,along_ray}` + `azimuth()` into correct 3D position | unit | `node --test backend/static/js/fe/halo_cone.test.mjs` | ❌ Wave 0 — new file |
| HALO-03 | Live cone-transport against real retrieval; delete-top-result transports next-most-similar in | e2e (real-subsystem) | `scripts/probe_live_*.py` (new, per D-01) | ❌ Wave 0 — new probe |
| HALO-03 | Stub-backed cone-transport e2e stays green | e2e | `npx playwright test frontend_e2e/halo.spec.js -g "cone"` | ❌ Wave 0 — new test case in existing file |
| HALO-04 | `classifyBraceStates` output renders correctly in panel mode (▸/▾/link) | unit | `node --test backend/static/js/fe/magic_markdown.test.mjs` | ⚠️ extend existing file — new test cases needed |
| HALO-04 | `renderGraph` threads `braceState` through; `graphVDom` draws resolved-external link | unit | `node --test backend/static/js/fe/magic_markdown.test.mjs` | ⚠️ extend existing file |
| HALO-04 | Node-count parity between panel and graph forms when a ref is revealed | e2e | `npx playwright test frontend_e2e/halo.spec.js -g "brace"` (or `object_exploration.spec.js` — Open Question 4/Pitfall 4) | ❌ Wave 0 — new test case, file TBD by planner |
| STEP-01 | `signal_advance` resolves to a chunk id (backend or frontend lookup) | unit/integration | pytest case on the resolution path (new) | ❌ Wave 0 — new test |
| STEP-01 | Advancing the 2D stepper flies/highlights the corresponding 3D node; 3D never drives 2D back | e2e | `npx playwright test frontend_e2e/halo.spec.js -g "stepper"` (file TBD) | ❌ Wave 0 — new test |
| STEP-01 | env-scenario coverage for the new chunk-id-resolution + 3D-focus telemetry | REPL scenario | `python scripts/sim_frontend.py env-scenario --name signal-stream-roundtrip` (extend) + possibly a new scenario | ⚠️ extend existing scenario |

### Sampling Rate
- **Per task commit:** Run the touched `.mjs` unit test file(s) directly via `node --test`,
  plus the relevant single `env-scenario --name <specific>` (fast, no full-smoke needed per
  task).
- **Per wave merge:** `env-scenario --name full-smoke` in BOTH stub and real modes (per the
  project's standing contract that full-smoke must stay green in both).
- **Phase gate:** Full suite green (full-smoke both modes + all touched e2e specs) before
  `/gsd-verify-work`; PLUS the D-01 real-subsystem acceptance run (clean-GPU preflight →
  real scan → real cone-transport assertion → real delete-transports-next-in assertion),
  driven from the MAIN context per the standing discipline (never a verifier subagent, to
  avoid wedging a real CUDA/Selenium boot).

### Wave 0 Gaps
- [ ] `backend/static/js/fe/halo_cone.test.mjs` — unit coverage for HALO-03's coordinate
      composition (new module)
- [ ] `backend/static/js/fe/stepper.test.mjs` — unit coverage for STEP-01's advance-and-focus
      driver (new module)
- [ ] New/extended cases in `backend/static/js/fe/magic_markdown.test.mjs` covering
      `panelVDom`/`graphVDom` branching on `braceState` (HALO-04)
- [ ] A new `scripts/probe_live_*.py` for the D-01 real-retrieval cone-transport acceptance
      (explicitly called out in 08-CONTEXT.md's verification surface as not yet existing)
- [ ] Planner decision + resulting new test cases in either `halo.spec.js` or
      `object_exploration.spec.js` (Open Question 4 / Pitfall 4 — file TBD)
- [ ] Possible new pytest case for the backend chunk-id resolution path if Open Question 1
      resolves to a backend-side fix

## Security Domain

This phase is a frontend-rendering and read-path wiring phase (no new auth/session/data
write surface beyond what already exists in `/apparitions` and `/ui/signal_advance`, both
of which are pre-existing routes). No new ASVS categories are introduced.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Unchanged — this phase touches no auth surface |
| V3 Session Management | No | Unchanged |
| V4 Access Control | No | Unchanged — `workspace_id` scoping already enforced by existing routes |
| V5 Input Validation | Marginal | If a new backend field (`chunk_id` resolution, Open Q1) is added to `/ui/signal_advance`'s request/response, validate `signal_index` bounds against `total` server-side (already done in `advance_signal`'s modulo wrap) |
| V6 Cryptography | No | Not applicable |

### Known Threat Patterns for this stack
No new threat surface — this phase adds no new write endpoints, no new user input parsing
beyond existing gesture dispatch, and no new external data ingestion path.

## Sources

### Primary (HIGH confidence)
- `backend/api/routes.py` — direct codebase read, confirmed `get_apparitions` transport
  branch, `ui_signal_advance`, halo_chain routes (2026-06-27/28 session)
- `backend/services/apparition_service.py` — direct codebase read, confirmed
  `manifold_nearest` ray-projected transport variant
- `backend/services/ui_state_service.py` — direct codebase read, confirmed
  `set_signal_stream`/`advance_signal`/`clear_signal_stream` shapes
- `backend/static/js/fe/magic_markdown.mjs` — direct codebase read, confirmed
  `classifyBraceStates`, `renderGraph`'s missing `braceState` field
- `backend/static/js/fe/projector.mjs` — direct codebase read, confirmed `azimuth()`,
  `frameCameraToRoot`, `drawConcept3DLinks`, `_stepCameraTween`
- `backend/static/js/fe/magic_markdown.test.mjs` — direct read, confirmed `iterableNode`
  per-signal test shape
- `backend/static/js/fe/gateway.mjs` — direct read, confirmed no existing cone/stepper
  gesture cases
- `scripts/sim_frontend.py` — direct read of `_env_scenario_signal_stream_roundtrip`,
  `_env_scenario_iterated_signal_rerender`, `_env_scenario_halo_chain_roundtrip`
- `frontend_e2e/halo.spec.js` — direct read, confirmed existing HALO-01/02 coverage and
  the `__mm_halo_rotate` test hook pattern
- `.planning/phases/WFH-08-halo-cone-ray-transport-brace-states-stepper/08-CONTEXT.md` —
  locked decisions D-01..D-04
- `.planning/REQUIREMENTS.md` — HALO-03/HALO-04/STEP-01 definitions and traceability

### Secondary (MEDIUM confidence)
- `docs/frontend/pattern_map_and_url_set.md` — grep-confirmed `sampled_chunks` shape inside
  `pattern_map` (not read in full)
- `docs/frontend/agent_and_rollout.md` — grep-confirmed the "one cycling readout node, not
  fan-out" §O.11 framing
- `.planning/STATE.md` — phase sequencing and prior-phase decision log

### Tertiary (LOW confidence — flagged in Assumptions Log)
- `docs/DOMAIN_MODEL.md` §O.18 — **not read verbatim this session**; cone-axis geometry
  detail (Assumption A1 / Open Question 2) is paraphrased from CONTEXT.md only and needs
  direct verification before implementation
- `docs/frontend/halo.md` / `docs/frontend/projector.md` — referenced by CONTEXT.md as
  canonical but not directly read this session for the exact cone-axis basis vector

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all reused modules directly confirmed by reading code
- Architecture: HIGH for the backend-half (directly read and verbatim-quoted); MEDIUM for
  the new-module geometry detail (cone axis basis vector not confirmed against
  DOMAIN_MODEL §O.18 directly — flagged as Open Question 2)
- Pitfalls: HIGH — all four pitfalls are based on direct code reads, not inference

**Research date:** 2026-06-28
**Valid until:** 30 days (stable in-repo code; no fast-moving external dependency)
