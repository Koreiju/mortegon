/**
 * workflow_client.js
 * Authoritative frontend HTTP and WebSocket client for Web Fiber Haptics.
 * Handles idempotency keys, structured error envelopes, and resilient connections (§14.10).
 */

class WorkflowError extends Error {
    constructor(errorObj) {
        super(errorObj.message);
        this.name = 'WorkflowError';
        this.code = errorObj.code;
        this.retryable = errorObj.retryable;
        this.retryAfterMs = errorObj.retry_after_ms;
        this.context = errorObj.context || {};
    }
}

class ResilientWebSocket {
    constructor(url, options = {}) {
        this.baseUrl = url;
        this.onFrame = options.onFrame || (() => {});
        this.onStateChange = options.onStateChange || (() => {});
        this.maxRetries = options.maxRetries ?? 10;
        this.baseDelayMs = options.baseDelayMs ?? 500;
        
        this.attempt = 0;
        this.lastSeq = 0;
        this.ws = null;
        this.isClosed = false;
    }

    connect() {
        this.isClosed = false;
        let url = this.baseUrl;
        if (this.lastSeq > 0) {
            url += (url.includes('?') ? '&' : '?') + `resume=${this.lastSeq}`;
        }
        
        this.onStateChange('connecting');
        this.ws = new WebSocket(url);
        
        this.ws.onopen = () => {
            this.attempt = 0;
            this.onStateChange('connected');
        };
        
        this.ws.onmessage = (event) => {
            try {
                const frame = JSON.parse(event.data);
                if (frame.seq !== undefined) {
                    this.lastSeq = Math.max(this.lastSeq, frame.seq);
                }
                this.onFrame(frame);
            } catch (e) {
                console.error("Failed to parse WS frame", e);
            }
        };
        
        this.ws.onclose = (event) => {
            this.ws = null;
            if (this.isClosed) return;
            
            if (event.code === 4000) { // ws_resume_expired or custom terminal code
                this.onStateChange('permanent_failure');
                return;
            }
            
            this._handleReconnect();
        };
        
        this.ws.onerror = () => {
            // onclose will automatically be called and handle the reconnect
        };
    }
    
    _handleReconnect() {
        if (this.attempt < this.maxRetries) {
            const delay = Math.min(30000, this.baseDelayMs * Math.pow(2, this.attempt));
            this.attempt++;
            this.onStateChange('reconnecting', { delay, attempt: this.attempt });
            setTimeout(() => {
                if (!this.isClosed) this.connect();
            }, delay);
        } else {
            this.onStateChange('permanent_failure');
        }
    }
    
    close() {
        this.isClosed = true;
        if (this.ws) {
            this.ws.close();
        }
        this.onStateChange('closed');
    }
}

class WorkflowClient {
    constructor(baseUrl = '') {
        this.base = baseUrl;
        this._idempotencyCounter = 0;
    }

    _newIdempotencyKey() {
        return `${performance.timeOrigin}-${++this._idempotencyCounter}`;
    }

    async _fetch(path, options = {}) {
        const url = `${this.base}${path}`;
        const res = await fetch(url, options);
        
        if (!res.ok) {
            let errData;
            try {
                errData = await res.json();
            } catch (e) {
                throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            }
            if (errData && errData.error) {
                throw new WorkflowError(errData.error);
            }
            throw new Error(errData.detail || `HTTP ${res.status}`);
        }
        return res.json();
    }

    // --- Snapshot ---
    beginSnapshot(url) {
        return this._fetch(`/api/snapshot?url=${encodeURIComponent(url)}&t=${Date.now()}`);
    }
    
