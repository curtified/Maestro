import Cocoa
import WebKit
import Foundation
import Security

class MaestroApp: NSObject, NSApplicationDelegate, WKUIDelegate, WKNavigationDelegate, WKScriptMessageHandler {
    var window: NSWindow!
    var webView: WKWebView!
    var backendProcess: Process?
    var backendPort: Int = 0
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        setupWindow()
        setupWebView()
        setupMenuBar()
        startBackendServer()
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        terminateBackend()
    }
    
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
    
    private func setupWindow() {
        let screenSize = NSScreen.main?.frame.size ?? NSSize(width: 1200, height: 800)
        let windowSize = NSSize(width: min(1200, screenSize.width * 0.8), 
                               height: min(900, screenSize.height * 0.8))
        
        window = NSWindow(
            contentRect: NSRect(origin: .zero, size: windowSize),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        
        window.title = "Maestro - Audio Plugin Installer"
        window.center()
        window.makeKeyAndOrderFront(nil)
        
        // Set minimum size
        window.minSize = NSSize(width: 800, height: 600)
    }
    
    private func setupWebView() {
        let config = WKWebViewConfiguration()
        
        // Enable file access
        config.preferences.setValue(true, forKey: "allowFileAccessFromFileURLs")
        config.setValue(true, forKey: "allowUniversalAccessFromFileURLs")
        
        // Add message handler for native communication
        let contentController = WKUserContentController()
        contentController.add(self, name: "maestroNative")
        config.userContentController = contentController
        
        webView = WKWebView(frame: window.contentView!.bounds, configuration: config)
        webView.uiDelegate = self
        webView.navigationDelegate = self
        webView.autoresizingMask = [.width, .height]
        
        window.contentView?.addSubview(webView)
        
        // Load the web interface
        loadWebInterface()
    }
    
    private func loadWebInterface() {
        guard let resourceURL = Bundle.main.resourceURL else {
            showAlert("Error", "Could not find application resources URL.")
            return
        }
        // Path to web content inside the .app bundle
        // Maestro.app/Contents/Resources/web/index.html
        let webRootPath = resourceURL.appendingPathComponent("web")
        let indexPath = webRootPath.appendingPathComponent("index.html")

        if FileManager.default.fileExists(atPath: indexPath.path) {
            // Allow read access to the 'web' directory.
            webView.loadFileURL(indexPath, allowingReadAccessTo: webRootPath)
            print("Attempting to load web interface from: \(indexPath)")
        } else {
            showAlert("Error", "Could not find web interface at \(indexPath.path)")
            print("Error: Web interface not found at \(indexPath.path)")
        }
    }
    
    private func setupMenuBar() {
        let mainMenu = NSMenu()
        
        // App menu
        let appMenuItem = NSMenuItem()
        mainMenu.addItem(appMenuItem)
        let appMenu = NSMenu()
        appMenuItem.submenu = appMenu
        appMenu.addItem(NSMenuItem(title: "About Maestro", action: nil, keyEquivalent: ""))
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(NSMenuItem(title: "Quit Maestro", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        
        // Local Data menu
        let localDataMenuItem = NSMenuItem(title: "Local Data", action: nil, keyEquivalent: "")
        mainMenu.addItem(localDataMenuItem)
        let localDataMenu = NSMenu(title: "Local Data")
        localDataMenuItem.submenu = localDataMenu
        
        let viewLogItem = NSMenuItem(title: "View Log", action: #selector(viewLogAction), keyEquivalent: "l")
        viewLogItem.target = self
        localDataMenu.addItem(viewLogItem)
        
        let openLogFolderItem = NSMenuItem(title: "Open Log Folder", action: #selector(openLogFolderAction), keyEquivalent: "L")
        openLogFolderItem.keyEquivalentModifierMask = [.command, .shift]
        openLogFolderItem.target = self
        localDataMenu.addItem(openLogFolderItem)
        
        NSApplication.shared.mainMenu = mainMenu
    }
    
    @objc private func viewLogAction() {
        // Send message to web interface to open log modal
        let jsCode = "if (window.openLogModal) { window.openLogModal(); }"
        webView.evaluateJavaScript(jsCode) { _, error in
            if let error = error {
                print("Error opening log modal: \(error)")
            }
        }
    }
    
    @objc private func openLogFolderAction() {
        // Path to logs consistent with Python backend logging
        // ~/Library/Logs/MaestroInstaller/
        guard let logsDirectory = FileManager.default.urls(for: .libraryDirectory, in: .userDomainMask).first?
                .appendingPathComponent("Logs/MaestroInstaller") else {
            showAlert("Error", "Could not determine logs directory.")
            return
        }
        
        if !FileManager.default.fileExists(atPath: logsDirectory.path) {
            try? FileManager.default.createDirectory(at: logsDirectory, withIntermediateDirectories: true, attributes: nil)
        }
        
        NSWorkspace.shared.open(logsDirectory)
        print("Opened log folder: \(logsDirectory.path)")
    }
    
    private func createEmergencyLogFile() {
        // Create an emergency log file if backend fails to start
        // Store Swift-specific emergency logs in the same parent directory as Python logs.
        guard let logsDirectory = FileManager.default.urls(for: .libraryDirectory, in: .userDomainMask).first?
                .appendingPathComponent("Logs/MaestroInstaller") else {
            print("Error: Could not determine logs directory for emergency log.")
            return
        }
        
        do {
            try FileManager.default.createDirectory(at: logsDirectory, withIntermediateDirectories: true, attributes: nil)
            
            let dateFormatter = DateFormatter()
            dateFormatter.dateFormat = "yyyyMMdd_HHmmss"
            let timestamp = dateFormatter.string(from: Date())
            
            let emergencyLogURL = logsDirectory.appendingPathComponent("maestro_swift_emergency_\(timestamp).log")
            
            let logContent = """
# Maestro Swift Emergency Log - Backend Failed to Start or Other Critical Swift Error
# Created: \(Date())
# Error: See details below. This log is from the Swift component.

\(Date()) - ERROR - 🚨 MAESTRO SWIFT encountered a critical issue.
\(Date()) - ERROR - This emergency log was created by the Swift frontend.
\(Date()) - ERROR - Possible causes for backend start failure:
\(Date()) - ERROR -   1. Bundled backend executable not found or not runnable.
\(Date()) - ERROR -   2. Permissions issues with the bundled backend.
\(Date()) - ERROR -   3. PyInstaller bundle is incomplete or corrupted.
\(Date()) - INFO - 📱 macOS Version: \(ProcessInfo.processInfo.operatingSystemVersionString)
\(Date()) - INFO - 🎯 App Bundle: \(Bundle.main.bundlePath)
\(Date()) - INFO - 📦 Resource URL: \(Bundle.main.resourceURL?.path ?? "Unknown")
\(Date()) - INFO - Please check the Console app for more detailed error messages from the app.
\(Date()) - INFO - Also check Maestro_Install.log in this directory for Python backend logs.
"""
            
            FileManager.default.createFile(atPath: emergencyLogURL.path, contents: logContent.data(using: .utf8), attributes: nil)
            print("Created Swift emergency log file: \(emergencyLogURL.path)")
        } catch {
            print("Failed to create Swift emergency log file: \(error)")
        }
    }

    private func startBackendServer() {
        guard let resourceURL = Bundle.main.resourceURL else {
            showAlert("Error", "Could not access application resources.")
            createEmergencyLogFile() // Log this critical Swift-side failure
            return
        }

        // Path to the bundled Python backend executable
        // Maestro.app/Contents/Resources/MaestroBackend/MaestroBackend
        let backendExecutablePath = resourceURL.appendingPathComponent("MaestroBackend/MaestroBackend")
        let backendDirectoryPath = resourceURL.appendingPathComponent("MaestroBackend")

        print("Looking for backend executable at: \(backendExecutablePath.path)")

        guard FileManager.default.isExecutableFile(atPath: backendExecutablePath.path) else {
            showAlert("Error", "Backend executable not found or not executable at: \(backendExecutablePath.path)")
            createEmergencyLogFile()
            return
        }
        
        backendProcess = Process()
        backendProcess?.executableURL = backendExecutablePath
        // No arguments needed if PyInstaller bundles everything correctly and the script knows its relative paths
        backendProcess?.arguments = []
        
        // Set the current working directory for the backend process to its own directory inside Resources
        // This helps if the Python script uses relative paths for any resources it might load itself (unlikely for this backend but good practice)
        backendProcess?.currentDirectoryURL = backendDirectoryPath
        
        // Set environment variables
        var environment = ProcessInfo.processInfo.environment
        // PYTHONPATH might not be strictly necessary for a PyInstaller --onedir bundle
        // but setting it to the Resources/MaestroBackend might help in some cases if it looks for modules.
        // For a fully bundled app, internal paths should be resolved by PyInstaller.
        // environment["PYTHONPATH"] = backendDirectoryPath.path
        environment["PYTHONUNBUFFERED"] = "1" // Keep this for immediate output
        // Potentially set LC_CTYPE, LANG to prevent Unicode errors with subprocesses from Python
        environment["LC_CTYPE"] = "UTF-8"
        environment["LANG"] = "en_US.UTF-8"
        backendProcess?.environment = environment
        
        // Capture output to get the port
        let outputPipe = Pipe()
        let errorPipe = Pipe()
        backendProcess?.standardOutput = outputPipe
        backendProcess?.standardError = errorPipe
        
        do {
            try backendProcess?.run()
            print("Backend process started successfully")
            
            // Monitor the process to detect if it exits unexpectedly
            DispatchQueue.global().async {
                self.backendProcess?.waitUntilExit()
                let exitCode = self.backendProcess?.terminationStatus ?? -1
                if exitCode != 0 {
                    print("Backend process exited with code: \(exitCode)")
                    DispatchQueue.main.async {
                        self.createEmergencyLogFile()
                    }
                }
            }
            
            // Read the port from backend output
            DispatchQueue.global().async {
                let outputData = outputPipe.fileHandleForReading.readData(ofLength: 1024)
                let errorData = errorPipe.fileHandleForReading.readData(ofLength: 1024)
                
                if let output = String(data: outputData, encoding: .utf8), !output.isEmpty {
                    print("Backend output: \(output)")
                    self.parseBackendOutput(output)
                }
                
                if let error = String(data: errorData, encoding: .utf8), !error.isEmpty {
                    print("Backend error: \(error)")
                    // If we see errors, create an emergency log
                    DispatchQueue.main.async {
                        self.createEmergencyLogFile()
                    }
                }
            }
            
        } catch {
            print("Failed to start backend: \(error)")
            createEmergencyLogFile()
            showAlert("Error", "Failed to start backend server: \(error)")
        }
    }
    
    private func parseBackendOutput(_ output: String) {
        let lines = output.components(separatedBy: .newlines)
        for line in lines {
            if line.hasPrefix("MAESTRO_BACKEND_PORT=") {
                let portString = String(line.dropFirst("MAESTRO_BACKEND_PORT=".count))
                if let port = Int(portString.trimmingCharacters(in: .whitespacesAndNewlines)) {
                    self.backendPort = port
                    
                    DispatchQueue.main.async {
                        // Inject port into web interface
                        print("🔗 Injecting backend port \(port) into web interface")
                        let jsCode = """
                            if (window.maestroApp) {
                                window.maestroApp.backendPort = \(port);
                                console.log('✅ Backend port set to:', \(port));
                            } else {
                                console.log('⚠️ maestroApp not ready, storing port globally');
                                window.MAESTRO_BACKEND_PORT = \(port);
                            }
                        """
                        self.webView.evaluateJavaScript(jsCode) { result, error in
                            if let error = error {
                                print("❌ Error injecting port: \(error)")
                            } else {
                                print("✅ Port injection completed")
                            }
                        }
                    }
                    break
                }
            }
        }
    }
    
    private func terminateBackend() {
        backendProcess?.terminate()
        backendProcess = nil
    }
    
    private func showAlert(_ title: String, _ message: String) {
        DispatchQueue.main.async {
            let alert = NSAlert()
            alert.alertStyle = .warning
            alert.messageText = title
            alert.informativeText = message
            alert.addButton(withTitle: "OK")
            alert.runModal()
        }
    }
    
    // MARK: - WKScriptMessageHandler
    
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == "maestroNative",
              let messageBody = message.body as? [String: Any],
              let action = messageBody["action"] as? String else {
            return
        }
        
        switch action {
        case "requestPassword":
            requestPasswordDialog()
        case "openLogFolder":
            openLogFolderAction() // Ensure this calls the updated method
        default:
            break
        }
    }
    
    // requestPasswordDialog remains unchanged from previous modifications
    private func requestPasswordDialog() {
        DispatchQueue.main.async {
            let alert = NSAlert()
            alert.messageText = "Administrator Password Required"
            alert.informativeText = "Installing to system folders requires administrator privileges."
            alert.addButton(withTitle: "OK")
            alert.addButton(withTitle: "Cancel")
            
            let passwordField = NSSecureTextField(frame: NSRect(x: 0, y: 0, width: 300, height: 24))
            passwordField.placeholderString = "Enter password"
            alert.accessoryView = passwordField
            
            let response = alert.runModal()
            
            var password: String? = nil
            if response == .alertFirstButtonReturn {
                password = passwordField.stringValue.isEmpty ? nil : passwordField.stringValue
            }
            
            // Send response back to web interface
            let jsCode = """
                if (window.handleNativeResponse) {
                    window.handleNativeResponse({
                        action: 'passwordResponse',
                        password: \(password != nil ? "\"\(password!)\"" : "null")
                    });
                }
            """
            
            self.webView.evaluateJavaScript(jsCode) { _, error in
                if let error = error {
                    print("Error sending password response: \(error)")
                }
            }

            // Clear password from memory
            passwordField.stringValue = ""
            password = nil
            // Forcing deallocation of alert and passwordField immediately is tricky
            // as they are local to this async block. Swift ARC should handle it once
            // the block finishes, but clearing the content is the most direct control.
            print("Password field and local variable cleared.")
        }
    }
    
    // openLogFolder is a duplicate of openLogFolderAction - this one will be removed by the diff if not careful.
    // The previous diff already modified openLogFolderAction correctly.
    // The search block should target the old openLogFolder if it exists, or ensure only openLogFolderAction is present.
    // Based on the provided code, openLogFolder is only called by userContentController, so that call should be openLogFolderAction.
    // The diff will replace the definition of openLogFolderAction and createEmergencyLogFile.
    // The openLogFolder method below is the old one, which is not directly called by menu anymore.
    // Let's ensure the `message.body` handler for "openLogFolder" calls the correct one.
    // It already calls `openLogFolder()` which needs to be updated or removed if `openLogFolderAction()` is the sole one.
    // The diff changes `openLogFolderAction` and `createEmergencyLogFile`.
    // The `openLogFolder` method called by `userContentController` should be `openLogFolderAction`.
    // The existing code has:
    // case "openLogFolder": openLogFolder()
    // This should become:
    // case "openLogFolder": openLogFolderAction()
    // This is handled in this diff block itself.

    // The definition of `openLogFolder()` that was previously here (and identical to the old `openLogFolderAction`)
    // will be effectively replaced by the changes to `openLogFolderAction` and `createEmergencyLogFile`.
    // No specific removal block for an old `openLogFolder()` is needed if its content is being replaced via `openLogFolderAction`.
    
    // MARK: - WKUIDelegate
    
    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        let alert = NSAlert()
        alert.alertStyle = .informational
        alert.messageText = "Maestro"
        alert.informativeText = message
        alert.addButton(withTitle: "OK")
        alert.runModal()
        completionHandler()
    }
    
    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let alert = NSAlert()
        alert.alertStyle = .informational
        alert.messageText = "Maestro"
        alert.informativeText = message
        alert.addButton(withTitle: "OK")
        alert.addButton(withTitle: "Cancel")
        let response = alert.runModal()
        completionHandler(response == .alertFirstButtonReturn)
    }
}

// MARK: - Main Application Entry Point

let app = NSApplication.shared
let delegate = MaestroApp()
app.delegate = delegate
app.run() 