/**
 * fe/pulse/tweens.js — interruptible eased tweens.
 *
 * A new target on a live handle recomputes from the CURRENT interpolated
 * value (never restarts/snaps) — this is what makes a umap_canonical
 * retarget mid-scan smooth. No tween holds authoritative state.
 * (code_specs/frontend/pulse.md §2)
 */

const easeInOutCubic = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

export class Tweens {
  constructor() { this._live = new Map(); } // handle(obj) -> { from, to, t0, ms, apply }

  /** Tween a 3-vector field on `target` toward `to` ([x,y,z]). */
  toVec3(target, to, { ms = 400, key = 'position' } = {}) {
    const cur = this._currentVec3(target, key);
    this._live.set(`${tid(target)}:${key}`, {
      target, key, kind: 'vec3',
      from: cur.slice(), to: to.slice(), t0: performance.now(), ms,
    });
  }

  toScalar(setter, getter, to, { ms = 250, id } = {}) {
    const k = `scalar:${id}`;
    this._live.set(k, { kind: 'scalar', setter, from: getter(), to, t0: performance.now(), ms });
  }

  _currentVec3(target, key) {
    const v = target[key];
    if (v && typeof v.x === 'number') return [v.x, v.y, v.z];           // THREE.Vector3
    if (Array.isArray(v)) return v.slice();
    return [0, 0, 0];
  }

  advance(now) {
    if (!this._live.size) return;
    for (const [k, tw] of this._live) {
      const raw = tw.ms <= 0 ? 1 : Math.min(1, (now - tw.t0) / tw.ms);
      const e = easeInOutCubic(raw);
      if (tw.kind === 'vec3') {
        const x = lerp(tw.from[0], tw.to[0], e), y = lerp(tw.from[1], tw.to[1], e), z = lerp(tw.from[2], tw.to[2], e);
        const v = tw.target[tw.key];
        if (v && typeof v.set === 'function') v.set(x, y, z);
        else tw.target[tw.key] = [x, y, z];
      } else if (tw.kind === 'scalar') {
        tw.setter(lerp(tw.from, tw.to, e));
      }
      if (raw >= 1) this._live.delete(k);
    }
  }

  get activeCount() { return this._live.size; }
}

function lerp(a, b, t) { return a + (b - a) * t; }
let _tidSeq = 0;
const _tidMap = new WeakMap();
function tid(obj) { if (!_tidMap.has(obj)) _tidMap.set(obj, ++_tidSeq); return _tidMap.get(obj); }
