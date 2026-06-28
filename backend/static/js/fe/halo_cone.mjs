/**
 * halo_cone.mjs — HALO-03 cone-ray transport (§O.18 / §8.2.1.1 / D-04).
 *
 * Opening a halo on a 2D query element transports retrieved 3D nodes onto a
 * SHARED CONE whose apex is that element's live screen position. Per
 * DOMAIN_MODEL §17.1.5 (line 1893): "for each projector-neighbour c_i: ray =
 * focal_centre → screen-projection(c_i.world_pos); intersect ray with cone —
 * collapsed-singular phantom placed at intersection." This module is PURE
 * geometry — apex + candidate + an injected projectFns trio → a position —
 * mirroring `magic_markdown_halo.mjs::haloLayout`'s exact shape (inputs in,
 * positions array out, zero DOM/THREE side effects, unit-testable in plain
 * Node).
 *
 * D10 (never recompute backend math client-side): the backend's
 * `get_apparitions` `transport=True` branch already computes
 * `transport.{similarity,radial,along_ray}` from the real triple-product
 * (`pagerank · tfidf_cos · nomic_cos`). `radial = (1-s)*R` is the backend's
 * own apex-distance scalar (strictly DECREASING as similarity rises — "more
 * similar → nearer the apex", routes.py's own comment). `along_ray = s*R` is
 * the complementary along-ray-axis placement (DOMAIN_MODEL §17.1.5's
 * "ray = focal_centre → screen-projection(c_i.world_pos); intersect ray with
 * cone" — the point where the ray crosses the cone's lateral surface,
 * measured from the apex along the ray itself). Both are consumed VERBATIM —
 * neither is recomputed from `similarity` here.
 *
 * `radial` is the per-candidate apex-distance scalar carried along the
 * ray direction (it is what makes Euclidean apex-distance monotonic in
 * similarity — `along_ray` alone would invert that, since it GROWS with
 * similarity, by backend design, to place the point further from the apex
 * along the ray axis as it nears the cone's lateral wall). `along_ray` is
 * applied as a perpendicular offset (the cone's lateral spread at that
 * depth) so the candidate sits ON the cone surface, not the bare ray.
 */

import { haloLayout } from "./magic_markdown_halo.mjs";

const EPS = 1e-9;

/**
 * _unitPerp(u) — an arbitrary unit vector perpendicular to unit vector `u`
 * (THREE.Vector3-free, plain {x,y,z} objects only — no THREE import, per
 * D-04's "free of THREE and DOM imports" constraint).
 */
function _unitPerp(u) {
  // pick the world axis least aligned with u, cross it with u, normalize.
  const ax = Math.abs(u.x), ay = Math.abs(u.y), az = Math.abs(u.z);
  const ref = (ax <= ay && ax <= az) ? { x: 1, y: 0, z: 0 }
    : (ay <= az) ? { x: 0, y: 1, z: 0 }
      : { x: 0, y: 0, z: 1 };
  const cx = u.y * ref.z - u.z * ref.y;
  const cy = u.z * ref.x - u.x * ref.z;
  const cz = u.x * ref.y - u.y * ref.x;
  const len = Math.hypot(cx, cy, cz) || 1;
  return { x: cx / len, y: cy / len, z: cz / len };
}

/**
 * placeOnCone(apex, candidate, projectFns) → { id, label, x, y, z, similarity,
 * radial, alongRay, hasBacking } | the 2D haloLayout fallback shape.
 *
 *   apex:       { x, y, z }  — the focal's live world position OR screen
 *               centre (apex is a 3D world point here; the projector's
 *               existing `project()` maps world→screen for rendering).
 *   candidate:  { id, label, transport: { similarity, radial, along_ray } }
 *   projectFns: { project, azimuth, nodeWorldPosition } — the projector's
 *               OWN live closure functions, dependency-injected so this
 *               function stays pure/testable without a real THREE scene.
 *
 * For a candidate WITH a backing 3D node (`nodeWorldPosition(id)` resolves):
 * the ray = apex → world_pos (the world-space analogue of "apex →
 * screen-projection(c_i.world_pos)" — projecting BOTH endpoints through the
 * SAME camera commutes with taking the ray in world space first, and this
 * keeps the module THREE-free). The candidate is placed at
 * `apex + ray_unit*radial + perp_unit*along_ray` — `radial` carries the
 * apex-distance-decreasing-with-similarity contract; `along_ray` is the
 * lateral (cone-surface) offset at that depth.
 *
 * For a candidate WITHOUT a backing 3D node (`nodeWorldPosition` returns
 * null/undefined): delegate to the EXISTING 2D `haloLayout` polar
 * placement — the cone path is ADDITIVE, the 2D fallback is preserved
 * (§O.18 line 1895).
 */
