/**
 * Maestro Web Interface
 * Handles drag-and-drop, file processing, API communication, and UI interactions
 */

class MaestroApp {
    constructor() {
        this.files = [];
        this.isInstalling = false;
        this.backendPort = window.MAESTRO_BACKEND_PORT || window.BACKEND_PORT || null;
        console.log('🎯 MaestroApp initialized with port:', this.backendPort);
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initDropZone();
        this.waitForBackendPort();
        this.showToast('Maestro ready for batch installation', 'success');
    }
    
    waitForBackendPort() {
        // Poll for backend port if not available immediately
        if (!this.backendPort) {
            console.log('⏳ Waiting for backend port...');
            this.discoverBackendPort();
        } else {
            this.getLogInfo();
        }
    }
    
    async discoverBackendPort() {
        // Try to get port from injected variable first
        if (window.MAESTRO_BACKEND_PORT) {
            this.backendPort = window.MAESTRO_BACKEND_PORT;
            console.log('✅ Backend port from injection:', this.backendPort);
            this.getLogInfo();
            return;
        }
        
        // Try to discover port by scanning common ports
        console.log('🔍 Scanning for backend port...');
        const commonPorts = [];
        
        // Generate likely port range (50000-53000)
        for (let port = 50000; port <= 53000; port += 100) {
            commonPorts.push(port);
        }
        
        for (const port of commonPorts) {
            try {
                const response = await fetch(`http://localhost:${port}/api/debug`, {
                    signal: AbortSignal.timeout(1000) // 1 second timeout
                });
                if (response.ok) {
                    const data = await response.json();
                    if (data.status === 'Backend is running successfully') {
                        this.backendPort = port;
                        console.log('✅ Backend port discovered:', port);
                        this.getLogInfo();
                        return;
                    }
                }
            } catch (error) {
                // Port not responding, continue scanning
                continue;
            }
        }
        
        // If still no port found, try a more systematic approach
        console.log('⚠️ Backend port not found in common range, trying systematic scan...');
        setTimeout(() => this.systematicPortScan(), 2000);
    }
    
    async systematicPortScan() {
        // Try ports 52000-53000 one by one
        for (let port = 52000; port <= 53000; port++) {
            try {
                const response = await fetch(`http://localhost:${port}/api/debug`, {
                    signal: AbortSignal.timeout(500) // 500ms timeout for faster scanning
                });
                if (response.ok) {
                    const data = await response.json();
                    if (data.status === 'Backend is running successfully') {
                        this.backendPort = port;
                        console.log('✅ Backend port found via systematic scan:', port);
                        this.getLogInfo();
                        return;
                    }
                }
            } catch (error) {
                // Continue scanning
                continue;
            }
        }
        
        console.error('❌ Could not discover backend port');
        this.showToast('Unable to connect to backend. Please restart the app.', 'error');
    }

    async getLogInfo() {
        try {
            const response = await fetch(`http://localhost:${this.backendPort}/api/log-info`);
            if (response.ok) {
                const logInfo = await response.json();
                console.log('Debug log file:', logInfo.log_file);
                // Store log file path for later use
                this.currentLogFile = logInfo.log_file;
            }
        } catch (error) {
            console.warn('Could not get log info:', error);
        }
    }

