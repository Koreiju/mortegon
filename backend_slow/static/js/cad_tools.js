/**
 * cad_tools.js
 * Dispatcher for Point / Paint / Similar-Preview / LCA-Preview CAD tools (§14.11).
 */

class CadToolDispatcher {
    constructor(projector, workflowClient) {
        this.projector = projector;
        this.client = workflowClient;
        this.tool = 'point'; // 'point', 'paint', 'similar-preview', 'lca-preview'
        this.autoCommute = true;
        this.paintBuffer = new Set();
        this.isPainting = false;

        this.bindEvents();
    }

    bindEvents() {
        window.addEventListener('keydown', (e) => this.onKeyDown(e));
    }

    setTool(tool) {
        this.tool = tool;
        console.log(`[CAD] Tool set to: ${tool}`);
        if (tool !== 'paint') {
            this.cancel();
        }
    }

    setAutoCommute(on) {
        this.autoCommute = on;
        console.log(`[CAD] Auto-commute: ${on ? 'ON' : 'OFF'}`);
    }

    onKeyDown(e) {
        // Ignore if user is typing in an input or textarea
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        
        if (e.key === 'v' || e.key === 'V') this.setTool('point');
        if (e.key === 'p' || e.key === 'P') this.setTool('paint');
        if (e.key === 's' || e.key === 'S') this.setTool('similar-preview');
        if (e.key === 'a' || e.key === 'A') this.setTool('lca-preview');
        if (e.key === 'c' || e.key === 'C') this.setAutoCommute(!this.autoCommute);
        if (e.key === 'Escape') this.cancel();
    }

    cancel() {
        this.paintBuffer.clear();
        this.isPainting = false;
        if (this.projector.controls) this.projector.controls.enabled = true;
        this.projector.clearHighlights();
    }

    handleNodeInteraction(id, eventType) {
        if (this.tool === 'paint') {
            if (eventType === 'mousedown' && id) {
                this.isPainting = true;
                this.paintBuffer.clear();
                this.paintBuffer.add(id);
                this.projector.highlightTemporary(id);
                if (this.projector.controls) this.projector.controls.enabled = false; // Disable orbit while painting
                return true;
            } else if (eventType === 'mousemove' && this.isPainting && id) {
                if (!this.paintBuffer.has(id)) {
                    this.paintBuffer.add(id);
                    this.projector.highlightTemporary(id);
                }
                return true;
            } else if (eventType === 'mouseup') {
                if (this.isPainting) {
                    this.isPainting = false;
                    if (this.projector.controls) this.projector.controls.enabled = true;
                    let firstId = this.paintBuffer.values().next().value;
                    if (firstId) {
                        const d = this.projector.dataMap.get(firstId);
                        if (d) this._commitPaint(d.url, d.snapshotIndex);
                    }
                    return true;
                }
            }
        } else if (this.tool === 'similar-preview') {
            if (eventType === 'click' && id) {
                const d = this.projector.dataMap.get(id);
                if (d) {
                    this.client.selectStructural(d.url, d.xpath)
                        .then(res => this.projector.highlightXpaths(res.matches || []))
                        .catch(e => console.error("[CAD] Similar preview failed", e));
                }
                return true;
            }
        }
        return false;
    }

    async _commitPaint(url, snapshotIndex) {
        if (this.paintBuffer.size === 0) return;
        const label = prompt("Enter label for painted nodes:");
        if (!label) {
            this.cancel();
            return;
        }

        const xpaths = [];
        this.paintBuffer.forEach(id => {
            const d = this.projector.dataMap.get(id);
            if (d) xpaths.push(d.xpath);
        });

        try {
            const res = await this.client.paintLabel(url, snapshotIndex, label, xpaths, {
                autoCommute: this.autoCommute,
                autoLca: true
            });
            console.log("[CAD] Paint batch committed", res);
            this.projector.highlightXpaths(res.consolidated?.pattern_xpaths || []);
        } catch (e) {
            console.error("[CAD] Paint failed", e);
        }
        this.paintBuffer.clear();
    }
}