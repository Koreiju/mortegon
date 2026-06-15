class AgenticFluidUI {
    constructor(projector) {
        this.projector = projector;
        this.activeFluidId = null;
        this.history = [];
    }

    instantiate() {
        console.log("Instantiate agentic fluid");
    }

    showRecommendation(step) {
        console.log("Show recommendation for step", step);
    }

    acceptStep(stepNum) {
        console.log("Accept step", stepNum);
    }

    rejectStep(stepNum) {
        console.log("Reject step", stepNum);
    }

    toggleAutoRun() {
        console.log("Toggle auto run");
    }

    renderTimeline(history) {
        console.log("Render timeline with", history);
        this.history = history;
    }
}
