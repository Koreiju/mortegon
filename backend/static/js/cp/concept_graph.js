/**
 * cp/concept_graph.js — 2D Concept-Graph Editor woven into the main UI.
 *
 * Direct, in-place port of backend/concept_builder/concept_graph_builder.html
 * brought into the live 3D app as a permanently-present 2D layer. There
 * is no toggle: concept cards float over the 3D scene the same way
 * pinned chunk panels do (§cp/billboard.js pinBillboard); the SVG layer
 * that draws the (solid, §O.16) edges between them lives full-screen above
 * the projector canvas with pointer-events disabled so it never interferes
 * with raycasting or orbit controls.
 *
 * The empty primitive spawns once on app init (matches the template's
 * `addNode('', 250, 180)` on page load). Every other detail of the
 * template is preserved verbatim:
 *
 *   • Slug rules: trim → lowercase → non-[a-z0-9_] → underscore →
 *     collapse → strip leading/trailing.
 *   • escapeHtml escapes only &, <, >, " (NOT apostrophe).
 *   • addNode semantics: empty name ⇒ timestamp id and
 *     `node.name = id`; named ⇒ slug as id; duplicate id ⇒ silent null.
 *   • The card markup is the same five-section anatomy
 *     (name input + delete / description / value / compiled-preview /
 *      compile button) with `concept-` class prefixes.
 *   • Drag exclusion list: INPUT, TEXTAREA, BUTTON, SELECT — exact.
 *   • Reference parser: same matchAll regex `/\{([^}]+)\}/g`, same
 *     auto-create at (source.x + 290, source.y + 50 + rand*60),
 *     "Auto‑created from {name}" description on the spawn, same
 *     setTimeout(0) DOM sync, same dedup-add of outgoing edges.
 *   • Stale-edge filter is preserved exactly (the template's filter
 *     compares raw ref strings to slug edge targets, removing nearly
 *     every outgoing edge each parse — the re-add loop right below
 *     restores them, net behaviour is correct). Fidelity over
 *     micro-optimisation.
 *   • Rename propagation rewrites `{oldId}` → `{newId}`
 *     (case-insensitive) in every other node's value AND the live
 *     <textarea>; node.name is always set to the slug at the tail.
 *     One latent template bug fixed: the renamed card's
 *     `data-node-id` attribute is updated so subsequent edge lookups
 *     don't drop the source card silently.
 *   • Compile is recursive substitution with a per-branch
 *     `new Set(visited)` so cycle detection blocks loops while sibling
 *     references stay independent.
 *   • drawEdges uses an `<svg>` with a namespaced `concept-arrow`
 *     marker, SOLID stroke (the template's dashed `4,2` was replaced per
 *     §O.16 / frontend_rendering.md §1.6 — see `_edgeStyleForType`),
 *     center-to-center geometry computed
 *     against the host (in our case `document.body` since the cards
 *     are positioned in viewport coordinates the same way pinned
 *     chunk panels are).
 *   • 120ms redraw timer is always-on (the editor is always visible);
 *     the visible-card check prevents busywork when the user never
 *     spawns one.
 *
 * Beyond the template:
 *
 *   • Per-card retrieval: typing into a card's description triggers a
 *     220 ms debounce, computes token-Jaccard similarity vs every
 *     other concept node's name+description+value tokens, and renders
 *     up to 3 clickable suggestion chips below the description input.
 *     Clicking a chip appends `{other_id}` to the value field and
 *     replays the value-input handler so the new edge auto-draws.
 *
 * Concept nodes share NO id-namespace and NO state with 3D env chunk
 * spheres. The two graphs are independent; a future explicit bridge
 * will wire chunks ↔ concept cards.
 */

