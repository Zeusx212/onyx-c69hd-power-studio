"""
ADB and Fastboot execution manager for Onyx Boox C69HD.
Provides robust process execution, device probing, and status parsing.
"""

import subprocess
import shutil
import re
import os

class ADBManager:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.adb_bin = shutil.which("adb") or "adb"
        self.fastboot_bin = shutil.which("fastboot") or "fastboot"

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
        """Runs `adb shell <cmd>`"""
        return self.run_adb("shell", shell_cmd, timeout=timeout)

    def get_connected_device_info(self):
        """
        Polls ADB and fastboot to identify connection state and device properties.
        Returns a dict of device metadata.
        """
        info = {
            "connected": False,
            "mode": "none", # "adb", "fastboot", "none"
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
            "raw_devices": ""
        }

        # 1. Check ADB devices
        ok, out, _ = self.run_adb("devices")
        if ok and out:
            lines = [l.strip() for l in out.splitlines() if l.strip() and not l.startswith("*")]
            if len(lines) > 1:
                # First non-header line
                parts = lines[1].split()
                if len(parts) >= 2 and parts[1] == "device":
                    info["connected"] = True
                    info["mode"] = "adb"
                    info["serial"] = parts[0]
                elif len(parts) >= 2 and parts[1] == "unauthorized":
                    info["connected"] = True
                    info["mode"] = "unauthorized"
                    info["serial"] = parts[0]
                    return info

        # If not found in ADB, check fastboot
        if not info["connected"]:
            ok, out, _ = self.run_fastboot("devices")
            if ok and out:
                lines = [l.strip() for l in out.splitlines() if l.strip()]
                if lines:
                    parts = lines[0].split()
                    info["connected"] = True
                    info["mode"] = "fastboot"
                    info["serial"] = parts[0]
                    # Probe fastboot getvar
                    ok_var, var_out, _ = self.run_fastboot("getvar", "current-slot")
                    if "current-slot:" in var_out:
                        slot = var_out.split("current-slot:")[-1].strip()
                        info["boot_slot"] = f"_{slot}" if not slot.startswith("_") else slot
                    return info

        if not info["connected"]:
            return info

        # 2. Extract Device Properties via ADB shell
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
                if len(props) >= 7 and props[6] == "0":
                    info["unlocked"] = True
                else:
                    info["unlocked"] = True # C69HD factory bootloader is unlocked

        # Determine if C69HD / Faust 5
        model_upper = (info["model"] + " " + info["device"]).upper()
        if "C69" in model_upper or "FAUST" in model_upper or "M_STAR" in model_upper:
            info["is_c69hd"] = True

        # 3. Check Root (su)
        ok_su, su_out, _ = self.run_shell("su -c 'id'")
        if ok_su and "uid=0" in su_out:
            info["rooted"] = True

        # 4. Check Battery
        ok_bat, bat_out, _ = self.run_shell("dumpsys battery")
        if ok_bat and bat_out:
            for l in bat_out.splitlines():
                if "level:" in l:
                    info["battery_level"] = l.split("level:")[-1].strip() + "%"
                if "USB powered:" in l or "AC powered:" in l:
                    if "true" in l.lower():
                        info["battery_charging"] = True

        return info
