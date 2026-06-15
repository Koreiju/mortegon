/* chunk_projector.js -- UMAP-based 3D projector over ``ChunkInstance`` rows.
 *
 * Adapted from ``old_projector_user_interface/ui/static/js/projector.js``
 * (the Flask company-discovery reference) but pointed at our Kuzu DB +
 * nomic-v1 GPU embedder via three new FastAPI endpoints:
 *
 *   GET  /api/chunk_nodes            -- UMAP 6D, one node per instance
 *   GET  /api/chunk_details/{id}     -- full row for the billboard
 *   POST /api/chunk_search           -- coarse-to-fine NL retrieval
 *
 * Differences from the Company reference:
 *   - No status (yes/no/unreviewed), no tag filters, no status buttons.
 *     Every node is "unreviewed" -- spectral color rotation applies
 *     uniformly.
 *   - Billboard displays the content-distilled ``html_raw`` as read-only
 *     text inside a <pre>, plus the rendered-markdown-lite text. This is
 *     the "chunk collage" control space the user asked for: every node's
 *     true payload is its HTML blob, addressable by vector similarity.
 *   - Search results are paginated by URL: each page card contains a
 *     nested list of its top matching instances, matching the
 *     coarse-to-fine drill-down in ``chunk_retrieval.retrieve_with_drilldown``.
 */

console.log("[ChunkProjector] Script loaded");


class ChunkProjector {
    // Media extension sets -- MUST mirror _IMAGE_EXTS / _VIDEO_EXTS /
    // _AUDIO_EXTS in backend/dom/content_tagger.py. If the backend list
    // changes, update these too so nodes tagged as images by the tagger
    // always get a sprite billboard in the 3D view.
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

        // Data -- id is ChunkInstance.instance_id.
        this.nodes = new Map();            // id -> THREE.Mesh
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
        this.detailsFetchQueue = new Set();
        this._imageSprites = new Map();

        // Pinned detached billboards (multi-panel UX).
        this._pinnedPanels = new Map(); // id -> { panel, data, minimized }
        this._panelHoverCount = 0;      // >0 freezes 3D motion

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

        // Snow-globe + spectral-color rotation constants (ported verbatim).
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

