/**
 * fe/membranes/billboard.js — Real→Imaginary coupling (screen-rect only).
 *
 * One #fe-billboard; content swapped per projector hover. On click it captures
 * getBoundingClientRect() and pins a panel at that exact rect (freeze-at-rect),
 * POSTing /ui/pin. Only the screen rect crosses into the editor — no 3D coord.
 * (code_specs/frontend/membranes.md §1)
 */

import { ConceptView } from '../cell/concept_view.js';

export class Billboard {
  constructor(store, gateway, { el, pinLayer } = {}) {
    this.store = store;
    this.gateway = gateway;
    this.el = el;                 // #fe-billboard
    this.pinLayer = pinLayer;     // #fe-pin-layer
    this._id = null;
    this.el.style.display = 'none';
    this.el.addEventListener('click', (e) => { if (e.target.closest('[data-pin]')) this._pin(); });
  }

  /** Called by the projector on hover (id may be a concept id or a chunk id). */
  showHover(id, screenPt) {
    if (id == null) { this.hide(); return; }
    this._id = id;
    const node = this.store.read('concepts').get(id);
    const chunk = this.store.read('chunks').get(String(id));
    this.el.innerHTML = '';
    const head = document.createElement('div'); head.className = 'fe-bb-head';
    head.innerHTML = `<span class="fe-bb-title">${esc((node && node.name) || (chunk && (chunk.summary || chunk.url)) || id)}</span>`;
    const pin = document.createElement('button'); pin.className = 'fe-btn'; pin.dataset.pin = '1'; pin.textContent = '📌';
    head.append(pin);
    this.el.append(head);
    this.el.append(node ? ConceptView.collapsed(node) : this._chunkBody(chunk, id));
    if (screenPt) { this.el.style.left = `${screenPt.x + 14}px`; this.el.style.top = `${screenPt.y + 14}px`; }
    this.el.style.display = 'block';
    this.gateway.send('ui.hover', { node_id: String(id) }).catch(() => {});
  }

  _chunkBody(chunk, id) {
    const w = document.createElement('div'); w.className = 'fe-bb-body';
    if (!chunk) { w.textContent = `node ${id}`; return w; }
    if (chunk.url) { const a = document.createElement('div'); a.className = 'fe-bb-desc'; a.textContent = chunk.url; w.append(a); }
    if (chunk.summary) { const p = document.createElement('pre'); p.className = 'fe-bb-rendering'; p.textContent = chunk.summary; w.append(p); }
    return w;
  }

  _pin() {
    if (this._id == null) return;
    const rect = this.el.getBoundingClientRect();
    const panel = this.el.cloneNode(true);                 // freeze-at-rect
    panel.classList.add('fe-pinned');
    panel.style.left = `${rect.left}px`; panel.style.top = `${rect.top}px`;
    panel.style.width = `${rect.width}px`; panel.style.display = 'block';
    const pinBtn = panel.querySelector('[data-pin]'); if (pinBtn) { pinBtn.textContent = '×'; pinBtn.onclick = () => panel.remove(); }
    this.pinLayer.append(panel);
    this.gateway.send('ui.pin', { node_id: String(this._id), rect: { top: rect.top, left: rect.left, w: rect.width, h: rect.height } }).catch(() => {});
    this.hide();
  }

  hide() { this.el.style.display = 'none'; this._id = null; }
}

function esc(s) { return String(s == null ? '' : s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c])); }
