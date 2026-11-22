### What is New in v1.1.1:
- **⚡ Power & Sleep Button Remapping**:
  - Full hardware mapping for physical side page-turn buttons (`gpio-keys`: Key 104 and Key 109) to **`POWER`**, **`SLEEP`**, or **`WAKEUP`**.
  - Automatic `WAKE` flag integration (`key 104 POWER WAKE`) so pressing physical buttons puts the device to standby and instantly wakes it up.
  - New curated presets:
    - *⚡ Power + Page Turn* (Top = POWER, Bottom = PAGE_DOWN)
    - *⚡ Page Turn + Power* (Top = PAGE_UP, Bottom = POWER)
    - *💤 Dual Power & Sleep* (Top = POWER, Bottom = SLEEP)
    - *⚡ Power + Back* (Top = POWER, Bottom = BACK)
  - Front Center Button (`KEYCODE_BACK`): Added **`KEYCODE_POWER`** for both Short-Press and Long-Press actions to sleep/wake screen.
- **🌐 System-wide ADB & Fastboot Setup Fixes**:
  - **Process Locking Fix**: Automatically terminates running ADB background daemons before extracting binaries, preventing Windows `[Errno 13] Permission denied: 'adb.exe'` errors.
  - **Machine-Wide System PATH**: Installs to canonical `C:\platform-tools` and registers in System PATH (`HKLM\...\Environment\Path`) with UAC elevation, alongside User PATH (`HKCU\Environment\Path`) and instant `WM_SETTINGCHANGE` broadcast.
  - **Fast Directory Probing**: Replaced sluggish recursive WinGet folder scanning with instant targeted directory matching.
- **🧪 Automated Standalone Executable Unit Testing**:
  - Added `tests/test_exe.py` covering binary existence, size integrity, bundled assets verification (`bootanimation.zip`, `magisk.apk`, `c69hd-wake.zip`, screensavers), and dynamic library runtime execution.
  - 23 unit tests passing across all test suites.

### Download Packages:
- **Windows (x64)**: [Onyx_C69HD_Power_Studio_win_x64.zip](https://github.com/Zeusx212/onyx-c69hd-power-studio/releases/download/v1.1.1/Onyx_C69HD_Power_Studio_win_x64.zip)
