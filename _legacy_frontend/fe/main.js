/**
 * fe/main.js — greenfield frontend entry. Wires the tiers per FRONTEND_REDESIGN
 * §11: Spine (frame_bus/store/gateway) · Cell · Real (projector) · Imaginary
 * (editor) · Membranes (billboard/halo/link_layer) · Pulse (raf/tweens).
 *
 * The frontend owns no truth: frames -> store -> views; gestures -> gateway ->
 * backend -> frames. Verified end-to-end via scripts/sim_frontend.py.
 */

import { WorkspaceStore } from './spine/store.js';
import { FrameBus } from './spine/frame_bus.js';
import { GestureGateway } from './spine/gateway.js';
import { Raf } from './pulse/raf.js';
import { Tweens } from './pulse/tweens.js';
import { Projector } from './real/projector.js';
import { Editor } from './imaginary/editor.js';
import { Halo } from './membranes/halo.js';
import { Billboard } from './membranes/billboard.js';
import { LinkLayer } from './membranes/link_layer.js';

function $(id) { return document.getElementById(id); }
function setStatus(s, cls) { const el = $('fe-status'); if (el) { el.textContent = s; el.dataset.state = cls || s; } }

async function whenThree(timeoutMs = 8000) {
  const t0 = Date.now();
  while (!window.THREE) { if (Date.now() - t0 > timeoutMs) throw new Error('THREE failed to load'); await new Promise((r) => setTimeout(r, 30)); }
}

async function boot() {
  await whenThree();
  const workspaceId = '_default';

  const store = new WorkspaceStore();
  const gateway = new GestureGateway(store, { onError: (e) => console.warn('[gateway]', e) });
  const tweens = new Tweens();
  const raf = new Raf();

  const halo = new Halo(store, gateway, { layer: $('fe-halo-layer') });
  const editor = new Editor(store, gateway, { layer: $('fe-editor-layer'), halo });
  const linkLayer = new LinkLayer(store, { svg: $('fe-edges'), editor });
  const billboard = new Billboard(store, gateway, { el: $('fe-billboard'), pinLayer: $('fe-pin-layer') });

  const projector = new Projector(store, {
    canvas: $('fe-canvas'),
    tweens,
    onHover: (id, pt) => billboard.showHover(id, pt),
    onPick: (id, pt) => { billboard.showHover(id, pt); billboard._pin(); },
  });
  window.__fe = { store, gateway, projector, editor, raf };  // debug handle

  // The one rAF loop: advance tweens -> render 3D -> route 2D links.
  raf.onFrame((now) => { tweens.advance(now); projector.tick(); linkLayer.route(); });
  raf.start();

  // FrameBus: the single inbound seam.
  const bus = new FrameBus(store, { workspaceId, onStatus: (s) => setStatus(s === 'open' ? 'live' : s, s) });
  bus.onFrame((f) => { if (f.type === 'done') setStatus('live'); });
  bus.connect();

  // Hydrate concepts (REST) so the editor populates immediately.
  try { const r = await gateway.send('concepts.list'); store.hydrateConcepts(r.concepts || []); }
  catch (e) { console.warn('hydrate concepts failed', e); }

  // Toolbar.
  $('fe-new-concept')?.addEventListener('click', () => editor.createConcept());
  $('fe-recompute')?.addEventListener('click', () => gateway.send('recompute_umap', {}).then(() => setStatus('umap ✓')).catch(() => setStatus('umap ✗')));
  $('fe-scan')?.addEventListener('click', async () => {
    setStatus('scanning…');
    try { await gateway.send('scan', {}); } catch { setStatus('scan ✗ (no driver in harness)'); }
  });
  $('fe-frame')?.addEventListener('click', () => projector.frameAll());
  const search = $('fe-search');
  search?.addEventListener('keydown', async (e) => {
    if (e.key !== 'Enter') return;
    const q = search.value.trim(); if (!q) return;
    try { const r = await gateway.send('chunk_search', { query: q, k: 20 }); renderResults(r); }
    catch (err) { renderResults({ error: String(err) }); }
  });

  setStatus('connecting…');
}

function renderResults(r) {
  const box = $('fe-results'); if (!box) return;
  box.innerHTML = '';
  const rows = (r && (r.results || r.hits || r.chunks)) || [];
  if (r && r.error) { box.innerHTML = `<div class="fe-empty">${r.error}</div>`; return; }
  if (!rows.length) { box.innerHTML = '<div class="fe-empty">No results.</div>'; return; }
  for (const row of rows) {
    const d = document.createElement('div'); d.className = 'fe-result';
    d.innerHTML = `<div class="fe-result-title">${esc(row.title || row.summary || row.url || row.chunk_id || '?')}</div>` +
      (row.score != null ? `<span class="fe-result-score">${Number(row.score).toFixed(3)}</span>` : '');
    box.append(d);
  }
}
function esc(s) { return String(s == null ? '' : s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c])); }

boot().catch((e) => { console.error('[fe boot]', e); setStatus('boot error: ' + e.message, 'error'); });
