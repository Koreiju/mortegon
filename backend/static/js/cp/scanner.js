/**
 * cp/scanner.js — Live-browser snapshot trigger, auto-connect to externally-
 * started scans, WebSocket-first streaming with polling fallback, and the
 * "Recompute UMAP" no-op button.
 *
 * ## Chunk-ID / Instance-ID streaming protocol
 *
 *   chunk_added / chunks_partial  →  cache metadata in _pendingChunks (no sphere)
 *   chunk_instances_partial       →  create sphere with instance_id; pull cached
 *                                    metadata from _pendingChunks so billboard is
 *                                    ready instantly
 *   chunk_replaced                →  remove old instances, cache new metadata
 *   chunk_removed                 →  look up instance_ids via _chunkIdToInstances
 *                                    and remove each sphere
 *   instances_indexed             →  DB is ready; lazy-fetch rich details for
 *                                    nodes that still lack html_raw
 *
 * ## Backend-delegation mode (scan.py + running app.py)
 *
 *   When scripts/scan.py is run while the backend server is up it delegates
 *   the scan via GET /api/snapshot.  The frontend auto-detects the in-progress
 *   scan via GET /api/scan_status and attaches to the same WebSocket stream,
 *   so live spheres appear without the user clicking Scan.
 *
 * Methods become ChunkProjector instance methods via prototype mixin.
 */

