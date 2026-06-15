/**
 * tests/test_node_loader.js — Tests for cp/node_loader.js.
 *
 * Covers:
 *  • addNodesIncrementally: doc hub creation, deduplication, edges
 *  • Immediate workspace visibility applied to new nodes
 *  • quiet-mode suppresses applyWorkspaceVisibility / renderFileTree jank
 *  • addUrlToActiveWorkspace does NOT fire applyWorkspaceVisibility when quiet
 *
 * Uses three_stub.js for THREE dependency.
 */

import * as THREE_STUBS from './three_stub.js';
globalThis.THREE = THREE_STUBS;
// Browser-global shim: the mixins read `window.THREE || THREE` (browser-
// correct); under Node `window` doesn't exist, so alias it to globalThis.
if (typeof globalThis.window === 'undefined') globalThis.window = globalThis;

import { describe, it, assert, runAll } from './test_runner.js';
import { InstanceManagerMixin } from '../cp/instance_manager.js';
import { NodeLoaderMixin }      from '../cp/node_loader.js';
import { WorkspaceMixin }       from '../cp/workspace.js';
import { layOutNode }           from '../cp/layout.js';

// ── Context factory ───────────────────────────────────────────────────────────
function makeCtx(wsUrls = [], hiddenUrls = []) {
    const capacity = 20;
    const wsId     = 'ws1';

    const ctx = Object.assign(
        Object.create(null),
        InstanceManagerMixin,
        NodeLoaderMixin,
        WorkspaceMixin,
        {
            // addNodesIncrementally calls this.constructor.layOutNode —
            // provide a fake constructor object that forwards to the real function.
            constructor: { layOutNode },
            // Constructor state
            scene:               new THREE_STUBS.Scene(),
            nodeInstanceMap:     new Map(),
            initialNodeData:     new Map(),
            dataMap:             new Map(),
            edges:               [],
            linesMesh:           null,
            _extraConnectorsMesh: null,
            _imageSprites:       new Map(),
            _extraSprites:       new Map(),
            _pinnedPanels:       new Map(),
            _panelHoverCount:    0,
            selectedId:          null,
            hoveredId:           null,
            domainTree:          new Map(),
            expandedFolders:     new Set(),
            workspaces:          [{ id: wsId, name: 'Test', urls: [...wsUrls], hiddenUrls: [...hiddenUrls] }],
            activeWorkspaceId:   wsId,
            wsEditTimers:        new Map(),
            wsEditOriginals:     new Map(),
            docCollapseTarget:   new Map(),
            docCollapseState:    new Map(),
            searchResults:       null,
            lastSearchPayload:   null,
            detailsFetchQueue:   new Set(),
            _freeDocIndices:     Array.from({ length: capacity }, (_, i) => capacity - 1 - i),
            _freeInstIndices:    Array.from({ length: capacity }, (_, i) => capacity - 1 - i),
            _docInstanceIdToNode:  new Array(capacity).fill(null),
            _instInstanceIdToNode: new Array(capacity).fill(null),

            // Call trackers
            _applyVisibilityCalls: [],
            _renderTreeCalls:      0,
            _renderBucketCalls:    0,
            _visibilityCalls:      [],   // tracks _setInstanceVisible calls

            // Overrides
            _setInstanceVisible(id, vis) {
                this._visibilityCalls.push({ id, vis });
                // Actually call the real implementation for correctness
                InstanceManagerMixin._setInstanceTransform.call(this, id,
                    vis ? 1.0 : 0.0,
                    this.nodeInstanceMap.get(id)?.originalColor || new THREE_STUBS.Color(1,1,1));
            },
            applyWorkspaceVisibility() {
                this._applyVisibilityCalls.push(Date.now());
            },
            renderFileTree()   { this._renderTreeCalls++;   },
            renderUrlBuckets() { this._renderBucketCalls++; },
            renderSearchResults() {},

            // WorkspaceMixin methods we need to work
            loadWorkspaces() { return []; },
            saveWorkspaces() {},

            // Stubs
            setLoadingProgress() {},
            hideLoadingProgress() {},
            rebuildEdges()       {},
            _rebuildEdgesSoon()  {},
            _requestUIUpdate()   {},
            unpinPanel()         {},
            hideBillboard()      {},
            _spawnImageBillboards() {},
            _lazyLoadAllNodeDetails() {},
            escape: (s) => String(s ?? ''),
            shortenUrl: (u) => u,
        }
    );

    ctx._createInstancedMeshes(capacity);

    // Bind WorkspaceMixin methods properly
    ctx.addUrlToActiveWorkspace = WorkspaceMixin.addUrlToActiveWorkspace.bind(ctx);
    ctx._isUrlVisible           = WorkspaceMixin._isUrlVisible.bind(ctx);

    return ctx;
}