export function placeOnCone(apex, candidate, projectFns, opts = {}) {
  const { nodeWorldPosition } = projectFns || {};
  const worldPos = typeof nodeWorldPosition === "function" ? nodeWorldPosition(candidate.id) : null;
  const t = candidate.transport || {};
  const similarity = t.similarity == null ? 0 : t.similarity;

  if (!worldPos) {
    // 2D fallback — additive, preserves the existing polar placement.
    const focal2d = opts.focal2d || { cx: apex.x || 0, cy: apex.y || 0 };
    const idx = opts.index == null ? 0 : opts.index;
    const total = opts.total == null ? 1 : opts.total;
    const camAngle = (typeof projectFns?.azimuth === "function") ? projectFns.azimuth() : 0;
    const placed = haloLayout(focal2d, [{ id: candidate.id, label: candidate.label, similarity }], {
      ...opts.haloOpts, camAngle,
      arcStart: opts.haloOpts?.arcStart != null ? opts.haloOpts.arcStart : -Math.PI,
      arcSpan: opts.haloOpts?.arcSpan != null ? opts.haloOpts.arcSpan : Math.PI,
    });
    // single-candidate haloLayout call always yields index 0/n=1 placement;
    // re-derive the multi-candidate angle the caller actually wants via the
    // batch wrapper (placeCandidatesOnCone) — single calls here keep t/total
    // informational on the returned record only.
    const p = placed[0];
    return {
      id: candidate.id, label: candidate.label, similarity,
      hasBacking: false,
      x: p.cx, y: p.cy, z: 0,
      r: p.r, angle: p.angle,
    };
  }

  const wx = worldPos.x, wy = worldPos.y, wz = worldPos.z;
  const dx = wx - apex.x, dy = wy - apex.y, dz = wz - apex.z;
  const rayLen = Math.hypot(dx, dy, dz);
  const ray = rayLen < EPS ? { x: 1, y: 0, z: 0 } : { x: dx / rayLen, y: dy / rayLen, z: dz / rayLen };
  const perp = _unitPerp(ray);

  const radial = t.radial == null ? 0 : t.radial;       // VERBATIM — never recomputed from similarity
  const alongRay = t.along_ray == null ? 0 : t.along_ray; // VERBATIM — never recomputed from similarity

  return {
    id: candidate.id,
    label: candidate.label,
    similarity,
    radial,
    alongRay,
    hasBacking: true,
    x: apex.x + ray.x * radial + perp.x * alongRay,
    y: apex.y + ray.y * radial + perp.y * alongRay,
    z: apex.z + ray.z * radial + perp.z * alongRay,
  };
}

/**
 * placeCandidatesOnCone(apex, candidates, projectFns, opts) → [placement, ...]
 * — batch wrapper over `placeOnCone`, one entry per candidate, preserving
 * input order (the delete-and-replace ordering test relies on this: removing
 * the top candidate and re-placing the remainder yields the next-most-
 * similar now occupying the nearest-apex slot).
 */
export function placeCandidatesOnCone(apex, candidates, projectFns, opts = {}) {
  const total = candidates.length;
  return candidates.map((c, index) => placeOnCone(apex, c, projectFns, { ...opts, index, total }));
}

export default { placeOnCone, placeCandidatesOnCone };
