"""
Windows native clipboard helper for PIL images.
Provides seamless 64-bit GlobalAlloc DIB clipboard copy.
"""

import io
import os
import ctypes

def copy_pil_image_to_clipboard(pil_image):
    """Copies a PIL Image object to the Windows system clipboard in CF_DIB format."""
    if os.name != 'nt':
        return False, "Clipboard image copy is only supported on Windows."

    try:
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
        return False, str(e)
