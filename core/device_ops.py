"""
Device operations controller for Onyx Boox C69HD.
Implements partition backup, Magisk rooting, hardware button remapping,
debloating, personalization (screensavers, boot animations), and system tweaks.
"""

import os
import json
import time
import zipfile
import shutil

# Try importing Pillow for image processing and thumbnail generation
try:
    from PIL import Image, ImageOps
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

# Available button mapping actions identified from Onyx ROM analysis
BUTTON_ACTIONS = {
    "KEYCODE_APP_SWITCH": "Recent Apps / App Switcher (Recommended for C69HD)",
    "fullRefreshScreen": "Full Screen E-Ink Refresh (Clears Ghosting)",
    "screenshot": "Take Screenshot",
    "showRefreshModeDialog": "Open E-Ink Refresh Mode Dialog",
    "back_to_home": "Return to Home Screen",
    "toggleA2": "Toggle A2 High-Speed Refresh Mode",
    "": "Standard Back Key Event",
    "toggleFrontLight": "Factory Default (Toggle Frontlight - No HW on C69HD)",
}

# Curated list of debloat targets for C69HD
DEBLOAT_CATALOG = [
    {
        "category": "Qualcomm Telephony & Cellular (No SIM Tray on C69HD)",
        "packages": [
            ("com.qualcomm.qti.sva", "Snapdragon Voice Activation (Hotword listener)"),
            ("com.qualcomm.qti.dynamicddsservice", "Qualcomm Dual-SIM Data Switching"),
            ("com.qualcomm.qti.uimGbaApp", "Qualcomm SIM GBA Authentication"),
            ("vendor.qti.iwlan", "Qualcomm Cellular Wi-Fi Calling"),
            ("com.qualcomm.qti.xrvd.service", "Qualcomm Extended Reality (XR/AR) Daemon"),
            ("com.android.cellbroadcastreceiver", "Cellular Emergency Broadcast Receiver"),
            ("com.android.cellbroadcastreceiver.module", "Cell Broadcast Receiver Module"),
            ("com.android.cellbroadcastservice", "Cell Broadcast Core Service"),
            ("com.android.smspush", "WAP SMS Push Service"),
        ],
        "safe_preset": True
    },
    {
        "category": "High RAM Consumers (Free up ~320MB RAM)",
        "packages": [
            ("com.google.android.gms", "Google Play Services (High RAM, ~200MB+)"),
            ("com.google.android.gsf", "Google Services Framework (~40MB)"),
        ],
        "safe_preset": False
    },
    {
        "category": "Stock OEM & Unused Applications",
        "packages": [
            ("com.onyx.mail", "Onyx Stock Email Client"),
            ("com.onyx.latinime", "Onyx AOSP Keyboard (Disable if using Simple Keyboard)"),
            ("com.onyx.kime", "Onyx KIME Asian Input Method"),
            ("com.android.bips", "Default Android Print Service"),
            ("com.android.printspooler", "Android Print Spooler"),
        ],
        "safe_preset": False
    }
]

SCREEN_WIDTH = 758
SCREEN_HEIGHT = 1024

