"""
ADB & Fastboot Automated Detection & Installer.
Detects missing Android SDK platform-tools, downloads official Google binaries,
unpacks them, registers them into PATH, and validates functionality.
"""

import os
import sys
import shutil
import zipfile
import urllib.request
import subprocess
import glob
import ctypes

def get_platform_tools_url():
    """Returns official Google download URL for current OS."""
    if sys.platform == "win32":
        return "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
    elif sys.platform == "darwin":
        return "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip"
    else:
        return "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"

def get_default_install_dir():
    """Returns the default directory where platform-tools should be installed."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_bin = os.path.join(base_dir, "bin", "platform-tools")
    return local_bin

def find_existing_platform_tools():
    """
    Searches for existing adb and fastboot binaries on PATH, in local bin/,
    in WinGet packages, Android SDK, and standard root locations.
    Returns: dict with 'adb', 'fastboot', 'installed', and 'version'
    """
    exe_suffix = ".exe" if sys.platform == "win32" else ""
    adb_name = f"adb{exe_suffix}"
    fastboot_name = f"fastboot{exe_suffix}"

    candidate_dirs = []

    # 1. Check local project bin directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate_dirs.append(os.path.join(base_dir, "bin", "platform-tools"))

    # 2. Check standard Windows locations
    if sys.platform == "win32":
        candidate_dirs.append(r"C:\platform-tools")
        candidate_dirs.append(r"C:\tools\platform-tools")
        candidate_dirs.append(r"C:\Android\platform-tools")

        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            candidate_dirs.append(os.path.join(local_app, "Android", "Sdk", "platform-tools"))
            # WinGet packages
            winget_root = os.path.join(local_app, "Microsoft", "WinGet", "Packages")
            if os.path.isdir(winget_root):
                try:
                    for root, dirs, files in os.walk(winget_root):
                        if adb_name in files:
                            candidate_dirs.append(root)
                except Exception:
                    pass

        # User profile
        user_prof = os.environ.get("USERPROFILE", "")
        if user_prof:
            candidate_dirs.append(os.path.join(user_prof, "platform-tools"))

    # Check candidates
    found_adb = None
    found_fastboot = None

    for d in candidate_dirs:
        if not d or not os.path.isdir(d):
            continue
        p_adb = os.path.join(d, adb_name)
        p_fb = os.path.join(d, fastboot_name)
        if os.path.isfile(p_adb) and not found_adb:
            found_adb = p_adb
        if os.path.isfile(p_fb) and not found_fastboot:
            found_fastboot = p_fb

    # Fallback to system PATH
    if not found_adb:
        found_adb = shutil.which("adb")
    if not found_fastboot:
        found_fastboot = shutil.which("fastboot")

    version = None
    if found_adb and os.path.isfile(found_adb):
        try:
            res = subprocess.run(
                [found_adb, "version"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if res.returncode == 0:
                # e.g. "Android Debug Bridge version 1.0.41"
                for line in res.stdout.splitlines():
                    if "Android Debug Bridge version" in line:
                        version = line.strip()
                        break
                if not version and res.stdout:
                    version = res.stdout.splitlines()[0].strip()
        except Exception:
            pass

    return {
        "installed": bool(found_adb and os.path.isfile(found_adb)),
        "adb": found_adb,
        "fastboot": found_fastboot,
        "version": version
    }

def add_directory_to_user_path(directory):
    """
    Adds a directory to Windows User Environment PATH registry and broadcasts WM_SETTINGCHANGE.
    Returns True if successfully added or already present.
    """
    if sys.platform != "win32":
        return True

    directory = os.path.abspath(directory)
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_ALL_ACCESS)
        try:
            curr_path, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            curr_path = ""

        paths = [p.strip() for p in curr_path.split(";") if p.strip()]
        if directory not in paths:
            paths.append(directory)
            new_path = ";".join(paths)
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            winreg.CloseKey(key)

            # Broadcast environment change
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            SMTO_ABORTIFHUNG = 0x0002
            result = ctypes.c_ulong()
            ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST,
                WM_SETTINGCHANGE,
                0,
                "Environment",
                SMTO_ABORTIFHUNG,
                2000,
                ctypes.byref(result)
            )
            return True
        else:
            winreg.CloseKey(key)
            return True
    except Exception as e:
        print(f"Warning: Could not update registry PATH: {e}")
        return False

def install_platform_tools(target_dir=None, progress_callback=None, register_in_path=True):
    """
    Downloads official Google Platform-Tools, unpacks them into target_dir,
    adds the directory to process PATH and user environment, and validates installation.

    progress_callback(percent: int, message: str)
    Returns: (success: bool, adb_path: str, fastboot_path: str, version: str)
    """
    if not target_dir:
        target_dir = get_default_install_dir()

    os.makedirs(target_dir, exist_ok=True)
    url = get_platform_tools_url()

    if progress_callback:
        progress_callback(5, f"Connecting to {url}...")

    zip_tmp = os.path.join(target_dir, "platform_tools_temp.zip")

    try:
        # 1. Download official ZIP
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) C69HD_Power_Studio/1.0"}
        )

        with urllib.request.urlopen(req, timeout=30) as response, open(zip_tmp, "wb") as out_file:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            block_size = 65536

            while True:
                chunk = response.read(block_size)
                if not chunk:
                    break
                downloaded += len(chunk)
                out_file.write(chunk)

                if total_size > 0 and progress_callback:
                    pct = int(5 + (downloaded / total_size) * 65)  # 5% to 70%
                    mb_cur = downloaded / (1024 * 1024)
                    mb_tot = total_size / (1024 * 1024)
                    progress_callback(pct, f"Downloading official tools: {mb_cur:.1f} / {mb_tot:.1f} MB...")

        if progress_callback:
            progress_callback(75, "Extracting platform-tools archive...")

        # 2. Extract ZIP
        with zipfile.ZipFile(zip_tmp, "r") as zf:
            members = zf.namelist()
            total_files = len(members)

            for idx, member in enumerate(members):
                # Google archive has prefix 'platform-tools/'
                filename = member
                if filename.startswith("platform-tools/"):
                    filename = filename[len("platform-tools/"):]
                elif filename.startswith("platform-tools\\"):
                    filename = filename[len("platform-tools\\"):]

                if not filename:
                    continue

                dest_path = os.path.join(target_dir, filename)
                if member.endswith("/"):
                    os.makedirs(dest_path, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with zf.open(member) as source, open(dest_path, "wb") as target:
                        shutil.copyfileobj(source, target)

                if progress_callback and total_files > 0 and idx % 5 == 0:
                    pct = int(75 + (idx / total_files) * 15)  # 75% to 90%
                    progress_callback(pct, f"Extracting {filename}...")

        # Remove temp zip
        try:
            if os.path.exists(zip_tmp):
                os.remove(zip_tmp)
        except Exception:
            pass

        # 3. Locate newly extracted binaries
        exe_suffix = ".exe" if sys.platform == "win32" else ""
        adb_path = os.path.join(target_dir, f"adb{exe_suffix}")
        fastboot_path = os.path.join(target_dir, f"fastboot{exe_suffix}")

        # Ensure executable permissions on POSIX
        if sys.platform != "win32":
            for p in (adb_path, fastboot_path):
                if os.path.isfile(p):
                    os.chmod(p, 0o755)

        if not os.path.isfile(adb_path):
            return False, None, None, f"adb binary missing from extracted archive in {target_dir}"

        # 4. Add to current runtime process PATH
        curr_path = os.environ.get("PATH", "")
        if target_dir not in curr_path.split(os.pathsep):
            os.environ["PATH"] = f"{target_dir}{os.pathsep}{curr_path}"

        # 5. Add to User PATH if requested
        if register_in_path and sys.platform == "win32":
            if progress_callback:
                progress_callback(92, "Registering in Windows environment PATH...")
            add_directory_to_user_path(target_dir)

        # 6. Verify installation
        if progress_callback:
            progress_callback(96, "Verifying ADB server execution...")

        res = subprocess.run(
            [adb_path, "version"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        version_str = "Android Debug Bridge"
        if res.returncode == 0 and res.stdout:
            for l in res.stdout.splitlines():
                if "Android Debug Bridge version" in l:
                    version_str = l.strip()
                    break

        if progress_callback:
            progress_callback(100, f"Successfully installed! ({version_str})")

        return True, adb_path, fastboot_path, version_str

    except Exception as e:
        try:
            if os.path.exists(zip_tmp):
                os.remove(zip_tmp)
        except Exception:
            pass
        return False, None, None, str(e)
