/**
 * Maestro Web Interface
 * Handles UI interactions, file uploads, and communication with the backend.
 */
class MaestroApp {
    constructor() {
        this.backendPort = 52000;
        this.files = [];
        this.isInstalling = false;
        this.currentLogFile = null;
        this.initialize();
    }

    initialize() {
        console.log('🎼 Maestro App Initializing...');
        window.maestroApp = this; 
        this.setupEventListeners();
        // Initial UI state
        document.getElementById('fileListSection').style.display = 'none';
        document.getElementById('actionSection').style.display = 'none';
        document.getElementById('progressSection').style.display = 'none';
        document.getElementById('resultsSection').style.display = 'none';
    }

    setupEventListeners() {
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const selectFilesBtn = document.getElementById('selectFilesBtn');
        const installBtn = document.getElementById('installBtn');
        const clearBtn = document.getElementById('clearBtn');
        const newInstallBtn = document.getElementById('newInstallBtn');

        // File Selection
        selectFilesBtn.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('click', (e) => {
            if (e.target === dropZone || e.target.parentElement === dropZone.firstElementChild) {
                fileInput.click();
            }
        });
        fileInput.addEventListener('change', (e) => this.handleFiles(Array.from(e.target.files)));

        // Drag and Drop
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('drag-over');
        });
        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('drag-over');
        });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('drag-over');
            this.handleFiles(Array.from(e.dataTransfer.files));
        });

        // Action Buttons
        installBtn.addEventListener('click', () => this.startInstallation());
        clearBtn.addEventListener('click', () => this.clearFiles());
        newInstallBtn.addEventListener('click', () => this.resetApp());

        // Password Modal Buttons
        document.getElementById('passwordSubmitBtn').addEventListener('click', () => this.submitPassword());
        document.getElementById('passwordCancelBtn').addEventListener('click', () => this.hidePasswordModal());
    }

    handleFiles(newFiles) {
        console.log('Handling files. Raw input from browser:', newFiles);
        newFiles.forEach(f => {
            console.log(`- File Name: "${f.name}", Size: ${f.size}, Type: "${f.type}"`);
        });

        const supportedExtensions = {
            '.component': 'install-component',
            '.vst': 'install-vst',
            '.vst3': 'install-vst3',
            '.aax': 'install-aax',
            '.app': 'install-app',
            '.pkg': 'install-pkg',
        };

        const validFiles = newFiles.filter(file => {
            const fileExt = this.getFileExtension(file.name);
            const checkboxId = supportedExtensions[fileExt];
            if (checkboxId && document.getElementById(checkboxId).checked) {
                return true;
            }
            this.showToast(`Skipping ${file.name} (type disabled or unsupported).`, 'warning');
            return false;
        });

        if (validFiles.length > 0) {
            this.showToast(`${validFiles.length} valid file(s) added.`, 'info');
        }

        validFiles.forEach(file => {
            if (!this.files.some(f => f.name === file.name && f.size === file.size)) {
                this.files.push(file);
            }
        });

        this.updateFileList();
    }

    updateFileList() {
        const fileListSection = document.getElementById('fileListSection');
        const actionSection = document.getElementById('actionSection');
        const fileList = document.getElementById('fileList');
        
        if (this.files.length === 0) {
            fileListSection.style.display = 'none';
            actionSection.style.display = 'none';
            return;
        }

        fileListSection.style.display = 'block';
        actionSection.style.display = 'block';
        fileList.innerHTML = '';

        this.files.forEach((file, index) => {
            fileList.appendChild(this.createFileItem(file, index));
        });
    }

    createFileItem(file, index) {
        const fileExt = this.getFileExtension(file.name);
        const fileType = this.getFileType(fileExt);
        const fileSize = this.formatFileSize(file.size);

        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="file-info">
                <div class="file-icon">${this.getFileIcon(fileType)}</div>
                <div class="file-details">
                    <h4>${file.name}</h4>
                    <p>${fileExt.toUpperCase()} &bull; ${fileSize} &bull; ${this.getInstallLocationInfo(fileType)}</p>
                </div>
            </div>
            <div class="file-actions">
                <button onclick="window.maestroApp.removeFile(${index})" title="Remove file">🗑️</button>
            </div>
        `;
        return fileItem;
    }

    async startInstallation() {
        if (this.files.length === 0 || this.isInstalling) return;

        const installType = document.querySelector('input[name="install-location"]:checked').value;
        const needsPassword = this.files.some(f => f.name.toLowerCase().endsWith('.pkg')) || installType === 'system';

        if (needsPassword) {
            this.showPasswordModal();
        } else {
            this.proceedWithInstallation('');
        }
    }
    
    async proceedWithInstallation(password) {
        this.isInstalling = true;
        this.showProgressSection();

        const installType = document.querySelector('input[name="install-location"]:checked').value;
        
        const installOptions = {
            'component': document.getElementById('install-component').checked,
            'vst': document.getElementById('install-vst').checked,
            'vst3': document.getElementById('install-vst3').checked,
            'aax': document.getElementById('install-aax').checked,
            'app': document.getElementById('install-app').checked,
            'pkg': document.getElementById('install-pkg').checked,
        };
        
        const formData = new FormData();
        this.files.forEach(file => formData.append('files', file));
        formData.append('install_type', installType);
        formData.append('password', password);
        formData.append('install_options', JSON.stringify(installOptions));

        try {
            this.addProgressLog('Uploading files to backend...');
            const response = await fetch(`http://127.0.0.1:${this.backendPort}/api/batch-install`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({ error: 'Unknown server error.' }));
                throw new Error(errData.error);
            }

            const result = await response.json();
            this.handleInstallationResults(result);

        } catch (error) {
            this.addProgressLog(`❌ Critical Error: ${error.message}`, 'error');
            this.showToast('Installation failed.', 'error');
        } finally {
            this.isInstalling = false;
        }
    }
    
    handleInstallationResults(batchResult) {
        if (!batchResult || !batchResult.results) {
            this.addProgressLog('Received an invalid response from the backend.', 'error');
            return;
        }

        this.addProgressLog(`Batch install complete. Success: ${batchResult.successful_installs}, Failed: ${batchResult.failed_installs}.`);
        this.showResults(batchResult.results);
        this.showToast('Installation complete!', 'success');
    }

    showPasswordModal() {
        document.getElementById('passwordInput').value = '';
        document.getElementById('passwordModal').style.display = 'flex';
        document.getElementById('passwordInput').focus();
    }

    hidePasswordModal() {
        document.getElementById('passwordModal').style.display = 'none';
    }

    submitPassword() {
        const password = document.getElementById('passwordInput').value;
        this.hidePasswordModal();
        if (password) {
            this.proceedWithInstallation(password);
        } else {
            this.showToast('Password cannot be empty.', 'warning');
        }
    }

    removeFile(index) {
        this.files.splice(index, 1);
        this.updateFileList();
        this.showToast('File removed.', 'info');
    }

    clearFiles() {
        this.files = [];
        this.updateFileList();
    }

    resetApp() {
        this.clearFiles();
        document.getElementById('progressSection').style.display = 'none';
        document.getElementById('resultsSection').style.display = 'none';
        this.showToast('Ready for new installation.', 'success');
    }
    
    showProgressSection() {
        document.getElementById('progressSection').style.display = 'block';
        document.getElementById('resultsSection').style.display = 'none';
        document.getElementById('progressLog').innerHTML = '';
        this.addProgressLog('Starting installation...');
    }

    addProgressLog(message, type = 'info') {
        const log = document.getElementById('progressLog');
        const p = document.createElement('p');
        p.className = type;
        p.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        log.appendChild(p);
        log.scrollTop = log.scrollHeight;
    }

    showResults(results) {
        const resultsContent = document.getElementById('resultsContent');
        resultsContent.innerHTML = '';
        document.getElementById('resultsSection').style.display = 'block';

        results.forEach(result => {
            const item = document.createElement('div');
            item.className = `result-item ${result.success ? 'success' : 'error'}`;
            let final_message = result.message || (result.success ? 'Installed successfully.' : result.error);
            item.innerHTML = `
                <span>${result.success ? '✅' : '❌'}</span>
                <span><strong>${result.file}:</strong> ${final_message}</span>
            `;
            resultsContent.appendChild(item);
        });
    }

    showToast(message, type = 'info', duration = 3000) {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), duration);
    }

    getFileExtension(filename) {
        const lower_filename = filename.toLowerCase();
        const bundleExtensions = ['.component', '.vst', '.vst3', '.app'];
        
        for (const ext of bundleExtensions) {
            if (lower_filename.endsWith(ext + '.zip')) {
                console.log(`Identified zipped bundle: ${filename}. Returning original extension: ${ext}`);
                return ext;
            }
            if (lower_filename.endsWith(ext)) {
                console.log(`Identified standard bundle: ${filename}. Returning extension: ${ext}`);
                return ext;
            }
        }
        
        const lastDot = lower_filename.lastIndexOf('.');
        if (lastDot === -1) {
            return '';
        }
        
        const standardExt = lower_filename.substring(lastDot);
        console.log(`Standard extension detected for ${filename}: ${standardExt}`);
        return standardExt;
    }

    getFileType(ext) {
        return ext.replace('.', '');
    }

    getFileIcon(type) {
        const icons = { 'component':'🎵', 'vst':'🎹', 'vst3':'🎛️', 'aax':'🎚️', 'app':'📱', 'pkg':'📦' };
        return icons[type] || '📄';
    }

    getInstallLocationInfo(type) {
        const locations = {
            'component': '-> /Library/Audio/Plug-Ins/Components',
            'vst': '-> /Library/Audio/Plug-Ins/VST',
            'vst3': '-> /Library/Audio/Plug-Ins/VST3',
            'aax': '-> /Library/Application Support/Avid/Audio/Plug-ins',
            'app': '-> /Applications',
            'pkg': '-> System-wide (via installer)'
        };
        return locations[type] || 'Unknown location';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new MaestroApp();
});
