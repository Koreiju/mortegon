/**
 * tests/test_media.js — Tests for cp/media.js (browser-only: uses DOMParser).
 *
 * Load via <script type="module"> in a test HTML page, or run under a
 * browser-driver such as Playwright/Puppeteer.
 */

import { describe, it, assert, runAll } from './test_runner.js';
import { IMAGE_EXTS, VIDEO_EXTS, AUDIO_EXTS, MediaMixin } from '../cp/media.js';

// Minimal stub context so we can call MediaMixin methods as `this`.
const ctx = Object.create(MediaMixin);
// Provide stub IMAGE_EXTS etc. via constructor static lookup.
ctx.constructor = {
    IMAGE_EXTS,
    VIDEO_EXTS,
    AUDIO_EXTS,
};
ctx.escape = (s) => String(s ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

// ── Media extension sets ─────────────────────────────────────────────────────
describe('Extension sets', () => {
    it('IMAGE_EXTS contains .png', () => assert.ok(IMAGE_EXTS.has('.png')));
    it('IMAGE_EXTS contains .svg', () => assert.ok(IMAGE_EXTS.has('.svg')));
    it('VIDEO_EXTS contains .mp4', () => assert.ok(VIDEO_EXTS.has('.mp4')));
    it('VIDEO_EXTS contains .webm', () => assert.ok(VIDEO_EXTS.has('.webm')));
    it('AUDIO_EXTS contains .mp3', () => assert.ok(AUDIO_EXTS.has('.mp3')));
    it('AUDIO_EXTS contains .wav', () => assert.ok(AUDIO_EXTS.has('.wav')));
    it('sets are disjoint (.mp4 not in IMAGE_EXTS)', () => assert.ok(!IMAGE_EXTS.has('.mp4')));
});

// ── _classifyMediaUrl ────────────────────────────────────────────────────────
describe('_classifyMediaUrl', () => {
    it('classifies .png as image',  () => assert.equal(ctx._classifyMediaUrl('https://x.com/a.png'), 'image'));
    it('classifies .jpg as image',  () => assert.equal(ctx._classifyMediaUrl('photo.jpg'), 'image'));
    it('classifies .webp as image', () => assert.equal(ctx._classifyMediaUrl('/img.webp'), 'image'));
    it('classifies .mp4 as video',  () => assert.equal(ctx._classifyMediaUrl('vid.mp4'), 'video'));
    it('classifies .webm as video', () => assert.equal(ctx._classifyMediaUrl('clip.webm'), 'video'));
    it('classifies .mp3 as audio',  () => assert.equal(ctx._classifyMediaUrl('song.mp3'), 'audio'));
    it('returns null for unknown ext', () => assert.equal(ctx._classifyMediaUrl('page.html'), null));
    it('returns null for null input', () => assert.equal(ctx._classifyMediaUrl(null), null));
    it('returns null for empty string', () => assert.equal(ctx._classifyMediaUrl(''), null));
    it('handles data:image/ URI', () => assert.equal(ctx._classifyMediaUrl('data:image/png;base64,abc'), 'image'));
    it('handles data:video/ URI', () => assert.equal(ctx._classifyMediaUrl('data:video/mp4;base64,xyz'), 'video'));
    it('handles data:audio/ URI', () => assert.equal(ctx._classifyMediaUrl('data:audio/mp3;base64,xyz'), 'audio'));
    it('ignores query string when classifying ext', () => {
        assert.equal(ctx._classifyMediaUrl('thumb.jpg?w=200&h=200'), 'image');
    });
    it('ignores fragment when classifying ext', () => {
        assert.equal(ctx._classifyMediaUrl('anim.gif#frame1'), 'image');
    });
    it('is case-insensitive', () => {
        assert.equal(ctx._classifyMediaUrl('IMAGE.PNG'), 'image');
    });
});

// ── extractMediaFromHtml ─────────────────────────────────────────────────────
// Platform gate: extraction parses real HTML via DOMParser (the module
// header documents these as browser-only). Under Node the DOM-bearing
// tests register as EXPLICIT labelled skips — silently vacuous passes
// (extraction returning [] making dedup/cap assertions trivially true)
// would be dishonest coverage.
const HAS_DOM_PARSER = typeof DOMParser !== 'undefined';
const itDom = HAS_DOM_PARSER
    ? it
    : ((name, _fn) => it(`${name} [SKIPPED under Node: needs DOMParser — run in browser]`, () => {}));

describe('extractMediaFromHtml', () => {
    const BASE = 'https://example.com';

    it('returns [] for empty input', () => {
        assert.deepEqual(ctx.extractMediaFromHtml('', BASE), []);
    });

    it('returns [] for null input', () => {
        assert.deepEqual(ctx.extractMediaFromHtml(null, BASE), []);
    });

    itDom('extracts an <img> src', () => {
        const media = ctx.extractMediaFromHtml('<img src="/photo.png">', BASE);
        assert.ok(media.length >= 1, 'Expected at least 1 media item');
        assert.equal(media[0].type, 'image');
        assert.ok(media[0].src.endsWith('/photo.png'));
    });

    itDom('resolves relative URLs against pageUrl', () => {
        const media = ctx.extractMediaFromHtml('<img src="thumb.jpg">', BASE);
        assert.ok(media[0].src.startsWith('https://example.com'), `Got: ${media[0].src}`);
    });

    itDom('extracts <video> src', () => {
        const media = ctx.extractMediaFromHtml('<video src="movie.mp4"></video>', BASE);
        const video = media.find(m => m.type === 'video');
        assert.ok(video, 'No video found');
    });

    itDom('extracts <video poster> as image', () => {
        const media = ctx.extractMediaFromHtml('<video poster="cover.jpg" src="film.mp4"></video>', BASE);
        const poster = media.find(m => m.src.endsWith('cover.jpg') && m.type === 'image');
        assert.ok(poster, 'Poster image not found');
    });

    itDom('deduplicates identical URLs', () => {
        const html  = '<img src="/a.png"><img src="/a.png">';
        const media = ctx.extractMediaFromHtml(html, BASE);
        const urls  = media.map(m => m.src);
        const unique = new Set(urls);
        assert.equal(urls.length, unique.size, 'Duplicate URLs not removed');
    });

    itDom('caps output at 8 items', () => {
        const imgs = Array.from({ length: 12 }, (_, i) => `<img src="/img${i}.png">`).join('');
        const media = ctx.extractMediaFromHtml(imgs, BASE);
        assert.ok(media.length <= 8, `Expected ≤8 items, got ${media.length}`);
    });

    itDom('skips javascript: URLs', () => {
        const media = ctx.extractMediaFromHtml('<img src="javascript:void(0)">', BASE);
        assert.equal(media.length, 0, 'javascript: URL should be skipped');
    });

    itDom('extracts data-src attribute', () => {
        const media = ctx.extractMediaFromHtml('<img data-src="/lazy.jpg">', BASE);
        const img   = media.find(m => m.src.endsWith('/lazy.jpg'));
        assert.ok(img, 'data-src image not found');
    });

    itDom('extracts CSS background-image url()', () => {
        const media = ctx.extractMediaFromHtml(
            '<div style="background-image:url(/bg.png)"></div>', BASE
        );
        const bg = media.find(m => m.src.endsWith('/bg.png'));
        assert.ok(bg, 'CSS background-image not found');
    });

    itDom('extracts srcset candidates', () => {
        const media = ctx.extractMediaFromHtml(
            '<img srcset="/sm.jpg 480w, /lg.jpg 1024w">', BASE
        );
        const lg = media.find(m => m.src.endsWith('/lg.jpg'));
        assert.ok(lg, 'srcset candidate not found');
    });

    itDom('preserves alt text from <img>', () => {
        const media = ctx.extractMediaFromHtml('<img src="/p.jpg" alt="A photo">', BASE);
        assert.equal(media[0].alt, 'A photo');
    });
});

runAll();
