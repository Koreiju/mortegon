/**
 * fe/real/texture_cache.js — single image fetch path: mem -> image_proxy -> direct.
 * Never caches the transparent-PNG fallback so a transient failure re-resolves.
 * (code_specs/frontend/real.md §3)
 */

const TRANSPARENT = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';

export class TextureCache {
  constructor() { this._mem = new Map(); this._loader = window.THREE ? new THREE.TextureLoader() : null; this._loader && (this._loader.crossOrigin = 'anonymous'); }

  get(url) {
    if (!url) return Promise.resolve(this._fallback());
    if (this._mem.has(url)) return Promise.resolve(this._mem.get(url));
    const proxied = `/api/image_proxy?url=${encodeURIComponent(url)}`;
    return this._load(proxied)
      .catch(() => this._load(url))
      .then((tex) => { this._mem.set(url, tex); return tex; })
      .catch(() => this._fallback()); // not cached
  }

  _load(src) {
    return new Promise((resolve, reject) => {
      if (!this._loader) return reject(new Error('no THREE'));
      this._loader.load(src, resolve, undefined, reject);
    });
  }

  _fallback() {
    if (!this._fb && this._loader) this._fb = this._loader.load(TRANSPARENT);
    return this._fb;
  }
}
