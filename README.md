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
  - **EinkBro**: Purpose-built E-Ink browser with physical page-turn button navigation and contrast controls.
  - **Komi Store**: Modern GitHub/Codeberg app store with direct APK downloads, auto-updates, and silent installs.
  - **Olauncher**: Distraction-free, minimal high-contrast text launcher ideal for Carta displays.
  - **Librera Reader**: Highly customizable multi-format reader with dedicated E-Ink high-contrast mode.
  - **Simple Keyboard**: Lightweight keyboard (replaces heavy 70 MB Onyx LatinIME).
  - **Key Mapper**: Enables double-press and multi-trigger remapping.
  - **LocalSend**: Offline Wi-Fi file sharing.
  - **F-Droid**: Open-source app store.

### 7. ⚡ E-Ink Remote & Screenshot Snip
- **Live Screenshot Tool**: Captures clean 758 × 1024 screenshots over ADB, with live thumbnail display, "Save as PNG", and "Copy to Windows Clipboard".
- **E-Ink Refresh Controls**: Remote full-screen e-ink refresh (`onyx.action.refresh_screen`) to clear ghosting, plus A2 speed mode toggle.
- **Virtual Navigation Keys**: Back, Home, Recent Apps, Volume Up/Down, and Lock/Sleep.

### 8. 🎨 Screensavers & Boot Animation
- **Screensaver Studio**: Auto-crops and scales any image to native Carta 758 × 1024 resolution with E-Ink high-contrast grayscale.
  - Target choices: User Gallery (`/sdcard/Pictures/Screensaver/`), System Standby (`standby-1.png`), or Shutdown Screen (`shutdown-default.png`).
  - Action buttons: "Open Wallpaper Settings on Device" and "Test Sleep Screen".
- **Boot Animation Studio**: Install custom `bootanimation.zip` into the Magisk media overlay (`c69hd-custom-media`).
  - **1-Click E-Ink Animation Generator**: Instantly builds a compliant, uncompressed (ZIP_STORED) 758 × 1024 animation at 4 FPS featuring vector book unfolding, clean typography, and ghosting-free pulsing progress dots.
  - **Custom Frame Packaging**: Pack any sequence of images into a compliant boot animation.
  - **Live Preview on Device**: Plays the boot animation live on the physical e-reader screen without needing a reboot (`setprop ctl.start bootanim`)!
  - 1-Click Restore stock Onyx animation.
  - Includes standalone CLI: `python scripts/generate_bootanimation.py --theme dark --fps 4 --preview --install`.

### 9. 🛡️ Step-by-Step Root Wizard & Partitions (Turnkey & Foolproof)
The tool features a dedicated 6-Step Root Wizard engineered to make rooting the Onyx Boox C69HD / Faust 5 intuitive and foolproof for any user:

1. **Step 1: Prerequisites & Bootloader Check**
   - Live dashboard detects active boot slot (`_a` or `_b`), bootloader status, and Superuser state.
   - 1-Click **"Reboot to Fastboot"** and 1-Click **"Unlock Bootloader"** (`fastboot flashing unlock` / `oem unlock`). Factory bootloader on the Onyx Boox C69HD is unlocked by default (`unlocked:yes`).
2. **Step 2: Obtain Stock Boot Image (`stock_boot.img`)**
   - **1-Click Turnkey**: Click **"📥 Use Pre-dumped Stock Boot"** to instantly load the verified factory `stock_boot_a.img` (96 MB) bundled in `backups/`.
   - Alternatively: Dump live partitions from device or browse for a local `.img`.
3. **Step 3: Install Magisk App & Push Stock Boot to Device**
   - 1-Click **"📲 Install Magisk & Push boot.img"** automatically installs `Magisk-v31.1.apk` on the device and transfers `stock_boot.img` into `/sdcard/Download/`.
   - 1-Click **"📱 Open Magisk App on Device"** launches the Magisk app on the device screen (mirrorable via native desktop Scrcpy).
