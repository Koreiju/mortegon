/**
 * fe/membranes/link_layer.js — the only line-drawer.
 *
 * Undirected lines, NO arrowheads, NO dashes (§O.16). Hard links brighter +
 * thicker, soft links dimmer. Routed per rAF frame from card centres.
 * (code_specs/frontend/membranes.md §3)
 */

const SVGNS = 'http://www.w3.org/2000/svg';

export class LinkLayer {
  constructor(store, { svg, editor } = {}) {
    this.store = store;
    this.svg = svg;             // #fe-edges
    this.editor = editor;
    this._lines = new Map();    // edge_id -> <line>
  }

  route() {
    const edges = this.store.read('edges');
    const live = new Set();
    for (const [edgeId, edge] of edges) {
      const a = this._center(edge.source_id);
      const b = this._center(edge.target_id);
      if (!a || !b) continue;
      live.add(edgeId);
      let ln = this._lines.get(edgeId);
      if (!ln) { ln = document.createElementNS(SVGNS, 'line'); this.svg.append(ln); this._lines.set(edgeId, ln); }
      const hard = (edge.edge_type || '') !== 'SIMILAR_TO';
      ln.setAttribute('x1', a.x); ln.setAttribute('y1', a.y);
      ln.setAttribute('x2', b.x); ln.setAttribute('y2', b.y);
      ln.setAttribute('stroke', hard ? 'var(--steel-300, #b8c0c8)' : 'var(--steel-700, #555c63)');
      ln.setAttribute('stroke-width', hard ? '2' : '1');
      // NO marker-end (no arrowheads), NO stroke-dasharray (no dotted lines).
    }
    for (const [edgeId, ln] of this._lines) if (!live.has(edgeId)) { ln.remove(); this._lines.delete(edgeId); }
  }

  _center(conceptId) {
    const card = this.editor?.cards.get(conceptId);
    if (!card) return null;
    const r = card.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  }
}
