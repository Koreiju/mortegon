/**
 * cp/layout.js — Deterministic 3D sphere placement and HSL→RGB conversion.
 *
 * Pure static functions: no DOM, no THREE, no shared state except _layoutCache.
 *
 * Layout model (Batch 2):
 *   • Every URL gets a "hub centroid" computed by hashing its doc_id to a
 *     unit-vector on the doc shell. Hubs live on a sphere of radius
 *     DOC_SHELL_RADIUS, so two URLs land far apart by construction
 *     (typical Hamming-distance between random hash unit-vectors gives
 *     centroid separations well above 2× CLUSTER_RADIUS for ≤ ~30 URLs).
 *   • Each chunk is anchored to its parent hub centroid. Its position
 *     is hub_centroid + hash_unit_sphere(chunk_id) * CLUSTER_RADIUS.
 *     CLUSTER_RADIUS is tuned to a comfortable multiple of the sphere
 *     diameter so neighbouring chunks read as siblings rather than a
 *     blob — parent-child distance ≤ CLUSTER_RADIUS = 8× sphere
 *     diameter on the default INSTANCE_SPHERE_DIAMETER.
 *
 * Why all-hash, no-count: streaming chunks land one-by-one, so any
 * layout that needed "total URLs" or "siblings per URL" would have to
 * shuffle prior positions every time a new chunk arrived. The hash
 * scheme is stable across additions — every chunk's coords are a
 * function of its own id + its parent's id, nothing else. UMAP (when
 * it kicks in at the chunk-count thresholds) overrides this with
 * semantic coords; until then the hash layout is the bootstrap.
 */

// Render diameters — used to pick spacings that read well visually.
// If you change the sphere geometry in instance_manager.js, tune these too.
export const DOC_SPHERE_DIAMETER  = 2.0;
export const INST_SPHERE_DIAMETER = 1.0;

// ── Per-URL cluster radius (BASE) ──
// Chunks of one URL fan out within this radius of their hub centroid
// when the doc has only one or two chunks. `clusterRadius(n_chunks)`
// below scales this up as a doc accumulates more chunks so the arc
// length between adjacent sibling chunks on the cluster shell stays
// roughly constant. Tightened from 2.5 → 1.8 so 1-2 chunks land close
// enough to their hub to read as a coherent cluster.
export const CLUSTER_RADIUS = 1.8;

// ── Distance from origin to any URL hub centroid (BASE) ──
// Used when the workspace has only one doc; `docShellRadius(n_docs)`
// scales it up as more URLs join so adjacent hubs on the shell stay
// at a similar arc separation regardless of how many docs are loaded.
// Tightened from 18 → 12 so a typical 3-5 URL workspace sits inside
// a comfortable orbit-camera framing without auto-zoom-out.
export const DOC_SHELL_RADIUS = 12.0;

// ── Growth thresholds ──
// "Soft start" counts at which the sqrt-scaling kicks in. Below the
// threshold the radius stays at its BASE value (no growth at all);
// above it the radius scales as sqrt(n / threshold) so the *rate* of
// growth is the arc-length-preserving rate, just shifted right on
// the n-axis so small workspaces don't get scattered across the void.
//
// Previously the formula was BASE · sqrt(n) which gave 36 at n=4
// and 72 at n=16 — visibly too large for typical scans. With the
// thresholds below, n=1..8 docs stay at the BASE radius (18), n=32
// reaches ~36, and the user only sees significant expansion past
// a few hundred URLs.
const DOC_SHELL_GROWTH_THRESHOLD = 12;
const CLUSTER_GROWTH_THRESHOLD   = 12;

/**
 * Soft-start arc-length-preserving doc-shell radius.
 *
 *   R(n) = DOC_SHELL_RADIUS · max(1, sqrt(n / 8))
 *
 * For n ≤ 8 the radius stays at DOC_SHELL_RADIUS (no growth — most
 * typical scans live entirely in this regime). For n > 8 it scales
 * as sqrt(n/8) so the great-circle arc between any two hubs stays
 * roughly constant: n=16 → 25, n=32 → 36, n=64 → 51, n=128 → 72.
 * Quadrupling the doc count doubles the shell — the same sqrt(N)
 * rate that keeps arc length constant, just delayed until the shell
 * has actually started to feel crowded.
 */
export function docShellRadius(nDocs) {
    const n = Math.max(1, nDocs | 0);
    return DOC_SHELL_RADIUS * Math.max(1, Math.sqrt(n / DOC_SHELL_GROWTH_THRESHOLD));
}

