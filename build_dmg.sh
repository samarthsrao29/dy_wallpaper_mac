#!/bin/bash
set -e

# Change directory to the script's directory
cd "$(dirname "$0")"

echo "=== YearFlow DMG Packager ==="

# Check if .venv exists, if not create and activate it
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing requirements..."
pip install -r requirements.txt

echo "Cleaning previous builds..."
rm -rf build dist

echo "Building standalone macOS Application..."
# We use pyinstaller to package the app
# --windowed: creates a macOS .app bundle
# --noconfirm: overwrite existing build without prompting
# --add-data: embed the fonts folder and quotes.json
pyinstaller --windowed --name YearFlow --noconfirm \
    --add-data "quotes.json:." \
    --add-data "fonts:fonts" \
    --add-data "launchd:launchd" \
    app.py

# Verify the app was built
if [ ! -d "dist/YearFlow.app" ]; then
    echo "Error: dist/YearFlow.app was not created successfully."
    exit 1
fi

echo "Creating DMG Installer..."
DMG_BUILD_DIR="dist/dmg_build"
rm -rf "$DMG_BUILD_DIR"
mkdir -p "$DMG_BUILD_DIR"

# Copy the app to the staging directory
cp -R "dist/YearFlow.app" "$DMG_BUILD_DIR/"

# Create a symlink to Applications directory
ln -s /Applications "$DMG_BUILD_DIR/Applications"

# Set up DMG name and remove old one if exists
DMG_FILE="dist/YearFlow.dmg"
rm -f "$DMG_FILE"

echo "Formatting Disk Image (DMG)..."
hdiutil create -volname "YearFlow" -srcfolder "$DMG_BUILD_DIR" -ov -format UDZO "$DMG_FILE"

# Clean up build staging directory
rm -rf "$DMG_BUILD_DIR"

echo "============================================="
echo "Success! DMG built at: dist/YearFlow.dmg"
echo "============================================="
