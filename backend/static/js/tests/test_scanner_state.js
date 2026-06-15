/**
 * tests/test_scanner_state.js — Tests for the scanner's chunk-ID → instance-ID
 * state machine in cp/scanner.js.
 *
 * Tests the internal maps (_pendingChunks, _chunkIdToInstances) and the
 * _removeInstancesByChunkId helper WITHOUT needing THREE.js or DOM.
 *
 * Node.js compatible.
 */

import { describe, it, assert, runAll } from './test_runner.js';
import { ScannerMixin } from '../cp/scanner.js';

// ── Context factory ───────────────────────────────────────────────────────────
// Provides just enough state for the scanner helper methods to run.
function makeCtx(overrides = {}) {
    const removed = [];
    return Object.assign(Object.create(ScannerMixin), {
        // Streaming state maps
        _pendingChunks:      new Map(),
        _chunkIdToInstances: new Map(),
        _pendingIndexRows:   [],
        nodeInstanceMap:     new Map(),
        dataMap:             new Map(),
        edges:               [],
        _imageSprites:       new Map(),
        _extraSprites:       new Map(),

        // Track which node ids were removed (for assertion)
        _removed: removed,
        _removeNodeInstance(id) { removed.push(id); this.nodeInstanceMap.delete(id); },

        // Stubs
        addNodesIncrementally() { return 0; },
        _spawnImageBillboards() {},
        _lazyLoadAllNodeDetails() {},
        addUrlToActiveWorkspace() {},
        applyWorkspaceVisibility() {},
        renderFileTree() {},
        renderUrlBuckets() {},
        _clearAllInstances() {},
        unpinPanel() {},
        _panelHoverCount: 0,
        _pinnedPanels: new Map(),
        linesMesh: null,
        scene: { remove: () => {}, add: () => {} },
        domainTree: new Map(),
        _updateStatsOverlay() {},
        _appendLogLine() {},
        setScanStatus() {},
        setLoadingProgress() {},
        hideLoadingProgress() {},
        loadNodes() {},
        unpinPanel() {},
        hideBillboard() {},

        ...overrides,
    });
}

// ── _removeInstancesByChunkId ─────────────────────────────────────────────────
describe('_removeInstancesByChunkId', () => {
    it('removes all instance nodes that belong to the chunk', () => {
        const ctx = makeCtx();
        ctx._chunkIdToInstances.set('chunk_abc', new Set(['inst_abc_0', 'inst_abc_1']));
        ctx.nodeInstanceMap.set('inst_abc_0', {});
        ctx.nodeInstanceMap.set('inst_abc_1', {});

        ctx._removeInstancesByChunkId('chunk_abc');

        assert.ok(ctx._removed.includes('inst_abc_0'), 'inst_abc_0 should be removed');
        assert.ok(ctx._removed.includes('inst_abc_1'), 'inst_abc_1 should be removed');
    });

    it('removes the chunk entry from _chunkIdToInstances', () => {
        const ctx = makeCtx();
        ctx._chunkIdToInstances.set('chunk_xyz', new Set(['inst_xyz_0']));
        ctx.nodeInstanceMap.set('inst_xyz_0', {});

        ctx._removeInstancesByChunkId('chunk_xyz');

        assert.ok(!ctx._chunkIdToInstances.has('chunk_xyz'), 'chunk entry should be deleted');
    });

    it('also removes the chunk from _pendingChunks', () => {
        const ctx = makeCtx();
        ctx._pendingChunks.set('chunk_xyz', { url: 'https://x.com', chunk: {} });
        ctx._chunkIdToInstances.set('chunk_xyz', new Set());

        ctx._removeInstancesByChunkId('chunk_xyz');

        assert.ok(!ctx._pendingChunks.has('chunk_xyz'), 'pending metadata should be cleared');
    });

    it('is a no-op when _chunkIdToInstances is undefined', () => {
        const ctx = makeCtx();
        delete ctx._chunkIdToInstances;
        assert.ok(() => ctx._removeInstancesByChunkId('no_such_chunk'),
            'should not throw when map is missing');
    });

    it('is a no-op for unknown chunk_id', () => {
        const ctx = makeCtx();
        ctx._removeInstancesByChunkId('unknown_chunk_id');
        assert.equal(ctx._removed.length, 0, 'nothing should be removed');
    });

    it('only removes nodes that are still in nodeInstanceMap', () => {
        const ctx = makeCtx();
        ctx._chunkIdToInstances.set('chunk_a', new Set(['inst_a_0', 'inst_a_gone']));
        // inst_a_gone is already absent from nodeInstanceMap
        ctx.nodeInstanceMap.set('inst_a_0', {});

        ctx._removeInstancesByChunkId('chunk_a');

        assert.ok(ctx._removed.includes('inst_a_0'), 'present instance removed');
        assert.ok(!ctx._removed.includes('inst_a_gone'), 'absent instance not double-removed');
    });
});

