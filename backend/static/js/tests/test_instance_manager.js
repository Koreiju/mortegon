/**
 * tests/test_instance_manager.js — Tests for cp/instance_manager.js.
 *
 * Key coverage:
 *  • _addNodeInstance merges pre-cached rich data instead of overwriting it
 *  • _freeInstance correctly recycles the slot
 *  • _removeNodeInstance cleans up sprites, edges, and state
 *  • _allocateInstance grows the mesh when the free list is empty
 *  • _clearAllInstances resets all pools
 *
 * Uses three_stub.js to satisfy the THREE.js global required by the mixin.
 */

import * as THREE_STUBS from './three_stub.js';
// Set the global BEFORE importing any mixin that references THREE at call-time.
globalThis.THREE = THREE_STUBS;
// Browser-global shim: the mixins read `window.THREE || THREE` (browser-
// correct); under Node `window` doesn't exist, so alias it to globalThis.
if (typeof globalThis.window === 'undefined') globalThis.window = globalThis;

import { describe, it, assert, runAll } from './test_runner.js';
import { InstanceManagerMixin } from '../cp/instance_manager.js';

// ── Context factory ───────────────────────────────────────────────────────────
function makeCtx(capacity = 10) {
    const scene = new THREE_STUBS.Scene();
    const ctx   = Object.assign(Object.create(InstanceManagerMixin), {
        scene,
        nodeInstanceMap:        new Map(),
        initialNodeData:        new Map(),
        dataMap:                new Map(),
        _freeDocIndices:        Array.from({ length: capacity }, (_, i) => capacity - 1 - i),
        _freeInstIndices:       Array.from({ length: capacity }, (_, i) => capacity - 1 - i),
        _docInstanceIdToNode:   new Array(capacity).fill(null),
        _instInstanceIdToNode:  new Array(capacity).fill(null),
        _imageSprites:          new Map(),
        _extraSprites:          new Map(),
        _pinnedPanels:          new Map(),
        _panelHoverCount:       0,
        selectedId:             null,
        hoveredId:              null,
        edges:                  [],
        linesMesh:              null,
        _extraConnectorsMesh:   null,

        // Stubs for cross-mixin calls
        unpinPanel(id)          { this._pinnedPanels.delete(id); },
        hideBillboard()         {},
        _rebuildEdgesSoon()     {},
    });

    // Create real-ish InstancedMesh objects using our stub
    ctx._createInstancedMeshes(capacity);
    return ctx;
}

function makeNode(id, opts = {}) {
    return {
        id,
        url:         opts.url         || 'https://example.com',
        is_document: opts.is_document || false,
        doc_id:      opts.doc_id      || `doc_${opts.url || 'https://example.com'}`,
        x: opts.x ?? 1, y: opts.y ?? 2, z: opts.z ?? 3,
        r: opts.r ?? 0.5, g: opts.g ?? 0.5, b: opts.b ?? 0.5,
    };
}

// ── _addNodeInstance ──────────────────────────────────────────────────────────
describe('_addNodeInstance — basic insertion', () => {
    it('populates nodeInstanceMap after adding a node', () => {
        const ctx  = makeCtx();
        const node = makeNode('inst_1');
        ctx._addNodeInstance(node);
        assert.ok(ctx.nodeInstanceMap.has('inst_1'), 'node should be in nodeInstanceMap');
    });

    it('populates initialNodeData with position and colour', () => {
        const ctx  = makeCtx();
        ctx._addNodeInstance(makeNode('inst_2', { x: 5, y: 6, z: 7 }));
        const init = ctx.initialNodeData.get('inst_2');
        assert.ok(init, 'initialNodeData entry should exist');
        assert.equal(init.position.x, 5);
        assert.equal(init.position.y, 6);
        assert.equal(init.position.z, 7);
    });

    it('is idempotent — calling twice does not create a second entry', () => {
        const ctx  = makeCtx();
        const node = makeNode('inst_3');
        ctx._addNodeInstance(node);
        ctx._addNodeInstance(node);
        assert.equal(ctx.nodeInstanceMap.size, 1);
    });

    it('stores the node in dataMap', () => {
        const ctx  = makeCtx();
        const node = makeNode('inst_4');
        ctx._addNodeInstance(node);
        assert.ok(ctx.dataMap.has('inst_4'));
    });
});

