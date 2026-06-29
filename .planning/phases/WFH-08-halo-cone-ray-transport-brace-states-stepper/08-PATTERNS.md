# Phase 8: Halo Cone-Ray Transport + Brace States + Stepper - Pattern Map

**Mapped:** 2026-06-27
**Files analyzed:** 9 (2 new frontend modules, 2 modified frontend modules, 1 possible backend extension, 4 test/probe/e2e scaffolds)
**Analogs found:** 9 / 9 (all have at least a role-match; several exact)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/static/js/fe/halo_cone.mjs` (NEW) | utility/transform (pure geometry fn) | transform | `backend/static/js/fe/magic_markdown_halo.mjs::haloLayout` (lines 31-49) | exact (same "pure placement fn" shape, 2D→3D variant) |
| `backend/static/js/fe/stepper.mjs` (NEW) | service/driver (client-side orchestration) | request-response + event-driven | `backend/static/js/fe/projector.mjs::frameCameraToRoot`/`_stepCameraTween` (lines 392-428) | role-match (camera-tween driver; URL-keyed → node-id-keyed) |
| `backend/static/js/fe/magic_markdown.mjs` (MODIFY) | transform/component (render-state composition) | transform | itself — `classifyBraceStates` (lines 259-281) is the correct half; `renderGraph` (lines 299-320) is the half to extend | exact (in-file precedent) |
| `backend/static/js/fe/magic_markdown_panel.mjs` (MODIFY) | component (DOM/SVG vdom renderer) | transform | itself — `panelVDom` (lines 41-76) / `graphVDom` (lines 85-125) | exact (in-file precedent) |
| `backend/static/js/fe/projector.mjs` (MODIFY — add `flyToNode`/`highlightNode`/`placeHaloCandidates`) | component (THREE.js scene ops) | event-driven | itself — `frameCameraToRoot` (392-415) + `drawConcept3DLinks` (603-677) + `nodeWorldPosition` (711-713) + `azimuth` (717) + `project` (699-706) | exact (in-file precedent) |
| `backend/services/ui_state_service.py` (POSSIBLE MODIFY — `chunk_id`/resolved signal_id) | service | CRUD (in-memory dict mutation) | itself — `set_signal_stream` (684-721) / `advance_signal` (723-752) | exact (in-file precedent) |
| `backend/static/js/fe/halo_cone.test.mjs` (NEW) | test | transform | `backend/static/js/fe/magic_markdown_halo.test.mjs` (haloLayout pure-fn unit tests) | exact |
| `backend/static/js/fe/stepper.test.mjs` (NEW) | test | event-driven | `backend/static/js/fe/projector.test.mjs` | role-match |
| `scripts/probe_live_*.py` (NEW, D-01 cone acceptance) | test (live probe) | request-response (real-subsystem) | `scripts/probe_live_archive_scan.py` / `scripts/probe_live_duckduckgo_walkthrough.py` | exact |

## Pattern Assignments

### `backend/static/js/fe/halo_cone.mjs` (NEW — utility, transform)

**Analog:** `backend/static/js/fe/magic_markdown_halo.mjs::haloLayout` (lines 18-49), consuming `backend/static/js/fe/projector.mjs::azimuth`/`project`/`nodeWorldPosition` (lines 699-717) and the backend's `routes.py::get_apparitions` `transport=True` branch (already implemented, verbatim per RESEARCH.md lines 178-190, 388-411).

**Pure-placement-function shape to mirror** (`haloLayout`, lines 31-49):
```js
export function haloLayout(focal, candidates, opts = {}) {
  const rBase = opts.rBase == null ? 120 : opts.rBase;
  const rExtent = opts.rExtent == null ? 200 : opts.rExtent;
  ...
  return candidates.map((c, i) => {
    const sim = Math.max(0, Math.min(1, c.similarity == null ? 0 : c.similarity));
    const r = rBase + (1 - sim) * rExtent;                 // constant-similarity radius
    const t = n === 1 ? 0.5 : i / (n - 1);
    const angle = arcStart + t * arcSpan + camAngle;        // ray angle updates with camAngle
    return { id: c.id, label: c.label, similarity: sim, r, angle, cx: ..., cy: ... };
  });
}
```
`halo_cone.mjs`'s `placeOnCone(apexWorldPos, candidate, index, total)` must follow this EXACT shape (pure function: inputs → positions array, no DOM/THREE side effects, unit-testable in plain Node) — only the dimensionality changes (2D `{cx,cy}` → 3D `{x,y,z}`) and the per-candidate distance values come from the backend's `candidate.transport.{radial, along_ray}` instead of being recomputed from `similarity` locally (D10 — never recompute `(1-sim)*rExtent`-style math from a raw score; consume the backend's already-normalized `radial`/`along_ray` verbatim).

**Backend transport contract to consume (verbatim, do not re-derive)** — `backend/api/routes.py::get_apparitions`:
```python
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

