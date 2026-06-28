/**
 * stepper.mjs — STEP-01: the 2D `{chunk samples}` stepper drives 3D focus
 * ONE-WAY (§O.6/§O.7/§O.11). A pure driver: it advances the existing
 * backend signal-stream cursor, reads the server-RESOLVED chunk id back
 * (D10 — the backend already correlated signal_index -> chunk id via
 * `ui_state_service.py::_resolve_signal_id`; this module never computes
 * that correlation itself), and focuses the 3D scene onto that chunk via
 * `flyToNode`/`highlightNode`.
 *
 * Hard constraints (08-UI-SPEC Interaction Contract C / D-03 / §O.6):
 *   - The 3D scene ALWAYS renders the FULL per-sample distribution. This
 *     module only ever calls flyToNode/highlightNode (camera + colour-slot
 *     focus) — it never adds, removes, or subsets nodes.
 *   - Strictly one-way: this module POSTs to /api/ui/signal_advance and
 *     reads the response. It never wires a 3D click/orbit callback that
 *     POSTs back into signal_advance — there is no such wiring anywhere in
 *     this file (the projector's own onFrame/click hooks are untouched;
 *     this module imports nothing from projector.mjs and registers no
 *     event listeners on it).
 *
 * `deps` are injected ({ fetch, flyToNode, highlightNode }) so the unit
 * test can stub them with no network and no THREE renderer (mirrors the
 * pure-driver-with-injected-effects split documented in 08-PATTERNS).
 */

/**
 * advanceAndFocus(cardId, step, deps) — POST the advance, read the
 * server-resolved chunk id (if any) for the new cursor position, and focus
 * the 3D scene onto it.
 *
 * @param {string} cardId - the `{chunk samples}` iterable card's id.
 * @param {number} step - the signal-cursor step (+1/-1, mirrors the
 *   existing `/api/ui/signal_advance` `step` field).
 * @param {{fetch: Function, flyToNode: Function, highlightNode: Function,
 *   workspaceId?: string, fieldPath?: string}} deps - injected effects.
 * @returns {Promise<{ ok: boolean, chunkId: string|null, state: object|null }>}
 *   chunkId is null when the resolved sample has no backing chunk id (an
 *   out-of-range / mismatched ordered list per V5 bounds-safety) — in that
 *   case flyToNode/highlightNode are NOT called (graceful no-op, never a
 *   focus jump to a stale/wrong node).
 */
export async function advanceAndFocus(cardId, step, deps) {
  const { fetch: fetchFn, flyToNode, highlightNode, workspaceId = "_default", fieldPath = "" } = deps;

  const res = await fetchFn("/api/ui/signal_advance", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ card_id: cardId, step, workspace_id: workspaceId, field_path: fieldPath }),
  });
  const payload = await res.json();
  const state = payload && payload.state ? payload.state : null;
  const entry = state && state.signal_stream ? state.signal_stream[cardId] : null;
  const chunkId = entry ? entry.signal_id || null : null;

  // D10 — chunkId is the server-resolved chunk id; this module performs NO
  // index->chunk correlation of its own. When unresolved (null), this is a
  // graceful no-op: never focus on a stale/guessed node.
  if (chunkId) {
    flyToNode(chunkId);
    highlightNode(chunkId);
  }

  return { ok: !!(payload && payload.ok), chunkId, state };
}