4. **Step 4: Patch Boot in Magisk**
   - Follow intuitive visual instructions: In Magisk, tap **Install** -> **Select and Patch a File** -> choose `Download/stock_boot.img` -> tap **LET'S GO**.
   - 1-Click **"📥 Auto-Detect & Pull Patched Image to PC"** scans device storage, locates the new `magisk_patched_*.img`, and pulls it to your PC.
   - **1-Click Turnkey**: Click **"⚡ Use Pre-Patched Image"** to skip manual patching and immediately use the verified, pre-tested `magisk_patched_boot_a.img`!
5. **Step 5: Flash Patched Boot via Fastboot & Reboot**
   - 1-Click **"⚡ Flash Patched Boot & Reboot"** safely switches the device to Fastboot if needed, flashes the patched boot to your active slot (`boot_a` / `boot_b`), and reboots into rooted Android.
6. **Step 6: Verify Root Access & Post-Install Tweaks**
   - 1-Click **"✔️ Verify Root Access"** runs `su -c 'id'` to confirm `uid=0(root)`.
   - 1-Click **"⚡ Install c69hd-wake Magisk Module"** configures hardware key wakeup from deep sleep.
   - 1-Click **"🚨 Emergency Stock Boot Restore"** reverts to 100% factory unrooted stock boot at any time.
7. **Step 7: Custom TWRP Recovery Studio (Touch & E-Ink EPDC DRM)**
   - **Verified Working TWRP 11.0**: Solves the E-Ink black screen / frozen splash issue by binding to primary graphics Plane 68 (`SSPP ViG0`) with vendor atomic DRM EPDC parameters and `DRM_MODE_ATOMIC_NONBLOCK`, paired with FocalTech multi-touch digitizer navigation.
   - **1-Click Zero-Risk Tether-Boot (Recommended)**: Runs `fastboot boot recovery.img` to stream TWRP directly into RAM without touching or modifying internal storage. Ideal for full NANDroid backups, testing, and partition inspection.
   - **1-Click Permanent Flash**: Executes `fastboot flash recovery recovery.img` (or `recovery_a` / `recovery_b`) and optionally reboots straight into custom recovery.
   - **Bundled Working Image**: Pre-loaded with verified `twrp_c69hd_recovery.img` in `backups/`, with support for custom `.img` file browsing and stock recovery dumping.

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

## 🌐 Cross-Platform Porting: Linux & macOS

Onyx Boox C69HD Power Studio is fully cross-platform and runs natively on **Linux (x86_64 / arm64)**, **macOS (Apple Silicon M1-M4 & Intel x86_64)**, and **Windows 10/11**:

- **Native Linux & macOS Launchers**: Run `./run_gui.sh` — automatically verifies Python 3, Tkinter (`python3-tk`), and virtualenv dependencies.
- **Native Package Manager ADB Setup**: Run `./install_adb.sh` — auto-detects Homebrew on macOS (`brew install android-platform-tools scrcpy`), APT on Debian/Ubuntu (`sudo apt install adb fastboot scrcpy`), DNF on Fedora, or Pacman on Arch.
- **Cross-Platform Image Pasteboard**: High-fidelity clipboard image copy via native macOS AppleScript pasteboard and Linux Wayland (`wl-copy`) / X11 (`xclip`).
- **Native Standalone Builds**:
  - Linux: `./build_linux.sh` -> packages standalone directory into `dist/Onyx_C69HD_Power_Studio_linux_x64.tar.gz`.
  - macOS: `./build_mac.sh` -> creates a native macOS `.app` bundle into `dist/Onyx_C69HD_Power_Studio_macOS.zip`.
- **Automated CI/CD Release Pipeline**: GitHub Actions workflow (`.github/workflows/build.yml`) continuously builds and releases native binaries across Windows, Linux, and macOS.

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
- **Custom TWRP Recovery**: [Zeusx212/android_device_onyx_c69](https://github.com/Zeusx212/android_device_onyx_c69) (enhanced with native Qualcomm Atomic DRM EPDC E-Ink driver & touch support, forked from [@7sarus](https://github.com/7sarus))
- **Button Remap**: [Zeusx212/onyx-c69hd-button-remap](https://github.com/Zeusx212/onyx-c69hd-button-remap)
- **Keyboard Debouncer**: [Zeusx212/keyboard-debouncer](https://github.com/Zeusx212/keyboard-debouncer)
