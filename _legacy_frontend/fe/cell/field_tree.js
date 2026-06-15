/**
 * fe/cell/field_tree.js — the data-self-defining interpreter.
 *
 * "Data is the schema": structure is parsed fresh per render. parse() detects
 * the shape (JSON | indent-tree | plaintext); print() is pure (key: value, tab
 * nesting, no syntax glyphs). Markers: {slug} -> ref. (code_specs/frontend/cell.md §1)
 */

export const FieldTree = {
  /** parse(raw) -> FieldNode root: { key, value, children[], path, meta }. */
  parse(raw) {
    const root = node('', '', '');
    if (raw == null || raw === '') return root;
    const text = String(raw);
    // Strategy 1: JSON object/array.
    const trimmed = text.trim();
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      try { return fromJson('', JSON.parse(trimmed), ''); } catch { /* fall through */ }
    }
    // Strategy 2: indent (tab/2-space) tree.
    if (/\n\s+\S/.test(text)) return fromIndent(text);
    // Strategy 3: plaintext leaf.
    root.value = text;
    return root;
  },

  /** print(node) -> pure-print string (key: value, tab nesting). */
  print(n, depth = 0) {
    const pad = '\t'.repeat(depth);
    if (!n.children.length) {
      if (n.key === '' && depth === 0) return n.value || '';
      return `${pad}${n.key}${n.value !== '' ? `: ${n.value}` : ''}`;
    }
    const head = depth === 0 && n.key === '' ? [] : [`${pad}${n.key}:`];
    const kids = n.children.map((c) => FieldTree.print(c, depth + (n.key === '' && depth === 0 ? 0 : 1)));
    return [...head, ...kids].join('\n');
  },

  /** All {slug} references found anywhere in the tree. */
  refs(n, out = new Set()) {
    const scan = (s) => { const m = String(s).matchAll(/\{([^{}]+)\}/g); for (const x of m) out.add(x[1]); };
    scan(n.key); scan(n.value);
    for (const c of n.children) FieldTree.refs(c, out);
    return [...out];
  },

  /** Pretty one-line-per-leaf rendering for a textarea (round-trips via parse on edit). */
  pretty(raw) {
    const root = FieldTree.parse(raw);
    if (!root.children.length) return root.value || '';
    return FieldTree.print(root);
  },
};

function node(key, value, path) { return { key, value: value ?? '', children: [], path, meta: detect(value) }; }
function detect(v) {
  const s = v == null ? '' : String(v);
  const meta = {};
  const ref = s.match(/^\{([^{}]+)\}$/); if (ref) meta.ref = ref[1];
  return meta;
}

function fromJson(key, val, path) {
  if (val !== null && typeof val === 'object') {
    const n = node(key, '', path);
    if (Array.isArray(val)) {
      val.forEach((v, i) => n.children.push(fromJson(String(i), v, `${path}/${i}`)));
    } else {
      for (const [k, v] of Object.entries(val)) n.children.push(fromJson(k, v, `${path}/${k}`));
    }
    return n;
  }
  return node(key, scalar(val), path);
}
function scalar(v) { return typeof v === 'string' ? v : JSON.stringify(v); }

function fromIndent(text) {
  const root = node('', '', '');
  const stack = [{ depth: -1, n: root }];
  for (const line of text.split('\n')) {
    if (!line.trim()) continue;
    const depth = (line.match(/^[\t ]*/)[0] || '').replace(/  /g, '\t').length;
    const body = line.trim();
    const ci = body.indexOf(':');
    const key = ci >= 0 ? body.slice(0, ci).trim() : body;
    const value = ci >= 0 ? body.slice(ci + 1).trim() : '';
    const n = node(key, value, key);
    while (stack.length > 1 && stack[stack.length - 1].depth >= depth) stack.pop();
    stack[stack.length - 1].n.children.push(n);
    stack.push({ depth, n });
  }
  return root;
}
