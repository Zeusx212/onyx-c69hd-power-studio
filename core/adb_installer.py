"""
ADB & Fastboot Automated Detection & Installer.
Detects missing Android SDK platform-tools, downloads official Google binaries,
unpacks them, registers them into User & Systemwide PATH, and validates functionality.
"""

import os
import sys
import shutil
import zipfile
import urllib.request
import subprocess
import glob
import time
import ctypes

def is_admin():
    """Returns True if the current process is running with administrative/root privileges."""
    if sys.platform == "win32":
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0 if hasattr(os, "geteuid") else False

def get_platform_tools_url():
    """Returns official Google download URL for current OS."""
    if sys.platform == "win32":
        return "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
    elif sys.platform == "darwin":
        return "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip"
    else:
        return "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"

def get_default_install_dir(systemwide=True):
    """
    Returns the target installation directory.
    If systemwide is True (recommended default on Windows):
        Uses C:\\platform-tools if writable/creatable, otherwise local app bin.
    """
    if sys.platform == "win32" and systemwide:
        sys_dir = r"C:\platform-tools"
        try:
            os.makedirs(sys_dir, exist_ok=True)
            test_file = os.path.join(sys_dir, ".perm_test")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return sys_dir
        except Exception:
            pass

    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_bin = os.path.join(base_dir, "bin", "platform-tools")
    return local_bin

def kill_adb_processes():
    """
    Stops running ADB daemons and processes to ensure executables are not locked on Windows.
    """
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/IM", "adb.exe"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            subprocess.run(["pkill", "-9", "adb"], capture_output=True)
    except Exception:
        pass
    time.sleep(0.3)

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

    # 1. Check local project or executable bin directory
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
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
            # Fast WinGet packages check (avoid full recursive walk which stalls)
            winget_root = os.path.join(local_app, "Microsoft", "WinGet", "Packages")
            if os.path.isdir(winget_root):
                try:
                    for pkg in glob.glob(os.path.join(winget_root, "*Google*PlatformTools*")):
                        for sub in (pkg, os.path.join(pkg, "platform-tools")):
                            if os.path.isdir(sub):
                                candidate_dirs.append(sub)
                except Exception:
                    pass

        # User profile
        user_prof = os.environ.get("USERPROFILE", "")
        if user_prof:
            candidate_dirs.append(os.path.join(user_prof, "platform-tools"))

    elif sys.platform == "darwin":
        candidate_dirs.extend([
            "/opt/homebrew/bin",
            "/usr/local/bin",
            os.path.expanduser("~/Library/Android/sdk/platform-tools"),
            os.path.expanduser("~/Android/Sdk/platform-tools"),
            os.path.expanduser("~/platform-tools"),
            "/opt/local/bin",
        ])

    else:  # Linux
        candidate_dirs.extend([
            "/usr/bin",
            "/usr/local/bin",
            os.path.expanduser("~/Android/Sdk/platform-tools"),
            os.path.expanduser("~/.android-sdk/platform-tools"),
            os.path.expanduser("~/platform-tools"),
            os.path.expanduser("~/.local/bin"),
        ])

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

def broadcast_environment_change():
    """Broadcasts WM_SETTINGCHANGE so running Windows applications detect PATH update."""
    if sys.platform != "win32":
        return
    try:
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        result = ctypes.c_ulong()
        SendMessageTimeoutW = ctypes.windll.user32.SendMessageTimeoutW
        SendMessageTimeoutW.argtypes = [
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p,
            ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_ulong)
        ]
        SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            "Environment",
            SMTO_ABORTIFHUNG,
            2000,
            ctypes.byref(result)
        )
    except Exception:
        pass

