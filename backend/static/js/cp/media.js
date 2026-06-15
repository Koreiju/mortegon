/**
 * cp/media.js — HTML media extraction, URL classification, and billboard
 * media-strip rendering.
 *
 * `IMAGE_EXTS`, `VIDEO_EXTS`, `AUDIO_EXTS` are exported so the main class
 * can re-expose them as static properties for backwards-compat.
 *
 * Methods become ChunkProjector instance methods via prototype mixin.
 */

export const IMAGE_EXTS = new Set([
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.avif',
    '.bmp', '.tiff', '.tif', '.apng', '.jfif', '.pjpeg', '.pjp',
]);
export const VIDEO_EXTS = new Set([
    '.mp4', '.webm', '.ogg', '.ogv', '.mov', '.avi', '.mkv', '.flv',
    '.wmv', '.m4v', '.3gp', '.ts', '.m3u8',
]);
export const AUDIO_EXTS = new Set([
    '.mp3', '.wav', '.flac', '.ogg', '.oga', '.aac', '.wma', '.opus',
    '.m4a', '.mid', '.midi',
]);

export const MediaMixin = {

    /**
     * Walk `htmlRaw` for media and return a de-duped list of absolute URLs
     * classified by type (max 8). Mirrors content_tagger.py heuristics.
     */
    extractMediaFromHtml(htmlRaw, pageUrl) {
        if (!htmlRaw) return [];
        const out  = [];
        const seen = new Set();
        const classifyMedia = (url) => this._classifyMediaUrl(url);
        const push = (type, src, alt) => {
            if (!src) return;
            let resolved = src;
            try { resolved = new URL(src, pageUrl || window.location.href).href; }
            catch (e) { return; }
            if (seen.has(resolved)) return;
            seen.add(resolved);
            out.push({ type, src: resolved, alt: alt || '' });
        };

        let doc;
        try {
            doc = new DOMParser().parseFromString(
                `<!DOCTYPE html><html><body>${htmlRaw}</body></html>`, 'text/html'
            );
        } catch (e) { return []; }

        const URL_ATTRS = [
            'href', 'src', 'data-src', 'data-lazy-src',
            'action', 'formaction', 'poster',
            'data-original', 'data-original-src', 'data-image',
        ];

        const walk = (selector, defaultType, altAttrs) => {
            doc.querySelectorAll(selector).forEach(el => {
                const alt = (altAttrs || []).reduce((acc, a) => acc || el.getAttribute(a) || '', '');
                URL_ATTRS.forEach(a => {
                    const v = el.getAttribute(a);
                    if (!v) return;
                    const low = v.trim().toLowerCase();
                    if (low.startsWith('javascript:') || low.startsWith('mailto:') || low.startsWith('tel:')) return;
                    const mediaType = classifyMedia(v) || defaultType;
                    if (mediaType) push(mediaType, v, alt);
                });
                const ss = el.getAttribute('srcset');
                if (ss) {
                    ss.split(',').forEach(part => {
                        const u = part.trim().split(/\s+/)[0];
                        if (!u) return;
                        const mediaType = classifyMedia(u) || defaultType;
                        if (mediaType) push(mediaType, u, alt);
                    });
                }
            });
        };

        walk('img, picture, svg, canvas', 'image', ['alt', 'title', 'aria-label']);
        walk('video',  'video', ['title', 'aria-label']);
        walk('source', null,    []);
        walk('track',  'video', []);
        walk('audio',  'audio', ['title', 'aria-label']);

        doc.querySelectorAll('source').forEach(s => {
            const parent   = s.parentElement && s.parentElement.tagName.toLowerCase();
            const fallback = parent === 'audio' ? 'audio' : parent === 'video' ? 'video' : 'image';
            URL_ATTRS.forEach(a => {
                const v = s.getAttribute(a);
                if (!v) return;
                push(classifyMedia(v) || fallback, v, '');
            });
        });

        doc.querySelectorAll('video[poster]').forEach(v => {
            push('image', v.getAttribute('poster'), v.getAttribute('title') || 'video poster');
        });

        URL_ATTRS.forEach(attr => {
            doc.querySelectorAll(`[${attr}]`).forEach(el => {
                const v = el.getAttribute(attr);
                if (!v) return;
                const low = v.trim().toLowerCase();
                if (low.startsWith('javascript:') || low.startsWith('mailto:') || low.startsWith('tel:')) return;
                const mediaType = classifyMedia(v);
                if (!mediaType) return;
                const alt = el.getAttribute('alt') || el.getAttribute('title') || el.getAttribute('aria-label') || '';
                push(mediaType, v, alt);
            });
        });

        doc.querySelectorAll('[style]').forEach(el => {
            const style = el.getAttribute('style');
            if (!style || !/url\(/i.test(style)) return;
            const clean = style.replace(/&quot;/g, '"');
            const re    = /url\(\s*['"]?([^'"\)]+)['"]?\s*\)/gi;
            let m;
            while ((m = re.exec(clean)) !== null) {
                const u = (m[1] || '').trim();
                if (!u) continue;
                const mediaType = classifyMedia(u) || 'image';
                push(mediaType, u, el.getAttribute('alt') || el.getAttribute('aria-label') || '');
            }
        });

        return out.slice(0, 8);
    },

    /** Mirror of backend `_classify_media` in content_tagger.py. */
    _classifyMediaUrl(url) {
        if (!url) return null;
        const u = url.trim();
        if (u.startsWith('data:image/')) return 'image';
        if (u.startsWith('data:video/')) return 'video';
        if (u.startsWith('data:audio/')) return 'audio';
        const clean = u.split('?')[0].split('#')[0].toLowerCase();
        const m     = clean.match(/\.([a-z0-9]{2,5})(?:[?#]|$)/);
        if (!m) return null;
        const ext = '.' + m[1];
        // Reference the sets via the class static properties so they stay in sync.
        if (this.constructor.IMAGE_EXTS.has(ext)) return 'image';
        if (this.constructor.VIDEO_EXTS.has(ext)) return 'video';
        if (this.constructor.AUDIO_EXTS.has(ext)) return 'audio';
        return null;
    },

    renderBillboardMedia(data) {
        const section = document.getElementById('billboard-media-section');
        const strip   = document.getElementById('billboard-media');
        if (!section || !strip) return;
        const media = this.extractMediaFromHtml(data.html_raw, data.url);
        if (media.length === 0) { section.style.display = 'none'; strip.innerHTML = ''; return; }
        section.style.display = 'block';
        strip.innerHTML = media.map(m => {
            const safe = this.escape(m.src);
            const alt  = this.escape(m.alt || 'chunk media');
            if (m.type === 'video') {
                return `<a class="billboard-media-cell" href="${safe}" target="_blank" title="${safe}">
                    <video class="billboard-media-video" src="${safe}" muted playsinline preload="metadata"></video>
                    <span class="billboard-media-badge"><i class="fas fa-play"></i></span>
                </a>`;
            }
            return `<a class="billboard-media-cell" href="${safe}" target="_blank" title="${safe}">
                <img class="billboard-media-thumb" src="${safe}" alt="${alt}" loading="lazy"
                     onerror="this.closest('.billboard-media-cell').style.display='none';">
            </a>`;
        }).join('');
    },
};
