"""
ADB and Fastboot execution manager for Onyx Boox C69HD.
Provides robust process execution, device probing, wireless ADB, screenshot capture, and status parsing.
"""

import subprocess
import shutil
import re
import os
import io

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

    def install_tools(self, progress_callback=None):
        """Downloads and sets up official platform tools."""
        ok, adb, fb, ver = install_platform_tools(progress_callback=progress_callback)
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

    def get_connected_device_info(self):
        info = {
            "connected": False,
            "mode": "none", # "adb", "fastboot", "none"
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
            "rooted": False,
            "battery_level": "N/A",
            "battery_charging": False,
            "storage_avail": "N/A",
            "storage_total": "N/A",
            "raw_devices": ""
        }

        # 1. Check ADB devices
        ok, out, _ = self.run_adb("devices")
        if ok and out:
            lines = [l.strip() for l in out.splitlines() if l.strip() and not l.startswith("*")]
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 2 and parts[1] == "device":
                    info["connected"] = True
                    info["mode"] = "adb"
                    info["serial"] = parts[0]
                    if ":" in parts[0]:
                        info["is_wireless"] = True
                        info["ip_address"] = parts[0].split(":")[0]

        # 2. Check fastboot if not in adb
        if not info["connected"]:
            ok, out, _ = self.run_fastboot("devices")
            if ok and out:
                lines = [l.strip() for l in out.splitlines() if l.strip()]
                if lines:
                    parts = lines[0].split()
                    info["connected"] = True
                    info["mode"] = "fastboot"
                    info["serial"] = parts[0]
                    ok_var, var_out, _ = self.run_fastboot("getvar", "current-slot")
                    if "current-slot:" in var_out:
                        slot = var_out.split("current-slot:")[-1].strip()
                        info["boot_slot"] = f"_{slot}" if not slot.startswith("_") else slot
                    return info

        if not info["connected"]:
            return info

        # Get device IP if not already wireless
        if not info["ip_address"]:
            info["ip_address"] = self.get_device_ip()

        # Extract Device Properties
        ok, out, _ = self.run_shell("getprop ro.product.model; echo ---SEP---; getprop ro.product.manufacturer; echo ---SEP---; getprop ro.product.device; echo ---SEP---; getprop ro.build.display.id; echo ---SEP---; getprop ro.build.version.release; echo ---SEP---; getprop ro.boot.slot_suffix; echo ---SEP---; getprop ro.boot.flash.locked")
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
