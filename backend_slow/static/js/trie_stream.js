/**
 * trie_stream.js
 *
 * Consumes /api/ws/trie/{snapshot_id} delta frames and renders them through
 * the projector's existing `_streamedNodes` / `_streamedLinks` pipeline.
 *
 * Patricia-trie nodes are keyed by `xpath_full`, which — with the
 * generalized-pattern builder — is the *generalized* xpath. Every trie
 * node therefore represents a unique structural pattern and carries a
 * `frequency` count (number of absolute xpaths that collapse into it).
 *
 * Layout is a **spherical radial tree**:
 *   • Leaves are distributed on the unit sphere via a Fibonacci spiral.
 *   • Interior nodes inherit a direction = normalized mean of children.
 *   • Each node is placed at `radius = ROOT_RADIUS_BIAS + depth * RADIUS_STEP`
 *     along its direction, giving a genuinely 3D "blooming sphere" view
 *     instead of a flat disc.
 */

(function (global) {
    'use strict';

    const RADIUS_STEP = 18;     // world units per patricia depth level
    const ROOT_RADIUS_BIAS = 4; // seed offset so the root doesn't sit at origin

    class TrieStreamAdapter {
        constructor(projector) {
            this.projector = projector;
            this.client = projector.client;

            this.snapshotId = null;
            this.url = null;
            this.revision = 0;

            // canonical trie state keyed by xpath_full (= generalized xpath)
            this.nodesByXpath = new Map();
            this.rootXpath = null;

            this.ws = null;
            this._done = false;
        }

        connect(trieSnapshotId, { statusLog, onStateChange } = {}) {
            this.snapshotId = trieSnapshotId;
            this.projector.currentTrieSnapshotId = trieSnapshotId;

            this.nodesByXpath.clear();
            this.rootXpath = null;
            this.revision = 0;
            this._done = false;

            this.ws = this.client.connectTrieStream(trieSnapshotId, {
                onStateChange: (state, info) => {
                    if (statusLog) {
                        if (state === 'connected') statusLog.innerText = 'Trie stream connected…';
                        if (state === 'reconnecting') statusLog.innerText = `Reconnecting (attempt ${info && info.attempt || '?'})…`;
                        if (state === 'permanent_failure') {
                            statusLog.innerText = 'Trie stream failed permanently.';
                            statusLog.style.color = 'orange';
                        }
                    }
                    if (typeof onStateChange === 'function') onStateChange(state, info);
                },
                onFrame: (frame) => this._onFrame(frame, statusLog),
            });
            this.ws.connect();
            return this.ws;
        }

        close() {
            if (this.ws) {
                try { this.ws.close(); } catch (_) {}
                this.ws = null;
            }
        }

        // --- frame handling ---------------------------------------------

        _onFrame(frame, statusLog) {
            if (!frame) return;
            if (frame.type === 'done') {
                this._done = true;
                if (statusLog) statusLog.innerText = `Trie complete — ${this.nodesByXpath.size} patterns.`;
                return;
            }
            if (frame.type !== 'trie') return;

            this.url = frame.url || this.url;
            this.revision = frame.revision || this.revision;
            this.rootXpath = frame.root_xpath || this.rootXpath;

            if (frame.clear_previous) this.nodesByXpath.clear();

            (frame.added || []).forEach(n => this.nodesByXpath.set(n.xpath_full, n));
            (frame.updated || []).forEach(n => this.nodesByXpath.set(n.xpath_full, n));

            if (frame.removed && frame.removed.length) {
                const rem = new Set(frame.removed);
                for (const [xp, node] of this.nodesByXpath) {
                    if (rem.has(node.node_id)) this.nodesByXpath.delete(xp);
                }
            }

            this._rebuildProjectorBuffers(frame.url);

            if (statusLog) {
                const patterns = this.nodesByXpath.size;
                let totalRaw = 0;
                this.nodesByXpath.forEach(n => { totalRaw += (n.frequency || 1); });
                statusLog.innerText =
                    `Streaming trie… ${patterns} generalized patterns over ${totalRaw} absolute paths (rev ${this.revision}).`;
            }
        }

        // --- layout + projector sync ------------------------------------

        _rebuildProjectorBuffers(url) {
            if (!this.nodesByXpath.size) return;

            // Build parent/children adjacency in generalized-xpath space.
            const nodesById = new Map();
            this.nodesByXpath.forEach(n => nodesById.set(n.node_id, n));

            const childrenByXp = new Map();
            this.nodesByXpath.forEach(n => childrenByXp.set(n.xpath_full, []));
            this.nodesByXpath.forEach(n => {
                if (!n.parent_id) return;
                const parent = nodesById.get(n.parent_id);
                if (parent) childrenByXp.get(parent.xpath_full).push(n.xpath_full);
            });

            // Choose root: reported root first, then the lone parentless node,
            // then the shallowest node as a fallback.
            let rootXp = this.rootXpath;
            if (!rootXp || !this.nodesByXpath.has(rootXp)) {
                let best = null;
                this.nodesByXpath.forEach(n => { if (!n.parent_id) best = best || n; });
                if (!best) {
                    this.nodesByXpath.forEach(n => {
                        if (!best || (n.depth_in_patricia || 0) < (best.depth_in_patricia || 0)) best = n;
                    });
                }
                rootXp = best ? best.xpath_full : null;
            }
            if (!rootXp) return;

            // --- Spherical layout -----------------------------------------
            // 1. Collect leaves in DFS order.
            const leaves = [];
            const collectLeaves = (xp) => {
                const kids = childrenByXp.get(xp) || [];
                if (!kids.length) leaves.push(xp);
                else kids.forEach(collectLeaves);
            };
            collectLeaves(rootXp);

            // 2. Assign each leaf a direction on the unit sphere via the
            //    golden-angle Fibonacci spiral — uniform coverage, no poles.
            const N = Math.max(1, leaves.length);
            const GOLDEN = Math.PI * (3 - Math.sqrt(5));
            const dirByXp = new Map();
            leaves.forEach((xp, i) => {
                const yy = 1 - (i + 0.5) * 2 / N;            // y in (1, -1]
                const r = Math.sqrt(Math.max(0, 1 - yy * yy));
                const theta = GOLDEN * i;
                dirByXp.set(xp, [r * Math.cos(theta), yy, r * Math.sin(theta)]);
            });

            // 3. Interior nodes: direction = normalized mean of children's
            //    directions. Falls back to a small outward nudge when the
            //    mean zeroes out (rare: perfectly antipodal children).
            const computeDir = (xp) => {
                const cached = dirByXp.get(xp);
                if (cached) return cached;
                const kids = childrenByXp.get(xp) || [];
                let sx = 0, sy = 0, sz = 0;
                kids.forEach(k => {
                    const d = computeDir(k);
                    sx += d[0]; sy += d[1]; sz += d[2];
                });
                const len = Math.sqrt(sx * sx + sy * sy + sz * sz);
                const d = len > 1e-6
                    ? [sx / len, sy / len, sz / len]
                    : [0, 1, 0];
                dirByXp.set(xp, d);
                return d;
            };
            computeDir(rootXp);

            // --- Construct renderable node list --------------------------
            const sNodes = [];
            const sLinks = [];
            let maxDepth = 0;

            this.nodesByXpath.forEach(n => {
                const depth = n.depth_in_patricia || 0;
                if (depth > maxDepth) maxDepth = depth;
                const R = ROOT_RADIUS_BIAS + depth * RADIUS_STEP;
                const dir = dirByXp.get(n.xpath_full) || [0, 1, 0];
                const x = R * dir[0];
                const y = R * dir[1];
                const z = R * dir[2];

                const freq = n.frequency != null
                    ? n.frequency
                    : (n.covered_xpaths ? n.covered_xpaths.length : 1);

                const tag = (n.chain_segments && n.chain_segments.length)
                    ? n.chain_segments[n.chain_segments.length - 1]
                    : 'root';

                sNodes.push({
                    id: n.node_id,
                    xpath: n.xpath_full,            // generalized xpath (identity)
                    generalized_xpath: n.xpath_pattern || n.xpath_full,
                    tag,
                    depth,
                    depthRaw: n.depth_in_raw,
                    ahu: n.ahu_canonical_form,
                    is_content: !!n.is_content,
                    covered_xpaths: n.covered_xpaths || [],
                    coveredCount: freq,
                    frequency: freq,
                    categories: [],
                    url: url || this.url || '',
                    snapshotIndex: 0,
                    x, y, z,
                });

                if (n.parent_id) {
                    sLinks.push({
                        source: n.parent_id,
                        target: n.node_id,
                        type: 'trie',
                    });
                }
            });

            // --- Push into projector stream buffers ----------------------
            const p = this.projector;
            p._streamSnapshotId = 0;
            p._streamOffsetX = 0;
            p._streamBoundingRadius = ROOT_RADIUS_BIAS + maxDepth * RADIUS_STEP + 10;
            p._streamUrl = url || this.url || '';

            p._streamedNodes = sNodes;
            p._streamedLinks = sLinks;
            p._streamedNodeIndex = new Map(sNodes.map((n, i) => [n.id, i]));
            p._streamedLinkIndex = new Map(sLinks.map(
                (l, i) => [`${l.source}|${l.target}|${l.type}`, i]
            ));

            // Cache trie metadata on the projector so other features
            // (click, highlight, retrieval) can reach it without state threading.
            p.trieNodesByXpath = this.nodesByXpath;
            p.trieNodesById = nodesById;

            if (typeof p._scheduleStreamRebuild === 'function') {
                p._scheduleStreamRebuild();
            } else if (typeof p.mergeStreamedNodes === 'function') {
                if (!p._trieRebuildScheduled) {
                    p._trieRebuildScheduled = true;
                    requestAnimationFrame(() => {
                        p._trieRebuildScheduled = false;
                        try { p.mergeStreamedNodes(); } catch (e) { console.error(e); }
                    });
                }
            }
        }
    }

    global.TrieStreamAdapter = TrieStreamAdapter;
})(window);