**Camera-azimuth + apex read** — `projector.mjs`:
```js
function azimuth() { return Math.atan2(camera.position.x, camera.position.z); }
function project(x, y, z) {
  const v = new THREE.Vector3(x, y, z).project(camera);
  return { x: (v.x*0.5+0.5)*w(), y: (-v.y*0.5+0.5)*h(), inFront: v.z<1, ndcX:v.x, ndcY:v.y, ndcZ:v.z };
}
```

**No-dasharray stroke contract to mirror** (`haloVDom`, line 63):
```js
stroke: "var(--slate-border,#c0c0c0)", "stroke-width": "1", opacity: "0.5",
// NO stroke-dasharray attribute anywhere — hard project-wide rule
```

**OPEN QUESTION flagged at point of use:** the exact 3D basis vector for `along_ray` (apex→camera-forward vs apex→scene-origin vs apex→canonical-direction) is NOT resolved by this pattern map — RESEARCH.md Open Question 2 / Assumption A1 explicitly defers this to a direct read of `docs/DOMAIN_MODEL.md` §O.18 (paraphrased only, not verbatim, in CONTEXT.md) plus `docs/frontend/halo.md` §3.2 / `docs/frontend/projector.md` §4-5. The planner/executor MUST read those sources directly before fixing `halo_cone.mjs`'s axis math — this pattern map's sketch (apex + along_ray along camera-forward, radial perpendicular at angle=azimuth+index-offset) is RESEARCH's proposal, not a confirmed contract.

---

### `backend/static/js/fe/stepper.mjs` (NEW — service/driver, request-response + event-driven)

**Analog:** `projector.mjs::frameCameraToRoot` + `_stepCameraTween` (lines 392-428) for the camera-tween half; `backend/services/ui_state_service.py::advance_signal` (723-752) + `backend/api/routes.py` `POST /ui/signal_advance` route for the backend-call half.

**Interruptible tween pattern to mirror EXACTLY** (`frameCameraToRoot`/`_stepCameraTween`, lines 392-428) — `flyToNode(nodeId)` must be the node-id-keyed sibling, same tween record shape:
```js
function frameCameraToRoot(url) {
  if (!controls) return false;
  const rootVec = _urlRootPositions.get(url);   // → flyToNode: nodeWorldPosition(nodeId) instead
  if (!rootVec) return false;
  ...
  _cameraTween = { t: 0, dur: 0.6, camStart: camera.position.clone(),
                   tgtStart: controls.target.clone(), camEnd, tgtEnd };
  return true;
}
function _stepCameraTween(dt) {
  if (!_cameraTween) return;
  const tw = _cameraTween;
  tw.t += dt;
  const u = Math.min(1, tw.t / tw.dur);
  const e = u < 0.5 ? 4*u*u*u : 1 - Math.pow(-2*u+2, 3)/2;   // cubic ease-in-out — REUSE VERBATIM
  camera.position.lerpVectors(tw.camStart, tw.camEnd, e);
  if (controls) controls.target.lerpVectors(tw.tgtStart, tw.tgtEnd, e);
  if (u >= 1) _cameraTween = null;
}
```
`flyToNode(nodeId)` swaps `_urlRootPositions.get(url)` for `nodeWorldPosition(nodeId)` (line 711-713: `function nodeWorldPosition(nodeId) { return _positions.get(nodeId) || null; }`) — the SAME WeakMap/Map-backed per-frame lookup `drawConcept3DLinks` already uses (line 617: `const worldPos = nodeId ? nodeWorldPosition(nodeId) : null;`).

