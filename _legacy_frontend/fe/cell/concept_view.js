/**
 * fe/cell/concept_view.js — the one record anatomy, four modes.
 *
 * One builder, modes elide (never a fork): 'card' (editor panel), 'collapsed'
 * (billboard), 'phantom' (halo, name-only), 'child' (value-only). Canonical
 * rows = name / description / value(data, field-tree) / compiled(rendering).
 * Fixtures + read_only nodes hide the delete affordance. (code_specs/frontend/cell.md §2)
 */

import { FieldTree } from './field_tree.js';

const el = (tag, cls, props = {}) => Object.assign(document.createElement(tag), cls ? { className: cls } : {}, props);

function isReadOnly(node) {
  const bp = node.backing_pointer || '';
  return bp.startsWith('fixture::') || /read_only|python_/.test(node.type_hint || '') || /"read_only"\s*:\s*true/.test(node.ui_state || '');
}

export const ConceptView = {
  /** Build a draggable editor card. handlers: {onPatch, onDelete, onCompile, onFocusField} */
  card(node, handlers = {}) {
    const ro = isReadOnly(node);
    const card = el('div', 'fe-card');
    card.dataset.conceptId = node.concept_id;
    card.dataset.readonly = ro ? '1' : '0';

    const header = el('div', 'fe-card-header');
    const name = el('input', 'fe-name', { value: node.name || '', placeholder: 'name', spellcheck: false });
    name.disabled = ro;
    const btns = el('div', 'fe-card-btns');
    const lock = ro ? el('span', 'fe-lock', { textContent: '🔒', title: 'read-only' }) : null;
    const compileBtn = el('button', 'fe-btn', { textContent: '⟳', title: 'compile' });
    const delBtn = ro ? null : el('button', 'fe-btn fe-btn-del', { textContent: '×', title: 'delete' });
    [lock, compileBtn, delBtn].forEach((b) => b && btns.append(b));
    header.append(name, btns);

    const body = el('div', 'fe-card-body');
    const descLbl = el('label', null, { textContent: 'description' });
    const desc = el('textarea', 'fe-desc', { value: node.description || '', placeholder: 'functional declaration (nomic-indexed)', spellcheck: false, rows: 2 });
    desc.disabled = ro;
    const valLbl = el('label', null, { textContent: 'value' });
    const val = el('textarea', 'fe-value', { value: FieldTree.pretty(node.data || ''), placeholder: 'field-tree (data)', spellcheck: false, rows: 3 });
    val.disabled = ro;
    const compiled = el('pre', 'fe-compiled');
    compiled.textContent = node.rendering || '';
    compiled.style.display = node.rendering ? 'block' : 'none';
    body.append(descLbl, desc, valLbl, val, compiled);

    card.append(header, body);

    // wiring
    if (!ro) {
      const commit = () => handlers.onPatch?.(node.concept_id, { name: name.value, description: desc.value, data: val.value });
      name.addEventListener('change', commit);
      desc.addEventListener('change', commit);
      val.addEventListener('change', commit);
      [name, desc, val].forEach((f) => {
        f.addEventListener('focus', () => handlers.onFocusField?.(node.concept_id, f));
      });
      delBtn?.addEventListener('click', () => handlers.onDelete?.(node.concept_id));
    }
    compileBtn.addEventListener('click', () => handlers.onCompile?.(node.concept_id));
    card._refs = { name, desc, val, compiled };
    return card;
  },

  /** Collapsed billboard content: name + description + rendering. */
  collapsed(node) {
    const wrap = el('div', 'fe-bb-body');
    wrap.append(el('div', 'fe-bb-name', { textContent: node.name || '(unnamed)' }));
    if (node.description) wrap.append(el('div', 'fe-bb-desc', { textContent: node.description }));
    if (node.rendering) wrap.append(el('pre', 'fe-bb-rendering', { textContent: node.rendering }));
    return wrap;
  },

  /** Phantom (halo): name only. */
  phantom(candidate) {
    const p = el('div', 'fe-phantom', { title: `score ${fmt(candidate.score)}` });
    p.textContent = candidate.name || candidate.card_id || candidate.concept_id || '?';
    p.dataset.id = candidate.card_id || candidate.concept_id || '';
    return p;
  },
};

function fmt(x) { return typeof x === 'number' ? x.toFixed(3) : String(x ?? ''); }
