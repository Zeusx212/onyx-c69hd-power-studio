#!/usr/bin/env python3
"""
Onyx Boox C69HD (Faust 5 OEM) - Custom E-Ink Boot Animation Generator
Generates a compliant, uncompressed (ZIP_STORED) bootanimation.zip
optimized specifically for 758x1024 Carta E-Ink displays.
"""

import os
import sys
import argparse
import zipfile
import shutil
import time
from PIL import Image, ImageDraw, ImageFont

# Set up module path to access ADBManager if run directly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.adb_manager import ADBManager

WIDTH = 758
HEIGHT = 1024

def get_fonts():
    """Attempts to load Segoe UI or falls back to default fonts."""
    font_paths = {
        "title": [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"],
        "sub": [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"],
        "mono": [r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\cour.ttf"],
    }
    
    loaded = {}
    for key, paths in font_paths.items():
        size = 30 if key == "title" else (14 if key == "sub" else 12)
        font = None
        for p in paths:
            if os.path.exists(p):
                try:
                    font = ImageFont.truetype(p, size)
                    break
                except Exception:
                    pass
        if not font:
            font = ImageFont.load_default()
        loaded[key] = font
    return loaded

def create_frame(theme="dark"):
    """Creates a base canvas for 758x1024 Carta E-Ink."""
    bg_color = 0 if theme == "dark" else 255
    return Image.new("L", (WIDTH, HEIGHT), color=bg_color)

def draw_book_emblem(draw, cx, cy, progress=1.0, theme="dark"):
    """Draws stylized E-Ink vector book emblem based on animation progress (0.0 to 1.0)."""
    fg = 255 if theme == "dark" else 0
    dim = 150 if theme == "dark" else 105

    # Spine
    draw.line([(cx, cy - 20), (cx, cy + 60)], fill=fg, width=2)
    
    if progress <= 0.1:
        return

    # Pages unfold based on progress
    span = int(75 * min(1.0, progress * 1.5))
    drop = int(40 * min(1.0, progress * 1.5))
    h = int(40 * min(1.0, progress * 1.2))

    # Left Page outline
    draw.line([(cx - 4, cy - 20), (cx - span, cy - 20 - (drop // 2))], fill=fg, width=3)
    draw.line([(cx - span, cy - 20 - (drop // 2)), (cx - span, cy + h)], fill=fg, width=3)
    draw.line([(cx - span, cy + h), (cx - 4, cy + 60)], fill=fg, width=3)

    # Right Page outline
    draw.line([(cx + 4, cy - 20), (cx + span, cy - 20 - (drop // 2))], fill=fg, width=3)
    draw.line([(cx + span, cy - 20 - (drop // 2)), (cx + span, cy + h)], fill=fg, width=3)
    draw.line([(cx + span, cy + h), (cx + 4, cy + 60)], fill=fg, width=3)

    if progress >= 0.6:
        # Fanned inner pages (subtle layered depth)
        draw.line([(cx - 4, cy - 14), (cx - span + 7, cy - 12 - (drop // 2)), (cx - span + 7, cy + h + 5), (cx - 4, cy + 64)], fill=dim, width=1)
        draw.line([(cx + 4, cy - 14), (cx + span - 7, cy - 12 - (drop // 2)), (cx + span - 7, cy + h + 5), (cx + 4, cy + 64)], fill=dim, width=1)

    if progress >= 0.8:
        # Stylized text lines on left page
        for offset_y in [-15, 0, 15]:
            draw.line([(cx - span + 15, cy + offset_y), (cx - 20, cy + offset_y + 5)], fill=dim, width=2)

        # Stylized text lines on right page
        for offset_y in [-15, 0, 15]:
            draw.line([(cx + 20, cy + offset_y + 5), (cx + span - 15, cy + offset_y)], fill=dim, width=2)

        # Ribbon bookmark
        draw.polygon([(cx - 4, cy + 60), (cx + 4, cy + 60), (cx + 4, cy + 85), (cx, cy + 78), (cx - 4, cy + 85)], fill=fg)

def draw_header_text(draw, cx, cy, fonts, theme="dark", alpha=1.0):
    """Draws title, subtitle, and divider."""
    if alpha <= 0:
        return
        
    fg = int((255 if theme == "dark" else 0) * alpha)
    dim = int((160 if theme == "dark" else 95) * alpha)
    div_c = int((90 if theme == "dark" else 180) * alpha)

    # Main Title
    t_text = "ONYX BOOX C69HD"
    bbox = draw.textbbox((0, 0), t_text, font=fonts["title"])
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw // 2, cy + 130), t_text, fill=fg, font=fonts["title"])

    # Subtitle
    s_text = "POWER STUDIO • E-INK EDITION"
    sbox = draw.textbbox((0, 0), s_text, font=fonts["sub"])
    sw = sbox[2] - sbox[0]
    draw.text((cx - sw // 2, cy + 175), s_text, fill=dim, font=fonts["sub"])

    # Divider line
    draw.line([cx - 130, cy + 215, cx + 130, cy + 215], fill=div_c, width=1)

def draw_activity_indicator(draw, cx, cy, fonts, frame_idx, theme="dark"):
    """Draws pulsing progress dots and status label."""
    fg = 255 if theme == "dark" else 0
    dim = 70 if theme == "dark" else 185

    dot_x_positions = [cx - 40, cx - 20, cx, cx + 20, cx + 40]
    active_idx = [0, 1, 2, 3, 4, 3, 2, 1][frame_idx % 8]

    for i, x in enumerate(dot_x_positions):
        if i == active_idx:
            r = 5
            c = fg
        else:
            r = 3
            c = dim
        draw.ellipse([x - r, cy + 245 - r, x + r, cy + 245 + r], fill=c)

    cursor = "■" if (frame_idx // 2) % 2 == 0 else " "
    status_text = f"INITIALIZING SYSTEM {cursor}"
    stbox = draw.textbbox((0, 0), status_text, font=fonts["mono"])
    stw = stbox[2] - stbox[0]
    draw.text((cx - stw // 2, cy + 270), status_text, fill=dim, font=fonts["mono"])

def generate_bootanimation_package(output_zip, theme="dark", fps=4):
    """Generates all part0 and part1 frames and bundles uncompressed bootanimation.zip."""
    fonts = get_fonts()
    work_dir = os.path.join(os.path.dirname(os.path.abspath(output_zip)), "_bootanim_build")
    part0_dir = os.path.join(work_dir, "part0")
    part1_dir = os.path.join(work_dir, "part1")

    shutil.rmtree(work_dir, ignore_errors=True)
    os.makedirs(part0_dir, exist_ok=True)
    os.makedirs(part1_dir, exist_ok=True)

    cx, cy = WIDTH // 2, 410

    print(f"Generating part0 intro sequence (12 frames @ {fps} FPS)...")
    total_intro = 12
    for i in range(total_intro):
        img = create_frame(theme)
        draw = ImageDraw.Draw(img)
        progress = (i + 1) / total_intro

        # Book emblem unfolding
        draw_book_emblem(draw, cx, cy, progress=progress, theme=theme)

        # Title fading in on later frames
        if i >= 6:
            text_alpha = (i - 5) / 6.0
            draw_header_text(draw, cx, cy, fonts, theme=theme, alpha=text_alpha)

        dest = os.path.join(part0_dir, f"{i:04d}.png")
        img.save(dest, format="PNG")

    print(f"Generating part1 looping sequence (8 frames @ {fps} FPS)...")
    total_loop = 8
    for i in range(total_loop):
        img = create_frame(theme)
        draw = ImageDraw.Draw(img)

        # Static emblem and title (prevents full-screen E-Ink flashing)
        draw_book_emblem(draw, cx, cy, progress=1.0, theme=theme)
        draw_header_text(draw, cx, cy, fonts, theme=theme, alpha=1.0)

        # Dynamic activity dots and blinking cursor
        draw_activity_indicator(draw, cx, cy, fonts, i, theme=theme)

        dest = os.path.join(part1_dir, f"{i:04d}.png")
        img.save(dest, format="PNG")

    # desc.txt specification
    desc_txt = os.path.join(work_dir, "desc.txt")
    with open(desc_txt, "w", newline="\n") as f:
        f.write(f"{WIDTH} {HEIGHT} {fps}\n")
        f.write("p 1 0 part0\n")
        f.write("p 0 0 part1\n")

    print(f"Packaging uncompressed ZIP: {output_zip}...")
    os.makedirs(os.path.dirname(os.path.abspath(output_zip)), exist_ok=True)
    if os.path.exists(output_zip):
        os.remove(output_zip)

    # Must be uncompressed ZIP_STORED for Android's bootanim binary
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_STORED) as z:
        z.write(desc_txt, "desc.txt")
        for root, dirs, files in os.walk(part0_dir):
            for file in sorted(files):
                full_path = os.path.join(root, file)
                rel_path = os.path.join("part0", file)
                z.write(full_path, rel_path)
        for root, dirs, files in os.walk(part1_dir):
            for file in sorted(files):
                full_path = os.path.join(root, file)
                rel_path = os.path.join("part1", file)
                z.write(full_path, rel_path)

    # Cleanup temporary frames
    shutil.rmtree(work_dir, ignore_errors=True)
    file_size_kb = os.path.getsize(output_zip) / 1024
    print(f"Successfully created bootanimation.zip! Size: {file_size_kb:.1f} KB")
    return True

def preview_on_device(zip_path, duration_sec=5):
    """Pushes animation to device and triggers live bootanim preview."""
    print("Connecting to device via ADB...")
    adb = ADBManager()
    if not adb.is_available():
        print("Error: ADB is not available.")
        return False

    info = adb.get_connected_device_info()
    if not info["connected"]:
        print("Error: No device connected.")
        return False

    remote_tmp = "/data/local/tmp/bootanimation.zip"
    print(f"Pushing {zip_path} -> {remote_tmp}...")
    ok, stdout, stderr = adb.run_adb("push", zip_path, remote_tmp)
    if not ok:
        print(f"Failed to push animation: {stderr}")
        return False

    print(f"Starting live screen preview for {duration_sec}s (ctl.start bootanim)...")
    script = (
        f"su -c 'cp {remote_tmp} /system/media/bootanimation.zip 2>/dev/null || "
        f"mkdir -p /data/adb/modules/c69hd-custom-media/system/media && "
        f"cp {remote_tmp} /data/adb/modules/c69hd-custom-media/system/media/bootanimation.zip; "
        f"setprop ctl.start bootanim; sleep {duration_sec}; setprop ctl.stop bootanim; "
        f"input keyevent KEYCODE_HOME'"
    )
    adb.run_shell(script)
    print("Preview complete!")
    return True

def install_on_device(zip_path):
    """Installs bootanimation.zip permanently via Magisk media overlay."""
    adb = ADBManager()
    info = adb.get_connected_device_info()
    if not info["connected"] or not info.get("rooted"):
        print("Error: Device must be connected and rooted to install boot animation.")
        return False

    module_dir = "/data/adb/modules/c69hd-custom-media"
    module_media = f"{module_dir}/system/media"

    print("Setting up Magisk systemless media overlay...")
    setup_cmds = f"""
su -c 'mkdir -p {module_media}
cat << "EOF" > {module_dir}/module.prop
id=c69hd-custom-media
name=C69HD Custom Media Overlay
version=1.0
versionCode=1
author=Zeusx212
description=Systemless custom boot animation and media overlay for Onyx Boox C69HD.
EOF
touch {module_dir}/auto_mount
chmod -R 755 {module_dir}'
"""
    adb.run_shell(setup_cmds)

    remote_tmp = "/data/local/tmp/bootanimation.zip"
    print("Pushing bootanimation.zip...")
    adb.run_adb("push", zip_path, remote_tmp)

    install_cmd = f"su -c 'cp {remote_tmp} {module_media}/bootanimation.zip && chmod 644 {module_media}/bootanimation.zip && rm -f {remote_tmp}'"
    adb.run_shell(install_cmd)
    print(f"Successfully installed boot animation to {module_media}/bootanimation.zip!")
    return True

def main():
    parser = argparse.ArgumentParser(description="Onyx Boox C69HD Custom Boot Animation Generator")
    parser.add_argument("--theme", choices=["dark", "light"], default="dark", help="Color theme (default: dark)")
    parser.add_argument("--fps", type=int, default=4, help="Frames per second (default: 4)")
    parser.add_argument("--output", default=os.path.join(BASE_DIR, "assets", "bootanimation.zip"), help="Output ZIP path")
    parser.add_argument("--preview", action="store_true", help="Preview live on connected device")
    parser.add_argument("--install", action="store_true", help="Install permanently to Magisk media overlay")

    args = parser.parse_args()

    generate_bootanimation_package(args.output, theme=args.theme, fps=args.fps)

    if args.preview:
        preview_on_device(args.output, duration_sec=5)

    if args.install:
        install_on_device(args.output)

if __name__ == "__main__":
    main()
