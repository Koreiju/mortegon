/**
 * cp/interaction.js — Mouse raycasting, hover/select state, node visuals,
 * search glow, and single-node detail fetching.
 *
 * Methods become ChunkProjector instance methods via prototype mixin.
 * THREE is a CDN global.
 */

export const InteractionMixin = {

    getIntersects(event) {
        if (!this.renderer || !this.camera) return [];
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width)  * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top)  / rect.height) * 2 + 1;
        this.raycaster.setFromCamera(this.mouse, this.camera);
        // Two target groups so a click on an image-sprite hits the
        // same nodeId path as a click on the underlying sphere — when
        // a sprite is present we hide the sphere (animate.js scale=0)
        // so the user can only see the billboard, but they still
        // expect hover/click to feel identical.
        const meshTargets   = [this.docInstancedMesh, this.instInstancedMesh].filter(m => m);
        const meshHits      = this.raycaster.intersectObjects(meshTargets);
        const spriteTargets = [];
        if (this._imageSprites) {
            this._imageSprites.forEach(s => { if (s && s.visible) spriteTargets.push(s); });
        }
        if (this._extraSprites) {
            this._extraSprites.forEach(arr => {
                if (!arr) return;
                arr.forEach(s => { if (s && s.visible) spriteTargets.push(s); });
            });
        }
        const spriteHits = spriteTargets.length
            ? this.raycaster.intersectObjects(spriteTargets, false)
            : [];
        const all = meshHits.concat(spriteHits).sort((a, b) => a.distance - b.distance);

        return all.map(hit => {
            let nodeId = null;
            if (hit.object === this.docInstancedMesh) {
                nodeId = this._docInstanceIdToNode[hit.instanceId];
            } else if (hit.object === this.instInstancedMesh) {
                nodeId = this._instInstanceIdToNode[hit.instanceId];
            } else if (hit.object && hit.object.userData && hit.object.userData.id) {
                // Sprites stash their owning node id in userData.id —
                // see cp/sprite_manager.js buildSprite. Hover / click
                // on the sprite resolves to the same node as the
                // hidden sphere would have.
                nodeId = hit.object.userData.id;
            }
            return { nodeId, point: hit.point, distance: hit.distance };
        }).filter(h => h.nodeId);
    },

    onMouseMove(event) {
        const intersects = this.getIntersects(event);
        if (intersects.length > 0) {
            const nodeId = intersects[0].nodeId;
            if (this.hoveredId !== nodeId) {
                if (this.hoveredId && this.hoveredId !== this.selectedId) this.restoreNodeVisuals(this.hoveredId);
                this.hoveredId = nodeId;
                document.body.style.cursor = 'pointer';
                if (nodeId !== this.selectedId) {
                    const entry = this.nodeInstanceMap.get(nodeId);
                    if (entry) this._setInstanceColor(nodeId, entry.originalColor.clone().multiplyScalar(1.5));
                }
                // W8 / MORTEGON §1.3 — multi-pin support: the hover
                // billboard is always live, even when a pinned panel
                // exists for the same node. Each click adds ANOTHER
                // pinned panel; the hover preview continues to follow
                // the mouse so the user can preview a sibling and pin
                // it as a second copy. The previous `hasPinned` gate
                // prevented this by hiding the hover billboard once
                // any pin existed — a regression against §1.3.
                const data = this.dataMap.get(nodeId);
                this.showBillboard(data, false);
                // billboard.md §6/§7 — mirror the 3D-chunk hover + its screen
                // rect so the UI-state (REPL/peer-tab/agent) tracks it, and the
                // next pin() defaults its stick_rect to this hover rect.
                this._mirrorUi('/api/ui/hover', { node_id: nodeId });
                const _bb = document.getElementById('billboard');
                if (_bb) {
                    const _r = _bb.getBoundingClientRect();
                    this._mirrorUi('/api/ui/hover_rect', { rect: { top: _r.top, left: _r.left, width: _r.width, height: _r.height } });
                }
                if (data && !data.is_document && data.html_raw === undefined)
                    this.fetchNodeDetails(nodeId, false);
            }
        } else if (this.hoveredId) {
            if (this.hoveredId !== this.selectedId) this.restoreNodeVisuals(this.hoveredId);
            this.hideBillboard();
            this.hoveredId = null;
            document.body.style.cursor = 'default';
            this._mirrorUi('/api/ui/hover', { node_id: null });  // mirror hover-clear
        }
    },

    async onClick(event) {
        if (this.isDragging) return;
        // H1 / §P.10 — a click on the compute-graph BISECTOR node opens/closes
        // the 2D graph in the editor. Raycast the isolated overlay pickables
        // first; on a hit, fire a decoupled event and stop (don't also pin a
        // chunk). Guarded so a missing overlay is a no-op.
        if (this._cgPickables && this._cgPickables.length && this.renderer && this.camera) {
            try {
                const rect = this.renderer.domElement.getBoundingClientRect();
                this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
                this.raycaster.setFromCamera(this.mouse, this.camera);
                const cgHits = this.raycaster.intersectObjects(this._cgPickables, false);
                const obj = cgHits.length ? cgHits[0].object : null;
                if (obj && obj.userData && obj.userData.computeGraphId) {
                    window.dispatchEvent(new CustomEvent('wfh:open-compute-graph',
                        { detail: { graphId: obj.userData.computeGraphId } }));
                    return;
                }
            } catch (_) { /* overlay raycast is best-effort */ }
        }
        const intersects = this.getIntersects(event);
        if (intersects.length > 0) {
            await this.selectNode(intersects[0].nodeId);
        } else {
            const input       = document.getElementById('nl-search');
            const searchActive = !!(input && input.value.trim());
            this.selectedId = null;
            if (!searchActive) this.searchResults = null;
            this.hideBillboard();
            this.nodeInstanceMap.forEach((_, id) => this.restoreNodeVisuals(id));
            this.applyWorkspaceVisibility();
        }
    },

    /**
     * Find a chunk on this doc that looks like the page's search
     * field — surfaced when the user clicks the URL's root hub so
     * the click-and-stick card carries the page's primary
     * interactive control rather than a generic empty payload.
     *
     * Detection is heuristic but cheap: a chunk whose
     * content_fields_full contains an `@type` of "search" / a key
     * matching `*search*`, OR whose html_raw mentions `<input
     * type="search"` / `role="search"`. Falls back to the chunk
     * with the highest text-field count if no obvious search input
     * is present. Returns a small {chunk_id, xpath, fields, snippet}
     * descriptor or null if the doc has no chunks yet.
     */
    _findUrlSearchChunk(docData) {
        if (!docData) return null;
        const docId = docData.id;
        const url   = docData.url || (docId && docId.startsWith('doc_') ? docId.slice(4) : '');
        let best = null;
        let bestScore = -1;
        this.dataMap.forEach((chunk) => {
            if (!chunk || chunk.is_document) return;
            if (chunk.doc_id !== docId && chunk.url !== url) return;
            const fields = chunk.fields || chunk.content_fields_full || {};
            const html   = chunk.html_raw || '';
            let score = 0;
            for (const k in fields) {
                const v = fields[k];
                if (typeof v !== 'string') continue;
                if (/search/i.test(k)) score += 3;
                if (/@type$/i.test(k) && /search/i.test(v)) score += 5;
                if (/@role$/i.test(k) && /search/i.test(v)) score += 4;
                if (/@aria-label$/i.test(k) && /search/i.test(v)) score += 2;
            }
            if (/<input[^>]*type=["']?search/i.test(html))   score += 6;
            if (/role=["']?search/i.test(html))               score += 4;
            if (/<form[^>]*search/i.test(html))               score += 2;
            if (score > bestScore) {
                bestScore = score;
                best = chunk;
            }
        });
        if (!best || bestScore <= 0) return null;
        return {
            chunk_id:       best.chunk_id || best.id,
            xpath:          best.absolute_xpath || '',
            fields:         best.fields || best.content_fields_full || {},
            rendered_text:  (best.rendered_text || '').slice(0, 300),
            score:          bestScore,
        };
    },

    restoreNodeVisuals(nodeId) {
        const entry = this.nodeInstanceMap.get(nodeId);
        if (!entry) return;
        let color = entry.originalColor.clone();
        if (this.searchResults && this.searchResults.has(nodeId))
            color.lerp(new THREE.Color(1, 1, 1), this.searchResults.get(nodeId) * 0.4);
        this._setInstanceTransform(nodeId, 1.0, color);
    },

    async selectNode(id) {
        const data    = this.dataMap.get(id);
        const prevId  = this.selectedId;

        // billboard.md §6 — click is the freeze-at-rect PIN. Capture the hover
        // billboard's current screen rect and mirror the pin to the UI-state so
        // the REPL viewer, peer tabs, and agent perception see it (this was the
        // 3D-chunk path's missing mirror; the 2D card path already posts hover).
        try {
            // single-left-click = select (edit focus) AND click-and-stick pin.
            this._mirrorUi('/api/ui/select', { node_id: id });
            const _bb = document.getElementById('billboard');
            const _r  = (_bb && _bb.style.display !== 'none') ? _bb.getBoundingClientRect() : null;
            this._mirrorUi('/api/ui/pin', {
                node_id: id,
                stick_rect: _r ? { top: _r.top, left: _r.left, width: _r.width, height: _r.height } : null,
            });
        } catch (_) {}

        // ── Document hub: toggle collapse + pin unified panel ──
        // Per Mortegon §4.1, doc-hub clicks must use the SAME unified
        // knowledge panel as chunk clicks — there is no separate
        // "root URL summary" concept card (the previous spawn here
        // produced a wrong-shaped panel with stringified JSON that
        // the user explicitly rejected). The doc-hub variant of
        // _renderPanelBody (cp/billboard.js) synthesises the
        // {URL, chunk_count, detected search chunk} content.
        if (data && data.is_document) {
            const cur = this.docCollapseTarget.get(id) || 0;
            this.docCollapseTarget.set(id, cur ? 0 : 1);
            // §8D.18 — mirror the collapse toggle so peer tabs + REPL track it.
            this._mirrorUi('/api/ui/collapse', { node_id: id, collapsed: !cur });

            if (prevId && prevId !== id) {
                const prevData = this.dataMap.get(prevId);
                if (prevData && prevData.is_document) {
                    this.docCollapseTarget.set(prevId, 0);
                }
                this.restoreNodeVisuals(prevId);
            }

            // Pin the unified panel for this doc-hub at the hover
            // billboard's current screen rect (pinBillboard handles
            // the rect freeze via getBoundingClientRect() on
            // #billboard). The pinned panel is the canonical
            // click-and-stick widget; the hover billboard hides
            // after pinning so the user can hover other nodes.
            this.selectedId = id;
            const entry = this.nodeInstanceMap.get(id);
            if (entry) {
                const hlColor = entry.originalColor.clone().lerp(new THREE.Color(1, 1, 1), 0.3);
                this._setInstanceTransform(id, 1.5, hlColor);
            }
            if (typeof this._pinDataAsPanel === 'function') this._pinDataAsPanel(id);
            else if (typeof this.pinBillboard === 'function') {
                const css = entry ? '#' + entry.originalColor.getHexString() : '#b8c0c8';
                const txt = entry ? this.getContrastYIQ(entry.originalColor) : '#fff';
                this.pinBillboard(data, css, txt);
            }
            return;
        } else if (prevId && prevId !== id) {
            // Switching from one instance node to another — just restore visuals.
            this.restoreNodeVisuals(prevId);
        }

        this.selectedId = id;
        const entry = this.nodeInstanceMap.get(id);
        if (entry) {
            const hlColor = entry.originalColor.clone().lerp(new THREE.Color(1, 1, 1), 0.3);
            this._setInstanceTransform(id, 1.5, hlColor);
        }

        if (data && data.is_document) { this.hideBillboard(); return; }
        // Click-and-stick ONLY. We deliberately do NOT call
        // `showBillboard` here — that's the legacy hover-preview
        // single-billboard widget that used to pop up beside chunk
        // panels and confused the user with two simultaneous knowledge
        // panels on every click. The concept-card spawned by
        // _pinDataAsPanel (which lives on the 2D editor surface with
        // the full chunk summary) is the canonical click-and-stick
        // panel; the hover billboard is reserved for transient
        // mouse-over previews only.
        if (data) this.hideBillboard();
        if (data && !data.is_document) {
            if (typeof this._pinDataAsPanel === 'function') this._pinDataAsPanel(id);
            else if (typeof this.pinBillboard === 'function') {
                const entryHere = this.nodeInstanceMap.get(id);
                const css = entryHere ? '#' + entryHere.originalColor.getHexString() : '#b8c0c8';
                const txt = entryHere ? this.getContrastYIQ(entryHere.originalColor) : '#fff';
                this.pinBillboard(data, css, txt);
            }
        }
        if (data && !data.is_document && data.html_raw === undefined)
            await this.fetchNodeDetails(id, true);
    },

    applySearchGlow(nodeId, score) {
        const entry = this.nodeInstanceMap.get(nodeId);
        if (!entry) return;
        const color = entry.originalColor.clone().lerp(new THREE.Color(1, 1, 1), score * 0.4);
        this._setInstanceTransform(nodeId, 1 + score * 0.3, color);
    },

    async fetchNodeDetails(id, isLocked = false) {
        if (this.detailsFetchQueue.has(id)) return;
        this.detailsFetchQueue.add(id);
        try {
            const res = await fetch(`/api/chunk_details/${encodeURIComponent(id)}`);
            if (res.ok) {
                const details = await res.json();
                const cached  = this.dataMap.get(id);
                if (cached) {
                    const merged = { ...cached, ...details };
                    this.dataMap.set(id, merged);
                    if ((this.hoveredId === id && !this.selectedId) || this.selectedId === id)
                        this.showBillboard(merged, isLocked || this.selectedId === id);
                }
            }
        } catch (e) {
            console.warn('[ChunkProjector] details fetch failed', e);
        } finally {
            this.detailsFetchQueue.delete(id);
        }
    },

    update3DVisualsFromResults(results) {
        this.nodeInstanceMap.forEach((entry, id) => {
            if (id !== this.selectedId)
                this._setInstanceTransform(id, 1.0, entry.originalColor.clone().multiplyScalar(0.15));
        });
        this.searchResults = new Map();
        results.forEach(r => {
            this.searchResults.set(r.id, r.score);
            if (r.id !== this.selectedId) this.applySearchGlow(r.id, r.score);
        });
    },

    // billboard.md §6/§7 — mirror 3D-chunk hover/pin to the UI-state so the REPL
    // viewer, peer tabs, and agent perception see the billboard the same way
    // they already see 2D concept-card hover/pin (concept_graph.js posts these).
    /**
     * §6.6.5 / §7.3.5 (Q.3-Q.5) — right-click a node in the 3D projector to
     * toggle its generalized rank-dominance collapse/isolate. Resolves the
     * dominator (the node's root URL for a chunk/doc-hub) and POSTs the same
     * `/api/ui/dominance_collapse` gesture the REPL `ui-dominance-collapse`
     * action fires — so the GUI right-click mirrors into the REPL viewer, and
     * the backend's broadcast reflects back here (scanner.js ui_state_changed).
     * Applies the response immediately for zero-latency feedback.
     */
    async onContextMenu(event) {
        if (event && typeof event.preventDefault === 'function') event.preventDefault();
        const intersects = this.getIntersects(event);
        if (!intersects.length) return;
        const nodeId = intersects[0].nodeId;
        const data   = this.dataMap.get(nodeId);
        // Dominator key: a chunk/doc-hub collapses onto its ROOT URL
        // (the user's "right-click a root url node" — Q.3). Fall back to
        // the node id itself for non-url nodes (e.g. a compute node).
        const dominator = (data && data.url) ? data.url : nodeId;
        if (!this._dominanceToggle) this._dominanceToggle = new Map();
        const next = !this._dominanceToggle.get(dominator);
        this._dominanceToggle.set(dominator, next);
        try {
            const res = await fetch('/api/ui/dominance_collapse', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workspace_id: this._conceptWorkspaceId ||
                        (typeof window !== 'undefined' && window._activeWorkspaceId) || '',
                    node_id: dominator,
                    collapsed: next,
                }),
            });
            const out = await res.json().catch(() => ({}));
            // Apply the authoritative membership immediately (the WS
            // broadcast will also land via scanner.js, idempotently).
            const dom = (out && out.dominance_collapse) || {};
            const hide = new Set();
            const keep = new Set();
            for (const k in dom) {
                const e = dom[k];
                if (!e || !e.collapsed) continue;
                keep.add(k);
                (e.folded_set || []).forEach(id => hide.add(String(id)));
                (e.hidden_set || []).forEach(id => hide.add(String(id)));
            }
            keep.forEach(k => hide.delete(String(k)));
            this._dominanceHiddenChunkIds = hide;
            this._dominanceActive = keep.size > 0;
            this.setScanStatus(
                next ? `collapsed ${String(dominator).slice(0, 48)} — ${hide.size} nodes hidden (right-click again to expand)`
                     : `expanded ${String(dominator).slice(0, 48)}`,
                '#b8c0c8');
        } catch (e) {
            console.warn('[interaction] dominance_collapse failed:', e && e.message);
        }
    },

    _mirrorUi(path, body) {
        try {
            fetch(path, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workspace_id: this._conceptWorkspaceId || (typeof window !== 'undefined' && window._activeWorkspaceId) || '',
                    ...body,
                }),
            }).catch(() => {});
        } catch (_) {}
    },
};
