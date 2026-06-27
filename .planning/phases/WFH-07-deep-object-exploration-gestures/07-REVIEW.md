---
phase: WFH-07-deep-object-exploration-gestures
reviewed: 2026-06-27T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - backend/api/routes.py
  - backend/static/js/fe/gateway.mjs
  - backend/static/js/fe/magic_markdown.mjs
  - backend/static/js/fe/magic_markdown_panel.mjs
  - scripts/probe_live_duckduckgo_walkthrough.py
  - scripts/sim_frontend.py
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase WFH-07: Code Review Report

**Reviewed:** 2026-06-27
**Depth:** standard
**Files Reviewed:** 6 (phase-7 additions only; routes.py and sim_frontend.py are large pre-existing files reviewed only at the phase-7 deltas)
**Status:** issues_found

## Summary

Phase 7 ports the §M/§N object-exploration gestures into the served `fe/` editor: a `next_rank` type-graph fetch route (correctly registered as a static path BEFORE the parametric `/concepts/{concept_id}`), an `inherit_types` side-effect on the two edge-create routes, a gateway that can emit an array of requests (DELETE_REF → edge-delete + value-clear), the `mount()` seven-gesture DOM capture, and a live DuckDuckGo probe with a self-test gate.

The core contracts hold: route ordering is correct, `_inherit_io_types` is idempotent (it routes through `create_concept_edge`, which dedups on the five-tuple natural key), self-edges are guarded, the 400 source/target validation runs before the inherit fast-path, the transient drag line and resolved-external link are SOLID (no `stroke-dasharray`), and the probe's `all_real` gate genuinely raises with no stub fallback.

The defects found are robustness/edge-case issues, not correctness blockers: the drag state machine leaks `dragState` and an orphaned `<line>` when a drag is released outside the host; the gateway array-send has no partial-failure handling (DELETE_REF can leave a deleted edge with a stale `{ref}` still rendered); the 🔒 read-only gate guards single-left edit but NOT the destructive double-right DELETE_REF; `next_rank` truncates at a 50000-edge fetch limit that can silently drop neighbors; and `next_rank`'s `workspace_id=""` default risks missing `_default`-workspace edges in real GUI use.

## Warnings

### WR-01: Drag released outside the host leaks `dragState` and an orphaned transient line

**File:** `backend/static/js/fe/magic_markdown_panel.mjs:294-308` (also `:261-269`)
**Issue:** The `mouseup` teardown listener is bound to `dom`. If the user begins a drag (`dragState.dragging === true`, transient `<line>` appended) and then moves the pointer off the host and releases the mouse button outside `dom`, no `mouseup` fires on `dom`. The `mouseleave` handler at line 308 only clears state when the drag has NOT yet started (`if (dragState && !dragState.dragging) dragState = null;`) — an *active* drag that leaves the host is deliberately left intact, so `dragState` stays non-null and the transient `mm-drag-line` element is never removed. The comment at line 307 ("released outside the host (or aborted) tears down cleanly too") does not match the code, which only tears down a not-yet-dragging press.

This corrupts the state machine: subsequent `mousemove` over the host keeps redrawing the stuck line, and the next `mousedown` overwrites `dragState = {...}` *without* calling `teardownDrag()` (line 265), permanently orphaning the prior `lineEl` in the DOM (no `parentNode.removeChild`). Repeated drag-out-and-release accumulates orphaned `<line>` nodes.
**Fix:**
```js
// 1) On mousedown, tear down any stale drag before starting a new one:
dom.addEventListener("mousedown", (ev) => {
  if (ev.button !== 0) return;
  const gnode = ev.target.closest(".mm-gnode");
  if (!gnode) return;
  teardownDrag(); // clear any stuck prior drag + its orphaned line
  dragState = { sourceEl: gnode, sourcePath: gnode.getAttribute("data-path"),
    startX: ev.clientX, startY: ev.clientY, dragging: false, lineEl: null };
});

// 2) Tear down an ACTIVE drag that leaves the host too (it has no in-host
//    mouseup to discard it). A window-level mouseup is the robust fix:
const onWindowUp = () => { if (dragState) teardownDrag(); };
window.addEventListener("mouseup", onWindowUp);
// (and remove it when the panel is torn down / re-mounted)
```

### WR-02: Gateway array-send (DELETE_REF) has no partial-failure handling — edge delete can succeed while value-clear is lost (or vice versa)

