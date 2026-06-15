/**
 * cp/edge_manager.js — Edge line rendering between chunk instances and their
 * parent document hubs, plus debounced/throttled helper timers.
 *
 * Methods become ChunkProjector instance methods via prototype mixin.
 * THREE is a CDN global.
 */

export const EdgeManagerMixin = {

    rebuildEdges() {
        if (this.linesMesh) {
            this.scene.remove(this.linesMesh);
            if (this.linesMesh.geometry) this.linesMesh.geometry.dispose();
            if (this.linesMesh.material) this.linesMesh.material.dispose();
            this.linesMesh = null;
        }
        if (!this.edges || this.edges.length === 0) return;
        const lineMaterial = new THREE.LineBasicMaterial({
            color: 0x556370, transparent: true, opacity: 0.3,
        });
        const points = [];
        this.edges.forEach(e => {
            const s = this.initialNodeData.get(e.source);
            const t = this.initialNodeData.get(e.target);
            if (s && t) points.push(s.position.clone(), t.position.clone());
        });
        if (points.length > 0) {
            const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);
            this.linesMesh = new THREE.LineSegments(lineGeometry, lineMaterial);
            this.scene.add(this.linesMesh);
        }
    },

    /** Coalesce rapid edge rebuilds during streaming into a single call. */
    _rebuildEdgesSoon() {
        if (this._rebuildEdgesTimer) return;
        this._rebuildEdgesTimer = setTimeout(() => {
            this._rebuildEdgesTimer = null;
            this.rebuildEdges();
        }, 200);
    },

    /** Throttle expensive tree/bucket re-renders during streaming. */
    _requestUIUpdate() {
        if (this._uiUpdateTimer) return;
        this._uiUpdateTimer = setTimeout(() => {
            this._uiUpdateTimer = null;
            try {
                this.applyWorkspaceVisibility();
                this.renderFileTree();
                this.renderUrlBuckets();
            } catch (_) { }
        }, 800);
    },
};
