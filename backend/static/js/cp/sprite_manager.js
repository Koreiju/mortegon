/**
 * cp/sprite_manager.js — Image/video sprite billboards spawned from
 * `html_raw` media extraction, and the NDJSON lazy-detail batch loader.
 *
 * Methods become ChunkProjector instance methods via prototype mixin.
 * THREE is a CDN global.
 */

export const SpriteManagerMixin = {

    _spawnImageBillboards(nodes) {
        if (!this._imageSprites)      this._imageSprites      = new Map();
        if (!this._extraSprites)      this._extraSprites      = new Map();
        if (!this._imageTextureCache) this._imageTextureCache = new Map();
        if (!this._imageProxyFailures) this._imageProxyFailures = new Set();
        // Per-host failure counters so we can surface "this domain is
        // unreachable" diagnostics instead of spamming one warning per
        // URL until we hit the suppression cap.
        if (!this._imageFailuresByHost) this._imageFailuresByHost = new Map();

        // Per-call diagnostics — counts how many candidate URLs we
        // tried this call vs. how many spawned a sprite. Surfaced via
        // _logSpriteDebug() at the end so the user can see in the
        // browser console whether images are being filtered out before
        // the network request, the proxy fetch is failing, or the
        // texture is loading but the sprite isn't appearing. The user
        // recently asked "Images have stopped being displayed on nodes
        // altogether" — this counter is the cheapest way to confirm
        // whether the pipeline ever even hands a URL to the loader.
        const diag = { nodesIn: nodes.length, withCandidates: 0, candidatesTotal: 0,
                       loaderHits: 0, loaderFails: 0, spawned: 0, dropped: 0 };

        const loader = new THREE.TextureLoader();
        loader.crossOrigin = 'anonymous';

        // Reject URLs that can never produce a usable image — placeholder
        // hrefs (``#``, ``javascript:``, ``about:``), tiny tracking-pixel
        // data URIs (1×1 transparent gif), and obviously-non-image
        // protocols. Avoids polluting the failure-log with cases that
        // weren't going to load no matter what.
        const NON_IMAGE_PROTOS = /^(javascript|mailto|tel|about|chrome|file):/i;
        const TINY_PIXEL_RE = /^data:image\/gif;base64,R0lGOD/i;  // 1×1 GIFs all start with this
        const isViableImageUrl = (u) => {
            if (!u || typeof u !== 'string') return false;
            const t = u.trim();
            if (!t || t === '#' || t.startsWith('#')) return false;
            if (NON_IMAGE_PROTOS.test(t)) return false;
            if (TINY_PIXEL_RE.test(t)) return false;
            // 1×1 PNG (commonly used as a transparent placeholder).
            if (/^data:image\/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYA/.test(t)) return false;
            return true;
        };

        const toProxy = (absUrl) => {
            if (!absUrl) return absUrl;
            try {
                const u = new URL(absUrl, window.location.href);
                if (u.protocol === 'data:' || u.protocol === 'blob:') return absUrl;
                if (u.origin === window.location.origin) return absUrl;
                return `/api/image_proxy?url=${encodeURIComponent(u.href)}`;
            } catch (_e) { return absUrl; }
        };

        const noteFailure = (imgUrl, where) => {
            // Group failures by hostname so noisy domains get one
            // consolidated counter instead of multiple per-URL log lines.
            let host;
            try { host = new URL(imgUrl, window.location.href).host || '(local)'; }
            catch (_) { host = '(unparsable)'; }
            const n = (this._imageFailuresByHost.get(host) || 0) + 1;
            this._imageFailuresByHost.set(host, n);
            // Throttled per-host logging: 1, 3, 10, 30, 100 …
            if (n === 1 || n === 3 || n === 10 || n === 30 || (n % 100 === 0)) {
                console.warn(`[ChunkProjector] image-load failures from ${host}: ${n} (latest: ${where} ${imgUrl.slice(0, 100)})`);
            }
        };

        const tokenizeUrl = (u) =>
            u.split(/[/?&#=.:_-]+/).filter(t => t.length > 2 && !/^\d+$/.test(t) &&
                t.toLowerCase() !== 'https' && t.toLowerCase() !== 'com' && t.toLowerCase() !== 'www');

        const extractArea = (u) => {
            try {
                const parsed = new URL(u);
                const w = parseInt(parsed.searchParams.get('w') || parsed.searchParams.get('width') || '0');
                if (w > 0) return w * w;
            } catch (_) { }
            const match = u.match(/(\d+)x(\d+)/i);
            if (match) return parseInt(match[1]) * parseInt(match[2]);
            return 0;
        };

        const buildSprite = (texture, node, idx, finalUrls) => {
            const initData = this.initialNodeData.get(node.id);
            if (!initData) { texture.dispose(); diag.dropped++; return; }
            const isPrimary = idx === 0;
            if (isPrimary && this._imageSprites.has(node.id)) { diag.dropped++; return; }
            diag.spawned++;

            const img = texture.image || {};
            const w = img.width || 1, h = img.height || 1;
            const aspect   = (w > 0 && h > 0) ? w / h : 1;
            const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false });
            const sprite   = new THREE.Sprite(material);
            const baseSize = isPrimary ? 1.0 : 0.55;
            if (aspect >= 1) sprite.scale.set(baseSize * aspect, baseSize, 1);
            else             sprite.scale.set(baseSize, baseSize / aspect, 1);
            sprite.position.copy(initData.position);

            let offsetX = 0, offsetY = 0;
            if (!isPrimary) {
                const extraCount = Math.max(1, finalUrls.length - 1);
                const theta  = ((idx - 1) / extraCount) * Math.PI * 2;
                const radius = 1.1 + Math.min(extraCount, 8) * 0.05;
                offsetX = Math.cos(theta) * radius;
                offsetY = Math.sin(theta) * radius;
                sprite.position.x += offsetX;
                sprite.position.y += offsetY;
            }
            sprite.userData = { id: node.id, baseScaleX: sprite.scale.x, baseScaleY: sprite.scale.y, isExtraImage: !isPrimary, offsetX, offsetY };

            if (isPrimary) {
                this._setInstanceVisible(node.id, false);
                this._imageSprites.set(node.id, sprite);
                if (this.searchResults && this.searchResults.has(node.id))
                    this.applySearchGlow(node.id, this.searchResults.get(node.id));
            } else {
                let arr = this._extraSprites.get(node.id);
                if (!arr) { arr = []; this._extraSprites.set(node.id, arr); }
                arr.push(sprite);
            }

            const ws = this.workspaces.find(w => w.id === this.activeWorkspaceId);
            if (ws) {
                const visibleSet = new Set(ws.urls.filter(u => !(ws.hiddenUrls || []).includes(u)));
                const data = this.dataMap.get(node.id);
                if (!data || !visibleSet.has(data.url)) sprite.visible = false;
            }
            this.scene.add(sprite);
        };

        nodes.forEach(node => {
            if (this._imageSprites.has(node.id) || node.is_document) return;
            // URL resolution rule: only resolve relative srcs against
            // the chunk's OWN URL. Falling back to window.location.href
            // here (the projector at localhost:8080) silently rewrote
            // every relative path like `/services/img/<id>` to
            // `http://localhost:8080/services/img/<id>`, which then
            // 502'd in the image_proxy. If the chunk has no url at all,
            // we only accept already-absolute candidates.
            const pageUrl = node.url || '';
            const isAbsolute = (u) => /^https?:\/\//i.test(u || '') || /^data:/i.test(u || '');
            const resolve = (u) => {
                if (!isViableImageUrl(u)) return null;
                try {
                    if (pageUrl) return new URL(u, pageUrl).href;
                    if (isAbsolute(u)) return new URL(u).href;
                    return null;  // relative + no base ⇒ unresolvable, drop
                } catch (e) { return null; }
            };
            const seen    = new Set();
            const urls    = [];
            const pushUnique = (u) => { const r = resolve(u); if (!r || seen.has(r)) return; seen.add(r); urls.push(r); };
            // 1) Primary single-URL field (legacy path).
            pushUnique(node.image_url);
            // 2) Plural array forwarded by the streaming pipeline — one
            //    entry per @src / @data-src / @data-image / @poster /
            //    @srcset URL discovered in content_fields_full. Each
            //    becomes a candidate sprite; sprite_manager downstream
            //    de-duplicates via Jaccard on tokenised path segments,
            //    promotes the largest to primary, and orbits the rest
            //    around it via _extraSprites.
            if (Array.isArray(node.image_urls)) {
                for (const u of node.image_urls) pushUnique(u);
            }
            // 2b) Last-resort sweep over content_fields_full directly —
            //     in case the producer (scanner.js) missed an image-attr
            //     key we didn't anticipate. The keys we know about are
            //     ``…/@src``, ``…/@srcset``, ``…/@data-src``,
            //     ``…/@data-original``, ``…/@data-image``, ``…/@poster``.
            //     Anything else with a value that LOOKS like an image
            //     URL (extension match) gets a shot too. The proxy
            //     downstream rejects non-image content-types so a stray
            //     /@href to an HTML page won't pollute the scene.
            const cff = node.content_fields_full || node.fields;
            if (cff && typeof cff === 'object') {
                const IMG_EXT_RE = /\.(?:png|jpe?g|gif|webp|svg|avif|bmp|ico)(?:\?|#|$)/i;
                for (const k in cff) {
                    const v = cff[k];
                    if (typeof v !== 'string' || !v) continue;
                    if (/\/@(src|srcset|data-src|data-image|data-original|poster)$/i.test(k)) {
                        // srcset values are comma-lists — take the first
                        // candidate so the loader gets a single URL.
                        const cand = /\/@srcset$/i.test(k)
                            ? (v.split(',')[0] || '').trim().split(/\s+/)[0]
                            : v;
                        if (cand) pushUnique(cand);
                    } else if (IMG_EXT_RE.test(v)) {
                        pushUnique(v);
                    }
                }
            }
            // 3) Extract from inlined HTML if available (post-detail-fetch).
            if (node.html_raw) {
                for (const m of this.extractMediaFromHtml(node.html_raw, pageUrl))
                    if (m.type === 'image') pushUnique(m.src);
            }
            if (urls.length === 0) return;
            diag.withCandidates++;
            diag.candidatesTotal += urls.length;

            // De-duplicate similar URLs (Jaccard on tokenized path segments).
            const groups = [];
            for (const url of urls) {
                const tokens = tokenizeUrl(url);
                const area   = extractArea(url);
                let foundGroup = false;
                for (const g of groups) {
                    const setA = new Set(tokens), setB = new Set(g.tokens);
                    let intersection = 0;
                    for (const t of setA) if (setB.has(t)) intersection++;
                    const union = setA.size + setB.size - intersection;
                    if (union && (intersection / union) >= 0.75) {
                        foundGroup = true;
                        if (area > g.area) { g.url = url; g.area = area; }
                        break;
                    }
                }
                if (!foundGroup) groups.push({ url, tokens, area });
            }
            const finalUrls = groups.map(g => g.url);

            // Memory-resident texture cache: key = absolute image URL.
            // Multiple chunks pointing at the same image (common on
            // search-result pages) now share a single Texture instead
            // of issuing one HTTP request per node. Survives across
            // scans within a session; the IndexedDB layer below
            // extends it across page reloads.
            const memCache = this._imageTextureCache;

            finalUrls.forEach((imgUrl, idx) => {
                // Build the success-path closure INSIDE the forEach so
                // it captures the right `imgUrl` for this iteration.
                // (Previously this helper was hoisted above the loop
                //  and referenced `imgUrl` from an outer scope that
                //  didn't exist — every successful texture load threw
                //  "ReferenceError: imgUrl is not defined" the moment
                //  the loader callback fired.)
                const onTextureReady = (texture) => {
                    memCache.set(imgUrl, texture);
                    diag.loaderHits++;
                    buildSprite(texture, node, idx, finalUrls);
                };

                // 1. In-memory cache hit — synchronous build.
                const cached = memCache.get(imgUrl);
                if (cached) {
                    diag.loaderHits++;
                    buildSprite(cached, node, idx, finalUrls);
                    return;
                }
                // 2. IndexedDB cache hit (async, cross-session).
                // 3. Single-fetch network path: `fetch()` the bytes
                //    once, build the texture from a blob-URL, AND
                //    save the same blob to IndexedDB in one pass. The
                //    previous code did `loader.load()` + a separate
                //    `fetch()` inside `_idbSaveTexture`, which made
                //    every cache-miss image download twice — the
                //    "images keep having to reload" the user reported.
                this._loadAndCacheImage(imgUrl)
                    .then(tex => {
                        if (tex) onTextureReady(tex);
                        else diag.loaderFails++;
                    })
                    .catch(() => { diag.loaderFails++; });
            });
        });

        // Synchronous summary at the end of the dispatch loop. Loader
        // hits/fails will trickle in asynchronously after this prints —
        // the snapshot below is "candidates and dispatches" not "final
        // outcomes", but seeing `candidatesTotal=0` immediately tells
        // the user the extraction itself never found a URL (the most
        // common failure mode this season). We rely on `setTimeout`'s
        // 0-delay micro-yield only when there were actual candidates,
        // so the print order in the console stays readable.
        if (diag.nodesIn > 0) {
            const summary = `[sprites] nodesIn=${diag.nodesIn} withCandidates=${diag.withCandidates} `
                + `candidatesTotal=${diag.candidatesTotal} → dispatched ${diag.candidatesTotal} loads`;
            if (diag.candidatesTotal === 0 && diag.nodesIn > 0) {
                console.warn(summary + '  (no image URLs extracted — chunk fields probably had no @src/@srcset/@data-* keys)');
            } else {
                console.debug(summary);
                // Late-print final outcomes once the loader callbacks settle.
                setTimeout(() => {
                    console.debug(`[sprites] outcome  hits=${diag.loaderHits} fails=${diag.loaderFails} spawned=${diag.spawned} dropped=${diag.dropped}`);
                }, 4000);
            }
        }
    },

    // ── IndexedDB texture persistence ───────────────────────────────────
    //
    // Cross-session image cache. Keyed on the absolute image URL,
    // stores the raw image Blob so a subsequent session avoids the
    // network round-trip entirely. We deliberately use a Blob (not a
    // serialised data URL) because:
    //   • Blobs round-trip through IDB as binary, no base64 overhead.
    //   • createObjectURL(blob) gives us a synthetic same-origin URL
    //     that THREE.TextureLoader can consume just like any other.
    //   • Storage cost = raw image bytes; data URLs would be 33% larger.

    _idbOpen() {
        if (this._idbPromise) return this._idbPromise;
        this._idbPromise = new Promise((resolve) => {
            try {
                const req = indexedDB.open('wfh_texture_cache', 1);
                req.onupgradeneeded = (ev) => {
                    const db = ev.target.result;
                    if (!db.objectStoreNames.contains('textures')) {
                        db.createObjectStore('textures', { keyPath: 'url' });
                    }
                };
                req.onsuccess = (ev) => resolve(ev.target.result);
                req.onerror  = ()    => resolve(null);
                req.onblocked = ()   => resolve(null);
            } catch (_) { resolve(null); }
        });
        return this._idbPromise;
    },

    async _idbLoadTexture(url) {
        const db = await this._idbOpen();
        if (!db) return null;
        return new Promise((resolve) => {
            try {
                const tx = db.transaction('textures', 'readonly');
                const store = tx.objectStore('textures');
                const r = store.get(url);
                r.onsuccess = () => {
                    const rec = r.result;
                    if (!rec || !rec.blob) { resolve(null); return; }
                    // Convert blob → object URL → THREE.Texture.
                    const objUrl = URL.createObjectURL(rec.blob);
                    const loader = new THREE.TextureLoader();
                    loader.load(objUrl, (tex) => {
                        // Free the object URL — the texture keeps the
                        // image data internally so we can revoke now.
                        try { URL.revokeObjectURL(objUrl); } catch (_) {}
                        resolve(tex);
                    }, undefined, () => {
                        try { URL.revokeObjectURL(objUrl); } catch (_) {}
                        resolve(null);
                    });
                };
                r.onerror = () => resolve(null);
            } catch (_) { resolve(null); }
        });
    },

    /**
     * Save the bytes at `fetchUrl` to IDB keyed by the canonical
     * image URL (`originalUrl`). Best-effort — failures are silent.
     * We do a fresh `fetch()` even though THREE.TextureLoader already
     * downloaded the same bytes; this is the simplest cross-browser
     * way to obtain the original Blob (the loader keeps only the
     * decoded ImageBitmap, not the source bytes). The fetch lands in
     * the browser HTTP cache so it's effectively free.
     */
    /** Save a raw blob keyed by absolute URL. No double-fetch — caller already has the bytes. */
    async _idbSaveBlob(originalUrl, blob) {
        try {
            if (!blob || blob.size < 32) return;
            const db = await this._idbOpen();
            if (!db) return;
            const tx = db.transaction('textures', 'readwrite');
            tx.objectStore('textures').put({
                url: originalUrl,
                blob,
                ts: Date.now(),
            });
        } catch (_) { /* IDB is best-effort */ }
    },

    /**
     * Single-fetch image loader.
     *
     *   1. Hit IDB by absolute URL → if a blob is cached, build the
     *      texture from a blob-URL and skip the network.
     *   2. Otherwise `fetch()` the proxy URL once, get the bytes, save
     *      them to IDB, build the texture from the same blob-URL.
     *   3. On proxy failure, retry direct (some CDNs serve native
     *      CORS), then give up.
     *
     * Replaces the previous `loader.load(...) + _idbSaveTexture(fetch
     * again)` chain that was double-fetching every cache-miss image.
     */
    async _loadAndCacheImage(originalUrl) {
        // 1. IDB hit.
        const cachedTex = await this._idbLoadTexture(originalUrl).catch(() => null);
        if (cachedTex) return cachedTex;

        const toProxy = (absUrl) => {
            try {
                const u = new URL(absUrl, window.location.href);
                if (u.protocol === 'data:' || u.protocol === 'blob:') return absUrl;
                if (u.origin === window.location.origin) return absUrl;
                return `/api/image_proxy?url=${encodeURIComponent(u.href)}`;
            } catch (_) { return absUrl; }
        };

        const buildFromBlob = (blob) => new Promise((resolve, reject) => {
            const objUrl = URL.createObjectURL(blob);
            const loader = new THREE.TextureLoader();
            loader.load(objUrl, (tex) => {
                try { URL.revokeObjectURL(objUrl); } catch (_) {}
                resolve(tex);
            }, undefined, (err) => {
                try { URL.revokeObjectURL(objUrl); } catch (_) {}
                reject(err);
            });
        });

        const tryFetch = async (url) => {
            const resp = await fetch(url);
            if (!resp.ok) throw new Error('http ' + resp.status);
            // Skip caching the transparent-1×1 proxy fallback so we
            // don't lock in a permanent failure as a "success".
            const note = resp.headers.get('X-Image-Proxy-Note');
            const blob = await resp.blob();
            const tex  = await buildFromBlob(blob);
            if (!note) this._idbSaveBlob(originalUrl, blob);  // fire-and-forget IDB save
            return tex;
        };

        // 2. Proxy fetch.
        try {
            return await tryFetch(toProxy(originalUrl));
        } catch (_proxyErr) {
            // 3. Direct retry (different host on bypass; if proxy URL
            //    equals direct URL the toProxy() identity short-
            //    circuits and the retry is harmless).
            try { return await tryFetch(originalUrl); }
            catch (_directErr) { return null; }
        }
    },

    async _lazyLoadAllNodeDetails(nodes) {
        const batchSize = 100;
        for (let i = 0; i < nodes.length; i += batchSize) {
            const batch   = nodes.slice(i, i + batchSize);
            const toFetch = batch
                .filter(n => !n.is_document && (!this.dataMap.has(n.id) || this.dataMap.get(n.id).html_raw === undefined))
                .map(n => n.id);
            if (toFetch.length > 0) {
                try {
                    const res = await fetch('/api/chunk_details_batch', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(toFetch),
                    });
                    if (res.ok && res.body) {
                        const reader  = res.body.getReader();
                        const decoder = new TextDecoder();
                        let buffer = '';
                        while (true) {
                            const { done, value } = await reader.read();
                            if (done) {
                                if (buffer.trim()) {
                                    try {
                                        const details = JSON.parse(buffer);
                                        const cached  = this.dataMap.get(details.id) || {};
                                        this.dataMap.set(details.id, { ...cached, ...details });
                                        if (this.dataMap.get(details.id)) this._spawnImageBillboards([this.dataMap.get(details.id)]);
                                    } catch (e) { console.warn('Failed to parse trailing NDJSON', e); }
                                }
                                break;
                            }
                            buffer += decoder.decode(value, { stream: true });
                            const lines = buffer.split('\n');
                            buffer = lines.pop();
                            for (const line of lines) {
                                if (!line.trim()) continue;
                                try {
                                    const details = JSON.parse(line);
                                    const cached  = this.dataMap.get(details.id) || {};
                                    this.dataMap.set(details.id, { ...cached, ...details });
                                    if (this.dataMap.get(details.id)) this._spawnImageBillboards([this.dataMap.get(details.id)]);
                                } catch (e) { console.warn('Failed to parse NDJSON line', e); }
                            }
                        }
                    }
                } catch (e) { console.error('[ChunkProjector] Batch fetch failed', e); }
            }
            await new Promise(r => setTimeout(r, 10));
        }
    },
};
