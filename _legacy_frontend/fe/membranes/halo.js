/**
 * fe/membranes/halo.js — apparition radiation around a focal field.
 *
 * Typing in a text field radiates name-only phantoms (apparitions) in a ring
 * around the focal card. Backend scores via the triple product
 * (GET /api/apparitions/{focal_id}); the frontend only renders. Clicking a
 * phantom wires it (soft->hard). (code_specs/frontend/membranes.md §2)
 */

import { ConceptView } from '../cell/concept_view.js';

export class Halo {
  constructor(store, gateway, { layer } = {}) {
    this.store = store;
    this.gateway = gateway;
    this.layer = layer;            // #fe-halo-layer
    this._focal = null;
    this._timer = 0;
    this._phantoms = [];
  }

  attach(focalId, fieldEl) {
    const onInput = () => this._schedule(focalId, fieldEl);
    fieldEl.addEventListener('input', onInput);
    this._schedule(focalId, fieldEl);
    fieldEl.addEventListener('blur', () => { clearTimeout(this._timer); setTimeout(() => this.clear(), 150); fieldEl.removeEventListener('input', onInput); }, { once: true });
  }

  _schedule(focalId, fieldEl) {
    clearTimeout(this._timer);
    this._timer = setTimeout(() => this.open(focalId, fieldEl), 220);
  }

  async open(focalId, anchorEl) {
    this._focal = focalId;
    let cands = [];
    try {
      const res = await this.gateway.send('apparitions.get', { focal_id: focalId, k: 8 });
      cands = res.candidates || res.apparitions || res || [];
    } catch { cands = this.store.read('apparitions').get(focalId) || []; }
    this.gateway.send('ui.halo_focus', { focal_card_id: focalId }).catch(() => {});
    this._render(cands, anchorEl);
  }

  _render(cands, anchorEl) {
    this.clear(false);
    const a = anchorEl?.getBoundingClientRect();
    const cx = a ? a.left + a.width / 2 : window.innerWidth / 2;
    const cy = a ? a.top : window.innerHeight / 2;
    const R = 150;
    cands.slice(0, 8).forEach((c, i, arr) => {
      const ang = (-Math.PI / 2) + (i / Math.max(1, arr.length)) * Math.PI * 2;
      const ph = ConceptView.phantom(c);
      ph.style.left = `${cx + Math.cos(ang) * R}px`;
      ph.style.top = `${cy + Math.sin(ang) * R}px`;
      ph.addEventListener('mousedown', (e) => { e.preventDefault(); this._wire(c); });
      this.layer.append(ph);
      this._phantoms.push(ph);
    });
  }

  _wire(candidate) {
    const target = candidate.card_id || candidate.concept_id;
    if (!this._focal || !target) return;
    this.gateway.send('edge.create', { source_id: this._focal, target_id: target, edge_type: 'RELATES_TO' }).catch(() => {});
    this.clear();
  }

  clear(resetFocal = true) {
    for (const p of this._phantoms) p.remove();
    this._phantoms = [];
    if (resetFocal && this._focal) { this.gateway.send('ui.halo_clear', {}).catch(() => {}); this._focal = null; }
  }
}