    connectSnapshotStream(wsId, opts) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${this.base}/api/ws/nodes/${wsId}`;
        return new ResilientWebSocket(wsUrl, opts);
    }

    // --- Labels ---
    applyLabel(url, xpath, label, snapshotId, opts = {}) {
        return this._fetch('/api/map/label', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Idempotency-Key': this._newIdempotencyKey()
            },
            body: JSON.stringify({
                url,
                snapshot_id: snapshotId,
                xpath,
                label,
                auto_commute: opts.autoCommute ?? true,
                auto_lca: opts.autoLca ?? true
            })
        });
    }

    editLabel(url, xpath, newLabel, etag) {
        const headers = { 'Content-Type': 'application/json' };
        if (etag) headers['If-Match'] = etag;
        return this._fetch('/api/map/label', {
            method: 'PATCH',
            headers,
            body: JSON.stringify({ url, xpath, new_label: newLabel })
        });
    }

    deleteLabel(url, xpath, cascade = true) {
        return this._fetch(`/api/map/label?url=${encodeURIComponent(url)}&xpath=${encodeURIComponent(xpath)}&cascade=${cascade}`, {
            method: 'DELETE'
        });
    }

    paintLabel(url, snapshotId, label, xpaths, opts = {}) {
        return this._fetch('/api/map/label-batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Idempotency-Key': this._newIdempotencyKey()
            },
            body: JSON.stringify({
                url,
                snapshot_id: snapshotId,
                label,
                xpaths,
                auto_commute: opts.autoCommute ?? true,
                auto_lca: opts.autoLca ?? true
            })
        });
    }

    // --- Selection (Read-Only) ---
    selectStructural(url, xpath) {
        return this._fetch('/api/map/select-structural', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, xpath })
        });
    }

    // --- Datasets ---
    sealDataset(url, snapshotId, opts = {}) {
        return this._fetch('/api/datasets/seal', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Idempotency-Key': this._newIdempotencyKey()
            },
            body: JSON.stringify({
                url,
                snapshot_id: snapshotId,
                split_seed: opts.splitSeed,
                train_pct: opts.trainPct,
                val_pct: opts.valPct
            })
        });
    }
    
    listDatasets(url) {
        return this._fetch(`/api/datasets?url=${encodeURIComponent(url)}`);
    }

    // --- Fit ---
    beginAutoFit(url, snapshotId, datasetId, pinnedAlgos = []) {
        return this._fetch('/api/analytics/auto-fit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url,
                snapshot_id: snapshotId,
                dataset_id: datasetId,
                pinned_algos: pinnedAlgos
            })
        });
    }

    connectFitStream(runId, opts) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${this.base}/api/ws/auto-fit/${runId}`;
        return new ResilientWebSocket(wsUrl, opts);
    }

    cancelFit(runId) {
        return this._fetch(`/api/analytics/run/${runId}`, { method: 'DELETE' });
    }

    // --- Sidebar / Node Panel ---
    getSidebar(url, runId = null) {
        let reqUrl = `/api/analytics/sidebar?url=${encodeURIComponent(url)}`;
        if (runId) reqUrl += `&run_id=${encodeURIComponent(runId)}`;
        return this._fetch(reqUrl);
    }

    getNode(url, xpath, runId = null) {
        let reqUrl = `/api/analytics/node?url=${encodeURIComponent(url)}&xpath=${encodeURIComponent(xpath)}`;
        if (runId) reqUrl += `&run_id=${encodeURIComponent(runId)}`;
        return this._fetch(reqUrl);
    }

    pinAlgorithms(url, runId, algoIds) {
        return this._fetch('/api/analytics/sidebar/pin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, run_id: runId, algo_ids: algoIds })
        });
    }

    // --- Runs ---
    listRuns(url) {
        return this._fetch(`/api/runs?url=${encodeURIComponent(url)}`);
    }

    getRun(runId) {
        return this._fetch(`/api/runs/${runId}`);
    }

    compareRuns(url, runIds, notes = '') {
        return this._fetch('/api/runs/compare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, run_ids: runIds, notes })
        });
    }

    // --- Reconcile ---
    reconcile(url) {
        return this._fetch(`/api/session/reconcile?url=${encodeURIComponent(url)}`);
    }

    // --- Legacy / Projection Integration ---
    getNodes(snapshotId = null, limit = 5000) {
        let url = `/api/nodes?t=${Date.now()}`;
        if (snapshotId) url += `&snapshot_id=${encodeURIComponent(snapshotId)}`;
        url += `&limit=${limit}`;
        return this._fetch(url);
    }

    getNodeDetailsLegacy(nodeId) {
        return this._fetch(`/api/details/${encodeURIComponent(nodeId)}`);
    }

    getMapDetail(url, xpath, snapshotId = null) {
        let reqUrl = `/api/map/detail?url=${encodeURIComponent(url)}&xpath=${encodeURIComponent(xpath)}`;
        if (snapshotId) reqUrl += `&snapshot_id=${encodeURIComponent(snapshotId)}`;
        return this._fetch(reqUrl);
    }

    updateNode(id, status, tags) {
        const body = { id };
        if (status !== undefined) body.status = status;
        if (tags !== undefined) body.tags = tags;
        return this._fetch('/api/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
    }

    getLabels(url) {
        return this._fetch(`/api/map/labels?url=${encodeURIComponent(url)}`);
    }

    // --- DOM Text Search ---
    searchDomText(query, url = '', snapshotId = null, limit = 50) {
        return this._fetch('/api/search/dom-text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query,
                url,
                snapshot_id: snapshotId,
                limit
            })
        });
    }

    // --- LCA Subtree ---
    getLcaSubtree(url, label, snapshotId = null) {
        let reqUrl = `/api/map/lca-subtree?url=${encodeURIComponent(url)}&label=${encodeURIComponent(label)}`;
        if (snapshotId) reqUrl += `&snapshot_id=${encodeURIComponent(snapshotId)}`;
        return this._fetch(reqUrl);
    }

    // --- Commutation Matches ---
    getCommutationMatches(url, xpath, snapshotId = null) {
        return this._fetch('/api/map/commutation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url,
                xpath,
                snapshot_id: snapshotId
            })
        });
    }

    // --- Content Chunks ---
    getChunks(snapshotId) {
        return this._fetch(`/api/map/snapshot/${encodeURIComponent(snapshotId)}/chunks`);
    }

    // --- Restore persisted snapshots ---
    restoreSnapshots() {
        return this._fetch(`/api/map/restore?t=${Date.now()}`);
    }

    setChunkLabel(chunkId, label, snapshotId = null) {
        return this._fetch('/api/map/chunks/label', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chunk_id: chunkId,
                label: label,
                snapshot_id: snapshotId,
            })
        });
    }

    // --- Subgroup Commutation (LCA-aware, pattern-set isomorphism) ---
    getSubgroupCommutationMatches(url, xpath, snapshotId = null) {
        return this._fetch('/api/map/subgroup-commutation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url,
                xpath,
                snapshot_id: snapshotId
            })
        });
    }
}