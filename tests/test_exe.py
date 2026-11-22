"""
Automated unit test and integrity verification for the compiled Windows standalone executable:
dist/Onyx_C69HD_Power_Studio/Onyx_C69HD_Power_Studio.exe
"""

import os
import sys
import time
import subprocess
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE_PATH = os.path.join(BASE_DIR, "dist", "Onyx_C69HD_Power_Studio", "Onyx_C69HD_Power_Studio.exe")
INTERNAL_DIR = os.path.join(BASE_DIR, "dist", "Onyx_C69HD_Power_Studio", "_internal")

class TestExecutableIntegrity(unittest.TestCase):
    def test_exe_binary_exists_and_size(self):
        self.assertTrue(os.path.isfile(EXE_PATH), f"Executable not found at: {EXE_PATH}")
        size_bytes = os.path.getsize(EXE_PATH)
        # Binary should be > 1 MB
        self.assertGreater(size_bytes, 1024 * 1024, f"Binary appears too small ({size_bytes} bytes)")

    def test_bundled_assets_present(self):
        required_assets = [
            os.path.join(INTERNAL_DIR, "assets", "bootanimation.zip"),
            os.path.join(INTERNAL_DIR, "assets", "magisk.apk"),
            os.path.join(INTERNAL_DIR, "assets", "c69hd-wake.zip"),
            os.path.join(INTERNAL_DIR, "assets", "shutdown-default.png"),
            os.path.join(INTERNAL_DIR, "assets", "standby-1.png"),
            os.path.join(INTERNAL_DIR, "assets", "twrp_c69hd_recovery.img"),
            os.path.join(BASE_DIR, "dist", "Onyx_C69HD_Power_Studio", "backups", "twrp_c69hd_recovery.img"),
        ]
        for asset in required_assets:
            self.assertTrue(
                os.path.isfile(asset),
                f"Missing bundled asset in executable distribution: {asset}"
            )

    def test_exe_launch_smoke_test(self):
        """
        Launches the compiled EXE in a subprocess, verifies it stays alive
        and does not crash immediately due to missing DLLs or corrupt bytecode,
        then terminates cleanly.
        """
        if sys.platform != "win32":
            self.skipTest("Windows executable test only runs on Windows platform.")

        proc = subprocess.Popen(
            [EXE_PATH],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=os.path.dirname(EXE_PATH)
        )
        try:
            # Allow GUI mainloop to spin up for 2.5 seconds
            time.sleep(2.5)
            # Check if process crashed or exited prematurely
            poll_ret = proc.poll()
            self.assertIsNone(
                poll_ret,
                f"Executable crashed or exited prematurely with code {poll_ret}!"
            )
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()

if __name__ == "__main__":
    unittest.main()
