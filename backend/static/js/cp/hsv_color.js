/**
 * cp/hsv_color.js — PURE colour maths for the 6D-UMAP chunk fill pipeline.
 *
 * DOMAIN_MODEL §6.1 / §707 / §709 / §8.2.1.2: each chunk's UMAP fit is a
 * 6-vector [x, y, z, h, s, v]; the last three are content-derived HSV (each
 * min-max normalised to [0,1] by the backend `LayoutService._project`, locked
 * by `env-scenario --name 6d-umap-format`). The frontend renders those three
 * channels as the chunk's fill colour, rotating the hue in lockstep with the
 * projector camera azimuth (default ~60 s per orbit) so a chunk's visual
 * identity persists across observation angle.
 *
 * Everything in this module is a PURE function of its arguments — no THREE,
 * no DOM, no module state. That is deliberate: the continuous hue ROTATION is
 * a render-loop visual the Python REPL cannot observe (no camera, no mesh), so
 * the *mapping* is factored out here where it CAN be unit-tested in isolation
 * (`node cp/hsv_color.test.mjs`). The render loop in cp/animation.js composes
 * these functions per frame; the halo phantom in cp/concept_graph.js composes
 * the same functions so its hue tracks its parent chunk (§709). See the
 * "REPL/render split" note in DOMAIN_MODEL §6.1.
 *
 * Consumed as ChunkProjector statics (assembled in chunk_projector.js, the
 * same pattern as layout.js `_hslToRgb` / `fibSphereUnit`), reached from mixin
 * methods via `this.constructor.<fn>`.
 */

const TAU = Math.PI * 2;

/** Clamp to [0,1]; non-finite → fallback (default 0.5, the neutral mid-band). */
function clamp01(x, fallback = 0.5) {
    const n = Number(x);
    if (!Number.isFinite(n)) return fallback;
    return n < 0 ? 0 : (n > 1 ? 1 : n);
}

/**
 * Wrap a real number into [0,1) (handles negatives, e.g. a negative azimuth).
 * @example wrap01(1.25) === 0.25 ; wrap01(-0.25) === 0.75
 */
function wrap01(x) {
    const n = Number(x);
    if (!Number.isFinite(n)) return 0;
    return ((n % 1) + 1) % 1;
}

/**
 * Map a UMAP 6-vector's HSV channels to a DISPLAY-READY {h, s, l} for
 * THREE.Color.setHSL (the realised projector convention; the design names the
 * space "HSV" but the third channel is applied as HSL lightness, matching the
 * backend's "setHSL-ready" contract and layout.js `_hslToRgb`).
 *
 * Contract:
 *   - `vec.length >= 6` → reads the content HSV channels vec[3..5].
 *   - `vec.length === 3` → treats the whole vector as a raw [h,s,v] triple
 *     (lets callers pass a bare HSV without the position prefix).
 *   - anything else / missing / non-finite channels → neutral 0.5 band.
 * Output bands keep colours vivid (never near-black / near-white): hue spans
 * the full wheel (it carries the dominant content signal); saturation and
 * lightness are mapped into controlled mid-bands. All outputs in [0,1].
 *
 * @param {number[]} vec  a [x,y,z,h,s,v] 6-vector (or a bare [h,s,v]).
 * @returns {{h:number, s:number, l:number}}
 * @example umap6ToHsl([0,0,0, 0.5, 1, 1]) → { h:0.5, s:0.9, l:0.68 }
 */
function umap6ToHsl(vec) {
    let rh = 0.5, rs = 0.5, rv = 0.5;
    if (Array.isArray(vec)) {
        if (vec.length >= 6) { rh = vec[3]; rs = vec[4]; rv = vec[5]; }
        else if (vec.length === 3) { rh = vec[0]; rs = vec[1]; rv = vec[2]; }
    }
    const h = clamp01(rh);
    // Saturation → [0.45, 0.90]; lightness → [0.38, 0.68]. Tuned so content
    // variation reads primarily through hue while every chunk stays legible.
    const s = 0.45 + 0.45 * clamp01(rs);
    const l = 0.38 + 0.30 * clamp01(rv);
    return { h, s, l };
}

/**
 * Camera azimuth → hue PHASE in [0,1), the offset added to every chunk's base
 * hue each frame (§707: "rotate slowly in lockstep with the projector orbit").
 * One full orbit (2π of azimuth) advances the hue by `cyclesPerOrbit` full
 * cycles (default 1 → one hue cycle per revolution; the "~60 s period" is then
 * emergent from the orbit rate, §6.1). Pure function of the angle, so the same
 * observation azimuth always yields the same hue — visual identity persists.
 *
 * The call site passes the *effective* observation azimuth, i.e. the
 * OrbitControls azimuth plus the world auto-rotation angle (both rotate the
 * presented content), so the hue advances during auto-spin AND tracks user
 * orbiting. That composition lives in animation.js; this function only knows
 * one scalar angle.
 *
 * @param {number} azimuthRad  radians (OrbitControls.getAzimuthalAngle()+spin).
 * @param {number} [cyclesPerOrbit=1]
 * @returns {number} phase in [0,1)
 * @example azimuthToHuePhase(0) === 0 ; azimuthToHuePhase(Math.PI) === 0.5
 */
function azimuthToHuePhase(azimuthRad, cyclesPerOrbit = 1) {
    const a = Number(azimuthRad);
    if (!Number.isFinite(a)) return 0;
    return wrap01((a / TAU) * cyclesPerOrbit);
}

/**
 * Add a phase to a base hue, wrapped into [0,1) — the per-chunk hue rotation.
 * @param {number} h base hue in [0,1]
 * @param {number} phase offset (typically from azimuthToHuePhase)
 * @returns {number} rotated hue in [0,1)
 * @example applyHuePhase(0.9, 0.2) === 0.1 (wraps around the wheel)
 */
function applyHuePhase(h, phase) {
    return wrap01(clamp01(h) + Number(phase || 0));
}

/**
 * Standard HSL→RGB (the algorithm THREE.Color.setHSL uses), so the halo
 * phantom's CSS `rgb()` accent matches the projector mesh exactly. Inputs are
 * clamped/wrapped; outputs are r,g,b in [0,1].
 * @param {number} h hue (wrapped to [0,1))
 * @param {number} s saturation [0,1]
 * @param {number} l lightness [0,1]
 * @returns {[number, number, number]} rgb each in [0,1]
 * @example hslToRgb(0, 1, 0.5) → [1, 0, 0]
 */
function hslToRgb(h, s, l) {
    h = wrap01(h);
    s = clamp01(s);
    l = clamp01(l);
    if (s === 0) return [l, l, l];
    const hue2rgb = (p, q, t) => {
        t = ((t % 1) + 1) % 1;
        if (t < 1 / 6) return p + (q - p) * 6 * t;
        if (t < 1 / 2) return q;
        if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
        return p;
    };
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    return [
        hue2rgb(p, q, h + 1 / 3),
        hue2rgb(p, q, h),
        hue2rgb(p, q, h - 1 / 3),
    ];
}

/** Convenience for the phantom path: 6-vector + live phase → CSS-ready [r,g,b] 0..255 ints. */
function umap6ToRgb255(vec, phase = 0) {
    const { h, s, l } = umap6ToHsl(vec);
    const [r, g, b] = hslToRgb(applyHuePhase(h, phase), s, l);
    return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}

export {
    clamp01,
    wrap01,
    umap6ToHsl,
    azimuthToHuePhase,
    applyHuePhase,
    hslToRgb,
    umap6ToRgb255,
};