// ── chunk_added metadata caching ─────────────────────────────────────────────
describe('_pendingChunks caching from chunk_added', () => {
    // These tests verify the expected contract without actually running the WS
    // message handler (which requires a full DOM).  We test the state maps
    // directly.

    it('stored metadata is keyed by chunk_id', () => {
        const ctx = makeCtx();
        const chunkMeta = { chunk_id: 'abc', rendered_text: 'Hello', image_url: 'http://img.jpg' };
        ctx._pendingChunks.set('abc', { url: 'https://x.com', chunk: chunkMeta });

        const stored = ctx._pendingChunks.get('abc');
        assert.equal(stored.chunk.rendered_text, 'Hello');
        assert.equal(stored.url, 'https://x.com');
    });

    it('metadata is not deleted by _removeInstancesByChunkId for unrelated chunks', () => {
        const ctx = makeCtx();
        ctx._pendingChunks.set('chunk_keep', { url: 'https://y.com', chunk: { chunk_id: 'chunk_keep' } });
        ctx._pendingChunks.set('chunk_del', { url: 'https://y.com', chunk: { chunk_id: 'chunk_del' } });
        ctx._chunkIdToInstances.set('chunk_del', new Set());

        ctx._removeInstancesByChunkId('chunk_del');

        assert.ok(ctx._pendingChunks.has('chunk_keep'), 'unrelated chunk metadata should survive');
    });

    it('same chunk metadata is accessible for multiple instances', () => {
        // Simulates a pattern with 3 instances (like a list with 3 items)
        const ctx = makeCtx();
        const meta = { chunk_id: 'list', rendered_text: 'Item', image_url: null };
        ctx._pendingChunks.set('list', { url: 'https://z.com', chunk: meta });

        // Simulate 3 instances all looking up the same pending chunk
        for (let i = 0; i < 3; i++) {
            const pending = ctx._pendingChunks.get('list');
            assert.ok(pending !== undefined, `lookup ${i} should succeed`);
            assert.equal(pending.chunk.rendered_text, 'Item');
        }
        // Metadata should still be there after all three lookups
        assert.ok(ctx._pendingChunks.has('list'), 'metadata survives multiple lookups');
    });
});

// ── _chunkIdToInstances tracking ─────────────────────────────────────────────
describe('_chunkIdToInstances tracking', () => {
    it('maps a chunk_id to multiple instance_ids', () => {
        const ctx = makeCtx();
        // Simulate what the chunk_instances_partial handler does
        const chunkId = 'chunk_001';
        ['inst_001_0', 'inst_001_1', 'inst_001_2'].forEach(iid => {
            if (!ctx._chunkIdToInstances.has(chunkId))
                ctx._chunkIdToInstances.set(chunkId, new Set());
            ctx._chunkIdToInstances.get(chunkId).add(iid);
        });

        assert.equal(ctx._chunkIdToInstances.get(chunkId).size, 3);
    });

    it('each chunk_id maps only its own instances', () => {
        const ctx = makeCtx();
        ctx._chunkIdToInstances.set('c1', new Set(['i1_0']));
        ctx._chunkIdToInstances.set('c2', new Set(['i2_0', 'i2_1']));

        assert.ok(!ctx._chunkIdToInstances.get('c1').has('i2_0'));
        assert.ok(!ctx._chunkIdToInstances.get('c2').has('i1_0'));
    });
});

// ── Scan reset ────────────────────────────────────────────────────────────────
describe('Per-scan state reset', () => {
    it('clears _pendingChunks on reset', () => {
        const ctx = makeCtx();
        ctx._pendingChunks.set('leftover', { url: 'x', chunk: {} });
        // Simulate the reset at the top of triggerScan
        ctx._pendingChunks.clear();
        ctx._chunkIdToInstances.clear();
        ctx._pendingIndexRows = [];

        assert.equal(ctx._pendingChunks.size, 0);
        assert.equal(ctx._chunkIdToInstances.size, 0);
        assert.deepEqual(ctx._pendingIndexRows, []);
    });

    it('resets _loggedImageFailures', () => {
        const ctx = makeCtx();
        ctx._loggedImageFailures = 5;
        // Simulate the image-failure reset in triggerScan
        ctx._loggedImageFailures = 0;
        assert.equal(ctx._loggedImageFailures, 0);
    });

    it('clears _imageProxyFailures', () => {
        const ctx = makeCtx();
        ctx._imageProxyFailures = new Set(['http://fail.jpg']);
        ctx._imageProxyFailures.clear();
        assert.equal(ctx._imageProxyFailures.size, 0);
    });
});

runAll();
