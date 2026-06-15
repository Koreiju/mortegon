console.log("[Projector] Script loaded");

// ---------------------------------------------------------------------------
// ForceLayoutEngine — DISABLED (dead code, retained for reference)
// Server computes deterministic radial-tree layout; no client-side physics.
// ---------------------------------------------------------------------------
class ForceLayoutEngine {
    constructor(opts = {}) {
        this.shellSpacing = opts.shellSpacing || 30;
        this.repulsion = opts.repulsion || 800;
        this.springStrength = opts.springStrength || 0.06;
        this.springRestLength = opts.springRestLength || 20;
        this.damping = opts.damping || 0.88;
        this.shellBias = opts.shellBias || 0.015;
        this.maxIterations = opts.maxIterations || 400;
        this.convergenceThreshold = opts.convergenceThreshold || 0.3;

        // State arrays — parallel indexed
        this.positions = [];   // [{x, y, z}, …]
        this.velocities = [];  // [{x, y, z}, …]
        this.depths = [];      // [int, …]
        this.links = [];       // [{source: idx, target: idx}, …]
        this.idToIndex = new Map();
        this.iteration = 0;
        this.running = false;
        this._frozen = false;
        this.onConverge = null; // callback when layout settles
    }

    /** Load a fresh graph. Resets all state. */
    load(nodes, links) {
        this.positions = [];
        this.velocities = [];
        this.depths = [];
        this.idToIndex.clear();
        this.links = [];
        this.iteration = 0;
        this._frozen = false;

        nodes.forEach((n, i) => {
            this.idToIndex.set(n.id, i);
            this.positions.push({ x: n.x || 0, y: n.y || 0, z: n.z || 0 });
            this.velocities.push({ x: 0, y: 0, z: 0 });
            this.depths.push(n.depth || 0);
        });

        links.forEach(l => {
            const si = this.idToIndex.get(l.source);
            const ti = this.idToIndex.get(l.target);
            if (si !== undefined && ti !== undefined) {
                this.links.push({ source: si, target: ti });
            }
        });

        this.running = true;
    }

    /** Hot-add new nodes near their parent. */
    addNodes(newNodes, newLinks) {
        const baseIdx = this.positions.length;
        newNodes.forEach((n, i) => {
            const idx = baseIdx + i;
            this.idToIndex.set(n.id, idx);
            this.positions.push({ x: n.x || 0, y: n.y || 0, z: n.z || 0 });
            this.velocities.push({ x: 0, y: 0, z: 0 });
            this.depths.push(n.depth || 0);
        });
        newLinks.forEach(l => {
            const si = this.idToIndex.get(l.source);
            const ti = this.idToIndex.get(l.target);
            if (si !== undefined && ti !== undefined) {
                this.links.push({ source: si, target: ti });
            }
        });
        // Reactivate simulation
        this.iteration = Math.max(0, this.iteration - 100);
        this._frozen = false;
        this.running = true;
    }

    /** Run one simulation step. Returns true if still running. */
    tick() {
        if (!this.running || this._frozen) return false;
        if (this.positions.length === 0) return false;

        const N = this.positions.length;
        const forces = new Array(N);
        for (let i = 0; i < N; i++) forces[i] = { x: 0, y: 0, z: 0 };

        // 1. Repulsion — O(N²) for small graphs, capped at 3000 nodes
        //    For larger graphs we sample a random subset
        const repCap = Math.min(N, 3000);
        const useSubset = N > repCap;
        for (let i = 0; i < N; i++) {
            const pi = this.positions[i];
            const jMax = useSubset ? repCap : N;
            for (let jj = 0; jj < jMax; jj++) {
                const j = useSubset ? Math.floor(Math.random() * N) : jj;
                if (j === i) continue;
                const pj = this.positions[j];
                let dx = pi.x - pj.x;
                let dy = pi.y - pj.y;
                let dz = pi.z - pj.z;
                let dist2 = dx * dx + dy * dy + dz * dz;
                if (dist2 < 0.01) {
                    dx = (Math.random() - 0.5) * 2;
                    dy = (Math.random() - 0.5) * 2;
                    dz = (Math.random() - 0.5) * 2;
                    dist2 = dx * dx + dy * dy + dz * dz;
                }
                const dist = Math.sqrt(dist2);
                const f = this.repulsion / dist2;
                const scale = useSubset ? (N / repCap) : 1;
                forces[i].x += (dx / dist) * f * scale;
                forces[i].y += (dy / dist) * f * scale;
                forces[i].z += (dz / dist) * f * scale;
            }
        }

        // 2. Link spring forces
        for (const link of this.links) {
            const { source: si, target: ti } = link;
            const ps = this.positions[si];
            const pt = this.positions[ti];
            let dx = pt.x - ps.x;
            let dy = pt.y - ps.y;
            let dz = pt.z - ps.z;
            const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 0.1;
            const depthDiff = Math.abs(this.depths[si] - this.depths[ti]);
            const rest = this.springRestLength * Math.max(depthDiff, 1);
            const displacement = dist - rest;
            const f = this.springStrength * displacement;
            const fx = (dx / dist) * f;
            const fy = (dy / dist) * f;
            const fz = (dz / dist) * f;
            forces[si].x += fx;
            forces[si].y += fy;
            forces[si].z += fz;
            forces[ti].x -= fx;
            forces[ti].y -= fy;
            forces[ti].z -= fz;
        }

        // 3. Depth-shell radial bias
        for (let i = 0; i < N; i++) {
            const p = this.positions[i];
            const targetR = (this.depths[i] + 1) * this.shellSpacing;
            const r = Math.sqrt(p.x * p.x + p.y * p.y + p.z * p.z) || 0.1;
            const radialError = targetR - r;
            const scale = this.shellBias * radialError;
            forces[i].x += (p.x / r) * scale;
            forces[i].y += (p.y / r) * scale;
            forces[i].z += (p.z / r) * scale;
        }

        // 4. Apply forces → velocity → position (velocity Verlet)
        let totalMovement = 0;
        for (let i = 0; i < N; i++) {
            const v = this.velocities[i];
            const p = this.positions[i];
            v.x = (v.x + forces[i].x) * this.damping;
            v.y = (v.y + forces[i].y) * this.damping;
            v.z = (v.z + forces[i].z) * this.damping;
            // Clamp velocity to prevent explosion
            const speed = Math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
            if (speed > 10) {
                const s = 10 / speed;
                v.x *= s; v.y *= s; v.z *= s;
            }
            p.x += v.x;
            p.y += v.y;
            p.z += v.z;
            totalMovement += Math.abs(v.x) + Math.abs(v.y) + Math.abs(v.z);
        }

        this.iteration++;
        const avgMovement = totalMovement / N;

        // Check convergence
        if (avgMovement < this.convergenceThreshold || this.iteration >= this.maxIterations) {
            this._frozen = true;
            this.running = false;
            console.log(`[ForceLayout] Converged after ${this.iteration} iterations (avg movement: ${avgMovement.toFixed(3)})`);
            if (this.onConverge) this.onConverge();
        }

        return true;
    }

    /** Get current position for a node ID. */
    getPosition(id) {
        const idx = this.idToIndex.get(id);
        if (idx === undefined) return null;
        return this.positions[idx];
    }

    /** Apply all positions to initialNodeData and InstancedMesh. */
    applyToScene(projector) {
        this.idToIndex.forEach((idx, nodeId) => {
            const initData = projector.initialNodeData.get(nodeId);
            if (!initData) return;
            const pos = this.positions[idx];
            initData.localPos.set(pos.x, pos.y, pos.z);
        });

        // Update InstancedMesh transforms per snapshot group
        const dummy = new THREE.Object3D();
        projector.nodes.forEach((nodeObj, nodeId) => {
            const initData = projector.initialNodeData.get(nodeId);
            if (!initData) return;
            dummy.position.copy(initData.localPos);
            dummy.updateMatrix();
            nodeObj.mesh.setMatrixAt(nodeObj.instanceId, dummy.matrix);
        });
        projector.snapshotGroups.forEach(group => {
            if (group.userData.nodesMesh) {
                group.userData.nodesMesh.instanceMatrix.needsUpdate = true;
            }
        });
    }
}

class CompanyProjector {
    constructor() {
        console.log("[Projector] Constructor called");
        this.client = new WorkflowClient();
        this.cadTools = new CadToolDispatcher(this, this.client);
        // Force layout disabled — server computes deterministic radial-tree layout.
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.clock = new THREE.Clock(); 
        this.animationTime = 0; // Custom accumulator for pausable animation
        
        // Data
        this.nodes = new Map(); // id -> Mesh
        this.lineMeshes = []; // track line geometry
        this.dataMap = new Map(); // id -> raw data (including tags)
        this.initialNodeData = new Map(); // Store initial Pos/Color for transformations
        this.selectedId = null;
        this.hoveredId = null; 
        this.activeTags = new Set();
        this.allTags = new Set();
        this.searchResults = null; 
        
        // Drag detection state
        this.isDragging = false;
        this.mouseDownPos = { x: 0, y: 0 };
        
        // Background
        this.backgroundMesh = null;
        this.backgroundDistance = 50000;
        
        // Physics / Animation Constants
        // Increased speeds for visibility
        this.spatialVelocity = { x: 0.05, y: 0.1, z: 0.02 }; // Snow Globe rotation
        this.colorVelocity = { x: 0.4, y: 0.6, z: 0.3 };     // Spectral color rotation
        
        // Constants for STATUS overrides (Yes/No)
        this.STATUS_COLORS = {
            yes: 0x10b981, // Green
            no: 0xef4444,  // Red
            hover: 0xffffff,
            selected: 0xffff00
        };

        // Snapshot tracking
        this.snapshotGroups = new Map();
        this.snapshotHistory = new Map();
        this.snapshotMeta = new Map(); // sIdx -> { offsetX, boundingRadius }
        this.seqLineMeshes = [];
        this.links = [];
        this._instanceLookup = new Map();
        this.maxSnapshotIndex = 0;

        // Only auto-focus the camera once (initial load). Subsequent stream
        // frames must NOT snap the camera back — the user's view is sacred.
        this._hasInitialFocus = false;

        // Interactive fold state.  Starts folded — only root visible.
        // Left-click a node to reveal its direct children; right-click to
        // collapse a subtree.  Labeled / searched / commuted nodes always
        // stay visible regardless of fold state.
        this._folded = true;           // auto-fold on startup
        this._unfoldedIds = new Set(); // nodes whose children are revealed
        this._commutedIds = new Set();
        this._childrenMap = new Map(); // parentId → Set<childId>
        this._parentMap = new Map();   // childId → parentId

        this.init();
        this.loadCompanies();
        this.initSidebar();
        this.initBillboardTags();
    }

    init() {
        console.log("[Projector] init() called");
        const container = document.getElementById('projector-panel');
        const canvas = document.getElementById('projector-canvas');

        if (!container || !canvas) {
            console.error("DOM Elements missing");
            return;
        }

        this.scene = new THREE.Scene();
        // this.scene.background = new THREE.Color(0x0f1115); // Handled by video plane
        this.scene.fog = new THREE.FogExp2(0x0f1115, 0.002); // Reduced fog significantly to see background

        this.camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 100000);
        this.camera.position.set(0, 5, 20);
        
        this.scene.add(this.camera);

        this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
        this.renderer.setSize(container.clientWidth, container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);

        const ambient = new THREE.AmbientLight(0xffffff, 0.7);
        const directional = new THREE.DirectionalLight(0xffffff, 0.8);
        directional.position.set(10, 20, 10);
        this.scene.add(ambient, directional);

        if (typeof THREE.OrbitControls === 'function') {
            this.controls = new THREE.OrbitControls(this.camera, canvas);
            this.controls.enableDamping = true;
            this.controls.dampingFactor = 0.05;
            this.controls.autoRotate = false; 
            this.controls.autoRotateSpeed = 0.5;
        } else {
            console.error("THREE.OrbitControls is missing. Controls disabled.");
        }

        window.addEventListener('resize', () => this.onResize());
        
        // Track right-mouse press so we can distinguish a pan gesture
        // (right-drag in OrbitControls) from an intentional right-click.
        this._rightDownPos = null;

        canvas.addEventListener('mousedown', (e) => {
            this.isDragging = false;
            this.mouseDownPos.x = e.clientX;
            this.mouseDownPos.y = e.clientY;
            if (e.button === 2) {
                this._rightDownPos = { x: e.clientX, y: e.clientY };
            }
            if (this.handleCadEvent(e, 'mousedown')) return;
        }, { capture: true });

        canvas.addEventListener('mousemove', (e) => {
            if (e.buttons === 1) {
                const dx = Math.abs(e.clientX - this.mouseDownPos.x);
                const dy = Math.abs(e.clientY - this.mouseDownPos.y);
                if (dx > 5 || dy > 5) {
                    this.isDragging = true;
                }
            }
            if (this.handleCadEvent(e, 'mousemove')) return;
            this.onMouseMove(e);
        });

        canvas.addEventListener('mouseup', (e) => {
            // Right-click release: fold subtree only if the user did NOT pan
            // (distance below 5px). OrbitControls uses right-drag to pan,
            // so we must not fire the fold action on a pan gesture.
            if (e.button === 2 && this._rightDownPos && this._folded) {
                const dx = Math.abs(e.clientX - this._rightDownPos.x);
                const dy = Math.abs(e.clientY - this._rightDownPos.y);
                this._rightDownPos = null;
                if (dx < 5 && dy < 5) {
                    const intersects = this.getIntersects(e);
                    if (intersects.length > 0) {
                        const id = this._resolveInstanceHit(intersects[0]);
                        if (id && this._unfoldedIds && this._unfoldedIds.has(id)) {
                            this._foldSubtree(id);
                            this.applyFilters();
                        }
                    }
                }
            } else if (e.button === 2) {
                this._rightDownPos = null;
            }
            if (this.handleCadEvent(e, 'mouseup')) return;
        });

        canvas.addEventListener('click', (e) => {
            if (this.handleCadEvent(e, 'click')) return;
            this.onClick(e);
        });

        // Suppress the native browser context menu — the fold action is
        // handled in mouseup with drag-distance gating.
        canvas.addEventListener('contextmenu', (e) => {
            e.preventDefault();
        });

        this.initBackground();

        // Bind snapshot button
        const snapshotBtn = document.getElementById('snapshot-btn');
        if (snapshotBtn) {
            snapshotBtn.addEventListener('click', async () => {
                console.log("[Projector] Snapshot button triggered!");
                snapshotBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Capturing...';
                snapshotBtn.disabled = true;
                
                // Add visual error console log directly into UI body
                const statusLog = document.createElement("div");
                statusLog.style = "position:absolute; bottom: 20px; left: 20px; color: yellow; z-index: 1000; font-family: monospace; text-shadow: 1px 1px 0 #000;";
                statusLog.id = "ui-error-log";
                document.body.appendChild(statusLog);
                
                statusLog.innerText = "Firing /api/snapshot...";
                
                try {
                    const snapData = await this.client.beginSnapshot('');
                    statusLog.innerText = "Streaming DOM nodes live...";
                    this.connectStream(snapData.snapshot_ws_id ?? snapData.snapshot_id, snapshotBtn, statusLog);
                    
                } catch (e) {
                    console.error("[Projector] Fatal error during snapshot:", e);
                    statusLog.innerText = "[CRITICAL] " + (e.message || e);
                    statusLog.style.color = "red";
                    alert("Failed to snapshot the DOM: " + (e.message || e));
                    snapshotBtn.innerHTML = '<i class="fas fa-camera"></i> Snapshot Live Browser';
                    snapshotBtn.disabled = false;
                }
            });
        }

