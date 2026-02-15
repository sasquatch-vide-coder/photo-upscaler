/* ComparisonView — Synchronized zoom/pan grid with original image */

function comparisonView() {
    return {
        panels: [],
        sharedZoom: 1,
        sharedPanX: 0,
        sharedPanY: 0,
        isPanning: false,
        panStartX: 0,
        panStartY: 0,
        panBaseX: 0,
        panBaseY: 0,

        get gridCols() {
            const count = this.panels.length;
            if (count <= 2) return count;
            if (count <= 4) return 2;
            return 3;
        },

        init() {
            // Listen for comparison start
            window.addEventListener('comparison-start', (e) => {
                const { originalUrl, modelIds } = e.detail;
                this.panels = [];
                this.resetZoom();

                // Add original panel
                this.panels.push({
                    id: 'original',
                    label: 'Original',
                    url: originalUrl,
                    duration: null,
                    loaded: false,
                });

                // Add placeholder panels for each model
                for (const modelId of modelIds) {
                    this.panels.push({
                        id: modelId,
                        label: modelId,
                        url: null,
                        duration: null,
                        loaded: false,
                    });
                }
            });

            // Listen for individual model results
            window.addEventListener('comparison-result', (e) => {
                const { modelId, imageUrl, duration, success, error } = e.detail;
                const panel = this.panels.find(p => p.id === modelId);
                if (panel) {
                    if (success && imageUrl) {
                        panel.url = imageUrl;
                        panel.duration = duration;
                    } else {
                        panel.label = `${modelId} (failed)`;
                        panel.duration = duration;
                    }
                }
            });
        },

        // --- Zoom/Pan ---

        handleWheel(event) {
            const delta = event.deltaY > 0 ? -0.1 : 0.1;
            this.sharedZoom = Math.max(0.25, Math.min(10, this.sharedZoom + delta * this.sharedZoom));
        },

        startPan(event) {
            if (event.button !== 0) return;
            this.isPanning = true;
            this.panStartX = event.clientX;
            this.panStartY = event.clientY;
            this.panBaseX = this.sharedPanX;
            this.panBaseY = this.sharedPanY;
        },

        handlePan(event) {
            if (!this.isPanning) return;
            const dx = (event.clientX - this.panStartX) / this.sharedZoom;
            const dy = (event.clientY - this.panStartY) / this.sharedZoom;
            this.sharedPanX = this.panBaseX + dx;
            this.sharedPanY = this.panBaseY + dy;
        },

        endPan() {
            this.isPanning = false;
        },

        resetZoom() {
            this.sharedZoom = 1;
            this.sharedPanX = 0;
            this.sharedPanY = 0;
        },

        async saveAll() {
            for (const panel of this.panels) {
                if (!panel.url || panel.id === 'original') continue;
                try {
                    const res = await fetch(panel.url);
                    const blob = await res.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `comparison_${panel.id}.png`;
                    a.click();
                    URL.revokeObjectURL(url);
                } catch (e) {
                    console.error('Failed to save:', panel.id, e);
                }
            }
        },
    };
}
