class SchemaCompass {
    constructor(container) {
        this.container = container;  // DOM element in bottom-left
        this.expanded = false;
        this.schemaData = null;      // from GET /api/graph/schema
        this.selectedType = null;
    }

    load(schemaData) {
        this.schemaData = schemaData;
        console.log("Loaded schema compass", schemaData);
    }

    highlightType(typeName) {
        console.log("Highlight type in schema compass", typeName);
    }

    onTypeClick(typeName) {
        console.log("Type click", typeName);
    }

    onTypeDoubleClick(typeName) {
        console.log("Type dblclick", typeName);
    }

    toggle() {
        this.expanded = !this.expanded;
        console.log("Toggled schema compass to", this.expanded);
    }
}
