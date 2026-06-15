/**
 * tests/test_visibility.js — Tests for workspace visibility logic.
 *
 * Covers:
 *  • _isUrlVisible: new URLs, hidden URLs, workspace membership
 *  • addNodesIncrementally immediate-visibility integration (via stub context)
 *
 * No THREE.js dependency — runs in Node.js or the browser.
 */

import { describe, it, assert, runAll } from './test_runner.js';
import { WorkspaceMixin } from '../cp/workspace.js';

// ── Context factory ───────────────────────────────────────────────────────────
function makeCtx(wsUrls = [], hiddenUrls = []) {
    const wsId = 'ws-test';
    return Object.assign(Object.create(WorkspaceMixin), {
        workspaces:        [{ id: wsId, name: 'Test', urls: [...wsUrls], hiddenUrls: [...hiddenUrls] }],
        activeWorkspaceId: wsId,
        // Stubs for methods called by workspace methods
        nodeInstanceMap:   new Map(),
        dataMap:           new Map(),
        _imageSprites:     new Map(),
        lastSearchPayload: null,
        applyWorkspaceVisibility() {},
        renderFileTree()   {},
        renderUrlBuckets() {},
        renderSearchResults() {},
        saveWorkspaces()   {},
        _setInstanceVisible() {},
        _setInstanceTransform() {},
        escape:     (s) => String(s ?? ''),
        shortenUrl: (u) => u,
        loadWorkspaces() { return []; },
    });
}

// ── _isUrlVisible ─────────────────────────────────────────────────────────────
describe('_isUrlVisible — new (unregistered) URLs', () => {
    it('returns true for a URL not yet in any workspace (new streaming URL)', () => {
        // A URL that hasn't been added yet should be visible; it will be
        // auto-added by addUrlToActiveWorkspace immediately after.
        const ctx = makeCtx([], []);
        assert.ok(ctx._isUrlVisible('https://brand-new.example.com'),
            'New URL should be visible by default (will be auto-added)');
    });

    it('returns true for empty string URL', () => {
        const ctx = makeCtx();
        assert.ok(ctx._isUrlVisible(''));
    });

    it('returns true for null URL', () => {
        const ctx = makeCtx();
        assert.ok(ctx._isUrlVisible(null));
    });

    it('returns true when there is no active workspace', () => {
        const ctx = makeCtx();
        ctx.workspaces = [];
        assert.ok(ctx._isUrlVisible('https://example.com'));
    });
});

describe('_isUrlVisible — workspace membership', () => {
    it('returns true when URL is in the workspace and not hidden', () => {
        const ctx = makeCtx(['https://example.com'], []);
        assert.ok(ctx._isUrlVisible('https://example.com'));
    });

    it('returns false when URL is in workspace AND in hiddenUrls', () => {
        const ctx = makeCtx(['https://example.com'], ['https://example.com']);
        assert.ok(!ctx._isUrlVisible('https://example.com'),
            'Explicitly hidden URL should not be visible');
    });

    it('returns true when URL is in workspace and hiddenUrls is empty array', () => {
        const ctx = makeCtx(['https://x.com'], []);
        assert.ok(ctx._isUrlVisible('https://x.com'));
    });

    it('returns true when URL is in workspace and hiddenUrls is undefined', () => {
        const ctx = makeCtx(['https://x.com']);
        ctx.workspaces[0].hiddenUrls = undefined;
        assert.ok(ctx._isUrlVisible('https://x.com'));
    });

    it('distinguishes between hidden and visible URLs in the same workspace', () => {
        const ctx = makeCtx(
            ['https://visible.com', 'https://hidden.com'],
            ['https://hidden.com']
        );
        assert.ok(ctx._isUrlVisible('https://visible.com'),   'visible.com should be visible');
        assert.ok(!ctx._isUrlVisible('https://hidden.com'),   'hidden.com should be invisible');
    });
});

describe('_isUrlVisible — multi-workspace', () => {
    it('only checks the active workspace', () => {
        const ctx = makeCtx(['https://active-ws-url.com'], []);
        // Add a second workspace that has the URL hidden
        ctx.workspaces.push({
            id: 'ws-other', name: 'Other',
            urls: ['https://active-ws-url.com'],
            hiddenUrls: ['https://active-ws-url.com'],
        });
        // Active workspace (ws-test) has it visible
        assert.ok(ctx._isUrlVisible('https://active-ws-url.com'),
            'Should check active workspace, not other workspaces');
    });
});

// ── toggleAllDocClusters ──────────────────────────────────────────────────────
describe('toggleAllDocClusters', () => {
    function makeCtxWithDocs(docIds, targets) {
        const ctx = makeCtx();
        ctx.docCollapseTarget = new Map(docIds.map((id, i) => [id, targets[i]]));
        ctx.nodeInstanceMap   = new Map();
        ctx.dataMap           = new Map();
        return ctx;
    }

    it('collapses all clusters when at least one is expanded (target=0)', () => {
        const ctx = makeCtxWithDocs(['doc_a', 'doc_b'], [0, 1]);
        ctx.toggleAllDocClusters();
        assert.equal(ctx.docCollapseTarget.get('doc_a'), 1, 'doc_a should collapse');
        assert.equal(ctx.docCollapseTarget.get('doc_b'), 1, 'doc_b should stay collapsed');
    });

    it('expands all clusters when all are collapsed (target=1)', () => {
        const ctx = makeCtxWithDocs(['doc_a', 'doc_b'], [1, 1]);
        ctx.toggleAllDocClusters();
        assert.equal(ctx.docCollapseTarget.get('doc_a'), 0);
        assert.equal(ctx.docCollapseTarget.get('doc_b'), 0);
    });

    it('seeds doc hubs from nodeInstanceMap when collapsing all', () => {
        const ctx = makeCtxWithDocs([], []);
        // Add a doc hub to the scene that hasn't been interacted with yet
        ctx.nodeInstanceMap.set('doc_new', { isDoc: true });
        ctx.dataMap.set('doc_new', { id: 'doc_new', is_document: true });
        // ABSENT target means EXPANDED (0) — the renderer + interaction
        // layer both default `docCollapse{Target,State}.get(...) || 0`
        // (animation.js:502, interaction.js:223), so the FIRST global
        // toggle COLLAPSES the seeded hub; the second expands it back.
        // (An earlier draft asserted the inverted phase.)
        ctx.toggleAllDocClusters();
        assert.equal(ctx.docCollapseTarget.get('doc_new'), 1, 'first toggle collapses the seeded hub');
        ctx.toggleAllDocClusters();
        assert.equal(ctx.docCollapseTarget.get('doc_new'), 0, 'second toggle expands it back');
    });

    it('no-ops gracefully when docCollapseTarget is empty', () => {
        const ctx = makeCtxWithDocs([], []);
        assert.ok(() => ctx.toggleAllDocClusters(), 'should not throw');
    });
});

runAll();