def check_path_status(directory):
    """
    Checks whether a directory is present in User PATH, System PATH, and Process PATH.
    Returns: dict {"in_user_path": bool, "in_system_path": bool, "in_process_path": bool}
    """
    directory = os.path.normcase(os.path.abspath(directory))
    in_user = False
    in_system = False

    proc_paths = [os.path.normcase(os.path.abspath(p.strip())) for p in os.environ.get("PATH", "").split(os.pathsep) if p.strip()]
    in_proc = directory in proc_paths

    if sys.platform == "win32":
        try:
            import winreg
            # User PATH (HKCU)
            try:
                k_user = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ)
                u_val, _ = winreg.QueryValueEx(k_user, "Path")
                winreg.CloseKey(k_user)
                u_paths = [os.path.normcase(os.path.abspath(p.strip())) for p in u_val.split(";") if p.strip()]
                in_user = directory in u_paths
            except Exception:
                pass

            # System PATH (HKLM)
            try:
                k_sys = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment", 0, winreg.KEY_READ)
                s_val, _ = winreg.QueryValueEx(k_sys, "Path")
                winreg.CloseKey(k_sys)
                s_paths = [os.path.normcase(os.path.abspath(p.strip())) for p in s_val.split(";") if p.strip()]
                in_system = directory in s_paths
            except Exception:
                pass
        except Exception:
            pass
    else:
        in_user = in_proc

    return {
        "in_user_path": in_user,
        "in_system_path": in_system,
        "in_process_path": in_proc
    }

def add_directory_to_user_path(directory):
    """
    Adds a directory to Windows User Environment PATH registry or Linux/macOS shell profiles.
    Returns True if successfully added or already present.
    """
    directory = os.path.abspath(directory)
    if sys.platform != "win32":
        shell = os.environ.get("SHELL", "")
        profile_candidates = []
        if sys.platform == "darwin" or "zsh" in shell:
            profile_candidates.append(os.path.expanduser("~/.zshrc"))
        profile_candidates.extend([
            os.path.expanduser("~/.bashrc"),
            os.path.expanduser("~/.profile"),
            os.path.expanduser("~/.bash_profile")
        ])
        export_line = f'export PATH="{directory}:$PATH"\n'
        for p in profile_candidates:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        content = f.read()
                    if directory not in content:
                        with open(p, "a", encoding="utf-8") as f:
                            f.write(f"\n# Added by Onyx Boox C69HD Power Studio\n{export_line}")
                    return True
                except Exception:
                    pass
        return True

    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_SET_VALUE)
        try:
            curr_path, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            curr_path = ""

        norm_dir = os.path.normcase(os.path.abspath(directory))
        raw_paths = [p.strip() for p in curr_path.split(";") if p.strip()]
        norm_paths = [os.path.normcase(os.path.abspath(p)) for p in raw_paths]

        if norm_dir not in norm_paths:
            raw_paths.append(directory)
            new_path = ";".join(raw_paths)
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            winreg.CloseKey(key)
            broadcast_environment_change()
            return True
        else:
            winreg.CloseKey(key)
            return True
    except Exception as e:
        print(f"Warning: Could not update user registry PATH: {e}")
        return False

