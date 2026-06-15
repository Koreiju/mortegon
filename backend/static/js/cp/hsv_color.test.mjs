/**
 * Unit tests for cp/hsv_color.js — the PURE colour maths of the 6D-UMAP chunk
 * fill pipeline (DOMAIN_MODEL §6.1 / §707 / §709).
 *
 * Run:  node backend/static/js/cp/hsv_color.test.mjs
 * Exit: 0 = all pass, 1 = any failure (CI-friendly).
 *
 * This is the unit-test half of the verification split called out in
 * DOMAIN_MODEL §6.1: the continuous hue rotation is a render-only visual the
 * Python REPL cannot observe, so the mapping is locked HERE instead. The
 * backend's 6-vector frame format is locked separately by the REPL scenario
 * `6d-umap-format`.
 */
import {
    clamp01, wrap01, umap6ToHsl, azimuthToHuePhase,
    applyHuePhase, hslToRgb, umap6ToRgb255,
} from './hsv_color.js';

let passed = 0;
let failed = 0;
const fails = [];

function ok(cond, msg) {
    if (cond) { passed++; }
    else { failed++; fails.push(msg); console.error('  ✗ ' + msg); }
}
const EPS = 1e-9;
const near = (a, b, eps = 1e-6) => Math.abs(a - b) <= eps;
function approx(a, b, msg, eps = 1e-6) { ok(near(a, b, eps), `${msg} (got ${a}, want ${b})`); }
function inUnit(x, msg) { ok(Number.isFinite(x) && x >= -EPS && x <= 1 + EPS, `${msg}: ${x} not in [0,1]`); }

// ── clamp01 ────────────────────────────────────────────────────────────────
approx(clamp01(0.5), 0.5, 'clamp01 passthrough');
approx(clamp01(-3), 0, 'clamp01 floors negatives');
approx(clamp01(7), 1, 'clamp01 caps >1');
approx(clamp01(NaN), 0.5, 'clamp01 NaN → neutral 0.5');
approx(clamp01(undefined, 0.0), 0.0, 'clamp01 honours custom fallback');

// ── wrap01 (handles negative azimuths) ───────────────────────────────────────
approx(wrap01(0), 0, 'wrap01 0');
approx(wrap01(1.25), 0.25, 'wrap01 1.25 → 0.25');
approx(wrap01(-0.25), 0.75, 'wrap01 -0.25 → 0.75');
approx(wrap01(3.5), 0.5, 'wrap01 3.5 → 0.5');
approx(wrap01(Infinity), 0, 'wrap01 non-finite → 0');

// ── umap6ToHsl ───────────────────────────────────────────────────────────────
{
    const c = umap6ToHsl([10, -20, 5, 0.5, 1, 1]); // reads channels 3..5
    approx(c.h, 0.5, 'umap6ToHsl hue from channel[3]');
    approx(c.s, 0.45 + 0.45 * 1, 'umap6ToHsl sat band top');
    approx(c.l, 0.38 + 0.30 * 1, 'umap6ToHsl light band top');
    inUnit(c.h, 'umap6ToHsl h'); inUnit(c.s, 'umap6ToHsl s'); inUnit(c.l, 'umap6ToHsl l');
}
{
    const c = umap6ToHsl([0.2, 0.4, 0.6]); // bare [h,s,v] triple
    approx(c.h, 0.2, 'umap6ToHsl bare-triple hue');
    approx(c.s, 0.45 + 0.45 * 0.4, 'umap6ToHsl bare-triple sat');
    approx(c.l, 0.38 + 0.30 * 0.6, 'umap6ToHsl bare-triple light');
}
{
    // Degenerate / hostile inputs → neutral band, never NaN, always in range.
    for (const bad of [null, undefined, [], [1, 2], [0, 0, 0, NaN, NaN, NaN], 'x', 42]) {
        const c = umap6ToHsl(bad);
        inUnit(c.h, `umap6ToHsl(${JSON.stringify(bad)}) h finite-in-range`);
        inUnit(c.s, `umap6ToHsl(${JSON.stringify(bad)}) s finite-in-range`);
        inUnit(c.l, `umap6ToHsl(${JSON.stringify(bad)}) l finite-in-range`);
    }
}

