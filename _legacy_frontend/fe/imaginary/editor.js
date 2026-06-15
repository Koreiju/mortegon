/**
 * fe/imaginary/editor.js — the Imaginary register: the 2D concept-graph editor.
 *
 * Renders concept cards (screen-px coords, never the 3D system) from the
 * store's concepts slice, reconciled keyed by concept_id. Create / edit /
 * delete / compile all leave through the gateway. (code_specs/frontend/imaginary.md)
 */

import { ConceptView } from '../cell/concept_view.js';
import { Reconciler } from '../pulse/reconciler.js';

export class Editor {
  constructor(store, gateway, { layer, halo } = {}) {
    this.store = store;
    this.gateway = gateway;
    this.layer = layer;                 // #fe-editor-layer
    this.halo = halo;
    this.cards = new Map();             // concept_id -> card element
    this._editing = new Set();          // concept_ids with an open editor field
    this._nextSlot = 0;
    store.subscribe((s) => s.concepts, () => this._reconcile());
    this._reconcile();
  }

  _reconcile() {
    const concepts = this.store.read('concepts');
    Reconciler.apply(this.cards, concepts, {
      isEditing: (id) => this._editing.has(id),
      onEnter: (id, node) => this._mount(node),
      onUpdate: (id, node, card) => this._refresh(card, node),
      onExit: (id, card) => card.remove(),
    });
  }

  _handlers() {
    return {
      onPatch: (id, patch) => this.gateway.send('concept.patch', { id, patch },
        { echo: { slice: 'concepts', key: id, value: { ...this.store.read('concepts').get(id), ...patch } } }).catch(() => {}),
      onDelete: (id) => this.gateway.send('concept.delete', { id }).catch(() => {}),
      onCompile: (id) => this.gateway.send('compile', { concept_id: id, use_slm: true, persist_rendering: true }).catch(() => {}),
      onFocusField: (id, fieldEl) => {
        this._editing.add(id);
        this.gateway.send('ui.edit_open', { card_id: id }).catch(() => {});
        fieldEl.addEventListener('blur', () => {
          this._editing.delete(id);
          this.gateway.send('ui.edit_close', { card_id: id }).catch(() => {});
        }, { once: true });
        // Halo: typing in a text field radiates apparitions (§O.3).
        if (this.halo && (fieldEl.classList.contains('fe-desc') || fieldEl.classList.contains('fe-name')))
          this.halo.attach(id, fieldEl);
      },
    };
  }

  _mount(node) {
    const card = ConceptView.card(node, this._handlers());
    this._place(card, node);
    this._makeDraggable(card);
    this.layer.append(card);
    this.cards.set(node.concept_id, card);
    return card;
  }

  _refresh(card, node) {
    const r = card._refs; if (!r) return;
    if (document.activeElement !== r.name) r.name.value = node.name || '';
    if (document.activeElement !== r.desc) r.desc.value = node.description || '';
    if (document.activeElement !== r.compiled && node.rendering != null) {
      r.compiled.textContent = node.rendering || '';
      r.compiled.style.display = node.rendering ? 'block' : 'none';
    }
  }

  _place(card, node) {
    let xy = null;
    try { if (node.layout_xy) xy = JSON.parse(node.layout_xy); } catch {}
    if (!xy || xy.x == null) {
      const cols = 4, gapX = 300, gapY = 220, ox = 320, oy = 90;
      const i = this._nextSlot++;
      xy = { x: ox + (i % cols) * gapX, y: oy + Math.floor(i / cols) * gapY };
    }
    card.style.left = `${xy.x}px`;
    card.style.top = `${xy.y}px`;
  }

  _makeDraggable(card) {
    const header = card.querySelector('.fe-card-header');
    if (!header) return;
    let sx, sy, ox, oy, dragging = false;
    header.addEventListener('pointerdown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
      dragging = true; card.setPointerCapture?.(e.pointerId);
      sx = e.clientX; sy = e.clientY; ox = parseFloat(card.style.left) || 0; oy = parseFloat(card.style.top) || 0;
      card.classList.add('fe-dragging');
    });
    header.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      card.style.left = `${ox + e.clientX - sx}px`;
      card.style.top = `${oy + e.clientY - sy}px`;
    });
    const end = () => { if (dragging) { dragging = false; card.classList.remove('fe-dragging'); } };
    header.addEventListener('pointerup', end);
    header.addEventListener('pointercancel', end);
  }

  /** Toolbar: spawn a new empty concept. */
  async createConcept(name = '') {
    try { await this.gateway.send('concept.create', { name: name || 'new concept', description: '', data: '' }); }
    catch (e) { console.warn('create concept failed', e); }
  }
}