**Backend advance-cursor contract to consume, never reimplement** — `ui_state_service.py::advance_signal`:
```python
def advance_signal(self, workspace_id, card_id, *, step=1, field_path=""):
    with self._lock:
        st = self._states.setdefault(workspace_id, UIState())
        entry = dict(st.signal_stream.get(card_id) or {})
        total = int(entry.get("total") or 0)
        cur = int(entry.get("signal_index") or 0)
        new_index = (cur + int(step)) % max(total, 1) if total > 0 else cur + int(step)
        entry.update({"card_id": card_id, "total": total, "signal_index": new_index, ...})
        st.signal_stream[card_id] = entry
        snap = self._stamp(st, workspace_id, "signal_advance")
    self._emit("signal_advance", workspace_id, snap)
    return snap
```

**CONFIRMED (not just flagged) gap for Open Question 1:** Grepped every `set_signal_stream(` call site in `backend/services/rollout_coordinator.py` (`play`/`pause`/`reset`, lines 53-91) — each one only ever passes through `signal_id=e.get("signal_id")`, i.e. whatever was already in the dict; NO caller in the entire codebase ever sets `signal_id` to an actual chunk concept_id. RESEARCH.md's Assumption A2 is confirmed TRUE: this is genuinely new backend plumbing, not a pre-existing answer hiding in `signal_id`. Per D-03/RESEARCH's recommendation, the planner should default to backend-side resolution (extend `set_signal_stream`/`advance_signal`'s entry shape with a real `chunk_id` resolved server-side from `pattern_map.<hash>.sampled_chunks[signal_index]`) — keeps data correlation server-side per D10.

**Data-flow note (D10):** `stepper.mjs` is a pure driver — it calls `POST /api/ui/signal_advance`, reads the response's resolved chunk pointer (however the planner decides to expose it), and calls `flyToNode`/`highlightNode`. It NEVER computes which chunk corresponds to which sample index itself (that's the open backend-vs-frontend resolution question), and it NEVER lets the 3D scene call back into `signal_advance` (one-way only, hard constraint per UI-SPEC Contract C).

---

### `backend/static/js/fe/magic_markdown.mjs` (MODIFY — HALO-04 wiring)

**Analog:** itself. `classifyBraceStates` (lines 259-281) is the CORRECT, ALREADY-WORKING half (confirmed by direct read — do not modify its logic). The gap is `renderGraph` (lines 299-320) dropping `braceState` from the node shape it builds:

```js
// CURRENT (gap) — renderGraph, lines 299-320:
export function renderGraph(rootNode, opts = {}) {
  const lines = renderPanel(rootNode, opts);
  const nodes = lines.map((l) => ({
    id: l.path,
    label: l.text,
    depth: l.depth,
    glyph: l.glyph,
    refTarget: l.refTarget,
    iterable: !!l.iterable,
    signalIndex: l.signalIndex,
    signalTotal: l.signalTotal,
    // braceState: l.braceState,   ← MISSING — this is the entire Pitfall-1 fix
  }));
  ...
}
```
Fix: add `braceState: l.braceState` to the destructured shape (RESEARCH.md Pitfall 1, "How to avoid"). `classifyBraceStates`'s output shape to consume verbatim:
```js
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
Each `Line` already carries `.braceState` after this call — `renderPanel`'s output (consumed identically by both `panelVDom` and `renderGraph`) requires NO change; only `renderGraph`'s field-list destructuring needs the one new key.

---

### `backend/static/js/fe/magic_markdown_panel.mjs` (MODIFY — HALO-04 visual wiring)

**Analog:** itself. `panelVDom` (lines 41-76) and `graphVDom` (lines 85-125) currently branch only on `l.glyph` (truthy/falsy) — neither reads `l.braceState` at all (confirmed gap, matches RESEARCH's "07-03 self-flagged: graphVDom has no drawing path for resolved-external").

**panelVDom's existing glyph-only branch to extend** (lines 43-68):
```js
const lineEls = lines.map((l) => {
  const children = [];
  if (l.glyph) {
    children.push(txt("span", {
      class: "mm-drop", role: "button", "data-path": l.path,
      "data-open": l.glyph === GLYPH_EXPANDED ? "1" : "0",
      "aria-label": l.glyph === GLYPH_EXPANDED ? "collapse" : "expand",
    }, l.glyph));
  }
  children.push(txt("span", { class: "mm-text" + ..., "data-path": l.path, ... }, l.text));
  return el("div", { class: "mm-line", "data-path": l.path, ... }, children);
});
```
HALO-04's wiring adds a THIRD case keyed off `l.braceState === BRACE_RESOLVED_EXTERNAL`: render a clickable cross-ref (`<a>`-like span with `href`/`data-ref-target`) INSTEAD of the glyph+text pair, per UI-SPEC Contract B's glyph table (lines 136-142 of 08-UI-SPEC.md): `BRACE_HIDDEN` → `▸` `--silver-700`; `BRACE_REVEALED_INTERNAL` → `▾` `--silver-300`; `BRACE_RESOLVED_EXTERNAL` → no glyph on this line, draw a link instead.

**graphVDom's missing link-draw to add** — must extend `lineEls`/`edges` construction (lines 108-114) with a NEW edge category for resolved-external targets, reusing the EXACT no-dasharray idiom already used for normal containment edges in this same function:
```js
// EXISTING graphVDom edge draw (containment only, lines 108-114):
const lineEls = edges.map((e) => {
  const a = pos.get(e.from), b = pos.get(e.to);
  return el("line", {
    x1: String(a.cx), y1: String(a.cy), x2: String(b.cx), y2: String(b.cy),
    stroke: "var(--slate-border,#c0c0c0)", "stroke-width": "1", opacity: "0.7",
  });
});
```
The resolved-external link reuses this SAME pattern, swapping the stroke color per UI-SPEC Color section: `--accent-arrow` `#ffd700` (3D-backed target, the same `drawConcept3DLinks` yellow, line 663 of `projector.mjs`) or `--silver-300` (2D-only target) — still NO `stroke-dasharray` either way.

**3D-aware variant reference (resolved-external link, 3D-backed case)** — `projector.mjs::drawConcept3DLinks` (lines 603-677), the no-dasharray + WeakMap-cached + true-NDC-frustum-test idiom:
```js
line.setAttribute("stroke", "#ffd700");        // --accent-arrow, the ONLY yellow permitted
line.setAttribute("stroke-width", "2");
line.setAttribute("stroke-opacity", "0.85");
// Solid — no dasharray (hard project-wide rule, T-06-11).
line.removeAttribute("marker-end");             // headless connector — no arrowheads
```

**OPEN QUESTION flagged at point of use:** whether the resolved-external link needs THIS 3D-aware (`drawConcept3DLinks`-style) variant, or whether the simpler 2D `#link-layer` SVG (same namespace `graphVDom` already renders into) suffices — RESEARCH.md Open Question 3 / UI-SPEC's own framing (lines 134, 142, 148 of 08-UI-SPEC.md: "ONLY when... carries `data-3d-node-id`") leans toward: use the plain 2D in-graph `<line>` shown above for the common case (both endpoints are graph-mode children of the same panel expansion), and reach for `drawConcept3DLinks`'s pattern ONLY if a resolved-external target is independently a 3D-only node — confirm via reading `editor.html`'s graph-mode DOM mount before finalizing.

---

### `backend/static/js/fe/projector.mjs` (MODIFY — add `placeHaloCandidates`, `flyToNode`, `highlightNode`)

**Analog:** itself — `frameCameraToRoot`/`_stepCameraTween` (392-428) for the new `flyToNode`; `drawConcept3DLinks`/`nodeWorldPosition` (603-677, 711-713) for `highlightNode`'s position lookup; `azimuth`/`project` (699-717) for `placeHaloCandidates`'s angular math consumer role.

