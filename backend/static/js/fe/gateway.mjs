/**
 * gateway.mjs — the single outbound seam (the fe/ spine).
 *
 * Intent flows one way: gesture → buildRequest → backend mirror route → frames
 * → store. `buildRequest` is PURE (gesture → { method, path, body }) so the
 * mapping is unit-testable; `GestureGateway` is the thin fetch glue. The routes
 * are the §9 "backend links to preserve" contract (the /api/ui/* mirror +
 * /api/concepts + /api/concept_edges) — so every panel gesture round-trips
 * through the same backend a REPL action would (R.8 REPL-mirrored).
 *
 * Bodies are kept minimal; exact field-schema reconciliation with the route
 * request models is the live-integration step.
 */
import { Action } from "./magic_markdown_gestures.mjs";

const WS = "workspace_id";

/**
 * buildRequest(gesture) → { method, path, body } | null.
 * `gesture` carries { action (from resolveGesture) | kind, cardId, path,
 * value, target, source, workspaceId, mode }.
 */
export function buildRequest(g = {}) {
  const ws = g.workspaceId || "_default";
  const card = g.cardId || g.id;
  switch (g.action || g.kind) {
    case Action.EDIT_TOKEN:
    case "concept-edit-data-row":
      return { method: "POST", path: "/api/ui/edit_close",
        body: { card_id: card, node_path: g.path, value: g.value, [WS]: ws } };

    case "concept-update":
      // commit an edited card's full §3 field text — the real persistence path
      // (PATCH → apply_update_lifecycle: WS broadcast + index + evolution log).
      // edit_close above is only the UI-mirror "who's editing" beacon.
      return { method: "PATCH", path: "/api/concepts/" + card,
        body: { data: g.data, [WS]: ws } };

    case Action.TOGGLE_FOLD:
    case "ui-node-fold":
      return { method: "POST", path: "/api/ui/node_fold",
        body: { card_id: card, node_path: g.path, expanded: !!g.expanded, [WS]: ws } };

    case Action.TOGGLE_PANEL_GRAPH:
      // direction by current mode: panel → expand to graph; graph → collapse
      return g.mode === "graph"
        ? { method: "POST", path: "/api/ui/compile_collapse", body: { card_id: card, [WS]: ws } }
        : { method: "POST", path: "/api/ui/compile_expand", body: { card_id: card, [WS]: ws } };

    case Action.COLLAPSE_TO_NODE:
    case "ui-dominance-collapse":
      return { method: "POST", path: "/api/ui/dominance_collapse", body: { card_id: card, [WS]: ws } };

    case Action.WIRE_LINK:
    case "concept-edge-create":
      // N.4 — inherit_types defaults false so non-wire callers (and any
      // caller not opting in) are unaffected; set g.inheritTypes:true to
      // fire the backend's single synchronous I/O-type-inheritance
      // side-effect (Open-Q3: one request, one lifecycle event).
      return { method: "POST", path: "/api/concept_edges",
        body: { source_id: g.sourceId || card, target_id: g.targetId, edge_type: g.edgeType || "RELATES_TO", inherit_types: !!g.inheritTypes, [WS]: ws } };

    case Action.DELETE_REF:
    case "concept-delete-ref": {
      // N.13 — double-right-delete of a {ref} must also remove the backing
      // ConceptEdge when one exists (RESEARCH Pitfall 1 / Assumption A2,
      // confirmed against object_exploration.md §N.13: "delete that
      // reference/instance", not merely clear its displayed text). When
      // g.edgeId is present, fire BOTH the edge delete AND the value-clear
      // as a sequential pair (GestureGateway.send's responsibility to fire
      // buildRequest-shaped calls in order — never an inline raw fetch()).
      // When g.edgeId is absent (a plain literal {ref}, no backing edge),
      // fall back to the existing value-clear-only behavior unchanged.
      const clearValueReq = { method: "POST", path: "/api/ui/edit_close",
        body: { card_id: card, node_path: g.path, value: g.value != null ? g.value : "", [WS]: ws } };
      if (g.edgeId) {
        return [
          { method: "DELETE", path: "/api/concept_edges/" + g.edgeId, body: null },
          clearValueReq,
        ];
      }
      return clearValueReq;
    }

    case "ui-pin":
      return { method: "POST", path: "/api/ui/pin", body: { chunk_id: g.chunkId || card, rect: g.rect, [WS]: ws } };
    case "ui-halo-focus":
      return { method: "POST", path: "/api/ui/halo_focus", body: { focal_card_id: card, [WS]: ws } };
    case "concept-create":
      return { method: "POST", path: "/api/concepts", body: { name: g.name || "", data: g.data || "", [WS]: ws } };
    default:
      return null;
  }
}

/**
 * GestureGateway(store, opts) — sends gestures to the backend and feeds the
 * returned frames back into the store. `opts.fetchImpl(method, url, body)`
 * defaults to window.fetch; `opts.base` is the API origin.
 */
export function GestureGateway(store, opts = {}) {
  const base = opts.base || "";
  const fetchImpl = opts.fetchImpl || ((m, url, body) =>
    fetch(url, { method: m, headers: { "Content-Type": "application/json" },
      body: body == null ? undefined : JSON.stringify(body) }).then((r) => r.json()));
  async function _sendOne(req) {
    const res = await fetchImpl(req.method, base + req.path, req.body);
    // backend lifecycle returns frames (or the store gets them via WS); fold
    // any inline frames so the optimistic loop stays consistent.
    if (res && res.frames && store) for (const f of res.frames) store.applyFrame(f);
    else if (res && res.type && store) store.applyFrame(res);
    return res;
  }
  async function send(gesture) {
    const req = buildRequest(gesture);
    if (!req) return null;
    try {
      // N.13 — DELETE_REF with a backing edge yields an ARRAY of
      // buildRequest-shaped calls (edge-delete then value-clear); fire them
      // sequentially through the SAME glue rather than an inline fetch().
      if (Array.isArray(req)) {
        let last = null;
        for (const r of req) last = await _sendOne(r);
        return last;
      }
      return await _sendOne(req);
    } catch (e) { opts.onError && opts.onError(e); return null; }
  }
  return { send, buildRequest };
}

export default { buildRequest, GestureGateway };
