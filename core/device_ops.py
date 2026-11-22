"""
Device operations controller for Onyx Boox C69HD.
Implements partition backup, Magisk rooting, hardware button remapping,
debloating, personalization (screensavers, boot animations), book transfers,
app sideloading, remote controls, and 1-click optimization presets.
"""

import os
import json
import time
import zipfile
import shutil
import urllib.request

try:
    from PIL import Image, ImageOps
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

# Available button mapping actions identified from Onyx ROM analysis
BUTTON_ACTIONS = {
    "KEYCODE_APP_SWITCH": "Recent Apps / App Switcher (Recommended for C69HD)",
    "KEYCODE_POWER": "Power / Sleep Screen (Turn Screen Off / Standby)",
    "fullRefreshScreen": "Full Screen E-Ink Refresh (Clears Ghosting)",
    "screenshot": "Take Screenshot",
    "showRefreshModeDialog": "Open E-Ink Refresh Mode Dialog",
    "back_to_home": "Return to Home Screen",
    "toggleA2": "Toggle A2 High-Speed Refresh Mode",
    "": "Standard Back Key Event",
    "toggleFrontLight": "Factory Default (Toggle Frontlight - No HW on C69HD)",
}

# Supported side button keycodes for E-Reader navigation
SIDE_BUTTON_KEYCODES = [
    ("PAGE_UP", "PAGE_UP (Previous Page / Scroll Up)"),
    ("PAGE_DOWN", "PAGE_DOWN (Next Page / Scroll Down)"),
    ("POWER", "POWER (Sleep / Screen Off / Wake / Power Menu)"),
    ("SLEEP", "SLEEP (Put Device into Standby / Sleep)"),
    ("WAKEUP", "WAKEUP (Wake Screen from Standby)"),
    ("VOLUME_UP", "VOLUME_UP (Kindle, Moon+, Koreader Previous)"),
    ("VOLUME_DOWN", "VOLUME_DOWN (Kindle, Moon+, Koreader Next)"),
    ("DPAD_UP", "DPAD_UP (Up Navigation / Scroll)"),
    ("DPAD_DOWN", "DPAD_DOWN (Down Navigation / Scroll)"),
    ("DPAD_LEFT", "DPAD_LEFT (Left Navigation)"),
    ("DPAD_RIGHT", "DPAD_RIGHT (Right Navigation)"),
    ("BACK", "BACK (Return / Exit)"),
    ("HOME", "HOME (Go to Home Launcher)"),
    ("APP_SWITCH", "APP_SWITCH (Recent Apps Switcher)"),
    ("FORWARD", "FORWARD (Browser Forward)"),
    ("MEDIA_PREVIOUS", "MEDIA_PREVIOUS (Previous Track/Page)"),
    ("MEDIA_NEXT", "MEDIA_NEXT (Next Track/Page)"),
    ("ZOOM_IN", "ZOOM_IN (Enlarge Text / Zoom In)"),
    ("ZOOM_OUT", "ZOOM_OUT (Shrink Text / Zoom Out)"),
    ("BRIGHTNESS_UP", "BRIGHTNESS_UP (Increase Brightness)"),
    ("BRIGHTNESS_DOWN", "BRIGHTNESS_DOWN (Decrease Brightness)"),
]

