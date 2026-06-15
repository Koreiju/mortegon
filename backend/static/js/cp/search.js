/**
 * cp/search.js — Right sidebar (#rs-latch), NL search input, search result
 * rendering, page-card HTML helpers, and per-URL chunk drilldown.
 *
 * Methods become ChunkProjector instance methods via prototype mixin.
 */

export const SearchMixin = {

    // §S.3 (2026-06-12) — the retrieval SIDEBAR is DEPRECATED (anti-pattern).
    // In-editor halo queries with ray projections (§8.2 / DOMAIN_MODEL §4.1.2)
    // subsume it: retrieval radiates proximal to the focal concept node the
    // user is composing, so there is no separate side panel to scroll.
    // `initSidebar` now RETIRES the surface: it hides the `#sidebar` /
    // `#history-sidebar` DOM and does NOT build the `#rs-latch` toggle. The
    // retrieval BACKEND stays — `triggerSearch` / `renderSearchResults` /
    // `clearSearch` below remain callable (the halo path and any
    // programmatic search still work); only the sidebar UI surface is gone.
    initSidebar() {
        // Retire the sidebar surfaces if the template still carries them.
        for (const id of ['sidebar', 'history-sidebar']) {
            const el = document.getElementById(id);
            if (el) { el.style.display = 'none'; el.dataset.deprecatedS3 = 'true'; }
        }
        // Defensively remove any stale toggle from a prior build.
        const stale = document.getElementById('rs-latch');
        if (stale && stale.parentNode) stale.parentNode.removeChild(stale);
        // No `#rs-latch`, no `#nl-search` binding — retrieval is the in-editor
        // halo (§8.2). Intentionally a no-op beyond hiding the legacy surface.
    },

    clearSearch() {
        this.searchResults    = null;
        this.lastSearchPayload = null;
        this.selectedId       = null;
        this.hideBillboard();
        this.nodeInstanceMap.forEach((_, id) => this.restoreNodeVisuals(id));
        // Stop the expanding-spine observer and clear all per-chunk
        // overrides so chunks resume following their doc's collapse
        // state (which is whatever the user last set globally).
        this._teardownSpineObserver();
        if (this.chunkCollapseTarget) this.chunkCollapseTarget.clear();
        if (this.chunkCollapseState)  this.chunkCollapseState.clear();
        this.renderUrlBuckets();
    },

    /**
     * Start an IntersectionObserver over ``.instance-row`` elements
     * inside the search results panel. Each row carries
     * ``data-id="<instance_id>"`` — when the row enters the visible
     * scroll area, set the chunk's per-collapse override to 0 so the
     * sphere pops out of its hub; when it leaves, set the override to
     * 1 so the sphere folds back. The result is a 1:1 "expanding spine"
     * mapping between which results are visible in the 2D scroll list
     * and which spheres are exposed in the 3D scene.
     *
     * The 200px rootMargin on top/bottom pre-pops rows just before they
     * scroll into the visible band so the user never sees an empty band
     * of un-popped chunks during fast scrolling. The threshold is 0.1
     * so partial visibility still counts.
     */
    _setupSpineObserver(container) {
        this._teardownSpineObserver();
        if (!container) return;
        if (!this.chunkCollapseTarget) this.chunkCollapseTarget = new Map();
        const ROW_SELECTOR = '.instance-row';
        try {
            const io = new IntersectionObserver((entries) => {
                const popped = [];
                const folded = [];
                for (const ent of entries) {
                    const id = ent.target.getAttribute('data-id');
                    if (!id) continue;
                    if (ent.isIntersecting) {
                        // Pop out: target 0 means "at canonical position"
                        this.chunkCollapseTarget.set(id, 0);
                        popped.push(id);
                    } else {
                        // Fold back into the hub.
                        this.chunkCollapseTarget.set(id, 1);
                        folded.push(id);
                    }
                }
                // W28 — broadcast the visible-row delta over the
                // workspace WS so the backend (and any meta-cognition
                // node reading EnvState) can correlate retrieval with
                // current viewport. Debounced 150 ms so a fast scroll
                // collapses into one POST.
                if (this._workspaceWs && this._workspaceWs.readyState === 1) {
                    if (this._spinePendingDelta == null) {
                        this._spinePendingDelta = { popped: new Set(), folded: new Set() };
                    }
                    popped.forEach(id => {
                        this._spinePendingDelta.popped.add(id);
                        this._spinePendingDelta.folded.delete(id);
                    });
                    folded.forEach(id => {
                        this._spinePendingDelta.folded.add(id);
                        this._spinePendingDelta.popped.delete(id);
                    });
                    if (this._spineBroadcastTimer) clearTimeout(this._spineBroadcastTimer);
                    this._spineBroadcastTimer = setTimeout(() => {
                        if (!this._spinePendingDelta) return;
                        try {
                            this._workspaceWs.send(JSON.stringify({
                                type: 'spine_delta',
                                workspace_id: this._conceptWorkspaceId || '_default',
                                popped: Array.from(this._spinePendingDelta.popped),
                                folded: Array.from(this._spinePendingDelta.folded),
                            }));
                        } catch (_) { /* ignore */ }
                        this._spinePendingDelta = null;
                    }, 150);
                }
                // §8D.18.1 strict-spine — ALSO mirror the visible-row set to the
                // UI-state (REST /api/ui/viewport_spine) so the REPL
                // watch-activity "visible 3D" row, peer tabs, and
                // viewport_visible_rows reflect the scroll-driven spine even when
                // the workspace WS isn't connected. Debounced like spine_delta.
                if (this._vpSpineTimer) clearTimeout(this._vpSpineTimer);
                this._vpSpineTimer = setTimeout(() => {
                    const ordered = [];
                    this.chunkCollapseTarget.forEach((v, k) => { if (v === 0) ordered.push(k); });
                    if (typeof this._mirrorUi === 'function')
                        this._mirrorUi('/api/ui/viewport_spine', { ordered, total: this.chunkCollapseTarget.size });
                }, 150);
            }, { root: container, rootMargin: '200px 0px', threshold: 0.1 });
            container.querySelectorAll(ROW_SELECTOR).forEach(row => io.observe(row));
            this._spineObserver = io;
            // Seed every visible row's chunk as folded (target=1) so
            // the observer's "intersecting" callback drives a clear
            // 1 → 0 lerp instead of starting half-popped from a stale
            // previous state.
            container.querySelectorAll(ROW_SELECTOR).forEach(row => {
                const id = row.getAttribute('data-id');
                if (id && !this.chunkCollapseTarget.has(id)) {
                    this.chunkCollapseTarget.set(id, 1);
                }
            });
        } catch (e) {
            console.warn('[ChunkProjector] IntersectionObserver unsupported, skipping spine effect', e);
        }
    },

    _teardownSpineObserver() {
        if (this._spineObserver) {
            try { this._spineObserver.disconnect(); } catch (_) {}
            this._spineObserver = null;
        }
    },

    async triggerSearch(query, ts, stillFreshest, urlFilter = null) {
        const container = document.getElementById('results-container');
        if (container) container.innerHTML = '<div class="empty-state">Searching...</div>';

        const activeUrls = new Set();
        this.nodeInstanceMap.forEach((entry, id) => {
            const data = this.dataMap.get(id);
            if (data && data.url) activeUrls.add(data.url);
        });

        try {
            const res = await fetch('/api/chunk_search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query,
                    urls: urlFilter ? urlFilter : Array.from(activeUrls),
                    page_limit: urlFilter ? 1 : 10,
                    instance_limit_per_page: 50,
                }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (stillFreshest && stillFreshest() !== ts) return;
            this.lastSearchPayload = data;
            this.renderSearchResults(data, urlFilter);
        } catch (e) {
            console.error('[ChunkProjector] search failed', e);
            if (container) container.innerHTML = `<div class="empty-state">Search failed: ${this.escape(e.message)}</div>`;
        }
    },

    renderSearchResults(payload, activeUrlFilter = null) {
        const container = document.getElementById('results-container');
        if (!container) return;
        const pages = payload.pages || [];
        if (pages.length === 0) {
            container.innerHTML = '<div class="empty-state">No matches.</div>';
            this.searchResults = null;
            this._activeSearchInstanceIds = null;  // stop auto-uncollapsing
            this.nodeInstanceMap.forEach((_, id) => this.restoreNodeVisuals(id));
            return;
        }

        if (activeUrlFilter && pages.length > 0) {
            const page     = pages[0];
            const doc_id   = `doc_${page.url}`;
            // Spine observer handles per-chunk pop — no bulk uncollapse
            const headColor = this.avgPageColor(page.instances);
            container.innerHTML = `
                <div class="bucket-heading">
                    <button id="back-to-search" style="margin-right:10px; cursor:pointer; background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.2); color:#fff; padding:2px 8px; border-radius:4px;">&larr; Back</button>
                    Instances on ${this.escape(this.shortenUrl(page.url))}
                </div>
                ${this.pageCardHtml(page, headColor, page.instances.length)}`;
            document.getElementById('back-to-search').onclick = () => {
                this.triggerSearch(payload.query, Date.now(), null, null);
            };
            const flat = [{ id: doc_id, score: page.score }];
            (page.instances || []).forEach(i => {
                flat.push({ id: i.id, score: i.score });
                if (this.dataMap.has(i.id)) this.dataMap.set(i.id, { ...this.dataMap.get(i.id), ...i });
            });
            this.update3DVisualsFromResults(flat);
            this._activeSearchInstanceIds = new Set(flat.map(r => r.id));
            this._wireInstanceRows(container);
            this._setupSpineObserver(container);
        } else {
            const parts = [`<div class="bucket-heading">
                ${pages.length} page${pages.length === 1 ? '' : 's'} &middot; query "${this.escape(payload.query || '')}"
            </div>`];
            pages.forEach(page => {
                const pct      = (page.score * 100).toFixed(1);
                const urlShort = this.shortenUrl(page.url);
                let snippetHtml = '';
                if (page.instances && page.instances.length > 0) {
                    const snippets = page.instances.slice(0, 3).map(inst => {
                        if (inst.rendered_text) {
                            const text = this.escape(inst.rendered_text.slice(0, 120)) + (inst.rendered_text.length > 120 ? '...' : '');
                            return `<div style="font-size:11px;color:#9ca3af;margin-top:4px;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;">&bull; "${text}"</div>`;
                        }
                        return '';
                    }).join('');
                    if (snippets) snippetHtml = `<div style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.1);padding-top:4px;">${snippets}</div>`;
                }
                const dataUrl = this.escape(page.url);
                // No inline onclick — we wire the click handler below
                // via addEventListener so it can run the full sequence
                // (fly + pin + drill-in) instead of just drilling.
                parts.push(`
                    <div class="page-card" data-url="${dataUrl}" data-query="${this.escape(payload.query || '')}" style="cursor:pointer;border-left:4px solid var(--accent-pastel,#88c0d0);margin-bottom:8px;padding:10px;background:var(--surface-elevated,#2e3440);border-radius:4px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <span title="${this.escape(page.url)}" style="font-weight:bold;color:#fff;">${this.escape(urlShort)}</span>
                            <span style="color:#9ca3af;">${pct}%</span>
                        </div>
                        ${snippetHtml}
                    </div>`);
            });
            container.innerHTML = parts.join('');

            container.querySelectorAll('.page-card').forEach(card => {
                const pageUrl = card.dataset.url;
                const docId   = `doc_${pageUrl}`;
                const query   = card.dataset.query;
                card.addEventListener('mouseenter', () => {
                    this.hoveredId = docId;
                    // Highlight the hub sphere.
                    const entry = this.nodeInstanceMap.get(docId);
                    if (entry && docId !== this.selectedId)
                        this._setInstanceColor(docId, entry.originalColor.clone().multiplyScalar(1.5));
                    // Per Mortegon §4.1: the same unified hover
                    // billboard shows for search-row hovers as for
                    // 3D node hovers — no separate "root summary."
                    const docData = this.dataMap.get(docId);
                    if (docData && !this._pinnedPanels.has(docId)) {
                        this.showBillboard(docData, false);
                    }
                    // Intentionally NO docCollapseTarget mutation here.
                    // Hovering a page card used to expand the whole URL,
                    // which violated the user's "only what's visible
                    // pops out" rule for the scroll-spine. Hub colour
                    // highlight stays (above) so the hover still feels
                    // tangible without snapping spheres outward.
                });
                card.addEventListener('mouseleave', () => {
                    if (this.hoveredId === docId) this.hoveredId = null;
                    if (docId !== this.selectedId) this.restoreNodeVisuals(docId);
                    // Hide the hover preview if it's showing this card's content.
                    if (!this.selectedId || this.selectedId === docId) this.hideBillboard();
                });
                card.addEventListener('click', () => {
                    // 1) Fly to the doc-hub so the user immediately
                    //    sees which cluster the result belongs to.
                    if (typeof this.flyToNode === 'function') this.flyToNode(docId);
                    // 2) Spawn the click-and-stick concept card for
                    //    this URL hub. selectNode → interaction.js
                    //    builds the root-URL payload (url, chunk_count,
                    //    search_chunk, …) and hands it to
                    //    spawnConceptFromValue. The concept card lands
                    //    on the 2D editor layer.
                    if (typeof this.selectNode === 'function') this.selectNode(docId);
                    // 3) Drill in to the per-URL instance list, same
                    //    as the previous inline onclick used to do.
                    this.triggerSearch(query || '', Date.now(), null, [pageUrl]);
                });
            });

            const flat = [];
            pages.forEach(p => {
                const doc_id = `doc_${p.url}`;
                // Intentionally do NOT auto-expand the doc here. The
                // expanding-spine observer below pops out *individual
                // chunks* per scroll position, so the hub-level state
                // should remain whatever the user set globally (usually
                // collapsed). This is the "scroll over results pops the
                // visible ones out of the hub" behaviour the user spec'd.
                flat.push({ id: doc_id, score: p.score });
                (p.instances || []).forEach(i => {
                    flat.push({ id: i.id, score: i.score });
                    if (this.dataMap.has(i.id)) this.dataMap.set(i.id, { ...this.dataMap.get(i.id), ...i });
                });
            });
            this.update3DVisualsFromResults(flat);
            // Remember the active result set so the streaming pipeline
            // can auto-uncollapse late-arriving matches (see
            // scanner.js chunk_instances_partial handler).
            this._activeSearchInstanceIds = new Set(flat.map(r => r.id));
            // Wire the scroll → 3D pop-out observer once the rows
            // exist in the DOM. Each rendered .instance-row maps 1:1
            // to a chunk sphere; the observer drives that chunk's
            // collapse override based on viewport intersection inside
            // the results-container scroll area.
            this._setupSpineObserver(container);
        }
    },

    _wireInstanceRows(container) {
        container.querySelectorAll('.instance-row').forEach(row => {
            const id = row.dataset.id;
            row.addEventListener('click', (e) => {
                if (e.target.closest('a')) return;
                const data = this.dataMap.get(id);
                // Per-CHUNK pop instead of doc-wide expand — the user
                // wants only the clicked result's sphere to emerge
                // from its hub, not every chunk of the same URL. The
                // chunkCollapseTarget Map overrides the parent doc's
                // collapse state in the animate loop, so this sphere
                // pops out while its siblings stay folded if the
                // user had collapsed the whole URL.
                if (data && !data.is_document) {
                    if (!this.chunkCollapseTarget) this.chunkCollapseTarget = new Map();
                    this.chunkCollapseTarget.set(id, 0);
                }
                // 1) Mark selected + open the single billboard / pin
                //    a knowledge panel for click-and-stick.
                this.selectNode(id);
                this._pinDataAsPanel(id);
                // 2) Fly the camera. flyToNode now uses init.position
                //    so the destination is the chunk's canonical
                //    un-collapsed location — the chunk lerps out of
                //    its hub while the camera tweens in, arriving
                //    together.
                if (typeof this.flyToNode === 'function') this.flyToNode(id);
            });
            row.addEventListener('mouseenter', () => {
                this.hoveredId = id;
                const entry = this.nodeInstanceMap.get(id);
                if (entry && id !== this.selectedId)
                    this._setInstanceColor(id, entry.originalColor.clone().multiplyScalar(1.5));
                // Per Mortegon §4.1: unified hover billboard for
                // search-row hovers. Skips if this row's chunk is
                // already pinned (the pinned panel sits at the same
                // screen position).
                const rowData = this.dataMap.get(id);
                if (rowData && !this._pinnedPanels.has(id)) {
                    this.showBillboard(rowData, false);
                    if (rowData && !rowData.is_document && rowData.html_raw === undefined) {
                        this.fetchNodeDetails(id, false);
                    }
                }
            });
            row.addEventListener('mouseleave', () => {
                if (this.hoveredId === id) this.hoveredId = null;
                if (id !== this.selectedId) this.restoreNodeVisuals(id);
                if (!this.selectedId || this.selectedId === id) this.hideBillboard();
            });
        });
        // Drilldown view rows need the same scroll-spine pop-out the
        // multi-page view has. The observer covers any .instance-row
        // inside the container; calling it here wires the drilldown
        // rows too. Idempotent — _setupSpineObserver tears down any
        // prior observer first.
        if (typeof this._setupSpineObserver === 'function') {
            this._setupSpineObserver(container);
        }
    },

    /**
     * Shared helper for search-row + page-card clicks: pull current
     * dataMap entry, derive the sphere's color, hand off to pinBillboard.
     * Idempotent — if a panel already exists for this id it stays put
     * (pinBillboard raises its z-index and un-minimises it).
     */
    _pinDataAsPanel(id) {
        const data  = this.dataMap.get(id);
        if (!data) return;
        const entry = this.nodeInstanceMap.get(id);
        let cssColor  = '#b8c0c8';
        let textColor = '#ffffff';
        if (entry && entry.originalColor) {
            cssColor  = '#' + entry.originalColor.getHexString();
            textColor = this.getContrastYIQ(entry.originalColor);
        }
        // pinBillboard tolerates partial data; details lazy-load below.
        this.pinBillboard(data, cssColor, textColor);
        // If the panel just got created and the chunk hasn't fetched its
        // html_raw / fields yet, kick off the lazy details fetch so the
        // panel body fills in shortly after pinning.
        if (data && !data.is_document && data.html_raw === undefined &&
                typeof this.fetchNodeDetails === 'function') {
            this.fetchNodeDetails(id, true);
        }
    },

    pageCardHtml(page, headColor, limit = 50) {
        const insts = (page.instances || []).slice(0, limit);
        const rows  = insts.map(i => {
            const entry = this.nodeInstanceMap.get(i.id);
            const chip  = entry ? `<span class="node-color-chip" style="background:#${entry.originalColor.getHexString()}"></span>` : '';
            const textSnippet = i.rendered_text ? this.escape(i.rendered_text.slice(0, 300)) : '';
            const textDisplay = i.rendered_text !== undefined
                ? (textSnippet || '<span style="color:#6b7280;font-style:italic;">(no text)</span>')
                : '<span style="color:#6b7280;font-style:italic;">Click node to load contents...</span>';
            const xpathDisplay = i.absolute_xpath ? this.escape(this.shortenXpath(i.absolute_xpath)) : 'Chunk Instance';
            return `
                <div class="instance-row" data-id="${this.escape(i.id)}">
                    <div class="instance-row-head">
                        ${chip}
                        <span class="instance-score">${(i.score * 100).toFixed(1)}%</span>
                        <span class="instance-xpath" title="${this.escape(i.absolute_xpath || '')}">${xpathDisplay}</span>
                    </div>
                    <div class="instance-text">${textDisplay}</div>
                </div>`;
        }).join('');
        return `
            <div class="page-card" style="border-left:4px solid ${headColor}">
                <div class="page-card-head">
                    <a class="page-url" href="${this.escape(page.url)}" target="_blank" title="${this.escape(page.url)}">${this.escape(this.shortenUrl(page.url))}</a>
                    <span class="page-score">${(page.score * 100).toFixed(1)}%</span>
                </div>
                <div class="page-meta">${page.instance_count} instance(s) on page</div>
                <div class="instance-list">${rows}</div>
            </div>`;
    },

    showChunksForUrl(url, items) {
        const container = document.getElementById('results-container');
        if (!container) return;
        const doc_id = `doc_${url}`;
        // Per Mortegon §4.2: do NOT auto-uncollapse the entire URL.
        // The spine observer below will pop out only the chunks whose
        // rows are currently visible in the scroll viewport. This
        // prevents the "all nodes explode outward" bug.
        const flat = items.map(i => ({ id: i.id, score: 1.0 }));
        flat.push({ id: doc_id, score: 1.0 });
        this.update3DVisualsFromResults(flat);
        this._activeSearchInstanceIds = new Set(flat.map(r => r.id));

        const page = {
            url, score: 1.0, instance_count: items.length,
            instances: items.map(i => {
                if (this.dataMap.has(i.id)) this.dataMap.set(i.id, { ...this.dataMap.get(i.id), ...i });
                return { id: i.id, score: 1.0, absolute_xpath: i.absolute_xpath, html_raw: i.html_raw, rendered_text: i.rendered_text };
            }),
        };
        const headColor = this.avgPageColor(page.instances);
        container.innerHTML = `
            <div class="bucket-heading">
                <button id="back-to-buckets" style="margin-right:10px;cursor:pointer;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);color:#fff;padding:2px 8px;border-radius:4px;">&larr; Back</button>
                ${items.length} chunks on ${this.escape(this.shortenUrl(url))}
            </div>
            ${this.pageCardHtml(page, headColor, items.length)}`;
        document.getElementById('back-to-buckets').addEventListener('click', () => this.clearSearch());
        this._wireInstanceRows(container);
        this._setupSpineObserver(container);
    },

    avgPageColor(instances) {
        let r = 0, g = 0, b = 0, n = 0;
        (instances || []).forEach(i => {
            const entry = this.nodeInstanceMap.get(i.id);
            if (entry) { const c = entry.originalColor; r += c.r; g += c.g; b += c.b; n++; }
        });
        if (n === 0) return '#b8c0c8';
        return `#${new THREE.Color(r / n, g / n, b / n).getHexString()}`;
    },
};
