#!/usr/bin/env bash
# =============================================================================
# Onyx Boox C69HD Power Studio • macOS App Bundle Build Script
# Builds native macOS .app bundle for Apple Silicon and Intel Macs.
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================="
echo "   Building Onyx Boox C69HD Power Studio for macOS"
echo "================================================================="

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

rm -rf build dist

echo "[*] Compiling macOS .app bundle with PyInstaller..."
pyinstaller --noconfirm --onedir --windowed \
    --name "Onyx_C69HD_Power_Studio" \
    --collect-all "customtkinter" \
    --collect-all "PIL" \
    --add-data "assets:assets" \
    --add-data "scripts:scripts" \
    --osx-bundle-identifier "com.zeusx212.onyx_c69hd_power_studio" \
    run_gui.py

# Package into zip
cd dist
zip -r "Onyx_C69HD_Power_Studio_macOS.zip" "Onyx_C69HD_Power_Studio.app"
cd ..

echo "================================================================="
echo "   [✓] macOS Build Complete: dist/Onyx_C69HD_Power_Studio_macOS.zip"
echo "================================================================="
