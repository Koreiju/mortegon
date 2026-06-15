/**
 * store.mjs — the WorkspaceStore (the fe/ spine, single source of truth).
 *
 * The frontend owns no truth: WS frames → applyFrame → store → views render.
 * This holds the normalized workspace state (concepts, edges, ui) and exposes
 * selectors the magic-markdown panel needs — notably `registry()`, which maps
 * each concept's ROOT (first) field to its parsed node so `{ref}` tokens
 * resolve (§V "externally referenced nodes, identified by their root field").
 *
 * Pure + framework-free → unit-testable in Node (see store.test.mjs).
 */
import { parse, buildRegistry } from "./magic_markdown.mjs";

export function createStore(initial) {
  const state = {
    concepts: {},     // id → { id, name, data, rendering, content_tree, ... }
    edges: [],        // { source, target, edge_type }
    ui: { expanded: {}, signals: {}, mode: {}, pinned: [] },
    ...(initial || {}),
  };
  const subs = new Set();
  const notify = () => { for (const fn of subs) fn(state); };

  /**
   * applyFrame — fold one backend WS frame into the store. The frame shapes
   * mirror the backend lifecycle broadcasts (concept_changed / concept_deleted
   * / edges / ui_state_changed); unknown frames are ignored (forward-compat).
   */
  function applyFrame(frame) {
    if (!frame || !frame.type) return state;
    switch (frame.type) {
      case "concept_changed": {
        const c = frame.concept || frame.node;
        if (c && c.id) state.concepts[c.id] = { ...state.concepts[c.id], ...c };
        break;
      }
      case "concept_deleted": {
        const id = frame.id || (frame.concept && frame.concept.id);
        if (id) delete state.concepts[id];
        break;
      }
      case "edges":
        if (Array.isArray(frame.edges)) state.edges = frame.edges.slice();
        break;
      case "ui_state_changed":
        state.ui = { ...state.ui, ...(frame.ui || {}) };
        break;
      default:
        return state;
    }
    notify();
    return state;
  }

  function getState() { return state; }
  function subscribe(fn) { subs.add(fn); return () => subs.delete(fn); }
  function concept(id) { return state.concepts[id]; }

  /**
   * The text body the magic-markdown panel renders for a concept. A scanned
   * HTML chunk uses its §U `content_tree`; an authored concept uses its `data`
   * (the field-tree); name prefixes as the root field when present.
   */
  function panelText(id) {
    const c = state.concepts[id];
    if (!c) return "";
    const body = c.content_tree || c.data || "";
    if (c.name && !String(body).startsWith(c.name)) {
      return c.name + (body ? "\n" + indent(body) : "");
    }
    return body;
  }

  /** Parse one concept's panel text into a magic-markdown node. */
  function node(id) { return parse(panelText(id)); }

  /**
   * registry() — every concept as a node keyed by its root field, so a `{ref}`
   * naming that field resolves. This is what lets a panel pull in an external
   * node by its first field (§V).
   */
  function registry() {
    return buildRegistry(Object.keys(state.concepts).map((id) => node(id)));
  }

  return { getState, subscribe, applyFrame, concept, panelText, node, registry };
}

function indent(text) {
  return String(text).split("\n").map((l) => "\t" + l).join("\n");
}

export default { createStore };
