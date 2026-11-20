# Onyx Boox C69HD (Faust 5 OEM) Customization Tool

An all-in-one desktop GUI tool designed specifically for the **Onyx Boox C69HD** (an OEM rebadge of the **Faust 5** / Poke 4 Lite, Qualcomm Snapdragon 662 `bengal`, 6" Carta e-ink display).

---

## 🎯 Device Background & Overview

The **C69HD** (`C69_M_STAR`) is an e-reader built on the Onyx Boox Faust 5 platform with unique hardware characteristics:
- **No Frontlight/Backlight Hardware**: Unlike other Faust 5 variants, the C69HD has no backlight LEDs. The factory default action for long-pressing the front hardware button is toggling the backlight—which does nothing.
- **Factory Unlocked Bootloader**: `ro.boot.vbmeta.device_state: unlocked`.
- **Memory Constrained**: 2 GB LPDDR4x RAM (~1.8 GB usable, ~200–500 MB free under load).
- **Infinite Screen Timeout Bug**: Factory `screen_off_timeout` is set to `2147483647` ms (~24.8 days), draining battery when unattended.
- **Cellular & Telephony Bloat**: Despite having no SIM card slot, background Qualcomm telephony daemons and voice listeners (`com.qualcomm.qti.sva`, `dynamicddsservice`, `uimGbaApp`, `iwlan`) run continuously.

This GUI utility automates rooting, partition backups, hardware button remapping, reversible debloating, and essential display/power tweaks in a single unified interface.

---

## 🌟 Features & Tabs

### 1. 🛡️ Root & Partitions
Based on [**Zeusx212/onyx-c69hd-root**](https://github.com/Zeusx212/onyx-c69hd-root):
- **Stock Partition Backup**: Dumps active `boot` (`boot_a` or `boot_b`) and `vbmeta` partitions directly to `./backups/`.
- **Magisk Root Setup**:
  1. 1-Click Install Magisk APK to device (bundled in `assets/magisk.apk`).
  2. One-click reboot to Bootloader (Fastboot).
  3. Flash Magisk-patched boot image to the active slot with automatic reboot.
  4. 1-Click Restore stock boot image if needed.
- **Hardware Button Wake**: Install the `c69hd-wake.zip` Magisk module to allow the front center button and side page-turn keys to wake the device from deep sleep.

### 2. 🔘 Hardware Button Remap
Based on [**Zeusx212/onyx-c69hd-button-remap**](https://github.com/Zeusx212/onyx-c69hd-button-remap):
- Remap the physical front center button (`KEYCODE_BACK`) without modifying system files:
  - **Long-Press (Hold)**:
    - `KEYCODE_APP_SWITCH` (Recent Apps / App Switcher) — **Recommended!**
    - `fullRefreshScreen` (Full E-Ink Refresh to clear ghosting)
    - `screenshot` (Take Screenshot)
    - `showRefreshModeDialog` (E-Ink Refresh Mode dialog)
    - `back_to_home` (Return to Home Screen)
    - `toggleA2` (Toggle A2 Speed Mode)
    - Factory Default (`toggleFrontLight`)
  - **Short-Press (Single Tap)**:
    - Standard Back Key (Recommended)
    - Recent Apps / Full Refresh / Screenshot / Home
- Automatically sets `key_custom_side_key_short_press_enable` and broadcasts `onyx.action.refresh_keymapping`.
- Settings survive device reboots.

### 3. 🧹 Debloating
- **1-Click Safe Debloat Preset**: Disables background cellular & Snapdragon voice services with zero risk on Wi-Fi e-readers:
  - `com.qualcomm.qti.sva` (Voice hotword listener)
  - `com.qualcomm.qti.dynamicddsservice` (Dual SIM service)
  - `com.qualcomm.qti.uimGbaApp` (SIM GBA auth service)
  - `vendor.qti.iwlan` (Wi-Fi calling daemon)
  - `com.qualcomm.qti.xrvd.service` (Qualcomm XR daemon)
  - `com.android.cellbroadcastreceiver` & modules (Cellular alerts)
  - `com.android.smspush` (WAP push service)
- **High RAM Consumers**: Free up ~320 MB RAM by disabling Google Play Services (`com.google.android.gms` / `gsf`) if using F-Droid, Aurora Store, or ReVanced GmsCore.
- **OEM & Unused Apps**: Onyx Mail, stock AOSP keyboards (LatinIME / KIME), and printing services.
- **Custom Package Manager**: Disable or re-enable any specific package by name.
- **100% Reversible**: Uses `pm disable-user --user 0`, fully re-enableable at any time.

### 4. ⚙️ Device Settings & Power Tweaks
- **Screen Timeout Fix**: Quickly set auto-sleep to 1m, 2m, 5m (Recommended), 10m, or 30m.
- **Telemetry Disabling**: Turns off background crash and error reporting (`send_action_app_error = 0`).
- **Background Scanning**: Disables continuous Bluetooth LE and Wi-Fi scanning.
- **Location Services**: Toggles GPS/Location mode to Off (`0`).
- **Display Clarity**: Configure font scale (`1.05` optimized), display density (reset to 212 DPI or custom), and high text contrast.

### 5. 📊 Device Info & Execution Logs
- Real-time display of SoC, board platform, active boot slot, build ID, root status, and battery percentage.
- Power controls: Normal Reboot, Reboot to Recovery, Reboot to Fastboot, Restart SystemUI.
- Live scrollable ADB command console with timestamps and output.

---

## 🚀 How to Run

### Requirements
- Windows 10/11 (or Linux/macOS)
- Python 3.8+ (comes with built-in Tkinter)
- ADB and Fastboot installed and available in system PATH
- USB Debugging enabled on your Onyx Boox C69HD

### Launching the Tool
Simply double-click:
```bat
run_gui.bat
```
Or run from terminal:
```bash
python run_gui.py
```

---

## 🔗 Related Repositories & Acknowledgments

- **Root & Partitions**: [Zeusx212/onyx-c69hd-root](https://github.com/Zeusx212/onyx-c69hd-root)
- **Button Remap**: [Zeusx212/onyx-c69hd-button-remap](https://github.com/Zeusx212/onyx-c69hd-button-remap)
- **Keyboard Debouncer**: [Zeusx212/keyboard-debouncer](https://github.com/Zeusx212/keyboard-debouncer)
- **Device Tree & TWRP**: [7sarus/android_device_onyx_c69](https://github.com/7sarus/android_device_onyx_c69) by [@7sarus](https://github.com/7sarus)
