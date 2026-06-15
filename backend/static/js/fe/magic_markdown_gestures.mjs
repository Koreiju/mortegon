/**
 * magic_markdown_gestures.mjs — the gesture → transformation resolver.
 *
 * V.5: "All gestures with right and left clicks and double-clicks are supposed
 * to define transformations and navigations between these representations."
 * This is the single, pure, testable mapping from a raw gesture to the editor
 * action that moves between the three representations (knowledge panel ⇄
 * text-tree fields ⇄ circular computation-graph nodes). The DOM layer only
 * classifies the gesture and dispatches the returned action; no editor logic
 * lives in event handlers.
 *
 * Realises the M.6–M.8 / N.4 / N.13 / §7.3.4 gesture model on the slate.
 */

export const Action = {
  EDIT_TOKEN: "edit_token",            // single-left a token → borderless edit (M.8)
  TOGGLE_FOLD: "toggle_fold",          // right-click a {ref} / dropdown → internalize⇄externalize inline
  COLLAPSE_TO_NODE: "collapse_to_node",// right-click self → rank-dominance collapse to the circular node (S.5)
  TOGGLE_PANEL_GRAPH: "toggle_panel_graph", // double-left body → panel ⇄ graph (M.7)
  WIRE_LINK: "wire_link",              // left-drag node→node → wire + inherit I/O (N.4)
  DELETE_REF: "delete_ref",            // double-right a {ref}/instance → delete (N.13)
  NONE: "none",
};

/**
 * resolveGesture(g) → { action, ... } where g = {
 *   button: 'left' | 'right',
 *   clicks: 1 | 2,
 *   target: 'dropdown' | 'ref' | 'token' | 'self' | 'body',
 *   mode:   'panel' | 'graph',
 *   drag?:  boolean,          // press-move-release between two nodes
 * }
 *
 * Non-collision (object_exploration §18.32): button + click-count + target
 * disambiguate every gesture; single-left never races right-click; double-left
 * targets body/self outside a token; a drag is distinct from a click.
 */
export function resolveGesture(g = {}) {
  const { button = "left", clicks = 1, target = "body", mode = "panel", drag = false } = g;

  // A drag between nodes wires a link (graph form especially), inheriting types.
  if (button === "left" && drag) {
    return { action: Action.WIRE_LINK };
  }

  if (button === "left") {
    if (clicks === 2) {
      // double-left on the body/self toggles the panel⇄graph dialectic
      if (target === "body" || target === "self") return { action: Action.TOGGLE_PANEL_GRAPH };
      // double-left elsewhere falls back to single-left intent
      return resolveGesture({ ...g, clicks: 1 });
    }
    // single-left
    if (target === "dropdown") return { action: Action.TOGGLE_FOLD };   // clicking the ▸/▾ char
    if (target === "ref" || target === "token") return { action: Action.EDIT_TOKEN };
    return { action: Action.NONE };
  }

  if (button === "right") {
    if (clicks === 2) {
      // double-right deletes a reference/instance (N.13)
      if (target === "ref" || target === "token") return { action: Action.DELETE_REF };
      return { action: Action.NONE };
    }
    // single-right
    if (target === "self") return { action: Action.COLLAPSE_TO_NODE };       // rank-dominance collapse
    if (target === "ref" || target === "dropdown" || target === "token") {
      return { action: Action.TOGGLE_FOLD };                                 // internalize⇄externalize inline
    }
    return { action: Action.NONE };
  }

  return { action: Action.NONE };
}

export default { Action, resolveGesture };
