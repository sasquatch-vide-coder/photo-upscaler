/* ModelSelector — Model cards with download support */

function modelSelector() {
    return {
        models: [],
        availableModels: [],
        showAvailable: false,
        loading: false,

        async loadModels() {
            this.loading = true;
            try {
                await Alpine.store('models').refresh();
                this.models = Alpine.store('models').list;

                // Load available models from registry
                const res = await fetch('/api/models/available');
                this.availableModels = (await res.json()).map(m => ({
                    ...m,
                    downloading: false,
                }));

                // Show download prompt if no models installed
                if (this.models.length === 0) {
                    this.showAvailable = true;
                }
            } catch (e) {
                console.error('Failed to load models:', e);
            } finally {
                this.loading = false;
            }
        },

        async downloadModel(entry) {
            entry.downloading = true;
            try {
                const res = await fetch('/api/models/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model_key: entry.key }),
                });
                if (!res.ok) throw new Error('Download failed');
                entry.is_downloaded = true;
                window.dispatchEvent(new CustomEvent('toast', {
                    detail: { msg: `${entry.name} downloaded`, type: 'success' }
                }));
                // Refresh model list
                await this.loadModels();
            } catch (e) {
                window.dispatchEvent(new CustomEvent('toast', {
                    detail: { msg: `Download failed: ${e.message}`, type: 'error' }
                }));
            } finally {
                entry.downloading = false;
            }
        },
    };
}