export const ConceptGraphMixin = {

    // ── Public surface ───────────────────────────────────────────────────────

    initConceptGraph() {
        // Backing stores — independent of every other ChunkProjector state.
        this._conceptNodes    = new Map();   // id → { id, name, description, value, x, y }
        this._conceptEdges    = [];          // [{ source, target }]
        this._conceptSuggestTimers = new Map();

        // W4 / §8D.44 — debounced write-through to backend persistence.
        // Each concept node edit produces a pending sync entry; a
        // ~600ms debounce coalesces rapid keystrokes into one POST.
        // The Map (above) stays the local source of truth for
        // rendering; the backend is the persistent ground truth that
        // survives reload. The two are kept in sync via:
        //   * _hydrateConceptsFromBackend()   on init (this method)
        //   * _scheduleConceptSync(id)        on every local edit
        //   * _flushConceptSync(id)           debounced POST
        this._conceptSyncTimers = new Map();   // concept_id → timeout handle
        this._conceptSyncPending = new Set();  // concept_ids awaiting flush
        this._conceptBackendOk = true;         // disable on persistent errors
        this._conceptWorkspaceId = (this.workspaceId || this.activeWorkspaceId || '');

        // Hydrate from backend (fire-and-forget; if backend isn't up
        // the editor still works in pure local mode).
        this._hydrateConceptsFromBackend().catch(err => {
            console.warn('[concept_graph] backend hydrate failed (local-only mode):', err && err.message);
            this._conceptBackendOk = false;
        });

        // W11 — Subscribe to the workspace WS channel for live frames
        // (concept_index_update, umap_canonical, agent_token,
        // purge_workspace). The connection is long-lived; reconnects
        // happen on close with exponential back-off.
        this._connectWorkspaceWs();

        // W16 / W29 — Keyboard shortcuts.
        //   Ctrl/Cmd+H — Evolution log panel
        //   Ctrl/Cmd+E — Spawn empty primitive (§8D.22)
        //   Ctrl/Cmd+N — Spawn regular new concept
        //   Ctrl/Cmd+Enter — Compile the focused card
        //   Ctrl/Cmd+L — Reload concepts from backend (debug)
        window.addEventListener('keydown', (ev) => {
            const isCmd = ev.ctrlKey || ev.metaKey;
            if (!isCmd) return;
            const k = ev.key.toLowerCase();
            if (k === 'h' && !ev.shiftKey) {
                ev.preventDefault();
                const existing = document.getElementById('wfh-evolution-log-panel');
                if (existing && existing.style.display !== 'none') {
                    existing.style.display = 'none';
                } else {
                    this.showEvolutionLogPanel();
                }
            } else if (k === 'e' && !ev.shiftKey) {
                ev.preventDefault();
                if (typeof this.spawnEmptyPrimitive === 'function') this.spawnEmptyPrimitive();
            } else if (k === 'n' && !ev.shiftKey) {
                // Only intercept if the user isn't typing in a card.
                if (ev.target && (ev.target.tagName === 'INPUT' || ev.target.tagName === 'TEXTAREA')) return;
                ev.preventDefault();
                this.addConceptNode();
            } else if (k === 'enter' && (ev.target && (ev.target.tagName === 'INPUT' || ev.target.tagName === 'TEXTAREA'))) {
                // Ctrl/Cmd+Enter compiles the focused card.
                const card = ev.target.closest && ev.target.closest('.concept-card');
                if (!card) return;
                ev.preventDefault();
                const btn = card.querySelector('.concept-compile-btn');
                if (btn) btn.click();
            } else if (k === 'l' && ev.shiftKey) {
                ev.preventDefault();
                if (typeof this._hydrateConceptsFromBackend === 'function') {
                    this._hydrateConceptsFromBackend().catch(_ => {});
                }
            } else if (k === 'g' && !ev.shiftKey) {
                ev.preventDefault();
                const existing = document.getElementById('wfh-agents-panel');
                if (existing && existing.style.display !== 'none') {
                    existing.style.display = 'none';
                } else {
                    this.showAgentVisibilityPanel();
                }
            }
        });

        // Wire the inline "+ New Concept" trigger that sits in the
        // top toolbar (added to index.html alongside the snapshot
        // button). Concept cards live in viewport coordinates so we
        // host them on document.body — exactly the same parent the
        // logs panel (#wfh-log-box) and pinned chunk panels use.
        const addBtn = document.getElementById('concept-add-btn');
        if (addBtn) {
            addBtn.addEventListener('click', () => this.addConceptNode());
        }

        // H1 / §6.6.4 / §P.10 — the 3D projector's compute-graph BISECTOR
        // node dispatches this when clicked; opening/closing the 2D graph is
        // the projector-side handle for the editor graph (dual of click-and-
        // stick). Toggle the graph card's compile (panel↔graph) if it's
        // present; otherwise record the open in the UI-state mirror so the
        // REPL / peer tabs observe it (telemetry-complete §8).
        if (!this._cgOpenListenerBound) {
            this._cgOpenListenerBound = true;
            window.addEventListener('wfh:open-compute-graph', (ev) => {
                const gid = ev && ev.detail && ev.detail.graphId;
                if (!gid) return;
                const card = document.querySelector(`.concept-card[data-node-id="${gid}"]`);
                if (card) {
                    card.style.zIndex = String((this._cardZ = (this._cardZ || 1000) + 1));
                    const btn = card.querySelector('.concept-compile-btn');
                    if (btn) btn.click();   // panel↔graph (§7.3.4)
                } else if (typeof this._mirrorUi === 'function') {
                    this._mirrorUi('/api/ui/compile_expand', { central_id: gid });
                }
            });
        }

        // W20 / §8D.22 — Empty primitive button.
        const emptyBtn = document.getElementById('empty-primitive-btn');
        if (emptyBtn) {
            emptyBtn.addEventListener('click', () => this.spawnEmptyPrimitive());
        }

        const umapBtn = document.getElementById('umap-recompute-btn');
        if (umapBtn) {
            umapBtn.addEventListener('click', async () => {
                const total = (this._chunkIdToInstances && this._chunkIdToInstances.size) || 0;
                if (total < 8) {
                    if (typeof this.setScanStatus === 'function') {
                        this.setScanStatus(`UMAP needs ≥ 8 chunks (have ${total})`, '#b25b5b');
                    }
                    return;
                }
                if (this._umapInFlight) {
                    if (typeof this.setScanStatus === 'function') {
                        this.setScanStatus('UMAP already running…', '#eef0f2');
                    }
                    return;
                }
                umapBtn.disabled = true;
                umapBtn.style.opacity = '0.6';
                try {
                    if (typeof this._runUmapAsync === 'function') {
                        await this._runUmapAsync(total);
                    }
                } finally {
                    umapBtn.disabled = false;
                    umapBtn.style.opacity = '';
                }
            });
        }

        // Ensure the edges-layer SVG exists. If index.html declared it
        // we reuse; otherwise we create one and attach to body so the
        // editor still works on stripped-down templates.
        let svg = document.getElementById('concept-edges');
        if (!svg) {
            svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.id = 'concept-edges';
            svg.style.cssText = 'position:fixed; inset:0; width:100vw; height:100vh; '
                              + 'pointer-events:none; z-index:9999;';
            document.body.appendChild(svg);
        }

        // Window resize: edges redraw from card bounding rects, so a
        // viewport size change shifts every edge.
        window.addEventListener('resize', () => this._drawConceptEdges());

        // Template's continuous 120 ms redraw — always on now that the
        // editor is part of the main UI. Cost is negligible: an empty
        // edges array short-circuits drawEdges in two early returns.
        this._conceptDrawTimer = setInterval(() => this._drawConceptEdges(), 120);

        // Per user feedback: no dummy seed card on startup. The
        // editor should appear EMPTY; the user creates concept
        // nodes deliberately via "+ New Concept", or implicitly via
        // Compile-time recursive decomposition (which spawns child
        // cards from JSON / indented-tree structures inside pinned
        // panel sections — see cp/billboard.js _decomposeIntoChildren).
        // The template's `addNode('', 250, 180)` seed was a vestige
        // of the standalone HTML demo where some visible affordance
        // was needed to communicate that the editor existed; in the
        // unified UI the "+ New Concept" toolbar button does that job.
    },

    // ── W4 / §8D.44 — Backend persistence sync ───────────────────────────────

    /**
     * Hydrate the in-memory concept Map from the backend's persisted
     * store. Called once at init. If the backend is unreachable or
     * empty, the editor stays in local-only mode. Returns silently.
     */
    async _hydrateConceptsFromBackend() {
        const ws = this._conceptWorkspaceId || '';
        // W11b — ask the backend to ensure foundation fixtures
        // (Database + WebBrowser) exist before we list concepts.
        // Best-effort; if it 404s we keep going.
        try {
            await fetch('/api/foundation/ensure?workspace_id=' + encodeURIComponent(ws), {
                method: 'POST',
            });
        } catch (_) { /* ignore */ }
        // §R.2 — workspace-open trigger: project the full ontology (fixtures
        // just ensured + python trees + user concepts) into the 3D GUI. The
        // resulting `ontology_layout` frame lands on the workspace WS and the
        // projector renders it (scanner._renderOntologyOverlay).
        try {
            fetch('/api/ontology/layout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ workspace_id: ws }),
            }).catch(() => {});
        } catch (_) { /* best-effort */ }
        const url = ws
            ? `/api/concepts?workspace_id=${encodeURIComponent(ws)}`
            : '/api/concepts';
        let resp;
        try {
            resp = await fetch(url);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        } catch (e) {
            // Backend unreachable; that's fine, we run local-only.
            this._conceptBackendOk = false;
            return;
        }
        let payload;
        try {
            payload = await resp.json();
        } catch (e) {
            this._conceptBackendOk = false;
            return;
        }
        const concepts = Array.isArray(payload && payload.concepts) ? payload.concepts : [];
        // The editor's in-memory shape uses (id, name, description,
        // value, x, y). Backend's ConceptNode uses (concept_id, name,
        // description, data, layout_xy). Map between them.
        for (const c of concepts) {
            if (!c || !c.concept_id) continue;
            // Don't clobber a local card the user just authored before
            // hydrate landed — local wins on collision.
            if (this._conceptNodes.has(c.concept_id)) continue;
            let x = 150 + Math.random() * 300;
            let y = 140 + Math.random() * 280;
            try {
                if (c.layout_xy) {
                    const parsed = JSON.parse(c.layout_xy);
                    if (parsed && typeof parsed.x === 'number') x = parsed.x;
                    if (parsed && typeof parsed.y === 'number') y = parsed.y;
                }
            } catch (_) { /* JSON parse error — use random fallback */ }
            const node = {
                id:          c.concept_id,
                name:        c.name || c.concept_id,
                description: c.description || '',
                value:       c.data || '',
                // §8D.20 — backend-derived syntax-free rendering tree.
                // Empty for new cards until the lifecycle chain derives
                // one; populated on every echoed concept_changed.
                rendering:   c.rendering || '',
                x, y,
                // W19 — carry the backing pointer so the memory-ref
                // classifier can read it. Also retained for invoke-
                // through-registry calls (C4).
                backing_pointer: c.backing_pointer || '',
                type_hint:       c.type_hint || '',
                provenance:      c.provenance || '',
            };
            this._conceptNodes.set(node.id, node);
            this._createConceptCard(node);
            // Seed the stable-backend-id map so rename writes
            // continue to PATCH the correct record.
            if (!this._conceptBackendIds) this._conceptBackendIds = new Map();
            this._conceptBackendIds.set(node.id, c.concept_id);
        }
        // Hydrate edges next (edge shape: { source, target }).
        const edges = Array.isArray(payload && payload.edges) ? payload.edges : [];
        for (const e of edges) {
            if (!e || !e.source_id || !e.target_id) continue;
            // Dedup: don't re-add if same source→target already present.
            const exists = this._conceptEdges.some(x =>
                x.source === e.source_id && x.target === e.target_id);
            if (exists) continue;
            this._conceptEdges.push({
                source: e.source_id,
                target: e.target_id,
                edge_id: e.edge_id || null,
                edge_type: e.edge_type || 'RELATES_TO',
            });
        }
    },

    /**
     * Schedule a debounced write-through to the backend for a
     * concept node. Called by the create / rename / description /
     * value / drag handlers — anywhere local state mutates. Multiple
     * rapid edits coalesce into one POST.
     */
    _scheduleConceptSync(conceptId, opts = {}) {
        if (!this._conceptBackendOk) return;
        if (!conceptId) return;
        this._conceptSyncPending.add(conceptId);
        // Track the stable backend id (may differ from the display
        // id when the user has renamed the card). Defaults to the
        // current id if no rename has happened yet.
        if (opts.backendId) {
            if (!this._conceptBackendIds) this._conceptBackendIds = new Map();
            this._conceptBackendIds.set(conceptId, opts.backendId);
        }
        // Clear any prior pending timer for this id.
        const prior = this._conceptSyncTimers.get(conceptId);
        if (prior) clearTimeout(prior);
        const delay = (opts.delay != null) ? opts.delay : 600;
        const timer = setTimeout(() => {
            this._conceptSyncTimers.delete(conceptId);
            this._flushConceptSync(conceptId).catch(err => {
                console.warn('[concept_graph] sync failed for', conceptId, err && err.message);
            });
        }, delay);
        this._conceptSyncTimers.set(conceptId, timer);
    },

    /**
     * Flush one concept's local state to the backend. PATCH if it has
     * been seen by the backend before (we use the concept_id itself
     * as the existence marker — first POST creates, subsequent PATCH
     * upserts via the same id). The current implementation always
     * tries PATCH first, falls back to POST on 404. Order is fine
     * because the backend's create is idempotent on concept_id.
     */
    async _flushConceptSync(conceptId) {
        if (!this._conceptBackendOk) return;
        const node = this._conceptNodes.get(conceptId);
        if (!node) {
            // The card may have been deleted; the delete handler issues
            // its own DELETE separately, so here we just clear pending.
            this._conceptSyncPending.delete(conceptId);
            return;
        }
        // Keep ``conceptId`` in ``_conceptSyncPending`` until AFTER the
        // backend round-trip. The backend re-broadcasts every write as
        // a ``concept_changed`` WS frame, and our originator tab also
        // receives that echo via the workspace socket. While the sync
        // is in flight, ``_applyConceptChangedFrame`` reads pending
        // and skips the echo so the textarea (and any further edits
        // the user has made since the debounce fired) is not clobbered
        // by stale server-echoed data.
        //
        // Echo-suppress fallback: even after the HTTP response returns,
        // the WS frame may arrive a few ms later via the loop's
        // ``call_soon_threadsafe`` push. Stash the id in
        // ``_conceptEchoSuppress`` with a short TTL so the echo is
        // ignored even after pending clears.
        if (!this._conceptEchoSuppress) this._conceptEchoSuppress = new Map();
        // Use the stable backend id when present (set on first
        // rename via card.dataset.backendConceptId); otherwise the
        // display id IS the backend id (this is the case for newly-
        // created cards that have never been renamed).
        const backendId = (this._conceptBackendIds && this._conceptBackendIds.get(conceptId))
            || conceptId;
        // Idempotency key — stamps this debounced flush so a network
        // retry doesn't fire duplicate broadcasts + evolution-log
        // entries on the backend. Per-flush key (not per-card) so
        // each settled edit gets its own dedup slot.
        const idemKey = this._newIdempotencyKey();
        const payload = {
            concept_id:  backendId,
            name:        node.name || '',
            description: node.description || '',
            data:        node.value || '',
            workspace_id: this._conceptWorkspaceId || '',
            layout_xy:   { x: node.x, y: node.y },
            idempotency_key: idemKey,
        };
        // Try PATCH (update existing). On 404, fall back to POST.
        // ``_fetchWithRetry`` retries on transport-level errors (network
        // drop / offline) with exponential backoff; the idempotency key
        // on the payload makes retry safe against duplicate side effects.
        const init = {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        };
        let resp = await this._fetchWithRetry(
            `/api/concepts/${encodeURIComponent(backendId)}`, init,
        );
        if (resp == null) {
            // All retries failed; mark backend offline and bail.
            this._conceptBackendOk = false;
            this._conceptSyncPending.delete(conceptId);
            return;
        }
        if (resp.status === 404) {
            // Not yet persisted — create.
            resp = await this._fetchWithRetry('/api/concepts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (resp == null) {
                this._conceptBackendOk = false;
                this._conceptSyncPending.delete(conceptId);
                return;
            }
        }
        if (!resp.ok) {
            console.warn('[concept_graph] backend rejected sync for', backendId, resp.status);
        } else {
            // §8D.20 — backend derives the syntax-free rendering from
            // ``data`` inside the lifecycle chain. Pull it from the
            // response so the originator tab updates its preview
            // without having to wait for the WS echo (which it skips).
            try {
                const updated = await resp.json();
                if (updated && updated.concept_id) {
                    const node = this._conceptNodes.get(conceptId);
                    if (node && typeof updated.rendering === 'string') {
                        node.rendering = updated.rendering;
                        const card = document.querySelector(
                            `.concept-card[data-node-id="${conceptId}"]`
                        );
                        if (card) {
                            const pv = card.querySelector('.concept-compiled-preview');
                            if (pv) {
                                pv.textContent = updated.rendering;
                                pv.style.display = updated.rendering ? 'block' : 'none';
                            }
                        }
                    }
                }
            } catch (_) { /* response body wasn't JSON; not fatal */ }
        }
        // Clear pending NOW (response landed). Add a TTL'd echo
        // suppression so an echo that arrives in the next ~1500 ms
        // is still skipped (handles call_soon_threadsafe latency).
        this._conceptSyncPending.delete(conceptId);
        const expiresAt = Date.now() + 1500;
        this._conceptEchoSuppress.set(backendId, expiresAt);
        if (backendId !== conceptId) this._conceptEchoSuppress.set(conceptId, expiresAt);
        // Lightweight GC: prune entries older than now on every flush.
        const now = Date.now();
        for (const [k, exp] of this._conceptEchoSuppress) {
            if (exp <= now) this._conceptEchoSuppress.delete(k);
        }
    },

    /**
     * Issue an immediate DELETE to the backend for a concept node.
     * Called from the delete-button handler. Not debounced — delete
     * is a discrete action the user expects to land authoritatively.
     */
    /**
     * Multi-tab sync — apply a peer tab's concept change locally.
     * Skips no-op cases: if we have a pending sync for the same
     * concept_id, we assume we authored this change ourselves and
     * the round-trip is harmless. Reload-from-backend lands the
     * latest state regardless.
     */
    _applyConceptChangedFrame(frame) {
        if (!frame || !frame.concept_id) return;
        const cid = frame.concept_id;
        const change = frame.change || 'updated';
        // Suppress if this tab originated the change. Two signals:
        //   1. ``_conceptSyncPending`` — sync is in flight RIGHT NOW.
        //   2. ``_conceptEchoSuppress`` — sync just completed; the
        //      echo may arrive shortly after the HTTP response, after
        //      pending has cleared. A short TTL window covers the
        //      ``call_soon_threadsafe`` push latency.
        if (this._conceptSyncPending && this._conceptSyncPending.has(cid)) return;
        if (this._conceptEchoSuppress) {
            const exp = this._conceptEchoSuppress.get(cid);
            if (exp && exp > Date.now()) return;
        }
        if (change === 'deleted') {
            // Tear down the local card if it exists.
            if (this._conceptNodes && this._conceptNodes.has(cid)) {
                const card = document.querySelector(`.concept-card[data-node-id="${cid}"]`);
                if (card && card.parentNode) card.parentNode.removeChild(card);
                this._conceptNodes.delete(cid);
                this._conceptEdges = this._conceptEdges.filter(
                    e => e.source !== cid && e.target !== cid
                );
                if (this._drawConceptEdges) this._drawConceptEdges();
            }
            return;
        }
        // created / updated: pull the concept from the frame body
        // and reconcile into the local Map.
        const c = frame.concept;
        if (!c) return;
        if (this._conceptNodes && this._conceptNodes.has(cid)) {
            // Update existing.
            const node = this._conceptNodes.get(cid);
            node.name = c.name || node.name;
            node.description = c.description != null ? c.description : node.description;
            node.value = c.data != null ? c.data : node.value;
            // §8D.20 — backend is authoritative for the syntax-free
            // rendering tree. Always pull it in from the echo so the
            // preview reflects the latest cascade.
            if (c.rendering != null) node.rendering = c.rendering;
            node.backing_pointer = c.backing_pointer != null ? c.backing_pointer : node.backing_pointer;
            node.type_hint = c.type_hint != null ? c.type_hint : node.type_hint;
            // Refresh the visible fields without re-creating the card.
            const card = document.querySelector(`.concept-card[data-node-id="${cid}"]`);
            if (card) {
                const ni = card.querySelector('.concept-name-input');
                if (ni && document.activeElement !== ni) ni.value = node.name;
                const di = card.querySelector('.concept-desc-input');
                if (di && document.activeElement !== di) di.value = node.description;
                const vi = card.querySelector('.concept-value-input');
                if (vi && document.activeElement !== vi) vi.value = node.value;
                const pv = card.querySelector('.concept-compiled-preview');
                if (pv && c.rendering != null) {
                    pv.textContent = c.rendering;
                    if (c.rendering) pv.style.display = 'block';
                }
            }
        } else if (this.addConceptNode) {
            // Create — only if it doesn't already exist locally.
            let x = 150 + Math.random() * 300;
            let y = 140 + Math.random() * 280;
            try {
                if (c.layout_xy) {
                    const parsed = JSON.parse(c.layout_xy);
                    if (parsed && typeof parsed.x === 'number') x = parsed.x;
                    if (parsed && typeof parsed.y === 'number') y = parsed.y;
                }
            } catch (_) {}
            const node = {
                id: cid,
                name: c.name || cid,
                description: c.description || '',
                value: c.data || '',
                rendering: c.rendering || '',
                x, y,
                backing_pointer: c.backing_pointer || '',
                type_hint:       c.type_hint || '',
                provenance:      c.provenance || '',
            };
            this._conceptNodes.set(cid, node);
            this._createConceptCard(node);
            if (!this._conceptBackendIds) this._conceptBackendIds = new Map();
            this._conceptBackendIds.set(cid, c.concept_id || cid);
        }
    },

    /**
     * Multi-tab sync — apply a peer tab's edge change locally. The
     * ``frame`` body is ``{ edge_id, change: created|deleted, edge? }``.
     * For created, dedup against existing local edges before adding.
     * For deleted, drop matching local edges and redraw.
     */
    _applyEdgeChangedFrame(frame) {
        if (!frame || !frame.edge_id) return;
        const change = frame.change || 'created';
        if (change === 'deleted') {
            const before = this._conceptEdges.length;
            this._conceptEdges = this._conceptEdges.filter(e => e.edge_id !== frame.edge_id);
            if (this._conceptEdges.length !== before) {
                if (this._drawConceptEdges) this._drawConceptEdges();
            }
            return;
        }
        const e = frame.edge;
        if (!e || !e.source_id || !e.target_id) return;
        // Dedup by edge_id first; fall back to (source, target) pair.
        const exists = this._conceptEdges.some(x =>
            (x.edge_id && x.edge_id === e.edge_id) ||
            (x.source === e.source_id && x.target === e.target_id)
        );
        if (exists) return;
        this._conceptEdges.push({
            source:   e.source_id,
            target:   e.target_id,
            edge_id:  e.edge_id || null,
            edge_type: e.edge_type || 'RELATES_TO',
        });
        if (this._drawConceptEdges) this._drawConceptEdges();
    },

    async _deleteConceptFromBackend(conceptId) {
        if (!this._conceptBackendOk) return;
        if (!conceptId) return;
        // Resolve to the stable backend id if the user has renamed
        // this card; otherwise the display id IS the backend id.
        const backendId = (this._conceptBackendIds && this._conceptBackendIds.get(conceptId))
            || conceptId;
        try {
            await fetch(`/api/concepts/${encodeURIComponent(backendId)}`, {
                method: 'DELETE',
            });
            if (this._conceptBackendIds) this._conceptBackendIds.delete(conceptId);
        } catch (e) {
            console.warn('[concept_graph] delete failed for', backendId, e && e.message);
        }
    },

    /**
     * W11 — Connect to the workspace-scoped WS channel for live frames.
     * Routes incoming frames through the existing scanner's
     * _processScanFrame dispatcher so all five frame-type handlers
     * (W1 plus W5/W7/W10) fire on the unified entry point.
     */
    _connectWorkspaceWs() {
        const ws = this._conceptWorkspaceId || '_default';
        if (this._workspaceWs && this._workspaceWs.readyState <= 1) return;
        // Fix: cancel any stale reconnect timer before spinning up
        // a new socket. Without this, rapidly switching workspaces
        // could leave several reconnect timers in flight, each one
        // racing to create a duplicate socket on its trigger.
        if (this._workspaceReconnectTimer) {
            clearTimeout(this._workspaceReconnectTimer);
            this._workspaceReconnectTimer = null;
        }
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${window.location.host}/api/ws/workspace/${encodeURIComponent(ws)}`;
        let socket;
        try {
            socket = new WebSocket(url);
        } catch (e) {
            console.warn('[concept_graph] workspace WS construction failed:', e && e.message);
            return;
        }
        this._workspaceWs = socket;
        // Remember which workspace this socket belongs to so the
        // close handler can detect a stale reconnect attempt.
        socket._wfhWorkspaceId = ws;
        socket.addEventListener('message', (ev) => {
            let frame;
            try { frame = JSON.parse(ev.data); }
            catch (_) { return; }
            // Route through the central dispatcher so all W1-W10 frame
            // handlers fire on a single entry point. The dispatcher
            // ignores frames it doesn't recognise.
            if (typeof this._processScanFrame === 'function') {
                try { this._processScanFrame(frame, {}); }
                catch (e) {
                    console.warn('[concept_graph] ws frame dispatch failed:', e && e.message);
                }
            }
        });
        socket.addEventListener('close', () => {
            // Skip reconnect if this socket belonged to a workspace
            // we've since switched away from. The current workspace's
            // _connectWorkspaceWs path handles its own connection.
            if (socket._wfhWorkspaceId !== (this._conceptWorkspaceId || '_default')) {
                return;
            }
            this._workspaceWs = null;
            // Re-connect with a 2s back-off; backend may have
            // restarted, or this tab was hidden.
            if (this._workspaceWsBackoff == null) this._workspaceWsBackoff = 2000;
            const backoff = Math.min(this._workspaceWsBackoff, 30000);
            this._workspaceReconnectTimer = setTimeout(() => {
                this._workspaceReconnectTimer = null;
                this._connectWorkspaceWs();
            }, backoff);
            this._workspaceWsBackoff = backoff * 1.5;
        });
        socket.addEventListener('open', () => {
            this._workspaceWsBackoff = 2000;  // reset on successful connect
            console.log('[concept_graph] workspace WS connected:', ws);
        });
    },

    // ── Slug / escape helpers (verbatim from template) ───────────────────────

    _conceptSlugify(s) {
        return String(s || '')
            .trim()
            .toLowerCase()
            .replace(/[^a-z0-9_]+/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_|_$/g, '');
    },

    _conceptEscapeHtml(s) {
        return String(s).replace(/[&<>"]/g, c => (
            { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]
        ));
    },

    _conceptEscapeRegex(s) {
        return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    },

    /**
     * W19 / §8D.24 — classify a concept node as memory-reference
     * (refers to data not generated by this graph) or computed-value
     * (output of a function in this graph). Heuristic:
     *   computed:    backing_pointer in { slm::invoke, db::cypher,
     *                                     db::tfidf_retrieve } or
     *                module::backend.* (a real python callable) or
     *                compiled_from_scans::searchable_url::* (search-
     *                and-paginate routine)
     *   memory ref:  everything else (user-authored, ontology nodes,
     *                pretty-printers, fixtures, xpath_pattern records,
     *                detected_accessor records)
     */
    _conceptClassifyMemoryRef(node) {
        if (!node) return true;
        const bp = String(node.backing_pointer || '');
        if (!bp) return true;
        if (bp === 'slm::invoke' || bp === 'db::cypher' || bp === 'db::tfidf_retrieve') return false;
        if (bp.startsWith('module::backend.')) return false;
        if (bp.startsWith('compiled_from_scans::searchable_url::')) return false;
        return true;
    },

    /**
     * Generate an idempotency-key UUID for a single mutation POST/PATCH.
     * Backend dedupes by (workspace, target, key) over its TTL so a
     * network retry doesn't fire duplicate broadcasts + log entries.
     * Centralised so concept / edge / spawn / fork all use the same
     * shape; falls back to a timestamp+random string if crypto.randomUUID
     * is unavailable (older browsers, http://localhost dev contexts).
     */
    _newIdempotencyKey() {
        if (typeof crypto !== 'undefined' && crypto.randomUUID) {
            return crypto.randomUUID();
        }
        return 'idem-' + Date.now() + '-' + Math.random().toString(36).slice(2, 10);
    },

    /**
     * Ray-constrained placement for auto-spawned cards (the 2D analogue
     * of the 3D UMAP-linear-radial layout). Distributes N peers along a
     * fixed fan of RAYS emanating from the focal/anchor card, each ray
     * growing radially outward — a deliberate radial arrangement, never
     * the forbidden golden-angle spiral / concentric rings (CLAUDE.md
     * forbidden concepts) nor the previous ``Math.random()`` scatter.
     *
     * Anchor priority:
     *   1. ``opts.anchorId`` — parent / focal card id (spawned children,
     *      auto-created {ref} targets, decomposed JSON children).
     *   2. The most-recently-touched card (``_lastTouchedId``) — typed-
     *      into / dragged / hovered.
     *   3. Editor viewport centre as last resort.
     *
     * Returns ``{ x, y }`` in viewport coords. Cards the user has
     * manually dragged are soft-pinned: their ``_userPositioned`` flag
     * makes the auto-layout skip them when distributing peers.
     */
    _rayConstrainedPosition(opts = {}) {
        // Ray-constrained placement — the 2D analogue of the 3D
        // UMAP-linear-radial layout. Auto-spawned cards extrude along a
        // fixed FAN OF RAYS from the focal (anchor) card; each ray grows
        // radially OUTWARD. This REPLACES the forbidden golden-angle
        // Fibonacci spiral / concentric rings (CLAUDE.md forbidden concepts
        // §"Concentric concept-graph rings": the 2D editor's
        // _fibonacciPosition "is replaced by ray-constrained placement
        // around the focal card").
        const N_RAYS = 8;            // fan of ray directions around the focal
        const BASE_RADIUS = 220;     // ring-0 distance from the focal
        const RAY_STEP = 150;        // radial spacing of successive rings on a ray
        // Anchor resolution.
        let anchor = null;
        if (opts.anchorId && this._conceptNodes.has(opts.anchorId)) {
            anchor = this._conceptNodes.get(opts.anchorId);
        } else if (this._lastTouchedId && this._conceptNodes.has(this._lastTouchedId)) {
            anchor = this._conceptNodes.get(this._lastTouchedId);
        }
        let cx, cy;
        if (anchor && typeof anchor.x === 'number' && typeof anchor.y === 'number') {
            cx = anchor.x; cy = anchor.y;
        } else {
            // Editor centre fallback.
            cx = (window.innerWidth || 1200) * 0.5;
            cy = (window.innerHeight || 800) * 0.5;
        }
        // Per-anchor spawn counter so repeated spawns from the same focal
        // fill the rays at ring 0 first, THEN step every ray outward — a
        // radial fan, never a continuous spiral filling concentric rings.
        if (!this._rayIdxByAnchor) this._rayIdxByAnchor = new Map();
        const anchorKey = anchor ? anchor.id : '_viewport';
        const idx = (this._rayIdxByAnchor.get(anchorKey) || 0);
        this._rayIdxByAnchor.set(anchorKey, idx + 1);
        const rayDir = (idx % N_RAYS) * (2 * Math.PI / N_RAYS);   // which ray
        const ring   = Math.floor(idx / N_RAYS);                  // step out along it
        const radius = BASE_RADIUS + ring * RAY_STEP;
        // Bound to viewport so off-screen cards don't surprise the user.
        const margin = 80;
        let x = cx + radius * Math.cos(rayDir);
        let y = cy + radius * Math.sin(rayDir);
        x = Math.max(margin, Math.min((window.innerWidth || 1200) - margin - 280, x));
        y = Math.max(margin, Math.min((window.innerHeight || 800) - margin - 220, y));
        return { x, y };
    },

    /**
     * Mark a card as user-positioned so the ray-constrained auto-layout
     * treats it as a soft pin (auto-spawned siblings flow around it).
     */
    _markUserPositioned(conceptId) {
        const node = this._conceptNodes && this._conceptNodes.get(conceptId);
        if (node) node._userPositioned = true;
    },

    /**
     * Retry-on-network-error wrapper for mutation fetches. The backend
     * dedupes by idempotency_key, so retrying the SAME payload is safe
     * — the server returns the cached response on the second hit
     * without re-firing the lifecycle. HTTP errors (4xx / 5xx) are
     * NOT retried because they're application-level, not transport-
     * level. Exponential backoff: 250, 500, 1000 ms.
     *
     * Returns the final ``Response`` or ``null`` if all retries
     * exhausted. Callers must check ``.ok`` / ``.status`` themselves.
     */
    async _fetchWithRetry(url, init, maxAttempts = 3) {
        let delay = 250;
        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                const resp = await fetch(url, init);
                // Transport succeeded — return regardless of HTTP status.
                return resp;
            } catch (err) {
                if (attempt === maxAttempts) {
                    console.warn(
                        '[concept_graph] mutation network retry exhausted for',
                        url, 'after', maxAttempts, 'attempts:', err && err.message,
                    );
                    return null;
                }
                // Network failure (DNS / refused / CORS / offline) —
                // wait, then retry. Idempotency key on the payload
                // makes this safe against duplicate side effects.
                await new Promise(r => setTimeout(r, delay));
                delay *= 2;
            }
        }
        return null;
    },

    // ── Node creation ────────────────────────────────────────────────────────

    /**
     * W20 / §8D.22 — Spawn the empty primitive.
     *
     * An empty primitive is a concept node with no resolved type:
     * empty description, empty data, and a `type_hint='empty'` marker.
     * Typing into either description OR data fires
     * /api/radiation against the typed text, which surfaces the
     * top-K candidates via the apparition halo overlay (W12). Clicking
     * a candidate "resolves" the empty into that concept: the empty
     * adopts the candidate's name + creates a DERIVED_FROM edge.
     *
     * If the user instead types a custom name and never picks a
     * candidate, the empty becomes a regular user-authored concept.
     */
    /**
     * D3 / §8D.13 — Attach a sample stepper to a card whose data
     * references an XPathPattern concept node.
     *
     * The stepper UI has prev / sample-i-of-N / next buttons. On
     * step, the card's data field morphs to the active sample's
     * rendered_text over a short tween (smooth-cascade contract).
     * Memory-reference cards (per W19 classification) downstream
     * of this card keep their cached value; computed-value cards
     * re-fire.
     */
    async attachSampleStepper(cardEl, conceptNode, patternConceptId) {
        if (!cardEl || !conceptNode) return;
        // Fix: track which pattern the bank was fetched for. If
        // the user changed the {ref} to point at a different pattern,
        // we need to refresh the bank rather than re-using stale
        // instances. _sampleBankPatternId is set on first attach;
        // subsequent attach calls that target a different pattern
        // tear down the prior stepper and rebuild.
        if (cardEl._sampleBankPatternId && cardEl._sampleBankPatternId !== patternConceptId) {
            const oldStepper = cardEl.querySelector('.concept-sample-stepper');
            if (oldStepper && oldStepper.parentNode) {
                oldStepper.parentNode.removeChild(oldStepper);
            }
            // Restore the pre-iteration data block so the user sees
            // their original authored value instead of a sample from
            // the wrong pattern.
            if (cardEl._preSampleData != null) {
                conceptNode.value = cardEl._preSampleData;
                const ta = cardEl.querySelector('.concept-value-input');
                if (ta) ta.value = cardEl._preSampleData;
            }
            cardEl._sampleBank = null;
            cardEl._sampleIdx = 0;
            // §8D.24 — clear the memory-ref snapshot map. A new
            // pattern's iteration takes a fresh snapshot on first step.
            cardEl._memoryRefSnapshots = null;
        }
        // Fetch the pattern's instance bank.
        const ws = this._conceptWorkspaceId || '';
        const params = new URLSearchParams();
        if (ws) params.set('workspace_id', ws);
        let instances = [];
        try {
            const resp = await fetch(`/api/pattern_instances/${encodeURIComponent(patternConceptId)}?` + params.toString());
            if (resp.ok) {
                const data = await resp.json();
                instances = Array.isArray(data && data.instances) ? data.instances : [];
            }
        } catch (_) { return; }
        if (!instances.length) return;
        // Cache the bank on the card for re-stepping.
        cardEl._sampleBank = instances;
        cardEl._sampleIdx = 0;
        cardEl._sampleBankPatternId = patternConceptId;
        // Stash the pre-iteration data so step-back-to-zero restores
        // the user's authored value.
        cardEl._preSampleData = conceptNode.value;
        // Add the stepper UI to the body header.
        let stepper = cardEl.querySelector('.concept-sample-stepper');
        if (!stepper) {
            stepper = document.createElement('div');
            stepper.className = 'concept-sample-stepper';
            stepper.style.cssText =
                'display:flex;gap:6px;align-items:center;font-size:10px;' +
                'padding:4px 6px;background:rgba(99,102,241,0.15);' +
                'border-radius:4px;margin:4px 8px;';
            const body = cardEl.querySelector('.concept-card-body');
            if (body) body.insertBefore(stepper, body.firstChild);
        }
        const renderStepper = () => {
            const n = cardEl._sampleBank.length;
            const i = cardEl._sampleIdx;
            stepper.innerHTML = `
                <button class="step-prev" style="background:none;border:none;color:#b8c0c8;cursor:pointer;">‹</button>
                <span style="opacity:0.8;">sample ${i + 1} / ${n}</span>
                <button class="step-next" style="background:none;border:none;color:#b8c0c8;cursor:pointer;">›</button>
                <button class="step-reset" title="Restore original data" style="background:none;border:none;color:#9aa3ab;cursor:pointer;font-size:9px;margin-left:auto;">⤺</button>
            `;
            stepper.querySelector('.step-prev').addEventListener('click', () => this._stepSample(cardEl, conceptNode, -1, renderStepper));
            stepper.querySelector('.step-next').addEventListener('click', () => this._stepSample(cardEl, conceptNode,  1, renderStepper));
            stepper.querySelector('.step-reset').addEventListener('click', () => {
                if (cardEl._preSampleData != null) {
                    conceptNode.value = cardEl._preSampleData;
                    const ta = cardEl.querySelector('.concept-value-input');
                    if (ta) ta.value = cardEl._preSampleData;
                    cardEl._sampleIdx = 0;
                    // §8D.24 — restore the memory-ref snapshots one
                    // last time, then drop them. The user's authored
                    // graph is back to its pre-iteration state.
                    this._restoreMemoryRefSnapshots(cardEl._memoryRefSnapshots);
                    cardEl._memoryRefSnapshots = null;
                    // §4.6.1 — mirror the signal-stream reset so peer tabs + REPL clear it.
                    if (typeof this._mirrorUi === 'function')
                        this._mirrorUi('/api/ui/signal_stream_clear', { card_id: conceptNode.id });
                    // PATCH the focal so the backend re-derives
                    // rendering from the restored data.
                    this._scheduleConceptSync(conceptNode.id, { delay: 100 });
                    renderStepper();
                    this._drawConceptEdges();
                }
            });
        };
        renderStepper();
        // Auto-bind first sample.
        this._stepSample(cardEl, conceptNode, 0, renderStepper);
    },

    _stepSample(cardEl, conceptNode, delta, renderStepper) {
        if (!cardEl || !cardEl._sampleBank) return;
        const n = cardEl._sampleBank.length;
        cardEl._sampleIdx = ((cardEl._sampleIdx + delta) % n + n) % n;
        const inst = cardEl._sampleBank[cardEl._sampleIdx];
        // §4.6.1 — mirror the signal-stream position (+ the step delta) so peer
        // tabs, the REPL, and the agent see which sample instance is rendering.
        if (typeof this._mirrorUi === 'function') {
            this._mirrorUi('/api/ui/signal_stream', { card_id: conceptNode.id, total: n, signal_index: cardEl._sampleIdx });
            if (delta) this._mirrorUi('/api/ui/signal_advance', { card_id: conceptNode.id, step: delta });
        }
        const next = inst && inst.rendered_text ? inst.rendered_text : JSON.stringify(inst, null, 2);
        // §8D.24 — snapshot the rendering of every downstream memory-ref
        // card before stepping so we can restore it after. Memory refs
        // are values pulled from outside this graph's computation; the
        // sample iteration must NOT touch them. Snapshot once per
        // step-session and reuse across steps.
        if (!cardEl._memoryRefSnapshots) {
            cardEl._memoryRefSnapshots = this._snapshotDownstreamMemoryRefs(conceptNode.id);
        }
        const computedDownstream = this._collectDownstreamComputedRefs(conceptNode.id);
        // Smooth-cascade: fade body opacity, swap value, fade back.
        const ta = cardEl.querySelector('.concept-value-input');
        if (ta) {
            ta.style.transition = 'opacity 120ms';
            ta.style.opacity = '0.3';
            setTimeout(() => {
                conceptNode.value = next;
                ta.value = next;
                ta.style.opacity = '1';
                // Re-parse references so downstream computed-value
                // cards re-fire on the new sample's content.
                this._parseConceptReferences(conceptNode);
                this._drawConceptEdges();
                // Schedule a backend sync for the new value (D3 +
                // C5 evolution log records the step too).
                this._scheduleConceptSync(conceptNode.id, { delay: 800 });
                // §8D.24 — restore the pinned rendering of every
                // downstream memory-ref card. They must not appear to
                // change under iteration (their values come from
                // outside this graph's computation).
                this._restoreMemoryRefSnapshots(cardEl._memoryRefSnapshots);
                // §8D.24 — re-fire the computed-value downstreams so
                // their rendering reflects the new sample. PATCH with
                // unchanged data is enough: the lifecycle re-derives
                // rendering via compute_rendering_tree and echoes the
                // updated value back via concept_changed.
                computedDownstream.forEach(id => {
                    this._scheduleConceptSync(id, { delay: 200 });
                });
                if (renderStepper) renderStepper();
            }, 120);
        }
    },

    /**
     * §8D.24 — walk one hop downstream from ``sourceId`` and split the
     * targets into memory-ref vs computed-value by their backing
     * pointer (per ``_conceptClassifyMemoryRef``). Used by the sample
     * stepper to enforce the "memory refs don't change under
     * iteration; computed values do" contract.
     */
    _snapshotDownstreamMemoryRefs(sourceId) {
        const snapshots = new Map();
        if (!this._conceptEdges) return snapshots;
        for (const e of this._conceptEdges) {
            if (e.source !== sourceId) continue;
            const node = this._conceptNodes.get(e.target);
            if (!node) continue;
            if (!this._conceptClassifyMemoryRef(node)) continue;
            snapshots.set(node.id, {
                rendering: node.rendering || '',
                value: node.value || '',
            });
        }
        return snapshots;
    },

    _collectDownstreamComputedRefs(sourceId) {
        const out = [];
        if (!this._conceptEdges) return out;
        for (const e of this._conceptEdges) {
            if (e.source !== sourceId) continue;
            const node = this._conceptNodes.get(e.target);
            if (!node) continue;
            if (this._conceptClassifyMemoryRef(node)) continue;
            out.push(node.id);
        }
        return out;
    },

    _restoreMemoryRefSnapshots(snapshots) {
        if (!snapshots || !snapshots.size) return;
        for (const [id, snap] of snapshots) {
            const node = this._conceptNodes.get(id);
            if (!node) continue;
            // Pin the rendering — the backend may re-derive it on the
            // stepped card's PATCH (since the stepped card's data
            // changed), but locally the user must see the pre-step
            // value. The next concept_changed echo for THIS memory-ref
            // card will overwrite the pin if its data actually changed
            // (a different cause), which is the correct behaviour.
            node.rendering = snap.rendering;
            const card = document.querySelector(`.concept-card[data-node-id="${id}"]`);
            if (!card) continue;
            const pv = card.querySelector('.concept-compiled-preview');
            if (pv && snap.rendering) {
                pv.textContent = snap.rendering;
                pv.style.display = 'block';
            }
        }
    },

    /**
     * §8D.22 — Resolve an empty primitive into a chosen apparition.
     *
     * Adopts the candidate's name & description into the empty,
     * draws a DERIVED_FROM edge from the resolved card back to the
     * candidate (so the provenance trail is preserved per §8D.33),
     * and clears the empty-primitive UI markers. The empty's
     * data block is left as-is so any text the user already typed
     * survives the resolution.
     */
    async _resolveEmptyPrimitive(card, emptyNode, candidateId) {
        // Fix: guard against double-resolve. Rapid double-clicks on
        // two phantoms (or a misfire that re-enters this method)
        // would resolve the empty twice, drawing duplicate
        // DERIVED_FROM edges and inheriting whichever name landed
        // last. The flag is per-card; cleared in the finally so
        // subsequent independent resolutions still work.
        if (card._resolvingEmpty) return;
        card._resolvingEmpty = true;
        try {
        // Fetch the candidate's metadata so we can adopt its name +
        // description. Use the local Map first; fall back to backend.
        let candidate = this._conceptNodes.get(candidateId);
        if (!candidate && this._conceptBackendOk) {
            try {
                const resp = await fetch(`/api/concepts/${encodeURIComponent(candidateId)}`);
                if (resp.ok) candidate = await resp.json();
            } catch (_) {}
        }
        if (!candidate) return;
        const newName = (candidate.name && this._conceptSlugify(candidate.name))
            || candidate.id || candidate.concept_id || emptyNode.id;
        const newDescription = candidate.description || candidate.name || '';
        // Update local model.
        emptyNode.name = newName;
        emptyNode.description = newDescription;
        emptyNode.type_hint = (candidate.type_hint && candidate.type_hint !== 'empty')
            ? candidate.type_hint : '';
        // Update the DOM.
        const nameInput = card.querySelector('.concept-name-input');
        const descInput = card.querySelector('.concept-desc-input');
        if (nameInput) nameInput.value = newName;
        if (descInput) {
            descInput.value = newDescription;
            descInput.style.borderLeft = '';  // clear indigo empty-marker
            descInput.setAttribute('placeholder', 'What does this concept mean?');
        }
        delete card.dataset.emptyPrimitive;
        // Remove the "∅ empty primitive · type to radiate candidates" badge.
        const body = card.querySelector('.concept-card-body');
        if (body && body.firstChild && body.firstChild.tagName === 'DIV') {
            const txt = (body.firstChild.textContent || '').toLowerCase();
            if (txt.includes('empty primitive')) body.removeChild(body.firstChild);
        }
        // Draw a DERIVED_FROM edge from resolved → candidate so the
        // provenance trail per §8D.22 / §8D.33 is preserved.
        const exists = this._conceptEdges.some(e =>
            e.source === emptyNode.id && e.target === candidateId);
        if (!exists) {
            this._conceptEdges.push({
                source: emptyNode.id,
                target: candidateId,
                edge_type: 'DERIVED_FROM',
            });
            this._drawConceptEdges();
            if (this._conceptBackendOk) {
                try {
                    const resp = await fetch('/api/concept_edges', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            source_id: (this._conceptBackendIds && this._conceptBackendIds.get(emptyNode.id)) || emptyNode.id,
                            target_id: candidateId,
                            edge_type: 'DERIVED_FROM',
                            workspace_id: this._conceptWorkspaceId || '',
                            idempotency_key: this._newIdempotencyKey(),
                        }),
                    });
                    if (resp.ok) {
                        const data = await resp.json();
                        if (data && data.edge_id) {
                            const last = this._conceptEdges[this._conceptEdges.length - 1];
                            if (last) last.edge_id = data.edge_id;
                        }
                    }
                } catch (_) { /* ignore */ }
            }
        }
        // Persist the resolved card's new name + description.
        this._scheduleConceptSync(emptyNode.id, { delay: 50 });
        } finally {
            // Release the resolution guard so a future independent
            // user gesture (e.g. spawn a NEW empty and click) can
            // resolve cleanly. If the same card somehow ends up
            // re-entering this method (race with concurrent halo
            // dispatch), the in-flight guard prevented duplicates.
            card._resolvingEmpty = false;
        }
    },

    spawnEmptyPrimitive(opts = {}) {
        // §8D.10 — if anchored (e.g. from §8B "New Link" affordance),
        // let the Fibonacci layout place the empty on the focal's ring.
        // Otherwise centre near the viewport with a small jitter.
        let x, y;
        if (!opts.anchorId) {
            x = (window.innerWidth || 1200) / 2 - 150 + (Math.random() - 0.5) * 100;
            y = (window.innerHeight || 800) / 2 - 90 + (Math.random() - 0.5) * 80;
        }
        const node = this.addConceptNode('', x, y, { anchorId: opts.anchorId });
        if (!node) return null;
        node.type_hint = 'empty';
        node.backing_pointer = '';
        // Tag the card visually so the user knows this is an empty
        // primitive (different from a regular blank card).
        const card = document.querySelector(`.concept-card[data-node-id="${node.id}"]`);
        if (card) {
            card.dataset.emptyPrimitive = '1';
            // Make the description field's placeholder "type to see candidates".
            const desc = card.querySelector('.concept-desc-input');
            if (desc) {
                desc.setAttribute('placeholder',
                    'Type a concept name or intent — the universal halo radiates candidates as you type.');
                desc.style.borderLeft = '2px solid #b8c0c8';
            }
            // Add a small "∅ empty" badge on the body so the user
            // can see this card is special.
            const body = card.querySelector('.concept-card-body');
            if (body) {
                const badge = document.createElement('div');
                badge.style.cssText = 'font-size:9px;opacity:0.5;margin-bottom:4px;letter-spacing:0.05em;text-transform:uppercase;color:#b8c0c8;';
                badge.textContent = '∅ empty primitive · type to radiate candidates';
                body.insertBefore(badge, body.firstChild);
            }
            // Replace the chip-suggestion handler with a radiation
            // call so the empty's typing drives /api/radiation
            // instead of focal-centric apparitions (which would
            // require the empty to already have an embedding).
            const descInput = card.querySelector('.concept-desc-input');
            const valInput = card.querySelector('.concept-value-input');
            const wireRadiation = (input) => {
                if (!input) return;
                input.addEventListener('input', () => {
                    if (this._emptyRadiationTimer) clearTimeout(this._emptyRadiationTimer);
                    const text = (descInput && descInput.value) + ' ' + (valInput && valInput.value);
                    this._emptyRadiationTimer = setTimeout(async () => {
                        try {
                            const resp = await fetch('/api/radiation', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ text: text.trim(), k: 8, workspace_id: this._conceptWorkspaceId || '' }),
                            });
                            if (!resp.ok) return;
                            const data = await resp.json();
                            const cands = Array.isArray(data && data.candidates) ? data.candidates : [];
                            if (cands.length) this._renderApparitionHalo(card, cands);
                        } catch (_) { /* ignore */ }
                    }, 280);
                });
            };
            wireRadiation(descInput);
            wireRadiation(valInput);
        }
        return node;
    },

    /**
     * Create a concept node. Template's addNode(name, x, y) semantics:
     *   - empty name ⇒ id = `node_${Date.now()}`, node.name = id
     *   - non-empty name ⇒ id = slug(name), node.name = id (slug),
     *     but the displayed name-input value is the user's literal text
     *   - duplicate id ⇒ silent null
     */
    addConceptNode(name = '', x, y, opts = {}) {
        // §7.3.2 / §K.5 — ray-constrained placement when caller doesn't
        // pin x/y explicitly (the 2D analogue of the 3D UMAP-linear-radial
        // layout; this REPLACES the forbidden Fibonacci/concentric-ring
        // placement). ``opts.anchorId`` lets callers say "place this near
        // the focal/parent card"; otherwise the helper anchors to the
        // most-recently-touched card or the viewport centre. Auto-positions
        // are NOT user-positioned (no soft pin); the auto-layout can revisit
        // them on the next spawn.
        if (typeof x !== 'number' || typeof y !== 'number') {
            const pos = this._rayConstrainedPosition({ anchorId: opts.anchorId });
            if (typeof x !== 'number') x = pos.x;
            if (typeof y !== 'number') y = pos.y;
        }
        const id = name ? this._conceptSlugify(name) : `node_${Date.now()}`;
        if (this._conceptNodes.has(id)) return null;
        const node = {
            id,
            name: name || id,  // matches template line 76
            description: '',
            value: '',
            x, y,
        };
        this._conceptNodes.set(id, node);
        this._lastTouchedId = id;
        this._createConceptCard(node);
        // W4 / §8D.44 — immediate sync on create so the backend learns
        // the new id before any debounced edits race against it.
        this._scheduleConceptSync(id, { delay: 50 });
        return node;
    },

    /**
     * Build the DOM card for `node` and wire all of its inputs.
     *
     * The card shares its visual language with the pinned knowledge
     * panels in cp/billboard.js (dark backdrop, light text, coloured
     * left stripe + matching coloured header) so the 2D editor and
     * the 3D scene's pinned panels read as one tool. Each card gets a
     * per-id hash colour (same hash as the chunk-instance colours) so
     * a concept named ``risk`` always wears the same hue across
     * sessions.
     *
     * Critical: the drag handle is the COLOURED HEADER, not the whole
     * card. The previous whole-card mousedown handler called
     * preventDefault on every non-INPUT/TEXTAREA target — clicking on
     * the body's div / label / padding triggered that path and broke
     * the browser's focus chain so the value textarea was no longer
     * writable. Header-only drag mirrors pinBillboard's pattern,
     * which is known-good, and leaves body events completely alone.
     */
    // field_tree.md §4 / §9.6.1 / object_exploration.md — render a python-native
    // node's signature as the typed `key: Type` form (+ `→ ReturnType`) rather
    // than raw JSON. Falls back to the signature string / member list / raw data.
    _pythonNativeTypedView(rawData) {
        try {
            const d = JSON.parse(rawData);
            if (d && d.signature) {
                const sig = String(d.signature);
                const lines = [];
                const inputs = (d.ports && Array.isArray(d.ports.inputs)) ? d.ports.inputs : null;
                if (inputs) {
                    inputs.forEach(p => {
                        if (p && p.name && p.name !== 'self')
                            lines.push(`${p.name}: ${p.type || p.type_ref || p.annotation || '?'}`);
                    });
                } else {
                    const m = sig.match(/^\(([^)]*)\)/);
                    if (m) m[1].split(',').map(s => s.trim()).filter(s => s && s !== 'self').forEach(s => lines.push(s));
                }
                let out = '';
                if (d.ports && Array.isArray(d.ports.outputs) && d.ports.outputs[0])
                    out = d.ports.outputs[0].type || d.ports.outputs[0].type_ref || d.ports.outputs[0].annotation || '';
                if (!out) { const mo = sig.match(/->\s*(.+)$/); if (mo) out = mo[1].trim(); }
                if (out) lines.push(`→ ${out}`);
                return lines.length ? lines.join('\n') : sig;
            }
            if (d && Array.isArray(d.members))
                return d.members.map(mm => String(mm).split('::').pop()).join('\n');
            return rawData;
        } catch (_) { return rawData; }
    },

    // pattern_map_and_url_set.md §3.1.2 / §18.24 — a `pattern_map` node renders
    // ONE pattern_hash at a time under the signal-stream constraint, NEVER the
    // flat all-patterns list. Returns the pure-print of just the visible
    // pattern (golden trio + sampled-chunk count + sub-pattern count) and
    // mirrors the signal-stream position (field_path="pattern_hash") so peers
    // + the REPL viewer's pattern-map row (§11.8) track which pattern is shown.
    _patternMapSignalPrint(node, card) {
        let data;
        try { data = JSON.parse(node.value || node.data || '{}'); }
        catch (_) { return this._fieldTreePrint(node.value); }
        const patterns = (data && data.patterns) || {};
        const hashes = Object.keys(patterns);
        if (hashes.length === 0) return '(no patterns yet — scan to populate)';
        if (card._patternIdx == null) card._patternIdx = 0;
        card._patternIdx = ((card._patternIdx % hashes.length) + hashes.length) % hashes.length;
        const hash = hashes[card._patternIdx];
        const p = patterns[hash] || {};
        const acc = p.accessor_map || {};
        const trio = p.golden_trio || ['', '', ''];
        const samples = (p.sampled_chunks || []).length;
        const subs = Object.keys(p.sub_patterns || {}).length;
        if (typeof this._mirrorUi === 'function') {
            this._mirrorUi('/api/ui/signal_stream', {
                card_id: node.id, total: hashes.length,
                signal_index: card._patternIdx, signal_id: hash,
                field_path: 'pattern_hash',
            });
        }
        const L = [];
        L.push(`pattern_hash\t${hash}`);
        if (p.url_root) L.push(`url_root\t${p.url_root}`);
        if (p.generalized_xpath) L.push(`generalized_xpath\t${p.generalized_xpath}`);
        L.push('golden_trio');
        L.push(`\ttitle\t${acc[trio[0]] || trio[0] || '—'}`);
        L.push(`\tlink\t${acc[trio[1]] || trio[1] || '—'}`);
        L.push(`\tcontent\t${acc[trio[2]] || trio[2] || '—'}`);
        L.push(`sampled_chunks\t${samples}`);
        if (subs) L.push(`sub_patterns\t${subs}`);
        return L.join('\n');
    },

    // Attach a compact ‹ pattern i/N › stepper to a pattern_map card. Advancing
    // swaps the visible pattern IN PLACE (§3.1.2) + fires the signal-advance
    // mirror with field_path="pattern_hash" (pattern_map_and_url_set.md §5).
    _attachPatternMapStepper(card, node, valuePrint) {
        if (!card || card.querySelector('.concept-pattern-stepper')) return;
        let data; try { data = JSON.parse(node.value || node.data || '{}'); } catch (_) { return; }
        const n = Object.keys((data && data.patterns) || {}).length;
        if (n <= 1) return;  // a single (or zero) pattern needs no stepper
        const stepper = document.createElement('div');
        stepper.className = 'concept-pattern-stepper';
        stepper.style.cssText =
            'display:flex;gap:6px;align-items:center;font-size:10px;' +
            'padding:3px 6px;color:var(--text-dim,#9aa3ab);';
        const body = card.querySelector('.concept-card-body');
        if (body) body.insertBefore(stepper, body.firstChild);
        const INTERVAL_MS = 1500;
        // §7.5 / RolloutCoordinator — pause the auto-tick + fire the mirror.
        const pause = () => {
            if (card._patternPlayTimer) { clearInterval(card._patternPlayTimer); card._patternPlayTimer = null; }
            card._patternPlaying = false;
            if (typeof this._mirrorUi === 'function')
                this._mirrorUi('/api/rollout/pause', { card_id: node.id, field_path: 'pattern_hash' });
        };
        const render = () => {
            const total = Object.keys((JSON.parse(node.value || node.data || '{}').patterns) || {}).length;
            const playGlyph = card._patternPlaying ? '⏸' : '▶';
            stepper.innerHTML =
                `<button class="pstep-prev" style="background:none;border:none;color:#b8c0c8;cursor:pointer;">‹</button>` +
                `<span style="opacity:0.8;">pattern ${(card._patternIdx || 0) + 1} / ${total}</span>` +
                `<button class="pstep-next" style="background:none;border:none;color:#b8c0c8;cursor:pointer;">›</button>` +
                `<button class="pstep-play" title="Play / pause the pattern rollout" style="background:none;border:none;color:#b8c0c8;cursor:pointer;margin-left:6px;">${playGlyph}</button>`;
            const step = (delta) => {
                card._patternIdx = (card._patternIdx || 0) + delta;
                if (valuePrint) valuePrint.textContent = this._patternMapSignalPrint(node, card) || '(empty)';
                if (typeof this._mirrorUi === 'function')
                    this._mirrorUi('/api/ui/signal_advance', { card_id: node.id, step: delta, field_path: 'pattern_hash' });
                render();
            };
            // §3.2 — play = advance on a timer (frontend-driven cadence); it
            // stops when it wraps back to pattern 0 or the user pauses.
            const play = () => {
                card._patternPlaying = true;
                if (typeof this._mirrorUi === 'function')
                    this._mirrorUi('/api/rollout/play', { card_id: node.id, field_path: 'pattern_hash', interval_ms: INTERVAL_MS });
                card._patternPlayTimer = setInterval(() => {
                    const tot = Object.keys((JSON.parse(node.value || node.data || '{}').patterns) || {}).length;
                    step(1);
                    if (((card._patternIdx % tot) + tot) % tot === 0) pause();  // wrapped → stop
                }, INTERVAL_MS);
                render();
            };
            stepper.querySelector('.pstep-prev').addEventListener('click', () => { pause(); step(-1); });
            stepper.querySelector('.pstep-next').addEventListener('click', () => { pause(); step(1); });
            stepper.querySelector('.pstep-play').addEventListener('click', () => (card._patternPlaying ? pause() : play()));
        };
        render();
    },

    // pattern_map_and_url_set.md §3.2 — a `url_set` ({urls_panel}) node is a
    // multi-line pure-print list of URLs (§2), iterable once per URL under the
    // signal-stream constraint (§3.2.2 / §18.30 — never a bulk concatenated
    // scan). The list stays visible + editable at rest (§3.2.1); a ▸ cursor
    // marks the currently-iterated URL, mirrored as field_path="url".
    _urlSetSignalPrint(node, card) {
        const raw = String(node.value != null ? node.value : (node.data || ''));
        const urls = raw.split('\n')
            .map(s => s.replace(/\t+/g, '  ').replace(/\s+$/, ''))
            .filter(s => s.trim().length);
        if (urls.length === 0) return '(no URLs — type one per line)';
        if (card._urlIdx == null) card._urlIdx = 0;
        card._urlIdx = ((card._urlIdx % urls.length) + urls.length) % urls.length;
        if (typeof this._mirrorUi === 'function') {
            this._mirrorUi('/api/ui/signal_stream', {
                card_id: node.id, total: urls.length,
                signal_index: card._urlIdx, signal_id: urls[card._urlIdx],
                field_path: 'url',
            });
        }
        return urls.map((u, i) => (i === card._urlIdx ? `▸ ${u}` : `  ${u}`)).join('\n');
    },

    // ‹ url i/N › + ▶/⏸ stepper for a url_set card — one `advance` per URL
    // (§17.1.4 / §18.30), driving the backend RolloutCoordinator with
    // field_path="url" (parallel to the pattern_map stepper).
    _attachUrlSetStepper(card, node, valuePrint) {
        if (!card || card.querySelector('.concept-urlset-stepper')) return;
        const count = () => String(node.value != null ? node.value : (node.data || ''))
            .split('\n').filter(s => s.trim().length).length;
        if (count() <= 1) return;
        const stepper = document.createElement('div');
        stepper.className = 'concept-urlset-stepper';
        stepper.style.cssText =
            'display:flex;gap:6px;align-items:center;font-size:10px;' +
            'padding:3px 6px;color:var(--text-dim,#9aa3ab);';
        const body = card.querySelector('.concept-card-body');
        if (body) body.insertBefore(stepper, body.firstChild);
        const INTERVAL_MS = 1500;
        const pause = () => {
            if (card._urlPlayTimer) { clearInterval(card._urlPlayTimer); card._urlPlayTimer = null; }
            card._urlPlaying = false;
            if (typeof this._mirrorUi === 'function')
                this._mirrorUi('/api/rollout/pause', { card_id: node.id, field_path: 'url' });
        };
        const render = () => {
            const total = count();
            stepper.innerHTML =
                `<button class="ustep-prev" style="background:none;border:none;color:#b8c0c8;cursor:pointer;">‹</button>` +
                `<span style="opacity:0.8;">url ${(card._urlIdx || 0) + 1} / ${total}</span>` +
                `<button class="ustep-next" style="background:none;border:none;color:#b8c0c8;cursor:pointer;">›</button>` +
                `<button class="ustep-play" title="Play / pause the per-URL rollout" style="background:none;border:none;color:#b8c0c8;cursor:pointer;margin-left:6px;">${card._urlPlaying ? '⏸' : '▶'}</button>`;
            const step = (delta) => {
                card._urlIdx = (card._urlIdx || 0) + delta;
                if (valuePrint) valuePrint.textContent = this._urlSetSignalPrint(node, card) || '(empty)';
                if (typeof this._mirrorUi === 'function')
                    this._mirrorUi('/api/ui/signal_advance', { card_id: node.id, step: delta, field_path: 'url' });
                render();
            };
            const play = () => {
                card._urlPlaying = true;
                if (typeof this._mirrorUi === 'function')
                    this._mirrorUi('/api/rollout/play', { card_id: node.id, field_path: 'url', interval_ms: INTERVAL_MS });
                card._urlPlayTimer = setInterval(() => {
                    const tot = count();
                    step(1);
                    if (((card._urlIdx % tot) + tot) % tot === 0) pause();  // wrapped → stop
                }, INTERVAL_MS);
                render();
            };
            stepper.querySelector('.ustep-prev').addEventListener('click', () => { pause(); step(-1); });
            stepper.querySelector('.ustep-next').addEventListener('click', () => { pause(); step(1); });
            stepper.querySelector('.ustep-play').addEventListener('click', () => (card._urlPlaying ? pause() : play()));
        };
        render();
    },

    // field_tree.md §4 — pure-print a JSON data block as a tab-nested key:value
    // tree (no braces / brackets / quotes). Non-JSON data passes through as-is
    // (it is already the field-tree / template text the user typed).
    _fieldTreePrint(raw) {
        if (raw == null) return '';
        const s = String(raw).trim();
        if (!(s.startsWith('{') || s.startsWith('['))) return String(raw);
        let obj; try { obj = JSON.parse(s); } catch { return String(raw); }
        if (typeof obj !== 'object' || obj === null) return String(raw);
        const out = [];
        const walk = (v, depth, key) => {
            const pad = '\t'.repeat(depth);
            if (v !== null && typeof v === 'object') {
                if (key != null) out.push(`${pad}${key}:`);
                const arr = Array.isArray(v);
                const entries = arr ? v.map((x, i) => [String(i), x]) : Object.entries(v);
                for (const [k, val] of entries) walk(val, key != null ? depth + 1 : depth, arr ? null : k);
            } else {
                const scalar = (typeof v === 'string') ? v : JSON.stringify(v);
                out.push(key != null ? `${pad}${key}: ${scalar}` : `${pad}${scalar}`);
            }
        };
        if (Array.isArray(obj)) obj.forEach((x) => walk(x, 0, null));
        else Object.entries(obj).forEach(([k, v]) => walk(v, 0, k));
        return out.join('\n');
    },

    _createConceptCard(node) {
        // §S.4 BLACK SLATE — no per-card hue, no coloured header, no left
        // stripe. Every card is the same black slate with a thin silver
        // border and serif white text. (The former hash-hue stripe is a
        // forbidden concept now, §S.4.)
        const headerFg = 'var(--slate-border,#c0c0c0)';  // silver glyph accents

        const card = document.createElement('div');
        card.className = 'concept-card';
        card.dataset.nodeId = node.id;
        card.dataset.minimized = '';
        // Inline cssText mirrors pinBillboard's exact recipe so the
        // visual contract matches: same backdrop, same border, same
        // shadow, same coloured left stripe.
        // §S.4 BLACK SLATE — thin silver border, completely black infill, serif
        // white text. No coloured header, no left stripe, no chrome. The whole
        // slate is the drag handle (textareas exempted, §below). Only the
        // editable bordered slate; nothing else.
        card.style.cssText =
            `position:fixed; left:${node.x}px; top:${node.y}px; ` +
            `width:300px; ` +
            `background:#000; color:#ffffff; ` +
            `font-family:Georgia,'Times New Roman',serif; ` +
            `border:1px solid var(--slate-border,#c0c0c0); border-radius:6px; ` +
            `box-shadow:0 12px 32px rgba(0,0,0,0.55); ` +
            `display:flex; flex-direction:column; ` +
            `z-index:9990; overflow:hidden;`;

        // W19 / §8D.24 — small ↩ marker for memory-reference nodes,
        // empty for computed-value nodes. The marker is purely visual;
        // per-sample iteration (D3) will read the same classification
        // to decide which cards re-fire when stepping samples.
        const isMemoryRef = this._conceptClassifyMemoryRef(node);
        const memMarker = isMemoryRef
            ? `<span class="concept-memref-marker" title="Memory reference (does not change under per-sample iteration)" style="opacity:0.8;font-size:11px;margin-right:4px;color:${headerFg};">↩</span>`
            : '';
        card.dataset.memoryRef = isMemoryRef ? '1' : '0';

        // §S.4 — NO header bar, NO minimise, NO delete (×) button. The name is
        // a borderless serif field at the top of the slate; deletion is the
        // §N.13 double-right-click (no button); collapse-into-parent is the
        // §7.3.4 fold gesture. Affordances that remain (compile, grow +→/+↓)
        // are hidden-overlay controls over the slate, not a persistent bar.
        const _slateLabel = 'color:var(--slate-border,#c0c0c0);font-family:Georgia,serif;font-size:9px;letter-spacing:0.04em;opacity:0.7;';
        card.innerHTML = `
            <div class="concept-card-body">
                ${memMarker}<input class="concept-name-input" placeholder="" value="${this._conceptEscapeHtml(node.name)}" style="background:transparent;border:none;outline:none;color:#fff;font-family:Georgia,serif;font-size:14px;font-weight:600;width:100%;padding:2px 0;">
                <textarea class="concept-desc-input" rows="2" placeholder="" style="background:transparent;border:none;outline:none;color:#fff;font-family:Georgia,serif;resize:none;width:100%;">${this._conceptEscapeHtml(node.description)}</textarea>
                <div class="concept-suggestions" style="display:none;"></div>
                <textarea class="concept-value-input" rows="4" placeholder="" style="background:transparent;border:none;outline:none;color:#fff;font-family:Georgia,serif;resize:none;width:100%;">${this._conceptEscapeHtml(node.value)}</textarea>
                <div class="concept-grow-row" style="display:none;gap:4px;margin-top:-2px;">
                    <button class="concept-grow-child" type="button" title="+→ add a CHILD row (indented one level) — field-tree growth (§4.6/§6.2)" style="font-size:10px;padding:1px 7px;background:#000;border:1px solid var(--slate-border,#c0c0c0);color:#fff;border-radius:3px;cursor:pointer;font-family:Georgia,serif;">+→</button>
                    <button class="concept-grow-sibling" type="button" title="+↓ add a SIBLING row (same level) — field-tree growth (§4.6/§6.2)" style="font-size:10px;padding:1px 7px;background:#000;border:1px solid var(--slate-border,#c0c0c0);color:#fff;border-radius:3px;cursor:pointer;font-family:Georgia,serif;">+↓</button>
                </div>
                <pre class="concept-value-print" title="Click to edit the field-tree" style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:12px;white-space:pre-wrap;word-break:break-word;color:#fff;background:transparent;border:none;padding:2px 0;min-height:16px;cursor:text;"></pre>
                <div class="concept-compiled-preview"></div>
                <button class="concept-compile-btn" style="display:none;">Compile</button>
                <button class="concept-inverse-btn" style="display:none;" title="W27 / §8D.7">↩ inverse</button>
            </div>
        `;

        const header     = card.querySelector('.concept-card-header');
        const nameInput  = card.querySelector('.concept-name-input');
        const descInput  = card.querySelector('.concept-desc-input');
        const valueInput = card.querySelector('.concept-value-input');
        const valuePrint = card.querySelector('.concept-value-print');
        const compileBtn = card.querySelector('.concept-compile-btn');
        const inverseBtn = card.querySelector('.concept-inverse-btn');
        const growChild   = card.querySelector('.concept-grow-child');
        const growSibling = card.querySelector('.concept-grow-sibling');
        // field_tree.md §6.2 — plus-sign growth. +→ appends a CHILD row (one tab
        // deeper than the last line); +↓ appends a SIBLING row at the last line's
        // indent. Each new row is a real field; field-tree growth IS the
        // promotion (§4.6) — there is no separate "promote to panel" affordance.
        const _growRow = (asChild) => {
            const v = valueInput.value;
            const lines = v.split('\n');
            const indent = ((lines[lines.length - 1] || '').match(/^\t*/) || [''])[0];
            const newLine = (asChild ? indent + '\t' : indent) + 'key: ';
            valueInput.value = (v && !v.endsWith('\n')) ? v + '\n' + newLine : v + newLine;
            valueInput.focus();
            valueInput.selectionStart = valueInput.selectionEnd = valueInput.value.length;
            valueInput.dispatchEvent(new Event('input'));
        };
        if (growChild)   growChild.addEventListener('click',   (ev) => { ev.stopPropagation(); _growRow(true); });
        if (growSibling) growSibling.addEventListener('click', (ev) => { ev.stopPropagation(); _growRow(false); });
        // concept_view.md §4 / §18.22 / §8D.4.2 — foundation fixtures and
        // read-only python-native nodes are UNDELETABLE and non-editable: omit
        // the × (show 🔒), make the fields read-only, and hide field-tree growth.
        const ro = /^fixture::/.test(node.backing_pointer || '') || /^python_/.test(node.type_hint || '');
        if (ro) {
            // §S.4 — there is no ✕ button to hide; show the 🔒 read-only
            // indicator as a small prefix on the name field inside the slate.
            const _bodyEl = card.querySelector('.concept-card-body');
            if (_bodyEl && !_bodyEl.querySelector('.concept-readonly-lock')) {
                const lock = document.createElement('span');
                lock.className = 'concept-readonly-lock';
                lock.textContent = '🔒';
                lock.title = 'Read-only (foundation fixture / python-native) — §8D.4.2';
                lock.style.cssText = 'color:var(--slate-border,#c0c0c0);font-size:11px;line-height:1;margin-right:4px;';
                _bodyEl.insertBefore(lock, _bodyEl.firstChild);
            }
            [nameInput, descInput, valueInput].forEach(el => { if (el) { el.readOnly = true; el.title = 'Read-only (§8D.4.2)'; } });
            const _gr = card.querySelector('.concept-grow-row'); if (_gr) _gr.style.display = 'none';
            // §9.6.1 — python-native nodes show their signature as the typed
            // `key: Type = value` form (object_exploration.md), not raw JSON.
            if (/^python_/.test(node.type_hint || '') && valueInput) {
                const _typed = this._pythonNativeTypedView(node.value || node.data || '');
                if (_typed) valueInput.value = _typed;
            }
        }
        const preview    = card.querySelector('.concept-compiled-preview');
        const deleteBtn  = card.querySelector('.concept-delete-btn');
        const minBtn     = card.querySelector('.concept-min-btn');

        // §8D.12 — foundation fixtures are structural pillars; the user
        // cannot delete them. Hide the X button outright so the click
        // path can't even attempt a 409 round-trip. Backend still guards
        // (defense in depth) but the UI shouldn't lead the user to a
        // dead end.
        if (node.id && String(node.id).startsWith('fixture::')) {
            if (deleteBtn) deleteBtn.style.display = 'none';
        }

        // §8D.7 — Inverse is now FUSED into Compile (the backend response
        // carries `inverse_candidates` alongside the rendering). Hide the
        // standalone INVERSE button so we don't suggest a two-step flow
        // when one click does both.
        if (inverseBtn) inverseBtn.style.display = 'none';

        // §8D.20 — surface the backend-derived rendering on first
        // mount so the user sees the syntax-free tree immediately
        // (no need to press Compile to view a hydrated card).
        if (preview && node.rendering) {
            preview.textContent = node.rendering;
            preview.style.display = 'block';
        }

        // ── Rename handler ── template lines 112-135 + the one fix
        // for the stale `data-node-id` attribute on the renamed card.
        nameInput.addEventListener('input', () => {
            const oldId   = node.id;
            const newName = nameInput.value.trim() || oldId;
            const newId   = this._conceptSlugify(newName);
            if (newId !== oldId && !this._conceptNodes.has(newId)) {
                this._conceptNodes.delete(oldId);
                node.id   = newId;
                node.name = newId;
                this._conceptNodes.set(newId, node);
                // Latent-template-bug fix: keep this card's dataset
                // in sync so subsequent edge lookups find it.
                card.dataset.nodeId = newId;
                this._conceptEdges.forEach(e => {
                    if (e.source === oldId) e.source = newId;
                    if (e.target === oldId) e.target = newId;
                });
                // Rewrite {oldId} → {newId} (case-insensitive) in
                // every other node's value and update its <textarea>
                // so the user sees the rename ripple through the
                // graph (template lines 122-130).
                this._conceptNodes.forEach(n => {
                    if (n.id !== newId) {
                        const re = new RegExp(
                            `\\{${this._conceptEscapeRegex(oldId)}\\}`, 'gi'
                        );
                        if (re.test(n.value)) {
                            n.value = n.value.replace(re, `{${newId}}`);
                            const c = document
                                .querySelector(`.concept-card[data-node-id="${n.id}"]`);
                            if (c) c.querySelector('.concept-value-input').value = n.value;
                        }
                    }
                });
            }
            // node.name is ALWAYS set to the slug — template line 133.
            node.name = newId;
            this._drawConceptEdges();
            // Fix: previous implementation did DELETE-old + CREATE-new
            // on every id change, which orphaned every backend
            // ConceptEdge row referencing the old concept_id. The
            // correct contract per §8D.44 is: the concept_id is the
            // stable storage identifier; the display name (and the
            // user-facing slug) can change without touching the id.
            // The frontend Map *does* re-key locally so the
            // {var} substitution machinery (§8D.21) works on slugs,
            // but the backend record keeps its original id, and we
            // PATCH its name field only. We track the original id
            // on the card's dataset so subsequent renames continue
            // to address the same backend record.
            if (!card.dataset.backendConceptId) {
                card.dataset.backendConceptId = oldId;
            }
            this._scheduleConceptSync(node.id, { backendId: card.dataset.backendConceptId });
        });

        // ── Description handler ── retrieval suggestions + curly-
        // brace reference parsing. The user spec extends `{var}`
        // linking from value-only to description-as-well, so a
        // user can sketch a concept like
        //   description: "computed via {scanner}, fed into {agent}"
        // and have the editor auto-create `scanner` + `agent` cards
        // (or wire edges to existing ones) the same way the value
        // field does.
        descInput.addEventListener('input', () => {
            node.description = descInput.value;
            // Parse {var} refs in the description. _parseConceptReferences
            // walks the node's `value` by default — we temporarily
            // splice the description into the parse so the same
            // dedup/auto-create/edge-add logic applies, then restore
            // the value so the parser doesn't lose the user's data field.
            this._parseConceptReferencesIn(node, 'description');
            const prev = this._conceptSuggestTimers.get(node.id);
            if (prev) clearTimeout(prev);
            const handle = setTimeout(() => {
                this._renderConceptSuggestions(card, node);
            }, 220);
            this._conceptSuggestTimers.set(node.id, handle);
            this._drawConceptEdges();
            this._scheduleConceptSync(node.id);  // W4 / §8D.44
        });

        // ── Value handler (the CRITICAL one in the template) ──
        // Parses {var} references on every keystroke; auto-creates
        // missing target nodes; rebuilds outgoing edges from this node.
        valueInput.addEventListener('input', () => {
            node.value = valueInput.value;
            // §8D.10 — typing into a card flags it as the focal so
            // the next auto-spawn anchors near it (attention follows
            // most-recent edit).
            this._lastTouchedId = node.id;
            this._parseConceptReferences(node);
            this._drawConceptEdges();
            this._scheduleConceptSync(node.id);  // W4 / §8D.44
        });
        // §9.4 edit-safety — mirror edit_open/close so the cascade + reconciler
        // know this field is being edited (don't clobber it) and peer tabs/REPL
        // see the open editor.
        valueInput.addEventListener('focus', () => {
            if (typeof this._mirrorUi === 'function')
                this._mirrorUi('/api/ui/edit_open', { card_id: node.id, field_path: 'value', value_so_far: valueInput.value });
        });
        valueInput.addEventListener('blur', () => {
            if (typeof this._mirrorUi === 'function')
                this._mirrorUi('/api/ui/edit_close', { card_id: node.id });
            // §R.5 — the live markdown gesture: committing an edit on a node
            // whose panel is already decomposed into its computation-graph
            // representation re-runs the syntax-agnostic decompose, so dash/
            // tab/number/newline gestures restructure the graph side in place
            // (children re-derive; the parent re-rewrites to {child} refs).
            if (node._decomposed && !ro) {
                try { this._decomposeValue(node); } catch (_) { /* best-effort */ }
            }
            // field_tree.md §4/§5 — return to the pure-print view on commit.
            if (valuePrint && !ro) {
                valuePrint.textContent = (node.type_hint === 'pattern_map')
                    ? (this._patternMapSignalPrint(node, card) || '(empty)')
                    : (node.type_hint === 'url_set')
                        ? (this._urlSetSignalPrint(node, card) || '(empty)')
                        : (this._fieldTreePrint(node.value) || '(empty)');
                valuePrint.style.display = 'block';
                valueInput.style.display = 'none';
                const _g = card.querySelector('.concept-grow-row'); if (_g) _g.style.display = 'none';
            }
        });
        // field_tree.md §4.1.1 — CLICK-TO-EDIT: the value shows as a pure-print
        // field-tree at rest (§4 print / §5 project); clicking it reveals the
        // editable surface (the raw textarea + plus-signs). Read-only nodes keep
        // the print view only. node.value / compile / sync are unchanged.
        if (valuePrint) {
            if (node.type_hint === 'pattern_map') {
                // §3.1.2 — one pattern_hash at a time + the ‹ i/N › stepper.
                valuePrint.textContent = this._patternMapSignalPrint(node, card) || '(empty)';
                this._attachPatternMapStepper(card, node, valuePrint);
            } else if (node.type_hint === 'url_set') {
                // §3.2 — the URL list with a ▸ per-URL signal cursor + stepper.
                valuePrint.textContent = this._urlSetSignalPrint(node, card) || '(empty)';
                this._attachUrlSetStepper(card, node, valuePrint);
            } else {
                valuePrint.textContent = (ro ? valueInput.value : this._fieldTreePrint(node.value)) || '(empty)';
            }
            valueInput.style.display = 'none';
            const _g0 = card.querySelector('.concept-grow-row'); if (_g0) _g0.style.display = 'none';
            if (!ro) {
                valuePrint.addEventListener('click', () => {
                    valuePrint.style.display = 'none';
                    valueInput.style.display = '';
                    const _g = card.querySelector('.concept-grow-row'); if (_g) _g.style.display = 'flex';
                    valueInput.focus();
                });
            } else {
                valuePrint.style.cursor = 'default';
                valuePrint.title = 'Read-only (§8D.4.2)';
            }
            // §7.3.4 / object_exploration — RIGHT-CLICK a {ref} token in the
            // print fires an inline node-fold (rank-1 reveal) through the
            // node_fold mirror; right-clicking elsewhere falls through to the
            // panel's compile/fold gesture. The token under the caret is
            // detected from the print text; a miss is a no-op (no preventDefault).
            valuePrint.addEventListener('contextmenu', (ev) => {
                const text = valuePrint.textContent || '';
                let offset = -1;
                try {
                    if (document.caretRangeFromPoint) {
                        const r = document.caretRangeFromPoint(ev.clientX, ev.clientY);
                        if (r) offset = r.startOffset;
                    } else if (document.caretPositionFromPoint) {
                        const p = document.caretPositionFromPoint(ev.clientX, ev.clientY);
                        if (p) offset = p.offset;
                    }
                } catch (_) { offset = -1; }
                if (offset < 0) return;
                let tok = null;
                const re = /\{([^{}]+)\}/g;
                let m;
                while ((m = re.exec(text))) {
                    if (offset >= m.index && offset <= m.index + m[0].length) {
                        tok = m[1];
                        break;
                    }
                }
                if (!tok) return;  // not on a {ref} token → let compile fire
                ev.preventDefault();
                ev.stopPropagation();
                card._nodeFold = card._nodeFold || {};
                card._nodeFold[tok] = !card._nodeFold[tok];
                if (typeof this._mirrorUi === 'function')
                    this._mirrorUi('/api/ui/node_fold', {
                        card_id: node.id, field_path: tok,
                        expanded: !!card._nodeFold[tok],
                    });
            });
        }
        // field_tree.md §6.1 / N.12 — intelligent multiline tree editing: Tab
        // indents at the caret (no focus loss); plain Enter auto-indents the new
        // line to match the current line's leading tabs (markdown-like), so
        // multi-`{ref}` templates stay legible without escaped-newline glyphs.
        // (Shift+Enter keeps the textarea's default newline.)
        valueInput.addEventListener('keydown', (ev) => {
            if (ev.key === 'Tab') {
                ev.preventDefault();
                const s = valueInput.selectionStart, e = valueInput.selectionEnd, v = valueInput.value;
                valueInput.value = v.slice(0, s) + '\t' + v.slice(e);
                valueInput.selectionStart = valueInput.selectionEnd = s + 1;
                valueInput.dispatchEvent(new Event('input'));
            } else if (ev.key === 'Enter' && !ev.shiftKey && !ev.ctrlKey && !ev.metaKey) {
                const s = valueInput.selectionStart, v = valueInput.value;
                const lineStart = v.lastIndexOf('\n', s - 1) + 1;
                const indent = (v.slice(lineStart, s).match(/^\t*/) || [''])[0];
                if (indent) {
                    ev.preventDefault();
                    valueInput.value = v.slice(0, s) + '\n' + indent + v.slice(valueInput.selectionEnd);
                    valueInput.selectionStart = valueInput.selectionEnd = s + 1 + indent.length;
                    valueInput.dispatchEvent(new Event('input'));
                }
            }
        });

        // ── Compile ── template lines 147-150
        // Extended: if the current value parses as JSON, first
        // decompose it into one child card per top-level key/index
        // and rewrite the value as a reference template. Subsequent
        // clicks then recompose the original JSON through the normal
        // `{var}` substitution path. Plain HTML / text values
        // compile directly with no decomposition.
        compileBtn.addEventListener('click', async () => {
            // Fix: guard against double-click race. The cypher
            // pre-pass is async; a second click before the first
            // resolves would decompose the JSON twice (creating
            // duplicate child cards) AND issue duplicate sync
            // POSTs. The in-flight flag short-circuits and a
            // disabled-button visual marks the state.
            if (compileBtn._compiling) return;
            compileBtn._compiling = true;
            const prevBg = compileBtn.style.background;
            const prevDis = compileBtn.disabled;
            compileBtn.disabled = true;
            compileBtn.style.opacity = '0.6';
            try {
            // D1 / §8D.2.1 — pre-pass the data block through the backend
            // compile pipeline so cypher patterns get resolved against
            // Kuzu before the local decompose + {var} substitution
            // runs. If the backend is unreachable or returns no
            // rewrites, we proceed with the original value.
            let trace = null;
            if (this._conceptBackendOk && node.value) {
                // Fix: snapshot the value BEFORE the await so we can
                // detect a concurrent user edit on return. If the
                // user typed into the field while the cypher pipeline
                // was running, we must NOT clobber their changes with
                // the stale-input rewrite. The trace still surfaces.
                const valueAtSubmit = node.value;
                try {
                    const resp = await fetch('/api/compile_pipeline', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text: valueAtSubmit, workspace_id: this._conceptWorkspaceId || '' }),
                    });
                    if (resp.ok) {
                        const data = await resp.json();
                        const userEditedDuringCompile = (node.value !== valueAtSubmit);
                        if (data && typeof data.rewritten === 'string'
                            && data.rewritten !== valueAtSubmit
                            && !userEditedDuringCompile) {
                            node.value = data.rewritten;
                            const ta = card.querySelector('.concept-value-input');
                            if (ta) ta.value = data.rewritten;
                            // Persist the rewritten value.
                            this._scheduleConceptSync(node.id, { delay: 50 });
                        } else if (userEditedDuringCompile) {
                            // User typed during compile — log a debug
                            // hint, keep their edit, skip the rewrite.
                            console.debug('[compile] user edit during compile detected; rewrite suppressed');
                        }
                        trace = Array.isArray(data && data.trace) ? data.trace : null;
                    }
                } catch (e) {
                    // Backend unreachable or pipeline error — fall back
                    // to local-only compile. Not fatal.
                }
            }
            // §7.1 / §18.15 — syntax-agnostic decompose (JSON OR native
            // indented field-tree), not JSON-only.
            this._decomposeValue(node);
            preview.style.display = 'block';
            preview.textContent = this._compileConceptNode(node.id);
            // H1 / §6.6.4 — if this node participates in a {ref}-linked graph,
            // materialise its 3D compute-graph overlay (bisector node + link
            // network) via the backend. Fire-and-forget; the projector renders
            // the resulting compute_graph_layout frame.
            if (this._conceptEdges &&
                this._conceptEdges.some(e => e.source === node.id || e.target === node.id) &&
                typeof this._requestComputeGraphOverlay === 'function') {
                this._requestComputeGraphOverlay(node.id);
            }
            // W31 / §8C.7 / §8D.5 — also run the ConceptComputeNode
            // primitive on the backend so the kind-dispatch (plain /
            // prompt / structured / python) fires and the SLM gets
            // called (when the card declares a prompt). The returned
            // rendering replaces our local tree-print whenever it
            // differs — the server-side compile is the authoritative
            // one (it resolves {ref}s against the persisted graph,
            // not the in-memory frontend cache).
            //
            // Best-effort: never throw, never block the local compile
            // path. Backend unreachable → keep the local rendering.
            if (this._conceptBackendOk && node.id) {
                try {
                    const ccResp = await fetch('/api/conceptual/compile', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            concept_id: node.id,
                            use_slm:    true,
                            persist_rendering: true,
                        }),
                    });
                    if (ccResp.ok) {
                        const ccData = await ccResp.json();
                        if (ccData && typeof ccData.rendering === 'string'
                            && ccData.rendering.length) {
                            // Surface the authoritative rendering. The
                            // user can see the kind that fired in the
                            // small trailing badge.
                            preview.textContent = ccData.rendering;
                            // Show the dispatch kind as a tiny chip so
                            // the user can tell whether their card was
                            // recognised as prompt / structured / python /
                            // plain — the same way the cypher trace
                            // surfaces detection.
                            let kindEl = card.querySelector('.concept-compute-kind');
                            if (!kindEl) {
                                kindEl = document.createElement('div');
                                kindEl.className = 'concept-compute-kind';
                                kindEl.style.cssText =
                                    'margin:4px 8px 0;padding:2px 6px;' +
                                    'border-radius:3px;font-size:10px;' +
                                    'font-family:monospace;display:inline-block;';
                                preview.parentNode.insertBefore(kindEl, preview);
                            }
                            const kindColours = {
                                plain:      'rgba(99,102,241,0.15)',
                                prompt:     'rgba(217,119,6,0.18)',
                                structured: 'rgba(34,197,94,0.18)',
                                python:     'rgba(184,192,200,0.18)',
                            };
                            kindEl.style.background = kindColours[ccData.kind] || 'rgba(184,192,200,0.15)';
                            kindEl.style.color      = '#d7dde2';
                            kindEl.textContent      = `kind: ${ccData.kind}`;
                        }
                    }
                } catch (_) {
                    // Backend reachable but compute endpoint missing or
                    // erroring — surface nothing extra, keep local render.
                }
            }
            // W26 / §8D.2.1 — surface cypher detection trace.
            if (trace && trace.length) {
                let traceEl = card.querySelector('.concept-compile-trace');
                if (!traceEl) {
                    traceEl = document.createElement('div');
                    traceEl.className = 'concept-compile-trace';
                    traceEl.style.cssText =
                        'margin:6px 8px;padding:6px;border-radius:4px;' +
                        'background:rgba(99,102,241,0.1);font-size:10px;' +
                        'font-family:monospace;color:#b8c0c8;';
                    preview.parentNode.insertBefore(traceEl, preview);
                }
                traceEl.innerHTML = `
                    <div style="opacity:0.7;font-size:9px;margin-bottom:4px;">cypher detection trace:</div>
                    ${trace.map(t => {
                        const status = t.ok ? '✓' : '✗';
                        const colour = t.ok ? '#b8c0c8' : '#b25b5b';
                        const segPreview = (t.segment || '').slice(0, 60).replace(/\n/g, ' ');
                        const detail = t.ok
                            ? `${t.rows_count || 0} rows`
                            : (t.error || 'error');
                        return `<div style="margin-bottom:2px;"><span style="color:${colour};">${status}</span> <span style="color:#d7dde2;">${this._conceptEscapeHtml(segPreview)}</span> — <span style="opacity:0.7;">${this._conceptEscapeHtml(detail)}</span></div>`;
                    }).join('')}
                `;
            } else {
                const traceEl = card.querySelector('.concept-compile-trace');
                if (traceEl && traceEl.parentNode) traceEl.parentNode.removeChild(traceEl);
            }
            } finally {
                // Fix: always release the in-flight guard so the user
                // can click Compile again on the next interaction,
                // even if cypher-detect / decompose threw mid-way.
                compileBtn._compiling = false;
                compileBtn.disabled = prevDis;
                compileBtn.style.opacity = '';
                compileBtn.style.background = prevBg;
            }
        });

        // W27 / §8D.7 — Inverse: given this card as desired output,
        // surface inputs that would produce it.
        if (inverseBtn) {
            inverseBtn.addEventListener('click', async () => {
                if (!this._conceptBackendOk) return;
                const ws = this._conceptWorkspaceId || '';
                const params = new URLSearchParams({ k: '8' });
                if (ws) params.set('workspace_id', ws);
                try {
                    const resp = await fetch(`/api/closest_inverse/${encodeURIComponent(node.id)}?${params.toString()}`);
                    if (!resp.ok) return;
                    const data = await resp.json();
                    const cands = Array.isArray(data && data.candidates) ? data.candidates : [];
                    if (cands.length) this._renderApparitionHalo(card, cands);
                } catch (_) { /* ignore */ }
            });
        }

        // ── Delete ── §S.4: no ✕ button — deletion is the §N.13 double-right-
        // click only. The logic lives in a closure (the button is gone).
        const doDeleteCard = () => {
            const deletedId = node.id;
            this._conceptNodes.delete(deletedId);
            this._conceptEdges = this._conceptEdges.filter(
                e => e.source !== deletedId && e.target !== deletedId
            );
            const t = this._conceptSuggestTimers.get(deletedId);
            if (t) { clearTimeout(t); this._conceptSuggestTimers.delete(deletedId); }
            card.remove();
            this._drawConceptEdges();
            // W4 / §8D.44 — issue authoritative DELETE to the backend.
            this._deleteConceptFromBackend(deletedId);
        };
        if (deleteBtn) deleteBtn.addEventListener('click', doDeleteCard);  // legacy guard (button removed)

        // §7.3.4 / §N.13 — DOUBLE-RIGHT-CLICK deletes the card (two right-clicks
        // within 400ms). A single right-click on the card body is swallowed (no
        // native menu) so the double can resolve. Interactive targets keep their
        // native menu (copy/paste in fields). There is no ✕ button (§S.4).
        card.addEventListener('contextmenu', (ev) => {
            if (isInteractive(ev.target)) return;
            ev.preventDefault();
            if (ro) return;   // §18.22 — read-only fixtures / python-native are undeletable
            const now = Date.now();
            if (card._lastCtx && (now - card._lastCtx) < 400) { card._lastCtx = 0; doDeleteCard(); }
            else { card._lastCtx = now; }
        });

        // ── Collapse-into-parent (§S.5) ── §S.4 removed the minimise button;
        // the collapse gesture (fold the panel into its parent field
        // computation node — the value-only rank-1 form) is reached through the
        // §7.3.4 fold gestures, not a chrome button. `_toggleConceptMinimize`
        // stays callable for those paths.
        if (minBtn) minBtn.addEventListener('click', (ev) => {
            ev.stopPropagation();
            this._toggleConceptMinimize(card);
        });

        // ── Drag (WHOLE CARD, with input/textarea/button exclusions) ──
        // Any non-interactive child of the card initiates drag —
        // header, labels, body padding, even the dark body background
        // — so the user can grab the card from anywhere it isn't
        // already a typing surface. Inputs, textareas, buttons, and
        // selects early-return BEFORE preventDefault runs, so the
        // browser's natural focus chain delivers them keystrokes
        // unmodified. This is the breakage the previous attempt had:
        // it called preventDefault on labels and div padding, which
        // can silently block textarea focus when adjacent to inputs.
        let isDragging = false, startX = 0, startY = 0, origLeft = 0, origTop = 0;
        const DRAG_SKIP_TAGS = new Set(['INPUT', 'TEXTAREA', 'BUTTON', 'SELECT']);
        const isInteractive = (t) => {
            if (!t) return false;
            if (DRAG_SKIP_TAGS.has(t.tagName)) return true;
            // Skip if the target is *inside* an interactive element
            // (e.g. the user clicked the placeholder text of a
            // textarea — the click target may be the textarea itself,
            // but checking ancestors keeps us safe against nested
            // elements like <i> icons inside buttons).
            if (t.closest && (
                t.closest('input') ||
                t.closest('textarea') ||
                t.closest('button') ||
                t.closest('select')
            )) return true;
            return false;
        };
        card.addEventListener('mousedown', (ev) => {
            // Always promote z-order on any engagement so the
            // recently-touched card sits above its peers.
            const z = String(this._nextConceptZ());
            if (card.style.zIndex !== z) card.style.zIndex = z;
            // If the user clicked on an interactive element, leave
            // the browser's default behaviour alone (focus the input
            // or fire the button). No preventDefault here.
            if (isInteractive(ev.target)) return;
            // Otherwise treat this as a drag-start.
            ev.preventDefault();
            isDragging = true;
            startX = ev.clientX;
            startY = ev.clientY;
            const r = card.getBoundingClientRect();
            origLeft = r.left;
            origTop  = r.top;
            card.style.cursor = 'grabbing';
        });
        // §7.3.4 — DOUBLE-LEFT-CLICK toggles panel↔graph. For a concept card
        // the "graph form" is its compile/decompose into child cards, so the
        // dbl-click fires the same path as the Compile button (additive; the
        // explicit button stays). Interactive targets are skipped so field
        // edits and buttons keep working.
        card.addEventListener('dblclick', (ev) => {
            if (isInteractive(ev.target)) return;
            ev.preventDefault();
            if (compileBtn && !compileBtn._compiling) compileBtn.click();
        });
        document.addEventListener('mousemove', (ev) => {
            if (!isDragging) return;
            const dx = ev.clientX - startX;
            const dy = ev.clientY - startY;
            card.style.left = (origLeft + dx) + 'px';
            card.style.top  = (origTop  + dy) + 'px';
            node.x = origLeft + dx;
            node.y = origTop  + dy;
            this._drawConceptEdges();
        });
        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                card.style.cursor = '';
                // §8D.10 — user-positioned cards are soft-pinned; the
                // Fibonacci auto-layout flows around them on the next
                // anchor recompute. Also tracks last-touched so the
                // next auto-spawn anchors near the card the user just
                // moved (matches the spec's "attention follows the
                // most-recent edit" intent).
                this._markUserPositioned(node.id);
                this._lastTouchedId = node.id;
                // W4 / §8D.44 — persist new layout_xy on drag-end.
                this._scheduleConceptSync(node.id);
            }
        });

        // W32 / §8C.3 — drag-from-port edge wiring.
        // A small ⚪ "port handle" sits on the right edge of each
        // card. Mousedown on it begins a drag; a rubber-band SVG
        // line follows the cursor. Mouseup over another card draws
        // a typed edge (RELATES_TO by default; user can change it
        // via the edge context menu in W33). The port handle is
        // pointer-events: auto so it doesn't trigger the card's
        // drag-to-move handler.
        const portHandle = document.createElement('div');
        portHandle.className = 'concept-port-handle';
        portHandle.title = 'Drag to another card to wire a new edge';
        portHandle.style.cssText =
            'position:absolute; right:-8px; top:50%; transform:translateY(-50%);' +
            'width:16px; height:16px; border-radius:50%;' +
            // §S.4 — silver-on-black port handle (no per-card hue).
            'background:#000; border:2px solid var(--slate-border,#c0c0c0);' +
            'cursor:crosshair; pointer-events:auto; z-index:10001;' +
            'box-shadow:0 2px 6px rgba(0,0,0,0.4);';
        card.appendChild(portHandle);
        portHandle.addEventListener('mousedown', (ev) => {
            ev.stopPropagation();
            ev.preventDefault();
            this._beginPortDrag(node, card, ev.clientX, ev.clientY);
        });

        // W13 / §8D.16 — hover-on-stuck-card surfaces an apparition
        // halo. The halo fades on mouseleave so the user can move
        // freely without phantoms accumulating. Debounced 200 ms so
        // a fast cursor pass doesn't fire a request per pixel.
        // W23 — also stamps a debug tooltip from the cached
        // ConceptIndex slot (pagerank + similar_to neighbour ids).
        let haloTimer = null;
        card.addEventListener('mouseenter', () => {
            // W23 — populate the card's native title attribute with
            // the latest ConceptIndex slot data so a hover-stalled
            // cursor shows pagerank + top similar_to neighbours.
            if (this._conceptIndexCache && this._conceptIndexCache.has(node.id)) {
                const slot = this._conceptIndexCache.get(node.id) || {};
                const pr = (typeof slot.pagerank === 'number') ? slot.pagerank.toFixed(4) : '?';
                const sim = Array.isArray(slot.similar_to) ? slot.similar_to.slice(0, 5).join(', ') : '';
                const prov = slot.provenance || node.provenance || 'unknown';
                card.title =
                    `pagerank ${pr} · provenance ${prov}` +
                    (sim ? `\nsimilar_to: ${sim}` : '');
            }
            if (!this._conceptBackendOk) return;
            // §UnifiedNodeView — echo the hover to the mirror so the
            // 2D concept card and the 3D chunk billboard share one
            // hover/click contract. The REPL reads /ui/node_state to
            // assert presentation state without screen-scraping.
            try {
                fetch('/api/ui/hover', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        workspace_id: this._conceptWorkspaceId || '',
                        node_id:      node.id,
                    }),
                }).catch(()=>{});
                // Also record where the hover preview will land (the
                // card's current screen rect) so Mortegon §1.2 stick-
                // rect parity carries over to 2D card → 3D billboard
                // transitions on the same canvas.
                const r = card.getBoundingClientRect();
                fetch('/api/ui/hover_rect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        workspace_id: this._conceptWorkspaceId || '',
                        rect: { top: r.top, left: r.left, width: r.width, height: r.height },
                    }),
                }).catch(()=>{});
            } catch (_) {}
            if (haloTimer) clearTimeout(haloTimer);
            haloTimer = setTimeout(async () => {
                try {
                    const cands = await this._fetchApparitionsForFocal(node.id, 6);
                    if (cands && cands.length) {
                        this._renderApparitionHalo(card, cands);
                    }
                } catch (_) { /* ignore */ }
            }, 200);
        });
        card.addEventListener('mouseleave', (ev) => {
            if (haloTimer) clearTimeout(haloTimer);
            // Echo hover-clear to the mirror (§UnifiedNodeView).
            try {
                fetch('/api/ui/hover', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        workspace_id: this._conceptWorkspaceId || '',
                        node_id:      null,
                    }),
                }).catch(()=>{});
            } catch (_) {}
            // Only clear the halo if the mouse is leaving the card
            // AND not entering a phantom (phantoms are
            // pointer-events:auto and the user may want to click
            // one). The halo's own phantoms have their own mouseenter
            // that holds the halo alive until clicked or dismissed.
            const to = ev.relatedTarget;
            if (to && to.classList && to.classList.contains('concept-apparition-phantom')) return;
            // Defer clearance a tick so phantom mouseenter can claim
            // the halo if the cursor is racing across the gap.
            setTimeout(() => {
                if (!document.querySelector('.concept-apparition-phantom:hover')) {
                    this._clearApparitionHalo();
                }
            }, 120);
        });

        // Host: document.body so the card lives in the same viewport
        // layer as #billboard / .pinned-panel / #wfh-log-box.
        document.body.appendChild(card);
        this._drawConceptEdges();
    },

    /**
     * Collapse / restore the card body. When minimized the card
     * becomes a thin coloured bar showing just the name input and
     * the close + maximize buttons — same UX as the logs panel
     * (§ui_utils.js wfh-log-box) and pinned chunk panels.
     */
    _toggleConceptMinimize(card) {
        const body = card.querySelector('.concept-card-body');
        if (!body) return;
        const wasMin = card.dataset.minimized === '1';
        if (wasMin) {
            body.style.display = '';
            card.dataset.minimized = '';
        } else {
            body.style.display = 'none';
            card.dataset.minimized = '1';
        }
        const icon = card.querySelector('.concept-min-btn i');
        if (icon) {
            icon.className = wasMin ? 'fas fa-window-minimize' : 'fas fa-window-maximize';
        }
        // Edges anchor at card centres — recompute since the card
        // height just changed.
        this._drawConceptEdges();
    },

    _nextConceptZ() {
        // Top of the concept-card stack. Concept cards live just
        // below pinned chunk panels (which use 10010+) — high enough
        // to clear the 3D canvas chrome, low enough to not paint over
        // a knowledge panel the user pinned for cross-reference.
        let z = 9000;
        document.querySelectorAll('.concept-card').forEach(el => {
            const cur = parseInt(el.style.zIndex || '0', 10);
            if (cur > z) z = cur;
        });
        return z + 1;
    },

    // ── Reference parsing ────────────────────────────────────────────────────

    /**
     * Faithful port of template parseReferences(node).
     *
     *   - Stale-edge filter compares raw ref strings to slug edge
     *     targets, so it effectively removes every outgoing edge each
     *     call. The re-add loop below restores them. Net: edges from
     *     this node = current refs, edges from others untouched.
     *     Preserved for fidelity (see file header).
     *
     *   - Auto-create places at (source.x + 290, source.y + 50..110)
     *     and a setTimeout(0) updates the freshly-spawned card's
     *     description input AFTER innerHTML finishes parsing.
     */
    /**
     * Parse the curly-brace `{var}` references in either `node.value`
     * or `node.description` (or both). The user spec extends linking
     * from value-only to description-as-well; this wrapper centralises
     * the field choice so the underlying parser doesn't have to grow
     * a second code path.
     */
    _parseConceptReferencesIn(node, field) {
        const src = (field === 'description') ? node.description : node.value;
        if (typeof src !== 'string' || !src) return;
        // Temporarily swap node.value with src, run the existing
        // parser (which reads node.value), then restore the original
        // value. The parser's side effects (edge add, auto-create)
        // operate on the slugged ref strings, so the temporary
        // substitution is invisible to it.
        if (field === 'description') {
            const savedValue = node.value;
            node.value = src;
            try { this._parseConceptReferences(node); }
            finally { node.value = savedValue; }
        } else {
            this._parseConceptReferences(node);
        }
    },

    _parseConceptReferences(node) {
        // D3 / §8D.13 — Detect XPathPattern references and attach a
        // stepper. We do this on every parse so newly-typed pattern
        // references light up the stepper without an explicit gesture.
        try {
            if (node && node.value) {
                const refRe = /\{([\w][\w \-]*)\}/g;
                let match;
                const card = document.querySelector(`.concept-card[data-node-id="${node.id}"]`);
                if (card) {
                    let patternIdInValue = null;
                    while ((match = refRe.exec(node.value)) !== null) {
                        const refId = this._conceptSlugify(match[1]);
                        const target = this._conceptNodes.get(refId);
                        if (target && target.type_hint === 'xpath_pattern') {
                            patternIdInValue = refId;
                            break;  // only one stepper per card
                        }
                    }
                    // Three states:
                    //   1. No pattern in value, no stepper attached → no-op
                    //   2. Pattern in value, no stepper (or different
                    //      pattern) → (re-)attach
                    //   3. No pattern in value, stepper attached → tear down
                    if (patternIdInValue &&
                        (!card._sampleBank || card._sampleBankPatternId !== patternIdInValue)) {
                        this.attachSampleStepper(card, node, patternIdInValue);
                    } else if (!patternIdInValue && card._sampleBank) {
                        // Pattern reference was deleted from the value
                        // — tear down the stepper.
                        const oldStepper = card.querySelector('.concept-sample-stepper');
                        if (oldStepper && oldStepper.parentNode) {
                            oldStepper.parentNode.removeChild(oldStepper);
                        }
                        if (card._preSampleData != null) {
                            node.value = card._preSampleData;
                            const ta = card.querySelector('.concept-value-input');
                            if (ta) ta.value = card._preSampleData;
                        }
                        card._sampleBank = null;
                        card._sampleBankPatternId = null;
                        card._sampleIdx = 0;
                    }
                }
            }
        } catch (_) { /* parse-time stepper attach is best-effort */ }
        const value   = node.value;
        // Reference regex: `{<slug-shaped name>}` — must START with a
        // word char and contain only word chars, spaces, or hyphens.
        // Previously `[^}]+` greedily matched across the OUTER braces
        // of a JSON object value (which the decompose pipeline writes
        // when click-and-stick spawns a card whose value is a JSON
        // chunk summary). Restricting the character class to slug
        // shapes lets the compile recursion correctly skip JSON
        // delimiters like `{ "key": ... }` while still matching every
        // legitimate `{user_concept}` or `{Foo Bar}` reference.
        const REF_RE  = /\{([\w][\w \-]*)\}/g;
        const matches = [...value.matchAll(REF_RE)];
        // Slugify every ref-name once up front; the previous version
        // compared raw user text to slug edge targets which made the
        // stale-edge filter near-useless. Using slug refs means the
        // filter now correctly preserves still-present outgoing
        // edges and only drops the ones whose `{ref}` is gone.
        const refIds = new Set(
            matches.map(m => this._conceptSlugify(m[1])).filter(Boolean),
        );

        // Identify outgoing edges this parse is about to remove so we
        // can decide whether the (now-orphaned) target node should
        // also be deleted (only if it was auto-spawned by us and has
        // no other inbound edges left).
        const removingTargets = this._conceptEdges
            .filter(e => e.source === node.id && !refIds.has(e.target))
            .map(e => e.target);

        // Drop outgoing edges whose `{ref}` is no longer in the value.
        this._conceptEdges = this._conceptEdges.filter(
            e => !(e.source === node.id && !refIds.has(e.target))
        );

        // Refresh the set of refs currently present, in the order they
        // appear in the text (matches order of the user's typing).
        matches.forEach((m) => {
            const refName  = m[1];
            const targetId = this._conceptSlugify(refName);
            if (!targetId) return;
            if (!this._conceptNodes.has(targetId)) {
                // §8D.10 — auto-created targets anchor to the source
                // card so they land on a golden-angle ring around it.
                // No explicit x/y → addConceptNode uses the Fibonacci
                // placement with anchorId=node.id.
                const fresh = this.addConceptNode(refName, undefined, undefined, { anchorId: node.id });
                if (fresh) {
                    fresh.description = `Auto‑created from {${refName}}`;
                    fresh._autoCreated = true;
                    setTimeout(() => {
                        const c = document
                            .querySelector(`.concept-card[data-node-id="${fresh.id}"]`);
                        if (c) c.querySelector('.concept-desc-input').value = fresh.description;
                    }, 0);
                }
            }
            if (!this._conceptEdges.some(
                e => e.source === node.id && e.target === targetId
            )) {
                this._conceptEdges.push({ source: node.id, target: targetId });
            }
        });

        // ── Cascade-delete orphaned auto-creations ──
        // For each target whose incoming edge we just removed, if that
        // target was auto-spawned by us AND has no remaining inbound
        // edges from anywhere, delete it. The user's intent is "I
        // erased the brace, so the placeholder that came with it
        // should also go" — but we never delete a manually-named card
        // (one without the _autoCreated flag) nor one that's still
        // referenced from a different value field.
        removingTargets.forEach(targetId => {
            const target = this._conceptNodes.get(targetId);
            if (!target || !target._autoCreated) return;
            const stillReferenced = this._conceptEdges.some(
                e => e.target === targetId
            );
            if (stillReferenced) return;
            // Also bail if the user has typed anything custom into
            // this card — empty placeholder only.
            if (target.value && target.value.trim() !== '') return;
            this._conceptNodes.delete(targetId);
            // Remove any outgoing edges from the deleted target too
            // (its description-edits could have created refs of its
            // own that we now want to clean up).
            this._conceptEdges = this._conceptEdges.filter(
                e => e.source !== targetId && e.target !== targetId
            );
            const card = document
                .querySelector(`.concept-card[data-node-id="${targetId}"]`);
            if (card && card.parentNode) card.parentNode.removeChild(card);
            const t = this._conceptSuggestTimers.get(targetId);
            if (t) { clearTimeout(t); this._conceptSuggestTimers.delete(targetId); }
        });
    },

    // ── Edge drawing ─────────────────────────────────────────────────────────

    _drawConceptEdges() {
        const svg = document.getElementById('concept-edges');
        if (!svg) return;
        // Cheap short-circuit: if no edges and no marker, leave svg untouched.
        if (!this._conceptEdges || this._conceptEdges.length === 0) {
            svg.innerHTML = '';
            this._edgeLineCache = null;
            return;
        }
        // W34 — Diffed renderer for large graphs.
        //
        // The previous implementation wiped svg.innerHTML and rebuilt
        // every line on each 120 ms tick. For ~100+ edges that thrashes
        // the DOM and causes visible jitter. The new path:
        //   1. Build a stable per-edge key (source|target|edge_type).
        //   2. Reuse the SVG <line> element from a cache by key.
        //   3. Only update x1/y1/x2/y2 attributes (which change every
        //      frame because cards drag/move) and skip stroke/dash
        //      attributes (which are static per edge_type).
        //   4. Remove cached lines whose edge is gone.
        //
        // First-time path (or after wipe) builds defs + every line
        // fresh; subsequent passes are O(N) attribute updates only.
        if (!this._edgeLineCache) this._edgeLineCache = new Map();
        const cache = this._edgeLineCache;
        const SVG_NS_X = 'http://www.w3.org/2000/svg';
        // Ensure defs/arrow marker exist (one-time per session).
        if (!svg.querySelector('defs')) {
            const defs = document.createElementNS(SVG_NS_X, 'defs');
            const marker = document.createElementNS(SVG_NS_X, 'marker');
            marker.id = 'concept-arrow';
            marker.setAttribute('viewBox', '0 0 10 10');
            marker.setAttribute('refX', '9');
            marker.setAttribute('refY', '5');
            marker.setAttribute('markerWidth', '6');
            marker.setAttribute('markerHeight', '6');
            marker.setAttribute('orient', 'auto');
            const arrowPath = document.createElementNS(SVG_NS_X, 'path');
            arrowPath.setAttribute('d', 'M 0 0 L 10 5 L 0 10 z');
            arrowPath.setAttribute('fill', '#b8c0c8');
            marker.appendChild(arrowPath);
            defs.appendChild(marker);
            svg.appendChild(defs);
        }
        // §8D.10 barrier colliders. Collect every card's bbox once so
        // the per-edge collision test is O(E·N) over cached rects, not
        // O(E·N) DOM queries + getBoundingClientRect calls. Each card
        // is keyed by its concept id so we can exclude endpoints from
        // the obstruction list for each edge.
        const allCards = document.querySelectorAll('.concept-card[data-node-id]');
        const cardRects = new Map();
        for (const card of allCards) {
            const id = card.getAttribute('data-node-id');
            if (id) cardRects.set(id, card.getBoundingClientRect());
        }
        // Track which keys we've seen this frame; anything in the
        // cache not seen will be removed at the end.
        const seenKeys = new Set();
        const edgeKey = (e) => `${e.source}|${e.target}|${e.edge_type || 'RELATES_TO'}`;
        this._conceptEdges.forEach(edge => {
            const sr = cardRects.get(String(edge.source));
            const tr = cardRects.get(String(edge.target));
            if (!sr || !tr) return;
            const x1 = sr.left + sr.width  / 2;
            const y1 = sr.top  + sr.height / 2;
            const x2 = tr.left + tr.width  / 2;
            const y2 = tr.top  + tr.height / 2;
            const key = edgeKey(edge);
            seenKeys.add(key);
            // §8D.10 — find the first obstructing card (if any) whose
            // bbox the straight segment crosses. The endpoints' own
            // cards are excluded. We pick the obstruction with the
            // longest projection along the segment, so the routing
            // bulge clears the most "in-the-way" obstacle.
            const obstruction = this._firstObstructingRect(
                x1, y1, x2, y2,
                cardRects,
                String(edge.source),
                String(edge.target),
            );
            const wantPath = obstruction !== null;
            let el = cache.get(key);
            const cachedIsPath = el && el.tagName && el.tagName.toLowerCase() === 'path';
            // If the cached element is the wrong shape (line ↔ path),
            // discard it so we can re-build with the right tag.
            if (el && (cachedIsPath !== wantPath)) {
                if (el.parentNode) el.parentNode.removeChild(el);
                cache.delete(key);
                el = null;
            }
            if (!el) {
                el = document.createElementNS(
                    SVG_NS_X, wantPath ? 'path' : 'line',
                );
                const style = this._edgeStyleForType(edge.edge_type || 'RELATES_TO');
                el.setAttribute('stroke', style.color);
                el.setAttribute('stroke-width', style.width);
                el.setAttribute('stroke-opacity', '0.92');
                if (style.dash) el.setAttribute('stroke-dasharray', style.dash);
                if (wantPath) el.setAttribute('fill', 'none');
                el.removeAttribute('marker-end');
                el.style.pointerEvents = 'stroke';
                el.style.cursor = 'pointer';
                const t = document.createElementNS(SVG_NS_X, 'title');
                t.textContent = edge.variable_name
                    ? `${edge.edge_type || 'RELATES_TO'} · ${edge.variable_name}`
                    : (edge.edge_type || 'RELATES_TO');
                el.appendChild(t);
                el.addEventListener('contextmenu', (ev) => {
                    ev.preventDefault();
                    this._openEdgeContextMenu(edge, ev.clientX, ev.clientY);
                });
                cache.set(key, el);
                svg.appendChild(el);
            }
            // Update geometry only — cheap on the common no-collision
            // path (just x1/y1/x2/y2 attribute writes). The Bezier
            // path is rebuilt each frame because the obstruction's
            // position can drift independently of the edge endpoints.
            if (wantPath) {
                el.setAttribute(
                    'd',
                    this._bezierAroundObstruction(x1, y1, x2, y2, obstruction),
                );
            } else {
                el.setAttribute('x1', x1);
                el.setAttribute('y1', y1);
                el.setAttribute('x2', x2);
                el.setAttribute('y2', y2);
            }
        });
        // Drop cache entries whose edge is gone this frame.
        for (const [key, lineEl] of cache.entries()) {
            if (!seenKeys.has(key)) {
                if (lineEl.parentNode) lineEl.parentNode.removeChild(lineEl);
                cache.delete(key);
            }
        }
        // The legacy below-here path is now dead; the diffed renderer
        // above replaces it. Keep the return so the old code (which
        // re-built defs and lines) doesn't double-render.
        return;
        // ---- legacy path retained for reference; never reached ----
        // Wipe and rebuild defs + lines each tick — template strategy.
        svg.innerHTML = '';
        const SVG_NS = 'http://www.w3.org/2000/svg';
        const defs   = document.createElementNS(SVG_NS, 'defs');
        const marker = document.createElementNS(SVG_NS, 'marker');
        marker.id = 'concept-arrow';
        marker.setAttribute('viewBox', '0 0 10 10');
        marker.setAttribute('refX', '9');
        marker.setAttribute('refY', '5');
        marker.setAttribute('markerWidth', '6');
        marker.setAttribute('markerHeight', '6');
        marker.setAttribute('orient', 'auto');
        const arrowPath = document.createElementNS(SVG_NS, 'path');
        arrowPath.setAttribute('d', 'M 0 0 L 10 5 L 0 10 z');
        arrowPath.setAttribute('fill', '#b8c0c8');
        marker.appendChild(arrowPath);
        defs.appendChild(marker);
        svg.appendChild(defs);

        this._conceptEdges.forEach(edge => {
            const sourceCard = document
                .querySelector(`.concept-card[data-node-id="${edge.source}"]`);
            const targetCard = document
                .querySelector(`.concept-card[data-node-id="${edge.target}"]`);
            if (!sourceCard || !targetCard) return;
            const sr = sourceCard.getBoundingClientRect();
            const tr = targetCard.getBoundingClientRect();
            // Viewport coordinates work directly — the SVG covers
            // 100vw × 100vh anchored to the viewport (position:fixed,
            // inset:0). No canvas-relative subtraction needed.
            const x1 = sr.left + sr.width  / 2;
            const y1 = sr.top  + sr.height / 2;
            const x2 = tr.left + tr.width  / 2;
            const y2 = tr.top  + tr.height / 2;
            const line = document.createElementNS(SVG_NS, 'line');
            line.setAttribute('x1', x1);
            line.setAttribute('y1', y1);
            line.setAttribute('x2', x2);
            line.setAttribute('y2', y2);
            // W22 / §8A.2, §8D.44 — per-edge-type visual style.
            // Each edge_type gets a distinctive stroke colour +
            // dash pattern so the graph's typed structure is
            // readable at a glance.
            const style = this._edgeStyleForType(edge.edge_type || 'RELATES_TO');
            line.setAttribute('stroke', style.color);
            line.setAttribute('stroke-width', style.width);
            line.setAttribute('stroke-opacity', '0.92');
            if (style.dash) line.setAttribute('stroke-dasharray', style.dash);
            line.removeAttribute('marker-end');
            // W33 — allow pointer events on the stroke (with a
            // generous detection radius via stroke-linecap=round)
            // so the right-click menu can target this edge.
            line.style.pointerEvents = 'stroke';
            line.style.cursor = 'pointer';
            // Tooltip carries edge_type and (when present) variable_name.
            const t = document.createElementNS(SVG_NS, 'title');
            t.textContent = edge.variable_name
                ? `${edge.edge_type || 'RELATES_TO'} · ${edge.variable_name}`
                : (edge.edge_type || 'RELATES_TO');
            line.appendChild(t);
            // W33 — right-click opens an edge context menu.
            line.addEventListener('contextmenu', (ev) => {
                ev.preventDefault();
                this._openEdgeContextMenu(edge, ev.clientX, ev.clientY);
            });
            svg.appendChild(line);
        });
    },

    /**
     * W33 — Edge context menu. Right-click any edge to surface:
     *   - Change edge_type (drop-down of canonical types)
     *   - Delete this edge
     */
    _openEdgeContextMenu(edge, x, y) {
        // Close any existing menu.
        const existing = document.getElementById('wfh-edge-context-menu');
        if (existing && existing.parentNode) existing.parentNode.removeChild(existing);
        const menu = document.createElement('div');
        menu.id = 'wfh-edge-context-menu';
        menu.style.cssText =
            `position:fixed; left:${x}px; top:${y}px; z-index:10500;` +
            'background:rgba(0,0,0,0.97); color:#e5e7eb;' +
            'border:1px solid rgba(255,255,255,0.15); border-radius:6px;' +
            'box-shadow:0 8px 24px rgba(0,0,0,0.4); padding:4px 0;' +
            'min-width:200px; font-family:monospace; font-size:11px;';
        const edgeTypes = [
            'RELATES_TO', 'IS_A', 'HAS_A', 'PART_OF',
            'INCLUDES', 'DERIVED_FROM', 'CLASSIFIES',
            'PROVIDES_VALUE_FOR', 'PROPERTY_REF', 'METHOD_OUTPUT',
            'SIMILAR_TO', 'ANNOTATES',
        ];
        const currentType = edge.edge_type || 'RELATES_TO';
        const header = document.createElement('div');
        header.style.cssText = 'padding:6px 10px;font-weight:600;color:#b8c0c8;border-bottom:1px solid rgba(255,255,255,0.05);';
        header.textContent = `${edge.source} → ${edge.target}`;
        menu.appendChild(header);
        const typeHeader = document.createElement('div');
        typeHeader.style.cssText = 'padding:4px 10px;color:#9aa3ab;font-size:9px;letter-spacing:0.05em;text-transform:uppercase;';
        typeHeader.textContent = 'edge type';
        menu.appendChild(typeHeader);
        edgeTypes.forEach(et => {
            const item = document.createElement('div');
            item.style.cssText =
                `padding:4px 12px;cursor:pointer;color:${et === currentType ? '#eef0f2' : '#e5e7eb'};` +
                (et === currentType ? 'background:rgba(184,192,200,0.1);' : '');
            item.textContent = et;
            item.addEventListener('mouseenter', () => {
                if (et !== currentType) item.style.background = 'rgba(255,255,255,0.05)';
            });
            item.addEventListener('mouseleave', () => {
                if (et !== currentType) item.style.background = '';
            });
            item.addEventListener('click', async () => {
                edge.edge_type = et;
                this._drawConceptEdges();
                menu.remove();
                // Update via backend (POST a new edge with the new type
                // and delete the old; backend doesn't yet support
                // PATCH-on-edge, so two-step write).
                if (this._conceptBackendOk && edge.edge_id) {
                    try {
                        await fetch(`/api/concept_edges/${encodeURIComponent(edge.edge_id)}`, { method: 'DELETE' });
                        const resp = await fetch('/api/concept_edges', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                source_id: edge.source, target_id: edge.target,
                                edge_type: et,
                                workspace_id: this._conceptWorkspaceId || '',
                                idempotency_key: this._newIdempotencyKey(),
                            }),
                        });
                        if (resp.ok) {
                            const data = await resp.json();
                            if (data && data.edge_id) edge.edge_id = data.edge_id;
                        }
                    } catch (_) { /* ignore */ }
                }
            });
            menu.appendChild(item);
        });
        const sep = document.createElement('div');
        sep.style.cssText = 'border-top:1px solid rgba(255,255,255,0.05);margin:4px 0;';
        menu.appendChild(sep);
        const delItem = document.createElement('div');
        delItem.style.cssText = 'padding:6px 12px;cursor:pointer;color:#b25b5b;';
        delItem.textContent = 'Delete edge';
        delItem.addEventListener('mouseenter', () => delItem.style.background = 'rgba(178,91,91,0.1)');
        delItem.addEventListener('mouseleave', () => delItem.style.background = '');
        delItem.addEventListener('click', async () => {
            this._conceptEdges = this._conceptEdges.filter(
                e => !(e.source === edge.source && e.target === edge.target && e.edge_type === edge.edge_type)
            );
            this._drawConceptEdges();
            menu.remove();
            if (this._conceptBackendOk && edge.edge_id) {
                try {
                    await fetch(`/api/concept_edges/${encodeURIComponent(edge.edge_id)}`, { method: 'DELETE' });
                } catch (_) { /* ignore */ }
            }
        });
        menu.appendChild(delItem);
        document.body.appendChild(menu);
        // Close on click-outside.
        setTimeout(() => {
            const onClick = (ev) => {
                if (!menu.contains(ev.target)) {
                    if (menu.parentNode) menu.parentNode.removeChild(menu);
                    document.removeEventListener('click', onClick);
                }
            };
            document.addEventListener('click', onClick);
        }, 0);
    },

    /**
     * W32 / §8C.3 — Begin a port-drag: rubber-band line follows
     * the cursor until mouseup over another card, which draws a
     * new edge from source to target. Default edge_type is
     * RELATES_TO; the user can change it via the edge context
     * menu (W33). The drag is cancelled on mouseup-off-card or Esc.
     */
    _beginPortDrag(sourceNode, sourceCard, startX, startY) {
        let svg = document.getElementById('concept-edges');
        if (!svg) return;
        const SVG_NS = 'http://www.w3.org/2000/svg';
        // Rubber-band line.
        const line = document.createElementNS(SVG_NS, 'line');
        line.setAttribute('x1', startX);
        line.setAttribute('y1', startY);
        line.setAttribute('x2', startX);
        line.setAttribute('y2', startY);
        line.setAttribute('stroke', '#ffd700');  // the one allowed accent (connector hue)
        line.setAttribute('stroke-width', '2');
        // solid rubber-band (no dashes per black/silver design)
        line.setAttribute('stroke-opacity', '0.95');
        svg.appendChild(line);

        const onMove = (ev) => {
            line.setAttribute('x2', ev.clientX);
            line.setAttribute('y2', ev.clientY);
            // Highlight the card under the cursor (if any) as a
            // potential drop target.
            const under = document.elementFromPoint(ev.clientX, ev.clientY);
            const targetCard = under && under.closest && under.closest('.concept-card');
            document.querySelectorAll('.concept-card').forEach(c => c.classList.remove('drop-target'));
            if (targetCard && targetCard !== sourceCard) {
                targetCard.classList.add('drop-target');
                targetCard.style.outline = '2px dashed #eef0f2';
            }
        };
        const cleanup = () => {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
            document.removeEventListener('keydown', onKey);
            document.querySelectorAll('.concept-card').forEach(c => {
                c.classList.remove('drop-target');
                if (c !== sourceCard) c.style.outline = '';
            });
            if (line.parentNode) line.parentNode.removeChild(line);
        };
        const onUp = async (ev) => {
            const under = document.elementFromPoint(ev.clientX, ev.clientY);
            const targetCard = under && under.closest && under.closest('.concept-card');
            cleanup();
            if (!targetCard || targetCard === sourceCard) return;
            const targetId = targetCard.dataset.nodeId;
            if (!targetId || targetId === sourceNode.id) return;
            // Dedup: skip if same edge already exists.
            const exists = this._conceptEdges.some(e =>
                e.source === sourceNode.id && e.target === targetId);
            if (exists) return;
            // Insert the local edge.
            this._conceptEdges.push({
                source: sourceNode.id,
                target: targetId,
                edge_type: 'RELATES_TO',
            });
            this._drawConceptEdges();
            // POST to backend.
            if (this._conceptBackendOk) {
                try {
                    const resp = await fetch('/api/concept_edges', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            source_id: sourceNode.id,
                            target_id: targetId,
                            edge_type: 'RELATES_TO',
                            workspace_id: this._conceptWorkspaceId || '',
                            idempotency_key: this._newIdempotencyKey(),
                        }),
                    });
                    if (resp.ok) {
                        const data = await resp.json();
                        // Stash backend edge_id on the local edge so
                        // delete-by-edge_id works (W33).
                        const last = this._conceptEdges[this._conceptEdges.length - 1];
                        if (last && data && data.edge_id) {
                            last.edge_id = data.edge_id;
                        }
                    }
                } catch (_) { /* ignore */ }
            }
        };
        const onKey = (ev) => { if (ev.key === 'Escape') cleanup(); };
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        document.addEventListener('keydown', onKey);
    },

    /**
     * W22 / §8A.2 / §O.16 — Stroke style table per edge_type. Returns
     *   { color, width, dash }.
     * Per frontend_rendering.md §1.6 + §2.3 (NO dashes anywhere; the §18.7
     * anti-goal): every edge is a SOLID line in the black/silver palette, and
     * the edge TYPE is conveyed by BRIGHTNESS + WIDTH only — hard structural
     * edges are brighter/thicker (IS_A #d7dde2 @2.6), soft edges dimmer/thinner
     * (SIMILAR_TO #555c63 @1). No hues, no dashes, no arrowheads. `dash` is
     * always '' (kept in the returned shape only so the renderer's
     * `if (style.dash)` guard stays inert — the older hue+dash scheme this
     * doc-block once described was removed when §O.16 landed).
     */
    _edgeStyleForType(type) {
        switch (String(type || '').toUpperCase()) {
            // Undirected SOLID lines; type conveyed by brightness + width only
            // (hard structural = brighter/thicker, soft = dimmer/thinner). No
            // hues, no dashes, no arrowheads (black/silver design, §O.16).
            case 'IS_A':                   return { color: '#d7dde2', width: '2.6', dash: '' };
            case 'HAS_A':                  return { color: '#c4ccd3', width: '2.2', dash: '' };
            case 'PART_OF':                return { color: '#b8c0c8', width: '2', dash: '' };
            case 'INCLUDES':
            case 'DERIVED_FROM':           return { color: '#b8c0c8', width: '2', dash: '' };
            case 'CLASSIFIES':             return { color: '#9aa3ab', width: '2', dash: '' };
            case 'PROVIDES_VALUE_FOR':
            case 'PROPERTY_REF':           return { color: '#d7dde2', width: '2.4', dash: '' };
            case 'METHOD_OUTPUT':          return { color: '#d7dde2', width: '2.4', dash: '' };
            case 'SIMILAR_TO':             return { color: '#555c63', width: '1', dash: '' };
            case 'ANNOTATES':              return { color: '#7c858d', width: '1.6', dash: '' };
            case 'RELATES_TO':
            default:                       return { color: '#b8c0c8', width: '2', dash: '' };
        }
    },

    // ── §8D.10 Barrier-Collider Edge Routing ────────────────────────────────

    /**
     * Test whether the segment (x1,y1)→(x2,y2) crosses any card's
     * bounding box other than the source/target endpoints. Returns
     * the first obstructing rect, or null when the straight line is
     * clear. Cohen-Sutherland clipping is used so the per-edge cost
     * is O(N) rect tests with cheap region-code early exits.
     *
     * Cards have a small padding so an edge that grazes a corner
     * still re-routes — the visual was ugly when arrowheads slid
     * along the edge of another card by 1-2 px.
     */
    _firstObstructingRect(x1, y1, x2, y2, cardRects, sourceId, targetId) {
        const PAD = 12;
        for (const [id, rect] of cardRects) {
            if (id === sourceId || id === targetId) continue;
            if (this._segmentIntersectsRect(x1, y1, x2, y2, rect, PAD)) {
                return rect;
            }
        }
        return null;
    },

    /**
     * Cohen-Sutherland segment-vs-rect intersection. Both endpoints
     * sharing an outside region trivially miss; either endpoint
     * inside trivially hits; otherwise iterate clipping until a
     * shared region appears or the segment is fully clipped away.
     */
    _segmentIntersectsRect(x1, y1, x2, y2, rect, pad) {
        const minX = rect.left   - pad;
        const minY = rect.top    - pad;
        const maxX = rect.right  + pad;
        const maxY = rect.bottom + pad;
        const code = (x, y) => {
            let c = 0;
            if (x < minX) c |= 1; else if (x > maxX) c |= 2;
            if (y < minY) c |= 4; else if (y > maxY) c |= 8;
            return c;
        };
        let c1 = code(x1, y1);
        let c2 = code(x2, y2);
        let a = x1, b = y1, p = x2, q = y2;
        // Bounded iter count — fully clipped segments resolve in ≤4
        // refinements; the cap is paranoia against pathological NaNs.
        for (let i = 0; i < 8; i++) {
            if ((c1 | c2) === 0) return true;
            if ((c1 & c2) !== 0) return false;
            const outCode = c1 !== 0 ? c1 : c2;
            let nx = 0, ny = 0;
            if (outCode & 8) {
                nx = a + (p - a) * (maxY - b) / (q - b);
                ny = maxY;
            } else if (outCode & 4) {
                nx = a + (p - a) * (minY - b) / (q - b);
                ny = minY;
            } else if (outCode & 2) {
                ny = b + (q - b) * (maxX - a) / (p - a);
                nx = maxX;
            } else {
                ny = b + (q - b) * (minX - a) / (p - a);
                nx = minX;
            }
            if (outCode === c1) { a = nx; b = ny; c1 = code(a, b); }
            else                { p = nx; q = ny; c2 = code(p, q); }
        }
        return false;
    },

    /**
     * §8D.10 — Build an SVG cubic Bezier ``d`` string for the
     * segment (x1,y1)→(x2,y2) that bulges around the obstruction
     * rect. The control points sit at 1/3 and 2/3 of the segment,
     * each offset perpendicular to the segment by enough to clear
     * the obstruction's larger half-extent + padding. Sign is
     * chosen to push AWAY from the obstruction's centre so the
     * curve never re-enters the collider it was meant to skirt.
     */
    _bezierAroundObstruction(x1, y1, x2, y2, obstRect) {
        const dx = x2 - x1;
        const dy = y2 - y1;
        const len = Math.hypot(dx, dy) || 1;
        // Unit perpendicular (CCW rotation of direction).
        const px = -dy / len;
        const py =  dx / len;
        const mx = (x1 + x2) / 2;
        const my = (y1 + y2) / 2;
        const ox = (obstRect.left + obstRect.right) / 2;
        const oy = (obstRect.top  + obstRect.bottom) / 2;
        // Project the vector from obstruction-centre to segment-mid
        // onto the perpendicular; sign tells us which side of the
        // segment the obstruction sits on so we can push the curve
        // away rather than through it.
        const sign = ((mx - ox) * px + (my - oy) * py) >= 0 ? 1 : -1;
        const halfW = (obstRect.right  - obstRect.left) / 2;
        const halfH = (obstRect.bottom - obstRect.top ) / 2;
        // Clear the larger half-extent plus a visual margin. 24 px
        // is empirically wide enough that the arrowhead doesn't
        // graze the rectangle even on a glancing angle.
        const push = (Math.max(halfW, halfH) + 24) * sign;
        const cx1 = x1 + dx / 3 + px * push;
        const cy1 = y1 + dy / 3 + py * push;
        const cx2 = x1 + 2 * dx / 3 + px * push;
        const cy2 = y1 + 2 * dy / 3 + py * push;
        return `M ${x1},${y1} C ${cx1},${cy1} ${cx2},${cy2} ${x2},${y2}`;
    },

    // ── Compilation ──────────────────────────────────────────────────────────

    /**
     * Recursive substitution of {var} with the target node's compiled
     * value. Cycle-safe via per-branch `new Set(visited)` so siblings
     * recurse independently while a circular chain bottoms out at
     * the literal `{id}` token.
     */
    _compileConceptNode(nodeId, visited) {
        if (!visited) visited = new Set();
        if (visited.has(nodeId)) return `{${nodeId}}`;
        visited.add(nodeId);
        const node = this._conceptNodes.get(nodeId);
        if (!node) return `{${nodeId}}`;
        // Same slug-shaped match as _parseConceptReferences so JSON
        // delimiters in decomposed-template values don't get clobbered.
        const REF_RE = /\{([\w][\w \-]*)\}/g;
        return String(node.value).replace(REF_RE, (_m, varName) => {
            const targetId = this._conceptSlugify(varName);
            if (this._conceptNodes.has(targetId)) {
                return this._compileConceptNode(targetId, new Set(visited));
            }
            return `{${varName}}`;
        });
    },

    // ── JSON decompose / recompose ──────────────────────────────────────
    //
    // The user wants click-and-stick knowledge panels to be regular
    // concept cards whose VALUE is the HTML summary of the clicked
    // 3D node, and whose Compile button decomposes any JSON value
    // into a graph of sub-cards (one per top-level key) that
    // recursively recompose into the original JSON when the root
    // card is compiled.
    //
    // The decomposition policy:
    //   • If the value parses as valid JSON object/array → spawn a
    //     child card per top-level key (or per array index), set the
    //     child's value to the stringified sub-value (which itself
    //     may decompose further on its own Compile press), and
    //     rewrite the parent's value to reference the children via
    //     `{slug}` placeholders. The Compile preview then walks
    //     those references and produces the original JSON.
    //   • If the value is plain text / HTML / not valid JSON → leave
    //     it alone, just render the existing `{var}` substitutions.
    //
    // Round-trip identity test (run via _selfTestJsonRoundtrip in
    // dev): for any nested JSON, parse → spawnFromJson → compile →
    // JSON.parse(result) deep-equals the original.

    /**
     * Try to parse `node.value` as JSON. On success, decompose the
     * top level into sub-cards and rewrite `node.value` to a
     * reference-bearing template. Returns true if decomposition
     * happened, false otherwise (value left untouched).
     */
    _decomposeJsonValue(node) {
        if (!node || typeof node.value !== 'string') return false;
        const trimmed = node.value.trim();
        if (!trimmed) return false;
        // Cheap pre-check: must look like an object/array.
        if (trimmed[0] !== '{' && trimmed[0] !== '[') return false;
        let parsed;
        try { parsed = JSON.parse(trimmed); }
        catch (_) { return false; }
        if (parsed === null || typeof parsed !== 'object') return false;
        const isArray = Array.isArray(parsed);
        const parts   = [];
        const card    = document.querySelector(`.concept-card[data-node-id="${node.id}"]`);
        const entries = isArray
            ? parsed.map((v, i) => [String(i), v])
            : Object.entries(parsed);
        entries.forEach(([key, val], idx) => {
            // Child card name: `<parent>_<key>` slugified so id stays
            // stable for the same JSON structure.
            const childRaw = `${node.id}__${key}`;
            const childId  = this._conceptSlugify(childRaw);
            // Spawn or reuse the child card. If it already exists
            // (e.g. user is re-compiling), overwrite its value.
            let child = this._conceptNodes.get(childId);
            if (!child) {
                // §7.3.2 / §K.5 — decomposed children fan out along
                // ray-constrained rays from the parent (NOT a golden-angle
                // concentric ring). addConceptNode reads anchorId from opts
                // and _rayConstrainedPosition steps each child outward along
                // a fixed fan of rays from the focal.
                child = this.addConceptNode(childRaw, undefined, undefined, { anchorId: node.id });
            }
            if (!child) return;
            // ALWAYS encode the child's value as a JSON literal so
            // strings carry their quotes, numbers stay numeric, and
            // nested objects/arrays stay parseable. The parent
            // template substitutes `{child_id}` raw, and the
            // resulting compiled string is valid JSON that matches
            // the original via JSON.parse round-trip.
            const valueStr = JSON.stringify(val);
            child.value = valueStr;
            child._autoCreated = true;  // delete with parent if last ref
            // Refresh the child's textarea live so the user can see it.
            const childCard = document.querySelector(`.concept-card[data-node-id="${child.id}"]`);
            if (childCard) {
                const valEl  = childCard.querySelector('.concept-value-input');
                if (valEl) valEl.value = valueStr;
                const descEl = childCard.querySelector('.concept-desc-input');
                if (descEl && !child.description) {
                    child.description = `JSON child of ${node.name} (${isArray ? `[${key}]` : `.${key}`})`;
                    descEl.value = child.description;
                }
                this._applyCompiledChildMode(childCard);  // §4.5 value-only
            }
            // Cascade: recurse syntax-agnostically (the child's value may
            // be JSON OR a native indented field-tree, §7.1 step 3).
            this._decomposeValue(child);
            // Build the parent's new template token. The placeholder
            // is bare because the child's JSON-encoded value already
            // carries its own delimiters (quotes/braces/brackets).
            parts.push(isArray ? `{${child.id}}` : `${JSON.stringify(key)}: {${child.id}}`);
            // Add the edge.
            if (!this._conceptEdges.some(e => e.source === node.id && e.target === child.id)) {
                this._conceptEdges.push({ source: node.id, target: child.id });
            }
        });
        // Stitch the new value template that recomposes to the
        // original JSON when compiled (the compile recursion replaces
        // every `{child.id}` with the child's value).
        node.value = isArray
            ? `[${parts.join(', ')}]`
            : `{ ${parts.join(', ')} }`;
        if (card) {
            const v = card.querySelector('.concept-value-input');
            if (v) v.value = node.value;
        }
        this._drawConceptEdges();
        return true;
    },

    // ── H1 / §6.6.4 / §P — request the 3D compute-graph projector overlay ──
    //
    // POSTs /api/compute_graph/layout for `focalId`'s {ref}-connected graph;
    // the backend returns + broadcasts a `compute_graph_layout` frame that
    // scanner.js renders (bisector node + UMAP-independent link network).
    // Fire-and-forget — overlay rendering is best-effort and never blocks the
    // 2D compile.
    _requestComputeGraphOverlay(focalId) {
        try {
            fetch('/api/compute_graph/layout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ workspace_id: '', focal_id: focalId }),
            }).catch(() => {});
        } catch (_) { /* best-effort */ }
    },

    // ── §7.1 / §18.15 / §R.5 — syntax-AGNOSTIC decompose dispatcher ─────
    //
    // The compile must "compile the data structure into its components
    // recursively and independent of syntax over recursive tree
    // structures" (§18.15). Strategies, in order: JSON; the §R.5
    // markdown-gesture outline (dashes, tabs, numbers, newline-with-
    // trailing-text); the native field-tree (tab/newline `key: value`,
    // §4.2.2 / §O.20). The first that detects structure wins. Strategy
    // order mirrors the backend `decompose_top_level` so both dialectic
    // sides produce the same children (§R.1 commutation). A successful
    // decompose tags `node._decomposed` so a later markdown edit to the
    // panel re-runs the restructure (the §R.5 live gesture).
    _decomposeValue(node) {
        if (!node || typeof node.value !== 'string') return false;
        const trimmed = node.value.trim();
        if (!trimmed) return false;
        let ok = false;
        // Strategy 1 — JSON (object/array). Unchanged, proven path.
        if (trimmed[0] === '{' || trimmed[0] === '[') {
            ok = this._decomposeJsonValue(node);
        }
        // Strategy 2 — §E.1 HTML element tree (browser DOMParser).
        if (!ok && this._looksLikeHtmlTree(trimmed)) {
            ok = this._decomposeHtmlTree(node);
        }
        // Strategy 3 — §E.1 non-JSON bracketed list ([a, b] / (a, b)).
        if (!ok) {
            const items = this._parseBracketedTopLevel(trimmed);
            if (items && items.length >= 2) {
                ok = this._decomposeEntries(
                    node, items.map((v, i) => ({ key: String(i), value: v })),
                    { listForm: true });
            }
        }
        // Strategy 4 — §R.5 markdown-gesture outline.
        if (!ok && this._looksLikeMarkdownTree(node.value)) {
            ok = this._decomposeMarkdownTree(node);
        }
        // Strategy 5 — native indented field-tree (`key: value` rows).
        if (!ok) ok = this._decomposeIndentTree(node);
        if (ok) node._decomposed = true;
        return ok;
    },

    // ── §E.1 — HTML element tree + bracketed list strategies ────────────
    //
    // "JSON, bracketed lists, indented trees, HTML element trees, plain
    //  text — all handled by the same routine." (§E.1, verbatim)
    // Shared semantics with the backend `parse_html_tree` /
    // `parse_bracketed_list` (compile_pipeline.py): decompose splits out
    // the ROOT element's children (the root tag is implicit in the parent
    // card's position, §4.5); repeated sibling tags fold under one key;
    // bracketed items take positional keys.

    _looksLikeHtmlTree(text) {
        if (!text || typeof DOMParser === 'undefined') return false;
        const s = String(text).trim();
        if (!/^<\s*[a-zA-Z][\w\-]*/.test(s)) return false;
        return s.includes('</') || s.includes('/>');
    },

    /**
     * Parse the value as an HTML element tree and return TOP-LEVEL entries
     * `[{key, value}]`: the root element's children grouped by tag —
     * single text child → its text; structured child → its innerHTML (so
     * recursion re-applies the HTML strategy); repeated tags → their
     * values joined by newline under the one tag key. Returns null when
     * not HTML or DOMParser is unavailable (node test harnesses).
     */
    _parseHtmlTopLevel(text) {
        if (!this._looksLikeHtmlTree(text)) return null;
        let doc;
        try {
            doc = new DOMParser().parseFromString(String(text), 'text/html');
        } catch (_) { return null; }
        const body = doc && doc.body;
        if (!body) return null;
        const roots = Array.from(body.children);
        if (!roots.length) return null;
        // One top element → decompose ITS children; several → treat the
        // body as the implicit root (mirrors backend parse_html_tree).
        const host = roots.length === 1 ? roots[0] : body;
        const kids = Array.from(host.children);
        if (!kids.length) return null;
        const groups = new Map();   // tag → [element]
        kids.forEach((el) => {
            const tag = el.tagName.toLowerCase();
            if (!groups.has(tag)) groups.set(tag, []);
            groups.get(tag).push(el);
        });
        const valOf = (el) => el.children.length
            ? el.innerHTML.trim()                       // recursable markup
            : (el.textContent || '').trim();            // leaf text
        const entries = [];
        groups.forEach((els, tag) => {
            entries.push({
                key: tag,
                value: els.map(valOf).filter(Boolean).join('\n'),
            });
        });
        return entries.length ? entries : null;
    },

    _decomposeHtmlTree(node) {
        const entries = this._parseHtmlTopLevel(node.value);
        if (!entries || !entries.length) return false;
        return this._decomposeEntries(node, entries, { listForm: false });
    },

    /**
     * §E.1 — top-level items of a NON-JSON bracketed list (`[a, b]`,
     * `(a, b, c)`; unquoted items, nesting + quotes guarded). Pure parse
     * (node-testable). Returns null when the gate rejects — strict JSON
     * stays owned by the JSON strategy upstream.
     */
    _parseBracketedTopLevel(text) {
        const s = String(text || '').trim();
        if (s.length < 2) return null;
        const pairs = { '[': ']', '(': ')' };
        if (!(s[0] in pairs) || s[s.length - 1] !== pairs[s[0]]) return null;
        try { JSON.parse(s); return null; } catch (_) { /* not JSON — ours */ }
        const inner = s.slice(1, -1);
        const items = [];
        let buf = [], depth = 0, quote = null;
        for (const ch of inner) {
            if (quote) {
                buf.push(ch);
                if (ch === quote) quote = null;
                continue;
            }
            if (ch === '"' || ch === "'") { quote = ch; buf.push(ch); }
            else if ('[({'.includes(ch)) { depth += 1; buf.push(ch); }
            else if ('])}'.includes(ch)) { depth -= 1; buf.push(ch); }
            else if (ch === ',' && depth === 0) { items.push(buf.join('')); buf = []; }
            else buf.push(ch);
        }
        if (buf.length) items.push(buf.join(''));
        const out = items.map(it => {
            let v = it.trim();
            if (v.length >= 2 && v[0] === v[v.length - 1] && (v[0] === '"' || v[0] === "'")) {
                v = v.slice(1, -1);
            }
            return v;
        }).filter(Boolean);
        return out.length ? out : null;
    },

    /**
     * Shared child-spawning core for the §E.1 strategies: one child card
     * per entry, value-only render mode, recursion through the one
     * dispatcher, parent rewritten to `key: {child.id}` rows (or a
     * bracketed `[{a}, {b}]` form for lists so the list shape survives
     * the round trip). Mirrors `_decomposeIndentTree`'s contract.
     */
    _decomposeEntries(node, entries, { listForm = false } = {}) {
        if (!entries || !entries.length) return false;
        const card  = document.querySelector(`.concept-card[data-node-id="${node.id}"]`);
        const parts = [];
        entries.forEach(({ key, value }) => {
            const childRaw = `${node.id}__${key}`;
            const childId  = this._conceptSlugify(childRaw);
            let child = this._conceptNodes.get(childId);
            if (!child) {
                child = this.addConceptNode(childRaw, undefined, undefined, { anchorId: node.id });
            }
            if (!child) return;
            child.value = (value || '').replace(/\n+$/, '');
            child._autoCreated = true;
            const childCard = document.querySelector(`.concept-card[data-node-id="${child.id}"]`);
            if (childCard) {
                const valEl = childCard.querySelector('.concept-value-input');
                if (valEl) valEl.value = child.value;
                this._applyCompiledChildMode(childCard);  // §4.5 value-only
            }
            this._decomposeValue(child);                  // §7.1 recursion
            parts.push(listForm ? `{${child.id}}` : `${key}: {${child.id}}`);
            if (!this._conceptEdges.some(e => e.source === node.id && e.target === child.id)) {
                this._conceptEdges.push({ source: node.id, target: child.id });
            }
        });
        node.value = listForm ? `[${parts.join(', ')}]` : parts.join('\n');
        if (card) {
            const v = card.querySelector('.concept-value-input');
            if (v) v.value = node.value;
        }
        this._drawConceptEdges();
        return true;
    },

    // ── §R.5 — markdown-gesture outline strategy ────────────────────────
    //
    // "when tree structures are modified with markdown editor gestures
    //  like dashes, tabs, numbers, and newlines with trailing text that
    //  aren't other newlines, the structure of the computation graph, the
    //  other side of the dialectic representation scheme, updates
    //  accordingly." (USER_REQUIREMENTS_VERBATIM.md §R.5)
    //
    // Shared semantics with the backend `parse_markdown_tree`
    // (compile_pipeline.py): dash/star bullets + `1.`/`1)` numbering open
    // a node, tab/space indentation nests (tab = 4 columns), a bare
    // non-blank line is a sibling, blank newlines are non-structural.

    _looksLikeMarkdownTree(text) {
        if (!text) return false;
        const lines = String(text).replace(/\r\n/g, '\n').split('\n').filter(l => l.trim());
        if (!lines.length) return false;
        const marker = /^[ \t]*(?:-|\*|\d+[.)])\s+\S/;
        if (lines.some(l => marker.test(l))) return true;
        if (lines.length >= 2) {
            return lines.slice(1).some(l => l[0] === ' ' || l[0] === '\t');
        }
        return false;
    },

    _mdIndentWidth(ws) {
        let w = 0;
        for (const c of ws) w += (c === '\t') ? 4 : 1;
        return w;
    },

    /**
     * §R.5 — parse a markdown-gesture outline into TOP-LEVEL entries
     * `[{key, value}]`. `value` keeps the child sub-block as raw markdown
     * (base indent stripped) so recursion re-applies the same strategy;
     * an inline value joins ahead of the sub-block. Keys: a `key:` row
     * uses its key; a labelled branch uses its label; a plain leaf item
     * uses its positional index (matching backend `decompose_top_level`).
     * Returns null when the text is not a markdown outline.
     */
    _parseMarkdownTopLevel(text) {
        if (!this._looksLikeMarkdownTree(text)) return null;
        const markerRe = /^([ \t]*)(-|\*|\d+[.)])\s+(\S.*)$/;
        const toks = [];
        for (const raw of String(text).replace(/\r\n/g, '\n').split('\n')) {
            if (!raw.trim()) continue;  // blank newlines are non-structural
            const m = raw.match(markerRe);
            if (m) {
                toks.push({ indent: this._mdIndentWidth(m[1]), text: m[3].trim(), raw });
            } else {
                const stripped = raw.replace(/^[ \t]+/, '');
                const ws = raw.slice(0, raw.length - stripped.length);
                toks.push({ indent: this._mdIndentWidth(ws), text: stripped.trimEnd(), raw });
            }
        }
        if (!toks.length) return null;
        const base = Math.min(...toks.map(t => t.indent));
        const entries = [];
        const kvRe = /^([^:{}\[\]]+?):\s?(.*)$/;
        let i = 0, leafIdx = 0;
        while (i < toks.length) {
            const t = toks[i];
            if (t.indent > base) { i += 1; continue; }  // ragged stray — skip
            // Collect this entry's child block (every deeper token run).
            const childToks = [];
            let j = i + 1;
            while (j < toks.length && toks[j].indent > base) {
                childToks.push(toks[j]);
                j += 1;
            }
            const kv = t.text.match(kvRe);
            let key, inline;
            if (kv && kv[1].trim()) {
                key = kv[1].trim();
                inline = (kv[2] || '').trim();
            } else if (childToks.length) {
                key = t.text;          // labelled branch
                inline = '';
            } else {
                key = String(leafIdx); // plain leaf — positional key
                inline = t.text;
            }
            let value = inline;
            if (childToks.length) {
                const childBase = Math.min(...childToks.map(c => c.indent));
                const sub = childToks.map(c => {
                    // Strip childBase columns of leading whitespace, preserving
                    // deeper relative indentation (tab = 4 columns).
                    let need = childBase, k = 0, line = c.raw;
                    while (k < line.length && need > 0 && (line[k] === ' ' || line[k] === '\t')) {
                        need -= (line[k] === '\t') ? 4 : 1;
                        k += 1;
                    }
                    return line.slice(k);
                }).join('\n');
                value = inline ? (inline + '\n' + sub) : sub;
            }
            entries.push({ key, value });
            leafIdx += 1;
            i = j;
        }
        return entries.length ? entries : null;
    },

    /**
     * §R.5 / §7.1 — decompose a markdown-gesture outline into one child
     * card per top-level entry, rewriting the parent to `- key: {child.id}`
     * rows (the dash gesture is preserved so the parent stays a markdown
     * tree that recompiles back — §R.1 commutation). Mirrors
     * `_decomposeIndentTree`'s round-trip. Returns true if decomposition
     * happened.
     */
    _decomposeMarkdownTree(node) {
        const entries = this._parseMarkdownTopLevel(node.value);
        if (!entries || !entries.length) return false;
        // Genuine structure gate (rank-1 minimalism, §N.14): ≥2 entries, or
        // one entry with a nested sub-block.
        const hasStructure = entries.length >= 2 ||
            (entries.length === 1 && entries[0].value.indexOf('\n') >= 0);
        if (!hasStructure) return false;
        const card  = document.querySelector(`.concept-card[data-node-id="${node.id}"]`);
        const parts = [];
        entries.forEach(({ key, value }) => {
            const childRaw = `${node.id}__${key}`;
            const childId  = this._conceptSlugify(childRaw);
            let child = this._conceptNodes.get(childId);
            if (!child) {
                // §7.3.2 / §K.5 — ray-constrained fan around the parent.
                child = this.addConceptNode(childRaw, undefined, undefined, { anchorId: node.id });
            }
            if (!child) return;
            child.value = (value || '').replace(/\n+$/, '');
            child._autoCreated = true;
            const childCard = document.querySelector(`.concept-card[data-node-id="${child.id}"]`);
            if (childCard) {
                const valEl = childCard.querySelector('.concept-value-input');
                if (valEl) valEl.value = child.value;
                this._applyCompiledChildMode(childCard);  // §4.5 value-only
            }
            // Recurse: a sub-block child decomposes further (§7.1 step 3).
            this._decomposeValue(child);
            parts.push(`- ${key}: {${child.id}}`);
            if (!this._conceptEdges.some(e => e.source === node.id && e.target === child.id)) {
                this._conceptEdges.push({ source: node.id, target: child.id });
            }
        });
        node.value = parts.join('\n');
        if (card) {
            const v = card.querySelector('.concept-value-input');
            if (v) v.value = node.value;
        }
        this._drawConceptEdges();
        return true;
    },

    /**
     * Parse a tab/space-indented `key: value` block into its TOP-LEVEL
     * entries. Returns `[{key, value}]` (value may be multi-line, one
     * indent level stripped), or `null` if the text is not a clean
     * indent tree (no top-level `key:` line). §4.2.2 IndentTree strategy.
     */
    _parseTopLevelIndentEntries(text) {
        const lines = String(text).replace(/\r\n/g, '\n').split('\n');
        const indentOf = (s) => { let n = 0; while (n < s.length && (s[n] === ' ' || s[n] === '\t')) n++; return n; };
        const entries = [];
        let cur = null;
        let sawKey = false;
        for (const raw of lines) {
            if (!raw.trim()) { if (cur) cur.value += '\n'; continue; }
            if (indentOf(raw) === 0) {
                // A top-level `key: value` row (key may contain spaces, §O.10;
                // exclude brace/JSON-ish lines so we don't misparse a ref).
                const m = raw.match(/^([^:{}\[\]]+?):\s?(.*)$/);
                if (m) {
                    sawKey = true;
                    cur = { key: m[1].trim(), value: m[2] || '' };
                    entries.push(cur);
                } else if (cur) {
                    cur.value += (cur.value ? '\n' : '') + raw;
                } else {
                    return null;  // top-level non-key line with no current entry
                }
            } else {
                if (!cur) return null;
                cur.value += (cur.value !== '' ? '\n' : '') + raw.replace(/^[ \t]/, '');
            }
        }
        return sawKey ? entries : null;
    },

    /**
     * §7.1 / §4.2.2 — decompose a native indented field-tree into one child
     * card per top-level key, rewriting the parent to `key: {child.id}`
     * rows that recompile back to the original tree. Mirrors the JSON path's
     * round-trip. Returns true if decomposition happened.
     */
    _decomposeIndentTree(node) {
        const entries = this._parseTopLevelIndentEntries(node.value);
        if (!entries || entries.length === 0) return false;
        // Only decompose when there's genuine structure: ≥2 keys, or a single
        // key whose value spans multiple lines (a nested sub-tree). A lone
        // scalar `key: value` stays a leaf (rank-1 minimalism, §N.14).
        const hasStructure = entries.length >= 2 ||
            (entries.length === 1 && entries[0].value.indexOf('\n') >= 0);
        if (!hasStructure) return false;
        const card  = document.querySelector(`.concept-card[data-node-id="${node.id}"]`);
        const parts = [];
        entries.forEach(({ key, value }) => {
            const childRaw = `${node.id}__${key}`;
            const childId  = this._conceptSlugify(childRaw);
            let child = this._conceptNodes.get(childId);
            if (!child) {
                // §7.3.2 / §K.5 — ray-constrained fan around the parent.
                child = this.addConceptNode(childRaw, undefined, undefined, { anchorId: node.id });
            }
            if (!child) return;
            child.value = (value || '').replace(/\n+$/, '');
            child._autoCreated = true;
            const childCard = document.querySelector(`.concept-card[data-node-id="${child.id}"]`);
            if (childCard) {
                const valEl = childCard.querySelector('.concept-value-input');
                if (valEl) valEl.value = child.value;
                this._applyCompiledChildMode(childCard);  // §4.5 value-only
            }
            // Recurse: a sub-tree child decomposes further (§7.1 step 3).
            this._decomposeValue(child);
            parts.push(`${key}: {${child.id}}`);
            if (!this._conceptEdges.some(e => e.source === node.id && e.target === child.id)) {
                this._conceptEdges.push({ source: node.id, target: child.id });
            }
        });
        node.value = parts.join('\n');
        if (card) {
            const v = card.querySelector('.concept-value-input');
            if (v) v.value = node.value;
        }
        this._drawConceptEdges();
        return true;
    },

    /**
     * §4.5 / §8D.2.2.1 — render a compiled-graph child as VALUE ONLY (the
     * name is implicit from structural position). Additive + low-risk: it
     * hides the name/description/compile chrome on the already-built card,
     * leaving the value print + a thin drag strip, so the child still
     * supports hover/click/halo (§8.2.3) and folds back on collapse. Mode
     * is applied post-build rather than forking the card builder (§18.11).
     */
    _applyCompiledChildMode(childCard) {
        if (!childCard) return;
        childCard.classList.add('concept-card--compiled-child');
        const nameInput = childCard.querySelector('.concept-name-input');
        if (nameInput) nameInput.style.display = 'none';
        childCard.querySelectorAll('.concept-desc-input, .concept-compile-btn')
            .forEach((el) => { el.style.display = 'none'; });
        // §S.4 — no header to shrink; the value-only slate IS the compute node.
    },

    /**
     * Public seeding helper. Spawn a concept card whose value is the
     * provided payload — used by selectNode / pinBillboard to turn a
     * clicked 3D sphere into a 2D concept-graph card with the
     * sphere's HTML summary as its value. Auto-decomposes JSON
     * payloads, leaves HTML / plain text intact.
     *
     * Returns the freshly-created node (or the existing one if a
     * card with this preferred name was already present).
     */
    spawnConceptFromValue(name, valueStr, opts) {
        const cfg = opts || {};
        // Centre the new card near the viewport's middle-right so it
        // doesn't paint over the user's existing graph.
        const x = (typeof cfg.x === 'number')
            ? cfg.x
            : Math.max(60, (window.innerWidth || 1200) - 360);
        const y = (typeof cfg.y === 'number')
            ? cfg.y
            : Math.max(60, 80 + (this._conceptNodes.size % 6) * 32);
        // If a card with this slug already exists, just update its
        // value rather than spawning a duplicate (idempotent multi-
        // click on the same 3D sphere).
        const slug = this._conceptSlugify(name);
        let node = this._conceptNodes.get(slug);
        if (!node) {
            node = this.addConceptNode(name, x, y);
        }
        if (!node) return null;
        node.value = String(valueStr || '');
        if (cfg.description) node.description = cfg.description;
        // Push the textarea contents live.
        const card = document.querySelector(`.concept-card[data-node-id="${node.id}"]`);
        if (card) {
            const v = card.querySelector('.concept-value-input');
            if (v) v.value = node.value;
            const d = card.querySelector('.concept-desc-input');
            if (d && cfg.description) d.value = cfg.description;
            // Stamp the linked 3D node id onto the card so
            // _drawConcept3DLinks (called from the animate loop) can
            // pull this card's matching sphere position each frame and
            // draw a SOLID arrow between them.
            if (cfg.nodeId) {
                card.dataset['3dNodeId'] = cfg.nodeId;
                card.setAttribute('data-3d-node-id', cfg.nodeId);
            }
        }
        // First-pass reference parse so any `{}` substitutions in
        // an HTML summary's interpolated text still resolve.
        this._parseConceptReferences(node);
        this._drawConceptEdges();
        return node;
    },

    // ── Retrieval: per-card suggestions ──────────────────────────────────────

    _conceptTokenize(s) {
        return ((s || '').toLowerCase().match(/[a-z0-9]+/g) || [])
            .filter(t => t.length >= 2);
    },

    _conceptSimilarity(aTokens, bTokens) {
        if (!aTokens.length || !bTokens.length) return 0;
        const A = new Set(aTokens), B = new Set(bTokens);
        let inter = 0;
        for (const t of A) if (B.has(t)) inter++;
        const union = A.size + B.size - inter;
        return union ? inter / union : 0;
    },

    _conceptRetrieve(fromNode, k = 3) {
        const queryTokens = this._conceptTokenize(fromNode.description);
        if (!queryTokens.length) return [];
        const out = [];
        this._conceptNodes.forEach(other => {
            if (other.id === fromNode.id) return;
            const corpus = `${other.name} ${other.description} ${other.value}`;
            const score = this._conceptSimilarity(queryTokens, this._conceptTokenize(corpus));
            if (score > 0) out.push({ id: other.id, name: other.name, score });
        });
        out.sort((a, b) => b.score - a.score);
        return out.slice(0, k);
    },

    _renderConceptSuggestions(card, node) {
        const host = card.querySelector('.concept-suggestions');
        if (!host) return;
        // W6 / §8D.43 — prefer backend triple-product retrieval. The
        // local token-Jaccard fallback (_conceptRetrieve) runs if the
        // backend is unreachable or the card hasn't been indexed yet.
        if (this._conceptBackendOk) {
            this._fetchApparitionsForFocal(node.id, 3)
                .then(remote => {
                    if (remote && remote.length) {
                        this._renderSuggestionChips(host, card, node, remote);
                    } else {
                        this._renderSuggestionChips(host, card, node, this._conceptRetrieve(node, 3));
                    }
                })
                .catch(() => {
                    this._renderSuggestionChips(host, card, node, this._conceptRetrieve(node, 3));
                });
            return;
        }
        const hits = this._conceptRetrieve(node, 3);
        this._renderSuggestionChips(host, card, node, hits);
    },

    /**
     * Render an array of suggestion hits as chips. Hits may be either
     * the local shape ({ id, name, score }) or the backend shape
     * ({ card_id, score, pagerank, tfidf_cos, nomic_cos, provenance }).
     */
    _renderSuggestionChips(host, card, node, hits) {
        if (!hits || !hits.length) {
            host.innerHTML = '';
            host.style.display = 'none';
            if (typeof this._mirrorUi === 'function') this._mirrorUi('/api/ui/autocomplete_clear', {});
            return;
        }
        host.style.display = 'flex';
        // §17.15 / §4.7 — mirror the autocomplete dropdown (the {var} suggestion
        // chips) so peer tabs + REPL see the open completion set.
        if (typeof this._mirrorUi === 'function')
            this._mirrorUi('/api/ui/autocomplete', {
                row_id: node.id, parent_card_id: node.id,
                query: String(node.description || node.value || ''),
                candidates: hits.map(h => ({ card_id: h.card_id || h.id, name: h.name || (h.card_id || h.id), score: (typeof h.score === 'number') ? h.score : 0 })),
            });
        host.innerHTML = hits.map(h => {
            const id = h.card_id || h.id;
            const name = h.name || id;
            const score = (typeof h.score === 'number') ? h.score : 0;
            return `
                <button type="button" class="concept-suggestion-chip"
                        data-target="${this._conceptEscapeHtml(id)}"
                        title="Insert {${this._conceptEscapeHtml(id)}} into the value field (score ${score.toFixed(2)})">
                    ${this._conceptEscapeHtml(name)}
                    <span class="concept-suggestion-score">${(score * 100).toFixed(0)}%</span>
                </button>
            `;
        }).join('');
        host.querySelectorAll('.concept-suggestion-chip').forEach(chip => {
            chip.addEventListener('click', (ev) => {
                ev.stopPropagation();
                const targetId = chip.dataset.target;
                if (!targetId) return;
                this._conceptInsertReference(card, node, targetId);
            });
        });
    },

    /**
     * Fetch apparitions for a focal concept node from the backend
     * triple-product retrieval endpoint (§8D.43). Returns a Promise
     * resolving to the candidate array (possibly empty).
     *
     * W25 — for nodes whose type_hint identifies them as
     * typed-graph artefacts (fixture_database, fixture_web_browser,
     * xpath_pattern, committed_subgraph, module), fall back to
     * DB-ontology recursion (§8D.36.3) where typed edges dominate.
     */
    async _fetchApparitionsForFocal(focalId, k = 10) {
        if (!focalId) return [];
        const node = this._conceptNodes && this._conceptNodes.get(focalId);
        const useOntology = node && (
            node.type_hint === 'fixture_database' ||
            node.type_hint === 'fixture_web_browser' ||
            node.type_hint === 'xpath_pattern' ||
            node.type_hint === 'committed_subgraph' ||
            node.type_hint === 'module'
        );
        const ws = this._conceptWorkspaceId || '';
        const params = new URLSearchParams({ k: String(k) });
        if (ws) params.set('workspace_id', ws);
        const url = useOntology
            ? `/api/ontology_walk/${encodeURIComponent(focalId)}?${params.toString()}&depth=1`
            : `/api/apparitions/${encodeURIComponent(focalId)}?${params.toString()}&transport=1`;
        try {
            const resp = await fetch(url);
            if (!resp.ok) return [];
            const data = await resp.json();
            if (useOntology) {
                // Adapt neighbour shape to the apparition-card shape
                // the halo renderer expects.
                const neighbours = Array.isArray(data && data.neighbours) ? data.neighbours : [];
                return neighbours.map(n => ({
                    card_id: n.card_id,
                    score:   Math.max(0, 1 - (n.distance || 0) * 0.3),
                    pagerank: 0,
                    tfidf_cos: 0,
                    nomic_cos: 0,
                    edge_type: n.edge_type || 'RELATES_TO',
                    distance: n.distance,
                }));
            }
            return Array.isArray(data && data.candidates) ? data.candidates : [];
        } catch (e) {
            return [];
        }
    },

    /**
     * W12 / §8D.22 — Render an apparition halo: phantom cards arranged
     * on a 2D arc around the focal card. Unlike the in-card chips
     * (which appear below the description), the halo is a transient
     * overlay on document.body that disappears on mouseleave. The
     * arc spans 180° centred above the focal so the halo doesn't
     * collide with the body fields.
     *
     * Called from:
     *   - hover handler (W13) when the user moves the mouse onto a
     *     stuck card; phantom halo appears around it.
     *   - empty-primitive radiation (W20) when typed text drives
     *     candidate retrieval.
     *
     * candidates: [{ card_id, score, pagerank, tfidf_cos, nomic_cos, ... }]
     */
    _renderApparitionHalo(focalCard, candidates) {
        if (!focalCard || !candidates || !candidates.length) {
            this._clearApparitionHalo();
            return;
        }
        // Reuse the halo overlay if it already exists for this focal.
        const focalId = focalCard.dataset.nodeId;
        if (this._haloFocalId === focalId && this._haloOverlay) {
            // Refresh content in place.
            this._populateHalo(this._haloOverlay, focalCard, candidates);
            // §8.2 / §14.2 — re-target with the same focal but a
            // possibly-different candidate list (cascade re-fire,
            // PageRank shift, etc.).
            this._postHaloFocusMirror(focalId, candidates);
            return;
        }
        this._clearApparitionHalo();
        const overlay = document.createElement('div');
        overlay.className = 'concept-apparition-halo';
        overlay.style.cssText =
            'position:fixed; left:0; top:0; width:100vw; height:100vh; ' +
            'pointer-events:none; z-index:9985;';
        document.body.appendChild(overlay);
        this._haloOverlay = overlay;
        this._haloFocalId = focalId;
        this._haloCandidates = candidates;
        this._haloFocalCard = focalCard;
        this._populateHalo(overlay, focalCard, candidates);
        // §8.2 / §14.2 — open mirror; backend ui_state_service records
        // halo_focus + broadcasts ui_state_changed; REPL viewer + peer
        // tabs + agent perception all see the same focal + candidates.
        this._postHaloFocusMirror(focalId, candidates);
        // Fix: re-populate the halo on viewport resize so phantoms
        // stay anchored relative to the (now-different-position)
        // focal card. Without this, resizing the window leaves
        // phantoms at their pre-resize coordinates and they appear
        // detached from the focal.
        if (!this._haloResizeListener) {
            this._haloResizeListener = () => {
                if (this._haloOverlay && this._haloFocalCard && this._haloCandidates) {
                    this._populateHalo(
                        this._haloOverlay,
                        this._haloFocalCard,
                        this._haloCandidates,
                    );
                }
            };
            window.addEventListener('resize', this._haloResizeListener);
        }
    },

    _populateHalo(overlay, focalCard, candidates) {
        // Compute focal centre.
        const r = focalCard.getBoundingClientRect();
        const cx = r.left + r.width / 2;
        const cy = r.top + r.height / 2;
        // Arc radius scales with how many candidates we have.
        const k = candidates.length;
        const radius = Math.max(160, 120 + k * 12);
        // W31 — choose arc orientation based on which screen edge
        // the focal is nearest. Default is the half-ellipse above
        // the focal (-π → 0). If the focal is in the top quarter,
        // place the halo below; if in the bottom quarter, above;
        // if in either left or right quarter, place horizontally.
        const vw = window.innerWidth || 1200;
        const vh = window.innerHeight || 800;
        let startAngle, endAngle, yScale;
        if (cy < vh * 0.25) {
            // Focal near top — arc below.
            startAngle = 0; endAngle = Math.PI; yScale = 0.55;
        } else if (cy > vh * 0.75) {
            // Focal near bottom — arc above (default direction).
            startAngle = -Math.PI; endAngle = 0; yScale = 0.55;
        } else if (cx < vw * 0.25) {
            // Focal near left — arc to the right.
            startAngle = -Math.PI / 2; endAngle = Math.PI / 2; yScale = 1.0;
        } else if (cx > vw * 0.75) {
            // Focal near right — arc to the left.
            startAngle = Math.PI / 2; endAngle = 3 * Math.PI / 2; yScale = 1.0;
        } else {
            // Default: half-ellipse above.
            startAngle = -Math.PI; endAngle = 0; yScale = 0.55;
        }
        const span = endAngle - startAngle;
        // Wipe prior children.
        overlay.innerHTML = '';
        // §8B — pre-compute the focal's existing outgoing-edge target
        // set so we can mark CONNECTED candidates distinctly from
        // POTENTIAL ones. Connected = already wired; Potential = could
        // be wired. The visual contract:
        //   Connected  → solid green border, "→" prefix.
        //   Potential  → dashed blue border, "+" prefix (default).
        //   New Link   → trailing "✦ new" phantom that spawns an empty.
        const focalId = focalCard && focalCard.dataset && focalCard.dataset.nodeId;
        const connected = new Set();
        if (this._conceptEdges) {
            for (const e of this._conceptEdges) {
                if (e.source === focalId) connected.add(e.target);
            }
        }
        // Render the candidate phantoms.
        const total = k + 1;   // reserve one slot for the New Link affordance
        candidates.forEach((c, i) => {
            const t = total === 1 ? 0.5 : (i / (total - 1));
            const a = startAngle + t * span;   // arc around focal (orientation-aware)
            // §O.18 cone-ray transport — closer-on-cone == more similar: scale
            // each phantom's radius by its similarity (the backend transport
            // scalar when present, else index-derived) so the most-similar
            // candidates sit nearest the focal apex.
            const _sim = (c.transport && typeof c.transport.similarity === 'number')
                ? c.transport.similarity : (k > 1 ? (1 - i / (k - 1)) : 1);
            const _rEff = radius * (0.55 + 0.45 * (1 - _sim));
            // §O.18 cone-ray transport — the SECOND axis: ``along_ray`` (= s·R,
            // depth toward the cone apex/viewer) drives a depth cue so the ring
            // reads as a true projected CONE, not a flat ellipse. radial=(1-s)·R
            // (the _rEff perpendicular offset above) + along_ray=s·R sum to R,
            // so along_ray/(radial+along_ray) == similarity; use the backend
            // scalar when present. More-along-ray ⇒ nearer the apex ⇒ rendered
            // larger + on top (closer-on-cone == more similar, §O.18 / §8.2.1.1).
            let _alongNorm = _sim;
            if (c.transport && typeof c.transport.along_ray === 'number') {
                const _ar = c.transport.along_ray;
                const _rad = (typeof c.transport.radial === 'number') ? c.transport.radial : 0;
                const _den = _ar + _rad;
                if (_den > 1e-6) _alongNorm = Math.max(0, Math.min(1, _ar / _den));
            }
            const _depthScale = 0.80 + 0.40 * _alongNorm;   // apex-near ⇒ larger
            const _depthZ = 1000 + Math.round(1000 * _alongNorm);  // apex-near ⇒ on top
            // W31 — clamp phantom positions to viewport with 8px margin.
            let px = cx + Math.cos(a) * _rEff;
            let py = cy + Math.sin(a) * (_rEff * yScale);
            px = Math.max(72, Math.min((window.innerWidth || 1200) - 72, px));
            py = Math.max(28, Math.min((window.innerHeight || 800) - 36, py));
            const targetId = c.card_id || c.id || '';
            const isConnected = targetId && connected.has(targetId);
            const phantom = document.createElement('div');
            phantom.className = 'concept-apparition-phantom';
            phantom.dataset.cardId = targetId;
            phantom.dataset.state = isConnected ? 'connected' : 'potential';
            // §8D.1.3 — the halo phantom shows ONLY the candidate's NAME (not
            // its id). The backend always supplies a non-empty name (apparition
            // name-guard); fall back to id only defensively.
            const name = c.name || c.card_id || c.id || '?';
            const score = (typeof c.score === 'number') ? c.score : 0;
            // §8D.1.3 — scores live in the slow-hover tooltip ONLY (no score chip
            // on the phantom face, §18.21). The full name is here for §O.4.
            phantom.title =
                `${this._conceptEscapeHtml(name)}\n` +
                `${isConnected ? 'connected · ' : 'potential · '}` +
                `score ${score.toFixed(3)} ` +
                `(pr ${(c.pagerank || 0).toFixed(3)}, ` +
                `tf ${(c.tfidf_cos || 0).toFixed(3)}, ` +
                `nm ${(c.nomic_cos || 0).toFixed(3)})`;
            // §2.4/§3.2/§O.16 — connected vs potential by silver BRIGHTNESS +
            // WEIGHT, never by hue; SOLID border (no dashes), no arrowheads.
            const borderColor = isConnected ? 'var(--silver-300, #b8c0c8)' : 'var(--silver-700, #555c63)';
            const borderWidth = isConnected ? '2px' : '1px';
            const prefix = isConnected ? '→' : '+';
            phantom.style.cssText =
                'position:absolute;' +
                `left:${Math.round(px - 60)}px; top:${Math.round(py - 18)}px;` +
                'width:120px; padding:4px 6px;' +
                'background:#000; color:var(--silver-200,#d7dde2);' +
                `border:${borderWidth} solid ${borderColor}; border-radius:4px;` +
                'font-family:monospace; font-size:10px;' +
                'overflow:hidden; text-overflow:ellipsis; white-space:nowrap;' +
                'pointer-events:auto; cursor:pointer; opacity:0.92;' +
                // §O.18 — along_ray depth cue: apex-near phantoms larger + on top.
                `transform:scale(${_depthScale.toFixed(3)}); z-index:${_depthZ};` +
                'transition:opacity 120ms, transform 120ms;';
            // §8.2.2 / §10 theme — HSV PROPAGATION: the ONE permitted colour in
            // the halo. When the candidate is a ray-projected 3D chunk, the
            // phantom inherits that node's UMAP HSV as a left-edge accent (the
            // connector lines stay silver §O.16; only this edge carries hue).
            // §709/§18.26 — the phantom carries its parent chunk's
            // slowly-rotating content-HSV hue: the SAME {h,s,l} (init.umapHsl,
            // coords[3:6]) and the SAME live camera-azimuth phase the projector
            // mesh uses this frame, so visual identity persists across the
            // 3D→2D dimensional collapse. The animate loop's
            // _updateHaloPhantomHues keeps it rotating thereafter (§709).
            // (Previously this read umapColor.r/.g/.b on a THREE.Vector3 — which
            // only exposes .x/.y/.z — so every phantom border was rgb(0,0,0).)
            const _nodeInit = this.initialNodeData && this.initialNodeData.get(targetId);
            const _Cp = this.constructor;
            if (_nodeInit && _nodeInit.umapHsl && _Cp && typeof _Cp.hslToRgb === 'function') {
                const _hsl = _nodeInit.umapHsl;
                const _phase = this._currentHuePhase || 0;
                const _h = _Cp.applyHuePhase ? _Cp.applyHuePhase(_hsl.h, _phase) : _hsl.h;
                const _rgb = _Cp.hslToRgb(_h, _hsl.s, _hsl.l);
                const _css = `rgb(${Math.round(_rgb[0] * 255)},${Math.round(_rgb[1] * 255)},${Math.round(_rgb[2] * 255)})`;
                phantom.style.borderLeft = `3px solid ${_css}`;
            }
            // §8D.1.3 / §18.21 — NAME ONLY, no score chip.
            phantom.innerHTML =
                `<span style="display:block;overflow:hidden;text-overflow:ellipsis;">` +
                `<span style="color:var(--silver-500,#7c858d);font-weight:bold;margin-right:3px;">${prefix}</span>` +
                this._conceptEscapeHtml(name) + `</span>`;
            // §8B.6 — Potential phantoms get a hover-delayed
            // candidate-list panel; Connected phantoms don't (the
            // user already knows that target). Timer starts on
            // enter, cancels on leave. The panel itself self-
            // dismisses when its own mouseleave fires (with a brief
            // grace window so the user can move into it).
            let _candTimer = null;
            phantom.addEventListener('mouseenter', () => {
                phantom.style.opacity = '1';
                phantom.style.transform = `scale(${(_depthScale * 1.06).toFixed(3)})`;
                if (!isConnected) {
                    if (_candTimer) clearTimeout(_candTimer);
                    _candTimer = setTimeout(() => {
                        this._showCandidateListPanel(phantom, focalId);
                    }, 520);
                }
            });
            phantom.addEventListener('mouseleave', (ev) => {
                phantom.style.opacity = '0.88';
                phantom.style.transform = `scale(${_depthScale.toFixed(3)})`;
                if (_candTimer) { clearTimeout(_candTimer); _candTimer = null; }
                // Grace window: if cursor lands on the candidate
                // panel itself, _showCandidateListPanel installs its
                // own listeners and keeps the panel open.
                const to = ev.relatedTarget;
                if (to && to.closest && to.closest('.concept-candidate-panel')) return;
                setTimeout(() => {
                    const panel = document.querySelector('.concept-candidate-panel');
                    if (panel && !panel.matches(':hover') &&
                        !phantom.matches(':hover')) {
                        this._hideCandidateListPanel();
                    }
                }, 240);
            });
            phantom.addEventListener('click', (ev) => {
                ev.stopPropagation();
                const targetId = phantom.dataset.cardId;
                if (!targetId) return;
                // §8.2.2 autoregression — clicking a halo phantom pushes it onto
                // the halo chain. Mirror so peer tabs + REPL track the chain.
                if (typeof this._mirrorUi === 'function')
                    this._mirrorUi('/api/ui/halo_chain_push', { focal_card_id: targetId });
                const focalNode = this._conceptNodes.get(focalId);
                const card = focalNode && document.querySelector(`.concept-card[data-node-id="${focalId}"]`);
                // §8D.22 — if the focal is an EMPTY PRIMITIVE,
                // clicking a phantom RESOLVES the empty into the
                // chosen type: adopt the candidate's name/description,
                // draw a DERIVED_FROM edge back to it, and clear
                // the empty-primitive badge. Otherwise (regular
                // card) fall back to the chip-style insert-{ref}
                // behaviour.
                if (card && card.dataset.emptyPrimitive === '1' && focalNode) {
                    this._resolveEmptyPrimitive(card, focalNode, targetId);
                } else if (focalNode && card) {
                    this._conceptInsertReference(card, focalNode, targetId);
                }
                this._clearApparitionHalo();
                // §8.2.2 / ConceptEdge.md §3.4 step 5 — the autoregressive WALK:
                // after committing, a new halo opens around the clicked
                // candidate automatically so the user keeps walking the
                // retrieval space (the halo_chain push above records the step).
                const nextCard = document.querySelector(
                    `.concept-card[data-node-id="${targetId}"]`);
                if (nextCard && typeof this._fetchApparitionsForFocal === 'function') {
                    this._fetchApparitionsForFocal(targetId, 6).then((cands) => {
                        if (cands && cands.length)
                            this._renderApparitionHalo(nextCard, cands);
                    }).catch(() => {});
                }
            });
            overlay.appendChild(phantom);
        });
        // §8B "New Link" affordance — a trailing phantom that always
        // appears at the end of the arc, regardless of candidate set.
        // Clicking it spawns a fresh empty primitive near the focal
        // (per §8D.22), which the user can then type into to drive a
        // new radiation pass. White "✦" badge to differentiate from
        // the connected / potential phantoms.
        const newLinkT = total === 1 ? 0.5 : ((total - 1) / (total - 1));
        const aN = startAngle + newLinkT * span;
        let nx = cx + Math.cos(aN) * radius;
        let ny = cy + Math.sin(aN) * (radius * yScale);
        nx = Math.max(72, Math.min((window.innerWidth || 1200) - 72, nx));
        ny = Math.max(28, Math.min((window.innerHeight || 800) - 36, ny));
        const newLink = document.createElement('div');
        newLink.className = 'concept-apparition-phantom';
        newLink.dataset.state = 'new_link';
        newLink.title = 'Spawn an empty primitive to start a new link from this card';
        newLink.style.cssText =
            'position:absolute;' +
            `left:${Math.round(nx - 60)}px; top:${Math.round(ny - 18)}px;` +
            'width:120px; padding:4px 6px;' +
            'background:rgba(255,255,255,0.08); color:#e5e7eb;' +
            'border:1px dotted rgba(229,231,235,0.4); border-radius:6px;' +
            'font-family:monospace; font-size:10px; text-align:center;' +
            'pointer-events:auto; cursor:pointer; opacity:0.78;' +
            'transition:opacity 120ms, transform 120ms;';
        newLink.innerHTML =
            '<span style="color:#fef3c7;font-weight:bold;margin-right:3px;">✦</span>' +
            'new link';
        newLink.addEventListener('mouseenter', () => {
            newLink.style.opacity = '1';
            newLink.style.transform = 'scale(1.06)';
        });
        newLink.addEventListener('mouseleave', () => {
            newLink.style.opacity = '0.78';
            newLink.style.transform = '';
        });
        newLink.addEventListener('click', (ev) => {
            ev.stopPropagation();
            // §8B.7 — open the ghost-node type-selection menu instead
            // of immediately spawning an empty primitive. The user
            // picks the target type up-front; commit creates a real
            // concept and wires a RELATES_TO edge back to the focal.
            // Esc / click-outside dismisses with no side effects.
            this._openGhostNodeMenu(newLink, focalId);
        });
        overlay.appendChild(newLink);
    },

    /**
     * §709 — collapsed halo phantoms rotate in colour with their projector
     * parents. Called once per animate frame from animation.js (render-only;
     * the Python REPL has no DOM/camera, so this is outside its observation
     * surface — DOMAIN_MODEL §6.1 REPL/render split). Cheap: a no-op unless a
     * halo is open. Each phantom whose parent 3D node carries content-HSV
     * (init.umapHsl, from coords[3:6]) gets its left-edge accent re-derived from
     * that {h,s,l} plus the current camera-azimuth hue phase — the SAME maths
     * the projector mesh uses — so the hues track across the 3D→2D collapse.
     */
    _updateHaloPhantomHues() {
        const Cp = this.constructor;
        if (!Cp || typeof Cp.hslToRgb !== 'function') return;
        const phantoms = document.getElementsByClassName('concept-apparition-phantom');
        if (!phantoms || !phantoms.length) return;
        const phase = this._currentHuePhase || 0;
        for (let k = 0; k < phantoms.length; k++) {
            const el = phantoms[k];
            const id = el.dataset && el.dataset.cardId;
            if (!id) continue;
            const init = this.initialNodeData && this.initialNodeData.get(id);
            if (!init || !init.umapHsl) continue;
            const hsl = init.umapHsl;
            const h = Cp.applyHuePhase ? Cp.applyHuePhase(hsl.h, phase) : hsl.h;
            const rgb = Cp.hslToRgb(h, hsl.s, hsl.l);
            el.style.borderLeft = '3px solid rgb(' +
                Math.round(rgb[0] * 255) + ',' +
                Math.round(rgb[1] * 255) + ',' +
                Math.round(rgb[2] * 255) + ')';
        }
    },

    /**
     * §8B.7 — Ghost-node creation flow.
     *
     * Opens a small floating menu anchored to the "✦ new link"
     * phantom. Options:
     *   • Empty primitive — current default (no commit yet)
     *   • User note       — creates a UserNote concept + edge
     *   • Ontology node   — creates an OntologyNode concept + edge
     *   • Pinned component — creates a PinnedComponent concept + edge
     *   • Search existing — opens the candidate-list panel (§8B.6)
     *
     * Each commit path:
     *   1. POST /api/concepts (with appropriate type_hint)
     *   2. POST /api/edges  (RELATES_TO from focal → new)
     *
     * The spec calls for a translucent ghost node + dashed line
     * preview before commit; the MVP here commits on choice so the
     * user sees the real card materialise. The translucent preview
     * is a follow-on visual polish — the type-up-front decision is
     * the spec gap that mattered.
     */
    _openGhostNodeMenu(anchorEl, focalId) {
        // One menu at a time. Clear any prior + the halo (so the
        // user's attention is on the choice).
        this._closeGhostNodeMenu();
        this._clearApparitionHalo();
        const menu = document.createElement('div');
        menu.className = 'concept-ghost-menu';
        const r = anchorEl.getBoundingClientRect();
        const vw = window.innerWidth || 1200;
        const vh = window.innerHeight || 800;
        // Anchor below-right of phantom; clamp to viewport.
        const left = Math.min(vw - 240, Math.max(8, r.right + 6));
        const top  = Math.min(vh - 220, Math.max(8, r.top));
        menu.style.cssText =
            'position:fixed; z-index:10060;' +
            `left:${Math.round(left)}px; top:${Math.round(top)}px;` +
            'width:232px; background:rgba(0,0,0,0.97); color:#e5e7eb;' +
            'border:1px solid rgba(184,192,200,0.6); border-radius:8px;' +
            'box-shadow:0 8px 24px rgba(0,0,0,0.55);' +
            'font-family:monospace; font-size:11px; padding:4px 0;' +
            'overflow:hidden;';
        const opts = [
            { label: 'Empty primitive',   hint: '',                  icon: 'star',
              tip: 'Spawn an empty concept card to fill in later' },
            { label: 'User note',         hint: 'user_note',         icon: 'sticky-note',
              tip: 'Free-form note attached to the focal' },
            { label: 'Ontology node',     hint: 'ontology_node',     icon: 'project-diagram',
              tip: 'Labelled concept in the ontology' },
            { label: 'Pinned component',  hint: 'pinned_component',  icon: 'thumbtack',
              tip: 'Component pinned from a DOM snapshot' },
            { label: 'Search existing',   hint: '__search__',        icon: 'search',
              tip: 'Open the candidate panel (§8B.6) for this focal' },
        ];
        const header = document.createElement('div');
        header.style.cssText =
            'padding:4px 10px;color:#9aa3ab;font-size:10px;' +
            'border-bottom:1px solid rgba(255,255,255,0.08);';
        header.textContent = 'Create a new link to…';
        menu.appendChild(header);
        for (const opt of opts) {
            const row = document.createElement('div');
            row.className = 'gnm-row';
            row.style.cssText =
                'padding:6px 10px; cursor:pointer;' +
                'display:flex;align-items:center;gap:8px;' +
                'border-bottom:1px solid rgba(255,255,255,0.04);';
            row.title = opt.tip;
            row.innerHTML =
                `<i class="fas fa-${opt.icon}" style="width:14px;color:#eef0f2;"></i>` +
                `<span>${this._conceptEscapeHtml(opt.label)}</span>`;
            row.addEventListener('mouseenter', () => {
                row.style.background = 'rgba(184,192,200,0.12)';
            });
            row.addEventListener('mouseleave', () => {
                row.style.background = '';
            });
            row.addEventListener('click', async (ev) => {
                ev.stopPropagation();
                this._closeGhostNodeMenu();
                await this._commitGhostNode(focalId, opt.hint);
            });
            menu.appendChild(row);
        }
        document.body.appendChild(menu);
        this._ghostMenu = menu;
        // Escape / click-outside dismissal — bind on next tick so the
        // click that opened the menu doesn't immediately close it.
        setTimeout(() => {
            const onKey = (e) => {
                if (e.key === 'Escape') { this._closeGhostNodeMenu(); }
            };
            const onClick = (e) => {
                if (this._ghostMenu && !this._ghostMenu.contains(e.target)) {
                    this._closeGhostNodeMenu();
                }
            };
            document.addEventListener('keydown', onKey);
            document.addEventListener('mousedown', onClick);
            this._ghostMenuListeners = { onKey, onClick };
        }, 0);
    },

    _closeGhostNodeMenu() {
        if (this._ghostMenu && this._ghostMenu.parentNode) {
            this._ghostMenu.parentNode.removeChild(this._ghostMenu);
        }
        this._ghostMenu = null;
        const ls = this._ghostMenuListeners;
        if (ls) {
            document.removeEventListener('keydown', ls.onKey);
            document.removeEventListener('mousedown', ls.onClick);
            this._ghostMenuListeners = null;
        }
    },

    /**
     * §8B.7 — Commit the ghost-node choice.
     *
     *   typeHint === ''            → spawn the §8D.22 empty primitive
     *                                (no commit; user fills in later)
     *   typeHint === '__search__'  → open the §8B.6 candidate panel
     *                                anchored to the focal card
     *   typeHint === <hint>        → POST /api/concepts with that
     *                                type_hint + POST /api/edges with
     *                                RELATES_TO from focal → new id
     */
    async _commitGhostNode(focalId, typeHint) {
        if (typeHint === '') {
            if (typeof this.spawnEmptyPrimitive === 'function') {
                this.spawnEmptyPrimitive({ anchorId: focalId });
            }
            return;
        }
        if (typeHint === '__search__') {
            // Fall back to the §8B.6 panel anchored to the focal card.
            const card = document.querySelector(
                `.concept-card[data-node-id="${focalId}"]`);
            if (card && typeof this._showCandidateListPanel === 'function') {
                this._showCandidateListPanel(card, focalId);
            }
            return;
        }
        // Real-commit path: create concept then wire edge.
        const friendly = ({
            user_note:        'note',
            ontology_node:    'concept',
            pinned_component: 'pin',
        })[typeHint] || 'node';
        const name = `new ${friendly}`;
        const body = {
            name,
            description: '',
            data: '',
            type_hint: typeHint,
            provenance: 'user-authored',
            workspace_id: this._conceptWorkspaceId || '',
        };
        let created = null;
        try {
            const resp = await fetch('/api/concepts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (resp && resp.ok) created = await resp.json();
        } catch (_) { /* swallow; user can retry */ }
        if (!created || !created.concept_id) return;
        // Wire RELATES_TO from focal → new. The spec calls for an
        // edge-type-selection dropdown next; defer that to the edge
        // context menu (right-click on the edge) which already exists.
        try {
            await fetch('/api/concept_edges', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source_id: focalId,
                    target_id: created.concept_id,
                    edge_type: 'RELATES_TO',
                    workspace_id: this._conceptWorkspaceId || '',
                }),
            });
        } catch (_) { /* edge can be drawn later via apparition */ }
        // Add to local node map so the editor sees it on the next
        // render tick. The WS broadcast will reconcile to the same
        // record; this is just the optimistic local insertion.
        if (this._conceptNodes && created.concept_id) {
            this._conceptNodes.set(created.concept_id, created);
        }
    },

    _clearApparitionHalo() {
        const hadHalo = !!(this._haloOverlay || this._haloFocalId);
        if (this._haloOverlay && this._haloOverlay.parentNode) {
            this._haloOverlay.parentNode.removeChild(this._haloOverlay);
        }
        this._haloOverlay = null;
        this._haloFocalId = null;
        this._haloCandidates = null;
        this._haloFocalCard = null;
        // The candidate panel is anchored to phantoms inside the
        // overlay; if the halo is gone the panel is orphaned, kill it.
        this._hideCandidateListPanel();
        // §8.2.2 — also clear the halo CHAIN mirror so the autoregression chain
        // resets across peer tabs + REPL when the halo is dismissed.
        if (hadHalo && typeof this._mirrorUi === 'function')
            this._mirrorUi('/api/ui/halo_chain_clear', {});
        // §8.2 / §14.2 — close the backend mirror so peer surfaces see
        // the halo went away. Only fire when there actually was a halo;
        // a no-op clear (e.g., on workspace bootstrap) shouldn't spam.
        if (hadHalo) this._postHaloClearMirror();
    },

    /**
     * §8.2 / §14.2 — POST the apparition halo focus + candidate list
     * to the backend UI state mirror so peer surfaces (REPL viewer,
     * agent perception, peer tabs) see what this user is seeing.
     *
     * Debounced (120 ms) so a rapid sequence of opens / re-targets
     * (typical when the user hovers across the apparition arc) folds
     * into one POST per settle. The backend's setter is idempotent
     * on (focal_card_id, candidates), so coalescing is lossless.
     *
     * Fire-and-forget — the halo render path is what the user sees;
     * the mirror is an observability concern that must never block
     * the UI on a slow network.
     */
    _postHaloFocusMirror(focalId, candidates) {
        if (!focalId || !candidates) return;
        const ws = this._conceptWorkspaceId || '';
        // Strip down to the {card_id, score, pagerank, tfidf_cos,
        // nomic_cos, name?} shape the backend stores. Frontend halo
        // candidates carry extra fields (DOM refs, prefix glyphs);
        // we only mirror the design-stable subset (§8.1 triple
        // product) so peer surfaces aren't tied to render details.
        const slim = candidates.map(c => ({
            card_id:   (c && (c.card_id || c.id)) || '',
            score:     (c && typeof c.score === 'number') ? c.score : 0,
            pagerank:  (c && typeof c.pagerank === 'number') ? c.pagerank : 0,
            tfidf_cos: (c && typeof c.tfidf_cos === 'number') ? c.tfidf_cos : 0,
            nomic_cos: (c && typeof c.nomic_cos === 'number') ? c.nomic_cos : 0,
            name:      (c && (c.name || c.card_id || c.id)) || '',
        }));
        // Debounce so a fast hover-sweep doesn't burst N posts.
        if (this._haloMirrorTimer) clearTimeout(this._haloMirrorTimer);
        this._haloMirrorTimer = setTimeout(() => {
            this._haloMirrorTimer = null;
            try {
                fetch('/api/ui/halo_focus', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        workspace_id:  ws,
                        focal_card_id: focalId,
                        candidates:    slim,
                    }),
                }).catch(() => { /* fire-and-forget */ });
            } catch (_) { /* never block UI on mirror failure */ }
        }, 120);
    },

    _postHaloClearMirror() {
        // Cancel any pending open mirror — clearing wins over a
        // queued open (the halo is gone before the open POSTs).
        if (this._haloMirrorTimer) {
            clearTimeout(this._haloMirrorTimer);
            this._haloMirrorTimer = null;
        }
        const ws = this._conceptWorkspaceId || '';
        try {
            fetch('/api/ui/halo_clear', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ workspace_id: ws }),
            }).catch(() => { /* fire-and-forget */ });
        } catch (_) { /* never block UI */ }
    },

    /**
     * §8B.6 — Floating candidate-list panel for a Potential phantom.
     *
     * Hovering a Potential apparition for ~half a second pops this
     * panel anchored beside the phantom. Where the halo phantoms
     * show top-K candidates radially, this panel surfaces a deeper
     * top-N=20 set with the full triple-product score breakdown
     * (PageRank × TF-IDF × Nomic) per row, ranked by composite
     * score per §8D.43. The panel is the "see all viable targets
     * for this edge type" affordance the spec calls for.
     *
     * Composite score in the apparition response IS the spec's
     * 0.4 semantic + 0.3 structural + 0.15 recency + 0.15 graph
     * proximity blend (it folds through the same triple-product
     * weighting on the backend). The panel surfaces the breakdown
     * so the user can see *why* a candidate ranks where it does.
     */
    async _showCandidateListPanel(phantom, focalId) {
        if (!phantom || !focalId) return;
        // Reuse the same panel — open one at a time. Caller's
        // mouseleave logic decides when to dismiss.
        this._hideCandidateListPanel();
        if (typeof this._fetchApparitionsForFocal !== 'function') return;
        const panel = document.createElement('div');
        panel.className = 'concept-candidate-panel';
        const r = phantom.getBoundingClientRect();
        // Anchor below-right of the phantom; clamp to viewport with
        // 16px margin so it never falls off-screen.
        const vw = window.innerWidth || 1200;
        const vh = window.innerHeight || 800;
        const left = Math.min(vw - 296, Math.max(8, r.right + 8));
        const top  = Math.min(vh - 320, Math.max(8, r.top));
        panel.style.cssText =
            'position:fixed; z-index:10050;' +
            `left:${Math.round(left)}px; top:${Math.round(top)}px;` +
            'width:288px; max-height:300px; overflow:auto;' +
            'background:rgba(0,0,0,0.97); color:#e5e7eb;' +
            'border:1px solid rgba(184,192,200,0.5); border-radius:8px;' +
            'box-shadow:0 8px 24px rgba(0,0,0,0.55);' +
            'font-family:monospace; font-size:11px; padding:6px 0;';
        panel.innerHTML =
            '<div style="padding:4px 10px;color:#9aa3ab;font-size:10px;' +
            'border-bottom:1px solid rgba(255,255,255,0.08);' +
            'display:flex;justify-content:space-between;align-items:center;">' +
            '<span>Candidates for this link</span>' +
            '<span style="color:#555c63;">loading…</span>' +
            '</div>' +
            '<div class="ccp-rows"></div>';
        document.body.appendChild(panel);
        this._candidatePanel = panel;
        let candidates = [];
        try {
            candidates = await this._fetchApparitionsForFocal(focalId, 20);
        } catch (_) {
            candidates = [];
        }
        // Panel may have been dismissed mid-fetch.
        if (!this._candidatePanel || this._candidatePanel !== panel) return;
        const header = panel.firstElementChild;
        if (header && header.lastElementChild) {
            header.lastElementChild.textContent =
                candidates.length ? `${candidates.length} candidates` : 'none found';
        }
        // Pre-compute focal's existing-edge target set to mark
        // already-connected candidates inline.
        const connected = new Set();
        if (this._conceptEdges) {
            for (const e of this._conceptEdges) {
                if (e.source === focalId) connected.add(e.target);
            }
        }
        const rows = panel.querySelector('.ccp-rows');
        candidates.forEach(c => {
            const tid = c.card_id || c.id || '';
            if (!tid) return;
            const isCon = connected.has(tid);
            const score = (typeof c.score === 'number') ? c.score : 0;
            const pr = (c.pagerank  || 0);
            const tf = (c.tfidf_cos || 0);
            const nm = (c.nomic_cos || 0);
            const row = document.createElement('div');
            row.className = 'ccp-row';
            row.dataset.cardId = tid;
            row.style.cssText =
                'padding:5px 10px; cursor:pointer; ' +
                'border-bottom:1px solid rgba(255,255,255,0.04); ' +
                'display:flex; flex-direction:column; gap:2px;';
            row.innerHTML =
                `<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">` +
                `<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;">` +
                `<span style="color:${isCon ? '#b8c0c8' : '#b8c0c8'};margin-right:4px;">` +
                `${isCon ? '→' : '+'}</span>` +
                `${this._conceptEscapeHtml(tid)}</span>` +
                `<span style="color:#9aa3ab;">${(score * 100).toFixed(0)}%</span></div>` +
                `<div style="color:#7c858d;font-size:9px;">` +
                `pr ${pr.toFixed(2)} · tf ${tf.toFixed(2)} · nm ${nm.toFixed(2)}` +
                (isCon ? ' · already connected' : '') + '</div>';
            row.addEventListener('mouseenter', () => {
                row.style.background = 'rgba(184,192,200,0.15)';
            });
            row.addEventListener('mouseleave', () => {
                row.style.background = '';
            });
            row.addEventListener('click', (ev) => {
                ev.stopPropagation();
                if (isCon) return;  // already wired — no-op
                const focalNode = this._conceptNodes.get(focalId);
                const card = focalNode &&
                    document.querySelector(`.concept-card[data-node-id="${focalId}"]`);
                if (card && card.dataset.emptyPrimitive === '1' && focalNode) {
                    this._resolveEmptyPrimitive(card, focalNode, tid);
                } else if (focalNode && card) {
                    this._conceptInsertReference(card, focalNode, tid);
                }
                this._hideCandidateListPanel();
                this._clearApparitionHalo();
            });
            rows.appendChild(row);
        });
        // Panel's own hover-out closes it (with the grace check the
        // phantom's mouseleave handler also uses).
        panel.addEventListener('mouseleave', (ev) => {
            const to = ev.relatedTarget;
            if (to && to.closest && to.closest('.concept-apparition-phantom')) return;
            setTimeout(() => {
                if (this._candidatePanel &&
                    !this._candidatePanel.matches(':hover')) {
                    this._hideCandidateListPanel();
                }
            }, 200);
        });
    },

    _hideCandidateListPanel() {
        if (this._candidatePanel && this._candidatePanel.parentNode) {
            this._candidatePanel.parentNode.removeChild(this._candidatePanel);
        }
        this._candidatePanel = null;
    },

    /**
     * W15 / §8D.8, §8D.28 — Live agent token display.
     *
     * A floating, minimisable panel that shows tokens streamed from
     * the meta-cognition node. Auto-created on first token; multi-
     * agent setups get tabs keyed by parameter_card_id.
     */
    _appendAgentToken(pcid, token) {
        const panel = this._ensureAgentTokenPanel();
        if (!panel) return;
        // Switch tab to the most-recently-active parameter card.
        if (this._agentTokenActivePcid !== pcid) {
            this._agentTokenActivePcid = pcid;
            this._renderAgentTokenTabs(panel);
        }
        const body = panel.querySelector('.wfh-agent-token-body');
        if (!body) return;
        // Append token; auto-scroll to bottom.
        const span = document.createElement('span');
        span.textContent = token;
        body.appendChild(span);
        // Cap rendered token-spans at 4000 to bound DOM growth
        // (matches the JS buffer cap in scanner.js).
        const MAX_NODES = 4000;
        while (body.childNodes.length > MAX_NODES) {
            body.removeChild(body.firstChild);
        }
        body.scrollTop = body.scrollHeight;
    },

    _ensureAgentTokenPanel() {
        if (this._agentTokenPanel && document.body.contains(this._agentTokenPanel)) {
            return this._agentTokenPanel;
        }
        const panel = document.createElement('div');
        panel.id = 'wfh-agent-token-panel';
        panel.style.cssText =
            'position:fixed; bottom:16px; right:16px; width:380px; height:240px;' +
            'background:rgba(0,0,0,0.95); color:#d7dde2;' +
            'border:1px solid rgba(255,255,255,0.1); border-radius:8px;' +
            'box-shadow:0 12px 32px rgba(0,0,0,0.45);' +
            'display:flex; flex-direction:column; z-index:9990;' +
            'font-family:monospace; font-size:11px; overflow:hidden;';
        panel.innerHTML = `
            <div class="wfh-agent-token-header" style="display:flex;align-items:center;justify-content:space-between;padding:6px 8px;background:rgba(99,102,241,0.4);cursor:move;user-select:none;">
                <span style="font-weight:600;">Agent · live tokens</span>
                <span style="display:flex;gap:6px;">
                    <button class="wfh-agent-token-clear" title="Clear" style="background:none;border:none;color:#d7dde2;cursor:pointer;font-size:11px;">⌫</button>
                    <button class="wfh-agent-token-min" title="Minimise" style="background:none;border:none;color:#d7dde2;cursor:pointer;font-size:11px;"><i class="fas fa-window-minimize"></i></button>
                    <button class="wfh-agent-token-close" title="Hide" style="background:none;border:none;color:#d7dde2;cursor:pointer;font-size:11px;">✕</button>
                </span>
            </div>
            <div class="wfh-agent-token-tabs" style="display:flex;gap:2px;padding:2px 6px;background:rgba(0,0,0,0.2);font-size:10px;"></div>
            <div class="wfh-agent-token-body" style="flex:1;padding:8px;overflow:auto;white-space:pre-wrap;line-height:1.4;"></div>
        `;
        document.body.appendChild(panel);
        this._agentTokenPanel = panel;
        // Wire chrome.
        const closeBtn = panel.querySelector('.wfh-agent-token-close');
        const minBtn = panel.querySelector('.wfh-agent-token-min');
        const clearBtn = panel.querySelector('.wfh-agent-token-clear');
        closeBtn.addEventListener('click', () => {
            if (panel.parentNode) panel.parentNode.removeChild(panel);
            this._agentTokenPanel = null;
        });
        minBtn.addEventListener('click', () => {
            const body = panel.querySelector('.wfh-agent-token-body');
            const tabs = panel.querySelector('.wfh-agent-token-tabs');
            const minimised = body.style.display === 'none';
            body.style.display = minimised ? 'block' : 'none';
            tabs.style.display = minimised ? 'flex' : 'none';
            panel.style.height = minimised ? '240px' : 'auto';
        });
        clearBtn.addEventListener('click', () => {
            const body = panel.querySelector('.wfh-agent-token-body');
            if (body) body.innerHTML = '';
            if (this._agentTokenBuffers) this._agentTokenBuffers.clear();
        });
        // Drag handler on header.
        const header = panel.querySelector('.wfh-agent-token-header');
        let dragging = false, dx = 0, dy = 0;
        header.addEventListener('mousedown', (ev) => {
            // Skip drag init if the user clicked a button in the header.
            if (ev.target && (ev.target.tagName === 'BUTTON' || ev.target.closest('button'))) return;
            dragging = true;
            const r = panel.getBoundingClientRect();
            dx = ev.clientX - r.left;
            dy = ev.clientY - r.top;
            ev.preventDefault();
        });
        document.addEventListener('mousemove', (ev) => {
            if (!dragging) return;
            panel.style.left = (ev.clientX - dx) + 'px';
            panel.style.top = (ev.clientY - dy) + 'px';
            panel.style.right = 'auto';
            panel.style.bottom = 'auto';
        });
        document.addEventListener('mouseup', () => { dragging = false; });
        return panel;
    },

    /**
     * W24 / §8C.8 — Render an agent review card (RequestUserReviewAction).
     *
     * Pops a yellow-bordered floating card showing the agent's
     * prompt + the card_ids it's asking the user to inspect.
     * Accept clicks call /api/agent/reviews/resolve with
     * decision=accepted; Dismiss calls with decision=dismissed.
     * Multiple reviews stack vertically.
     */
    _renderAgentReview(entry) {
        if (!entry || !entry.review_id) return;
        let host = document.getElementById('wfh-agent-reviews');
        if (!host) {
            host = document.createElement('div');
            host.id = 'wfh-agent-reviews';
            host.style.cssText =
                'position:fixed; top:80px; right:16px; width:340px;' +
                'display:flex; flex-direction:column; gap:8px; z-index:9994;' +
                'pointer-events:none;';
            document.body.appendChild(host);
        }
        if (host.querySelector(`[data-review-id="${entry.review_id}"]`)) return;
        const card = document.createElement('div');
        card.dataset.reviewId = entry.review_id;
        card.style.cssText =
            'background:rgba(254,243,199,0.96); color:#7c2d12;' +
            'border-left:4px solid #9aa3ab; border-radius:6px;' +
            'box-shadow:0 8px 24px rgba(0,0,0,0.35);' +
            'padding:8px 10px; font-family:monospace; font-size:11px;' +
            'pointer-events:auto;';
        const cardIdsHtml = (entry.card_ids || []).map(id =>
            `<span style="display:inline-block;background:rgba(124,45,18,0.15);padding:1px 4px;border-radius:3px;margin:1px 2px;">${this._conceptEscapeHtml(String(id))}</span>`
        ).join('');
        card.innerHTML = `
            <div style="font-weight:600;margin-bottom:4px;">
                <i class="fas fa-flag"></i> Agent requests review
                <span style="float:right;font-size:9px;opacity:0.7;">${this._conceptEscapeHtml(entry.actor || '')}</span>
            </div>
            <div style="margin-bottom:6px;line-height:1.4;">${this._conceptEscapeHtml(entry.prompt || '')}</div>
            ${cardIdsHtml ? `<div style="margin-bottom:6px;">cards: ${cardIdsHtml}</div>` : ''}
            <div style="display:flex;gap:6px;justify-content:flex-end;">
                <button class="agent-review-accept" style="background:#16a34a;color:white;border:none;border-radius:4px;padding:3px 8px;cursor:pointer;font-size:10px;">Accept</button>
                <button class="agent-review-dismiss" style="background:#6b7280;color:white;border:none;border-radius:4px;padding:3px 8px;cursor:pointer;font-size:10px;">Dismiss</button>
            </div>
        `;
        host.appendChild(card);
        const resolve = async (decision) => {
            try {
                await fetch('/api/agent/reviews/resolve', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ review_id: entry.review_id, decision }),
                });
            } catch (_) { /* ignore */ }
            card.style.transition = 'opacity 200ms';
            card.style.opacity = '0';
            setTimeout(() => { if (card.parentNode) card.parentNode.removeChild(card); }, 220);
        };
        card.querySelector('.agent-review-accept').addEventListener('click', () => resolve('accepted'));
        card.querySelector('.agent-review-dismiss').addEventListener('click', () => resolve('dismissed'));
    },

    /**
     * W16 / §8D.33.5 — Evolution log UI panel.
     *
     * Floating, dismissable history panel listing recent diffs with
     * actor / target / kind / time. Right-click a diff to revert it
     * (calls /api/evolution_log/rollback). Hit "Refresh" to re-poll.
     * Bound to a keyboard shortcut (Ctrl/Cmd+H) for quick access.
     */
    showEvolutionLogPanel() {
        let panel = document.getElementById('wfh-evolution-log-panel');
        if (panel) { panel.style.display = 'flex'; this._refreshEvolutionLog(panel); return; }
        panel = document.createElement('div');
        panel.id = 'wfh-evolution-log-panel';
        panel.style.cssText =
            'position:fixed; left:20px; bottom:20px; width:420px; height:360px;' +
            'background:rgba(0,0,0,0.97); color:#e5e7eb;' +
            'border:1px solid rgba(255,255,255,0.1); border-radius:8px;' +
            'box-shadow:0 12px 32px rgba(0,0,0,0.45);' +
            'display:flex; flex-direction:column; z-index:9991;' +
            'font-family:monospace; font-size:11px; overflow:hidden;';
        panel.innerHTML = `
            <div class="wfh-evlog-header" style="display:flex;align-items:center;justify-content:space-between;padding:6px 8px;background:rgba(245,158,11,0.4);cursor:move;user-select:none;">
                <span style="font-weight:600;">Evolution log · history</span>
                <span style="display:flex;gap:6px;">
                    <button class="wfh-evlog-refresh" title="Refresh" style="background:none;border:none;color:#e5e7eb;cursor:pointer;font-size:11px;">↻</button>
                    <button class="wfh-evlog-close" title="Close" style="background:none;border:none;color:#e5e7eb;cursor:pointer;font-size:11px;">✕</button>
                </span>
            </div>
            <div class="wfh-evlog-body" style="flex:1;padding:0;overflow:auto;"></div>
            <div class="wfh-evlog-footer" style="padding:4px 8px;border-top:1px solid rgba(255,255,255,0.05);font-size:10px;color:#9aa3ab;">
                Right-click a row to revert that edit.
            </div>
        `;
        document.body.appendChild(panel);
        panel.querySelector('.wfh-evlog-close').addEventListener('click', () => {
            panel.style.display = 'none';
        });
        panel.querySelector('.wfh-evlog-refresh').addEventListener('click', () => {
            this._refreshEvolutionLog(panel);
        });
        // Drag.
        const header = panel.querySelector('.wfh-evlog-header');
        let dragging = false, dx = 0, dy = 0;
        header.addEventListener('mousedown', (ev) => {
            if (ev.target && (ev.target.tagName === 'BUTTON' || ev.target.closest('button'))) return;
            dragging = true;
            const r = panel.getBoundingClientRect();
            dx = ev.clientX - r.left; dy = ev.clientY - r.top;
            ev.preventDefault();
        });
        document.addEventListener('mousemove', (ev) => {
            if (!dragging) return;
            panel.style.left = (ev.clientX - dx) + 'px';
            panel.style.top  = (ev.clientY - dy) + 'px';
            panel.style.right = 'auto'; panel.style.bottom = 'auto';
        });
        document.addEventListener('mouseup', () => { dragging = false; });
        this._refreshEvolutionLog(panel);
    },

    /**
     * W38 — Multi-agent visibility panel.
     *
     * Lists every concept node with type_hint='agent_parameter'
     * (or a data block containing a "goal" field) as an active
     * agent. Each row shows the goal, current step_index, and
     * has tick / pause / fork buttons. Bound to Ctrl/Cmd+G.
     */
    showAgentVisibilityPanel() {
        let panel = document.getElementById('wfh-agents-panel');
        if (panel) {
            panel.style.display = 'flex';
            this._refreshAgentVisibilityPanel(panel);
            return;
        }
        panel = document.createElement('div');
        panel.id = 'wfh-agents-panel';
        panel.style.cssText =
            'position:fixed; right:16px; top:80px; width:360px; max-height:60vh;' +
            'background:rgba(0,0,0,0.97); color:#e5e7eb;' +
            'border:1px solid rgba(255,255,255,0.1); border-radius:8px;' +
            'box-shadow:0 12px 32px rgba(0,0,0,0.45);' +
            'display:flex; flex-direction:column; z-index:9992;' +
            'font-family:monospace; font-size:11px; overflow:hidden;';
        panel.innerHTML = `
            <div class="wfh-agents-header" style="display:flex;align-items:center;justify-content:space-between;padding:6px 8px;background:rgba(34,197,94,0.35);cursor:move;user-select:none;">
                <span style="font-weight:600;"><i class="fas fa-robot"></i> Active agents</span>
                <span style="display:flex;gap:6px;">
                    <button class="wfh-agents-spawn" title="Spawn agent with visible body subgraph (§8D.27)" style="background:rgba(34,197,94,0.4);border:1px solid rgba(34,197,94,0.6);color:#e5e7eb;cursor:pointer;font-size:10px;padding:2px 6px;border-radius:4px;">+ Spawn</button>
                    <button class="wfh-agents-refresh" title="Refresh" style="background:none;border:none;color:#e5e7eb;cursor:pointer;font-size:11px;">↻</button>
                    <button class="wfh-agents-close" title="Close" style="background:none;border:none;color:#e5e7eb;cursor:pointer;font-size:11px;">✕</button>
                </span>
            </div>
            <div class="wfh-agents-body" style="flex:1;padding:0;overflow:auto;"></div>
            <div class="wfh-agents-footer" style="padding:4px 8px;border-top:1px solid rgba(255,255,255,0.05);font-size:10px;color:#9aa3ab;display:flex;justify-content:space-between;align-items:center;">
                <span>Each entry = parameter card driving a perception → transformer → emitter subgraph.</span>
                <span class="wfh-agents-health" title="WebSocket queue drops since process start; non-zero = slow consumer or backpressure event"
                      style="color:#9aa3ab;font-family:monospace;font-size:9px;">…</span>
            </div>
        `;
        document.body.appendChild(panel);
        panel.querySelector('.wfh-agents-close').addEventListener('click', () => {
            panel.style.display = 'none';
        });
        panel.querySelector('.wfh-agents-refresh').addEventListener('click', () => {
            this._refreshAgentVisibilityPanel(panel);
        });
        // §8D.27 — spawn a parameter card + visible body subgraph in
        // one shot. The four resulting cards (param, perception,
        // transformer, emitter) land on canvas with backing pointers
        // wired; the user can pin / edit / fork any of them.
        panel.querySelector('.wfh-agents-spawn').addEventListener('click', async () => {
            const goal = prompt(
                'Initial goal for the agent\n(stored in the parameter card; you can edit it later):',
                'Inspect the graph and suggest one useful next concept.',
            );
            if (goal == null) return;
            try {
                const resp = await fetch('/api/agent/spawn', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        workspace_id: this._conceptWorkspaceId || '',
                        goal: String(goal),
                        idempotency_key: this._newIdempotencyKey(),
                    }),
                });
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                // The four created cards arrive as ``concept_changed``
                // WS frames; the agents panel auto-refresh picks them
                // up on the next render. Also kick a hydrate so any
                // races are covered.
                if (typeof this._hydrateConceptsFromBackend === 'function') {
                    await this._hydrateConceptsFromBackend();
                }
                this._refreshAgentVisibilityPanel(panel);
            } catch (e) {
                alert('Agent spawn failed: ' + (e && e.message));
            }
        });
        // Drag.
        const header = panel.querySelector('.wfh-agents-header');
        let dragging = false, dx = 0, dy = 0;
        header.addEventListener('mousedown', (ev) => {
            if (ev.target && (ev.target.tagName === 'BUTTON' || ev.target.closest('button'))) return;
            dragging = true;
            const r = panel.getBoundingClientRect();
            dx = ev.clientX - r.left; dy = ev.clientY - r.top;
            ev.preventDefault();
        });
        document.addEventListener('mousemove', (ev) => {
            if (!dragging) return;
            panel.style.left = (ev.clientX - dx) + 'px';
            panel.style.top  = (ev.clientY - dy) + 'px';
            panel.style.right = 'auto';
        });
        document.addEventListener('mouseup', () => { dragging = false; });
        this._refreshAgentVisibilityPanel(panel);
    },

    async _refreshAgentVisibilityPanel(panel) {
        const body = panel.querySelector('.wfh-agents-body');
        if (!body) return;
        body.innerHTML = '<div style="padding:8px;color:#9aa3ab;">scanning…</div>';
        // Backpressure badge — poll /api/health for WS drop counts so
        // the user can see slow-consumer pressure inside the agents
        // panel without scraping logs. Non-zero drops tint the badge
        // amber; >100 drops tint it red so an at-a-glance scan picks
        // up trouble fast.
        const healthBadge = panel.querySelector('.wfh-agents-health');
        if (healthBadge) {
            fetch('/api/health')
                .then(r => r.ok ? r.json() : null)
                .then(data => {
                    if (!data || !data.ws_drops) {
                        healthBadge.textContent = '—';
                        return;
                    }
                    const drops = Object.values(data.ws_drops).reduce((a, b) => a + b, 0);
                    const queueDepths = [
                        ...Object.values((data.ws_queue_sizes || {}).snapshot || {}),
                        ...Object.values((data.ws_queue_sizes || {}).workspace || {}),
                    ];
                    const maxDepth = queueDepths.length ? Math.max(...queueDepths) : 0;
                    healthBadge.textContent = `drops ${drops} · max-depth ${maxDepth}`;
                    if (drops > 100) {
                        healthBadge.style.color = '#b25b5b';
                    } else if (drops > 0) {
                        healthBadge.style.color = '#eef0f2';
                    } else {
                        healthBadge.style.color = '#9aa3ab';
                    }
                })
                .catch(() => { healthBadge.textContent = 'health ?'; });
        }
        // Find parameter cards in the local concept Map.
        const agents = [];
        if (this._conceptNodes) {
            for (const node of this._conceptNodes.values()) {
                const hint = (node.type_hint || '').toLowerCase();
                if (hint === 'agent_parameter' || hint === 'parameter_card' || hint === 'agent_state') {
                    agents.push(node);
                    continue;
                }
                // Fallback: parse data block for a goal field.
                try {
                    const data = JSON.parse(node.value || '{}');
                    if (data && typeof data.goal === 'string') agents.push(node);
                } catch (_) {}
            }
        }
        if (!agents.length) {
            body.innerHTML = '<div style="padding:8px;color:#9aa3ab;">No active parameter cards. Spawn an empty primitive, type a description starting with "goal:", and tick the agent via /api/agent/tick.</div>';
            return;
        }
        body.innerHTML = '';
        // §8D.38.1 — fetch cascade diagnostics in parallel so each row
        // can show fire count + last-fire age. The poll is cheap (a
        // dict snapshot) and lets the user verify AUTO is actually
        // advancing the agent rather than just claiming to be.
        let cascadeStatus = {};
        try {
            const resp = await fetch('/api/agent/cascade_status');
            if (resp.ok) {
                const data = await resp.json();
                cascadeStatus = (data && data.agents) || {};
            }
        } catch (_) { /* diagnostics are best-effort */ }
        agents.forEach(node => {
            let meta = {};
            try { meta = JSON.parse(node.value || '{}'); } catch (_) {}
            const row = document.createElement('div');
            row.style.cssText =
                'padding:6px 8px;border-bottom:1px solid rgba(255,255,255,0.04);';
            const goal = meta.goal || '(no goal set)';
            const step = meta.step_index != null ? `step ${meta.step_index}` : '';
            const zoiSize = meta.zone_of_influence ? Object.keys(meta.zone_of_influence).length : 0;
            const cascadeOn = !!meta.cascade_enabled;
            const paused = !!meta.paused;
            const diag = cascadeStatus[node.id] || {};
            // §8D.38.1 — auto / pause status badge.
            let statusBadge = '';
            if (paused) {
                statusBadge = `<span style="color:#b25b5b;font-size:9px;background:rgba(178,91,91,0.15);padding:1px 5px;border-radius:3px;margin-right:6px;">PAUSED</span>`;
            } else if (cascadeOn) {
                statusBadge = `<span style="color:#b8c0c8;font-size:9px;background:rgba(184,192,200,0.15);padding:1px 5px;border-radius:3px;margin-right:6px;">AUTO</span>`;
            } else {
                statusBadge = `<span style="color:#9aa3ab;font-size:9px;background:rgba(184,192,200,0.15);padding:1px 5px;border-radius:3px;margin-right:6px;">MANUAL</span>`;
            }
            // Diagnostics row — fires, last fire age, last-skip reason.
            const totalFires = diag.total_fires || 0;
            const firesPerMin = diag.fires_last_minute || 0;
            const ageSec = diag.last_fire_age_sec;
            const armed = !!diag.armed;
            const skip = diag.last_skip_reason || '';
            const ageStr = ageSec == null
                ? 'never'
                : (ageSec < 60 ? `${ageSec.toFixed(0)}s ago` :
                   ageSec < 3600 ? `${(ageSec/60).toFixed(0)}m ago` :
                   `${(ageSec/3600).toFixed(0)}h ago`);
            const armedDot = armed ? '<span title="debounce timer armed" style="color:#eef0f2;">●</span> ' : '';
            const totalSpawns = diag.total_spawns || 0;
            const spawnsRateLim = diag.total_spawns_rate_limited || 0;
            const spawnLine = (totalSpawns || spawnsRateLim)
                ? ` · spawns: ${totalSpawns}${spawnsRateLim ? ` (${spawnsRateLim} capped)` : ''}`
                : '';
            const diagBlock = `
                <div style="color:#7c858d;font-size:9px;margin-bottom:4px;">
                    ${armedDot}fires: ${totalFires} · ${firesPerMin}/min · last ${ageStr}${spawnLine}${skip ? ` · skipped: <span style="color:#b25b5b;">${this._conceptEscapeHtml(skip)}</span>` : ''}
                </div>`;
            row.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">
                    <span>${statusBadge}<span style="color:#86efac;font-weight:600;">${this._conceptEscapeHtml(node.id)}</span></span>
                    <span style="color:#9aa3ab;font-size:9px;">${step}${zoiSize ? ` · zoi ${zoiSize}` : ''}</span>
                </div>
                <div style="color:#d7dde2;margin-bottom:4px;line-height:1.4;">${this._conceptEscapeHtml(String(goal).slice(0, 120))}</div>
                ${diagBlock}
                <div style="display:flex;gap:6px;justify-content:flex-end;flex-wrap:wrap;">
                    <button class="agent-tick" data-id="${node.id}" style="background:#16a34a;color:white;border:none;border-radius:4px;padding:3px 8px;cursor:pointer;font-size:10px;">Tick</button>
                    <button class="agent-auto" data-id="${node.id}" data-state="${cascadeOn ? 'on' : 'off'}" title="Toggle cascade auto-fire on every input change (§8D.38.1)" style="background:${cascadeOn ? '#0891b2' : 'rgba(8,145,178,0.2)'};color:${cascadeOn ? 'white' : '#67e8f9'};border:1px solid rgba(8,145,178,0.5);border-radius:4px;padding:3px 8px;cursor:pointer;font-size:10px;">${cascadeOn ? 'Auto on' : 'Auto off'}</button>
                    <button class="agent-pause" data-id="${node.id}" data-state="${paused ? 'paused' : 'running'}" title="Pause / resume — gates the cascade scheduler entirely" style="background:${paused ? '#dc2626' : 'rgba(220,38,38,0.2)'};color:${paused ? 'white' : '#fca5a5'};border:1px solid rgba(220,38,38,0.5);border-radius:4px;padding:3px 8px;cursor:pointer;font-size:10px;">${paused ? 'Resume' : 'Pause'}</button>
                    <button class="agent-focus" data-id="${node.id}" style="background:#b8c0c8;color:white;border:none;border-radius:4px;padding:3px 8px;cursor:pointer;font-size:10px;">Focus</button>
                    <button class="agent-fork" data-id="${node.id}" style="background:#9aa3ab;color:white;border:none;border-radius:4px;padding:3px 8px;cursor:pointer;font-size:10px;">Fork</button>
                </div>
            `;
            body.appendChild(row);
        });
        // Helper for flag toggles. Re-fetches the latest data block
        // (the panel's local copy might be stale by the time the user
        // clicks), flips the flag, and PATCHes back.
        const togglePcidFlag = async (pcid, flag, value) => {
            try {
                const resp = await fetch(`/api/concepts/${encodeURIComponent(pcid)}`);
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                const c = await resp.json();
                let data = {};
                try { data = JSON.parse(c.data || '{}'); } catch (_) {}
                data[flag] = value;
                await fetch(`/api/concepts/${encodeURIComponent(pcid)}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        concept_id: pcid,
                        data: JSON.stringify(data, null, 2),
                        workspace_id: this._conceptWorkspaceId || '',
                    }),
                });
            } catch (e) {
                console.warn('[agent panel] flag toggle failed:', e && e.message);
            }
        };
        body.querySelectorAll('.agent-auto').forEach(btn => {
            btn.addEventListener('click', async () => {
                const pid = btn.dataset.id;
                const on = btn.dataset.state === 'on';
                await togglePcidFlag(pid, 'cascade_enabled', !on);
                this._refreshAgentVisibilityPanel(panel);
            });
        });
        body.querySelectorAll('.agent-pause').forEach(btn => {
            btn.addEventListener('click', async () => {
                const pid = btn.dataset.id;
                const paused = btn.dataset.state === 'paused';
                await togglePcidFlag(pid, 'paused', !paused);
                this._refreshAgentVisibilityPanel(panel);
            });
        });
        // Wire row buttons.
        body.querySelectorAll('.agent-tick').forEach(btn => {
            btn.addEventListener('click', async () => {
                const pid = btn.dataset.id;
                try {
                    await fetch('/api/agent/tick', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ parameter_card_id: pid, workspace_id: this._conceptWorkspaceId || '' }),
                    });
                } catch (_) {}
                this._refreshAgentVisibilityPanel(panel);
            });
        });
        body.querySelectorAll('.agent-focus').forEach(btn => {
            btn.addEventListener('click', () => {
                const pid = btn.dataset.id;
                const card = document.querySelector(`.concept-card[data-node-id="${pid}"]`);
                if (card) {
                    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    card.style.outline = '3px solid #eef0f2';
                    setTimeout(() => { card.style.outline = ''; }, 1200);
                }
            });
        });
        body.querySelectorAll('.agent-fork').forEach(btn => {
            btn.addEventListener('click', async () => {
                const pid = btn.dataset.id;
                // §8D.32.3 — server-side fork. The backend clones the
                // parameter card + the perception / transformer /
                // emitter body so the user-customised configuration
                // (prompt template, emitter filter, perception toggles)
                // carries over. Local-only addConceptNode was the
                // pre-§8D.27 path and only duplicated the parameter
                // card without its body subgraph.
                const newName = prompt(
                    'Name for the forked agent (blank = "<source>_fork"):',
                    pid + '_fork',
                );
                if (newName == null) return;  // user cancelled
                try {
                    const resp = await fetch('/api/agent/fork', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            source_parameter_card_id: pid,
                            workspace_id: this._conceptWorkspaceId || '',
                            new_name: String(newName || '').trim(),
                            idempotency_key: this._newIdempotencyKey(),
                        }),
                    });
                    if (!resp.ok) throw new Error('HTTP ' + resp.status);
                    // The new cards arrive via concept_changed WS
                    // frames; hydrate to be sure we don't miss any
                    // that landed before the WS subscription completed.
                    if (typeof this._hydrateConceptsFromBackend === 'function') {
                        await this._hydrateConceptsFromBackend();
                    }
                } catch (e) {
                    alert('Agent fork failed: ' + (e && e.message));
                }
                this._refreshAgentVisibilityPanel(panel);
            });
        });
    },

    async _refreshEvolutionLog(panel) {
        const body = panel.querySelector('.wfh-evlog-body');
        if (!body) return;
        body.innerHTML = '<div style="padding:8px;color:#9aa3ab;">loading…</div>';
        const ws = this._conceptWorkspaceId || '';
        const params = new URLSearchParams({ limit: '100' });
        if (ws) params.set('workspace_id', ws);
        try {
            const resp = await fetch('/api/evolution_log?' + params.toString());
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            const data = await resp.json();
            const diffs = Array.isArray(data && data.diffs) ? data.diffs : [];
            if (!diffs.length) {
                body.innerHTML = '<div style="padding:8px;color:#9aa3ab;">No diffs yet.</div>';
                return;
            }
            body.innerHTML = '';
            diffs.forEach(d => {
                const row = document.createElement('div');
                row.className = 'wfh-evlog-row';
                row.style.cssText =
                    'padding:6px 8px; border-bottom:1px solid rgba(255,255,255,0.04);' +
                    'cursor:context-menu;';
                const kindColor = {
                    create: '#b8c0c8', modify: '#eef0f2', delete: '#b25b5b',
                    rollback: '#b8c0c8', link: '#b8c0c8', unlink: '#9aa3ab',
                }[d.kind] || '#e5e7eb';
                const tm = new Date((d.timestamp || 0) * 1000).toLocaleTimeString();
                row.innerHTML =
                    `<span style="color:${kindColor};font-weight:600;">${this._conceptEscapeHtml(d.kind)}</span> ` +
                    `<span style="color:#9aa3ab;">#${d.edit_id}</span> ` +
                    `<span style="color:#d7dde2;">${this._conceptEscapeHtml((d.target || '').slice(0, 40))}</span> ` +
                    `<span style="color:#7c858d;font-size:9px;">${this._conceptEscapeHtml(d.actor || '')} · ${tm}</span>`;
                row.addEventListener('contextmenu', async (ev) => {
                    ev.preventDefault();
                    if (!confirm(`Revert edit #${d.edit_id} (${d.kind} on ${d.target})?`)) return;
                    try {
                        const resp = await fetch('/api/evolution_log/rollback', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ edit_id: d.edit_id, workspace_id: ws }),
                        });
                        if (!resp.ok) throw new Error('HTTP ' + resp.status);
                        // Re-hydrate concepts after rollback.
                        await this._hydrateConceptsFromBackend();
                        this._refreshEvolutionLog(panel);
                    } catch (e) {
                        alert('Rollback failed: ' + (e && e.message));
                    }
                });
                body.appendChild(row);
            });
        } catch (e) {
            body.innerHTML = '<div style="padding:8px;color:#b25b5b;">load failed: ' +
                              this._conceptEscapeHtml(String(e && e.message || e)) + '</div>';
        }
    },

    /**
     * Append a single diff row to the live evolution-log panel if it
     * is open. Mirrors the row shape produced by ``_refreshEvolutionLog``
     * so the live feed is visually consistent with the polled load.
     * If the panel is closed, the diff is dropped on the floor — the
     * next time the user opens it, the REST poll picks it up.
     */
    _appendEvolutionLogDiff(diff) {
        if (!diff || !diff.edit_id) return;
        const panel = document.getElementById('wfh-evolution-log-panel');
        if (!panel || panel.style.display === 'none') return;
        const body = panel.querySelector('.wfh-evlog-body');
        if (!body) return;
        // Filter by workspace if the panel was opened against one.
        const ws = this._conceptWorkspaceId || '';
        if (ws && diff.workspace_id && diff.workspace_id !== ws) return;
        // Dedupe — if a refresh just landed and we already have this
        // edit_id, skip.
        if (body.querySelector(`[data-edit-id="${diff.edit_id}"]`)) return;
        // If the placeholder "No diffs yet." is showing, clear it.
        const placeholder = body.firstElementChild;
        if (placeholder && placeholder.textContent && placeholder.textContent.includes('No diffs yet')) {
            body.innerHTML = '';
        }
        const row = document.createElement('div');
        row.className = 'wfh-evlog-row';
        row.dataset.editId = String(diff.edit_id);
        row.style.cssText =
            'padding:6px 8px; border-bottom:1px solid rgba(255,255,255,0.04);' +
            'cursor:context-menu; background:rgba(34,197,94,0.06);';
        const kindColor = {
            create: '#b8c0c8', modify: '#eef0f2', delete: '#b25b5b',
            rollback: '#b8c0c8', link: '#b8c0c8', unlink: '#9aa3ab',
        }[diff.kind] || '#e5e7eb';
        const tm = new Date((diff.timestamp || 0) * 1000).toLocaleTimeString();
        row.innerHTML =
            `<span style="color:${kindColor};font-weight:600;">${this._conceptEscapeHtml(diff.kind)}</span> ` +
            `<span style="color:#9aa3ab;">#${diff.edit_id}</span> ` +
            `<span style="color:#d7dde2;">${this._conceptEscapeHtml((diff.target || '').slice(0, 40))}</span> ` +
            `<span style="color:#7c858d;font-size:9px;">${this._conceptEscapeHtml(diff.actor || '')} · ${tm}</span>`;
        row.addEventListener('contextmenu', async (ev) => {
            ev.preventDefault();
            if (!confirm(`Revert edit #${diff.edit_id} (${diff.kind} on ${diff.target})?`)) return;
            try {
                const resp = await fetch('/api/evolution_log/rollback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ edit_id: diff.edit_id, workspace_id: ws }),
                });
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                await this._hydrateConceptsFromBackend();
                this._refreshEvolutionLog(panel);
            } catch (e) {
                alert('Rollback failed: ' + (e && e.message));
            }
        });
        // Newest at top (matches the polled order in _refreshEvolutionLog).
        body.insertBefore(row, body.firstChild);
        // Fade the "just-arrived" tint after ~1s so it doesn't pile up.
        setTimeout(() => {
            row.style.background = '';
            row.style.transition = 'background 600ms';
        }, 1000);
    },

    _renderAgentTokenTabs(panel) {
        const tabs = panel.querySelector('.wfh-agent-token-tabs');
        if (!tabs) return;
        tabs.innerHTML = '';
        const buffers = this._agentTokenBuffers || new Map();
        const ids = Array.from(buffers.keys());
        if (ids.length <= 1) {
            tabs.style.display = 'none';
            return;
        }
        tabs.style.display = 'flex';
        const active = this._agentTokenActivePcid;
        ids.forEach(id => {
            const tab = document.createElement('button');
            tab.textContent = id.length > 20 ? id.slice(0, 17) + '...' : id;
            tab.style.cssText =
                'background:none;border:none;cursor:pointer;padding:2px 6px;' +
                'border-radius:3px;font-size:10px;color:' +
                (id === active ? '#eef0f2' : '#9aa3ab') + ';' +
                (id === active ? 'background:rgba(184,192,200,0.1);' : '');
            tab.addEventListener('click', () => {
                this._agentTokenActivePcid = id;
                const body = panel.querySelector('.wfh-agent-token-body');
                const buf = this._agentTokenBuffers.get(id) || [];
                body.textContent = buf.join('');
                this._renderAgentTokenTabs(panel);
            });
            tabs.appendChild(tab);
        });
    },

    /**
     * Draw / update the SOLID SVG link from each pinned concept card
     * that carries a `data-3d-node-id` attribute to its corresponding
     * 3D sphere's projected screen position. Called every frame from
     * the animate loop so the line tracks the sphere as the scene
     * rotates.
     *
     * The lines live inside `#concept-edges` (the same SVG that draws
     * concept↔concept edges) but in their own `<g id="concept-3d-links">`
     * group so they paint above the concept-edges but below the cards
     * themselves. Uses solid stroke + an arrow marker pointing at the
     * 3D node end, matching the user's "hard-filled-in 2D lines" spec.
     */
    _drawConcept3DLinks() {
        const svg = document.getElementById('concept-edges');
        if (!svg) return;
        const SVG_NS = 'http://www.w3.org/2000/svg';
        let group = svg.querySelector('#concept-3d-links');
        if (!group) {
            group = document.createElementNS(SVG_NS, 'g');
            group.setAttribute('id', 'concept-3d-links');
            svg.appendChild(group);
            // One solid arrowhead marker for every 3D link.
            const defs = document.createElementNS(SVG_NS, 'defs');
            const marker = document.createElementNS(SVG_NS, 'marker');
            marker.setAttribute('id', 'concept-3d-arrow');
            marker.setAttribute('viewBox', '0 0 10 10');
            marker.setAttribute('refX', '9');
            marker.setAttribute('refY', '5');
            marker.setAttribute('markerWidth', '7');
            marker.setAttribute('markerHeight', '7');
            marker.setAttribute('orient', 'auto');
            const tri = document.createElementNS(SVG_NS, 'path');
            tri.setAttribute('d', 'M 0 0 L 10 5 L 0 10 z');
            tri.setAttribute('fill', '#eef0f2');
            marker.appendChild(tri);
            defs.appendChild(marker);
            group.appendChild(defs);
        }

        // Find every pinned concept card that's bound to a 3D node.
        const cards = document.querySelectorAll('.concept-card[data-3d-node-id]');
        if (!cards.length) {
            // Nothing to draw — wipe the group's old lines (keep defs).
            const stale = group.querySelectorAll('line');
            stale.forEach(el => el.parentNode.removeChild(el));
            return;
        }

        // Re-pool <line> children: reuse existing ones, append new.
        const lines = Array.from(group.querySelectorAll('line'));
        let lineIdx = 0;

        cards.forEach(card => {
            const nodeId = card.dataset['3dNodeId'] || card.getAttribute('data-3d-node-id');
            if (!nodeId) return;
            // 3D position → world → screen. _getNodePosition reads
            // the instance matrix (post-rotation) so the line tracks
            // the sphere as the snow-globe rotation animates.
            if (typeof this._getNodePosition !== 'function') return;
            const worldPos = this._getNodePosition(nodeId);
            if (!worldPos) return;
            const projected = worldPos.clone().project(this.camera);
            // NDC → CSS pixels. The canvas fills #projector-panel; we
            // project against the canvas rect so the line lands on the
            // sphere even when the side panels are open.
            const canvas = this.renderer && this.renderer.domElement;
            if (!canvas) return;
            const rect = canvas.getBoundingClientRect();
            // Behind-camera reject — `z` outside [-1, 1] in NDC means
            // the point is behind the near/far plane.
            if (projected.z < -1 || projected.z > 1) {
                // Hide any existing line for this card.
                const existing = card.__concept3dLine;
                if (existing) existing.setAttribute('visibility', 'hidden');
                return;
            }
            const x2 = rect.left + (projected.x *  0.5 + 0.5) * rect.width;
            const y2 = rect.top  + (-projected.y * 0.5 + 0.5) * rect.height;

            // 2D end: nearest edge midpoint of the card facing the
            // 3D node. Cheap heuristic — pick whichever of left/right/
            // top/bottom edge midpoint is closer to (x2, y2).
            const cr = card.getBoundingClientRect();
            const cx = cr.left + cr.width  / 2;
            const cy = cr.top  + cr.height / 2;
            // Anchor point on the card border in the direction of the
            // 3D node (clipped against the card rect).
            const dx = x2 - cx, dy = y2 - cy;
            let x1, y1;
            if (Math.abs(dx) * cr.height >= Math.abs(dy) * cr.width) {
                // Exits left/right.
                x1 = dx >= 0 ? cr.right : cr.left;
                const t = (x1 - cx) / dx;
                y1 = cy + dy * t;
            } else {
                // Exits top/bottom.
                y1 = dy >= 0 ? cr.bottom : cr.top;
                const t = (y1 - cy) / dy;
                x1 = cx + dx * t;
            }

            // Reuse pooled <line> or create a fresh one.
            let line = lines[lineIdx++];
            if (!line) {
                line = document.createElementNS(SVG_NS, 'line');
                line.setAttribute('stroke', '#eef0f2');
                line.setAttribute('stroke-width', '2');
                line.setAttribute('stroke-opacity', '0.85');
                // Solid — no dasharray.
                line.removeAttribute('marker-end');  // headless connector (no arrowheads)
                group.appendChild(line);
            }
            line.setAttribute('visibility', 'visible');
            line.setAttribute('x1', x1);
            line.setAttribute('y1', y1);
            line.setAttribute('x2', x2);
            line.setAttribute('y2', y2);
            card.__concept3dLine = line;
        });

        // Trim any leftover <line>s from previous frames.
        for (let k = lineIdx; k < lines.length; k++) {
            const el = lines[k];
            el.setAttribute('visibility', 'hidden');
        }
    },

    _conceptInsertReference(card, node, targetId) {
        const valueInput = card.querySelector('.concept-value-input');
        if (!valueInput) return;
        const ref = `{${targetId}}`;
        const cur = valueInput.value || '';
        const next = cur.length === 0 ? ref
                   : (cur.endsWith(' ') || cur.endsWith('\n')) ? (cur + ref)
                   : (cur + ' ' + ref);
        valueInput.value = next;
        node.value = next;
        this._parseConceptReferences(node);
        this._drawConceptEdges();
    },
};