    initMaroniteTheme() {
        document.body.style.overflowX = 'hidden';
        const style = document.createElement('style');
        style.innerHTML = `
            @font-face {
                font-family: 'VHS';
                src: url('/static/vhs.ttf') format('truetype');
            }
            
            @keyframes rainbow-text {
                0%   { color: #ff5555; }
                16%  { color: #ffff55; }
                33%  { color: #55ff55; }
                50%  { color: #55ffff; }
                66%  { color: #5555ff; }
                83%  { color: #ff55ff; }
                100% { color: #ff5555; }
            }

            @keyframes rainbow-bg {
                0%   { background-color: #ff5555; }
                16%  { background-color: #ffff55; }
                33%  { background-color: #55ff55; }
                50%  { background-color: #55ffff; }
                66%  { background-color: #5555ff; }
                83%  { background-color: #ff55ff; }
                100% { background-color: #ff5555; }
            }

            :root {
                --surface-base: #000000;
                --surface-elevated: #111111;
                --surface-hover: #000080;
                --border-light: #c0c0c0;
                --text-primary: #c0c0c0;
                --text-secondary: #808080;
                --text-muted: #666666;
                --accent-pastel: #0000ff;
                --accent-pastel-green: #00ff00;
                --radius-md: 0px;
                --radius-sm: 0px;
                --shadow-soft: none;
            }

            body, input, button, .sidebar, .panel, #history-container, #results-container, #billboard, #wfh-loader-box, .empty-state, .bucket-heading {
                font-family: 'VHS', 'VCR OSD Mono', 'Courier New', monospace !important;
                text-transform: uppercase !important;
                letter-spacing: 1px !important;
                text-shadow: none !important;
                -webkit-text-stroke: 0 !important;
            }

            *, body, input, button, a, .instance-score, .page-score, .url-bucket-count, .instance-xpath, .ft-url-label, .instance-text, .billboard-header, #billboard-title, #billboard pre, #billboard code {
                animation: rainbow-text 4s linear infinite !important;
            }

            #wfh-loader-bar {
                animation: rainbow-bg 4s linear infinite !important;
            }

            /* Solid panels, no transparency, Web 1.0 borders */
            .sidebar, .panel, .panel-left, .panel-right, #left-panel, #right-panel, .side-panel, #history-container, #results-container, #billboard, #wfh-loader-box, #rs-latch, #ft-latch {
                background: var(--surface-base) !important;
                background-color: var(--surface-base) !important;
                backdrop-filter: none !important;
                -webkit-backdrop-filter: none !important;
                border: 3px ridge var(--border-light) !important;
                border-radius: var(--radius-md) !important;
                box-shadow: var(--shadow-soft) !important;
                box-sizing: border-box !important;
            }
            
            .sidebar #history-container, .sidebar #results-container {
                border: none !important;
                box-shadow: none !important;
                animation: none !important;
            }

            #rs-latch { border-right: none !important; border-top-right-radius: 0 !important; border-bottom-right-radius: 0 !important; }
            #ft-latch { border-left: none !important; border-top-left-radius: 0 !important; border-bottom-left-radius: 0 !important; }

            /* Strip out pseudo-element effects from old theme */
            .sidebar::after, #billboard::after, #wfh-loader-box::after, body::after, .sidebar::before, #billboard::before, #wfh-loader-box::before, body::before {
                display: none !important;
                content: none !important;
                animation: none !important;
                background: none !important;
            }

            /* Clean interactive components */
            .result-card, .instance-row, .page-card, .url-bucket, .bucket-heading, .ft-item, .ft-items, .ft-folder-title, .ft-header-main {
                background: transparent !important;
                border-color: var(--border-light) !important;
            }

            input {
                background: #000000 !important;
                border: 2px inset #ffffff !important;
                border-radius: var(--radius-sm) !important;
                padding: 6px 10px;
                box-sizing: border-box;
                font-family: 'VHS', 'VCR OSD Mono', 'Courier New', monospace !important;
            }
            
            input:focus {
                border-color: var(--accent-pastel) !important;
                outline: none;
            }

            button {
                background: #000000 !important;
                border: 2px outset #ffffff !important;
                border-radius: var(--radius-sm) !important;
                cursor: pointer;
                font-family: 'VHS', 'VCR OSD Mono', 'Courier New', monospace !important;
                font-weight: bold;
                padding: 2px 6px;
            }
            button:active {
                border: 2px inset #ffffff !important;
            }
            
            #ft-latch, #rs-latch {
                animation: none !important;
            }

            /* Hover states (rainbow highlight) */
            .instance-row:hover, .page-card.clickable-card:hover, .url-bucket:hover, .ft-item:hover, .ft-folder-title:hover, button:hover {
                border-color: var(--border-light) !important;
                transform: none !important;
                filter: none !important;
                animation: rainbow-bg 4s linear infinite !important;
            }

            #rs-latch:hover, #ft-latch:hover {
                border-color: var(--border-light) !important;
                animation: rainbow-bg 4s linear infinite !important;
            }

            .instance-row:hover *, .page-card.clickable-card:hover *, .url-bucket:hover *, .ft-item:hover *, .ft-folder-title:hover *, button:hover *, #rs-latch:hover *, #ft-latch:hover * {
                color: #ffffff !important;
                text-shadow: none !important;
                animation: none !important;
            }
            
            /* Classic Links */
            a { text-decoration: underline; }

            /* Text specifics */
            .instance-score, .page-score, .url-bucket-count { font-weight: normal; }
            
            /* Billboard and special UI resets */
            #billboard { padding: 0 !important; overflow: hidden; z-index: 10005 !important; }
            .billboard-header { 
                background: #000000 !important; 
                border-bottom: 2px ridge var(--border-light) !important; 
                padding: 4px 8px; 
                font-family: 'VHS', 'VCR OSD Mono', 'Courier New', monospace !important;
                font-weight: bold;
            }
            #billboard-title { font-weight: bold; font-size: 14px; }
            .billboard-content { padding: 15px; }
            #billboard pre, #billboard code { 
                background: #000000 !important; 
                border: 2px inset #888 !important; 
                border-radius: 0 !important; 
                padding: 8px;
                font-family: 'VHS', 'VCR OSD Mono', 'Courier New', monospace !important;
            }
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
        `;
        document.body.insertAdjacentHTML('beforeend', barHtml);
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

    // ------------------------------------------------------------------
    // Setup
    // ------------------------------------------------------------------

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
            // Use setTimeout to allow click events to process with the current isDragging state
            setTimeout(() => { this.isDragging = false; }, 0);
        });

        canvas.addEventListener('mouseleave', () => {
            if (this.hoveredId) {
                if (this.hoveredId !== this.selectedId) {
                    const prev = this.nodes.get(this.hoveredId);
                    if (prev) this.restoreNodeVisuals(prev);
                }
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
        if (THREE.RGBFormat) texture.format = THREE.RGBFormat;

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
        const vFOV = THREE.MathUtils
            ? THREE.MathUtils.degToRad(this.camera.fov)
            : THREE.Math.degToRad(this.camera.fov);
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
        const yiq = (threeColor.r * 255 * 299
                   + threeColor.g * 255 * 587
                   + threeColor.b * 255 * 114) / 1000;
        return yiq >= 128 ? '#000000' : '#ffffff';
    }

    // ------------------------------------------------------------------
    // Node loading
    // ------------------------------------------------------------------

    async loadNodes() {
        this.setLoadingProgress("Fetching chunks from DB...", 10);
        try {
            const res = await fetch('/api/chunk_nodes');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            this.setLoadingProgress("Parsing chunk data...", 30);
            const data = await res.json();
            console.log(`[ChunkProjector] Loaded ${data.count} chunk nodes`);

            if (!data.nodes || data.nodes.length === 0) {
                document.getElementById('results-container').innerHTML =
                    '<div class="empty-state">No embedded chunks in DB yet.<br>'
                    + 'Enter a URL in the <strong>Scan</strong> field at the '
                    + 'top and click Scan to populate the projector.</div>';
                this.renderFileTree();
                this.renderUrlBuckets();
                this.hideLoadingProgress();
                return;
            }

            this.setLoadingProgress("Clearing previous scene...", 40);
            this.nodes.forEach(m => this.scene.remove(m));
            this.nodes.clear();
            // Purge image-billboard sprites from the previous snapshot too.
            // Each sprite's position was driven through the now-removed
            // mesh's ``userData.imageSprite`` pointer, so if we kept the
            // sprite but rebuilt meshes, the sprite would orphan in place
            // (freeze) while the new graph animates around it. We dispose
            // the texture+material and clear the cache so
            // ``_spawnImageBillboards`` is free to re-create a fresh sprite
            // attached to the new mesh.
            if (this._imageSprites) {
                this._imageSprites.forEach(sprite => {
                    this.scene.remove(sprite);
                    if (sprite.material) {
                        if (sprite.material.map) sprite.material.map.dispose();
                        sprite.material.dispose();
                    }
                });
                this._imageSprites.clear();
            }
            if (this._extraSprites) {
                this._extraSprites.forEach(arr => {
                    arr.forEach(sprite => {
                        this.scene.remove(sprite);
                        if (sprite.material) {
                            if (sprite.material.map) sprite.material.map.dispose();
                            sprite.material.dispose();
                        }
                    });
                });
                this._extraSprites.clear();
            }
            // Connector lines that tether extra sprites to their parent
            // mesh are rebuilt per-frame; drop the mesh here so we don't
            // carry vertices from a previous snapshot.
            if (this._extraConnectorsMesh) {
                this.scene.remove(this._extraConnectorsMesh);
                if (this._extraConnectorsMesh.geometry) this._extraConnectorsMesh.geometry.dispose();
                if (this._extraConnectorsMesh.material) this._extraConnectorsMesh.material.dispose();
                this._extraConnectorsMesh = null;
            }
            // Tear down any pinned panels tied to the previous snapshot.
            if (this._pinnedPanels && this._pinnedPanels.size) {
                Array.from(this._pinnedPanels.keys()).forEach(id => this.unpinPanel(id));
                this._panelHoverCount = 0;
            }
            this.dataMap.clear();
            this.initialNodeData.clear();
            this.edges = [];

            // Use larger geometry for page/document nodes to keep them distinct
            const docGeometry = new THREE.SphereGeometry(0.35, 16, 16);
            const instGeometry = new THREE.SphereGeometry(0.18, 16, 16);
            const box = new THREE.Box3();

            this.setLoadingProgress(`Building 3D objects for ${data.nodes.length} chunks...`, 60);
            data.nodes.forEach(node => {
                const umapColor = new THREE.Vector3(node.r, node.g, node.b);
                const activeColor = new THREE.Color(node.r, node.g, node.b);

                const material = new THREE.MeshPhongMaterial({
                    color: activeColor,
                    emissive: 0x000000,
                    emissiveIntensity: 0,
                    shininess: 30,
                    transparent: true,
                    opacity: 1
                });

                const geometryToUse = node.is_document ? docGeometry : instGeometry;
                const mesh = new THREE.Mesh(geometryToUse, material);
                const initialPos = new THREE.Vector3(node.x, node.y, node.z);
                mesh.position.copy(initialPos);
                box.expandByPoint(mesh.position);

                mesh.userData = {
                    id: node.id,
                    originalColor: activeColor.clone(),
                    baseUmapColor: umapColor
                };

                this.initialNodeData.set(node.id, {
                    position: initialPos,
                    umapColor: umapColor
                });

                this.scene.add(mesh);
                this.nodes.set(node.id, mesh);
                this.dataMap.set(node.id, node);
            });

            // Draw edges tracing chunk instances back to their document nodes
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
            // Build Domain Tree from loaded nodes
            this.domainTree.clear();
            this.dataMap.forEach(n => {
                if (!n.url) return;
                let domain = 'Unknown';
                try { domain = new URL(n.url).hostname; } catch (e) {}
                if (!this.domainTree.has(domain)) this.domainTree.set(domain, new Set());
                this.domainTree.get(domain).add(n.url);
            });

            this.applyWorkspaceVisibility();
            this.renderFileTree();
            this.renderUrlBuckets();

            this.setLoadingProgress("Ready", 100);
            setTimeout(() => this.hideLoadingProgress(), 400);
            
            this._spawnImageBillboards(data.nodes);
            this._lazyLoadAllNodeDetails(data.nodes);

        } catch (e) {
            this.setLoadingProgress("Failed to load chunks", 100);
            setTimeout(() => this.hideLoadingProgress(), 1000);
            console.error("[ChunkProjector] Failed to load chunk nodes", e);
            alert("Failed to load chunk nodes. See console.");
            this.renderFileTree();
        }
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

    /**
     * Rebuild the connector LineSegments that tether every extra
     * sprite to its parent node. Called once per animation frame from
     * ``animate()`` with a flat positions array already laid out as
     * ``[A.xyz, B.xyz, A.xyz, B.xyz, ...]`` for three.js LineSegments.
     *
     * We reuse the same BufferAttribute across frames when the vertex
     * count is stable (which is the common case — extras spawn at load
     * time and don't change), and only reallocate when the count
     * changes (image texture finished loading, snapshot reloaded,
     * etc.). That keeps the per-frame cost to a single ``set()`` +
     * ``needsUpdate = true`` in the steady state.
     */
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
            // Draw under the regular edges so the tree backbone stays
            // readable while the tethers just fill in the image halo.
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

    _spawnImageBillboards(nodes) {
        if (!this._imageSprites) this._imageSprites = new Map();
        if (!this._extraSprites) this._extraSprites = new Map();
        if (!this._imageTextureCache) this._imageTextureCache = new Map();
        if (!this._imageProxyFailures) this._imageProxyFailures = new Set();
        const loader = new THREE.TextureLoader();
        // Textures sourced via ``/api/image_proxy`` always come back with
        // ``Access-Control-Allow-Origin: *`` so WebGL can sample them;
        // ``crossOrigin = 'anonymous'`` is required for the browser to
        // even send the request through the CORS path.
        loader.crossOrigin = 'anonymous';

        // Rewrite any same-origin absolute URL onto the backend image
        // proxy. Most source pages don't serve CORS on their static
        // assets so a raw TextureLoader call silently fails with
        // "Cross-origin image loading" — the billboard <img> still works
        // (display doesn't require CORS) but the 3D sphere replacement
        // depends on GL-sampling the pixels, which does. Routing through
        // ``/api/image_proxy`` side-steps the problem for every source.
        const toProxy = (absUrl) => {
            if (!absUrl) return absUrl;
            try {
                const u = new URL(absUrl, window.location.href);
                // Data/blob URIs don't go through the network, skip proxy.
                if (u.protocol === 'data:' || u.protocol === 'blob:') return absUrl;
                // Same-origin already CORS-safe. Skip proxy to avoid a
                // needless round trip (and to let the browser cache do
                // its job on app assets).
                if (u.origin === window.location.origin) return absUrl;
                return `/api/image_proxy?url=${encodeURIComponent(u.href)}`;
            } catch (_e) {
                return absUrl;
            }
        };

        nodes.forEach(node => {
            if (this._imageSprites.has(node.id) || node.is_document) return;

            // Collect ALL image URLs associated with this node so tail/head
            // resources adjacent to the chunk's primary image still become
            // billboards instead of disappearing. The primary ``image_url``
            // (set by the backend when available) always comes first so the
            // main sprite lands exactly on the node center; additional
            // images from the chunk's html_raw fan out around it.
            //
            // Always resolve against ``node.url`` so relative paths
            // (``Images/frames.gif``, classic HTML4-style pages like
            // visual-memory.co.uk) don't accidentally load against our
            // backend origin. Skipping resolution there was why some img
            // billboards failed silently — three.js TextureLoader ran
            // against ``document.baseURI`` (``http://localhost:8080/``)
            // instead of the snapshot's source page.
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

            urls.forEach((imgUrl, idx) => {
                const fetchUrl = toProxy(imgUrl);
                loader.load(
                    fetchUrl,
                    (texture) => {
                        const mesh = this.nodes.get(node.id);
                        const initData = this.initialNodeData.get(node.id);
                        if (!mesh || !initData) { texture.dispose(); return; }
                        // Only the very first sprite replaces the mesh; the
                        // rest orbit it. This keeps hover / click / glow
                        // logic that keys on ``isImageBillboard`` working
                        // unchanged while still surfacing every image.
                        const isPrimary = idx === 0;
                        if (isPrimary && mesh.userData.isImageBillboard) return;

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
                        // Ring offset stored on the sprite so the render
                        // loop can apply ``spatialMatrix`` to the parent
                        // node's initial position then translate by this
                        // offset -- extras stay glued to their parent node
                        // instead of orphaning mid-rotation.
                        let offsetX = 0, offsetY = 0;
                        if (!isPrimary) {
                            // Fan extras in a small ring around the node so
                            // they don't z-fight. Radius scales with sprite
                            // count so a chunk with many images doesn't
                            // collapse into a clump.
                            const extraCount = Math.max(1, urls.length - 1);
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
                            offsetX,
                            offsetY,
                        };

                        if (isPrimary) {
                            mesh.visible = false;
                            mesh.userData.imageSprite = sprite;
                            mesh.userData.isImageBillboard = true;
                            this._imageSprites.set(node.id, sprite);

                            if (this.searchResults && this.searchResults.has(node.id)) {
                                this.applySearchGlow(mesh, this.searchResults.get(node.id));
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
                        // First failure path: the proxy itself errored
                        // (timeout, 502, or the original URL was bad).
                        // If we were already using the proxy, try one
                        // direct fetch as a fallback in case the source
                        // happens to serve CORS — otherwise log and drop.
                        if (this._imageProxyFailures.has(fetchUrl)) return;
                        this._imageProxyFailures.add(fetchUrl);
                        if (fetchUrl === imgUrl) {
                            // Was already direct. Nothing else to try.
                            if (!this._loggedImageFailures) this._loggedImageFailures = 0;
                            if (this._loggedImageFailures < 5) {
                                console.warn(
                                    "[ChunkProjector] Image texture failed:",
                                    imgUrl,
                                );
                                this._loggedImageFailures++;
                            }
                            return;
                        }
                        // Try direct as last-ditch — only helps for
                        // sources that DO set Access-Control-Allow-Origin
                        // themselves (e.g. Wikipedia, some CDNs).
                        loader.load(
                            imgUrl,
                            (texture) => {
                                const mesh = this.nodes.get(node.id);
                                const initData = this.initialNodeData.get(node.id);
                                if (!mesh || !initData) { texture.dispose(); return; }
                                const isPrimary = idx === 0;
                                if (isPrimary && mesh.userData.isImageBillboard) return;
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
                                    const extraCount = Math.max(1, urls.length - 1);
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
                                    mesh.visible = false;
                                    mesh.userData.imageSprite = sprite;
                                    mesh.userData.isImageBillboard = true;
                                    this._imageSprites.set(node.id, sprite);
                                    if (this.searchResults && this.searchResults.has(node.id)) {
                                        this.applySearchGlow(mesh, this.searchResults.get(node.id));
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
                                    console.warn(
                                        "[ChunkProjector] Image texture failed (proxy+direct):",
                                        imgUrl,
                                    );
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
        const batchSize = 10;
        for (let i = 0; i < nodes.length; i += batchSize) {
            const batch = nodes.slice(i, i + batchSize);
            await Promise.all(batch.map(async n => {
                if (n.is_document) return;
                const cached = this.dataMap.get(n.id);
                if (cached && cached.html_raw !== undefined) return;
                await this.fetchNodeDetails(n.id, false);
            }));
            
            const resolvedBatch = batch.map(n => this.dataMap.get(n.id)).filter(Boolean);
            this._spawnImageBillboards(resolvedBatch);
            
            await new Promise(r => setTimeout(r, 50));
        }
    }

    // ------------------------------------------------------------------
    // File Tree & Workspace Management
    // ------------------------------------------------------------------

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

        const getPanel = (containerId, selectors) => {
            const container = document.getElementById(containerId);
            if (!container) return null;
            let panel = container.closest(selectors);
            if (!panel) {
                let curr = container;
                while (curr.parentElement && curr.parentElement.tagName !== 'BODY' && curr.parentElement.tagName !== 'MAIN') {
                    curr = curr.parentElement;
                }
                panel = curr;
            }
            return panel;
        };

        latch.addEventListener('click', () => {
            const panel = getPanel('history-container', '.sidebar, aside, .panel, #left-panel, .panel-left, .side-panel');
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

            // The left history panel is ``position: absolute`` (see index.html)
            // so it does NOT take up flex space in ``#container``. We animate
            // it with ``transform: translateX`` to slide the WHOLE panel off
            // the left edge of the viewport — that's the "sweep outward"
            // visual. The old code animated ``width: 0`` instead, which kept
            // the left edge anchored at 0 while the right edge moved leftward
            // and the contents folded inward toward the left edge. That read
            // as "panel closing inward" and was the bug the user reported.
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
        } catch (e) {}
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
            // Attempt backend deletion (fails gracefully if endpoint doesn't exist yet)
            await fetch(`/api/map/snapshots?url=${encodeURIComponent(url)}`, { method: 'DELETE' });
        } catch(e) {
            console.warn('DB delete fetch failed', e);
        }

        // Cleanup local state immediately
        const toDelete = [];
        this.nodes.forEach((mesh, id) => {
            const data = this.dataMap.get(id);
            if (data && data.url === url) {
                toDelete.push(id);
                this.scene.remove(mesh);
                if (mesh.geometry) mesh.geometry.dispose();
                if (mesh.material) mesh.material.dispose();
            }
        });
        
        toDelete.forEach(id => {
            this.nodes.delete(id);
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

        this.nodes.forEach((mesh, id) => {
            const data = this.dataMap.get(id);
            if (data && visibleSet.has(data.url)) {
                if (mesh.userData.isImageBillboard && mesh.userData.imageSprite) {
                    mesh.visible = false;
                    mesh.userData.imageSprite.visible = true;
                    mesh.userData.imageSprite.material.opacity = 1.0;
                } else {
                    mesh.visible = true;
                    mesh.material.opacity = 1.0;
                }
                mesh.material.transparent = true;
                mesh.userData.isPreview = false;
            } else {
                mesh.visible = false;
                if (mesh.userData.imageSprite) mesh.userData.imageSprite.visible = false;
            }
        });
        // Don't clobber the results panel while a search is active — the
        // user is still looking at their matches. Re-render buckets only
        // when there's no live query and no payload to preserve.
        const input = document.getElementById('nl-search');
        const searchActive = !!(input && input.value.trim()) || !!this.lastSearchPayload;
        if (searchActive && this.lastSearchPayload) {
            this.renderSearchResults(this.lastSearchPayload);
        } else {
            this.renderUrlBuckets();
        }
    }

    previewUrl(url) {
        this.nodes.forEach((mesh, id) => {
            const data = this.dataMap.get(id);
            if (data && data.url === url) {
                if (!mesh.visible && (!mesh.userData.isImageBillboard || !mesh.userData.imageSprite.visible)) {
                    if (mesh.userData.isImageBillboard && mesh.userData.imageSprite) {
                        mesh.userData.imageSprite.visible = true;
                        mesh.userData.imageSprite.material.opacity = 0.2;
                    } else {
                        mesh.visible = true;
                        mesh.material.opacity = 0.2;
                    }
                    mesh.material.transparent = true;
                    mesh.userData.isPreview = true;
                }
            }
        });
    }

    clearPreview() {
        this.nodes.forEach((mesh) => {
            if (mesh.userData.isPreview) {
                mesh.visible = false;
                mesh.material.opacity = 1.0;
                mesh.userData.isPreview = false;
                if (mesh.userData.imageSprite) {
                    mesh.userData.imageSprite.visible = false;
                    mesh.userData.imageSprite.material.opacity = 1.0;
                }
            }
        });
    }

    renderUrlBuckets() {
        const container = document.getElementById('results-container');
        if (!container) return;
        const byUrl = new Map();
        this.nodes.forEach((mesh, id) => {
            if (!mesh.visible) return;
            const data = this.dataMap.get(id);
            if (!data || !data.url) return;
            
            // Normalize URL to prevent duplicates (strip trailing slash and query string)
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

        const visibleCount = Array.from(this.nodes.values()).filter(m => m.visible).length;
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

        // Bind clicks to expand the bucket
        container.querySelectorAll('.url-bucket').forEach(el => {
            const url = el.dataset.url;
            el.addEventListener('click', () => {
                let targetItems = [];
                const normClicked = url.split('?')[0].replace(/\/+$/, "");
                if (byUrl.has(normClicked)) {
                    targetItems = byUrl.get(normClicked).items;
                }
                if (targetItems.length > 0) {
                    this.showChunksForUrl(url, targetItems);
                }
            });
            const docId = `doc_${url}`;
            el.addEventListener('mouseenter', () => {
                this.hoveredId = docId;
                const mesh = this.nodes.get(docId);
                if (mesh && docId !== this.selectedId) {
                    mesh.material.emissiveIntensity = 1.0;
                    mesh.material.opacity = 1.0;
                    mesh.scale.setScalar(1.8);
                }
            });
            el.addEventListener('mouseleave', () => {
                if (this.hoveredId === docId) this.hoveredId = null;
                const mesh = this.nodes.get(docId);
                if (mesh && docId !== this.selectedId) this.restoreNodeVisuals(mesh);
            });
        });
    }

    // ------------------------------------------------------------------
    // Interaction
    // ------------------------------------------------------------------

    getIntersects(event) {
        if (!this.renderer || !this.camera) return [];
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        this.raycaster.setFromCamera(this.mouse, this.camera);
        const visibleNodes = [];
        this.nodes.forEach((mesh) => {
            if (mesh.userData.isImageBillboard && mesh.userData.imageSprite) {
                if (mesh.userData.imageSprite.visible) {
                    visibleNodes.push(mesh.userData.imageSprite);
                }
            } else if (mesh.visible) {
                visibleNodes.push(mesh);
            }
        });
        return this.raycaster.intersectObjects(visibleNodes);
    }

    onMouseMove(event) {
        const intersects = this.getIntersects(event);
        if (intersects.length > 0) {
            let object = intersects[0].object;
            const id = object.userData.id;
            const mesh = this.nodes.get(id);
            if (mesh) object = mesh;

            if (this.hoveredId !== id) {
                if (this.hoveredId && this.hoveredId !== this.selectedId) {
                    const prev = this.nodes.get(this.hoveredId);
                    if (prev) this.restoreNodeVisuals(prev);
                }
                this.hoveredId = id;
                document.body.style.cursor = 'pointer';
                if (id !== this.selectedId) {
                    object.material.emissiveIntensity = 1.0;
                    object.material.opacity = 1.0;
                    object.scale.setScalar(1.8);
                    if (object.userData.isImageBillboard && object.userData.imageSprite) {
                        const sprite = object.userData.imageSprite;
                        sprite.scale.set(sprite.userData.baseScaleX * 1.8, sprite.userData.baseScaleY * 1.8, 1);
                    }
                }
                if (!this.selectedId) {
                    const data = this.dataMap.get(id);
                    this.showBillboard(data, false);
                    if (data && !data.is_document && data.html_raw === undefined) {
                        this.fetchNodeDetails(id, false);
                    }
                }
            }
        } else if (this.hoveredId) {
            if (this.hoveredId !== this.selectedId) {
                const prev = this.nodes.get(this.hoveredId);
                if (prev) this.restoreNodeVisuals(prev);
            }
            if (!this.selectedId) this.hideBillboard();
            this.hoveredId = null;
            document.body.style.cursor = 'default';
        }
    }

    async onClick(event) {
        if (this.isDragging) return;
        const intersects = this.getIntersects(event);
        if (intersects.length > 0) {
            const mesh = intersects[0].object;
            await this.selectNode(mesh.userData.id);
        } else {
            // Click on background -- deselect the current node but preserve
            // the search panel and node-highlights if the user still has a
            // query in the input box. The query staying visible means they
            // expect to keep refining — don't wipe their results out from
            // under them.
            const input = document.getElementById('nl-search');
            const searchActive = !!(input && input.value.trim());
            this.selectedId = null;
            if (!searchActive) this.searchResults = null;
            this.hideBillboard();
            this.nodes.forEach(m => this.restoreNodeVisuals(m));
            this.applyWorkspaceVisibility();
        }
    }

    restoreNodeVisuals(mesh) {
        const id = mesh.userData.id;
        if (this.searchResults && this.searchResults.has(id)) {
            this.applySearchGlow(mesh, this.searchResults.get(id));
        } else {
            mesh.material.color.copy(mesh.userData.originalColor);
            mesh.material.emissive.setHex(0x000000);
            mesh.material.emissiveIntensity = 0;
            mesh.material.opacity = 1;
            mesh.scale.setScalar(1);
            
            if (mesh.userData.isImageBillboard && mesh.userData.imageSprite) {
                const sprite = mesh.userData.imageSprite;
                sprite.material.color.setHex(0xffffff);
                sprite.material.opacity = 1;
                sprite.scale.set(sprite.userData.baseScaleX, sprite.userData.baseScaleY, 1);
            }
        }
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

    async selectNode(id) {
        const cached = this.dataMap.get(id);

        if (cached && cached.is_document) {
            // Toggle collapse target for this document
            const currentTarget = this.docCollapseTarget.get(id) || 0;
            this.docCollapseTarget.set(id, currentTarget === 1 ? 0 : 1);
        }

        if (this.selectedId && this.selectedId !== id) {
            const prev = this.nodes.get(this.selectedId);
            if (prev) this.restoreNodeVisuals(prev);
        }
        this.selectedId = id;
        const mesh = this.nodes.get(id);
        if (mesh) {
            mesh.material.emissive.setHex(0xffffff);
            mesh.material.emissiveIntensity = 0.5;
            mesh.scale.setScalar(1.5);
            mesh.material.opacity = 1;
            
            if (mesh.userData.isImageBillboard && mesh.userData.imageSprite) {
                mesh.visible = false;
                const sprite = mesh.userData.imageSprite;
                sprite.material.color.setHex(0xffaaaa);
                sprite.scale.set(sprite.userData.baseScaleX * 1.5, sprite.userData.baseScaleY * 1.5, 1);
            } else {
                mesh.visible = true;
            }
        }

        if (cached && cached.is_document) {
            this.hideBillboard();
            return; // Skip detail fetch for document centroids
        }

        if (cached) this.showBillboard(cached, true);
        
        if (cached && !cached.is_document && cached.html_raw === undefined) {
            await this.fetchNodeDetails(id, true);
        }
    }

    applySearchGlow(mesh, score) {
        mesh.material.emissive.copy(mesh.userData.originalColor);
        const safe = Math.max(0, Math.min(1, score));
        mesh.material.emissiveIntensity = 0.2 + safe * 0.4;
        mesh.material.opacity = 0.8;
        mesh.scale.setScalar(1 + safe * 0.3);
        
        if (mesh.userData.isImageBillboard && mesh.userData.imageSprite) {
            const sprite = mesh.userData.imageSprite;
            sprite.material.color.copy(mesh.userData.originalColor);
            sprite.material.opacity = 0.8 + safe * 0.2;
            sprite.scale.set(
                sprite.userData.baseScaleX * (1 + safe * 0.3),
                sprite.userData.baseScaleY * (1 + safe * 0.3),
                1
            );
        }
    }

    update3DVisualsFromResults(results) {
        // Dim everything first...
        this.nodes.forEach(mesh => {
            if (mesh.userData.id === this.selectedId) return;
            mesh.material.color.copy(mesh.userData.originalColor);
            mesh.material.emissive.setHex(0x000000);
            mesh.material.emissiveIntensity = 0;
            mesh.scale.setScalar(1);
            mesh.material.opacity = 0.15;
            
            if (mesh.userData.isImageBillboard && mesh.userData.imageSprite) {
                const sprite = mesh.userData.imageSprite;
                sprite.material.color.setHex(0xffffff);
                sprite.material.opacity = 0.15;
                sprite.scale.set(sprite.userData.baseScaleX, sprite.userData.baseScaleY, 1);
            }
        });
        // ...then glow the hits.
        this.searchResults = new Map();
        results.forEach(r => {
            this.searchResults.set(r.id, r.score);
            const mesh = this.nodes.get(r.id);
            if (mesh && r.id !== this.selectedId) {
                this.applySearchGlow(mesh, r.score);
                if (!mesh.userData.isImageBillboard) mesh.material.opacity = 1;
                else mesh.userData.imageSprite.material.opacity = 1;
            }
        });
    }

    // ------------------------------------------------------------------
    // Animation
    // ------------------------------------------------------------------

    animate() {
        requestAnimationFrame(() => this.animate());

        // Perfect 60fps latch tracking bound tightly to physical container rects
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

        let linesNeedUpdate = false;
        this.docCollapseTarget.forEach((target, doc_id) => {
            let current = this.docCollapseState.get(doc_id) || 0;
            if (current !== target) {
                linesNeedUpdate = true;
                if (current < target) {
                    current = Math.min(1, current + delta * 4);
                } else {
                    current = Math.max(0, current - delta * 4);
                }
                this.docCollapseState.set(doc_id, current);
            }
        });

        // Collected during the node pass below so we can build a single
        // LineSegments mesh tethering every extra sprite to its parent
        // node. Without this, sprites spawned from ``html_raw`` (extras
        // that ring a primary billboard) have no visible link back into
        // the graph and look like free-floating images drifting above
        // the chunk cluster.
        const extraConnectorPositions = [];

        this.nodes.forEach((mesh, id) => {
            const init = this.initialNodeData.get(id);
            if (!init) return;
            
            const data = this.dataMap.get(id);
            const localPos = init.position.clone();

            if (data && !data.is_document && data.doc_id) {
                const collapseT = this.docCollapseState.get(data.doc_id) || 0;
                if (collapseT > 0) {
                    const docInit = this.initialNodeData.get(data.doc_id);
                    if (docInit) localPos.lerp(docInit.position, collapseT);
                }
            }

            const newPos = localPos.applyMatrix4(spatialMatrix);
            mesh.position.copy(newPos);

            if (mesh.userData.isImageBillboard && mesh.userData.imageSprite) {
                mesh.userData.imageSprite.position.copy(newPos);
            }
            // Extra billboards (html_raw-extracted images that fan around
            // the primary) must also follow the rotated center so they
            // don't appear to "float free" while the rest of the structure
            // rotates. Apply the same spatial matrix then re-add the local
            // ring offset that was baked at load time.
            if (this._extraSprites) {
                const extras = this._extraSprites.get(id);
                if (extras && extras.length) {
                    for (const spr of extras) {
                        spr.position.copy(newPos);
                        spr.position.x += spr.userData.offsetX || 0;
                        spr.position.y += spr.userData.offsetY || 0;
                        // Parent → extra tether. Pushed in pairs
                        // (A.xyz, B.xyz) so the aggregated buffer can go
                        // straight into a LineSegments geometry.
                        extraConnectorPositions.push(
                            newPos.x, newPos.y, newPos.z,
                            spr.position.x, spr.position.y, spr.position.z,
                        );
                    }
                }
            }

            // Spectral color rotation: recenter around 0.5, rotate, snap
            // back, clamp. Every chunk gets it (no status cohort here).
            const centered = init.umapColor.clone().subScalar(0.5);
            centered.applyMatrix4(colorMatrix);
            centered.addScalar(0.5);
            centered.x = Math.max(0, Math.min(1, centered.x));
            centered.y = Math.max(0, Math.min(1, centered.y));
            centered.z = Math.max(0, Math.min(1, centered.z));
            const newColor = new THREE.Color(centered.x, centered.y, centered.z);
            mesh.userData.originalColor.copy(newColor);

            mesh.material.color.copy(newColor);

            if (this.selectedId === id) {
                mesh.material.emissive.setHex(0xffffff);
            } else if (this.hoveredId === id || (this.searchResults && this.searchResults.has(id))) {
                mesh.material.emissive.copy(newColor);
            } else {
                mesh.material.emissive.setHex(0x000000);
            }
        });

        this._updateExtraConnectors(extraConnectorPositions);

        if (linesNeedUpdate && this.linesMesh && this.edges && this.edges.length > 0) {
            const positions = this.linesMesh.geometry.attributes.position.array;
            let i = 0;
            this.edges.forEach(e => {
                const sData = this.dataMap.get(e.source);
                const collapseT = (sData && sData.doc_id) ? (this.docCollapseState.get(sData.doc_id) || 0) : 0;
                const sInit = this.initialNodeData.get(e.source);
                const tInit = this.initialNodeData.get(e.target);
                
                if (sInit && tInit) {
                    const sPos = sInit.position.clone();
                    if (collapseT > 0) sPos.lerp(tInit.position, collapseT);
                    
                    positions[i++] = sPos.x;
                    positions[i++] = sPos.y;
                    positions[i++] = sPos.z;
                    positions[i++] = tInit.position.x;
                    positions[i++] = tInit.position.y;
                    positions[i++] = tInit.position.z;
                }
            });
            this.linesMesh.geometry.attributes.position.needsUpdate = true;
        }

        if (this.linesMesh) {
            this.linesMesh.setRotationFromMatrix(spatialMatrix);
        }

        if (this.controls) this.controls.update();
        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }

        const targetId = this.selectedId || this.hoveredId;
        if (targetId && document.getElementById('billboard').style.display === 'block') {
            const mesh = this.nodes.get(targetId);
            if (mesh) this.updateBillboardPosition(mesh);
        }
    }

    // ------------------------------------------------------------------
    // Billboard (knowledge panel) -- shows html_raw as read-only text
    // ------------------------------------------------------------------

    showBillboard(data, isLocked) {
        const billboard = document.getElementById('billboard');
        if (!billboard || !data) {
            return;
        }
        
        if (data.is_document) {
            this.hideBillboard();
            return;
        }

        const mesh = this.nodes.get(data.id);
        let cssColor = '#60a5fa';
        let textColor = '#ffffff';
        if (mesh) {
            const color = mesh.userData.originalColor;
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
                billboard.style.display = 'none';
                this.selectedId = null;
                this.nodes.forEach(m => this.restoreNodeVisuals(m));
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

        // Visit link: full URL.
        const link = document.getElementById('billboard-link');
        if (link) {
            link.href = data.url || '#';
            link.textContent = data.url || '';
        }

        // Media strip: pull images/videos out of html_raw so the panel shows
        // "what the human would see" alongside the text control space.
        this.renderBillboardMedia(data);

        // Read-only HTML + rendered text preview -- the chunk's true payload.
        const htmlPre = document.getElementById('billboard-html');
        if (htmlPre) {
            if (data.html_raw !== undefined) {
                htmlPre.textContent = (data.html_raw || '').trim() || '(no HTML)';
            } else {
                htmlPre.innerHTML = '<span style="color:#6b7280; font-style:italic;">Click node to load HTML...</span>';
            }
        }
        const textPre = document.getElementById('billboard-rendered-text');
        if (textPre) {
            if (data.rendered_text !== undefined) {
                textPre.textContent = (data.rendered_text || '').trim() || '(no text)';
            } else {
                textPre.innerHTML = '<span style="color:#6b7280; font-style:italic;">Click node to load text...</span>';
            }
        }
        // Content-structure summary: {extended_xpath: [values]} — the
        // top-down chunker's authoritative view. Render one line per
        // key in the exact shape the SLM sees.
        const fieldsPre = document.getElementById('billboard-fields');
        if (fieldsPre) {
            if (data.fields === undefined) {
                fieldsPre.innerHTML = '<span style="color:#6b7280; font-style:italic;">Click node to load summary...</span>';
            } else {
                const fields = data.fields || {};
                const keys = Object.keys(fields);
                if (!keys.length) {
                    fieldsPre.textContent = '(no summary)';
                } else {
                    fieldsPre.textContent = keys
                        .map(k => `${k}: ${JSON.stringify(fields[k])}`)
                        .join('\n');
                }
            }
        }
        const xpathEl = document.getElementById('billboard-xpath');
        if (xpathEl) {
            xpathEl.textContent = data.absolute_xpath || (data.is_document ? '' : 'Click node to load XPath...');
        }

        // Match score (only when part of a search result).
        const scoreEl = document.getElementById('billboard-score');
        if (scoreEl) {
            if (this.searchResults && this.searchResults.has(data.id)) {
                const s = this.searchResults.get(data.id);
                scoreEl.textContent = `${(s * 100).toFixed(1)}% match`;
                scoreEl.style.display = 'inline-block';
            } else {
                scoreEl.style.display = 'none';
            }
        }

        billboard.style.display = 'block';
        if (mesh) this.updateBillboardPosition(mesh);
    }

    hideBillboard() {
        const b = document.getElementById('billboard');
        if (b) b.style.display = 'none';
        this.hideBillboardArrow();
    }

    // Pinned-panel API: clones the current billboard payload into a
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

    _escapeHtml(s) {
        return String(s ?? '')
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    _nextPanelZ() {
        let z = 10010;
        this._pinnedPanels.forEach(({ panel }) => {
            const cur = parseInt(panel.style.zIndex || '0', 10);
            if (cur > z) z = cur;
        });
        return z + 1;
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

    updateBillboardPosition(mesh) {
        const billboard = document.getElementById('billboard');
        if (!mesh || !billboard) return;

        const panel = document.getElementById('projector-panel');
        const panelRect = panel ? panel.getBoundingClientRect() : { left: 0, top: 0, width: window.innerWidth, height: window.innerHeight };

        const vector = mesh.position.clone();
        vector.project(this.camera);
        const x = (vector.x * 0.5 + 0.5) * panelRect.width + panelRect.left;
        const y = -(vector.y * 0.5 - 0.5) * panelRect.height + panelRect.top;
        const behindCamera = vector.z > 1 || vector.z < -1;
        const rect = billboard.getBoundingClientRect();
        const NODE_CLEARANCE_PX = 110;
        billboard.style.left =
            `${Math.min(panelRect.right - rect.width - 20, Math.max(panelRect.left + 20, x + NODE_CLEARANCE_PX))}px`;
        billboard.style.top =
            `${Math.min(panelRect.bottom - rect.height - 20, Math.max(panelRect.top + 20, y - rect.height / 2))}px`;
            
        const svg = document.getElementById('billboard-arrow-svg');
        const line = document.getElementById('billboard-arrow-line');
        if (svg && line) {
            const bbRect = billboard.getBoundingClientRect();
            const targetX = x;
            const targetY = y;
            const bbLeft = bbRect.left;
            const bbTop = bbRect.top;
            const bbRight = bbLeft + bbRect.width;
            const bbBottom = bbTop + bbRect.height;
            const cx = (bbLeft + bbRight) / 2;
            const cy = (bbTop + bbBottom) / 2;

            let anchorX = cx;
            let anchorY = cy;
            const dx = targetX - cx;
            const dy = targetY - cy;
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
                if (mesh.material && mesh.material.color) cssColor = `#${mesh.material.color.getHexString()}`;
                else if (mesh.userData && mesh.userData.originalColor) cssColor = `#${mesh.userData.originalColor.getHexString()}`;
                
                line.setAttribute('stroke', cssColor);
                const markerPolygon = svg.querySelector('marker polygon');
                if (markerPolygon) markerPolygon.setAttribute('fill', cssColor);
            }
        }
    }

    // ------------------------------------------------------------------
    // Sidebar + search
    // ------------------------------------------------------------------

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

        const getPanel = (containerId, selectors) => {
            const container = document.getElementById(containerId);
            if (!container) return null;
            let panel = container.closest(selectors);
            if (!panel) {
                let curr = container;
                while (curr.parentElement && curr.parentElement.tagName !== 'BODY' && curr.parentElement.tagName !== 'MAIN') {
                    curr = curr.parentElement;
                }
                panel = curr;
            }
            return panel;
        };

        latch.addEventListener('click', () => {
            const panel = getPanel('results-container', '.sidebar, aside, .panel, #right-panel, .panel-right, .side-panel');
            if (!panel) return;

            if (!panel.classList.contains('sidebar-sliding')) panel.classList.add('sidebar-sliding');

            if (!panel.dataset.originalWidth || parseInt(panel.dataset.originalWidth) === 0) {
                if (panel.offsetWidth > 0) panel.dataset.originalWidth = panel.offsetWidth;
            }
            const width = parseInt(panel.dataset.originalWidth) || 300;

            // Pin width + disable flex grow/shrink so the panel keeps its
            // natural size during the transform. Without this, the flex
            // container could rescale the panel mid-animation and the
            // slide-out would look jittery.
            panel.style.width = `${width}px`;
            panel.style.flexShrink = '0';
            panel.style.flexGrow = '0';

            const isCollapsed = panel.dataset.collapsed === 'true';
            const icon = latch.querySelector('i');

            // The right sidebar IS a flex child of ``#container`` (see
            // index.html), so unlike the left panel we have to collapse its
            // flex slot too — otherwise sliding it off-screen would leave a
            // blank 300px gap on the right edge of the 3D canvas. We pair:
            //   - ``transform: translateX(+width)`` — animate the panel off
            //     the RIGHT edge (sweep outward)
            //   - ``margin-right: -width`` — closes the flex slot so the
            //     center canvas grows to fill; this runs through the same
            //     300ms transition (``margin 0.3s ease`` in .sidebar-sliding)
            //     so canvas expansion is paced with the slide instead of
            //     snapping.
            // The old code animated ``width: 0`` alone, which both shrank the
            // panel from its right edge leftward AND let the flex canvas
            // claim the space instantly — reading as "center content
            // sweeping inward across the panel".
            if (isCollapsed) {
                panel.style.transform = '';
                panel.style.marginRight = '';
                panel.style.opacity = '1';
                panel.style.pointerEvents = '';
                icon.style.transform = 'rotate(0deg)';
                panel.dataset.collapsed = 'false';
            } else {
                panel.style.transform = `translateX(${width + 10}px)`;
                panel.style.marginRight = `-${width}px`;
                panel.style.opacity = '0';
                panel.style.pointerEvents = 'none';
                icon.style.transform = 'rotate(180deg)';
                panel.dataset.collapsed = 'true';
            }

            // Canvas really does change size for the right panel (flex slot
            // closes), so keep the resize pulses through the transition.
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
        this.nodes.forEach(m => this.restoreNodeVisuals(m));
        this.renderUrlBuckets();
    }

    async triggerSearch(query, ts, stillFreshest, urlFilter = null) {
        const container = document.getElementById('results-container');
        if (container) {
            container.innerHTML =
                '<div class="empty-state">Searching...</div>';
        }

        // Collect actively visible URLs to pass as filter 
        const activeUrls = new Set();
        this.nodes.forEach((mesh, id) => {
            if (mesh.visible) {
                const data = this.dataMap.get(id);
                if (data && data.url) activeUrls.add(data.url);
            }
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
            if (stillFreshest && stillFreshest() !== ts) return; // stale
            this.lastSearchPayload = data;
            this.renderSearchResults(data, urlFilter);
        } catch (e) {
            console.error("[ChunkProjector] search failed", e);
            if (container) {
                container.innerHTML =
                    `<div class="empty-state">Search failed: ${this.escape(e.message)}</div>`;
            }
        }
    }

    renderSearchResults(payload, activeUrlFilter = null) {
        const container = document.getElementById('results-container');
        if (!container) return;
        const pages = payload.pages || [];
        if (pages.length === 0) {
            container.innerHTML = '<div class="empty-state">No matches.</div>';
            this.searchResults = null;
            this.nodes.forEach(m => this.restoreNodeVisuals(m));
            return;
        }

        if (activeUrlFilter && pages.length > 0) {
            // Full instance drilldown for the chosen URL
            const page = pages[0];
            const doc_id = `doc_${page.url}`;
            this.docCollapseTarget.set(doc_id, 0); // Auto-expand when drilled down

            const headColor = this.avgPageColor(page.instances);
            const html = `
                <div class="bucket-heading">
                    <button id="back-to-search" style="margin-right: 10px; cursor: pointer; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #fff; padding: 2px 8px; border-radius: 4px;">&larr; Back</button>
                    Instances on ${this.escape(this.shortenUrl(page.url))}
                </div>
                ${this.pageCardHtml(page, headColor, page.instances.length)}
            `;
            container.innerHTML = html;

            document.getElementById('back-to-search').onclick = () => {
                this.triggerSearch(payload.query, Date.now(), null, null);
            };

            const flat = [];
            flat.push({ id: doc_id, score: page.score }); // Keep doc node glowing
            (page.instances || []).forEach(i => {
                flat.push({ id: i.id, score: i.score });
                if (this.dataMap.has(i.id)) {
                    this.dataMap.set(i.id, { ...this.dataMap.get(i.id), ...i });
                }
            });
            this.update3DVisualsFromResults(flat);

            container.querySelectorAll('.instance-row').forEach(row => {
                const id = row.dataset.id;
                row.addEventListener('click', (e) => {
                    if (e.target.closest('a')) return;
                    this.selectNode(id);
                });
                row.addEventListener('mouseenter', () => {
                    this.hoveredId = id;
                    const mesh = this.nodes.get(id);
                    if (mesh && id !== this.selectedId) {
                        mesh.material.emissiveIntensity = 1.0;
                        mesh.material.opacity = 1.0;
                        mesh.scale.setScalar(1.8);
                    }
                });
                row.addEventListener('mouseleave', () => {
                    if (this.hoveredId === id) this.hoveredId = null;
                    const mesh = this.nodes.get(id);
                    if (mesh && id !== this.selectedId) this.restoreNodeVisuals(mesh);
                });
            });
        } else {
            // Minimal URL ranking view
            const parts = [`<div class="bucket-heading">
                ${pages.length} page${pages.length === 1 ? '' : 's'} &middot; query "${this.escape(payload.query || '')}"
            </div>`];
            
            pages.forEach(page => {
                const pct = (page.score * 100).toFixed(1);
                const urlShort = this.escape(this.shortenUrl(page.url));
                
                let snippetHtml = '';
                if (page.instances && page.instances.length > 0) {
                    const snippets = page.instances.slice(0, 3).map(inst => {
                        if (inst.rendered_text) {
                            const text = this.escape(inst.rendered_text.slice(0, 120)) + (inst.rendered_text.length > 120 ? '...' : '');
                            return `<div style="font-size: 11px; color: #9ca3af; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">&bull; "${text}"</div>`;
                        }
                        return '';
                    }).join('');
                    if (snippets) {
                        snippetHtml = `<div style="margin-top: 6px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 4px;">${snippets}</div>`;
                    }
                }

                const dataUrl = this.escape(page.url);
                parts.push(`
                    <div class="page-card" data-url="${dataUrl}" style="cursor: pointer; border-left: 4px solid var(--accent-pastel, #88c0d0); margin-bottom: 8px; padding: 10px; background: var(--surface-elevated, #2e3440); border-radius: 4px;" onclick="app.triggerSearch('${this.escape(payload.query)}', Date.now(), null, ['${this.escape(page.url)}'])">
                        <div class="page-card-head" style="display: flex; justify-content: space-between; align-items: center;">
                            <span class="page-url" title="${this.escape(page.url)}" style="font-weight: bold; color: #fff;">${urlShort}</span>
                            <span class="page-score" style="color: #9ca3af;">${pct}%</span>
                        </div>
                        ${snippetHtml}
                    </div>`);
            });
            container.innerHTML = parts.join('');
            
            container.querySelectorAll('.page-card').forEach(card => {
                const docId = `doc_${card.dataset.url}`;
                card.addEventListener('mouseenter', () => {
                    this.hoveredId = docId;
                    const mesh = this.nodes.get(docId);
                    if (mesh && docId !== this.selectedId) {
                        mesh.material.emissiveIntensity = 1.0;
                        mesh.material.opacity = 1.0;
                        mesh.scale.setScalar(1.8);
                    }
                });
                card.addEventListener('mouseleave', () => {
                    if (this.hoveredId === docId) this.hoveredId = null;
                    const mesh = this.nodes.get(docId);
                    if (mesh && docId !== this.selectedId) this.restoreNodeVisuals(mesh);
                });
            });

            // Update 3D Visuals: Auto-expand matching URLs and glow their instances
            const flat = [];
            pages.forEach(p => {
                 const doc_id = `doc_${p.url}`;
                 this.docCollapseTarget.set(doc_id, 0); // Auto-expand
                 flat.push({ id: doc_id, score: p.score });
                 (p.instances || []).forEach(i => {
                     flat.push({ id: i.id, score: i.score });
                     if (this.dataMap.has(i.id)) {
                         this.dataMap.set(i.id, { ...this.dataMap.get(i.id), ...i });
                     }
                 });
            });
            this.update3DVisualsFromResults(flat);
        }
    }

    pageCardHtml(page, headColor, limit = 50) {
        const insts = (page.instances || []).slice(0, limit);
        const rows = insts.map(i => {
            const mesh = this.nodes.get(i.id);
            let chip = '';
            if (mesh) {
                const c = mesh.userData.originalColor;
                chip = `<span class="node-color-chip" style="background:#${c.getHexString()}"></span>`;
            }
            
            const textSnippet = i.rendered_text ? this.escape(i.rendered_text.slice(0, 300)) : '';
            let textDisplay;
            if (i.rendered_text !== undefined) {
                textDisplay = textSnippet || '<span style="color:#6b7280; font-style:italic;">(no text)</span>';
            } else {
                textDisplay = '<span style="color:#6b7280; font-style:italic;">Click node to load contents...</span>';
            }
            const xpathDisplay = i.absolute_xpath ? this.escape(this.shortenXpath(i.absolute_xpath)) : 'Chunk Instance';
            
            return `
                <div class="instance-row" data-id="${this.escape(i.id)}">
                    <div class="instance-row-head">
                        ${chip}
                        <span class="instance-score">${(i.score * 100).toFixed(1)}%</span>
                        <span class="instance-xpath" title="${this.escape(i.absolute_xpath || '')}">
                            ${xpathDisplay}
                        </span>
                    </div>
                    <div class="instance-text">${textDisplay}</div>
                </div>`;
        }).join('');

        const urlShort = this.escape(this.shortenUrl(page.url));
        const pct = (page.score * 100).toFixed(1);
        return `
            <div class="page-card" style="border-left: 4px solid ${headColor}">
                <div class="page-card-head">
                    <a class="page-url" href="${this.escape(page.url)}" target="_blank"
                       title="${this.escape(page.url)}">${urlShort}</a>
                    <span class="page-score">${pct}%</span>
                </div>
                <div class="page-meta">${page.instance_count} instance(s) on page</div>
                <div class="instance-list">${rows}</div>
            </div>`;
    }

    showChunksForUrl(url, items) {
        const container = document.getElementById('results-container');
        if (!container) return;

        const doc_id = `doc_${url}`;
        this.docCollapseTarget.set(doc_id, 0); // Auto-expand when browsing url bucket

        // Dim non-matches, glow matches
        const flat = items.map(i => ({id: i.id, score: 1.0}));
        flat.push({ id: doc_id, score: 1.0 });
        this.update3DVisualsFromResults(flat);

        const page = {
            url: url,
            score: 1.0,
            instance_count: items.length,
            instances: items.map(i => {
                if (this.dataMap.has(i.id)) {
                    this.dataMap.set(i.id, { ...this.dataMap.get(i.id), ...i });
                }
                return {
                    id: i.id,
                    score: 1.0,
                    absolute_xpath: i.absolute_xpath,
                    html_raw: i.html_raw,
                    rendered_text: i.rendered_text
                };
            })
        };

        const headColor = this.avgPageColor(page.instances);
        const html = `
            <div class="bucket-heading">
                <button id="back-to-buckets" style="margin-right: 10px; cursor: pointer; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #fff; padding: 2px 8px; border-radius: 4px;">&larr; Back</button>
                ${items.length} chunks on ${this.escape(this.shortenUrl(url))}
            </div>
            ${this.pageCardHtml(page, headColor, items.length)}
        `;
        container.innerHTML = html;

        const backBtn = document.getElementById('back-to-buckets');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                this.clearSearch();
            });
        }

        container.querySelectorAll('.instance-row').forEach(row => {
            const id = row.dataset.id;
            row.addEventListener('click', (e) => {
                if (e.target.closest('a')) return;
                this.selectNode(id);
            });
            row.addEventListener('mouseenter', () => {
                this.hoveredId = id;
                const mesh = this.nodes.get(id);
                if (mesh && id !== this.selectedId) {
                    mesh.material.emissiveIntensity = 1.0;
                    mesh.material.opacity = 1.0;
                    mesh.scale.setScalar(1.8);
                }
            });
            row.addEventListener('mouseleave', () => {
                if (this.hoveredId === id) this.hoveredId = null;
                const mesh = this.nodes.get(id);
                if (mesh && id !== this.selectedId) this.restoreNodeVisuals(mesh);
            });
        });
    }

    avgPageColor(instances) {
        // Average the node colors for the page header's left-border tint.
        let r = 0, g = 0, b = 0, n = 0;
        (instances || []).forEach(i => {
            const mesh = this.nodes.get(i.id);
            if (mesh) {
                const c = mesh.userData.originalColor;
                r += c.r; g += c.g; b += c.b; n += 1;
            }
        });
        if (n === 0) return '#60a5fa';
        const col = new THREE.Color(r / n, g / n, b / n);
        return `#${col.getHexString()}`;
    }

    // ------------------------------------------------------------------
    // Billboard media strip
    // ------------------------------------------------------------------

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

    // ------------------------------------------------------------------
    // Snapshot button -- trigger a real scan of whatever URL is currently
    // loaded in the Selenium-driven live browser. The backend derives the
    // URL from `driver.current_url` when we omit the ?url= parameter, so
    // the user's workflow is: navigate Firefox → click Snapshot.
    // ------------------------------------------------------------------

    initSnapshot() {
        const btn = document.getElementById('snapshot-btn');
        if (btn) {
            btn.addEventListener('click', () => this.triggerScan());

            // Inject Recompute UMAP button next to it
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
                } catch(e) {
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

        const preCount = this.nodes ? this.nodes.size : 0;
        const preIds = new Set(this.dataMap.keys());

        this.setLoadingProgress("Initiating live browser scan...", 10);

        let settled = false;
        let failed = false;

        try {
            // No ?url= -> backend uses the live driver's current_url.
            const res = await fetch('/api/snapshot', { method: 'GET' });
            if (!res.ok && res.status !== 202) {
                const body = await res.text().catch(() => '');
                throw new Error(`HTTP ${res.status} ${body || ''}`);
            }
            this.setScanStatus('scan running…', '#93c5fd');
            this.setLoadingProgress("Extracting and distilling DOM...", 30);
            
            // Poll /api/chunk_nodes until the node count grows. Cap tight
            // (45s) — a scan that hasn't produced new chunks by then is
            // very likely stuck and the user should see that, not a blue
            // spinner forever.
            const pollStart = Date.now();
            const POLL_CAP_MS = 45 * 1000;
            const POLL_INTERVAL_MS = 2000;
            while (Date.now() - pollStart < POLL_CAP_MS) {
                await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));
                
                const elapsed = Date.now() - pollStart;
                const prog = Math.min(85, 30 + (elapsed / POLL_CAP_MS) * 55);
                this.setLoadingProgress("Processing chunks and rendering summaries...", prog);
                
                try {
                    const nodes = await fetch('/api/chunk_nodes').then(r => r.json());
                    const count = (nodes && nodes.count) || 0;
                    if (count > preCount) {
                        this.setScanStatus(
                            `found ${count - preCount} new chunk(s), refreshing…`,
                            '#34d399',
                        );
                        this.setLoadingProgress(`Discovered ${count - preCount} new chunks! Reloading scene...`, 90);
                        await this.loadNodes();
                        
                        const postIds = new Set(this.dataMap.keys());
                        const scannedUrls = new Set();
                        postIds.forEach(id => {
                            if (!preIds.has(id)) {
                                const data = this.dataMap.get(id);
                                if (data && data.url) scannedUrls.add(data.url);
                            }
                        });
                        
                        if (scannedUrls.size === 0 && this.dataMap.size > 0) {
                            const values = Array.from(this.dataMap.values());
                            scannedUrls.add(values[values.length - 1].url);
                        }

                        scannedUrls.forEach(u => this.addUrlToActiveWorkspace(u));
                        settled = true;
                        break;
                    }
                } catch (e) {
                    // Transient fetch error -- keep polling.
                    console.warn('[ChunkProjector] chunk_nodes poll failed', e);
                }
            }
            if (!settled) {
                this.setScanStatus(
                    'no new chunks after 45s — check server logs',
                    '#fbbf24',
                );
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
