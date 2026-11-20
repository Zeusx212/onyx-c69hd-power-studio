"""
Unit test suite for Onyx Boox C69HD Customizer.
Validates ADB manager, device operations, scrcpy integration,
button remapping, debloat catalog, settings parsing, and image processing.
"""

import unittest
import os
import sys
import json
import zipfile
import shutil
from unittest.mock import MagicMock, patch
from PIL import Image

# Add root directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.adb_manager import ADBManager
from core.device_ops import DeviceOps, BUTTON_ACTIONS, DEBLOAT_CATALOG, CURATED_EINK_APPS
from core.scrcpy_manager import ScrcpyManager

class TestADBManager(unittest.TestCase):
    def setUp(self):
        self.adb = ADBManager()

    def test_binaries_present(self):
        self.assertIsNotNone(self.adb.adb_bin)
        self.assertIsNotNone(self.adb.fastboot_bin)

    def test_run_cmd_failure_handling(self):
        # Invalid command should fail gracefully without unhandled exception
        success, stdout, stderr = self.adb.run_adb("non_existent_command_xyz123")
        self.assertFalse(success)

    def test_device_info_structure(self):
        info = self.adb.get_connected_device_info()
        self.assertIsInstance(info, dict)
        self.assertIn("connected", info)
        self.assertIn("boot_slot", info)
        self.assertIn("unlocked", info)
        self.assertIn("rooted", info)
        self.assertIn("model", info)

    def test_ip_parsing(self):
        # Mock route output
        sample_route = "192.168.1.0/24 proto kernel scope link src 192.168.1.42\n"
        with patch.object(self.adb, 'run_shell', return_value=(True, sample_route, "")):
            ip = self.adb.get_device_ip()
            self.assertEqual(ip, "192.168.1.42")

class TestDeviceOps(unittest.TestCase):
    def setUp(self):
        self.adb = MagicMock()
        self.ops = DeviceOps(self.adb)

    def test_button_mapping_payload(self):
        # Test applying Recent Apps
        self.ops.apply_button_mapping(long_action="KEYCODE_APP_SWITCH", short_action="")
        calls = [c[0][0] for c in self.adb.run_shell.call_args_list]
        
        # Verify JSON payload in settings put
        payload_call = [c for c in calls if "KEYCODE_BACK" in c][0]
        self.assertIn('"longPressAction":"KEYCODE_APP_SWITCH"', payload_call)
        self.assertIn('"shortPressAction":""', payload_call)
        
        # Verify broadcast
        broadcast_call = [c for c in calls if "onyx.action.refresh_keymapping" in c]
        self.assertTrue(len(broadcast_call) > 0)

    def test_button_mapping_query_parsing(self):
        sample_json = '{"keySet":["KEYCODE_BACK"],"shortPressAction":"","longPressAction":"KEYCODE_APP_SWITCH","repeat":false}'
        self.adb.run_shell.side_effect = [
            (True, sample_json, ""),
            (True, "0", "")
        ]
        res = self.ops.get_current_button_mapping()
        self.assertEqual(res["longPressAction"], "KEYCODE_APP_SWITCH")
        self.assertEqual(res["shortPressAction"], "")
        self.assertFalse(res["shortPressEnabled"])

    def test_debloat_catalog_integrity(self):
        self.assertTrue(len(DEBLOAT_CATALOG) >= 3)
        for cat in DEBLOAT_CATALOG:
            self.assertIn("category", cat)
            self.assertIn("packages", cat)
            for pkg, desc in cat["packages"]:
                self.assertTrue(pkg.startswith("com.") or pkg.startswith("vendor."))
                self.assertTrue(len(desc) > 0)

    def test_curated_apps_catalog(self):
        self.assertTrue(len(CURATED_EINK_APPS) >= 5)
        for app in CURATED_EINK_APPS:
            self.assertIn("name", app)
            self.assertIn("url", app)
            self.assertTrue(app["url"].startswith("http"))

    def test_image_processing_carta_resolution(self):
        # Create a test square image
        test_src = os.path.join(BASE_DIR, "tests", "_test_in.png")
        test_dest = os.path.join(BASE_DIR, "tests", "_test_out.png")
        
        img = Image.new("RGB", (500, 500), color="blue")
        img.save(test_src)

        try:
            ok = self.ops.process_image_for_c69hd(test_src, test_dest, convert_grayscale=True)
            self.assertTrue(ok)
            self.assertTrue(os.path.exists(test_dest))

            with Image.open(test_dest) as res_img:
                self.assertEqual(res_img.size, (758, 1024))
                self.assertEqual(res_img.mode, "L") # Grayscale
        finally:
            if os.path.exists(test_src): os.remove(test_src)
            if os.path.exists(test_dest): os.remove(test_dest)

    def test_bootanimation_zip_creation(self):
        test_dir = os.path.join(BASE_DIR, "tests", "_test_anim")
        os.makedirs(test_dir, exist_ok=True)
        frame1 = os.path.join(test_dir, "001.png")
        frame2 = os.path.join(test_dir, "002.png")
        out_zip = os.path.join(test_dir, "bootanim.zip")

        Image.new("RGB", (100, 100), color="black").save(frame1)
        Image.new("RGB", (100, 100), color="white").save(frame2)

        try:
            self.ops.create_bootanimation_zip([frame1, frame2], out_zip, fps=2)
            self.assertTrue(os.path.exists(out_zip))
            
            with zipfile.ZipFile(out_zip, 'r') as z:
                names = z.namelist()
                self.assertIn("desc.txt", names)
                desc = z.read("desc.txt").decode()
                self.assertIn("758 1024 2", desc)
                # Verify uncompressed (ZIP_STORED)
                for info in z.infolist():
                    self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

class TestScrcpyManager(unittest.TestCase):
    def setUp(self):
        self.scrcpy = ScrcpyManager()

    def test_availability(self):
        # Scrcpy was verified installed on this machine
        self.assertTrue(self.scrcpy.is_available())

    def test_stop_when_not_running(self):
        # Should execute safely without exception
        self.scrcpy.stop()
        self.assertFalse(self.scrcpy.is_running())

if __name__ == "__main__":
    unittest.main()
