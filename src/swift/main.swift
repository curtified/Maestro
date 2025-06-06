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
        guard let resourcePath = Bundle.main.resourcePath else {
            showAlert("Error", "Could not find application resources")
            return
        }
        
        let indexPath = URL(fileURLWithPath: resourcePath).appendingPathComponent("index.html")
        
        if FileManager.default.fileExists(atPath: indexPath.path) {
            webView.loadFileURL(indexPath, allowingReadAccessTo: URL(fileURLWithPath: resourcePath))
        } else {
            showAlert("Error", "Could not find web interface files")
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
        let homeURL = FileManager.default.homeDirectoryForCurrentUser
        let logFolderURL = homeURL.appendingPathComponent("Maestro_Logs")
        
        if !FileManager.default.fileExists(atPath: logFolderURL.path) {
            try? FileManager.default.createDirectory(at: logFolderURL, withIntermediateDirectories: true)
        }
        
        NSWorkspace.shared.open(logFolderURL)
    }
    
    private func createEmergencyLogFile() {
        // Create an emergency log file if backend fails to start
        let homeURL = FileManager.default.homeDirectoryForCurrentUser
        let logFolderURL = homeURL.appendingPathComponent("Maestro_Logs")
        
        do {
            try FileManager.default.createDirectory(at: logFolderURL, withIntermediateDirectories: true)
            
            let dateFormatter = DateFormatter()
            dateFormatter.dateFormat = "yyyyMMdd_HHmmss"
            let timestamp = dateFormatter.string(from: Date())
            
            let emergencyLogURL = logFolderURL.appendingPathComponent("maestro_emergency_\(timestamp).log")
            
            let logContent = """
# Maestro Emergency Log - Backend Failed to Start
# Created: \(Date())
# Error: Backend process could not be started

\(Date()) - ERROR - 🚨 MAESTRO BACKEND FAILED TO START
\(Date()) - ERROR - This emergency log was created because the Python backend could not be started
\(Date()) - ERROR - Possible causes:
\(Date()) - ERROR -   1. Python virtual environment not found
\(Date()) - ERROR -   2. Missing Python dependencies (Flask, Flask-CORS)
\(Date()) - ERROR -   3. Python script execution permissions
\(Date()) - ERROR -   4. File path issues
\(Date()) - INFO - 📱 macOS Version: \(ProcessInfo.processInfo.operatingSystemVersionString)
\(Date()) - INFO - 🎯 App Bundle: \(Bundle.main.bundlePath)
\(Date()) - INFO - 📁 Resource Path: \(Bundle.main.resourcePath ?? "Unknown")
\(Date()) - INFO - Please check the Console app for more detailed error messages
"""
            
            FileManager.default.createFile(atPath: emergencyLogURL.path, contents: logContent.data(using: .utf8), attributes: nil)
            print("Created emergency log file: \(emergencyLogURL.path)")
        } catch {
            print("Failed to create emergency log file: \(error)")
        }
    }

    private func startBackendServer() {
        guard let resourcePath = Bundle.main.resourcePath else {
            createEmergencyLogFile()
            showAlert("Error", "Could not find Python backend")
            return
        }
        
        let backendPath = URL(fileURLWithPath: resourcePath).appendingPathComponent("maestro_backend.py")
        
        guard FileManager.default.fileExists(atPath: backendPath.path) else {
            createEmergencyLogFile()
            showAlert("Error", "Python backend not found at: \(backendPath.path)")
            return
        }
        
        backendProcess = Process()
        
        // Try to use virtual environment Python first, fallback to system Python
        let venvPythonPath = URL(fileURLWithPath: resourcePath).appendingPathComponent("venv/bin/python")
        if FileManager.default.fileExists(atPath: venvPythonPath.path) {
            print("Using virtual environment Python: \(venvPythonPath.path)")
            backendProcess?.executableURL = venvPythonPath
        } else {
            print("Virtual environment not found, using system Python")
            backendProcess?.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        }
        
        backendProcess?.arguments = [backendPath.path]
        backendProcess?.currentDirectoryURL = URL(fileURLWithPath: resourcePath)
        
        // Set environment variables
        var environment = ProcessInfo.processInfo.environment
        environment["PYTHONPATH"] = resourcePath
        environment["PYTHONUNBUFFERED"] = "1"
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
            openLogFolder()
        default:
            break
        }
    }
    
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
        }
    }
    
    private func openLogFolder() {
        let homeURL = FileManager.default.homeDirectoryForCurrentUser
        let logFolderURL = homeURL.appendingPathComponent("Maestro_Logs")
        
        if !FileManager.default.fileExists(atPath: logFolderURL.path) {
            try? FileManager.default.createDirectory(at: logFolderURL, withIntermediateDirectories: true)
        }
        
        NSWorkspace.shared.open(logFolderURL)
    }
    
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