/**
 * Soft-start arc-length-preserving per-doc cluster radius.
 *
 *   r(c) = CLUSTER_RADIUS · max(1, sqrt(c / 8))
 *
 * Symmetric with docShellRadius: chunks-per-doc up to 8 sit on the
 * base CLUSTER_RADIUS (2.5) sphere. Past 8 the cluster grows just
 * fast enough to keep adjacent siblings the same visual distance
 * apart on the cluster's local shell: c=16 → 3.5, c=32 → 5,
 * c=64 → 7, c=128 → 10.
 */
export function clusterRadius(nChunks) {
    const c = Math.max(1, nChunks | 0);
    return CLUSTER_RADIUS * Math.max(1, Math.sqrt(c / CLUSTER_GROWTH_THRESHOLD));
}

// Optional jitter applied to hub centroids so two URLs whose ids
// happen to share leading bits don't get placed almost on top of each
// other. Tiny radial perturbation keeps the cluster surfaces apart.
export const DOC_SHELL_JITTER = 2.0;

// Cache computed layouts so layOutNode is idempotent and O(1) on repeat calls.
export const _layoutCache = new Map();

/**
 * FNV-1a hash of `s` salted with `salt`, mapped to [0, 1).
 * Used to produce stable, well-distributed spatial/color seeds per node id.
 */
export function _hashUnit(s, salt) {
    let h = 0x811c9dc5;
    const a = (salt || '') + ':';
    for (let i = 0; i < a.length; i++) {
        h ^= a.charCodeAt(i);
        h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
    }
    for (let i = 0; i < s.length; i++) {
        h ^= s.charCodeAt(i);
        h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
    }
    return (h >>> 0) / 0x1_0000_0000;
}

/**
 * Hash `id` (salted with `prefix`) to a uniformly-distributed unit
 * vector on the 2-sphere. Used as a fallback when an insertion-order
 * ordinal isn't available (e.g. orphan chunks without a parent doc);
 * the Fibonacci path below is preferred for equidistant spacing.
 */
function _unitVector(id, prefix) {
    const u1 = _hashUnit(id, prefix + '/theta');
    const u2 = _hashUnit(id, prefix + '/phi');
    const theta  = 2 * Math.PI * u1;
    const cosPhi = 2 * u2 - 1;
    const sinPhi = Math.sqrt(Math.max(0, 1 - cosPhi * cosPhi));
    return [
        Math.cos(theta) * sinPhi,
        Math.sin(theta) * sinPhi,
        cosPhi,
    ];
}

// Per-step angular increment for the Fibonacci spiral, taken verbatim
// from the user's reference implementation
// (antivenom/best_gui_representation_framework_ever.py):
//
//   theta = π · (1 + √5) · indices
//
// where `indices` is `range(N) + 0.5`. Numerically equivalent (modulo
// 2π) to the canonical "golden angle" `2π·(1 − 1/φ) ≈ 2.39996 rad`
// but with the +0.5 shift folded in and a rotation direction that
// matches the reference's resulting sphere geometry. We use the
// reference's literal form so any node we render here lines up bit-
// for-bit with what `generate_equally_spaced_points(N)` would draw
// in matplotlib.
const FIB_THETA_STEP = Math.PI * (1 + Math.sqrt(5));

/**
 * Fibonacci-sphere unit vector for the i-th of N points.
 *
 * Mirrors antivenom/best_gui_representation_framework_ever.py:
 *
 *   indices = range(N) + 0.5
 *   phi     = arccos(1 - 2 · indices / N)
 *   theta   = π · (1 + √5) · indices
 *   x = cos(theta) · sin(phi)
 *   y = sin(theta) · sin(phi)
 *   z = cos(phi)
 *
 * The +0.5 shift gets applied to BOTH `phi` and `theta`. The previous
 * JS port dropped the shift from theta (used `i · golden_angle`
 * instead of `(i+0.5) · π(1+√5)`), which gave the cluster the
 * "warped to one side" tilt the user spotted — every point's
 * azimuth was off by a half-step relative to its z band, so the
 * spiral started on the equator instead of mid-tilt and accumulated
 * a visible bias toward one hemisphere.
 */
export function fibSphereUnit(i, N) {
    const total = Math.max(1, N | 0);
    const idx   = Math.max(0, i | 0) % total;
    const indexShifted = idx + 0.5;
    const z      = 1 - 2 * indexShifted / total;     // = cos(phi)
    const zc     = z < -1 ? -1 : (z > 1 ? 1 : z);
    const sinPhi = Math.sqrt(Math.max(0, 1 - zc * zc));
    const theta  = FIB_THETA_STEP * indexShifted;
    return [
        Math.cos(theta) * sinPhi,
        Math.sin(theta) * sinPhi,
        zc,
    ];
}

