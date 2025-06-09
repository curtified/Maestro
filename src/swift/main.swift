import Cocoa
import WebKit
import Foundation

class MaestroApp: NSObject, NSApplicationDelegate, WKUIDelegate, WKNavigationDelegate, WKScriptMessageHandler {
    var window: NSWindow!
    var webView: WKWebView!
    var backendProcess: Process?

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
        let windowSize = NSSize(width: 1200, height: 800)
        window = NSWindow(
            contentRect: NSRect(origin: .zero, size: windowSize),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Maestro - Audio Plugin Installer"
        window.center()
        window.makeKeyAndOrderFront(nil)
        window.minSize = NSSize(width: 800, height: 600)
    }

    private func setupWebView() {
        let config = WKWebViewConfiguration()
        let contentController = WKUserContentController()
        contentController.add(self, name: "maestroNative")
        config.userContentController = contentController
        
        // Allow loading local files
        config.preferences.setValue(true, forKey: "allowFileAccessFromFileURLs")

        webView = WKWebView(frame: window.contentView!.bounds, configuration: config)
        webView.uiDelegate = self
        webView.navigationDelegate = self
        webView.autoresizingMask = [.width, .height]
        window.contentView?.addSubview(webView)
        
        loadWebInterface()
    }

    private func loadWebInterface() {
        guard let resourceURL = Bundle.main.resourceURL else {
            showAlert(title: "Fatal Error", message: "Could not find application resources.")
            return
        }
        let webRootPath = resourceURL.appendingPathComponent("web")
        let indexPath = webRootPath.appendingPathComponent("index.html")

        if FileManager.default.fileExists(atPath: indexPath.path) {
            webView.loadFileURL(indexPath, allowingReadAccessTo: webRootPath)
        } else {
            showAlert(title: "Fatal Error", message: "Web interface not found at \(indexPath.path)")
        }
    }

