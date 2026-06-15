/**
 * cp/node_loader.js — Fetch chunks from the API, build or incrementally
 * update the 3D scene, and the localStorage optimistic cache.
 *
 * Methods become ChunkProjector instance methods via prototype mixin.
 * THREE is a CDN global.
 */

export const NodeLoaderMixin = {

    async loadNodes(opts) {
        opts = opts || {};
        this.setLoadingProgress('Fetching chunks from DB...', 10);

        if (!opts.skipCache) {
            try {
                const cached = localStorage.getItem('wfh_chunk_nodes_cache_v1');
                if (cached) {
                    const cachedData = JSON.parse(cached);
                    if (cachedData && Array.isArray(cachedData.nodes) && cachedData.nodes.length) {
                        console.log(`[ChunkProjector] painting ${cachedData.nodes.length} cached nodes optimistically`);
                        this.setLoadingProgress('Restoring last scene from cache…', 25);
                        this._buildSceneFromPayload(cachedData);
                    }
                }
            } catch (e) { /* ignore */ }
        }

        try {
            const res = await fetch('/api/chunk_nodes');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            this.setLoadingProgress('Parsing chunk data...', 30);
            const data = await res.json();
            console.log(`[ChunkProjector] Loaded ${data.count} chunk nodes`);
            try {
                localStorage.setItem('wfh_chunk_nodes_cache_v1', JSON.stringify(data));
            } catch (e) {
                try { localStorage.removeItem('wfh_chunk_nodes_cache_v1'); } catch (_) { }
            }
            this._buildSceneFromPayload(data);
        } catch (e) {
            this.setLoadingProgress('Failed to load chunks', 100);
            console.error('[ChunkProjector] loadNodes failed', e);
            setTimeout(() => this.hideLoadingProgress(), 1500);
        }
    },

    _buildSceneFromPayload(data) {
        if (data && Array.isArray(data.nodes)) {
            for (const n of data.nodes) this.constructor.layOutNode(n);
            // Populate _chunkIdToInstances for DB-loaded nodes so UMAP can apply
            if (this._chunkIdToInstances) {
                for (const n of data.nodes) {
                    if (n.chunk_id && !n.is_document) {
                        if (!this._chunkIdToInstances.has(n.chunk_id))
                            this._chunkIdToInstances.set(n.chunk_id, new Set());
                        this._chunkIdToInstances.get(n.chunk_id).add(n.id);
                    }
                }
            }
        }

        if (!data.nodes || data.nodes.length === 0) {
            const empty = document.getElementById('results-container');
            if (empty) {
                empty.innerHTML =
                    '<div class="empty-state">No embedded chunks in DB yet.<br>'
                    + 'Enter a URL in the <strong>Scan</strong> field at the '
                    + 'top and click Scan to populate the projector.</div>';
            }
            this.renderFileTree();
            this.renderUrlBuckets();
            this.hideLoadingProgress();
            return;
        }

        // Path 1: unchanged node set — skip rebuild
        const incomingIds = new Set(data.nodes.map(n => n.id));
        if (this.nodeInstanceMap.size > 0) {
            let allSame = incomingIds.size === this.nodeInstanceMap.size;
            if (allSame) {
                for (const id of incomingIds) {
                    if (!this.nodeInstanceMap.has(id)) { allSame = false; break; }
                }
            }
            if (allSame) { this.hideLoadingProgress(); return; }

            // Path 2: incremental add-only (no removals).
            // allPresent must be declared here so it is visible to the
            // guard below regardless of whether allSame was already true.
            let allPresent = true;
            if (!allSame) {
                allPresent = true;
                for (const id of this.nodeInstanceMap.keys()) {
                    if (!incomingIds.has(id)) { allPresent = false; break; }
                }
            }
            if (allPresent && incomingIds.size > this.nodeInstanceMap.size) {
                const newNodes = data.nodes.filter(n => !this.nodeInstanceMap.has(n.id));
                console.log(`[ChunkProjector] Incremental add: +${newNodes.length} nodes`);
                newNodes.forEach(node => this._addNodeInstance(node));
                if (data.edges) {
                    const existingEdgeKeys = new Set(this.edges.map(e => `${e.source}|${e.target}`));
                    data.edges.forEach(e => {
                        if (!existingEdgeKeys.has(`${e.source}|${e.target}`)) this.edges.push(e);
                    });
                    this.rebuildEdges();
                }
                newNodes.forEach(n => {
                    if (!n.url) return;
                    let domain = 'Unknown';
                    try { domain = new URL(n.url).hostname; } catch (_) { }
                    if (!this.domainTree.has(domain)) this.domainTree.set(domain, new Set());
                    this.domainTree.get(domain).add(n.url);
                    try { this.addUrlToActiveWorkspace(n.url); } catch (_) { }
                });
                this.applyWorkspaceVisibility();
                this.renderFileTree();
                this.renderUrlBuckets();
                this.hideLoadingProgress();
                this._spawnImageBillboards(newNodes);
                this._lazyLoadAllNodeDetails(newNodes);
                return;
            }
        }

        // Path 3: full rebuild
        this.setLoadingProgress('Clearing previous scene...', 40);
        this._clearAllInstances();
        if (this._pinnedPanels && this._pinnedPanels.size) {
            Array.from(this._pinnedPanels.keys()).forEach(id => this.unpinPanel(id));
            this._panelHoverCount = 0;
        }

        const box = new THREE.Box3();
        this.setLoadingProgress(`Building 3D objects for ${data.nodes.length} chunks...`, 60);
        data.nodes.forEach(node => {
            this._addNodeInstance(node);
            box.expandByPoint(new THREE.Vector3(node.x, node.y, node.z));
        });

        this.edges = data.edges || [];
        this.rebuildEdges();

        this.setLoadingProgress('Framing camera...', 80);
        if (!box.isEmpty()) {
            const center = box.getCenter(new THREE.Vector3());
            const size   = box.getSize(new THREE.Vector3());
            const maxDim = Math.max(size.x, size.y, size.z) || 10;
            if (this.controls) {
                this.controls.target.copy(center);
                this.camera.position.set(center.x, center.y + maxDim * 0.4, center.z + maxDim * 1.6);
                this.controls.update();
            }
        }

        this.setLoadingProgress('Building domain tree...', 90);
        this.domainTree.clear();
        this.dataMap.forEach(n => {
            if (!n.url) return;
            let domain = 'Unknown';
            try { domain = new URL(n.url).hostname; } catch (e) { }
            if (!this.domainTree.has(domain)) this.domainTree.set(domain, new Set());
            this.domainTree.get(domain).add(n.url);
        });

        try {
            const known   = new Set();
            this.workspaces.forEach(ws => (ws.urls || []).forEach(u => known.add(u)));
            const activeWs = this.workspaces.find(w => w.id === this.activeWorkspaceId);
            if (activeWs) {
                let touched = false;
                this.dataMap.forEach(n => {
                    if (n && n.url && !known.has(n.url)) {
                        activeWs.urls.push(n.url); known.add(n.url); touched = true;
                    }
                });
                if (touched) this.saveWorkspaces();
            }
        } catch (_) { }

        // Drop any URLs still in localStorage workspaces that have no
        // corresponding chunks in the just-loaded server payload —
        // those are leftovers from a previous session, typically
        // after the user ran scripts/reset_state.py to wipe the DB.
        // Without this pass the sidebar shows ghost URLs the user
        // cannot interact with because nothing in the 3D scene
        // matches them.
        if (typeof this._pruneOrphanWorkspaceUrls === 'function') {
            this._pruneOrphanWorkspaceUrls();
        }

        this.applyWorkspaceVisibility();
        this.renderFileTree();
        this.renderUrlBuckets();

        this.setLoadingProgress('Ready', 100);
        setTimeout(() => this.hideLoadingProgress(), 400);

        this._spawnImageBillboards(data.nodes);
        this._lazyLoadAllNodeDetails(data.nodes);
    },

    addNodesIncrementally(rows, opts) {
        if (!Array.isArray(rows) || rows.length === 0) return 0;
        opts = opts || {};
        if (!this.scene || !this.nodeInstanceMap) return 0;

        const toAdd    = [];
        const seenUrls = new Set();
        for (const row of rows) {
            if (!row || !row.id) continue;
            const url = row.url || '';
            if (url && !seenUrls.has(url)) {
                seenUrls.add(url);
                const docId = row.doc_id || `doc_${url}`;
                if (!this.nodeInstanceMap.has(docId))
                    toAdd.push({ id: docId, url, is_document: true, doc_id: '' });
            }
            if (!this.nodeInstanceMap.has(row.id)) {
                toAdd.push({
                    id: row.id, url,
                    is_document: !!row.is_document,
                    doc_id: row.doc_id || (url ? `doc_${url}` : ''),
                });
            }
        }
        if (toAdd.length === 0) return 0;

        const newEdges = [];
        for (const node of toAdd) {
            this.constructor.layOutNode(node);
            this._addNodeInstance(node);
            // Immediately honour workspace visibility so a chunk whose URL
            // is toggled off never flickers on-screen, even for one frame.
            // Applies to both instance nodes and document hubs so the hub
            // sphere also stays hidden when its URL is toggled off.
            if (!this._isUrlVisible(node.url))
                this._setInstanceVisible(node.id, false);
            if (!node.is_document && node.doc_id)
                newEdges.push({ source: node.id, target: node.doc_id });
            if (node.url) {
                let domain = 'Unknown';
                try { domain = new URL(node.url).hostname; } catch (_) { }
                if (!this.domainTree.has(domain)) this.domainTree.set(domain, new Set());
                this.domainTree.get(domain).add(node.url);
                try { this.addUrlToActiveWorkspace(node.url, !!opts.quiet); } catch (_) { }
            }
        }

        if (newEdges.length) {
            const existingKeys = new Set(this.edges.map(e => `${e.source}|${e.target}`));
            for (const e of newEdges)
                if (!existingKeys.has(`${e.source}|${e.target}`)) this.edges.push(e);
            if (opts.quiet) this._rebuildEdgesSoon(); else this.rebuildEdges();
        }

        if (!opts.quiet) {
            this.applyWorkspaceVisibility();
            this.renderFileTree();
            this.renderUrlBuckets();
        } else {
            this._requestUIUpdate();
        }
        return toAdd.length;
    },
};