See excerpts under `halo_cone.mjs` and `stepper.mjs` above — these three new functions are SIBLINGS exposed from this same module's existing return/export object (line 757: `nodeWorldPosition, drawConcept3DLinks,` — the export list `halo_cone.mjs`/`stepper.mjs` must extend with the three new names).

---

### `backend/services/ui_state_service.py` (POSSIBLE MODIFY — STEP-01 chunk-id resolution, per Open Question 1's CONFIRMED finding)

**Analog:** itself — `set_signal_stream` (684-721) / `advance_signal` (723-752), both already shown above under `stepper.mjs`. If the planner picks backend-side resolution (recommended), the new field threads through the SAME `entry.update({...})` dict-merge pattern both functions already use — no new data structure, just one more key (`chunk_id`) resolved from `pattern_map.<hash>.sampled_chunks[signal_index]` at the point `entry.update(...)` is built.

---

### Test/probe/e2e scaffolds

**`halo_cone.test.mjs` (NEW)** — analog: `magic_markdown_halo.test.mjs` (existing, pure-function unit tests over `haloLayout`'s `{cx,cy}`/`r`/`angle` outputs for known inputs). Mirror its "pure-fn, no DOM, plain Node `node:test`" structure for `placeOnCone`'s 3D outputs.

**`stepper.test.mjs` (NEW)** — analog: `projector.test.mjs` (existing). Mirror its pattern for asserting tween state/camera position over time without a real THREE renderer (stub camera/controls objects).

**`magic_markdown.test.mjs` (EXTEND)** — add cases asserting `renderGraph`'s node shape now includes `braceState` matching `classifyBraceStates`'s per-line output, and `panelVDom`/`graphVDom` branch correctly (existing `iterableNode` per-signal test shape in this file, per RESEARCH Sources, is the structural precedent for new per-state test cases).

**`scripts/probe_live_*.py` (NEW, D-01 acceptance)** — analogs: `scripts/probe_live_archive_scan.py` (real Selenium scan → real retrieval → pin → compile pattern) and `scripts/probe_live_duckduckgo_walkthrough.py`. Mirror their structure: clean-GPU preflight assertion → real scan trigger → poll WS until `done` → real `/apparitions/{focal_id}?transport=1` call → assert `transport.{radial,along_ray}` monotonic in `transport.similarity` across the returned candidate list → delete top candidate → re-call and assert the next-most-similar now occupies the vacated cone slot.

**e2e (`halo.spec.js` vs `object_exploration.spec.js`)** — analog: existing `halo.spec.js` (HALO-01/02 coverage, `__mm_halo_rotate` test hook pattern, confirmed via direct read per RESEARCH Sources). RESEARCH's Pitfall 4 / Open Question 4 explicitly leaves this unresolved for the planner — flagged here again: default recommendation is `halo.spec.js` for HALO-03 cone-transport cases (topically exact, same file's existing hooks) and the planner's explicit choice (stated in the plan, not guessed) for HALO-04/STEP-01 cases.

## Shared Patterns

### D10 — Backend computes, frontend renders (cross-cutting, applies to ALL three new/modified surfaces)
**Source:** `routes.py::get_apparitions` transport branch + `ui_state_service.py::advance_signal`/`set_signal_stream`
**Apply to:** `halo_cone.mjs`, `stepper.mjs`, and any modification touching `projector.mjs`/`magic_markdown.mjs`.
No file in this phase recomputes `pagerank · tfidf_cos · nomic_cos`, the `(1-s)*R`/`s*R` cone formula, or the signal-cursor modulo-wrap math client-side. Every new frontend function takes already-computed backend values (`transport.{similarity,radial,along_ray}`, `state.signal_stream[card_id]`) and combines them with PURELY client-local state (`azimuth()`, `controls.target`, DOM rects).

