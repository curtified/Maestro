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
    // Expose openLogModal globally for native menu access
    window.openLogModal = openLogModal;
    // Expose debug functions
    window.testBackendConnection = testBackendConnection;
    window.setBackendPort = setBackendPort;
});

// Debug function to test backend connection
async function testBackendConnection(port) {
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
}

// Function to manually set backend port
function setBackendPort(port) {
    window.maestroApp.backendPort = port;
    window.MAESTRO_BACKEND_PORT = port;
    console.log('🔧 Backend port manually set to:', port);
}

// Handle native responses
window.handleNativeResponse = function(response) {
    // This will be overridden by specific request handlers
    console.log('Native response:', response);
};

// Setup modal handlers when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Modal close buttons
    document.getElementById('closeLogModal').addEventListener('click', closeLogModal);
    document.getElementById('closeLogModalBtn').addEventListener('click', closeLogModal);

    // Refresh log button
    document.getElementById('refreshLogBtn').addEventListener('click', refreshLogContent);

    // Copy log button
    document.getElementById('copyLogBtn').addEventListener('click', copyLogToClipboard);

    // Close modal when clicking outside
    document.getElementById('logModal').addEventListener('click', (e) => {
        if (e.target.id === 'logModal') {
            closeLogModal();
        }
    });

    // Close modal with Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && document.getElementById('logModal').style.display !== 'none') {
            closeLogModal();
        }
    });
});

async function openLogModal() {
    document.getElementById('logModal').style.display = 'flex';
    document.getElementById('logContent').textContent = 'Loading log...';
    
    try {
        await refreshLogContent();
    } catch (error) {
        document.getElementById('logContent').textContent = `Error loading log: ${error.message}`;
        document.getElementById('logFileInfo').textContent = 'Error loading log information';
    }
}

async function refreshLogContent() {
    try {
        const logInfo = await getLogInfo();
        const logContent = await getLogContent();
        
        document.getElementById('logFileInfo').textContent = `Log file: ${logInfo.filename || 'No log file found'}`;
        document.getElementById('logContent').textContent = logContent;
    } catch (error) {
        document.getElementById('logContent').textContent = `Error loading log: ${error.message}`;
        document.getElementById('logFileInfo').textContent = 'Error loading log information';
    }
}

async function getLogInfo() {
    try {
        const response = await fetch(`http://localhost:${window.maestroApp.backendPort}/api/log-info`);
        if (!response.ok) {
            throw new Error('Failed to get log info');
        }
        return await response.json();
    } catch (error) {
        console.error('Error getting log info:', error);
        return { filename: null, exists: false };
    }
}

async function getLogContent() {
    console.log('🔍 Attempting to fetch log content from port:', window.maestroApp.backendPort);
    
    if (!window.maestroApp.backendPort) {
        console.error('❌ Backend port not available');
        return 'Error: Backend port not available. Backend may not have started successfully.';
    }
    
    try {
        const url = `http://localhost:${window.maestroApp.backendPort}/api/log-content`;
        console.log('🌐 Fetching log from:', url);
        
        const response = await fetch(url);
        console.log('📡 Response status:', response.status);
        
        if (!response.ok) {
            if (response.status === 404) {
                return 'No log file found. Install some files to generate logs.';
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const text = await response.text();
        console.log('✅ Log content retrieved, length:', text.length);
        return text || 'Log file is empty.';
    } catch (error) {
        console.error('❌ Error getting log content:', error);
        return `Error loading log: ${error.message}\n\nDebugging info:\n- Backend port: ${window.maestroApp.backendPort}\n- Error type: ${error.name}\n- Check browser console for more details`;
    }
}

function closeLogModal() {
    document.getElementById('logModal').style.display = 'none';
}



async function copyLogToClipboard() {
    try {
        const logContent = document.getElementById('logContent').textContent;
        await navigator.clipboard.writeText(logContent);
        maestroApp.showToast('Log copied to clipboard', 'success');
    } catch (error) {
        // Fallback for older browsers
        try {
            const textArea = document.createElement('textarea');
            textArea.value = document.getElementById('logContent').textContent;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            maestroApp.showToast('Log copied to clipboard', 'success');
        } catch (fallbackError) {
            maestroApp.showToast('Failed to copy log to clipboard', 'error');
        }
    }
}
