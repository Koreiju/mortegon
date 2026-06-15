/**
 * cp/instance_manager.js — InstancedMesh pool: create, grow, allocate, free,
 * remove, transform, and visibility helpers.
 *
 * Methods become ChunkProjector instance methods via prototype mixin.
 * THREE is a CDN global.
 */

export const InstanceManagerMixin = {

    _createInstancedMeshes(capacity = 10_000) {
        // Sphere sizes are tuned to the current cluster scale
        // (DOC_SHELL_RADIUS=12, CLUSTER_RADIUS=1.8, camera at ~35
        // units). Doc-hubs draw at radius 0.6 so they read as the
        // dominant landmark of each URL even at the new camera
        // distance; chunk-instance spheres at 0.32 are large enough
        // to be clickable without overlapping each other inside the
        // tighter cluster. Previously 0.35 / 0.18 — tuned for the
        // old 40-unit cluster + (0,25,95) camera, both shrunk too
        // small under the new camera framing.
        const docGeom  = new THREE.SphereGeometry(0.6, 16, 16);
        const instGeom = new THREE.SphereGeometry(0.32, 16, 16);
        const material = new THREE.MeshPhongMaterial({
            color: 0xffffff, emissive: 0x000000, shininess: 30,
        });
        this.docInstancedMesh = new THREE.InstancedMesh(docGeom, material, capacity);
        this.docInstancedMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        this.scene.add(this.docInstancedMesh);

        this.instInstancedMesh = new THREE.InstancedMesh(instGeom, material, capacity);
        this.instInstancedMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        this.scene.add(this.instInstancedMesh);

        this._freeDocIndices  = Array.from({ length: capacity }, (_, i) => capacity - 1 - i);
        this._freeInstIndices = Array.from({ length: capacity }, (_, i) => capacity - 1 - i);
        this._docInstanceIdToNode  = new Array(capacity).fill(null);
        this._instInstanceIdToNode = new Array(capacity).fill(null);
    },

    _growDocMesh(newCapacity) {
        const old  = this.docInstancedMesh;
        const mesh = new THREE.InstancedMesh(old.geometry, old.material, newCapacity);
        mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        const mat = new THREE.Matrix4();
        const col = new THREE.Color();
        for (let i = 0; i < old.count; i++) {
            old.getMatrixAt(i, mat); mesh.setMatrixAt(i, mat);
            if (old.instanceColor) { old.getColorAt(i, col); mesh.setColorAt(i, col); }
        }
        mesh.count = old.count;
        this.scene.remove(old); old.dispose();
        this.docInstancedMesh = mesh;
        this.scene.add(mesh);
        for (let i = old.count; i < newCapacity; i++) this._freeDocIndices.push(i);
        this._docInstanceIdToNode.length = newCapacity;
    },

    _growInstMesh(newCapacity) {
        const old  = this.instInstancedMesh;
        const mesh = new THREE.InstancedMesh(old.geometry, old.material, newCapacity);
        mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        const mat = new THREE.Matrix4();
        const col = new THREE.Color();
        for (let i = 0; i < old.count; i++) {
            old.getMatrixAt(i, mat); mesh.setMatrixAt(i, mat);
            if (old.instanceColor) { old.getColorAt(i, col); mesh.setColorAt(i, col); }
        }
        mesh.count = old.count;
        this.scene.remove(old); old.dispose();
        this.instInstancedMesh = mesh;
        this.scene.add(mesh);
        for (let i = old.count; i < newCapacity; i++) this._freeInstIndices.push(i);
        this._instInstanceIdToNode.length = newCapacity;
    },

    _allocateInstance(isDoc) {
        const freeList = isDoc ? this._freeDocIndices : this._freeInstIndices;
        if (freeList.length === 0) {
            const mesh   = isDoc ? this.docInstancedMesh : this.instInstancedMesh;
            const newCap = Math.max(16, Math.ceil(mesh.count * 1.5));
            if (isDoc) this._growDocMesh(newCap); else this._growInstMesh(newCap);
            return this._allocateInstance(isDoc);
        }
        return freeList.pop();
    },

    _freeInstance(nodeId) {
        const entry = this.nodeInstanceMap.get(nodeId);
        if (!entry) return;
        const { isDoc, index } = entry;
        if (isDoc) {
            this._freeDocIndices.push(index);
            this._docInstanceIdToNode[index] = null;
        } else {
            this._freeInstIndices.push(index);
            this._instInstanceIdToNode[index] = null;
        }
        const mesh = isDoc ? this.docInstancedMesh : this.instInstancedMesh;
        mesh.setMatrixAt(index, new THREE.Matrix4().makeScale(0, 0, 0));
        if (mesh.instanceColor) mesh.setColorAt(index, new THREE.Color(0, 0, 0));
        mesh.instanceMatrix.needsUpdate = true;
        if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
        this.nodeInstanceMap.delete(nodeId);
    },

    _removeNodeInstance(nodeId) {
        this._freeInstance(nodeId); // also removes from nodeInstanceMap
        const sprite = this._imageSprites && this._imageSprites.get(nodeId);
        if (sprite) {
            this.scene.remove(sprite);
            if (sprite.material) {
                if (sprite.material.map) sprite.material.map.dispose();
                sprite.material.dispose();
            }
            this._imageSprites.delete(nodeId);
        }
        if (this._extraSprites) {
            const extras = this._extraSprites.get(nodeId);
            if (extras) {
                extras.forEach(s => {
                    this.scene.remove(s);
                    if (s.material) {
                        if (s.material.map) s.material.map.dispose();
                        s.material.dispose();
                    }
                });
                this._extraSprites.delete(nodeId);
            }
        }
        this.dataMap.delete(nodeId);
        this.initialNodeData.delete(nodeId);
        this.unpinPanel(nodeId);
        this.edges = this.edges.filter(e => e.source !== nodeId && e.target !== nodeId);
        this._rebuildEdgesSoon();
        if (this.selectedId === nodeId) this.selectedId = null;
        if (this.hoveredId  === nodeId) { this.hoveredId = null; this.hideBillboard(); }
    },

    /**
     * W17 / §9.12 — Record a per-instance provenance tint.
     *
     * Accepts the {id: provenance} map from the umap_canonical
     * frame. Each provenance class has a signature hue that the
     * animate loop lerps 25% toward, ON TOP of the per-frame rotated
     * content-HSV (§6.1/§707):
     *   - scanner-emitted: no tint (pure content-HSV)
     *   - graph-output:    25% toward cyan (#22d3ee)
     *   - agent-output:    25% toward amber (#eef0f2)
     *
     * IMPORTANT: this method only RECORDS the class + precomputed tint
     * colour on the entry (`entry._provenance`, `entry._provenanceTint`).
     * It must NOT write `entry.originalColor` directly: the animate loop
     * rewrites originalColor every frame from `init.umapHsl` + the hue
     * phase, so a write here is clobbered ~16 ms later (the prior W17
     * bug, where the tint never actually showed). Recording the tint and
     * composing it in the animate loop lets the rotation and the
     * provenance tint coexist — content identity AND provenance are both
     * legible at once.
     */
    _applyProvenanceTint(provenance_map) {
        if (!provenance_map || !this.nodeInstanceMap) return;
        const T = window.THREE || THREE;
        const tints = {
            'scanner-emitted': null,
            'graph-output':    new T.Color('#22d3ee'),
            'agent-output':    new T.Color('#eef0f2'),
        };
        for (const [id, prov] of Object.entries(provenance_map)) {
            const entry = this.nodeInstanceMap.get(id);
            if (!entry) continue;
            entry._provenance = prov;
            entry._provenanceTint = Object.prototype.hasOwnProperty.call(tints, prov)
                ? tints[prov] : null;
        }
    },

    _setInstanceColor(nodeId, color) {
        const entry = this.nodeInstanceMap.get(nodeId);
        if (!entry) return;
        const mesh = entry.isDoc ? this.docInstancedMesh : this.instInstancedMesh;
        if (mesh.instanceColor) {
            mesh.setColorAt(entry.index, color);
            mesh.instanceColor.needsUpdate = true;
        }
    },

    _setInstanceTransform(nodeId, scale, color) {
        const entry = this.nodeInstanceMap.get(nodeId);
        if (!entry) return;
        const mesh = entry.isDoc ? this.docInstancedMesh : this.instInstancedMesh;
        const init = this.initialNodeData.get(nodeId);
        if (!init) return;
        const mat = new THREE.Matrix4().compose(
            init.position, new THREE.Quaternion(), new THREE.Vector3(scale, scale, scale)
        );
        mesh.setMatrixAt(entry.index, mat);
        if (mesh.instanceColor) {
            mesh.setColorAt(entry.index, color);
            mesh.instanceColor.needsUpdate = true;
        }
        mesh.instanceMatrix.needsUpdate = true;
    },

    _setInstanceVisible(nodeId, visible) {
        this._setInstanceTransform(
            nodeId,
            visible ? 1.0 : 0.0,
            this.nodeInstanceMap.get(nodeId)?.originalColor || new THREE.Color(1, 1, 1)
        );
    },

    _getNodePosition(nodeId) {
        const entry = this.nodeInstanceMap.get(nodeId);
        if (!entry) return null;
        const mesh = entry.isDoc ? this.docInstancedMesh : this.instInstancedMesh;
        const mat  = new THREE.Matrix4();
        mesh.getMatrixAt(entry.index, mat);
        const pos   = new THREE.Vector3();
        const scale = new THREE.Vector3();
        const quat  = new THREE.Quaternion();
        mat.decompose(pos, quat, scale);
        return pos;
    },

    /** Zero every slot; reset free-list stacks; remove sprites and edge lines. */
    _clearAllInstances() {
        if (this.docInstancedMesh) {
            this.docInstancedMesh.count = 0;
            this._freeDocIndices = [];
            const cap = this._docInstanceIdToNode.length;
            for (let i = 0; i < cap; i++) this._freeDocIndices.push(i);
            this._docInstanceIdToNode = new Array(cap).fill(null);
        }
        if (this.instInstancedMesh) {
            this.instInstancedMesh.count = 0;
            this._freeInstIndices = [];
            const cap = this._instInstanceIdToNode.length;
            for (let i = 0; i < cap; i++) this._freeInstIndices.push(i);
            this._instInstanceIdToNode = new Array(cap).fill(null);
        }
        this.nodeInstanceMap.clear();
        this.initialNodeData.clear();
        this.dataMap.clear();
        if (this._imageSprites) {
            this._imageSprites.forEach(sprite => {
                this.scene.remove(sprite);
                if (sprite.material) { if (sprite.material.map) sprite.material.map.dispose(); sprite.material.dispose(); }
            });
            this._imageSprites.clear();
        }
        if (this._extraSprites) {
            this._extraSprites.forEach(arr => arr.forEach(sprite => {
                this.scene.remove(sprite);
                if (sprite.material) { if (sprite.material.map) sprite.material.map.dispose(); sprite.material.dispose(); }
            }));
            this._extraSprites.clear();
        }
        if (this._extraConnectorsMesh) {
            this.scene.remove(this._extraConnectorsMesh);
            if (this._extraConnectorsMesh.geometry) this._extraConnectorsMesh.geometry.dispose();
            if (this._extraConnectorsMesh.material) this._extraConnectorsMesh.material.dispose();
            this._extraConnectorsMesh = null;
        }
        if (this.linesMesh) {
            this.scene.remove(this.linesMesh);
            this.linesMesh.geometry.dispose();
            this.linesMesh.material.dispose();
            this.linesMesh = null;
        }
    },

    _addNodeInstance(node) {
        if (this.nodeInstanceMap.has(node.id)) return;
        const isDoc = !!node.is_document;
        const idx   = this._allocateInstance(isDoc);
        const mesh  = isDoc ? this.docInstancedMesh : this.instInstancedMesh;
        const color = new THREE.Color(node.r, node.g, node.b);
        const entry = { isDoc, index: idx, originalColor: color.clone() };
        this.nodeInstanceMap.set(node.id, entry);

        // ── Count + ordinal bookkeeping for Fibonacci layout ──
        // Each doc gets a stable insertion-order ordinal so the
        // layout module can hand it the i-th Fibonacci-sphere slot
        // of `_n_docs`. Chunks get a per-doc ordinal the same way.
        // The counts also feed the sqrt(N) radius scaling so the
        // shell grows with the workspace.
        if (!this._chunksPerDoc)  this._chunksPerDoc  = new Map();
        if (!this._docOrdinals)   this._docOrdinals   = new Map();
        if (!this._chunkOrdinals) this._chunkOrdinals = new Map();
        if (typeof this._n_docs !== 'number') this._n_docs = 0;
        if (isDoc) {
            this._n_docs++;
            if (!this._docOrdinals.has(node.id)) {
                // Size BEFORE insert = next free 0-based ordinal.
                this._docOrdinals.set(node.id, this._docOrdinals.size);
            }
        } else if (node.doc_id) {
            const c = (this._chunksPerDoc.get(node.doc_id) || 0) + 1;
            this._chunksPerDoc.set(node.doc_id, c);
            if (!this._chunkOrdinals.has(node.id)) {
                // 0-based ordinal of this chunk within its parent doc:
                // count is `c` AFTER incrementing, so the new ordinal
                // is `c - 1`.
                this._chunkOrdinals.set(node.id, c - 1);
            }
        }

        // Apply the cumulative scene-recenter offset so new nodes land
        // in the same frame as everything already in initialNodeData.
        // Without this, a chunk arriving *after* its doc-hub has been
        // recentered would land at its canonical hash position (still
        // far from the origin) while the hub sits at (0,0,0) — chunks
        // visibly detach from their cluster.
        if (!this._sceneShift) this._sceneShift = new THREE.Vector3(0, 0, 0);
        const pos = new THREE.Vector3(
            node.x + this._sceneShift.x,
            node.y + this._sceneShift.y,
            node.z + this._sceneShift.z,
        );
        mesh.setMatrixAt(idx, new THREE.Matrix4().setPosition(pos));
        if (mesh.instanceColor) mesh.setColorAt(idx, color);
        mesh.count = Math.max(mesh.count, idx + 1);
        mesh.instanceMatrix.needsUpdate = true;
        if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;

        if (isDoc) this._docInstanceIdToNode[idx]  = node.id;
        else       this._instInstanceIdToNode[idx] = node.id;

        // umapColor: bootstrap RGB (kept for any legacy reader). umapHsl: the
        // {h,s,l} the animate loop rotates per-frame by the camera-azimuth hue
        // phase (§6.1/§707). Seeded from the hash-family bootstrap HSL set by
        // layout.js (node.h/s/l); OVERWRITTEN with canonical content-HSV
        // (coords[3:6]) by scanner._applyUmapCoords on the next umap_canonical
        // frame — exactly as the bootstrap position is overwritten by canonical.
        const _bh = Number.isFinite(node.h) ? node.h : 0.6;
        const _bs = Number.isFinite(node.s) ? node.s : 0.6;
        const _bl = Number.isFinite(node.l) ? node.l : 0.5;
        this.initialNodeData.set(node.id, {
            position: pos.clone(),
            umapColor: new THREE.Vector3(node.r, node.g, node.b),
            umapHsl: { h: _bh, s: _bs, l: _bl },
        });
        // Merge: preserve any rich metadata (rendered_text, html_raw, chunk_id,
        // content_fields, absolute_xpath…) that scanner.js pre-populated from
        // the chunk_added / chunk_instances_partial stream BEFORE this node was
        // added.  Spreading `node` last ensures layout fields (x/y/z/r/g/b) and
        // navigation fields (doc_id, is_document) from the thin layout row win
        // without erasing the richer fields from the streaming cache.
        const existing = this.dataMap.get(node.id);
        this.dataMap.set(node.id, existing ? { ...existing, ...node } : node);

        // ── Arc-length-preserving relayout ──
        // doc-add → relayout the whole scene (hubs all move outward as
        // _n_docs grows; chunks follow their hubs). chunk-add → just
        // re-spread the chunks of THIS doc since its cluster radius
        // just nudged. Writes go straight to init.position so the
        // next animate frame renders the new positions immediately —
        // no debounce, no smooth lerp, just an instant update. The
        // previous "smooth via init.targetPosition" experiment made
        // updates feel laggy and broke the visible layout while the
        // lerp settled.
        if (isDoc) {
            this._relayoutSphericalGrowth();
        } else if (node.doc_id) {
            this._relayoutSphericalGrowthForDoc(node.doc_id);
        }

        // Centroid maintenance: each time a new doc-hub is added, recompute
        // the centroid of all doc-hub positions and shift the whole scene
        // by -centroid so the mean position of the hubs always sits at the
        // world origin. The spatial-rotation matrix in animate() rotates
        // around the origin, so without this the cluster as a whole would
        // sweep an off-axis circle instead of spinning in place. Cheap:
        // O(N_docs) per hub-add and N_docs is small (≤ workspace size).
        if (isDoc && typeof this._recenterScene === 'function') {
            this._recenterScene();
        }
    },

    /** Build the current layout ctx for layOutNode — includes counts AND ordinals so the Fibonacci path activates. */
    _layoutCtx() {
        return {
            nDocs:         this._n_docs,
            chunksPerDoc:  this._chunksPerDoc,
            docOrdinals:   this._docOrdinals,
            chunkOrdinals: this._chunkOrdinals,
        };
    },

    /**
     * Recompute every node's Fibonacci-sphere position.
     *
     * The algorithm is intentionally simple, matching the user's
     * antivenom/best_gui_representation_framework_ever.py reference:
     *
     *   1. For each doc-hub, compute its target world position as
     *      `fibSphereUnit(docOrdinal, n_docs) * docShellRadius(n_docs)`.
     *   2. Translate every hub by `-centroid_of_hubs` so the cluster
     *      sits at world origin (rotation pivots around it).
     *   3. For each chunk, place it at
     *      `parentHub + fibSphereUnit(chunkOrdinal, chunks_in_doc) * clusterRadius(chunks_in_doc)`.
     *
     * UMAP-locked nodes (those whose positions came from
     * /api/recompute_umap) are skipped so prior UMAP arrangements
     * persist across new scans.
     *
     * Writes directly to `init.position` — no smooth lerp, no
     * debounce, no sceneShift accumulation. The previous version
     * accumulated `_sceneShift` over many recenter passes and the
     * drift produced "contact lens" clusters because new layouts
     * inherited the wrong offset frame.
     */
    _relayoutSphericalGrowth() {
        // Once UMAP + force-directed layout is active, the Fibonacci
        // sphere is no longer authoritative. Skip entirely so UMAP'd
        // positions persist across new doc-adds.
        if (this._umapLayoutActive) return;

        const Layout = (window.app && window.app.constructor) || null;
        if (!Layout) return;
        const fib = Layout.fibSphereUnit;
        const docShellRadius  = Layout.docShellRadius;
        const clusterRadius   = Layout.clusterRadius;
        if (!fib || !docShellRadius || !clusterRadius) return;

        // Step 1 — Fibonacci hub positions, indexed by docId.
        //
        // Per Mortegon §9 two URL clusters should never visually
        // overlap. We enforce a separation by adding the LARGEST
        // cluster's radius to the doc-shell radius — but only when
        // there are ≥ 2 docs, since a single-doc scan should still
        // place its hub at the origin (the recentre step below
        // collapses any non-zero shell back to (0,0,0) for nDocs=1
        // anyway, but we keep the shell modest so streaming chunks
        // never land at extreme world coordinates that the camera
        // bounds would then clamp).
        const hubPos = new Map();
        const nDocs  = Math.max(1, this._n_docs | 0);
        let maxClusterR = 0;
        if (nDocs >= 2 && this._chunksPerDoc && this._chunksPerDoc.size) {
            this._chunksPerDoc.forEach((count) => {
                const r = clusterRadius(count);
                if (r > maxClusterR) maxClusterR = r;
            });
        }
        const baseShell = docShellRadius(nDocs);
        // 1.5× safety margin around the largest cluster keeps hubs
        // far enough apart that their chunk clusters don't merge,
        // while not pushing them so far out that camera framing
        // breaks. For nDocs=1 maxClusterR is 0 (clamped above) and
        // the shell reduces to the base.
        const shell = Math.max(baseShell, baseShell + maxClusterR * 1.5);
        this._docOrdinals.forEach((ordinal, docId) => {
            if (this._umapLocked && this._umapLocked.has(docId)) return;
            const [ux, uy, uz] = fib(ordinal, nDocs);
            hubPos.set(docId, [ux * shell, uy * shell, uz * shell]);
        });

        // Step 2 — recentre hubs so their centroid is at world origin.
        let cx = 0, cy = 0, cz = 0, n = 0;
        hubPos.forEach(p => { cx += p[0]; cy += p[1]; cz += p[2]; n++; });
        if (n > 0) { cx /= n; cy /= n; cz /= n; }
        hubPos.forEach(p => { p[0] -= cx; p[1] -= cy; p[2] -= cz; });

        // Apply hubs to initialNodeData.
        hubPos.forEach((p, docId) => {
            const init = this.initialNodeData.get(docId);
            if (init) init.position.set(p[0], p[1], p[2]);
        });

        // Step 3 — chunks anchor to their hubs.
        this.dataMap.forEach((data, id) => {
            if (!data || data.is_document) return;
            if (!data.doc_id) return;
            if (this._umapLocked && this._umapLocked.has(id)) return;
            const init = this.initialNodeData.get(id);
            if (!init) return;
            const hub = hubPos.get(data.doc_id);
            if (!hub) return;
            const chunkCount = this._chunksPerDoc.get(data.doc_id) || 1;
            const chunkOrd   = this._chunkOrdinals.get(id);
            if (typeof chunkOrd !== 'number') return;
            const [ux, uy, uz] = fib(chunkOrd, chunkCount);
            const r = clusterRadius(chunkCount);
            init.position.set(
                hub[0] + ux * r,
                hub[1] + uy * r,
                hub[2] + uz * r,
            );
        });

        // Maintain `_sceneShift` for any external code that still
        // reads it, but the layout above doesn't need it any more.
        if (!this._sceneShift) {
            const T = window.THREE || THREE;
            this._sceneShift = new T.Vector3(0, 0, 0);
        }
        this._sceneShift.set(0, 0, 0);
    },

    /**
     * Per-doc variant: recompute every chunk position for one doc
     * after a chunk-add. The hub doesn't move (n_docs unchanged) so
     * we only touch the chunks of `docId`.
     */
    _relayoutSphericalGrowthForDoc(docId) {
        if (this._umapLayoutActive) return;

        const Layout = (window.app && window.app.constructor) || null;
        if (!Layout) return;
        const fib = Layout.fibSphereUnit;
        const clusterRadius = Layout.clusterRadius;
        if (!fib || !clusterRadius) return;
        const hubInit = this.initialNodeData.get(docId);
        if (!hubInit) return;
        const hub = [hubInit.position.x, hubInit.position.y, hubInit.position.z];
        const chunkCount = this._chunksPerDoc.get(docId) || 1;
        this.dataMap.forEach((data, id) => {
            if (!data || data.is_document) return;
            if (data.doc_id !== docId) return;
            if (this._umapLocked && this._umapLocked.has(id)) return;
            const init = this.initialNodeData.get(id);
            if (!init) return;
            const chunkOrd = this._chunkOrdinals.get(id);
            if (typeof chunkOrd !== 'number') return;
            const [ux, uy, uz] = fib(chunkOrd, chunkCount);
            const r = clusterRadius(chunkCount);
            init.position.set(
                hub[0] + ux * r,
                hub[1] + uy * r,
                hub[2] + uz * r,
            );
        });
    },

    /**
     * Shift every node's stored position by -(centroid_of_doc_hubs) so the
     * cluster of clusters is centred on the origin. The animation loop reads
     * ``init.position`` each frame, so this slide propagates to the next
     * render without further bookkeeping.
     *
     * Idempotent — calling it twice in a row produces no further change
     * because the second call's computed centroid is already (0,0,0).
     *
     * Also accumulates the applied shift into ``this._sceneShift`` so
     * any *future* incoming node (chunks of doc-hubs that arrive after
     * the recenter, or doc-hubs of later URLs) gets placed in the same
     * shifted frame at ``_addNodeInstance`` time. Without that, chunks
     * land at their canonical hash positions and visibly detach from
     * their cluster hubs.
     */
    _recenterScene() {
        // Once force layout is active, per-URL root positions are
        // authoritative — recentering would fight the placement.
        if (this._umapLayoutActive) return;

        if (!this._sceneShift) this._sceneShift = new THREE.Vector3(0, 0, 0);
        // ── Preserve UMAP-locked clusters ──
        // Once any nodes have been UMAP'd we must NOT translate them.
        // The earlier implementation shifted every init.position by
        // -centroid_of_all_doc_hubs, which moved the previous UMAP'd
        // cluster every time a new URL was added — exactly the "old
        // billboards collapse / bunch up" symptom the user reported.
        //
        // New rule:
        //   1. Compute centroid only over UNLOCKED doc hubs.
        //   2. Shift only UNLOCKED nodes by -centroid.
        //   3. _sceneShift accumulates the delta applied to unlocked
        //      nodes only (used by `_addNodeInstance` to place new
        //      arrivals into the recentered frame).
        //
        // The locked subset stays at its absolute UMAP coordinates;
        // the unlocked subset (the new scan's freshly-laid-out
        // Fibonacci cluster) centres itself on origin. The two
        // clusters end up at different absolute positions, which
        // visually reads as "two distinct workspaces" — exactly the
        // behaviour the user asked for.
        const locked = this._umapLocked;
        let cx = 0, cy = 0, cz = 0, n = 0;
        this.nodeInstanceMap.forEach((entry, id) => {
            if (!entry || !entry.isDoc) return;
            if (locked && locked.has(id)) return;  // skip locked hubs
            const init = this.initialNodeData.get(id);
            if (!init) return;
            cx += init.position.x; cy += init.position.y; cz += init.position.z;
            n++;
        });
        if (n === 0) return;
        cx /= n; cy /= n; cz /= n;
        // Tiny offsets aren't worth the work; bail to avoid micro-jitter.
        const SHIFT_EPS = 1e-4;
        if (Math.abs(cx) < SHIFT_EPS && Math.abs(cy) < SHIFT_EPS && Math.abs(cz) < SHIFT_EPS) return;
        // Shift only the unlocked subset.
        this.initialNodeData.forEach((init, id) => {
            if (locked && locked.has(id)) return;
            init.position.x -= cx;
            init.position.y -= cy;
            init.position.z -= cz;
        });
        this._sceneShift.x -= cx;
        this._sceneShift.y -= cy;
        this._sceneShift.z -= cz;
    },
};
