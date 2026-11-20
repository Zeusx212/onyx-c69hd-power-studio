"""
Scrcpy integration manager for Onyx Boox C69HD.
Supports both native embedded mirroring (inside a GUI frame) and standalone window mode,
with E-Ink performance profiles (low FPS, screen-off while controlling, recording).
"""

import subprocess
import shutil
import threading
import time
import os
import glob
import collections
import ctypes
from ctypes import c_void_p, c_int, c_long

user32 = ctypes.windll.user32 if os.name == 'nt' else None
if user32:
    try:
        user32.SetParent.argtypes = [c_void_p, c_void_p]
        user32.SetParent.restype = c_void_p
        user32.SetWindowPos.argtypes = [c_void_p, c_void_p, c_int, c_int, c_int, c_int, c_int]
        user32.SetWindowPos.restype = c_int
    except Exception:
        pass

class ScrcpyManager:
    @staticmethod
    def locate_scrcpy_executable():
        """Find scrcpy binary on PATH, in Winget packages, or in standard install locations."""
        # 1. Check system PATH
        path_bin = shutil.which("scrcpy")
        if path_bin and os.path.isfile(path_bin):
            return path_bin

        # 2. Check WinGet package directories
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

        # 3. Common fallback locations
        fallback_paths = [
            r"C:\scrcpy\scrcpy.exe",
            r"C:\tools\scrcpy\scrcpy.exe",
            os.path.expanduser(r"~\scrcpy\scrcpy.exe"),
            os.path.expanduser(r"~\AppData\Local\Programs\scrcpy\scrcpy.exe"),
            r"C:\ProgramData\chocolatey\bin\scrcpy.exe",
        ]
        for p in fallback_paths:
            if os.path.isfile(p):
                return p

        return "scrcpy"

    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.scrcpy_bin = self.locate_scrcpy_executable()
        self.process = None
        self.embedded_hwnd = None
        self.container_hwnd = None
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
        h = None
        self._user_stopped = True
        with self._lock:
            if self.process is not None and self.process.poll() is None:
                proc = self.process
            h = self.embedded_hwnd
            self.process = None
            self.embedded_hwnd = None

        if h and user32:
            try:
                user32.ShowWindow(h, 0)
                user32.SetParent(h, 0)
            except Exception:
                pass

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

    def start(self, container_hwnd=None, options=None, on_stop=None):
        if self.is_running():
            self.stop()

        self._user_stopped = False

        # Re-verify binary location if needed
        if not self.is_available():
            self.scrcpy_bin = self.locate_scrcpy_executable()
            if not self.is_available():
                return False, f"scrcpy executable not found. Please install scrcpy or add it to PATH."

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
        embedded = options.get("embedded", True) and (container_hwnd is not None) and (os.name == 'nt')

        timestamp = int(time.time() * 1000)
        window_title = f"Onyx_C69HD_Mirror_{timestamp}" if embedded else "Onyx Boox C69HD Screen Mirror"

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
        if always_on_top and not embedded:
            cmd.append("--always-on-top")
        if read_only:
            cmd.append("--no-control")
        if record_file:
            cmd.append(f"--record={record_file}")

        cmd.append(f"--window-title={window_title}")
        if embedded:
            cmd.append("--window-borderless")

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

        if embedded and user32:
            self.container_hwnd = container_hwnd
            threading.Thread(target=self._embed_worker, args=(window_title, container_hwnd, proc), daemon=True).start()

        # Start process monitor thread
        threading.Thread(target=self._process_monitor_worker, args=(proc,), daemon=True).start()
        return True, "Scrcpy mirror started successfully."

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

    def _embed_worker(self, target_title, c_hwnd, proc):
        found = []
        def enum_cb(h, lp):
            length = user32.GetWindowTextLengthW(h)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(h, buff, length + 1)
                if buff.value == target_title:
                    found.append(h)
                    return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        for _ in range(50):  # poll up to 5 seconds
            with self._lock:
                if self.process is not proc or proc.poll() is not None:
                    return
            time.sleep(0.1)
            try:
                user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
            except Exception:
                pass
            if found:
                break

        if found:
            h = found[0]
            with self._lock:
                if self.process is not proc:
                    return
                self.embedded_hwnd = h

            try:
                self.log(f"Found scrcpy window HWND: {h}. Reparenting into container {c_hwnd}...")
                user32.SetParent(h, c_hwnd)

                rect = (ctypes.c_long * 4)()
                user32.GetClientRect(c_hwnd, rect)
                w = max(rect[2] - rect[0], 100)
                h_dim = max(rect[3] - rect[1], 100)
                SWP_SHOWWINDOW = 0x0040
                user32.SetWindowPos(h, 0, 0, 0, w, h_dim, SWP_SHOWWINDOW)
                self.log("Scrcpy successfully embedded into GUI window!")
            except Exception as e:
                self.log(f"Error reparenting scrcpy window: {e}")

    def resize_embedded(self, width, height):
        with self._lock:
            h = self.embedded_hwnd
        if h and user32 and width > 50 and height > 50:
            try:
                SWP_NOZORDER = 0x0004
                user32.SetWindowPos(h, 0, 0, 0, width, height, SWP_NOZORDER)
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
                self.embedded_hwnd = None

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
