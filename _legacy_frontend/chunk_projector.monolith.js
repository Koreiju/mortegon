/* chunk_projector.js -- UMAP-based 3D projector over ``ChunkInstance`` rows.
 * Adapted for InstancedMesh, frustum culling, WS-first polling.
 */

console.log("[ChunkProjector] Script loaded");

class ChunkProjector {
    // Media extension sets unchanged
    static IMAGE_EXTS = new Set([
        '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.avif',
        '.bmp', '.tiff', '.tif', '.apng', '.jfif', '.pjpeg', '.pjp',
    ]);
    static VIDEO_EXTS = new Set([
        '.mp4', '.webm', '.ogg', '.ogv', '.mov', '.avi', '.mkv', '.flv',
        '.wmv', '.m4v', '.3gp', '.ts', '.m3u8',
    ]);
    static AUDIO_EXTS = new Set([
        '.mp3', '.wav', '.flac', '.ogg', '.oga', '.aac', '.wma', '.opus',
        '.m4a', '.mid', '.midi',
    ]);

    static DOC_RADIUS = 8.0;
    static INST_RADIUS = 15.0;
    static _layoutCache = new Map();

    static _hashUnit(s, salt) {
        let h = 0x811c9dc5;
        const a = (salt || '') + ':';
        for (let i = 0; i < a.length; i++) {
            h ^= a.charCodeAt(i);
            h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
        }
        for (let i = 0; i < s.length; i++) {
            h ^= s.charCodeAt(i);
            h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
        }
        return (h >>> 0) / 0x1_0000_0000;
    }

    static _hslToRgb(h, s, l) {
        if (s === 0) return [l, l, l];
        const q = l >= 0.5 ? (l + s - l * s) : (l * (1 + s));
        const p = 2 * l - q;
        const hue = (t) => {
            if (t < 0) t += 1;
            if (t > 1) t -= 1;
            if (t < 1 / 6) return p + (q - p) * 6 * t;
            if (t < 1 / 2) return q;
            if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
            return p;
        };
        return [hue(h + 1 / 3), hue(h), hue(h - 1 / 3)];
    }

    static layOutNode(node) {
        if (!node || !node.id) return node;
        const has = (k) => typeof node[k] === 'number' && Number.isFinite(node[k]);
        if (has('x') && has('y') && has('z') && has('r') && has('g') && has('b')) return node;
        let cached = ChunkProjector._layoutCache.get(node.id);
        if (cached) {
            node.x = cached[0]; node.y = cached[1]; node.z = cached[2];
            node.r = cached[3]; node.g = cached[4]; node.b = cached[5];
            return node;
        }
        const isDoc = !!node.is_document;
        const radius = isDoc ? ChunkProjector.DOC_RADIUS : ChunkProjector.INST_RADIUS;
        const u1 = ChunkProjector._hashUnit(node.id, 'theta');
        const u2 = ChunkProjector._hashUnit(node.id, 'phi');
        const theta = 2 * Math.PI * u1;
        const cosPhi = 2 * u2 - 1;
        const sinPhi = Math.sqrt(Math.max(0, 1 - cosPhi * cosPhi));
        node.x = radius * Math.cos(theta) * sinPhi;
        node.y = radius * Math.sin(theta) * sinPhi;
        node.z = radius * cosPhi;
        const hue = ChunkProjector._hashUnit(node.id, 'hue');
        const light = isDoc ? 0.62 : 0.55;
        const [r, g, b] = ChunkProjector._hslToRgb(hue, 0.65, light);
        node.r = r; node.g = g; node.b = b;
        ChunkProjector._layoutCache.set(node.id, [node.x, node.y, node.z, node.r, node.g, node.b]);
        if (ChunkProjector._layoutCache.size > 100000) ChunkProjector._layoutCache.clear();
        return node;
    }

    constructor() {
        console.log("[ChunkProjector] Constructor");
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.clock = new THREE.Clock();
        this.animationTime = 0;

        // InstancedMesh for documents and instances
        this.docInstancedMesh = null;
        this.instInstancedMesh = null;

        // Maps nodeId -> { isDoc, index, originalColor (THREE.Color) }
        this.nodeInstanceMap = new Map();
        this._freeDocIndices = [];
        this._freeInstIndices = [];
        this._docInstanceIdToNode = [];
        this._instInstanceIdToNode = [];

        // Data -- id is ChunkInstance.instance_id.
        this.dataMap = new Map();          // id -> raw projector node
        this.initialNodeData = new Map();  // id -> { position, umapColor }
        this.selectedId = null;
        this.hoveredId = null;
        this.searchResults = null;         // id -> score during NL search
        this.lastSearchPayload = null;     // last /api/chunk_search response

        // Collapse state
        this.docCollapseTarget = new Map(); // doc_id -> target T (0 or 1)
        this.docCollapseState = new Map();  // doc_id -> current T (0.0 to 1.0)
        this.edges = [];
        this.linesMesh = null;             // LineSegments for edges
        this.detailsFetchQueue = new Set();
        this._imageSprites = new Map();     // nodeId -> sprite (primary)
        this._extraSprites = new Map();     // nodeId -> [sprite, ...]
        this._imageTextureCache = new Map();
        this._imageProxyFailures = new Set();

        // Pinned detached billboards (multi-panel UX).
        this._pinnedPanels = new Map(); // id -> { panel, data, minimized }
        this._panelHoverCount = 0;

        // File Tree & Workspaces State
        this.workspaces = this.loadWorkspaces();
        if (this.workspaces.length === 0) this.createWorkspace('Default Workspace');
        this.activeWorkspaceId = this.workspaces[0].id;
        this.domainTree = new Map();       // domain -> Set<url>
        this.expandedFolders = new Set(['ft-domains', `ft-ws-${this.activeWorkspaceId}`]);
        this.wsEditTimers = new Map();
        this.wsEditOriginals = new Map();

        // Drag detection.
        this.isDragging = false;
        this.mouseDownPos = { x: 0, y: 0 };

        // Background video plane (frustum-attached).
        this.backgroundMesh = null;
        this.backgroundDistance = 500;

        // Snow-globe + spectral-color rotation constants
        this.spatialVelocity = { x: 0.05, y: 0.1, z: 0.02 };
        this.colorVelocity = { x: 0.4, y: 0.6, z: 0.3 };

        this.initMaroniteTheme();
        this.init();
        this.initLoadingBar();
        this.loadNodes();
        this.initSidebar();
        this.initSnapshot();
        this.initFileTree();
        this.initRainbowObserver();
        this.initBillboardArrow();
    }

    // ------------------------------------------------------------------
    // Theme, loading bar, etc. (compressed)
    // ------------------------------------------------------------------
    initMaroniteTheme() {
        const style = document.createElement('style');
        style.innerHTML = `
            @font-face { font-family: 'VHS'; src: url('/static/vhs.ttf') format('truetype'); }
            @keyframes rainbow-text { 0% { color: #ff5555; } 16% { color: #ffff55; } 33% { color: #55ff55; } 50% { color: #55ffff; } 66% { color: #5555ff; } 83% { color: #ff55ff; } 100% { color: #ff5555; } }
            @keyframes rainbow-bg { 0% { background-color: #ff5555; } 16% { background-color: #ffff55; } 33% { background-color: #55ff55; } 50% { background-color: #55ffff; } 66% { background-color: #5555ff; } 83% { background-color: #ff55ff; } 100% { background-color: #ff5555; } }
            :root {
                --surface-base: #000000; --surface-elevated: #111111; --surface-hover: #000080;
                --border-light: #c0c0c0; --text-primary: #c0c0c0; --text-secondary: #808080;
                --text-muted: #666666; --accent-pastel: #0000ff; --accent-pastel-green: #00ff00;
                --radius-md: 0px; --radius-sm: 0px; --shadow-soft: none;
            }
            body, input, button, .sidebar, .panel, #history-container, #results-container, #billboard, #wfh-loader-box, .empty-state, .bucket-heading {
                font-family: 'VHS', 'VCR OSD Mono', 'Courier New', monospace !important;
                text-transform: uppercase !important; letter-spacing: 1px !important;
                text-shadow: none !important; -webkit-text-stroke: 0 !important;
            }
            *, body, input, button, a, .instance-score, .page-score, .url-bucket-count, .instance-xpath, .ft-url-label, .instance-text, .billboard-header, #billboard-title, #billboard pre, #billboard code {
                animation: rainbow-text 4s linear infinite !important;
            }
            #wfh-loader-bar { animation: rainbow-bg 4s linear infinite !important; }
            .sidebar, .panel, .panel-left, .panel-right, #left-panel, #right-panel, .side-panel, #history-container, #results-container, #billboard, #wfh-loader-box, #rs-latch, #ft-latch {
                background: var(--surface-base) !important; border: 3px ridge var(--border-light) !important;
                border-radius: var(--radius-md) !important; box-shadow: var(--shadow-soft) !important; box-sizing: border-box !important;
            }
            .sidebar #history-container, .sidebar #results-container { border: none !important; box-shadow: none !important; animation: none !important; }
            #rs-latch { border-right: none !important; border-top-right-radius: 0 !important; border-bottom-right-radius: 0 !important; }
            #ft-latch { border-left: none !important; border-top-left-radius: 0 !important; border-bottom-left-radius: 0 !important; }
            .sidebar::after, #billboard::after, #wfh-loader-box::after, body::after, .sidebar::before, #billboard::before, #wfh-loader-box::before, body::before { display: none !important; content: none !important; animation: none !important; background: none !important; }
            .result-card, .instance-row, .page-card, .url-bucket, .bucket-heading, .ft-item, .ft-items, .ft-folder-title, .ft-header-main { background: transparent !important; border-color: var(--border-light) !important; }
            input { background: #000000 !important; border: 2px inset #ffffff !important; border-radius: var(--radius-sm) !important; padding: 6px 10px; box-sizing: border-box; font-family: 'VHS', 'VCR OSD Mono', 'Courier New', monospace !important; }
            input:focus { border-color: var(--accent-pastel) !important; outline: none; }
            button { background: #000000 !important; border: 2px outset #ffffff !important; border-radius: var(--radius-sm) !important; cursor: pointer; font-family: 'VHS', 'VCR OSD Mono', 'Courier New', monospace !important; font-weight: bold; padding: 2px 6px; }
            button:active { border: 2px inset #ffffff !important; }
            #ft-latch, #rs-latch { animation: none !important; }
            .instance-row:hover, .page-card.clickable-card:hover, .url-bucket:hover, .ft-item:hover, .ft-folder-title:hover, button:hover { border-color: var(--border-light) !important; transform: none !important; filter: none !important; animation: rainbow-bg 4s linear infinite !important; }
            #rs-latch:hover, #ft-latch:hover { border-color: var(--border-light) !important; animation: rainbow-bg 4s linear infinite !important; }
            .instance-row:hover *, .page-card.clickable-card:hover *, .url-bucket:hover *, .ft-item:hover *, .ft-folder-title:hover *, button:hover *, #rs-latch:hover *, #ft-latch:hover * { color: #ffffff !important; text-shadow: none !important; animation: none !important; }
            a { text-decoration: underline; }
            .instance-score, .page-score, .url-bucket-count { font-weight: normal; }
            #billboard { padding: 0 !important; overflow: hidden; z-index: 10005 !important; }
            .billboard-header { background: #000000 !important; border-bottom: 2px ridge var(--border-light) !important; padding: 4px 8px; font-family: 'VHS', 'VCR OSD Mono', 'Courier New', monospace !important; font-weight: bold; }
            #billboard-title { font-weight: bold; font-size: 14px; }
            .billboard-content { padding: 15px; }
            #billboard pre, #billboard code { background: #000000 !important; border: 2px inset #888 !important; border-radius: 0 !important; padding: 8px; font-family: 'VHS', 'VCR OSD Mono', 'Courier New', monospace !important; }
        `;
        document.head.appendChild(style);
    }

