#!/usr/bin/env python3
"""
Onyx Boox C69HD (Faust 5 OEM) Customization Tool
GUI Entry point.
"""

import sys
import os

# Ensure local directories are in python search path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.adb_manager import ADBManager
from core.device_ops import DeviceOps
from gui.main_window import MainWindow

def main():
    adb = ADBManager()
    ops = DeviceOps(adb)
    app = MainWindow(adb, ops)
    app.mainloop()

if __name__ == "__main__":
    main()