    setupEventListeners() {
        // File selection
        document.getElementById('selectFiles').addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });

        document.getElementById('fileInput').addEventListener('change', (e) => {
            this.handleFiles(Array.from(e.target.files));
        });

        // Action buttons
        document.getElementById('installBtn').addEventListener('click', () => {
            this.startInstallation();
        });

        document.getElementById('clearBtn').addEventListener('click', () => {
            this.clearFiles();
        });

        document.getElementById('newInstallBtn').addEventListener('click', () => {
            this.resetApp();
        });
    }

    initDropZone() {
        const dropZone = document.getElementById('dropZone');

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            if (!dropZone.contains(e.relatedTarget)) {
                dropZone.classList.remove('drag-over');
            }
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            
            const files = Array.from(e.dataTransfer.files);
            this.handleFiles(files);
        });

        dropZone.addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });
    }

    handleFiles(files) {
        const supportedExtensions = ['.component', '.vst', '.vst3', '.aax', '.app', '.pkg'];
        const validFiles = files.filter(file => {
            const fileName = file.name.toLowerCase();
            return supportedExtensions.some(ext => fileName.endsWith(ext));
        });

        if (validFiles.length === 0) {
            this.showToast('No supported files found. Please select .component, .vst, .vst3, .aax, .app, or .pkg files.', 'error');
            return;
        }

        // Add new files to the list, avoiding duplicates
        validFiles.forEach(file => {
            if (!this.files.find(f => f.name === file.name && f.size === file.size)) {
                this.files.push(file);
            }
        });

        this.updateFileList();
        this.showToast(`Added ${validFiles.length} file(s) to installation queue`, 'success');
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
            const fileItem = this.createFileItem(file, index);
            fileList.appendChild(fileItem);
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
                <div class="file-icon ${fileType}">
                    ${this.getFileIcon(fileType)}
                </div>
                <div class="file-details">
                    <h4>${file.name}</h4>
                    <p>${fileExt.toUpperCase()} • ${fileSize} • ${this.getInstallLocation(fileType)}</p>
                </div>
            </div>
            <div class="file-actions">
                <button onclick="maestroApp.removeFile(${index})" title="Remove file">
                    🗑️
                </button>
            </div>
        `;

        return fileItem;
    }

    getFileExtension(filename) {
        return filename.substring(filename.lastIndexOf('.')).toLowerCase();
    }

    getFileType(extension) {
        const typeMap = {
            '.component': 'component',
            '.vst': 'vst',
            '.vst3': 'vst3',
            '.aax': 'aax',
            '.app': 'app',
            '.pkg': 'pkg'
        };
        return typeMap[extension] || 'unknown';
    }

    getFileIcon(type) {
        const iconMap = {
            'component': '🎵',
            'vst': '🎹',
            'vst3': '🎛️',
            'aax': '🎚️',
            'app': '📱',
            'pkg': '📦'
        };
        return iconMap[type] || '📄';
    }

    getInstallLocation(type) {
        const installType = document.querySelector('input[name="install-location"]:checked').value;
        const baseLocation = installType === 'system' ? '/Library' : '~/Library';
        
        const locationMap = {
            'component': `${baseLocation}/Audio/Plug-Ins/Components/`,
            'vst': `${baseLocation}/Audio/Plug-Ins/VST/`,
            'vst3': `${baseLocation}/Audio/Plug-Ins/VST3/`,
            'aax': `${baseLocation}/Application Support/Avid/Audio/Plug-Ins/`,
            'app': installType === 'system' ? '/Applications/' : '~/Applications/',
            'pkg': 'Extracted and installed'
        };
        return locationMap[type] || 'Unknown location';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    removeFile(index) {
        this.files.splice(index, 1);
        this.updateFileList();
        this.showToast('File removed from installation queue', 'success');
    }

    clearFiles() {
        this.files = [];
        this.updateFileList();
        this.showToast('Installation queue cleared', 'success');
    }

    async startInstallation() {
        if (this.files.length === 0) {
            this.showToast('No files to install', 'error');
            return;
        }

        if (this.isInstalling) {
            this.showToast('Installation already in progress', 'warning');
            return;
        }

        this.isInstalling = true;
        this.showProgressSection();

        try {
            const installType = document.querySelector('input[name="install-location"]:checked').value;
            const enabledTypes = this.getEnabledFileTypes();

            let password = null;
            if (installType === 'system') {
                password = await this.requestPassword();
                if (!password) {
                    this.showToast('Installation cancelled - password required for system installation', 'warning');
                    this.isInstalling = false;
                    this.hideProgressSection();
                    return;
                }
            }

            const results = [];
            let completed = 0;

            for (const file of this.files) {
                const fileType = this.getFileType(this.getFileExtension(file.name));
                
                if (!enabledTypes[fileType]) {
                    this.addProgressLog(`Skipping ${file.name} - file type disabled`, 'warning');
                    completed++;
                    this.updateProgress(completed, this.files.length);
                    continue;
                }

                this.addProgressLog(`Installing ${file.name}...`);

                try {
                    const result = await this.installFile(file, installType, password);
                    results.push(result);
                    
                    if (result.success) {
                        if (fileType === 'pkg') {
                            this.addProgressLog(`✅ ${file.name} installed using macOS installer`, 'success');
                            if (result.details && result.details.length > 0) {
                                this.addProgressLog(`  └─ Detected ${result.details.length} installed items:`, 'success');
                                result.details.forEach(detail => {
                                    this.addProgressLog(`     • ${detail.filename} (${detail.file_type})`, 'success');
                                });
                            } else if (result.installed_count > 1) {
                                this.addProgressLog(`  └─ ${result.installed_count} items installed`, 'success');
                            }
                            if (result.message) {
                                this.addProgressLog(`  └─ ${result.message}`, 'info');
                            }
                        } else {
                            this.addProgressLog(`✅ ${file.name} installed to ${result.file_type} folder`, 'success');
                        }
                    } else {
                        this.addProgressLog(`❌ Failed to install ${file.name}: ${result.error}`, 'error');
                        if (result.installer_output) {
                            this.addProgressLog(`  └─ Installer output: ${result.installer_output}`, 'warning');
                        }
                        if (result.installer_stderr) {
                            this.addProgressLog(`  └─ Installer errors: ${result.installer_stderr}`, 'error');
                        }
                        if (result.log_file) {
                            this.addProgressLog(`  └─ Debug log saved to: ${result.log_file}`, 'info');
                        }
                    }
                } catch (error) {
                    const errorResult = {
                        filename: file.name,
                        success: false,
                        error: error.message
                    };
                    results.push(errorResult);
                    this.addProgressLog(`❌ Error installing ${file.name}: ${error.message}`, 'error');
                }

                completed++;
                this.updateProgress(completed, this.files.length);
            }

            this.showResults(results);
            this.showToast('Installation completed', 'success');
            
            // Always show log file location
            if (this.currentLogFile) {
                this.addProgressLog(`📋 Complete debug log saved to: ${this.currentLogFile}`, 'info');
            }

        } catch (error) {
            this.addProgressLog(`❌ Installation failed: ${error.message}`, 'error');
            this.showToast('Installation failed', 'error');
        } finally {
            this.isInstalling = false;
        }
    }

    getEnabledFileTypes() {
        return {
            component: document.getElementById('install-component').checked,
            vst: document.getElementById('install-vst').checked,
            vst3: document.getElementById('install-vst3').checked,
            aax: document.getElementById('install-aax').checked,
            app: document.getElementById('install-app').checked,
            pkg: document.getElementById('install-pkg').checked
        };
    }

    async installFile(file, installType, password) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('install_type', installType);
        if (password) {
            formData.append('password', password);
        }

        const response = await fetch(`http://localhost:${this.backendPort}/api/install`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Installation failed');
        }

        return result;
    }

    async requestPassword() {
        return new Promise((resolve) => {
            // Set up the response handler first
            window.handleNativeResponse = (response) => {
                if (response.action === 'passwordResponse') {
                    // Clean up the handler
                    delete window.handleNativeResponse;
                    resolve(response.password || null);
                }
            };

            // Try different ways to access the native bridge
            if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.maestroNative) {
                // WKWebView message handler
                window.webkit.messageHandlers.maestroNative.postMessage({
                    action: 'requestPassword'
                });
            } else if (window.maestroNative) {
                // Alternative native bridge
                window.maestroNative.postMessage({
                    action: 'requestPassword'
                });
            } else {
                // Fallback for testing in browser
                delete window.handleNativeResponse;
                const password = prompt('Enter administrator password:');
                resolve(password);
            }
        });
    }

    showProgressSection() {
        document.getElementById('progressSection').style.display = 'block';
        document.getElementById('resultsSection').style.display = 'none';
        this.updateProgress(0, this.files.length);
        document.getElementById('progressLog').innerHTML = '';
    }

    hideProgressSection() {
        document.getElementById('progressSection').style.display = 'none';
    }

    updateProgress(completed, total) {
        const percentage = Math.round((completed / total) * 100);
        document.getElementById('progressFill').style.width = percentage + '%';
        document.getElementById('progressText').textContent = percentage + '%';
    }

    addProgressLog(message, type = 'info') {
        const progressLog = document.getElementById('progressLog');
        const logEntry = document.createElement('p');
        logEntry.className = type;
        logEntry.textContent = message;
        progressLog.appendChild(logEntry);
        progressLog.scrollTop = progressLog.scrollHeight;
    }

    showResults(results) {
        document.getElementById('progressSection').style.display = 'none';
        document.getElementById('resultsSection').style.display = 'block';

        const resultsContent = document.getElementById('resultsContent');
        resultsContent.innerHTML = '';

        results.forEach(result => {
            const resultItem = document.createElement('div');
            resultItem.className = `result-item ${result.success ? 'success' : 'error'}`;
            
            const icon = result.success ? '✅' : '❌';
            const message = result.success ? 
                `${result.filename} installed successfully` : 
                `${result.filename}: ${result.error}`;

            resultItem.innerHTML = `
                <span style="margin-right: 1rem;">${icon}</span>
                <span>${message}</span>
            `;

            resultsContent.appendChild(resultItem);
        });
    }

    resetApp() {
        this.files = [];
        this.isInstalling = false;
        this.updateFileList();
        document.getElementById('progressSection').style.display = 'none';
        document.getElementById('resultsSection').style.display = 'none';
        document.getElementById('actionSection').style.display = 'none';
        this.showToast('Ready for new installation', 'success');
    }

    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        toastContainer.appendChild(toast);

        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 4000);
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.maestroApp = new MaestroApp();
    
    // Log Modal Functions
    const logModal = document.getElementById('logModal');
    const logFileInfoSpan = document.getElementById('logFileInfo');
    const logContentPre = document.getElementById('logContent');

    async function fetchLogInfo() {
        logFileInfoSpan.textContent = 'Loading log info...';
        if (!window.maestroApp || !window.maestroApp.backendPort) {
            logFileInfoSpan.textContent = 'Error: Backend not connected.';
            return;
        }
        try {
            const response = await fetch(`http://localhost:${window.maestroApp.backendPort}/api/log-info`);
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            const data = await response.json();
            logFileInfoSpan.textContent = `Path: ${data.log_file || 'N/A'} | Size: ${data.log_size_human || 'N/A'} | Exists: ${data.log_exists ? 'Yes' : 'No'}`;
        } catch (error) {
            logFileInfoSpan.textContent = `Error fetching log info: ${error.message}`;
            console.error('Error fetching log info:', error);
        }
    }

    async function fetchLogContent() {
        logContentPre.textContent = 'Loading log content...';
        if (!window.maestroApp || !window.maestroApp.backendPort) {
            logContentPre.textContent = 'Error: Backend not connected.';
            return;
        }
        try {
            const response = await fetch(`http://localhost:${window.maestroApp.backendPort}/api/log-content`);
            if (!response.ok) {
                if (response.status === 404) {
                    logContentPre.textContent = 'Log file not found or empty. Install some files to generate logs.';
                } else {
                    throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
                }
            } else {
                const text = await response.text();
                logContentPre.textContent = text || 'Log file is empty.';
            }
        } catch (error) {
            logContentPre.textContent = `Error fetching log content: ${error.message}`;
            console.error('Error fetching log content:', error);
        }
    }

    function openLogModal_internal() {
        logModal.style.display = 'flex';
        fetchLogInfo();
        fetchLogContent();
    }
    // Expose openLogModal globally for native menu access AND for any existing debug functions
    window.openLogModal = openLogModal_internal;

    function closeLogModal_internal() {
        logModal.style.display = 'none';
    }

    async function copyLogToClipboard_internal() {
        try {
            await navigator.clipboard.writeText(logContentPre.textContent);
            window.maestroApp.showToast('Log copied to clipboard!', 'success');
        } catch (err) {
            console.error('Failed to copy log: ', err);
            window.maestroApp.showToast('Failed to copy log. See console.', 'error');
        }
    }

    // Event Listeners for Log Modal
    document.getElementById('closeLogModal').addEventListener('click', closeLogModal_internal);
    document.getElementById('closeLogModalBtn').addEventListener('click', closeLogModal_internal);
    document.getElementById('refreshLogBtn').addEventListener('click', () => {
        fetchLogInfo();
        fetchLogContent();
    });
    document.getElementById('copyLogBtn').addEventListener('click', copyLogToClipboard_internal);

    logModal.addEventListener('click', (event) => {
        if (event.target === logModal) { // Clicked on the overlay itself
            closeLogModal_internal();
        }
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && logModal.style.display === 'flex') {
            closeLogModal_internal();
        }
    });

    // Expose debug functions (if they were intended to be global)
    // These are kept from the original script but might be removed if not needed.
    window.testBackendConnection = async function(port) { // Made it a global function
        if (port) {
            window.maestroApp.backendPort = port;
        }
        console.log('🔍 Testing backend connection on port:', window.maestroApp.backendPort);
        try {
            const response = await fetch(`http://localhost:${window.maestroApp.backendPort}/api/debug`);
            const data = await response.json();
            console.log('✅ Backend connection successful:', data);
            return data;
        } catch (error) {
            console.error('❌ Backend connection failed:', error);
            return null;
        }
    };

    window.setBackendPort = function(port) { // Made it a global function
        window.maestroApp.backendPort = port;
        window.MAESTRO_BACKEND_PORT = port; // If this global var is still used
        console.log('🔧 Backend port manually set to:', port);
    };
});


// Handle native responses (kept from original script, might need review based on actual native calls)
window.handleNativeResponse = function(response) {
    // This will be overridden by specific request handlers like in requestPassword()
    console.log('Global Native response handler:', response);
};

// Note: The original script had multiple DOMContentLoaded listeners and global function definitions.
// This refactoring attempts to consolidate log modal logic within one DOMContentLoaded listener.
// The MaestroApp class and its methods are assumed to be defined before this block.
// Ensure that `window.maestroApp` is initialized before these global functions or modal listeners are fully operational if they depend on it.
// The current structure where `window.maestroApp = new MaestroApp();` is at the top of the listener should be fine.