def add_directory_to_system_path(directory, elevate_if_needed=True):
    """
    Adds a directory to Windows System-wide (Machine) Environment PATH registry (HKLM).
    Available to ALL users and background services.
    If not running as admin and elevate_if_needed is True, triggers Windows UAC prompt.
    Returns: (success: bool, status_message: str)
    """
    directory = os.path.abspath(directory)
    if sys.platform != "win32":
        return True, "POSIX environment configured"

    norm_dir = os.path.normcase(os.path.abspath(directory))

    # 1. If running as administrator, write directly to HKLM
    if is_admin():
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                0,
                winreg.KEY_READ | winreg.KEY_SET_VALUE
            )
            try:
                curr_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                curr_path = ""

            raw_paths = [p.strip() for p in curr_path.split(";") if p.strip()]
            norm_paths = [os.path.normcase(os.path.abspath(p)) for p in raw_paths]

            if norm_dir not in norm_paths:
                raw_paths.append(directory)
                new_path = ";".join(raw_paths)
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                winreg.CloseKey(key)
                broadcast_environment_change()
                add_directory_to_user_path(directory)
                return True, "Successfully registered in System-wide PATH (All Users)!"
            else:
                winreg.CloseKey(key)
                add_directory_to_user_path(directory)
                return True, "Directory is already present in System-wide PATH."
        except Exception as e:
            return False, f"Failed writing to HKLM registry: {e}"

    # 2. Not running as administrator - use elevation if permitted
    if elevate_if_needed:
        try:
            ps_script = (
                f"$dir = '{directory}'; "
                f"$curr = [Environment]::GetEnvironmentVariable('Path', 'Machine'); "
                f"$parts = $curr -split ';' | Where-Object {{ $_ -ne '' }}; "
                f"if ($parts -notcontains $dir) {{ "
                f"  $new = ($parts + $dir) -join ';'; "
                f"  [Environment]::SetEnvironmentVariable('Path', $new, 'Machine'); "
                f"}}"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command",
                 f"Start-Process powershell -Verb RunAs -Wait -ArgumentList '-NoProfile -Command \"{ps_script}\"'"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            add_directory_to_user_path(directory)

            status = check_path_status(directory)
            if status["in_system_path"]:
                broadcast_environment_change()
                return True, "Successfully elevated and registered in System-wide PATH (All Users)!"
            else:
                return True, "Registered in Windows User PATH (System PATH elevation was skipped or declined)."
        except Exception as e:
            add_directory_to_user_path(directory)
            return True, f"Registered in User PATH (System-wide elevation encountered: {e})"

    # Fallback to User PATH
    add_directory_to_user_path(directory)
    return True, "Registered in User PATH."

def install_platform_tools(target_dir=None, progress_callback=None, register_in_path=True, systemwide=True):
    """
    Downloads official Google Platform-Tools, unpacks them into target_dir,
    stops any running ADB daemons to avoid file locks, adds directory to PATH,
    and validates installation.

    progress_callback(percent: int, message: str)
    Returns: (success: bool, adb_path: str, fastboot_path: str, version: str)
    """
    if not target_dir:
        target_dir = get_default_install_dir(systemwide=systemwide)

    os.makedirs(target_dir, exist_ok=True)
    url = get_platform_tools_url()

    # Step 1: Terminate running ADB processes so Windows does not lock adb.exe during extraction
    if progress_callback:
        progress_callback(2, "Stopping any active ADB server processes...")
    kill_adb_processes()

    if progress_callback:
        progress_callback(5, f"Connecting to {url}...")

    zip_tmp = os.path.join(target_dir, "platform_tools_temp.zip")

    try:
        # Download official ZIP
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) C69HD_Power_Studio/1.1"}
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

        # Kill once more immediately before extraction in case an external tool restarted ADB
        kill_adb_processes()

        with zipfile.ZipFile(zip_tmp, "r") as zf:
            members = zf.namelist()
            total_files = len(members)

            for idx, member in enumerate(members):
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
                    # Retry write if file is briefly held
                    written = False
                    for attempt in range(3):
                        try:
                            with zf.open(member) as source, open(dest_path, "wb") as target:
                                shutil.copyfileobj(source, target)
                            written = True
                            break
                        except PermissionError:
                            kill_adb_processes()
                            time.sleep(0.2)
                    if not written:
                        raise PermissionError(f"Cannot overwrite locked file: {dest_path}")

                if progress_callback and total_files > 0 and idx % 5 == 0:
                    pct = int(75 + (idx / total_files) * 15)  # 75% to 90%
                    progress_callback(pct, f"Extracting {filename}...")

        # Remove temp zip
        try:
            if os.path.exists(zip_tmp):
                os.remove(zip_tmp)
        except Exception:
            pass

        # Locate newly extracted binaries
        exe_suffix = ".exe" if sys.platform == "win32" else ""
        adb_path = os.path.join(target_dir, f"adb{exe_suffix}")
        fastboot_path = os.path.join(target_dir, f"fastboot{exe_suffix}")

        if sys.platform != "win32":
            for p in (adb_path, fastboot_path):
                if os.path.isfile(p):
                    os.chmod(p, 0o755)

        if not os.path.isfile(adb_path):
            return False, None, None, f"adb binary missing from extracted archive in {target_dir}"

        # Add to current process PATH
        curr_path = os.environ.get("PATH", "")
        norm_target = os.path.normcase(os.path.abspath(target_dir))
        proc_paths = [os.path.normcase(os.path.abspath(p.strip())) for p in curr_path.split(os.pathsep) if p.strip()]
        if norm_target not in proc_paths:
            os.environ["PATH"] = f"{target_dir}{os.pathsep}{curr_path}"

        # Register in Windows PATH if requested
        if register_in_path and sys.platform == "win32":
            if progress_callback:
                progress_callback(92, "Registering in Windows environment PATH...")
            if systemwide:
                add_directory_to_system_path(target_dir, elevate_if_needed=True)
            else:
                add_directory_to_user_path(target_dir)

        # Verify installation
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
