/**
 * fe/spine/frame_bus.js — the single inbound seam.
 *
 * One long-lived WebSocket to /api/ws/workspace/{id}. Every truth the
 * frontend receives arrives here and is handed to store.applyFrame(). No
 * view opens its own socket. Auto-reconnects with backoff.
 * (code_specs/frontend/spine.md §2; backend WS handler routes.py §515)
 */

export class FrameBus {
  constructor(store, { workspaceId = '_default', onStatus = () => {} } = {}) {
    this.store = store;
    this.workspaceId = workspaceId;
    this.onStatus = onStatus;
    this.ws = null;
    this._backoff = 500;
    this._closed = false;
    this._onFrameHooks = new Set();   // extra observers (e.g. activity dashboard)
  }

  onFrame(cb) { this._onFrameHooks.add(cb); return () => this._onFrameHooks.delete(cb); }

  connect() {
    this._closed = false;
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${location.host}/api/ws/workspace/${encodeURIComponent(this.workspaceId)}`;
    let ws;
    try { ws = new WebSocket(url); } catch (e) { this._scheduleReconnect(); return; }
    this.ws = ws;
    ws.onopen = () => { this._backoff = 500; this.onStatus('open'); };
    ws.onmessage = (ev) => {
      let frame;
      try { frame = JSON.parse(ev.data); } catch { return; }
      try { this.store.applyFrame(frame); } catch (e) { console.error('[frame_bus apply]', e); }
      for (const h of this._onFrameHooks) { try { h(frame); } catch {} }
    };
    ws.onclose = () => { this.onStatus('closed'); if (!this._closed) this._scheduleReconnect(); };
    ws.onerror = () => { try { ws.close(); } catch {} };
  }

  /** Send a client→server frame (e.g. spine_delta). */
  send(frame) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try { this.ws.send(JSON.stringify(frame)); return true; } catch {}
    }
    return false;
  }

  _scheduleReconnect() {
    this.onStatus('reconnecting');
    setTimeout(() => this.connect(), this._backoff);
    this._backoff = Math.min(this._backoff * 2, 8000);
  }

  close() { this._closed = true; try { this.ws && this.ws.close(); } catch {} }
}
