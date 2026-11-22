#!/usr/bin/env python3
"""
Single-Click ADB & Fastboot Downloader & Setup Tool for Onyx Boox C69HD Power Studio.
Downloads official Google Platform-Tools, extracts them, and registers them into PATH.
"""

import os
import sys
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.adb_installer import (
    find_existing_platform_tools,
    install_platform_tools,
    get_default_install_dir,
    check_path_status,
    is_admin
)

def main():
    parser = argparse.ArgumentParser(description="Auto-detect and install Android SDK Platform-Tools (ADB & Fastboot).")
    parser.add_argument("--force", action="store_true", help="Force re-download even if ADB is already installed.")
    parser.add_argument("--dir", type=str, default=None, help="Target install directory (default: C:\\platform-tools or bin/platform-tools).")
    parser.add_argument("--user-only", action="store_true", help="Register only in User PATH rather than System-wide PATH.")
    parser.add_argument("--no-path", action="store_true", help="Do not register directory in environment PATH.")
    args = parser.parse_args()

    print("=" * 65)
    print("   Onyx Boox C69HD • Android SDK Platform-Tools Installer")
    print("=" * 65)

    systemwide = not args.user_only
    if sys.platform == "win32":
        print(f"[*] Privilege Level : {'Administrator (Elevated)' if is_admin() else 'Standard User'}")
        print(f"[*] Install Target  : {'System-wide (All Users)' if systemwide else 'User Profile Only'}")

    info = find_existing_platform_tools()
    if info["installed"] and not args.force:
        print(f"\n[✓] ADB is ALREADY INSTALLED on your computer:")
        print(f"    - Version : {info['version'] or 'Installed'}")
        print(f"    - ADB Exe : {info['adb']}")
        print(f"    - Fastboot: {info['fastboot'] or 'Not found'}")
        if sys.platform == "win32" and info['adb']:
            adb_dir = os.path.dirname(info['adb'])
            st = check_path_status(adb_dir)
            sys_stat = "[✓] Registered" if st["in_system_path"] else "[ ] Not in System PATH"
            usr_stat = "[✓] Registered" if st["in_user_path"] else "[ ] Not in User PATH"
            print(f"    - System PATH : {sys_stat}")
            print(f"    - User PATH   : {usr_stat}")
        print("\nNo action needed! If you wish to re-install, run with --force.")
        return 0

    if info["installed"] and args.force:
        print(f"\n[!] Existing installation found at: {info['adb']}")
        print("[!] --force specified: Re-downloading latest official package from Google...")
    else:
        print("\n[!] ADB / Fastboot was not found on your system PATH.")
        print("[*] Downloading official Google Platform-Tools (latest release)...")

    target_dir = args.dir or get_default_install_dir(systemwide=systemwide)
    print(f"[*] Target Directory: {target_dir}")

    def progress_cb(pct, msg):
        sys.stdout.write(f"\r[{pct:>3}%] {msg:<60}")
        sys.stdout.flush()

    ok, adb_path, fb_path, ver_str = install_platform_tools(
        target_dir=target_dir,
        progress_callback=progress_cb,
        register_in_path=not args.no_path,
        systemwide=systemwide
    )
    print("\n")

    if ok:
        print("=" * 65)
        print("   [✓] INSTALLATION SUCCESSFUL!")
        print("=" * 65)
        print(f"  • ADB Location      : {adb_path}")
        print(f"  • Fastboot Location : {fb_path}")
        print(f"  • Verified Version  : {ver_str}")
        if not args.no_path and sys.platform == "win32":
            st = check_path_status(target_dir)
            sys_s = "Yes (All Users)" if st["in_system_path"] else "No"
            usr_s = "Yes" if st["in_user_path"] else "No"
            print(f"  • System-wide PATH  : {sys_s}")
            print(f"  • Windows User PATH : {usr_s}")
        print("=" * 65)
        print("You can now launch 'run_gui.bat' to start the customization studio!")
        return 0
    else:
        print("=" * 65)
        print(f"   [X] INSTALLATION FAILED: {ver_str}")
        print("=" * 65)
        return 1

if __name__ == "__main__":
    sys.exit(main())