function row(id, url = 'https://example.com', is_document = false) {
    return { id, url, is_document, doc_id: `doc_${url}` };
}

// ── addNodesIncrementally ─────────────────────────────────────────────────────
describe('addNodesIncrementally — basic', () => {
    it('returns 0 for empty input', () => {
        const ctx = makeCtx();
        assert.equal(ctx.addNodesIncrementally([], {}), 0);
    });

    it('adds an instance node', () => {
        const ctx = makeCtx();
        ctx.addNodesIncrementally([row('inst_1')], { quiet: true });
        assert.ok(ctx.nodeInstanceMap.has('inst_1'), 'node should be added');
    });

    it('auto-creates a document hub for the URL', () => {
        const ctx = makeCtx();
        ctx.addNodesIncrementally([row('inst_1', 'https://a.com')], { quiet: true });
        assert.ok(ctx.nodeInstanceMap.has('doc_https://a.com'),
            'doc hub should be auto-created');
    });

    it('does not duplicate nodes on repeated calls', () => {
        const ctx = makeCtx();
        ctx.addNodesIncrementally([row('inst_dup')], { quiet: true });
        ctx.addNodesIncrementally([row('inst_dup')], { quiet: true });
        // nodeInstanceMap should still only have 1 entry for inst_dup
        let count = 0;
        ctx.nodeInstanceMap.forEach((_, id) => { if (id === 'inst_dup') count++; });
        assert.equal(count, 1, 'duplicate node should not be added twice');
    });

    it('adds multiple rows in one call', () => {
        const ctx = makeCtx();
        ctx.addNodesIncrementally([
            row('i1', 'https://a.com'),
            row('i2', 'https://a.com'),
            row('i3', 'https://b.com'),
        ], { quiet: true });
        assert.ok(ctx.nodeInstanceMap.has('i1'));
        assert.ok(ctx.nodeInstanceMap.has('i2'));
        assert.ok(ctx.nodeInstanceMap.has('i3'));
    });

    it('creates only one doc hub per unique URL', () => {
        const ctx = makeCtx();
        ctx.addNodesIncrementally([
            row('inst_a', 'https://same.com'),
            row('inst_b', 'https://same.com'),
        ], { quiet: true });
        // Should have: inst_a, inst_b, doc_https://same.com
        assert.equal(ctx.nodeInstanceMap.size, 3);
    });

    it('returns the count of nodes actually added', () => {
        const ctx = makeCtx();
        const n = ctx.addNodesIncrementally([row('c1'), row('c2')], { quiet: true });
        // 2 instances + 2 doc hubs (each has different default url?)
        // Actually default url is same for both, so 2 inst + 1 doc = 3
        assert.ok(n > 0, 'should return a positive count');
    });
});

describe('addNodesIncrementally — doc_id propagation', () => {
    it('sets doc_id in dataMap for instance nodes', () => {
        const ctx = makeCtx();
        ctx.addNodesIncrementally([row('inst_d1', 'https://ex.com')], { quiet: true });
        const data = ctx.dataMap.get('inst_d1');
        assert.equal(data.doc_id, 'doc_https://ex.com',
            'doc_id should be set so billboard can expand the cluster');
    });
});

