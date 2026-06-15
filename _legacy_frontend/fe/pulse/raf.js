/**
 * fe/pulse/raf.js — the ONE requestAnimationFrame loop for the whole app.
 *
 * Every Organ/Membrane registers an onFrame consumer rather than spinning
 * its own loop, so positions, lines, and panels agree every paint.
 * (code_specs/frontend/pulse.md §3)
 */

export class Raf {
  constructor() { this._cbs = []; this._running = false; this._raf = 0; }
  onFrame(cb) { this._cbs.push(cb); return () => { const i = this._cbs.indexOf(cb); if (i >= 0) this._cbs.splice(i, 1); }; }
  start() {
    if (this._running) return;
    this._running = true;
    const loop = (now) => {
      if (!this._running) return;
      for (const cb of this._cbs) { try { cb(now); } catch (e) { console.error('[raf]', e); } }
      this._raf = requestAnimationFrame(loop);
    };
    this._raf = requestAnimationFrame(loop);
  }
  stop() { this._running = false; cancelAnimationFrame(this._raf); }
}
