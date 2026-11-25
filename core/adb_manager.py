"""
ADB and Fastboot execution manager for Onyx Boox C69HD.
Provides robust process execution, device probing, wireless ADB, screenshot capture, and status parsing.
"""

import subprocess
import shutil
import re
import os
import io
import time

from core.adb_installer import find_existing_platform_tools, install_platform_tools

# Optional Pillow import for screenshot decoding
try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

class ADBManager:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        tools = find_existing_platform_tools()
        self.adb_bin = tools["adb"] or "adb"
        self.fastboot_bin = tools["fastboot"] or "fastboot"
        self._installed = tools["installed"]
        self._version = tools["version"]

    def is_available(self):
        """Returns True if a valid adb executable exists."""
        if os.path.isabs(self.adb_bin):
            return os.path.isfile(self.adb_bin)
        return shutil.which(self.adb_bin) is not None

    def get_tool_info(self):
        """Returns metadata about the ADB installation."""
        return {
            "installed": self.is_available(),
            "adb_path": self.adb_bin,
            "fastboot_path": self.fastboot_bin,
            "version": self._version or "Unknown"
        }

    def install_tools(self, progress_callback=None, systemwide=True):
        """Downloads and sets up official platform tools."""
        ok, adb, fb, ver = install_platform_tools(progress_callback=progress_callback, systemwide=systemwide)
        if ok:
            self.adb_bin = adb
            self.fastboot_bin = fb
            self._installed = True
            self._version = ver
        return ok, ver

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(f"[ADB] {message}")

    def run_cmd(self, cmd_args, tool="adb", timeout=30):
        """Run an adb or fastboot command and return (success, stdout, stderr)"""
        exe = self.adb_bin if tool == "adb" else self.fastboot_bin
        full_cmd = [exe] + cmd_args
        self.log(f"Executing: {' '.join(full_cmd)}")
        try:
            res = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            success = (res.returncode == 0)
            stdout = res.stdout.strip()
            stderr = res.stderr.strip()
            if not success and stderr:
                self.log(f"Error ({res.returncode}): {stderr}")
            return success, stdout, stderr
        except subprocess.TimeoutExpired:
            self.log(f"Command timed out after {timeout}s: {' '.join(full_cmd)}")
            return False, "", "Command timed out"
        except FileNotFoundError:
            self.log(f"Executable '{exe}' not found in PATH.")
            return False, "", f"'{exe}' not found"
        except Exception as e:
            self.log(f"Exception executing command: {str(e)}")
            return False, "", str(e)

    def run_adb(self, *args, timeout=30):
        return self.run_cmd(list(args), tool="adb", timeout=timeout)

    def run_fastboot(self, *args, timeout=30):
        return self.run_cmd(list(args), tool="fastboot", timeout=timeout)

    def run_shell(self, shell_cmd, timeout=30):
        return self.run_adb("shell", shell_cmd, timeout=timeout)

    def get_device_ip(self):
        """Detects the Wi-Fi IP address of the connected device."""
        ok, out, _ = self.run_shell("ip -4 route show dev wlan0")
        if ok and out:
            # e.g.: 192.168.1.0/24 proto kernel scope link src 192.168.1.11
            m = re.search(r'src\s+(\d+\.\d+\.\d+\.\d+)', out)
            if m:
                return m.group(1)

        # Fallback to ip addr
        ok, out, _ = self.run_shell("ip -4 addr show wlan0")
        if ok and out:
            m = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', out)
            if m:
                return m.group(1)
        return None

    def enable_wireless_adb(self, port=5555):
        """Enables wireless ADB on port 5555 and connects to device IP."""
        ip = self.get_device_ip()
        if not ip:
            return False, "Could not determine device Wi-Fi IP address. Ensure device is connected to Wi-Fi."

        self.log(f"Switching ADB daemon to TCP port {port}...")
        ok, out, err = self.run_adb("tcpip", str(port))
        if not ok:
            return False, f"Failed to switch to tcpip mode: {err or out}"

        self.log(f"Connecting to {ip}:{port}...")
        ok, out, err = self.run_adb("connect", f"{ip}:{port}")
        if ok and "connected" in out.lower():
            return True, f"Successfully connected wirelessly to {ip}:{port}!"
        return False, f"Failed to connect wirelessly: {out or err}"

    def disconnect_wireless_adb(self):
        """Disconnects wireless ADB connections and reverts to USB."""
        self.run_adb("disconnect")
        self.run_adb("usb")
        return True, "Disconnected wireless ADB. Reverted to USB mode."

    def capture_screenshot(self):
        """Captures a screenshot via adb exec-out screencap -p and returns a PIL Image."""
        if not HAS_PILLOW:
            return None, "Pillow library is required for screenshot capture."
        
        full_cmd = [self.adb_bin, "exec-out", "screencap", "-p"]
        try:
            raw = subprocess.check_output(full_cmd, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            img = Image.open(io.BytesIO(raw))
            return img, None
        except Exception as e:
            return None, str(e)

    def get_quick_serial(self):
        """Quickly check for an attached ADB device serial in under 50ms."""
        ok, out, _ = self.run_adb("devices")
        if ok and out:
            lines = [l.strip() for l in out.splitlines() if l.strip() and not l.startswith("*")]
            for l in lines[1:]:
                parts = l.split()
                if len(parts) >= 2 and parts[1] == "device":
                    return parts[0]
        return None

    def get_fastboot_var(self, var_name, timeout=10):
        """
        Queries a fastboot variable (`fastboot getvar <var_name>`).
        Fastboot prints getvar responses to stderr (or stdout in some wrappers),
        so both streams are inspected.
        """
        ok, out, err = self.run_fastboot("getvar", var_name, timeout=timeout)
        combined = f"{out}\n{err}"
        for line in combined.splitlines():
            line_s = line.strip()
            if line_s.lower().startswith(f"{var_name.lower()}:"):
                return line_s.split(":", 1)[1].strip()
        return None

    def get_device_mode(self):
        """
        Lightweight probe returning (mode, serial, is_wireless) without running
        heavy dumpsys/df shell commands.
        Modes: "adb", "recovery", "sideload", "fastboot", "unauthorized", "offline", "none".
        """
        ok, out, _ = self.run_adb("devices", timeout=8)
        if ok and out:
            lines = [l.strip() for l in out.splitlines() if l.strip() and not l.startswith("*")]
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 2:
                    serial, state = parts[0], parts[1].lower()
                    is_wireless = ":" in serial
                    if state == "device":
                        return "adb", serial, is_wireless
                    elif state == "recovery":
                        return "recovery", serial, is_wireless
                    elif state == "sideload":
                        return "sideload", serial, is_wireless
                    elif state == "unauthorized":
                        return "unauthorized", serial, is_wireless
                    elif state == "offline":
                        return "offline", serial, is_wireless

        ok_fb, out_fb, _ = self.run_fastboot("devices", timeout=8)
        if ok_fb and out_fb:
            lines = [l.strip() for l in out_fb.splitlines() if l.strip()]
            if lines:
                parts = lines[0].split()
                return "fastboot", parts[0], False

        return "none", "N/A", False

    def wait_for_mode(self, target_modes, timeout=35, poll_interval=1.0, status_callback=None):
        """
        Polls get_device_mode() until the device reaches one of `target_modes`.
        Returns (True, reached_mode, serial) or (False, last_mode, diagnostic_message).
        """
        if isinstance(target_modes, str):
            target_modes = [target_modes]

        start = time.time()
        last_mode = "none"
        while time.time() - start < timeout:
            mode, serial, is_wireless = self.get_device_mode()
            last_mode = mode
            if mode in target_modes:
                return True, mode, serial
            if status_callback:
                elapsed = int(time.time() - start)
                status_callback(f"Waiting for {'/'.join(target_modes)} mode... ({elapsed}s, current: {mode})")
            time.sleep(poll_interval)

        hint = ""
        if "fastboot" in target_modes:
            hint = (
                "\n\nTroubleshooting:\n"
                "• Fastboot requires a direct USB data cable (Wireless ADB does not work in Fastboot).\n"
                "• On Windows, if the device screen shows FASTBOOT but isn't detected, install the Google/Qualcomm Android Bootloader Interface USB driver in Device Manager."
            )
        elif "recovery" in target_modes:
            hint = "\n\nEnsure the USB cable is connected and wait for TWRP to finish initializing ADB."
        return False, last_mode, f"Timed out after {timeout}s waiting for {'/'.join(target_modes)} mode (last state: {last_mode}).{hint}"

    def get_connected_device_info(self):
        info = {
            "connected": False,
            "mode": "none", # "adb", "recovery", "sideload", "fastboot", "unauthorized", "offline", "none"
            "is_wireless": False,
            "ip_address": None,
            "serial": "N/A",
            "model": "Unknown",
            "manufacturer": "Unknown",
            "brand": "Unknown",
            "device": "Unknown",
            "is_c69hd": False,
            "display_id": "Unknown",
            "android_version": "Unknown",
            "boot_slot": "_a",
            "unlocked": False,
            "is_userspace": False,
            "rooted": False,
            "recovery_root": False,
            "battery_level": "N/A",
            "battery_charging": False,
            "storage_avail": "N/A",
            "storage_total": "N/A",
            "raw_devices": ""
        }

        # 1. Check ADB devices (supports device, recovery, sideload, unauthorized, offline)
        ok, out, _ = self.run_adb("devices")
        if ok and out:
            lines = [l.strip() for l in out.splitlines() if l.strip() and not l.startswith("*")]
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 2:
                    serial = parts[0]
                    state = parts[1].lower()
                    info["serial"] = serial
                    if ":" in serial:
                        info["is_wireless"] = True
                        info["ip_address"] = serial.split(":")[0]

                    if state in ("device", "recovery", "sideload"):
                        info["connected"] = True
                        info["mode"] = "adb" if state == "device" else state
                    elif state in ("unauthorized", "offline"):
                        info["mode"] = state
                        return info

        # 2. Check fastboot if not connected via adb
        if not info["connected"]:
            ok, out, _ = self.run_fastboot("devices")
            if ok and out:
                lines = [l.strip() for l in out.splitlines() if l.strip()]
                if lines:
                    parts = lines[0].split()
                    info["connected"] = True
                    info["mode"] = "fastboot"
                    info["serial"] = parts[0]

                    slot_val = self.get_fastboot_var("current-slot")
                    if slot_val:
                        clean_slot = slot_val.strip().lstrip("_")
                        if clean_slot in ("a", "b"):
                            info["boot_slot"] = f"_{clean_slot}"

                    unlocked_val = self.get_fastboot_var("unlocked")
                    if unlocked_val is not None:
                        info["unlocked"] = (unlocked_val.strip().lower() == "yes")

                    userspace_val = self.get_fastboot_var("is-userspace")
                    if userspace_val is not None:
                        info["is_userspace"] = (userspace_val.strip().lower() == "yes")

                    product_val = self.get_fastboot_var("product")
                    if product_val:
                        info["device"] = product_val.strip()
                        if "C69" in product_val.upper() or "BENGAL" in product_val.upper() or "FAUST" in product_val.upper():
                            info["is_c69hd"] = True

                    return info

        if not info["connected"] or info["mode"] == "sideload":
            return info

        # Recovery mode (TWRP) has limited shell properties & root adbd
        if info["mode"] == "recovery":
            ok_id, id_out, _ = self.run_shell("id")
            if ok_id and "uid=0" in id_out:
                info["recovery_root"] = True
            ok_props, out_props, _ = self.run_shell(
                "getprop ro.product.device; echo ---SEP---; getprop ro.boot.slot_suffix; echo ---SEP---; getprop ro.boot.flash.locked"
            )
            if ok_props and out_props:
                props = [p.strip() for p in out_props.split("---SEP---")]
                if len(props) >= 1 and props[0]:
                    info["device"] = props[0]
                    info["model"] = props[0]
                if len(props) >= 2 and props[1] in ("_a", "_b"):
                    info["boot_slot"] = props[1]
                if len(props) >= 3 and props[2]:
                    info["unlocked"] = (props[2] == "0")
            return info

        # Get device IP if not already wireless
        if not info["ip_address"]:
            info["ip_address"] = self.get_device_ip()

        # Extract Device Properties
        ok, out, _ = self.run_shell("getprop ro.product.model; echo ---SEP---; getprop ro.product.manufacturer; echo ---SEP---; getprop ro.product.device; echo ---SEP---; getprop ro.build.display.id; echo ---SEP---; getprop ro.build.version.release; echo ---SEP---; getprop ro.boot.slot_suffix; echo ---SEP---; getprop ro.boot.flash.locked; echo ---SEP---; getprop ro.boot.verifiedbootstate")
        if ok and out:
            props = [p.strip() for p in out.split("---SEP---")]
            if len(props) >= 6:
                info["model"] = props[0]
                info["manufacturer"] = props[1]
                info["device"] = props[2]
                info["display_id"] = props[3]
                info["android_version"] = props[4]
                slot = props[5]
                if slot in ["_a", "_b"]:
                    info["boot_slot"] = slot
                flash_locked = props[6] if len(props) >= 7 else ""
                verified_state = props[7].lower() if len(props) >= 8 else ""
                if flash_locked == "0":
                    info["unlocked"] = True
                elif flash_locked == "1":
                    info["unlocked"] = False
                elif verified_state == "orange":
                    info["unlocked"] = True

        model_upper = (info["model"] + " " + info["device"]).upper()
        if "C69" in model_upper or "FAUST" in model_upper or "M_STAR" in model_upper:
            info["is_c69hd"] = True

        # Check Root (su)
        ok_su, su_out, _ = self.run_shell("su -c 'id'")
        if ok_su and "uid=0" in su_out:
            info["rooted"] = True

        # Check Battery
        ok_bat, bat_out, _ = self.run_shell("dumpsys battery")
        if ok_bat and bat_out:
            for l in bat_out.splitlines():
                if "level:" in l:
                    info["battery_level"] = l.split("level:")[-1].strip() + "%"
                if "USB powered:" in l or "AC powered:" in l:
                    if "true" in l.lower():
                        info["battery_charging"] = True

        # Check Storage
        ok_df, df_out, _ = self.run_shell("df -h /sdcard")
        if ok_df and df_out:
            lines = df_out.splitlines()
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 4:
                    info["storage_total"] = parts[1]
                    info["storage_avail"] = parts[3]

        return info
