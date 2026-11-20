#!/usr/bin/env python3
"""
Onyx Boox C69HD (Faust 5 OEM) Customization Tool
GUI Entry point.
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.adb_manager import ADBManager
from core.device_ops import DeviceOps
from core.scrcpy_manager import ScrcpyManager
from gui.main_window import MainWindow

def main():
    adb = ADBManager()
    ops = DeviceOps(adb)
    scrcpy = ScrcpyManager(log_callback=adb.log)
    app = MainWindow(adb, ops, scrcpy)
    app.mainloop()

if __name__ == "__main__":
    main()