    private func setupMenuBar() {
        let mainMenu = NSMenu()
        
        // App Menu
        let appMenuItem = NSMenuItem()
        mainMenu.addItem(appMenuItem)
        
        let appMenu = NSMenu()
        appMenuItem.submenu = appMenu
        
        appMenu.addItem(NSMenuItem(title: "About Maestro", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: ""))
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(NSMenuItem(title: "Quit Maestro", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        
        // Logs Menu
        let logsMenuItem = NSMenuItem()
        mainMenu.addItem(logsMenuItem)
        
        let logsMenu = NSMenu()
        logsMenuItem.submenu = logsMenu
        logsMenu.addItem(NSMenuItem(title: "View Logs", action: #selector(viewLogs), keyEquivalent: ""))
        
        NSApp.mainMenu = mainMenu
    }

    @objc func viewLogs() {
        let logFilePath = "~/Library/Logs/MaestroInstaller/Maestro_Install.log"
        let expandedLogFilePath = NSString(string: logFilePath).expandingTildeInPath
        
        if FileManager.default.fileExists(atPath: expandedLogFilePath) {
            NSWorkspace.shared.openFile(expandedLogFilePath, withApplication: "Console")
        } else {
            showAlert(title: "Log File Not Found", message: "The log file does not exist. Try installing a file to generate logs.")
        }
    }

    private func startBackendServer() {
        guard let backendPath = Bundle.main.path(forResource: "MaestroBackend", ofType: nil, inDirectory: "MaestroBackend") else {
            showAlert(title: "Backend Error", message: "Backend executable not found in the app bundle.")
            createEmergencyLogFile(message: "Backend executable not found.")
            return
        }

        guard FileManager.default.isExecutableFile(atPath: backendPath) else {
            showAlert(title: "Backend Error", message: "Backend is not an executable file.")
            createEmergencyLogFile(message: "Backend is not an executable file.")
            return
        }

        killExistingBackendProcesses()

        let lockFile = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/Maestro/backend.lock")
        try? FileManager.default.removeItem(at: lockFile)

        var environment = ProcessInfo.processInfo.environment
        environment["PYTHONUNBUFFERED"] = "1"
        environment["LC_CTYPE"] = "UTF-8"
        
        let process = Process()
        process.executableURL = URL(fileURLWithPath: backendPath)
        process.environment = environment

        let outputPipe = Pipe()
        let errorPipe = Pipe()
        process.standardOutput = outputPipe
        process.standardError = errorPipe

        outputPipe.fileHandleForReading.readabilityHandler = { fileHandle in
            if let output = String(data: fileHandle.availableData, encoding: .utf8), !output.isEmpty {
                print("[Backend STDOUT]: \(output.trimmingCharacters(in: .whitespacesAndNewlines))")
            }
        }
        errorPipe.fileHandleForReading.readabilityHandler = { fileHandle in
            if let output = String(data: fileHandle.availableData, encoding: .utf8), !output.isEmpty {
                print("[Backend STDERR]: \(output.trimmingCharacters(in: .whitespacesAndNewlines))")
            }
        }

        do {
            try process.run()
            backendProcess = process
            print("Backend process started with PID: \(process.processIdentifier)")
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { [weak self] in
                self?.checkBackendHealth()
            }
        } catch {
            showAlert(title: "Backend Error", message: "Failed to start backend: \(error.localizedDescription)")
            createEmergencyLogFile(message: "Failed to start backend: \(error.localizedDescription)")
        }
    }

    private func checkBackendHealth() {
        let healthURL = URL(string: "http://127.0.0.1:52000/api/health")!
        let task = URLSession.shared.dataTask(with: healthURL) { [weak self] data, response, error in
            DispatchQueue.main.async {
                if let error = error {
                    print("Backend health check failed: \(error.localizedDescription)")
                    self?.showAlert(title: "Connection Error", message: "Unable to connect to the backend service. Please restart the app. Error: \(error.localizedDescription)")
                    return
                }

                if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                    print("Backend health check successful.")
                    self?.updateFrontendWithBackendPort(52000)
                } else {
                    let statusCode = (response as? HTTPURLResponse)?.statusCode ?? -1
                    print("Backend health check failed with status: \(statusCode)")
                    self?.showAlert(title: "Backend Error", message: "Backend service responded with status code: \(statusCode).")
                }
            }
        }
        task.resume()
    }
    
    private func updateFrontendWithBackendPort(_ port: Int) {
        // This is a failsafe; the JS should already know the port.
        // We can use this to trigger a ready event in the future.
        let script = "console.log('Swift confirmed backend port \(port) is active.');"
        webView.evaluateJavaScript(script, completionHandler: nil)
    }

    private func killExistingBackendProcesses() {
        let processName = "MaestroBackend"
        let task = Process()
        task.launchPath = "/usr/bin/killall"
        task.arguments = [processName]
        task.launch()
        task.waitUntilExit()
        if task.terminationStatus == 0 {
            print("Terminated existing backend processes.")
        }
    }
    
    private func terminateBackend() {
        if let process = backendProcess, process.isRunning {
            process.terminate()
            print("Terminated backend process.")
        }
        backendProcess = nil
    }

    private func showAlert(title: String, message: String) {
        DispatchQueue.main.async {
            let alert = NSAlert()
            alert.alertStyle = .critical
            alert.messageText = title
            alert.informativeText = message
            alert.runModal()
        }
    }

    private func createEmergencyLogFile(message: String) {
        guard let logsDirectory = FileManager.default.urls(for: .libraryDirectory, in: .userDomainMask).first?.appendingPathComponent("Logs/MaestroInstaller") else { return }
        try? FileManager.default.createDirectory(at: logsDirectory, withIntermediateDirectories: true, attributes: nil)
        let logURL = logsDirectory.appendingPathComponent("maestro_swift_emergency.log")
        let logContent = """
        \(Date()) - CRITICAL ERROR
        Message: \(message)
        OS: \(ProcessInfo.processInfo.operatingSystemVersionString)
        App Path: \(Bundle.main.bundlePath)
        
        """
        
        if let fileHandle = try? FileHandle(forWritingTo: logURL) {
            defer { fileHandle.closeFile() }
            fileHandle.seekToEndOfFile()
            if let data = logContent.data(using: .utf8) {
                fileHandle.write(data)
            }
        } else {
            try? logContent.data(using: .utf8)?.write(to: logURL)
        }
    }

    // MARK: - WKScriptMessageHandler
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        // Not used in this simplified version, but kept for future native interactions.
        print("Received message from web view: \(message.name)")
    }
    
    // MARK: - WKUIDelegate (for JS alerts)
    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        let alert = NSAlert()
        alert.messageText = "Maestro Notification"
        alert.informativeText = message
        alert.addButton(withTitle: "OK")
        alert.runModal()
        completionHandler()
    }
}

// MARK: - Main App Entry
let app = NSApplication.shared
let delegate = MaestroApp()
app.delegate = delegate
app.run() 