### Solid-line-only stroke contract (cross-cutting)
**Source:** `magic_markdown_halo.mjs::haloVDom` (line 63), `projector.mjs::drawConcept3DLinks` (lines 663-666), `magic_markdown_panel.mjs::graphVDom` (lines 108-114)
**Apply to:** `halo_cone.mjs`'s cone rays, `graphVDom`'s new resolved-external link draw.
```js
stroke: "var(--slate-border,#c0c0c0)" /* or "#ffd700" for 3D-backed */, "stroke-width": "1" /* or "2" */, opacity: "0.5" /* or "0.85"/"0.7" */
// NEVER set stroke-dasharray — hard project-wide rule (CLAUDE.md Forbidden Concepts)
```

### Pure-placement-function + thin-DOM-glue split (cross-cutting)
**Source:** `magic_markdown_halo.mjs` (`haloLayout` pure / `haloVDom` DOM), `magic_markdown_panel.mjs` (`panelVDom`/`graphVDom` pure vdom-spec / `mount`/`realise` thin DOM glue)
**Apply to:** `halo_cone.mjs` (keep `placeOnCone` pure, no THREE/DOM imports beyond reading `azimuth()`'s return value as a plain number) and `stepper.mjs` (keep the fetch+resolve logic separable from the `flyToNode`/`highlightNode` THREE-side calls so the resolution logic is independently unit-testable).

### One-invariant-edge, multi-render-state (cross-cutting, HALO-04-specific but shared between panel/graph)
**Source:** `magic_markdown.mjs::classifyBraceStates` (lines 259-281)
**Apply to:** `panelVDom` and `graphVDom` both — they must read the SAME `line.braceState`/`node.braceState` value computed ONCE by `classifyBraceStates`, never maintain two parallel classifications. Node-count parity (UI-SPEC Contract B, mandatory invariant) depends on both renderers consuming the identical upstream array.

## No Analog Found

None — all 9 classified files have at least a role-match analog already in the codebase (this is a narrow wiring phase per RESEARCH.md's own framing: "the hard computation already exists server-side or in a sibling frontend module").

## Open Questions Flagged At Point Of Use (carried from RESEARCH.md, re-surfaced here for the planner)

1. **Cone along-ray basis vector (Open Question 2 / Assumption A1)** — flagged under `halo_cone.mjs` above. Needs a direct read of `docs/DOMAIN_MODEL.md` §O.18 + `docs/frontend/halo.md` §3.2 / `docs/frontend/projector.md` §4-5 before fixing the exact 3D vector math (apex→camera-forward vs apex→scene-origin vs apex→candidate's original 3D position).
2. **Chunk-id resolution: backend vs frontend (Open Question 1)** — flagged under `stepper.mjs` and `ui_state_service.py` above. CONFIRMED (this pattern-mapping session re-grepped all `set_signal_stream(` call sites in `rollout_coordinator.py`) that `signal_id` is NEVER populated with a real chunk concept_id anywhere in the current codebase — this is genuinely new plumbing, not a hidden pre-existing answer. Recommend backend-side resolution per D10.
3. **Resolved-external link: 2D `#link-layer`/in-graph `<line>` vs 3D `drawConcept3DLinks` (Open Question 3)** — flagged under `magic_markdown_panel.mjs` above. Default to the simpler 2D in-graph `<line>` (same SVG namespace `graphVDom` already renders into); reach for the 3D-aware `drawConcept3DLinks` pattern only if a resolved-external target is independently a 3D-only node.
4. **e2e file placement: `halo.spec.js` vs `object_exploration.spec.js` (Pitfall 4 / Open Question 4)** — flagged under the test scaffolds section above. No default assumed; planner must state the choice explicitly in the plan.

## Metadata

**Analog search scope:** `backend/static/js/fe/` (all modules read directly), `backend/services/ui_state_service.py`, `backend/services/rollout_coordinator.py`, `backend/api/routes.py` (grep-located, RESEARCH.md already verbatim-quotes the relevant sections), `scripts/probe_live_*.py` (named, not re-read — RESEARCH.md already confirms their existence/pattern)
**Files scanned:** 9 target files classified; 6 analog source files read directly this session (`magic_markdown_halo.mjs`, `projector.mjs` ×2 reads, `magic_markdown.mjs`, `magic_markdown_panel.mjs`, `ui_state_service.py` grep, `rollout_coordinator.py`)
**Pattern extraction date:** 2026-06-27
