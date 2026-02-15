/* BatchPanel — Batch folder processing UI */

function batchPanel() {
    return {
        batchInputDir: '',
        batchOutputDir: '',
        batchModel: '',
        batchScale: 4,
        batchRecursive: false,
        batchSkipExisting: false,
        batchRunning: false,
        batchStatus: '',
        batchJobId: null,

        async startBatch() {
            if (!this.batchInputDir || !this.batchModel) return;
            this.batchRunning = true;
            this.batchStatus = '';

            const formData = new FormData();
            formData.append('input_dir', this.batchInputDir);
            formData.append('output_dir', this.batchOutputDir);
            formData.append('model_id', this.batchModel);
            formData.append('scale', this.batchScale);
            formData.append('recursive', this.batchRecursive);
            formData.append('skip_existing', this.batchSkipExisting);

            try {
                const res = await fetch('/api/upscale/batch', {
                    method: 'POST',
                    body: formData,
                });
                if (!res.ok) throw new Error('Batch start failed');
                const data = await res.json();
                this.batchJobId = data.job_id;
                this.pollJob(data.job_id);
            } catch (e) {
                this.batchRunning = false;
                window.dispatchEvent(new CustomEvent('toast', {
                    detail: { msg: e.message, type: 'error' }
                }));
            }
        },

        async pollJob(jobId) {
            const poll = async () => {
                try {
                    const res = await fetch(`/api/jobs/${jobId}`);
                    const data = await res.json();

                    if (data.status === 'completed') {
                        this.batchRunning = false;
                        const r = data.results && data.results[0];
                        if (r) {
                            this.batchStatus = `Complete: ${r.completed} processed, ${r.skipped} skipped, ${r.failed} failed`;
                        } else {
                            this.batchStatus = 'Batch complete';
                        }
                        window.dispatchEvent(new CustomEvent('toast', {
                            detail: { msg: 'Batch processing complete', type: 'success' }
                        }));
                        return;
                    }

                    if (data.status === 'failed') {
                        this.batchRunning = false;
                        this.batchStatus = `Failed: ${data.error || 'Unknown error'}`;
                        return;
                    }

                    setTimeout(poll, 2000);
                } catch (e) {
                    setTimeout(poll, 3000);
                }
            };
            setTimeout(poll, 1000);
        },
    };
}
