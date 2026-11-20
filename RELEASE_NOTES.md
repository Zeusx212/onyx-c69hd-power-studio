### What is New in v1.1.0:
- **Physical Side Button Remapper**: Full hardware-level key remapping for physical side page-turn buttons (`gpio-keys`: Key 104 and Key 109). Includes presets for Volume Keys (Kindle, Moon+ Reader, KOReader, Tachiyomi page turns), Default Page Turn, Inverted Left-Hand Mode, D-Pad Navigation, Reader + Back, and custom keycodes, plus Onyx OS long-press actions (`fullRefreshScreen`, `screenshot`, `toggleA2`, `showRefreshModeDialog`, etc.) with zero-risk Magisk systemless persistence.
- **Ported to Linux & macOS**:
  - Native POSIX launchers: `./run_gui.sh` and `./install_adb.sh`.
  - Native standalone build scripts: `build_linux.sh` and `build_mac.sh`.
  - Cross-platform screenshot clipboard helper (AppleScript pasteboard on macOS, `wl-copy`/`xclip` on Linux).
  - Cross-platform ADB and Scrcpy detection & auto-installation (Homebrew, APT, DNF, Pacman, Google SDK).
- **Automated Multi-Platform CI/CD**: GitHub Actions workflow (`.github/workflows/build.yml`) compiling and releasing native Windows, Linux, and macOS standalone binaries on tag push.

### Download Packages:
- **Windows (x64)**: [Onyx_C69HD_Power_Studio_win_x64.zip](https://github.com/Zeusx212/onyx-c69hd-power-studio/releases/download/v1.1.0/Onyx_C69HD_Power_Studio_win_x64.zip)
- **Linux (x64)**: [Onyx_C69HD_Power_Studio_linux_x64.tar.gz](https://github.com/Zeusx212/onyx-c69hd-power-studio/releases/download/v1.1.0/Onyx_C69HD_Power_Studio_linux_x64.tar.gz)
- **macOS**: [Onyx_C69HD_Power_Studio_macOS.zip](https://github.com/Zeusx212/onyx-c69hd-power-studio/releases/download/v1.1.0/Onyx_C69HD_Power_Studio_macOS.zip)
