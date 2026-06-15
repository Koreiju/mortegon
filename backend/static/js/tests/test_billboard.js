/**
 * tests/test_billboard.js — Tests for cp/billboard.js pure helpers.
 *
 * _escapeHtml, _renderPanelBody, and _nextPanelZ are pure enough to test
 * without a full ChunkProjector instance.  pinBillboard and friends require
 * DOM, so they are integration-tested via a minimal DOM stub.
 */

import { describe, it, assert, runAll } from './test_runner.js';
import { BillboardMixin } from '../cp/billboard.js';

// Stub instance with the minimum properties BillboardMixin needs.
function makeCtx(overrides = {}) {
    const ctx = Object.assign(Object.create(BillboardMixin), {
        _pinnedPanels:   new Map(),
        _panelHoverCount: 0,
        nodeInstanceMap:  new Map(),
        searchResults:    null,
        selectedId:       null,
        hoveredId:        null,
        camera:           null,
        shortenUrl:       (u) => u,
        getContrastYIQ:   () => '#ffffff',
        renderBillboardMedia: () => {},
        hideBillboardArrow:   () => {},
        restoreNodeVisuals:   () => {},
        ...overrides,
    });
    return ctx;
}

// ── _escapeHtml ──────────────────────────────────────────────────────────────
describe('_escapeHtml', () => {
    const ctx = makeCtx();

    it('escapes &', () => assert.equal(ctx._escapeHtml('a & b'), 'a &amp; b'));
    it('escapes <', () => assert.equal(ctx._escapeHtml('<div>'), '&lt;div&gt;'));
    it('escapes >', () => assert.equal(ctx._escapeHtml('x > y'), 'x &gt; y'));
    it('escapes "', () => assert.equal(ctx._escapeHtml('"quoted"'), '&quot;quoted&quot;'));
    it("escapes '", () => assert.equal(ctx._escapeHtml("it's"), 'it&#39;s'));
    it('handles empty string', () => assert.equal(ctx._escapeHtml(''), ''));
    it('handles null', () => assert.equal(ctx._escapeHtml(null), ''));
    it('handles undefined', () => assert.equal(ctx._escapeHtml(undefined), ''));
    it('does not double-escape', () => {
        const once = ctx._escapeHtml('<b>');
        const twice = ctx._escapeHtml(once);
        assert.notEqual(twice, ctx._escapeHtml('<b>'));
    });
    it('passes through plain text unchanged', () => assert.equal(ctx._escapeHtml('hello'), 'hello'));
});

// ── _renderPanelBody ─────────────────────────────────────────────────────────
describe('_renderPanelBody', () => {
    const ctx = makeCtx();

    it('returns a non-empty HTML string', () => {
        const html = ctx._renderPanelBody({ html_raw: '<p>Hi</p>', rendered_text: 'Hi', url: 'https://x.com' });
        assert.ok(typeof html === 'string' && html.length > 0);
    });

    it('includes the url as a Visit source link', () => {
        const html = ctx._renderPanelBody({ url: 'https://example.com', html_raw: '', rendered_text: '' });
        assert.ok(html.includes('Visit source'));
        assert.ok(html.includes('https://example.com'));
    });

    it('shows (no HTML) when html_raw is empty', () => {
        const html = ctx._renderPanelBody({ html_raw: '', rendered_text: '', url: '' });
        assert.ok(html.includes('(no HTML)'));
    });

    it('shows (no text) when rendered_text is empty', () => {
        const html = ctx._renderPanelBody({ html_raw: 'x', rendered_text: '', url: '' });
        assert.ok(html.includes('(no text)'));
    });

    it('escapes html_raw to prevent XSS', () => {
        const html = ctx._renderPanelBody({ html_raw: '<script>alert(1)</script>', rendered_text: '', url: '' });
        assert.ok(!html.includes('<script>'), 'Unescaped <script> found in panel body');
        assert.ok(html.includes('&lt;script&gt;'));
    });

    it('includes the xpath when present', () => {
        const html = ctx._renderPanelBody({ html_raw: '', rendered_text: '', url: '', absolute_xpath: '/html/body/div[1]' });
        assert.ok(html.includes('/html/body/div[1]'));
    });
});

