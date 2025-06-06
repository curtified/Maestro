# Maestro - Professional Audio Plugin Installer

<div align="center">

![Maestro](src/web/assets/icon.png)

**A sophisticated macOS application for seamless audio plugin installation with a beautiful, modern interface**

[![macOS](https://img.shields.io/badge/platform-macOS-blue?logo=apple)](https://www.apple.com/macos/)
[![Swift](https://img.shields.io/badge/Swift-5.0+-orange?logo=swift)](https://swift.org/)
[![Python](https://img.shields.io/badge/Python-3.7+-green?logo=python)](https://python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

## 🎼 Overview

Maestro is a professional-grade audio plugin installer designed specifically for macOS. It provides a beautiful, intuitive graphical interface for installing audio plugins while giving users precise control over the installation process. Whether you're dealing with complex .pkg installers or direct plugin files, Maestro makes the process seamless and secure.

## ✨ Key Features

### 🎨 **Beautiful, Modern Interface**
- Dark theme with gradient backgrounds (#1a1a2e to #16213e)
- Intuitive drag-and-drop functionality
- Real-time progress tracking
- Native macOS dialogs and notifications

### 🔍 **Intelligent Package Analysis**
- Automatic .pkg file extraction and analysis
- Discovers all audio plugins within installers
- Plugin selection with detailed information
- Preview before installation

### 🎛️ **Comprehensive Plugin Support**
- **.pkg** - Installer packages
- **.component** - Audio Unit plugins
- **.vst** - VST 2.x plugins
- **.vst3** - VST 3.x plugins
- **.aax** - AAX (Pro Tools) plugins

### 🔐 **Secure Installation Process**
- User and system-wide installation options
- Automatic code signing of installed plugins
- Secure password handling for administrator privileges
- Safe temporary file management

### ⚡ **Advanced Features**
- Selective plugin installation from packages
- Real-time installation progress
- Detailed results reporting
- File association for double-click installation
- Native macOS integration

## 🏗️ Architecture

Maestro uses a hybrid architecture combining three main components:

### 1. **Swift Native Wrapper** (`src/swift/main.swift`)
- Lightweight macOS application shell
- WKWebView hosting for web interface
- Native dialog handling
- Background process management
- File association handling

### 2. **Python Backend Server** (`src/python/maestro_backend.py`)
- Flask-based HTTP server
- Package analysis and extraction
- Plugin installation logic
- Code signing automation
- Secure command execution

### 3. **Web Interface** (`src/web/`)
- Modern HTML5/CSS3/JavaScript frontend
- Drag-and-drop file handling
- Real-time communication with backend
- Responsive design
- Dark theme implementation

## 🚀 Installation

### Prerequisites
- **macOS 10.15+** (Catalina or later)
- **Python 3.7+** (usually pre-installed on modern macOS)
- **Xcode Command Line Tools** (for building from source)

### Option 1: Pre-built Application
1. Download `Maestro_Standalone.app` from the releases
2. Copy to your `/Applications` folder
3. Right-click and select "Open" (first time only)
4. Grant necessary permissions when prompted

### Option 2: Build from Source
```bash
# Clone the repository
git clone https://github.com/yourusername/maestro.git
cd maestro/Maestro_Project

# Run the build script
chmod +x build/create_maestro_standalone.sh
./build/create_maestro_standalone.sh

# The built app will be in build/Maestro_Standalone.app
```

## 📖 Usage Guide

### 🎯 **Direct Plugin Installation**
1. Launch Maestro
2. Drag plugin files (.component, .vst, .vst3, .aax) onto the app window
3. Choose installation location:
   - **User**: `~/Library/Audio/Plug-Ins/` (no admin password required)
   - **System**: `/Library/Audio/Plug-Ins/` (requires admin password)
4. Click "Install Selected Plugins"
5. Enter admin password if installing system-wide
6. Monitor progress and view results

### 📦 **Package Installation**
1. Drag a .pkg installer file onto Maestro
2. Wait for automatic package analysis
3. Review the list of discovered plugins
4. Select/deselect plugins you want to install
5. Choose installation location
6. Click "Install Selected Plugins"
7. Monitor the installation process

### ⚙️ **Advanced Options**
- **Settings**: Access installation preferences
- **Progress Monitoring**: Real-time installation feedback
- **Error Handling**: Detailed error reporting and resolution guidance
- **Plugin Management**: View installation results and locations

## 🗂️ Project Structure

```
Maestro_Project/
├── src/
│   ├── swift/
│   │   └── main.swift              # Native macOS wrapper
│   ├── python/
│   │   └── maestro_backend.py      # Backend server
│   └── web/
│       ├── index.html              # Main interface
│       ├── styles.css              # Dark theme styles
│       ├── script.js               # Application logic
│       └── assets/
│           └── icon.png            # Application icon
├── build/
│   └── create_maestro_standalone.sh # Build script
└── README.md                       # This file
```

## 🔧 Development

### Building the Application
```bash
cd Maestro_Project
./build/create_maestro_standalone.sh
```

### Development Requirements
- macOS development environment
- Xcode or Command Line Tools
- Python 3.7+ with pip
- Required Python packages:
  - Flask==2.3.3
  - Flask-CORS==4.0.0
  - Werkzeug==2.3.7

### Running in Development Mode
```bash
# Start the backend server
cd src/python
python3 maestro_backend.py --debug

# Open the web interface in a browser
open http://127.0.0.1:8080
```

## 🛡️ Security Considerations

- **Code Signing**: All installed plugins are automatically code-signed
- **Password Security**: Admin passwords are handled securely and never stored
- **Temporary Files**: Secure cleanup of all temporary files
- **Network Security**: Local-only HTTP server with CORS protection
- **File Validation**: Comprehensive validation of all plugin files

## 🎨 UI/UX Design

### Color Scheme
- **Primary Gradient**: `#1a1a2e` → `#16213e`
- **Accent Colors**: `#6366f1` (purple) for highlights
- **Text Colors**: White (`#ffffff`) primary, muted grays for secondary
- **Status Colors**: Green for success, red for errors, blue for info

### Typography
- **Primary Font**: Inter (web-safe fallbacks included)
- **Sizing**: Responsive scaling from 12px to 24px
- **Weights**: 300-700 range for proper hierarchy

### Interactions
- **Hover Effects**: Subtle animations and state changes
- **Progress Indicators**: Real-time feedback with animated progress bars
- **Modal Dialogs**: Native-style overlays for important actions
- **Notifications**: Toast-style messages with auto-dismiss

## 🔍 File Locations

### Plugin Installation Directories

#### User Installation
```
~/Library/Audio/Plug-Ins/
├── Components/         # Audio Unit (.component)
├── VST/               # VST 2.x (.vst)
├── VST3/              # VST 3.x (.vst3)
└── AAX/               # AAX (.aax)
```

#### System Installation
```
/Library/Audio/Plug-Ins/
├── Components/         # Audio Unit (.component)
├── VST/               # VST 2.x (.vst)
├── VST3/              # VST 3.x (.vst3)
└── AAX/               # AAX (.aax)
```

### Application Data
- **Application Bundle**: `/Applications/Maestro_Standalone.app`
- **Backend Server**: `Contents/Resources/maestro_backend.py`
- **Web Interface**: `Contents/Resources/index.html`
- **Temporary Files**: System temporary directory (auto-cleaned)

## 🚨 Troubleshooting

### Common Issues

#### **"App can't be opened because it is from an unidentified developer"**
- Right-click the app and select "Open"
- Click "Open" in the security dialog

#### **Backend Connection Issues**
- Check if any firewall is blocking local connections
- Ensure Python 3 is installed and accessible
- Try restarting the application

#### **Installation Failures**
- Verify you have proper permissions for the target directory
- Check available disk space
- Ensure the plugin files are not corrupted
- Try installing to user directory first

#### **Code Signing Errors**
- This is usually safe to ignore for personal use
- Install Xcode for proper code signing tools
- Use system installation only when necessary

### Debug Mode
Run the backend in debug mode for detailed logging:
```bash
python3 maestro_backend.py --debug --port 8080
```

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow Swift and Python style guidelines
- Maintain backward compatibility
- Add tests for new features
- Update documentation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Apple** - For the excellent macOS development frameworks
- **Flask Community** - For the robust web framework
- **Audio Plugin Developers** - For creating the amazing tools we help install

## 📞 Support

- **GitHub Issues**: For bug reports and feature requests
- **Documentation**: Comprehensive guides in the wiki
- **Community**: Join discussions in the issues section

---

<div align="center">

**Made with ❤️ for the audio production community**

[Report Bug](https://github.com/yourusername/maestro/issues) · [Request Feature](https://github.com/yourusername/maestro/issues) · [View Documentation](https://github.com/yourusername/maestro/wiki)

</div> 