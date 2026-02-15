/* ImageViewer — Reusable zoomable/pannable image component */

function imageViewer() {
    return {
        zoom: 1,
        panX: 0,
        panY: 0,
        isPanning: false,
        panStartX: 0,
        panStartY: 0,
        panBaseX: 0,
        panBaseY: 0,
        resultUrl: null,

        initViewer(detail) {
            if (detail && detail.url) {
                this.resultUrl = detail.url;
                this.resetView();
            }
        },

        zoomIn() {
            this.zoom = Math.min(10, this.zoom * 1.25);
        },

        zoomOut() {
            this.zoom = Math.max(0.1, this.zoom / 1.25);
        },

        resetView() {
            this.zoom = 1;
            this.panX = 0;
            this.panY = 0;
        },

        handleWheel(event) {
            event.preventDefault();
            const delta = event.deltaY > 0 ? -0.1 : 0.1;
            this.zoom = Math.max(0.1, Math.min(10, this.zoom + delta * this.zoom));
        },

        startPan(event) {
            if (event.button !== 0) return;
            this.isPanning = true;
            this.panStartX = event.clientX;
            this.panStartY = event.clientY;
            this.panBaseX = this.panX;
            this.panBaseY = this.panY;
        },

        handlePan(event) {
            if (!this.isPanning) return;
            this.panX = this.panBaseX + (event.clientX - this.panStartX) / this.zoom;
            this.panY = this.panBaseY + (event.clientY - this.panStartY) / this.zoom;
        },

        endPan() {
            this.isPanning = false;
        },
    };
}
