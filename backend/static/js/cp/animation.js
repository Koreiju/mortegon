/**
 * cp/animation.js — The core requestAnimationFrame loop: latch tracking,
 * collapse/expand lerp, frustum culling, camera-azimuth content-HSV hue
 * rotation (§6.1/§707, via cp/hsv_color.js), sprite positioning, edge
 * updates, extra-sprite connectors, and render call.
 *
 * Methods become ChunkProjector instance methods via prototype mixin.
 * THREE is a CDN global.
 */

export const AnimationMixin = {

    initScene() {
        const container = document.getElementById('projector-panel');
        const canvas    = document.getElementById('projector-canvas');
        if (!container || !canvas) { console.error('[ChunkProjector] Missing DOM targets'); return; }

        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(0x0f1115, 0.002);

        this.camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 2000);
        // Default camera framing matched to the current cluster scale.
        // The doc-shell radius is now 12 (was 40) with chunks sitting
        // on a ~1.8-unit local shell, so the entire cluster fits in
        // roughly a 28-unit-diameter sphere around the origin. At
        // FOV 60° the camera needs to sit about 28/(2·tan 30°) ≈ 24
        // units away to fit it; (0, 8, 35) gives a slight 3/4 elevation
        // and ~36-unit camera-to-origin distance — enough headroom
        // for the cluster to grow during a scan while still rendering
        // each sphere at readable on-screen pixel size.
        this.camera.position.set(0, 8, 35);
        this.scene.add(this.camera);

        this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
        // CRITICAL — pass `updateStyle = false` so we do NOT write
        // inline `style.width`/`style.height` pixel values onto the
        // canvas element. Those inline styles would beat the
        // stylesheet rule `#projector-canvas { width:100%; height:100%; }`
        // and lock the canvas at its initial pixel size; on a
        // subsequent window-resize the CSS would still say 100% but
        // the inline override would keep the canvas at the original
        // pixel size, making the 3D scene look "stuck" while the 2D
        // overlay continued to reflow. With updateStyle=false the
        // CSS `100%` rule is the sole authority on display size,
        // while setSize controls ONLY the framebuffer.
        this.renderer.setSize(container.clientWidth, container.clientHeight, /*updateStyle=*/false);
        // Defensive: if any earlier code path wrote inline px
        // dimensions onto the canvas, blow them away so CSS wins.
        canvas.style.width  = '';
        canvas.style.height = '';
        this.renderer.setPixelRatio(window.devicePixelRatio);

        this.scene.add(new THREE.AmbientLight(0xffffff, 0.7));
        const dir = new THREE.DirectionalLight(0xffffff, 0.8);
        dir.position.set(10, 20, 10);
        this.scene.add(dir);

        if (typeof THREE.OrbitControls === 'function') {
            this.controls = new THREE.OrbitControls(this.camera, canvas);
            this.controls.enableDamping  = true;
            this.controls.dampingFactor  = 0.05;
            // Zoom guard rails. Without these the user can dolly
            // straight into the cluster (camera ends up INSIDE a
            // sphere, raycasting hits nothing useful and the scene
            // looks like a tunnel of black) or pull infinitely far
            // away. The min keeps the camera outside the smallest
            // sphere we'd ever render; the max is updated each frame
            // from the actual bounding radius of the layout so the
            // user can never zoom past the outermost node.
            this.controls.minDistance = 6;
            this.controls.maxDistance = 200;  // soft default; tightened per-frame below
            this.controls.addEventListener('start', () => {
                this._userHasInteracted = true;
            });
        } else {
            console.error('[ChunkProjector] THREE.OrbitControls missing');
        }

        this._createInstancedMeshes(10_000);

        // Resize wiring:
        //   • `window.resize` catches the browser window itself being
        //     resized (the user's primary complaint).
        //   • `ResizeObserver` on #projector-panel catches everything
        //     else that can change the canvas size — sidebar collapses,
        //     CSS reflows, DevTools docking changes. Without this, the
        //     canvas keeps its initial pixel buffer when neighbouring
        //     panels expand/collapse and the aspect drifts.
        //   • A trailing rAF coalesces back-to-back events so we don't
        //     re-allocate the renderer's framebuffer 60 times during a
        //     resize-drag.
        window.addEventListener('resize', () => {
            this._scheduleResize();
            // Direct background-plane rescale, in case the main resize
            // path's no-change guard short-circuits on a viewport
            // change that didn't move #projector-panel.
            this._forceBackgroundRescale();
        });
        try {
            const ro = new ResizeObserver(() => this._scheduleResize());
            ro.observe(container);
            this._resizeObserver = ro;
        } catch (_) { /* old browsers — window.resize is the fallback */ }

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

        window.addEventListener('mouseup', () => { setTimeout(() => { this.isDragging = false; }, 0); });

        canvas.addEventListener('mouseleave', () => {
            if (this.hoveredId) {
                if (this.hoveredId !== this.selectedId) this.restoreNodeVisuals(this.hoveredId);
                if (!this.selectedId) this.hideBillboard();
                this.hoveredId = null;
                document.body.style.cursor = 'default';
            }
        });

        canvas.addEventListener('click', (e) => this.onClick(e));

        // §6.6.5/§7.3.5 (Q.3-Q.5) — right-click a node in the 3D projector
        // to toggle its rank-dominance collapse/isolate. Fires the same
        // gesture a REPL `ui-dominance-collapse` does, so GUI→REPL mirrors.
        canvas.addEventListener('contextmenu', (e) => {
            if (typeof this.onContextMenu === 'function') this.onContextMenu(e);
        });

        this.initBackground();
        this.animate();
    },

    initBackground() {
        // Black core (design): the 3D scene sits on PURE BLACK — chunk spheres
        // (HSV) and billboards are the only saturated pixels. The full-bleed
        // waterfall video backdrop is removed per the black/silver design
        // (FRONTEND_REDESIGN / theme.md). backgroundMesh stays undefined; the
        // updateBackgroundScale / _forceBackgroundRescale guards no-op on it.
        this.scene.background = new THREE.Color(0x000000);
    },

    updateBackgroundScale() {
        if (!this.camera || !this.backgroundMesh) return;
        // The plane sits at z = -backgroundDistance in CAMERA space and
        // its scale must fill the frustum at that depth so the
        // waterfall video looks like a full-bleed backdrop. Plane
        // height at depth D is `2·D·tan(fov/2)`; plane width is
        // `h·aspect`. Pulling aspect from the camera here means a
        // single source-of-truth — the camera's current aspect — drives
        // both the projection and the background scale together, so a
        // viewport-change can never desynchronise them.
        const vFOV = (THREE.MathUtils || THREE.Math).degToRad(this.camera.fov);
        const h    = 2 * Math.tan(vFOV / 2) * this.backgroundDistance;
        const w    = h * this.camera.aspect;
        this.backgroundMesh.scale.set(w, h, 1);
    },

    /**
     * Belt-and-suspenders: the rAF-coalesced onResize already calls
     * updateBackgroundScale, but if the no-change guard in there
     * happens to short-circuit on a window resize that didn't change
     * the projector-panel's clientWidth/clientHeight (e.g. only the
     * vertical browser chrome height changed), the background plane
     * never refreshes. A direct window-resize listener that re-pulls
     * camera.aspect from clientWidth/clientHeight and rescales the
     * plane guarantees we don't miss a viewport change.
     */
    _forceBackgroundRescale() {
        const container = document.getElementById('projector-panel');
        if (!container || !this.camera) return;
        const w = container.clientWidth;
        const h = container.clientHeight;
        if (w < 2 || h < 2) return;
        // Only touch aspect if it actually drifted from the rendered
        // viewport's aspect — keeps onResize as the canonical source.
        const aspect = w / h;
        if (Math.abs(this.camera.aspect - aspect) > 0.001) {
            this.camera.aspect = aspect;
            this.camera.updateProjectionMatrix();
        }
        this.updateBackgroundScale();
    },

    /**
     * Fly the orbit camera so it frames the given node at a comfortable
     * distance. Used by the search panel: clicking a result tweens the
     * camera to the matching sphere instead of teleporting.
     *
     * The tween is cubic-eased over ~0.6 s and runs inside the rAF loop
     * (see _stepCameraTween, called from animate()). It cancels any
     * prior tween cleanly and respects OrbitControls.target so the
     * user can orbit around the focused node after arrival.
     */
    flyToNode(id, opts) {
        if (!this.camera || !this.controls) return false;
        // Use the canonical, un-collapsed init.position when we know
        // it — that's where the chunk lives in the layout regardless
        // of its current collapse animation. Otherwise fall back to
        // the mesh's current rendered position. This is what lets a
        // search-result click fly to a chunk that's currently folded
        // into its hub (the search.js click handler simultaneously
        // pops the chunk via chunkCollapseTarget so by the time the
        // camera arrives, the sphere has eased out of the hub and is
        // sitting exactly where we land).
        const init = this.initialNodeData && this.initialNodeData.get(id);
        let target;
        if (init && init.position) {
            target = init.position.clone();
            // Apply the active snow-globe rotation so the camera
            // lands on the chunk's RENDERED position. Rotation
            // pauses on interaction (selectedId/pinnedPanels are
            // set right before flyToNode in the click handler), so
            // this matrix is effectively frozen for the duration of
            // the tween.
            const t = this.animationTime;
            const m = new THREE.Matrix4();
            m.makeRotationFromEuler(new THREE.Euler(
                t * this.spatialVelocity.x,
                t * this.spatialVelocity.y,
                t * this.spatialVelocity.z,
            ));
            target.applyMatrix4(m);
        } else if (typeof this._getNodePosition === 'function') {
            target = this._getNodePosition(id);
        }
        if (!target) return false;

        const cfg = opts || {};
        // Pick a viewing distance that's a function of the bounding sphere
        // around all currently visible nodes — large enough to frame the
        // node without losing context. Falls back to a fixed 12 units.
        let viewDist = cfg.distance;
        if (!viewDist) {
            const entry = this.nodeInstanceMap.get(id);
            const base  = entry && entry.isDoc ? 22 : 12;
            viewDist    = base;
        }

        // Preserve the user's current viewing direction: keep the unit
        // vector from camera→target the same, just rescale to viewDist.
        const curTarget = this.controls.target.clone();
        const curCam    = this.camera.position.clone();
        const dir       = curCam.sub(curTarget);
        if (dir.lengthSq() < 1e-6) dir.set(0, 0.4, 1);  // safe fallback
        dir.normalize().multiplyScalar(viewDist);

        const camEnd    = target.clone().add(dir);
        const tgtEnd    = target.clone();

        this._cameraTween = {
            t: 0, dur: Math.max(0.15, cfg.duration || 0.6),
            camStart: this.camera.position.clone(),
            tgtStart: this.controls.target.clone(),
            camEnd, tgtEnd,
        };
        return true;
    },

    /**
     * Frame the camera so all currently-allocated instances fit inside the
     * viewport. Computes the AABB of every non-zero matrix row in both
     * the doc and instance InstancedMesh pools (cheap — one pass over
     * 16-floats-per-row), derives a bounding-sphere radius from the
     * diagonal, then sets up a flyToNode-style tween to a viewing
     * distance that frames the sphere at the current FOV.
     */
    frameAllInstances(opts) {
        if (!this.camera || !this.controls) return false;
        const meshes = [this.docInstancedMesh, this.instInstancedMesh].filter(Boolean);
        if (!meshes.length) return false;
        let minX=Infinity, minY=Infinity, minZ=Infinity;
        let maxX=-Infinity, maxY=-Infinity, maxZ=-Infinity;
        let count = 0;
        for (const mesh of meshes) {
            const arr = mesh.instanceMatrix && mesh.instanceMatrix.array;
            if (!arr) continue;
            for (let i = 0; i < mesh.count; i++) {
                const o = i * 16;
                const x = arr[o + 12], y = arr[o + 13], z = arr[o + 14];
                if (Math.abs(x) + Math.abs(y) + Math.abs(z) < 0.001) continue;
                if (x < minX) minX = x; if (x > maxX) maxX = x;
                if (y < minY) minY = y; if (y > maxY) maxY = y;
                if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;
                count++;
            }
        }
        if (!count) return false;
        const cx = (minX + maxX) * 0.5;
        const cy = (minY + maxY) * 0.5;
        const cz = (minZ + maxZ) * 0.5;
        // Half-diagonal as a generous bounding-sphere radius.
        const radius = 0.5 * Math.hypot(maxX - minX, maxY - minY, maxZ - minZ);
        const vFov = (THREE.MathUtils || THREE.Math).degToRad(this.camera.fov);
        const dist = Math.max(20, (radius / Math.tan(vFov / 2)) * 1.4);

        // Reuse the existing camera tween machinery for a smooth move.
        const cfg = opts || {};
        const curTarget = this.controls.target.clone();
        const curCam    = this.camera.position.clone();
        const dir       = curCam.sub(curTarget);
        if (dir.lengthSq() < 1e-6) dir.set(0.2, 0.4, 1);
        dir.normalize().multiplyScalar(dist);
        const camEnd = new THREE.Vector3(cx + dir.x, cy + dir.y, cz + dir.z);
        const tgtEnd = new THREE.Vector3(cx, cy, cz);
        this._cameraTween = {
            t: 0, dur: Math.max(0.15, cfg.duration || 0.7),
            camStart: this.camera.position.clone(),
            tgtStart: this.controls.target.clone(),
            camEnd, tgtEnd,
        };
        return true;
    },

    _stepCameraTween(delta) {
        const tw = this._cameraTween;
        tw.t += delta;
        const u = Math.min(1, tw.t / tw.dur);
        // Cubic ease-in-out for a smooth landing without overshoot.
        const e = u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
        this.camera.position.lerpVectors(tw.camStart, tw.camEnd, e);
        this.controls.target.lerpVectors(tw.tgtStart, tw.tgtEnd, e);
        if (typeof this.controls.update === 'function') this.controls.update();
        if (u >= 1) this._cameraTween = null;
    },

    /**
     * Coalesce resize events through a single rAF so a drag-resize
     * triggers one renderer reconfigure per frame instead of one per
     * pixel.  ``onResize`` itself is cheap, but ``renderer.setSize``
     * reallocates the framebuffer — calling it 60×/sec during a drag
     * tanks frame rate on low-end GPUs.
     */
    _scheduleResize() {
        if (this._resizeRaf) return;
        this._resizeRaf = requestAnimationFrame(() => {
            this._resizeRaf = 0;
            this.onResize();
        });
    },

    onResize() {
        const container = document.getElementById('projector-panel');
        if (!(this.camera && this.renderer && container)) return;
        const w = container.clientWidth;
        const h = container.clientHeight;
        // Guard against transient 0-dim states (e.g. a parent flex
        // container in the middle of a layout). A 0 width yields
        // aspect = 0/h = 0 → singular projection matrix → black scene.
        if (w < 2 || h < 2) return;
        // NOTE: previously we had an `if (lastW === w && lastH === h)
        // return` guard here, intended to break a ResizeObserver
        // feedback loop. The loop was actually caused by
        // setSize(updateStyle=true) writing CSS pixel values back onto
        // the canvas — switching to updateStyle=false (below) breaks
        // the loop at the source. The guard then started biting on
        // subpixel HiDPI dimensions and silently locked the 3D
        // viewport at its first-rendered size while the 2D overlay
        // kept resizing with the window. No guard now: every resize
        // event re-runs the camera + framebuffer update.
        const dpr = window.devicePixelRatio || 1;
        if (this.renderer.getPixelRatio() !== dpr) this.renderer.setPixelRatio(dpr);
        this.camera.aspect = w / h;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(w, h, /*updateStyle=*/false);
        this.updateBackgroundScale();
        // 2D overlay: re-anchor the floating billboard to its node's
        // freshly-projected screen position. Without this, the panel
        // visibly lags by one rAF after a resize and feels disconnected
        // from the sphere it describes. Wrapped in try/catch so a bad
        // projection (e.g. selectedId pointing at a recycled instance)
        // can't break the resize chain and leave the canvas stuck.
        try {
            const targetId = this.selectedId || this.hoveredId;
            if (targetId && typeof this._getNodePosition === 'function') {
                const pos = this._getNodePosition(targetId);
                if (pos && typeof this.updateBillboardPosition === 'function') {
                    this.updateBillboardPosition({ position: pos });
                }
            }
        } catch (e) {
            console.warn('[onResize] billboard reposition skipped:', e && e.message);
        }
    },

    animate() {
        requestAnimationFrame(() => this.animate());

        // Belt-and-suspenders adaptive resize (Mortegon §3.3): the
        // canonical resize path is the ResizeObserver on
        // #projector-panel + the window.resize listener, but if
        // either fails to fire (browser quirks, tab background
        // throttling) the renderer's framebuffer can drift away from
        // the container's actual pixel dimensions and the scene
        // looks stretched. Compare buffer to container every frame
        // and self-heal — this is cheap (two integer reads + at most
        // one branch) and guarantees the 3D canvas tracks the 2D
        // overlay's reflow.
        try {
            const c = document.getElementById('projector-canvas');
            const panel = document.getElementById('projector-panel');
            if (c && panel && this.renderer && this.camera) {
                const wantW = panel.clientWidth | 0;
                const wantH = panel.clientHeight | 0;
                if (wantW > 1 && wantH > 1 &&
                    (c.width !== wantW * (this.renderer.getPixelRatio ? this.renderer.getPixelRatio() : 1) ||
                     c.height !== wantH * (this.renderer.getPixelRatio ? this.renderer.getPixelRatio() : 1))) {
                    this.onResize();
                }
            }
        } catch (_) { /* never let resize self-heal abort the animate loop */ }

        // Latch tracking — both latches follow their panel's right/left edge at 60 fps.
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
                const rect          = panel.getBoundingClientRect();
                const viewportWidth = document.documentElement.clientWidth || window.innerWidth;
                rsLatch.style.setProperty('transform', `translate(-${viewportWidth - rect.left}px, -50%)`, 'important');
            }
        }

        const delta = Math.min(this.clock.getDelta(), 0.1);
        // Auto-rotation pauses while ANY user interaction is in progress:
        //   - dragging the orbit camera,
        //   - hovering or selecting a node,
        //   - hovering an unpinned panel,
        //   - AT LEAST ONE pinned knowledge panel is open. Previously the
        //     rotation resumed as soon as the panel went "engaged" (user
        //     clicked into the body), which moved the underlying node out
        //     from under the panel's tether arrow. The user explicitly
        //     wants the world frozen while any panel is pinned, so the
        //     panels stay anchored to their nodes.
        const hasPinned = this._pinnedPanels && this._pinnedPanels.size > 0;
        const isInteracting = this.isDragging || this.hoveredId || this.selectedId
                              || this._panelHoverCount > 0 || hasPinned;
        if (!isInteracting) this.animationTime += delta;
        // Per-frame camera tween (driven by flyToNode). Runs independently
        // of the rotation pause so the user always gets the fly-to motion.
        if (this._cameraTween) this._stepCameraTween(delta);
        const t = this.animationTime;

        const spatialMatrix = new THREE.Matrix4();
        spatialMatrix.makeRotationFromEuler(new THREE.Euler(
            t * this.spatialVelocity.x, t * this.spatialVelocity.y, t * this.spatialVelocity.z
        ));
        // §6.1/§707 — camera-azimuth hue phase. Chunk colours are the UMAP
        // CONTENT-HSV (init.umapHsl, coords[3:6]); their hue rotates in lockstep
        // with the projector orbit so a chunk's visual identity persists across
        // observation angle. The "effective observation azimuth" combines BOTH
        // rotations the user actually sees: the OrbitControls camera azimuth
        // (changes on drag) AND the world auto-spin angle (t · spatialVelocity.y,
        // a full 2π in ~62.8 s ≈ the design's default 60 s period; frozen while
        // a panel is pinned since `t` freezes). One full revolution = one hue
        // cycle (cyclesPerOrbit=1). This replaces the old time-based RGB-space
        // `colorMatrix` tumble, which rotated hash-family colour rather than
        // content-HSV and was not locked to the camera. The maths is the pure,
        // unit-tested azimuthToHuePhase (cp/hsv_color.js); only the composition
        // lives here. The continuous rotation itself is render-only (no REPL
        // observation surface — see DOMAIN_MODEL §6.1 REPL/render split).
        const _camAz = (this.controls && typeof this.controls.getAzimuthalAngle === 'function')
            ? this.controls.getAzimuthalAngle() : 0;
        const _effAz = _camAz + t * (this.spatialVelocity ? this.spatialVelocity.y : 0);
        const huePhase = (typeof this.constructor.azimuthToHuePhase === 'function')
            ? this.constructor.azimuthToHuePhase(_effAz) : 0;
        // Stash for on-demand consumers (halo phantoms, §709) so they rotate in
        // colour with their projector parents.
        this._currentHuePhase = huePhase;
        const _applyHuePhase = this.constructor.applyHuePhase;
        // §709 — keep any open halo phantoms' hue tracking their projector
        // parents (render-only; no-op when no halo is open).
        if (typeof this._updateHaloPhantomHues === 'function') this._updateHaloPhantomHues();

        // Collapse-state lerp (doc-level — folds all chunks of a URL into
        // its hub or back out as a single group)
        this.docCollapseTarget.forEach((target, doc_id) => {
            let current = this.docCollapseState.get(doc_id) || 0;
            if (current !== target) {
                current = target > current
                    ? Math.min(1, current + delta * 4)
                    : Math.max(0, current - delta * 4);
                this.docCollapseState.set(doc_id, current);
            }
        });
        // Per-chunk override lerp — drives the "expanding spine" effect
        // when the user scrolls over search results: each visible row's
        // chunk eases out of (or back into) its hub independently of its
        // parent doc's collapse state.
        if (this.chunkCollapseTarget && this.chunkCollapseTarget.size) {
            this.chunkCollapseTarget.forEach((target, chunkId) => {
                let current = this.chunkCollapseState.get(chunkId);
                if (current === undefined) current = 1;  // start folded
                if (current !== target) {
                    current = target > current
                        ? Math.min(1, current + delta * 4)
                        : Math.max(0, current - delta * 4);
                    this.chunkCollapseState.set(chunkId, current);
                }
            });
        }

        // Frustum
        const frustum          = new THREE.Frustum();
        const projScreenMatrix = new THREE.Matrix4();
        projScreenMatrix.multiplyMatrices(this.camera.projectionMatrix, this.camera.matrixWorldInverse);
        frustum.setFromProjectionMatrix(projScreenMatrix);

        const extraConnectorPositions = [];

        // Per-frame frustum-membership + world-space position record.
        // The sprite-visibility loop below needs to know two things
        // about each nodeId: is it inside the camera frustum (so the
        // sprite should be rendered) and where in world space did
        // the mesh loop just decide to put it (so the sprite can be
        // pinned to that exact spot — important because the
        // sphere-or-sprite replacement zeros the sphere's scale and
        // therefore breaks any signal that tries to derive
        // visibility from the sphere's instance matrix).
        const insideFrustum = new Map();
        const worldPosByNode = new Map();

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
                if (!init) { mesh.setMatrixAt(i, new THREE.Matrix4().makeScale(0, 0, 0)); continue; }
                const data = this.dataMap.get(nodeId);
                let pos = init.position.clone();
                if (data && !data.is_document && data.doc_id) {
                    // Per-chunk override (set by search-panel scroll
                    // events for the "expanding spine" effect) wins
                    // over the parent doc's collapse state. If neither
                    // is set the chunk stays at its canonical position.
                    let collapseT;
                    if (this.chunkCollapseState && this.chunkCollapseState.has(nodeId)) {
                        collapseT = this.chunkCollapseState.get(nodeId);
                    } else {
                        collapseT = this.docCollapseState.get(data.doc_id) || 0;
                    }
                    if (collapseT > 0) {
                        const docInit = this.initialNodeData.get(data.doc_id);
                        if (docInit) pos.lerp(docInit.position, collapseT);
                    }
                }
                pos.applyMatrix4(spatialMatrix);

                const inside = frustum.containsPoint(pos);
                insideFrustum.set(nodeId, inside);
                worldPosByNode.set(nodeId, pos);
                // Sphere-or-billboard replacement: if a sprite has
                // been spawned for this node, the sphere collapses
                // to scale 0 so the user sees the image alone, not
                // the image sitting on top of a redundant sphere.
                // Sprite visibility below is now driven from the
                // `insideFrustum` map we just populated — NOT from
                // this scale value — so zeroing the sphere here
                // cannot hide its sprite.
                const hasSprite = this._imageSprites && this._imageSprites.has(nodeId);
                // Per Mortegon §4.3: per-URL visibility gate. Eye-off
                // in the sidebar adds the URL to `_hiddenUrls`; this
                // loop forces scale=0 for any node belonging to a
                // hidden URL, regardless of frustum/sprite state.
                const urlHidden = this._hiddenUrls && data && data.url &&
                                  this._hiddenUrls.has(data.url);
                // §6.6.5/§7.3.5 (Q.3-Q.5) — rank-dominance collapse isolate:
                // a node whose chunk-id (or instance-id) is in the active
                // collapse's folded/hidden set is forced to scale 0, so the
                // dominator alone remains. Driven by the dominance_collapse
                // mirror (scanner.js ui_state_changed handler).
                const domHidden = this._dominanceHiddenChunkIds &&
                    this._dominanceHiddenChunkIds.size > 0 &&
                    ( this._dominanceHiddenChunkIds.has(nodeId) ||
                      (data && data.chunk_id &&
                       this._dominanceHiddenChunkIds.has(String(data.chunk_id))) );
                const scale  = (inside && !hasSprite && !urlHidden && !domHidden) ? 1.0 : 0.0;
                mesh.setMatrixAt(i, new THREE.Matrix4().compose(pos, new THREE.Quaternion(), new THREE.Vector3(scale, scale, scale)));

                // §6.1/§707 — content-HSV fill with camera-azimuth hue rotation.
                // Base {h,s,l} is the UMAP content colour (init.umapHsl); rotate
                // the hue by the per-frame phase, then setHSL. Fallback to a
                // neutral band if umapHsl is somehow absent (never NaN/black).
                const hsl = init.umapHsl || { h: 0.6, s: 0.6, l: 0.5 };
                const rotatedHue = _applyHuePhase ? _applyHuePhase(hsl.h, huePhase)
                                                  : hsl.h;
                const newColor = new THREE.Color();
                newColor.setHSL(rotatedHue, hsl.s, hsl.l);
                const entry    = this.nodeInstanceMap.get(nodeId);
                // §9.12 — provenance tint composes ON TOP of the rotating
                // content-HSV (lerp 25% toward the signature hue), every frame,
                // so content identity and provenance are both legible. Recorded
                // by instance_manager._applyProvenanceTint; applied here (a
                // direct write there would be clobbered by this loop — the prior
                // W17 bug). scanner-emitted → _provenanceTint is null → no tint.
                if (entry && entry._provenanceTint) {
                    newColor.lerp(entry._provenanceTint, 0.25);
                }
                if (entry) entry.originalColor.copy(newColor);

                let finalColor = newColor;
                if (nodeId === this.selectedId)
                    finalColor = newColor.clone().lerp(new THREE.Color(1, 1, 1), 0.5);
                else if (this.searchResults && this.searchResults.has(nodeId))
                    finalColor = newColor.clone().lerp(new THREE.Color(1, 1, 1), this.searchResults.get(nodeId) * 0.4);
                else if (nodeId === this.hoveredId)
                    finalColor = newColor.clone().multiplyScalar(1.5);

                if (mesh.instanceColor) { mesh.setColorAt(i, finalColor); mesh.instanceColor.needsUpdate = true; }

                // Extra-sprite connectors: dashed lines from the
                // sphere's centre out to each of its orbiting
                // extra-image sprites. Gate on frustum membership
                // alone — NOT on the sphere's render scale — so
                // sprite-replaced nodes (sphere scale=0) still get
                // their connector mesh updated.
                if (inside && this._extraSprites) {
                    const extras = this._extraSprites.get(nodeId);
                    if (extras && extras.length) {
                        for (const spr of extras) {
                            const sprPos = spr.position.clone();
                            extraConnectorPositions.push(pos.x, pos.y, pos.z, sprPos.x, sprPos.y, sprPos.z);
                        }
                    }
                }
            }
            mesh.instanceMatrix.needsUpdate = true;
            if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
        };

        updateMesh(this.docInstancedMesh,  true);
        updateMesh(this.instInstancedMesh, false);

        // ── Sprite visibility ──
        // Driven by the `insideFrustum` map the mesh loop just built,
        // NOT by the sphere's instance scale. The sphere's scale is 0
        // whenever a sprite exists (sprite-replaces-sphere), so the
        // old "decompose the instance matrix and check s.x" trick
        // returned false for the very nodes whose sprites we want
        // visible. Using the frustum map directly makes the two
        // signals independent.
        //
        // We also reuse the world-space `pos` the mesh loop wrote
        // (`worldPosByNode`) instead of calling `_getNodePosition`
        // again — that helper redecomposes the instance matrix,
        // which for sprite-replaced nodes returns a position with
        // scale 0 that some browsers treat as "not really there".
        // Helper: per-Mortegon §4.3, sprites also honour the per-URL
        // visibility gate. The mesh loop already hides their sphere;
        // here we hide the sprite itself so eye-off truly removes
        // the node from the GUI.
        const isUrlHidden = (nodeId) => {
            // §6.6.5/§7.3.5 — also hide sprites of dominance-collapsed nodes.
            if (this._dominanceHiddenChunkIds && this._dominanceHiddenChunkIds.size > 0) {
                const d0 = this.dataMap.get(nodeId);
                if (this._dominanceHiddenChunkIds.has(nodeId) ||
                    (d0 && d0.chunk_id && this._dominanceHiddenChunkIds.has(String(d0.chunk_id)))) {
                    return true;
                }
            }
            if (!this._hiddenUrls) return false;
            const d = this.dataMap.get(nodeId);
            return !!(d && d.url && this._hiddenUrls.has(d.url));
        };
        this._imageSprites.forEach((sprite, nodeId) => {
            const visible = !!insideFrustum.get(nodeId) && !isUrlHidden(nodeId);
            sprite.visible = visible;
            if (visible) {
                const pos = worldPosByNode.get(nodeId);
                if (pos) sprite.position.copy(pos);
            }
        });
        this._extraSprites.forEach((arr, nodeId) => {
            const visible = !!insideFrustum.get(nodeId) && !isUrlHidden(nodeId);
            arr.forEach(sprite => { sprite.visible = visible; });
        });

        this._updateExtraConnectors(extraConnectorPositions);

        // Live edge-position update
        if (this.linesMesh && this.edges && this.edges.length) {
            const positions = this.linesMesh.geometry.attributes.position.array;
            let idx = 0;
            this.edges.forEach(e => {
                const sInit = this.initialNodeData.get(e.source);
                const tInit = this.initialNodeData.get(e.target);
                if (sInit && tInit) {
                    const sData    = this.dataMap.get(e.source);
                    // Same override precedence as the mesh loop above:
                    // per-chunk first (search-panel spine), then doc.
                    let collapseT = 0;
                    if (sData && sData.doc_id) {
                        if (this.chunkCollapseState && this.chunkCollapseState.has(e.source)) {
                            collapseT = this.chunkCollapseState.get(e.source);
                        } else {
                            collapseT = this.docCollapseState.get(sData.doc_id) || 0;
                        }
                    }
                    const sPos = sInit.position.clone();
                    if (collapseT > 0) sPos.lerp(tInit.position, collapseT);
                    const tPos = tInit.position.clone();
                    sPos.applyMatrix4(spatialMatrix);
                    tPos.applyMatrix4(spatialMatrix);
                    positions[idx++] = sPos.x; positions[idx++] = sPos.y; positions[idx++] = sPos.z;
                    positions[idx++] = tPos.x; positions[idx++] = tPos.y; positions[idx++] = tPos.z;
                }
            });
            this.linesMesh.geometry.attributes.position.needsUpdate = true;
        }

        // Force-directed radial layout step (Mortegon §2.2).
        // Runs only when UMAP has activated the layout; otherwise no-op.
        if (typeof this._stepForceDirected === 'function') {
            try { this._stepForceDirected(delta); }
            catch (_) { /* never let force step abort the animate loop */ }
        }

        // Adaptive zoom bounds (Mortegon §3.1):
        //   minDistance = 0.6 × clusterRadius of the workspace under
        //     the orbit target — so dollying in still keeps part of
        //     the cluster's outer surface visible.
        //   maxDistance = 3.0 × outermost node radius — so the user
        //     can frame the whole scene but never escape to infinity.
        if (this.controls && this.initialNodeData && this.initialNodeData.size) {
            let maxR2 = 0;
            this.initialNodeData.forEach((init) => {
                const p = init.position;
                const r2 = p.x*p.x + p.y*p.y + p.z*p.z;
                if (r2 > maxR2) maxR2 = r2;
            });
            const maxR = Math.sqrt(maxR2);
            // Per Mortegon §3.1, maxDistance is 3.0 × outermost
            // node radius (was 2.5 — bumped so the user can always
            // pull back far enough to frame multi-scan workspaces).
            const wantMax = Math.max(60, maxR * 3.0);
            if (Math.abs(this.controls.maxDistance - wantMax) > 1) {
                this.controls.maxDistance = wantMax;
            }
            // minDistance: cluster radius of the largest workspace's
            // doc-hub (chunksPerDoc.maxN drives docShellRadius). We
            // pick the largest cluster so dollying never lets the
            // user lose sight of the densest hub. Static for the
            // life of a scan; recomputed only when workspace size
            // changes (cheap — single Map.get + sqrt).
            let maxChunks = 1;
            if (this._chunksPerDoc) {
                this._chunksPerDoc.forEach((n) => { if (n > maxChunks) maxChunks = n; });
            }
            // `this.constructor.docShellRadius` reads the static
            // helper that chunk_projector.js attaches to the
            // ChunkProjector class itself (mirrors the layout.js
            // export). Falls back to the bare DOC_SHELL_RADIUS
            // constant of 12 if the static is missing (e.g. during
            // hot-reload before chunk_projector.js finishes).
            const docShellR = (this.constructor &&
                               typeof this.constructor.docShellRadius === 'function')
                ? this.constructor.docShellRadius(maxChunks)
                : 12;
            // 0.6 × clusterRadius — leaves room to still see the
            // outer surface of the cluster at the camera's closest
            // approach. The hard floor of 2 prevents pathological
            // tiny scans (1–2 chunks) from collapsing minDistance
            // to a value that effectively lets the user dolly INTO
            // a sphere (sphere radius is 0.32–0.6).
            const wantMin = Math.max(2, docShellR * 0.6);
            if (Math.abs(this.controls.minDistance - wantMin) > 0.5) {
                this.controls.minDistance = wantMin;
            }
        }

        if (this.controls) this.controls.update();
        this.renderer.render(this.scene, this.camera);

        const targetId = this.selectedId || this.hoveredId;
        if (targetId && document.getElementById('billboard').style.display === 'block') {
            const pos = this._getNodePosition(targetId);
            if (pos) this.updateBillboardPosition({ position: pos });
        }

        // 2D ↔ 3D arrow tracking: each pinned concept card with
        // `data-3d-node-id` gets a solid SVG line from its border to
        // its corresponding sphere's projected screen position. Runs
        // every frame so the line tracks the snow-globe rotation in
        // real time. Cheap when no cards are pinned (early-out).
        if (typeof this._drawConcept3DLinks === 'function') {
            try { this._drawConcept3DLinks(); }
            catch (e) { /* keep the animate loop alive on any draw error */ }
        }
    },

    _updateExtraConnectors(positions) {
        if (!positions || positions.length === 0) {
            if (this._extraConnectorsMesh) this._extraConnectorsMesh.visible = false;
            return;
        }
        const posArr = new Float32Array(positions);
        if (!this._extraConnectorsMesh) {
            const geom = new THREE.BufferGeometry();
            geom.setAttribute('position', new THREE.BufferAttribute(posArr, 3));
            const mat  = new THREE.LineBasicMaterial({ color: 0x7d8b9a, transparent: true, opacity: 0.35 });
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
    },
};
