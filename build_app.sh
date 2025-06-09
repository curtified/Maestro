#!/bin/bash
set -ex # Exit on error and print commands

echo "INFO: Starting Maestro App build process..."

# --- Aggressive Clean ---
# Clean previous build directories and artifacts from root
echo "INFO: Aggressively cleaning previous build directories (build/, dist/)..."
rm -rf build
rm -rf dist

# Recreate the main build directory
mkdir -p build

# Bundle Python backend
echo "INFO: Bundling Python backend with PyInstaller..."
# Ensure the Python script itself is executable if it's not already
chmod +x src/python/maestro_backend.py

pyinstaller --noconfirm --onedir --windowed --name MaestroBackend src/python/maestro_backend.py --distpath build/dist_backend --workpath build/pyinstaller_build --additional-hooks-dir=./hooks --hidden-import=pkg_resources.py2_warn --hidden-import=flask_cors --hidden-import=werkzeug --hidden-import=jinja2 --hidden-import=itsdangerous --hidden-import=click --hidden-import=markupsafe --debug all --log-level DEBUG
# Added common Flask-related hidden imports just in case.

# Create .app structure
echo "INFO: Creating .app bundle structure..."
mkdir -p build/Maestro.app/Contents/MacOS
mkdir -p build/Maestro.app/Contents/Resources/web
mkdir -p build/Maestro.app/Contents/Resources/MaestroBackend # PyInstaller output is a dir

# Create Info.plist
echo "INFO: Creating Info.plist..."
cat << EOF > build/Maestro.app/Contents/Info.plist
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>MaestroSwift</string>
    <key>CFBundleIconFile</key>
    <string>icon.png</string>
    <key>CFBundleIdentifier</key>
    <string>com.yourdomain.maestro</string>
    <key>CFBundleName</key>
    <string>Maestro</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>NSMainNibFile</key>
    <string></string>
    <key>NSRequiresAquaSystemAppearance</key>
    <string>NO</string>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © $(date +%Y) Your Name. All rights reserved.</string>
    <key>LSUIElement</key> <!-- Optional: Set to true to make it a background app without a Dock icon -->
    <string>false</string>
</dict>
</plist>
EOF

# Compile Swift
echo "INFO: Compiling Swift application..."
swiftc src/swift/main.swift -o build/Maestro.app/Contents/MacOS/MaestroSwift -target x86_64-apple-macosx10.13 # Or arm64 if needed

# Copy Python backend to Resources
echo "INFO: Copying Python backend to app Resources..."
# PyInstaller creates MaestroBackend/MaestroBackend, so we copy the inner MaestroBackend folder
cp -R build/dist_backend/MaestroBackend build/Maestro.app/Contents/Resources/

# Copy web interface to Resources
echo "INFO: Copying web interface to app Resources..."
cp -R src/web/* build/Maestro.app/Contents/Resources/web/

# Copy icon
echo "INFO: Copying app icon..."
if [ -f "src/web/assets/icon.png" ]; then
    cp src/web/assets/icon.png build/Maestro.app/Contents/Resources/icon.png
else
    echo "WARNING: src/web/assets/icon.png not found. Skipping icon copy."
fi

# Code sign (Ad-hoc)
echo "INFO: Code signing application (ad-hoc)..."
codesign --force --deep --sign - build/Maestro.app

# Make the script executable (though this chmod is for the script itself, not the built app)
chmod +x build/Maestro.app/Contents/MacOS/MaestroSwift

echo "INFO: Maestro.app bundled successfully in build/ directory."
echo "INFO: To run, try: open build/Maestro.app"
echo "NOTE: If PyInstaller issues occur, you might need to install it in your global Python env or ensure it's in PATH."
echo "NOTE: For distribution, proper code signing with an Apple Developer ID is required."
