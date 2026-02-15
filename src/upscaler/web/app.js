/* Photo Upscaler — Main Application (Alpine.js) */

document.addEventListener('alpine:init', () => {
    // --- Alpine Stores ---

    // Models store — shared across tabs
    Alpine.store('models', {
        list: [],
        async refresh() {
            try {
                const res = await fetch('/api/models');
                this.list = await res.json();
            } catch (e) {
                console.error('Failed to load models:', e);
            }
        }
    });

    // Viewport store — shared zoom/pan for comparison view
    Alpine.store('viewport', {
        zoom: 1,
        panX: 0,
        panY: 0,
    });
});

function app() {
    return {
        // Tabs
        tab: 'models',

        // State
        showSettings: false,
        uploadedFile: null,
        selectedModel: '',
        upscaleScale: 4,
        outputFormat: 'png',
        isProcessing: false,
        resultUrl: null,
        loadedModelCount: 0,

        // Compare state
        compareModels: [],
        compareScale: 4,
        isComparing: false,
        comparisonId: null,

        // WebSocket
        ws: null,
        wsReconnectTimer: null,

        async init() {
            await Alpine.store('models').refresh();
            this.updateLoadedCount();
            this.connectWebSocket();

            // Poll for model count updates
            setInterval(() => this.updateLoadedCount(), 5000);
        },

        updateLoadedCount() {
            const models = Alpine.store('models').list;
            this.loadedModelCount = models.filter(m => m.is_loaded).length;
        },

        connectWebSocket() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${location.host}/ws/progress`;

            try {
                this.ws = new WebSocket(wsUrl);
                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    // Send periodic pings to keep alive
                    this._pingInterval = setInterval(() => {
                        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                            this.ws.send('ping');
                        }
                    }, 30000);
                };

                this.ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        this.handleWSEvent(data);
                    } catch (e) {}
                };

                this.ws.onclose = () => {
                    clearInterval(this._pingInterval);
                    // Reconnect after 3 seconds
                    this.wsReconnectTimer = setTimeout(() => this.connectWebSocket(), 3000);
                };

                this.ws.onerror = () => {
                    this.ws.close();
                };
            } catch (e) {
                console.error('WebSocket connection failed:', e);
            }
        },

        handleWSEvent(data) {
            // Dispatch to relevant components via custom events
            window.dispatchEvent(new CustomEvent('ws-event', { detail: data }));

            if (data.type === 'model_loaded' || data.type === 'model_loading') {
                Alpine.store('models').refresh();
                this.updateLoadedCount();
            }

            if (data.type === 'comparison_model_done' && data.success) {
                window.dispatchEvent(new CustomEvent('comparison-model-done', { detail: data }));
            }

            if (data.type === 'image_complete') {
                this.toast('Image processing complete', 'success');
            }

            if (data.type === 'image_error') {
                this.toast(`Error: ${data.error || 'Processing failed'}`, 'error');
            }
        },

        toast(msg, type = 'info') {
            window.dispatchEvent(new CustomEvent('toast', { detail: { msg, type } }));
        },

        // --- Upscale ---

        async startUpscale() {
            if (!this.uploadedFile || !this.selectedModel) return;
            this.isProcessing = true;
            this.resultUrl = null;

            const formData = new FormData();
            formData.append('file', this.uploadedFile);
            formData.append('model_id', this.selectedModel);
            formData.append('scale', this.upscaleScale);
            formData.append('output_format', this.outputFormat);

            try {
                const res = await fetch('/api/upscale', { method: 'POST', body: formData });
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Upscale failed');
                }
                const blob = await res.blob();
                this.resultUrl = URL.createObjectURL(blob);
                window.dispatchEvent(new CustomEvent('result-ready', { detail: { url: this.resultUrl } }));
            } catch (e) {
                this.toast(e.message, 'error');
            } finally {
                this.isProcessing = false;
            }
        },

        // --- Compare ---

        async startComparison() {
            if (!this.uploadedFile || this.compareModels.length === 0) return;
            this.isComparing = true;

            const formData = new FormData();
            formData.append('file', this.uploadedFile);
            formData.append('model_ids', this.compareModels.join(','));
            formData.append('scale', this.compareScale);
            formData.append('output_format', this.outputFormat);

            try {
                const res = await fetch('/api/compare', { method: 'POST', body: formData });
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Comparison failed');
                }
                const data = await res.json();
                this.comparisonId = data.comparison_id;

                // Set up original image panel
                const originalUrl = `/api/images/${data.input_image_id}`;
                window.dispatchEvent(new CustomEvent('comparison-start', {
                    detail: {
                        comparisonId: data.comparison_id,
                        originalUrl,
                        modelIds: this.compareModels,
                    }
                }));

                // Poll for results
                this.pollComparison(data.comparison_id);
            } catch (e) {
                this.toast(e.message, 'error');
                this.isComparing = false;
            }
        },

        async pollComparison(comparisonId) {
            const expectedCount = this.compareModels.length;
            const seen = new Set();

            const poll = async () => {
                try {
                    const res = await fetch(`/api/compare/${comparisonId}`);
                    const data = await res.json();

                    for (const result of data.results) {
                        if (!seen.has(result.model_id)) {
                            seen.add(result.model_id);
                            window.dispatchEvent(new CustomEvent('comparison-result', {
                                detail: {
                                    modelId: result.model_id,
                                    imageId: result.image_id,
                                    imageUrl: result.image_id ? `/api/images/${result.image_id}` : null,
                                    duration: result.duration_seconds,
                                    success: result.success,
                                    error: result.error,
                                }
                            }));
                        }
                    }

                    if (seen.size < expectedCount) {
                        setTimeout(poll, 1500);
                    } else {
                        this.isComparing = false;
                        this.toast('Comparison complete', 'success');
                    }
                } catch (e) {
                    setTimeout(poll, 2000);
                }
            };

            setTimeout(poll, 2000);
        },
    };
}
