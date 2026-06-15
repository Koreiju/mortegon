/**
 * telemetry.js — Frontend → backend MutationObserver bridge.
 *
 * Watches the rendered surfaces the CLI cares about (concept-card
 * list in the 2D editor, pinned-panel container, apparition halo
 * overlays, 3D scene root) and POSTs structured mutation reports
 * to ``/api/ui/telemetry`` whenever the visible DOM changes. The
 * CLI's ``ui-telemetry`` action drains the resulting buffer so
 * Claude / a human operator sees what the user is seeing without
 * screen-scraping or browser automation.
 *
 * Design notes:
 *   • Each observer is debounced (200 ms) so a rapid burst of
 *     additions (e.g. a workspace-open bootstrap creating 50 cards)
 *     collapses into one report.
 *   • POSTs are fire-and-forget — failures are silently dropped.
 *     The backend ring buffer is best-effort; missing one report
 *     between two drains is acceptable.
 *   • Workspace_id is read from this._conceptWorkspaceId (set by
 *     concept_graph.js); falls back to "" → "_default".
 *
 * Add new tracked surfaces by:
 *   1. Find the host DOM container (by id or selector).
 *   2. Call this._installTelemetryObserver(host, kind) in
 *      _telemetryInit (below).
 *   3. The observer fires _telemetryPost({kind, count, target_id})
 *      automatically on subtree mutations.
 */