/**
 * Compute the centroid (3D position) of a URL hub.
 *
 * Two placement modes:
 *   1. If `docOrdinal` and `nDocs` are both known, place the hub on
 *      the Fibonacci-sphere slot `(docOrdinal, nDocs)` — equidistant
 *      from its neighbours.
 *   2. Otherwise fall back to a hash-derived unit vector keyed off
 *      doc_id (the older "moldy but stable" placement).
 *
 * The radial jitter that scattered hubs across slightly different
 * shells in the hash mode is intentionally OMITTED on the Fibonacci
 * path: Fibonacci's whole point is uniform arc length between hubs,
 * which jitter would break.
 */
export function _docCentroid(docId, nDocs, docOrdinal) {
    // §6.1 / §18.2 — the ONLY permitted transient angular sampling is the
    // hash-direction unit vector; Fibonacci-sphere angular placement is a
    // forbidden concept. This preliminary placeholder is replaced wholesale
    // by the backend umap_canonical frame, so it is never a final authority.
    const useFib = false;
    const [ux, uy, uz] = useFib
        ? fibSphereUnit(docOrdinal, nDocs)
        : _unitVector(docId, 'doc');
    const base = (typeof nDocs === 'number' && nDocs > 0)
        ? docShellRadius(nDocs)
        : DOC_SHELL_RADIUS;
    if (useFib) {
        return [ux * base, uy * base, uz * base];
    }
    // Hash path retains the radial jitter so colliding hash
    // directions don't sit at identical shell radii.
    const jitter = (_hashUnit(docId, 'doc/r') - 0.5) * DOC_SHELL_JITTER;
    const r = base + jitter;
    return [ux * r, uy * r, uz * r];
}

/** Standard HSL → RGB conversion returning [r, g, b] in [0, 1]. */
export function _hslToRgb(h, s, l) {
    if (s === 0) return [l, l, l];
    const q = l >= 0.5 ? (l + s - l * s) : (l * (1 + s));
    const p = 2 * l - q;
    const hue = (t) => {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1 / 6) return p + (q - p) * 6 * t;
        if (t < 1 / 2) return q;
        if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
        return p;
    };
    return [hue(h + 1 / 3), hue(h), hue(h - 1 / 3)];
}

/**
 * Assign deterministic {x,y,z,r,g,b} to `node`.
 *
 * For URL hubs (``node.is_document === true``):
 *   centroid = unit_hash(doc_id) · docShellRadius(nDocs)  (+ small radial jitter)
 *
 * For chunk instances:
 *   if ``node.doc_id`` is set we anchor to that URL's hub centroid and
 *   add a per-chunk unit-vector offset of length
 *   clusterRadius(chunks_in_this_doc) · rJitter. If ``doc_id`` is
 *   missing, we fall back to placing the chunk on a base-cluster-
 *   radius shell around the origin — same diameter as a normal
 *   cluster, just centred at (0,0,0).
 *
 * Optional `ctx` argument carries the current counts AND insertion-
 * order ordinals. With ordinals present, hubs and chunks are placed
 * on true Fibonacci-sphere slots (equidistant). Without ordinals we
 * fall back to hash-based unit vectors (random, "moldy" but stable).
 *
 *   ctx = {
 *     nDocs:          number,
 *     chunksPerDoc:   Map<doc_id, number>,
 *     docOrdinals:    Map<doc_id, number>,    // 0-based insertion ordinal
 *     chunkOrdinals:  Map<chunk_id, number>,  // 0-based within parent doc
 *   }
 *
 * The radial jitter that scattered chunks across slightly different
 * cluster shells in the hash mode is intentionally OMITTED on the
 * Fibonacci path so the equidistance survives end-to-end.
 *
 * Result is cached; already-laid-out nodes are returned immediately.
 * The cache key is the node id alone, NOT (node id, counts), because
 * the projector's instance manager invalidates the cache on every
 * relayout pass.
 */
