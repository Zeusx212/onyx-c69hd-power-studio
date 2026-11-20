#!/usr/bin/env bash
# =============================================================================
# Onyx Boox C69HD Power Studio • ADB & Fastboot Setup for Linux / macOS
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================="
echo "   Android SDK Platform-Tools Installer (Linux / macOS)"
echo "================================================================="

# Check if adb is already installed
if command -v adb &>/dev/null; then
    echo "[✓] ADB is already available:"
    adb version | head -n 2
    echo "No further action needed. If you need scrcpy:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  brew install scrcpy"
    else
        echo "  sudo apt install scrcpy  (or snap install scrcpy)"
    fi
    exit 0
fi

# Native package manager detection
if [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v brew &>/dev/null; then
        echo "[*] Homebrew detected! Installing official platform-tools & scrcpy..."
        brew install android-platform-tools scrcpy
        echo "[✓] Installation complete via Homebrew."
        exit 0
    fi
else
    if command -v apt-get &>/dev/null; then
        echo "[*] Debian/Ubuntu detected. You can install via apt:"
        echo "    sudo apt update && sudo apt install -y adb fastboot scrcpy"
        read -p "Would you like to run this command now with sudo? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo apt update && sudo apt install -y adb fastboot scrcpy
            exit 0
        fi
    elif command -v dnf &>/dev/null; then
        echo "[*] Fedora detected. You can install via dnf:"
        echo "    sudo dnf install -y android-tools scrcpy"
        read -p "Would you like to run this command now with sudo? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo dnf install -y android-tools scrcpy
            exit 0
        fi
    elif command -v pacman &>/dev/null; then
        echo "[*] Arch Linux detected. You can install via pacman:"
        echo "    sudo pacman -S --noconfirm android-tools scrcpy"
        read -p "Would you like to run this command now with sudo? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo pacman -S --noconfirm android-tools scrcpy
            exit 0
        fi
    fi
fi

# Fallback to automated python Google downloader
echo "[*] Launching automated official Google Platform-Tools downloader..."
python3 install_adb.py "$@"