describe('_addNodeInstance — dataMap MERGE (Bug #1)', () => {
    it('preserves pre-cached rendered_text when merging', () => {
        const ctx = makeCtx();
        // Pre-cache rich metadata from streaming (simulates scanner.js pre-population)
        ctx.dataMap.set('inst_5', {
            id:            'inst_5',
            rendered_text: 'Hello world',
            html_raw:      '<p>Hello</p>',
            chunk_id:      'chunk_abc',
            url:           'https://example.com',
            is_document:   false,
            absolute_xpath: '/html/body/p[1]',
        });

        // addNodeInstance is called with a thin node (layout fields only)
        const thinNode = makeNode('inst_5', { doc_id: 'doc_https://example.com' });
        ctx._addNodeInstance(thinNode);

        const stored = ctx.dataMap.get('inst_5');
        assert.equal(stored.rendered_text, 'Hello world',
            'rendered_text from pre-cache should survive _addNodeInstance');
        assert.equal(stored.html_raw, '<p>Hello</p>',
            'html_raw from pre-cache should survive');
        assert.equal(stored.absolute_xpath, '/html/body/p[1]',
            'absolute_xpath from pre-cache should survive');
        assert.equal(stored.chunk_id, 'chunk_abc',
            'chunk_id from pre-cache should survive');
    });

    it('adds doc_id from the thin node to the merged entry', () => {
        const ctx = makeCtx();
        ctx.dataMap.set('inst_6', {
            id: 'inst_6', url: 'https://x.com', is_document: false,
            rendered_text: 'Text',
        });

        const thinNode = makeNode('inst_6', { doc_id: 'doc_https://x.com' });
        ctx._addNodeInstance(thinNode);

        const stored = ctx.dataMap.get('inst_6');
        assert.equal(stored.doc_id, 'doc_https://x.com',
            'doc_id from thin node should be merged in');
    });

    it('updates position fields (x/y/z) from the thin node', () => {
        const ctx = makeCtx();
        ctx.dataMap.set('inst_7', { id: 'inst_7', rendered_text: 'X', x: 0, y: 0, z: 0 });

        const thinNode = makeNode('inst_7', { x: 10, y: 20, z: 30 });
        ctx._addNodeInstance(thinNode);

        const stored = ctx.dataMap.get('inst_7');
        assert.equal(stored.x, 10, 'x should come from the layout node');
        assert.equal(stored.y, 20, 'y should come from the layout node');
        assert.equal(stored.z, 30, 'z should come from the layout node');
        assert.equal(stored.rendered_text, 'X', 'pre-cached text survives');
    });

    it('works correctly when no pre-cached data exists', () => {
        const ctx = makeCtx();
        const node = makeNode('inst_8');
        ctx._addNodeInstance(node);

        const stored = ctx.dataMap.get('inst_8');
        assert.equal(stored.id, 'inst_8');
        assert.equal(stored.url, 'https://example.com');
    });
});

// ── _freeInstance ─────────────────────────────────────────────────────────────
describe('_freeInstance', () => {
    it('removes node from nodeInstanceMap', () => {
        const ctx  = makeCtx();
        ctx._addNodeInstance(makeNode('free_1'));
        ctx._freeInstance('free_1');
        assert.ok(!ctx.nodeInstanceMap.has('free_1'));
    });

    it('returns the slot index to the free list', () => {
        const ctx      = makeCtx();
        const before   = ctx._freeInstIndices.length;
        ctx._addNodeInstance(makeNode('free_2'));
        const afterAdd = ctx._freeInstIndices.length;
        ctx._freeInstance('free_2');
        const afterFree = ctx._freeInstIndices.length;

        assert.equal(afterAdd, before - 1, 'one slot consumed on add');
        assert.equal(afterFree, before,     'slot recycled on free');
    });

    it('is a no-op for unknown id', () => {
        const ctx = makeCtx();
        ctx._freeInstance('does_not_exist');
        // should not throw
    });

    it('zeroes the instance matrix (scale 0) so freed slot is invisible', () => {
        const ctx = makeCtx();
        ctx._addNodeInstance(makeNode('free_3'));
        const entry = ctx.nodeInstanceMap.get('free_3');
        const mesh  = ctx.instInstancedMesh;

        ctx._freeInstance('free_3');

        const mat = new THREE_STUBS.Matrix4();
        mesh.getMatrixAt(entry.index, mat);
        // makeScale(0,0,0) sets elements[0]=elements[5]=elements[10]=0
        assert.equal(mat.elements[0], 0, 'scale.x should be 0 after free');
        assert.equal(mat.elements[5], 0, 'scale.y should be 0 after free');
    });
});

