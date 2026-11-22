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
from core.device_ops import (
    DeviceOps,
    BUTTON_ACTIONS,
    SIDE_BUTTON_PRESETS,
    SIDE_BUTTON_KEYCODES,
    SIDE_BUTTON_LONG_ACTIONS,
    DEBLOAT_CATALOG,
    CURATED_EINK_APPS
)
from core.scrcpy_manager import ScrcpyManager
from core.clipboard_helper import copy_pil_image_to_clipboard

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

    def test_side_button_mapping_and_presets(self):
        # 1. Test preset catalog integrity
        self.assertTrue(len(SIDE_BUTTON_PRESETS) >= 11)
        self.assertTrue(len(SIDE_BUTTON_KEYCODES) >= 18)
        self.assertIn("none", SIDE_BUTTON_LONG_ACTIONS)
        self.assertIn("power", SIDE_BUTTON_LONG_ACTIONS)
        self.assertIn("fullRefreshScreen", SIDE_BUTTON_LONG_ACTIONS)
        self.assertIn("KEYCODE_POWER", BUTTON_ACTIONS)

        # Check Power/Sleep presets exist
        preset_ids = [p["id"] for p in SIDE_BUTTON_PRESETS]
        self.assertIn("POWER_PAGE", preset_ids)
        self.assertIn("PAGE_POWER", preset_ids)
        self.assertIn("POWER_SLEEP", preset_ids)
        self.assertIn("POWER_BACK", preset_ids)

        # Check Power/Sleep keycodes exist
        kc_names = [k[0] for k in SIDE_BUTTON_KEYCODES]
        self.assertIn("POWER", kc_names)
        self.assertIn("SLEEP", kc_names)
        self.assertIn("WAKEUP", kc_names)

        # 2. Test query parsing with mock output
        mock_kl = (
            "key 115   VOLUME_UP\n"
            "key 114   VOLUME_DOWN\n"
            "key 104   VOLUME_UP\n"
            "key 109   VOLUME_DOWN\n"
        )
        self.adb.run_shell.side_effect = [
            (True, mock_kl, ""),
            (True, "1", ""),
            (True, "fullRefreshScreen", ""),
            (True, "screenshot", "")
        ]
        res = self.ops.get_current_side_button_mapping()
        self.assertEqual(res["top_key"], "VOLUME_UP")
        self.assertEqual(res["bottom_key"], "VOLUME_DOWN")
        self.assertTrue(res["long_press_enabled"])
        self.assertEqual(res["top_long"], "fullRefreshScreen")
        self.assertEqual(res["bottom_long"], "screenshot")
        self.assertEqual(res["preset_id"], "VOLUME_KEYS")

        # 3. Test apply side button mapping
        self.adb.run_shell.side_effect = None
        self.adb.run_shell.return_value = (True, "", "")
        ok, msg = self.ops.apply_side_button_mapping(
            top_key="PAGE_DOWN",
            bottom_key="PAGE_UP",
            top_long="none",
            bottom_long="none"
        )
        self.assertTrue(ok)
        self.assertIn("PAGE_DOWN", msg)
        self.assertIn("PAGE_UP", msg)

        # Verify deployment commands executed
        calls = [str(c[0][0]) for c in self.adb.run_shell.call_args_list]
        self.assertTrue(any("gpio-keys.kl" in c for c in calls))
        self.assertTrue(any("onyx.action.refresh_keymapping" in c for c in calls))

        # 4. Test reset side button mapping
        ok_reset, msg_reset = self.ops.reset_side_button_mapping()
        self.assertTrue(ok_reset)
        self.assertIn("PAGE_UP / PAGE_DOWN", msg_reset)

    def test_power_sleep_side_mapping(self):
        # Verify that POWER and SLEEP keys generate WAKE flag in gpio-keys.kl
        self.adb.run_shell.side_effect = None
        self.adb.run_shell.return_value = (True, "", "")
        ok, msg = self.ops.apply_side_button_mapping(
            top_key="POWER",
            bottom_key="SLEEP",
            top_long="power",
            bottom_long="none"
        )
        self.assertTrue(ok)
        calls = [str(c[0][0]) for c in self.adb.run_shell.call_args_list]
        kl_call = [c for c in calls if "gpio-keys.kl" in c][0]
        self.assertIn("key 104   POWER WAKE", kl_call)
        self.assertIn("key 109   SLEEP WAKE", kl_call)

    def test_debloat_catalog_integrity(self):
        self.assertTrue(len(DEBLOAT_CATALOG) >= 3)
        for cat in DEBLOAT_CATALOG:
            self.assertIn("category", cat)
            self.assertIn("packages", cat)
            for pkg, desc in cat["packages"]:
                self.assertTrue(pkg.startswith("com.") or pkg.startswith("vendor."))
                self.assertTrue(len(desc) > 0)

    def test_curated_apps_catalog(self):
        self.assertTrue(len(CURATED_EINK_APPS) >= 8)
        names = [app["name"] for app in CURATED_EINK_APPS]
        self.assertNotIn("Taskbar", names)
        self.assertIn("Komi Store", names)
        self.assertIn("EinkBro", names)
        self.assertIn("Olauncher", names)
        self.assertIn("Librera Reader", names)
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

    def test_unlock_bootloader_fastboot(self):
        # 1. Success on flashing unlock
        self.adb.run_fastboot.return_value = (True, "OKAY", "")
        ok, msg = self.ops.unlock_bootloader_fastboot()
        self.assertTrue(ok)
        self.adb.run_fastboot.assert_called_with("flashing", "unlock")

        # 2. Fallback to oem unlock
        self.adb.run_fastboot.side_effect = [
            (False, "", "unknown command"),
            (True, "OKAY", "")
        ]
        ok, msg = self.ops.unlock_bootloader_fastboot()
        self.assertTrue(ok)

        # 3. Both fail
        self.adb.run_fastboot.side_effect = [
            (False, "", "failed 1"),
            (False, "", "failed 2")
        ]
        ok, msg = self.ops.unlock_bootloader_fastboot()
        self.assertFalse(ok)
        self.adb.run_fastboot.side_effect = None

    def test_push_boot_to_device(self):
        # 1. Non-existent file
        ok, msg = self.ops.push_boot_to_device("non_existent_boot_image.img")
        self.assertFalse(ok)
        self.assertIn("not found", msg)

        # 2. Existing file push
        test_file = os.path.join(BASE_DIR, "tests", "_test_push_boot.img")
        with open(test_file, "wb") as f:
            f.write(b"MOCK_BOOT_IMAGE_DATA")
        try:
            self.adb.run_shell.return_value = (True, "", "")
            self.adb.run_adb.return_value = (True, "1 file pushed", "")
            ok, msg = self.ops.push_boot_to_device(test_file)
            self.assertTrue(ok)
            self.assertIn("/sdcard/Download/stock_boot.img", msg)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_pull_latest_magisk_patched_boot(self):
        # 1. No patched file found on device
        self.adb.run_shell.return_value = (True, "", "")
        ok, path, msg = self.ops.pull_latest_magisk_patched_boot()
        self.assertFalse(ok)
        self.assertIsNone(path)
        self.assertIn("No Magisk-patched", msg)

        # 2. Patched file found and pulled
        test_out_dir = os.path.join(BASE_DIR, "tests", "_test_pull_dir")
        os.makedirs(test_out_dir, exist_ok=True)
        try:
            self.adb.run_shell.return_value = (True, "/sdcard/Download/magisk_patched_25200_abcde.img\n", "")
            
            # Simulate pull creating local file
            def mock_pull(*args):
                dest = args[2]
                with open(dest, "wb") as f:
                    f.write(b"MOCK_PATCHED_BOOT_BYTES" * 100)
                return True, "1 file pulled", ""

            self.adb.run_adb.side_effect = mock_pull
            ok, local_path, msg = self.ops.pull_latest_magisk_patched_boot(dest_dir=test_out_dir)
            self.assertTrue(ok)
            self.assertIsNotNone(local_path)
            self.assertTrue(os.path.exists(local_path))
            self.assertIn("magisk_patched_25200_abcde.img", local_path)
        finally:
            self.adb.run_adb.side_effect = None
            shutil.rmtree(test_out_dir, ignore_errors=True)

    def test_launch_magisk_app(self):
        self.adb.run_shell.return_value = (True, "Events injected: 1", "")
        ok, msg = self.ops.launch_magisk_app()
        self.assertTrue(ok)
        self.assertIn("Magisk app opened", msg)

        self.adb.run_shell.return_value = (False, "", "Activity not found")
        ok, msg = self.ops.launch_magisk_app()
        self.assertFalse(ok)

    def test_verify_root_access(self):
        self.adb.run_shell.return_value = (True, "uid=0(root) gid=0(root) groups=0(root)\n", "")
        ok, msg = self.ops.verify_root_access()
        self.assertTrue(ok)
        self.assertIn("Root verified", msg)

        self.adb.run_shell.return_value = (False, "uid=2000(shell) gid=2000(shell)\n", "")
        ok, msg = self.ops.verify_root_access()
        self.assertFalse(ok)

    def test_boot_recovery_fastboot(self):
        # 1. Missing file
        ok, msg = self.ops.boot_recovery_fastboot("non_existent_rec.img")
        self.assertFalse(ok)
        self.assertIn("not found", msg)

        # 2. Existing file - Fastboot boot success
        test_file = os.path.join(BASE_DIR, "tests", "_test_rec.img")
        with open(test_file, "wb") as f:
            f.write(b"MOCK_RECOVERY_IMAGE_DATA")
        try:
            self.adb.run_fastboot.return_value = (True, "booting...", "")
            ok, msg = self.ops.boot_recovery_fastboot(test_file)
            self.assertTrue(ok)
            self.assertIn("tether-booting", msg)
            self.adb.run_fastboot.assert_called_with("boot", test_file)

            # 3. Fastboot boot failure
            self.adb.run_fastboot.return_value = (False, "", "FAILED (remote: unknown command)")
            ok, msg = self.ops.boot_recovery_fastboot(test_file)
            self.assertFalse(ok)
            self.assertIn("Fastboot boot failed", msg)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_flash_recovery_fastboot(self):
        # 1. Missing file
        ok, msg = self.ops.flash_recovery_fastboot("non_existent_rec.img")
        self.assertFalse(ok)

        # 2. Existing file - Flash slotted recovery with reboot
        test_file = os.path.join(BASE_DIR, "tests", "_test_rec_flash.img")
        with open(test_file, "wb") as f:
            f.write(b"MOCK_RECOVERY_IMAGE_DATA")
        try:
            self.adb.run_fastboot.side_effect = [
                (True, "writing 'recovery_a'...", ""),
                (True, "rebooting...", "")
            ]
            ok, msg = self.ops.flash_recovery_fastboot(test_file, slot="_a", reboot_to_recovery=True)
            self.assertTrue(ok)
            self.assertIn("flashed successfully", msg)

            # 3. Slotted fails, unslotted fallback
            self.adb.run_fastboot.side_effect = [
                (False, "", "unknown partition recovery_a"),
                (True, "writing 'recovery'...", ""),
                (True, "rebooting...", "")
            ]
            ok, msg = self.ops.flash_recovery_fastboot(test_file, slot="_a", reboot_to_recovery=True)
            self.assertTrue(ok)
            self.assertIn("flashed successfully", msg)
        finally:
            self.adb.run_fastboot.side_effect = None
            if os.path.exists(test_file):
                os.remove(test_file)

