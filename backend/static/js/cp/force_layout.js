/**
 * cp/force_layout.js — UMAP + force-directed-along-root-rays layout.
 *
 * Replaces the Fibonacci concentric-sphere layout as the authoritative
 * positioning system once UMAP has fired. Per Mortegon §2:
 *
 *   Stage A: UMAP provides initial 3D coords per chunk (the layout
 *            initializer). Fit-to-sphere + collider repulsion post-process.
 *
 *   Stage B: Each chunk is constrained to move ONLY along the ray from
 *            its root URL position to its initial UMAP position (1D radial
 *            problem). Repulsive forces between pairs push nodes apart
 *            along their own rays.
 *
 *   Stage C: Each URL workspace has its own root coordinate. New scans are
 *            placed at distance = existing_max_radius + new_radius + gap.
 *
 * The force-directed loop runs every frame (gated on _umapLayoutActive).
 * Fibonacci positions are ONLY used as a temporary bootstrap while chunks
 * stream in before UMAP fires at scan-end.
 *
 * Methods become ChunkProjector instance methods via prototype mixin.
 */

export const ForceLayoutMixin = {

    /**
     * Initialize per-URL workspace layout state.
     * Called once from initScene or on first scan.
     */
    _initForceLayout() {
        // Per-URL root positions and bounding radii (Mortegon §9.1)
        this._urlRootPositions = new Map();   // url → THREE.Vector3
        this._urlBoundingRadii = new Map();   // url → number
        this._umapLayoutActive = false;       // true once first UMAP fires
        // Per-node ray data: { rayDir: Vector3 (unit), minR: number, maxR: number }
        this._nodeRayData = new Map();
    },

    /**
     * Compute independent root position for a new URL workspace.
     * Places it outside all existing workspaces' bounding spheres.
     * Per Mortegon §2.3 / §9.2.
     */
    _computeUrlRootPosition(url, newBoundingRadius) {
        const T = window.THREE || THREE;
        if (!this._urlRootPositions) this._initForceLayout();

        if (this._urlRootPositions.size === 0) {
            // First URL goes at origin
            const pos = new T.Vector3(0, 0, 0);
            this._urlRootPositions.set(url, pos);
            this._urlBoundingRadii.set(url, newBoundingRadius);
            return pos;
        }

        // Find direction with most empty space (greedy)
        let maxExistingRadius = 0;
        this._urlBoundingRadii.forEach(r => {
            if (r > maxExistingRadius) maxExistingRadius = r;
        });

        const SAFETY_GAP = 5.0;
        const placementDist = maxExistingRadius + newBoundingRadius + SAFETY_GAP;

        // Try candidate directions, pick the one farthest from all existing roots
        const candidates = [];
        const golden = Math.PI * (1 + Math.sqrt(5));
        const nCandidates = 12;
        for (let i = 0; i < nCandidates; i++) {
            const idx = i + 0.5;
            const z = 1 - 2 * idx / nCandidates;
            const sinPhi = Math.sqrt(Math.max(0, 1 - z * z));
            const theta = golden * idx;
            candidates.push(new T.Vector3(
                Math.cos(theta) * sinPhi * placementDist,
                Math.sin(theta) * sinPhi * placementDist,
                z * placementDist
            ));
        }

        let bestDir = candidates[0];
        let bestMinDist = -Infinity;
        for (const cand of candidates) {
            let minDist = Infinity;
            this._urlRootPositions.forEach(existingPos => {
                const d = cand.distanceTo(existingPos);
                if (d < minDist) minDist = d;
            });
            if (minDist > bestMinDist) {
                bestMinDist = minDist;
                bestDir = cand;
            }
        }

        this._urlRootPositions.set(url, bestDir.clone());
        this._urlBoundingRadii.set(url, newBoundingRadius);
        return bestDir;
    },

    /**
     * After UMAP fires, compute ray data for each node.
     * The ray goes from the node's root URL position through the node's
     * UMAP-assigned position. The node can only move along this ray.
     */
    _computeRayData() {
        const T = window.THREE || THREE;
        if (!this._urlRootPositions) this._initForceLayout();
        this._nodeRayData.clear();

        this.initialNodeData.forEach((init, nodeId) => {
            const data = this.dataMap.get(nodeId);
            if (!data || data.is_document) return;

            const url = data.url || '';
            let rootPos = this._urlRootPositions.get(url);
            if (!rootPos) {
                // URL root not yet placed — use its doc hub position
                const docId = data.doc_id;
                if (docId) {
                    const docInit = this.initialNodeData.get(docId);
                    if (docInit) rootPos = docInit.position.clone();
                }
                if (!rootPos) rootPos = new T.Vector3(0, 0, 0);
                this._urlRootPositions.set(url, rootPos.clone());
            }

            const nodePos = init.position.clone();
            const ray = nodePos.clone().sub(rootPos);
            const rayLen = ray.length();

            if (rayLen < 0.001) {
                // Degenerate: node sits on root — assign arbitrary ray
                ray.set(1, 0, 0);
            } else {
                ray.normalize();
            }

            this._nodeRayData.set(nodeId, {
                rayDir: ray,
                radius: rayLen,
                rootPos: rootPos.clone(),
            });
        });
    },

    /**
     * Per-frame force-directed update. Runs only when _umapLayoutActive.
     * Each node moves only along its ray from root URL.
     * Hard-boundary repulsion: pairs closer than 2*R get pushed to 2*R.
     *
     * Per Mortegon §2.4: no soft falloff tail. Two chunks at separation
     * >= 2*R exert zero force. Below that, exactly enough to reach 2*R*safety.
     */
    _stepForceDirected(dt) {
        if (!this._umapLayoutActive) return;
        if (!this._nodeRayData || this._nodeRayData.size === 0) return;

        const T = window.THREE || THREE;
        const NODE_RADIUS = 0.9;
        const SAFETY = 1.4;
        const MIN_SEPARATION = 2 * NODE_RADIUS * SAFETY;

        // Collect all active chunk nodes with ray data
        const nodes = [];
        this._nodeRayData.forEach((rayData, nodeId) => {
            const init = this.initialNodeData.get(nodeId);
            if (!init) return;
            nodes.push({ id: nodeId, init, rayData, pos: init.position.clone() });
        });

        if (nodes.length < 2) return;

        // For each pair, compute repulsion projected onto each node's ray
        const radialForces = new Map(); // nodeId → delta_r (along ray)
        nodes.forEach(n => radialForces.set(n.id, 0));

        for (let a = 0; a < nodes.length; a++) {
            for (let b = a + 1; b < nodes.length; b++) {
                const na = nodes[a];
                const nb = nodes[b];
                const dx = nb.pos.x - na.pos.x;
                const dy = nb.pos.y - na.pos.y;
                const dz = nb.pos.z - na.pos.z;
                const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

                if (dist >= MIN_SEPARATION) continue;
                if (dist < 0.001) continue;

                // Separation vector (unit)
                const ux = dx / dist;
                const uy = dy / dist;
                const uz = dz / dist;

                // Push magnitude needed
                const pushTotal = (MIN_SEPARATION - dist) * 0.5;

                // Project push onto each node's ray direction
                const dotA = -(ux * na.rayData.rayDir.x + uy * na.rayData.rayDir.y + uz * na.rayData.rayDir.z);
                const dotB = (ux * nb.rayData.rayDir.x + uy * nb.rayData.rayDir.y + uz * nb.rayData.rayDir.z);

                radialForces.set(na.id, radialForces.get(na.id) + pushTotal * dotA);
                radialForces.set(nb.id, radialForces.get(nb.id) + pushTotal * dotB);
            }
        }

        // Apply radial forces: move each node along its ray
        const DAMPING = 0.3;
        let moved = 0;
        radialForces.forEach((deltaR, nodeId) => {
            if (Math.abs(deltaR) < 0.001) return;
            const rayData = this._nodeRayData.get(nodeId);
            const init = this.initialNodeData.get(nodeId);
            if (!rayData || !init) return;

            const newRadius = Math.max(0.5, rayData.radius + deltaR * DAMPING);
            rayData.radius = newRadius;

            init.position.set(
                rayData.rootPos.x + rayData.rayDir.x * newRadius,
                rayData.rootPos.y + rayData.rayDir.y * newRadius,
                rayData.rootPos.z + rayData.rayDir.z * newRadius,
            );
            moved++;
        });

        // Update bounding radii per URL
        if (moved > 0 && this._urlRootPositions) {
            const urlMaxR = new Map();
            this._nodeRayData.forEach((rayData, nodeId) => {
                const data = this.dataMap.get(nodeId);
                if (!data) return;
                const url = data.url || '';
                const curr = urlMaxR.get(url) || 0;
                if (rayData.radius > curr) urlMaxR.set(url, rayData.radius);
            });
            urlMaxR.forEach((r, url) => {
                this._urlBoundingRadii.set(url, r);
            });
        }
    },

    /**
     * Activate the force-directed layout after UMAP coords are applied.
     * Computes ray data for all UMAP'd nodes and enables the per-frame loop.
     */
    _activateForceLayout() {
        if (!this._urlRootPositions) this._initForceLayout();

        // Compute root positions from doc hub centroids
        this.dataMap.forEach((data, nodeId) => {
            if (!data || !data.is_document) return;
            const init = this.initialNodeData.get(nodeId);
            if (!init) return;
            const url = data.url || '';
            if (!this._urlRootPositions.has(url)) {
                this._urlRootPositions.set(url, init.position.clone());
            }
        });

        // Compute bounding radii per URL
        this.initialNodeData.forEach((init, nodeId) => {
            const data = this.dataMap.get(nodeId);
            if (!data || data.is_document) return;
            const url = data.url || '';
            const rootPos = this._urlRootPositions.get(url);
            if (!rootPos) return;
            const r = init.position.distanceTo(rootPos);
            const curr = this._urlBoundingRadii.get(url) || 0;
            if (r > curr) this._urlBoundingRadii.set(url, r);
        });

        this._computeRayData();
        this._umapLayoutActive = true;
    },

    /**
     * Place a new URL's workspace independently from existing ones.
     * Called when UMAP coords arrive for a URL we haven't placed yet.
     * Returns the offset to apply to all nodes of this URL.
     */
    _placeNewUrlWorkspace(url, coords) {
        const T = window.THREE || THREE;
        if (!this._urlRootPositions) this._initForceLayout();

        // Compute the new URL's bounding radius from its coords
        let maxR = 0;
        let cx = 0, cy = 0, cz = 0, n = 0;
        for (const cid in coords) {
            const xyz = coords[cid];
            if (!xyz || xyz.length !== 3) continue;
            cx += xyz[0]; cy += xyz[1]; cz += xyz[2]; n++;
        }
        if (n > 0) { cx /= n; cy /= n; cz /= n; }
        for (const cid in coords) {
            const xyz = coords[cid];
            if (!xyz || xyz.length !== 3) continue;
            const dx = xyz[0] - cx, dy = xyz[1] - cy, dz = xyz[2] - cz;
            const r = Math.sqrt(dx * dx + dy * dy + dz * dz);
            if (r > maxR) maxR = r;
        }

        // If this URL already has a root position, keep it
        if (this._urlRootPositions.has(url)) {
            return this._urlRootPositions.get(url);
        }

        return this._computeUrlRootPosition(url, maxR);
    },
};
