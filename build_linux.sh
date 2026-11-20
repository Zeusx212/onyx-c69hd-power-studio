#!/usr/bin/env bash
# =============================================================================
# Onyx Boox C69HD Power Studio • Linux PyInstaller Standalone Build Script
# Builds standalone executable for x86_64 Linux distributions.
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================="
echo "   Building Onyx Boox C69HD Power Studio for Linux"
echo "================================================================="

# Check virtualenv / requirements
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

rm -rf build dist

echo "[*] Compiling with PyInstaller..."
pyinstaller --noconfirm --onedir --windowed \
    --name "Onyx_C69HD_Power_Studio" \
    --collect-all "customtkinter" \
    --collect-all "PIL" \
    --add-data "assets:assets" \
    --add-data "scripts:scripts" \
    run_gui.py

# Package into tar.gz
cd dist
tar -czvf "Onyx_C69HD_Power_Studio_linux_x64.tar.gz" "Onyx_C69HD_Power_Studio"
cd ..

echo "================================================================="
echo "   [✓] Linux Build Complete: dist/Onyx_C69HD_Power_Studio_linux_x64.tar.gz"
echo "================================================================="
