/* SettingsPanel — Settings modal with tile size, format, quality, fp16 */

function settingsPanel() {
    return {
        tileSize: 512,
        defaultFormat: 'png',
        jpegQuality: 95,
        fp16: true,
        defaultScale: 4,
        maxLoadedModels: 3,

        async loadSettings() {
            try {
                const res = await fetch('/api/settings');
                const data = await res.json();
                this.tileSize = data.tile_size;
                this.defaultFormat = data.default_format;
                this.jpegQuality = data.jpeg_quality;
                this.fp16 = data.fp16;
                this.defaultScale = data.default_scale;
                this.maxLoadedModels = data.max_loaded_models;
            } catch (e) {
                console.error('Failed to load settings:', e);
            }
        },

        async saveSettings() {
            try {
                const res = await fetch('/api/settings', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tile_size: this.tileSize,
                        tile_overlap: 32,
                        default_format: this.defaultFormat,
                        jpeg_quality: this.jpegQuality,
                        fp16: this.fp16,
                        default_scale: this.defaultScale,
                        max_loaded_models: this.maxLoadedModels,
                    }),
                });
                if (!res.ok) throw new Error('Save failed');
                window.dispatchEvent(new CustomEvent('toast', {
                    detail: { msg: 'Settings saved', type: 'success' }
                }));
            } catch (e) {
                window.dispatchEvent(new CustomEvent('toast', {
                    detail: { msg: `Failed to save settings: ${e.message}`, type: 'error' }
                }));
            }
        },
    };
}
