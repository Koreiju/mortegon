/**
 * magic_markdown_halo.mjs — the apparition halo (ray-projection of retrieval
 * similarity around a focal panel).
 *
 * §V.4 / O.18 / §15.2: the auto-halo retrieves candidates and projects each 3D
 * node toward the focal panel along a RAY whose **radial distance encodes a
 * CONSTANT retrieval similarity** (more similar → nearer the focal apex), with
 * **dynamic along-line sliding** + a **ray angle that updates** as the scene
 * (camera azimuth) or the focal moves. Each phantom renders as a **collapsed
 * circular node** showing ONLY the candidate's name/root field (D.1, §15.1).
 *
 * `haloLayout` is PURE (focal + candidates + camAngle → positions) so the ray
 * mechanics are unit-testable in Node; `haloVDom` renders the overlay (above
 * the slate — the T.4 z-order fix), re-anchored to the focal's live rect (the
 * T.4 scroll/move fix) by re-calling on scroll/drag/rAF.
 */

const TAU = Math.PI * 2;

/**
 * haloLayout(focal, candidates, opts) → [{ id, label, similarity, r, angle, cx, cy }].
 *   focal:      { cx, cy }                  // focal panel/token centre (live rect)
 *   candidates: [{ id, label, similarity }] // similarity in [0,1] (the triple product)
 *   opts: { rBase=120, rExtent=200, arcStart=-Math.PI, arcSpan=Math.PI, camAngle=0 }
 *
 * Ray: r = rBase + (1 - similarity)·rExtent  — CONSTANT per candidate (depends
 * only on its similarity, not on camAngle) → "constant-similarity ray". As
 * camAngle changes, the phantom **slides along its ray** (angle rotates, r
 * fixed) — the along-line slide + updating angle. angle = base(i) + camAngle.
 */
export function haloLayout(focal, candidates, opts = {}) {
  const rBase = opts.rBase == null ? 120 : opts.rBase;
  const rExtent = opts.rExtent == null ? 200 : opts.rExtent;
  const arcStart = opts.arcStart == null ? -Math.PI : opts.arcStart;
  const arcSpan = opts.arcSpan == null ? Math.PI : opts.arcSpan;
  const camAngle = opts.camAngle || 0;
  const n = candidates.length;
  return candidates.map((c, i) => {
    const sim = Math.max(0, Math.min(1, c.similarity == null ? 0 : c.similarity));
    const r = rBase + (1 - sim) * rExtent;                 // constant-similarity radius
    const t = n === 1 ? 0.5 : i / (n - 1);
    const angle = arcStart + t * arcSpan + camAngle;        // ray angle updates with camAngle
    return {
      id: c.id, label: c.label, similarity: sim, r, angle,
      cx: focal.cx + r * Math.cos(angle),
      cy: focal.cy + r * Math.sin(angle),
    };
  });
}

function el(tag, attrs = {}, children = []) { return { tag, attrs, children }; }
function txt(tag, attrs, text) { return { tag, attrs, text }; }

/**
 * haloVDom(focal, candidates, opts) → overlay element spec: a fixed full-bleed
 * layer (z ABOVE the slate, pointer-events:none) with one ray line + one
 * collapsed circular phantom (name-only) per candidate.
 */
export function haloVDom(focal, candidates, opts = {}) {
  const placed = haloLayout(focal, candidates, opts);
  const lines = placed.map((p) => el("line", {
    x1: String(focal.cx), y1: String(focal.cy), x2: String(p.cx), y2: String(p.cy),
    stroke: "var(--slate-border,#c0c0c0)", "stroke-width": "1", opacity: "0.5",
  }));
  const svg = el("svg", {
    class: "mm-halo-rays",
    style: "position:fixed;left:0;top:0;width:100vw;height:100vh;pointer-events:none;",
  }, lines);
  const phantoms = placed.map((p) => {
    const w = Math.max(56, Math.min(180, (p.label || "").length * 7 + 20));
    return txt("div", {
      class: "mm-phantom",
      "data-id": p.id,
      "data-sim": p.similarity.toFixed(3),
      style: `position:fixed;left:${p.cx - w / 2}px;top:${p.cy - 18}px;width:${w}px;` +
        `display:flex;align-items:center;justify-content:center;text-align:center;` +
        `background:#000;color:#fff;border:1px solid var(--slate-border,#c0c0c0);` +
        `border-radius:50%/40px;font-family:Georgia,serif;font-size:11px;padding:6px 8px;` +
        `pointer-events:auto;cursor:pointer;box-sizing:border-box;`,
    }, p.label);
  });
  return el("div", {
    class: "mm-halo",
    // ABOVE the slate (the slate sits ~z 9990 in the legacy app; the demo uses
    // a low z, so a large value keeps the halo on top everywhere) — T.4 fix #1.
    style: "position:fixed;left:0;top:0;width:0;height:0;z-index:2147483000;",
  }, [svg, ...phantoms]);
}

export default { haloLayout, haloVDom };