export const TelemetryMixin = {

    _telemetryInit() {
        // Idempotent — bootstrap can fire multiple times during page
        // life (e.g. workspace reopen). Don't double-wire observers.
        if (this._telemetryWired) return;
        this._telemetryWired = true;
        this._telemetryDebounce = new Map();   // kind → setTimeout id
        this._telemetryLastCount = new Map();  // kind → last reported count
        // Wait for DOM-content to ensure the host containers exist.
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded',
                () => this._telemetryWireAll(), { once: true });
        } else {
            // Small delay so the rest of the projector's startup
            // wiring finishes before our observers fire their first
            // childList-snapshot summary.
            setTimeout(() => this._telemetryWireAll(), 300);
        }
    },

    _telemetryWireAll() {
        // The four tracked surfaces — add more here when new UI
        // areas need CLI visibility.
        const wireOne = (selector, kind) => {
            const host = document.querySelector(selector);
            if (!host) return;
            this._installTelemetryObserver(host, kind);
            // Send an initial-state report so a fresh CLI drain
            // sees the current count (otherwise it'd only see
            // future deltas).
            this._telemetryPost({
                kind: kind + '/initial',
                count: this._telemetryCountFor(host, kind),
            });
        };
        // 2D editor's concept-card area. concept_graph.js places
        // cards in a known container; #concept-editor in the
        // template, with .concept-card children.
        wireOne('#concept-editor', 'concept-card-list');
        // Pinned billboards anchor under #projector-panel.
        wireOne('#projector-panel', 'pinned-billboards');
        // Apparition halo overlay (created dynamically by
        // _renderApparitionHalo). The observer's wireOne returns
        // null on first call (overlay not present yet); we
        // re-attempt periodically via _telemetryPollHaloOverlay.
        this._telemetryPollHaloOverlay();
        // 3D scene host — Three.js renders into #three-container.
        // We can't observe Three.js geometry directly, but we CAN
        // observe its size-change events from window resizes.
        const sceneHost = document.querySelector('#three-container');
        if (sceneHost) {
            // Observe attribute changes (canvas size, etc.) rather
            // than subtree (Three.js mutates per-frame which would
            // saturate the buffer).
            const obs = new MutationObserver(() => this._telemetryPostDebounced({
                kind: 'three-container-attr',
            }));
            obs.observe(sceneHost, { attributes: true, attributeFilter: ['style', 'class'] });
        }
        console.log('[telemetry] observers wired on 2D editor + billboards + 3D host');
    },

    _telemetryPollHaloOverlay() {
        // The apparition halo overlay is created on first hover; once
        // it exists we attach an observer permanently (it's reused
        // across hovers — only its children change).
        const tryAttach = () => {
            const overlay = document.querySelector('.concept-apparition-halo-overlay');
            if (overlay && !overlay.__telemetryWired) {
                overlay.__telemetryWired = true;
                this._installTelemetryObserver(overlay, 'apparition-halo');
                return true;
            }
            return false;
        };
        if (tryAttach()) return;
        // Poll every 2s for up to 60s; halo is created lazily.
        let attempts = 0;
        const iv = setInterval(() => {
            attempts += 1;
            if (tryAttach() || attempts >= 30) clearInterval(iv);
        }, 2000);
    },

    _installTelemetryObserver(host, kind) {
        if (!host || !window.MutationObserver) return;
        const obs = new MutationObserver((mutations) => {
            // Sum childList add/remove counts so we don't post per-
            // record (a single React-style re-render would otherwise
            // produce 50 reports for one logical change).
            let added = 0, removed = 0;
            for (const m of mutations) {
                if (m.type === 'childList') {
                    added += m.addedNodes ? m.addedNodes.length : 0;
                    removed += m.removedNodes ? m.removedNodes.length : 0;
                }
            }
            if (added === 0 && removed === 0) return;
            // Snapshot the current host child count so the CLI knows
            // the absolute state, not just the delta.
            const count = this._telemetryCountFor(host, kind);
            const lastCount = this._telemetryLastCount.get(kind);
            // Skip if nothing actually changed shape (some Three.js
            // observers fire on style-only mutations).
            if (lastCount === count && added === 0 && removed === 0) return;
            this._telemetryLastCount.set(kind, count);
            this._telemetryPostDebounced({
                kind,
                count,
                extra: { added, removed },
            });
        });
        obs.observe(host, { childList: true, subtree: false });
    },

    _telemetryCountFor(host, kind) {
        // For ``concept-card-list`` we want a count of .concept-card
        // elements, not raw children (the host may have other UI
        // chrome mixed in). For other kinds, host.children.length is
        // the right number.
        if (kind === 'concept-card-list') {
            return host.querySelectorAll('.concept-card').length;
        }
        if (kind === 'pinned-billboards') {
            return host.querySelectorAll('.pinned-panel').length;
        }
        if (kind === 'apparition-halo') {
            return host.querySelectorAll('.concept-apparition-phantom').length;
        }
        return host.children ? host.children.length : 0;
    },

    _telemetryPostDebounced(payload) {
        const key = payload.kind;
        const prior = this._telemetryDebounce.get(key);
        if (prior) clearTimeout(prior);
        const handle = setTimeout(() => {
            this._telemetryDebounce.delete(key);
            this._telemetryPost(payload);
        }, 200);
        this._telemetryDebounce.set(key, handle);
    },

    async _telemetryPost(payload) {
        // workspace_id falls back to "" → "_default" server-side.
        const ws = this._conceptWorkspaceId || '';
        try {
            await fetch('/api/ui/telemetry', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workspace_id: ws,
                    kind:         payload.kind,
                    target_id:    payload.target_id || null,
                    count:        (typeof payload.count === 'number') ? payload.count : null,
                    extra:        payload.extra || {},
                }),
            });
        } catch (_) {
            // Fire-and-forget — backend buffer is best-effort.
        }
    },

    /**
     * Manual telemetry hook — gestures can call this directly when
     * they want to emit a labelled event the MutationObservers
     * wouldn't catch (e.g. "user clicked apparition phantom X"
     * doesn't change the visible DOM but is worth recording).
     *
     * Use sparingly — observer-driven reports are the bulk channel.
     */
    telemetryEmit(kind, opts = {}) {
        this._telemetryPost({
            kind,
            target_id: opts.target_id || null,
            count:     (typeof opts.count === 'number') ? opts.count : null,
            extra:     opts.extra || {},
        });
    },

};