**File:** `backend/static/js/fe/gateway.mjs:114-128` (array path), with `:63-83` building the pair
**Issue:** `DELETE_REF` with a backing `edgeId` returns a two-element array `[edge-delete, value-clear]`. `send()` fires them sequentially: `for (const r of req) last = await _sendOne(r)`. If `_sendOne` on the first request (DELETE `/api/concept_edges/{edgeId}`) throws, the `catch` swallows it and returns `null` — the value-clear never runs, so the displayed `{ref}` text persists while the user intended a delete. Worse, if the edge-delete *succeeds* but the value-clear (`/api/ui/edit_close`) then throws, the backing ConceptEdge is gone but the rendered value still shows the dangling `{ref}` — an inconsistent state with no rollback and no surfaced error beyond `opts.onError`. There is no atomicity across the pair and no per-step error reporting to the caller (the whole `send` resolves to `null`, indistinguishable from "no request built").
**Fix:** Make partial failure observable and recoverable — e.g. surface which step failed so the caller can retry/reconcile, and don't silently drop the second request:
```js
if (Array.isArray(req)) {
  const results = [];
  for (const r of req) {
    try { results.push(await _sendOne(r)); }
    catch (e) { opts.onError && opts.onError(e, r); results.push({ ok: false, error: e, req: r }); }
  }
  return results; // caller can detect a partial failure and reconcile UI/backend
}
```
(Or expose a backend transactional endpoint that deletes the edge and clears the value in one lifecycle event, matching the "one request, one lifecycle event" principle already applied to `inherit_types`.)

### WR-03: 🔒 read-only gate does NOT guard the destructive double-right DELETE_REF

**File:** `backend/static/js/fe/magic_markdown_panel.mjs:224-246` (contextmenu) vs the gate at `:194,206-207`
**Issue:** `readOnly` is computed once in `mount` and applied ONLY in the `click` handler (single-left edit, line 206-207). The `contextmenu` handler has no `readOnly` check, so on a read-only python-native / fixture node a double-right gesture still resolves `DELETE_REF` and fires `handlers.onDelete(path, el)`. The accompanying tests (`magic_markdown_panel.test.mjs:361-399`) only assert that *exploration* gestures (fold/collapse/hover) survive the gate — DELETE_REF is a destructive **mutation**, not exploration. Allowing a locked node's `{ref}` to be deleted (and its backing edge removed) bypasses the 🔒 read-only contract (DOMAIN §8D.4.2: read-only nodes carry no edits). Fold/collapse are correctly left intact; only the delete mutation should be gated.
**Fix:**
```js
if (isDoubleRight) {
  lastRight = { ts: 0, el: null };
  const { action } = resolveGesture({ button: "right", clicks: 2, target: kind, mode: opts.mode });
  if (action === Action.DELETE_REF) {
    if (readOnly) return; // 🔒 — refuse destructive delete on a locked node
    const path = el.getAttribute("data-path");
    handlers.onDelete && handlers.onDelete(path, el);
  }
  return;
}
```

### WR-04: `next_rank` truncates at a 50000-edge fetch then filters in Python — silently incomplete neighbors

**File:** `backend/api/routes.py:2488-2507`
**Issue:** `get_concept_next_rank` calls `ge.list_concept_edges(workspace_id=workspace_id, limit=50000)` and then filters `edge.source_id == concept_id` in Python. `list_concept_edges` already accepts a `source_id` filter (used by `_inherit_io_types` at line 2449), but the route ignores it and fetches the whole workspace edge set. If a workspace has more than 50000 edges, the route silently truncates the candidate set, so a node's typed neighbors can be dropped without any error — `next_rank` returns an incomplete `neighbors` list and the caller cannot tell. (Performance of the full fetch is out of v1 scope, but the silent truncation is a correctness/robustness defect.)
**Fix:** Push the `source_id` filter into the query so the route fetches only the node's out-edges and the 50000 cap is no longer a truncation risk:
```python
edges = ge.list_concept_edges(workspace_id=workspace_id, source_id=concept_id)
for edge in edges:
    if edge.edge_type not in _NEXT_RANK_EDGE_TYPES:
        continue
    if edge.target_id == concept_id:
        continue
    ...
```

### WR-05: `_inherit_io_types` re-fires `apply_edge_create_lifecycle` for already-existing (idempotent) edges

