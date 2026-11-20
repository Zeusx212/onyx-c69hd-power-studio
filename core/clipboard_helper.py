"""
Cross-platform native clipboard helper for PIL images.
Supports:
- Windows: 64-bit GlobalAlloc CF_DIB
- macOS: Native osascript AppleScript PNG pasteboard
- Linux: X11 xclip / Wayland wl-copy with PNG MIME
"""

import io
import os
import sys
import shutil
import tempfile
import subprocess

def copy_pil_image_to_clipboard(pil_image):
    """Copies a PIL Image object to the system clipboard across Windows, macOS, and Linux."""
    # 1. Windows Implementation (CF_DIB via Win32 API)
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import c_void_p, c_size_t, c_uint
            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32

            kernel32.GlobalAlloc.argtypes = [c_uint, c_size_t]
            kernel32.GlobalAlloc.restype = c_void_p
            kernel32.GlobalLock.argtypes = [c_void_p]
            kernel32.GlobalLock.restype = c_void_p
            kernel32.GlobalUnlock.argtypes = [c_void_p]
            user32.OpenClipboard.argtypes = [c_void_p]
            user32.SetClipboardData.argtypes = [c_uint, c_void_p]

            output = io.BytesIO()
            pil_image.convert('RGB').save(output, 'BMP')
            data = output.getvalue()[14:]  # Strip 14-byte BITMAPFILEHEADER to get CF_DIB
            output.close()

            GMEM_MOVEABLE = 0x0002
            h_glob = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not h_glob:
                return False, "Failed to allocate global memory"

            p_glob = kernel32.GlobalLock(h_glob)
            ctypes.memmove(p_glob, data, len(data))
            kernel32.GlobalUnlock(h_glob)

            user32.OpenClipboard(None)
            user32.EmptyClipboard()
            CF_DIB = 8
            user32.SetClipboardData(CF_DIB, h_glob)
            user32.CloseClipboard()
            return True, "Image successfully copied to Windows clipboard!"
        except Exception as e:
            return False, f"Windows clipboard error: {e}"

    # 2. macOS Implementation (osascript / NSPasteboard)
    elif sys.platform == "darwin":
        tmp_png = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                tmp_png = f.name
                pil_image.save(tmp_png, "PNG")

            script = f'set the clipboard to (read (POSIX file "{tmp_png}") as «class PNGf»)'
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return True, "Image successfully copied to macOS pasteboard!"
            else:
                return False, f"macOS clipboard error: {res.stderr.strip()}"
        except Exception as e:
            return False, f"macOS clipboard exception: {e}"
        finally:
            if tmp_png and os.path.exists(tmp_png):
                try: os.remove(tmp_png)
                except Exception: pass

    # 3. Linux Implementation (wl-copy or xclip)
    else:
        tmp_png = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                tmp_png = f.name
                pil_image.save(tmp_png, "PNG")

            # Try wl-copy (Wayland)
            if shutil.which("wl-copy"):
                with open(tmp_png, "rb") as png_in:
                    res = subprocess.run(["wl-copy", "-t", "image/png"], stdin=png_in, capture_output=True, timeout=5)
                    if res.returncode == 0:
                        return True, "Image successfully copied to Wayland clipboard (wl-copy)!"

            # Try xclip (X11)
            if shutil.which("xclip"):
                res = subprocess.run(["xclip", "-selection", "clipboard", "-t", "image/png", "-i", tmp_png], capture_output=True, timeout=5)
                if res.returncode == 0:
                    return True, "Image successfully copied to X11 clipboard (xclip)!"

            # Try xsel
            if shutil.which("xsel"):
                return False, "xsel does not support image mime types. Install xclip or wl-clipboard: sudo apt install xclip"

            return False, "No clipboard utility found on Linux. Please install xclip (sudo apt install xclip) or wl-clipboard."
        except Exception as e:
            return False, f"Linux clipboard exception: {e}"
        finally:
            if tmp_png and os.path.exists(tmp_png):
                try: os.remove(tmp_png)
                except Exception: pass