class DeviceOps:
    def __init__(self, adb_manager):
        self.adb = adb_manager

    # ==========================================
    # ROOT & PARTITIONS
    # ==========================================
    def backup_stock_partitions(self, slot="_a", dest_dir=None):
        """Dumps stock boot and vbmeta partitions to local backup folder."""
        if not dest_dir:
            dest_dir = os.path.join(os.getcwd(), "backups")
        os.makedirs(dest_dir, exist_ok=True)

        boot_local = os.path.join(dest_dir, f"stock_boot{slot}.img")
        vbmeta_local = os.path.join(dest_dir, f"stock_vbmeta{slot}.img")

        self.adb.log(f"Starting stock partition dump for slot {slot}...")
        
        ok, su_check, _ = self.adb.run_shell("su -c 'id'")
        if not ok or "uid=0" not in su_check:
            return False, "Root (su) is required on device to dump active partitions directly."

        self.adb.run_shell(f"su -c 'dd if=/dev/block/bootdevice/by-name/boot{slot} of=/sdcard/stock_boot.img'")
        ok, _, err = self.adb.run_adb("pull", "/sdcard/stock_boot.img", boot_local)
        self.adb.run_shell("rm -f /sdcard/stock_boot.img")
        if not ok or not os.path.exists(boot_local):
            return False, f"Failed to pull boot partition: {err}"

        self.adb.run_shell(f"su -c 'dd if=/dev/block/bootdevice/by-name/vbmeta{slot} of=/sdcard/stock_vbmeta.img'")
        self.adb.run_adb("pull", "/sdcard/stock_vbmeta.img", vbmeta_local)
        self.adb.run_shell("rm -f /sdcard/stock_vbmeta.img")

        boot_size = os.path.getsize(boot_local)
        self.adb.log(f"Successfully backed up stock_boot{slot}.img ({boot_size} bytes)")
        return True, f"Partitions backed up to:\n{boot_local}\n{vbmeta_local}"

    def install_magisk_apk(self, apk_path):
        if not os.path.exists(apk_path):
            return False, f"APK file not found: {apk_path}"
        self.adb.log(f"Installing Magisk APK: {apk_path}")
        ok, out, err = self.adb.run_adb("install", "-r", apk_path)
        if ok and "Success" in out:
            return True, "Magisk APK installed successfully on device!"
        return False, f"Failed to install APK: {err or out}"

    def flash_boot_image_fastboot(self, image_path, slot="_a"):
        if not os.path.exists(image_path):
            return False, f"Image file not found: {image_path}"
        
        self.adb.log(f"Flashing {image_path} to boot{slot}...")
        ok, out, err = self.adb.run_fastboot("flash", f"boot{slot}", image_path)
        if not ok:
            ok, out, err = self.adb.run_fastboot("flash", "boot", image_path)
        
        if ok:
            self.adb.log("Flash completed successfully. Rebooting device...")
            self.adb.run_fastboot("reboot")
            return True, "Boot image flashed successfully! Device is rebooting."
        return False, f"Fastboot flash failed: {err or out}"

    def install_magisk_wake_module(self, zip_path):
        if not os.path.exists(zip_path):
            return False, f"Module zip not found: {zip_path}"
        
        self.adb.log(f"Pushing Magisk module {zip_path} to /data/local/tmp/c69hd-wake.zip...")
        ok, _, err = self.adb.run_adb("push", zip_path, "/data/local/tmp/c69hd-wake.zip")
        if not ok:
            return False, f"Failed to push module: {err}"
        
        self.adb.log("Executing magisk --install-module on device...")
        ok, out, err = self.adb.run_shell("su -c 'magisk --install-module /data/local/tmp/c69hd-wake.zip'")
        self.adb.run_shell("rm -f /data/local/tmp/c69hd-wake.zip")
        if ok and ("done" in out.lower() or "success" in out.lower() or "installed" in out.lower()):
            return True, "c69hd-wake module installed! Reboot to activate hardware button wake."
        return False, f"Magisk module install output:\n{out or err}"

    # ==========================================
    # BUTTON REMAPPING
    # ==========================================
    def get_current_button_mapping(self):
        ok, out, _ = self.adb.run_shell("settings get global KEYCODE_BACK")
        short_action = ""
        long_action = "toggleFrontLight"
        if ok and out and out != "null":
            try:
                data = json.loads(out)
                short_action = data.get("shortPressAction", "")
                long_action = data.get("longPressAction", "toggleFrontLight")
            except Exception:
                pass

        ok_sp, out_sp, _ = self.adb.run_shell("settings get global key_custom_side_key_short_press_enable")
        sp_enabled = (out_sp.strip() == "1")

        return {
            "shortPressAction": short_action,
            "longPressAction": long_action,
            "shortPressEnabled": sp_enabled,
            "raw": out
        }

    def apply_button_mapping(self, long_action, short_action=""):
        payload = {
            "keySet": ["KEYCODE_BACK"],
            "shortPressAction": short_action,
            "longPressAction": long_action,
            "repeat": False
        }
        json_str = json.dumps(payload, separators=(',', ':'))

        self.adb.log(f"Applying KEYCODE_BACK mapping: Long='{long_action}', Short='{short_action}'")
        self.adb.run_shell(f"settings put global KEYCODE_BACK '{json_str}'")

        if short_action:
            self.adb.run_shell("settings put global key_custom_side_key_short_press_enable 1")
        else:
            self.adb.run_shell("settings put global key_custom_side_key_short_press_enable 0")

        self.adb.run_shell("am broadcast -a onyx.action.refresh_keymapping")
        self.adb.log("Sent onyx.action.refresh_keymapping broadcast.")
        return True, "Button mapping successfully applied and broadcasted!"

    def reset_button_mapping(self):
        return self.apply_button_mapping(long_action="toggleFrontLight", short_action="")

    # ==========================================
    # PERSONALIZATION: SCREENSAVER & BOOT ANIMATION
    # ==========================================
    def process_image_for_c69hd(self, src_path, dest_path, convert_grayscale=True):
        """Resizes/crops image to 758x1024 native C69HD e-ink resolution."""
        if not HAS_PILLOW:
            shutil.copyfile(src_path, dest_path)
            return True

        try:
            with Image.open(src_path) as img:
                # Convert to RGB if needed
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                
                # Fit image into 758x1024 with aspect ratio preservation
                fitted = ImageOps.fit(img, (SCREEN_WIDTH, SCREEN_HEIGHT), Image.Resampling.LANCZOS)
                
                if convert_grayscale:
                    # Convert to high contrast 8-bit grayscale for E-Ink
                    fitted = fitted.convert("L")
                
                fitted.save(dest_path, "PNG")
                return True
        except Exception as e:
            self.adb.log(f"Image processing error: {e}")
            return False

    def push_screensaver_image(self, local_image_path, target="user", custom_name="c69hd_custom_ss"):
        """
        Pushes a screensaver image to the device.
        target: 'user' (stores in /sdcard/Pictures/Screensaver/),
                'standby' (replaces /system/media/standby-1.png via Magisk),
                'shutdown' (replaces /system/media/shutdown-default.png via Magisk)
        """
        if not os.path.exists(local_image_path):
            return False, f"File not found: {local_image_path}"

        temp_processed = os.path.join(os.path.dirname(local_image_path), f"_processed_{os.path.basename(local_image_path)}.png")
        self.process_image_for_c69hd(local_image_path, temp_processed)

        if target == "user":
            remote_dir = "/sdcard/Pictures/Screensaver"
            remote_file = f"{remote_dir}/{custom_name}.png"
            self.adb.run_shell(f"mkdir -p {remote_dir}")
            ok, _, err = self.adb.run_adb("push", temp_processed, remote_file)
            # Notify media scanner
            self.adb.run_shell(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{remote_file}")
            if os.path.exists(temp_processed):
                os.remove(temp_processed)
            if ok:
                return True, f"Screensaver pushed to {remote_file} and registered in Gallery/Screensaver selector!"
            return False, f"Failed to push screensaver: {err}"

        elif target in ["standby", "shutdown"]:
            target_filename = "standby-1.png" if target == "standby" else "shutdown-default.png"
            module_dir = "/data/adb/modules/c69hd-custom-media"
            module_media = f"{module_dir}/system/media"
            
            # Setup Magisk module structure
            setup_cmds = f"""
mkdir -p {module_media}
cat << 'EOF' > {module_dir}/module.prop
id=c69hd-custom-media
name=C69HD Custom Media Overlay
version=1.0
versionCode=1
author=Zeusx212
description=Systemless custom boot animation and screensaver media overlay for Onyx Boox C69HD.
EOF
touch {module_dir}/auto_mount
chmod -R 755 {module_dir}
"""
            self._run_su_script(setup_cmds)

            # Push to tmp then move
            tmp_remote = f"/data/local/tmp/{target_filename}"
            self.adb.run_adb("push", temp_processed, tmp_remote)
            move_cmds = f"""
cp {tmp_remote} {module_media}/{target_filename}
chmod 644 {module_media}/{target_filename}
rm -f {tmp_remote}
"""
            self._run_su_script(move_cmds)
            if os.path.exists(temp_processed):
                os.remove(temp_processed)
            return True, f"System {target} image successfully installed into Magisk media overlay! Survives reboots."

    def open_device_screensaver_settings(self):
        """Launches Onyx WallpaperActivity on device."""
        self.adb.run_shell("am start -n com.onyx/.common.screen.ui.WallpaperActivity")
        return True, "Opened Wallpaper Settings on Onyx device."

    def create_bootanimation_zip(self, frame_paths, output_zip_path, fps=1):
        """Creates an uncompressed bootanimation.zip required by Android."""
        os.makedirs(os.path.dirname(output_zip_path), exist_ok=True)
        temp_dir = os.path.join(os.path.dirname(output_zip_path), "_bootanim_temp")
        part0_dir = os.path.join(temp_dir, "part0")
        os.makedirs(part0_dir, exist_ok=True)

        desc_content = f"{SCREEN_WIDTH} {SCREEN_HEIGHT} {fps}\np 0 0 part0\n"
        with open(os.path.join(temp_dir, "desc.txt"), "w", newline="\n") as f:
            f.write(desc_content)

        for idx, fp in enumerate(frame_paths):
            dest_frame = os.path.join(part0_dir, f"{idx:04d}.png")
            self.process_image_for_c69hd(fp, dest_frame, convert_grayscale=True)

        # Android REQUIRES ZIP_STORED (no compression) for bootanimation.zip
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_STORED) as z:
            z.write(os.path.join(temp_dir, "desc.txt"), "desc.txt")
            for root, _, files in os.walk(part0_dir):
                for file in sorted(files):
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, temp_dir)
                    z.write(full_p, rel_p)

        shutil.rmtree(temp_dir, ignore_errors=True)
        return True

    def install_bootanimation_zip(self, zip_path):
        """Installs bootanimation.zip into Magisk custom media module."""
        if not os.path.exists(zip_path):
            return False, f"bootanimation.zip not found: {zip_path}"

        module_dir = "/data/adb/modules/c69hd-custom-media"
        module_media = f"{module_dir}/system/media"

        setup_cmds = f"""
mkdir -p {module_media}
cat << 'EOF' > {module_dir}/module.prop
id=c69hd-custom-media
name=C69HD Custom Media Overlay
version=1.0
versionCode=1
author=Zeusx212
description=Systemless custom boot animation and screensaver media overlay for Onyx Boox C69HD.
EOF
touch {module_dir}/auto_mount
chmod -R 755 {module_dir}
"""
        self._run_su_script(setup_cmds)

        tmp_remote = "/data/local/tmp/bootanimation.zip"
        self.adb.run_adb("push", zip_path, tmp_remote)
        move_cmds = f"""
cp {tmp_remote} {module_media}/bootanimation.zip
chmod 644 {module_media}/bootanimation.zip
rm -f {tmp_remote}
"""
        self._run_su_script(move_cmds)
        return True, "Custom bootanimation.zip installed into Magisk media overlay! Reboot to see it."

    def preview_bootanimation_on_device(self, duration_sec=4):
        """Runs the live boot animation on device screen for verification without rebooting."""
        self.adb.log(f"Triggering boot animation preview on device for {duration_sec}s...")
        script = f"setprop ctl.start bootanim; sleep {duration_sec}; setprop ctl.stop bootanim; input keyevent KEYCODE_HOME"
        self._run_su_script(script)
        return True, "Boot animation played on device display."

    def restore_stock_bootanimation(self):
        """Removes custom bootanimation.zip from Magisk module overlay."""
        cmd = "rm -f /data/adb/modules/c69hd-custom-media/system/media/bootanimation.zip"
        self._run_su_script(cmd)
        return True, "Custom boot animation removed. Device will use stock Onyx boot animation."

    def _run_su_script(self, script_text):
        """Executes multiline script with root privileges cleanly via stdin."""
        import subprocess
        full_cmd = [self.adb.adb_bin, "shell", "su", "-c", "sh"]
        try:
            res = subprocess.run(
                full_cmd,
                input=script_text,
                text=True,
                capture_output=True,
                timeout=20,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return res.returncode == 0, res.stdout, res.stderr
        except Exception as e:
            return False, "", str(e)

    # ==========================================
    # DEBLOATING
    # ==========================================
    def get_disabled_packages(self):
        ok, out, _ = self.adb.run_shell("pm list packages -d")
        disabled = set()
        if ok and out:
            for line in out.splitlines():
                if line.startswith("package:"):
                    disabled.add(line.replace("package:", "").strip())
        return disabled

    def disable_package(self, package_name):
        ok, out, err = self.adb.run_shell(f"pm disable-user --user 0 {package_name}")
        self.adb.log(f"pm disable-user {package_name} -> {out or err}")
        return ok and "disabled" in out.lower()

    def enable_package(self, package_name):
        ok, out, err = self.adb.run_shell(f"pm enable {package_name}")
        self.adb.log(f"pm enable {package_name} -> {out or err}")
        return ok and "enabled" in out.lower()

    def apply_safe_debloat_preset(self):
        results = []
        for cat in DEBLOAT_CATALOG:
            if cat.get("safe_preset"):
                for pkg, desc in cat["packages"]:
                    success = self.disable_package(pkg)
                    results.append((pkg, desc, success))
        return results

    # ==========================================
    # SYSTEM & DISPLAY SETTINGS
    # ==========================================
    def get_system_settings(self):
        settings = {
            "screen_off_timeout": "300000",
            "send_action_app_error": "0",
            "ble_scan": "0",
            "wifi_scan": "0",
            "location_mode": "0",
            "font_scale": "1.0",
            "density": "212",
            "high_contrast": "0"
        }
        
        ok, out, _ = self.adb.run_shell("settings get system screen_off_timeout")
        if ok and out: settings["screen_off_timeout"] = out.strip()

        ok, out, _ = self.adb.run_shell("settings get global send_action_app_error")
        if ok and out: settings["send_action_app_error"] = out.strip()

        ok, out, _ = self.adb.run_shell("settings get global ble_scan_always_enabled")
        if ok and out: settings["ble_scan"] = out.strip()

        ok, out, _ = self.adb.run_shell("settings get global wifi_scan_always_enabled")
        if ok and out: settings["wifi_scan"] = out.strip()

        ok, out, _ = self.adb.run_shell("settings get secure location_mode")
        if ok and out: settings["location_mode"] = out.strip()

        ok, out, _ = self.adb.run_shell("settings get system font_scale")
        if ok and out: settings["font_scale"] = out.strip()

        ok, out, _ = self.adb.run_shell("wm density")
        if ok and out:
            for l in out.splitlines():
                if "density:" in l:
                    settings["density"] = l.split("density:")[-1].strip()

        ok, out, _ = self.adb.run_shell("settings get secure high_text_contrast_enabled")
        if ok and out: settings["high_contrast"] = out.strip()

        return settings

    def apply_system_settings(self, settings_dict):
        if "screen_off_timeout" in settings_dict:
            self.adb.run_shell(f"settings put system screen_off_timeout {settings_dict['screen_off_timeout']}")
        if "send_action_app_error" in settings_dict:
            self.adb.run_shell(f"settings put global send_action_app_error {settings_dict['send_action_app_error']}")
        if "ble_scan" in settings_dict:
            self.adb.run_shell(f"settings put global ble_scan_always_enabled {settings_dict['ble_scan']}")
        if "wifi_scan" in settings_dict:
            self.adb.run_shell(f"settings put global wifi_scan_always_enabled {settings_dict['wifi_scan']}")
        if "location_mode" in settings_dict:
            self.adb.run_shell(f"settings put secure location_mode {settings_dict['location_mode']}")
        if "font_scale" in settings_dict:
            self.adb.run_shell(f"settings put system font_scale {settings_dict['font_scale']}")
        if "density" in settings_dict:
            if settings_dict["density"] == "reset":
                self.adb.run_shell("wm density reset")
            else:
                self.adb.run_shell(f"wm density {settings_dict['density']}")
        if "high_contrast" in settings_dict:
            self.adb.run_shell(f"settings put secure high_text_contrast_enabled {settings_dict['high_contrast']}")
        
        self.adb.log("System settings successfully updated.")
        return True, "Settings applied successfully!"

    # ==========================================
    # POWER / REBOOT HELPERS
    # ==========================================
    def reboot_device(self, target="system"):
        if target == "bootloader":
            self.adb.log("Rebooting device to bootloader (Fastboot)...")
            return self.adb.run_adb("reboot", "bootloader")
        elif target == "recovery":
            self.adb.log("Rebooting device to recovery...")
            return self.adb.run_adb("reboot", "recovery")
        elif target == "systemui":
            self.adb.log("Restarting SystemUI...")
            return self.adb.run_shell("pkill -f com.android.systemui")
        elif target == "sleep":
            self.adb.log("Sending Power Key (Sleep)...")
            return self.adb.run_shell("input keyevent KEYCODE_POWER")
        else:
            self.adb.log("Rebooting device...")
            return self.adb.run_adb("reboot")