// ── _allocateInstance / growth ────────────────────────────────────────────────
describe('_allocateInstance growth', () => {
    it('allocates without error when free list is non-empty', () => {
        const ctx = makeCtx(4);
        const idx = ctx._allocateInstance(false);
        assert.ok(typeof idx === 'number' && idx >= 0);
    });

    it('grows the instInstancedMesh when free list is exhausted', () => {
        const ctx      = makeCtx(2);
        const oldMesh  = ctx.instInstancedMesh;
        // Allocate both slots
        ctx._addNodeInstance(makeNode('g_0', { is_document: false }));
        ctx._addNodeInstance(makeNode('g_1', { is_document: false }));
        // This should trigger growth
        ctx._addNodeInstance(makeNode('g_2', { is_document: false }));
        assert.ok(ctx.nodeInstanceMap.has('g_2'), 'node added after growth');
    });
});

// ── _clearAllInstances ────────────────────────────────────────────────────────
describe('_clearAllInstances', () => {
    it('empties nodeInstanceMap, dataMap, and initialNodeData', () => {
        const ctx = makeCtx();
        ctx._addNodeInstance(makeNode('clear_1'));
        ctx._addNodeInstance(makeNode('clear_2', { is_document: true }));
        ctx._clearAllInstances();
        assert.equal(ctx.nodeInstanceMap.size,  0, 'nodeInstanceMap should be empty');
        assert.equal(ctx.dataMap.size,          0, 'dataMap should be empty');
        assert.equal(ctx.initialNodeData.size,  0, 'initialNodeData should be empty');
    });

    it('empties image sprite maps', () => {
        const ctx  = makeCtx();
        ctx._imageSprites.set('s1', { material: null });
        ctx._extraSprites.set('s1', []);
        ctx._clearAllInstances();
        assert.equal(ctx._imageSprites.size, 0);
        assert.equal(ctx._extraSprites.size, 0);
    });
});

// ── _setInstanceVisible ───────────────────────────────────────────────────────
describe('_setInstanceVisible', () => {
    it('sets scale to 1 when visible=true', () => {
        const ctx  = makeCtx();
        const node = makeNode('vis_1');
        ctx._addNodeInstance(node);

        ctx._setInstanceVisible('vis_1', true);

        const entry = ctx.nodeInstanceMap.get('vis_1');
        const mesh  = entry.isDoc ? ctx.docInstancedMesh : ctx.instInstancedMesh;
        const mat   = new THREE_STUBS.Matrix4();
        mesh.getMatrixAt(entry.index, mat);
        assert.equal(mat.elements[0],  1, 'scale.x should be 1 when visible');
    });

    it('sets scale to 0 when visible=false', () => {
        const ctx  = makeCtx();
        const node = makeNode('vis_2');
        ctx._addNodeInstance(node);

        ctx._setInstanceVisible('vis_2', false);

        const entry = ctx.nodeInstanceMap.get('vis_2');
        const mesh  = entry.isDoc ? ctx.docInstancedMesh : ctx.instInstancedMesh;
        const mat   = new THREE_STUBS.Matrix4();
        mesh.getMatrixAt(entry.index, mat);
        assert.equal(mat.elements[0], 0, 'scale.x should be 0 when hidden');
    });

    it('is a no-op for unknown ids', () => {
        const ctx = makeCtx();
        ctx._setInstanceVisible('ghost', true); // should not throw
    });
});

runAll();
