class ActivityHistory {
    /**
     * Full chronological activity feed + action replay (§15C.2, §15C.3).
     * 
     * Slide-out panel with filterable activity log,
     * causal chain visualization, and SLM-powered reification.
     */

    constructor() {
        this.entries = [];
        this.filters = { actor: null, actionVerb: null, targetType: null };
    }

    // --- History Panel ---
    open(scrollToEntryId = null) {
        // Slide panel in from right edge
        // Load history from /api/activity/history
        // If scrollToEntryId, scroll to that entry
    }

    close() { /* Slide panel out */ }

    applyFilters(filters) {
        this.filters = { ...this.filters, ...filters };
        // Re-fetch history with actor/action/target/time filters
    }

    groupBy(dimension) {
        // 'actor': group entries by who did them
        // 'time': group by time buckets
        // 'target': group by what was affected
    }

    // --- Action Replay (§15C.3) ---
    openReplay(entryId) {
        // 1. Fetch full detail from /api/activity/{id}/detail
        // 2. Render: actor context (prompt, reasoning)
        // 3. Render: diff view (before/after fields)
        // 4. Render: causal chain visualization (ancestors ← this → descendants)
    }

    traceChain(entryId, direction) {
        // Fetch and render causal chain
        // 'backward': what led to this action
        // 'forward': what happened because of this
        // Render as a connected timeline
    }

    reify(entryId, instruction) {
        // 1. POST /api/activity/{id}/reify with natural language instruction
        // 2. SLM translates to concrete operations
        // 3. Operations execute, new activity entry emitted
        // 4. Panel updates to show the reification result
    }
}
