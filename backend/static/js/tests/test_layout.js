/**
 * tests/test_layout.js — Unit tests for cp/layout.js pure functions.
 *
 * Run in the browser by importing this file and calling runAll(), or via:
 *   node --input-type=module < tests/test_layout.js  (Node 18+)
 */

import { describe, it, assert, runAll } from './test_runner.js';
import {
    _hashUnit, _hslToRgb, layOutNode,
    DOC_RADIUS, INST_RADIUS, _layoutCache,
} from '../cp/layout.js';

// ── _hashUnit ────────────────────────────────────────────────────────────────
describe('_hashUnit', () => {
    it('returns a number in [0, 1)', () => {
        const v = _hashUnit('hello', 'theta');
        assert.ok(v >= 0 && v < 1, `Out of range: ${v}`);
    });

    it('is deterministic for the same inputs', () => {
        assert.equal(_hashUnit('abc', 'phi'), _hashUnit('abc', 'phi'));
    });

    it('produces different values for different salts', () => {
        assert.notEqual(_hashUnit('abc', 'theta'), _hashUnit('abc', 'phi'));
    });

    it('produces different values for different strings', () => {
        assert.notEqual(_hashUnit('node1', 'theta'), _hashUnit('node2', 'theta'));
    });

    it('handles empty string', () => {
        const v = _hashUnit('', '');
        assert.ok(v >= 0 && v < 1);
    });

    it('distributes reasonably across 1000 samples', () => {
        const samples = Array.from({ length: 1000 }, (_, i) => _hashUnit(String(i), 'test'));
        const mean    = samples.reduce((a, b) => a + b, 0) / samples.length;
        // For a uniform [0,1) distribution the mean should be ~0.5 ± 0.05
        assert.ok(mean > 0.4 && mean < 0.6, `Poor distribution, mean=${mean.toFixed(3)}`);
    });
});

// ── _hslToRgb ────────────────────────────────────────────────────────────────
describe('_hslToRgb', () => {
    it('maps (0, 0, 0) to black', () => {
        assert.deepEqual(_hslToRgb(0, 0, 0), [0, 0, 0]);
    });

    it('maps (0, 0, 1) to white', () => {
        assert.deepEqual(_hslToRgb(0, 0, 1), [1, 1, 1]);
    });

    it('maps (0, 0, 0.5) to mid-grey', () => {
        const [r, g, b] = _hslToRgb(0, 0, 0.5);
        assert.closeTo(r, 0.5, 1e-9);
        assert.closeTo(g, 0.5, 1e-9);
        assert.closeTo(b, 0.5, 1e-9);
    });

    it('returns values in [0, 1]', () => {
        for (let h = 0; h < 1; h += 0.1) {
            const [r, g, b] = _hslToRgb(h, 0.65, 0.55);
            assert.ok(r >= 0 && r <= 1, `r out of range: ${r}`);
            assert.ok(g >= 0 && g <= 1, `g out of range: ${g}`);
            assert.ok(b >= 0 && b <= 1, `b out of range: ${b}`);
        }
    });

    it('maps saturated red hue (h=0) to dominant red channel', () => {
        const [r, g, b] = _hslToRgb(0, 1, 0.5);
        assert.ok(r > g && r > b, `Expected red to dominate: r=${r}, g=${g}, b=${b}`);
    });

    it('maps saturated green hue (h=1/3) to dominant green channel', () => {
        const [r, g, b] = _hslToRgb(1 / 3, 1, 0.5);
        assert.ok(g > r && g > b, `Expected green to dominate: r=${r}, g=${g}, b=${b}`);
    });
});