# Curated side button remapping presets
SIDE_BUTTON_PRESETS = [
    {
        "id": "PAGE_TURN_DEFAULT",
        "name": "📖 Page Turn (Default Onyx): Top = PAGE_UP, Bottom = PAGE_DOWN",
        "top": "PAGE_UP",
        "bottom": "PAGE_DOWN",
        "desc": "Standard NeoReader and Onyx OS page-turn mapping."
    },
    {
        "id": "VOLUME_KEYS",
        "name": "🔊 Volume Buttons: Top = VOLUME_UP, Bottom = VOLUME_DOWN",
        "top": "VOLUME_UP",
        "bottom": "VOLUME_DOWN",
        "desc": "Recommended for Kindle, Moon+ Reader, Mihon/Tachiyomi, Librera, and KOReader."
    },
    {
        "id": "POWER_PAGE",
        "name": "⚡ Power + Page Turn: Top = POWER, Bottom = PAGE_DOWN",
        "top": "POWER",
        "bottom": "PAGE_DOWN",
        "desc": "Top button acts as Sleep/Power/Wake button; bottom button turns page forward."
    },
    {
        "id": "PAGE_POWER",
        "name": "⚡ Page Turn + Power: Top = PAGE_UP, Bottom = POWER",
        "top": "PAGE_UP",
        "bottom": "POWER",
        "desc": "Top button turns page back; bottom button acts as Sleep/Power/Wake button."
    },
    {
        "id": "POWER_SLEEP",
        "name": "💤 Dual Power & Sleep: Top = POWER, Bottom = SLEEP",
        "top": "POWER",
        "bottom": "SLEEP",
        "desc": "Dedicated hardware buttons for screen sleep/wake and standby."
    },
    {
        "id": "POWER_BACK",
        "name": "⚡ Power + Back: Top = POWER, Bottom = BACK",
        "top": "POWER",
        "bottom": "BACK",
        "desc": "Top button toggles Power/Sleep; bottom button returns Back."
    },
    {
        "id": "INVERTED_PAGE_TURN",
        "name": "🔄 Inverted Page Turn: Top = PAGE_DOWN, Bottom = PAGE_UP",
        "top": "PAGE_DOWN",
        "bottom": "PAGE_UP",
        "desc": "Top button advances to next page (ergonomic for left-handed reading)."
    },
    {
        "id": "INVERTED_VOLUME",
        "name": "🔉 Inverted Volume: Top = VOLUME_DOWN, Bottom = VOLUME_UP",
        "top": "VOLUME_DOWN",
        "bottom": "VOLUME_UP",
        "desc": "Top button advances page in apps configured for volume key navigation."
    },
    {
        "id": "DPAD_NAV",
        "name": "⬆️ D-Pad Directional: Top = DPAD_UP, Bottom = DPAD_DOWN",
        "top": "DPAD_UP",
        "bottom": "DPAD_DOWN",
        "desc": "Smooth vertical scrolling in web browsers (EinkBro, Chrome) and article lists."
    },
    {
        "id": "READER_BACK",
        "name": "↩️ Reader + Back: Top = PAGE_DOWN, Bottom = BACK",
        "top": "PAGE_DOWN",
        "bottom": "BACK",
        "desc": "Top button turns page forward; bottom button exits/returns back."
    },
    {
        "id": "HOME_BACK",
        "name": "🏠 Home + Back: Top = HOME, Bottom = BACK",
        "top": "HOME",
        "bottom": "BACK",
        "desc": "Full system navigation keys on physical side buttons."
    },
    {
        "id": "CUSTOM",
        "name": "⚙️ Custom Keycode Pair (User-Selected)",
        "top": "",
        "bottom": "",
        "desc": "Select any individual keycode for top and bottom side buttons."
    }
]

