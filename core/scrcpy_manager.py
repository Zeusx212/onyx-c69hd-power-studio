"""
Scrcpy integration manager for Onyx Boox C69HD.
Launches and manages native hardware-accelerated screen mirroring with E-Ink performance profiles
(15 FPS, screen-off while controlling, keep-awake, MP4 recording).
"""

import subprocess
import shutil
import threading
import time
import os
import glob
import collections

class ScrcpyManager:
    @staticmethod
    def locate_scrcpy_executable():
        """Find scrcpy binary on PATH, in package managers, or in standard OS install locations."""
        import sys

        # 1. Check system PATH
        path_bin = shutil.which("scrcpy")
        if path_bin and os.path.isfile(path_bin):
            return path_bin

        # 2. Check Windows locations
        if sys.platform == "win32":
            local_app = os.environ.get("LOCALAPPDATA", "")
            if local_app:
                winget_root = os.path.join(local_app, "Microsoft", "WinGet", "Packages")
                if os.path.isdir(winget_root):
                    try:
                        candidates = glob.glob(os.path.join(winget_root, "**", "scrcpy.exe"), recursive=True)
                        if candidates:
                            for c in candidates:
                                if os.path.isfile(c):
                                    return c
                    except Exception:
                        pass

            win_fallbacks = [
                r"C:\scrcpy\scrcpy.exe",
                r"C:\tools\scrcpy\scrcpy.exe",
                os.path.expanduser(r"~\scrcpy\scrcpy.exe"),
                os.path.expanduser(r"~\AppData\Local\Programs\scrcpy\scrcpy.exe"),
                r"C:\ProgramData\chocolatey\bin\scrcpy.exe",
            ]
            for p in win_fallbacks:
                if os.path.isfile(p):
                    return p

        # 3. Check macOS locations (Homebrew Apple Silicon / Intel, MacPorts)
        elif sys.platform == "darwin":
            mac_fallbacks = [
                "/opt/homebrew/bin/scrcpy",
                "/usr/local/bin/scrcpy",
                "/opt/local/bin/scrcpy",
                os.path.expanduser("~/homebrew/bin/scrcpy"),
                os.path.expanduser("~/.local/bin/scrcpy"),
            ]
            for p in mac_fallbacks:
                if os.path.isfile(p):
                    return p

        # 4. Check Linux locations (Debian/Ubuntu, Arch, Fedora, Snap)
        else:
            linux_fallbacks = [
                "/usr/bin/scrcpy",
                "/usr/local/bin/scrcpy",
                "/snap/bin/scrcpy",
                os.path.expanduser("~/.local/bin/scrcpy"),
                "/var/lib/flatpak/exports/bin/com.github.rom1v.scrcpy",
            ]
            for p in linux_fallbacks:
                if os.path.isfile(p):
                    return p

        return "scrcpy"

    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.scrcpy_bin = self.locate_scrcpy_executable()
        self.process = None
        self.on_stop_callback = None
        self.recent_logs = collections.deque(maxlen=30)
        self._lock = threading.Lock()
        self._user_stopped = False

    def log(self, msg):
        try:
            self.recent_logs.append(msg)
            if self.log_callback:
                self.log_callback(f"[scrcpy] {msg}")
            else:
                print(f"[scrcpy] {msg}")
        except Exception:
            pass

    def is_available(self):
        """Returns True if a valid scrcpy binary was located."""
        if os.path.isabs(self.scrcpy_bin):
            return os.path.isfile(self.scrcpy_bin)
        return shutil.which(self.scrcpy_bin) is not None

    def get_binary_path(self):
        return self.scrcpy_bin

    def is_running(self):
        with self._lock:
            return self.process is not None and self.process.poll() is None

    def stop(self):
        proc = None
        self._user_stopped = True
        with self._lock:
            if self.process is not None and self.process.poll() is None:
                proc = self.process
            self.process = None

        if proc:
            self.log("Stopping scrcpy process...")
            def _stop_worker(p):
                try:
                    p.terminate()
                    try:
                        p.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        p.kill()
                        p.wait(timeout=1.0)
                except Exception:
                    try:
                        p.kill()
                    except Exception:
                        pass
            threading.Thread(target=_stop_worker, args=(proc,), daemon=True).start()

    def start(self, options=None, on_stop=None):
        if self.is_running():
            self.stop()

        self._user_stopped = False

        # Re-verify binary location if needed
        if not self.is_available():
            self.scrcpy_bin = self.locate_scrcpy_executable()
            if not self.is_available():
                return False, "scrcpy executable not found. Please install scrcpy or add it to PATH."

        self.on_stop_callback = on_stop
        if not options:
            options = {}

        serial = options.get("serial")
        max_size = options.get("max_size", "758")
        max_fps = options.get("max_fps", "15")
        bit_rate = options.get("bit_rate", "2M")
        turn_screen_off = options.get("turn_screen_off", False)
        stay_awake = options.get("stay_awake", True)
        always_on_top = options.get("always_on_top", False)
        read_only = options.get("read_only", False)
        record_file = options.get("record_file", None)

        cmd = [self.scrcpy_bin]

        # Bind to specific serial if available
        if serial and serial not in ("N/A", "Unknown", ""):
            cmd.extend(["-s", str(serial)])

        cmd.append("--no-audio")

        if max_size and max_size != "native":
            cmd.append(f"--max-size={max_size}")
        if max_fps:
            cmd.append(f"--max-fps={max_fps}")
        if bit_rate:
            cmd.append(f"--video-bit-rate={bit_rate}")
        if turn_screen_off:
            cmd.append("--turn-screen-off")
        if stay_awake:
            cmd.append("--stay-awake")
        if always_on_top:
            cmd.append("--always-on-top")
        if read_only:
            cmd.append("--no-control")
        if record_file:
            cmd.append(f"--record={record_file}")

        cmd.append("--window-title=Onyx Boox C69HD Screen Mirror")

        self.log(f"Starting command: {' '.join(cmd)}")
        self.recent_logs.clear()

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            with self._lock:
                self.process = proc
        except Exception as e:
            self.log(f"Failed to launch scrcpy: {e}")
            return False, str(e)

        # Start continuous output streaming thread
        threading.Thread(target=self._stream_reader_worker, args=(proc,), daemon=True).start()

        # Start process monitor thread
        threading.Thread(target=self._process_monitor_worker, args=(proc,), daemon=True).start()
        return True, "Scrcpy mirror window launched successfully."

    def _stream_reader_worker(self, proc):
        """Continuously reads scrcpy stdout/stderr to prevent pipe buffer deadlocks."""
        try:
            if proc.stdout:
                for line in iter(proc.stdout.readline, ''):
                    clean = line.strip()
                    if clean:
                        self.log(clean)
        except Exception:
            pass

    def _process_monitor_worker(self, proc):
        # Wait for this specific process to terminate
        try:
            proc.wait()
        except Exception:
            pass

        exit_code = proc.returncode
        self.log(f"Scrcpy process terminated with return code {exit_code}")

        with self._lock:
            if self.process is proc:
                self.process = None

        error_msg = None
        if not self._user_stopped and exit_code not in (0, None):
            # Collect error lines from recent_logs
            err_lines = [l for l in self.recent_logs if "error" in l.lower() or "fail" in l.lower() or "warn" in l.lower()]
            if err_lines:
                error_msg = "\n".join(err_lines[-5:])
            elif self.recent_logs:
                error_msg = "\n".join(list(self.recent_logs)[-5:])
        elif self._user_stopped:
            exit_code = 0

        if self.on_stop_callback:
            try:
                self.on_stop_callback(exit_code, error_msg)
            except Exception:
                pass
