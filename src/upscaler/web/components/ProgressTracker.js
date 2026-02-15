/* ProgressTracker — WebSocket-driven progress bars with ETA */

function progressTracker() {
    return {
        progressPercent: 0,
        progressLabel: 'Waiting...',
        startTime: null,
        _handler: null,

        init() {
            this.startTime = Date.now();
            this._handler = (e) => this.handleWSEvent(e.detail);
            window.addEventListener('ws-event', this._handler);
        },

        destroy() {
            if (this._handler) {
                window.removeEventListener('ws-event', this._handler);
            }
        },

        handleWSEvent(data) {
            if (data.type === 'tile_progress') {
                const done = data.tiles_done || 0;
                const total = data.tiles_total || 1;
                const passNum = data.pass_num || 1;
                const totalPasses = data.total_passes || 1;
                const pct = Math.round((done / total) * 100);
                this.progressPercent = pct;

                let label = `Tiles: ${done}/${total}`;
                if (totalPasses > 1) {
                    label = `Pass ${passNum}/${totalPasses} — ${label}`;
                }

                // ETA calculation
                const elapsed = (Date.now() - this.startTime) / 1000;
                if (done > 0 && elapsed > 2) {
                    const rate = done / elapsed;
                    const remaining = (total - done) / rate;
                    label += ` — ~${Math.ceil(remaining)}s remaining`;
                }

                this.progressLabel = label;
            }

            if (data.type === 'model_loading') {
                this.progressLabel = `Loading model: ${data.model_id || ''}...`;
                this.progressPercent = 0;
                this.startTime = Date.now();
            }

            if (data.type === 'model_loaded') {
                this.progressLabel = 'Model loaded, processing...';
            }

            if (data.type === 'comparison_model_start') {
                this.progressLabel = `Processing: ${data.model_id || ''}...`;
                this.progressPercent = 0;
                this.startTime = Date.now();
            }

            if (data.type === 'batch_progress') {
                const completed = data.completed || 0;
                const total = data.total || 1;
                const pct = Math.round((completed / total) * 100);
                this.progressPercent = pct;
                this.progressLabel = `Batch: ${completed}/${total} images — ${data.current_file || ''}`;
            }

            if (data.type === 'download_progress') {
                const downloaded = data.downloaded || 0;
                const total = data.total || 1;
                const pct = total > 0 ? Math.round((downloaded / total) * 100) : 0;
                this.progressPercent = pct;
                const mb = (downloaded / 1024 / 1024).toFixed(1);
                const totalMb = (total / 1024 / 1024).toFixed(1);
                this.progressLabel = `Downloading: ${mb}/${totalMb} MB`;
            }

            if (data.type === 'image_complete') {
                this.progressPercent = 100;
                this.progressLabel = 'Complete!';
            }
        },
    };
}