export function layOutNode(node, ctx) {
    if (!node || !node.id) return node;
    const has = (k) => typeof node[k] === 'number' && Number.isFinite(node[k]);
    if (has('x') && has('y') && has('z') && has('r') && has('g') && has('b')) return node;
    const cached = _layoutCache.get(node.id);
    if (cached) {
        node.x = cached[0]; node.y = cached[1]; node.z = cached[2];
        node.r = cached[3]; node.g = cached[4]; node.b = cached[5];
        return node;
    }
    const isDoc          = !!node.is_document;
    const nDocs          = ctx && typeof ctx.nDocs === 'number' ? ctx.nDocs : undefined;
    const chunksPerDoc   = ctx && ctx.chunksPerDoc;
    const docOrdinals    = ctx && ctx.docOrdinals;
    const chunkOrdinals  = ctx && ctx.chunkOrdinals;
    const docOrdFor      = (id) => (docOrdinals && docOrdinals.has(id))
        ? docOrdinals.get(id) : undefined;
    const chunkOrdFor    = (id) => (chunkOrdinals && chunkOrdinals.has(id))
        ? chunkOrdinals.get(id) : undefined;

    let px = 0, py = 0, pz = 0;
    if (isDoc) {
        const c = _docCentroid(node.id, nDocs, docOrdFor(node.id));
        px = c[0]; py = c[1]; pz = c[2];
    } else if (node.doc_id) {
        const c          = _docCentroid(node.doc_id, nDocs, docOrdFor(node.doc_id));
        const chunkCount = (chunksPerDoc && chunksPerDoc.get(node.doc_id)) || 1;
        const chunkOrd   = chunkOrdFor(node.id);
        // §6.1 / §18.2 — hash-direction angular sampling ONLY (Fibonacci-sphere
        // angular placement is forbidden). Transient placeholder; the backend
        // umap_canonical frame supersedes it (never a final authority).
        const useFib     = false;
        const [ux, uy, uz] = useFib
            ? fibSphereUnit(chunkOrd, chunkCount)
            : _unitVector(node.id, 'chunk');
        // Hash path keeps a 0.55..1.0 radial jitter for visual depth so random
        // unit vectors don't all sit on a thin shell — the §6.1 R·(1+n/k)-style
        // radial spread of the preliminary placeholder.
        const rJitter = useFib
            ? 1.0
            : (0.55 + 0.45 * _hashUnit(node.id, 'chunk/r'));
        const r = clusterRadius(chunkCount) * rJitter;
        px = c[0] + ux * r;
        py = c[1] + uy * r;
        pz = c[2] + uz * r;
    } else {
        // No parent hub — orphan instance. Place on a cluster-radius
        // shell around origin so it doesn't slam into the doc shell.
        const [ux, uy, uz] = _unitVector(node.id, 'orphan');
        px = ux * CLUSTER_RADIUS;
        py = uy * CLUSTER_RADIUS;
        pz = uz * CLUSTER_RADIUS;
    }
    node.x = px; node.y = py; node.z = pz;

    // Colour — BOOTSTRAP (transient) only. This is the colour analogue of
    // the "Preliminary radial" position state (DOMAIN_MODEL §6.1): before the
    // scan-end UMAP joint fit lands, a chunk has no content-HSV yet, so we
    // seed a stable per-URL hue family by hashing the parent doc_id (NOT
    // chunk_id) — at a glance a cluster of related blues / oranges rather than
    // rainbow confetti. The very next `umap_canonical` frame OVERWRITES this
    // with the canonical content-HSV (coords[3:6]) via scanner._applyUmapCoords
    // → init.umapHsl, exactly as the hash-direction position is overwritten by
    // the canonical position. Hash-family hue is a legibility bootstrap, never
    // the final colour authority (§6.1 forbidden: doc_id-hash hue as final).
    const colourKey = isDoc ? node.id : (node.doc_id || node.id);
    const hue   = _hashUnit(colourKey, 'hue');
    // Per-chunk lightness variation so siblings are visually distinguishable
    // inside the cluster despite sharing a hue.
    const lJitter = isDoc ? 0 : (_hashUnit(node.id, 'light') - 0.5) * 0.25;
    const light = (isDoc ? 0.62 : 0.55) + lJitter;
    const sat = 0.65;
    const lgt = Math.max(0.2, Math.min(0.85, light));
    const [r, g, b] = _hslToRgb(hue, sat, lgt);
    node.r = r; node.g = g; node.b = b;
    // Expose the bootstrap HSL too (instance_manager stores it as
    // init.umapHsl so the animate-loop hue-phase rotation always has a valid
    // {h,s,l} to rotate, even before UMAP lands). h,s,l are each in [0,1].
    node.h = hue; node.s = sat; node.l = lgt;

    _layoutCache.set(node.id, [node.x, node.y, node.z, node.r, node.g, node.b]);
    if (_layoutCache.size > 100_000) _layoutCache.clear();
    return node;
}

// Backwards-compatible exports for any old code that imported the
// shell-radius constants directly. New code should reference DOC_SHELL_RADIUS.
export const DOC_RADIUS  = DOC_SHELL_RADIUS;
export const INST_RADIUS = DOC_SHELL_RADIUS;  // chunks now anchor relative; no global INST shell