// ── azimuthToHuePhase ────────────────────────────────────────────────────────
approx(azimuthToHuePhase(0), 0, 'azimuth 0 → phase 0');
approx(azimuthToHuePhase(Math.PI), 0.5, 'azimuth π → phase 0.5');
approx(azimuthToHuePhase(2 * Math.PI), 0, 'azimuth 2π → phase 0 (wrap)');
approx(azimuthToHuePhase(-Math.PI), 0.5, 'azimuth -π → phase 0.5 (negative wraps)');
approx(azimuthToHuePhase(Math.PI, 2), 0, 'azimuth π × 2 cycles → phase 0');
approx(azimuthToHuePhase(Math.PI / 2, 2), 0.5, 'azimuth π/2 × 2 cycles → 0.5');
approx(azimuthToHuePhase(NaN), 0, 'azimuth NaN → 0');
// Visual-identity-persists invariant: same azimuth (mod 2π) ⇒ identical phase.
approx(azimuthToHuePhase(0.7), azimuthToHuePhase(0.7 + 2 * Math.PI),
    'phase is periodic in 2π (identity persists across full orbit)');

// ── applyHuePhase (wrap-around the wheel) ────────────────────────────────────
approx(applyHuePhase(0.9, 0.2), 0.1, 'applyHuePhase wraps 0.9+0.2 → 0.1');
approx(applyHuePhase(0.3, 0.4), 0.7, 'applyHuePhase 0.3+0.4 → 0.7');
approx(applyHuePhase(0.5, 0), 0.5, 'applyHuePhase zero phase identity');
approx(applyHuePhase(0.5, 1), 0.5, 'applyHuePhase full-cycle phase identity');
inUnit(applyHuePhase(1.5, 0.9), 'applyHuePhase always in [0,1)');

// ── hslToRgb (parity with THREE.Color.setHSL semantics) ──────────────────────
function rgbApprox(rgb, want, msg) {
    ok(near(rgb[0], want[0]) && near(rgb[1], want[1]) && near(rgb[2], want[2]),
        `${msg} (got [${rgb.map(x => x.toFixed(3))}], want [${want}])`);
}
rgbApprox(hslToRgb(0, 1, 0.5), [1, 0, 0], 'hsl red');
rgbApprox(hslToRgb(1 / 3, 1, 0.5), [0, 1, 0], 'hsl green');
rgbApprox(hslToRgb(2 / 3, 1, 0.5), [0, 0, 1], 'hsl blue');
rgbApprox(hslToRgb(0, 0, 1), [1, 1, 1], 'hsl white');
rgbApprox(hslToRgb(0, 0, 0), [0, 0, 0], 'hsl black');
rgbApprox(hslToRgb(0, 0, 0.5), [0.5, 0.5, 0.5], 'hsl grey (s=0)');
rgbApprox(hslToRgb(1, 1, 0.5), [1, 0, 0], 'hsl hue wraps (1 ≡ 0)');
for (const [h, s, l] of [[0.1, 0.7, 0.4], [0.55, 0.3, 0.8], [0.9, 1, 0.2]]) {
    const rgb = hslToRgb(h, s, l);
    rgb.forEach((c, i) => inUnit(c, `hslToRgb(${h},${s},${l})[${i}] in range`));
}

// ── umap6ToRgb255 composition ────────────────────────────────────────────────
{
    const rgb = umap6ToRgb255([0, 0, 0, 0, 1, 0.5 / 0.30 * 1]); // hue 0 path
    ok(rgb.length === 3 && rgb.every(c => Number.isInteger(c) && c >= 0 && c <= 255),
        'umap6ToRgb255 returns 3 ints in [0,255]');
    // Phase rotation actually changes the colour for a saturated chunk.
    const a = umap6ToRgb255([0, 0, 0, 0.0, 1, 1], 0.0);
    const b = umap6ToRgb255([0, 0, 0, 0.0, 1, 1], 0.5);
    ok(a.join(',') !== b.join(','), 'umap6ToRgb255 hue phase shifts the colour');
}

// ── summary ──────────────────────────────────────────────────────────────────
console.log(`\nhsv_color.test: ${passed} passed, ${failed} failed`);
if (failed) { console.error('FAILED:\n  - ' + fails.join('\n  - ')); process.exit(1); }
console.log('OK — pure 6D-UMAP colour maths verified');
process.exit(0);
