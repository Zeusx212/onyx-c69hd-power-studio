# Onyx Boox C69HD (Faust 5 OEM) Power Studio

A comprehensive, modern desktop application designed specifically for the **Onyx Boox C69HD** (an OEM rebadge of the **Faust 5** / Poke 4 Lite, Qualcomm Snapdragon 662 `bengal`, 6" Carta E-Ink display).

---

## 🎯 Device Background & Overview

The **C69HD** (`C69_M_STAR`) has unique hardware characteristics:
- **No Frontlight/Backlight Hardware**: Unlike other Faust 5 models, the C69HD has no backlight LEDs. Factory default long-press on the front button is toggling the backlight—which does nothing.
- **Factory Unlocked Bootloader**: `ro.boot.flash.locked = 0`.
- **Memory Constrained**: 2 GB LPDDR4x RAM (~1.8 GB usable, ~200–500 MB free under load).
- **Infinite Screen Timeout Bug**: Factory `screen_off_timeout` defaults to `2147483647` ms (~24.8 days), draining battery when unattended.
- **Cellular & Telephony Bloat**: Despite having no SIM card slot, background Qualcomm telephony daemons and voice listeners (`com.qualcomm.qti.sva`, `dynamicddsservice`, `uimGbaApp`, `iwlan`) run continuously.

---

## 🌟 Complete Feature Suite

### 1. 🏆 1-Click Profile Presets
- **🔋 Extreme Battery Life**: Screen timeout 2m, background Wi-Fi/BLE scanning off, Location off, telemetry off, Qualcomm SVA & cellular daemons disabled.
- **⚡ Free RAM Booster (+320MB RAM)**: Suspends Google Play Services, Services Framework, Onyx Mail, and stock AOSP keyboards to reclaim over 320 MB of usable memory.
- **📖 Distraction-Free Reading**: Relaxed 10-minute timeout, optimized 1.05 font scale, quiet background environment.
- **🔄 Factory Default Revert**: Restores all stock packages, button mappings, and default settings.

### 2. 🛠️ Automated ADB & Fastboot Detection & 1-Click Installer
- **Intelligent Environment Detection**: Scans system PATH, Windows user registry (`HKCU\Environment\Path`), Android SDK directories, WinGet packages, and local project folders for existing Platform-Tools installations.
- **In-App 1-Click Auto-Installer**: If ADB or Fastboot is missing, an alert badge appears in the sidebar and hardware logs page. Clicking the button downloads official Google Platform-Tools directly from `https://dl.google.com/android/repository/platform-tools-latest-windows.zip`, unpacks binaries, and verifies `adb.exe version` in real-time.
- **Windows User PATH Registration**: 1-click registration of `platform-tools/` in Windows User Environment variables with instant `WM_SETTINGCHANGE` broadcast notification.
- **Standalone CLI & Batch Installer**: Includes `install_adb.py` and `install_adb.bat` for standalone setup or setup on headless/clean workstations.

### 3. 📱 Scrcpy Screen Mirroring (Hardware-Accelerated Window)
- **Native Direct3D11 Window**: Launches a native Scrcpy window with high-performance Direct3D11 rendering, crisp text, and zero UI latency.
- **E-Ink Specific Presets**:
  - FPS limiter (15 FPS recommended for Carta E-Ink stability, low CPU, and cool device operation).
  - Turn device screen OFF while mirroring (`--turn-screen-off`) to save E-Ink battery and operate 100% from PC.
  - Stay awake while connected (`--stay-awake`).
  - Read-only viewer mode (`--no-control`).
  - MP4 session recording (`--record=<filename>`).
- **Remote E-Ink Controls & Hotkey Guide**:
  - Remote hardware buttons: Back, Home, Recent Apps, Volume Up/Down, and Lock/Sleep.
  - E-Ink controls: Full-screen refresh to clear ghosting and A2 speed mode toggle.
  - Live cheat-sheet of Scrcpy keyboard shortcuts and instant drag-and-drop APK installation.

### 4. 📶 1-Click Wireless ADB (Cable-Free Mode)
- Automatically detects the device's local Wi-Fi IP (e.g. `192.168.1.11`).
- Switches ADB to port 5555 and connects wirelessly with a single click in the sidebar.
- Disconnect and switch back to USB cable at any time.

### 5. 📚 Book & Comic Transfer Hub
- Drag & drop or browse `.epub`, `.pdf`, `.mobi`, `.azw3`, `.cbz`, `.cbr`, and `.txt` files.
- Select target destination (`/sdcard/Books/`, `/sdcard/Books/Manga/`, etc.).
- Automatically sends Android `MEDIA_SCANNER_SCAN_FILE` broadcasts so new books appear on your Onyx Bookshelf immediately without needing a reboot or reconnect.

### 6. 📦 E-Ink App Sideload Hub
- **Local APK Sideload**: Install any `.apk` with replacement permissions.
- **Curated 1-Click E-Ink Catalog**: Automatic download and install of official releases:
  - **KOReader**: The premier open-source E-Ink e-reader engine.
  - **Mihon**: High-contrast manga and comic reader.
  - **Simple Keyboard**: Lightweight keyboard (replaces heavy 70 MB Onyx LatinIME).
  - **Key Mapper**: Enables double-press and multi-trigger remapping.
  - **LocalSend**: Offline Wi-Fi file sharing.
  - **F-Droid**: Open-source app store.
  - **Taskbar**: Floating app drawer and multitasking switcher.

### 7. ⚡ E-Ink Remote & Screenshot Snip
- **Live Screenshot Tool**: Captures clean 758 × 1024 screenshots over ADB, with live thumbnail display, "Save as PNG", and "Copy to Windows Clipboard".
- **E-Ink Refresh Controls**: Remote full-screen e-ink refresh (`onyx.action.refresh_screen`) to clear ghosting, plus A2 speed mode toggle.
- **Virtual Navigation Keys**: Back, Home, Recent Apps, Volume Up/Down, and Lock/Sleep.

### 8. 🎨 Screensavers & Boot Animation
- **Screensaver Studio**: Auto-crops and scales any image to native Carta 758 × 1024 resolution with E-Ink high-contrast grayscale.
  - Target choices: User Gallery (`/sdcard/Pictures/Screensaver/`), System Standby (`standby-1.png`), or Shutdown Screen (`shutdown-default.png`).
  - Action buttons: "Open Wallpaper Settings on Device" and "Test Sleep Screen".
- **Boot Animation Studio**: Install custom `bootanimation.zip` into the Magisk media overlay (`c69hd-custom-media`).
  - Create from folder of PNG frames.
  - **Live Preview on Device**: Plays the boot animation live on the physical e-reader screen without needing a reboot!
  - 1-Click Restore stock Onyx animation.

### 9. 🛡️ Root & Partitions
- **Stock Partition Backup**: Single or full dump of `boot`, `dtbo`, `recovery`, `vbmeta`, `vbmeta_system`, and `persist`.
- **Magisk Root Workflow**: Install Magisk APK -> Reboot Fastboot -> Flash Patched Boot -> Restore Stock.
- **Hardware Button Wake**: Install `c69hd-wake.zip` Magisk module to allow physical center and side keys to wake the device from sleep.

### 10. 🔘 Hardware Button Remapper
- Remap front button (`KEYCODE_BACK`):
  - **Long-Press**: Recent Apps / App Switcher (Recommended), Full Refresh, Screenshot, Refresh Mode Dialog, Home, Toggle A2, Factory Default.
  - **Short-Press**: Standard Back Key, Recent Apps, Full Refresh, Screenshot, Home.
- Automatically writes to `settings put global KEYCODE_BACK`, configures `key_custom_side_key_short_press_enable`, and broadcasts `onyx.action.refresh_keymapping`.

### 11. 🧹 Reversible System Debloater
- Real-time search filter.
- Safe 1-Click Debloat: Disables Snapdragon Voice Activation, dual-SIM daemons, SIM GBA, IWLAN, XR service, and cell broadcast alerts.
- High RAM Consumers: Google Play Services & GSF toggle.
- 100% reversible via `pm disable-user --user 0`.

### 12. ⚙️ Device Settings & Power Tweaks
- Screen timeout bug fix with 1-click **"Fix to 5 Minutes"**.
- Telemetry, Bluetooth LE, and Wi-Fi scanning toggles.
- Location mode toggle.
- Font scale, display density (212 DPI reset / custom), and high text contrast.

---

## 🧪 Unit Testing

Run the automated test suite across all modules:
```bash
python -m unittest discover -s tests -p "test_*.py"
```
Covers:
- Automated ADB and Fastboot detection & installer verification
- Scrcpy standalone execution and Direct3D11 flags
- ADB manager parsing and device info probes
- Partition dump definitions and safety validations
- Screensaver 758x1024 high-contrast grayscale conversion
- Boot animation `desc.txt` and uncompressed ZIP format checks
- Button remapping JSON payloads and broadcast commands
- Curated app store catalogue and debloat package definitions

---

## 🚀 How to Run

### Requirements
- Windows 10/11 (or macOS/Linux)
- Python 3.8+
- Dependencies: `pip install customtkinter Pillow`
- **ADB & Fastboot**: Auto-detected or auto-installed directly inside the application (or via `install_adb.bat`).
- USB Debugging enabled on your Onyx Boox C69HD

### Launching the Application
Double-click:
```bat
run_gui.bat
```
Or run from terminal:
```bash
python run_gui.py
```

---

## 🔗 Related Repositories & Credits

- **Root & Partitions**: [Zeusx212/onyx-c69hd-root](https://github.com/Zeusx212/onyx-c69hd-root)
- **Button Remap**: [Zeusx212/onyx-c69hd-button-remap](https://github.com/Zeusx212/onyx-c69hd-button-remap)
- **Keyboard Debouncer**: [Zeusx212/keyboard-debouncer](https://github.com/Zeusx212/keyboard-debouncer)
- **Device Tree & TWRP**: [7sarus/android_device_onyx_c69](https://github.com/7sarus/android_device_onyx_c69) by [@7sarus](https://github.com/7sarus)
