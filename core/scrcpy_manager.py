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
import ctypes

user32 = ctypes.windll.user32 if os.name == 'nt' else None

class ScrcpyManager:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.scrcpy_bin = shutil.which("scrcpy") or "scrcpy"
        self.process = None
        self.embedded_hwnd = None
        self.container_hwnd = None
        self._monitor_thread = None
        self.on_stop_callback = None

    def log(self, msg):
        if self.log_callback:
            self.log_callback(f"[scrcpy] {msg}")
        else:
            print(f"[scrcpy] {msg}")

    def is_available(self):
        return shutil.which("scrcpy") is not None

    def is_running(self):
        return self.process is not None and self.process.poll() is None

    def stop(self):
        if self.is_running():
            self.log("Stopping scrcpy process...")
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
        self.process = None
        self.embedded_hwnd = None
        if self.on_stop_callback:
            self.on_stop_callback()

    def start(self, container_hwnd=None, options=None, on_stop=None):
        if self.is_running():
            self.stop()

        self.on_stop_callback = on_stop
        if not options:
            options = {}

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

        cmd = [self.scrcpy_bin, "--no-audio"]
        
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

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
        except Exception as e:
            self.log(f"Failed to launch scrcpy: {e}")
            return False, str(e)

        if embedded and user32:
            self.container_hwnd = container_hwnd
            # Start background thread to locate and dock the window
            threading.Thread(target=self._embed_worker, args=(window_title, container_hwnd), daemon=True).start()

        # Start process monitor thread
        threading.Thread(target=self._process_monitor_worker, daemon=True).start()
        return True, "Scrcpy mirror started successfully."

    def _embed_worker(self, target_title, c_hwnd):
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
        for _ in range(40): # up to 4 seconds
            if not self.is_running():
                return
            time.sleep(0.1)
            user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
            if found:
                break

        if found:
            self.embedded_hwnd = found[0]
            self.log(f"Found scrcpy window HWND: {self.embedded_hwnd}. Docking into container {c_hwnd}...")
            user32.SetParent(self.embedded_hwnd, c_hwnd)
            # Fetch container dimensions
            rect = (ctypes.c_long * 4)()
            user32.GetClientRect(c_hwnd, rect)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            SWP_SHOWWINDOW = 0x0040
            user32.SetWindowPos(self.embedded_hwnd, 0, 0, 0, w, h, SWP_SHOWWINDOW)
            self.log("Scrcpy successfully embedded into GUI window!")

    def resize_embedded(self, width, height):
        if self.embedded_hwnd and user32:
            SWP_NOZORDER = 0x0004
            user32.SetWindowPos(self.embedded_hwnd, 0, 0, 0, width, height, SWP_NOZORDER)

    def _process_monitor_worker(self):
        if not self.process:
            return
        # Wait for process exit
        self.process.wait()
        self.log(f"Scrcpy process exited with code {self.process.returncode}")
        self.embedded_hwnd = None
        if self.on_stop_callback:
            self.on_stop_callback()