// ── layOutNode ───────────────────────────────────────────────────────────────
describe('layOutNode', () => {
    it('assigns x/y/z/r/g/b to a node', () => {
        const node = { id: 'test-node-1', is_document: false };
        layOutNode(node);
        assert.ok(Number.isFinite(node.x), 'x not finite');
        assert.ok(Number.isFinite(node.y), 'y not finite');
        assert.ok(Number.isFinite(node.z), 'z not finite');
        assert.ok(Number.isFinite(node.r), 'r not finite');
        assert.ok(Number.isFinite(node.g), 'g not finite');
        assert.ok(Number.isFinite(node.b), 'b not finite');
    });

    it('is idempotent — calling twice gives same result', () => {
        const node = { id: 'test-node-2', is_document: false };
        layOutNode(node);
        const x1 = node.x, y1 = node.y, z1 = node.z;
        layOutNode(node);
        assert.equal(node.x, x1); assert.equal(node.y, y1); assert.equal(node.z, z1);
    });

    // §6.1 / §18.2 — the preliminary placeholder is a hash-DIRECTION unit
    // vector at a radial distance (jittered shell / cluster radius), NOT a
    // fixed-radius concentric shell. Exact DOC_RADIUS/INST_RADIUS placement
    // was the old (forbidden) concentric layout; the real contract now is
    // deterministic + finite + positive radial placement (the backend
    // umap_canonical frame supersedes it as the final authority).
    it('places document nodes at a deterministic positive radius', () => {
        const node = { id: 'doc-test-abc', is_document: true };
        layOutNode(node);
        const dist = Math.sqrt(node.x ** 2 + node.y ** 2 + node.z ** 2);
        assert.ok(Number.isFinite(dist) && dist > 0, `Doc distance ${dist} not positive/finite`);
        // Deterministic: a fresh node with the same id lands identically.
        _layoutCache.clear();
        const node2 = { id: 'doc-test-abc', is_document: true };
        layOutNode(node2);
        assert.closeTo(node2.x, node.x, 1e-9, 'doc placement not deterministic');
    });

    it('places instance nodes at a deterministic positive radius', () => {
        const node = { id: 'inst-test-xyz', is_document: false };
        layOutNode(node);
        const dist = Math.sqrt(node.x ** 2 + node.y ** 2 + node.z ** 2);
        assert.ok(Number.isFinite(dist) && dist > 0, `Inst distance ${dist} not positive/finite`);
        _layoutCache.clear();
        const node2 = { id: 'inst-test-xyz', is_document: false };
        layOutNode(node2);
        assert.closeTo(node2.x, node.x, 1e-9, 'inst placement not deterministic');
    });

    it('gives different positions to different ids', () => {
        const a = { id: 'node-aaa', is_document: false };
        const b = { id: 'node-bbb', is_document: false };
        layOutNode(a); layOutNode(b);
        assert.ok(a.x !== b.x || a.y !== b.y || a.z !== b.z, 'Same position for different ids');
    });

    it('returns the same node object (mutates in place)', () => {
        const node   = { id: 'mutate-test', is_document: false };
        const result = layOutNode(node);
        assert.ok(result === node, 'layOutNode should return the same object');
    });

    it('populates the layout cache', () => {
        _layoutCache.clear();
        const node = { id: 'cache-test-node', is_document: false };
        layOutNode(node);
        assert.ok(_layoutCache.has('cache-test-node'), 'Cache not populated');
    });

    it('uses cached values on second call', () => {
        const node1 = { id: 'cache-hit-node', is_document: false };
        layOutNode(node1);
        const cached = _layoutCache.get('cache-hit-node');

        // Modify node and re-apply — should get cached values back
        node1.x = 999;
        const node2 = { id: 'cache-hit-node', is_document: false };
        layOutNode(node2);
        assert.equal(node2.x, cached[0], 'Cache miss on second call');
    });

    it('skips nodes that already have finite x/y/z/r/g/b', () => {
        const node = { id: 'pre-laid-out', is_document: false, x: 1, y: 2, z: 3, r: 0.5, g: 0.5, b: 0.5 };
        layOutNode(node);
        assert.equal(node.x, 1); // should not overwrite
    });

    it('handles null gracefully', () => {
        const result = layOutNode(null);
        assert.equal(result, null);
    });

    it('handles node without id gracefully', () => {
        const node   = { is_document: false };
        const result = layOutNode(node);
        // should return node unchanged without crashing
        assert.ok(!Number.isFinite(node.x), 'Should not assign x to an id-less node');
    });

    it('rgb channels are in [0, 1]', () => {
        for (let i = 0; i < 20; i++) {
            const node = { id: `rgb-range-test-${i}`, is_document: i % 2 === 0 };
            layOutNode(node);
            assert.ok(node.r >= 0 && node.r <= 1, `r out of range: ${node.r}`);
            assert.ok(node.g >= 0 && node.g <= 1, `g out of range: ${node.g}`);
            assert.ok(node.b >= 0 && node.b <= 1, `b out of range: ${node.b}`);
        }
    });
});

runAll();