class TestScrcpyManager(unittest.TestCase):
    def setUp(self):
        self.scrcpy = ScrcpyManager()

    def test_availability(self):
        # Scrcpy was verified installed on this machine
        self.assertTrue(self.scrcpy.is_available())

    def test_cross_platform_scrcpy_locations(self):
        # Test locate_scrcpy_executable returns a valid string on all platforms
        exe = ScrcpyManager.locate_scrcpy_executable()
        self.assertIsInstance(exe, str)
        self.assertTrue(len(exe) > 0)

        # Mocking darwin
        with patch("sys.platform", "darwin"):
            with patch("shutil.which", return_value=None):
                with patch("os.path.isfile", side_effect=lambda p: p == "/opt/homebrew/bin/scrcpy"):
                    self.assertEqual(ScrcpyManager.locate_scrcpy_executable(), "/opt/homebrew/bin/scrcpy")

        # Mocking linux
        with patch("sys.platform", "linux"):
            with patch("shutil.which", return_value=None):
                with patch("os.path.isfile", side_effect=lambda p: p == "/usr/bin/scrcpy"):
                    self.assertEqual(ScrcpyManager.locate_scrcpy_executable(), "/usr/bin/scrcpy")

    def test_stop_when_not_running(self):
        # Should execute safely without exception
        self.scrcpy.stop()
        self.assertFalse(self.scrcpy.is_running())