export const ScannerMixin = {

    // ── initSnapshot ──────────────────────────────────────────────────────────

    initSnapshot() {
        const btn = document.getElementById('snapshot-btn');
        if (!btn) return;
        btn.addEventListener('click', () => this.triggerScan());
        // NOTE: the legacy dynamic "Recompute UMAP" button that this
        // method used to inject right after the snapshot button is
        // gone. The static `#umap-recompute-btn` in index.html (wired
        // by cp/concept_graph.js initConceptGraph) is the single
        // canonical UMAP entry point now — keeping both produced two
        // visually-different buttons doing the same thing, which the
        // user spotted.
    },

    setScanStatus(text, color) {
        const el = document.getElementById('scan-status');
        if (!el) return;
        if (!text) { el.style.display = 'none'; el.textContent = ''; return; }
        el.style.display = 'inline';
        el.style.color   = color || '#b8c0c8';
        el.textContent   = text;
    },

    // ── Shared WS frame processor ─────────────────────────────────────────────
    //
    // All incoming WebSocket frames are routed through this single method.
    // Both triggerScan and checkForActiveScan call it, so the streaming logic
    // lives in exactly one place.
    //
    // callbacks:
    //   onDone()  — called when the backend signals the scan is complete

    _processScanFrame(frame, callbacks = {}) {
        const { onDone } = callbacks;
        const t = frame && frame.type;

        // ── frame_seq ordering (W1 / §11.4) ──────────────────────────────────
        // Backend stamps a monotone ``frame_seq`` (scoped per snapshot_id /
        // workspace_id) on every outgoing frame. Drop frames whose seq is
        // lower than the highest we've already applied for this scope —
        // out-of-order delivery (rare; reconnection replay can backfill an
        // older seq after a newer one) should not be allowed to clobber
        // current state. Legacy frames without ``frame_seq`` (older
        // backend builds) bypass this check.
        //
        // Fix: previously the high-water-mark was bumped BEFORE the
        // dispatch ran. If the dispatched handler threw, the mark
        // was still bumped, and every subsequent retry of that frame
        // (replay-on-resume) would be silently discarded. Now we
        // only bump AFTER the if/else chain returns without throwing.
        let _frameSeqScope = null;
        let _frameSeqPrevHigh = 0;
        if (frame && typeof frame.frame_seq === 'number') {
            const scope = frame.workspace_id || String(frame.snapshot_id || '_global');
            if (!this._frameSeqHigh) this._frameSeqHigh = new Map();
            const high = this._frameSeqHigh.get(scope) || 0;
            if (frame.frame_seq < high) {
                // Out-of-order; discard.
                return;
            }
            _frameSeqScope = scope;
            _frameSeqPrevHigh = high;
            this._frameSeqHigh.set(scope, frame.frame_seq);
        }
        // The dispatch chain below may throw (a handler bug, a JSON
        // parse failure, etc.). If it does, ROLL BACK the high-
        // water-mark so a subsequent retry of the same seq isn't
        // discarded as stale. This requires wrapping the entire
        // if/else chain in try/catch — we use a sentinel that the
        // closure restores in the catch path.
        const _rollbackSeqOnError = (err) => {
            if (_frameSeqScope != null && this._frameSeqHigh) {
                this._frameSeqHigh.set(_frameSeqScope, _frameSeqPrevHigh);
            }
            console.warn('[scanner] frame dispatch threw, rolling back seq:', err && err.message);
        };
        try {

        // ── Telemetry ─────────────────────────────────────────────────────────
        if (t === 'stats') {
            this._updateStatsOverlay(frame);
            this.setScanStatus(
                `streaming… ${frame.deltas_verified || 0} verified, ${frame.nodes_streamed || 0} nodes`,
                '#b8c0c8'
            );

        } else if (t === 'log') {
            this._appendLogLine(frame);

        // ── Chunk-level events (pattern granularity) ──────────────────────────
        //
        // chunk_added fires first (from _process_delta).  Cache metadata; no
        // sphere yet.  The sphere comes with chunk_instances_partial moments later.

        } else if (t === 'chunk_added' && frame.chunk) {
            const ch = frame.chunk;
            if (ch.chunk_id)
                this._pendingChunks.set(ch.chunk_id, { url: frame.url || '', chunk: ch });

        } else if (t === 'chunk_replaced' && frame.chunk) {
            const ch = frame.chunk;
            if (frame.replaced_chunk_id)
                this._removeInstancesByChunkId(frame.replaced_chunk_id);
            if (ch.chunk_id)
                this._pendingChunks.set(ch.chunk_id, { url: frame.url || '', chunk: ch });

        } else if (t === 'chunk_removed' && frame.chunk_id) {
            this._removeInstancesByChunkId(frame.chunk_id);
            this._pendingChunks.delete(frame.chunk_id);

        // chunks_partial is the batch form of chunk_added (multiple patterns).
        } else if (t === 'chunks_partial' && Array.isArray(frame.chunks)) {
            frame.chunks.forEach(ch => {
                if (ch && ch.chunk_id)
                    this._pendingChunks.set(ch.chunk_id, { url: frame.url || '', chunk: ch });
            });

        // ── Instance-level events (node granularity) ──────────────────────────
        //
        // chunk_instances_partial carries instance_id — the canonical node ID.
        // We pull pre-cached metadata from _pendingChunks and stamp it onto the
        // node's dataMap entry so the billboard is instantly populated.

        } else if (t === 'chunk_instances_partial' && Array.isArray(frame.instances)) {
            const frameUrl = frame.url || '';
            const rows = [];

            frame.instances.forEach(i => {
                if (!i || !i.instance_id) return;
                if (this.nodeInstanceMap.has(i.instance_id)) return;  // idempotent

                const pending = i.chunk_id
                    ? this._pendingChunks.get(i.chunk_id)
                    : null;

                if (pending) {
                    // The billboard panel reads `data.fields` for the
                    // "Content-structure summary" section. The JS engine
                    // ships its dict as `content_fields_full` (snake-cased
                    // by mapper._apply_js_deltas before reaching us). We
                    // alias it to `fields` here so the summary is populated
                    // the moment the sphere appears — no need to wait for
                    // the /api/chunk_details fetch to complete (which fails
                    // mid-scan anyway because the instance row isn't in
                    // Kuzu yet and the live path keys by chunk_id, not
                    // instance_id).
                    const cff = pending.chunk.content_fields_full
                        || pending.chunk.contentFieldsFull
                        || {};
                    this.dataMap.set(i.instance_id, {
                        ...pending.chunk,
                        id:             i.instance_id,
                        chunk_id:       i.chunk_id,
                        url:            frameUrl || pending.url,
                        is_document:    false,
                        absolute_xpath: i.absolute_xpath || pending.chunk.representative_xpath || '',
                        fields:         cff,
                    });
                }

                if (i.chunk_id) {
                    if (!this._chunkIdToInstances.has(i.chunk_id))
                        this._chunkIdToInstances.set(i.chunk_id, new Set());
                    this._chunkIdToInstances.get(i.chunk_id).add(i.instance_id);
                }

                const row = {
                    id:          i.instance_id,
                    url:         frameUrl || (pending ? pending.url : ''),
                    is_document: false,
                    doc_id:      frameUrl ? `doc_${frameUrl}` : '',
                };
                if (pending && pending.chunk.image_url) row.image_url = pending.chunk.image_url;
                // Forward the raw content_fields_full to the sprite spawner
                // so its last-resort sweep (sprite_manager.js) can pick up
                // image-attr keys we didn't anticipate in the main extraction
                // pass below. Without this, the sweep sees an empty `node.
                // content_fields_full` and falls back to extractMediaFromHtml
                // which only fires after the html_raw lazy-load — too late
                // for streaming.
                if (pending && pending.chunk.content_fields_full) {
                    row.content_fields_full = pending.chunk.content_fields_full;
                }
                // Multi-image fan-out: every URL-typed field in the chunk's
                // content_fields_full becomes a candidate sprite around the
                // node. _spawnImageBillboards de-duplicates near-identical
                // URLs and promotes the first to the primary sprite; the
                // rest land in _extraSprites and orbit the primary.
                if (pending && pending.chunk.content_fields_full) {
                    const urls = [];
                    const fields = pending.chunk.content_fields_full;
                    for (const k in fields) {
                        const v = fields[k];
                        if (typeof v !== 'string' || !v) continue;
                        if (/\/@srcset$/i.test(k)) {
                            // srcset is a comma-separated list of
                            // ``URL <descriptor>`` pairs (e.g.
                            // ``foo-1x.jpg 1x, foo-2x.jpg 2x``). The
                            // largest-resolution candidate is usually the
                            // right one to display; pick the entry with
                            // the highest density / width descriptor.
                            // Without this split the entire srcset string
                            // would be sent to the texture loader as one
                            // (broken) URL.
                            let best = null, bestScore = -1;
                            v.split(',').forEach(part => {
                                const tok = part.trim();
                                if (!tok) return;
                                const ws = tok.split(/\s+/);
                                const u  = ws[0];
                                let score = 1;
                                if (ws[1]) {
                                    const m = ws[1].match(/^([\d.]+)(x|w)$/i);
                                    if (m) score = parseFloat(m[1]) * (m[2].toLowerCase() === 'w' ? 1 : 1000);
                                }
                                if (score > bestScore) { bestScore = score; best = u; }
                            });
                            if (best) urls.push(best);
                        } else if (/\/@(src|data-src|data-image|data-original|poster)$/i.test(k)) {
                            urls.push(v);
                        }
                    }
                    if (urls.length) row.image_urls = urls;
                }
                rows.push(row);
            });

            if (rows.length) {
                // Track that a scan is in flight so other code (e.g.
                // the recenter routine) can choose to be gentler.
                this._scanInFlight = true;
                this.addNodesIncrementally(rows, { quiet: true });
                // Multi-image fan-out: also forward rows whose image_urls
                // array carries fan-out candidates from content_fields_full,
                // even if no singular image_url was attached. Without this,
                // chunks whose ONLY image lives behind @data-src / @srcset
                // (the common DDG / Tarot / Substack pattern) never got
                // their sprite spawned.
                const withImages = rows.filter(r =>
                    r.image_url || (Array.isArray(r.image_urls) && r.image_urls.length > 0)
                );
                if (withImages.length) this._spawnImageBillboards(withImages);
                this._pendingIndexRows.push(...rows);
                // Camera-framing policy:
                //   • If this is the FIRST batch of the FIRST scan
                //     (no `_firstBatchFramed` yet AND the user hasn't
                //     orbited the camera themselves) → ONE framing
                //     tween so the brand-new cluster lands in view.
                //   • Otherwise → leave the camera exactly where the
                //     user has it. The previous regression of
                //     "constant re-snapping" came from doing this on
                //     every chunk arrival; gating on _firstBatchFramed
                //     limits it to a single one-shot.
                if (!this._firstBatchFramed
                    && !this._userHasInteracted
                    && typeof this.frameAllInstances === 'function') {
                    this.frameAllInstances({ duration: 0.5 });
                }
                this._firstBatchFramed = true;
                // Retrieval auto-uncollapse-on-arrival. If a search is
                // active and any of these new instances matches it,
                // un-collapse their parent doc clusters so the user can
                // see the late-arriving hits without re-running the
                // query. Honours the user's global Collapse-All toggle
                // by ONLY expanding matching docs — non-matching ones
                // stay collapsed as the user requested.
                if (this._activeSearchInstanceIds && this._activeSearchInstanceIds.size) {
                    for (const r of rows) {
                        if (this._activeSearchInstanceIds.has(r.id) && r.doc_id) {
                            this.docCollapseTarget.set(r.doc_id, 0);
                        }
                    }
                }
                // §5.4 / §16.5 — incremental mid-scan UMAP refits. The old
                // draft disabled these because (a) the mid-scan recompute
                // wiped init.position and (b) a half-finished SVD on a tiny
                // doc count looked random. Both are now resolved: the layout
                // is real neighbour-preserving UMAP (G2, gated to ≥8 samples,
                // SVD-bridge below that), and _applyUmapCoords RETARGETS each
                // chunk via the interruptible tween (§9.2) rather than wiping
                // it — so a mid-scan refit settles smoothly. Until the first
                // refit lands, the hash-DIRECTION radial placeholder (§6.1,
                // cp/layout.js — NOT a concentric-sphere layout) holds the
                // streaming spheres; the scan-end fit on 'done' still runs.
                // Throttled (≥8 chunks, ≥2.5s apart, not-in-flight) so we
                // refit periodically, not on every batch.
                try {
                    const totalChunks =
                        (this._chunkIdToInstances && this._chunkIdToInstances.size) || 0;
                    const now = Date.now();
                    if (totalChunks >= 8 && !this._umapInFlight &&
                        (now - (this._lastIncUmapAt || 0)) >= 2500 &&
                        typeof this._runUmapAsync === 'function') {
                        this._lastIncUmapAt = now;
                        this._runUmapAsync(totalChunks);  // fire-and-forget; self-gated
                    }
                } catch (e) {
                    console.warn('[scanner] incremental UMAP skipped:', e && e.message);
                }
            }
            // Keep _pendingChunks alive for later batches of the same pattern.

        // ── DB-persistence confirmation ────────────────────────────────────────
        //
        // instances_indexed fires AFTER kuzu has committed this batch.
        // Lazy-fetch rich details (html_raw, rendered_text) for nodes that
        // still lack them.

        } else if (t === 'instances_indexed') {
            if (this._pendingIndexRows && this._pendingIndexRows.length) {
                this._lazyLoadAllNodeDetails(this._pendingIndexRows);
                this._pendingIndexRows = [];
            }

        } else if (t === 'cached') {
            this.setScanStatus('cached — page unchanged since last scan', '#b8c0c8');
            this.setLoadingProgress('Page unchanged — using cached snapshot', 100);

        // ── W1 new frame types (§11.4) ────────────────────────────────────────
        //
        // Wire the schema end-to-end now; downstream workstreams (W2, W5,
        // W6) light up the substantive behaviour. Each handler is a
        // documented forward-declaration that won't crash if the backend
        // emits the frame today.

        } else if (t === 'umap_canonical') {
            // §11.5 — canonical 6D coords broadcast from Layout Service (W2).
            // Body: { coords: {id: [x,y,z,h,s,v]}, url_roots?, removed_ids?, provenance? }
            //   - [0:3] = spatial position → init.position.
            //   - [3:6] = UMAP content-HSV (§6.1/§707) → init.umapHsl, which the
            //     animate loop renders as the chunk fill colour and rotates by
            //     the camera-azimuth hue phase. Provenance tint (§9.12) lerps on
            //     TOP of that content-HSV each frame. (RESOLVED: this was once an
            //     open render gap where the HSV channels were discarded and the
            //     mesh used hash-family hue; coords[3:6] are now wired end-to-end
            //     via _applyUmapCoords → cp/hsv_color.js, §6.1 REPL/render split.)
            // _applyUmapCoords applies BOTH the position and the HSV (it accepts
            // the 6-vector; the prior length===3 guard rejected every canonical
            // frame). Per-URL root_position from url_roots is also stashed for
            // force_layout.js consumers.
            this._lastUmapCanonical = frame;
            if (Array.isArray(frame.removed_ids)) {
                frame.removed_ids.forEach(id => {
                    if (this.nodeInstanceMap && this.nodeInstanceMap.has(id)) {
                        this._removeNodeInstance(id);
                    }
                });
            }
            // Stash per-URL roots so force_layout.js can read them on
            // its next step. Without this the layout would re-derive
            // hash-based offsets and contradict the backend's choice.
            if (frame.url_roots) {
                if (!this._urlRootPositions) this._urlRootPositions = new Map();
                for (const [url, rec] of Object.entries(frame.url_roots)) {
                    if (rec && Array.isArray(rec.root_position)) {
                        this._urlRootPositions.set(url, {
                            root_position: rec.root_position.slice(),
                            bounding_radius: rec.bounding_radius || 0,
                        });
                    }
                }
            }
            // Stash provenance per id so the animate-loop can render
            // small badges per chunk (W7 will surface them in the UI;
            // W3 just caches).
            if (frame.provenance) {
                if (!this._provenanceById) this._provenanceById = new Map();
                for (const [id, prov] of Object.entries(frame.provenance)) {
                    this._provenanceById.set(id, prov);
                }
                // W17 — apply visual provenance tint to existing
                // instances. Scanner-emitted = no tint (default).
                // graph-output = cyan shift; agent-output = amber.
                if (typeof this._applyProvenanceTint === 'function') {
                    this._applyProvenanceTint(frame.provenance);
                }
            }
            // Apply the coords. The legacy /api/recompute_umap path
            // delivers the same dict shape, so we reuse the existing
            // post-processing (fit-to-sphere + client-side collider
            // repulsion + UMAP-lock per-instance flag).
            if (frame.coords && typeof this._applyUmapCoords === 'function') {
                try {
                    this._applyUmapCoords(frame.coords);
                } catch (e) {
                    console.warn('[scanner] umap_canonical apply failed:', e && e.message);
                }
            }

        } else if (t === 'compute_graph_layout') {
            // H1 / §6.6.4 / §P — the backend compute-graph projector overlay
            // (bisector node + UMAP-independent link network + settled
            // readouts). Rendered into an isolated overlay group.
            this._renderComputeGraphOverlay(frame);

        } else if (t === 'ontology_layout') {
            // §R.2 — the FULL database ontology projected into the 6D space:
            // fixtures, python-native functional-object trees, user concepts,
            // compiled-from-scans — alongside the chunk field. Isolated
            // overlay group, same defensive posture as the compute-graph one.
            this._renderOntologyOverlay(frame);

        } else if (t === 'concept_changed') {
            // Multi-tab sync — a peer tab edited / created / deleted
            // a concept node. Reload our local Map and DOM for that
            // specific card so we stay in sync without polling.
            //
            // Skip the broadcast if it came from US (the originator
            // already updated locally before issuing the REST call).
            // We can't fully attribute frames to "this tab"; the
            // simplest filter is: if the change matches our pending
            // sync state for that id, ignore.
            if (typeof this._applyConceptChangedFrame === 'function') {
                this._applyConceptChangedFrame(frame);
            }

        } else if (t === 'edge_changed') {
            // Multi-tab sync — a peer tab created / deleted an edge.
            // Reconcile the local edge list + redraw without a full
            // /api/concepts re-fetch.
            if (typeof this._applyEdgeChangedFrame === 'function') {
                this._applyEdgeChangedFrame(frame);
            }

        } else if (t === 'concept_index_update') {
            // §11.6 — concept-side index update (embedding + pagerank +
            // similar_to + provenance). Frontend's retrieval surfaces
            // (hover apparitions, empty radiation) read from this cache.
            // W5 wires the substantive consumer; W1 just stores.
            if (!this._conceptIndexCache) this._conceptIndexCache = new Map();
            const updates = frame.updates || {};
            for (const [cardId, slot] of Object.entries(updates)) {
                this._conceptIndexCache.set(cardId, slot);
            }
            if (Array.isArray(frame.removed_ids)) {
                frame.removed_ids.forEach(id => this._conceptIndexCache.delete(id));
            }

        } else if (t === 'purge_workspace') {
            // §9.11 — authoritative reset / URL removal from backend.
            // W1 wires the receive path; existing client-side purge logic
            // in workspace.js handles the scene mutation when invoked.
            const urls = Array.isArray(frame.urls) ? frame.urls : null;
            if (urls && urls.length) {
                urls.forEach(u => {
                    if (typeof this._purgeUrlFromScene === 'function') {
                        this._purgeUrlFromScene(u);
                    }
                });
            } else {
                // Full workspace purge — clear in-memory caches the W1
                // schema introduced. Mesh-side cleanup is handled by
                // existing workspace.js reset paths called separately.
                if (this._frameSeqHigh) this._frameSeqHigh.clear();
                if (this._conceptIndexCache) this._conceptIndexCache.clear();
                this._lastUmapCanonical = null;
                // H1 — drop the compute-graph overlay on full purge.
                if (typeof this._clearComputeGraphOverlay === 'function') {
                    this._clearComputeGraphOverlay();
                }
                // §R.2 — drop the ontology overlay on full purge.
                if (typeof this._clearOntologyOverlay === 'function') {
                    this._clearOntologyOverlay();
                }
            }

        } else if (t === 'ui_state_changed') {
            // §6.6.5 / §7.3.5 (Q.3-Q.5) — generalized rank-dominance collapse.
            // A REPL (or peer-tab) `ui-dominance-collapse` gesture lands here
            // via the persistent workspace WS. Build the set of chunk ids to
            // hide (the dominator's folded chunk samples + every isolated
            // node) so the animate-loop forces scale=0 — making the REPL
            // gesture VISIBLE in the live 3D projector. Re-expand clears the
            // entry and the nodes return next frame (fold is a flag, never a
            // mesh mutation, §6.3).
            const state = frame.state || frame.ui || {};
            const dom = state.dominance_collapse || {};
            const hide = new Set();
            const keepDominators = new Set();
            for (const nodeId in dom) {
                const e = dom[nodeId];
                if (!e || !e.collapsed) continue;
                keepDominators.add(nodeId);
                (e.folded_set || []).forEach(id => hide.add(String(id)));
                (e.hidden_set || []).forEach(id => hide.add(String(id)));
            }
            // Never hide a dominator node that itself appears in the mesh
            // (e.g. a compute/bisector node clicked in 3D).
            keepDominators.forEach(id => hide.delete(String(id)));
            this._dominanceHiddenChunkIds = hide;
            this._dominanceActive = keepDominators.size > 0;
            // Force an immediate matrix refresh so the change is instant
            // even if the camera is still (the rAF loop reads the set).
            if (typeof this._requestRender === 'function') this._requestRender();

        } else if (t === 'apparition_hint') {
            // §8D.16 / §8D.43 — top-K candidates for a focal concept node.
            // Body: { focal_id, candidates: [{ card_id, score, ... }] }
            // W6 wires the substantive renderer (apparition halo around
            // the focal); W1 stores the latest hint per focal.
            if (!this._apparitionHints) this._apparitionHints = new Map();
            if (frame.focal_id) {
                this._apparitionHints.set(frame.focal_id, frame.candidates || []);
            }

        } else if (t === 'agent_review') {
            // W24 / §8C.8 — RequestUserReviewAction landed.
            // Body: { entry: { review_id, prompt, card_ids, actor } }
            const entry = frame && frame.entry;
            if (entry && typeof this._renderAgentReview === 'function') {
                this._renderAgentReview(entry);
            }

        } else if (t === 'evolution_log_diff') {
            // C5 / §8D.33 — append-only log emits this frame on every
            // diff write so any open log-viewer panel sees the new row
            // immediately instead of polling /api/evolution_log.
            if (typeof this._appendEvolutionLogDiff === 'function' && frame.diff) {
                this._appendEvolutionLogDiff(frame.diff);
            }

        } else if (t === 'agent_token') {
            // W10 / §8D.8, §8D.28 — live SLM token stream from a
            // meta-cognition node tick. Body:
            //   { token: str, parameter_card_id: str }
            // Append to per-parameter buffer + the floating display
            // overlay (W15) so the user can watch the agent reason
            // in real time.
            //
            // Fix: cap the per-parameter buffer at 4000 tokens to
            // bound memory. Tokens beyond the cap roll off the
            // front so the most-recent reasoning stays visible.
            if (!this._agentTokenBuffers) this._agentTokenBuffers = new Map();
            if (!this._agentTokenSeenPcids) this._agentTokenSeenPcids = new Set();
            const pcid = frame.parameter_card_id || '_default';
            // §8D.8 retroactive fetch — first time we see tokens for
            // this pcid in this session, ask the backend for the
            // ring buffer so we don't miss the tick's opening tokens
            // that streamed before our WS subscription landed. We do
            // this once per pcid per session to avoid pulling the
            // backlog on every frame.
            if (!this._agentTokenSeenPcids.has(pcid)) {
                this._agentTokenSeenPcids.add(pcid);
                if (pcid !== '_default') {
                    fetch(`/api/agent/tokens/${encodeURIComponent(pcid)}`)
                        .then(r => r.ok ? r.json() : null)
                        .then(data => {
                            if (!data || !Array.isArray(data.tokens)) return;
                            const buf2 = this._agentTokenBuffers.get(pcid) || [];
                            // Prepend backlog tokens that aren't already
                            // present at the tail of the buffer. The
                            // overlap detection is naive but cheap.
                            const backlog = data.tokens.map(x => x.token || '').filter(Boolean);
                            if (backlog.length && buf2.length === 0) {
                                buf2.push(...backlog);
                                this._agentTokenBuffers.set(pcid, buf2.slice(-4000));
                                if (typeof this._renderAgentTokens === 'function') {
                                    this._renderAgentTokens(pcid);
                                }
                            }
                        })
                        .catch(() => { /* retro-fetch is best-effort */ });
                }
            }
            const buf = this._agentTokenBuffers.get(pcid) || [];
            if (typeof frame.token === 'string') buf.push(frame.token);
            const MAX_BUF = 4000;
            if (buf.length > MAX_BUF) buf.splice(0, buf.length - MAX_BUF);
            this._agentTokenBuffers.set(pcid, buf);
            if (typeof this._appendAgentToken === 'function' && typeof frame.token === 'string') {
                this._appendAgentToken(pcid, frame.token);
            }

        } else if (t === 'done') {
            // Final lazy-load sweep.
            if (this._pendingIndexRows && this._pendingIndexRows.length) {
                this._lazyLoadAllNodeDetails(this._pendingIndexRows);
                this._pendingIndexRows = [];
            }
            try {
                this.applyWorkspaceVisibility();
                this.renderFileTree();
                this.renderUrlBuckets();
            } catch (_) {}
            // Per Mortegon §2.1: UMAP is the layout initialiser, and
            // the recompute "fires automatically at the tail of every
            // scan." The earlier comment claiming UMAP was manual-only
            // documented a previous workaround for mid-scan jitter;
            // running UMAP ONCE at scan-end (with a chunk threshold
            // so a 2-chunk scan doesn't trigger a malformed SVD) is
            // the correct contract. _userHasInteracted gates the
            // camera fly so we don't yank a user who's manually
            // exploring; UMAP itself always runs.
            //
            // The fly-to-newest tween from the previous draft was
            // pulled out — it landed at minDistance and made small
            // scans feel "stuck zoomed in." UMAP-driven layout
            // already centres + scales the result; the user's own
            // orbit input now determines framing.
            try {
                const totalChunks = (this._chunkIdToInstances && this._chunkIdToInstances.size) || 0;
                if (totalChunks >= 8 && typeof this._runUmapAsync === 'function' && !this._umapInFlight) {
                    // Fire-and-forget; _runUmapAsync handles its own
                    // gating, error logging, and post-processing
                    // (fit-to-sphere + collider repulsion in
                    // _applyUmapCoords).
                    this._runUmapAsync(totalChunks);
                }
            } catch (e) {
                console.warn('[scanner] scan-end UMAP skipped:', e && e.message);
            }
            // §R.2 — refresh the full-ontology projection at scan-end so the
            // concept side (incl. compiled-from-scans the scan just minted)
            // tracks the chunk field's cadence.
            if (typeof this._requestOntologyLayout === 'function') {
                this._requestOntologyLayout();
            }
            this._scanInFlight = false;
            if (onDone) onDone();
        }
        } catch (e) {
            _rollbackSeqOnError(e);
        }
    },

    // ── Helper: remove all spheres that belong to a chunk_id ─────────────────

    _removeInstancesByChunkId(chunkId) {
        if (!this._chunkIdToInstances) return;
        const ids = this._chunkIdToInstances.get(chunkId);
        if (!ids) return;
        ids.forEach(iid => {
            if (this.nodeInstanceMap.has(iid)) this._removeNodeInstance(iid);
        });
        this._chunkIdToInstances.delete(chunkId);
        this._pendingChunks.delete(chunkId);
    },

    // ── Auto-connect to an externally started scan ────────────────────────────
    //
    // Called once on page load.  If scripts/scan.py is running in backend-
    // delegation mode, the backend will have an active scan that the frontend
    // would otherwise miss.  We detect it via GET /api/scan_status and attach
    // to the same WebSocket stream transparently.

    async checkForActiveScan() {
        try {
            const data = await fetch('/api/scan_status').then(r => r.ok ? r.json() : null);
            if (!data || !data.active || !data.ws_url) return;

            console.log('[ChunkProjector] Active scan detected — auto-connecting');
            this.setScanStatus('scan detected — connecting…', '#b8c0c8');
            this.setLoadingProgress('Attaching to active scan…', 20);

            await new Promise(resolve => {
                let done = false;
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                // resume=0 requests a full replay from frame 1 so we never miss
                // chunks that were emitted before we connected.
                const ws = new WebSocket(
                    `${protocol}//${window.location.host}${data.ws_url}?resume=0`
                );

                ws.onmessage = (event) => {
                    try {
                        this._processScanFrame(JSON.parse(event.data), {
                            onDone: () => {
                                done = true;
                                setTimeout(() => this.setScanStatus(''), 4000);
                                this.hideLoadingProgress();
                                try { ws.close(); } catch (_) {}
                                resolve();
                            },
                        });
                    } catch (_) {}
                };

                ws.onerror = () => { if (!done) { this.hideLoadingProgress(); resolve(); } };
                ws.onclose = () => { if (!done) { this.hideLoadingProgress(); resolve(); } };
            });
        } catch (_) {
            // Backend unreachable or no active scan — silently ignore.
        }
    },

    // ── Main scan trigger ─────────────────────────────────────────────────────

    async triggerScan() {
        const btn = document.getElementById('snapshot-btn');
        if (!btn) return;
        btn.disabled  = true;
        const origHtml = btn.innerHTML;
        btn.innerHTML  = '<i class="fas fa-spinner fa-spin"></i> Scanning';
        this.setScanStatus('dispatching…', '#b8c0c8');

        // INCREMENTAL scan: keep previously-scanned URLs in the scene
        // and stream coordinate updates for new chunks. The old behavior
        // wiped the entire instance pool on every Scan click which made
        // re-scanning a URL feel like a fresh page load. Now we:
        //   * Leave nodeInstanceMap / dataMap intact.
        //   * Unpin panels (user starts a new investigation) but don't
        //     blank out the scene.
        //   * Reset the per-scan delivery bookkeeping so chunk_added /
        //     chunk_instances_partial frames for THIS scan are tracked
        //     fresh, but any chunk_id we've seen before keeps its
        //     existing sphere — chunk_replaced will swap the metadata
        //     in place and chunk_removed cleans up if needed.
        if (this._pinnedPanels && this._pinnedPanels.size) {
            Array.from(this._pinnedPanels.keys()).forEach(id => this.unpinPanel(id));
            this._panelHoverCount = 0;
        }
        // Reset per-scan tracking state. These are scan-scoped, not
        // scene-scoped — clearing them does NOT affect already-rendered
        // spheres or their data.
        if (!this._pendingChunks)      this._pendingChunks      = new Map();
        if (!this._chunkIdToInstances) this._chunkIdToInstances = new Map();
        this._pendingChunks.clear();
        this._pendingIndexRows = [];
        this._loggedImageFailures = 0;
        if (this._imageProxyFailures) this._imageProxyFailures.clear();
        // Re-arm the auto-frame so a fresh scan re-aims the camera at its
        // first batch (useful when previous scans were of a different URL).
        this._firstBatchFramed = false;
        // NB: _chunkIdToInstances is kept across scans so chunk_removed
        // events for previously-streamed chunks can still resolve to
        // their existing spheres. The map is keyed by chunk_id which is
        // url + xpath-hash; same chunk on a re-scan keeps the same id.

        const preIds = new Set(this.dataMap.keys());
        this.setLoadingProgress('Initiating live browser scan...', 10);

        let settled   = false;
        let wsFailed  = false;
        let ws        = null;
        let wsCleanup = () => {};

        try {
            const res = await fetch('/api/snapshot', { method: 'GET' });
            if (!res.ok && res.status !== 202) {
                const body = await res.text().catch(() => '');
                throw new Error(`HTTP ${res.status} ${body || ''}`);
            }

            const dispatch      = await res.json().catch(() => ({}));
            const wsId          = dispatch.snapshot_ws_id ?? dispatch.snapshot_id ?? null;
            const wsPath        = dispatch.ws_url || (wsId !== null ? `/api/ws/nodes/${wsId}` : null);
            const dispatchedUrl = dispatch.url || null;
            if (dispatchedUrl) { try { this.addUrlToActiveWorkspace(dispatchedUrl); } catch (_) {} }

            this.setScanStatus('scan running…', '#b8c0c8');
            this.setLoadingProgress('Extracting and distilling DOM...', 30);

            let scanDone = false;
            let doneResolver;
            const donePromise = new Promise(r => { doneResolver = r; });

            if (wsPath) {
                try {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    ws             = new WebSocket(`${protocol}//${window.location.host}${wsPath}`);

                    ws.onmessage = (event) => {
                        try {
                            this._processScanFrame(JSON.parse(event.data), {
                                onDone: () => {
                                    scanDone = true;
                                    try { doneResolver(); } catch (_) {}
                                },
                            });
                        } catch (_) {}
                    };

                    ws.onerror = () => { wsFailed = true; };
                    ws.onclose = () => { if (!scanDone) wsFailed = true; };
                    wsCleanup  = () => { try { ws && ws.close(); } catch (_) {} };
                } catch (_e) { wsFailed = true; }
            } else {
                wsFailed = true;
            }

            // ── Polling fallback ──────────────────────────────────────────────
            const pollStart    = Date.now();
            const POLL_CAP_MS  = 5 * 60 * 1_000;
            const _idsEqual    = (a, b) => {
                if (a.size !== b.size) return false;
                for (const k of a) if (!b.has(k)) return false;
                return true;
            };
            let lastLoadedIds   = new Set(preIds);
            let stablePollCount = 0;

            const reloadIfChanged = async (label) => {
                try {
                    const nodes   = await fetch('/api/chunk_nodes').then(r => r.json());
                    const liveIds = new Set((nodes && nodes.nodes ? nodes.nodes : []).map(n => n.id));
                    if (_idsEqual(liveIds, lastLoadedIds)) return false;
                    this.setLoadingProgress(`Reloading scene… (${label})`, 90);
                    await this.loadNodes();
                    lastLoadedIds = new Set(this.dataMap.keys());
                    return true;
                } catch (_) { return false; }
            };

            while (Date.now() - pollStart < POLL_CAP_MS) {
                if (wsFailed) {
                    await new Promise(r => setTimeout(r, 1500));
                    if (scanDone) { await reloadIfChanged('final'); settled = true; break; }
                    const changed = await reloadIfChanged('progress');
                    if (changed) stablePollCount = 0;
                    else if (++stablePollCount >= 20) { await reloadIfChanged('stable'); settled = true; break; }
                } else {
                    await Promise.race([donePromise, new Promise(r => setTimeout(r, 10_000))]);
                    if (scanDone) { await reloadIfChanged('final'); settled = true; break; }
                    wsFailed = true;
                }
            }

            wsCleanup();
            if (!settled) this.setScanStatus('scan incomplete — check server', '#b8c0c8');
            else setTimeout(() => this.setScanStatus(''), 4000);

        } catch (err) {
            console.error('[ChunkProjector] scan failed', err);
            this.setScanStatus(`scan failed: ${err.message || err}`, '#b25b5b');
            this.setLoadingProgress('Scan failed', 100);
            setTimeout(() => this.hideLoadingProgress(), 1000);
        } finally {
            if (!settled) this.hideLoadingProgress();
            btn.disabled  = false;
            btn.innerHTML = origHtml;
        }
    },

    /**
     * Incremental UMAP scheduler. Tracks the cumulative unique chunk
     * count across all URLs; the first time it crosses 500 we POST
     * /api/recompute_umap and apply the returned per-chunk coordinates
     * to the scene. After that we re-trigger every time the count
     * doubles (1000, 2000, 4000, …) so layout stays current as more
     * chunks come in without recomputing on every batch.
     */
    _maybeRecomputeUmap() {
        // Cumulative chunk count = unique chunk_ids the projector has seen.
        // _chunkIdToInstances is populated by chunk_instances_partial and
        // survives across scans (Batch 1.4 made the scene persistent).
        const n = (this._chunkIdToInstances && this._chunkIdToInstances.size) || 0;
        if (n < 500) return;
        const lastTrigger = this._lastUmapAt || 0;
        // First trigger at 500, then each doubling.
        const threshold = lastTrigger === 0 ? 500 : lastTrigger * 2;
        if (n < threshold) return;
        this._lastUmapAt = n;
        this._runUmapAsync(n);
    },

    async _runUmapAsync(n) {
        if (this._umapInFlight) return;
        this._umapInFlight = true;
        try {
            this.setScanStatus(`recomputing UMAP @ ${n} chunks…`, '#b8c0c8');
            const res = await fetch('/api/recompute_umap', { method: 'POST' });
            if (!res.ok) throw new Error('HTTP ' + res.status);
            const data = await res.json();
            if (data && data.status === 'success' && data.coords)
                this._applyUmapCoords(data.coords);
        } catch (err) {
            console.warn('[UMAP] recompute failed', err);
        } finally {
            this._umapInFlight = false;
            this.setScanStatus('');
        }
    },

    // ── H1 / §6.6.4 / §P — compute-graph projector overlay ───────────────
    //
    // Renders the §P.10 BISECTOR node (the single collapsed compute-graph
    // node on the input↔output transport line) plus the UMAP-INDEPENDENT
    // link network (§P.8/P.9) into a dedicated overlay group, kept distinct
    // from the chunk InstancedMesh so a malformed frame can never perturb
    // the chunk field or the animate loop (defensive + fully isolated).
    // Consumes the backend `compute_graph_layout` frame (ws_frames
    // build_compute_graph_layout): { graph_id, node:{pos,hsv}, settle_seq,
    // readouts:[{chunk_id,pos,hsv}], links:[{src_id,dst_id,kind}] }.
    // Clicking the bisector node opens/closes the 2D graph (§P.10) via a
    // decoupled `wfh:open-compute-graph` CustomEvent the editor listens for.
    _renderComputeGraphOverlay(frame) {
        try {
            if (!frame || !this.scene) return;
            const T = window.THREE || (typeof THREE !== 'undefined' ? THREE : null);
            if (!T) return;
            if (!this._cgOverlay) {
                this._cgOverlay = new T.Group();
                this._cgOverlay.name = 'compute-graph-overlay';
                this.scene.add(this._cgOverlay);
                this._cgNodes = new Map();    // graph_id → bisector mesh
                this._cgPickables = [];        // raycast targets (interaction.js)
                this._cgLinks = [];            // line objects (rebuilt per frame)
            }
            const gid  = frame.graph_id || '';
            const node = frame.node || null;
            // No placement (e.g. a graph with no resolved input↔output
            // distribution) → don't render a phantom bisector at the origin.
            const hasPlacement = !!(node && Array.isArray(node.pos) &&
                (node.pos[0] || node.pos[1] || node.pos[2] ||
                 (frame.readouts && frame.readouts.length)));
            if (!hasPlacement) return;
            const pos  = node.pos;
            const hsv  = Array.isArray(node.hsv) ? node.hsv : [0.5, 0.5, 0.5];
            const prev = this._cgNodes.get(gid);
            // settle_seq monotone guard — ignore a stale out-of-order frame.
            if (prev && typeof frame.settle_seq === 'number' &&
                frame.settle_seq < (prev.userData.settleSeq || 0)) return;
            let mesh = prev;
            if (!mesh) {
                const geo = new T.SphereGeometry(1.2, 18, 18);
                const mat = new T.MeshBasicMaterial({ color: new T.Color(0x9aa3ad) });
                mesh = new T.Mesh(geo, mat);
                // userData.id mirrors the chunk-mesh convention so interaction.js
                // raycast can read it; computeGraphId marks the open/close target.
                mesh.userData = { id: `cg::${gid}`, computeGraphId: gid };
                this._cgOverlay.add(mesh);
                this._cgNodes.set(gid, mesh);
                this._cgPickables.push(mesh);
            }
            mesh.position.set(pos[0], pos[1], pos[2]);   // §P.10 slides on bisector
            mesh.userData.settleSeq = frame.settle_seq || 0;
            if (mesh.material && mesh.material.color && mesh.material.color.setHSL) {
                mesh.material.color.setHSL(
                    hsv[0], hsv[1] != null ? hsv[1] : 0.6, hsv[2] != null ? hsv[2] : 0.5);
            }
            // §7.8.3 — seat each settled readout on its perimeter coord by
            // writing into initialNodeData; the chunk field re-places it.
            (frame.readouts || []).forEach((r) => {
                if (r && r.chunk_id && Array.isArray(r.pos) && this.initialNodeData) {
                    const init = this.initialNodeData.get(r.chunk_id);
                    if (init && init.position && init.position.set) {
                        init.position.set(r.pos[0], r.pos[1], r.pos[2]);
                    }
                }
            });
            // §R.4 — project the readout PERIMETER as rendered panels (name +
            // §8D.20 clean-text tree). Only the outermost computation nodes
            // (no succeeding links — the backend readout set) ever get a
            // panel; hidden-state nodes are not in the frame by contract.
            this._upsertReadoutPanels(frame, mesh);
            // Rebuild the coordinate-free link network: resolve each endpoint
            // id to a live position (the bisector node, or a chunk/readout in
            // initialNodeData). Links whose endpoints aren't placed are skipped.
            this._cgLinks.forEach((l) => { try { this._cgOverlay.remove(l); } catch (_) {} });
            this._cgLinks = [];
            const resolve = (id) => {
                if (id === gid || id === `cg::${gid}`) return mesh.position;
                if (this.initialNodeData && this.initialNodeData.has(id)) {
                    const init = this.initialNodeData.get(id);
                    if (init && init.position) return init.position;
                }
                return null;
            };
            (frame.links || []).forEach((link) => {
                const a = resolve(link.src_id), b = resolve(link.dst_id);
                if (!a || !b) return;
                const g = new T.BufferGeometry().setFromPoints([
                    a.clone ? a.clone() : a, b.clone ? b.clone() : b,
                ]);
                const m = new T.LineBasicMaterial(
                    { color: 0x8893a0, transparent: true, opacity: 0.5 });
                const line = new T.Line(g, m);
                this._cgOverlay.add(line);
                this._cgLinks.push(line);
            });
        } catch (e) {
            console.warn('[scanner] compute_graph overlay render failed:', e && e.message);
        }
    },

    _clearComputeGraphOverlay() {
        try {
            if (this._cgOverlay && this.scene) this.scene.remove(this._cgOverlay);
        } catch (_) {}
        this._cgOverlay = null;
        this._cgNodes = null;
        this._cgPickables = [];
        this._cgLinks = [];
        this._clearReadoutPanels();
    },

    // ── §R.2 — full-ontology projector overlay ───────────────────────────
    //
    // "the full database ontology mapped to our 3D umap GUI, which
    //  integrates our full set of DB functional-objects and scanned
    //  webpage chunk structures." (USER_REQUIREMENTS_VERBATIM.md §R.2)
    //
    // Consumes the `ontology_layout` frame: every workspace ConceptNode
    // (fixtures, python_object/property/function trees, user concepts,
    // compiled-from-scans) at its 6D nomic-UMAP coordinate, plus the
    // coordinate-free one-edge-table adjacency. Rendered into a dedicated
    // THREE.Group — octahedron markers (visually distinct from the chunk
    // InstancedMesh spheres), HSL from the fit's HSV channels, faint typed
    // links. Raycast-pickable via userData.id = `onto::<concept_id>` so
    // click-and-stick (§5.3) extends to ontology nodes.
    _renderOntologyOverlay(frame) {
        try {
            if (!frame || !this.scene) return;
            const T = window.THREE || (typeof THREE !== 'undefined' ? THREE : null);
            if (!T) return;
            if (!this._ontoOverlay) {
                this._ontoOverlay = new T.Group();
                this._ontoOverlay.name = 'ontology-overlay';
                this.scene.add(this._ontoOverlay);
                this._ontoNodes = new Map();   // concept_id → mesh
                this._ontoPickables = [];
                this._ontoLinks = [];
            }
            const coords = frame.coords || {};
            const names = frame.names || {};
            const hints = frame.type_hints || {};
            const seen = new Set();
            for (const [cid, v] of Object.entries(coords)) {
                if (!Array.isArray(v) || v.length < 3) continue;
                seen.add(cid);
                let mesh = this._ontoNodes.get(cid);
                if (!mesh) {
                    // Octahedron = ontology marker; size by class (fixtures
                    // anchor slightly larger, python-native members smaller).
                    const hint = hints[cid] || '';
                    const isFixture = /^fixture::/.test(cid);
                    const size = isFixture ? 1.1 : /^python_/.test(hint) ? 0.55 : 0.8;
                    const geo = new T.OctahedronGeometry(size, 0);
                    const mat = new T.MeshBasicMaterial({
                        color: 0xc8ccd2, transparent: true, opacity: 0.85,
                    });
                    mesh = new T.Mesh(geo, mat);
                    mesh.userData = {
                        id: `onto::${cid}`, ontologyConceptId: cid,
                        name: names[cid] || cid, typeHint: hint,
                    };
                    this._ontoOverlay.add(mesh);
                    this._ontoNodes.set(cid, mesh);
                    this._ontoPickables.push(mesh);
                }
                mesh.position.set(v[0], v[1], v[2]);
                if (v.length >= 6 && mesh.material && mesh.material.color &&
                    mesh.material.color.setHSL) {
                    mesh.material.color.setHSL(v[3], 0.35 + 0.4 * v[4], 0.35 + 0.35 * v[5]);
                }
            }
            // Drop nodes the new frame no longer carries (deleted concepts).
            for (const [cid, mesh] of Array.from(this._ontoNodes.entries())) {
                if (!seen.has(cid)) {
                    try { this._ontoOverlay.remove(mesh); } catch (_) {}
                    this._ontoNodes.delete(cid);
                    const i = this._ontoPickables.indexOf(mesh);
                    if (i >= 0) this._ontoPickables.splice(i, 1);
                }
            }
            // Rebuild the typed link lines (coordinate-free adjacency,
            // resolved against the just-placed ontology meshes).
            this._ontoLinks.forEach((l) => { try { this._ontoOverlay.remove(l); } catch (_) {} });
            this._ontoLinks = [];
            (frame.edges || []).forEach((e) => {
                const a = this._ontoNodes.get(e.src_id);
                const b = this._ontoNodes.get(e.dst_id);
                if (!a || !b) return;
                const g = new T.BufferGeometry().setFromPoints([
                    a.position.clone(), b.position.clone(),
                ]);
                const m = new T.LineBasicMaterial({
                    color: 0x6b7480, transparent: true, opacity: 0.28,
                });
                const line = new T.Line(g, m);
                this._ontoOverlay.add(line);
                this._ontoLinks.push(line);
            });
        } catch (e) {
            console.warn('[scanner] ontology overlay render failed:', e && e.message);
        }
    },

    _clearOntologyOverlay() {
        try {
            if (this._ontoOverlay && this.scene) this.scene.remove(this._ontoOverlay);
        } catch (_) {}
        this._ontoOverlay = null;
        this._ontoNodes = null;
        this._ontoPickables = [];
        this._ontoLinks = [];
    },

    /**
     * §R.2 — request the ontology projection from the backend (dual-routed:
     * the `ontology_layout` frame also lands on the workspace WS, which is
     * what actually renders). Fired on workspace open and after scan-end so
     * the ontology tracks the chunk field's cadence.
     */
    _requestOntologyLayout() {
        try {
            fetch('/api/ontology/layout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workspace_id: (typeof window !== 'undefined' && window._activeWorkspaceId) || '',
                }),
            }).catch(() => {});
        } catch (_) { /* best-effort */ }
    },

    // ── §R.4 — readout perimeter as RENDERED PANELS ──────────────────────
    //
    // "project only the outermost computation nodes in the form of their
    //  rendered panel versions with clean-text tree structures that don't
    //  have any succeeding links in the computation graph representation."
    //  (USER_REQUIREMENTS_VERBATIM.md §R.4, verbatim)
    //
    // Each readout in a `compute_graph_layout` frame carries `name` +
    // `rendering` (the §8D.20 clean-text tree the compile settled). We
    // render them as screen-anchored DOM mini-panels (the app's one panel
    // idiom — DOM over canvas, like the hover billboard / pinned panels;
    // §18.11 mode-is-a-parameter: this is the unified panel at its most
    // compact, not a new card type). World position: the readout's
    // perimeter coord, else its chunk seat, else a deterministic fan
    // around the bisector node. A lightweight rAF tick reprojects the
    // panels as the camera moves; behind-camera panels hide.

    _upsertReadoutPanels(frame, bisectorMesh) {
        try {
            const T = window.THREE || (typeof THREE !== 'undefined' ? THREE : null);
            if (!T || !this.camera) return;
            if (!this._cgReadoutPanels) this._cgReadoutPanels = new Map();
            let layer = document.getElementById('cg-readout-layer');
            if (!layer) {
                layer = document.createElement('div');
                layer.id = 'cg-readout-layer';
                layer.style.cssText =
                    'position:fixed;left:0;top:0;width:0;height:0;overflow:visible;' +
                    'pointer-events:none;z-index:40;';
                document.body.appendChild(layer);
            }
            const readouts = (frame.readouts || []).filter(r => r && r.chunk_id);
            readouts.forEach((r, idx) => {
                if (!(r.name || r.rendering)) return;  // nothing to panel
                // World position: perimeter coord → chunk seat → bisector fan.
                let world = null;
                if (Array.isArray(r.pos) && r.pos.length >= 3 &&
                    (r.pos[0] || r.pos[1] || r.pos[2])) {
                    world = new T.Vector3(r.pos[0], r.pos[1], r.pos[2]);
                } else if (this.initialNodeData && this.initialNodeData.has(r.chunk_id)) {
                    const init = this.initialNodeData.get(r.chunk_id);
                    if (init && init.position) world = init.position.clone();
                }
                if (!world && bisectorMesh) {
                    // Deterministic fan on the perimeter around the bisector
                    // (§6.6.1) — angle from the readout's slot index.
                    const angle = (idx / Math.max(1, readouts.length)) * Math.PI * 2;
                    const R = 9;
                    world = bisectorMesh.position.clone();
                    world.x += Math.cos(angle) * R;
                    world.y += Math.sin(angle) * R;
                }
                if (!world) return;
                let entry = this._cgReadoutPanels.get(r.chunk_id);
                if (!entry) {
                    const el = document.createElement('div');
                    el.className = 'cg-readout-panel';
                    el.dataset.readoutId = r.chunk_id;
                    el.style.cssText =
                        'position:fixed;max-width:260px;padding:6px 8px;' +
                        'background:rgba(13,17,23,0.92);border:1px solid #3a4150;' +
                        'border-radius:4px;color:#e6edf3;font-family:monospace;' +
                        'font-size:10px;line-height:1.35;pointer-events:none;' +
                        'white-space:pre-wrap;word-break:break-word;';
                    el.innerHTML =
                        '<div class="cg-readout-name" style="color:#9aa3ad;font-size:9px;' +
                        'letter-spacing:0.04em;margin-bottom:3px;"></div>' +
                        '<pre class="cg-readout-tree" style="margin:0;font:inherit;' +
                        'white-space:pre-wrap;word-break:break-word;"></pre>';
                    layer.appendChild(el);
                    entry = { el, world };
                    this._cgReadoutPanels.set(r.chunk_id, entry);
                }
                entry.world = world;
                const nameEl = entry.el.querySelector('.cg-readout-name');
                const treeEl = entry.el.querySelector('.cg-readout-tree');
                if (nameEl) nameEl.textContent = r.name || r.chunk_id;
                if (treeEl) treeEl.textContent = r.rendering || '';
                entry.el.style.display = '';
            });
            this._startReadoutPanelTick();
        } catch (e) {
            console.warn('[scanner] readout panel upsert failed:', e && e.message);
        }
    },

    _startReadoutPanelTick() {
        if (this._cgReadoutTick) return;
        const tick = () => {
            if (!this._cgReadoutPanels || this._cgReadoutPanels.size === 0) {
                this._cgReadoutTick = null;
                return;
            }
            try {
                const panel = document.getElementById('projector-panel');
                const rect = panel ? panel.getBoundingClientRect()
                    : { left: 0, top: 0, width: window.innerWidth, height: window.innerHeight };
                this._cgReadoutPanels.forEach((entry) => {
                    if (!entry.world || !this.camera) return;
                    const v = entry.world.clone();
                    v.project(this.camera);
                    const behind = v.z > 1 || v.z < -1;
                    if (behind) { entry.el.style.display = 'none'; return; }
                    entry.el.style.display = '';
                    const x = (v.x * 0.5 + 0.5) * rect.width + rect.left;
                    const y = -(v.y * 0.5 - 0.5) * rect.height + rect.top;
                    entry.el.style.left = `${Math.round(x + 12)}px`;
                    entry.el.style.top  = `${Math.round(y - 10)}px`;
                });
            } catch (_) { /* keep ticking */ }
            this._cgReadoutTick = requestAnimationFrame(tick);
        };
        this._cgReadoutTick = requestAnimationFrame(tick);
    },

    _clearReadoutPanels() {
        try {
            if (this._cgReadoutTick) cancelAnimationFrame(this._cgReadoutTick);
        } catch (_) {}
        this._cgReadoutTick = null;
        try {
            const layer = document.getElementById('cg-readout-layer');
            if (layer && layer.parentNode) layer.parentNode.removeChild(layer);
        } catch (_) {}
        this._cgReadoutPanels = null;
    },

    /**
     * Apply a {chunk_id: [x,y,z,h,s,v]} mapping (§6.1/§1.8 6D contract;
     * also accepts legacy [x,y,z]) by writing canonical positions AND
     * canonical content-HSV into initialNodeData. The rAF loop in
     * animation.js reads ``init.position`` for placement and
     * ``init.umapHsl`` ({h,s,l} from coords[3:6]) as the base hue it
     * rotates each frame by the camera-azimuth phase (§707), giving
     * semantically-related chunks cohesive, content-derived colour that
     * rotates in lockstep with the projector orbit. ``init.umapColor`` is
     * kept as a derived (un-rotated) RGB cache for legacy readers only.
     *
     * Each backend chunk_id can map to multiple instance_ids in the
     * scene (anchor fusion produces one chunk with N member xpaths).
     * We move every instance_id keyed to that chunk_id to the same
     * UMAP coord plus a tiny per-instance jitter so they don't stack
     * exactly on top of each other; every instance shares the chunk's HSV.
     */
    _applyUmapCoords(coords) {
        if (!coords || !this.initialNodeData) return 0;
        let moved = 0;
        const T = window.THREE || THREE;
        // Accumulators for per-doc chunk centroids so doc hubs can be
        // moved into the SAME frame as their UMAP-projected chunks at
        // the end of this function. Without this step the hubs stay at
        // their hash-bootstrap (recentered) positions while chunks land
        // in the SVD-centred cube — two disjoint frames that visually
        // detach the cluster from its hub. Keyed by doc_id, each entry
        // accumulates {x, y, z, n} so we can divide for the centroid.
        const docCentroids = new Map();
        const docInitsByChunk = (instanceId) => {
            const d = this.dataMap.get(instanceId);
            return d && d.doc_id ? d.doc_id : null;
        };
        // (The old tanh `norm` helper derived chunk colour from xyz position;
        // it is gone — colour now comes from the UMAP HSV channels coords[3:6]
        // via this.constructor.umap6ToHsl, written to init.umapHsl below.)
        // UMAP-locked node ids: any instance whose position is set
        // from these coords gets locked so the Fibonacci relayout
        // (instance_manager._relayoutSphericalGrowth) leaves it alone
        // on subsequent doc-adds. Persists previous UMAP arrangements
        // across new scans, as the user requested.
        if (!this._umapLocked) this._umapLocked = new Set();
        // ── Two-stage UMAP post-processing ──
        //
        //  Stage A — Fit-to-sphere
        //    The backend returns coords already centred at origin
        //    and scaled to roughly a 40-unit cube, but the actual
        //    extent depends on the SVD principal components and can
        //    blow past the camera frustum on dense scans. We rescale
        //    uniformly so the FARTHEST point sits on a target sphere
        //    of radius TARGET_RADIUS (25 units = comfortably within
        //    the default camera frustum). Smaller scans stay small;
        //    larger scans get clipped down.
        //
        //  Stage B — Collider repulsion
        //    Treats every billboard as a sphere of radius
        //    NODE_COLLIDER_RADIUS. Runs a few iterations of pairwise
        //    push-apart so no two billboards overlap. A uniform
        //    Lagrange-multiplier-style enforcement: every pair
        //    separated by less than 2·R + safety gap gets pushed
        //    apart equally. Idempotent at convergence.
        //
        const TARGET_RADIUS = 25;
        const NODE_COLLIDER_RADIUS = 0.9;   // half the billboard diameter
        // §9.7 / USER_REQUIREMENTS_VERBATIM B.3: user reported "spacing
        // too close together." Bumped 1.4 → 2.2 so the centre-to-centre
        // minimum 2·R·safety = 2·0.9·2.2 ≈ 3.96 units, leaving ~2.16
        // units of clear gap between 0.9-radius billboards. Mirrors the
        // backend constant DEFAULT_COLLIDER_SAFETY in layout_service.py.
        const COLLIDER_SAFETY = 2.2;
        const MIN_PAIR_DIST = 2 * NODE_COLLIDER_RADIUS * COLLIDER_SAFETY;

        // Build a coord array we can scale + repel in-place.
        const coordList = [];   // [{cid, xyz: [x,y,z]}]
        for (const cid in coords) {
            const xyz = coords[cid];
            // §6.1/§1.8 — the canonical `umap_canonical` frame carries
            // 6-vectors [x,y,z,h,s,v], and the legacy /api/recompute_umap path
            // returns 6 too. Accept length >= 3 and use ONLY [0:3] for
            // position here; the HSV channels [3:6] are read separately into
            // init.umapHsl below. The prior `!== 3` guard rejected every
            // 6-vector, silently dropping ALL canonical positions AND colour —
            // chunks were stranded at their hash-bootstrap layout.
            if (!xyz || xyz.length < 3) continue;
            // Defensive: skip non-finite coords (would NaN-propagate).
            if (!Number.isFinite(xyz[0]) || !Number.isFinite(xyz[1]) || !Number.isFinite(xyz[2])) continue;
            coordList.push({ cid, xyz: [xyz[0], xyz[1], xyz[2]] });
        }

        // Stage A — fit to TARGET_RADIUS.
        let maxR = 0;
        for (const e of coordList) {
            const r = Math.sqrt(e.xyz[0]*e.xyz[0] + e.xyz[1]*e.xyz[1] + e.xyz[2]*e.xyz[2]);
            if (r > maxR) maxR = r;
        }
        if (maxR > TARGET_RADIUS && maxR > 0) {
            const k = TARGET_RADIUS / maxR;
            for (const e of coordList) {
                e.xyz[0] *= k; e.xyz[1] *= k; e.xyz[2] *= k;
            }
            console.debug(`[UMAP] fit-to-sphere: maxR ${maxR.toFixed(2)} → ${TARGET_RADIUS} (scale ${k.toFixed(3)})`);
        }

        // Stage B — uniform collider repulsion (small N²; 5 iters).
        // For each pair below MIN_PAIR_DIST, push them apart along
        // their connecting vector until they sit exactly at
        // MIN_PAIR_DIST. The Lagrange multiplier is implicit: every
        // pair gets the same minimum separation, so the radius
        // enforcement is uniform across all nodes (URL-independent).
        const REPULSE_ITERS = 5;
        for (let iter = 0; iter < REPULSE_ITERS; iter++) {
            let moved = 0;
            for (let a = 0; a < coordList.length; a++) {
                const pa = coordList[a].xyz;
                for (let b = a + 1; b < coordList.length; b++) {
                    const pb = coordList[b].xyz;
                    const dx = pb[0] - pa[0];
                    const dy = pb[1] - pa[1];
                    const dz = pb[2] - pa[2];
                    const d2 = dx*dx + dy*dy + dz*dz;
                    if (d2 >= MIN_PAIR_DIST * MIN_PAIR_DIST) continue;
                    const d = Math.sqrt(d2);
                    if (d < 1e-9) {
                        // Degenerate overlap — pick an arbitrary axis.
                        pa[0] -= MIN_PAIR_DIST * 0.5;
                        pb[0] += MIN_PAIR_DIST * 0.5;
                        moved++;
                        continue;
                    }
                    const push = (MIN_PAIR_DIST - d) * 0.5;
                    const ux = dx / d, uy = dy / d, uz = dz / d;
                    pa[0] -= ux * push;  pa[1] -= uy * push;  pa[2] -= uz * push;
                    pb[0] += ux * push;  pb[1] += uy * push;  pb[2] += uz * push;
                    moved++;
                }
            }
            if (moved === 0) break;
        }

        // Re-pack repelled coords back into a Map indexed by chunkId.
        const finalCoords = new Map();
        for (const e of coordList) finalCoords.set(e.cid, e.xyz);

        // ── Per-URL workspace offsetting (Mortegon §2.3/§9.2) ──
        // Group chunks by URL, compute per-URL centroid in UMAP space,
        // then offset each URL's nodes to its independent root position
        // so multiple scans don't overlap at the origin.
        const urlChunks = new Map(); // url → [{chunkId, xyz}]
        for (const chunkId in coords) {
            const repelled = finalCoords.get(chunkId);
            if (!repelled) continue;
            const insts = this._chunkIdToInstances && this._chunkIdToInstances.get(chunkId);
            if (!insts) continue;
            let url = '';
            insts.forEach(iid => {
                const d = this.dataMap.get(iid);
                if (d && d.url) url = d.url;
            });
            if (!urlChunks.has(url)) urlChunks.set(url, []);
            urlChunks.get(url).push({ chunkId, xyz: repelled });
        }

        // Compute per-URL centroid and determine offsets
        const urlOffsets = new Map(); // url → {x, y, z}
        if (typeof this._placeNewUrlWorkspace === 'function') {
            urlChunks.forEach((chunks, url) => {
                let cx = 0, cy = 0, cz = 0;
                chunks.forEach(c => { cx += c.xyz[0]; cy += c.xyz[1]; cz += c.xyz[2]; });
                const n = chunks.length;
                cx /= n; cy /= n; cz /= n;
                // Bounding radius for this URL in UMAP space
                let maxR = 0;
                chunks.forEach(c => {
                    const dx = c.xyz[0] - cx, dy = c.xyz[1] - cy, dz = c.xyz[2] - cz;
                    const r = Math.sqrt(dx*dx + dy*dy + dz*dz);
                    if (r > maxR) maxR = r;
                });
                const rootPos = this._placeNewUrlWorkspace(url, {});
                // Offset = rootPos - umapCentroid (translate UMAP cluster to root)
                urlOffsets.set(url, {
                    x: rootPos.x - cx,
                    y: rootPos.y - cy,
                    z: rootPos.z - cz,
                });
                if (this._urlBoundingRadii) this._urlBoundingRadii.set(url, maxR);
            });
        }

        for (const chunkId in coords) {
            const repelled = finalCoords.get(chunkId);
            if (!repelled) continue;
            const insts = this._chunkIdToInstances && this._chunkIdToInstances.get(chunkId);
            if (!insts) continue;

            // Determine URL for offset
            let url = '';
            insts.forEach(iid => {
                const d = this.dataMap.get(iid);
                if (d && d.url) url = d.url;
            });
            const offset = urlOffsets.get(url) || { x: 0, y: 0, z: 0 };
            const sx = repelled[0] + offset.x;
            const sy = repelled[1] + offset.y;
            const sz = repelled[2] + offset.z;

            // §6.1/§707 — canonical CONTENT colour comes from the UMAP HSV
            // channels coords[3:6] (NOT from the xyz position). umap6ToHsl maps
            // them to a display-ready {h,s,l}; the animate loop rotates the hue
            // by the camera-azimuth phase each frame. Read the HSV from the
            // ORIGINAL frame coord (the repelled/offset path only moves
            // position). Previously colour was derived from the position via
            // norm(), discarding the HSV channels the backend emits (§431).
            const _Cp = this.constructor;
            const _hsl = (_Cp && typeof _Cp.umap6ToHsl === 'function')
                ? _Cp.umap6ToHsl(coords[chunkId])
                : { h: 0.6, s: 0.6, l: 0.5 };
            const _crgb = (_Cp && typeof _Cp.hslToRgb === 'function')
                ? _Cp.hslToRgb(_hsl.h, _hsl.s, _hsl.l)
                : null;
            let i = 0;
            insts.forEach((instanceId) => {
                const init = this.initialNodeData.get(instanceId);
                if (!init) return;
                const golden = 2.39996;
                const r  = 0.4 * Math.sqrt(i + 0.5);
                const a  = i * golden;
                const dx = r * Math.cos(a);
                const dy = r * Math.sin(a);
                init.position.set(sx + dx, sy + dy, sz);
                // Canonical content-HSV — the per-frame hue rotation reads this.
                init.umapHsl = { h: _hsl.h, s: _hsl.s, l: _hsl.l };
                // Keep umapColor as a derived (un-rotated) RGB cache for any
                // legacy reader; the hue phase is applied in the animate loop.
                if (_crgb) {
                    if (init.umapColor && typeof init.umapColor.set === 'function') {
                        init.umapColor.set(_crgb[0], _crgb[1], _crgb[2]);
                    } else {
                        init.umapColor = new T.Vector3(_crgb[0], _crgb[1], _crgb[2]);
                    }
                }
                this._umapLocked.add(instanceId);
                const docId = docInitsByChunk(instanceId);
                if (docId) {
                    let acc = docCentroids.get(docId);
                    if (!acc) { acc = { x: 0, y: 0, z: 0, n: 0 }; docCentroids.set(docId, acc); }
                    acc.x += init.position.x;
                    acc.y += init.position.y;
                    acc.z += init.position.z;
                    acc.n += 1;
                }
                moved++;
                i++;
            });
        }
        // ── Unify the frame ───────────────────────────────────────
        // Move every doc hub to the centroid of its UMAP'd chunks so
        // hubs and chunks live in one coordinate system. Then reset
        // _sceneShift to (0,0,0): the UMAP route already centres its
        // output, so the recenter offset accumulated during hash-layout
        // bootstrap no longer applies, and any node arriving AFTER this
        // recompute (e.g. a chunk of a freshly-scanned URL) should be
        // stored in the same SVD frame as everything else. Without this
        // reset, post-UMAP arrivals would land at hash_position +
        // (old _sceneShift), which is offset from the UMAP cluster.
        // Early bail: if UMAP didn't actually move any node (e.g. the
        // backend returned `coords` whose chunk_ids don't match the
        // frontend's _chunkIdToInstances, or the SVD was skipped due
        // to a too-small TF matrix), leave the entire scene untouched.
        // Previously we still zeroed _sceneShift here, which detached
        // the hash-based recenter offset from the existing layout and
        // visually blanked the scene from the user's viewpoint.
        if (moved === 0) {
            console.debug('[UMAP] no chunks matched — spherical layout retained');
            return 0;
        }
        let hubsMoved = 0;
        docCentroids.forEach((acc, docId) => {
            if (!acc.n) return;
            const hubInit = this.initialNodeData.get(docId);
            if (!hubInit) return;
            hubInit.position.set(acc.x / acc.n, acc.y / acc.n, acc.z / acc.n);
            // Lock the hub too so the next Fibonacci relayout
            // doesn't shove it back onto the spherical shell.
            this._umapLocked.add(docId);
            hubsMoved++;
        });
        // Safe to zero now — `moved > 0` means the SVD frame is the
        // authoritative one for every UMAP'd chunk, and any later
        // `_addNodeInstance` should land in that same frame.
        if (typeof this._sceneShift !== 'undefined' && this._sceneShift) {
            this._sceneShift.set(0, 0, 0);
        }
        console.debug(`[UMAP] applied coords → chunks_moved=${moved} hubs_moved=${hubsMoved} (frame: SVD-centred, scene_shift=0)`);
        // Activate force-directed layout along root-rays (Mortegon §2.2).
        // This computes ray data for all UMAP'd nodes and enables the
        // per-frame force loop that keeps nodes collision-free along their
        // radial rays from root URL positions.
        if (typeof this._activateForceLayout === 'function') {
            try { this._activateForceLayout(); }
            catch (e) { console.warn('[UMAP] force layout activation failed:', e && e.message); }
        }
        // Camera tween to the most recent URL's root position
        // (Mortegon §3.2). If the user hasn't orbited manually, fly
        // the camera to the newest workspace at a comfortable distance.
        if (!this._userHasInteracted && this.controls && this._urlRootPositions) {
            // Find the URL with the most recently placed root (last in map)
            let newestUrl = null;
            this._urlRootPositions.forEach((_, url) => { newestUrl = url; });
            const rootPos = newestUrl && this._urlRootPositions.get(newestUrl);
            const boundR = (newestUrl && this._urlBoundingRadii && this._urlBoundingRadii.get(newestUrl)) || 15;
            if (rootPos) {
                const camDist = boundR * 1.8;
                const target = rootPos.clone();
                this.controls.target.copy(target);
                this.camera.position.set(
                    target.x, target.y + camDist * 0.3, target.z + camDist
                );
                this.controls.update();
            }
        } else if (!this._userHasInteracted && typeof this.frameAllInstances === 'function') {
            this.frameAllInstances({ duration: 0.6 });
        }
        return moved;
    },
};
