# Phase 7: Deep Object-Exploration Gestures - Pattern Map

**Mapped:** 2026-06-23
**Files analyzed:** 10 (5 modify, 5 net-new incl. test scaffolds)
**Analogs found:** 8 / 10 (2 explicitly flagged NO ANALOG per RESEARCH.md correction)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/static/js/fe/magic_markdown_panel.mjs` (MODIFY: `mount()`) | component (DOM event wiring) | event-driven | its OWN `mount()` (lines 152-173, same file) + `cp/concept_graph.js` contextmenu `node_fold` handler | exact (self-extend) / role-match (legacy ref) |
| `backend/static/js/fe/magic_markdown.mjs` (MODIFY: typed-render mode) | utility (pure render fn) | transform | `cp/concept_graph.js::_pythonNativeTypedView` (lines 1366-1393) | role-match (algorithm port, not literal copy — different data shape) |
| `backend/static/js/fe/gateway.mjs` (MODIFY/confirm: buildRequest) | service (action→HTTP mapper) | request-response | its OWN `buildRequest` switch (lines 23-74, same file) | exact (self-extend) |
| `backend/static/js/fe/store.mjs` (consume edges + fold state) | store | event-driven | existing `applyFrame`/WS merge pattern (not re-read this pass; RESEARCH confirms "likely no change") | exact (self-extend) |
| `backend/api/routes.py` — new `GET /api/concepts/{id}/next_rank` | route | request-response | `editor_link` / `EditorLinkRequest` route family (lines 5043-5149); `/ui/node_fold` (lines 4376-4394) | role-match (new read route, same Pydantic+router conventions) |
| `backend/api/routes.py` — edge-create I/O-type-inheritance extension | route | CRUD | `EditorLinkRequest` + `editor_link` handler (lines 5043-5149) — confirmed NO type/ports/inherit field today | role-match (extend existing handler) |
| `frontend_e2e/object_exploration.spec.js` (NEW) | test | request-response | existing `frontend_e2e/*.spec.js` (e.g. Phase 6 projector spec) + `playwright.config.js` boot pattern | role-match |
| `magic_markdown*.test.mjs` extensions | test | transform | `magic_markdown_gestures.test.mjs` + `integration.test.mjs` (own existing assertion style) | exact |
| `scripts/sim_frontend.py` — `duckduckgo-walkthrough` scenario (NEW) | utility (REPL scenario) | event-driven | `_env_scenario_node_fold_roundtrip` (lines ~7780-7806) | exact (template) |
| `scripts/probe_live_duckduckgo_walkthrough.py` (NEW) | test (live probe) | request-response | `probe_python_api.py` (assertion style) + `probe_live_archive_scan.py` (real-Selenium-scan pattern) | role-match |

## Pattern Assignments

### `backend/static/js/fe/magic_markdown_panel.mjs::mount()` (component, event-driven)

**Analog:** same file's existing `mount()` (lines 140-173) for the wiring SHAPE; `cp/concept_graph.js` for the missing-gesture reference (contextmenu/node_fold, read-only 🔒 gate).

**Current state to extend** (verified, lines 152-173):
```javascript
export function mount(host, rootNode, opts = {}, handlers = {}) {
  host.innerHTML = "";
  const isGraph = opts.mode === "graph";
  const dom = realise(isGraph ? graphVDom(rootNode, opts) : panelVDom(rootNode, opts));
  dom.addEventListener("click", (ev) => {
    const drop = ev.target.closest(".mm-drop");
    if (drop) { handlers.onToggle && handlers.onToggle(drop.getAttribute("data-path")); ev.stopPropagation(); return; }
    const gnode = ev.target.closest(".mm-gnode");
    if (gnode && gnode.getAttribute("data-glyph")) {
      handlers.onToggle && handlers.onToggle(gnode.getAttribute("data-path")); return;
    }
    const text = ev.target.closest('.mm-text[data-editable="1"]');
    if (text) { handlers.onEdit && handlers.onEdit(text.getAttribute("data-path")); }
  });
  // double-left on the body (not a token/node) → panel ⇄ graph (M.7 / §V)
  dom.addEventListener("dblclick", (ev) => {
    if (ev.target.closest(".mm-drop, .mm-gnode, .mm-text")) return;
    handlers.onTogglePanelGraph && handlers.onTogglePanelGraph();
  });
  host.appendChild(dom);
  return dom;
}
```

**Pattern to mirror when adding new handlers:** same `ev.target.closest(...)` dispatch shape, same `handlers.onX && handlers.onX(...)` invocation convention, same call-through to `resolveGesture()` (never inline new classification logic — per RESEARCH "Don't Hand-Roll" table). New work:
1. `contextmenu` listener → classify `target` (self vs ref/dropdown/token) → call `resolveGesture({button:"right", clicks:1, target, mode})`.
2. Manual double-right debounce (no native double-right DOM event — RESEARCH Pitfall 4): track `{ts, target}` on each `contextmenu`; if a second fires on the same target within ~400ms, call `resolveGesture({button:"right", clicks:2, target})` instead of firing the single-right action.
3. `mousedown`/`mousemove`/`mouseup` drag-state machine (graph mode only): press on a node → track pointer → move-threshold (a few px) distinguishes drag from click → release over another node fires `resolveGesture({button:"left", drag:true})`; render the transient line per UI-SPEC "Drag-Wire Affordance Contract" during the drag.

**Read-only 🔒 gate to carry over** (verified, `cp/concept_graph.js` ~lines 1684-1708 per RESEARCH):
```javascript
const ro = /^fixture::/.test(node.backing_pointer || "") || /^python_/.test(node.type_hint || "");
// → single-left no-op highlight (edit refused); hover/right-click/double-left still work.
```

---

### `backend/static/js/fe/magic_markdown.mjs` (utility, transform — new typed-render mode)

**Analog:** `cp/concept_graph.js::_pythonNativeTypedView` (verified, lines 1366-1393) — algorithm to RE-IMPLEMENT as a pure function over the `Line[]`/vdom model, NOT a literal port (legacy operates on THREE.js card DOM + Babylon-era JSON shapes; the fe/ target operates on the `renderPanel`/`Line[]` model).

**Algorithm to mirror** (verified excerpt):
```javascript
_pythonNativeTypedView(rawData) {
    const d = JSON.parse(rawData);
    if (d && d.signature) {
        const inputs = (d.ports && Array.isArray(d.ports.inputs)) ? d.ports.inputs : null;
        if (inputs) {
            inputs.forEach(p => {
                if (p && p.name && p.name !== 'self')
                    lines.push(`${p.name}: ${p.type || p.type_ref || p.annotation || '?'}`);
            });
        }
        // ... fallback to signature-string parse via regex if no ports.inputs
        let out = (d.ports?.outputs?.[0]?.type || ...) ;
        if (out) lines.push(`→ ${out}`);
        return lines.join('\n');
    }
    if (d && Array.isArray(d.members))
        return d.members.map(mm => String(mm).split('::').pop()).join('\n');
}
```

**Port guidance (per RESEARCH Pattern 2):** write a NEW pure function e.g. `renderTypedPanel(node, opts)` inside `magic_markdown.mjs` that returns the project's `Line[]` shape (`{text, path, glyph, source, refTarget, ...}`), each typed row as `key : Type = value` (per UI-SPEC Type-Slot Row Rendering Contract). Gate this typed mode on EXACTLY the same condition as the read-only 🔒 check (RESEARCH Pitfall 3 / Common Pitfalls): `/^python_/.test(node.type_hint||'') || node.read_only===true` — never a separate "show types" flag, to avoid leaking types onto rank-1-minimalism user compute nodes.

**Backend edge types this typed view consumes** (verified, `python_api_materialiser.py` lines 19-22, 550, 584, 597-598):
```python
# OBJECT_HAS_PROPERTY — class → property
# OBJECT_HAS_FUNCTION — class → function
# FUNCTION_INPUT_TYPE — function → input parameter's type
# FUNCTION_OUTPUT_TYPE — function → return annotation's type
```
These edges already exist and are idempotent/transitively-closed (proven by `probe_python_api.py`). The new typed-render mode and the new `next_rank` backend route both consume this SAME edge vocabulary — do not invent a parallel one.

---

### `backend/static/js/fe/gateway.mjs::buildRequest` (service, request-response)

**Analog:** its OWN existing switch statement (verified, lines 23-74).

**Existing mapping pattern to extend** (verified excerpt, the WIRE_LINK and DELETE_REF cases — the two needing extension):
```javascript
case Action.WIRE_LINK:
case "concept-edge-create":
  return { method: "POST", path: "/api/concept_edges",
    body: { source_id: g.sourceId || card, target_id: g.targetId, edge_type: g.edgeType || "RELATES_TO", [WS]: ws } };

case Action.DELETE_REF:
case "concept-delete-ref":
  // removing a {ref} is a data edit on the owning card
  return { method: "POST", path: "/api/ui/edit_close",
    body: { card_id: card, node_path: g.path, value: g.value != null ? g.value : "", [WS]: ws } };
```

**Extension pattern:**
- `WIRE_LINK` case: add `inherit_types: true` (or similar) field to the body per D-03 — single synchronous side-effect on edge-create (RESEARCH Open Question 3 recommendation: prefer one request over a two-step frontend-orchestrated sequence, consistent with "cascade is the default").
- `DELETE_REF` case: per RESEARCH Pitfall 1 / Assumption A2, decide whether to ALSO fire `DELETE /api/concept_edges/{edge_id}` when the `{ref}` corresponds to a backing `ConceptEdge` — follow the SAME `switch`-case-returns-one-request shape; if a two-step delete is needed, prefer the gateway's existing `send()` wrapper firing two sequential `buildRequest`-shaped calls rather than inlining `fetch()` elsewhere (`GestureGateway.send`, lines 81-99, already owns this responsibility).

---

### `backend/api/routes.py` — new `GET /api/concepts/{id}/next_rank` (route, request-response)

**Analog:** `EditorLinkRequest` + `editor_link` handler (verified, lines 5043-5149) for the Pydantic-request + idempotency + lifecycle-dispatch CONVENTIONS (this new route is a GET so idempotency/lifecycle don't directly apply, but the request/response shape and docstring convention do); `/ui/node_fold` (lines 4376-4394, from RESEARCH excerpt) for a simpler existing GET-adjacent pattern.

**Convention to mirror** (verified excerpt, EditorLinkRequest):
```python
class EditorLinkRequest(BaseModel):
    """§9.5.1 Editor.link — new ConceptEdge through the lifecycle."""
    source_id: str
    target_id: str
    edge_type: str = "RELATES_TO"
    workspace_id: str = ""
    idempotency_key: Optional[str] = None

@router.post("/editor/link")
def editor_link(req: EditorLinkRequest):
    cached = _idempotency_lookup(req.workspace_id, f"editor:link:...", req.idempotency_key)
    if cached is not None:
        return cached
    ge = _get_graph_editor()
    try:
        edge = ge.create_concept_edge(...)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    ...
    return response
```

**New route pattern (no direct analog — net-new per RESEARCH Open Question 2):** filter `ConceptEdge` rows by `source_id` + `edge_type ∈ {OBJECT_HAS_PROPERTY, OBJECT_HAS_FUNCTION, FUNCTION_INPUT_TYPE, FUNCTION_OUTPUT_TYPE}`, resolve target `ConceptNode`s, return a rank-1 typed neighbor list. Mirror the existing router's typed-Pydantic-response convention even though there's no literal precedent for this exact shape; reuse `ge` (`_get_graph_editor()`) as the data-access seam, same as `editor_link`.

---

### `backend/api/routes.py` — edge-create I/O-type-inheritance extension (route, CRUD)

**Analog:** `EditorLinkRequest` / `editor_link` handler (verified, lines 5043-5149) — confirmed gap: **no type/ports/inherit field exists today**.

**Gap excerpt (verified, the field list to extend):**
```python
class EditorLinkRequest(BaseModel):
    source_id: str
    target_id: str
    edge_type: str = "RELATES_TO"
    workspace_id: str = ""
    idempotency_key: Optional[str] = None
    # NO type/ports/inherit field — N.4's "target inherits source's I/O types +
    # object model" has no server-side implementation today.
```

**Extension pattern:** add `inherit_types: bool = False` field; when true, after `ge.create_concept_edge(...)` succeeds, read the source node's `ports`/materialiser edges (`OBJECT_HAS_PROPERTY`/`FUNCTION_*_TYPE`) and write equivalent edges/fields onto the target — as a single synchronous side-effect inside the SAME handler (per RESEARCH Open Question 3), gated through the existing `apply_edge_create_lifecycle` so WS/index/evolution-log fan-out stays consistent (same call already present at lines 5139-5142).

---

### `frontend_e2e/object_exploration.spec.js` (test, request-response)

**Analog:** existing `frontend_e2e/*.spec.js` files (Phase 6's projector spec cited by RESEARCH) + `frontend_e2e/playwright.config.js` (verified: self-boots a stub backend via `scripts/_serve_for_tests.py` with `WFH_FAKE_SLM=1 WFH_FAKE_EMBEDDER=1 NO_WEBDRIVER=1`).

**Convention to mirror:** Playwright spec structure already established in the existing specs (not re-read this pass — RESEARCH already confirms shape); reuse the same `playwright.config.js` stub-boot fixture. New cases needed (RESEARCH Wave 0 Gaps, confirmed by grep — none exist today): hover-type-graph, ref-propagation render, drag-wire+delete, brace-state.

---

### `magic_markdown*.test.mjs` extensions (test, transform)

**Analog:** `magic_markdown_gestures.test.mjs` (resolver-level cases already exist for drag/double-right per RESEARCH) + `integration.test.mjs` (verified, full passing end-to-end pure-logic test below).

**Assertion style to mirror** (verified, `integration.test.mjs`):
```javascript
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
This SAME shape (build state → resolve gesture → assert resulting `Line[]` text) is what new typed-rendering-mode tests and DOM-capture tests should follow — extend `integration.test.mjs` for the duplicate-instance-proxy case (EXPLORE-02), and add cases to `magic_markdown_gestures.test.mjs` once the new DOM-capture layer is built (resolver-level cases for drag/double-right already exist — verify they cover the new layer, don't duplicate).

---

### `scripts/sim_frontend.py` — `duckduckgo-walkthrough` env-scenario (utility, event-driven)

**Analog:** `_env_scenario_node_fold_roundtrip` (verified, lines ~7780-7806).

**Template to mirror (verified excerpt):**
```python
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

**Shape for `duckduckgo-walkthrough`:** `purge` → `editor-create` (author `self=duckduckgo`) → a drag-wire-equivalent REPL action (extend `editor-link`, or a new `ui-wire-link` verb if the D-03 type-inheritance endpoint needs its own REPL action) → `ui-node-fold` to reveal rank-1 `url{}`/`dom{}` → assert against `ui-state` → (real-subsystem probe variant) trigger a real scan via the existing scan-trigger route and assert chunk iteration via the `{chunk samples}` iterable model.

---

### `scripts/probe_live_duckduckgo_walkthrough.py` (test/live probe, request-response)

**Analog:** `scripts/probe_python_api.py` (assertion style — grepped structure only, not deep-read this pass per RESEARCH) + `scripts/probe_live_archive_scan.py` (real-Selenium-scan pattern: per-snapshot WS watch through `done`, real retrieval, pin, compile_expand mirror, real LangGraph+GPT4All compile).

**Pattern to mirror:** same real-subsystem boot discipline as `probe_live_archive_scan.py` — confirm `all_real: true` via `/api/subsystem_status` before asserting; honor D-01's clean-GPU pre-flight (0 stray python/firefox + ~0 VRAM) immediately before boot, driven from the MAIN context (not a verifier subagent).

## Shared Patterns

### Gesture resolution — single source of truth
**Source:** `backend/static/js/fe/magic_markdown_gestures.mjs::resolveGesture` (verified, full file read, lines 1-77 — already implements all seven gestures correctly).
**Apply to:** every new DOM handler added to `mount()` (contextmenu, double-right debounce, drag state machine). Always populate `{button, clicks, target, mode, drag}` and call `resolveGesture()` — never inline a second `if (button===...)` classification chain.

### Action → HTTP request mapping
**Source:** `backend/static/js/fe/gateway.mjs::buildRequest` (verified, lines 23-74).
**Apply to:** any new gesture-triggered network call. Extend the existing `switch` with new `case` arms (or new body fields on existing arms) rather than adding ad-hoc `fetch()` calls in handlers.

### Fold-state persistence (backend-authoritative)
**Source:** `backend/services/ui_state_service.py::set_node_fold` (verified excerpt, ~lines 149-198) + `/ui/node_fold` route (verified excerpt, ~lines 4384-4394).
```python
def set_node_fold(self, workspace_id, card_id, field_path, *, expanded=True):
    """Toggles field_path in/out of node_fold_state[card_id]['expanded_paths'];
    removes the card_id entry entirely once its list empties; stamps updated_at;
    emits a 'node_fold' broadcast event."""

@router.post("/ui/node_fold")
def ui_node_fold(req: UINodeFoldRequest):
    svc = get_ui_state_service(broadcast=_ws_push)
    snap = svc.set_node_fold(req.workspace_id, req.card_id, req.field_path, expanded=bool(req.expanded))
    return {"ok": True, "state": snap.to_dict(), "node_fold_state": snap.node_fold_state}
```
**Apply to:** all new fold/expand handlers in `magic_markdown_panel.mjs` — use the EXISTING `fe/` structural `path` addressing scheme (from `renderPanel`'s `Line.path`), NOT the legacy `cp/` literal-token-text scheme. No new fold-state code needed server-side.

### Read-only / 🔒 gating
**Source:** `cp/concept_graph.js` (verified excerpt, ~lines 1684-1708 per RESEARCH).
```javascript
const ro = /^fixture::/.test(node.backing_pointer || "") || /^python_/.test(node.type_hint || "");
```
**Apply to:** both the new typed-rendering mode in `magic_markdown.mjs` (gate typed-line rendering on this SAME condition, per Pitfall 3) and the single-left no-op behavior in `mount()`'s click handler.

### Materialiser type-graph edge vocabulary
**Source:** `backend/services/python_api_materialiser.py` (verified, lines 19-22, 550, 584, 597-598).
**Apply to:** the new `next_rank` route, the typed-render mode, and the I/O-type-inheritance extension — all three must read/write the SAME four edge types (`OBJECT_HAS_PROPERTY`, `OBJECT_HAS_FUNCTION`, `FUNCTION_INPUT_TYPE`, `FUNCTION_OUTPUT_TYPE`), never a parallel vocabulary.

## No Analog Found

| File / Feature | Role | Data Flow | Reason |
|---|---|---|---|
| N.4 drag-wire-creates-edge-AND-inherits-I/O-types backend logic | service (graph mutation) | event-driven | RESEARCH confirms `cp/edge_manager.js` is a pure THREE.js 3D edge-line-geometry mixin with ZERO 2D gesture or type-inheritance logic — there is nothing to port. Design fresh against `object_exploration.md` N.4, using `EditorLinkRequest`/`editor_link` as a STRUCTURAL (not behavioral) template only. |
| N.6/M.11 duplicate-instance-proxy semantics | service / model | event-driven | RESEARCH confirms `cp/instance_manager.js` is a pure THREE.js `InstancedMesh` pooling mixin with ZERO object-instance-inheritance logic — nothing to port. Per RESEARCH Open Question 1, FIRST test whether the existing `buildRegistry`/`refTarget` live-resolution mechanism (which always resolves `{ref}` to the current live node, not a frozen snapshot) already satisfies "operationally calls the originating object" before building anything new — likely a zero-new-code item disguised as a hard one. |

## Metadata

**Analog search scope:** `backend/static/js/fe/*.mjs` (full reads: `magic_markdown_gestures.mjs`, `gateway.mjs`, `magic_markdown_panel.mjs` excerpt), `backend/static/js/cp/concept_graph.js` (targeted excerpt, lines 1360-1400), `backend/api/routes.py` (targeted excerpt, lines 5043-5157 + grep for class/route names), `backend/services/python_api_materialiser.py` (grep for edge-type constants), `scripts/sim_frontend.py` and probe files (per RESEARCH.md's own prior verified reads — not re-read this pass to avoid duplicate-range violations).
**Files scanned:** 7 read/grepped directly this pass + RESEARCH.md's prior-session reads incorporated by reference (REPL scenario template, probe style, e2e config — RESEARCH.md already quotes these verbatim with line numbers and this pass does not re-read them).
**Pattern extraction date:** 2026-06-23

## PATTERN MAPPING COMPLETE

**Phase:** 7 - Deep Object-Exploration Gestures
**Files classified:** 10
**Analogs found:** 8 / 10

### Coverage
- Files with exact analog (self-extend existing function/scenario): 5
- Files with role-match analog (legacy port or structural template): 5
- Files with no analog (greenfield design required): 2 (N.4 drag-wire type-inheritance backend logic; N.6/M.11 duplicate-instance-proxy semantics)

### Key Patterns Identified
- All seven gestures are ALREADY correctly resolved by `resolveGesture()` and ALREADY correctly mapped to HTTP requests by `buildRequest()` — the entire phase's DOM/HTTP work is wiring new event listeners (`contextmenu`, double-right debounce, drag state machine) that call these existing pure functions, never re-deriving gesture logic.
- The legacy typed-view reference is `cp/concept_graph.js::_pythonNativeTypedView`, NOT `cp/edge_manager.js`/`cp/instance_manager.js` as CONTEXT.md originally stated (RESEARCH correction, verified by direct read) — those two files are pure THREE.js 3D mixins with zero 2D/type-inheritance logic.
- Fold-state backend infrastructure (`ui_state_service.py::set_node_fold` + `/ui/node_fold`) is fully built and correct — use the existing `fe/` structural `path` addressing scheme, never the legacy caret/token-text scheme.
- N.4 (drag-wire type-inheritance) and N.6 (duplicate-instance proxy) have NO legacy precedent anywhere in the codebase and must be designed fresh against `object_exploration.md`, using the existing `EditorLinkRequest`/`editor_link` and `buildRegistry`/`refTarget` mechanisms only as structural templates, not behavioral sources.

### File Created
`C:\Users\isaac\Documents\web_fiber_haptics\.planning\phases\WFH-07-deep-object-exploration-gestures\07-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference analog patterns in PLAN.md files.