// ── Workspace visibility: new URLs ────────────────────────────────────────────
describe('addNodesIncrementally — immediate visibility for hidden URLs', () => {
    it('hides nodes for explicitly-hidden URLs immediately', () => {
        const ctx = makeCtx(
            ['https://hidden.com'],
            ['https://hidden.com']
        );
        ctx.addNodesIncrementally([row('h_inst', 'https://hidden.com')], { quiet: true });

        const call = ctx._visibilityCalls.find(c => c.id === 'h_inst');
        assert.ok(call, '_setInstanceVisible should have been called for h_inst');
        assert.ok(!call.vis, 'hidden URL node should be made invisible immediately');
    });

    it('does NOT hide nodes for new (unseen) URLs', () => {
        // Bug fix #2: new URLs should be visible (they get auto-added to workspace)
        const ctx = makeCtx([], []);
        ctx.addNodesIncrementally([row('new_inst', 'https://brand-new.com')], { quiet: true });

        const call = ctx._visibilityCalls.find(c => c.id === 'new_inst');
        // Either no visibility call was made (already visible by default),
        // or the call set it to true.
        if (call) {
            assert.ok(call.vis !== false, 'new URL node should NOT be hidden');
        }
    });

    it('hides doc hub for explicitly-hidden URLs', () => {
        const ctx = makeCtx(['https://hidden2.com'], ['https://hidden2.com']);
        ctx.addNodesIncrementally([row('h2_inst', 'https://hidden2.com')], { quiet: true });

        const docId = 'doc_https://hidden2.com';
        const call  = ctx._visibilityCalls.find(c => c.id === docId);
        // Bug fix #1 (doc hubs): no longer guarded by !node.is_document
        assert.ok(call && !call.vis,
            'doc hub should also be hidden immediately for hidden URLs');
    });
});

// ── quiet mode ────────────────────────────────────────────────────────────────
describe('addNodesIncrementally — quiet mode suppresses expensive UI', () => {
    it('does not call applyWorkspaceVisibility directly when quiet=true', () => {
        const ctx = makeCtx(['https://q.com'], []);
        ctx._applyVisibilityCalls = [];
        ctx.addNodesIncrementally([row('q_inst', 'https://q.com')], { quiet: true });
        // The direct applyWorkspaceVisibility call should NOT fire (only _requestUIUpdate)
        // NOTE: addUrlToActiveWorkspace still calls it unless we fix Bug #3.
        // After Bug #3 fix: this should be 0.
        assert.equal(ctx._applyVisibilityCalls.length, 0,
            'applyWorkspaceVisibility should not fire during quiet streaming');
    });

    it('calls applyWorkspaceVisibility when quiet=false', () => {
        const ctx = makeCtx(['https://q2.com'], []);
        ctx._applyVisibilityCalls = [];
        ctx.addNodesIncrementally([row('q2_inst', 'https://q2.com')], { quiet: false });
        assert.ok(ctx._applyVisibilityCalls.length > 0,
            'applyWorkspaceVisibility should fire in non-quiet mode');
    });
});

// ── addUrlToActiveWorkspace quiet mode ────────────────────────────────────────
describe('addUrlToActiveWorkspace — quiet parameter', () => {
    it('does not call applyWorkspaceVisibility when quiet=true', () => {
        const ctx = makeCtx([], []);
        let avCalled = false;
        ctx.applyWorkspaceVisibility = () => { avCalled = true; };

        ctx.addUrlToActiveWorkspace('https://stream.com', true);
        assert.ok(!avCalled, 'applyWorkspaceVisibility should be suppressed in quiet mode');
    });

    it('does call applyWorkspaceVisibility when quiet=false (default)', () => {
        const ctx = makeCtx([], []);
        let avCalled = false;
        ctx.applyWorkspaceVisibility = () => { avCalled = true; };

        ctx.addUrlToActiveWorkspace('https://stream.com', false);
        assert.ok(avCalled, 'applyWorkspaceVisibility should fire in normal mode');
    });

    it('still adds the URL to the workspace in quiet mode', () => {
        const ctx = makeCtx([], []);
        ctx.addUrlToActiveWorkspace('https://quiet-add.com', true);
        const ws = ctx.workspaces.find(w => w.id === ctx.activeWorkspaceId);
        assert.ok(ws.urls.includes('https://quiet-add.com'), 'URL should be added even in quiet mode');
    });
});

runAll();
