# Onyx Boox C69HD Power Studio v1.1.3

### 🔥 Custom TWRP Recovery Studio (Touch & E-Ink DRM)
- **Direct TWRP Flashing & Tether-Booting**: Integrated complete recovery management directly into the Root & Partitions Studio:
  - **⚡ 1-Click Tether-Boot to RAM (Zero-Risk)**: Streams the recovery image directly to device RAM using `fastboot boot recovery.img`. Leaves internal storage and factory recovery completely untouched—perfect for risk-free NANDroid backups, partition inspection, or testing.
  - **💾 1-Click Permanent Flash**: Safely writes TWRP to the recovery partition via `fastboot flash recovery recovery.img` (or `recovery_a` / `recovery_b`), with automatic reboot into TWRP.
  - **🔄 Reboot to Recovery**: 1-click reboot to recovery from either Android ADB mode or Fastboot mode.
  - **🛡️ Stock Recovery Backup**: 1-click partition dumper to save factory stock recovery before making modifications.
  - **Verified Working TWRP 11.0 Pre-Bundled**: Includes `twrp_c69hd_recovery.img` from [Zeusx212/android_device_onyx_c69](https://github.com/Zeusx212/android_device_onyx_c69), featuring native Qualcomm Atomic DRM EPDC E-Ink display drivers on Plane 68 (`SSPP ViG0`) and FocalTech touchscreen digitizer support.
  - **Custom Image Browsing**: Select and flash any custom recovery image `.img` from local storage.

### 🛡️ Turnkey 6-Step Guided Root Wizard
- Live device status dashboard inspecting bootloader lock state, boot slot (`_a` or `_b`), and root privileges.
- Pre-bundled factory partition images (`stock_boot_a.img`, `stock_boot_b.img`, `stock_vbmeta_a.img`) and pre-patched Magisk boot image (`magisk_patched_boot_a.img`) for 1-click turnkey rooting.
- Automated Magisk APK install, boot image push, and fastboot flashing with emergency unroot restore.

### ⚡ Power & Sleep Hardware Button Remapping
- Hardware mapping for physical side keys (`gpio-keys`: Key 104 and 109) to **`POWER`**, **`SLEEP`**, and **`WAKEUP`** with Android **`WAKE`** flag injection.
- Front center button mapping to **`KEYCODE_POWER`**.

### 🌐 System-Wide ADB & Fastboot Fixes
- Automated ADB daemon process termination (`kill_adb_processes()`) to eliminate Windows `[Errno 13] Permission denied: 'adb.exe'`.
- System-wide environment registration in `HKLM\...\Environment\Path` via UAC elevation, user environment fallback, and instant `WM_SETTINGCHANGE` broadcast.

### 🧪 Comprehensive Test Suite
- **30 automated tests passing** across unit testing (`tests/test_all_features.py`) and executable integrity (`tests/test_exe.py`).
- GUI smoke test verified clean initialization, layout, and termination.

### 📦 Standalone Packages
- **Windows (x64)**: [Onyx_C69HD_Power_Studio_win_x64.zip](https://github.com/Zeusx212/onyx-c69hd-power-studio/releases/download/v1.1.3/Onyx_C69HD_Power_Studio_win_x64.zip) (106 MB complete turnkey package containing standalone desktop app, all dependencies, custom TWRP recovery, stock boot images, and Magisk patched images).