**File:** `backend/api/routes.py:2455-2461` with callers at `:5290-5296` and `:5580-5586`
**Issue:** `_inherit_io_types` calls `ge.create_concept_edge(...)`, which is idempotent and returns the *existing* edge when the five-tuple already exists (`graph_editor.py:916-920`). The data integrity is fine, but the callers unconditionally feed every returned edge — including pre-existing ones — into `apply_edge_create_lifecycle` and append them to `inherited_edges`. On a repeat `inherit_types` link of the same source/target pair, this re-broadcasts "edge created" frames, re-schedules PageRank refit, and re-logs evolution entries for edges that already existed, and reports them as freshly `inherited_edges` in the response. This churns downstream consumers and misrepresents the inheritance as new on every retry (the lifecycle module otherwise treats create as a real mutation).
**Fix:** Have `_inherit_io_types` (or its callers) distinguish newly-created edges from returned-existing ones and only fan/report the new ones — e.g. capture the pre-existing edge_id set before the loop, or have `create_concept_edge` return a `(edge, created: bool)` tuple, and skip the lifecycle fan + `inherited_edges.append` when `created is False`.

## Info

### IN-01: Double-right DELETE_REF still commits the first click's single-right fold as a side effect

**File:** `backend/static/js/fe/magic_markdown_panel.mjs:239-245`
**Issue:** The first `contextmenu` of a double-right pair unconditionally resolves and fires the single-right action (TOGGLE_FOLD / COLLAPSE_TO_NODE) before the second click upgrades to DELETE_REF. So a double-right-delete also toggles the fold of the target as a visible side effect. This is **codified as intended** by `magic_markdown_panel.test.mjs:274` (`toggleCalls === 1` for the pair), so it is not an unintended bug — but it is a UX wrinkle worth noting: there is no way to defer the first action pending a possible double, so every delete flickers a fold first. Documenting it here so it is not mistaken for a regression later.
**Fix:** If undesired, debounce the single-right action behind a short timer that is cancelled when the double completes (at the cost of added latency on every single-right fold). No change recommended unless the flicker is reported.

### IN-02: `next_rank` `workspace_id=""` default risks missing `_default`-workspace edges in real GUI use

**File:** `backend/api/routes.py:2466` (`workspace_id: str = ""`)
**Issue:** `next_rank` defaults `workspace_id` to `""` and passes it to `list_concept_edges`, which filters `e.workspace_id = ""` whenever the value is not `None`. The phase-7 probe and the `duckduckgo-walkthrough` scenario both materialise fixtures and link edges under workspace `""`, so they stay self-consistent. But much of the app's canonical state lives under `_default` (per CLAUDE.md). A GUI caller that omits `workspace_id` would query the empty-string workspace and find no typed neighbors for a `_default` node — an empty `neighbors` list with no error. Not exercised by phase-7 tests because they pin `""` throughout.
**Fix:** Either default to the same workspace the rest of the GUI uses, or treat `""` as "all workspaces" (pass `None` to `list_concept_edges`) so the route does not silently scope to the empty-string workspace. Confirm the intended default against how `_default` vs `""` is resolved elsewhere.

### IN-03: `assert_shadow_dom_present` is exercised only by `--self-test`, never by the real walkthrough

**File:** `scripts/probe_live_duckduckgo_walkthrough.py:124-135` (defined), `:438-448` (self-test only)
**Issue:** `assert_shadow_dom_present` is one of the three "pure assertion helpers" and is proven to have teeth by the self-test, but the real `main()` walkthrough (lines 497-510) never calls it — the real run asserts `all_real`, scan completion, `assert_min_chunks`, inherit success, rank-1 minimalism, next_rank reachability, and signal iteration, but never the ShadowDOM `url`/`dom` rank-1 presence (N.7) the helper checks. The N.7 ShadowDOM assertion the docstring (lines 124-127) describes is therefore covered only against a hand-built stub fixture, not against the real scan payload. Consider wiring `assert_shadow_dom_present` into the real path against the actual scanner resolution, or drop the claim that the real run verifies N.7.

### IN-04: Drag transient-line SVG host fallback (`|| dom`) appends an SVG `<line>` into a non-SVG `<div>` in panel mode

**File:** `backend/static/js/fe/magic_markdown_panel.mjs:279`
**Issue:** `const svgHost = dom.querySelector("svg.mm-edges") || dom;` falls back to the root `dom` (a `<div class="mm-slate">` in panel mode) when no `svg.mm-edges` exists. An SVG `<line>` appended to an HTML `<div>` will not render. In practice the drag only starts on `.mm-gnode` elements, which exist solely in graph mode (where `svg.mm-edges` is present), so the fallback path is effectively unreachable for real drags — but the fallback is dead/incorrect and would silently no-op if a `.mm-gnode` ever appeared in panel mode. Harmless today; flag so the fallback isn't trusted as a real rendering path.
**Fix:** Drop the `|| dom` fallback (or guard the drag start on `isGraph`) so a transient line is only ever created when there is a real SVG host to hold it.

---

_Reviewed: 2026-06-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