        this.animate();
        console.log("[Projector] 3D Environment initialized");
    }

    initBackground() {
        const video = document.createElement('video');
        video.src = '/static/waterfall.mp4'; 
        video.loop = true;
        video.muted = true;
        video.playsInline = true;
        video.crossOrigin = "anonymous";
        video.play().catch(e => console.warn("Video play failed:", e));

        const texture = new THREE.VideoTexture(video);
        texture.minFilter = THREE.LinearFilter;
        texture.magFilter = THREE.LinearFilter;
        texture.format = THREE.RGBFormat;

        const geometry = new THREE.PlaneGeometry(1, 1);
        const material = new THREE.MeshBasicMaterial({ 
            map: texture,
            depthTest: true,
            depthWrite: false,
            fog: false // Crucial: Disable fog for the background video
        });

        this.backgroundMesh = new THREE.Mesh(geometry, material);
        this.backgroundMesh.position.z = -this.backgroundDistance;
        this.backgroundMesh.renderOrder = -1;

        this.camera.add(this.backgroundMesh);
        this.updateBackgroundScale();
    }

    updateBackgroundScale() {
        if (!this.camera || !this.backgroundMesh) return;
        const vFOV = THREE.Math.degToRad(this.camera.fov);
        const height = 2 * Math.tan(vFOV / 2) * this.backgroundDistance;
        const width = height * this.camera.aspect;
        this.backgroundMesh.scale.set(width, height, 1);
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
        const r = threeColor.r * 255;
        const g = threeColor.g * 255;
        const b = threeColor.b * 255;
        const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
        return (yiq >= 128) ? '#000000' : '#ffffff';
    }

    
    _resetSceneState() {
        this.snapshotGroups.forEach(group => this.scene.remove(group));
        this.seqLineMeshes.forEach(mesh => this.scene.remove(mesh.mesh));
        this.snapshotGroups.clear();
        this.seqLineMeshes = [];
        this.nodes.clear();
        this._instanceLookup.clear();
        this.dataMap.clear();
        this.initialNodeData.clear();
        this.allTags.clear();
        this.snapshotHistory.clear();
        this.snapshotMeta.clear();
        this.links = [];
        this._linkInstData = [];
        this._unfoldedIds = new Set();
        this._childrenMap = new Map();
        this._parentMap = new Map();
        this._cardIds = new Set();
        this._cardMeta = new Map();
        this._cardContainingCard = new Map();
        this._cardDescendants = new Map();
        this._unfoldedCardIds = new Set();
        this._cardModeEnabled = false;
        if (this._imageSprites) this._imageSprites.clear();
    }

    async loadCompanies() {
        console.log("[Projector] loadCompanies() called");
        try {
            let restored = null;
            try {
                restored = await this.client.restoreSnapshots();
            } catch (e) {
                console.warn("[Projector] /map/restore unavailable, falling back", e);
            }

            const snapshots = (restored && restored.snapshots) || [];
            if (snapshots.length) {
                this._resetSceneState();

                const RESTORE_OFFSET = 100000;  // keep restored indices clear of live snapshot IDs
                snapshots.forEach((snap, idx) => {
                    const nodes = snap.nodes || [];
                    if (!nodes.length) return;
                    this._streamedNodes = nodes;
                    this._streamedLinks = snap.links || [];
                    this._streamSnapshotId = RESTORE_OFFSET + idx;
                    this._streamOffsetX = snap.offsetX || 0;
                    this._streamBoundingRadius = snap.boundingRadius || 50;
                    this._streamUrl = snap.url || '';
                    this.mergeStreamedNodes();
                });

                snapshots.forEach((snap) => {
                    const chunks = snap.chunks || [];
                    if (!chunks.length) return;
                    this.onChunksArrived({
                        snapshot_id: snap.snapshot_id,
                        url: snap.url || '',
                        chunks,
                    });
                });

                this.renderTagFilters();
                this.renderHistorySidebar();
                this.applyFilters();

                if (!this._hasInitialFocus && snapshots.some(s => (s.nodes || []).length)) {
                    this.focusOnNodes();
                    this._hasInitialFocus = true;
                }

                console.log(`[Projector] Restored ${snapshots.length} snapshot(s) from Kuzu`);
                return;
            }

            const data = await this.client.getNodes();
            this.links = data.links || [];

            this._resetSceneState();
            this.links = data.links || [];

            if (!data.nodes || data.nodes.length === 0) {
                this.renderHistorySidebar();
                return;
            }

            // Group nodes by their offsetX.  We detect snapshot groups by clustering
            // x values:  all nodes sharing the same nearest offsetX belong together.
            // Collect the unique offset centres present in the data.
            const offsetSet = new Set();
            data.nodes.forEach(n => {
                // The scanner wrote layout coords relative to centre then shifted by offsetX.
                // The bounding radius of any single graph is typically < 200, so we round to
                // the nearest 10 to bucket nodes whose offsetX is identical.
                offsetSet.add(Math.round(n.x / 10.0) * 10.0);
            });
            // Cluster: sort unique rounded-x values ascending, then merge close ones
            const sortedOffsets = [...offsetSet].sort((a, b) => a - b);
            const clusterCentres = [];
            sortedOffsets.forEach(o => {
                if (clusterCentres.length === 0 || Math.abs(o - clusterCentres[clusterCentres.length - 1]) > 50) {
                    clusterCentres.push(o);
                } else {
                    // absorb into previous cluster (average)
                    clusterCentres[clusterCentres.length - 1] = (clusterCentres[clusterCentres.length - 1] + o) / 2;
                }
            });
            // Assign each node to the nearest cluster centre → snapshot index
            const centreToIdx = new Map();
            clusterCentres.forEach((c, i) => centreToIdx.set(c, i));
            const findCluster = (x) => {
                let best = clusterCentres[0], bestDist = Math.abs(x - best);
                for (const c of clusterCentres) {
                    const d = Math.abs(x - c);
                    if (d < bestDist) { best = c; bestDist = d; }
                }
                return { centre: best, idx: centreToIdx.get(best) };
            };

            const nodesBySnapshot = new Map();
            const radiusBySnapshot = new Map();

            data.nodes.forEach(node => {
                const { centre, idx: sIdx } = findCluster(node.x);
                if (!nodesBySnapshot.has(sIdx)) nodesBySnapshot.set(sIdx, []);
                nodesBySnapshot.get(sIdx).push(node);

                if (!this.snapshotHistory.has(sIdx)) {
                    this.snapshotHistory.set(sIdx, { index: sIdx, url: node.url || 'Unknown', nodeCount: 0 });
                }
                this.snapshotHistory.get(sIdx).nodeCount++;
                this.dataMap.set(node.id, node);
                if (node.tags) node.tags.forEach(t => this.allTags.add(t));

                // localPos = position relative to the cluster centre
                const localX = node.x - centre;
                const localR = Math.sqrt(localX * localX + node.y * node.y + node.z * node.z);
                radiusBySnapshot.set(sIdx, Math.max(radiusBySnapshot.get(sIdx) || 0, localR));

                let umapColor = new THREE.Vector3(0.2, 0.5, 1.0);
                if (node.r !== undefined) umapColor = new THREE.Vector3(node.r, node.g, node.b);

                // Use server-computed radial-tree coordinates
                this.initialNodeData.set(node.id, {
                    localPos: new THREE.Vector3(localX, node.y, node.z),
                    umapColor: umapColor,
                    snapshotIndex: sIdx
                });
            });

            // Compute non-overlapping group X positions from bounding radii
            const sortedSnapIndices = [...nodesBySnapshot.keys()].sort((a, b) => a - b);
            const groupPositions = new Map();
            let cursor = 0;
            sortedSnapIndices.forEach((sIdx, i) => {
                const br = radiusBySnapshot.get(sIdx) || 50;
                this.snapshotMeta.set(sIdx, { boundingRadius: br });
                if (i === 0) {
                    groupPositions.set(sIdx, 0);
                    cursor = br;
                } else {
                    cursor += br + 20; // 20 units gap
                    groupPositions.set(sIdx, cursor);
                    cursor += br;
                }
            });
            // Centre them around 0
            const totalSpan = cursor;
            const centreShift = totalSpan / 2;

            this.maxSnapshotIndex = Math.max(...sortedSnapIndices);
            const sphereGeom = new THREE.SphereGeometry(0.6, 16, 16);

            nodesBySnapshot.forEach((nodesList, sIdx) => {
                const groupX = groupPositions.get(sIdx) - centreShift;
                const group = new THREE.Group();
                const material = new THREE.MeshPhongMaterial({
                    emissive: 0x000000, emissiveIntensity: 0,
                    shininess: 30, transparent: true, opacity: 1
                });
                const instMesh = new THREE.InstancedMesh(sphereGeom, material, nodesList.length);
                const dummy = new THREE.Object3D();

                nodesList.forEach((node, instId) => {
                    const initData = this.initialNodeData.get(node.id);
                    dummy.position.copy(initData.localPos);
                    dummy.updateMatrix();
                    instMesh.setMatrixAt(instId, dummy.matrix);

                    let activeColor = new THREE.Color();
                    if (node.status === 'yes') activeColor.setHex(this.STATUS_COLORS.yes);
                    else if (node.status === 'no') activeColor.setHex(this.STATUS_COLORS.no);
                    else activeColor.setRGB(initData.umapColor.x, initData.umapColor.y, initData.umapColor.z);
                    instMesh.setColorAt(instId, activeColor);

                    this.nodes.set(node.id, {
                        id: node.id, snapshotIndex: sIdx, instanceId: instId,
                        mesh: instMesh, originalColor: activeColor.clone()
                    });
                    this._instanceLookup.set(`${instMesh.uuid}:${instId}`, node.id);
                });

                instMesh.instanceMatrix.needsUpdate = true;
                if (instMesh.instanceColor) instMesh.instanceColor.needsUpdate = true;

                group.add(instMesh);
                group.position.x = groupX;
                group.userData = { snapshotIndex: sIdx, nodesMesh: instMesh };

                this.scene.add(group);
                this.snapshotGroups.set(sIdx, group);

                // Async-load image billboards for nodes carrying src URLs.
                this._spawnImageBillboards(group, nodesList, sIdx);
            });

            this.renderTagFilters();
            this.createLines();
            this._buildTreeMaps();
            this.applyFilters();
            this.renderHistorySidebar();

            // Layout is deterministic (radial tree from server).
            // Auto-centre camera on the graph — only on the very first load.
            if (!this._hasInitialFocus && data.nodes.length > 0) {
                this.focusOnNodes();
                this._hasInitialFocus = true;
            }
            console.log(`[Projector] Loaded ${data.nodes.length} nodes with concentric layout`);

        } catch (e) {
            console.error("Failed to load nodes", e);
        }
    }

    connectStream(snapshotId, snapshotBtn, statusLog) {
        console.log(`[Projector] Opening stream for ${snapshotId}`);

        this._streamedNodes = [];
        this._streamedLinks = [];
        this._streamDone = false;
        this._streamSnapshotId = snapshotId;
        this._streamOffsetX = 0;
        this._streamBoundingRadius = 50;

        const resetBtn = () => {
            if (snapshotBtn) {
                snapshotBtn.innerHTML = '<i class="fas fa-camera"></i> Snapshot Live Browser';
                snapshotBtn.disabled = false;
            }
        };

        const cleanup = (msg) => {
            if (statusLog) {
                statusLog.innerText = msg;
                setTimeout(() => { if (statusLog.parentNode) statusLog.remove(); }, 2000);
            }
            resetBtn();
        };

        const fallbackPoll = () => {
            let sweeps = 0;
            const poll = setInterval(async () => {
                sweeps++;
                await this.loadCompanies();
                if (sweeps >= 6) {
                    clearInterval(poll);
                    cleanup("Polling complete!");
                }
            }, 3000);
        };

        const ws = this.client.connectSnapshotStream(snapshotId, {
            onStateChange: (state) => {
                if (state === 'connected') {
                    console.log('[Projector] WebSocket connected');
                    if (statusLog) statusLog.innerText = "Connected! Streaming DOM nodes...";
                } else if (state === 'permanent_failure') {
                    if (statusLog) {
                        statusLog.innerText = "Stream failed permanently, falling back to polling...";
                        statusLog.style.color = "orange";
                    }
                    fallbackPoll();
                } else if (state === 'closed') {
                    if (!this._streamDone) {
                        console.warn('[Projector] WebSocket closed before done signal');
                        cleanup("Stream ended.");
                    }
                }
            },
            onFrame: (data) => {
                if (data.type === 'nodes') {
                    // Capture metadata from the payload
                    if (data.offsetX !== undefined) this._streamOffsetX = data.offsetX;
                    if (data.boundingRadius !== undefined) this._streamBoundingRadius = data.boundingRadius;
                    if (data.url) this._streamUrl = data.url;
                    if (data.clear_previous) {
                        this._streamedNodes = [];
                        this._streamedLinks = [];
                    }
                    this._streamedNodes.push(...data.nodes);
                    this._streamedLinks.push(...(data.links || []));
                    this.mergeStreamedNodes();
                    if (statusLog) {
                        const urlDisplay = data.url ? ` (${data.url})` : '';
                        statusLog.innerText = `Streaming... ${this._streamedNodes.length} nodes${urlDisplay}`;
                    }
                } else if (data.type === 'chunks') {
                    console.log(`[Projector] ${data.chunks ? data.chunks.length : 0} chunks received`);
                    this.onChunksArrived(data);
                } else if (data.type === 'chunk_added' || data.type === 'chunk_replaced') {
                    // Continuous-streaming absorber events. Lets the user
                    // see chunks materialize per scroll iteration instead
                    // of waiting for the entire scan to finish.
                    console.log(`[Projector] ${data.type} chunk_id=${data.chunk && data.chunk.chunk_id}` +
                        (data.replaced_chunk_id ? ` (replaced ${data.replaced_chunk_id})` : ''));
                    this.onChunkAbsorbEvent(data);
                } else if (data.type === 'chunk_unchanged') {
                    // Suppressed by the backend by default; ignore if it
                    // ever leaks through so a future emitter change doesn't
                    // accidentally double-render the same chunk.
                } else if (data.type === 'done') {
                    this._streamDone = true;
                    console.log('[Projector] Stream complete');
                    ws.close();
                    cleanup("Scan complete!");
                }
            }
        });
        ws.connect();
    }

    mergeStreamedNodes() {
        const nodes = this._streamedNodes;
        const links = this._streamedLinks;
        if (!nodes.length) return;

        const sIdx = this._streamSnapshotId;
        const offsetX = this._streamOffsetX;
        const boundingRadius = this._streamBoundingRadius || 50;

        this.maxSnapshotIndex = Math.max(this.maxSnapshotIndex || 0, sIdx);
        this.snapshotMeta.set(sIdx, { boundingRadius, offsetX });

        this.snapshotHistory.set(sIdx, {
            index: sIdx,
            url: nodes[0].url || 'Unknown',
            nodeCount: nodes.length
        });

        // Register all streamed nodes in data maps.
        // Backend sends deterministic radial-tree coordinates.
        nodes.forEach(node => {
            if (!this.dataMap.has(node.id)) {
                this.dataMap.set(node.id, node);
            } else {
                const existing = this.dataMap.get(node.id);
                this.dataMap.set(node.id, { ...existing, ...node, tags: existing.tags, status: existing.status });
            }
            if (node.tags) node.tags.forEach(t => this.allTags.add(t));

            // Use server-computed radial-tree coordinates directly
            const sx = node.x || 0;
            const sy = node.y || 0;
            const sz = node.z || 0;

            let umapColor = new THREE.Vector3(0.2, 0.5, 1.0);
            if (node.r !== undefined) {
                umapColor = new THREE.Vector3(node.r, node.g, node.b);
            } else if (node.depth !== undefined) {
                // Depth-based hue cycling for visual structure
                const hue = (node.depth * 0.12 + 0.55) % 1.0;
                const sat = (node.categories && node.categories.length > 0) ? 0.9 : 0.4;
                const light = (node.categories && node.categories.length > 0) ? 0.7 : 0.5;
                const c = new THREE.Color().setHSL(hue, sat, light);
                umapColor = new THREE.Vector3(c.r, c.g, c.b);
            }
            this.initialNodeData.set(node.id, {
                localPos: new THREE.Vector3(sx, sy, sz),
                umapColor: umapColor,
                snapshotIndex: sIdx
            });
        });

        // Tear down only THIS snapshot's group (leave others intact)
        const oldGroup = this.snapshotGroups.get(sIdx);
        if (oldGroup) {
            this.scene.remove(oldGroup);
            
            // Dispose WebGL resources to prevent GPU memory leaks during streams!
            if (oldGroup.userData.nodesMesh) {
                oldGroup.userData.nodesMesh.geometry.dispose();
                oldGroup.userData.nodesMesh.material.dispose();
                oldGroup.userData.nodesMesh.dispose();
            }
            if (oldGroup.userData.structMesh) {
                oldGroup.userData.structMesh.geometry.dispose();
                oldGroup.userData.structMesh.material.dispose();
                oldGroup.userData.structMesh.dispose();
            }
            
            this.nodes.forEach((v, k) => {
                if (v.snapshotIndex === sIdx) {
                    this._instanceLookup.delete(`${v.mesh.uuid}:${v.instanceId}`);
                    this.nodes.delete(k);
                    // Do NOT delete this.dataMap.delete(k) here, otherwise we lose user edits (tags/status)
                    // on every stream delta rebuild!
                }
            });
        }

        // Compute group X position: place each group with radius-based separation
        const groupX = this._computeGroupX(sIdx);

        // Build InstancedMesh for this snapshot's accumulated nodes
        const sphereGeom = new THREE.SphereGeometry(0.6, 16, 16);
        const group = new THREE.Group();
        const material = new THREE.MeshPhongMaterial({
            emissive: 0x000000, emissiveIntensity: 0,
            shininess: 30, transparent: true, opacity: 1
        });
        const instMesh = new THREE.InstancedMesh(sphereGeom, material, nodes.length);
        const dummy = new THREE.Object3D();

        nodes.forEach((node, instId) => {
            const initData = this.initialNodeData.get(node.id);
            dummy.position.copy(initData.localPos);
            dummy.updateMatrix();
            instMesh.setMatrixAt(instId, dummy.matrix);

            let activeColor = new THREE.Color();
            if (node.status === 'yes') activeColor.setHex(this.STATUS_COLORS.yes);
            else if (node.status === 'no') activeColor.setHex(this.STATUS_COLORS.no);
            else activeColor.setRGB(initData.umapColor.x, initData.umapColor.y, initData.umapColor.z);
            instMesh.setColorAt(instId, activeColor);

            this.nodes.set(node.id, {
                id: node.id, snapshotIndex: sIdx, instanceId: instId,
                mesh: instMesh, originalColor: activeColor.clone()
            });
            this._instanceLookup.set(`${instMesh.uuid}:${instId}`, node.id);
        });

        instMesh.instanceMatrix.needsUpdate = true;
        if (instMesh.instanceColor) instMesh.instanceColor.needsUpdate = true;

        group.add(instMesh);
        group.position.x = groupX;
        group.userData = { snapshotIndex: sIdx, nodesMesh: instMesh };

        // Build structural lines within this snapshot
        const validLinks = links.filter(l =>
            this.initialNodeData.has(l.source) && this.initialNodeData.has(l.target)
        );
        if (!this._linkInstData) this._linkInstData = [];
        // Remove stale entries for this snapshot
        this._linkInstData = this._linkInstData.filter(e => {
            const sd = this.initialNodeData.get(e.sourceId);
            return !sd || sd.snapshotIndex !== sIdx;
        });
        if (validLinks.length > 0) {
            const structMaterial = new THREE.MeshPhongMaterial({
                color: 0x556370, transparent: true, opacity: 0.6
            });
            const cylRadius = 0.30;
            const cylGeom = new THREE.CylinderGeometry(cylRadius, cylRadius, 1.0, 8, 1, false);
            cylGeom.translate(0, 0.5, 0);
            cylGeom.rotateX(Math.PI / 2);
            const lineInstMesh = new THREE.InstancedMesh(cylGeom, structMaterial, validLinks.length);
            const lineDummy = new THREE.Object3D();

            validLinks.forEach((link, instId) => {
                const startLocal = this.initialNodeData.get(link.source).localPos;
                const endLocal = this.initialNodeData.get(link.target).localPos;
                const distance = startLocal.distanceTo(endLocal);
                lineDummy.position.copy(startLocal);
                lineDummy.scale.set(1, 1, distance);
                lineDummy.lookAt(endLocal);
                lineDummy.updateMatrix();
                lineInstMesh.setMatrixAt(instId, lineDummy.matrix);

                this._linkInstData.push({
                    sourceId: link.source,
                    targetId: link.target,
                    mesh: lineInstMesh,
                    instId: instId,
                    origMatrix: lineDummy.matrix.clone(),
                });
            });
            lineInstMesh.instanceMatrix.needsUpdate = true;
            group.add(lineInstMesh);
            group.userData.structMesh = lineInstMesh;
        }

        this.scene.add(group);
        this.snapshotGroups.set(sIdx, group);

        // For nodes carrying a downloadable image src, try to render an
        // image billboard in place of the sphere.
        this._spawnImageBillboards(group, nodes, sIdx);

        // Merge links into master list
        this.links = [
            ...(this.links || []).filter(l => {
                const sd = this.initialNodeData.get(l.source);
                return !sd || sd.snapshotIndex !== sIdx;
            }),
            ...links
        ];

        this._buildTreeMaps();
        this.renderHistorySidebar();
        this.applyFilters();

        // Auto-centre camera only if the user hasn't seen a focused view yet
        // (i.e. first stream with empty initial cache). Otherwise preserve
        // whatever camera pose the user is currently looking from.
        if (!this._hasInitialFocus && nodes.length > 0) {
            this.focusOnNodes();
            this._hasInitialFocus = true;
        }
        console.log(`[Projector] Concentric layout rendered with ${nodes.length} streamed nodes`);
    }

    _computeGroupX(targetSIdx) {
        // Position groups sequentially by their bounding radii with gaps
        const indices = [...this.snapshotMeta.keys()].sort((a, b) => a - b);
        const positions = new Map();
        let cursor = 0;
        for (let i = 0; i < indices.length; i++) {
            const sIdx = indices[i];
            const br = (this.snapshotMeta.get(sIdx) || {}).boundingRadius || 50;
            if (i === 0) {
                positions.set(sIdx, 0);
                cursor = br;
            } else {
                cursor += br + 20;
                positions.set(sIdx, cursor);
                cursor += br;
            }
        }
        // Centre around 0
        const shift = cursor / 2;
        // Also reposition any existing groups that may have shifted
        for (const sIdx of indices) {
            const gx = positions.get(sIdx) - shift;
            const existingGroup = this.snapshotGroups.get(sIdx);
            if (existingGroup && sIdx !== targetSIdx) {
                existingGroup.position.x = gx;
            }
        }
        return (positions.get(targetSIdx) || 0) - shift;
    }

    focusOnNodes() {
        if (!this.camera || !this.controls) return;
        if (this.initialNodeData.size === 0) return;

        // Compute world-space bounding sphere of all nodes
        let cx = 0, cy = 0, cz = 0, count = 0;
        this.initialNodeData.forEach((initData) => {
            const group = this.snapshotGroups.get(initData.snapshotIndex);
            if (!group) return;
            const world = initData.localPos.clone().applyMatrix4(group.matrixWorld);
            cx += world.x; cy += world.y; cz += world.z;
            count++;
        });
        if (count === 0) return;
        cx /= count; cy /= count; cz /= count;

        let maxR = 0;
        this.initialNodeData.forEach((initData) => {
            const group = this.snapshotGroups.get(initData.snapshotIndex);
            if (!group) return;
            const world = initData.localPos.clone().applyMatrix4(group.matrixWorld);
            const d = Math.sqrt((world.x-cx)**2 + (world.y-cy)**2 + (world.z-cz)**2);
            if (d > maxR) maxR = d;
        });

        // Position camera to see the full bounding sphere
        const fovRad = THREE.MathUtils.degToRad(this.camera.fov / 2);
        const dist = (maxR / Math.sin(fovRad)) * 1.2; // 20% margin
        const dir = new THREE.Vector3(0.3, 0.2, 1).normalize();

        this.camera.position.set(cx + dir.x * dist, cy + dir.y * dist, cz + dir.z * dist);
        this.controls.target.set(cx, cy, cz);
        this.controls.update();
        console.log(`[Projector] Camera focused on ${count} nodes (radius=${maxR.toFixed(1)}, dist=${dist.toFixed(1)})`);
    }

    _rebuildStructuralEdges() {
        // Update structural edge cylinders in-place by recalculating transforms
        // after force layout has moved node positions.
        const lineDummy = new THREE.Object3D();
        this.snapshotGroups.forEach(group => {
            const structMesh = group.userData.structMesh;
            if (!structMesh) return;
            // We need the links for this snapshot — filter from master
            const sIdx = group.userData.snapshotIndex;
            let instId = 0;
            this.links.forEach(link => {
                const sd = this.initialNodeData.get(link.source);
                const ed = this.initialNodeData.get(link.target);
                if (!sd || !ed) return;
                if (sd.snapshotIndex !== sIdx || ed.snapshotIndex !== sIdx) return;
                if (link.type === 'sequence') return;
                if (instId >= structMesh.count) return;

                const startLocal = sd.localPos;
                const endLocal = ed.localPos;
                const distance = startLocal.distanceTo(endLocal);
                lineDummy.position.copy(startLocal);
                lineDummy.scale.set(1, 1, distance);
                lineDummy.lookAt(endLocal);
                lineDummy.updateMatrix();
                structMesh.setMatrixAt(instId, lineDummy.matrix);
                instId++;
            });
            structMesh.instanceMatrix.needsUpdate = true;
        });
    }

    handleCadEvent(event, type) {
        if (!this.cadTools) return false;
        const intersects = this.getIntersects(event);
        const id = intersects.length > 0 ? this._resolveInstanceHit(intersects[0]) : null;
        return this.cadTools.handleNodeInteraction(id, type);
    }

    highlightXpaths(xpaths) {
        const xpathSet = new Set(xpaths);
        this.nodes.forEach((nodeObj, id) => {
            const data = this.dataMap.get(id);
            if (data && xpathSet.has(data.xpath)) {
                nodeObj.mesh.setColorAt(nodeObj.instanceId, new THREE.Color(0xff8c00));
            } else {
                nodeObj.mesh.setColorAt(nodeObj.instanceId, nodeObj.originalColor);
            }
        });
        this._flushInstanceColors();
    }

    highlightTemporary(id) {
        const nodeObj = this.nodes.get(id);
        if (nodeObj) {
            nodeObj.mesh.setColorAt(nodeObj.instanceId, new THREE.Color(0x00ff00));
            nodeObj.mesh.instanceColor.needsUpdate = true;
        }
    }

    clearHighlights() {
        this.nodes.forEach((nodeObj) => {
            nodeObj.mesh.setColorAt(nodeObj.instanceId, nodeObj.originalColor);
        });
        // Reapply commutation colors so they survive highlight resets
        this._reapplyCommutationColors();
        this._flushInstanceColors();
        if (this._folded) this.applyFilters();
    }

    /** Explicitly clear commutation (user-triggered only). */
    clearCommutation() {
        if (this._commutedIds) this._commutedIds.clear();
        this._commutationSourceId = null;
        this._commutationPalette = null;
        this.nodes.forEach((nodeObj) => {
            nodeObj.mesh.setColorAt(nodeObj.instanceId, nodeObj.originalColor);
        });
        this._flushInstanceColors();
        if (this._folded) this.applyFilters();
    }

    /** Recolor commuted nodes so they persist through highlight/color resets.
     *  Uses the palette captured when commutation was last applied, so
     *  regular vs subgroup commutation stay visually distinct. */
    _reapplyCommutationColors() {
        if (!this._commutedIds || this._commutedIds.size === 0) return;
        const palette = this._commutationPalette || {
            source: 0x00ffff, match: 0x2dd4bf,
        };
        const sourceColor = new THREE.Color(palette.source);
        const matchColor = new THREE.Color(palette.match);
        this._commutedIds.forEach(nodeId => {
            const nodeObj = this.nodes.get(nodeId);
            if (!nodeObj) return;
            // Source = the node that was originally selected for commutation
            const isSource = (nodeId === this._commutationSourceId);
            nodeObj.mesh.setColorAt(nodeObj.instanceId, isSource ? sourceColor : matchColor);
        });
    }

    _resolveInstanceHit(intersect) {
        // Image billboards are individual Sprite objects; we encoded their
        // node id in userData at spawn time.
        if (intersect.object && intersect.object.isSprite
                && intersect.object.userData && intersect.object.userData.nodeId) {
            return intersect.object.userData.nodeId;
        }
        const key = `${intersect.object.uuid}:${intersect.instanceId}`;
        return this._instanceLookup.get(key) || null;
    }

    /** Resolve a possibly-relative URL against the page URL of the node.
     *  Returns an absolute URL string, or null if it cannot be resolved.
     *  Handles: data:, blob:, absolute http(s), protocol-relative (//),
     *  root-relative (/path), and path-relative (foo/bar) forms. */
    _resolveUrl(raw, pageUrl) {
        if (!raw || typeof raw !== 'string') return null;
        raw = raw.trim().replace(/&amp;/g, '&');
        if (!raw) return null;
        // Already usable as-is
        if (/^(data|blob|https?|ftp|file):/i.test(raw)) return raw;
        if (raw.startsWith('//')) {
            // Protocol-relative — infer from page URL or default https
            try {
                const proto = pageUrl ? new URL(pageUrl).protocol : 'https:';
                return proto + raw;
            } catch (_) {
                return 'https:' + raw;
            }
        }
        const base = pageUrl || this._streamUrl || '';
        if (!base) return null;
        try {
            return new URL(raw, base).href;
        } catch (_) {
            return null;
        }
    }

    _extractImageUrl(node) {
        if (!node) return null;
        // Extensions — keep conservative but allow query/hash suffixes and
        // also URLs that carry the extension deep inside the path
        // (e.g. CDN-style /v1/abc.jpg/resize/...)
        const _IMG_RE = /\.(png|jpe?g|gif|webp|svg|bmp|avif|ico|tiff?|apng|heic|heif)(\?|#|\/|$)/i;
        // Any URL shape: protocol, protocol-relative, root-relative, or
        // path-relative. Stops at whitespace and common delimiters.
        const _ABS_URL_RE = /(?:https?:\/\/|\/\/)[^\s"'<>(){}\[\]]+/gi;
        const _REL_URL_RE = /(?:^|[\s"'(=,])(\/[^\s"'<>(){}\[\]]+)/g;
        const tag = (node.tag || '').toString().toLowerCase();
        const pageUrl = node.url || this._streamUrl || '';

        const tryResolve = (raw) => {
            const u = this._resolveUrl(raw, pageUrl);
            return u && _IMG_RE.test(u) ? u : null;
        };

        // 1. Direct src (already resolved by backend)
        if (node.src) {
            const r = tryResolve(node.src);
            if (r) return r;
            if (tag === 'img' || tag === 'image' || tag === 'picture') {
                // Accept extension-less CDN URLs on explicit image tags.
                const rr = this._resolveUrl(node.src, pageUrl);
                if (rr) return rr;
            }
        }

        const attrs = node.attributes || {};

        // 2. srcset / data-srcset — pick highest resolution
        for (const key of ['srcset', 'data-srcset', 'data-lazy-srcset', 'imagesrcset']) {
            const srcset = attrs[key];
            if (!srcset || typeof srcset !== 'string') continue;
            let bestUrl = null, bestW = -1;
            srcset.split(',').forEach(entry => {
                const parts = entry.trim().split(/\s+/);
                if (!parts[0]) return;
                const wm = (parts[1] || '').match(/(\d+)w/);
                const w = wm ? parseInt(wm[1]) : 0;
                if (w > bestW || bestW < 0) { bestW = w; bestUrl = parts[0]; }
            });
            if (bestUrl) {
                const r = this._resolveUrl(bestUrl, pageUrl);
                if (r) return r;
            }
        }

        // 3. Dedicated image-ish attribute keys — prefer explicit ones
        //    before falling back to substring scanning.
        const PRIORITY_KEYS = [
            'src', 'data-src', 'data-lazy-src', 'data-original',
            'data-image', 'data-img', 'data-bg', 'data-background',
            'data-hi-res-src', 'data-full-src', 'poster', 'href',
            'xlink:href', 'content',
        ];
        for (const key of PRIORITY_KEYS) {
            const val = attrs[key];
            if (!val || typeof val !== 'string') continue;
            const r = tryResolve(val);
            if (r) return r;
        }

        // 4. Scan EVERY attribute value for embedded URLs — absolute,
        //    protocol-relative, and root-relative forms. Catches images
        //    referenced through JSON blobs, custom attrs, and wrapped
        //    analytics payloads.
        for (const [key, val] of Object.entries(attrs)) {
            if (typeof val !== 'string' || val.length > 4000) continue;
            if (key === 'class' || key === 'id') continue;
            // Direct-as-URL fast path
            const direct = tryResolve(val);
            if (direct) return direct;
            // Absolute and protocol-relative forms
            let m;
            _ABS_URL_RE.lastIndex = 0;
            while ((m = _ABS_URL_RE.exec(val)) !== null) {
                const r = tryResolve(m[0]);
                if (r) return r;
            }
            // Root-relative paths (e.g. /static/img/foo.webp)
            _REL_URL_RE.lastIndex = 0;
            while ((m = _REL_URL_RE.exec(val)) !== null) {
                const r = tryResolve(m[1]);
                if (r) return r;
            }
        }

        // 5. CSS background-image: url(...) in a style attribute
        const style = attrs['style'];
        if (style && typeof style === 'string') {
            const urlCalls = style.matchAll(/url\s*\(\s*['"]?([^'")\s]+)['"]?\s*\)/gi);
            for (const m of urlCalls) {
                const r = tryResolve(m[1]);
                if (r) return r;
            }
        }

        // 6. href (on <a>/<link>) that points at an image
        if (node.href) {
            const r = tryResolve(node.href);
            if (r) return r;
        }
        // 7. On explicit image-ish tags, accept extension-less CDN URLs
        if ((tag === 'img' || tag === 'picture' || tag === 'source' || tag === 'image')
            && (node.src || attrs['src'])) {
            const rr = this._resolveUrl(node.src || attrs['src'], pageUrl);
            if (rr) return rr;
        }
        return null;
    }

    _isImageNode(node) {
        return !!this._extractImageUrl(node);
    }

    _spawnImageBillboards(group, nodes, sIdx) {
        const imageNodes = nodes.filter(n => this._isImageNode(n));
        if (!imageNodes.length) return;

        if (!this._imageSprites) this._imageSprites = new Map();
        const loader = new THREE.TextureLoader();
        loader.crossOrigin = 'anonymous';

        imageNodes.forEach(node => {
            const imgUrl = this._extractImageUrl(node);
            if (!imgUrl) return;
            loader.load(
                imgUrl,
                (texture) => {
                    // The group for this snapshot may have been torn down
                    // during a restream — bail out silently in that case.
                    if (!group.parent) { texture.dispose(); return; }
                    const nodeObj = this.nodes.get(node.id);
                    const initData = this.initialNodeData.get(node.id);
                    if (!nodeObj || !initData) { texture.dispose(); return; }

                    const img = texture.image || {};
                    const w = img.width || 1, h = img.height || 1;
                    const aspect = (w > 0 && h > 0) ? w / h : 1;

                    const material = new THREE.SpriteMaterial({
                        map: texture, transparent: true, depthWrite: false
                    });
                    const sprite = new THREE.Sprite(material);
                    const baseSize = 2.6;
                    if (aspect >= 1) sprite.scale.set(baseSize * aspect, baseSize, 1);
                    else sprite.scale.set(baseSize, baseSize / aspect, 1);

                    sprite.position.copy(initData.localPos);
                    sprite.userData = { nodeId: node.id };
                    // Respect current fold visibility at spawn time
                    if (this._folded) {
                        const data = this.dataMap.get(node.id);
                        const isRoot = !!(data && data.is_root);
                        const isLabeled = !!(data && (data.nodeLabel || data.label));
                        const isCommuted = this._commutedIds && this._commutedIds.has(node.id);
                        const parentId = this._parentMap.get(node.id);
                        const parentUnfolded = parentId && this._unfoldedIds.has(parentId);
                        const selfUnfolded = this._unfoldedIds.has(node.id);
                        const isSearch = this.searchResults && this.searchResults.has(node.id);
                        sprite.visible = isRoot || parentUnfolded || selfUnfolded || isLabeled || isCommuted || isSearch;
                    }
                    group.add(sprite);

                    // Collapse the sphere instance so it doesn't peek through.
                    const dummy = new THREE.Object3D();
                    dummy.position.copy(initData.localPos);
                    dummy.scale.set(0.001, 0.001, 0.001);
                    dummy.updateMatrix();
                    nodeObj.mesh.setMatrixAt(nodeObj.instanceId, dummy.matrix);
                    nodeObj.mesh.instanceMatrix.needsUpdate = true;
                    nodeObj.imageSprite = sprite;
                    nodeObj.isImageBillboard = true;

                    this._imageSprites.set(node.id, sprite);
                },
                undefined,
                (err) => {
                    // Load failure (CORS, 404, etc.) — keep the sphere.
                    // Log a one-line diagnostic so the user can see which
                    // image URLs are being rejected and why.
                    console.warn(`[ImageBillboard] Failed to load ${imgUrl} for node ${node.id}`, err && err.type ? err.type : err);
                }
            );
        });
    }

    _flushInstanceColors() {
        this.snapshotGroups.forEach(g => {
            if (g.userData.nodesMesh && g.userData.nodesMesh.instanceColor)
                g.userData.nodesMesh.instanceColor.needsUpdate = true;
        });
    }

    createLines() {
        console.log(`[Projector] Creating InstancedMesh Cylinders natively...`);
        const structMaterial = new THREE.MeshPhongMaterial({ color: 0x556370, transparent: true, opacity: 0.6 });
        const seqMaterial = new THREE.MeshPhongMaterial({ color: 0xa855f7, emissive: 0xa855f7, emissiveIntensity: 0.8, transparent: true, opacity: 0.9 });
        const cylinderRadius = 0.30;
        const cylGeom = new THREE.CylinderGeometry(cylinderRadius, cylinderRadius, 1.0, 8, 1, false);
        cylGeom.translate(0, 0.5, 0);
        cylGeom.rotateX(Math.PI / 2);

        const structLinksBySnap = new Map();
        const seqLinks = [];

        this.links.forEach(link => {
            const startData = this.initialNodeData.get(link.source);
            const endData = this.initialNodeData.get(link.target);
            if (!startData || !endData) return;

            if (startData.snapshotIndex === endData.snapshotIndex && link.type !== 'sequence') {
                const sIdx = startData.snapshotIndex;
                if (!structLinksBySnap.has(sIdx)) structLinksBySnap.set(sIdx, []);
                structLinksBySnap.get(sIdx).push({ link, startData, endData });
            } else {
                seqLinks.push({ link, startData, endData });
            }
        });

        // Track per-instance link metadata so applyFilters can hide edges
        // whose endpoints are invisible during fold navigation.
        if (!this._linkInstData) this._linkInstData = [];
        this._linkInstData = [];

        structLinksBySnap.forEach((linksList, sIdx) => {
            const group = this.snapshotGroups.get(sIdx);
            if (!group) return;

            const instMesh = new THREE.InstancedMesh(cylGeom, structMaterial, linksList.length);
            const dummy = new THREE.Object3D();

            linksList.forEach((info, instId) => {
                const startLocal = info.startData.localPos;
                const endLocal = info.endData.localPos;
                const distance = startLocal.distanceTo(endLocal);

                dummy.position.copy(startLocal);
                dummy.scale.set(1, 1, distance);
                dummy.lookAt(endLocal);
                dummy.updateMatrix();

                instMesh.setMatrixAt(instId, dummy.matrix);

                this._linkInstData.push({
                    sourceId: info.link.source,
                    targetId: info.link.target,
                    mesh: instMesh,
                    instId: instId,
                    origMatrix: dummy.matrix.clone(),
                });
            });

            instMesh.instanceMatrix.needsUpdate = true;
            group.add(instMesh);
            group.userData.structMesh = instMesh;
        });

        const seqGeom = new THREE.CylinderGeometry(cylinderRadius, cylinderRadius, 1.0, 8, 1, false);
        seqGeom.translate(0, 0.5, 0);
        seqGeom.rotateX(Math.PI / 2);
        
        seqLinks.forEach(info => {
            const mesh = new THREE.Mesh(seqGeom, seqMaterial);
            this.scene.add(mesh);
            this.seqLineMeshes.push({
                mesh: mesh,
                startData: info.startData,
                endData: info.endData,
                snapshotIndex: info.startData.snapshotIndex
            });
        });
    }


    
    renderHistorySidebar() {
        const container = document.getElementById('history-container');
        if (!container) return;
        container.innerHTML = '';
        
        if (this.snapshotHistory.size === 0) {
            container.innerHTML = '<div class="empty-state" style="color: #6b7280; font-size: 13px; text-align: center; padding: 20px 0;">No snapshots recorded yet.</div>';
            return;
        }

        // Sort descending natively!
        const sortedSnaps = Array.from(this.snapshotHistory.values()).sort((a, b) => b.index - a.index);
        
        sortedSnaps.forEach((snap, idx) => {
            const isNewest = idx === 0;
            const item = document.createElement('div');
            let displayUrl = snap.url;
            try { displayUrl = new URL(snap.url).hostname; } catch(e) {}

            item.className = 'history-item';
            item.style.cssText = `
                padding: 12px;
                background: rgba(255,255,255,0.05);
                border-radius: 8px;
                border-left: 3px solid ${isNewest ? '#3b82f6' : '#4b5563'};
                display: flex; align-items: center; gap: 10px;
                transition: background 0.2s;
            `;

            item.innerHTML = `
                <div style="flex-shrink: 0;">
                    <label style="cursor: pointer; display: flex; align-items: center;">
                        <input type="checkbox" class="history-toggle" data-idx="${snap.index}" checked
                               style="width: 16px; height: 16px; cursor: pointer;">
                    </label>
                </div>
                <div style="flex-grow: 1; min-width: 0;">
                    <div style="color: ${isNewest ? '#fff' : '#9ca3af'}; font-weight: bold; font-size: 13px; margin-bottom: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        ${displayUrl}
                    </div>
                    <div style="color: #6b7280; font-size: 11px;">
                        #${snap.index} • ${snap.nodeCount} nodes
                    </div>
                </div>
            `;

            // Attach listener directly to this checkbox — no querySelectorAll duplication
            const cb = item.querySelector('.history-toggle');
            cb.addEventListener('change', (e) => {
                const snapIdx = parseInt(e.target.dataset.idx);
                const isVisible = e.target.checked;
                const group = this.snapshotGroups.get(snapIdx);
                if (group) group.visible = isVisible;
                if (this.seqLineMeshes) {
                    this.seqLineMeshes.forEach(line => {
                        if (line.snapshotIndex === snapIdx) line.mesh.visible = isVisible;
                    });
                }
            });

            container.appendChild(item);
        });
    }

    // --- Interaction ---

    getIntersects(event) {
        if (!this.renderer || !this.camera) return [];
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        this.raycaster.setFromCamera(this.mouse, this.camera);

        const targets = [];
        this.snapshotGroups.forEach(group => {
            if (group.visible && group.userData.nodesMesh) {
                targets.push(group.userData.nodesMesh);
            }
        });
        // Include image billboard sprites so they are clickable / right-clickable.
        if (this._imageSprites) {
            this._imageSprites.forEach(sprite => { if (sprite.visible) targets.push(sprite); });
        }
        return this.raycaster.intersectObjects(targets);
    }

    onMouseMove(event) {
        const intersects = this.getIntersects(event);

        if (intersects.length > 0) {
            const id = this._resolveInstanceHit(intersects[0]);
            if (!id) return;

            if (this.hoveredId !== id) {
                if (this.hoveredId && this.hoveredId !== this.selectedId) {
                    const prevNode = this.nodes.get(this.hoveredId);
                    if (prevNode) this.restoreNodeVisuals(prevNode);
                }

                this.hoveredId = id;
                document.body.style.cursor = 'pointer';

                if (id !== this.selectedId) {
                    const nodeObj = this.nodes.get(id);
                    if (nodeObj) {
                        nodeObj.mesh.setColorAt(nodeObj.instanceId, new THREE.Color(0xffffff));
                        nodeObj.mesh.instanceColor.needsUpdate = true;
                    }
                }

                if (!this.selectedId) {
                    const data = this.dataMap.get(id);
                    if (data) {
                        // Populate hover-level knowledge panel from streamed data
                        data.nodeAttributes = data.attributes || {};
                        data.generalized_xpath = data.generalized_xpath || '';
                        this.showBillboard(data, false);
                    }
                }
            }
        } else {
            if (this.hoveredId) {
                if (this.hoveredId !== this.selectedId) {
                    const prevNode = this.nodes.get(this.hoveredId);
                    if (prevNode) this.restoreNodeVisuals(prevNode);
                }

                if (!this.selectedId) {
                    this.hideBillboard();
                }

                this.hoveredId = null;
                document.body.style.cursor = 'default';
            }
        }
    }

    async onClick(event) {
        if (this.isDragging) return;
        if (this.controls) this.controls.autoRotate = false;

        const intersects = this.getIntersects(event);
        const hitId = intersects.length > 0 ? this._resolveInstanceHit(intersects[0]) : null;

        // Double-click detection with 50ms latency — isolate the full path
        // (root → node → all descendants) through the clicked node.
        const now = performance.now();
        const DOUBLE_MS = 50;
        if (hitId && this._lastClickedId === hitId &&
            (now - (this._lastClickTime || 0)) <= DOUBLE_MS) {
            this._lastClickedId = null;
            this._lastClickTime = 0;
            if (this._pendingClickTimer) {
                clearTimeout(this._pendingClickTimer);
                this._pendingClickTimer = null;
            }
            this.isolatePath(hitId);
            return;
        }
        this._lastClickedId = hitId;
        this._lastClickTime = now;

        // Delay the single-click action by DOUBLE_MS so a follow-up click
        // within the window can upgrade to a double-click without flicker.
        if (this._pendingClickTimer) clearTimeout(this._pendingClickTimer);
        this._pendingClickTimer = setTimeout(async () => {
            this._pendingClickTimer = null;
            if (hitId) {
                await this.selectNode(hitId);
            } else {
                this.selectedId = null;
                this.hideBillboard();
                this._pathIsolationIds = null;
                this._neighborVisibleIds = null;
                this.nodes.forEach((nodeObj) => {
                    nodeObj.mesh.setColorAt(nodeObj.instanceId, nodeObj.originalColor);
                });
                this._reapplyCommutationColors();
                if (this.searchResults) this._applySearchHighlights();
                this._flushInstanceColors();
                this.applyFilters();
            }
        }, DOUBLE_MS);
    }

    /** Isolate a full path: root → node → all descendants. Everything
     *  else is hidden in fold mode. Non-holonomic rank-1 neighbor view
     *  is overridden by this more restrictive isolation. */
    isolatePath(id) {
        if (!this._parentMap || !this._childrenMap) return;
        const pathIds = new Set();
        pathIds.add(id);
        // Walk up through ancestors
        let cur = id;
        while (true) {
            const parent = this._parentMap.get(cur);
            if (!parent) break;
            pathIds.add(parent);
            cur = parent;
        }
        // Walk down through descendants
        const stack = [id];
        while (stack.length) {
            const n = stack.pop();
            const kids = this._childrenMap.get(n);
            if (!kids) continue;
            kids.forEach(k => {
                if (!pathIds.has(k)) {
                    pathIds.add(k);
                    stack.push(k);
                }
            });
        }
        this._pathIsolationIds = pathIds;
        this._neighborVisibleIds = null;
        if (!this._folded) {
            this._folded = true;
            const label = document.getElementById('fold-toggle-label');
            if (label) label.textContent = 'Unfold DOM';
        }
        this.selectedId = id;
        const mesh = this.nodes.get(id);
        if (mesh) {
            mesh.mesh.setColorAt(mesh.instanceId, new THREE.Color(0xffff00));
            mesh.mesh.instanceColor.needsUpdate = true;
        }
        this.selectNode(id); // opens knowledge panel
        this.applyFilters();
    }

    restoreNodeVisuals(nodeObj) {
        const id = nodeObj.id;

        if (this.searchResults && this.searchResults.has(id)) {
            const score = this.searchResults.get(id);
            this.applySearchGlow(nodeObj, score);
        } else {
            nodeObj.mesh.setColorAt(nodeObj.instanceId, nodeObj.originalColor);
            nodeObj.mesh.instanceColor.needsUpdate = true;
        }
    }

    async selectNode(id) {
        // Root is a synthetic anchor — not clickable, no knowledge panel.
        const rawData = this.dataMap.get(id);
        if (rawData && rawData.is_root) {
            // Clicking the root in fold mode unfolds its direct children.
            if (this._folded) {
                this._unfoldedIds.add(id);
                this.applyFilters();
            }
            return;
        }

        // Card cards are a special case: selecting a card unfolds the
        // entire descendant subtree in a single action, not just rank-1.
        // This runs whether or not the global fold is on.
        if (this._cardModeEnabled && this._cardIds && this._cardIds.has(id)) {
            this.unfoldCardSubtree(id);
        } else if (this._folded) {
            // Interactive fold: clicking any node reveals its direct children
            // AND its rank-1 parent neighbor (non-holonomic selection — every
            // selection independently exposes all 1-hop tree neighbors,
            // regardless of prior fold state).
            this._unfoldedIds.add(id);
            // Remember rank-1 neighbors for the visibility pass so the
            // parent side of the "V" is revealed too, without forcing
            // siblings open through a grand-unfold of the parent.
            if (!this._neighborVisibleIds) this._neighborVisibleIds = new Set();
            this._neighborVisibleIds.add(id);
            const parentId = this._parentMap.get(id);
            if (parentId) this._neighborVisibleIds.add(parentId);
            const kids = this._childrenMap.get(id);
            if (kids) kids.forEach(k => this._neighborVisibleIds.add(k));
            this.applyFilters();
        }

        if (this.selectedId && this.selectedId !== id) {
            const prevMesh = this.nodes.get(this.selectedId);
            if (prevMesh) this.restoreNodeVisuals(prevMesh);
        }

        this.selectedId = id;

        const mesh = this.nodes.get(id);
        if(mesh) { mesh.mesh.setColorAt(mesh.instanceId, new THREE.Color(0xffff00)); mesh.mesh.instanceColor.needsUpdate = true; }

        try {
            // Try mapper detail endpoint first (xpath-based), fall back to legacy
            const data = this.dataMap.get(id);
            const nodeXpath = data ? data.xpath : '';
            const nodeUrl = data ? data.url : '';
            let details;

            if (nodeXpath && nodeUrl) {
                details = await this.client.getMapDetail(nodeUrl, nodeXpath);
                // Merge with local data
                details.id = id;
                details.name = details.tag || data.name || '';
                details.status = data.status || 'unreviewed';
                details.tags = data.tags || [];
                details.location = details.tag || '';
                details.website = nodeUrl;
                details.description = details.html || '';
                details.nodeAttributes = details.attributes || data.attributes || {};
                details.nodeLabel = details.label || '';
                details.categories = details.categories || data.categories || [];
                details.xpath = details.xpath || nodeXpath;
                details.generalized_xpath = details.generalized_xpath || '';
            } else {
                details = await this.client.getNodeDetailsLegacy(id);
            }

            if (data) {
                details.chunk_id = data.chunk_id;
                details.chunk_pattern = data.chunk_pattern;
                details.chunk_label = data.chunk_label;
                details.chunk_char_count = data.chunk_char_count;
                details.chunk_commutation_count = data.chunk_commutation_count;
                details.chunk_content_fields = data.chunk_content_fields;
                details.chunk_text_preview = data.chunk_text_preview;
                details.is_chunk_root = data.is_chunk_root;
                details.is_card = !!data.is_card;
                details.card_image_url = data.card_image_url;
            }

            this.showBillboard(details, true);
        } catch (e) {
            console.error(e);
        }
    }

    update3DVisualsFromResults(results) {
        if (this.searchResults) {
            this.nodes.forEach((nodeObj, id) => {
                if (id !== this.selectedId) {
                    nodeObj.mesh.setColorAt(nodeObj.instanceId, nodeObj.originalColor);
                }
            });
            this._flushInstanceColors();
        }

        this.searchResults = new Map();

        results.forEach(res => {
            this.searchResults.set(res.id, res.score);
            const nodeObj = this.nodes.get(res.id);
            if (nodeObj && res.id !== this.selectedId) {
                this.applySearchGlow(nodeObj, res.score);
            }
        });
    }

    applySearchGlow(nodeObj, score) {
        const safeScore = Math.max(0, Math.min(1, score));
        const glowColor = nodeObj.originalColor.clone().lerp(new THREE.Color(0xffffff), 0.3 + safeScore * 0.4);
        nodeObj.mesh.setColorAt(nodeObj.instanceId, glowColor);
        nodeObj.mesh.instanceColor.needsUpdate = true;
    }

    // --- Animation & Physics ---

    
    animate() {
        requestAnimationFrame(() => this.animate());

        const delta = this.clock.getDelta();
        if (this.controls) this.controls.update();

        // Layout is deterministic (radial tree computed server-side).
        // No force-directed tick needed.

        const isInteracting = this.isDragging || 
                              (this.controls && this.controls.state !== -1) || 
                              (document.querySelector('.haptics-pnl') && document.querySelector('.haptics-pnl').matches(':hover')) ||
                              (document.querySelector('.search-pnl') && document.querySelector('.search-pnl').matches(':hover'));
                              
        if (!isInteracting) {
            this.animationTime += delta;
        }

        const time = this.animationTime;
        const spatialEuler = new THREE.Euler(
            time * this.spatialVelocity.x,
            time * this.spatialVelocity.y,
            time * this.spatialVelocity.z
        );
        
        if (this.snapshotGroups) {
            this.snapshotGroups.forEach(group => {
                group.rotation.copy(spatialEuler);
                group.updateMatrixWorld(true);
            });
        }

        const colorMatrix = new THREE.Matrix4();
        const colorEuler = new THREE.Euler(
            time * this.colorVelocity.x,
            time * this.colorVelocity.y,
            time * this.colorVelocity.z
        );
        colorMatrix.makeRotationFromEuler(colorEuler);

        this.nodes.forEach((nodeObj, id) => {
            const data = this.dataMap.get(id);
            if (data && data.status === 'unreviewed') {
                const initData = this.initialNodeData.get(id);
                const centeredColor = initData.umapColor.clone().subScalar(0.5);
                centeredColor.applyMatrix4(colorMatrix);
                centeredColor.addScalar(0.5);
                centeredColor.x = Math.max(0, Math.min(1, centeredColor.x));
                centeredColor.y = Math.max(0, Math.min(1, centeredColor.y));
                centeredColor.z = Math.max(0, Math.min(1, centeredColor.z));
                const newColor = new THREE.Color(centeredColor.x, centeredColor.y, centeredColor.z);
                nodeObj.originalColor.copy(newColor);
                if (this.selectedId !== id && this.hoveredId !== id && (!this.searchResults || !this.searchResults.has(id))) {
                    nodeObj.mesh.setColorAt(nodeObj.instanceId, newColor);
                    nodeObj.mesh.instanceColor.needsUpdate = true;
                }
            }
        });

        if (this.seqLineMeshes) {
            this.seqLineMeshes.forEach(line => {
                const groupA = this.snapshotGroups.get(line.startData.snapshotIndex);
                const groupB = this.snapshotGroups.get(line.endData.snapshotIndex);
                if (!groupA || !groupB) return;
                
                const startWorld = line.startData.localPos.clone().applyMatrix4(groupA.matrixWorld);
                const endWorld = line.endData.localPos.clone().applyMatrix4(groupB.matrixWorld);
                const distance = startWorld.distanceTo(endWorld);
                
                line.mesh.position.copy(startWorld);
                line.mesh.scale.set(1, 1, distance);
                line.mesh.lookAt(endWorld);
            });
        }

        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
        
        const targetId = this.selectedId || this.hoveredId;
        if (targetId && document.getElementById('billboard').style.display === 'block') {
            const nodeObj = this.nodes.get(targetId);
            if (nodeObj) {
                const group = this.snapshotGroups.get(nodeObj.snapshotIndex);
                if (group) {
                    const initData = this.initialNodeData.get(targetId);
                    const worldPos = initData.localPos.clone().applyMatrix4(group.matrixWorld);
                    this.updateBillboardPosition({ position: worldPos });
                }
            }
        } else {
            this.hideBillboardArrow();
        }
    }



    // --- Rest of standard methods ---

    initSidebar() {
        const foldBtn = document.getElementById('fold-toggle-btn');
        if (foldBtn) {
            foldBtn.addEventListener('click', () => this.toggleFold());
        }

        const searchInput = document.getElementById('nl-search');
        if (searchInput) {
            // Debounced live search — re-read value at fire time to avoid
            // stale-closure single-token retrieval.
            let debounceTimer = null;
            searchInput.addEventListener('input', () => {
                clearTimeout(debounceTimer);
                if (!searchInput.value.trim()) {
                    this.clearSearchResults();
                    return;
                }
                debounceTimer = setTimeout(() => {
                    const q = searchInput.value.trim();
                    if (q) this.triggerDomTextSearch(q);
                }, 600);
            });
            // Enter = immediate search, cancel pending debounce
            searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    clearTimeout(debounceTimer);
                    const q = searchInput.value.trim();
                    if (q) this.triggerDomTextSearch(q);
                }
            });
        }
    }

    // --- DOM Text Search ---

    async triggerDomTextSearch(query) {
        if (!query) return;
        const container = document.getElementById('results-container');
        if (container) container.innerHTML = '<div class="empty-state" style="color:#6b7280;">Searching...</div>';

        try {
            // Determine URL from active stream or first known node
            let searchUrl = this._streamUrl || '';
            if (!searchUrl) {
                for (const [, d] of this.dataMap) {
                    if (d.url) { searchUrl = d.url; break; }
                }
            }

            const data = await this.client.searchDomText(query, searchUrl);
            const results = data.results || [];
            this.renderSearchResults(results, query);
        } catch (e) {
            console.error('[Search] DOM text search failed:', e);
            if (container) container.innerHTML = '<div class="empty-state" style="color:#ef4444;">Search failed.</div>';
        }
    }

    renderSearchResults(results, query) {
        const container = document.getElementById('results-container');
        if (!container) return;
        container.innerHTML = '';

        if (!results.length) {
            container.innerHTML = '<div class="empty-state" style="color:#6b7280;">No results found.</div>';
            return;
        }

        // Update 3D highlighting for search results
        this.searchResults = new Map();
        results.forEach(r => {
            if (this.nodes.has(r.id)) {
                this.searchResults.set(r.id, r.score);
            }
        });
        this._applySearchHighlights();

        // In fold mode, mark the MINIMUM path from each result up to the
        // root so retrieval only reveals the tree spine connecting hits —
        // no intermediate siblings are exposed.
        if (this._folded) {
            this._searchPathIds = new Set();
            this.searchResults.forEach((_, nodeId) => {
                this._markSearchPath(nodeId);
            });
            this.applyFilters();
        }

        results.forEach((result, idx) => {
            const card = document.createElement('div');
            card.className = 'result-card';
            card.style.cssText = `
                padding: 10px 12px;
                margin-bottom: 6px;
                background: rgba(255,255,255,0.04);
                border-radius: 6px;
                cursor: pointer;
                border-left: 3px solid ${result.is_content ? '#3b82f6' : '#4b5563'};
                transition: background 0.15s;
            `;
            card.addEventListener('mouseenter', () => {
                card.style.background = 'rgba(255,255,255,0.1)';
                if (this.nodes.has(result.id)) {
                    this.highlightTemporary(result.id);
                }
            });
            card.addEventListener('mouseleave', () => {
                card.style.background = 'rgba(255,255,255,0.04)';
                if (this.nodes.has(result.id)) {
                    this.restoreNodeVisuals(this.nodes.get(result.id));
                }
            });

            // Highlight the query in the snippet
            const snippet = this._highlightQuery(result.snippet || result.text || '', query);
            const scorePercent = Math.round((result.score || 0) * 100);
            const catChips = (result.categories || []).map(c =>
                `<span style="font-size:9px; padding:1px 4px; border-radius:8px; background:rgba(59,130,246,0.2); color:#93c5fd; margin-right:3px;">${c}</span>`
            ).join('');

            card.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span style="color:#e5e7eb; font-weight:600; font-size:12px;">
                        &lt;${result.tag || '?'}&gt;
                        <span style="color:#6b7280; font-weight:400; font-size:10px; margin-left:4px;">${result.name || ''}</span>
                    </span>
                    <span style="color:#9ca3af; font-size:10px;">${scorePercent}%</span>
                </div>
                <div style="font-size:11px; color:#d1d5db; line-height:1.4; margin-bottom:4px; max-height:48px; overflow:hidden;">${snippet}</div>
                <div style="display:flex; flex-wrap:wrap; gap:2px; align-items:center;">
                    ${catChips}
                    <span style="font-size:9px; color:#4b5563; margin-left:auto;" title="${result.xpath}">${this._truncXpath(result.xpath)}</span>
                </div>
            `;

            // Click to fly to node and open knowledge panel
            card.addEventListener('click', () => {
                this.flyToNodeAndSelect(result.id, result.url, result.xpath);
            });

            container.appendChild(card);
        });

        // Show result count header
        const header = document.createElement('div');
        header.style.cssText = 'color:#6b7280; font-size:11px; padding:4px 0 8px; border-bottom:1px solid rgba(255,255,255,0.05); margin-bottom:8px;';
        header.textContent = `${results.length} results`;
        container.insertBefore(header, container.firstChild);
    }

    _highlightQuery(text, query) {
        if (!query) return text;
        // Escape HTML entities first
        const escaped = text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        // Case-insensitive highlight
        const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        return escaped.replace(regex, '<mark style="background:#f59e0b; color:#000; padding:0 1px; border-radius:2px;">$1</mark>');
    }

    _truncXpath(xpath) {
        if (!xpath || xpath.length < 50) return xpath || '';
        const parts = xpath.split('/').filter(Boolean);
        if (parts.length <= 3) return xpath;
        return '/…/' + parts.slice(-3).join('/');
    }

    clearSearchResults() {
        const container = document.getElementById('results-container');
        if (container) container.innerHTML = '<div class="empty-state">Select a node or search to find content.</div>';
        this.searchResults = null;
        this._searchPathIds = null;
        // Reset colors to original, then re-overlay commutation colors
        this.nodes.forEach((nodeObj) => {
            nodeObj.mesh.setColorAt(nodeObj.instanceId, nodeObj.originalColor);
        });
        this._reapplyCommutationColors();
        this._flushInstanceColors();
        if (this._folded) this.applyFilters();
    }

    _applySearchHighlights() {
        if (!this.searchResults) return;
        this.nodes.forEach((nodeObj, id) => {
            if (this.searchResults.has(id)) {
                this.applySearchGlow(nodeObj, this.searchResults.get(id));
            } else if (id !== this.selectedId && id !== this.hoveredId) {
                nodeObj.mesh.setColorAt(nodeObj.instanceId, nodeObj.originalColor);
            }
        });
        this._flushInstanceColors();
    }

    // --- Fly-to-Node ---

    async flyToNodeAndSelect(nodeId, url, xpath) {
        // If the node exists in the 3D scene, fly to it
        const nodeObj = this.nodes.get(nodeId);
        if (nodeObj) {
            this.flyToNode(nodeId);
            await this.selectNode(nodeId);
        } else {
            // Node might not be in the content-distilled set but exists in raw DOM.
            // Fetch its detail and show in a billboard at screen center.
            try {
                const details = await this.client.getMapDetail(url, xpath);
                details.id = nodeId;
                details.name = details.tag || '';
                details.status = 'unreviewed';
                details.tags = [];
                details.nodeAttributes = details.attributes || {};
                details.categories = details.categories || [];
                details.xpath = xpath;
                this.showBillboard(details, true);

                // Position billboard at screen center since there's no 3D node
                const billboard = document.getElementById('billboard');
                if (billboard) {
                    billboard.style.left = '50%';
                    billboard.style.top = '50%';
                    billboard.style.transform = 'translate(-50%, -50%)';
                }
            } catch (e) {
                console.error('[FlyTo] Failed to fetch node detail:', e);
            }
        }
    }

    flyToNode(nodeId) {
        const nodeObj = this.nodes.get(nodeId);
        if (!nodeObj || !this.camera || !this.controls) return;

        const initData = this.initialNodeData.get(nodeId);
        const group = this.snapshotGroups.get(nodeObj.snapshotIndex);
        if (!initData || !group) return;

        const worldPos = initData.localPos.clone().applyMatrix4(group.matrixWorld);
        const distance = 30; // Close-up distance
        const dir = new THREE.Vector3().subVectors(this.camera.position, this.controls.target).normalize();

        // Target camera position: slightly in front of the node
        const targetPos = worldPos.clone().add(dir.multiplyScalar(distance));
        const targetLookAt = worldPos.clone();

        // Animate camera smoothly
        this._animateCameraTo(targetPos, targetLookAt, 600);
    }

    _animateCameraTo(targetPos, targetLookAt, durationMs) {
        const startPos = this.camera.position.clone();
        const startTarget = this.controls.target.clone();
        const startTime = performance.now();

        const animateStep = () => {
            const elapsed = performance.now() - startTime;
            const t = Math.min(elapsed / durationMs, 1);
            // Ease-out cubic
            const ease = 1 - Math.pow(1 - t, 3);

            this.camera.position.lerpVectors(startPos, targetPos, ease);
            this.controls.target.lerpVectors(startTarget, targetLookAt, ease);
            this.controls.update();

            if (t < 1) {
                requestAnimationFrame(animateStep);
            }
        };
        requestAnimationFrame(animateStep);
    }

    renderTagFilters() {
        const container = document.getElementById('tag-filters-list');
        const wrapper = document.getElementById('tag-filter-container');
        if (!container || !wrapper) return;

        container.innerHTML = '';
        if (this.allTags.size === 0) {
            wrapper.style.display = 'none';
            return;
        }
        wrapper.style.display = 'block';
        
        this.allTags.forEach(tag => {
            const chip = document.createElement('div');
            chip.className = 'filter-chip';
            chip.textContent = tag;
            chip.onclick = () => {
                if (this.activeTags.has(tag)) {
                    this.activeTags.delete(tag);
                    chip.classList.remove('active');
                } else {
                    this.activeTags.add(tag);
                    chip.classList.add('active');
                }
                this.applyFilters();
                if (this.lastResults) this.renderResults(this.lastResults);
            };
            container.appendChild(chip);
        });
    }

    
    applyFilters() {
        const dummy = new THREE.Object3D();

        // Track which nodes are visible this pass so we can filter edges.
        const visibleIds = new Set();

        this.nodes.forEach((nodeObj, id) => {
            const data = this.dataMap.get(id);
            const isMatch = this.checkFilterMatch(data);
            const isSearchResult = this.searchResults && this.searchResults.has(id);
            const isSearchPath = this._searchPathIds && this._searchPathIds.has(id);

            let visible;
            if (this._pathIsolationIds) {
                // Double-click isolate mode: only nodes on the isolated
                // path are shown; everything else is hidden regardless
                // of other state.
                visible = this._pathIsolationIds.has(id);
            } else if (this._folded) {
                // Interactive fold: roots always visible; children visible only
                // when their parent has been explicitly unfolded by the user.
                const isRoot = !!(data && data.is_root);
                const isLabeled = !!(data && (data.nodeLabel || data.label));
                const isCommuted = this._commutedIds && this._commutedIds.has(id);
                const isSelected = (id === this.selectedId);
                const parentId = this._parentMap.get(id);
                const parentUnfolded = parentId && this._unfoldedIds.has(parentId);
                const selfUnfolded = this._unfoldedIds.has(id);
                const isNeighbor = this._neighborVisibleIds && this._neighborVisibleIds.has(id);
                visible = isRoot || parentUnfolded || selfUnfolded
                        || isLabeled || isSearchResult || isSearchPath
                        || isCommuted || isSelected || isNeighbor;
            } else {
                visible = (isMatch || isSearchResult);
            }

            // Card-fold: card nodes are always visible; descendants of
            // an unselected card are hidden. This runs on top of the
            // other visibility logic so full fold/isolate still win.
            if (visible && !this._pathIsolationIds && this._cardModeEnabled) {
                const isCard = this._cardIds && this._cardIds.has(id);
                if (isCard) {
                    visible = true;
                } else if (this._isHiddenByCard(id) && id !== this.selectedId) {
                    visible = false;
                }
            }
            const initData = this.initialNodeData.get(id);

            dummy.position.copy(initData.localPos);
            if (!visible) {
                dummy.scale.set(0, 0, 0);
            } else if (nodeObj.isImageBillboard) {
                // Node is represented by a Sprite — keep the sphere
                // invisible so the billboard image stands alone.
                dummy.scale.set(0.001, 0.001, 0.001);
                visibleIds.add(id);
            } else {
                dummy.scale.set(1, 1, 1);
                visibleIds.add(id);
            }

            dummy.updateMatrix();
            nodeObj.mesh.setMatrixAt(nodeObj.instanceId, dummy.matrix);

            // Also hide/show the image sprite for this node
            if (nodeObj.imageSprite) nodeObj.imageSprite.visible = visible;
        });

        // Filter structural edge instances: show only edges where BOTH
        // endpoints are visible.  This keeps the tree structure clear while
        // the user progressively unfolds the graph.
        if (this._linkInstData && (this._folded || this._cardModeEnabled || this._pathIsolationIds)) {
            this._linkInstData.forEach(({sourceId, targetId, mesh, instId, origMatrix}) => {
                if (visibleIds.has(sourceId) && visibleIds.has(targetId)) {
                    mesh.setMatrixAt(instId, origMatrix);
                } else {
                    dummy.position.set(0, 0, 0);
                    dummy.scale.set(0, 0, 0);
                    dummy.updateMatrix();
                    mesh.setMatrixAt(instId, dummy.matrix);
                }
            });
        }

        if(this.snapshotGroups) {
            Array.from(this.snapshotGroups.values()).forEach(g => {
                if (g.userData.nodesMesh) g.userData.nodesMesh.instanceMatrix.needsUpdate = true;
                // In fold mode we keep structMesh visible but filter individual
                // instances above.  In unfold mode everything is shown.
                if (g.userData.structMesh) {
                    g.userData.structMesh.visible = true;
                    g.userData.structMesh.instanceMatrix.needsUpdate = true;
                }
            });
        }
        if (this.seqLineMeshes) {
            this.seqLineMeshes.forEach(l => {
                if (l.mesh) l.mesh.visible = !this._folded;
            });
        }

        // Reapply persistent commutation colors after any filter pass
        this._reapplyCommutationColors();
        this._flushInstanceColors();
    }

    toggleFold() {
        this._folded = !this._folded;
        // Any new fold state invalidates the transient isolation mode.
        this._pathIsolationIds = null;
        if (this._folded) {
            this._unfoldedIds = new Set();
            this._neighborVisibleIds = new Set();
            // Preserve minimum search paths so retrieval results stay
            // connected to the root after a re-fold.
            if (this.searchResults) {
                this._searchPathIds = new Set();
                this.searchResults.forEach((_, nodeId) => {
                    this._markSearchPath(nodeId);
                });
            }
        }
        const label = document.getElementById('fold-toggle-label');
        const btn = document.getElementById('fold-toggle-btn');
        if (label) label.textContent = this._folded ? 'Unfold DOM' : 'Fold DOM';
        if (btn) {
            btn.style.background = this._folded ? 'rgba(245,158,11,0.2)' : 'rgba(96,165,250,0.15)';
            btn.style.borderColor = this._folded ? '#f59e0b' : '#60a5fa';
            btn.style.color = this._folded ? '#f59e0b' : '#60a5fa';
        }
        this.applyFilters();
    }

    /** Build parent↔children maps from the current link set. */
    _buildTreeMaps() {
        this._childrenMap = new Map();
        this._parentMap = new Map();
        (this.links || []).forEach(link => {
            if (link.type !== 'structure') return;
            // mapper: source = child, target = parent
            const childId = link.source;
            const parentId = link.target;
            this._parentMap.set(childId, parentId);
            if (!this._childrenMap.has(parentId)) this._childrenMap.set(parentId, new Set());
            this._childrenMap.get(parentId).add(childId);
        });
    }

    /** Walk up the parent chain, adding each ancestor to _unfoldedIds
     *  so the tree path from root to this node is visible with edges.
     *  NOTE: this unfolds each ancestor, which also exposes siblings of
     *  intermediate nodes. Prefer _markSearchPath for search results so
     *  only the minimum path (not the full subtree) is revealed. */
    _unfoldAncestors(id) {
        let cur = id;
        while (cur) {
            const parentId = this._parentMap.get(cur);
            if (!parentId) break;
            if (this._unfoldedIds.has(parentId)) break; // already open above
            this._unfoldedIds.add(parentId);
            cur = parentId;
        }
    }

    /** Add only the nodes on the path from ``id`` up to the root into
     *  ``_searchPathIds``. Unlike ``_unfoldAncestors`` this does NOT
     *  unfold intermediate parents, so siblings of the path stay hidden
     *  — the "minimum tree path" visualisation for retrieval results. */
    _markSearchPath(id) {
        if (!this._searchPathIds) this._searchPathIds = new Set();
        let cur = id;
        while (cur) {
            if (this._searchPathIds.has(cur)) break;
            this._searchPathIds.add(cur);
            cur = this._parentMap.get(cur);
        }
    }

    /** Recursively remove a node and all descendants from _unfoldedIds. */
    _foldSubtree(id) {
        this._unfoldedIds.delete(id);
        const children = this._childrenMap.get(id);
        if (children) {
            children.forEach(childId => this._foldSubtree(childId));
        }
    }



    checkFilterMatch(data) {
        // Status checkboxes were removed — status no longer filters visibility.
        if (this.activeTags.size === 0) return true;
        const nodeTags = new Set(data.tags || []);
        return [...this.activeTags].some(t => nodeTags.has(t));
    }

    renderResults(results) {
        const container = document.getElementById('results-container');
        container.innerHTML = '';
        
        results.forEach(item => {
            if (!this.checkFilterMatch(item)) return;

            const card = document.createElement('div');
            card.className = `result-card ${item.id === this.selectedId ? 'selected' : ''}`;
            
            const mesh = this.nodes.get(item.id);
            if (mesh) {
                const color = mesh.originalColor;
                const cssColor = `#${color.getHexString()}`;

                card.style.borderLeft = `4px solid ${cssColor}`;
                card.style.background = `linear-gradient(90deg, rgba(${color.r*255},${color.g*255},${color.b*255},0.15) 0%, rgba(37, 40, 48, 0.6) 100%)`;
            }

            card.innerHTML = `
                <div class="card-header">
                    <span class="card-title">${item.name}</span>
                    <span class="card-score">${(item.score * 100).toFixed(0)}% Match</span>
                </div>
                <div class="card-meta">${item.location}</div>
                <div class="card-desc">${item.description}</div>
                <div class="tags-input-container">
                    <div class="tags-list" id="tags-${item.id}"></div>
                    <input type="text" class="tag-input" placeholder="+ Add tag (Enter)" data-id="${item.id}">
                </div>
            `;

            card.addEventListener('mouseenter', () => {
                const mesh = this.nodes.get(item.id);
                if(mesh) { mesh.mesh.setColorAt(mesh.instanceId, new THREE.Color(0xffff00)); mesh.mesh.instanceColor.needsUpdate = true; }
            });

            card.addEventListener('mouseleave', () => {
                const mesh = this.nodes.get(item.id);
                if (mesh && item.id !== this.selectedId) {
                    this.restoreNodeVisuals(mesh);
                }
            });

            card.addEventListener('click', (e) => {
                if (e.target.tagName === 'INPUT' || e.target.classList.contains('tag-remove')) return;
                this.selectNode(item.id);
            });

            const tagInput = card.querySelector('.tag-input');
            const tagsList = card.querySelector('.tags-list');
            if (item.tags) {
                item.tags.forEach(tag => this.addTagToUi(tagsList, tag, item.id));
            }

            tagInput.addEventListener('keypress', async (e) => {
                if (e.key === 'Enter' && tagInput.value.trim()) {
                    const newTag = tagInput.value.trim();
                    this.addTagToNode(item.id, newTag);
                    tagInput.value = '';
                }
            });

            container.appendChild(card);
        });
    }

    addTagToUi(container, tagText, nodeId) {
        const chip = document.createElement('span');
        chip.className = 'tag-chip';
        chip.innerHTML = `${tagText} <i class="fas fa-times tag-remove"></i>`;
        
        chip.querySelector('.tag-remove').onclick = async () => {
            chip.remove();
            const nodeData = this.dataMap.get(nodeId);
            if (nodeData && nodeData.tags) {
                nodeData.tags = nodeData.tags.filter(t => t !== tagText);
                await this.client.updateNode(nodeId, undefined, nodeData.tags);
                if (this.selectedId === nodeId) {
                    this.renderQuickTags(nodeId);
                }
            }
        };
        container.appendChild(chip);
    }

    async addTagToNode(nodeId, newTag) {
        if (!newTag) return;
        const nodeData = this.dataMap.get(nodeId);
        if (!nodeData) return;
        if (!nodeData.tags) nodeData.tags = [];
        if (nodeData.tags.includes(newTag)) return;

        nodeData.tags.push(newTag);
        this.allTags.add(newTag);
        this.renderTagFilters();

        await this.client.updateNode(nodeId, undefined, nodeData.tags);

        const billboardList = document.getElementById('billboard-tags-list');
        if (billboardList && (this.selectedId === nodeId || this.hoveredId === nodeId)) {
            this.addTagToUi(billboardList, newTag, nodeId);
        }
        
        const sidebarList = document.getElementById(`tags-${nodeId}`);
        if (sidebarList) {
            this.addTagToUi(sidebarList, newTag, nodeId);
        }
        this.renderQuickTags(nodeId);
    }

    initBillboardTags() {
        const tagInput = document.getElementById('billboard-tag-input');
        if (tagInput) {
            tagInput.addEventListener('keypress', async (e) => {
                if (e.key === 'Enter' && tagInput.value.trim()) {
                    const targetId = this.selectedId || this.hoveredId;
                    if (!targetId) return;
                    this.addTagToNode(targetId, tagInput.value.trim());
                    tagInput.value = '';
                }
            });
        }

        // Ontology label input
        const labelInput = document.getElementById('billboard-label-input');
        if (labelInput) {
            labelInput.addEventListener('keydown', async (e) => {
                if (e.key === 'Enter' && labelInput.value.trim()) {
                    e.preventDefault();
                    e.stopPropagation();
                    const targetId = this.selectedId || this.hoveredId;
                    if (!targetId) return;
                    const data = this.dataMap.get(targetId);
                    if (!data) return;
                    const labelVal = labelInput.value.trim();
                    const singleInstance = e.shiftKey;
                    // Immediately update local dataMap so fold-mode keeps the
                    // node visible as "labeled" even before the API returns.
                    data.label = labelVal;
                    data.nodeLabel = labelVal;
                    await this.applyOntologyLabel(data.url, data.xpath, labelVal, data.snapshotIndex, singleInstance);
                    labelInput.value = '';
                    // Keep billboard open — re-render panel with new label info
                    const billboard = document.getElementById('billboard');
                    if (billboard) billboard.style.display = 'block';
                    this.renderKnowledgePanel(data);
                }
            });
        }
    }

    async applyOntologyLabel(url, xpath, label, snapshotId, singleInstance = false) {
        const statusEl = document.getElementById('billboard-label-status');
        const infoEl = document.getElementById('billboard-label-info');
        if (statusEl) statusEl.textContent = 'Applying...';

        try {
            const result = await this.client.applyLabel(url, xpath, label, snapshotId, {
                autoCommute: singleInstance ? false : this.cadTools.autoCommute,
                autoLca: true
            });

            if (statusEl) statusEl.textContent = 'Applied';
            if (infoEl) {
                infoEl.innerHTML = `
                    Commuted to ${result.commuted_xpaths ? result.commuted_xpaths.length : 0} matching nodes<br>
                    LCA: <code>${result.lca_xpath || '/'}</code>
                `;
            }

            // Highlight the LCA subtree (members + connecting structure)
            if (result.lca_xpath && result.lca_xpath !== '/') {
                this.highlightLcaSubtree(url, label);
            } else if (result.commuted_xpaths && result.commuted_xpaths.length > 0) {
                this.highlightLabelGroup(url, label);
            }

            setTimeout(() => { if (statusEl) statusEl.textContent = ''; }, 3000);
        } catch (e) {
            console.error('[Label] Error:', e);
            if (statusEl) { statusEl.textContent = 'Error'; statusEl.style.color = 'red'; }
        }
    }

    async highlightLabelGroup(url, label) {
        try {
            const data = await this.client.getLabels(url);
            const group = (data.labels || []).find(l => l.label === label);
            if (!group) return;

            const lcaXpath = group.lca_xpath || '/';
            const labelColor = new THREE.Color(0xff8c00); // Orange for labeled

            // Highlight all nodes whose xpath starts with the LCA
            this.dataMap.forEach((nodeData, nodeId) => {
                if (nodeData.url !== url) return;
                const xp = nodeData.xpath || '';
                if (xp.startsWith(lcaXpath)) {
                    const nodeObj = this.nodes.get(nodeId);
                    if (nodeObj) {
                        nodeObj.mesh.setColorAt(nodeObj.instanceId, labelColor);
                        nodeObj.mesh.instanceColor.needsUpdate = true;
                    }
                }
            });
        } catch (e) {
            console.error('[Label] Highlight error:', e);
        }
    }

    // --- LCA Subtree Highlighting (§22 Patricia Path Tree) ---

    async highlightLcaSubtree(url, label) {
        /**
         * Highlights the full connecting structure between labeled nodes:
         * the LCA subtree spanning all instances of a label group.
         *
         * Member nodes (directly labeled) → bright orange
         * LCA subtree nodes (connecting structure) → dim gold
         * LCA root node → pulsing yellow
         */
        try {
            const data = await this.client.getLcaSubtree(url, label);
            const memberSet = new Set(data.member_xpaths || []);
            const subtreeSet = new Set(data.subtree_xpaths || []);
            const lcaXpath = data.lca_xpath || '/';

            const memberColor = new THREE.Color(0xff8c00);   // Bright orange — labeled instances
            const subtreeColor = new THREE.Color(0xb8860b);  // Dark goldenrod — connecting structure
            const lcaColor = new THREE.Color(0xffd700);      // Gold — LCA root

            // First, reset all to original
            this.clearHighlights();

            let highlightCount = 0;
            this.dataMap.forEach((nodeData, nodeId) => {
                if (nodeData.url !== url) return;
                const xp = nodeData.xpath || '';
                const nodeObj = this.nodes.get(nodeId);
                if (!nodeObj) return;

                if (xp === lcaXpath) {
                    nodeObj.mesh.setColorAt(nodeObj.instanceId, lcaColor);
                    highlightCount++;
                } else if (memberSet.has(xp)) {
                    nodeObj.mesh.setColorAt(nodeObj.instanceId, memberColor);
                    highlightCount++;
                } else if (subtreeSet.has(xp)) {
                    nodeObj.mesh.setColorAt(nodeObj.instanceId, subtreeColor);
                    highlightCount++;
                }
            });
            this._flushInstanceColors();
            console.log(`[LCA] Highlighted ${highlightCount} nodes in subtree for label "${label}" (LCA: ${lcaXpath})`);
        } catch (e) {
            console.error('[LCA] Subtree highlight error:', e);
        }
    }

    // --- Commutation Highlighting (Lateral Pattern Matching) ---

    async highlightCommutation(url, xpath) {
        /**
         * Highlights all content nodes sharing the same generalized xpath
         * pattern — the lateral commutation group. These are structurally
         * equivalent nodes (e.g., all <li><a> in a list, all <td> in a
         * column) that would receive the same label under auto-commute.
         *
         * Source node → bright cyan
         * Pattern matches → medium teal
         */
        try {
            const data = await this.client.getCommutationMatches(url, xpath);
            const matchSet = new Set(data.matching_xpaths || []);
            const pattern = data.pattern || '';

            const sourceColor = new THREE.Color(0x00ffff);  // Cyan — source
            const matchColor = new THREE.Color(0x2dd4bf);   // Teal — pattern match
            this._commutationPalette = { source: 0x00ffff, match: 0x2dd4bf };

            // First, reset all to original
            this.clearHighlights();

            let highlightCount = 0;
            this._commutedIds = new Set();
            this._commutationSourceId = null;
            this.dataMap.forEach((nodeData, nodeId) => {
                if (nodeData.url !== url) return;
                const xp = nodeData.xpath || '';
                const nodeObj = this.nodes.get(nodeId);
                if (!nodeObj) return;

                if (xp === xpath) {
                    nodeObj.mesh.setColorAt(nodeObj.instanceId, sourceColor);
                    this._commutedIds.add(nodeId);
                    this._commutationSourceId = nodeId;
                    highlightCount++;
                } else if (matchSet.has(xp)) {
                    nodeObj.mesh.setColorAt(nodeObj.instanceId, matchColor);
                    this._commutedIds.add(nodeId);
                    highlightCount++;
                }
            });
            this._flushInstanceColors();
            console.log(`[Commutation] Highlighted ${highlightCount} nodes matching pattern "${pattern}"`);

            // Re-apply filters so folded mode picks up the new commutation set
            if (this._folded) this.applyFilters();

            // Show pattern info in the billboard label-info area
            const infoEl = document.getElementById('billboard-label-info');
            if (infoEl && highlightCount > 1) {
                infoEl.innerHTML = `
                    <span style="color:#2dd4bf;">Pattern:</span> <code style="font-size:9px;">${pattern}</code><br>
                    <span style="color:#2dd4bf;">${data.match_count} structural matches</span>
                `;
            }
        } catch (e) {
            console.error('[Commutation] Highlight error:', e);
        }
    }

    // --- Subgroup Commutation (LCA-aware pattern-set isomorphism) ---

    async highlightSubgroupCommutation(url, xpath) {
        /**
         * Subgroup commutation: only highlights nodes whose descendant
         * generalized-xpath pattern set matches the source's, restricted
         * to members of "connected LCA groups" (≥2 labeled nodes with a
         * labeled LCA). Distinct purple palette to contrast with raw
         * pattern-equality commutation.
         *
         * Source → violet
         * Subgroup matches → lavender
         */
        try {
            const data = await this.client.getSubgroupCommutationMatches(url, xpath);
            const matchSet = new Set(data.matching_xpaths || []);

            if (data.reason) {
                const infoEl = document.getElementById('billboard-label-info');
                if (infoEl) {
                    const msgs = {
                        no_tree: 'No content tree available for this URL.',
                        no_labeled_lca_group:
                            'Needs ≥2 labeled nodes whose LCA is also labeled.',
                        empty_source_subtree: 'Source subtree has no descendants.',
                    };
                    infoEl.innerHTML = `<span style="color:#ef4444;">Subgroup commutation unavailable:</span> ${msgs[data.reason] || data.reason}`;
                }
                return;
            }

            const sourceColor = new THREE.Color(0xa855f7);  // violet
            const matchColor = new THREE.Color(0xc4b5fd);   // lavender
            this._commutationPalette = { source: 0xa855f7, match: 0xc4b5fd };

            this.clearHighlights();

            let highlightCount = 0;
            this._commutedIds = new Set();
            this._commutationSourceId = null;
            this.dataMap.forEach((nodeData, nodeId) => {
                if (nodeData.url !== url) return;
                const xp = nodeData.xpath || '';
                const nodeObj = this.nodes.get(nodeId);
                if (!nodeObj) return;

                if (xp === xpath) {
                    nodeObj.mesh.setColorAt(nodeObj.instanceId, sourceColor);
                    this._commutedIds.add(nodeId);
                    this._commutationSourceId = nodeId;
                    highlightCount++;
                } else if (matchSet.has(xp)) {
                    nodeObj.mesh.setColorAt(nodeObj.instanceId, matchColor);
                    this._commutedIds.add(nodeId);
                    highlightCount++;
                }
            });
            this._flushInstanceColors();

            if (this._folded) this.applyFilters();

            const infoEl = document.getElementById('billboard-label-info');
            if (infoEl) {
                const groupCount = (data.groups || []).length;
                const patternCount = (data.pattern_set || []).length;
                infoEl.innerHTML = `
                    <span style="color:#a855f7;">Subgroup:</span>
                    ${data.match_count} matches across ${groupCount} labeled group(s)<br>
                    <span style="color:#6b7280; font-size:9px;">Pattern set size: ${patternCount}</span>
                `;
            }

            console.log(`[SubgroupCommutation] ${highlightCount} matches across ${(data.groups || []).length} groups`);
        } catch (e) {
            console.error('[SubgroupCommutation] Highlight error:', e);
        }
    }

    // --- Post-scan Chunk Cards ---
    //
    // A "chunk" is a budget-sized partition of the distilled DOM. Each
    // member xpath becomes a "card" node in the 3D scene: its descendant
    // subtree is auto-folded behind it, and its sphere is swapped for an
    // image billboard when the subtree contains media. Selecting a card
    // unfolds its full subtree (not just rank-1) and renders an aggregated
    // knowledge panel over content_fields tagged during scanning.

    _hashChunkId(chunkId) {
        let h = 2166136261 >>> 0;
        for (let i = 0; i < chunkId.length; i++) {
            h ^= chunkId.charCodeAt(i);
            h = Math.imul(h, 16777619) >>> 0;
        }
        return h;
    }

    _chunkColor(chunkId) {
        const h = this._hashChunkId(chunkId);
        const hue = ((h >>> 0) % 360) / 360;
        return new THREE.Color().setHSL(hue, 0.72, 0.6);
    }

    /** Walk every card member down to its descendants so we know which
     *  nodes belong to each card's subtree. */
    _rebuildCardSubtreeIndex() {
        this._cardContainingCard = new Map();   // nodeId -> cardId (card this node lives under)
        this._cardDescendants = new Map();      // cardId -> Set of descendant nodeIds
        if (!this._cardIds || !this._childrenMap) return;
        this._cardIds.forEach(cardId => {
            const descendants = new Set();
            const stack = [cardId];
            while (stack.length) {
                const n = stack.pop();
                const kids = this._childrenMap.get(n);
                if (!kids) continue;
                kids.forEach(k => {
                    // Don't cross into another card — that card owns its own subtree.
                    if (this._cardIds.has(k)) return;
                    if (!descendants.has(k)) {
                        descendants.add(k);
                        this._cardContainingCard.set(k, cardId);
                        stack.push(k);
                    }
                });
            }
            this._cardDescendants.set(cardId, descendants);
        });
    }

    /** Handler for the post-scan 'chunks' frame. Marks card nodes, folds
     *  their subtrees, swaps image-bearing cards for billboards, and
     *  refreshes the knowledge panel if the selected node is a card.
     *
     *  Treated as the AUTHORITATIVE final state: replaces any chunks
     *  the absorber's progressive 'chunk_added' / 'chunk_replaced'
     *  events accumulated during the scan. Safe to call after any
     *  number of incremental events. */
    onChunksArrived(payload) {
        const chunks = payload.chunks || [];
        const url = payload.url || this._streamUrl || '';
        if (!chunks.length) return;

        this._chunksById = new Map();
        this._cardIds = new Set();
        this._cardMeta = new Map();  // nodeId -> {chunk, memberXpath, imageUrl}

        chunks.forEach(chunk => {
            this._mergeChunkState(chunk, url);
        });

        this._rebuildCardSubtreeIndex();
        this._applyCardVisuals();
        this._enableCardFoldMode();

        // If the user had a card selected before the chunks arrived,
        // re-render its panel to pick up the freshly attached fields.
        if (this.selectedId && this._cardIds.has(this.selectedId)) {
            this.selectNode(this.selectedId);
        }

        console.log(`[Cards] ${chunks.length} chunks → ${this._cardIds.size} card nodes`);
    }

    /** Merge a single chunk into the projector's card-state maps.
     *  Shared helper for the post-scan ``chunks`` batch and the
     *  per-iteration ``chunk_added`` / ``chunk_replaced`` events. */
    _mergeChunkState(chunk, url) {
        if (!chunk || !chunk.chunk_id) return;
        if (!this._chunksById) this._chunksById = new Map();
        if (!this._cardIds)    this._cardIds    = new Set();
        if (!this._cardMeta)   this._cardMeta   = new Map();

        this._chunksById.set(chunk.chunk_id, chunk);
        const imageUrls = chunk.image_urls || {};
        (chunk.member_xpaths || []).forEach(xp => {
            const nodeId = `${url}:${xp}`;
            this._cardIds.add(nodeId);
            this._cardMeta.set(nodeId, {
                chunkId: chunk.chunk_id,
                memberXpath: xp,
                imageUrl: imageUrls[xp] || null,
            });
            const data = this.dataMap.get(nodeId);
            if (data) {
                data.is_card = true;
                data.chunk_id = chunk.chunk_id;
                data.chunk_pattern = chunk.pattern;
                data.chunk_label = chunk.label || null;
                data.chunk_char_count = chunk.char_count;
                data.chunk_commutation_count = chunk.commutation_count;
                data.chunk_content_fields = chunk.content_fields || {};
                data.chunk_text_preview = chunk.text_preview || '';
                data.card_image_url = imageUrls[xp] || null;
            }
        });
    }

    /** Drop the chunk and all of its associated card-state from the
     *  projector. Called when the absorber emits a ``chunk_replaced``
     *  event referencing a now-superseded chunk_id (e.g. iter N had
     *  12 cards, iter N+1 has 24 — the 12-member chunk is evicted). */
    _dropChunkState(replacedChunkId) {
        if (!replacedChunkId) return;
        if (!this._chunksById || !this._chunksById.has(replacedChunkId)) return;

        const old = this._chunksById.get(replacedChunkId);
        this._chunksById.delete(replacedChunkId);

        const url = this._streamUrl || '';
        (old.member_xpaths || []).forEach(xp => {
            const nodeId = `${url}:${xp}`;
            // Only drop if no other (newer) chunk has already claimed
            // this xpath. The absorber feeds replacement BEFORE eviction,
            // so a still-present meta entry whose chunkId no longer
            // matches the old means a newer chunk owns it — leave it.
            const meta = this._cardMeta && this._cardMeta.get(nodeId);
            if (meta && meta.chunkId === replacedChunkId) {
                this._cardMeta.delete(nodeId);
                if (this._cardIds) this._cardIds.delete(nodeId);
                const data = this.dataMap.get(nodeId);
                if (data) {
                    data.is_card = false;
                    data.chunk_id = null;
                }
            }
        });
    }

    /** Per-iteration handler invoked while a scan is still in progress.
     *  ``replacedChunkId`` is non-null when the absorber decided this
     *  pattern's earlier emission is now stale (e.g. an infinite-scroll
     *  list grew from 12 → 24 cards). */
    onChunkAbsorbEvent(payload) {
        const chunk = payload.chunk;
        const url = payload.url || this._streamUrl || '';
        if (!chunk) return;

        if (payload.type === 'chunk_replaced' && payload.replaced_chunk_id) {
            this._dropChunkState(payload.replaced_chunk_id);
        }
        this._mergeChunkState(chunk, url);

        // _rebuildCardSubtreeIndex + _applyCardVisuals together walk
        // every card's subtree; running them on EVERY absorber event
        // (3-6 per scan, plus they may arrive back-to-back over a
        // single WebSocket flush) is wasted CPU. Schedule a single
        // coalesced refresh at the next animation frame so multiple
        // events that arrive in the same tick collapse to one redraw.
        this._scheduleCardRefresh();
    }

    /** Coalesce card-state redraw work into a single frame. Multiple
     *  ``chunk_added`` / ``chunk_replaced`` events landing in the same
     *  tick share one rAF callback instead of triggering N walks of
     *  the card subtree. */
    _scheduleCardRefresh() {
        if (this._cardRefreshScheduled) return;
        this._cardRefreshScheduled = true;
        const run = () => {
            this._cardRefreshScheduled = false;
            this._rebuildCardSubtreeIndex();
            this._applyCardVisuals();
            this._enableCardFoldMode();
            if (this.selectedId && this._cardIds && this._cardIds.has(this.selectedId)) {
                this.selectNode(this.selectedId);
            }
        };
        if (typeof requestAnimationFrame === 'function') {
            requestAnimationFrame(run);
        } else {
            setTimeout(run, 16);
        }
    }

    /** Color every card sphere by chunk_id hash and spawn an image billboard
     *  for any card whose subtree had a media/image resource. Non-card
     *  descendants keep their original UMAP color. */
    _applyCardVisuals() {
        if (!this._cardIds) return;
        const cardsWithImages = [];
        this._cardIds.forEach(nodeId => {
            const nodeObj = this.nodes.get(nodeId);
            const meta = this._cardMeta.get(nodeId);
            if (!nodeObj || !meta) return;
            const color = this._chunkColor(meta.chunkId);
            nodeObj.originalColor.copy(color);
            if (!this.selectedId || this.selectedId !== nodeId) {
                nodeObj.mesh.setColorAt(nodeObj.instanceId, color);
            }
            if (meta.imageUrl) {
                const data = this.dataMap.get(nodeId);
                if (data) {
                    // Let _spawnImageBillboards find the URL via node.src
                    if (!data.src) data.src = meta.imageUrl;
                    cardsWithImages.push(data);
                }
            }
        });
        this._flushInstanceColors();

        if (cardsWithImages.length) {
            // Group cards-with-images by snapshot index and spawn through
            // the existing billboard pipeline.
            const bySnap = new Map();
            cardsWithImages.forEach(n => {
                const init = this.initialNodeData.get(n.id);
                if (!init) return;
                if (!bySnap.has(init.snapshotIndex)) bySnap.set(init.snapshotIndex, []);
                bySnap.get(init.snapshotIndex).push(n);
            });
            bySnap.forEach((cards, sIdx) => {
                const group = this.snapshotGroups.get(sIdx);
                if (group) this._spawnImageBillboards(group, cards, sIdx);
            });
        }
    }

    /** Enable card-fold visibility. Unlike the global fold toggle this
     *  only hides descendants of card nodes — every other node in the
     *  DOM keeps its existing visibility. Users can still toggle full
     *  fold mode separately. */
    _enableCardFoldMode() {
        if (!this._cardIds || !this._cardIds.size) return;
        this._cardModeEnabled = true;
        if (!this._unfoldedCardIds) this._unfoldedCardIds = new Set();
        this.applyFilters();
    }

    /** Is this node inside the folded-away subtree of an unselected card? */
    _isHiddenByCard(id) {
        if (!this._cardModeEnabled) return false;
        const cardId = this._cardContainingCard && this._cardContainingCard.get(id);
        if (!cardId) return false;
        return !(this._unfoldedCardIds && this._unfoldedCardIds.has(cardId));
    }

    /** Unfold every descendant of a card so its entire subtree becomes
     *  visible. Used when the user selects a card. */
    unfoldCardSubtree(cardId) {
        if (!this._unfoldedCardIds) this._unfoldedCardIds = new Set();
        this._unfoldedCardIds.add(cardId);
        // Also add all descendants to _unfoldedIds so global fold mode
        // (if later toggled on) still shows them.
        if (!this._unfoldedIds) this._unfoldedIds = new Set();
        this._unfoldedIds.add(cardId);
        const descendants = this._cardDescendants && this._cardDescendants.get(cardId);
        if (descendants) descendants.forEach(d => this._unfoldedIds.add(d));
        this.applyFilters();
    }

    /** Re-collapse a card's descendants. */
    foldCardSubtree(cardId) {
        if (this._unfoldedCardIds) this._unfoldedCardIds.delete(cardId);
        const descendants = this._cardDescendants && this._cardDescendants.get(cardId);
        if (descendants && this._unfoldedIds) {
            descendants.forEach(d => this._unfoldedIds.delete(d));
        }
        this.applyFilters();
    }

    renderKnowledgePanel(details) {
        // --- Knowledge Table: tag row + attribute rows ---
        const tagCell = document.getElementById('billboard-tag-cell');
        const segCell = document.getElementById('billboard-segment-cell');
        const tbody = document.getElementById('billboard-table-body');

        if (tagCell) tagCell.textContent = details.tag || details.name || '';
        if (segCell) {
            // Segment assignment = last part of xpath
            const xpath = details.xpath || '';
            const parts = xpath.split('/').filter(Boolean);
            segCell.textContent = parts.length > 0 ? parts[parts.length - 1] : '';
        }

        // Clear old attribute rows (keep the tag row)
        if (tbody) {
            const tagRow = document.getElementById('billboard-row-tag');
            tbody.innerHTML = '';
            if (tagRow) tbody.appendChild(tagRow);

            // Inject attribute rows
            const attrs = details.nodeAttributes || details.attributes || {};
            Object.entries(attrs).forEach(([k, v]) => {
                const tr = document.createElement('tr');
                const truncVal = String(v).length > 80 ? String(v).substring(0, 80) + '...' : String(v);
                tr.innerHTML = `
                    <td style="padding: 3px 6px; color: #60a5fa; border-bottom: 1px solid rgba(255,255,255,0.05); white-space: nowrap; vertical-align: top;">${k}</td>
                    <td style="padding: 3px 6px; color: #a5d6a7; border-bottom: 1px solid rgba(255,255,255,0.05); word-break: break-all;">${truncVal}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        // --- XPath display ---
        const xpathEl = document.getElementById('billboard-xpath');
        const patternEl = document.getElementById('billboard-pattern');
        if (xpathEl) xpathEl.textContent = details.xpath || '';
        if (patternEl) patternEl.textContent = details.generalized_xpath || details.generalizedXpath || '';

        // --- Content categories as chips ---
        const catsEl = document.getElementById('billboard-categories');
        if (catsEl) {
            const cats = details.categories || [];
            catsEl.innerHTML = cats.map(c =>
                `<span style="font-size:10px; padding:2px 6px; border-radius:10px; background:rgba(59,130,246,0.3); color:#93c5fd;">${c}</span>`
            ).join('');
        }

        // --- Node text (same content the retrieval panel shows) ---
        const textEl = document.getElementById('billboard-text');
        if (textEl) {
            const rawText = (details.text || '').trim();
            if (rawText) {
                textEl.textContent = rawText;
                textEl.style.display = '';
            } else {
                textEl.textContent = '';
                textEl.style.display = 'none';
            }
        }

        // --- Label input ---
        const labelInput = document.getElementById('billboard-label-input');
        const infoEl = document.getElementById('billboard-label-info');
        if (labelInput) {
            labelInput.value = '';
            labelInput.placeholder = details.nodeLabel || details.label
                ? `Current: "${details.nodeLabel || details.label}" (Enter new)`
                : 'Label this node (Enter)';
        }
        if (infoEl) {
            const lbl = details.nodeLabel || details.label;
            let infoHtml = lbl ? `Labeled as: <strong>${lbl}</strong>` : '';

            // Add LCA highlight button if this node has a label
            if (lbl) {
                infoHtml += ` <button id="btn-show-lca" style="font-size:9px; padding:1px 6px; margin-left:6px; background:rgba(255,215,0,0.2); border:1px solid #b8860b; color:#ffd700; border-radius:4px; cursor:pointer;" title="Highlight LCA subtree for this label group">LCA</button>`;
            }

            // Add commutation highlight button for any node with an xpath
            const xp = details.xpath || '';
            const nodeUrl = details.website || details.url || '';
            if (xp) {
                infoHtml += ` <button id="btn-show-commutation" style="font-size:9px; padding:1px 6px; margin-left:4px; background:rgba(45,212,191,0.2); border:1px solid #2dd4bf; color:#2dd4bf; border-radius:4px; cursor:pointer;" title="Highlight structurally equivalent nodes">Commute</button>`;
                infoHtml += ` <button id="btn-show-subgroup-commutation" style="font-size:9px; padding:1px 6px; margin-left:4px; background:rgba(168,85,247,0.2); border:1px solid #a855f7; color:#a855f7; border-radius:4px; cursor:pointer;" title="Commute only across labeled LCA groups sharing the same descendant pattern set">Subgroup</button>`;
            }

            // Show commutation membership indicator + clear-all toggle
            if (this._commutedIds && this._commutedIds.size > 0) {
                const isMember = this._commutedIds.has(details.id);
                infoHtml += `<div style="margin-top:4px;"><span style="color:#2dd4bf; font-size:10px;"><i class="fas fa-link"></i> ${this._commutedIds.size} commuted</span>${isMember ? ' <span style="color:#2dd4bf; font-size:9px;">(this node)</span>' : ''} <button id="btn-clear-commutation" style="font-size:9px; padding:1px 6px; margin-left:4px; background:rgba(239,68,68,0.2); border:1px solid #ef4444; color:#ef4444; border-radius:4px; cursor:pointer;" title="Clear all commutation highlights">Clear All</button></div>`;
            }

            infoEl.innerHTML = infoHtml;

            // Wire LCA button
            const lcaBtn = document.getElementById('btn-show-lca');
            if (lcaBtn && lbl && nodeUrl) {
                lcaBtn.addEventListener('click', () => {
                    this.highlightLcaSubtree(nodeUrl, lbl);
                });
            }

            // Wire commutation button
            const commuteBtn = document.getElementById('btn-show-commutation');
            if (commuteBtn && xp && nodeUrl) {
                commuteBtn.addEventListener('click', () => {
                    this.highlightCommutation(nodeUrl, xp);
                });
            }

            // Wire subgroup commutation button
            const subgroupBtn = document.getElementById('btn-show-subgroup-commutation');
            if (subgroupBtn && xp && nodeUrl) {
                subgroupBtn.addEventListener('click', () => {
                    this.highlightSubgroupCommutation(nodeUrl, xp);
                });
            }

            // Wire clear-all-commutation button
            const clearCommBtn = document.getElementById('btn-clear-commutation');
            if (clearCommBtn) {
                clearCommBtn.addEventListener('click', () => {
                    this.clearCommutation();
                    clearCommBtn.parentElement.remove();
                });
            }

        }

        // If the selected node is a card, paint the card knowledge panel
        // with the aggregated content_fields from its chunk.
        this._renderCardPanel(details);
    }

    /** Appends (or refreshes) the card-specific knowledge panel when the
     *  selected node is a chunk card. Shows color swatch, pattern, label
     *  input, text preview, and one row per content_fields category. */
    _renderCardPanel(details) {
        if (!details || !details.is_card) return;
        const host = document.getElementById('billboard-label-info');
        if (!host) return;

        const cid = details.chunk_id;
        const pat = details.chunk_pattern || '';
        const lbl = details.chunk_label || '';
        const preview = details.chunk_text_preview || '';
        const fields = details.chunk_content_fields || {};
        const swatchHex = '#' + this._chunkColor(cid).getHexString();

        const fieldRows = Object.entries(fields).map(([cat, vals]) => {
            const valsHtml = vals.slice(0, 4).map(v => {
                const t = String(v);
                const trunc = t.length > 120 ? t.slice(0, 120) + '…' : t;
                return `<div style="color:#cbd5e1; font-size:10px; margin-left:6px;">• ${trunc}</div>`;
            }).join('');
            const more = vals.length > 4 ? `<div style="color:#6b7280; font-size:9px; margin-left:6px;">+${vals.length - 4} more</div>` : '';
            return `
                <div style="margin-top:3px;">
                    <div style="color:${swatchHex}; font-size:9px; text-transform:uppercase; letter-spacing:0.5px;">${cat}</div>
                    ${valsHtml}${more}
                </div>
            `;
        }).join('');

        const cardBlock = document.createElement('div');
        cardBlock.className = 'card-panel-block';
        cardBlock.style.cssText = `margin-top:8px; padding:6px 8px; border-left:3px solid ${swatchHex}; background:rgba(255,255,255,0.03);`;
        cardBlock.innerHTML = `
            <div style="font-size:11px; color:#e5e7eb;">
                <span style="display:inline-block; width:10px; height:10px; background:${swatchHex}; border-radius:50%; margin-right:6px; vertical-align:middle;"></span>
                <strong>Card</strong>
                ${lbl ? `· <span style="color:${swatchHex};">${lbl}</span>` : ''}
            </div>
            ${pat ? `<div style="font-size:9px; color:#9ca3af; margin-top:2px;"><code>${pat}</code></div>` : ''}
            <div style="font-size:9px; color:#9ca3af; margin-top:2px;">${details.chunk_char_count || 0} chars · ${details.chunk_commutation_count || 0} commuted</div>
            ${preview ? `<div style="font-size:10px; color:#d1d5db; margin-top:4px; font-style:italic;">${preview}</div>` : ''}
            ${fieldRows ? `<div style="margin-top:6px;">${fieldRows}</div>` : ''}
            <div style="margin-top:6px;">
                <button id="btn-card-fold" style="font-size:9px; padding:1px 6px; background:rgba(96,165,250,0.2); border:1px solid #60a5fa; color:#60a5fa; border-radius:4px; cursor:pointer;">Re-fold subtree</button>
                <input id="card-label-input" type="text" placeholder="${lbl ? 'Rename label' : 'Label this card'}" style="width:60%; font-size:10px; padding:2px 4px; margin-left:4px; background:rgba(0,0,0,0.4); border:1px solid #374151; color:#e5e7eb; border-radius:3px;" />
                <button id="btn-card-save-label" style="font-size:9px; padding:1px 6px; margin-left:4px; background:rgba(59,130,246,0.2); border:1px solid #3b82f6; color:#93c5fd; border-radius:4px; cursor:pointer;">Save</button>
            </div>
        `;
        // Remove any previous card block before appending the new one
        host.querySelectorAll('.card-panel-block').forEach(el => el.remove());
        host.appendChild(cardBlock);

        const foldBtn = cardBlock.querySelector('#btn-card-fold');
        if (foldBtn) foldBtn.addEventListener('click', () => this.foldCardSubtree(details.id));

        const lblInput = cardBlock.querySelector('#card-label-input');
        const saveBtn = cardBlock.querySelector('#btn-card-save-label');
        const save = async () => {
            const v = (lblInput && lblInput.value || '').trim();
            if (!v) return;
            try {
                await this.client.setChunkLabel(cid, v, this._streamSnapshotId);
                if (this._chunksById && this._chunksById.has(cid)) {
                    this._chunksById.get(cid).label = v;
                }
                this.dataMap.forEach((n) => { if (n.chunk_id === cid) n.chunk_label = v; });
                details.chunk_label = v;
                this._renderCardPanel(details);
            } catch (e) {
                console.error('[Card] label save failed:', e);
            }
        };
        if (saveBtn) saveBtn.addEventListener('click', save);
        if (lblInput) lblInput.addEventListener('keydown', (ev) => {
            if (ev.key === 'Enter') { ev.preventDefault(); save(); }
        });
    }

    renderQuickTags(nodeId) {
        const container = document.getElementById('billboard-quick-tags');
        if (!container) return;
        
        container.innerHTML = '';
        const nodeData = this.dataMap.get(nodeId);
        if (!nodeData) return;
        
        const currentTags = new Set(nodeData.tags || []);

        this.allTags.forEach(tag => {
            const chip = document.createElement('div');
            const isAssigned = currentTags.has(tag);
            chip.className = 'filter-chip'; 
            chip.style.cssText = `
                font-size: 10px; 
                padding: 2px 6px; 
                border-radius: 10px; 
                cursor: pointer; 
                border: 1px solid #333;
                background: ${isAssigned ? 'rgba(59, 130, 246, 0.4)' : 'rgba(255,255,255,0.05)'};
                color: ${isAssigned ? '#fff' : '#9aa5b1'};
                opacity: ${isAssigned ? '0.6' : '1'};
            `;
            chip.textContent = isAssigned ? `✓ ${tag}` : `+ ${tag}`;
            if (!isAssigned) {
                chip.onclick = () => {
                    this.addTagToNode(nodeId, tag);
                };
            }
            container.appendChild(chip);
        });
    }

    showBillboard(data, isLocked) {
        const billboard = document.getElementById('billboard');
        if (!data) return;
        const nodeMesh = this.nodes.get(data.id);

        if (nodeMesh) {
            const color = nodeMesh.originalColor;
            const cssColor = `#${color.getHexString()}`;
            const textColor = this.getContrastYIQ(color);
            billboard.style.borderLeft = `4px solid ${cssColor}`;
            const header = billboard.querySelector('.billboard-header');
            if (header) {
                header.style.backgroundColor = cssColor;
                header.style.color = textColor;
                document.getElementById('billboard-title').style.color = textColor;
                document.getElementById('billboard-close').style.color = textColor;
            }
        }

        // Title = tag#id or tag.class or just tag
        const displayName = data.name || data.tag || '';
        document.getElementById('billboard-title').textContent = displayName;

        // Link to this node's own endpoint (href attribute) — NOT the base
        // page URL.  If the node carries no href, hide the Visit button.
        const linkEl = document.getElementById('billboard-link');
        if (linkEl) {
            const attrs = data.nodeAttributes || data.attributes || {};
            const nodeHref = data.href || attrs.href || attrs.src || '';
            if (nodeHref && nodeHref !== '#') {
                linkEl.href = nodeHref;
                linkEl.style.display = '';
                let label = nodeHref;
                try {
                    const u = new URL(nodeHref);
                    label = u.hostname + (u.pathname && u.pathname !== '/' ? u.pathname : '');
                } catch (e) { /* keep raw */ }
                if (label.length > 40) label = label.substring(0, 37) + '...';
                linkEl.textContent = label + ' ';
                linkEl.innerHTML += '<i class="fas fa-external-link-alt"></i>';
            } else {
                linkEl.removeAttribute('href');
                linkEl.style.display = 'none';
            }
        }

        this.renderKnowledgePanel(data);

        document.getElementById('billboard-close').onclick = () => {
            billboard.style.display = 'none';
            this.hideBillboardArrow();
            this.selectedId = null;
            this.searchResults = null;
            this.nodes.forEach((nodeObj) => {
                nodeObj.mesh.setColorAt(nodeObj.instanceId, nodeObj.originalColor);
            });
            this._flushInstanceColors();
            this.applyFilters();
        };

        billboard.style.display = 'block';
        billboard.style.transform = '';  // Reset any centering transform from non-3D results
        if (nodeMesh) {
            const group = this.snapshotGroups.get(nodeMesh.snapshotIndex);
            if (group) {
                const initData = this.initialNodeData.get(data.id);
                if (initData) {
                    const worldPos = initData.localPos.clone().applyMatrix4(group.matrixWorld);
                    this.updateBillboardPosition({ position: worldPos });
                }
            }
        }
    }

    hideBillboard() {
        document.getElementById('billboard').style.display = 'none';
        this.hideBillboardArrow();
    }

    async updateNodeStatus(id, status) {
        await this.client.updateNode(id, status);
    }

    updateBillboardPosition(mesh) {
        const billboard = document.getElementById('billboard');
        if (!mesh || !billboard) return;

        // The renderer is sized to #projector-panel, NOT the full window.
        // NDC → viewport must use the panel rect so the arrow actually
        // reaches the 3D node instead of overshooting by the sidebar width.
        const panel = document.getElementById('projector-panel');
        const panelRect = panel ? panel.getBoundingClientRect() : { left: 0, top: 0, width: window.innerWidth, height: window.innerHeight };

        const vector = mesh.position.clone();
        vector.project(this.camera);
        // Viewport-absolute coordinates of the projected 3D point
        const x = (vector.x * 0.5 + 0.5) * panelRect.width + panelRect.left;
        const y = -(vector.y * 0.5 - 0.5) * panelRect.height + panelRect.top;
        const behindCamera = vector.z > 1 || vector.z < -1;
        const rect = billboard.getBoundingClientRect();

        // Offset to the right of the node (was 20, now 110) so the
        // originating sphere stays clickable and the arrow has room to
        // actually cross open space instead of starting on top of the node.
        const NODE_CLEARANCE_PX = 110;
        if (Math.abs(this.controls.getAzimuthalAngle()) > 0 || this.controls.autoRotate || this.hoveredId || this.isDragging) {
             billboard.style.left = `${Math.min(panelRect.width - rect.width - 20, Math.max(20, x - panelRect.left + NODE_CLEARANCE_PX))}px`;
             billboard.style.top = `${Math.min(panelRect.height - rect.height - 20, Math.max(20, y - panelRect.top - rect.height/2))}px`;
        }

        // Draw an arrow from the edge of the billboard to the 3D node.
        // We intersect the billboard rect with the ray from its centre to
        // the node so the arrow-tail sits flush on the box edge that faces
        // the node — not clamped into a corner.
        const svg = document.getElementById('billboard-arrow-svg');
        const line = document.getElementById('billboard-arrow-line');
        if (svg && line) {
            const bbRect = billboard.getBoundingClientRect();

            // Panel-local coordinates for both the 3D target and the billboard
            const targetX = x - panelRect.left;
            const targetY = y - panelRect.top;
            const bbLeft = bbRect.left - panelRect.left;
            const bbTop = bbRect.top - panelRect.top;
            const bbRight = bbLeft + bbRect.width;
            const bbBottom = bbTop + bbRect.height;
            const cx = (bbLeft + bbRight) / 2;
            const cy = (bbTop + bbBottom) / 2;

            // Ray from billboard centre toward target; find first exit
            // point on the rectangle boundary (clamped to the box).
            let anchorX = cx;
            let anchorY = cy;
            const dx = targetX - cx;
            const dy = targetY - cy;
            if (dx !== 0 || dy !== 0) {
                const tX = dx > 0
                    ? (bbRight - cx) / dx
                    : dx < 0 ? (bbLeft - cx) / dx : Infinity;
                const tY = dy > 0
                    ? (bbBottom - cy) / dy
                    : dy < 0 ? (bbTop - cy) / dy : Infinity;
                const t = Math.max(0, Math.min(tX, tY));
                anchorX = cx + dx * t;
                anchorY = cy + dy * t;
            }

            const insideBillboard = targetX >= bbLeft && targetX <= bbRight &&
                                    targetY >= bbTop && targetY <= bbBottom;
            if (behindCamera || insideBillboard) {
                svg.style.display = 'none';
            } else {
                svg.style.display = '';
                line.setAttribute('x1', anchorX);
                line.setAttribute('y1', anchorY);
                line.setAttribute('x2', targetX);
                line.setAttribute('y2', targetY);
            }
        }
    }

    hideBillboardArrow() {
        const svg = document.getElementById('billboard-arrow-svg');
        if (svg) svg.style.display = 'none';
    }
}

window.addEventListener('DOMContentLoaded', () => {
    if (typeof THREE === 'undefined') {
        console.error("THREE.js not loaded!");
        alert("Critical Error: Three.js failed to load. Please check your internet connection.");
    } else {
        window.app = new CompanyProjector();
    }
});