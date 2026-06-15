/**
 * tests/test_runner.js — Minimal browser-native test runner.
 *
 * Usage (from any test file):
 *   import { describe, it, assert, runAll } from './test_runner.js';
 *   describe('My suite', () => { it('works', () => assert.equal(1, 1)); });
 *   runAll();
 *
 * Results are written to the DOM if a <div id="test-output"> exists, and
 * always mirrored to console.  Can also be driven from Node.js via:
 *   node --experimental-vm-modules tests/test_runner.js  (with stubs for DOM)
 */

const suites = [];
let currentSuite = null;

export function describe(name, fn) {
    const suite = { name, tests: [] };
    suites.push(suite);
    const prev = currentSuite;
    currentSuite = suite;
    try { fn(); } finally { currentSuite = prev; }
}

export function it(name, fn) {
    if (!currentSuite) throw new Error('it() called outside describe()');
    currentSuite.tests.push({ name, fn });
}

export const assert = {
    ok(val, msg) {
        if (!val) throw new Error(msg || `Expected truthy, got ${val}`);
    },
    equal(a, b, msg) {
        if (a !== b) throw new Error(msg || `Expected ${JSON.stringify(a)} === ${JSON.stringify(b)}`);
    },
    notEqual(a, b, msg) {
        if (a === b) throw new Error(msg || `Expected ${JSON.stringify(a)} !== ${JSON.stringify(b)}`);
    },
    deepEqual(a, b, msg) {
        const sa = JSON.stringify(a), sb = JSON.stringify(b);
        if (sa !== sb) throw new Error(msg || `Expected ${sa} deep-equal to ${sb}`);
    },
    throws(fn, msg) {
        let threw = false;
        try { fn(); } catch (e) { threw = true; }
        if (!threw) throw new Error(msg || 'Expected function to throw');
    },
    closeTo(a, b, delta = 1e-9, msg) {
        if (Math.abs(a - b) > delta)
            throw new Error(msg || `Expected ${a} ≈ ${b} (delta ${delta})`);
    },
};

export async function runAll() {
    let passed = 0, failed = 0;
    const lines = [];

    for (const suite of suites) {
        lines.push(`\n▶ ${suite.name}`);
        for (const test of suite.tests) {
            try {
                await test.fn();
                passed++;
                lines.push(`  ✓ ${test.name}`);
            } catch (e) {
                failed++;
                lines.push(`  ✗ ${test.name}\n      ${e.message}`);
            }
        }
    }

    const summary = `\n${passed + failed} tests: ${passed} passed, ${failed} failed`;
    lines.push(summary);
    const output = lines.join('\n');

    console.log(output);

    const el = typeof document !== 'undefined' && document.getElementById('test-output');
    if (el) {
        el.style.cssText = 'font-family:monospace;white-space:pre;padding:20px;background:#0d1117;color:#e6edf3;font-size:13px;';
        el.textContent   = output;
    }

    return { passed, failed };
}
