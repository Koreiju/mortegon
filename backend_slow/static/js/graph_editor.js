class GraphEditorUI {
    constructor(scene, projector) {
        this.scene = scene;
        this.projector = projector;
        this.mode = 'label';     // 'label' (DOM CAD tools) or 'graph' (knowledge graph editor)
        this.undoStack = [];     // §8A.8 edit history for undo
        this.redoStack = [];
        this.activeView = null;  // §8A.10 current filter view
    }

    toggleMode() {
        this.mode = this.mode === 'label' ? 'graph' : 'label';
        console.log("Mode switched to", this.mode);
    }

    // --- Node creation ---
    addNote(position) {
        console.log("Add note at", position);
    }

    addOntologyNode(position) {
        console.log("Add ontology node at", position);
    }

    pinSubtree(lcaXpath) {
        console.log("Pin subtree", lcaXpath);
    }

    // --- Edge creation (§8A.6 drag gesture) ---
    startEdgeDrag(sourceId) {
        console.log("Start edge drag from", sourceId);
    }

    completeEdgeDrag(sourceId, targetId) {
        console.log("Complete edge drag between", sourceId, "and", targetId);
    }

    // --- Node interaction ---
    showNodeProperties(nodeId) {
        console.log("Show properties for", nodeId);
    }

    editNodeInline(nodeId) {
        console.log("Edit inline for", nodeId);
    }

    deleteNode(nodeId) {
        console.log("Delete node", nodeId);
    }

    repositionNode(nodeId, newPosition) {
        console.log("Reposition", nodeId, "to", newPosition);
    }

    // --- Multi-select (§8A.6) ---
    addToSelection(nodeId) {
        console.log("Add to selection", nodeId);
    }

    batchCreateEdges(selectedIds, targetId, edgeType) {
        console.log("Batch edge create");
    }

    // --- Undo / Redo (§8A.8) ---
    undo() {
        console.log("Undo");
    }

    redo() {
        console.log("Redo");
    }

    // --- Retrieval panel (§8A.3) ---
    openSearchPanel() {
        console.log("Open search panel");
    }

    // --- Views (§8A.10) ---
    openViewPanel() {
        console.log("Open view panel");
    }

    applyView(viewId) {
        console.log("Apply view", viewId);
    }

    // --- Context assembly (§8A.4) ---
    openAssemblyPanel() {
        console.log("Open assembly panel");
    }

    // --- Import / Export (§8A.9) ---
    openImportExportPanel() {
        console.log("Open import export panel");
    }
}