# Side button long-press actions supported by Onyx framework
SIDE_BUTTON_LONG_ACTIONS = {
    "none": "No Action (Standard Hardware Press)",
    "power": "Sleep / Power Off Screen",
    "fullRefreshScreen": "Full Screen E-Ink Refresh (Clears Ghosting)",
    "screenshot": "Take Screenshot",
    "toggleA2": "Toggle A2 High-Speed Refresh Mode",
    "showRefreshModeDialog": "Open E-Ink Refresh Mode Dialog",
    "back_to_home": "Return to Home Screen",
    "KEYCODE_APP_SWITCH": "Recent Apps Switcher",
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

# Curated E-Ink Apps for Sideload Hub
CURATED_EINK_APPS = [
    {
        "name": "KOReader",
        "desc": "The #1 open-source e-reader with custom E-Ink refresh & typography",
        "package": "org.koreader.launcher",
        "url": "https://github.com/koreader/koreader/releases/download/v2024.11/koreader-android-arm-v2024.11.apk"
    },
    {
        "name": "Mihon",
        "desc": "High-contrast manga & comic reader optimized for Carta displays",
        "package": "app.mihon",
        "url": "https://github.com/mihonapp/mihon/releases/download/v0.17.1/mihon-arm64-v8a-v0.17.1.apk"
    },
    {
        "name": "EinkBro",
        "desc": "Web browser engineered specifically for E-Ink with physical page turn keys & contrast tuning",
        "package": "info.plateaukao.einkbro",
        "url": "https://github.com/plateaukao/einkbro/releases/download/v16.7.1/app-universal-release.apk"
    },
    {
        "name": "Komi Store",
        "desc": "Open-source GitHub/Codeberg app store with direct APK downloads & update manager",
        "package": "zed.rainxch.githubstore",
        "url": "https://github.com/komi-store/komi-store/releases/download/v1.9.4/Komi-Store-1.9.4.apk"
    },
    {
        "name": "Simple Keyboard",
        "desc": "Ultra-lightweight keyboard (replaces heavy 70MB Onyx LatinIME)",
        "package": "rkr.simplekeyboard.inputmethod",
        "url": "https://github.com/rkkr/simple-keyboard/releases/download/149/app-release.apk"
    },
    {
        "name": "Key Mapper",
        "desc": "Enables double-press, hold, and multi-key triggers on hardware keys",
        "package": "io.github.sds100.keymapper",
        "url": "https://github.com/keymapperorg/KeyMapper/releases/download/v4.7.1/keymapper-4.7.1-foss.apk"
    },
    {
        "name": "Olauncher",
        "desc": "Distraction-free, minimal text launcher perfectly suited for E-Ink screens",
        "package": "app.tanuj.launcher",
        "url": "https://github.com/tanujnotes/Olauncher/releases/download/v6.9.17/Olauncher-v6.9.17.apk"
    },
    {
        "name": "Librera Reader",
        "desc": "Customizable multi-format book and PDF reader with dedicated E-Ink mode",
        "package": "com.foobnix.pdf.reader",
        "url": "https://github.com/foobnix/LibreraReader/releases/download/10.1.7/Librera.Fdroid-10.1.7-mupdf-uni.apk"
    },
    {
        "name": "LocalSend",
        "desc": "Offline file, book, and APK sharing over local Wi-Fi",
        "package": "org.localsend.localsend_app",
        "url": "https://github.com/localsend/localsend/releases/download/v1.18.2/LocalSend-1.18.2-android-arm64v8.apk"
    },
    {
        "name": "F-Droid",
        "desc": "The classic FOSS Android application repository and package manager",
        "package": "org.fdroid.fdroid",
        "url": "https://f-droid.org/F-Droid.apk"
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
    def backup_stock_partitions(self, slot="_a", dest_dir=None, partition_list=None):
        if not dest_dir:
            dest_dir = os.path.join(os.getcwd(), "backups")
        os.makedirs(dest_dir, exist_ok=True)

        if not partition_list:
            partition_list = [f"boot{slot}", f"vbmeta{slot}"]

        self.adb.log(f"Starting partition dump for: {', '.join(partition_list)}...")
        
        ok, su_check, _ = self.adb.run_shell("su -c 'id'")
        if not ok or "uid=0" not in su_check:
            return False, "Root (su) is required on device to dump active partitions directly."

        saved_files = []
        for part in partition_list:
            local_file = os.path.join(dest_dir, f"stock_{part}.img")
            self.adb.run_shell(f"su -c 'dd if=/dev/block/bootdevice/by-name/{part} of=/sdcard/dump_{part}.img'")
            ok_pull, _, err = self.adb.run_adb("pull", f"/sdcard/dump_{part}.img", local_file)
            self.adb.run_shell(f"rm -f /sdcard/dump_{part}.img")
            if ok_pull and os.path.exists(local_file):
                saved_files.append(local_file)
                self.adb.log(f"Saved {part} -> {local_file} ({os.path.getsize(local_file)} bytes)")

        if saved_files:
            return True, f"Successfully dumped {len(saved_files)} partitions to:\n" + "\n".join(saved_files)
        return False, "Failed to dump partitions."

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

    def unlock_bootloader_fastboot(self):
        """Attempts to unlock the bootloader in Fastboot mode."""
        self.adb.log("Attempting Fastboot bootloader unlock...")
        ok, out, err = self.adb.run_fastboot("flashing", "unlock")
        if not ok:
            ok, out, err = self.adb.run_fastboot("oem", "unlock")
        if ok:
            return True, "Bootloader unlock command sent successfully. If prompted on device screen, confirm using side keys."
        return False, f"Bootloader unlock failed: {err or out}"

    def push_boot_to_device(self, boot_img_path, dest_remote="/sdcard/Download/stock_boot.img"):
        """Pushes a local stock boot.img to the device's Download folder ready for Magisk patching."""
        if not os.path.exists(boot_img_path):
            return False, f"Local boot image not found: {boot_img_path}"
        self.adb.log(f"Pushing {boot_img_path} -> {dest_remote}...")
        self.adb.run_shell("mkdir -p /sdcard/Download")
        ok, out, err = self.adb.run_adb("push", boot_img_path, dest_remote)
        if ok:
            return True, f"Stock boot image pushed to {dest_remote} on device."
        return False, f"Failed to push boot image: {err or out}"

    def pull_latest_magisk_patched_boot(self, dest_dir=None):
        """
        Finds the newest magisk_patched_*.img on the device in /sdcard/Download/ or /sdcard/,
        and pulls it to the local backups directory.
        """
        if not dest_dir:
            dest_dir = os.path.join(os.getcwd(), "backups")
        os.makedirs(dest_dir, exist_ok=True)

        self.adb.log("Scanning device for Magisk-patched boot images...")
        ok, out, err = self.adb.run_shell(
            "ls -t /sdcard/Download/magisk_patched*.img /sdcard/magisk_patched*.img 2>/dev/null"
        )
        if not ok or not out.strip():
            return False, None, "No Magisk-patched boot images found in /sdcard/Download/ yet. Please patch stock_boot.img in the Magisk app first."

        candidate = out.strip().splitlines()[0].strip()
        filename = os.path.basename(candidate)
        local_dest = os.path.join(dest_dir, filename)

        self.adb.log(f"Found patched image: {candidate} -> Pulling to {local_dest}...")
        ok_pull, _, err_pull = self.adb.run_adb("pull", candidate, local_dest)
        if ok_pull and os.path.exists(local_dest):
            size_mb = os.path.getsize(local_dest) / (1024 * 1024)
            return True, local_dest, f"Successfully pulled {filename} ({size_mb:.1f} MB) to:\n{local_dest}"
        return False, None, f"Failed to pull patched boot image: {err_pull}"

    def launch_magisk_app(self):
        """Launches the Magisk application on the device screen."""
        self.adb.log("Launching Magisk app on device...")
        ok, out, err = self.adb.run_shell("monkey -p com.topjohnwu.magisk -c android.intent.category.LAUNCHER 1")
        if ok:
            return True, "Magisk app opened on device screen."
        return False, f"Could not launch Magisk app: {err or out}"

    def verify_root_access(self):
        """Checks if device has working root access with uid=0."""
        self.adb.log("Verifying root access (su check)...")
        ok, out, err = self.adb.run_shell("su -c 'id'")
        if ok and "uid=0" in out:
            return True, f"Root verified! Superuser active: {out.strip()}"
        return False, f"Device is not rooted or su permission denied: {out or err}"

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
    # SIDE BUTTONS (PAGE TURN KEYS) REMAPPING
    # ==========================================
    def get_current_side_button_mapping(self):
        """
        Reads physical side button layout (gpio-keys.kl: top=key 104, bottom=key 109)
        and Onyx OS side button long-press settings.
        """
        # 1. Read key layout file
        # Check Magisk module overlay first, then fallback to stock /system
        kl_cmd = (
            "if [ -f /data/adb/modules/c69hd-custom-media/system/usr/keylayout/gpio-keys.kl ]; then "
            "cat /data/adb/modules/c69hd-custom-media/system/usr/keylayout/gpio-keys.kl; "
            "else cat /system/usr/keylayout/gpio-keys.kl; fi"
        )
        ok_kl, out_kl, _ = self.adb.run_shell(f"su -c '{kl_cmd}'")

        top_key = "PAGE_UP"
        bottom_key = "PAGE_DOWN"
        if ok_kl and out_kl:
            for line in out_kl.splitlines():
                parts = line.strip().split()
                if len(parts) >= 3 and parts[0] == "key":
                    if parts[1] == "104":
                        top_key = parts[2]
                    elif parts[1] == "109":
                        bottom_key = parts[2]

        # 2. Read Onyx long-press settings
        _, out_lp, _ = self.adb.run_shell("settings get global key_custom_side_key_long_press_enable")
        lp_enabled = (out_lp.strip() == "1")

        _, out_top_lp, _ = self.adb.run_shell("settings get global key_custom_side_key_long_press_up")
        top_long = out_top_lp.strip() if out_top_lp and out_top_lp != "null" else "none"

        _, out_bot_lp, _ = self.adb.run_shell("settings get global key_custom_side_key_long_press_down")
        bottom_long = out_bot_lp.strip() if out_bot_lp and out_bot_lp != "null" else "none"

        # 3. Detect matching preset
        matched_preset_id = "CUSTOM"
        for p in SIDE_BUTTON_PRESETS:
            if p["id"] != "CUSTOM" and p["top"] == top_key and p["bottom"] == bottom_key:
                matched_preset_id = p["id"]
                break

        return {
            "top_key": top_key,
            "bottom_key": bottom_key,
            "long_press_enabled": lp_enabled,
            "top_long": top_long,
            "bottom_long": bottom_long,
            "preset_id": matched_preset_id
        }

    def apply_side_button_mapping(self, top_key="PAGE_UP", bottom_key="PAGE_DOWN", top_long="none", bottom_long="none"):
        """
        Applies side button key layout remapping to gpio-keys.kl via systemless Magisk module
        and bind-mount for immediate effect, plus configures Onyx framework long-press actions.
        """
        top_key = top_key.strip().upper()
        bottom_key = bottom_key.strip().upper()

        if not top_key or not bottom_key:
            return False, "Both top and bottom keycodes must be specified."

        self.adb.log(f"Applying side button remap: Top='{top_key}', Bottom='{bottom_key}', TopLong='{top_long}', BotLong='{bottom_long}'")

        # 1. Generate compliant gpio-keys.kl
        # For POWER, SLEEP, WAKEUP keys, append WAKE flag so physical button can wake device from standby
        def _format_kl_key(scancode, keycode):
            kc = keycode.strip().upper()
            if kc in ("POWER", "SLEEP", "WAKEUP"):
                return f"key {scancode:<5} {kc} WAKE\n"
            return f"key {scancode:<5} {kc}\n"

        kl_content = (
            "# Onyx Boox C69HD Remapped Keylayout\n"
            "key 115   VOLUME_UP\n"
            "key 114   VOLUME_DOWN\n"
            "key 102   HOME\n"
            "key 528   FOCUS\n"
            "key 766   CAMERA\n"
            + _format_kl_key(104, top_key)
            + _format_kl_key(109, bottom_key)
        )

        # 2. Write to Magisk module for persistent systemless overlay across reboots
        magisk_target = "/data/adb/modules/c69hd-custom-media/system/usr/keylayout/gpio-keys.kl"
        create_script = (
            f"cat << 'EOF' > /data/local/tmp/gpio-keys.kl\n{kl_content}\nEOF\n"
            "mkdir -p /data/adb/modules/c69hd-custom-media/system/usr/keylayout\n"
            f"cp /data/local/tmp/gpio-keys.kl {magisk_target}\n"
            f"chmod 644 {magisk_target}\n"
            f"mount -o bind {magisk_target} /system/usr/keylayout/gpio-keys.kl 2>/dev/null || true\n"
            "rm -f /data/local/tmp/gpio-keys.kl\n"
        )

        ok_kl, out_kl, err_kl = self.adb.run_shell(f"su -c '{create_script}'")
        if not ok_kl:
            self.adb.log(f"Failed to write gpio-keys.kl: {out_kl or err_kl}")
            return False, f"Failed to deploy keylayout: {out_kl or err_kl}"

        # 3. Configure Onyx framework long-press settings
        has_long = (top_long != "none" or bottom_long != "none")
        if has_long:
            self.adb.run_shell("settings put global key_custom_side_key_long_press_enable 1")
            self.adb.run_shell(f"settings put global key_custom_side_key_long_press_up '{top_long}'")
            self.adb.run_shell(f"settings put global key_custom_side_key_long_press_down '{bottom_long}'")
        else:
            self.adb.run_shell("settings put global key_custom_side_key_long_press_enable 0")
            self.adb.run_shell("settings put global key_custom_side_key_long_press_up 'none'")
            self.adb.run_shell("settings put global key_custom_side_key_long_press_down 'none'")

        # 4. Broadcast refresh to Onyx input manager
        self.adb.run_shell("am broadcast -a onyx.action.refresh_keymapping")
        self.adb.log("Side buttons remapped successfully.")
        return True, f"Side buttons successfully remapped to Top: {top_key}, Bottom: {bottom_key}!"

    def reset_side_button_mapping(self):
        """Resets physical side buttons to Onyx factory default (PAGE_UP / PAGE_DOWN)."""
        # Remove custom module override if present
        cleanup_script = (
            "umount /system/usr/keylayout/gpio-keys.kl 2>/dev/null || true\n"
            "rm -f /data/adb/modules/c69hd-custom-media/system/usr/keylayout/gpio-keys.kl\n"
        )
        self.adb.run_shell(f"su -c '{cleanup_script}'")
        self.adb.run_shell("settings put global key_custom_side_key_long_press_enable 0")
        self.adb.run_shell("settings put global key_custom_side_key_long_press_up 'none'")
        self.adb.run_shell("settings put global key_custom_side_key_long_press_down 'none'")
        self.adb.run_shell("am broadcast -a onyx.action.refresh_keymapping")
        self.adb.log("Reset side buttons to factory defaults.")
        return True, "Side buttons reset to factory defaults (PAGE_UP / PAGE_DOWN)."

    # ==========================================
    # PERSONALIZATION: SCREENSAVER & BOOT MEDIA
    # ==========================================
    def process_image_for_c69hd(self, src_path, dest_path, convert_grayscale=True):
        if not HAS_PILLOW:
            shutil.copyfile(src_path, dest_path)
            return True

        try:
            with Image.open(src_path) as img:
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                fitted = ImageOps.fit(img, (SCREEN_WIDTH, SCREEN_HEIGHT), Image.Resampling.LANCZOS)
                if convert_grayscale:
                    fitted = fitted.convert("L")
                fitted.save(dest_path, "PNG")
                return True
        except Exception as e:
            self.adb.log(f"Image processing error: {e}")
            return False

    def push_screensaver_image(self, local_image_path, target="user", custom_name="c69hd_custom_ss"):
        if not os.path.exists(local_image_path):
            return False, f"File not found: {local_image_path}"

        temp_processed = os.path.join(os.path.dirname(local_image_path), f"_processed_{os.path.basename(local_image_path)}.png")
        self.process_image_for_c69hd(local_image_path, temp_processed)

        if target == "user":
            remote_dir = "/sdcard/Pictures/Screensaver"
            remote_file = f"{remote_dir}/{custom_name}.png"
            self.adb.run_shell(f"mkdir -p {remote_dir}")
            ok, _, err = self.adb.run_adb("push", temp_processed, remote_file)
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
        self.adb.run_shell("am start -n com.onyx/.common.screen.ui.WallpaperActivity")
        return True, "Opened Wallpaper Settings on Onyx device."

    def create_bootanimation_zip(self, frame_paths, output_zip_path, fps=1):
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
        self.adb.log(f"Triggering boot animation preview on device for {duration_sec}s...")
        script = f"setprop ctl.start bootanim; sleep {duration_sec}; setprop ctl.stop bootanim; input keyevent KEYCODE_HOME"
        self._run_su_script(script)
        return True, "Boot animation played on device display."

    def restore_stock_bootanimation(self):
        cmd = "rm -f /data/adb/modules/c69hd-custom-media/system/media/bootanimation.zip"
        self._run_su_script(cmd)
        return True, "Custom boot animation removed. Device will use stock Onyx boot animation."

    # ==========================================
    # BOOKS & DOCUMENT TRANSFER HUB
    # ==========================================
    def push_books_batch(self, file_paths, target_dir="/sdcard/Books"):
        """Pushes a list of book files and triggers media scan on device."""
        self.adb.run_shell(f"mkdir -p {target_dir}")
        uploaded = 0
        errors = []

        for fp in file_paths:
            if not os.path.exists(fp):
                errors.append(f"Not found: {fp}")
                continue
            fname = os.path.basename(fp)
            remote_path = f"{target_dir}/{fname}"
            self.adb.log(f"Pushing book: {fname} -> {remote_path}...")
            ok, _, err = self.adb.run_adb("push", fp, remote_path)
            if ok:
                uploaded += 1
                # Trigger media scan
                self.adb.run_shell(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{remote_path}")
            else:
                errors.append(f"Failed {fname}: {err}")

        # Scan folder
        self.adb.run_shell(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{target_dir}")
        msg = f"Transferred {uploaded} / {len(file_paths)} books to {target_dir} and refreshed bookshelf!"
        if errors:
            msg += "\nErrors:\n" + "\n".join(errors[:3])
        return uploaded > 0, msg

    # ==========================================
    # APP SIDELOAD HUB
    # ==========================================
    def sideload_apk(self, apk_path):
        """Installs an APK via adb install -r."""
        if not os.path.exists(apk_path):
            return False, f"File not found: {apk_path}"
        self.adb.log(f"Sideloading APK: {os.path.basename(apk_path)}...")
        ok, out, err = self.adb.run_adb("install", "-r", apk_path, timeout=60)
        if ok and "Success" in out:
            return True, f"Successfully installed {os.path.basename(apk_path)}!"
        return False, f"Install failed: {out or err}"

    def download_and_install_curated_app(self, app_info, download_dir=None, progress_callback=None):
        """Downloads app from GitHub release and sideloads it."""
        if not download_dir:
            download_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(download_dir, exist_ok=True)

        url = app_info["url"]
        fname = f"{app_info['name'].lower().replace(' ', '_')}.apk"
        local_apk = os.path.join(download_dir, fname)

        self.adb.log(f"Downloading {app_info['name']} from {url}...")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp, open(local_apk, 'wb') as out_f:
                total_size = int(resp.headers.get('content-length', 0))
                downloaded = 0
                block_size = 65536
                while True:
                    buffer = resp.read(block_size)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    out_f.write(buffer)
                    if progress_callback and total_size > 0:
                        progress_callback(downloaded / total_size)
        except Exception as e:
            return False, f"Download failed: {str(e)}"

        self.adb.log(f"Downloaded {local_apk} ({os.path.getsize(local_apk)} bytes). Sideloading to device...")
        return self.sideload_apk(local_apk)

    # ==========================================
    # E-INK REMOTE & SCREEN TOOLS
    # ==========================================
    def trigger_eink_refresh(self):
        """Triggers full-screen e-ink refresh to clear ghosting."""
        self.adb.log("Broadcasting full E-Ink refresh...")
        self.adb.run_shell("am broadcast -a onyx.action.refresh_screen")
        self.adb.run_shell("am broadcast -a onyx.action.full_refresh")
        return True, "E-Ink screen refresh broadcast sent."

    def toggle_a2_speed_mode(self):
        """Toggles high-speed A2 refresh mode."""
        self.adb.log("Toggling A2 speed refresh mode...")
        self.adb.run_shell("am broadcast -a onyx.action.toggleA2")
        return True, "A2 refresh mode toggled."

    def send_keyevent(self, keycode_name):
        """Sends keyevent over ADB."""
        self.adb.log(f"Sending keyevent: {keycode_name}")
        return self.adb.run_shell(f"input keyevent {keycode_name}")

    # ==========================================
    # 1-CLICK OPTIMIZATION PRESETS
    # ==========================================
    def apply_profile_extreme_battery(self):
        """Applies battery-saving preset."""
        settings = {
            "screen_off_timeout": "120000", # 2 minutes
            "send_action_app_error": "0",
            "ble_scan": "0",
            "wifi_scan": "0",
            "location_mode": "0"
        }
        self.apply_system_settings(settings)
        # Safe debloat
        self.apply_safe_debloat_preset()
        return True, "Extreme Battery Saver preset applied (2m sleep, radios off, cellular daemons disabled)!"

    def apply_profile_free_ram(self):
        """Frees up ~320MB RAM by suspending heavy Google & OEM services."""
        heavy_pkgs = [
            "com.google.android.gms",
            "com.google.android.gsf",
            "com.onyx.mail",
            "com.onyx.latinime",
            "com.onyx.kime",
            "com.qualcomm.qti.sva"
        ]
        disabled = []
        for p in heavy_pkgs:
            if self.disable_package(p):
                disabled.append(p)
        return True, f"Free RAM Booster applied: disabled {len(disabled)} memory hogs (reclaimed ~320MB RAM)!"

    def apply_profile_distraction_free(self):
        """Applies reading focus preset."""
        settings = {
            "screen_off_timeout": "600000", # 10 minutes
            "send_action_app_error": "0",
            "location_mode": "0",
            "font_scale": "1.05"
        }
        self.apply_system_settings(settings)
        return True, "Distraction-Free Reading preset applied (10m sleep, optimized 1.05 font, quiet background)!"

    def apply_profile_factory_restore(self):
        """Re-enables all catalog packages and sets factory defaults."""
        for cat in DEBLOAT_CATALOG:
            for p, _ in cat["packages"]:
                self.enable_package(p)
        self.reset_button_mapping()
        self.apply_system_settings({
            "screen_off_timeout": "300000",
            "send_action_app_error": "1",
            "location_mode": "3",
            "font_scale": "1.00",
            "density": "reset"
        })
        return True, "Factory defaults and all stock packages restored."

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

    def _run_su_script(self, script_text):
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
