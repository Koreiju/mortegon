class ActivityTicker {
    /**
     * Game-style scrolling text overlay on 3D viewport (§15C.1).
     * 
     * Renders naked text lines that scroll up and fade.
     * No chrome, no borders — just text over the 3D view.
     */

    constructor(wsUrl, viewportContainer) {
        this.wsUrl = wsUrl; // Usually handled through a WS layer
        this.container = viewportContainer;
        this.maxLines = 8;           // max visible at once
        this.fadeMs = 5000;          // fade duration
        this.lines = [];             // active ticker lines
    }

    onActivityEntry(entry) {
        const el = document.createElement('div');
        el.className = 'ticker-line';
        el.innerText = entry.summary || entry.action_verb;
        this.container.appendChild(el);
        this.lines.push({id: entry.entry_id, element: el});
        
        // Start fade-out timer (5 seconds)
        setTimeout(() => {
            if (el.parentNode) {
                el.parentNode.removeChild(el);
            }
            this.lines = this.lines.filter(l => l.id !== entry.entry_id);
        }, this.fadeMs);
    }

    onLineClick(entryId) {
        // Freeze this line (pause fade)
        // Open history panel scrolled to this entry
    }

    onLineHover(entryId) {
        // Pause fade timer for this line
    }

    onLineUnhover(entryId) {
        // Resume fade timer
    }
}
