/**
 * fe/spine/gateway.js — the single outbound seam.
 *
 * Every gesture leaves through send(kind, args). A closed catalogue maps each
 * kind to the real backend route (verified against backend/api/routes.py and
 * the sim_frontend.py reference harness). Mutations carry an Idempotency-Key.
 * (code_specs/frontend/spine.md §3)
 */

const API = '/api';

// kind -> (args) => { method, path, body? , query? }
const ROUTES = {
  // reads
  'concepts.list':        () => ({ method: 'GET', path: '/concepts' }),
  'concept.get':          (a) => ({ method: 'GET', path: `/concepts/${enc(a.id)}` }),
  'nodes.get':            (a) => ({ method: 'GET', path: '/nodes', query: a }),
  'apparitions.get':      (a) => ({ method: 'GET', path: `/apparitions/${enc(a.focal_id)}`, query: { k: a.k ?? 8 } }),
  'apparitions.mode':     () => ({ method: 'GET', path: '/apparitions/mode' }),
  'completions.get':      (a) => ({ method: 'GET', path: '/concept_completions', query: a }),
  'closest_inverse.get':  (a) => ({ method: 'GET', path: `/closest_inverse/${enc(a.output_id)}` }),
  'halo.graph':           (a) => ({ method: 'GET', path: `/graph/halo/${enc(a.node_id)}` }),
  'details.get':          (a) => ({ method: 'GET', path: `/details/${a.node_id}` }),
  'ui.state':             () => ({ method: 'GET', path: '/ui/state' }),
  'subsystem.status':     () => ({ method: 'GET', path: '/subsystem_status' }),
  'scan_status':          () => ({ method: 'GET', path: '/scan_status' }),
  'evolution.log':        () => ({ method: 'GET', path: '/evolution_log' }),

  // concept lifecycle
  'concept.create':       (a) => ({ method: 'POST', path: '/concepts', body: a, idem: true }),
  'concept.patch':        (a) => ({ method: 'PATCH', path: `/concepts/${enc(a.id)}`, body: a.patch, idem: true }),
  'concept.delete':       (a) => ({ method: 'DELETE', path: `/concepts/${enc(a.id)}`, idem: true }),
  'edge.create':          (a) => ({ method: 'POST', path: '/concept_edges', body: a, idem: true }),
  'edge.delete':          (a) => ({ method: 'DELETE', path: `/concept_edges/${enc(a.edge_id)}`, idem: true }),

  // editor primitives (§9.5.1)
  'editor.create':        (a) => ({ method: 'POST', path: '/editor/create', body: a, idem: true }),
  'editor.link':          (a) => ({ method: 'POST', path: '/editor/link', body: a, idem: true }),
  'editor.overwrite':     (a) => ({ method: 'POST', path: '/editor/overwrite', body: a, idem: true }),
  'editor.delete':        (a) => ({ method: 'POST', path: '/editor/delete', body: a, idem: true }),

  // compile / layout
  'compile':              (a) => ({ method: 'POST', path: '/conceptual/compile', body: a, idem: true }),
  'compile_chain':        (a) => ({ method: 'POST', path: '/conceptual/compile_chain', body: a, idem: true }),
  'recompute_umap':       (a) => ({ method: 'POST', path: '/recompute_umap', body: a || {}, idem: true }),
  'radiation':            (a) => ({ method: 'POST', path: '/radiation', body: a, idem: true }),

  // scan
  'scan':                 (a) => ({ method: 'GET', path: '/snapshot', query: a }),
  'web_browser.scan':     (a) => ({ method: 'POST', path: '/web_browser/scan', body: a, idem: true }),
  'chunk_search':         (a) => ({ method: 'POST', path: '/chunk_search', body: a }),

  // agent
  'agent.spawn':          (a) => ({ method: 'POST', path: '/agent/spawn', body: a, idem: true }),
  'agent.tick':           (a) => ({ method: 'POST', path: '/agent/tick', body: a, idem: true }),

  // UI-state mirror (each broadcasts ui_state via the backend)
  'ui.hover':             (a) => ({ method: 'POST', path: '/ui/hover', body: a }),
  'ui.hover_rect':        (a) => ({ method: 'POST', path: '/ui/hover_rect', body: a }),
  'ui.select':            (a) => ({ method: 'POST', path: '/ui/select', body: a }),
  'ui.pin':               (a) => ({ method: 'POST', path: '/ui/pin', body: a }),
  'ui.pin_chrome':        (a) => ({ method: 'POST', path: '/ui/pin_chrome', body: a }),
  'ui.unpin':             (a) => ({ method: 'POST', path: '/ui/unpin', body: a }),
  'ui.collapse':          (a) => ({ method: 'POST', path: '/ui/collapse', body: a }),
  'ui.latch':             (a) => ({ method: 'POST', path: '/ui/latch', body: a }),
  'ui.edit_open':         (a) => ({ method: 'POST', path: '/ui/edit_open', body: a }),
  'ui.edit_close':        (a) => ({ method: 'POST', path: '/ui/edit_close', body: a }),
  'ui.halo_focus':        (a) => ({ method: 'POST', path: '/ui/halo_focus', body: a }),
  'ui.halo_clear':        (a) => ({ method: 'POST', path: '/ui/halo_clear', body: a }),
  'ui.viewport_spine':    (a) => ({ method: 'POST', path: '/ui/viewport_spine', body: a }),
  'ui.url_visibility':    (a) => ({ method: 'POST', path: '/ui/url_visibility', body: a }),
  'ui.autocomplete':      (a) => ({ method: 'POST', path: '/ui/autocomplete', body: a }),
  'ui.compile_expand':    (a) => ({ method: 'POST', path: '/ui/compile_expand', body: a }),
  'ui.compile_collapse':  (a) => ({ method: 'POST', path: '/ui/compile_collapse', body: a }),
  'ui.telemetry':         (a) => ({ method: 'POST', path: '/ui/telemetry', body: a }),

  // workspace
  'purge':                (a) => ({ method: 'POST', path: '/purge_workspace', body: a || {}, idem: true }),
};

