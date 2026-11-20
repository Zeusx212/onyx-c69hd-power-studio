import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.adb_manager import ADBManager
from core.device_ops import DeviceOps
from core.scrcpy_manager import ScrcpyManager
from gui.main_window import MainWindow

print("Initializing ADB, DeviceOps, ScrcpyManager...")
adb = ADBManager()
ops = DeviceOps(adb)
scrcpy = ScrcpyManager(log_callback=adb.log)
print("Creating MainWindow...")
app = MainWindow(adb, ops, scrcpy)
print("Testing GUI update cycle...")
app.update()
print("Destroying window...")
app.destroy()
print("SMOKE_TEST_SUCCESS")
