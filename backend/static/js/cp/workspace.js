/**
 * cp/workspace.js — File tree, workspace management, URL visibility, and the
 * left (#ft-latch) sidebar panel toggle.
 *
 * Methods become ChunkProjector instance methods via prototype mixin.
 */

// Monotonic sequence number appended to workspace IDs so that two workspaces
// created within the same millisecond (common in tests) are never given the
// same ID, which would cause a filter-by-id to remove both entries.
let _wsIdSeq = 0;

export const WorkspaceMixin = {

    initFileTree() {
        const style = document.createElement('style');
        style.innerHTML = `
            #ft-latch {
                position: fixed; top: 50%; left: 0px;
                background: var(--surface-base, #242933); border: 1px solid var(--border-light, #434c5e);
                border-left: none; color: var(--text-secondary, #d8dee9); padding: 20px 6px; cursor: pointer;
                z-index: 9500; border-radius: 0 8px 8px 0;
                transition: background-color 0.15s;
                box-shadow: 4px 0 6px rgba(0,0,0,0.1); display: flex;
                align-items: center; justify-content: center;
            }
            #ft-latch:hover { color: var(--text-primary, #eceff4); background: var(--surface-hover, #3b4252); }
            .sidebar-sliding { transition: transform 0.3s ease, margin 0.3s ease, width 0.3s ease, min-width 0.3s ease, padding 0.3s ease, opacity 0.2s ease !important; }
            .ft-header-main {
                padding: 12px 15px; border-bottom: 1px solid rgba(255,255,255,0.1);
                font-weight: 600; color: #fff; background: rgba(255,255,255,0.02);
            }
            .ft-section { padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
            .ft-section-header {
                padding: 5px 15px; font-weight: 600; color: #9ca3af;
                display: flex; justify-content: space-between; align-items: center;
                cursor: pointer; user-select: none;
            }
            .ft-section-header:hover { color: #fff; }
            .ft-btn-icon {
                background: none; border: none; color: #9ca3af; cursor: pointer;
                padding: 2px 6px; border-radius: 4px; font-size: 14px; line-height: 1;
            }
            .ft-btn-icon:hover { background: rgba(255,255,255,0.1); color: #fff; }
            .ws-save-btn { color: #b8c0c8; }
            .ws-save-btn:hover { color: #9aa3ab; }
            .ft-folder { margin: 2px 0; }
            .ft-folder-title {
                padding: 6px 15px 6px 25px; cursor: pointer; display: flex; align-items: center;
                transition: background 0.15s; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            }
            .ft-folder-title:hover { background: rgba(255,255,255,0.05); }
            .ft-folder.active-ws .ft-folder-title { background: rgba(184,192,200,0.15); color: #b8c0c8; font-weight: bold; }
            .ws-name-input {
                background: transparent; border: none; color: inherit; font: inherit; outline: none;
                width: calc(100% - 40px); cursor: text;
            }
            .ws-name-input:focus { border-bottom: 1px solid rgba(255,255,255,0.5); }
            .ft-add-ws-btn {
                padding: 6px 15px 6px 40px; cursor: pointer; color: #9ca3af; transition: color 0.15s; font-weight: bold; font-size: 16px;
            }
            .ft-add-ws-btn:hover { color: #fff; background: rgba(255,255,255,0.05); }
            .ft-items { display: none; background: rgba(0,0,0,0.2); }
            .ft-items.expanded { display: block; }
            .ft-item {
                padding: 5px 15px 5px 40px; cursor: pointer; display: flex; align-items: center;
                justify-content: space-between; transition: background 0.15s;
            }
            .ft-item:hover { background: rgba(255,255,255,0.08); }
            .ft-url-label { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 170px; }
            .ft-item-actions { display: none; gap: 4px; }
            .ft-item:hover .ft-item-actions { display: flex; }
            .ft-item-actions button {
                background: none; border: none; color: #9ca3af; cursor: pointer; padding: 2px;
            }
            .ft-item-actions button:hover { color: #fff; }
            .ft-item-actions button.remove-hover:hover { color: #b25b5b; }
        `;
        document.head.appendChild(style);

        const latch = document.createElement('div');
        latch.id        = 'ft-latch';
        latch.title     = 'Toggle Workspace Panel';
        latch.innerHTML = '<i class="fas fa-chevron-left" style="transition: transform 0.3s ease;"></i>';
        document.body.appendChild(latch);

        latch.addEventListener('click', () => {
            const panel = document.getElementById('history-sidebar');
            if (!panel) return;
            if (!panel.classList.contains('sidebar-sliding')) panel.classList.add('sidebar-sliding');
            if (!panel.dataset.originalWidth || parseInt(panel.dataset.originalWidth) === 0)
                if (panel.offsetWidth > 0) panel.dataset.originalWidth = panel.offsetWidth;
            const width       = parseInt(panel.dataset.originalWidth) || 280;
            const isCollapsed = panel.dataset.collapsed === 'true';
            const icon        = latch.querySelector('i');
            if (isCollapsed) {
                panel.style.transform    = '';
                panel.style.opacity      = '1';
                panel.style.pointerEvents = '';
                icon.style.transform     = 'rotate(0deg)';
                panel.dataset.collapsed  = 'false';
            } else {
                panel.style.transform    = `translateX(-${width + 10}px)`;
                panel.style.opacity      = '0';
                panel.style.pointerEvents = 'none';
                icon.style.transform     = 'rotate(180deg)';
                panel.dataset.collapsed  = 'true';
            }
            let start = Date.now();
            const timer = setInterval(() => {
                window.dispatchEvent(new Event('resize'));
                if (Date.now() - start > 350) clearInterval(timer);
            }, 16);
        });

        this.renderFileTree();
    },

    loadWorkspaces() {
        try { const raw = localStorage.getItem('wfh_workspaces'); if (raw) return JSON.parse(raw); }
        catch (e) { }
        return [];
    },

    saveWorkspaces() {
        localStorage.setItem('wfh_workspaces', JSON.stringify(this.workspaces));
    },

    createWorkspace(name) {
        const ws = { id: `ws_${Date.now()}_${++_wsIdSeq}`, name, urls: [], hiddenUrls: [] };
        this.workspaces.push(ws);
        this.saveWorkspaces();
        return ws.id;
    },

    renderFileTree() {
        const container = document.getElementById('history-container');
        if (!container) return;
        let html = `<div class="ft-header-main" style="display:flex;align-items:center;justify-content:space-between;">
            <span>File Explorer</span>
            <button onclick="app.toggleAllDocClusters()" title="Toggle all document clusters"
                style="background:none;border:none;color:#9ca3af;cursor:pointer;font-size:12px;padding:2px 6px;border-radius:3px;"
                onmouseenter="this.style.color='#fff'" onmouseleave="this.style.color='#9ca3af'">
                <i class="fas fa-compress-arrows-alt"></i>
            </button>
        </div>`;

        html += `<div class="ft-section">
            <div class="ft-section-header" onclick="app.toggleFtFolder('ft-workspaces')">
                <span><i class="fas ${this.expandedFolders.has('ft-workspaces') ? 'fa-chevron-down' : 'fa-chevron-right'}"></i> Workspaces</span>
            </div>
            <div id="ft-workspaces" class="ft-items ${this.expandedFolders.has('ft-workspaces') ? 'expanded' : ''}">`;

        this.workspaces.forEach(ws => {
            const isActive = ws.id === this.activeWorkspaceId;
            const folderId = `ft-ws-${ws.id}`;
            const isExp    = this.expandedFolders.has(folderId);
            html += `<div class="ft-folder ${isActive ? 'active-ws' : ''}">
                <div class="ft-folder-title" onclick="app.setActiveWorkspace('${ws.id}')" oncontextmenu="app.deleteWorkspace('${ws.id}', event)">
                    <span style="margin-right:8px;" onclick="event.stopPropagation(); app.toggleFtFolder('${folderId}')">
                        <i class="fas fa-dot-circle" ${isExp ? '' : 'style="opacity: 0.5;"'}></i>
                    </span>
                    <input type="text" class="ws-name-input" id="input-ws-${ws.id}" value="${this.escape(ws.name)}"
                        onclick="event.stopPropagation(); app.setActiveWorkspace('${ws.id}')"
                        oninput="app.onWorkspaceNameInput('${ws.id}')"
                        onkeydown="if(event.key==='Enter') app.saveWorkspaceName('${ws.id}')" />
                    <button class="ft-btn-icon ws-save-btn" id="save-ws-${ws.id}" style="display:none;"
                        onclick="event.stopPropagation(); app.saveWorkspaceName('${ws.id}')"><i class="fas fa-check"></i></button>
                </div>
                <div id="${folderId}" class="ft-items ${isExp ? 'expanded' : ''}">`;
            ws.urls.forEach(url => {
                const isHidden = ws.hiddenUrls && ws.hiddenUrls.includes(url);
                // Clicking the URL row toggles the doc-hub's collapse
                // state in the 3D scene — uncollapses if currently
                // folded, recollapses if currently popped. The action
                // buttons keep their own handlers via stopPropagation.
                html += `<div class="ft-item" style="cursor:pointer;"
                              onclick="app.toggleDocCollapseForUrl('${this.escape(url)}')">
                    <span class="ft-url-label" title="${this.escape(url)}">📄 ${this.escape(this.shortenUrl(url))}</span>
                    <span class="ft-item-actions">
                        <button title="${isHidden ? 'Show in GUI' : 'Deselect from GUI'}" onclick="event.stopPropagation(); app.toggleUrlVisibility('${ws.id}', '${this.escape(url)}')">
                            <i class="fas ${isHidden ? 'fa-eye-slash' : 'fa-eye'}"></i>
                        </button>
                        <button class="remove-hover" title="Remove from Workspace" onclick="event.stopPropagation(); app.removeUrlFromWorkspace('${ws.id}', '${this.escape(url)}')">
                            <i class="fas fa-times"></i>
                        </button>
                    </span>
                </div>`;
            });
            html += `</div></div>`;
        });
        html += `<div class="ft-add-ws-btn" title="Add Workspace" onclick="app.addNewWorkspaceField()">+</div>`;
        html += `</div></div>`;

        html += `<div class="ft-section">
            <div class="ft-section-header" onclick="app.toggleFtFolder('ft-domains')">
                <span><i class="fas ${this.expandedFolders.has('ft-domains') ? 'fa-chevron-down' : 'fa-chevron-right'}"></i> Domains</span>
            </div>
            <div id="ft-domains" class="ft-items ${this.expandedFolders.has('ft-domains') ? 'expanded' : ''}">`;
        if (this.domainTree.size === 0)
            html += `<div class="ft-item" style="color:#6b7280; font-style:italic;">No domains loaded</div>`;
        this.domainTree.forEach((urls, domain) => {
            const folderId = `ft-dom-${domain}`;
            const isExp    = this.expandedFolders.has(folderId);
            html += `<div class="ft-folder">
                <div class="ft-folder-title" onclick="app.toggleFtFolder('${folderId}')">
                    <span style="margin-right:8px;"><i class="fas fa-globe"></i></span>
                    ${this.escape(domain)} <span style="color:#6b7280; margin-left:8px;">(${urls.size})</span>
                </div>
                <div id="${folderId}" class="ft-items ${isExp ? 'expanded' : ''}">`;
            urls.forEach(url => {
                // Domain rows: click toggles the doc-hub's collapse
                // state in the 3D scene (uncollapse on first click,
                // recollapse on the next). Adding the URL to the
                // active workspace also happens implicitly via the
                // toggle method if it's not already a workspace URL.
                html += `<div class="ft-item domain-item"
                              onmouseenter="app.previewUrl('${this.escape(url)}')"
                              onmouseleave="app.clearPreview()"
                              onclick="app.toggleDocCollapseForUrl('${this.escape(url)}')">
                    <span class="ft-url-label" title="${this.escape(url)}">🔗 ${this.escape(this.shortenUrl(url))}</span>
                </div>`;
            });
            html += `</div></div>`;
        });
        html += `</div></div>`;
        html += `<div style="margin-top:auto; padding:10px 15px; font-size:11px; color:#6b7280; border-top:1px solid rgba(255,255,255,0.05);">
            <i class="fas fa-info-circle"></i> Right-click a Workspace to delete it.
        </div>`;
        container.innerHTML = html;
    },

    toggleFtFolder(id) {
        if (this.expandedFolders.has(id)) this.expandedFolders.delete(id); else this.expandedFolders.add(id);
        this.renderFileTree();
    },

    onWorkspaceNameInput(id) {
        const inputEl = document.getElementById(`input-ws-${id}`);
        const saveBtn = document.getElementById(`save-ws-${id}`);
        if (!inputEl || !saveBtn) return;
        if (!this.wsEditOriginals.has(id)) {
            const ws = this.workspaces.find(w => w.id === id);
            this.wsEditOriginals.set(id, ws ? ws.name : '');
        }
        saveBtn.style.display = 'inline-block';
        if (this.wsEditTimers.has(id)) clearTimeout(this.wsEditTimers.get(id));
        const timer = setTimeout(() => {
            inputEl.value = this.wsEditOriginals.get(id) || '';
            saveBtn.style.display = 'none';
            this.wsEditOriginals.delete(id);
            this.wsEditTimers.delete(id);
        }, 3000);
        this.wsEditTimers.set(id, timer);
    },

    saveWorkspaceName(id) {
        const inputEl = document.getElementById(`input-ws-${id}`);
        const saveBtn = document.getElementById(`save-ws-${id}`);
        if (!inputEl) return;
        if (this.wsEditTimers.has(id)) { clearTimeout(this.wsEditTimers.get(id)); this.wsEditTimers.delete(id); }
        const newName = inputEl.value.trim();
        const ws      = this.workspaces.find(w => w.id === id);
        if (ws && newName) { ws.name = newName; this.saveWorkspaces(); }
        else if (ws) inputEl.value = ws.name;
        if (saveBtn) saveBtn.style.display = 'none';
        this.wsEditOriginals.delete(id);
    },

    addNewWorkspaceField() {
        const newId = this.createWorkspace('');
        this.expandedFolders.add(`ft-ws-${newId}`);
        this.renderFileTree();
        setTimeout(() => {
            const inputEl = document.getElementById(`input-ws-${newId}`);
            if (inputEl) { inputEl.focus(); inputEl.select(); }
        }, 50);
    },

    setActiveWorkspace(id) {
        if (this.activeWorkspaceId === id) return;
        this.activeWorkspaceId = id;
        this.applyWorkspaceVisibility();
        const container = document.getElementById('history-container');
        if (container) {
            container.querySelectorAll('.ft-folder').forEach(f => f.classList.remove('active-ws'));
            const activeFolder = container.querySelector(`#ft-ws-${id}`)?.closest('.ft-folder');
            if (activeFolder) activeFolder.classList.add('active-ws');
        }
        // W21 — re-hydrate concept cards for the new workspace.
        // Tear down current cards (the local Map is the rendering
        // source of truth; backend has its own per-workspace store).
        if (this._conceptNodes && this._conceptNodes.size) {
            for (const id of Array.from(this._conceptNodes.keys())) {
                const card = document.querySelector(`.concept-card[data-node-id="${id}"]`);
                if (card && card.parentNode) card.parentNode.removeChild(card);
            }
            this._conceptNodes.clear();
            this._conceptEdges = [];
            if (this._edgeLineCache) this._edgeLineCache.clear();
            if (typeof this._drawConceptEdges === 'function') this._drawConceptEdges();
        }
        // Fix: cancel every pending concept sync timer so we don't
        // PATCH against the old workspace's concept ids after switch.
        // Without this, the debounced edit fired just before switch
        // would write into the new workspace (likely 404).
        if (this._conceptSyncTimers) {
            for (const t of this._conceptSyncTimers.values()) clearTimeout(t);
            this._conceptSyncTimers.clear();
        }
        if (this._conceptSyncPending) this._conceptSyncPending.clear();
        if (this._conceptBackendIds) this._conceptBackendIds.clear();
        // Clear cached overlays + side panels so we don't see
        // stale state from the previous workspace.
        if (typeof this._clearApparitionHalo === 'function') this._clearApparitionHalo();
        const tokenPanel = document.getElementById('wfh-agent-token-panel');
        if (tokenPanel && tokenPanel.parentNode) tokenPanel.parentNode.removeChild(tokenPanel);
        this._agentTokenPanel = null;
        if (this._agentTokenBuffers) this._agentTokenBuffers.clear();
        const reviewsHost = document.getElementById('wfh-agent-reviews');
        if (reviewsHost) reviewsHost.innerHTML = '';
        const evlogPanel = document.getElementById('wfh-evolution-log-panel');
        if (evlogPanel && evlogPanel.parentNode) evlogPanel.parentNode.removeChild(evlogPanel);
        const agentsPanel = document.getElementById('wfh-agents-panel');
        if (agentsPanel && agentsPanel.parentNode) agentsPanel.parentNode.removeChild(agentsPanel);
        // Reset concept-index cache + apparition-hints cache.
        if (this._conceptIndexCache) this._conceptIndexCache.clear();
        if (this._apparitionHints) this._apparitionHints.clear();
        this._conceptWorkspaceId = id;
        // Re-connect the workspace WS to the new id. Also clear
        // any pending reconnect back-off timer so we don't have
        // a stale callback racing the new connect.
        if (this._workspaceReconnectTimer) {
            clearTimeout(this._workspaceReconnectTimer);
            this._workspaceReconnectTimer = null;
        }
        if (this._workspaceWs) {
            try { this._workspaceWs.close(); } catch (_) {}
            this._workspaceWs = null;
        }
        this._workspaceWsBackoff = 2000;
        if (typeof this._connectWorkspaceWs === 'function') {
            this._connectWorkspaceWs();
        }
        if (typeof this._hydrateConceptsFromBackend === 'function') {
            this._hydrateConceptsFromBackend().catch(_ => {});
        }
    },

    deleteWorkspace(id, event) {
        if (event) { event.preventDefault(); event.stopPropagation(); }
        if (this.workspaces.length <= 1) return;
        if (!confirm('Delete this workspace?')) return;
        this.workspaces = this.workspaces.filter(w => w.id !== id);
        if (this.activeWorkspaceId === id) this.activeWorkspaceId = this.workspaces[0].id;
        this.saveWorkspaces();
        this.applyWorkspaceVisibility();
        this.renderFileTree();
    },

    addUrlToActiveWorkspace(url, quiet = false) {
        const ws = this.workspaces.find(w => w.id === this.activeWorkspaceId);
        if (!ws) return;
        if (!ws.urls.includes(url)) {
            ws.urls.push(url);
            this.saveWorkspaces();
            // During streaming (quiet=true) skip the expensive full-scene
            // visibility pass and DOM rebuild — the debounced _requestUIUpdate
            // in addNodesIncrementally will flush these at most once per 800 ms.
            if (!quiet) {
                this.applyWorkspaceVisibility();
                this.renderFileTree();
            }
        }
    },

    removeUrlFromWorkspace(wsId, url) {
        const ws = this.workspaces.find(w => w.id === wsId);
        if (!ws) return;
        ws.urls = ws.urls.filter(u => u !== url);
        if (ws.hiddenUrls) ws.hiddenUrls = ws.hiddenUrls.filter(u => u !== url);
        this.saveWorkspaces();
        // ── Hard cleanup of the URL's 3D footprint ──
        // The user expects "remove from workspace" to actually make
        // the URL's nodes disappear from the scene, not just the
        // sidebar listing. Drop the doc hub, every chunk, every
        // sprite, and any edges incident to them across ALL
        // workspaces (since a URL the user removed from one
        // workspace is also gone from any others — that's what
        // the user's request implies).
        this._purgeUrlFromScene(url);
        if (this.activeWorkspaceId === wsId) this.applyWorkspaceVisibility();
        this.renderFileTree();
    },

    /**
     * Strip every trace of `url` from the 3D scene and the supporting
     * maps. Removes the doc-hub sphere, every chunk-instance sphere,
     * any image sprites, any sticky pinned panels, edges incident to
     * the removed nodes, and the URL's entry in the domain tree.
     *
     * Idempotent — calling it on a URL that's not present in the
     * scene is a no-op aside from a workspace-list filter that also
     * runs unconditionally so localStorage stays consistent.
     */
    _purgeUrlFromScene(url) {
        if (!url) return;
        const docId = `doc_${url}`;
        const victimIds = [];
        // Collect all chunk-instance ids tied to this URL.
        this.nodeInstanceMap.forEach((entry, id) => {
            const data = this.dataMap.get(id);
            if (data && (data.url === url || id === docId)) {
                victimIds.push(id);
            }
        });
        // Remove each one through the canonical _removeNodeInstance
        // path so freelists, sprites, panels, edges, and selection
        // state all reconcile correctly.
        for (const id of victimIds) {
            if (typeof this._removeNodeInstance === 'function') {
                this._removeNodeInstance(id);
            }
        }
        // Reverse-map cleanup: per-chunk indices / counts.
        if (this._chunkIndex) {
            victimIds.forEach(id => this._chunkIndex.delete(id));
        }
        if (this._chunksPerDoc) {
            this._chunksPerDoc.delete(docId);
        }
        if (this._docIndex) {
            this._docIndex.delete(docId);
        }
        // Domain tree update.
        for (const [domain, urls] of this.domainTree.entries()) {
            urls.delete(url);
            if (urls.size === 0) this.domainTree.delete(domain);
        }
        // Workspace-wide: drop the URL from every workspace that had
        // it (the user removed it from one — they don't expect to
        // see ghosts in another).
        this.workspaces.forEach(w => {
            w.urls       = w.urls.filter(u => u !== url);
            if (w.hiddenUrls) w.hiddenUrls = w.hiddenUrls.filter(u => u !== url);
        });
        this.saveWorkspaces();
        // Clean force-layout per-URL state so purged URLs don't leave
        // ghost root positions that affect future scan placement.
        if (this._urlRootPositions) this._urlRootPositions.delete(url);
        if (this._urlBoundingRadii) this._urlBoundingRadii.delete(url);
        // Force a redraw so the edge mesh updates immediately.
        if (typeof this._rebuildEdgesSoon === 'function') this._rebuildEdgesSoon();
        else if (typeof this.rebuildEdges === 'function') this.rebuildEdges();
    },

    /**
     * Drop workspace URLs that have NO corresponding chunk in the
     * just-loaded scene. Surfaces orphaned localStorage state left
     * over from a previous session (or a server-side reset that
     * wiped the kuzu DB while the browser still cached the old
     * workspace structure).
     *
     * Called once at the tail of `loadNodes` after the initial chunk
     * payload has been applied. Only prunes URLs that are NOT
     * referenced by any actual chunk in `dataMap`.
     */
    _pruneOrphanWorkspaceUrls() {
        // Build the set of URLs that the scene actually knows about
        // post-load. If the server returned chunks for url X, X stays.
        const liveUrls = new Set();
        this.dataMap.forEach((data) => {
            if (data && data.url) liveUrls.add(data.url);
        });
        let removed = 0;
        this.workspaces.forEach(w => {
            const before = w.urls.length;
            w.urls = w.urls.filter(u => liveUrls.has(u));
            if (w.hiddenUrls) {
                w.hiddenUrls = w.hiddenUrls.filter(u => liveUrls.has(u));
            }
            removed += (before - w.urls.length);
        });
        // Domain tree pruning — same rule.
        for (const [domain, urls] of this.domainTree.entries()) {
            const live = new Set();
            urls.forEach(u => { if (liveUrls.has(u)) live.add(u); });
            if (live.size === 0) this.domainTree.delete(domain);
            else this.domainTree.set(domain, live);
        }
        if (removed > 0) {
            console.info(`[workspace] pruned ${removed} orphan URL(s) absent from server payload`);
            this.saveWorkspaces();
        }
        return removed;
    },

    toggleUrlVisibility(wsId, url) {
        const ws = this.workspaces.find(w => w.id === wsId);
        if (!ws) return;
        if (!ws.hiddenUrls) ws.hiddenUrls = [];
        if (ws.hiddenUrls.includes(url)) ws.hiddenUrls = ws.hiddenUrls.filter(u => u !== url);
        else ws.hiddenUrls.push(url);
        // §6.3 — mirror per-URL visibility so the 3D projector hide/show, peer
        // tabs, and the REPL "hidden 3D" row stay in sync with the eye toggle.
        if (typeof this._mirrorUi === 'function')
            this._mirrorUi('/api/ui/url_visibility', { url, collapsed: ws.hiddenUrls.includes(url) });
        this.saveWorkspaces();
        if (this.activeWorkspaceId === wsId) this.applyWorkspaceVisibility();
        this.renderFileTree();
    },

    async deleteUrlFromDB(url, event) {
        if (event) event.preventDefault();
        if (!confirm(`Permanently delete all chunks for ${url} from the database? This cannot be undone.`)) return;
        try {
            await fetch(`/api/map/snapshots?url=${encodeURIComponent(url)}`, { method: 'DELETE' });
        } catch (e) { console.warn('DB delete fetch failed', e); }
        const toDelete = [];
        this.nodeInstanceMap.forEach((entry, id) => {
            const data = this.dataMap.get(id);
            if (data && data.url === url) { toDelete.push(id); this._freeInstance(id); }
        });
        toDelete.forEach(id => { this.dataMap.delete(id); this.initialNodeData.delete(id); });
        this.edges = this.edges.filter(e => this.initialNodeData.has(e.source) && this.initialNodeData.has(e.target));
        this.rebuildEdges();
        for (const [domain, urls] of this.domainTree.entries()) {
            urls.delete(url);
            if (urls.size === 0) this.domainTree.delete(domain);
        }
        this.workspaces.forEach(w => {
            w.urls = w.urls.filter(u => u !== url);
            if (w.hiddenUrls) w.hiddenUrls = w.hiddenUrls.filter(u => u !== url);
        });
        this.saveWorkspaces();
        this.applyWorkspaceVisibility();
        this.renderFileTree();
    },

    applyWorkspaceVisibility() {
        const ws = this.workspaces.find(w => w.id === this.activeWorkspaceId);
        if (!ws) return;
        const visibleSet = new Set(ws.urls.filter(u => !(ws.hiddenUrls || []).includes(u)));
        // Per Mortegon §4.3: write the per-URL hidden set onto the
        // ChunkProjector so the animate-loop scale gate can read it
        // every frame. The old code only nudged the instance matrix
        // once via _setInstanceVisible, but the per-frame loop in
        // animation.js overwrites scale from (frustum && no sprite),
        // so the hide was invisible. The animate-loop gate (added in
        // cp/animation.js) reads `this._hiddenUrls` and forces scale=0
        // for any node whose URL is in the set.
        //
        // IMPORTANT — must match `_isUrlVisible`'s tri-state model:
        //   1. URL explicitly in ws.hiddenUrls (eye-off)        → HIDDEN
        //   2. URL in another workspace but not active workspace → HIDDEN
        //   3. URL not in ANY workspace (brand-new streaming URL) → VISIBLE
        // Case 3 was being incorrectly hidden by an earlier draft of
        // this fix (the broad "if not visibleSet.has(url) then hide"
        // rule swallowed streaming chunks whose URL hadn't yet been
        // added to the active workspace by addUrlToActiveWorkspace —
        // visually that's "scan stops early"). The correct rule below
        // only adds a URL to _hiddenUrls when we have positive evidence
        // it should be hidden (it appears in another workspace or in
        // this workspace's hiddenUrls list).
        if (!this._hiddenUrls) this._hiddenUrls = new Set();
        this._hiddenUrls.clear();
        (ws.hiddenUrls || []).forEach(u => this._hiddenUrls.add(u));
        // URLs belonging to a different workspace get hidden too — per
        // Mortegon §5.3: "Switching the active workspace hides all
        // hubs whose URL isn't in the new active workspace's `urls`."
        this.workspaces.forEach(other => {
            if (other.id === ws.id) return;
            (other.urls || []).forEach(u => {
                if (!ws.urls.includes(u)) this._hiddenUrls.add(u);
            });
        });
        // Same predicate, applied as a one-shot to the instance
        // matrices. The per-frame gate handles persistence; this just
        // gets the immediate-feedback frame.
        this.nodeInstanceMap.forEach((entry, id) => {
            const data = this.dataMap.get(id);
            if (!data) return;
            const visible = !this._hiddenUrls.has(data.url);
            this._setInstanceVisible(id, visible);
        });
        this._imageSprites.forEach((sprite, nodeId) => {
            const data = this.dataMap.get(nodeId);
            const visible = data && !this._hiddenUrls.has(data.url);
            if (visible) { sprite.visible = true; sprite.material.opacity = 1; }
            else sprite.visible = false;
        });
        const input      = document.getElementById('nl-search');
        const searchActive = !!(input && input.value.trim()) || !!this.lastSearchPayload;
        if (searchActive && this.lastSearchPayload) this.renderSearchResults(this.lastSearchPayload);
        else this.renderUrlBuckets();
    },

    previewUrl(url) {
        this.nodeInstanceMap.forEach((entry, id) => {
            const data = this.dataMap.get(id);
            if (data && data.url === url && !this._imageSprites.has(id)) {
                this._setInstanceTransform(id, 1.0, entry.originalColor.clone().multiplyScalar(0.3));
            }
        });
    },

    clearPreview() {
        this.nodeInstanceMap.forEach((entry, id) => {
            if (!this._imageSprites.has(id)) this.restoreNodeVisuals(id);
        });
    },

    /**
     * Toggle the doc-hub collapse state for a given URL. Wired to
     * every URL row in the left sidebar (both workspace items and
     * domain items): one click uncollapses the cluster, the next
     * recollapses. Also opens the URL's knowledge panel so the user
     * sees the page-level summary (search chunk if available) when
     * the chunks pop out.
     *
     * Falls back to no-op if the doc isn't present in the scene yet.
     */
    toggleDocCollapseForUrl(url) {
        if (!url) return;
        // Doc-hub ids in the projector follow the `doc_<url>` pattern
        // (set in scanner.js when chunks arrive: `doc_id: ${`doc_${frameUrl}`}`).
        const docId = `doc_${url}`;
        if (!this.nodeInstanceMap.has(docId)) return;
        if (!this.docCollapseTarget) this.docCollapseTarget = new Map();
        const cur = this.docCollapseTarget.get(docId);
        // Default state is "uncollapsed" (0); flip to 1 to collapse,
        // back to 0 to uncollapse.
        const next = (cur === 1) ? 0 : 1;
        this.docCollapseTarget.set(docId, next);
        // Per Mortegon §4.2: when a search is active, the scroll-spine
        // observer maintains per-chunk overrides (visible rows = popped,
        // off-screen rows = folded). Clearing these on every URL click
        // destroys the spine state and makes all chunks of the URL
        // explode together — exactly the bug the user reported. Only
        // clear overrides when no search is active; with a search, let
        // the spine observer keep authority and toggleDoc only nudges
        // the URL-level default for chunks that have no spine override
        // (e.g. chunks not currently in the search results).
        const searchInput  = document.getElementById('nl-search');
        const searchActive = !!(searchInput && searchInput.value.trim()) ||
                             !!this.lastSearchPayload;
        if (!searchActive &&
            this.chunkCollapseTarget && this.chunkCollapseTarget.size) {
            this.chunkCollapseTarget.forEach((_, chunkId) => {
                const d = this.dataMap.get(chunkId);
                if (d && d.doc_id === docId) this.chunkCollapseTarget.delete(chunkId);
            });
        }
        // Fly the camera so the user sees what they just toggled.
        if (next === 0 && typeof this.flyToNode === 'function') {
            this.flyToNode(docId);
        }
    },

    renderUrlBuckets() {
        const container = document.getElementById('results-container');
        if (!container) return;
        const byUrl = new Map();
        this.nodeInstanceMap.forEach((entry, id) => {
            const data = this.dataMap.get(id);
            if (!data || !data.url) return;
            if (!this._getNodePosition(id)) return;
            const normUrl = data.url.split('?')[0].replace(/\/+$/, '');
            if (!byUrl.has(normUrl)) byUrl.set(normUrl, { displayUrl: data.url, items: [] });
            byUrl.get(normUrl).items.push(data);
        });
        if (byUrl.size === 0) { container.innerHTML = '<div class="empty-state">No chunks loaded.</div>'; return; }
        let visibleCount = 0;
        this.nodeInstanceMap.forEach((entry, id) => { if (this._getNodePosition(id)) visibleCount++; });
        const parts = [`<div class="bucket-heading">${visibleCount} chunks across ${byUrl.size} URL${byUrl.size === 1 ? '' : 's'}</div>`];
        byUrl.forEach((group, normUrl) => {
            parts.push(`
                <div class="url-bucket" data-url="${this.escape(group.displayUrl)}" style="cursor: pointer;">
                    <div class="url-bucket-head" title="${this.escape(normUrl)}">
                        <i class="fas fa-globe"></i> ${this.escape(this.shortenUrl(normUrl))}
                        <span class="url-bucket-count">${group.items.length}</span>
                    </div>
                </div>`);
        });
        container.innerHTML = parts.join('');
        container.querySelectorAll('.url-bucket').forEach(el => {
            const url = el.dataset.url;
            el.addEventListener('click', () => {
                const normClicked = url.split('?')[0].replace(/\/+$/, '');
                const targetItems = byUrl.has(normClicked) ? byUrl.get(normClicked).items : [];
                if (targetItems.length > 0) this.showChunksForUrl(url, targetItems);
            });
            const docId = `doc_${url}`;
            el.addEventListener('mouseenter', () => {
                this.hoveredId = docId;
                const entry = this.nodeInstanceMap.get(docId);
                if (entry && docId !== this.selectedId)
                    this._setInstanceColor(docId, entry.originalColor.clone().multiplyScalar(1.8));
            });
            el.addEventListener('mouseleave', () => {
                if (this.hoveredId === docId) this.hoveredId = null;
                if (docId !== this.selectedId) this.restoreNodeVisuals(docId);
            });
        });
    },

    /**
     * Return true if `url` should be visible under the active workspace.
     * Called immediately after _addNodeInstance so streaming nodes respect
     * the user's current visibility toggles from frame one.
     */
    _isUrlVisible(url) {
        if (!url) return true;
        const ws = this.workspaces.find(w => w.id === this.activeWorkspaceId);
        if (!ws) return true;
        // A URL that is not yet in the workspace is a brand-new streaming URL
        // that addUrlToActiveWorkspace will add immediately after this check.
        // Treat it as visible so it never flickers off-then-on.
        // Only URLs explicitly listed AND present in hiddenUrls are hidden.
        if (!ws.urls.includes(url)) return true;
        return !(ws.hiddenUrls && ws.hiddenUrls.includes(url));
    },

    /**
     * Collapse all document clusters if any are expanded, otherwise expand all.
     * Wired to the toggle button in the File Explorer header.
     *
     * Previously this iterated nodeInstanceMap looking for entries whose
     * dataMap row had ``is_document: true``. That missed any doc hub
     * whose dataMap row had been overwritten by chunk metadata (e.g.,
     * after a frame whose URL bucket reused the same ``doc_<url>`` id
     * key). The result was that one URL would keep snapping back to
     * expanded on every Collapse-All click. Now we read straight off
     * the InstanceMap entry's ``isDoc`` flag — set at allocation time
     * and never mutated thereafter, so the doc set is authoritative.
     *
     * The function ALSO sets ``_userGlobalCollapse`` so that downstream
     * hover-based search handlers (which transiently expand a doc on
     * mouseenter) know to restore to the user's collapse decision on
     * mouseleave rather than the implicit default.
     */
    toggleAllDocClusters() {
        // Enumerate every doc hub authoritatively via the InstanceMap.
        const docIds = [];
        this.nodeInstanceMap.forEach((entry, id) => {
            if (entry && entry.isDoc) docIds.push(id);
        });
        // Pick up any tracked docs that — for whatever reason — aren't
        // in nodeInstanceMap right now (lazy spawn paths, replay frames
        // in flight). The collapse target should be authoritative across
        // both populations so neither snaps back.
        this.docCollapseTarget.forEach((_, docId) => {
            if (!docIds.includes(docId)) docIds.push(docId);
        });

        // Decide direction from the union: if ANY hub is currently
        // expanded (target 0 or absent, since absent defaults to 0),
        // the toggle collapses everything. Otherwise expand.
        let anyExpanded = false;
        for (const id of docIds) {
            const cur = this.docCollapseTarget.get(id);
            if (cur === 0 || cur === undefined) { anyExpanded = true; break; }
        }
        const newTarget = anyExpanded ? 1 : 0;

        for (const id of docIds) this.docCollapseTarget.set(id, newTarget);
        // Remember the user's explicit global state so transient hovers
        // (search-result mouseenter/leave) restore TO this value rather
        // than their hardcoded default. Without this, hovering then
        // unhovering a result card while everything was globally
        // collapsed left that doc stuck at expanded.
        this._userGlobalCollapse = newTarget;
    },
};
