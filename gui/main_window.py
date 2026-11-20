"""
Comprehensive modern CustomTkinter GUI for Onyx Boox C69HD Customizer.
Includes Native Embedded Scrcpy Screen Mirroring, Root/Partitions, Button Remap,
Screensaver Studio, Book Library Sync, E-Ink App Sideload Hub, Remote E-Ink Controls & Screenshot,
1-Click Presets, Debloater, System Settings, and Wireless ADB.
"""

import os
import queue
import threading
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

from core.device_ops import (
    BUTTON_ACTIONS,
    DEBLOAT_CATALOG,
    CURATED_EINK_APPS,
    HAS_PILLOW
)
from core.clipboard_helper import copy_pil_image_to_clipboard

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MainWindow(ctk.CTk):
    def __init__(self, adb_manager, device_ops, scrcpy_manager):
        super().__init__()
        self.adb = adb_manager
        self.ops = device_ops
        self.scrcpy = scrcpy_manager
        self.device_info = {}
        self._gui_queue = queue.Queue()

        self.adb.log_callback = self.append_log
        self.scrcpy.log_callback = self.append_log

        self.title("Onyx Boox C69HD Suite • Faust 5 OEM Power Studio")
        self.geometry("1180x840")
        self.minsize(1040, 720)

        # State variables
        self._selected_image_path = None
        self._selected_bootanim_path = None
        self._selected_books = []
        self._ctk_preview_image = None
        self._ctk_screenshot_image = None
        self._last_pil_screenshot = None
        self._record_video_path = None

        # Colors
        self.COLOR_SIDEBAR = "#0F1219"
        self.COLOR_MAIN_BG = "#080A0F"
        self.COLOR_CARD = "#141822"
        self.COLOR_CARD_BORDER = "#1E2433"
        self.COLOR_CYAN = "#38BDF8"
        self.COLOR_BLUE = "#3B82F6"
        self.COLOR_GREEN = "#10B981"
        self.COLOR_RED = "#EF4444"
        self.COLOR_AMBER = "#F59E0B"
        self.COLOR_TEXT_MUTED = "#94A3B8"

        self.configure(fg_color=self.COLOR_MAIN_BG)

        # Start thread-safe GUI dispatch loop
        self._process_gui_queue()

        # Window close handler to terminate background scrcpy cleanly
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_content_area()

        # Start on Presets
        self._show_page("presets")

        # Initial device probe
        self.refresh_device_status_async()

    def dispatch(self, func, *args, **kwargs):
        """Thread-safe queue dispatch to execute callbacks on the Tkinter main loop."""
        self._gui_queue.put((func, args, kwargs))

    def _process_gui_queue(self):
        try:
            while True:
                func, args, kwargs = self._gui_queue.get_nowait()
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    print(f"[GUI Dispatch Error] {e}")
        except queue.Empty:
            pass
        except Exception:
            pass
        finally:
            try:
                self.after(30, self._process_gui_queue)
            except Exception:
                pass

    def _on_close(self):
        if self.scrcpy.is_running():
            self.scrcpy.stop()
        self.destroy()

    # =========================================================================
    # SIDEBAR NAVIGATION & WIRELESS ADB
    # =========================================================================
    def _build_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color=self.COLOR_SIDEBAR)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")

        # Brand Box
        brand_box = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        brand_box.pack(fill="x", padx=18, pady=(20, 14))

        ctk.CTkLabel(
            brand_box,
            text="ONYX C69HD",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#FFFFFF"
        ).pack(anchor="w")

        ctk.CTkLabel(
            brand_box,
            text="Faust 5 OEM Studio • v3.1",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=self.COLOR_CYAN
        ).pack(anchor="w")

        # Navigation Scroll Area
        nav_scroll = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        nav_scroll.pack(fill="both", expand=True, padx=8, pady=4)

        self.nav_buttons = {}
        pages = [
            ("presets", "🏆  1-Click Presets"),
            ("mirror", "📱  Screen Mirror (Scrcpy)"),
            ("root", "🛡️  Root & Partitions"),
            ("button", "🔘  Button Remapper"),
            ("media", "🎨  Screensaver & Boot"),
            ("books", "📚  Books & Library"),
            ("apps", "📦  E-Ink App Store"),
            ("remote", "⚡  E-Ink Remote & Snip"),
            ("debloat", "🧹  Reversible Debloat"),
            ("settings", "⚙️  Device Settings"),
            ("logs", "📊  Hardware & Logs")
        ]

        for page_id, text in pages:
            btn = ctk.CTkButton(
                nav_scroll,
                text=text,
                height=38,
                corner_radius=8,
                fg_color="transparent",
                text_color=self.COLOR_TEXT_MUTED,
                hover_color="#1A202C",
                anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="normal"),
                command=lambda pid=page_id: self._show_page(pid)
            )
            btn.pack(fill="x", pady=2)
            self.nav_buttons[page_id] = btn

        # Bottom Device Status & Wireless ADB Card
        status_box = ctk.CTkFrame(self.sidebar_frame, corner_radius=10, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        status_box.pack(side="bottom", fill="x", padx=12, pady=14)

        self.lbl_device_title = ctk.CTkLabel(
            status_box,
            text="Probing Device...",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#FFFFFF"
        )
        self.lbl_device_title.pack(anchor="w", padx=12, pady=(10, 2))

        self.lbl_device_details = ctk.CTkLabel(
            status_box,
            text="Slot: -- • Battery: --",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=self.COLOR_TEXT_MUTED
        )
        self.lbl_device_details.pack(anchor="w", padx=12, pady=(0, 6))

        self.lbl_status_badge = ctk.CTkLabel(
            status_box,
            text="DISCONNECTED",
            corner_radius=6,
            fg_color="#7F1D1D",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            padx=8,
            pady=3
        )
        self.lbl_status_badge.pack(anchor="w", padx=12, pady=(0, 8))

        # 1-Click ADB Installer button (shown if ADB is missing)
        self.btn_sidebar_install_adb = ctk.CTkButton(
            status_box,
            text="📥 Auto-Install ADB & Fastboot",
            height=30,
            corner_radius=6,
            fg_color=self.COLOR_GREEN,
            hover_color="#059669",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._action_install_adb
        )

        self.btn_wireless = ctk.CTkButton(
            status_box,
            text="📶 Connect via Wi-Fi",
            height=28,
            corner_radius=6,
            fg_color="#1E293B",
            hover_color="#334155",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._action_toggle_wireless_adb
        )
        self.btn_wireless.pack(fill="x", padx=12, pady=(0, 6))

        ctk.CTkButton(
            status_box,
            text="↻ Refresh Status",
            height=26,
            corner_radius=6,
            fg_color="transparent",
            hover_color="#1E2433",
            text_color=self.COLOR_CYAN,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self.refresh_device_status_async
        ).pack(fill="x", padx=12, pady=(0, 8))

    # =========================================================================
    # CONTENT AREA & PAGES
    # =========================================================================
    def _build_content_area(self):
        self.content_container = ctk.CTkFrame(self, fg_color=self.COLOR_MAIN_BG, corner_radius=0)
        self.content_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=18)
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

        self.pages = {}
        self.pages["presets"] = self._create_page_presets()
        self.pages["mirror"] = self._create_page_mirror()
        self.pages["root"] = self._create_page_root()
        self.pages["button"] = self._create_page_button()
        self.pages["media"] = self._create_page_media()
        self.pages["books"] = self._create_page_books()
        self.pages["apps"] = self._create_page_apps()
        self.pages["remote"] = self._create_page_remote()
        self.pages["debloat"] = self._create_page_debloat()
        self.pages["settings"] = self._create_page_settings()
        self.pages["logs"] = self._create_page_logs()

    def _show_page(self, page_id):
        for pid, frame in self.pages.items():
            if pid == page_id:
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.grid_forget()

        for pid, btn in self.nav_buttons.items():
            if pid == page_id:
                btn.configure(fg_color="#1A202C", text_color=self.COLOR_CYAN, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
            else:
                btn.configure(fg_color="transparent", text_color=self.COLOR_TEXT_MUTED, font=ctk.CTkFont(family="Segoe UI", size=12, weight="normal"))

    # =========================================================================
    # PAGE: LIVE SCREEN MIRROR (SCRCPY INTEGRATION)
    # =========================================================================
    def _create_page_mirror(self):
        page = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")

        # Header Title
        lbl_h = ctk.CTkLabel(page, text="Live Screen Mirror (Scrcpy)", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        lbl_h.pack(anchor="w", pady=(0, 4))
        lbl_sub = ctk.CTkLabel(page, text="Hardware-accelerated Direct3D11 screen mirror with E-Ink optimizations, keyboard & mouse controls, and instant APK drag-and-drop.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", pady=(0, 16))

        # Two-column container
        split = ctk.CTkFrame(page, fg_color="transparent")
        split.pack(fill="both", expand=True)
        split.grid_columnconfigure(0, weight=1)
        split.grid_columnconfigure(1, weight=1)

        # -------------------------------------------------------------
        # Left Card: Mirroring Controls & Stream Configuration
        # -------------------------------------------------------------
        ctrl_card = ctk.CTkFrame(split, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        ctrl_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        inner_ctrl = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        inner_ctrl.pack(fill="both", expand=True, padx=18, pady=16)

        ctk.CTkLabel(inner_ctrl, text="Mirror Session Controls", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w")

        # Status Badge
        self.lbl_mirror_status = ctk.CTkLabel(
            inner_ctrl,
            text="STATUS: IDLE",
            corner_radius=6,
            fg_color="#1E293B",
            text_color=self.COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            padx=8,
            pady=4
        )
        self.lbl_mirror_status.pack(anchor="w", pady=(8, 4))

        # Binary status
        bin_path = self.scrcpy.get_binary_path()
        bin_avail = self.scrcpy.is_available()
        bin_desc = f"scrcpy ({os.path.basename(bin_path)})" if bin_avail else "scrcpy not found"
        self.lbl_scrcpy_bin = ctk.CTkLabel(
            inner_ctrl,
            text=f"Engine: {bin_desc}",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=self.COLOR_GREEN if bin_avail else self.COLOR_RED
        )
        self.lbl_scrcpy_bin.pack(anchor="w", pady=(0, 10))

        if not bin_avail:
            self.btn_install_scrcpy = ctk.CTkButton(
                inner_ctrl,
                text="📥 Install Scrcpy (WinGet)",
                height=30,
                corner_radius=6,
                fg_color="#0284C7",
                hover_color="#0369A1",
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                command=self._action_install_scrcpy_winget
            )
            self.btn_install_scrcpy.pack(anchor="w", pady=(0, 12))

        # Start / Stop Buttons
        btn_box = ctk.CTkFrame(inner_ctrl, fg_color="transparent")
        btn_box.pack(fill="x", pady=(0, 14))

        self.btn_start_mirror = ctk.CTkButton(
            btn_box,
            text="▶ Launch Mirror Window",
            height=38,
            corner_radius=8,
            fg_color=self.COLOR_GREEN,
            hover_color="#059669",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._action_start_scrcpy
        )
        self.btn_start_mirror.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_stop_mirror = ctk.CTkButton(
            btn_box,
            text="⏹ Stop",
            height=38,
            corner_radius=8,
            fg_color=self.COLOR_RED,
            hover_color="#DC2626",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._action_stop_scrcpy,
            state="disabled"
        )
        self.btn_stop_mirror.pack(side="right", fill="x", expand=True)

        # Quality Preset
        ctk.CTkLabel(inner_ctrl, text="Quality / Performance Profile:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(anchor="w", pady=(4, 2))
        self.opt_mirror_profile = ctk.CTkOptionMenu(
            inner_ctrl,
            height=32,
            corner_radius=8,
            values=[
                "E-Ink Optimal (758px, 15 FPS, 2M) [Recommended]",
                "Crisp Reading (1024px, 20 FPS, 4M)",
                "Full Speed (Native, 60 FPS, 8M)"
            ],
            width=300
        )
        self.opt_mirror_profile.set("E-Ink Optimal (758px, 15 FPS, 2M) [Recommended]")
        self.opt_mirror_profile.pack(anchor="w", pady=(0, 12))

        # E-Ink Power Toggles
        ctk.CTkLabel(inner_ctrl, text="E-Ink Optimizations:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(anchor="w", pady=(6, 4))

        self.sw_turn_screen_off = ctk.CTkSwitch(
            inner_ctrl,
            text="Turn Device Screen OFF while mirroring\n(Saves E-Ink battery, control 100% from PC)",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.sw_turn_screen_off.pack(anchor="w", pady=4)

        self.sw_stay_awake = ctk.CTkSwitch(inner_ctrl, text="Keep Device Awake (--stay-awake)", font=ctk.CTkFont(family="Segoe UI", size=11))
        self.sw_stay_awake.select()
        self.sw_stay_awake.pack(anchor="w", pady=4)

        self.sw_mirror_ontop = ctk.CTkSwitch(inner_ctrl, text="Always on Top Window (--always-on-top)", font=ctk.CTkFont(family="Segoe UI", size=11))
        self.sw_mirror_ontop.pack(anchor="w", pady=4)

        self.sw_mirror_readonly = ctk.CTkSwitch(ctrl_card, text="Read-Only Mode (--no-control)", font=ctk.CTkFont(family="Segoe UI", size=11))
        self.sw_mirror_readonly.pack(anchor="w", pady=4)

        # Record to MP4 row
        rec_box = ctk.CTkFrame(inner_ctrl, fg_color="transparent")
        rec_box.pack(fill="x", pady=(12, 4))
        self.sw_record = ctk.CTkSwitch(rec_box, text="Record to MP4:", font=ctk.CTkFont(family="Segoe UI", size=11))
        self.sw_record.pack(side="left")
        ctk.CTkButton(rec_box, text="Choose Path...", width=95, height=26, corner_radius=6, fg_color="#283042", command=self._action_choose_record_path).pack(side="right")

        self.lbl_record_path = ctk.CTkLabel(inner_ctrl, text="No recording path set", font=ctk.CTkFont(family="Segoe UI", size=10), text_color=self.COLOR_TEXT_MUTED)
        self.lbl_record_path.pack(anchor="w", pady=(0, 6))

        # -------------------------------------------------------------
        # Right Card: Remote Key Controls & Keyboard Shortcuts Cheat-Sheet
        # -------------------------------------------------------------
        remote_card = ctk.CTkFrame(split, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        remote_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)

        inner_rem = ctk.CTkFrame(remote_card, fg_color="transparent")
        inner_rem.pack(fill="both", expand=True, padx=18, pady=16)

        ctk.CTkLabel(inner_rem, text="Remote E-Ink Key Controls", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w")
        ctk.CTkLabel(inner_rem, text="Send hardware keyevents and e-ink commands directly to device.", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=self.COLOR_TEXT_MUTED).pack(anchor="w", pady=(2, 10))

        m_nav1 = ctk.CTkFrame(inner_rem, fg_color="transparent")
        m_nav1.pack(fill="x", pady=2)
        ctk.CTkButton(m_nav1, text="◀ Back", height=32, corner_radius=6, fg_color="#283042", command=lambda: self.ops.send_keyevent("KEYCODE_BACK")).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(m_nav1, text="⌂ Home", height=32, corner_radius=6, fg_color="#283042", command=lambda: self.ops.send_keyevent("KEYCODE_HOME")).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(m_nav1, text="☰ Overview", height=32, corner_radius=6, fg_color="#283042", command=lambda: self.ops.send_keyevent("KEYCODE_APP_SWITCH")).grid(row=0, column=2, padx=2, pady=2, sticky="ew")
        m_nav1.grid_columnconfigure(0, weight=1)
        m_nav1.grid_columnconfigure(1, weight=1)
        m_nav1.grid_columnconfigure(2, weight=1)

        m_nav2 = ctk.CTkFrame(inner_rem, fg_color="transparent")
        m_nav2.pack(fill="x", pady=2)
        ctk.CTkButton(m_nav2, text="🔊 Vol Up", height=30, corner_radius=6, fg_color="#1E293B", command=lambda: self.ops.send_keyevent("KEYCODE_VOLUME_UP")).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(m_nav2, text="🔉 Vol Down", height=30, corner_radius=6, fg_color="#1E293B", command=lambda: self.ops.send_keyevent("KEYCODE_VOLUME_DOWN")).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(m_nav2, text="🔒 Lock / Sleep", height=30, corner_radius=6, fg_color="#1E293B", command=lambda: self.ops.send_keyevent("KEYCODE_POWER")).grid(row=0, column=2, padx=2, pady=2, sticky="ew")
        m_nav2.grid_columnconfigure(0, weight=1)
        m_nav2.grid_columnconfigure(1, weight=1)
        m_nav2.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(inner_rem, text="🔄 Clear Ghosting (Full Screen Refresh)", height=34, corner_radius=6, fg_color=self.COLOR_BLUE, hover_color="#2563EB", command=self.ops.trigger_eink_refresh).pack(fill="x", pady=(10, 4))
        ctk.CTkButton(inner_rem, text="⚡ Toggle A2 Speed Mode", height=30, corner_radius=6, fg_color="#1E293B", command=self.ops.toggle_a2_speed_mode).pack(fill="x", pady=(0, 14))

        # Shortcuts Guide Box
        ctk.CTkLabel(inner_rem, text="Scrcpy Window Keyboard Shortcuts", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color="#FFFFFF").pack(anchor="w", pady=(6, 4))

        shortcuts_box = ctk.CTkFrame(inner_rem, corner_radius=8, fg_color="#080A10", border_width=1, border_color=self.COLOR_CARD_BORDER)
        shortcuts_box.pack(fill="x", pady=4)

        shortcuts = [
            ("Alt + o", "Turn device screen OFF (keeps PC mirror active)"),
            ("Alt + Shift + o", "Turn device screen ON"),
            ("Alt + p", "Power toggle (wake or sleep device)"),
            ("Alt + r", "Rotate screen clockwise"),
            ("Alt + f", "Toggle fullscreen mode"),
            ("Alt + n", "Expand notification panel"),
            ("Alt + v", "Paste PC clipboard to device"),
            ("Drag & Drop", "Drop APK files into window to install")
        ]

        for key, desc in shortcuts:
            row = ctk.CTkFrame(shortcuts_box, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=3)
            ctk.CTkLabel(row, text=key, font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color=self.COLOR_CYAN, width=110, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=desc, font=ctk.CTkFont(family="Segoe UI", size=10), text_color=self.COLOR_TEXT_MUTED, anchor="w").pack(side="left", fill="x", expand=True)

        return page

    # =========================================================================
    # ACTIONS: SCRCPY MIRRORING
    # =========================================================================
    def _action_choose_record_path(self):
        f = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")])
        if f:
            self._record_video_path = f
            self.lbl_record_path.configure(text=os.path.basename(f))
            self.sw_record.select()

    def _action_start_scrcpy(self):
        if self.scrcpy.is_running():
            return

        if not self.scrcpy.is_available():
            messagebox.showerror(
                "Scrcpy Not Found",
                "scrcpy executable was not found on your PC.\n\n"
                "Please click '📥 Install Scrcpy (WinGet)' or install via PowerShell:\n"
                "winget install Genymobile.scrcpy"
            )
            return

        serial = self.device_info.get("serial")
        if not serial or serial in ("N/A", "Unknown"):
            serial = self.adb.get_quick_serial()

        if not serial:
            messagebox.showwarning(
                "Device Not Connected",
                "Please connect your Onyx Boox C69HD via USB Debugging or Wi-Fi ADB before starting screen mirror."
            )
            return

        profile = self.opt_mirror_profile.get()

        max_size = "758"
        max_fps = "15"
        bit_rate = "2M"

        if "1024px" in profile:
            max_size = "1024"
            max_fps = "20"
            bit_rate = "4M"
        elif "Full Speed" in profile:
            max_size = "native"
            max_fps = "60"
            bit_rate = "8M"

        options = {
            "serial": serial,
            "max_size": max_size,
            "max_fps": max_fps,
            "bit_rate": bit_rate,
            "turn_screen_off": bool(self.sw_turn_screen_off.get()),
            "stay_awake": bool(self.sw_stay_awake.get()),
            "always_on_top": bool(self.sw_mirror_ontop.get()),
            "read_only": bool(self.sw_mirror_readonly.get()),
            "record_file": self._record_video_path if self.sw_record.get() else None,
        }

        self.lbl_mirror_status.configure(text="STATUS: LAUNCHING...", fg_color=self.COLOR_AMBER, text_color="#FFFFFF")
        self.btn_start_mirror.configure(state="disabled")

        def _on_stop_cb(exit_code=0, error_msg=None):
            self.dispatch(self._handle_scrcpy_stopped, exit_code, error_msg)

        ok, msg = self.scrcpy.start(options=options, on_stop=_on_stop_cb)
        if ok:
            self.lbl_mirror_status.configure(text=f"STATUS: STREAMING ({max_size}px / {max_fps} FPS)", fg_color="#064E3B", text_color="#FFFFFF")
            self.btn_stop_mirror.configure(state="normal")
        else:
            self.lbl_mirror_status.configure(text="STATUS: ERROR", fg_color=self.COLOR_RED, text_color="#FFFFFF")
            self.btn_start_mirror.configure(state="normal")
            messagebox.showerror("Scrcpy Error", f"Failed to start mirror:\n{msg}")

    def _action_stop_scrcpy(self):
        self.scrcpy.stop()
        self._handle_scrcpy_stopped(0, None)

    def _handle_scrcpy_stopped(self, exit_code=0, error_msg=None):
        self.btn_start_mirror.configure(state="normal")
        self.btn_stop_mirror.configure(state="disabled")
        if exit_code not in (0, None):
            self.lbl_mirror_status.configure(text=f"STATUS: EXITED (Code {exit_code})", fg_color=self.COLOR_RED, text_color="#FFFFFF")
            if error_msg:
                messagebox.showerror("Scrcpy Mirror Error", f"Scrcpy mirror stopped unexpectedly (exit code {exit_code}):\n\n{error_msg}")
        else:
            self.lbl_mirror_status.configure(text="STATUS: IDLE", fg_color="#1E293B", text_color=self.COLOR_TEXT_MUTED)

    def _action_install_scrcpy_winget(self):
        def _run():
            self.append_log("Installing scrcpy via WinGet...")
            res = subprocess.run(["winget", "install", "--id", "Genymobile.scrcpy", "--silent", "--accept-source-agreements", "--accept-package-agreements"], capture_output=True, text=True)
            self.scrcpy.scrcpy_bin = self.scrcpy.locate_scrcpy_executable()
            if self.scrcpy.is_available():
                self.dispatch(lambda: messagebox.showinfo("Scrcpy Installed", "Scrcpy was installed successfully!"))
                self.dispatch(lambda: self.lbl_scrcpy_bin.configure(text=f"Engine: scrcpy ({os.path.basename(self.scrcpy.get_binary_path())})", text_color=self.COLOR_GREEN))
            else:
                self.dispatch(lambda: messagebox.showerror("Install Failed", f"Could not install scrcpy automatically:\n{res.stderr or res.stdout}"))
        threading.Thread(target=_run, daemon=True).start()

    def _action_install_scrcpy_winget(self):
        def _run():
            self.append_log("Installing scrcpy via WinGet...")
            res = subprocess.run(["winget", "install", "--id", "Genymobile.scrcpy", "--silent", "--accept-source-agreements", "--accept-package-agreements"], capture_output=True, text=True)
            self.scrcpy.scrcpy_bin = self.scrcpy.locate_scrcpy_executable()
            if self.scrcpy.is_available():
                self.dispatch(lambda: messagebox.showinfo("Scrcpy Installed", "Scrcpy was installed successfully!"))
                self.dispatch(lambda: self.lbl_scrcpy_bin.configure(text=f"Engine: scrcpy ({os.path.basename(self.scrcpy.get_binary_path())})", text_color=self.COLOR_GREEN))
            else:
                self.dispatch(lambda: messagebox.showerror("Install Failed", f"Could not install scrcpy automatically:\n{res.stderr or res.stdout}"))
        threading.Thread(target=_run, daemon=True).start()

    # =========================================================================
    # PAGE: 1-CLICK PROFILES (PRESETS)
    # =========================================================================
    def _create_page_presets(self):
        page = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")

        lbl_h = ctk.CTkLabel(page, text="1-Click Device Profiles", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        lbl_h.pack(anchor="w", pady=(0, 4))
        lbl_sub = ctk.CTkLabel(page, text="Apply curated profiles tailored for battery endurance, maximum free RAM, or focused reading.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", pady=(0, 16))

        presets = [
            (
                "🔋 Extreme Battery Life Profile",
                "Fixes screen timeout to 2 minutes, shuts down background Bluetooth LE & Wi-Fi scanning, turns off Location, and disables Qualcomm voice listener & cellular daemons. Maximum battery standby.",
                self.COLOR_GREEN,
                "#059669",
                self._action_apply_preset_battery
            ),
            (
                "⚡ Free RAM Booster Profile (+320MB RAM)",
                "The C69HD has only 2GB RAM. This profile suspends Google Play Services, Services Framework, Onyx Mail, and stock AOSP keyboards, freeing over 320 MB of usable memory for seamless multitasking.",
                self.COLOR_BLUE,
                "#2563EB",
                self._action_apply_preset_ram
            ),
            (
                "📖 Distraction-Free Reading Profile",
                "Sets a relaxed 10-minute screen timeout, optimizes font scale to 1.05, silences background telemetry, and configures an ideal uninterrupted reading environment.",
                "#8B5CF6",
                "#7C3AED",
                self._action_apply_preset_reading
            ),
            (
                "🔄 Factory Default Revert",
                "Re-enables all disabled system packages, restores standard button mapping (toggleFrontLight), and returns settings to default.",
                self.COLOR_RED,
                "#DC2626",
                self._action_apply_preset_restore
            )
        ]

        for title, desc, color, hover, cmd in presets:
            card = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
            card.pack(fill="x", pady=6)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=18, pady=16)

            ctk.CTkLabel(inner, text=title, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#FFFFFF").pack(anchor="w")
            ctk.CTkLabel(inner, text=desc, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=self.COLOR_TEXT_MUTED, justify="left", wraplength=700).pack(anchor="w", pady=(4, 12))

            ctk.CTkButton(
                inner,
                text="Apply This Profile",
                height=34,
                corner_radius=8,
                fg_color=color,
                hover_color=hover,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                command=cmd
            ).pack(anchor="w")

        return page

    # =========================================================================
    # PAGE: BOOKS & LIBRARY SYNC
    # =========================================================================
    def _create_page_books(self):
        page = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")

        lbl_h = ctk.CTkLabel(page, text="Books & Document Transfer Hub", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        lbl_h.pack(anchor="w", pady=(0, 4))
        lbl_sub = ctk.CTkLabel(page, text="Send books, comics, and PDFs directly to your Onyx bookshelf with automatic library indexing.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", pady=(0, 16))

        card = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        card.pack(fill="x", pady=8)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=16)

        ctk.CTkLabel(inner, text="Select Books to Transfer", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w")
        ctk.CTkLabel(
            inner,
            text="Supports EPUB, PDF, MOBI, AZW3, CBZ, CBR, TXT. Transferred files automatically trigger\n"
                 "Android's MediaScanner so they appear instantly on the Onyx Bookshelf without restarting.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=self.COLOR_TEXT_MUTED,
            justify="left"
        ).pack(anchor="w", pady=(2, 10))

        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(anchor="w", pady=4)

        ctk.CTkButton(btn_row, text="📁 Choose Book Files...", height=34, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=self._action_choose_books).pack(side="left", padx=(0, 10))
        self.lbl_books_count = ctk.CTkLabel(btn_row, text="No files selected", text_color=self.COLOR_TEXT_MUTED)
        self.lbl_books_count.pack(side="left")

        dest_row = ctk.CTkFrame(inner, fg_color="transparent")
        dest_row.pack(anchor="w", pady=10)

        ctk.CTkLabel(dest_row, text="Destination on Device:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(side="left", padx=(0, 8))
        self.opt_book_dest = ctk.CTkOptionMenu(
            dest_row,
            height=32,
            corner_radius=8,
            values=["/sdcard/Books", "/sdcard/Books/Manga", "/sdcard/Books/Comics", "/sdcard/Download"],
            width=260
        )
        self.opt_book_dest.pack(side="left")

        ctk.CTkButton(
            inner,
            text="🚀  Transfer Books to Device & Sync Library",
            height=38,
            corner_radius=8,
            fg_color=self.COLOR_BLUE,
            hover_color="#2563EB",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._action_push_books
        ).pack(anchor="w", pady=(12, 4))

        self.txt_books_list = ctk.CTkTextbox(inner, height=130, corner_radius=8, fg_color="#0A0D14", text_color="#E2E8F0", font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_books_list.pack(fill="x", pady=(10, 0))

        return page

    # =========================================================================
    # PAGE: E-INK APP STORE / SIDELOAD HUB
    # =========================================================================
    def _create_page_apps(self):
        page = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")

        lbl_h = ctk.CTkLabel(page, text="E-Ink App Sideload Hub", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        lbl_h.pack(anchor="w", pady=(0, 4))
        lbl_sub = ctk.CTkLabel(page, text="Install local APKs or 1-click download curated essentials designed for Carta E-Ink.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", pady=(0, 16))

        c_local = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c_local.pack(fill="x", pady=8)

        l_inner = ctk.CTkFrame(c_local, fg_color="transparent")
        l_inner.pack(fill="x", padx=18, pady=16)

        ctk.CTkLabel(l_inner, text="Sideload Local APK File", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w")
        ctk.CTkLabel(l_inner, text="Select any .apk package from your computer to install it with replacement permissions (-r).", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=self.COLOR_TEXT_MUTED).pack(anchor="w", pady=(2, 10))

        ctk.CTkButton(l_inner, text="📦 Choose & Sideload APK...", height=36, corner_radius=8, fg_color=self.COLOR_BLUE, hover_color="#2563EB", command=self._action_sideload_local_apk).pack(anchor="w")

        c_cat = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c_cat.pack(fill="x", pady=8)

        cat_inner = ctk.CTkFrame(c_cat, fg_color="transparent")
        cat_inner.pack(fill="x", padx=18, pady=16)

        ctk.CTkLabel(cat_inner, text="Curated E-Ink Application Catalog", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w")
        ctk.CTkLabel(cat_inner, text="1-Click automatic download from official GitHub releases and installation over ADB.", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=self.COLOR_TEXT_MUTED).pack(anchor="w", pady=(2, 12))

        for app in CURATED_EINK_APPS:
            row = ctk.CTkFrame(cat_inner, corner_radius=8, fg_color="#181D29", border_width=1, border_color="#222A3B")
            row.pack(fill="x", pady=3)

            ibox = ctk.CTkFrame(row, fg_color="transparent")
            ibox.pack(side="left", padx=12, pady=8)

            ctk.CTkLabel(ibox, text=app["name"], font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#FFFFFF").pack(anchor="w")
            ctk.CTkLabel(ibox, text=app["desc"], font=ctk.CTkFont(family="Segoe UI", size=10), text_color=self.COLOR_TEXT_MUTED).pack(anchor="w")

            ctk.CTkButton(
                row,
                text="⬇️ Install",
                width=80,
                height=28,
                corner_radius=6,
                fg_color="#283042",
                hover_color=self.COLOR_BLUE,
                command=lambda a=app: self._action_install_curated_app(a)
            ).pack(side="right", padx=12, pady=8)

        return page

    # =========================================================================
    # PAGE: REMOTE E-INK & SCREENSHOT
    # =========================================================================
    def _create_page_remote(self):
        page = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")

        lbl_h = ctk.CTkLabel(page, text="E-Ink Remote Control & Screenshot Snip", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        lbl_h.pack(anchor="w", pady=(0, 4))
        lbl_sub = ctk.CTkLabel(page, text="Live screencap capture, clear ghosting broadcast, and virtual navigation keys.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", pady=(0, 16))

        split = ctk.CTkFrame(page, fg_color="transparent")
        split.pack(fill="x")

        # Left Column: Remote Controls
        left = ctk.CTkFrame(split, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        l_inner = ctk.CTkFrame(left, fg_color="transparent")
        l_inner.pack(fill="both", expand=True, padx=18, pady=16)

        ctk.CTkLabel(l_inner, text="E-Ink Refresh Controls", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w", pady=(0, 10))

        ctk.CTkButton(l_inner, text="🔄  Clear Ghosting (Full Screen Refresh)", height=36, corner_radius=8, fg_color=self.COLOR_BLUE, hover_color="#2563EB", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=self.ops.trigger_eink_refresh).pack(fill="x", pady=4)
        ctk.CTkButton(l_inner, text="⚡  Toggle A2 High-Speed Refresh Mode", height=36, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=self.ops.toggle_a2_speed_mode).pack(fill="x", pady=4)

        ctk.CTkLabel(l_inner, text="Virtual Navigation Keys", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w", pady=(18, 10))

        nav_grid = ctk.CTkFrame(l_inner, fg_color="transparent")
        nav_grid.pack(fill="x", pady=4)

        ctk.CTkButton(nav_grid, text="◀ Back", height=34, corner_radius=6, fg_color="#283042", command=lambda: self.ops.send_keyevent("KEYCODE_BACK")).grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(nav_grid, text="⌂ Home", height=34, corner_radius=6, fg_color="#283042", command=lambda: self.ops.send_keyevent("KEYCODE_HOME")).grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(nav_grid, text="☰ Overview", height=34, corner_radius=6, fg_color="#283042", command=lambda: self.ops.send_keyevent("KEYCODE_APP_SWITCH")).grid(row=0, column=2, padx=4, pady=4, sticky="ew")

        ctk.CTkButton(nav_grid, text="🔉 Vol -", height=34, corner_radius=6, fg_color="#283042", command=lambda: self.ops.send_keyevent("KEYCODE_VOLUME_DOWN")).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(nav_grid, text="🔊 Vol +", height=34, corner_radius=6, fg_color="#283042", command=lambda: self.ops.send_keyevent("KEYCODE_VOLUME_UP")).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(nav_grid, text="🔒 Lock/Sleep", height=34, corner_radius=6, fg_color=self.COLOR_RED, command=lambda: self.ops.send_keyevent("KEYCODE_POWER")).grid(row=1, column=2, padx=4, pady=4, sticky="ew")

        nav_grid.grid_columnconfigure(0, weight=1)
        nav_grid.grid_columnconfigure(1, weight=1)
        nav_grid.grid_columnconfigure(2, weight=1)

        # Right Column: Screenshot Snip
        right = ctk.CTkFrame(split, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER, width=280)
        right.pack(side="right", fill="both")

        r_inner = ctk.CTkFrame(right, fg_color="transparent")
        r_inner.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(r_inner, text="Live Screen Capture", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w")

        self.box_screenshot = ctk.CTkLabel(r_inner, text="No screenshot\ncaptured yet", width=220, height=290, fg_color="#0A0D14", corner_radius=8)
        self.box_screenshot.pack(pady=10)

        ctk.CTkButton(r_inner, text="📸  Capture Live Screenshot", height=34, corner_radius=8, fg_color=self.COLOR_BLUE, hover_color="#2563EB", command=self._action_capture_screenshot).pack(fill="x", pady=3)
        ctk.CTkButton(r_inner, text="📋  Copy to Windows Clipboard", height=34, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=self._action_copy_screenshot_clipboard).pack(fill="x", pady=3)
        ctk.CTkButton(r_inner, text="💾  Save as PNG File...", height=34, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=self._action_save_screenshot).pack(fill="x", pady=3)

        return page

    # =========================================================================
    # REUSED CORE PAGES (Root, Button, Media, Debloat, Settings, Logs)
    # =========================================================================
    def _create_page_root(self):
        page = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")

        lbl_h = ctk.CTkLabel(page, text="Rooting & Partition Management", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        lbl_h.pack(anchor="w", pady=(0, 4))
        lbl_sub = ctk.CTkLabel(page, text="Backup stock partitions, flash Magisk patched boot images, and enable hardware wake.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", pady=(0, 16))

        # Card 1: Stock Backup
        c1 = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c1.pack(fill="x", pady=8)

        ctk.CTkLabel(c1, text="1. Stock Partition Backup", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w", padx=18, pady=(16, 4))
        ctk.CTkLabel(
            c1,
            text="Dumps active boot (boot_a / boot_b), vbmeta, and optional dtbo/recovery into './backups/'.\nEssential before attempting any custom image flashes.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT_MUTED,
            justify="left"
        ).pack(anchor="w", padx=18, pady=(0, 12))

        b_row = ctk.CTkFrame(c1, fg_color="transparent")
        b_row.pack(anchor="w", padx=18, pady=(0, 16))

        ctk.CTkButton(b_row, text="📥  Backup Boot & VBMeta", height=36, corner_radius=8, fg_color=self.COLOR_BLUE, hover_color="#2563EB", command=self._action_backup_partitions).pack(side="left", padx=(0, 8))
        ctk.CTkButton(b_row, text="📥  Full Partition Dump (Boot, DTBO, Recovery, VBMeta)", height=36, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=self._action_backup_full_partitions).pack(side="left")

        # Card 2: Magisk Root & Fastboot
        c2 = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c2.pack(fill="x", pady=8)

        ctk.CTkLabel(c2, text="2. Magisk Root Installation & Fastboot Flashing", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w", padx=18, pady=(16, 4))
        ctk.CTkLabel(c2, text="1. Install Magisk APK -> 2. Patch your dumped stock_boot.img -> 3. Flash patched image via Fastboot.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED).pack(anchor="w", padx=18, pady=(0, 12))

        btn_row_m = ctk.CTkFrame(c2, fg_color="transparent")
        btn_row_m.pack(fill="x", padx=18, pady=(0, 16))

        ctk.CTkButton(btn_row_m, text="📦 1. Install Magisk APK", height=36, corner_radius=8, fg_color="#283042", command=self._action_install_magisk).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row_m, text="⚡ 2. Reboot to Fastboot", height=36, corner_radius=8, fg_color="#283042", command=lambda: self.ops.reboot_device("bootloader")).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row_m, text="🚀 3. Flash Patched Boot...", height=36, corner_radius=8, fg_color=self.COLOR_BLUE, command=self._action_flash_patched_boot).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row_m, text="🔄 Restore Stock Boot...", height=36, corner_radius=8, fg_color=self.COLOR_RED, command=self._action_restore_stock_boot).pack(side="left")

        # Card 3: Button Wake Magisk Module
        c3 = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c3.pack(fill="x", pady=8)

        ctk.CTkLabel(c3, text="3. Hardware Physical Button Wake (Magisk Module)", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w", padx=18, pady=(16, 4))
        ctk.CTkLabel(c3, text="Patches gpio-keys.kl so pressing the front center button or side keys instantly wakes the e-reader.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED).pack(anchor="w", padx=18, pady=(0, 12))

        ctk.CTkButton(c3, text="⚡ Install 'c69hd-wake' Magisk Module", height=38, corner_radius=8, fg_color=self.COLOR_GREEN, command=self._action_install_wake_module).pack(anchor="w", padx=18, pady=(0, 16))

        return page

    def _create_page_button(self):
        page = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")

        lbl_h = ctk.CTkLabel(page, text="Hardware Button Remapper", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        lbl_h.pack(anchor="w", pady=(0, 4))
        lbl_sub = ctk.CTkLabel(page, text="Customize the center physical button (KEYCODE_BACK) on your Onyx Boox C69HD.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", pady=(0, 16))

        info_banner = ctk.CTkFrame(page, corner_radius=10, fg_color="#1E2638", border_width=1, border_color="#2E3A54")
        info_banner.pack(fill="x", pady=6)
        ctk.CTkLabel(
            info_banner,
            text="💡 Why Remap? The C69HD has NO frontlight hardware. The factory default action\n"
                 "for holding the front button is toggling the backlight—which does nothing!\n"
                 "Remap it to Recent Apps (App Switcher) for instant multitasking.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#CBD5E1",
            justify="left"
        ).pack(anchor="w", padx=16, pady=12)

        c_config = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c_config.pack(fill="x", pady=10)

        ctk.CTkLabel(c_config, text="Configure Center Physical Button Actions", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w", padx=18, pady=(16, 12))

        ctk.CTkLabel(c_config, text="Long-Press (Hold) Action:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(anchor="w", padx=18, pady=(4, 4))
        self.opt_long_press = ctk.CTkOptionMenu(c_config, height=36, corner_radius=8, values=[f"{v} [{k}]" if k else f"{v} [Standard Back]" for k, v in BUTTON_ACTIONS.items()], width=550)
        self.opt_long_press.set("Recent Apps / App Switcher (Recommended for C69HD) [KEYCODE_APP_SWITCH]")
        self.opt_long_press.pack(anchor="w", padx=18, pady=(0, 12))

        ctk.CTkLabel(c_config, text="Short-Press (Single Tap) Action:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(anchor="w", padx=18, pady=(4, 4))
        self.opt_short_press = ctk.CTkOptionMenu(c_config, height=36, corner_radius=8, values=["Standard Back Key Event [Recommended] []", "Recent Apps / App Switcher [KEYCODE_APP_SWITCH]", "Full Screen E-Ink Refresh (Clears Ghosting) [fullRefreshScreen]", "Take Screenshot [screenshot]", "Return to Home Screen [back_to_home]"], width=550)
        self.opt_short_press.set("Standard Back Key Event [Recommended] []")
        self.opt_short_press.pack(anchor="w", padx=18, pady=(0, 16))

        btn_box = ctk.CTkFrame(c_config, fg_color="transparent")
        btn_box.pack(anchor="w", padx=18, pady=(0, 18))

        ctk.CTkButton(btn_box, text="💾  Apply Mapping to Device", height=38, corner_radius=8, fg_color=self.COLOR_BLUE, command=self._action_apply_button_remap).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_box, text="📖  Query Current Mapping", height=38, corner_radius=8, fg_color="#283042", command=self._action_read_button_remap).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_box, text="🔄  Reset to Factory Default", height=38, corner_radius=8, fg_color=self.COLOR_RED, command=self._action_reset_button_remap).pack(side="left")

        c_active = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c_active.pack(fill="x", pady=6)

        ctk.CTkLabel(c_active, text="Active Mapping in Device Settings.Global", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w", padx=18, pady=(14, 4))
        self.lbl_active_mapping = ctk.CTkLabel(c_active, text="Click 'Query Current Mapping' to check connected device...", font=ctk.CTkFont(family="Consolas", size=11), text_color="#38BDF8", justify="left")
        self.lbl_active_mapping.pack(anchor="w", padx=18, pady=(0, 14))

        return page

    def _create_page_media(self):
        page = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")

        lbl_h = ctk.CTkLabel(page, text="Screensaver & Boot Animation Studio", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        lbl_h.pack(anchor="w", pady=(0, 4))
        lbl_sub = ctk.CTkLabel(page, text="Customize sleep screens, wallpaper galleries, and Android boot animation for Carta 6\" E-Ink.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", pady=(0, 16))

        # Screensaver
        c1 = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c1.pack(fill="x", pady=8)

        ctk.CTkLabel(c1, text="1. Custom Screensaver & Sleep Screen", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w", padx=18, pady=(16, 4))

        split_ss = ctk.CTkFrame(c1, fg_color="transparent")
        split_ss.pack(fill="x", padx=18, pady=(0, 16))

        left_ctrl = ctk.CTkFrame(split_ss, fg_color="transparent")
        left_ctrl.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(left_ctrl, text="Automatically scaled/cropped to 758 × 1024 native Carta resolution with E-Ink contrast.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED).pack(anchor="w", pady=(0, 8))

        f_picker_row = ctk.CTkFrame(left_ctrl, fg_color="transparent")
        f_picker_row.pack(anchor="w", pady=4)

        ctk.CTkButton(f_picker_row, text="📁 Choose Image...", height=34, corner_radius=8, fg_color="#283042", command=self._action_choose_screensaver_file).pack(side="left", padx=(0, 10))
        self.lbl_chosen_image = ctk.CTkLabel(f_picker_row, text="No image selected", text_color=self.COLOR_TEXT_MUTED)
        self.lbl_chosen_image.pack(side="left")

        self.sw_grayscale = ctk.CTkSwitch(left_ctrl, text="Auto-convert to high-contrast E-Ink grayscale (LANCZOS 758x1024)", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.sw_grayscale.select()
        self.sw_grayscale.pack(anchor="w", pady=8)

        self.var_ss_target = ctk.StringVar(value="user")
        radio_row = ctk.CTkFrame(left_ctrl, fg_color="transparent")
        radio_row.pack(anchor="w", pady=2)
        ctk.CTkRadioButton(radio_row, text="User Gallery (/sdcard/Pictures/Screensaver)", variable=self.var_ss_target, value="user").pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(radio_row, text="System Standby (standby-1.png)", variable=self.var_ss_target, value="standby").pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(radio_row, text="Shutdown Screen", variable=self.var_ss_target, value="shutdown").pack(side="left")

        ss_btn_row = ctk.CTkFrame(left_ctrl, fg_color="transparent")
        ss_btn_row.pack(anchor="w", pady=(14, 4))

        ctk.CTkButton(ss_btn_row, text="🚀 Push Screensaver", height=36, corner_radius=8, fg_color=self.COLOR_BLUE, command=self._action_push_screensaver).pack(side="left", padx=(0, 8))
        ctk.CTkButton(ss_btn_row, text="📱 Open Wallpaper Settings", height=36, corner_radius=8, fg_color="#283042", command=self.ops.open_device_screensaver_settings).pack(side="left", padx=(0, 8))
        ctk.CTkButton(ss_btn_row, text="💤 Test Sleep", height=36, corner_radius=8, fg_color="#283042", command=lambda: self.ops.reboot_device("sleep")).pack(side="left")

        right_preview = ctk.CTkFrame(split_ss, corner_radius=10, fg_color="#0F121A", border_width=1, border_color="#252C3D", width=140, height=190)
        right_preview.pack(side="right", padx=(16, 0))
        right_preview.pack_propagate(False)

        self.lbl_image_preview = ctk.CTkLabel(right_preview, text="Preview\n758x1024", text_color=self.COLOR_TEXT_MUTED)
        self.lbl_image_preview.pack(expand=True, fill="both")

        # Boot Animation
        c2 = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c2.pack(fill="x", pady=8)

        ctk.CTkLabel(c2, text="2. Custom Boot Animation", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w", padx=18, pady=(16, 4))
        ctk.CTkLabel(c2, text="Install custom bootanimation.zip systemlessly via Magisk media overlay.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED).pack(anchor="w", padx=18, pady=(0, 10))

        b_picker_row = ctk.CTkFrame(c2, fg_color="transparent")
        b_picker_row.pack(anchor="w", padx=18, pady=4)

        ctk.CTkButton(b_picker_row, text="📁 Select bootanimation.zip...", height=34, corner_radius=8, fg_color="#283042", command=self._action_choose_bootanim_zip).pack(side="left", padx=(0, 8))
        ctk.CTkButton(b_picker_row, text="✨ Generate E-Ink Animation...", height=34, corner_radius=8, fg_color=self.COLOR_GREEN, hover_color="#059669", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), command=self._action_generate_eink_bootanim).pack(side="left", padx=(0, 8))
        ctk.CTkButton(b_picker_row, text="🖼️ Create from Folder of Frames...", height=34, corner_radius=8, fg_color="#283042", command=self._action_create_bootanim_from_folder).pack(side="left", padx=(0, 10))
        self.lbl_chosen_bootanim = ctk.CTkLabel(b_picker_row, text="No animation selected", text_color=self.COLOR_TEXT_MUTED)
        self.lbl_chosen_bootanim.pack(side="left")

        b_btn_row = ctk.CTkFrame(c2, fg_color="transparent")
        b_btn_row.pack(anchor="w", padx=18, pady=(12, 18))

        ctk.CTkButton(b_btn_row, text="⚡ Install Animation (Magisk)", height=36, corner_radius=8, fg_color=self.COLOR_BLUE, command=self._action_install_bootanim).pack(side="left", padx=(0, 8))
        ctk.CTkButton(b_btn_row, text="▶️ Live Preview on Device Screen", height=36, corner_radius=8, fg_color=self.COLOR_GREEN, command=lambda: threading.Thread(target=self.ops.preview_bootanimation_on_device, daemon=True).start()).pack(side="left", padx=(0, 8))
        ctk.CTkButton(b_btn_row, text="🔄 Restore Stock Boot Animation", height=36, corner_radius=8, fg_color=self.COLOR_RED, command=self._action_restore_stock_bootanim).pack(side="left")

        return page

    def _create_page_debloat(self):
        page = ctk.CTkFrame(self.content_container, fg_color="transparent")
        page.grid_rowconfigure(2, weight=1)
        page.grid_columnconfigure(0, weight=1)

        lbl_h = ctk.CTkLabel(page, text="Reversible System Debloater", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        lbl_h.grid(row=0, column=0, sticky="w", pady=(0, 4))
        lbl_sub = ctk.CTkLabel(page, text="Safely disable unused cellular daemons, SVA voice listener, and Google services without root risk.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED)
        lbl_sub.grid(row=1, column=0, sticky="w", pady=(0, 14))

        ctrl_bar = ctk.CTkFrame(page, corner_radius=10, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        ctrl_bar.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        bar_inner = ctk.CTkFrame(ctrl_bar, fg_color="transparent")
        bar_inner.pack(fill="x", padx=14, pady=10)

        ctk.CTkButton(bar_inner, text="🛡️ 1-Click Safe Debloat", height=34, corner_radius=8, fg_color=self.COLOR_BLUE, command=self._action_safe_debloat).pack(side="left", padx=(0, 8))
        ctk.CTkButton(bar_inner, text="🔄 Re-enable All", height=34, corner_radius=8, fg_color="#283042", command=self._action_enable_all_debloated).pack(side="left", padx=(0, 8))
        ctk.CTkButton(bar_inner, text="↻ Refresh List", height=34, corner_radius=8, fg_color="#283042", command=self._action_refresh_debloat_list).pack(side="left", padx=(0, 14))

        self.entry_filter = ctk.CTkEntry(bar_inner, placeholder_text="🔍 Filter packages...", width=220, height=34, corner_radius=8)
        self.entry_filter.pack(side="right")
        self.entry_filter.bind("<KeyRelease>", lambda e: self._filter_debloat_items())

        self.scroll_debloat = ctk.CTkScrollableFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        self.scroll_debloat.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        page.grid_rowconfigure(3, weight=1)

        self.pkg_widgets = {}
        self.category_headers = {}
        self._populate_debloat_items()

        custom_box = ctk.CTkFrame(page, corner_radius=10, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        custom_box.grid(row=4, column=0, sticky="ew")

        c_inner = ctk.CTkFrame(custom_box, fg_color="transparent")
        c_inner.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(c_inner, text="Manual Package Control:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(side="left", padx=(0, 8))
        self.entry_custom_pkg = ctk.CTkEntry(c_inner, placeholder_text="e.g. com.onyx.mail", width=280, height=34, corner_radius=8)
        self.entry_custom_pkg.pack(side="left", padx=(0, 8))

        ctk.CTkButton(c_inner, text="Disable Package", height=34, corner_radius=8, fg_color=self.COLOR_RED, command=self._action_custom_disable).pack(side="left", padx=(0, 6))
        ctk.CTkButton(c_inner, text="Enable Package", height=34, corner_radius=8, fg_color="#283042", command=self._action_custom_enable).pack(side="left")

        return page

    def _populate_debloat_items(self):
        for widget in self.scroll_debloat.winfo_children():
            widget.destroy()

        self.pkg_widgets.clear()
        self.category_headers.clear()

        for cat in DEBLOAT_CATALOG:
            cat_title = cat["category"]
            lbl_cat = ctk.CTkLabel(self.scroll_debloat, text=cat_title, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=self.COLOR_CYAN)
            lbl_cat.pack(anchor="w", padx=10, pady=(14, 6))
            self.category_headers[cat_title] = {
                "label": lbl_cat,
                "packages": []
            }

            for pkg, desc in cat["packages"]:
                row = ctk.CTkFrame(self.scroll_debloat, corner_radius=8, fg_color="#1A1F2C", border_width=1, border_color="#262D3D")
                row.pack(fill="x", pady=3)

                info_box = ctk.CTkFrame(row, fg_color="transparent")
                info_box.pack(side="left", padx=12, pady=8)

                lbl_name = ctk.CTkLabel(info_box, text=pkg, font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color="#FFFFFF")
                lbl_name.pack(anchor="w")

                lbl_desc = ctk.CTkLabel(info_box, text=desc, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=self.COLOR_TEXT_MUTED)
                lbl_desc.pack(anchor="w")

                btn_toggle = ctk.CTkButton(row, text="Querying...", width=90, height=30, corner_radius=6, fg_color="#283042")
                btn_toggle.pack(side="right", padx=12, pady=8)

                self.pkg_widgets[pkg] = {
                    "row": row,
                    "button": btn_toggle,
                    "desc": desc,
                    "category": cat_title,
                    "disabled": False
                }
                self.category_headers[cat_title]["packages"].append(pkg)

    def _filter_debloat_items(self):
        query = self.entry_filter.get().strip().lower()
        for cat_title, cat_data in self.category_headers.items():
            cat_has_matches = False
            for pkg in cat_data["packages"]:
                item = self.pkg_widgets[pkg]
                match = (query in pkg.lower()) or (query in item["desc"].lower())
                if match or not query:
                    item["row"].pack(fill="x", pady=3)
                    cat_has_matches = True
                else:
                    item["row"].pack_forget()

            if cat_has_matches:
                cat_data["label"].pack(anchor="w", padx=10, pady=(14, 6))
            else:
                cat_data["label"].pack_forget()

    def _create_page_settings(self):
        page = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")

        lbl_h = ctk.CTkLabel(page, text="Device Settings & Power Tweaks", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        lbl_h.pack(anchor="w", pady=(0, 4))
        lbl_sub = ctk.CTkLabel(page, text="Fix the factory infinite sleep bug, disable telemetry drain, and adjust font clarity.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", pady=(0, 16))

        c_to = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c_to.pack(fill="x", pady=8)

        ctk.CTkLabel(c_to, text="Screen Timeout (Fix 24.8-Day Sleep Bug)", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w", padx=18, pady=(16, 4))
        ctk.CTkLabel(c_to, text="⚠️ Factory Bug: Timeout often defaults to 2147483647 ms (24.8 days) causing battery drain!\nSet to 5 Minutes for optimal reading.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_AMBER, justify="left").pack(anchor="w", padx=18, pady=(0, 12))

        to_row = ctk.CTkFrame(c_to, fg_color="transparent")
        to_row.pack(anchor="w", padx=18, pady=(0, 16))

        self.opt_timeout = ctk.CTkOptionMenu(to_row, height=36, corner_radius=8, values=["1 Minute (60000 ms)", "2 Minutes (120000 ms)", "5 Minutes [Recommended] (300000 ms)", "10 Minutes (600000 ms)", "30 Minutes (1800000 ms)", "Never Sleep [Buggy default] (2147483647 ms)"], width=320)
        self.opt_timeout.set("5 Minutes [Recommended] (300000 ms)")
        self.opt_timeout.pack(side="left", padx=(0, 10))

        ctk.CTkButton(to_row, text="⚡ Fix to 5 Minutes Now", height=36, corner_radius=8, fg_color=self.COLOR_GREEN, command=self._action_fix_timeout_preset).pack(side="left")

        c_rad = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c_rad.pack(fill="x", pady=8)

        ctk.CTkLabel(c_rad, text="Battery & Privacy Radios", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w", padx=18, pady=(16, 8))

        self.sw_telemetry = ctk.CTkSwitch(c_rad, text="Disable background crash & error telemetry (send_action_app_error = 0)", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.sw_telemetry.pack(anchor="w", padx=18, pady=4)

        self.sw_ble = ctk.CTkSwitch(c_rad, text="Disable background Bluetooth LE scanning (ble_scan_always_enabled = 0)", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.sw_ble.pack(anchor="w", padx=18, pady=4)

        self.sw_wifi = ctk.CTkSwitch(c_rad, text="Disable background Wi-Fi scanning (wifi_scan_always_enabled = 0)", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.sw_wifi.pack(anchor="w", padx=18, pady=4)

        self.sw_location = ctk.CTkSwitch(c_rad, text="Turn off Location services on e-reader (location_mode = 0)", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.sw_location.pack(anchor="w", padx=18, pady=(4, 16))

        c_disp = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c_disp.pack(fill="x", pady=8)

        ctk.CTkLabel(c_disp, text="Display & Reading Clarity", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w", padx=18, pady=(16, 12))

        disp_grid = ctk.CTkFrame(c_disp, fg_color="transparent")
        disp_grid.pack(anchor="w", padx=18, pady=(0, 16))

        ctk.CTkLabel(disp_grid, text="Font Scale:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).grid(row=0, column=0, sticky="w", pady=6)
        self.opt_font = ctk.CTkOptionMenu(disp_grid, height=32, corner_radius=8, values=["0.85 (Small)", "1.00 (Standard)", "1.05 (Optimized)", "1.10 (Large)", "1.15 (Extra Large)"], width=220)
        self.opt_font.set("1.05 (Optimized)")
        self.opt_font.grid(row=0, column=1, padx=12, pady=6)

        ctk.CTkLabel(disp_grid, text="Display DPI:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).grid(row=1, column=0, sticky="w", pady=6)
        self.opt_dpi = ctk.CTkOptionMenu(disp_grid, height=32, corner_radius=8, values=["Reset to 212 DPI (Default)", "200 DPI", "225 DPI", "240 DPI"], width=220)
        self.opt_dpi.set("Reset to 212 DPI (Default)")
        self.opt_dpi.grid(row=1, column=1, padx=12, pady=6)

        self.sw_contrast = ctk.CTkSwitch(disp_grid, text="High Contrast Text (high_text_contrast_enabled)", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.sw_contrast.grid(row=2, column=0, columnspan=2, sticky="w", pady=8)

        set_btn_row = ctk.CTkFrame(page, fg_color="transparent")
        set_btn_row.pack(anchor="w", pady=12)

        ctk.CTkButton(set_btn_row, text="💾 Apply System Settings", height=38, corner_radius=8, fg_color=self.COLOR_BLUE, command=self._action_apply_settings).pack(side="left", padx=(0, 8))
        ctk.CTkButton(set_btn_row, text="📖 Query Device Settings", height=38, corner_radius=8, fg_color="#283042", command=self._action_query_settings).pack(side="left")

        return page

    def _create_page_logs(self):
        page = ctk.CTkFrame(self.content_container, fg_color="transparent")
        page.grid_rowconfigure(2, weight=1)
        page.grid_columnconfigure(0, weight=1)

        lbl_h = ctk.CTkLabel(page, text="Hardware Platform & Console Logs", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        lbl_h.grid(row=0, column=0, sticky="w", pady=(0, 4))
        lbl_sub = ctk.CTkLabel(page, text="Live hardware diagnostics and ADB execution telemetry.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED)
        lbl_sub.grid(row=1, column=0, sticky="w", pady=(0, 14))

        top_split = ctk.CTkFrame(page, fg_color="transparent")
        top_split.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        top_split.grid_columnconfigure(0, weight=2)
        top_split.grid_columnconfigure(1, weight=1)

        specs_card = ctk.CTkFrame(top_split, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        specs_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(specs_card, text="Hardware & Platform Specifications", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w", padx=16, pady=(14, 6))
        self.lbl_specs = ctk.CTkLabel(specs_card, text="Probing device specs...", font=ctk.CTkFont(family="Consolas", size=11), text_color="#E2E8F0", justify="left")
        self.lbl_specs.pack(anchor="w", padx=16, pady=(0, 14))

        pwr_card = ctk.CTkFrame(top_split, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        pwr_card.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(pwr_card, text="Device Power Controls", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=self.COLOR_CYAN).pack(anchor="w", padx=16, pady=(14, 8))
        ctk.CTkButton(pwr_card, text="⚡ Reboot System", height=32, corner_radius=6, fg_color="#283042", command=lambda: self.ops.reboot_device("system")).pack(fill="x", padx=16, pady=2)
        ctk.CTkButton(pwr_card, text="⚡ Reboot Recovery", height=32, corner_radius=6, fg_color="#283042", command=lambda: self.ops.reboot_device("recovery")).pack(fill="x", padx=16, pady=2)
        ctk.CTkButton(pwr_card, text="⚡ Reboot Fastboot", height=32, corner_radius=6, fg_color="#283042", command=lambda: self.ops.reboot_device("bootloader")).pack(fill="x", padx=16, pady=2)
        ctk.CTkButton(pwr_card, text="🔄 Restart SystemUI", height=32, corner_radius=6, fg_color="#283042", command=lambda: self.ops.reboot_device("systemui")).pack(fill="x", padx=16, pady=(2, 14))

        # Android SDK Platform-Tools (ADB & Fastboot) Environment Card
        env_card = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        env_card.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        env_head = ctk.CTkFrame(env_card, fg_color="transparent")
        env_head.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(env_head, text="Android SDK Platform-Tools (ADB & Fastboot) Environment", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=self.COLOR_CYAN).pack(side="left")

        self.lbl_adb_env = ctk.CTkLabel(env_card, text="Detecting platform-tools environment...", font=ctk.CTkFont(family="Consolas", size=11), text_color="#E2E8F0", justify="left")
        self.lbl_adb_env.pack(anchor="w", padx=16, pady=(0, 10))

        env_btn_box = ctk.CTkFrame(env_card, fg_color="transparent")
        env_btn_box.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkButton(
            env_btn_box,
            text="📥 Auto-Install / Update Platform-Tools",
            height=30,
            corner_radius=6,
            fg_color=self.COLOR_GREEN,
            hover_color="#059669",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._action_install_adb
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            env_btn_box,
            text="🌐 Register ADB in Windows PATH",
            height=30,
            corner_radius=6,
            fg_color="#283042",
            hover_color="#3B4660",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self._action_register_adb_path
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            env_btn_box,
            text="📂 Open Tools Folder",
            height=30,
            corner_radius=6,
            fg_color="#1E293B",
            hover_color="#334155",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self._action_open_tools_folder
        ).pack(side="left")

        log_card = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        log_card.grid(row=4, column=0, sticky="nsew")
        page.grid_rowconfigure(4, weight=1)

        log_head = ctk.CTkFrame(log_card, fg_color="transparent")
        log_head.pack(fill="x", padx=16, pady=(10, 4))

        ctk.CTkLabel(log_head, text="Real-time Execution Console", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=self.COLOR_CYAN).pack(side="left")
        ctk.CTkButton(log_head, text="Clear Console", width=90, height=26, corner_radius=6, fg_color="#283042", command=lambda: self.txt_log.delete("1.0", "end")).pack(side="right")

        self.txt_log = ctk.CTkTextbox(log_card, corner_radius=8, fg_color="#06080F", text_color=self.COLOR_CYAN, font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_log.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        return page

    # =========================================================================
    # LOGGING & PROBING LOGIC
    # =========================================================================
    def append_log(self, text):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        msg = f"[{now}] {text}\n"
        self.dispatch(self._insert_log_text, msg)

    def _insert_log_text(self, msg):
        try:
            self.txt_log.insert("end", msg)
            self.txt_log.see("end")
        except Exception:
            pass

    def refresh_device_status_async(self):
        self.lbl_status_badge.configure(text="PROBING...", fg_color="#283042", text_color=self.COLOR_CYAN)
        threading.Thread(target=self._worker_probe_device, daemon=True).start()

    def _worker_probe_device(self):
        info = self.adb.get_connected_device_info()
        self.dispatch(self._update_ui_device_status, info)

    def _update_ui_device_status(self, info):
        self.device_info = info

        # Check platform tools availability
        if not self.adb.is_available():
            self.lbl_status_badge.configure(text="ADB MISSING", fg_color=self.COLOR_AMBER, text_color="#000000")
            self.lbl_device_title.configure(text="ADB Not Detected")
            self.lbl_device_details.configure(text="Click below to auto-install")
            self.lbl_specs.configure(text="ADB is missing. Please click 'Auto-Install ADB & Fastboot' below.")
            try:
                self.btn_sidebar_install_adb.pack(fill="x", padx=12, pady=(0, 6), before=self.btn_wireless)
            except Exception:
                self.btn_sidebar_install_adb.pack(fill="x", padx=12, pady=(0, 6))
        else:
            try:
                self.btn_sidebar_install_adb.pack_forget()
            except Exception:
                pass

        if hasattr(self, "lbl_adb_env"):
            tool_info = self.adb.get_tool_info()
            if tool_info["installed"]:
                self.lbl_adb_env.configure(
                    text=f"Status   : Installed & Verified (Version: {tool_info['version']})\n"
                         f"ADB      : {tool_info['adb_path']}\n"
                         f"Fastboot : {tool_info['fastboot_path']}"
                )
            else:
                self.lbl_adb_env.configure(
                    text="Status   : Missing ADB & Fastboot executables\n"
                         "Action   : Click 'Auto-Install Platform-Tools' below to auto-download official Google binaries."
                )

        if not self.adb.is_available():
            return

        if info["connected"]:
            if info["mode"] == "adb":
                root_status = "Rooted" if info["rooted"] else "Unrooted"
                self.lbl_status_badge.configure(
                    text=f"CONNECTED ({root_status.upper()})",
                    fg_color="#064E3B" if info["rooted"] else "#075985",
                    text_color="#FFFFFF"
                )
                self.lbl_device_title.configure(text=f"{info['model']} ({info['manufacturer']})")
                self.lbl_device_details.configure(text=f"Slot: {info['boot_slot']} • Bat: {info['battery_level']}")
            elif info["mode"] == "fastboot":
                self.lbl_status_badge.configure(text="FASTBOOT MODE", fg_color="#78350F", text_color="#FFFFFF")
                self.lbl_device_title.configure(text="Fastboot Device")
                self.lbl_device_details.configure(text=f"Serial: {info['serial']}")

            if info.get("is_wireless"):
                self.btn_wireless.configure(text="🔌 Switch to USB Cable", fg_color=self.COLOR_AMBER)
            else:
                ip = info.get("ip_address")
                label = f"📶 Connect Wi-Fi ({ip})" if ip else "📶 Connect via Wi-Fi"
                self.btn_wireless.configure(text=label, fg_color="#1E293B")

            specs_text = (
                f"Model            : {info['model']} ({info['device']})\n"
                f"Manufacturer     : {info['manufacturer']}\n"
                f"Platform / Board : Qualcomm Snapdragon 662 (bengal)\n"
                f"Display Build ID : {info['display_id']}\n"
                f"Android Version  : Android {info['android_version']} (API 30)\n"
                f"Active Boot Slot : {info['boot_slot']}\n"
                f"Bootloader State : {'Unlocked' if info['unlocked'] else 'Locked'}\n"
                f"Root (Magisk/su) : {'Active (UID 0)' if info['rooted'] else 'No su binary detected'}\n"
                f"Battery Status   : {info['battery_level']} (Charging: {info['battery_charging']})\n"
                f"Internal Storage : {info.get('storage_avail', 'N/A')} free of {info.get('storage_total', 'N/A')}\n"
            )
            self.lbl_specs.configure(text=specs_text)
            self._action_refresh_debloat_list_async()
            self._action_query_settings_silent()
        else:
            self.lbl_status_badge.configure(text="DISCONNECTED", fg_color="#7F1D1D", text_color="#FFFFFF")
            self.lbl_device_title.configure(text="No Device Detected")
            self.lbl_device_details.configure(text="Connect via USB or Wi-Fi")
            self.lbl_specs.configure(text="No device connected.")

    # =========================================================================
    # ACTIONS: WIRELESS ADB
    # =========================================================================
    def _action_toggle_wireless_adb(self):
        info = self.adb.get_connected_device_info()
        def _run():
            if info.get("is_wireless"):
                self.adb.disconnect_wireless_adb()
                messagebox.showinfo("Wireless ADB", "Disconnected wireless ADB. Switched back to USB mode.")
            else:
                ok, msg = self.adb.enable_wireless_adb()
                if ok:
                    messagebox.showinfo("Wireless ADB Connected", msg + "\nYou can now disconnect the USB cable!")
                else:
                    messagebox.showerror("Wireless ADB Failed", msg)
            self.refresh_device_status_async()
        threading.Thread(target=_run, daemon=True).start()

    # =========================================================================
    # ACTIONS: PRESETS
    # =========================================================================
    def _action_apply_preset_battery(self):
        def _run():
            ok, msg = self.ops.apply_profile_extreme_battery()
            self.refresh_device_status_async()
            messagebox.showinfo("Battery Profile Applied", msg)
        threading.Thread(target=_run, daemon=True).start()

    def _action_apply_preset_ram(self):
        def _run():
            ok, msg = self.ops.apply_profile_free_ram()
            self.refresh_device_status_async()
            messagebox.showinfo("RAM Booster Applied", msg)
        threading.Thread(target=_run, daemon=True).start()

    def _action_apply_preset_reading(self):
        def _run():
            ok, msg = self.ops.apply_profile_distraction_free()
            self.refresh_device_status_async()
            messagebox.showinfo("Reading Profile Applied", msg)
        threading.Thread(target=_run, daemon=True).start()

    def _action_apply_preset_restore(self):
        if not messagebox.askyesno("Confirm Revert", "Revert all settings and re-enable all debloated packages to stock?"):
            return
        def _run():
            ok, msg = self.ops.apply_profile_factory_restore()
            self.refresh_device_status_async()
            messagebox.showinfo("Stock Restored", msg)
        threading.Thread(target=_run, daemon=True).start()

    # =========================================================================
    # ACTIONS: BOOKS
    # =========================================================================
    def _action_choose_books(self):
        files = filedialog.askopenfilenames(
            title="Choose Books / Comics to Transfer",
            filetypes=[("E-Books & Comics", "*.epub;*.pdf;*.mobi;*.azw3;*.cbz;*.cbr;*.txt"), ("All Files", "*.*")]
        )
        if not files:
            return
        self._selected_books = list(files)
        self.lbl_books_count.configure(text=f"{len(files)} files selected")
        self.txt_books_list.delete("1.0", "end")
        for f in files:
            self.txt_books_list.insert("end", f"• {os.path.basename(f)} ({os.path.getsize(f) // 1024} KB)\n")

    def _action_push_books(self):
        if not self._selected_books:
            messagebox.showwarning("No Books", "Please select book files first.")
            return

        dest = self.opt_book_dest.get()
        def _run():
            ok, msg = self.ops.push_books_batch(self._selected_books, target_dir=dest)
            if ok:
                messagebox.showinfo("Books Transferred", msg)
            else:
                messagebox.showerror("Transfer Failed", msg)
        threading.Thread(target=_run, daemon=True).start()

    # =========================================================================
    # ACTIONS: APPS & SIDELOAD
    # =========================================================================
    def _action_sideload_local_apk(self):
        apk = filedialog.askopenfilename(title="Select APK to Sideload", filetypes=[("APK Package", "*.apk")])
        if not apk:
            return
        def _run():
            ok, msg = self.ops.sideload_apk(apk)
            if ok:
                messagebox.showinfo("Install Succeeded", msg)
            else:
                messagebox.showerror("Install Failed", msg)
        threading.Thread(target=_run, daemon=True).start()

    def _action_install_curated_app(self, app_info):
        def _run():
            ok, msg = self.ops.download_and_install_curated_app(app_info)
            if ok:
                messagebox.showinfo("App Installed", msg)
            else:
                messagebox.showerror("App Error", msg)
        threading.Thread(target=_run, daemon=True).start()

    # =========================================================================
    # ACTIONS: SCREENSHOT & REMOTE
    # =========================================================================
    def _action_capture_screenshot(self):
        def _run():
            img, err = self.adb.capture_screenshot()
            if err or not img:
                messagebox.showerror("Screenshot Error", f"Failed to capture screenshot:\n{err}")
                return
            self._last_pil_screenshot = img
            thumb = img.copy()
            thumb.thumbnail((200, 270), Image.Resampling.LANCZOS)
            self._ctk_screenshot_image = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=thumb.size)
            self.dispatch(lambda: self.box_screenshot.configure(image=self._ctk_screenshot_image, text=""))
        threading.Thread(target=_run, daemon=True).start()

    def _action_copy_screenshot_clipboard(self):
        if not self._last_pil_screenshot:
            messagebox.showwarning("No Screenshot", "Capture a screenshot first.")
            return
        ok, msg = copy_pil_image_to_clipboard(self._last_pil_screenshot)
        if ok:
            messagebox.showinfo("Copied to Clipboard", "Screenshot copied to Windows clipboard! You can now paste (Ctrl+V) it anywhere.")
        else:
            messagebox.showerror("Clipboard Error", f"Failed to copy to clipboard:\n{msg}")

    def _action_save_screenshot(self):
        if not self._last_pil_screenshot:
            messagebox.showwarning("No Screenshot", "Capture a screenshot first.")
            return
        f = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image", "*.png")])
        if f:
            self._last_pil_screenshot.save(f)
            messagebox.showinfo("Saved", f"Screenshot saved to {f}")

    # =========================================================================
    # ACTIONS: SCREENSAVER & BOOT MEDIA
    # =========================================================================
    def _action_choose_screensaver_file(self):
        f = filedialog.askopenfilename(
            title="Choose Screensaver Image",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"), ("All Files", "*.*")]
        )
        if not f:
            return
        self._selected_image_path = f
        self.lbl_chosen_image.configure(text=os.path.basename(f))

        if HAS_PILLOW:
            try:
                pil_img = Image.open(f)
                pil_thumb = pil_img.copy()
                pil_thumb.thumbnail((120, 162), Image.Resampling.LANCZOS)
                if self.sw_grayscale.get():
                    pil_thumb = pil_thumb.convert("L")
                self._ctk_preview_image = ctk.CTkImage(light_image=pil_thumb, dark_image=pil_thumb, size=pil_thumb.size)
                self.lbl_image_preview.configure(image=self._ctk_preview_image, text="")
            except Exception:
                self.lbl_image_preview.configure(image=None, text="Preview Error")

    def _action_push_screensaver(self):
        if not self._selected_image_path:
            messagebox.showwarning("No Image", "Please select an image file first.")
            return

        target = self.var_ss_target.get()
        custom_name = f"c69hd_ss_{int(datetime.datetime.now().timestamp())}"

        def _run():
            ok, msg = self.ops.push_screensaver_image(self._selected_image_path, target=target, custom_name=custom_name)
            if ok:
                messagebox.showinfo("Screensaver Updated", msg)
            else:
                messagebox.showerror("Error", msg)
        threading.Thread(target=_run, daemon=True).start()

    def _action_choose_bootanim_zip(self):
        f = filedialog.askopenfilename(
            title="Select bootanimation.zip",
            filetypes=[("Zip Archives", "*.zip"), ("All Files", "*.*")]
        )
        if f:
            self._selected_bootanim_path = f
            self.lbl_chosen_bootanim.configure(text=os.path.basename(f))

    def _action_generate_eink_bootanim(self):
        try:
            from scripts.generate_bootanimation import generate_bootanimation_package
            out_zip = os.path.join(os.getcwd(), "backups", "custom_bootanimation.zip")
            os.makedirs(os.path.dirname(out_zip), exist_ok=True)
            ok = generate_bootanimation_package(out_zip, theme="dark", fps=4)
            if ok:
                self._selected_bootanim_path = out_zip
                self.lbl_chosen_bootanim.configure(text=f"Built: {os.path.basename(out_zip)} (E-Ink Dark Edition)")
                self.append_log(f"Generated custom E-Ink boot animation: {out_zip}")
                if messagebox.askyesno("Boot Animation Built", f"Successfully generated custom E-Ink boot animation (758x1024 @ 4 FPS, uncompressed)!\nPath: {out_zip}\n\nWould you like to preview it live on the physical device screen now?"):
                    threading.Thread(target=self.ops.preview_bootanimation_on_device, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Generation Error", f"Failed to generate boot animation: {e}")

    def _action_create_bootanim_from_folder(self):
        d = filedialog.askdirectory(title="Select Folder Containing PNG Frames")
        if not d:
            return
        files = [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.lower().endswith((".png", ".jpg"))]
        if not files:
            messagebox.showwarning("No Frames", "No PNG or JPG images found in the selected folder.")
            return

        out_zip = os.path.join(os.getcwd(), "backups", "custom_bootanimation.zip")
        self.ops.create_bootanimation_zip(files, out_zip, fps=1)
        self._selected_bootanim_path = out_zip
        self.lbl_chosen_bootanim.configure(text=f"Built: {os.path.basename(out_zip)} ({len(files)} frames)")
        messagebox.showinfo("Boot Animation Built", f"Successfully created uncompressed bootanimation.zip with {len(files)} frames!\nPath: {out_zip}")

    def _action_install_bootanim(self):
        if not self._selected_bootanim_path:
            messagebox.showwarning("No Animation", "Please select or generate a bootanimation.zip first.")
            return
        def _run():
            ok, msg = self.ops.install_bootanimation_zip(self._selected_bootanim_path)
            if ok:
                messagebox.showinfo("Boot Animation Installed", msg)
            else:
                messagebox.showerror("Install Error", msg)
        threading.Thread(target=_run, daemon=True).start()

    def _action_restore_stock_bootanim(self):
        def _run():
            self.ops.restore_stock_bootanimation()
            messagebox.showinfo("Restored", "Stock boot animation restored.")
        threading.Thread(target=_run, daemon=True).start()

    # =========================================================================
    # ACTIONS: ROOT & BUTTON REMAP
    # =========================================================================
    def _action_backup_partitions(self):
        def _run():
            info = self.adb.get_connected_device_info()
            slot = info.get("boot_slot", "_a")
            ok, msg = self.ops.backup_stock_partitions(slot=slot, partition_list=[f"boot{slot}", f"vbmeta{slot}"])
            if ok:
                messagebox.showinfo("Backup Success", msg)
            else:
                messagebox.showerror("Backup Failed", msg)
        threading.Thread(target=_run, daemon=True).start()

    def _action_backup_full_partitions(self):
        def _run():
            info = self.adb.get_connected_device_info()
            slot = info.get("boot_slot", "_a")
            full_list = [f"boot{slot}", f"dtbo{slot}", f"recovery{slot}", f"vbmeta{slot}", f"vbmeta_system{slot}", "persist"]
            ok, msg = self.ops.backup_stock_partitions(slot=slot, partition_list=full_list)
            if ok:
                messagebox.showinfo("Full Backup Success", msg)
            else:
                messagebox.showerror("Full Backup Failed", msg)
        threading.Thread(target=_run, daemon=True).start()

    def _action_install_magisk(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        assets_apk = os.path.join(base_dir, "assets", "magisk.apk")
        if not os.path.exists(assets_apk):
            assets_apk = filedialog.askopenfilename(title="Select Magisk APK", filetypes=[("APK Files", "*.apk")])
            if not assets_apk:
                return

        def _run():
            ok, msg = self.ops.install_magisk_apk(assets_apk)
            if ok:
                messagebox.showinfo("Magisk Installed", msg)
            else:
                messagebox.showerror("Install Error", msg)
        threading.Thread(target=_run, daemon=True).start()

    def _action_flash_patched_boot(self):
        img_path = filedialog.askopenfilename(title="Select Magisk-Patched Boot Image (.img)", filetypes=[("Disk Image", "*.img")])
        if not img_path:
            return

        info = self.adb.get_connected_device_info()
        slot = info.get("boot_slot", "_a")

        if not messagebox.askyesno("Confirm Boot Flash", f"Are you sure you want to flash:\n{img_path}\nto slot {slot} via Fastboot?"):
            return

        def _run():
            ok, msg = self.ops.flash_boot_image_fastboot(img_path, slot=slot)
            if ok:
                messagebox.showinfo("Flash Success", msg)
            else:
                messagebox.showerror("Flash Failed", msg)
            self.refresh_device_status_async()
        threading.Thread(target=_run, daemon=True).start()

    def _action_restore_stock_boot(self):
        img_path = filedialog.askopenfilename(title="Select Stock Boot Image (.img)", filetypes=[("Disk Image", "*.img")])
        if not img_path:
            return

        info = self.adb.get_connected_device_info()
        slot = info.get("boot_slot", "_a")

        def _run():
            ok, msg = self.ops.flash_boot_image_fastboot(img_path, slot=slot)
            if ok:
                messagebox.showinfo("Stock Restored", msg)
            else:
                messagebox.showerror("Restore Failed", msg)
            self.refresh_device_status_async()
        threading.Thread(target=_run, daemon=True).start()

    def _action_install_wake_module(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        assets_zip = os.path.join(base_dir, "assets", "c69hd-wake.zip")
        if not os.path.exists(assets_zip):
            assets_zip = filedialog.askopenfilename(title="Select c69hd-wake.zip Module", filetypes=[("Zip Archive", "*.zip")])
            if not assets_zip:
                return

        def _run():
            ok, msg = self.ops.install_magisk_wake_module(assets_zip)
            if ok:
                messagebox.showinfo("Module Installed", msg)
            else:
                messagebox.showerror("Module Error", msg)
        threading.Thread(target=_run, daemon=True).start()

    def _action_apply_button_remap(self):
        long_sel = self.opt_long_press.get()
        short_sel = self.opt_short_press.get()

        long_key = "KEYCODE_APP_SWITCH"
        for k in BUTTON_ACTIONS:
            if f"[{k}]" in long_sel or (not k and "[Standard Back]" in long_sel):
                long_key = k
                break

        short_key = ""
        if "[KEYCODE_APP_SWITCH]" in short_sel: short_key = "KEYCODE_APP_SWITCH"
        elif "[fullRefreshScreen]" in short_sel: short_key = "fullRefreshScreen"
        elif "[screenshot]" in short_sel: short_key = "screenshot"
        elif "[back_to_home]" in short_sel: short_key = "back_to_home"

        def _run():
            ok, msg = self.ops.apply_button_mapping(long_action=long_key, short_action=short_key)
            if ok:
                messagebox.showinfo("Remap Applied", msg)
                self._action_read_button_remap()
            else:
                messagebox.showerror("Remap Error", msg)
        threading.Thread(target=_run, daemon=True).start()

    def _action_read_button_remap(self):
        def _run():
            res = self.ops.get_current_button_mapping()
            txt = (
                f"Short-Press Action : {res['shortPressAction'] or '(Standard Back)'}\n"
                f"Long-Press Action  : {res['longPressAction']}\n"
                f"Short-Press Enabled: {res['shortPressEnabled']}\n"
                f"Raw Global Payload : {res['raw']}"
            )
            # Synchronize dropdown selections to match device
            for opt in self.opt_long_press._values:
                if f"[{res['longPressAction']}]" in opt:
                    self.dispatch(lambda o=opt: self.opt_long_press.set(o))
                    break

            for opt in self.opt_short_press._values:
                if (not res['shortPressAction'] and "[Recommended]" in opt) or (res['shortPressAction'] and f"[{res['shortPressAction']}]" in opt):
                    self.dispatch(lambda o=opt: self.opt_short_press.set(o))
                    break

            self.dispatch(lambda: self.lbl_active_mapping.configure(text=txt))
        threading.Thread(target=_run, daemon=True).start()

    def _action_reset_button_remap(self):
        if not messagebox.askyesno("Reset Button", "Reset center button to Onyx factory default (toggleFrontLight)?"):
            return
        def _run():
            self.ops.reset_button_mapping()
            self._action_read_button_remap()
            messagebox.showinfo("Reset", "Button reset to factory defaults.")
        threading.Thread(target=_run, daemon=True).start()

    # =========================================================================
    # ACTIONS: DEBLOATER & SETTINGS
    # =========================================================================
    def _action_refresh_debloat_list_async(self):
        threading.Thread(target=self._action_refresh_debloat_list, daemon=True).start()

    def _action_refresh_debloat_list(self):
        disabled_set = self.ops.get_disabled_packages()
        for pkg, item in self.pkg_widgets.items():
            is_dis = pkg in disabled_set
            item["disabled"] = is_dis
            btn = item["button"]
            if is_dis:
                self.dispatch(lambda b=btn, p=pkg: b.configure(text="Enable", fg_color="#283042", hover_color="#37435C", command=lambda: self._toggle_package(p, False)))
            else:
                self.dispatch(lambda b=btn, p=pkg: b.configure(text="Disable", fg_color=self.COLOR_RED, hover_color="#DC2626", command=lambda: self._toggle_package(p, True)))

    def _toggle_package(self, pkg_name, disable):
        def _run():
            if disable: self.ops.disable_package(pkg_name)
            else: self.ops.enable_package(pkg_name)
            self._action_refresh_debloat_list()
        threading.Thread(target=_run, daemon=True).start()

    def _action_safe_debloat(self):
        if not messagebox.askyesno("Safe Debloat", "Disable background Qualcomm cellular, dual-SIM, and voice activation services?"):
            return
        def _run():
            res = self.ops.apply_safe_debloat_preset()
            self._action_refresh_debloat_list()
            messagebox.showinfo("Safe Debloat Completed", f"Successfully processed {len(res)} packages.")
        threading.Thread(target=_run, daemon=True).start()

    def _action_enable_all_debloated(self):
        def _run():
            for pkg in self.pkg_widgets:
                self.ops.enable_package(pkg)
            self._action_refresh_debloat_list()
            messagebox.showinfo("Enabled", "All packages re-enabled.")
        threading.Thread(target=_run, daemon=True).start()

    def _action_custom_disable(self):
        pkg = self.entry_custom_pkg.get().strip()
        if not pkg: return
        threading.Thread(target=lambda: [self.ops.disable_package(pkg), self._action_refresh_debloat_list()], daemon=True).start()

    def _action_custom_enable(self):
        pkg = self.entry_custom_pkg.get().strip()
        if not pkg: return
        threading.Thread(target=lambda: [self.ops.enable_package(pkg), self._action_refresh_debloat_list()], daemon=True).start()

    def _action_fix_timeout_preset(self):
        def _run():
            self.ops.apply_system_settings({"screen_off_timeout": "300000"})
            self._action_query_settings_silent()
            messagebox.showinfo("Timeout Fixed", "Screen timeout fixed to 5 Minutes (300,000 ms)!")
        threading.Thread(target=_run, daemon=True).start()

    def _action_apply_settings(self):
        to_str = self.opt_timeout.get()
        timeout_val = "300000"
        if "60000" in to_str: timeout_val = "60000"
        elif "120000" in to_str: timeout_val = "120000"
        elif "300000" in to_str: timeout_val = "300000"
        elif "600000" in to_str: timeout_val = "600000"
        elif "1800000" in to_str: timeout_val = "1800000"
        elif "2147483647" in to_str: timeout_val = "2147483647"

        font_str = self.opt_font.get()
        font_val = "1.05" if "1.05" in font_str else ("1.00" if "1.00" in font_str else ("0.85" if "0.85" in font_str else "1.15"))

        dpi_str = self.opt_dpi.get()
        dpi_val = "reset" if "Reset" in dpi_str else ("200" if "200" in dpi_str else ("225" if "225" in dpi_str else "240"))

        payload = {
            "screen_off_timeout": timeout_val,
            "send_action_app_error": "1" if not self.sw_telemetry.get() else "0",
            "ble_scan": "1" if not self.sw_ble.get() else "0",
            "wifi_scan": "1" if not self.sw_wifi.get() else "0",
            "location_mode": "3" if not self.sw_location.get() else "0",
            "font_scale": font_val,
            "density": dpi_val,
            "high_contrast": "1" if self.sw_contrast.get() else "0"
        }

        def _run():
            ok, msg = self.ops.apply_system_settings(payload)
            if ok:
                messagebox.showinfo("Settings Applied", msg)
            else:
                messagebox.showerror("Error", msg)
        threading.Thread(target=_run, daemon=True).start()

    def _action_query_settings_silent(self):
        def _run():
            s = self.ops.get_system_settings()
            self.dispatch(self._update_settings_ui, s, False)
        threading.Thread(target=_run, daemon=True).start()

    def _action_query_settings(self):
        def _run():
            s = self.ops.get_system_settings()
            self.dispatch(self._update_settings_ui, s, True)
        threading.Thread(target=_run, daemon=True).start()

    def _update_settings_ui(self, s, show_dialog=False):
        to = s.get("screen_off_timeout", "")
        if to == "60000": self.opt_timeout.set("1 Minute (60000 ms)")
        elif to == "120000": self.opt_timeout.set("2 Minutes (120000 ms)")
        elif to == "300000": self.opt_timeout.set("5 Minutes [Recommended] (300000 ms)")
        elif to == "600000": self.opt_timeout.set("10 Minutes (600000 ms)")
        elif to == "1800000": self.opt_timeout.set("30 Minutes (1800000 ms)")
        elif to == "2147483647": self.opt_timeout.set("Never Sleep [Buggy default] (2147483647 ms)")

        if s.get("send_action_app_error") == "0": self.sw_telemetry.select()
        else: self.sw_telemetry.deselect()

        if s.get("ble_scan") == "0": self.sw_ble.select()
        else: self.sw_ble.deselect()

        if s.get("wifi_scan") == "0": self.sw_wifi.select()
        else: self.sw_wifi.deselect()

        if s.get("location_mode") == "0": self.sw_location.select()
        else: self.sw_location.deselect()

        if s.get("high_contrast") == "1": self.sw_contrast.select()
        else: self.sw_contrast.deselect()

        # Update font scale and DPI
        font_s = s.get("font_scale", "1.0")
        for val in self.opt_font._values:
            if font_s in val:
                self.opt_font.set(val)
                break

        dpi_s = s.get("density", "212")
        for val in self.opt_dpi._values:
            if dpi_s in val or (dpi_s == "212" and "Default" in val):
                self.opt_dpi.set(val)
                break

        if show_dialog:
            messagebox.showinfo("Settings Queried", f"Current Device Values:\nTimeout: {s.get('screen_off_timeout')}ms\nFont: {s.get('font_scale')}\nDensity: {s.get('density')}")

    # =========================================================================
    # ACTIONS: ADB & PLATFORM TOOLS MANAGEMENT
    # =========================================================================
    def _action_install_adb(self):
        """Opens a progress dialog and auto-downloads official Google Android Platform-Tools."""
        modal = ctk.CTkToplevel(self)
        modal.title("Android SDK Platform-Tools Installer")
        modal.geometry("520x260")
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()

        try:
            x = self.winfo_x() + (self.winfo_width() - 520) // 2
            y = self.winfo_y() + (self.winfo_height() - 260) // 2
            modal.geometry(f"+{x}+{y}")
        except Exception:
            pass

        ctk.CTkLabel(
            modal,
            text="Android SDK Platform-Tools Installer",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#FFFFFF"
        ).pack(anchor="w", padx=20, pady=(16, 4))

        ctk.CTkLabel(
            modal,
            text="Official Google Binaries: adb.exe, fastboot.exe, AdbWinApi.dll",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=self.COLOR_TEXT_MUTED
        ).pack(anchor="w", padx=20, pady=(0, 14))

        lbl_status = ctk.CTkLabel(
            modal,
            text="Connecting to dl.google.com...",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=self.COLOR_CYAN,
            justify="left"
        )
        lbl_status.pack(anchor="w", padx=20, pady=(0, 8))

        progress_bar = ctk.CTkProgressBar(modal, height=12, corner_radius=6, progress_color=self.COLOR_GREEN)
        progress_bar.set(0.0)
        progress_bar.pack(fill="x", padx=20, pady=(0, 16))

        btn_box = ctk.CTkFrame(modal, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(0, 16))

        btn_close = ctk.CTkButton(
            btn_box,
            text="Cancel",
            width=100,
            height=32,
            corner_radius=6,
            fg_color="#283042",
            hover_color="#3B4660",
            command=modal.destroy
        )
        btn_close.pack(side="right")

        def _worker():
            def _prog(percent, msg):
                def _ui():
                    progress_bar.set(percent / 100.0)
                    lbl_status.configure(text=f"{msg} ({percent:.1f}%)")
                self.dispatch(_ui)

            ok, ver = self.adb.install_tools(progress_callback=_prog)
            def _finish():
                if ok:
                    progress_bar.set(1.0)
                    lbl_status.configure(text=f"Installed & verified successfully! ({ver})")
                    btn_close.configure(text="Done", fg_color=self.COLOR_GREEN, hover_color="#059669")
                    self.append_log(f"Platform-tools installed successfully: {ver}")
                    self.refresh_device_status_async()
                    messagebox.showinfo("ADB Installed", f"Android SDK Platform-Tools successfully installed!\nVersion: {ver}\nLocation: {self.adb.adb_bin}")
                else:
                    lbl_status.configure(text="Download or extraction failed. Check connection.")
                    btn_close.configure(text="Close")
                    messagebox.showerror("Installation Failed", "Could not download or install Google Platform-Tools. Check your network or firewall.")
            self.dispatch(_finish)

        threading.Thread(target=_worker, daemon=True).start()

    def _action_register_adb_path(self):
        """Registers the current ADB directory into the Windows User PATH environment variable."""
        from core.adb_installer import add_directory_to_user_path
        adb_dir = os.path.dirname(self.adb.adb_bin)
        if not os.path.isdir(adb_dir):
            messagebox.showwarning("Register PATH", "No valid platform-tools directory found. Please run Auto-Install first.")
            return
        ok = add_directory_to_user_path(adb_dir)
        if ok:
            messagebox.showinfo("PATH Updated", f"Successfully registered in Windows User PATH:\n{adb_dir}\n\nA broadcast notification has been sent to running applications.")
            self.append_log(f"Registered {adb_dir} in User PATH")
        else:
            messagebox.showerror("PATH Update Failed", "Failed to write to User PATH registry (HKCU\\Environment\\Path).")

    def _action_open_tools_folder(self):
        """Opens Windows Explorer at the platform-tools directory."""
        adb_dir = os.path.dirname(self.adb.adb_bin)
        if os.path.isdir(adb_dir):
            try:
                os.startfile(adb_dir)
            except Exception as e:
                messagebox.showerror("Folder Error", f"Could not open directory: {e}")
        else:
            messagebox.showwarning("Tools Folder", "Platform-tools folder does not exist yet. Please run Auto-Install first.")
