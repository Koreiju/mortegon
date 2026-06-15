console.log("[Projector] Script loaded");

class CompanyProjector {
    constructor() {
        console.log("[Projector] Constructor called");
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
        
        canvas.addEventListener('mousedown', (e) => {
            this.isDragging = false;
            this.mouseDownPos.x = e.clientX;
            this.mouseDownPos.y = e.clientY;
        }, { capture: true });

        canvas.addEventListener('mousemove', (e) => {
            if (e.buttons === 1) { 
                const dx = Math.abs(e.clientX - this.mouseDownPos.x);
                const dy = Math.abs(e.clientY - this.mouseDownPos.y);
                if (dx > 5 || dy > 5) {
                    this.isDragging = true;
                }
            }
            this.onMouseMove(e);
        });

        canvas.addEventListener('click', (e) => this.onClick(e));
        
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
                    const res = await fetch('/api/snapshot');
                    const text = await res.text();
                    console.log(`[Projector] Snapshot API responded with text payload: ${text.substring(0, 500)}`);
                    
                    if (!res.ok) {
                        statusLog.innerText = `[ERROR] HTTP ${res.status}: ${text}`;
                        statusLog.style.color = "red";
                        throw new Error(`Snapshot Failed HTTP ${res.status}`);
                    }
                    
                    statusLog.innerText = "Snapshot sequence started! Polling recursively natively...";
                    
                    let sweeps = 0;
                    const pollInterval = setInterval(async () => {
                        sweeps++;
                        await this.loadCompanies(); // Reload map natively!
                        
                        if (sweeps >= 6) { 
                            clearInterval(pollInterval);
                            snapshotBtn.innerHTML = '<i class="fas fa-camera"></i> Snapshot Live Browser';
                            snapshotBtn.disabled = false;
                            setTimeout(() => { if(statusLog) statusLog.remove(); }, 2000);
                        }
                    }, 3000);
                    
                } catch (e) {
                    console.error("[Projector] Fatal error during snapshot:", e);
                    statusLog.innerText = "[CRITICAL] " + e.message;
                    statusLog.style.color = "red";
                    alert("Failed to snapshot the DOM: " + e.message);
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

    
    async loadCompanies() {
        console.log("[Projector] loadCompanies() called");
        try {
            const res = await fetch('/api/nodes?t=' + Date.now(), { cache: 'no-store' });
            const rawBody = await res.text();
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            
            const data = JSON.parse(rawBody);
            this.links = data.links || [];
            
            // Clean up existing meshes
            if (this.snapshotGroups) {
                this.snapshotGroups.forEach(group => this.scene.remove(group));
            }
            if (this.seqLineMeshes) {
                this.seqLineMeshes.forEach(mesh => this.scene.remove(mesh.mesh));
            }
            
            this.snapshotGroups = new Map();
            this.seqLineMeshes = [];
            this.nodes.clear();
            this.dataMap.clear();
            this.initialNodeData.clear();
            this.allTags.clear();
            
            this.maxSnapshotIndex = 0;
            if (data.nodes && data.nodes.length > 0) {
                this.maxSnapshotIndex = Math.max(...data.nodes.map(n => Math.round(n.x / 500.0)));
            }

            this.snapshotHistory = new Map(); 
            
            if (!data.nodes) return;
            
            const nodesBySnapshot = new Map();
            data.nodes.forEach(node => {
                const sIdx = Math.round(node.x / 500.0);
                if (!nodesBySnapshot.has(sIdx)) nodesBySnapshot.set(sIdx, []);
                nodesBySnapshot.get(sIdx).push(node);
                
                if (!this.snapshotHistory.has(sIdx)) {
                    this.snapshotHistory.set(sIdx, { index: sIdx, url: node.url || 'Unknown', nodeCount: 0 });
                }
                this.snapshotHistory.get(sIdx).nodeCount++;
                this.dataMap.set(node.id, node);
                if (node.tags) node.tags.forEach(t => this.allTags.add(t));
                
                let umapColor = new THREE.Vector3(0.2, 0.5, 1.0);
                if (node.r !== undefined) umapColor = new THREE.Vector3(node.r, node.g, node.b);
                this.initialNodeData.set(node.id, {
                    localPos: new THREE.Vector3(node.x - (sIdx * 500.0), node.y, node.z),
                    translation: new THREE.Vector3((sIdx - this.maxSnapshotIndex) * 500.0, 0, 0),
                    umapColor: umapColor,
                    snapshotIndex: sIdx
                });
            });

            const sphereGeom = new THREE.SphereGeometry(0.6, 16, 16);
            const box = new THREE.Box3();

            nodesBySnapshot.forEach((nodesList, sIdx) => {
                const group = new THREE.Group();
                const totalNodes = nodesList.length;
                
                const material = new THREE.MeshPhongMaterial({
                    emissive: 0x000000, 
                    emissiveIntensity: 0,
                    shininess: 30,
                    transparent: true,
                    opacity: 1
                });
                const instMesh = new THREE.InstancedMesh(sphereGeom, material, totalNodes);
                
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
                        id: node.id,
                        snapshotIndex: sIdx,
                        instanceId: instId,
                        mesh: instMesh,
                        originalColor: activeColor.clone()
                    });
                    
                    const finalPos = new THREE.Vector3().addVectors(initData.localPos, initData.translation);
                    box.expandByPoint(finalPos);
                });
                
                instMesh.instanceMatrix.needsUpdate = true;
                if (instMesh.instanceColor) instMesh.instanceColor.needsUpdate = true;
                
                group.add(instMesh);
                group.position.x = (sIdx - this.maxSnapshotIndex) * 500.0;
                group.userData = { snapshotIndex: sIdx, nodesMesh: instMesh };
                
                this.scene.add(group);
                this.snapshotGroups.set(sIdx, group);
            });

            this.renderTagFilters();
            
            if (!box.isEmpty() && this.controls) {
                this.controls.target.set(0, 0, 0);
                this.camera.position.set(0, 5, 20);
                this.controls.update();
            }
            
            this.applyFilters();
            this.createLines();
            this.renderHistorySidebar();

        } catch (e) {
            console.error("Failed to load nodes", e);
        }
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
            // Extract a nice clean baseline domain
            let displayUrl = snap.url;
            try {
                displayUrl = new URL(snap.url).hostname;
            } catch(e) {}
            
            item.className = 'history-item';
            item.style.cssText = `
                padding: 12px; 
                background: rgba(255,255,255,0.05); 
                border-radius: 8px; 
                border-left: 3px solid ${isNewest ? '#3b82f6' : '#4b5563'};
                display: flex;
                align-items: center;
                gap: 10px;
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
            
            container.appendChild(item);
        });

        
        document.querySelectorAll('.history-toggle').forEach(cb => {
            cb.addEventListener('change', (e) => {
                const idx = parseInt(e.target.dataset.idx);
                const isVisible = e.target.checked;
                const group = this.snapshotGroups.get(idx);
                if (group) group.visible = isVisible;
                if (this.seqLineMeshes) {
                    this.seqLineMeshes.forEach(line => {
                        if (line.snapshotIndex === idx) line.mesh.visible = isVisible;
                    });
                }
            });
        });
    }

    // --- Interaction ---

    getIntersects(event) {
        if (!this.renderer || !this.camera) return [];
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        this.raycaster.setFromCamera(this.mouse, this.camera);
        
        const visibleNodes = Array.from(this.nodes.values()).filter(n => n.visible);
        return this.raycaster.intersectObjects(visibleNodes);
    }

    onMouseMove(event) {
        const intersects = this.getIntersects(event);

        if (intersects.length > 0) {
            const object = intersects[0].object;
            const id = object.userData.id;

            if (this.hoveredId !== id) {
                if (this.hoveredId && this.hoveredId !== this.selectedId) {
                    const prevMesh = this.nodes.get(this.hoveredId);
                    if (prevMesh) this.restoreNodeVisuals(prevMesh);
                }

                this.hoveredId = id;
                document.body.style.cursor = 'pointer';

                if (id !== this.selectedId) {
                    object.material.emissive.setHex(0x333333); 
                    object.material.emissiveIntensity = 0.5;
                    object.scale.setScalar(1.5);
                }

                if (!this.selectedId) {
                    this.showBillboard(this.dataMap.get(id), false);
                }
            }
        } else {
            if (this.hoveredId) {
                if (this.hoveredId !== this.selectedId) {
                    const prevMesh = this.nodes.get(this.hoveredId);
                    if (prevMesh) this.restoreNodeVisuals(prevMesh);
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
        if (intersects.length > 0) {
            const mesh = intersects[0].object;
            await this.selectNode(mesh.userData.id);
        } else {
            this.selectedId = null;
            this.searchResults = null; 
            this.hideBillboard();
            
            this.nodes.forEach(mesh => {
                mesh.material.color.copy(mesh.userData.originalColor);
                mesh.material.emissive.setHex(0x000000);
                mesh.material.emissiveIntensity = 0;
                mesh.scale.setScalar(1);
            });

            this.applyFilters(); 
        }
    }

    restoreNodeVisuals(mesh) {
        const id = mesh.userData.id;
        
        if (this.searchResults && this.searchResults.has(id)) {
            const score = this.searchResults.get(id);
            this.applySearchGlow(mesh, score);
        } else {
            mesh.material.color.copy(mesh.userData.originalColor);
            mesh.material.emissive.setHex(0x000000);
            mesh.material.emissiveIntensity = 0;
            
            const data = this.dataMap.get(id);
            const isMatch = this.checkFilterMatch(data);
            mesh.material.opacity = isMatch ? 1 : 0.1;
            mesh.scale.setScalar(1);
        }
    }

    async selectNode(id) {
        if (this.selectedId && this.selectedId !== id) {
            const prevMesh = this.nodes.get(this.selectedId);
            if (prevMesh) this.restoreNodeVisuals(prevMesh);
        }

        this.selectedId = id;
        
        const mesh = this.nodes.get(id);
        if(mesh) { mesh.mesh.setColorAt(mesh.instanceId, new THREE.Color(0xffff00)); mesh.mesh.instanceColor.needsUpdate = true; }

        try {
            const res = await fetch(`/api/details/${encodeURIComponent(id)}`);
            const details = await res.json();
            this.showBillboard(details, true);
            // this.triggerRetrieval({ target_id: id }, details); 
        } catch (e) {
            console.error(e);
        }
    }

    update3DVisualsFromResults(results) {
        if (this.searchResults) {
            this.nodes.forEach(mesh => {
                if (mesh.userData.id !== this.selectedId) {
                    mesh.material.color.copy(mesh.userData.originalColor);
                    mesh.material.emissive.setHex(0x000000);
                    mesh.material.emissiveIntensity = 0;
                    mesh.scale.setScalar(1);
                    const data = this.dataMap.get(mesh.userData.id);
                    const isMatch = this.checkFilterMatch(data);
                    mesh.material.opacity = isMatch ? 1 : 0.1;
                }
            });
        }

        this.searchResults = new Map(); 

        results.forEach(res => {
            this.searchResults.set(res.id, res.score);
            const mesh = this.nodes.get(res.id);
            if (mesh && res.id !== this.selectedId) {
                this.applySearchGlow(mesh, res.score);
            }
        });
    }

    applySearchGlow(mesh, score) {
        mesh.material.emissive.copy(mesh.userData.originalColor);
        const safeScore = Math.max(0, Math.min(1, score));
        mesh.material.emissiveIntensity = 0.3 + (safeScore * 1.5);
        mesh.material.opacity = 1; 
        mesh.scale.setScalar(1 + (safeScore * 0.5)); 
    }

    // --- Animation & Physics ---

    
    animate() {
        requestAnimationFrame(() => this.animate());

        const delta = this.clock.getDelta();
        if (this.controls) this.controls.update();

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
        }
    }



    // --- Rest of standard methods ---

    initSidebar() {
        document.querySelectorAll('.filter-cb').forEach(cb => {
            cb.addEventListener('change', () => {
                this.applyFilters();
                if (this.lastResults) this.renderResults(this.lastResults);
            });
        });

        const searchInput = document.getElementById('nl-search');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.triggerRetrieval({ query: searchInput.value });
                }
            });
        }
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
        const statusFilters = Array.from(document.querySelectorAll('.filter-cb:checked')).map(cb => cb.value);
        const dummy = new THREE.Object3D();
        
        this.nodes.forEach((nodeObj, id) => {
            const data = this.dataMap.get(id);
            const isMatch = this.checkFilterMatch(data, statusFilters);
            const isSearchResult = this.searchResults && this.searchResults.has(id);
            
            const visible = (isMatch || isSearchResult);
            const initData = this.initialNodeData.get(id);
            
            dummy.position.copy(initData.localPos);
            if (!visible) dummy.scale.set(0, 0, 0);
            else dummy.scale.set(1, 1, 1);
            
            dummy.updateMatrix();
            nodeObj.mesh.setMatrixAt(nodeObj.instanceId, dummy.matrix);
        });
        
        if(this.snapshotGroups) {
            Array.from(this.snapshotGroups.values()).forEach(g => {
                if (g.userData.nodesMesh) g.userData.nodesMesh.instanceMatrix.needsUpdate = true;
            });
        }
    }



    checkFilterMatch(data, statusFilters = null) {
        if (!statusFilters) {
            statusFilters = Array.from(document.querySelectorAll('.filter-cb:checked')).map(cb => cb.value);
        }
        const statusMatch = statusFilters.includes(data.status);
        let tagMatch = true;
        if (this.activeTags.size > 0) {
            const nodeTags = new Set(data.tags || []);
            tagMatch = [...this.activeTags].some(t => nodeTags.has(t));
        }
        return statusMatch && tagMatch;
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
                const color = mesh.userData.originalColor;
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
                await fetch('/api/update', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ id: nodeId, tags: nodeData.tags })
                });
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

        await fetch('/api/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ id: nodeId, tags: nodeData.tags })
        });

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
        const nodeMesh = this.nodes.get(data.id);
        
        if (nodeMesh) {
            const color = nodeMesh.userData.originalColor;
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

        document.getElementById('billboard-title').textContent = data.name;
        document.getElementById('billboard-desc').textContent = data.description;
        document.querySelector('#billboard-location span').textContent = data.location;
        document.getElementById('billboard-link').href = data.website;

        const tagsList = document.getElementById('billboard-tags-list');
        tagsList.innerHTML = '';
        if (data.tags) {
            data.tags.forEach(tag => this.addTagToUi(tagsList, tag, data.id));
        }
        
        this.renderQuickTags(data.id);

        const btnYes = document.getElementById('btn-yes');
        const btnNo = document.getElementById('btn-no');
        
        btnYes.className = 'status-btn ' + (data.status === 'yes' ? 'active' : '');
        btnNo.className = 'status-btn ' + (data.status === 'no' ? 'active' : '');

        const handleStatus = (status) => {
            const newStatus = (data.status === status) ? 'unreviewed' : status;
            this.updateNodeStatus(data.id, newStatus);
            data.status = newStatus;
            
            const nodeData = this.dataMap.get(data.id);
            if(nodeData) nodeData.status = newStatus;
            
            const mesh = this.nodes.get(data.id);
            if (mesh) {
                let baseColor;
                if (newStatus === 'yes') {
                    baseColor = new THREE.Color(this.STATUS_COLORS.yes);
                } else if (newStatus === 'no') {
                    baseColor = new THREE.Color(this.STATUS_COLORS.no);
                } else {
                    const init = this.initialNodeData.get(data.id);
                    if (init && init.umapColor) {
                        baseColor = new THREE.Color(init.umapColor.x, init.umapColor.y, init.umapColor.z);
                    } else {
                        baseColor = new THREE.Color(0x3b82f6);
                    }
                }
                mesh.userData.originalColor = baseColor;
                mesh.material.color.copy(baseColor);
                
                const cssColor = `#${baseColor.getHexString()}`;
                const textColor = this.getContrastYIQ(baseColor);
                billboard.style.borderLeft = `4px solid ${cssColor}`;
                const header = billboard.querySelector('.billboard-header');
                if (header) {
                    header.style.backgroundColor = cssColor;
                    header.style.color = textColor;
                    document.getElementById('billboard-title').style.color = textColor;
                    document.getElementById('billboard-close').style.color = textColor;
                }
            }

            btnYes.className = 'status-btn ' + (newStatus === 'yes' ? 'active' : '');
            btnNo.className = 'status-btn ' + (newStatus === 'no' ? 'active' : '');
            this.applyFilters();
        };

        btnYes.onclick = () => handleStatus('yes');
        btnNo.onclick = () => handleStatus('no');
        document.getElementById('billboard-close').onclick = () => {
            billboard.style.display = 'none';
            this.selectedId = null;
            this.searchResults = null;
            this.nodes.forEach(mesh => {
                mesh.material.color.copy(mesh.userData.originalColor);
                mesh.material.emissive.setHex(0x000000);
                mesh.material.emissiveIntensity = 0;
                mesh.scale.setScalar(1);
            });
            this.applyFilters();
        };

        billboard.style.display = 'block';
        if (nodeMesh) this.updateBillboardPosition(nodeMesh);
    }

    hideBillboard() {
        document.getElementById('billboard').style.display = 'none';
    }

    async updateNodeStatus(id, status) {
        await fetch('/api/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id, status})
        });
    }

    updateBillboardPosition(mesh) {
        const billboard = document.getElementById('billboard');
        if (!mesh || !billboard) return;
        
        const vector = mesh.position.clone();
        vector.project(this.camera);
        const x = (vector.x * 0.5 + 0.5) * window.innerWidth;
        const y = -(vector.y * 0.5 - 0.5) * window.innerHeight;
        const rect = billboard.getBoundingClientRect();
        
        if (Math.abs(this.controls.getAzimuthalAngle()) > 0 || this.controls.autoRotate || this.hoveredId || this.isDragging) {
             billboard.style.left = `${Math.min(window.innerWidth - rect.width - 20, Math.max(20, x + 20))}px`;
             billboard.style.top = `${Math.min(window.innerHeight - rect.height - 20, Math.max(20, y - rect.height/2))}px`;
        }
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