    initLoadingBar() {
        const barHtml = `
            <div id="wfh-loader-box" style="position: fixed; bottom: 20px; right: 320px; width: 280px; background: var(--surface-base, #242933); border: 1px solid var(--border-light, #434c5e); border-radius: 8px; padding: 12px 15px; z-index: 10000; display: flex; flex-direction: column; transition: opacity 0.3s ease, transform 0.3s ease; opacity: 0; transform: translateY(10px); pointer-events: none; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                <div style="margin-bottom: 8px; font-size: 11px; color: var(--text-primary, #eceff4); font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; display: flex; justify-content: space-between; align-items: center;">
                    <span>System Activity</span>
                    <button onclick="app.hideLoadingProgress()" style="background: none; border: none; color: var(--text-muted, #aeb5c0); cursor: pointer; padding: 0; margin: 0; font-size: 16px; line-height: 1;">&times;</button>
                </div>
                <div style="width: 100%; background: var(--surface-elevated, #2e3440); border-radius: 4px; overflow: hidden; height: 4px; margin-bottom: 8px;">
                    <div id="wfh-loader-bar" style="width: 0%; height: 100%; background: var(--accent-pastel, #88c0d0); transition: width 0.2s ease;"></div>
                </div>
                <div id="wfh-loader-text" style="color: var(--text-secondary, #d8dee9); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%;">Initializing...</div>
            </div>

            <!-- Pipeline stats overlay: live counters for the
                 scan/tfidf/stream worker stages. Driven by the
                 'stats' WS frame the SnapshotPipeline emits every
                 ~400 ms. Hidden until the first stats frame
                 arrives so it doesn't take up screen real-estate
                 between scans. -->
            <div id="wfh-stats-box" style="position: fixed; bottom: 20px; right: 612px; width: 260px; background: var(--surface-base, #242933); border: 1px solid var(--border-light, #434c5e); border-radius: 8px; padding: 12px 15px; z-index: 10000; display: none; flex-direction: column; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-family: 'JetBrains Mono', 'Consolas', monospace;">
                <div style="margin-bottom: 8px; font-size: 11px; color: var(--text-primary, #eceff4); font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; display: flex; justify-content: space-between; align-items: center;">
                    <span><i class="fas fa-microchip"></i> Pipeline</span>
                    <button onclick="document.getElementById('wfh-stats-box').style.display='none'" style="background: none; border: none; color: var(--text-muted, #aeb5c0); cursor: pointer; padding: 0; margin: 0; font-size: 16px; line-height: 1;">&times;</button>
                </div>
                <div id="wfh-stats-rows" style="display: grid; grid-template-columns: 1fr auto; gap: 4px 12px; font-size: 11px; color: var(--text-secondary, #d8dee9);">
                    <span>elapsed</span><span id="wfh-stat-elapsed">0.0s</span>
                    <span>iters / nodes</span><span id="wfh-stat-iters">0 / 0</span>
                    <span>verified deltas</span><span id="wfh-stat-verified">0</span>
                    <span>chunks → tfidf</span><span id="wfh-stat-vec">0 / 0</span>
                    <span>db rows committed</span><span id="wfh-stat-db">0</span>
                    <span>vocab</span><span id="wfh-stat-vocab">0</span>
                    <span>global docs</span><span id="wfh-stat-docs">0</span>
                </div>
            </div>

            <!-- Pipeline log overlay: rolling tail of per-stage profiler
                 lines (TF-IDF vectorize timings, persist timings, scan
                 worker exits). Driven by the 'log' WS frame emitted by
                 SnapshotPipeline. Hidden until the first log line lands
                 so it doesn't reserve screen space between scans. -->
            <div id="wfh-log-box" style="position: fixed; bottom: 20px; right: 884px; width: 320px; max-height: 200px; background: var(--surface-base, #242933); border: 1px solid var(--border-light, #434c5e); border-radius: 8px; padding: 10px 12px; z-index: 10000; display: none; flex-direction: column; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-family: 'JetBrains Mono', 'Consolas', monospace;">
                <div style="margin-bottom: 6px; font-size: 11px; color: var(--text-primary, #eceff4); font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; display: flex; justify-content: space-between; align-items: center;">
                    <span><i class="fas fa-stream"></i> Pipeline Log</span>
                    <button onclick="document.getElementById('wfh-log-box').style.display='none'" style="background: none; border: none; color: var(--text-muted, #aeb5c0); cursor: pointer; padding: 0; margin: 0; font-size: 16px; line-height: 1;">&times;</button>
                </div>
                <div id="wfh-log-rows" style="overflow-y: auto; max-height: 160px; font-size: 10px; color: var(--text-secondary, #d8dee9); line-height: 1.4;"></div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', barHtml);
    }

    /** Append a single log line to the pipeline log overlay.
     *
     *  Frame shape: ``{type: 'log', stage: 'tfidf'|'stream'|'scan',
     *  message: string, ts: float}``. The list is bounded to the most
     *  recent ~100 lines so a long scan can't grow it without bound.
     */
    _appendLogLine(frame) {
        const box = document.getElementById('wfh-log-box');
        const rows = document.getElementById('wfh-log-rows');
        if (!box || !rows) return;
        if (box.style.display === 'none') box.style.display = 'flex';

        const stageColors = {
            tfidf: '#fbbf24',
            stream: '#34d399',
            scan: '#60a5fa',
        };
        const color = stageColors[frame.stage] || '#9ca3af';
        const stage = (frame.stage || '?').toUpperCase().padEnd(6, ' ');
        const msg = (frame.message || '').replace(/[<>]/g, '');
        const ts = frame.ts ? new Date(frame.ts * 1000) : new Date();
        const hh = String(ts.getHours()).padStart(2, '0');
        const mm = String(ts.getMinutes()).padStart(2, '0');
        const ss = String(ts.getSeconds()).padStart(2, '0');

        const row = document.createElement('div');
        row.style.cssText = 'white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 1px 0;';
        row.innerHTML = `<span style="color:#6b7280">${hh}:${mm}:${ss}</span> `
            + `<span style="color:${color}">${stage}</span> ${msg}`;
        rows.appendChild(row);

        // Trim to last 100 entries.
        while (rows.children.length > 100) rows.removeChild(rows.firstChild);
        rows.scrollTop = rows.scrollHeight;
    }

    /** Update the pipeline stats overlay from a 'stats' WS frame.
     *  Called from the WS message handler in triggerScan. */
    _updateStatsOverlay(frame) {
        const box = document.getElementById('wfh-stats-box');
        if (!box) return;
        if (box.style.display === 'none') box.style.display = 'flex';
        const set = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        set('wfh-stat-elapsed', `${frame.elapsed_s ?? 0}s`);
        set('wfh-stat-iters', `${frame.iter_count || 0} / ${frame.nodes_streamed || 0}`);
        set('wfh-stat-verified', String(frame.deltas_verified || 0));
        set('wfh-stat-vec',
            `${frame.chunks_built || 0} / ${frame.chunks_vectorized || 0}`);
        set('wfh-stat-db', String(frame.instances_persisted || 0));
        set('wfh-stat-vocab', String(frame.vocab_size || 0));
        set('wfh-stat-docs', String(frame.doc_count || 0));

        // Pipeline signalled completion — show green badge, auto-hide.
        if (frame.complete) {
            box.style.borderColor = '#34d399';
            const title = box.querySelector('span');
            if (title) title.innerHTML = '<i class="fas fa-check-circle" style="color:#34d399"></i> Pipeline Complete';
            if (this._statsHideTimer) clearTimeout(this._statsHideTimer);
            this._statsHideTimer = setTimeout(() => {
                box.style.display = 'none';
                box.style.borderColor = '';
                if (title) title.innerHTML = '<i class="fas fa-microchip"></i> Pipeline';
            }, 4000);
        }
    }

    setLoadingProgress(text, pct) {
        const box = document.getElementById('wfh-loader-box');
        const bar = document.getElementById('wfh-loader-bar');
        const textEl = document.getElementById('wfh-loader-text');
        if (box && bar && textEl) {
            box.style.opacity = '1';
            box.style.transform = 'translateY(0)';
            box.style.pointerEvents = 'all';
            bar.style.width = pct + '%';
            textEl.textContent = text;
            textEl.title = text;
        }
    }
    hideLoadingProgress() {
        const box = document.getElementById('wfh-loader-box');
        if (box) {
            box.style.opacity = '0';
            box.style.transform = 'translateY(10px)';
            box.style.pointerEvents = 'none';
        }
    }
    initBillboardArrow() {
        let svg = document.getElementById('billboard-arrow-svg');
        if (!svg) {
            svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.id = "billboard-arrow-svg";
            svg.style.cssText = "position:fixed; top:0; left:0; width:100%; height:100%; pointer-events:none; z-index:10004; display:none;";
            const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
            const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
            marker.setAttribute("id", "arrowhead");
            marker.setAttribute("markerWidth", "10");
            marker.setAttribute("markerHeight", "7");
            marker.setAttribute("refX", "9");
            marker.setAttribute("refY", "3.5");
            marker.setAttribute("orient", "auto");
            const polygon = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
            polygon.setAttribute("points", "0 0, 10 3.5, 0 7");
            polygon.setAttribute("fill", "var(--border-light, #c0c0c0)");
            marker.appendChild(polygon);
            defs.appendChild(marker);
            svg.appendChild(defs);
            const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
            line.id = "billboard-arrow-line";
            line.setAttribute("stroke", "var(--border-light, #c0c0c0)");
            line.setAttribute("stroke-width", "2");
            line.setAttribute("stroke-dasharray", "4,4");
            line.setAttribute("marker-end", "url(#arrowhead)");
            svg.appendChild(line);
            document.body.appendChild(svg);
        }
    }
    hideBillboardArrow() {
        const svg = document.getElementById('billboard-arrow-svg');
        if (svg) svg.style.display = 'none';
    }

    // ====================== InstancedMesh helpers ======================
    _createInstancedMeshes(capacity = 10000) {
        const docGeom = new THREE.SphereGeometry(0.35, 16, 16);
        const instGeom = new THREE.SphereGeometry(0.18, 16, 16);
        const material = new THREE.MeshPhongMaterial({
            color: 0xffffff,
            emissive: 0x000000,
            shininess: 30,
        });
        this.docInstancedMesh = new THREE.InstancedMesh(docGeom, material, capacity);
        this.docInstancedMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        this.scene.add(this.docInstancedMesh);

        this.instInstancedMesh = new THREE.InstancedMesh(instGeom, material, capacity);
        this.instInstancedMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        this.scene.add(this.instInstancedMesh);

        this._freeDocIndices = Array.from({ length: capacity }, (_, i) => capacity - 1 - i);
        this._freeInstIndices = Array.from({ length: capacity }, (_, i) => capacity - 1 - i);
        this._docInstanceIdToNode = new Array(capacity).fill(null);
        this._instInstanceIdToNode = new Array(capacity).fill(null);
    }

    _growDocMesh(newCapacity) {
        const old = this.docInstancedMesh;
        const mesh = new THREE.InstancedMesh(old.geometry, old.material, newCapacity);
        mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        for (let i = 0; i < old.count; i++) {
            mesh.setMatrixAt(i, old.getMatrixAt(i));
            if (old.instanceColor) mesh.setColorAt(i, old.getColorAt(i));
        }
        mesh.count = old.count;
        this.scene.remove(old);
        old.dispose();
        this.docInstancedMesh = mesh;
        this.scene.add(mesh);
        for (let i = old.count; i < newCapacity; i++) this._freeDocIndices.push(i);
        this._docInstanceIdToNode.length = newCapacity;
    }

    _growInstMesh(newCapacity) {
        const old = this.instInstancedMesh;
        const mesh = new THREE.InstancedMesh(old.geometry, old.material, newCapacity);
        mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        for (let i = 0; i < old.count; i++) {
            mesh.setMatrixAt(i, old.getMatrixAt(i));
            if (old.instanceColor) mesh.setColorAt(i, old.getColorAt(i));
        }
        mesh.count = old.count;
        this.scene.remove(old);
        old.dispose();
        this.instInstancedMesh = mesh;
        this.scene.add(mesh);
        for (let i = old.count; i < newCapacity; i++) this._freeInstIndices.push(i);
        this._instInstanceIdToNode.length = newCapacity;
    }

    _allocateInstance(isDoc) {
        const freeList = isDoc ? this._freeDocIndices : this._freeInstIndices;
        if (freeList.length === 0) {
            const mesh = isDoc ? this.docInstancedMesh : this.instInstancedMesh;
            const newCap = Math.max(16, Math.ceil(mesh.count * 1.5));
            if (isDoc) this._growDocMesh(newCap);
            else this._growInstMesh(newCap);
            return this._allocateInstance(isDoc);
        }
        return freeList.pop();
    }

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
        const mat = new THREE.Matrix4().makeScale(0, 0, 0);
        mesh.setMatrixAt(index, mat);
        if (mesh.instanceColor) mesh.setColorAt(index, new THREE.Color(0, 0, 0));
        mesh.instanceMatrix.needsUpdate = true;
        if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
        this.nodeInstanceMap.delete(nodeId);
    }

    _removeNodeInstance(nodeId) {
        this._freeInstance(nodeId); // also deletes from nodeInstanceMap
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
        if (this.hoveredId === nodeId) { this.hoveredId = null; this.hideBillboard(); }
    }

    _setInstanceColor(nodeId, color) {
        const entry = this.nodeInstanceMap.get(nodeId);
        if (!entry) return;
        const mesh = entry.isDoc ? this.docInstancedMesh : this.instInstancedMesh;
        if (mesh.instanceColor) {
            mesh.setColorAt(entry.index, color);
            mesh.instanceColor.needsUpdate = true;
        }
    }

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
    }

    _setInstanceVisible(nodeId, visible) {
        this._setInstanceTransform(
            nodeId,
            visible ? 1.0 : 0.0,
            this.nodeInstanceMap.get(nodeId)?.originalColor || new THREE.Color(1, 1, 1)
        );
    }

    _getNodePosition(nodeId) {
        const entry = this.nodeInstanceMap.get(nodeId);
        if (!entry) return null;
        const mesh = entry.isDoc ? this.docInstancedMesh : this.instInstancedMesh;
        const mat = new THREE.Matrix4();
        mesh.getMatrixAt(entry.index, mat);
        const pos = new THREE.Vector3();
        const scale = new THREE.Vector3();
        const quat = new THREE.Quaternion();
        mat.decompose(pos, quat, scale);
        return pos;
    }

    // ====================== Scene setup ======================
    init() {
        const container = document.getElementById('projector-panel');
        const canvas = document.getElementById('projector-canvas');
        if (!container || !canvas) {
            console.error("[ChunkProjector] Missing DOM targets");
            return;
        }

        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(0x0f1115, 0.002);

        this.camera = new THREE.PerspectiveCamera(
            60, container.clientWidth / container.clientHeight, 0.1, 1000
        );
        this.camera.position.set(0, 5, 25);
        this.scene.add(this.camera);

        this.renderer = new THREE.WebGLRenderer({
            canvas, antialias: true, alpha: true
        });
        this.renderer.setSize(container.clientWidth, container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);

        this.scene.add(new THREE.AmbientLight(0xffffff, 0.7));
        const directional = new THREE.DirectionalLight(0xffffff, 0.8);
        directional.position.set(10, 20, 10);
        this.scene.add(directional);

        if (typeof THREE.OrbitControls === 'function') {
            this.controls = new THREE.OrbitControls(this.camera, canvas);
            this.controls.enableDamping = true;
            this.controls.dampingFactor = 0.05;
        } else {
            console.error("[ChunkProjector] THREE.OrbitControls missing");
        }

        // Create InstancedMeshes for documents and instances
        this._createInstancedMeshes(10000);

        window.addEventListener('resize', () => this.onResize());

        canvas.addEventListener('mousedown', (e) => {
            this.isDragging = false;
            this.mouseDownPos.x = e.clientX;
            this.mouseDownPos.y = e.clientY;
        }, { capture: true });

        canvas.addEventListener('mousemove', (e) => {
            if (e.buttons === 1) {
                const dx = Math.abs(e.clientX - this.mouseDownPos.x);
                const dy = Math.abs(e.clientY - this.mouseDownPos.y);
                if (dx > 5 || dy > 5) this.isDragging = true;
            }
            this.onMouseMove(e);
        });

        window.addEventListener('mouseup', () => {
            setTimeout(() => { this.isDragging = false; }, 0);
        });

        canvas.addEventListener('mouseleave', () => {
            if (this.hoveredId) {
                if (this.hoveredId !== this.selectedId) this.restoreNodeVisuals(this.hoveredId);
                if (!this.selectedId) this.hideBillboard();
                this.hoveredId = null;
                document.body.style.cursor = 'default';
            }
        });

        canvas.addEventListener('click', (e) => this.onClick(e));

        this.initBackground();
        this.animate();
    }

    initBackground() {
        const video = document.createElement('video');
        video.src = '/static/waterfall.mp4';
        video.loop = true;
        video.muted = true;
        video.playsInline = true;
        video.crossOrigin = "anonymous";
        video.play().catch(e => console.warn("[ChunkProjector] Video play failed:", e));

        const texture = new THREE.VideoTexture(video);
        texture.minFilter = THREE.LinearFilter;
        texture.magFilter = THREE.LinearFilter;

        const geometry = new THREE.PlaneGeometry(1, 1);
        const material = new THREE.MeshBasicMaterial({
            map: texture, depthTest: true, depthWrite: false, fog: false
        });

        this.backgroundMesh = new THREE.Mesh(geometry, material);
        this.backgroundMesh.position.z = -this.backgroundDistance;
        this.backgroundMesh.renderOrder = -1;
        this.camera.add(this.backgroundMesh);
        this.updateBackgroundScale();
    }

    updateBackgroundScale() {
        if (!this.camera || !this.backgroundMesh) return;
        const vFOV = THREE.MathUtils ?
            THREE.MathUtils.degToRad(this.camera.fov) :
            THREE.Math.degToRad(this.camera.fov);
        const h = 2 * Math.tan(vFOV / 2) * this.backgroundDistance;
        const w = h * this.camera.aspect;
        this.backgroundMesh.scale.set(w, h, 1);
    }

    onResize() {
        const container = document.getElementById('projector-panel');
        if (this.camera && this.renderer && container) {
            this.camera.aspect = container.clientWidth / container.clientHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(container.clientWidth, container.clientHeight);
            this.updateBackgroundScale();
        }
    }

    getContrastYIQ(threeColor) {
        const yiq = (threeColor.r * 255 * 299 +
            threeColor.g * 255 * 587 +
            threeColor.b * 255 * 114) / 1000;
        return yiq >= 128 ? '#000000' : '#ffffff';
    }

    // ====================== Node loading ======================
    async loadNodes(opts) {
        opts = opts || {};
        this.setLoadingProgress("Fetching chunks from DB...", 10);

        if (!opts.skipCache) {
            try {
                const cached = localStorage.getItem('wfh_chunk_nodes_cache_v1');
                if (cached) {
                    const cachedData = JSON.parse(cached);
                    if (cachedData && Array.isArray(cachedData.nodes) && cachedData.nodes.length) {
                        console.log(`[ChunkProjector] painting ${cachedData.nodes.length} cached nodes optimistically`);
                        this.setLoadingProgress("Restoring last scene from cache…", 25);
                        this._buildSceneFromPayload(cachedData);
                    }
                }
            } catch (e) { /* ignore */ }
        }

        try {
            const res = await fetch('/api/chunk_nodes');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            this.setLoadingProgress("Parsing chunk data...", 30);
            const data = await res.json();
            console.log(`[ChunkProjector] Loaded ${data.count} chunk nodes`);
            try {
                localStorage.setItem('wfh_chunk_nodes_cache_v1', JSON.stringify(data));
            } catch (e) {
                try { localStorage.removeItem('wfh_chunk_nodes_cache_v1'); } catch (_) { }
            }
            this._buildSceneFromPayload(data);
        } catch (e) {
            this.setLoadingProgress("Failed to load chunks", 100);
            setTimeout(() => this.hideLoadingProgress(), 1000);
            console.error("[ChunkProjector] Failed to load chunk nodes", e);
            this.renderFileTree();
        }
    }

    _clearAllInstances() {
        if (this.docInstancedMesh) {
            this.docInstancedMesh.count = 0;
            this._freeDocIndices = [];
            const capDoc = this._docInstanceIdToNode.length;
            for (let i = 0; i < capDoc; i++) this._freeDocIndices.push(i);
            this._docInstanceIdToNode = new Array(capDoc).fill(null);
        }
        if (this.instInstancedMesh) {
            this.instInstancedMesh.count = 0;
            this._freeInstIndices = [];
            const capInst = this._instInstanceIdToNode.length;
            for (let i = 0; i < capInst; i++) this._freeInstIndices.push(i);
            this._instInstanceIdToNode = new Array(capInst).fill(null);
        }
        this.nodeInstanceMap.clear();
        this.initialNodeData.clear();
        this.dataMap.clear();
        this._imageSprites.forEach(sprite => {
            this.scene.remove(sprite);
            if (sprite.material) {
                if (sprite.material.map) sprite.material.map.dispose();
                sprite.material.dispose();
            }
        });
        this._imageSprites.clear();
        if (this._extraSprites) {
            this._extraSprites.forEach(arr => arr.forEach(sprite => {
                this.scene.remove(sprite);
                if (sprite.material) {
                    if (sprite.material.map) sprite.material.map.dispose();
                    sprite.material.dispose();
                }
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
    }

    _addNodeInstance(node) {
        if (this.nodeInstanceMap.has(node.id)) return;
        const isDoc = !!node.is_document;
        const idx = this._allocateInstance(isDoc);
        const mesh = isDoc ? this.docInstancedMesh : this.instInstancedMesh;
        const color = new THREE.Color(node.r, node.g, node.b);
        const entry = { isDoc, index: idx, originalColor: color.clone() };
        this.nodeInstanceMap.set(node.id, entry);

        const pos = new THREE.Vector3(node.x, node.y, node.z);
        const mat = new THREE.Matrix4().setPosition(pos);
        mesh.setMatrixAt(idx, mat);
        if (mesh.instanceColor) mesh.setColorAt(idx, color);
        mesh.count = Math.max(mesh.count, idx + 1);
        mesh.instanceMatrix.needsUpdate = true;
        if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;

        if (isDoc) this._docInstanceIdToNode[idx] = node.id;
        else this._instInstanceIdToNode[idx] = node.id;

        this.initialNodeData.set(node.id, { position: pos.clone(), umapColor: new THREE.Vector3(node.r, node.g, node.b) });
        this.dataMap.set(node.id, node);
    }

    _buildSceneFromPayload(data) {
        if (data && Array.isArray(data.nodes)) {
            for (const n of data.nodes) ChunkProjector.layOutNode(n);
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

        // Path 1: Short-circuit when node set is unchanged
        const incomingIds = new Set(data.nodes.map(n => n.id));
        if (this.nodeInstanceMap.size > 0) {
            let allSame = incomingIds.size === this.nodeInstanceMap.size;
            if (allSame) {
                for (const id of incomingIds) {
                    if (!this.nodeInstanceMap.has(id)) { allSame = false; break; }
                }
            }
            if (allSame) {
                this.hideLoadingProgress();
                return;
            }

            // Path 2: Incremental add-only
            let allPresent = true;
            if (!allSame) {
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
                        const key = `${e.source}|${e.target}`;
                        if (!existingEdgeKeys.has(key)) this.edges.push(e);
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

        // Path 3: Full rebuild
        this.setLoadingProgress("Clearing previous scene...", 40);
        this._clearAllInstances();
        if (this._pinnedPanels && this._pinnedPanels.size) {
            Array.from(this._pinnedPanels.keys()).forEach(id => this.unpinPanel(id));
            this._panelHoverCount = 0;
        }

        const box = new THREE.Box3();
        this.setLoadingProgress(`Building 3D objects for ${data.nodes.length} chunks...`, 60);
        data.nodes.forEach(node => {
            this._addNodeInstance(node);
            const pos = new THREE.Vector3(node.x, node.y, node.z);
            box.expandByPoint(pos);
        });

        this.edges = data.edges || [];
        this.rebuildEdges();

        this.setLoadingProgress("Framing camera...", 80);
        if (!box.isEmpty()) {
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());
            const maxDim = Math.max(size.x, size.y, size.z) || 10;
            if (this.controls) {
                this.controls.target.copy(center);
                this.camera.position.set(
                    center.x, center.y + maxDim * 0.4, center.z + maxDim * 1.6
                );
                this.controls.update();
            }
        }

        this.setLoadingProgress("Building domain tree...", 90);
        this.domainTree.clear();
        this.dataMap.forEach(n => {
            if (!n.url) return;
            let domain = 'Unknown';
            try { domain = new URL(n.url).hostname; } catch (e) { }
            if (!this.domainTree.has(domain)) this.domainTree.set(domain, new Set());
            this.domainTree.get(domain).add(n.url);
        });

        try {
            const known = new Set();
            this.workspaces.forEach(ws => (ws.urls || []).forEach(u => known.add(u)));
            const activeWs = this.workspaces.find(w => w.id === this.activeWorkspaceId);
            if (activeWs) {
                let touched = false;
                this.dataMap.forEach(n => {
                    if (n && n.url && !known.has(n.url)) {
                        activeWs.urls.push(n.url);
                        known.add(n.url);
                        touched = true;
                    }
                });
                if (touched) this.saveWorkspaces();
            }
        } catch (_) { }

        this.applyWorkspaceVisibility();
        this.renderFileTree();
        this.renderUrlBuckets();

        this.setLoadingProgress("Ready", 100);
        setTimeout(() => this.hideLoadingProgress(), 400);

        this._spawnImageBillboards(data.nodes);
        this._lazyLoadAllNodeDetails(data.nodes);
    }

    addNodesIncrementally(rows, opts) {
        if (!Array.isArray(rows) || rows.length === 0) return 0;
        opts = opts || {};
        if (!this.scene || !this.nodeInstanceMap) return 0;

        const toAdd = [];
        const seenUrls = new Set();
        for (const row of rows) {
            if (!row || !row.id) continue;
            const url = row.url || '';
            if (url && !seenUrls.has(url)) {
                seenUrls.add(url);
                const docId = row.doc_id || `doc_${url}`;
                if (!this.nodeInstanceMap.has(docId)) {
                    toAdd.push({ id: docId, url, is_document: true, doc_id: '' });
                }
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
            ChunkProjector.layOutNode(node);
            this._addNodeInstance(node);
            if (!node.is_document && node.doc_id) {
                newEdges.push({ source: node.id, target: node.doc_id });
            }
            if (node.url) {
                let domain = 'Unknown';
                try { domain = new URL(node.url).hostname; } catch (_) { }
                if (!this.domainTree.has(domain)) this.domainTree.set(domain, new Set());
                this.domainTree.get(domain).add(node.url);
                try { this.addUrlToActiveWorkspace(node.url); } catch (_) { }
            }
        }

        if (newEdges.length) {
            const existingKeys = new Set(this.edges.map(e => `${e.source}|${e.target}`));
            for (const e of newEdges) {
                const key = `${e.source}|${e.target}`;
                if (!existingKeys.has(key)) this.edges.push(e);
            }
            // Debounce during rapid streaming; immediate rebuild on non-streaming callers.
            if (opts.quiet) {
                this._rebuildEdgesSoon();
            } else {
                this.rebuildEdges();
            }
        }

        if (!opts.quiet) {
            this.applyWorkspaceVisibility();
            this.renderFileTree();
            this.renderUrlBuckets();
        } else {
            this._requestUIUpdate();
        }
        return toAdd.length;
    }

    rebuildEdges() {
        if (this.linesMesh) {
            this.scene.remove(this.linesMesh);
            if (this.linesMesh.geometry) this.linesMesh.geometry.dispose();
            if (this.linesMesh.material) this.linesMesh.material.dispose();
            this.linesMesh = null;
        }
        if (!this.edges || this.edges.length === 0) return;
        const lineMaterial = new THREE.LineBasicMaterial({ color: 0x556370, transparent: true, opacity: 0.3 });
        const points = [];
        this.edges.forEach(e => {
            const s = this.initialNodeData.get(e.source);
            const t = this.initialNodeData.get(e.target);
            if (s && t) {
                points.push(s.position.clone(), t.position.clone());
            }
        });
        if (points.length > 0) {
            const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);
            this.linesMesh = new THREE.LineSegments(lineGeometry, lineMaterial);
            this.scene.add(this.linesMesh);
        }
    }

    // ====================== Sprites (image billboards) ======================
    _spawnImageBillboards(nodes) {
        if (!this._imageSprites) this._imageSprites = new Map();
        if (!this._extraSprites) this._extraSprites = new Map();
        if (!this._imageTextureCache) this._imageTextureCache = new Map();
        if (!this._imageProxyFailures) this._imageProxyFailures = new Set();
        const loader = new THREE.TextureLoader();
        loader.crossOrigin = 'anonymous';

        const toProxy = (absUrl) => {
            if (!absUrl) return absUrl;
            try {
                const u = new URL(absUrl, window.location.href);
                if (u.protocol === 'data:' || u.protocol === 'blob:') return absUrl;
                if (u.origin === window.location.origin) return absUrl;
                return `/api/image_proxy?url=${encodeURIComponent(u.href)}`;
            } catch (_e) { return absUrl; }
        };

        nodes.forEach(node => {
            if (this._imageSprites.has(node.id) || node.is_document) return;

            const pageUrl = node.url || window.location.href;
            const resolve = (u) => {
                if (!u) return null;
                try { return new URL(u, pageUrl).href; }
                catch (e) { return null; }
            };
            const urls = [];
            const seen = new Set();
            const pushUnique = (u) => {
                const r = resolve(u);
                if (!r) return;
                if (seen.has(r)) return;
                seen.add(r);
                urls.push(r);
            };
            pushUnique(node.image_url);
            if (node.html_raw) {
                for (const m of this.extractMediaFromHtml(node.html_raw, pageUrl)) {
                    if (m.type === 'image') pushUnique(m.src);
                }
            }
            if (urls.length === 0) return;

            // Deduplicate similar URLs (same as original)
            const tokenizeUrl = (u) => u.split(/[/?&#=.:_-]+/).filter(t => t.length > 2 && !/^\d+$/.test(t) && t.toLowerCase() !== 'https' && t.toLowerCase() !== 'com' && t.toLowerCase() !== 'www');
            const extractArea = (u) => {
                try {
                    const parsed = new URL(u);
                    const w = parseInt(parsed.searchParams.get('w') || parsed.searchParams.get('width') || '0');
                    if (w > 0) return w * w;
                } catch (_) { }
                const match = u.match(/(\d+)x(\d+)/i);
                if (match) return parseInt(match[1]) * parseInt(match[2]);
                return 0;
            };
            const groups = [];
            for (const url of urls) {
                const tokens = tokenizeUrl(url);
                const area = extractArea(url);
                let foundGroup = false;
                for (const g of groups) {
                    const setA = new Set(tokens);
                    const setB = new Set(g.tokens);
                    let intersection = 0;
                    for (const t of setA) if (setB.has(t)) intersection++;
                    const union = setA.size + setB.size - intersection;
                    if (union && (intersection / union) >= 0.75) {
                        foundGroup = true;
                        if (area > g.area) { g.url = url; g.area = area; }
                        break;
                    }
                }
                if (!foundGroup) groups.push({ url, tokens, area });
            }
            const finalUrls = groups.map(g => g.url);

            finalUrls.forEach((imgUrl, idx) => {
                const fetchUrl = toProxy(imgUrl);
                loader.load(
                    fetchUrl,
                    (texture) => {
                        const initData = this.initialNodeData.get(node.id);
                        if (!initData) { texture.dispose(); return; }
                        const isPrimary = idx === 0;
                        if (isPrimary && this._imageSprites.has(node.id)) return;

                        const img = texture.image || {};
                        const w = img.width || 1, h = img.height || 1;
                        const aspect = (w > 0 && h > 0) ? w / h : 1;
                        const material = new THREE.SpriteMaterial({
                            map: texture, transparent: true, depthWrite: false
                        });
                        const sprite = new THREE.Sprite(material);
                        const baseSize = isPrimary ? 1.0 : 0.55;
                        if (aspect >= 1) sprite.scale.set(baseSize * aspect, baseSize, 1);
                        else sprite.scale.set(baseSize, baseSize / aspect, 1);
                        sprite.position.copy(initData.position);
                        let offsetX = 0, offsetY = 0;
                        if (!isPrimary) {
                            const extraCount = Math.max(1, finalUrls.length - 1);
                            const theta = ((idx - 1) / extraCount) * Math.PI * 2;
                            const radius = 1.1 + Math.min(extraCount, 8) * 0.05;
                            offsetX = Math.cos(theta) * radius;
                            offsetY = Math.sin(theta) * radius;
                            sprite.position.x += offsetX;
                            sprite.position.y += offsetY;
                        }
                        sprite.userData = {
                            id: node.id,
                            baseScaleX: sprite.scale.x,
                            baseScaleY: sprite.scale.y,
                            isExtraImage: !isPrimary,
                            offsetX, offsetY,
                        };

                        if (isPrimary) {
                            this._setInstanceVisible(node.id, false);
                            this._imageSprites.set(node.id, sprite);
                            if (this.searchResults && this.searchResults.has(node.id)) {
                                this.applySearchGlow(node.id, this.searchResults.get(node.id));
                            }
                        } else {
                            let arr = this._extraSprites.get(node.id);
                            if (!arr) { arr = []; this._extraSprites.set(node.id, arr); }
                            arr.push(sprite);
                        }

                        const ws = this.workspaces.find(w => w.id === this.activeWorkspaceId);
                        if (ws) {
                            const visibleSet = new Set(ws.urls.filter(u => !(ws.hiddenUrls || []).includes(u)));
                            const data = this.dataMap.get(node.id);
                            if (!data || !visibleSet.has(data.url)) {
                                sprite.visible = false;
                            }
                        }
                        this.scene.add(sprite);
                    },
                    undefined,
                    (_err) => {
                        if (this._imageProxyFailures.has(fetchUrl)) return;
                        this._imageProxyFailures.add(fetchUrl);
                        if (fetchUrl === imgUrl) {
                            if (!this._loggedImageFailures) this._loggedImageFailures = 0;
                            if (this._loggedImageFailures < 5) {
                                console.warn("[ChunkProjector] Image texture failed:", imgUrl);
                                this._loggedImageFailures++;
                            }
                            return;
                        }
                        loader.load(
                            imgUrl,
                            (texture) => {
                                const initData = this.initialNodeData.get(node.id);
                                if (!initData) { texture.dispose(); return; }
                                const isPrimary = idx === 0;
                                if (isPrimary && this._imageSprites.has(node.id)) return;
                                const img = texture.image || {};
                                const w = img.width || 1, h = img.height || 1;
                                const aspect = (w > 0 && h > 0) ? w / h : 1;
                                const material = new THREE.SpriteMaterial({
                                    map: texture, transparent: true, depthWrite: false
                                });
                                const sprite = new THREE.Sprite(material);
                                const baseSize = isPrimary ? 1.0 : 0.55;
                                if (aspect >= 1) sprite.scale.set(baseSize * aspect, baseSize, 1);
                                else sprite.scale.set(baseSize, baseSize / aspect, 1);
                                sprite.position.copy(initData.position);
                                let offsetX = 0, offsetY = 0;
                                if (!isPrimary) {
                                    const extraCount = Math.max(1, finalUrls.length - 1);
                                    const theta = ((idx - 1) / extraCount) * Math.PI * 2;
                                    const radius = 1.1 + Math.min(extraCount, 8) * 0.05;
                                    offsetX = Math.cos(theta) * radius;
                                    offsetY = Math.sin(theta) * radius;
                                    sprite.position.x += offsetX;
                                    sprite.position.y += offsetY;
                                }
                                sprite.userData = {
                                    id: node.id,
                                    baseScaleX: sprite.scale.x,
                                    baseScaleY: sprite.scale.y,
                                    isExtraImage: !isPrimary,
                                    offsetX, offsetY,
                                };
                                if (isPrimary) {
                                    this._setInstanceVisible(node.id, false);
                                    this._imageSprites.set(node.id, sprite);
                                    if (this.searchResults && this.searchResults.has(node.id)) {
                                        this.applySearchGlow(node.id, this.searchResults.get(node.id));
                                    }
                                } else {
                                    let arr = this._extraSprites.get(node.id);
                                    if (!arr) { arr = []; this._extraSprites.set(node.id, arr); }
                                    arr.push(sprite);
                                }
                                const ws = this.workspaces.find(w => w.id === this.activeWorkspaceId);
                                if (ws) {
                                    const visibleSet = new Set(ws.urls.filter(u => !(ws.hiddenUrls || []).includes(u)));
                                    const data = this.dataMap.get(node.id);
                                    if (!data || !visibleSet.has(data.url)) {
                                        sprite.visible = false;
                                    }
                                }
                                this.scene.add(sprite);
                            },
                            undefined,
                            (_err2) => {
                                if (!this._loggedImageFailures) this._loggedImageFailures = 0;
                                if (this._loggedImageFailures < 5) {
                                    console.warn("[ChunkProjector] Image texture failed (proxy+direct):", imgUrl);
                                    this._loggedImageFailures++;
                                }
                            }
                        );
                    }
                );
            });
        });
    }

    async _lazyLoadAllNodeDetails(nodes) {
        const batchSize = 100;
        for (let i = 0; i < nodes.length; i += batchSize) {
            const batch = nodes.slice(i, i + batchSize);
            const toFetch = batch.filter(n => !n.is_document && (!this.dataMap.has(n.id) || this.dataMap.get(n.id).html_raw === undefined)).map(n => n.id);
            if (toFetch.length > 0) {
                try {
                    const res = await fetch('/api/chunk_details_batch', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(toFetch)
                    });
                    if (res.ok && res.body) {
                        const reader = res.body.getReader();
                        const decoder = new TextDecoder();
                        let buffer = '';
                        while (true) {
                            const { done, value } = await reader.read();
                            if (done) {
                                if (buffer.trim()) {
                                    try {
                                        const details = JSON.parse(buffer);
                                        const cached = this.dataMap.get(details.id) || {};
                                        this.dataMap.set(details.id, { ...cached, ...details });
                                        if (this.dataMap.get(details.id)) this._spawnImageBillboards([this.dataMap.get(details.id)]);
                                    } catch (e) { console.warn("Failed to parse trailing NDJSON", e); }
                                }
                                break;
                            }
                            buffer += decoder.decode(value, { stream: true });
                            const lines = buffer.split('\n');
                            buffer = lines.pop();
                            for (const line of lines) {
                                if (!line.trim()) continue;
                                try {
                                    const details = JSON.parse(line);
                                    const cached = this.dataMap.get(details.id) || {};
                                    this.dataMap.set(details.id, { ...cached, ...details });
                                    if (this.dataMap.get(details.id)) this._spawnImageBillboards([this.dataMap.get(details.id)]);
                                } catch (e) { console.warn("Failed to parse NDJSON line", e); }
                            }
                        }
                    }
                } catch (e) { console.error("[ChunkProjector] Batch fetch failed", e); }
            }
            await new Promise(r => setTimeout(r, 10));
        }
    }

    // ====================== File Tree & Workspace Management ======================
    // (unchanged except where noted; uses this.dataMap / this.nodeInstanceMap)
    initFileTree() {
        const style = document.createElement('style');
        style.innerHTML = `
            #ft-latch {
                position: fixed; top: 50%; left: 0px;
                background: var(--surface-base, #242933); border: 1px solid var(--border-light, #434c5e);
                border-left: none; color: var(--text-secondary, #d8dee9); padding: 20px 6px; cursor: pointer;
                z-index: 9999; border-radius: 0 8px 8px 0;
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
            .ws-save-btn { color: #34d399; }
            .ws-save-btn:hover { color: #10b981; }
            .ft-folder { margin: 2px 0; }
            .ft-folder-title {
                padding: 6px 15px 6px 25px; cursor: pointer; display: flex; align-items: center;
                transition: background 0.15s; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            }
            .ft-folder-title:hover { background: rgba(255,255,255,0.05); }
            .ft-folder.active-ws .ft-folder-title { background: rgba(59, 130, 246, 0.15); color: #60a5fa; font-weight: bold; }
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
            .ft-item-actions button.remove-hover:hover { color: #ef4444; }
        `;
        document.head.appendChild(style);

        const latch = document.createElement('div');
        latch.id = 'ft-latch';
        latch.title = "Toggle Workspace Panel";
        latch.innerHTML = '<i class="fas fa-chevron-left" style="transition: transform 0.3s ease;"></i>';
        document.body.appendChild(latch);

        latch.addEventListener('click', () => {
            // Target the LEFT sidebar element directly. The previous
            // ``closest()``/walk-up heuristic landed on ``#container``
            // (the flex parent of the entire app) when no ``.sidebar``
            // class was found, so collapsing the latch hid the WHOLE
            // GUI. ``#history-sidebar`` is the actual left panel (see
            // templates/index.html) and is ``position: absolute``, so
            // ``transform`` animates the panel off-screen without
            // affecting the rest of the layout.
            const panel = document.getElementById('history-sidebar');
            if (!panel) return;

            if (!panel.classList.contains('sidebar-sliding')) panel.classList.add('sidebar-sliding');

            // Cache the natural width once so the collapse animation has a
            // stable target even after we've blown out ``offsetWidth`` via
            // transform on subsequent clicks.
            if (!panel.dataset.originalWidth || parseInt(panel.dataset.originalWidth) === 0) {
                if (panel.offsetWidth > 0) panel.dataset.originalWidth = panel.offsetWidth;
            }
            const width = parseInt(panel.dataset.originalWidth) || 280;

            const isCollapsed = panel.dataset.collapsed === 'true';
            const icon = latch.querySelector('i');

            if (isCollapsed) {
                panel.style.transform = '';
                panel.style.opacity = '1';
                panel.style.pointerEvents = '';
                icon.style.transform = 'rotate(0deg)';
                panel.dataset.collapsed = 'false';
            } else {
                // +10px extra so the box-shadow also clears the viewport.
                panel.style.transform = `translateX(-${width + 10}px)`;
                panel.style.opacity = '0';
                // While collapsed, ignore clicks on the (off-screen) panel so
                // it can't eat events for UI that is now visible underneath.
                panel.style.pointerEvents = 'none';
                icon.style.transform = 'rotate(180deg)';
                panel.dataset.collapsed = 'true';
            }

            // Kick three.js to re-evaluate canvas size through the slide. The
            // center canvas doesn't actually change size here (left panel is
            // absolute-positioned) but the billboard-arrow SVG and other
            // overlays listen for resize and it's cheap to fire.
            let start = Date.now();
            let timer = setInterval(() => {
                window.dispatchEvent(new Event('resize'));
                if (Date.now() - start > 350) clearInterval(timer);
            }, 16);
        });

        this.renderFileTree();
    }

    loadWorkspaces() {
        try {
            const raw = localStorage.getItem('wfh_workspaces');
            if (raw) return JSON.parse(raw);
        } catch (e) { }
        return [];
    }

    saveWorkspaces() {
        localStorage.setItem('wfh_workspaces', JSON.stringify(this.workspaces));
    }

    createWorkspace(name) {
        const ws = { id: 'ws_' + Date.now(), name, urls: [], hiddenUrls: [] };
        this.workspaces.push(ws);
        this.saveWorkspaces();
        return ws.id;
    }

    renderFileTree() {
        const container = document.getElementById('history-container');
        if (!container) return;

        let html = `<div class="ft-header-main">File Explorer</div>`;

        // 1. Workspaces Section
        html += `<div class="ft-section">
            <div class="ft-section-header" onclick="app.toggleFtFolder('ft-workspaces')">
                <span><i class="fas ${this.expandedFolders.has('ft-workspaces') ? 'fa-chevron-down' : 'fa-chevron-right'}"></i> Workspaces</span>
            </div>
            <div id="ft-workspaces" class="ft-items ${this.expandedFolders.has('ft-workspaces') ? 'expanded' : ''}">`;

        this.workspaces.forEach(ws => {
            const isActive = ws.id === this.activeWorkspaceId;
            const folderId = `ft-ws-${ws.id}`;
            const isExp = this.expandedFolders.has(folderId);

            html += `<div class="ft-folder ${isActive ? 'active-ws' : ''}">
                <div class="ft-folder-title" onclick="app.setActiveWorkspace('${ws.id}')" oncontextmenu="app.deleteWorkspace('${ws.id}', event)">
                    <span style="margin-right:8px;" onclick="event.stopPropagation(); app.toggleFtFolder('${folderId}')">
                        <i class="fas fa-dot-circle" ${isExp ? '' : 'style="opacity: 0.5;"'}></i>
                    </span>
                    <input type="text" class="ws-name-input" id="input-ws-${ws.id}" value="${this.escape(ws.name)}" onclick="event.stopPropagation(); app.setActiveWorkspace('${ws.id}')" oninput="app.onWorkspaceNameInput('${ws.id}')" onkeydown="if(event.key==='Enter') app.saveWorkspaceName('${ws.id}')" />
                    <button class="ft-btn-icon ws-save-btn" id="save-ws-${ws.id}" style="display:none;" onclick="event.stopPropagation(); app.saveWorkspaceName('${ws.id}')"><i class="fas fa-check"></i></button>
                </div>
                <div id="${folderId}" class="ft-items ${isExp ? 'expanded' : ''}">`;

            ws.urls.forEach(url => {
                const isHidden = ws.hiddenUrls && ws.hiddenUrls.includes(url);
                html += `<div class="ft-item">
                    <span class="ft-url-label" title="${this.escape(url)}">📄 ${this.escape(this.shortenUrl(url))}</span>
                    <span class="ft-item-actions">
                        <button title="${isHidden ? 'Show in GUI' : 'Deselect from GUI'}" onclick="app.toggleUrlVisibility('${ws.id}', '${this.escape(url)}')">
                            <i class="fas ${isHidden ? 'fa-eye-slash' : 'fa-eye'}"></i>
                        </button>
                        <button class="remove-hover" title="Remove from Workspace" onclick="app.removeUrlFromWorkspace('${ws.id}', '${this.escape(url)}')">
                            <i class="fas fa-times"></i>
                        </button>
                    </span>
                </div>`;
            });

            html += `</div></div>`;
        });
        html += `<div class="ft-add-ws-btn" title="Add Workspace" onclick="app.addNewWorkspaceField()">+</div>`;
        html += `</div></div>`;

        // 2. Domains Section
        html += `<div class="ft-section">
            <div class="ft-section-header" onclick="app.toggleFtFolder('ft-domains')">
                <span><i class="fas ${this.expandedFolders.has('ft-domains') ? 'fa-chevron-down' : 'fa-chevron-right'}"></i> Domains</span>
            </div>
            <div id="ft-domains" class="ft-items ${this.expandedFolders.has('ft-domains') ? 'expanded' : ''}">`;

        if (this.domainTree.size === 0) {
            html += `<div class="ft-item" style="color:#6b7280; font-style:italic;">No domains loaded</div>`;
        }

        this.domainTree.forEach((urls, domain) => {
            const folderId = `ft-dom-${domain}`;
            const isExp = this.expandedFolders.has(folderId);

            html += `<div class="ft-folder">
                <div class="ft-folder-title" onclick="app.toggleFtFolder('${folderId}')">
                    <span style="margin-right:8px;"><i class="fas ${isExp ? 'fa-globe' : 'fa-globe'}"></i></span>
                    ${this.escape(domain)} <span style="color:#6b7280; margin-left:8px;">(${urls.size})</span>
                </div>
                <div id="${folderId}" class="ft-items ${isExp ? 'expanded' : ''}">`;

            urls.forEach(url => {
                html += `<div class="ft-item domain-item" 
                              onmouseenter="app.previewUrl('${this.escape(url)}')" 
                              onmouseleave="app.clearPreview()" 
                              onclick="app.addUrlToActiveWorkspace('${this.escape(url)}')">
                    <span class="ft-url-label" title="${this.escape(url)}">🔗 ${this.escape(this.shortenUrl(url))}</span>
                </div>`;
            });
            html += `</div></div>`;
        });
        html += `</div></div>`;

        // Footer tip
        html += `<div style="margin-top:auto; padding:10px 15px; font-size:11px; color:#6b7280; border-top:1px solid rgba(255,255,255,0.05);">
            <i class="fas fa-info-circle"></i> Right-click a Workspace to delete it.
        </div>`;

        container.innerHTML = html;
    }

    initRainbowObserver() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach(m => {
                m.addedNodes.forEach(node => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        this.applyRainbowDelays(node);
                    }
                });
                if (m.type === 'characterData' && m.target.parentElement) {
                    this._applyDelay(m.target.parentElement, true);
                }
            });
        });
        observer.observe(document.body, { childList: true, subtree: true, characterData: true });
        this.applyRainbowDelays(document.body);
    }

    applyRainbowDelays(container) {
        if (!container || !container.querySelectorAll) return;
        this._applyDelay(container);
        const elements = container.querySelectorAll('*');
        elements.forEach(el => this._applyDelay(el));
    }

    _applyDelay(el, force = false) {
        if (!el || el.nodeType !== Node.ELEMENT_NODE) return;
        if (!force && el.dataset && el.dataset.rainbowDelayed) return;

        let hasText = false;

        if (el.childNodes) {
            el.childNodes.forEach(child => {
                if (child.nodeType === Node.TEXT_NODE && child.textContent.trim().length > 0) {
                    hasText = true;
                }
            });
        }

        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.tagName === 'BUTTON') {
            hasText = true;
        }

        if (hasText) {
            let delay = el.dataset.rainbowDelayVal;
            if (!delay) {
                delay = (Math.random() * 4).toFixed(2);
                el.dataset.rainbowDelayVal = delay;
            }
            el.style.setProperty('animation-delay', `-${delay}s`, 'important');
            if (el.dataset) el.dataset.rainbowDelayed = "true";
        }
    }

    toggleFtFolder(id) {
        if (this.expandedFolders.has(id)) this.expandedFolders.delete(id);
        else this.expandedFolders.add(id);
        this.renderFileTree();
    }

    onWorkspaceNameInput(id) {
        const inputEl = document.getElementById(`input-ws-${id}`);
        const saveBtn = document.getElementById(`save-ws-${id}`);
        if (!inputEl || !saveBtn) return;

        if (!this.wsEditOriginals.has(id)) {
            const ws = this.workspaces.find(w => w.id === id);
            this.wsEditOriginals.set(id, ws ? ws.name : '');
        }

        saveBtn.style.display = 'inline-block';

        if (this.wsEditTimers.has(id)) {
            clearTimeout(this.wsEditTimers.get(id));
        }

        // Debounce back to original text if not clicked
        const timer = setTimeout(() => {
            inputEl.value = this.wsEditOriginals.get(id) || '';
            saveBtn.style.display = 'none';
            this.wsEditOriginals.delete(id);
            this.wsEditTimers.delete(id);
        }, 3000);

        this.wsEditTimers.set(id, timer);
    }

    saveWorkspaceName(id) {
        const inputEl = document.getElementById(`input-ws-${id}`);
        const saveBtn = document.getElementById(`save-ws-${id}`);
        if (!inputEl) return;

        if (this.wsEditTimers.has(id)) {
            clearTimeout(this.wsEditTimers.get(id));
            this.wsEditTimers.delete(id);
        }

        const newName = inputEl.value.trim();
        const ws = this.workspaces.find(w => w.id === id);
        if (ws && newName) {
            ws.name = newName;
            this.saveWorkspaces();
        } else if (ws) {
            inputEl.value = ws.name; // Revert input if empty submission
        }

        if (saveBtn) saveBtn.style.display = 'none';
        this.wsEditOriginals.delete(id);
    }

    addNewWorkspaceField() {
        const newId = this.createWorkspace('');
        this.expandedFolders.add(`ft-ws-${newId}`);
        this.renderFileTree();

        // Automatically focus newly added field
        setTimeout(() => {
            const inputEl = document.getElementById(`input-ws-${newId}`);
            if (inputEl) {
                inputEl.focus();
                inputEl.select();
            }
        }, 50);
    }

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
    }

    deleteWorkspace(id, event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        if (this.workspaces.length <= 1) return;
        if (!confirm("Delete this workspace?")) return;
        this.workspaces = this.workspaces.filter(w => w.id !== id);
        if (this.activeWorkspaceId === id) this.activeWorkspaceId = this.workspaces[0].id;
        this.saveWorkspaces();
        this.applyWorkspaceVisibility();
        this.renderFileTree();
    }

    addUrlToActiveWorkspace(url) {
        const ws = this.workspaces.find(w => w.id === this.activeWorkspaceId);
        if (!ws) return;
        if (!ws.urls.includes(url)) {
            ws.urls.push(url);
            this.saveWorkspaces();
            this.applyWorkspaceVisibility();
            this.renderFileTree();
        }
    }

    removeUrlFromWorkspace(wsId, url) {
        const ws = this.workspaces.find(w => w.id === wsId);
        if (!ws) return;
        ws.urls = ws.urls.filter(u => u !== url);
        if (ws.hiddenUrls) ws.hiddenUrls = ws.hiddenUrls.filter(u => u !== url);
        this.saveWorkspaces();
        if (this.activeWorkspaceId === wsId) this.applyWorkspaceVisibility();
        this.renderFileTree();
    }

    toggleUrlVisibility(wsId, url) {
        const ws = this.workspaces.find(w => w.id === wsId);
        if (!ws) return;
        if (!ws.hiddenUrls) ws.hiddenUrls = [];

        if (ws.hiddenUrls.includes(url)) {
            ws.hiddenUrls = ws.hiddenUrls.filter(u => u !== url);
        } else {
            ws.hiddenUrls.push(url);
        }
        this.saveWorkspaces();
        if (this.activeWorkspaceId === wsId) this.applyWorkspaceVisibility();
        this.renderFileTree();
    }

    async deleteUrlFromDB(url, event) {
        if (event) event.preventDefault();
        if (!confirm(`Permanently delete all chunks for ${url} from the database? This cannot be undone.`)) return;
        try {
            await fetch(`/api/map/snapshots?url=${encodeURIComponent(url)}`, { method: 'DELETE' });
        } catch (e) {
            console.warn('DB delete fetch failed', e);
        }
        // Cleanup local state using nodeInstanceMap
        const toDelete = [];
        this.nodeInstanceMap.forEach((entry, id) => {
            const data = this.dataMap.get(id);
            if (data && data.url === url) {
                toDelete.push(id);
                this._freeInstance(id);
            }
        });
        toDelete.forEach(id => {
            this.dataMap.delete(id);
            this.initialNodeData.delete(id);
        });
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
    }

    applyWorkspaceVisibility() {
        const ws = this.workspaces.find(w => w.id === this.activeWorkspaceId);
        if (!ws) return;
        const visibleSet = new Set(ws.urls.filter(u => !(ws.hiddenUrls || []).includes(u)));

        this.nodeInstanceMap.forEach((entry, id) => {
            const data = this.dataMap.get(id);
            if (data && visibleSet.has(data.url)) {
                this._setInstanceVisible(id, true);
            } else {
                this._setInstanceVisible(id, false);
            }
        });
        this._imageSprites.forEach((sprite, nodeId) => {
            const data = this.dataMap.get(nodeId);
            if (data && visibleSet.has(data.url)) {
                sprite.visible = true;
                sprite.material.opacity = 1;
            } else {
                sprite.visible = false;
            }
        });
        const input = document.getElementById('nl-search');
        const searchActive = !!(input && input.value.trim()) || !!this.lastSearchPayload;
        if (searchActive && this.lastSearchPayload) {
            this.renderSearchResults(this.lastSearchPayload);
        } else {
            this.renderUrlBuckets();
        }
    }

    previewUrl(url) {
        this.nodeInstanceMap.forEach((entry, id) => {
            const data = this.dataMap.get(id);
            if (data && data.url === url) {
                if (!this._imageSprites.has(id)) {
                    const color = entry.originalColor.clone().multiplyScalar(0.3);
                    this._setInstanceTransform(id, 1.0, color);
                }
            }
        });
    }

    clearPreview() {
        this.nodeInstanceMap.forEach((entry, id) => {
            if (this._imageSprites.has(id)) return;
            this.restoreNodeVisuals(id);
        });
    }

    renderUrlBuckets() {
        const container = document.getElementById('results-container');
        if (!container) return;
        const byUrl = new Map();
        this.nodeInstanceMap.forEach((entry, id) => {
            const data = this.dataMap.get(id);
            if (!data || !data.url) return;
            if (!this._getNodePosition(id)) return; // invisible
            let normUrl = data.url.split('?')[0].replace(/\/+$/, "");
            if (!byUrl.has(normUrl)) {
                byUrl.set(normUrl, { displayUrl: data.url, items: [] });
            }
            byUrl.get(normUrl).items.push(data);
        });

        if (byUrl.size === 0) {
            container.innerHTML = '<div class="empty-state">No chunks loaded.</div>';
            return;
        }

        let visibleCount = 0;
        this.nodeInstanceMap.forEach((entry, id) => {
            if (this._getNodePosition(id)) visibleCount++;
        });
        const parts = [`<div class="bucket-heading">
            ${visibleCount} chunks across ${byUrl.size} URL${byUrl.size === 1 ? '' : 's'}
        </div>`];
        byUrl.forEach((group, normUrl) => {
            const shortUrl = this.shortenUrl(normUrl);
            parts.push(`
                <div class="url-bucket" data-url="${this.escape(group.displayUrl)}" style="cursor: pointer;">
                    <div class="url-bucket-head" title="${this.escape(normUrl)}">
                        <i class="fas fa-globe"></i> ${this.escape(shortUrl)}
                        <span class="url-bucket-count">${group.items.length}</span>
                    </div>
                </div>`);
        });
        container.innerHTML = parts.join('');

        container.querySelectorAll('.url-bucket').forEach(el => {
            const url = el.dataset.url;
            el.addEventListener('click', () => {
                let targetItems = [];
                const normClicked = url.split('?')[0].replace(/\/+$/, "");
                if (byUrl.has(normClicked)) targetItems = byUrl.get(normClicked).items;
                if (targetItems.length > 0) this.showChunksForUrl(url, targetItems);
            });
            const docId = `doc_${url}`;
            el.addEventListener('mouseenter', () => {
                this.hoveredId = docId;
                const entry = this.nodeInstanceMap.get(docId);
                if (entry && docId !== this.selectedId) {
                    const hlColor = entry.originalColor.clone().multiplyScalar(1.8);
                    this._setInstanceColor(docId, hlColor);
                }
            });
            el.addEventListener('mouseleave', () => {
                if (this.hoveredId === docId) this.hoveredId = null;
                if (docId !== this.selectedId) this.restoreNodeVisuals(docId);
            });
        });
    }

    // ====================== Interaction ======================
    getIntersects(event) {
        if (!this.renderer || !this.camera) return [];
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        this.raycaster.setFromCamera(this.mouse, this.camera);
        const targets = [this.docInstancedMesh, this.instInstancedMesh].filter(m => m);
        const hits = this.raycaster.intersectObjects(targets);
        return hits.map(hit => {
            let nodeId = null;
            if (hit.object === this.docInstancedMesh) nodeId = this._docInstanceIdToNode[hit.instanceId];
            else if (hit.object === this.instInstancedMesh) nodeId = this._instInstanceIdToNode[hit.instanceId];
            return { nodeId, point: hit.point, distance: hit.distance };
        }).filter(h => h.nodeId);
    }

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
                    if (entry) {
                        const hlColor = entry.originalColor.clone().multiplyScalar(1.5);
                        this._setInstanceColor(nodeId, hlColor);
                    }
                }
                if (!this.selectedId) {
                    const data = this.dataMap.get(nodeId);
                    this.showBillboard(data, false);
                    if (data && !data.is_document && data.html_raw === undefined) this.fetchNodeDetails(nodeId, false);
                }
            }
        } else if (this.hoveredId) {
            if (this.hoveredId !== this.selectedId) this.restoreNodeVisuals(this.hoveredId);
            if (!this.selectedId) this.hideBillboard();
            this.hoveredId = null;
            document.body.style.cursor = 'default';
        }
    }

    async onClick(event) {
        if (this.isDragging) return;
        const intersects = this.getIntersects(event);
        if (intersects.length > 0) {
            await this.selectNode(intersects[0].nodeId);
        } else {
            const input = document.getElementById('nl-search');
            const searchActive = !!(input && input.value.trim());
            this.selectedId = null;
            if (!searchActive) this.searchResults = null;
            this.hideBillboard();
            this.nodeInstanceMap.forEach((_, id) => this.restoreNodeVisuals(id));
            this.applyWorkspaceVisibility();
        }
    }

    restoreNodeVisuals(nodeId) {
        const entry = this.nodeInstanceMap.get(nodeId);
        if (!entry) return;
        let color = entry.originalColor.clone();
        if (this.searchResults && this.searchResults.has(nodeId)) {
            const score = this.searchResults.get(nodeId);
            color.lerp(new THREE.Color(1, 1, 1), score * 0.4);
        }
        this._setInstanceTransform(nodeId, 1.0, color);
    }

    async selectNode(id) {
        const data = this.dataMap.get(id);
        if (data && data.is_document) {
            const cur = this.docCollapseTarget.get(id) || 0;
            this.docCollapseTarget.set(id, cur ? 0 : 1);
        }
        if (this.selectedId && this.selectedId !== id) this.restoreNodeVisuals(this.selectedId);
        this.selectedId = id;
        const entry = this.nodeInstanceMap.get(id);
        if (entry) {
            const hlColor = entry.originalColor.clone().lerp(new THREE.Color(1, 1, 1), 0.3);
            this._setInstanceTransform(id, 1.5, hlColor);
        }
        if (data && data.is_document) {
            this.hideBillboard();
            return;
        }
        if (data) this.showBillboard(data, true);
        if (data && !data.is_document && data.html_raw === undefined) await this.fetchNodeDetails(id, true);
    }

    applySearchGlow(nodeId, score) {
        const entry = this.nodeInstanceMap.get(nodeId);
        if (!entry) return;
        const color = entry.originalColor.clone().lerp(new THREE.Color(1, 1, 1), score * 0.4);
        this._setInstanceTransform(nodeId, 1 + score * 0.3, color);
    }

    async fetchNodeDetails(id, isLocked = false) {
        if (this.detailsFetchQueue.has(id)) return;
        this.detailsFetchQueue.add(id);

        try {
            const res = await fetch(`/api/chunk_details/${encodeURIComponent(id)}`);
            if (res.ok) {
                const details = await res.json();
                const cached = this.dataMap.get(id);
                if (cached) {
                    const merged = { ...cached, ...details };
                    this.dataMap.set(id, merged);

                    if ((this.hoveredId === id && !this.selectedId) || this.selectedId === id) {
                        this.showBillboard(merged, isLocked || this.selectedId === id);
                    }
                }
            }
        } catch (e) {
            console.warn("[ChunkProjector] details fetch failed", e);
        } finally {
            this.detailsFetchQueue.delete(id);
        }
    }

    update3DVisualsFromResults(results) {
        this.nodeInstanceMap.forEach((entry, id) => {
            if (id !== this.selectedId) {
                const color = entry.originalColor.clone().multiplyScalar(0.15);
                this._setInstanceTransform(id, 1.0, color);
            }
        });
        this.searchResults = new Map();
        results.forEach(r => {
            this.searchResults.set(r.id, r.score);
            if (r.id !== this.selectedId) this.applySearchGlow(r.id, r.score);
        });
    }

    // ====================== Animation with frustum culling ======================
    animate() {
        requestAnimationFrame(() => this.animate());

        // Latch positioning (unchanged)
        const ftLatch = document.getElementById('ft-latch');
        if (ftLatch) {
            const container = document.getElementById('history-container');
            if (container) {
                let panel = container.closest('.sidebar, aside, .panel, #left-panel, .panel-left, .side-panel');
                if (!panel && container.parentElement && container.parentElement !== document.body) panel = container.parentElement;
                if (!panel) panel = container;
                const rect = panel.getBoundingClientRect();
                ftLatch.style.setProperty('transform', `translate(${rect.right}px, -50%)`, 'important');
            }
        }
        const rsLatch = document.getElementById('rs-latch');
        if (rsLatch) {
            const container = document.getElementById('results-container');
            if (container) {
                let panel = container.closest('.sidebar, aside, .panel, #right-panel, .panel-right, .side-panel');
                if (!panel && container.parentElement && container.parentElement !== document.body) panel = container.parentElement;
                if (!panel) panel = container;
                const rect = panel.getBoundingClientRect();
                const viewportWidth = document.documentElement.clientWidth || window.innerWidth;
                rsLatch.style.setProperty('transform', `translate(-${viewportWidth - rect.left}px, -50%)`, 'important');
            }
        }

        const delta = Math.min(this.clock.getDelta(), 0.1);
        const isInteracting = this.isDragging || this.hoveredId || this.selectedId || this._panelHoverCount > 0;
        if (!isInteracting) this.animationTime += delta;
        const t = this.animationTime;

        const spatialMatrix = new THREE.Matrix4();
        spatialMatrix.makeRotationFromEuler(new THREE.Euler(
            t * this.spatialVelocity.x,
            t * this.spatialVelocity.y,
            t * this.spatialVelocity.z
        ));
        const colorMatrix = new THREE.Matrix4();
        colorMatrix.makeRotationFromEuler(new THREE.Euler(
            t * this.colorVelocity.x,
            t * this.colorVelocity.y,
            t * this.colorVelocity.z
        ));

        // Frustum culling
        const frustum = new THREE.Frustum();
        const projScreenMatrix = new THREE.Matrix4();
        projScreenMatrix.multiplyMatrices(this.camera.projectionMatrix, this.camera.matrixWorldInverse);
        frustum.setFromProjectionMatrix(projScreenMatrix);

        const extraConnectorPositions = [];

        const updateMesh = (mesh, isDoc) => {
            const idMap = isDoc ? this._docInstanceIdToNode : this._instInstanceIdToNode;
            for (let i = 0; i < mesh.count; i++) {
                const nodeId = idMap[i];
                if (!nodeId) {
                    mesh.setMatrixAt(i, new THREE.Matrix4().makeScale(0, 0, 0));
                    if (mesh.instanceColor) mesh.setColorAt(i, new THREE.Color(0, 0, 0));
                    continue;
                }
                const init = this.initialNodeData.get(nodeId);
                if (!init) {
                    mesh.setMatrixAt(i, new THREE.Matrix4().makeScale(0, 0, 0));
                    continue;
                }
                const data = this.dataMap.get(nodeId);
                let pos = init.position.clone();
                if (data && !data.is_document && data.doc_id) {
                    const collapseT = this.docCollapseState.get(data.doc_id) || 0;
                    if (collapseT > 0) {
                        const docInit = this.initialNodeData.get(data.doc_id);
                        if (docInit) pos.lerp(docInit.position, collapseT);
                    }
                }
                pos.applyMatrix4(spatialMatrix);

                const inside = frustum.containsPoint(pos);
                const scale = inside ? 1.0 : 0.0;
                const matrix = new THREE.Matrix4().compose(pos, new THREE.Quaternion(), new THREE.Vector3(scale, scale, scale));
                mesh.setMatrixAt(i, matrix);

                // Color rotation
                const centered = init.umapColor.clone().subScalar(0.5);
                centered.applyMatrix4(colorMatrix);
                centered.addScalar(0.5);
                centered.x = Math.max(0, Math.min(1, centered.x));
                centered.y = Math.max(0, Math.min(1, centered.y));
                centered.z = Math.max(0, Math.min(1, centered.z));
                const newColor = new THREE.Color(centered.x, centered.y, centered.z);
                const entry = this.nodeInstanceMap.get(nodeId);
                if (entry) entry.originalColor.copy(newColor);

                let finalColor = newColor;
                if (nodeId === this.selectedId) {
                    finalColor = newColor.clone().lerp(new THREE.Color(1, 1, 1), 0.5);
                } else if (this.searchResults && this.searchResults.has(nodeId)) {
                    const score = this.searchResults.get(nodeId);
                    finalColor = newColor.clone().lerp(new THREE.Color(1, 1, 1), score * 0.4);
                } else if (nodeId === this.hoveredId) {
                    finalColor = newColor.clone().multiplyScalar(1.5);
                }
                if (mesh.instanceColor) {
                    mesh.setColorAt(i, finalColor);
                    mesh.instanceColor.needsUpdate = true;
                }

                if (inside && scale > 0 && this._extraSprites) {
                    const extras = this._extraSprites.get(nodeId);
                    if (extras && extras.length) {
                        for (const spr of extras) {
                            const sprPos = spr.position.clone();
                            extraConnectorPositions.push(
                                pos.x, pos.y, pos.z,
                                sprPos.x, sprPos.y, sprPos.z,
                            );
                        }
                    }
                }
            }
            mesh.instanceMatrix.needsUpdate = true;
            if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
        };

        updateMesh(this.docInstancedMesh, true);
        updateMesh(this.instInstancedMesh, false);

        // Sprite visibility and primary sprite positions
        const isInstanceVisible = (nodeId) => {
            const entry = this.nodeInstanceMap.get(nodeId);
            if (!entry) return false;
            const mesh = entry.isDoc ? this.docInstancedMesh : this.instInstancedMesh;
            const mat = new THREE.Matrix4();
            mesh.getMatrixAt(entry.index, mat);
            const s = new THREE.Vector3();
            mat.decompose(new THREE.Vector3(), new THREE.Quaternion(), s);
            return s.x > 0.001;
        };
        this._imageSprites.forEach((sprite, nodeId) => {
            sprite.visible = isInstanceVisible(nodeId);
            if (sprite.visible) {
                const pos = this._getNodePosition(nodeId);
                if (pos) sprite.position.copy(pos);
            }
        });
        this._extraSprites.forEach((arr, nodeId) => {
            arr.forEach(sprite => { sprite.visible = isInstanceVisible(nodeId); });
        });

        this._updateExtraConnectors(extraConnectorPositions);

        // Edge lines update
        if (this.linesMesh && this.edges && this.edges.length) {
            const positions = this.linesMesh.geometry.attributes.position.array;
            let i = 0;
            this.edges.forEach(e => {
                const sInit = this.initialNodeData.get(e.source);
                const tInit = this.initialNodeData.get(e.target);
                if (sInit && tInit) {
                    const sData = this.dataMap.get(e.source);
                    const collapseT = (sData && sData.doc_id) ? (this.docCollapseState.get(sData.doc_id) || 0) : 0;
                    const sPos = sInit.position.clone();
                    if (collapseT > 0) sPos.lerp(tInit.position, collapseT);
                    const tPos = tInit.position.clone();
                    sPos.applyMatrix4(spatialMatrix);
                    tPos.applyMatrix4(spatialMatrix);
                    positions[i++] = sPos.x; positions[i++] = sPos.y; positions[i++] = sPos.z;
                    positions[i++] = tPos.x; positions[i++] = tPos.y; positions[i++] = tPos.z;
                }
            });
            this.linesMesh.geometry.attributes.position.needsUpdate = true;
        }

        if (this.controls) this.controls.update();
        this.renderer.render(this.scene, this.camera);

        const targetId = this.selectedId || this.hoveredId;
        if (targetId && document.getElementById('billboard').style.display === 'block') {
            const pos = this._getNodePosition(targetId);
            if (pos) this.updateBillboardPosition({ position: pos });
        }
    }

    _updateExtraConnectors(positions) {
        if (!positions || positions.length === 0) {
            if (this._extraConnectorsMesh) this._extraConnectorsMesh.visible = false;
            return;
        }
        const posArr = new Float32Array(positions);
        if (!this._extraConnectorsMesh) {
            const geom = new THREE.BufferGeometry();
            geom.setAttribute('position', new THREE.BufferAttribute(posArr, 3));
            const mat = new THREE.LineBasicMaterial({
                color: 0x7d8b9a, transparent: true, opacity: 0.35,
            });
            this._extraConnectorsMesh = new THREE.LineSegments(geom, mat);
            this._extraConnectorsMesh.renderOrder = -1;
            this.scene.add(this._extraConnectorsMesh);
            return;
        }
        const attr = this._extraConnectorsMesh.geometry.getAttribute('position');
        if (!attr || attr.array.length !== posArr.length) {
            this._extraConnectorsMesh.geometry.dispose();
            const geom = new THREE.BufferGeometry();
            geom.setAttribute('position', new THREE.BufferAttribute(posArr, 3));
            this._extraConnectorsMesh.geometry = geom;
        } else {
            attr.array.set(posArr);
            attr.needsUpdate = true;
        }
        this._extraConnectorsMesh.visible = true;
    }

    // ====================== Billboard & Search ======================
    showBillboard(data, isLocked) {
        const billboard = document.getElementById('billboard');
        if (!billboard || !data) return;
        if (data.is_document) {
            this.hideBillboard();
            return;
        }
        const entry = this.nodeInstanceMap.get(data.id);
        let cssColor = '#60a5fa';
        let textColor = '#ffffff';
        if (entry) {
            const color = entry.originalColor;
            cssColor = `#${color.getHexString()}`;
            textColor = this.getContrastYIQ(color);
            billboard.style.borderLeft = `4px solid ${cssColor}`;
        }
        const title = document.getElementById('billboard-title');
        if (title) {
            title.textContent = this.shortenUrl(data.url || '');
            title.style.color = textColor;
        }
        const header = billboard.querySelector('.billboard-header');
        if (header) {
            header.style.backgroundColor = cssColor;
            header.style.color = textColor;
        }
        const closeBtn = document.getElementById('billboard-close');
        if (closeBtn) {
            closeBtn.style.color = textColor;
            closeBtn.onclick = () => {
                this.hideBillboard();
                this.selectedId = null;
                this.nodeInstanceMap.forEach((_, id) => this.restoreNodeVisuals(id));
            };
        }
        const pinBtn = document.getElementById('billboard-pin');
        if (pinBtn) {
            pinBtn.style.color = textColor;
            pinBtn.onclick = (ev) => {
                ev.stopPropagation();
                this.pinBillboard(data, cssColor, textColor);
            };
        }
        const link = document.getElementById('billboard-link');
        if (link) {
            link.href = data.url || '#';
            link.textContent = data.url || '';
        }
        this.renderBillboardMedia(data);
        const htmlPre = document.getElementById('billboard-html');
        if (htmlPre) {
            if (data.html_raw !== undefined) htmlPre.textContent = (data.html_raw || '').trim() || '(no HTML)';
            else htmlPre.innerHTML = '<span style="color:#6b7280;font-style:italic;">Click node to load HTML...</span>';
        }
        const textPre = document.getElementById('billboard-rendered-text');
        if (textPre) {
            if (data.rendered_text !== undefined) textPre.textContent = (data.rendered_text || '').trim() || '(no text)';
            else textPre.innerHTML = '<span style="color:#6b7280;font-style:italic;">Click node to load text...</span>';
        }
        const fieldsPre = document.getElementById('billboard-fields');
        if (fieldsPre) {
            if (data.fields === undefined) {
                fieldsPre.innerHTML = '<span style="color:#6b7280;font-style:italic;">Click node to load summary...</span>';
            } else {
                const fields = data.fields || {};
                const keys = Object.keys(fields);
                fieldsPre.textContent = keys.length ? keys.map(k => `${k}: ${JSON.stringify(fields[k])}`).join('\n') : '(no summary)';
            }
        }
        const xpathEl = document.getElementById('billboard-xpath');
        if (xpathEl) xpathEl.textContent = data.absolute_xpath || (data.is_document ? '' : 'Click node to load XPath...');
        const scoreEl = document.getElementById('billboard-score');
        if (scoreEl) {
            if (this.searchResults && this.searchResults.has(data.id)) {
                scoreEl.textContent = `${(this.searchResults.get(data.id) * 100).toFixed(1)}% match`;
                scoreEl.style.display = 'inline-block';
            } else {
                scoreEl.style.display = 'none';
            }
        }
        billboard.style.display = 'block';
        const pos = this._getNodePosition(data.id);
        if (pos) this.updateBillboardPosition({ position: pos });
    }

    hideBillboard() {
        const b = document.getElementById('billboard');
        if (b) b.style.display = 'none';
        this.hideBillboardArrow();
    }

    // Pinned-panel API: clones the current billboard payload into a
    _escapeHtml(s) {
        return String(s ?? '')
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    _renderPanelBody(data) {
        const html = (data.html_raw || '').trim();
        const txt = (data.rendered_text || '').trim();
        const xp = data.absolute_xpath || '';
        const linkHref = data.url || '#';
        return `
            <div style="font-family:monospace;font-size:10px;color:#9ca3af;margin-bottom:6px;word-break:break-all;">${this._escapeHtml(xp)}</div>
            <pre style="white-space:pre-wrap;word-break:break-word;background:rgba(0,0,0,0.25);padding:6px;border-radius:4px;max-height:180px;overflow:auto;font-size:10px;">${this._escapeHtml(html || '(no HTML)')}</pre>
            <div style="font-size:10px;color:#9ca3af;margin:6px 0 2px;">Rendered text</div>
            <pre style="white-space:pre-wrap;word-break:break-word;background:rgba(0,0,0,0.25);padding:6px;border-radius:4px;max-height:140px;overflow:auto;font-size:10px;">${this._escapeHtml(txt || '(no text)')}</pre>
            <div style="margin-top:6px;"><a href="${this._escapeHtml(linkHref)}" target="_blank" style="color:#60a5fa;font-size:10px;">Visit source</a></div>`;
    }

    _nextPanelZ() {
        let z = 10010;
        this._pinnedPanels.forEach(({ panel }) => {
            const cur = parseInt(panel.style.zIndex || '0', 10);
            if (cur > z) z = cur;
        });
        return z + 1;
    }

    _rebuildEdgesSoon() {
        if (this._rebuildEdgesTimer) return;
        this._rebuildEdgesTimer = setTimeout(() => {
            this._rebuildEdgesTimer = null;
            this.rebuildEdges();
        }, 200);
    }

    _requestUIUpdate() {
        if (this._uiUpdateTimer) return;
        this._uiUpdateTimer = setTimeout(() => {
            this._uiUpdateTimer = null;
            try {
                this.applyWorkspaceVisibility();
                this.renderFileTree();
                this.renderUrlBuckets();
            } catch (_) {}
        }, 800);
    }

    // free-standing draggable panel that lives outside the selection
    // lifecycle. Multiple nodes can stay on-screen simultaneously.
    pinBillboard(data, cssColor, textColor) {
        if (!data || !data.id) return;
        // Already pinned -> un-minimize + raise.
        const existing = this._pinnedPanels.get(data.id);
        if (existing) {
            if (existing.minimized) this._togglePanelMinimize(data.id);
            existing.panel.style.zIndex = String(this._nextPanelZ());
            return;
        }
        const host = document.getElementById('projector-panel') || document.body;
        const panel = document.createElement('div');
        panel.className = 'pinned-panel';
        panel.dataset.panelId = data.id;
        // Offset each new panel so they don't stack exactly on top.
        const n = this._pinnedPanels.size;
        panel.style.cssText =
            'position:absolute; z-index:' + this._nextPanelZ() + ';' +
            'top:' + (80 + n * 24) + 'px; left:' + (80 + n * 24) + 'px;' +
            'width:380px; max-height:70vh; overflow:hidden;' +
            'background:rgba(17,24,39,0.95); color:#e5e7eb;' +
            'border:1px solid rgba(255,255,255,0.1); border-radius:8px;' +
            'box-shadow:0 12px 32px rgba(0,0,0,0.45);' +
            'border-left:4px solid ' + (cssColor || '#60a5fa') + ';' +
            'display:flex; flex-direction:column; resize:both;';

        const title = (data.url || data.absolute_xpath || 'Pinned chunk').toString();
        const headerBg = cssColor || '#60a5fa';
        const headerFg = textColor || '#fff';
        panel.innerHTML = `
            <div class="pinned-panel-header" style="display:flex;align-items:center;justify-content:space-between;padding:6px 10px;background:${headerBg};color:${headerFg};cursor:move;user-select:none;">
                <span class="pinned-panel-title" style="font-family:monospace;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:260px;">${this._escapeHtml(this.shortenUrl(title))}</span>
                <span style="display:flex;gap:6px;">
                    <button class="pinned-panel-min" title="Minimize" style="background:none;border:none;color:${headerFg};cursor:pointer;font-size:12px;"><i class="fas fa-window-minimize"></i></button>
                    <button class="pinned-panel-close" title="Unpin" style="background:none;border:none;color:${headerFg};cursor:pointer;font-size:12px;"><i class="fas fa-times"></i></button>
                </span>
            </div>
            <div class="pinned-panel-body" style="padding:8px 10px;overflow:auto;flex:1;font-size:11px;">
                ${this._renderPanelBody(data)}
            </div>`;
        host.appendChild(panel);

        const entry = { panel, data, minimized: false, engaged: false, hovered: false };
        this._pinnedPanels.set(data.id, entry);

        // Hover over any pinned panel freezes the 3D motion so the user
        // can read without the world drifting underneath -- unless the
        // panel has been "engaged" (clicked into), in which case motion
        // resumes so the background stays alive while they read.
        panel.addEventListener('mouseenter', () => {
            entry.hovered = true;
            if (!entry.engaged) this._panelHoverCount++;
        });
        panel.addEventListener('mouseleave', () => {
            entry.hovered = false;
            if (!entry.engaged) {
                this._panelHoverCount = Math.max(0, this._panelHoverCount - 1);
            }
        });
        // Clicking into the panel body should NOT trigger the canvas click
        // handler that clears search/selection state.
        panel.addEventListener('click', (ev) => ev.stopPropagation());
        panel.addEventListener('mousedown', (ev) => ev.stopPropagation());
        // Click into the body = "I'm engaged" -> unfreeze the 3D motion.
        const bodyEl = panel.querySelector('.pinned-panel-body');
        if (bodyEl) {
            bodyEl.addEventListener('click', () => {
                if (!entry.engaged) {
                    entry.engaged = true;
                    if (entry.hovered) {
                        this._panelHoverCount = Math.max(0, this._panelHoverCount - 1);
                    }
                    panel.style.boxShadow = '0 12px 32px rgba(96,165,250,0.55)';
                }
            });
        }

        panel.querySelector('.pinned-panel-close').addEventListener('click', (ev) => {
            ev.stopPropagation();
            this.unpinPanel(data.id);
        });
        panel.querySelector('.pinned-panel-min').addEventListener('click', (ev) => {
            ev.stopPropagation();
            this._togglePanelMinimize(data.id);
        });
        this._makePanelDraggable(panel);
    }
    unpinPanel(id) {
        const entry = this._pinnedPanels.get(id);
        if (!entry) return;
        // Release any hover lock this panel was still holding so motion
        // doesn't stay frozen forever after an unpin-while-hovered.
        if (entry.hovered && !entry.engaged) {
            this._panelHoverCount = Math.max(0, this._panelHoverCount - 1);
        }
        if (entry.panel && entry.panel.parentNode) {
            entry.panel.parentNode.removeChild(entry.panel);
        }
        this._pinnedPanels.delete(id);
    }
    _togglePanelMinimize(id) {
        const entry = this._pinnedPanels.get(id);
        if (!entry) return;
        const body = entry.panel.querySelector('.pinned-panel-body');
        if (!body) return;
        entry.minimized = !entry.minimized;
        body.style.display = entry.minimized ? 'none' : '';
        entry.panel.style.resize = entry.minimized ? 'none' : 'both';
        entry.panel.style.height = entry.minimized ? 'auto' : '';
    }
    _makePanelDraggable(panel) {
        const header = panel.querySelector('.pinned-panel-header');
        if (!header) return;
        let startX = 0, startY = 0, origLeft = 0, origTop = 0, dragging = false;
        const onMove = (ev) => {
            if (!dragging) return;
            const dx = ev.clientX - startX;
            const dy = ev.clientY - startY;
            panel.style.left = (origLeft + dx) + 'px';
            panel.style.top = (origTop + dy) + 'px';
        };
        const onUp = () => {
            dragging = false;
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        };
        header.addEventListener('mousedown', (ev) => {
            // Clicks on the header buttons shouldn't start a drag.
            if (ev.target.closest('button')) return;
            dragging = true;
            startX = ev.clientX;
            startY = ev.clientY;
            const rect = panel.getBoundingClientRect();
            const hostRect = (panel.parentNode || document.body).getBoundingClientRect();
            origLeft = rect.left - hostRect.left;
            origTop = rect.top - hostRect.top;
            panel.style.zIndex = String(this._nextPanelZ());
            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);
            ev.preventDefault();
        });
    }

    updateBillboardPosition(meshOrObj) {
        const billboard = document.getElementById('billboard');
        const pos = meshOrObj?.position;
        if (!pos || !billboard) return;

        const panel = document.getElementById('projector-panel');
        const panelRect = panel ? panel.getBoundingClientRect() : { left: 0, top: 0, width: window.innerWidth, height: window.innerHeight };

        const vector = pos.clone();
        vector.project(this.camera);
        const x = (vector.x * 0.5 + 0.5) * panelRect.width + panelRect.left;
        const y = -(vector.y * 0.5 - 0.5) * panelRect.height + panelRect.top;
        const behindCamera = vector.z > 1 || vector.z < -1;
        const rect = billboard.getBoundingClientRect();
        const NODE_CLEARANCE_PX = 110;
        billboard.style.left = `${Math.min(panelRect.right - rect.width - 20, Math.max(panelRect.left + 20, x + NODE_CLEARANCE_PX))}px`;
        billboard.style.top = `${Math.min(panelRect.bottom - rect.height - 20, Math.max(panelRect.top + 20, y - rect.height / 2))}px`;

        const svg = document.getElementById('billboard-arrow-svg');
        const line = document.getElementById('billboard-arrow-line');
        if (svg && line) {
            const bbRect = billboard.getBoundingClientRect();
            const targetX = x, targetY = y;
            const bbLeft = bbRect.left, bbTop = bbRect.top;
            const bbRight = bbLeft + bbRect.width;
            const bbBottom = bbTop + bbRect.height;
            const cx = (bbLeft + bbRight) / 2, cy = (bbTop + bbBottom) / 2;
            let anchorX = cx, anchorY = cy;
            const dx = targetX - cx, dy = targetY - cy;
            if (dx !== 0 || dy !== 0) {
                const tX = dx > 0 ? (bbRight - cx) / dx : dx < 0 ? (bbLeft - cx) / dx : Infinity;
                const tY = dy > 0 ? (bbBottom - cy) / dy : dy < 0 ? (bbTop - cy) / dy : Infinity;
                const t = Math.max(0, Math.min(tX, tY));
                anchorX = cx + dx * t;
                anchorY = cy + dy * t;
            }
            const insideBillboard = targetX >= bbLeft && targetX <= bbRight && targetY >= bbTop && targetY <= bbBottom;
            if (behindCamera || insideBillboard) {
                svg.style.display = 'none';
            } else {
                svg.style.display = '';
                line.setAttribute('x1', anchorX);
                line.setAttribute('y1', anchorY);
                line.setAttribute('x2', targetX);
                line.setAttribute('y2', targetY);
                let cssColor = '#c0c0c0';
                const entry = this.nodeInstanceMap.get(this.selectedId || this.hoveredId);
                if (entry) cssColor = `#${entry.originalColor.getHexString()}`;
                line.setAttribute('stroke', cssColor);
                const markerPolygon = svg.querySelector('marker polygon');
                if (markerPolygon) markerPolygon.setAttribute('fill', cssColor);
            }
        }
    }

    // ====================== Sidebar + Search ======================
    initSidebar() {
        const style = document.createElement('style');
        style.innerHTML = `
            #rs-latch {
                position: fixed; top: 50%; right: 0px;
                background: var(--surface-base, #242933); border: 1px solid var(--border-light, #434c5e);
                border-right: none; color: var(--text-secondary, #d8dee9); padding: 20px 6px; cursor: pointer;
                z-index: 9999; border-radius: 8px 0 0 8px;
                transition: background-color 0.15s;
                box-shadow: -4px 0 6px rgba(0,0,0,0.1); display: flex;
                align-items: center; justify-content: center;
            }
            #rs-latch:hover { color: var(--text-primary, #eceff4); background: var(--surface-hover, #3b4252); }
        `;
        document.head.appendChild(style);

        const latch = document.createElement('div');
        latch.id = 'rs-latch';
        latch.title = "Toggle Search Panel";
        latch.innerHTML = '<i class="fas fa-chevron-right" style="transition: transform 0.3s ease;"></i>';
        document.body.appendChild(latch);

        latch.addEventListener('click', () => {
            // Mirror image of the left latch: ``#sidebar`` is now
            // ``position: absolute; right: 0`` (see styles.css), so it
            // does NOT consume flex space in ``#container``. The 3D
            // canvas always fills the full container width, and the
            // panel slides in/out via ``transform`` over top of it.
            // This keeps the canvas size CONSTANT through the animation
            // (the previous ``marginRight: -width`` flex-collapse was
            // the source of the "background unnecessarily resized"
            // complaint).
            const panel = document.getElementById('sidebar');
            if (!panel) return;

            if (!panel.classList.contains('sidebar-sliding')) panel.classList.add('sidebar-sliding');

            // Cache the natural width once so the collapse animation has a
            // stable target even after we've blown out ``offsetWidth`` via
            // transform on subsequent clicks.
            if (!panel.dataset.originalWidth || parseInt(panel.dataset.originalWidth) === 0) {
                if (panel.offsetWidth > 0) panel.dataset.originalWidth = panel.offsetWidth;
            }
            const width = parseInt(panel.dataset.originalWidth) || 350;

            const isCollapsed = panel.dataset.collapsed === 'true';
            const icon = latch.querySelector('i');

            if (isCollapsed) {
                panel.style.transform = '';
                panel.style.opacity = '1';
                panel.style.pointerEvents = '';
                icon.style.transform = 'rotate(0deg)';
                panel.dataset.collapsed = 'false';
            } else {
                // +10px extra so the box-shadow also clears the viewport.
                panel.style.transform = `translateX(${width + 10}px)`;
                panel.style.opacity = '0';
                // While collapsed, ignore clicks on the (off-screen) panel
                // so it can't eat events for UI now visible underneath.
                panel.style.pointerEvents = 'none';
                icon.style.transform = 'rotate(180deg)';
                panel.dataset.collapsed = 'true';
            }

            // Canvas size doesn't actually change (sidebar is absolute-
            // positioned), but the billboard-arrow SVG and other overlays
            // listen for resize and it's cheap to fire — kept symmetric
            // with the left latch.
            let start = Date.now();
            let timer = setInterval(() => {
                window.dispatchEvent(new Event('resize'));
                if (Date.now() - start > 350) clearInterval(timer);
            }, 16);
        });

        const input = document.getElementById('nl-search');
        if (!input) return;
        input.placeholder = 'Search chunk contents...';

        let lastFired = 0;
        let lastQuery = null;
        let debounceTimer = null;

        const fire = (force = false) => {
            const q = input.value.trim();
            if (!q) {
                if (lastQuery !== '') {
                    this.clearSearch();
                    lastQuery = '';
                }
                return;
            }
            if (!force && q === lastQuery) return;
            lastQuery = q;
            const ts = Date.now();
            lastFired = ts;
            this.triggerSearch(q, ts, () => lastFired, null);
        };

        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                clearTimeout(debounceTimer);
                fire(true);
            }
        });

        // Trigger on input with debounce instead of blur to prevent click-race conditions
        input.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => fire(false), 400);
        });
    }
    clearSearch() {
        this.searchResults = null;
        this.lastSearchPayload = null;
        this.selectedId = null;
        this.hideBillboard();
        this.nodeInstanceMap.forEach((_, id) => this.restoreNodeVisuals(id));
        this.renderUrlBuckets();
    }

    async triggerSearch(query, ts, stillFreshest, urlFilter = null) {
        // identical to original, but uses this.nodeInstanceMap to collect visible URLs
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
                    instance_limit_per_page: 50
                })
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (stillFreshest && stillFreshest() !== ts) return;
            this.lastSearchPayload = data;
            this.renderSearchResults(data, urlFilter);
        } catch (e) {
            console.error("[ChunkProjector] search failed", e);
            if (container) container.innerHTML = `<div class="empty-state">Search failed: ${this.escape(e.message)}</div>`;
        }
    }

    renderSearchResults(payload, activeUrlFilter = null) {
        const container = document.getElementById('results-container');
        if (!container) return;
        const pages = payload.pages || [];
        if (pages.length === 0) {
            container.innerHTML = '<div class="empty-state">No matches.</div>';
            this.searchResults = null;
            this.nodeInstanceMap.forEach((_, id) => this.restoreNodeVisuals(id));
            return;
        }

        if (activeUrlFilter && pages.length > 0) {
            // Full instance drilldown
            const page = pages[0];
            const doc_id = `doc_${page.url}`;
            this.docCollapseTarget.set(doc_id, 0);
            const headColor = this.avgPageColor(page.instances);
            const html = `
                <div class="bucket-heading">
                    <button id="back-to-search" style="margin-right:10px; cursor:pointer; background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.2); color:#fff; padding:2px 8px; border-radius:4px;">&larr; Back</button>
                    Instances on ${this.escape(this.shortenUrl(page.url))}
                </div>
                ${this.pageCardHtml(page, headColor, page.instances.length)}
            `;
            container.innerHTML = html;
            document.getElementById('back-to-search').onclick = () => {
                this.triggerSearch(payload.query, Date.now(), null, null);
            };
            const flat = [];
            flat.push({ id: doc_id, score: page.score });
            (page.instances || []).forEach(i => {
                flat.push({ id: i.id, score: i.score });
                if (this.dataMap.has(i.id)) this.dataMap.set(i.id, { ...this.dataMap.get(i.id), ...i });
            });
            this.update3DVisualsFromResults(flat);

            container.querySelectorAll('.instance-row').forEach(row => {
                const id = row.dataset.id;
                row.addEventListener('click', (e) => { if (!e.target.closest('a')) this.selectNode(id); });
                row.addEventListener('mouseenter', () => {
                    this.hoveredId = id;
                    const entry = this.nodeInstanceMap.get(id);
                    if (entry && id !== this.selectedId) {
                        const hlColor = entry.originalColor.clone().multiplyScalar(1.5);
                        this._setInstanceColor(id, hlColor);
                    }
                });
                row.addEventListener('mouseleave', () => {
                    if (this.hoveredId === id) this.hoveredId = null;
                    if (id !== this.selectedId) this.restoreNodeVisuals(id);
                });
            });
        } else {
            // URL ranking view
            const parts = [`<div class="bucket-heading">
                ${pages.length} page${pages.length === 1 ? '' : 's'} &middot; query "${this.escape(payload.query || '')}"
            </div>`];
            pages.forEach(page => {
                const pct = (page.score * 100).toFixed(1);
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
                parts.push(`
                    <div class="page-card" data-url="${dataUrl}" style="cursor:pointer;border-left:4px solid var(--accent-pastel, #88c0d0);margin-bottom:8px;padding:10px;background:var(--surface-elevated, #2e3440);border-radius:4px;" onclick="app.triggerSearch('${this.escape(payload.query)}', Date.now(), null, ['${this.escape(page.url)}'])">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <span title="${this.escape(page.url)}" style="font-weight:bold;color:#fff;">${this.escape(urlShort)}</span>
                            <span style="color:#9ca3af;">${pct}%</span>
                        </div>
                        ${snippetHtml}
                    </div>`);
            });
            container.innerHTML = parts.join('');

            container.querySelectorAll('.page-card').forEach(card => {
                const docId = `doc_${card.dataset.url}`;
                card.addEventListener('mouseenter', () => {
                    this.hoveredId = docId;
                    const entry = this.nodeInstanceMap.get(docId);
                    if (entry && docId !== this.selectedId) {
                        const hlColor = entry.originalColor.clone().multiplyScalar(1.5);
                        this._setInstanceColor(docId, hlColor);
                    }
                });
                card.addEventListener('mouseleave', () => {
                    if (this.hoveredId === docId) this.hoveredId = null;
                    if (docId !== this.selectedId) this.restoreNodeVisuals(docId);
                });
            });

            const flat = [];
            pages.forEach(p => {
                const doc_id = `doc_${p.url}`;
                this.docCollapseTarget.set(doc_id, 0);
                flat.push({ id: doc_id, score: p.score });
                (p.instances || []).forEach(i => {
                    flat.push({ id: i.id, score: i.score });
                    if (this.dataMap.has(i.id)) this.dataMap.set(i.id, { ...this.dataMap.get(i.id), ...i });
                });
            });
            this.update3DVisualsFromResults(flat);
        }
    }

    pageCardHtml(page, headColor, limit = 50) {
        const insts = (page.instances || []).slice(0, limit);
        const rows = insts.map(i => {
            const entry = this.nodeInstanceMap.get(i.id);
            let chip = '';
            if (entry) chip = `<span class="node-color-chip" style="background:#${entry.originalColor.getHexString()}"></span>`;
            const textSnippet = i.rendered_text ? this.escape(i.rendered_text.slice(0, 300)) : '';
            let textDisplay;
            if (i.rendered_text !== undefined) {
                textDisplay = textSnippet || '<span style="color:#6b7280;font-style:italic;">(no text)</span>';
            } else {
                textDisplay = '<span style="color:#6b7280;font-style:italic;">Click node to load contents...</span>';
            }
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
    }

    showChunksForUrl(url, items) {
        const container = document.getElementById('results-container');
        if (!container) return;
        const doc_id = `doc_${url}`;
        this.docCollapseTarget.set(doc_id, 0);
        const flat = items.map(i => ({ id: i.id, score: 1.0 }));
        flat.push({ id: doc_id, score: 1.0 });
        this.update3DVisualsFromResults(flat);

        const page = {
            url: url,
            score: 1.0,
            instance_count: items.length,
            instances: items.map(i => {
                if (this.dataMap.has(i.id)) this.dataMap.set(i.id, { ...this.dataMap.get(i.id), ...i });
                return { id: i.id, score: 1.0, absolute_xpath: i.absolute_xpath, html_raw: i.html_raw, rendered_text: i.rendered_text };
            })
        };
        const headColor = this.avgPageColor(page.instances);
        const html = `
            <div class="bucket-heading">
                <button id="back-to-buckets" style="margin-right:10px;cursor:pointer;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);color:#fff;padding:2px 8px;border-radius:4px;">&larr; Back</button>
                ${items.length} chunks on ${this.escape(this.shortenUrl(url))}
            </div>
            ${this.pageCardHtml(page, headColor, items.length)}
        `;
        container.innerHTML = html;
        document.getElementById('back-to-buckets').addEventListener('click', () => this.clearSearch());

        container.querySelectorAll('.instance-row').forEach(row => {
            const id = row.dataset.id;
            row.addEventListener('click', (e) => { if (!e.target.closest('a')) this.selectNode(id); });
            row.addEventListener('mouseenter', () => {
                this.hoveredId = id;
                const entry = this.nodeInstanceMap.get(id);
                if (entry && id !== this.selectedId) {
                    const hlColor = entry.originalColor.clone().multiplyScalar(1.5);
                    this._setInstanceColor(id, hlColor);
                }
            });
            row.addEventListener('mouseleave', () => {
                if (this.hoveredId === id) this.hoveredId = null;
                if (id !== this.selectedId) this.restoreNodeVisuals(id);
            });
        });
    }

    avgPageColor(instances) {
        let r = 0, g = 0, b = 0, n = 0;
        (instances || []).forEach(i => {
            const entry = this.nodeInstanceMap.get(i.id);
            if (entry) {
                const c = entry.originalColor;
                r += c.r; g += c.g; b += c.b;
                n += 1;
            }
        });
        if (n === 0) return '#60a5fa';
        return `#${new THREE.Color(r / n, g / n, b / n).getHexString()}`;
    }

    /**
     * Walk ``htmlRaw`` for media and return a deduped list of absolute
     * URLs classified by type. Heuristics MUST stay in sync with
     * ``backend/dom/content_tagger.py`` so that every image the backend
     * tags actually replaces its sphere with a billboard in the 3D view.
     *
     * Mirrors content_tagger.py:
     *   - _IMAGE_EXTS / _VIDEO_EXTS / _AUDIO_EXTS extension sets
     *   - data:image|video|audio/ URI prefix detection
     *   - URL-bearing attributes: href, src, data-src, data-lazy-src,
     *     action, formaction, poster, data-original, data-original-src,
     *     data-image, srcset
     *   - CSS background-image via inline style url(...)
     *   - Element-tag tagging (img/picture/svg/canvas → image,
     *     video/source/track → video, audio → audio)
     *
     * Parses via a detached DOMParser document so browsing the fragment
     * does not trigger network fetches -- loads only happen once the
     * thumbs are stamped into the billboard DOM.
     */
    extractMediaFromHtml(htmlRaw, pageUrl) {
        if (!htmlRaw) return [];
        const out = [];
        const seen = new Set();
        const classifyMedia = (url) => this._classifyMediaUrl(url);
        const push = (type, src, alt) => {
            if (!src) return;
            let resolved = src;
            try {
                resolved = new URL(src, pageUrl || window.location.href).href;
            } catch (e) {
                return;
            }
            if (seen.has(resolved)) return;
            seen.add(resolved);
            out.push({ type, src: resolved, alt: alt || '' });
        };

        let doc;
        try {
            // Wrap in <html><body>...</body></html> so even a raw <column>
            // fragment (tarot.com's content-distilled markup) parses.
            doc = new DOMParser().parseFromString(
                `<!DOCTYPE html><html><body>${htmlRaw}</body></html>`,
                'text/html'
            );
        } catch (e) {
            return [];
        }

        const URL_ATTRS = [
            'href', 'src', 'data-src', 'data-lazy-src',
            'action', 'formaction', 'poster',
            'data-original', 'data-original-src', 'data-image',
        ];

        // 1. Element-tag-based tagging -- matches content_tagger.py §2.5.
        //    Every <img>/<picture>/<svg>/<canvas> is tagged as image even
        //    if its src is missing; we then try to recover a URL from any
        //    attribute on the element. Same for <video>/<source>/<track>
        //    and <audio>.
        const walk = (selector, defaultType, altAttrs) => {
            doc.querySelectorAll(selector).forEach(el => {
                const alt = (altAttrs || []).reduce(
                    (acc, a) => acc || el.getAttribute(a) || '', ''
                );
                URL_ATTRS.forEach(a => {
                    const v = el.getAttribute(a);
                    if (!v) return;
                    const low = v.trim().toLowerCase();
                    if (low.startsWith('javascript:') ||
                        low.startsWith('mailto:') ||
                        low.startsWith('tel:')) return;
                    const mediaType = classifyMedia(v) || defaultType;
                    if (mediaType) push(mediaType, v, alt);
                });
                // srcset -- each candidate contributes a URL.
                const ss = el.getAttribute('srcset');
                if (ss) {
                    ss.split(',').forEach(part => {
                        const u = part.trim().split(/\s+/)[0];
                        if (!u) return;
                        const mediaType = classifyMedia(u) || defaultType;
                        if (mediaType) push(mediaType, u, alt);
                    });
                }
            });
        };

        walk('img, picture, svg, canvas', 'image', ['alt', 'title', 'aria-label']);
        walk('video', 'video', ['title', 'aria-label']);
        walk('source', null, []); // type inferred from URL ext or parent
        walk('track', 'video', []);
        walk('audio', 'audio', ['title', 'aria-label']);

        // <source> inside <video>/<audio> inherits parent type when URL
        // extension is unrecognized.
        doc.querySelectorAll('source').forEach(s => {
            const parent = s.parentElement && s.parentElement.tagName.toLowerCase();
            const fallback = parent === 'audio' ? 'audio'
                : parent === 'video' ? 'video' : 'image';
            URL_ATTRS.forEach(a => {
                const v = s.getAttribute(a);
                if (!v) return;
                push(classifyMedia(v) || fallback, v, '');
            });
        });

        // <video> poster -- always an image thumbnail.
        doc.querySelectorAll('video[poster]').forEach(v => {
            push('image', v.getAttribute('poster'), v.getAttribute('title') || 'video poster');
        });

        // 2. Scan every element's URL-bearing attrs so cards that hide
        //    their thumb behind a <div data-image="...">, <a data-original=...>,
        //    or similar get picked up too. Matches content_tagger.py §4c.
        URL_ATTRS.forEach(attr => {
            doc.querySelectorAll(`[${attr}]`).forEach(el => {
                const v = el.getAttribute(attr);
                if (!v) return;
                const low = v.trim().toLowerCase();
                if (low.startsWith('javascript:') ||
                    low.startsWith('mailto:') ||
                    low.startsWith('tel:')) return;
                const mediaType = classifyMedia(v);
                if (!mediaType) return; // only keep if ext identifies media
                const alt = el.getAttribute('alt')
                    || el.getAttribute('title')
                    || el.getAttribute('aria-label') || '';
                push(mediaType, v, alt);
            });
        });

        // 3. Inline-style background images (content_tagger.py §4 style block).
        doc.querySelectorAll('[style]').forEach(el => {
            const style = el.getAttribute('style');
            if (!style || !/url\(/i.test(style)) return;
            const clean = style.replace(/&quot;/g, '"');
            const re = /url\(\s*['"]?([^'"\)]+)['"]?\s*\)/gi;
            let m;
            while ((m = re.exec(clean)) !== null) {
                const u = (m[1] || '').trim();
                if (!u) continue;
                const mediaType = classifyMedia(u) || 'image'; // CSS url() in practice is always a thumb
                const alt = el.getAttribute('alt')
                    || el.getAttribute('aria-label') || '';
                push(mediaType, u, alt);
            }
        });

        return out.slice(0, 8); // cap the strip so layout stays tight
    }

    /**
     * Mirror of backend ``_classify_media`` in content_tagger.py -- returns
     * ``'image'`` / ``'video'`` / ``'audio'`` / null based on URL extension
     * or data: URI prefix. The returned type uses singular form matching
     * what ``extractMediaFromHtml`` emits (backend uses plural subcats like
     * 'images', the frontend uses 'image' because the sprite code keys off
     * ``m.type === 'image'``).
     */
    _classifyMediaUrl(url) {
        if (!url) return null;
        const u = url.trim();
        if (u.startsWith('data:image/')) return 'image';
        if (u.startsWith('data:video/')) return 'video';
        if (u.startsWith('data:audio/')) return 'audio';
        const clean = u.split('?')[0].split('#')[0].toLowerCase();
        const m = clean.match(/\.([a-z0-9]{2,5})(?:[?#]|$)/);
        if (!m) return null;
        const ext = '.' + m[1];
        if (ChunkProjector.IMAGE_EXTS.has(ext)) return 'image';
        if (ChunkProjector.VIDEO_EXTS.has(ext)) return 'video';
        if (ChunkProjector.AUDIO_EXTS.has(ext)) return 'audio';
        return null;
    }

    renderBillboardMedia(data) {
        const section = document.getElementById('billboard-media-section');
        const strip = document.getElementById('billboard-media');
        if (!section || !strip) return;
        const media = this.extractMediaFromHtml(data.html_raw, data.url);
        if (media.length === 0) {
            section.style.display = 'none';
            strip.innerHTML = '';
            return;
        }
        section.style.display = 'block';
        strip.innerHTML = media.map(m => {
            const safe = this.escape(m.src);
            const alt = this.escape(m.alt || 'chunk media');
            if (m.type === 'video') {
                return `<a class="billboard-media-cell" href="${safe}" target="_blank" title="${safe}">
                    <video class="billboard-media-video" src="${safe}" muted playsinline preload="metadata"></video>
                    <span class="billboard-media-badge"><i class="fas fa-play"></i></span>
                </a>`;
            }
            return `<a class="billboard-media-cell" href="${safe}" target="_blank" title="${safe}">
                <img class="billboard-media-thumb" src="${safe}" alt="${alt}" loading="lazy"
                     onerror="this.closest('.billboard-media-cell').style.display='none';">
            </a>`;
        }).join('');
    }

    // ====================== Snapshot trigger with WS-first polling ======================
    initSnapshot() {
        const btn = document.getElementById('snapshot-btn');
        if (btn) {
            btn.addEventListener('click', () => this.triggerScan());
            const umapBtn = document.createElement('button');
            umapBtn.id = 'recompute-umap-btn';
            umapBtn.innerHTML = '<i class="fas fa-project-diagram"></i> Recompute UMAP';
            umapBtn.style.marginLeft = '10px';
            umapBtn.style.padding = '6px 12px';
            umapBtn.style.background = 'rgba(96,165,250,0.15)';
            umapBtn.style.border = '1px solid #60a5fa';
            umapBtn.style.color = '#60a5fa';
            umapBtn.style.borderRadius = '4px';
            umapBtn.style.cursor = 'pointer';
            umapBtn.addEventListener('click', async () => {
                umapBtn.disabled = true;
                const origHtml = umapBtn.innerHTML;
                umapBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Recomputing...';
                this.setLoadingProgress("Recomputing UMAP projection across all chunks...", 10);
                try {
                    const res = await fetch('/api/recompute_umap', { method: 'POST' });
                    if (!res.ok) throw new Error(`HTTP ${res.status}`);
                    await this.loadNodes();
                } catch (e) {
                    console.error("[ChunkProjector] UMAP Recompute failed", e);
                    alert("Failed to recompute UMAP: " + e.message);
                } finally {
                    umapBtn.disabled = false;
                    umapBtn.innerHTML = origHtml;
                    this.hideLoadingProgress();
                }
            });
            btn.parentNode.insertBefore(umapBtn, btn.nextSibling);
        }
    }

    setScanStatus(text, color) {
        const el = document.getElementById('scan-status');
        if (!el) return;
        if (!text) {
            el.style.display = 'none';
            el.textContent = '';
            return;
        }
        el.style.display = 'inline';
        el.style.color = color || '#93c5fd';
        el.textContent = text;
    }

    async triggerScan() {
        const btn = document.getElementById('snapshot-btn');
        if (!btn) return;
        btn.disabled = true;
        const origHtml = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scanning';
        this.setScanStatus('dispatching…', '#93c5fd');

        // Clear the scene so a new scan starts from a clean slate — prevents
        // duplicate spheres when the user triggers a second scan mid-stream.
        this._clearAllInstances();
        if (this._pinnedPanels && this._pinnedPanels.size) {
            Array.from(this._pinnedPanels.keys()).forEach(id => this.unpinPanel(id));
            this._panelHoverCount = 0;
        }
        this.edges = [];
        this.domainTree.clear();
        if (this.linesMesh) {
            this.scene.remove(this.linesMesh);
            if (this.linesMesh.geometry) this.linesMesh.geometry.dispose();
            if (this.linesMesh.material) this.linesMesh.material.dispose();
            this.linesMesh = null;
        }

        const preIds = new Set(this.dataMap.keys());
        this.setLoadingProgress("Initiating live browser scan...", 10);

        let settled = false;
        let wsFailed = false;
        let ws = null;
        let wsCleanup = () => { };

        try {
            const res = await fetch('/api/snapshot', { method: 'GET' });
            if (!res.ok && res.status !== 202) {
                const body = await res.text().catch(() => '');
                throw new Error(`HTTP ${res.status} ${body || ''}`);
            }

            const dispatch = await res.json().catch(() => ({}));
            const wsId = dispatch.snapshot_ws_id ?? dispatch.snapshot_id ?? null;
            const wsPath = dispatch.ws_url || (wsId !== null ? `/api/ws/nodes/${wsId}` : null);
            const dispatchedUrl = dispatch.url || null;
            if (dispatchedUrl) { try { this.addUrlToActiveWorkspace(dispatchedUrl); } catch (_) { } }

            this.setScanStatus('scan running…', '#93c5fd');
            this.setLoadingProgress("Extracting and distilling DOM...", 30);

            let scanDone = false;
            let doneResolver;
            const donePromise = new Promise(r => { doneResolver = r; });
            let verifiedChunkResolver;
            let verifiedChunkPromise = new Promise(r => { verifiedChunkResolver = r; });
            const _kickVerified = () => { try { verifiedChunkResolver(); } catch (_) { } verifiedChunkPromise = new Promise(r => { verifiedChunkResolver = r; }); };

            if (wsPath) {
                try {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const wsUrl = `${protocol}//${window.location.host}${wsPath}`;
                    ws = new WebSocket(wsUrl);
                    ws.onmessage = (event) => {
                        try {
                            const frame = JSON.parse(event.data);
                            const t = frame && frame.type;
                            if (t === 'stats') {
                                this._updateStatsOverlay(frame);
                                this.setScanStatus(`streaming… ${frame.deltas_verified || 0} verified chunks, ${frame.nodes_streamed || 0} nodes`, '#34d399');
                            } else if (t === 'log') {
                                this._appendLogLine(frame);
                            } else if (t === 'chunk_removed' && frame.chunk_id) {
                                const removedId = frame.chunk_id;
                                if (this.nodeInstanceMap.has(removedId)) {
                                    this._removeNodeInstance(removedId);
                                    // nodeInstanceMap.delete already called by _freeInstance inside _removeNodeInstance
                                }
                            } else if (t === 'chunk_added' && frame.chunk) {
                                const ch = frame.chunk;
                                const cid = ch.chunk_id;
                                if (cid && !this.nodeInstanceMap.has(cid)) {
                                    const row = {
                                        id: cid,
                                        url: frame.url || '',
                                        is_document: false,
                                        doc_id: frame.url ? `doc_${frame.url}` : '',
                                    };
                                    this.addNodesIncrementally([row], { quiet: true });
                                }
                            } else if (t === 'chunk_replaced' && frame.chunk) {
                                const ch = frame.chunk;
                                const cid = ch.chunk_id;
                                if (cid && this.nodeInstanceMap.has(cid)) {
                                    const inst = this.nodeInstanceMap.get(cid);
                                    if (inst && inst.userData) {
                                        inst.userData.chunk = ch;
                                    }
                                } else if (cid) {
                                    const row = {
                                        id: cid,
                                        url: frame.url || '',
                                        is_document: false,
                                        doc_id: frame.url ? `doc_${frame.url}` : '',
                                    };
                                    this.addNodesIncrementally([row], { quiet: true });
                                }
                            } else if (t === 'chunks_partial' && Array.isArray(frame.chunks)) {
                                _kickVerified();
                            } else if (t === 'chunk_instances_partial' && Array.isArray(frame.instances)) {
                                const rows = frame.instances
                                    .filter(i => i && i.instance_id)
                                    .map(i => ({
                                        id: i.instance_id,
                                        url: frame.url || '',
                                        is_document: false,
                                        doc_id: frame.url ? `doc_${frame.url}` : '',
                                    }));
                                if (rows.length) {
                                    this.addNodesIncrementally(rows, { quiet: true });
                                if (!this._pendingIndexRows) this._pendingIndexRows = [];
                                this._pendingIndexRows.push(...rows);
                                }
                        } else if (t === 'instances_indexed') {
                            if (this._pendingIndexRows && this._pendingIndexRows.length > 0) {
                                this._lazyLoadAllNodeDetails(this._pendingIndexRows);
                                this._pendingIndexRows = [];
                            }
                            } else if (t === 'cached') {
                                this.setScanStatus('cached — page unchanged since last scan', '#a78bfa');
                                this.setLoadingProgress('Page unchanged — using cached snapshot', 100);
                            } else if (t === 'done') {
                                scanDone = true;
                                try {
                                    this.applyWorkspaceVisibility();
                                    this.renderFileTree();
                                    this.renderUrlBuckets();
                                } catch (_) { }
                                try { doneResolver(); } catch (_) { }
                            }
                        } catch (_e) { /* ignore */ }
                    };
                    ws.onerror = () => { wsFailed = true; };
                    ws.onclose = () => { if (!scanDone) wsFailed = true; };
                    wsCleanup = () => { try { ws && ws.close(); } catch (_) { } };
                } catch (_e) {
                    wsFailed = true;
                }
            } else {
                wsFailed = true;
            }

            const pollStart = Date.now();
            const POLL_CAP_MS = 5 * 60 * 1000;
            const _idsEqual = (a, b) => {
                if (a.size !== b.size) return false;
                for (const k of a) if (!b.has(k)) return false;
                return true;
            };
            let lastLoadedIds = new Set(preIds);
            let stablePollCount = 0;

            const reloadIfChanged = async (label) => {
                try {
                    const nodes = await fetch('/api/chunk_nodes').then(r => r.json());
                    const liveIds = new Set((nodes && nodes.nodes ? nodes.nodes : []).map(n => n.id));
                    const changed = !_idsEqual(liveIds, lastLoadedIds);
                    if (!changed) return false;
                    this.setLoadingProgress(`Reloading scene… (${label})`, 90);
                    await this.loadNodes();
                    lastLoadedIds = new Set(this.dataMap.keys());
                    return true;
                } catch (e) { return false; }
            };

            while (Date.now() - pollStart < POLL_CAP_MS) {
                if (wsFailed) {
                    await new Promise(r => setTimeout(r, 1500));
                    if (scanDone) { await reloadIfChanged('final'); settled = true; break; }
                    const changed = await reloadIfChanged('progress');
                    if (changed) {
                        stablePollCount = 0;
                    } else {
                        stablePollCount++;
                        if (stablePollCount >= 20) {
                            await reloadIfChanged('stable');
                            settled = true;
                            break;
                        }
                    }
                } else {
                    await Promise.race([
                        donePromise,
                        new Promise(r => setTimeout(r, 10000))
                    ]);
                    if (scanDone) {
                        await reloadIfChanged('final');
                        settled = true;
                        break;
                    }
                    wsFailed = true; // fallback to polling if WS stalls
                }
            }

            wsCleanup();
            if (!settled) {
                this.setScanStatus('scan incomplete — check server', '#fbbf24');
            } else {
                setTimeout(() => this.setScanStatus(''), 4000);
            }
        } catch (err) {
            console.error('[ChunkProjector] scan failed', err);
            this.setScanStatus(`scan failed: ${err.message || err}`, '#f87171');
            this.setLoadingProgress("Scan failed", 100);
            setTimeout(() => this.hideLoadingProgress(), 1000);
        } finally {
            if (!settled) this.hideLoadingProgress();
            btn.disabled = false;
            btn.innerHTML = origHtml;
        }
    }

    // ------------------------------------------------------------------
    // Utilities
    // ------------------------------------------------------------------

    shortenUrl(url) {
        try {
            const u = new URL(url);
            const path = u.pathname.length > 32 ? u.pathname.slice(0, 32) + '...' : u.pathname;
            return `${u.host}${path}${u.search ? '?...' : ''}`;
        } catch {
            return (url || '').slice(0, 64);
        }
    }

    shortenXpath(xpath) {
        if (!xpath) return '';
        const parts = xpath.split('/').filter(Boolean);
        if (parts.length <= 4) return xpath;
        return '/' + parts.slice(0, 2).join('/') + '/.../' + parts.slice(-2).join('/');
    }

    escape(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
}

window.addEventListener('DOMContentLoaded', () => {
    if (typeof THREE === 'undefined') {
        console.error("[ChunkProjector] THREE is not loaded");
        const box = document.createElement('div');
        box.style.cssText = 'position:fixed;top:20px;left:20px;background:#300;color:#fff;padding:20px;z-index:9999;';
        box.textContent = 'THREE.js failed to load. Check network.';
        document.body.appendChild(box);
        return;
    }
    window.app = new ChunkProjector();
});