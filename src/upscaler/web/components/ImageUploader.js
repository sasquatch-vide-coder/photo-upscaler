/* ImageUploader — Drag-and-drop with preview */

function imageUploader() {
    return {
        dragover: false,
        preview: null,
        fileName: '',
        dimensions: '',
        fileSize: '',

        handleDrop(event) {
            this.dragover = false;
            const files = event.dataTransfer.files;
            if (files.length > 0) this.processFile(files[0]);
        },

        handleFileSelect(event) {
            const files = event.target.files;
            if (files.length > 0) this.processFile(files[0]);
        },

        processFile(file) {
            const validTypes = ['image/png', 'image/jpeg', 'image/webp', 'image/bmp', 'image/tiff'];
            if (!validTypes.includes(file.type) && !file.name.match(/\.(png|jpe?g|webp|bmp|tiff?)$/i)) {
                window.dispatchEvent(new CustomEvent('toast', {
                    detail: { msg: 'Unsupported file format', type: 'error' }
                }));
                return;
            }

            this.fileName = file.name;
            this.fileSize = (file.size / 1024 / 1024).toFixed(1) + ' MB';

            // Set on parent app data
            const appEl = document.querySelector('[x-data="app"]');
            if (appEl && appEl.__x) {
                appEl.__x.$data.uploadedFile = file;
            }
            // Also set via Alpine magic
            this.$dispatch('file-selected', { file });

            // Store on the root app
            const root = Alpine.closestRoot(this.$el).closest('[x-data="app"]');
            if (root && root._x_dataStack) {
                root._x_dataStack[0].uploadedFile = file;
            }

            // Generate preview
            const reader = new FileReader();
            reader.onload = (e) => {
                this.preview = e.target.result;
                // Get dimensions
                const img = new Image();
                img.onload = () => {
                    this.dimensions = `${img.width} x ${img.height}`;
                };
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);
        },
    };
}
