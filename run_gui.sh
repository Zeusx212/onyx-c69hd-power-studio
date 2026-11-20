#!/usr/bin/env bash
# =============================================================================
# Onyx Boox C69HD Power Studio • Linux & macOS Desktop Launcher
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================="
echo "   Onyx Boox C69HD Power Studio (Linux / macOS Launcher)"
echo "================================================================="

# 1. Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "[!] Python 3 is not installed or not in PATH."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "    Install Python 3 via Homebrew: brew install python"
    else
        echo "    Install Python 3 via your package manager: sudo apt install python3 python3-pip python3-tk"
    fi
    exit 1
fi

# 2. Check Tkinter (often separated on Ubuntu/Debian)
if ! python3 -c "import tkinter" &>/dev/null; then
    echo "[!] Tkinter is missing from your Python installation."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "    On macOS: brew install python-tk"
    else
        echo "    On Debian/Ubuntu: sudo apt install python3-tk"
        echo "    On Fedora:        sudo dnf install python3-tkinter"
        echo "    On Arch:          sudo pacman -S tk"
    fi
    exit 1
fi

# 3. Check / create virtualenv if desired
if [ -d ".venv" ]; then
    echo "[*] Activating virtual environment (.venv)..."
    source .venv/bin/activate
elif [ -f "requirements.txt" ]; then
    # Verify core dependencies
    if ! python3 -c "import customtkinter, PIL" &>/dev/null; then
        echo "[*] Missing dependencies detected. Setting up virtual environment..."
        python3 -m venv .venv
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
    fi
fi

# 4. Launch Desktop Studio
echo "[*] Launching Onyx Boox C69HD Power Studio..."
exec python3 run_gui.py "$@"
