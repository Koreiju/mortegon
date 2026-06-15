class GhostNodeManager {
    constructor(scene, graphEditor) {
        this.scene = scene;
        this.graphEditor = graphEditor;
        this.activeGhosts = new Map();  // ghost_id → GhostState
    }

    spawn(sourceNodeId, position, preselectedEdgeType = null) {
        let ghostId = "ghost_" + Date.now();
        this.activeGhosts.set(ghostId, { sourceNodeId, position, edgeType: preselectedEdgeType, type: null });
        console.log("Spawned ghost node", ghostId);
        return ghostId;
    }

    selectType(ghostId, type) {
        let ghost = this.activeGhosts.get(ghostId);
        if (ghost) {
            ghost.type = type;
            console.log("Selected type", type, "for", ghostId);
        }
    }

    selectEdgeType(ghostId, edgeType) {
        let ghost = this.activeGhosts.get(ghostId);
        if (ghost) {
            ghost.edgeType = edgeType;
            console.log("Selected edge type", edgeType, "for", ghostId);
        }
    }

    commit(ghostId) {
        console.log("Committed ghost", ghostId);
        this.activeGhosts.delete(ghostId);
    }

    cancel(ghostId) {
        console.log("Cancelled ghost", ghostId);
        this.activeGhosts.delete(ghostId);
    }

    cancelAll() {
        console.log("Cancelled all ghosts");
        this.activeGhosts.clear();
    }
}