class TestADBInstaller(unittest.TestCase):
    def test_find_platform_tools(self):
        from core.adb_installer import find_existing_platform_tools, get_platform_tools_url, get_default_install_dir
        info = find_existing_platform_tools()
        self.assertIn("installed", info)
        self.assertIn("adb", info)
        self.assertIn("fastboot", info)
        self.assertIn("version", info)
        self.assertTrue(info["installed"])

        url = get_platform_tools_url()
        self.assertTrue(url.startswith("https://dl.google.com/android/repository/platform-tools-latest-"))

        default_dir = get_default_install_dir()
        self.assertTrue(os.path.isabs(default_dir))
        self.assertTrue(default_dir.endswith("platform-tools"))

    def test_adb_installer_helpers(self):
        from core.adb_installer import (
            kill_adb_processes,
            check_path_status,
            get_default_install_dir,
            is_admin
        )
        # 1. kill_adb_processes should run safely
        kill_adb_processes()

        # 2. check_path_status returns expected keys
        status = check_path_status(r"C:\platform-tools" if sys.platform == "win32" else "/usr/local/bin")
        self.assertIn("in_user_path", status)
        self.assertIn("in_system_path", status)
        self.assertIn("in_process_path", status)

        # 3. get_default_install_dir with systemwide True vs False
        sys_dir = get_default_install_dir(systemwide=True)
        user_dir = get_default_install_dir(systemwide=False)
        self.assertTrue(os.path.isabs(sys_dir))
        self.assertTrue(os.path.isabs(user_dir))
        if sys.platform == "win32":
            self.assertEqual(sys_dir, r"C:\platform-tools")

        # 4. is_admin returns a bool
        self.assertIsInstance(is_admin(), bool)

    def test_adb_manager_availability(self):
        adb = ADBManager()
        self.assertTrue(adb.is_available())
        tool_info = adb.get_tool_info()
        self.assertTrue(tool_info["installed"])
        self.assertIsNotNone(tool_info["adb_path"])

    def test_gui_device_status_update_and_adb_fallback(self):
        from gui.main_window import MainWindow
        adb = ADBManager()
        ops = DeviceOps(adb)
        scrcpy = ScrcpyManager(log_callback=adb.log)
        app = MainWindow(adb, ops, scrcpy)
        
        def is_packed(widget):
            try:
                return bool(widget.pack_info())
            except Exception:
                return False

        try:
            # 1. Normal connected status
            info = {
                "connected": True, "mode": "adb", "rooted": True,
                "model": "C69HD", "manufacturer": "ONYX", "device": "c69hd",
                "display_id": "1.0.0", "android_version": "11", "boot_slot": "_a",
                "unlocked": True, "battery_level": "95%", "battery_charging": "No"
            }
            app._update_ui_device_status(info)
            self.assertIn("CONNECTED", app.lbl_status_badge.cget("text"))
            self.assertFalse(is_packed(app.btn_sidebar_install_adb))

            # 2. Simulated missing ADB status
            with patch.object(adb, "is_available", return_value=False):
                with patch.object(adb, "get_tool_info", return_value={"installed": False, "adb_path": None, "fastboot_path": None, "version": None}):
                    app._update_ui_device_status({"connected": False, "mode": "disconnected"})
                    self.assertEqual(app.lbl_status_badge.cget("text"), "ADB MISSING")
                    self.assertEqual(app.lbl_device_title.cget("text"), "ADB Not Detected")
                    self.assertTrue(is_packed(app.btn_sidebar_install_adb))
        finally:
            app.destroy()

class TestCrossPlatformClipboard(unittest.TestCase):
    def test_clipboard_copy(self):
        img = Image.new("RGB", (100, 100), color="red")
        # On current platform, verify function executes and returns a bool and message
        ok, msg = copy_pil_image_to_clipboard(img)
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(msg, str)
        if sys.platform == "win32":
            self.assertTrue(ok)

        # Test simulated darwin
        with patch("sys.platform", "darwin"):
            with patch("subprocess.run") as mock_sub:
                mock_sub.return_value = MagicMock(returncode=0)
                ok_mac, msg_mac = copy_pil_image_to_clipboard(img)
                self.assertTrue(ok_mac)
                self.assertIn("macOS", msg_mac)

        # Test simulated linux xclip
        with patch("sys.platform", "linux"):
            with patch("shutil.which", side_effect=lambda bin_name: "/usr/bin/xclip" if bin_name == "xclip" else None):
                with patch("subprocess.run") as mock_sub:
                    mock_sub.return_value = MagicMock(returncode=0)
                    ok_lin, msg_lin = copy_pil_image_to_clipboard(img)
                    self.assertTrue(ok_lin)
                    self.assertIn("X11", msg_lin)

if __name__ == "__main__":
    unittest.main()