// ── §8B.5 _extractLinkChips ─────────────────────────────────────────────────
describe('_extractLinkChips', () => {
    const ctx = makeCtx();

    it('returns four empty buckets when data is empty', () => {
        const c = ctx._extractLinkChips({});
        assert.deepEqual(c.internal, []);
        assert.deepEqual(c.external, []);
        assert.deepEqual(c.media, []);
        assert.deepEqual(c.json, []);
    });

    it('classifies hrefs by hostname comparison against data.url', () => {
        const c = ctx._extractLinkChips({
            url: 'https://example.com/page',
            fields: {
                '/a/@href':    ['https://example.com/about'],
                '/a[2]/@href': ['https://other.com/help'],
                '/nav/@data-link': ['/relative'],
            },
        });
        const internalHrefs = c.internal.map(x => x.href);
        const externalHrefs = c.external.map(x => x.href);
        assert.ok(internalHrefs.includes('https://example.com/about'),
            'same-host href should be internal');
        assert.ok(internalHrefs.includes('/relative'),
            'relative href should be internal');
        assert.ok(externalHrefs.includes('https://other.com/help'),
            'different-host href should be external');
    });

    it('extracts media from @src + image_urls and dedupes', () => {
        const c = ctx._extractLinkChips({
            url: 'https://x.com',
            image_urls: { '/img[1]': 'https://x.com/logo.png' },
            fields: {
                '/img/@src': ['https://x.com/logo.png'],   // duplicate
                '/img[2]/@src': ['https://x.com/photo.jpg'],
                '/img/@srcset': ['https://x.com/a.png 1x, https://x.com/b.png 2x'],
            },
        });
        const hrefs = c.media.map(x => x.href);
        // Logo is in both buckets; only one chip survives dedup.
        assert.equal(hrefs.filter(h => h === 'https://x.com/logo.png').length, 1);
        assert.ok(hrefs.includes('https://x.com/photo.jpg'));
        // Both srcset entries get parsed.
        assert.ok(hrefs.includes('https://x.com/a.png'));
        assert.ok(hrefs.includes('https://x.com/b.png'));
    });

    it('detects JSON-shaped data-* attribute values', () => {
        const c = ctx._extractLinkChips({
            url: 'https://x.com',
            fields: {
                '/div/@data-config':  ['{"k":1,"v":true}'],
                '/div/@data-array':   ['[1,2,3]'],
                '/div/@data-not-json': ['just a string'],
            },
        });
        assert.equal(c.json.length, 2,
            `expected 2 JSON chips, got ${c.json.length}`);
        const labels = c.json.map(x => x.label).sort();
        assert.deepEqual(labels, ['@data-array', '@data-config']);
    });

    it('skips null / undefined / empty string values', () => {
        const c = ctx._extractLinkChips({
            url: 'https://x.com',
            fields: {
                '/a/@href': [null, undefined, '', 'https://x.com/ok'],
            },
        });
        assert.equal(c.internal.length, 1);
        assert.equal(c.internal[0].href, 'https://x.com/ok');
    });
});


// ── _renderLinkChips ────────────────────────────────────────────────────────
describe('_renderLinkChips', () => {
    const ctx = makeCtx();

    it('returns empty string when chunk has no extractable links', () => {
        const html = ctx._renderLinkChips({ url: 'https://x.com' });
        assert.equal(html, '');
    });

    it('renders one chip per extracted target', () => {
        const html = ctx._renderLinkChips({
            url: 'https://x.com',
            fields: {
                '/a/@href': ['https://x.com/a'],
                '/b/@href': ['https://other.com/b'],
                '/img/@src': ['https://x.com/img.png'],
                '/div/@data-cfg': ['{"x":1}'],
            },
        });
        // One chip per type — count the data-chip-type attributes.
        const m = html.match(/data-chip-type="(\w+)"/g) || [];
        const types = m.map(s => s.match(/"(\w+)"/)[1]).sort();
        assert.deepEqual(types, ['external', 'internal', 'json', 'media']);
    });
});


// ── _nextPanelZ ─────────────────────────────────────────────────────────────
describe('_nextPanelZ', () => {
    it('returns at least 10011 with no panels', () => {
        const ctx = makeCtx();
        assert.ok(ctx._nextPanelZ() >= 10011, 'z-index below 10011 with empty panels');
    });

    it('returns one more than the current max z-index', () => {
        const ctx = makeCtx();
        const fakePanel = { style: { zIndex: '10050' } };
        ctx._pinnedPanels.set('p1', { panel: fakePanel });
        assert.equal(ctx._nextPanelZ(), 10051);
    });

    it('handles multiple panels correctly', () => {
        const ctx = makeCtx();
        ctx._pinnedPanels.set('p1', { panel: { style: { zIndex: '10020' } } });
        ctx._pinnedPanels.set('p2', { panel: { style: { zIndex: '10035' } } });
        assert.equal(ctx._nextPanelZ(), 10036);
    });
});

// ── unpinPanel ───────────────────────────────────────────────────────────────
describe('unpinPanel', () => {
    it('removes the panel entry from _pinnedPanels', () => {
        const ctx = makeCtx();
        const fakePanel = { style: { zIndex: '10010' }, parentNode: null };
        ctx._pinnedPanels.set('node-1', { panel: fakePanel, hovered: false, engaged: false });
        ctx.unpinPanel('node-1');
        assert.ok(!ctx._pinnedPanels.has('node-1'), 'Panel entry not removed');
    });

    it('releases hover lock when panel was hovered but not engaged', () => {
        const ctx = makeCtx();
        ctx._panelHoverCount = 1;
        const fakePanel = { style: { zIndex: '10010' }, parentNode: null };
        ctx._pinnedPanels.set('node-2', { panel: fakePanel, hovered: true, engaged: false });
        ctx.unpinPanel('node-2');
        assert.equal(ctx._panelHoverCount, 0, 'Hover count not decremented');
    });

    it('is a no-op for unknown id', () => {
        const ctx = makeCtx();
        ctx._panelHoverCount = 0;
        ctx.unpinPanel('nonexistent');
        assert.equal(ctx._panelHoverCount, 0);
    });
});

runAll();