function enc(s) { return encodeURIComponent(String(s)); }
function qs(obj) {
  if (!obj) return '';
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(obj)) if (v != null) p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : '';
}
let _idemCounter = 0;
function idemKey() { return `fe-${Date.now()}-${++_idemCounter}`; }

export class GestureGateway {
  constructor(store, { onError = () => {} } = {}) { this.store = store; this.onError = onError; }

  kinds() { return Object.keys(ROUTES); }

  async send(kind, args = {}, { echo } = {}) {
    const make = ROUTES[kind];
    if (!make) throw new Error(`[gateway] unknown gesture kind: ${kind}`);
    const spec = make(args) || {};
    const headers = { 'Content-Type': 'application/json' };
    if (spec.idem) headers['Idempotency-Key'] = args.idempotency_key || idemKey();
    if (echo) this.store.echo(echo.slice, echo.key, echo.value);
    const url = `${API}${spec.path}${qs(spec.query)}`;
    let res, data;
    try {
      res = await fetch(url, {
        method: spec.method,
        headers: spec.method === 'GET' ? undefined : headers,
        body: spec.body != null ? JSON.stringify(spec.body) : undefined,
      });
    } catch (e) {
      if (echo) this.store.clearEcho(echo.slice, echo.key);
      this.onError({ kind, error: String(e) });
      throw e;
    }
    const ct = res.headers.get('content-type') || '';
    data = ct.includes('application/json') ? await res.json().catch(() => null) : await res.text().catch(() => null);
    if (!res.ok) {
      if (echo) this.store.clearEcho(echo.slice, echo.key);
      this.onError({ kind, status: res.status, data });
      const err = new Error(`[gateway] ${kind} → HTTP ${res.status}`);
      err.status = res.status; err.data = data;
      throw err;
    }
    return data;
  }
}
