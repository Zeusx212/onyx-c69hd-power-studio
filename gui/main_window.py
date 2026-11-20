"""
Modern CustomTkinter GUI for Onyx Boox C69HD Customizer.
Features modern Windows 11 / macOS fluent cards, sidebar navigation,
live device probing, personalization studio (screensavers & boot animations),
debloater, button remapping, and system tweaks.
"""

import os
import threading
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

from core.device_ops import BUTTON_ACTIONS, DEBLOAT_CATALOG, HAS_PILLOW

# Initialize CustomTkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MainWindow(ctk.CTk):
    def __init__(self, adb_manager, device_ops):
        super().__init__()
        self.adb = adb_manager
        self.ops = device_ops
        self.adb.log_callback = self.append_log

        self.title("Onyx Boox C69HD Suite • Faust 5 OEM Customizer")
        self.geometry("1100x780")
        self.minsize(980, 680)

        # Selected files
        self._selected_image_path = None
        self._selected_bootanim_path = None
        self._ctk_preview_image = None
        self.active_nav_btn = None

        # Color Palette
        self.COLOR_SIDEBAR = "#11141C"
        self.COLOR_MAIN_BG = "#0A0C10"
        self.COLOR_CARD = "#161922"
        self.COLOR_CARD_BORDER = "#232838"
        self.COLOR_CYAN = "#38BDF8"
        self.COLOR_BLUE = "#3B82F6"
        self.COLOR_GREEN = "#10B981"
        self.COLOR_RED = "#EF4444"
        self.COLOR_AMBER = "#F59E0B"
        self.COLOR_TEXT_MUTED = "#94A3B8"

        self.configure(fg_color=self.COLOR_MAIN_BG)

        # Build Main Layout: Left Sidebar + Right Dynamic Content Area
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_content_area()

        # Start on Root Page
        self._show_page("root")

        # Initial background device probe
        self.refresh_device_status_async()

    # =========================================================================
    # SIDEBAR NAVIGATION
    # =========================================================================
    def _build_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=self.COLOR_SIDEBAR)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        # App Brand Header
        brand_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        brand_frame.pack(fill="x", padx=18, pady=(20, 16))

        lbl_logo = ctk.CTkLabel(
            brand_frame,
            text="ONYX C69HD",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_logo.pack(anchor="w")

        lbl_edition = ctk.CTkLabel(
            brand_frame,
            text="Faust 5 OEM Suite • v2.1",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=self.COLOR_CYAN
        )
        lbl_edition.pack(anchor="w")

        # Navigation Buttons
        self.nav_buttons = {}
        pages = [
            ("root", "🛡️  Root & Partitions"),
            ("button", "🔘  Button Remapper"),
            ("media", "🎨  Screensaver & Boot"),
            ("debloat", "🧹  Reversible Debloat"),
            ("settings", "⚙️  Device Settings"),
            ("logs", "📊  Hardware & Logs")
        ]

        nav_box = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        nav_box.pack(fill="x", padx=12, pady=6)

        for page_id, text in pages:
            btn = ctk.CTkButton(
                nav_box,
                text=text,
                height=42,
                corner_radius=8,
                fg_color="transparent",
                text_color=self.COLOR_TEXT_MUTED,
                hover_color="#1E2330",
                anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="normal"),
                command=lambda pid=page_id: self._show_page(pid)
            )
            btn.pack(fill="x", pady=3)
            self.nav_buttons[page_id] = btn

        # Bottom Device Status Card inside Sidebar
        device_card = ctk.CTkFrame(self.sidebar_frame, corner_radius=10, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        device_card.pack(side="bottom", fill="x", padx=14, pady=16)

        self.lbl_device_title = ctk.CTkLabel(
            device_card,
            text="Probing Device...",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#FFFFFF"
        )
        self.lbl_device_title.pack(anchor="w", padx=12, pady=(10, 2))

        self.lbl_device_details = ctk.CTkLabel(
            device_card,
            text="Slot: -- | Battery: --",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=self.COLOR_TEXT_MUTED
        )
        self.lbl_device_details.pack(anchor="w", padx=12, pady=(0, 6))

        self.lbl_status_badge = ctk.CTkLabel(
            device_card,
            text="DISCONNECTED",
            corner_radius=6,
            fg_color="#7F1D1D",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            padx=8,
            pady=3
        )
        self.lbl_status_badge.pack(anchor="w", padx=12, pady=(0, 10))

        btn_reprobe = ctk.CTkButton(
            device_card,
            text="↻ Refresh Connection",
            height=28,
            corner_radius=6,
            fg_color="#283042",
            hover_color="#37435C",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self.refresh_device_status_async
        )
        btn_reprobe.pack(fill="x", padx=12, pady=(0, 10))

    # =========================================================================
    # CONTENT AREA & PAGE SWITCHER
    # =========================================================================
    def _build_content_area(self):
        self.content_container = ctk.CTkFrame(self, fg_color=self.COLOR_MAIN_BG, corner_radius=0)
        self.content_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

        self.pages = {}
        self.pages["root"] = self._create_page_root()
        self.pages["button"] = self._create_page_button()
        self.pages["media"] = self._create_page_media()
        self.pages["debloat"] = self._create_page_debloat()
        self.pages["settings"] = self._create_page_settings()
        self.pages["logs"] = self._create_page_logs()

    def _show_page(self, page_id):
        for pid, frame in self.pages.items():
            if pid == page_id:
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.grid_forget()

        # Update Sidebar Button Highlights
        for pid, btn in self.nav_buttons.items():
            if pid == page_id:
                btn.configure(fg_color="#1E2433", text_color=self.COLOR_CYAN, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"))
            else:
                btn.configure(fg_color="transparent", text_color=self.COLOR_TEXT_MUTED, font=ctk.CTkFont(family="Segoe UI", size=13, weight="normal"))

    # =========================================================================
    # PAGE 1: ROOT & PARTITIONS
    # =========================================================================
    def _create_page_root(self):
        page = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")

        # Header Title
        lbl_h = ctk.CTkLabel(page, text="Rooting & Partition Management", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        lbl_h.pack(anchor="w", pady=(0, 4))
        lbl_sub = ctk.CTkLabel(page, text="Backup stock partitions, flash Magisk patched boot images, and enable hardware wake.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", pady=(0, 16))

        # Card 1: Stock Partition Backup
        c1 = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c1.pack(fill="x", pady=8)

        lbl_c1_t = ctk.CTkLabel(c1, text="1. Stock Partition Backup", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN)
        lbl_c1_t.pack(anchor="w", padx=18, pady=(16, 4))
        lbl_c1_d = ctk.CTkLabel(
            c1,
            text="Dumps active boot (boot_a / boot_b) and vbmeta partitions into the local './backups/' folder.\nAlways do this before attempting any fastboot modifications.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT_MUTED,
            justify="left"
        )
        lbl_c1_d.pack(anchor="w", padx=18, pady=(0, 12))

        btn_backup = ctk.CTkButton(
            c1,
            text="📥  Backup Stock Partitions (dd + adb pull)",
            height=38,
            corner_radius=8,
            fg_color=self.COLOR_BLUE,
            hover_color="#2563EB",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._action_backup_partitions
        )
        btn_backup.pack(anchor="w", padx=18, pady=(0, 16))

        # Card 2: Magisk Root & Fastboot Flashing
        c2 = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c2.pack(fill="x", pady=8)

        lbl_c2_t = ctk.CTkLabel(c2, text="2. Magisk Root Installation & Fastboot Flashing", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN)
        lbl_c2_t.pack(anchor="w", padx=18, pady=(16, 4))
        lbl_c2_d = ctk.CTkLabel(
            c2,
            text="Step-by-step workflow:\n"
                 "1. Install Magisk APK to device -> 2. Patch your dumped stock_boot.img -> 3. Flash patched image via Fastboot.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT_MUTED,
            justify="left"
        )
        lbl_c2_d.pack(anchor="w", padx=18, pady=(0, 12))

        btn_row_m = ctk.CTkFrame(c2, fg_color="transparent")
        btn_row_m.pack(fill="x", padx=18, pady=(0, 16))

        ctk.CTkButton(btn_row_m, text="📦 1. Install Magisk APK", height=36, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=self._action_install_magisk).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row_m, text="⚡ 2. Reboot to Fastboot", height=36, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=lambda: self.ops.reboot_device("bootloader")).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row_m, text="🚀 3. Flash Patched Boot...", height=36, corner_radius=8, fg_color=self.COLOR_BLUE, hover_color="#2563EB", command=self._action_flash_patched_boot).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row_m, text="🔄 Restore Stock Boot...", height=36, corner_radius=8, fg_color=self.COLOR_RED, hover_color="#DC2626", command=self._action_restore_stock_boot).pack(side="left")

        # Card 3: Button Wake Magisk Module
        c3 = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c3.pack(fill="x", pady=8)

        lbl_c3_t = ctk.CTkLabel(c3, text="3. Hardware Physical Button Wake (Magisk Module)", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN)
        lbl_c3_t.pack(anchor="w", padx=18, pady=(16, 4))
        lbl_c3_d = ctk.CTkLabel(
            c3,
            text="By default on C69HD, only the top power key wakes the e-reader.\n"
                 "This Magisk module patches gpio-keys.kl so pressing the front center button or side keys instantly wakes the screen.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT_MUTED,
            justify="left"
        )
        lbl_c3_d.pack(anchor="w", padx=18, pady=(0, 12))

        ctk.CTkButton(
            c3,
            text="⚡ Install 'c69hd-wake' Magisk Module",
            height=38,
            corner_radius=8,
            fg_color=self.COLOR_GREEN,
            hover_color="#059669",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._action_install_wake_module
        ).pack(anchor="w", padx=18, pady=(0, 16))

        return page

    # =========================================================================
    # PAGE 2: BUTTON REMAPPING
    # =========================================================================
    def _create_page_button(self):
        page = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")

        lbl_h = ctk.CTkLabel(page, text="Hardware Button Remapper", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        lbl_h.pack(anchor="w", pady=(0, 4))
        lbl_sub = ctk.CTkLabel(page, text="Customize the center physical button (KEYCODE_BACK) on your Onyx Boox C69HD.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", pady=(0, 16))

        # Hardware Context Banner
        info_banner = ctk.CTkFrame(page, corner_radius=10, fg_color="#1E2638", border_width=1, border_color="#2E3A54")
        info_banner.pack(fill="x", pady=6)
        lbl_b_text = ctk.CTkLabel(
            info_banner,
            text="💡 Why Remap? The C69HD has NO frontlight/backlight hardware. The factory default action\n"
                 "for holding the front button is toggling the backlight—which does literally nothing!\n"
                 "Remapping it to Recent Apps (App Switcher) gives you instant multitasking.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#CBD5E1",
            justify="left"
        )
        lbl_b_text.pack(anchor="w", padx=16, pady=12)

        # Configuration Card
        c_config = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c_config.pack(fill="x", pady=10)

        lbl_cfg_t = ctk.CTkLabel(c_config, text="Configure Center Physical Button Actions", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN)
        lbl_cfg_t.pack(anchor="w", padx=18, pady=(16, 12))

        # Long Press
        lbl_lp = ctk.CTkLabel(c_config, text="Long-Press (Hold) Action:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        lbl_lp.pack(anchor="w", padx=18, pady=(4, 4))

        self.opt_long_press = ctk.CTkOptionMenu(
            c_config,
            height=36,
            corner_radius=8,
            values=[f"{v} [{k}]" if k else f"{v} [Standard Back]" for k, v in BUTTON_ACTIONS.items()],
            width=550
        )
        self.opt_long_press.set("Recent Apps / App Switcher (Recommended for C69HD) [KEYCODE_APP_SWITCH]")
        self.opt_long_press.pack(anchor="w", padx=18, pady=(0, 12))

        # Short Press
        lbl_sp = ctk.CTkLabel(c_config, text="Short-Press (Single Tap) Action:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        lbl_sp.pack(anchor="w", padx=18, pady=(4, 4))

        self.opt_short_press = ctk.CTkOptionMenu(
            c_config,
            height=36,
            corner_radius=8,
            values=[
                "Standard Back Key Event [Recommended] []",
                "Recent Apps / App Switcher [KEYCODE_APP_SWITCH]",
                "Full Screen E-Ink Refresh (Clears Ghosting) [fullRefreshScreen]",
                "Take Screenshot [screenshot]",
                "Return to Home Screen [back_to_home]"
            ],
            width=550
        )
        self.opt_short_press.set("Standard Back Key Event [Recommended] []")
        self.opt_short_press.pack(anchor="w", padx=18, pady=(0, 16))

        # Action Buttons
        btn_box = ctk.CTkFrame(c_config, fg_color="transparent")
        btn_box.pack(anchor="w", padx=18, pady=(0, 18))

        ctk.CTkButton(btn_box, text="💾  Apply Mapping to Device", height=38, corner_radius=8, fg_color=self.COLOR_BLUE, hover_color="#2563EB", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=self._action_apply_button_remap).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_box, text="📖  Query Current Mapping", height=38, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=self._action_read_button_remap).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_box, text="🔄  Reset to Factory Default", height=38, corner_radius=8, fg_color=self.COLOR_RED, hover_color="#DC2626", command=self._action_reset_button_remap).pack(side="left")

        # Active Status Card
        c_active = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c_active.pack(fill="x", pady=6)

        lbl_act_t = ctk.CTkLabel(c_active, text="Active Mapping in Device Settings.Global", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=self.COLOR_CYAN)
        lbl_act_t.pack(anchor="w", padx=18, pady=(14, 4))

        self.lbl_active_mapping = ctk.CTkLabel(c_active, text="Click 'Query Current Mapping' to check connected device...", font=ctk.CTkFont(family="Consolas", size=11), text_color="#38BDF8", justify="left")
        self.lbl_active_mapping.pack(anchor="w", padx=18, pady=(0, 14))

        return page

    # =========================================================================
    # PAGE 3: SCREENSAVER & BOOT MEDIA
    # =========================================================================
    def _create_page_media(self):
        page = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")

        lbl_h = ctk.CTkLabel(page, text="Screensaver & Boot Animation Studio", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        lbl_h.pack(anchor="w", pady=(0, 4))
        lbl_sub = ctk.CTkLabel(page, text="Customize sleep screens, wallpaper galleries, and Android boot animation for Carta 6\" E-Ink.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", pady=(0, 16))

        # Card 1: Custom Screensaver
        c1 = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c1.pack(fill="x", pady=8)

        lbl_c1_t = ctk.CTkLabel(c1, text="1. Custom Screensaver & Sleep Screen", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN)
        lbl_c1_t.pack(anchor="w", padx=18, pady=(16, 4))

        split_ss = ctk.CTkFrame(c1, fg_color="transparent")
        split_ss.pack(fill="x", padx=18, pady=(0, 16))

        # Left Column: Controls
        left_ctrl = ctk.CTkFrame(split_ss, fg_color="transparent")
        left_ctrl.pack(side="left", fill="both", expand=True)

        lbl_ss_desc = ctk.CTkLabel(
            left_ctrl,
            text="Select any image (.png, .jpg, .webp). The tool will automatically scale/crop it\n"
                 "to 758 × 1024 native Carta resolution with high-contrast grayscale for E-Ink.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT_MUTED,
            justify="left"
        )
        lbl_ss_desc.pack(anchor="w", pady=(0, 8))

        f_picker_row = ctk.CTkFrame(left_ctrl, fg_color="transparent")
        f_picker_row.pack(anchor="w", pady=4)

        ctk.CTkButton(f_picker_row, text="📁 Choose Image...", height=34, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=self._action_choose_screensaver_file).pack(side="left", padx=(0, 10))
        self.lbl_chosen_image = ctk.CTkLabel(f_picker_row, text="No image selected", text_color=self.COLOR_TEXT_MUTED)
        self.lbl_chosen_image.pack(side="left")

        self.sw_grayscale = ctk.CTkSwitch(left_ctrl, text="Auto-convert to high-contrast E-Ink grayscale (LANCZOS 758x1024)", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.sw_grayscale.select()
        self.sw_grayscale.pack(anchor="w", pady=8)

        lbl_target = ctk.CTkLabel(left_ctrl, text="Target Location:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        lbl_target.pack(anchor="w", pady=(4, 4))

        self.var_ss_target = ctk.StringVar(value="user")
        radio_row = ctk.CTkFrame(left_ctrl, fg_color="transparent")
        radio_row.pack(anchor="w", pady=2)

        ctk.CTkRadioButton(radio_row, text="User Gallery (/sdcard/Pictures/Screensaver)", variable=self.var_ss_target, value="user").pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(radio_row, text="System Standby (standby-1.png)", variable=self.var_ss_target, value="standby").pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(radio_row, text="Shutdown Screen", variable=self.var_ss_target, value="shutdown").pack(side="left")

        ss_btn_row = ctk.CTkFrame(left_ctrl, fg_color="transparent")
        ss_btn_row.pack(anchor="w", pady=(14, 4))

        ctk.CTkButton(ss_btn_row, text="🚀 Push Screensaver", height=36, corner_radius=8, fg_color=self.COLOR_BLUE, hover_color="#2563EB", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=self._action_push_screensaver).pack(side="left", padx=(0, 8))
        ctk.CTkButton(ss_btn_row, text="📱 Open Wallpaper Settings", height=36, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=self.ops.open_device_screensaver_settings).pack(side="left", padx=(0, 8))
        ctk.CTkButton(ss_btn_row, text="💤 Test Sleep (Lock)", height=36, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=lambda: self.ops.reboot_device("sleep")).pack(side="left")

        # Right Column: Live Thumbnail Preview
        right_preview = ctk.CTkFrame(split_ss, corner_radius=10, fg_color="#0F121A", border_width=1, border_color="#252C3D", width=140, height=190)
        right_preview.pack(side="right", padx=(16, 0))
        right_preview.pack_propagate(False)

        self.lbl_image_preview = ctk.CTkLabel(right_preview, text="Preview\n758x1024", text_color=self.COLOR_TEXT_MUTED)
        self.lbl_image_preview.pack(expand=True, fill="both")

        # Card 2: Boot Animation
        c2 = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c2.pack(fill="x", pady=8)

        lbl_c2_t = ctk.CTkLabel(c2, text="2. Custom Boot Animation", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN)
        lbl_c2_t.pack(anchor="w", padx=18, pady=(16, 4))

        lbl_c2_d = ctk.CTkLabel(
            c2,
            text="Install custom bootanimation.zip systemlessly via Magisk media overlay.\n"
                 "Pick an existing bootanimation.zip or build one from a folder of PNG frames.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT_MUTED,
            justify="left"
        )
        lbl_c2_d.pack(anchor="w", padx=18, pady=(0, 10))

        b_picker_row = ctk.CTkFrame(c2, fg_color="transparent")
        b_picker_row.pack(anchor="w", padx=18, pady=4)

        ctk.CTkButton(b_picker_row, text="📁 Select bootanimation.zip...", height=34, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=self._action_choose_bootanim_zip).pack(side="left", padx=(0, 8))
        ctk.CTkButton(b_picker_row, text="🖼️ Create from Folder of Frames...", height=34, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=self._action_create_bootanim_from_folder).pack(side="left", padx=(0, 10))
        self.lbl_chosen_bootanim = ctk.CTkLabel(b_picker_row, text="No animation selected", text_color=self.COLOR_TEXT_MUTED)
        self.lbl_chosen_bootanim.pack(side="left")

        b_btn_row = ctk.CTkFrame(c2, fg_color="transparent")
        b_btn_row.pack(anchor="w", padx=18, pady=(12, 18))

        ctk.CTkButton(b_btn_row, text="⚡ Install Animation (Magisk)", height=36, corner_radius=8, fg_color=self.COLOR_BLUE, hover_color="#2563EB", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=self._action_install_bootanim).pack(side="left", padx=(0, 8))
        ctk.CTkButton(b_btn_row, text="▶️ Live Preview on Device Screen", height=36, corner_radius=8, fg_color=self.COLOR_GREEN, hover_color="#059669", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=lambda: threading.Thread(target=self.ops.preview_bootanimation_on_device, daemon=True).start()).pack(side="left", padx=(0, 8))
        ctk.CTkButton(b_btn_row, text="🔄 Restore Stock Boot Animation", height=36, corner_radius=8, fg_color=self.COLOR_RED, hover_color="#DC2626", command=self._action_restore_stock_bootanim).pack(side="left")

        return page

    # =========================================================================
    # PAGE 4: DEBLOATER
    # =========================================================================
    def _create_page_debloat(self):
        page = ctk.CTkFrame(self.content_container, fg_color="transparent")
        page.grid_rowconfigure(2, weight=1)
        page.grid_columnconfigure(0, weight=1)

        # Header Title
        lbl_h = ctk.CTkLabel(page, text="Reversible System Debloater", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        lbl_h.grid(row=0, column=0, sticky="w", pady=(0, 4))
        lbl_sub = ctk.CTkLabel(page, text="Safely disable unused cellular daemons, SVA voice listener, and Google services without root risk.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED)
        lbl_sub.grid(row=1, column=0, sticky="w", pady=(0, 14))

        # Top Control Bar (Search + Presets)
        ctrl_bar = ctk.CTkFrame(page, corner_radius=10, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        ctrl_bar.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        bar_inner = ctk.CTkFrame(ctrl_bar, fg_color="transparent")
        bar_inner.pack(fill="x", padx=14, pady=10)

        ctk.CTkButton(bar_inner, text="🛡️ 1-Click Safe Debloat", height=34, corner_radius=8, fg_color=self.COLOR_BLUE, hover_color="#2563EB", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=self._action_safe_debloat).pack(side="left", padx=(0, 8))
        ctk.CTkButton(bar_inner, text="🔄 Re-enable All", height=34, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=self._action_enable_all_debloated).pack(side="left", padx=(0, 8))
        ctk.CTkButton(bar_inner, text="↻ Refresh List", height=34, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=self._action_refresh_debloat_list).pack(side="left", padx=(0, 14))

        self.entry_filter = ctk.CTkEntry(bar_inner, placeholder_text="🔍 Filter packages...", width=220, height=34, corner_radius=8)
        self.entry_filter.pack(side="right")
        self.entry_filter.bind("<KeyRelease>", lambda e: self._filter_debloat_items())

        # Scrollable Packages Frame
        self.scroll_debloat = ctk.CTkScrollableFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        self.scroll_debloat.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        page.grid_rowconfigure(3, weight=1)

        self.pkg_widgets = {}
        self._populate_debloat_items()

        # Custom Package Entry Box
        custom_box = ctk.CTkFrame(page, corner_radius=10, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        custom_box.grid(row=4, column=0, sticky="ew")

        c_inner = ctk.CTkFrame(custom_box, fg_color="transparent")
        c_inner.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(c_inner, text="Manual Package Control:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(side="left", padx=(0, 8))
        self.entry_custom_pkg = ctk.CTkEntry(c_inner, placeholder_text="e.g. com.onyx.mail", width=280, height=34, corner_radius=8)
        self.entry_custom_pkg.pack(side="left", padx=(0, 8))

        ctk.CTkButton(c_inner, text="Disable Package", height=34, corner_radius=8, fg_color=self.COLOR_RED, hover_color="#DC2626", command=self._action_custom_disable).pack(side="left", padx=(0, 6))
        ctk.CTkButton(c_inner, text="Enable Package", height=34, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=self._action_custom_enable).pack(side="left")

        return page

    def _populate_debloat_items(self):
        for widget in self.scroll_debloat.winfo_children():
            widget.destroy()

        self.pkg_widgets.clear()

        for cat in DEBLOAT_CATALOG:
            cat_title = cat["category"]
            lbl_cat = ctk.CTkLabel(self.scroll_debloat, text=cat_title, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=self.COLOR_CYAN)
            lbl_cat.pack(anchor="w", padx=10, pady=(14, 6))

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
                    "disabled": False
                }

    def _filter_debloat_items(self):
        query = self.entry_filter.get().strip().lower()
        for pkg, data in self.pkg_widgets.items():
            match = (query in pkg.lower()) or (query in data["desc"].lower())
            if match or not query:
                data["row"].pack(fill="x", pady=3)
            else:
                data["row"].pack_forget()

    # =========================================================================
    # PAGE 5: DEVICE SETTINGS
    # =========================================================================
    def _create_page_settings(self):
        page = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")

        lbl_h = ctk.CTkLabel(page, text="Device Settings & Power Tweaks", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        lbl_h.pack(anchor="w", pady=(0, 4))
        lbl_sub = ctk.CTkLabel(page, text="Fix the factory infinite sleep bug, disable telemetry drain, and adjust font clarity.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", pady=(0, 16))

        # Card 1: Screen Timeout Bug Fix
        c_to = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c_to.pack(fill="x", pady=8)

        lbl_to_t = ctk.CTkLabel(c_to, text="Screen Timeout (Fix 24.8-Day Sleep Bug)", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN)
        lbl_to_t.pack(anchor="w", padx=18, pady=(16, 4))

        lbl_to_d = ctk.CTkLabel(
            c_to,
            text="⚠️ Factory Bug: Many C69HD units ship with screen_off_timeout set to 2147483647 ms (24.8 days)!\n"
                 "The device stays awake indefinitely and drains battery. Set it to 5 Minutes for optimal reading.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_AMBER,
            justify="left"
        )
        lbl_to_d.pack(anchor="w", padx=18, pady=(0, 12))

        to_row = ctk.CTkFrame(c_to, fg_color="transparent")
        to_row.pack(anchor="w", padx=18, pady=(0, 16))

        self.opt_timeout = ctk.CTkOptionMenu(
            to_row,
            height=36,
            corner_radius=8,
            values=[
                "1 Minute (60000 ms)",
                "2 Minutes (120000 ms)",
                "5 Minutes [Recommended] (300000 ms)",
                "10 Minutes (600000 ms)",
                "30 Minutes (1800000 ms)",
                "Never Sleep [Buggy default] (2147483647 ms)"
            ],
            width=320
        )
        self.opt_timeout.set("5 Minutes [Recommended] (300000 ms)")
        self.opt_timeout.pack(side="left", padx=(0, 10))

        ctk.CTkButton(to_row, text="⚡ Fix to 5 Minutes Now", height=36, corner_radius=8, fg_color=self.COLOR_GREEN, hover_color="#059669", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=self._action_fix_timeout_preset).pack(side="left")

        # Card 2: Radios & Privacy
        c_rad = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c_rad.pack(fill="x", pady=8)

        lbl_rad_t = ctk.CTkLabel(c_rad, text="Battery & Privacy Radios", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN)
        lbl_rad_t.pack(anchor="w", padx=18, pady=(16, 8))

        self.sw_telemetry = ctk.CTkSwitch(c_rad, text="Disable background crash & error telemetry (send_action_app_error = 0)", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.sw_telemetry.pack(anchor="w", padx=18, pady=4)

        self.sw_ble = ctk.CTkSwitch(c_rad, text="Disable background Bluetooth LE scanning (ble_scan_always_enabled = 0)", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.sw_ble.pack(anchor="w", padx=18, pady=4)

        self.sw_wifi = ctk.CTkSwitch(c_rad, text="Disable background Wi-Fi scanning (wifi_scan_always_enabled = 0)", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.sw_wifi.pack(anchor="w", padx=18, pady=4)

        self.sw_location = ctk.CTkSwitch(c_rad, text="Turn off Location services on e-reader (location_mode = 0)", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.sw_location.pack(anchor="w", padx=18, pady=(4, 16))

        # Card 3: Display Clarity
        c_disp = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        c_disp.pack(fill="x", pady=8)

        lbl_disp_t = ctk.CTkLabel(c_disp, text="Display & Reading Clarity", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.COLOR_CYAN)
        lbl_disp_t.pack(anchor="w", padx=18, pady=(16, 12))

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

        # Action Buttons
        set_btn_row = ctk.CTkFrame(page, fg_color="transparent")
        set_btn_row.pack(anchor="w", pady=12)

        ctk.CTkButton(set_btn_row, text="💾 Apply System Settings", height=38, corner_radius=8, fg_color=self.COLOR_BLUE, hover_color="#2563EB", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=self._action_apply_settings).pack(side="left", padx=(0, 8))
        ctk.CTkButton(set_btn_row, text="📖 Query Device Settings", height=38, corner_radius=8, fg_color="#283042", hover_color="#37435C", command=self._action_query_settings).pack(side="left")

        return page

    # =========================================================================
    # PAGE 6: HARDWARE & LOGS
    # =========================================================================
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

        # Specs Card
        specs_card = ctk.CTkFrame(top_split, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        specs_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        lbl_sc_t = ctk.CTkLabel(specs_card, text="Hardware & Platform Specifications", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=self.COLOR_CYAN)
        lbl_sc_t.pack(anchor="w", padx=16, pady=(14, 6))

        self.lbl_specs = ctk.CTkLabel(specs_card, text="Probing device specs...", font=ctk.CTkFont(family="Consolas", size=11), text_color="#E2E8F0", justify="left")
        self.lbl_specs.pack(anchor="w", padx=16, pady=(0, 14))

        # Power Controls Card
        pwr_card = ctk.CTkFrame(top_split, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        pwr_card.grid(row=0, column=1, sticky="nsew")

        lbl_pwr_t = ctk.CTkLabel(pwr_card, text="Device Power Controls", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=self.COLOR_CYAN)
        lbl_pwr_t.pack(anchor="w", padx=16, pady=(14, 8))

        ctk.CTkButton(pwr_card, text="⚡ Reboot System", height=32, corner_radius=6, fg_color="#283042", hover_color="#37435C", command=lambda: self.ops.reboot_device("system")).pack(fill="x", padx=16, pady=2)
        ctk.CTkButton(pwr_card, text="⚡ Reboot Recovery", height=32, corner_radius=6, fg_color="#283042", hover_color="#37435C", command=lambda: self.ops.reboot_device("recovery")).pack(fill="x", padx=16, pady=2)
        ctk.CTkButton(pwr_card, text="⚡ Reboot Fastboot", height=32, corner_radius=6, fg_color="#283042", hover_color="#37435C", command=lambda: self.ops.reboot_device("bootloader")).pack(fill="x", padx=16, pady=2)
        ctk.CTkButton(pwr_card, text="🔄 Restart SystemUI", height=32, corner_radius=6, fg_color="#283042", hover_color="#37435C", command=lambda: self.ops.reboot_device("systemui")).pack(fill="x", padx=16, pady=(2, 14))

        # Log Console Box
        log_card = ctk.CTkFrame(page, corner_radius=12, fg_color=self.COLOR_CARD, border_width=1, border_color=self.COLOR_CARD_BORDER)
        log_card.grid(row=3, column=0, sticky="nsew")
        page.grid_rowconfigure(3, weight=1)

        log_head = ctk.CTkFrame(log_card, fg_color="transparent")
        log_head.pack(fill="x", padx=16, pady=(10, 4))

        ctk.CTkLabel(log_head, text="Real-time Execution Console", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=self.COLOR_CYAN).pack(side="left")
        ctk.CTkButton(log_head, text="Clear Console", width=90, height=26, corner_radius=6, fg_color="#283042", hover_color="#37435C", command=lambda: self.txt_log.delete("1.0", "end")).pack(side="right")

        self.txt_log = ctk.CTkTextbox(log_card, corner_radius=8, fg_color="#06080F", text_color=self.COLOR_CYAN, font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_log.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        return page

    # =========================================================================
    # LOGGING & DEVICE PROBING
    # =========================================================================
    def append_log(self, text):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        msg = f"[{now}] {text}\n"
        def _insert():
            self.txt_log.insert("end", msg)
            self.txt_log.see("end")
        self.after(0, _insert)

    def refresh_device_status_async(self):
        self.lbl_status_badge.configure(text="PROBING...", fg_color="#283042", text_color=self.COLOR_CYAN)
        threading.Thread(target=self._worker_probe_device, daemon=True).start()

    def _worker_probe_device(self):
        info = self.adb.get_connected_device_info()
        self.after(0, lambda: self._update_ui_device_status(info))

    def _update_ui_device_status(self, info):
        if info["connected"]:
            if info["mode"] == "adb":
                root_status = "Magisk Rooted" if info["rooted"] else "Unrooted"
                self.lbl_status_badge.configure(
                    text=f"CONNECTED ({root_status.upper()})",
                    fg_color="#064E3B" if info["rooted"] else "#075985",
                    text_color="#FFFFFF"
                )
                self.lbl_device_title.configure(text=f"{info['model']} ({info['manufacturer']})")
                self.lbl_device_details.configure(text=f"Slot: {info['boot_slot']} • Battery: {info['battery_level']}")
            elif info["mode"] == "fastboot":
                self.lbl_status_badge.configure(text="FASTBOOT MODE", fg_color="#78350F", text_color="#FFFFFF")
                self.lbl_device_title.configure(text="Fastboot Device")
                self.lbl_device_details.configure(text=f"Serial: {info['serial']}")

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
            )
            self.lbl_specs.configure(text=specs_text)
            self._action_refresh_debloat_list_async()
            self._action_query_settings_silent()
        else:
            self.lbl_status_badge.configure(text="DISCONNECTED", fg_color="#7F1D1D", text_color="#FFFFFF")
            self.lbl_device_title.configure(text="No Device Detected")
            self.lbl_device_details.configure(text="Connect via USB with Debugging")
            self.lbl_specs.configure(text="No device connected.")

    # =========================================================================
    # ACTIONS: SCREENSAVER & MEDIA
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

        # Generate live CTkImage preview
        if HAS_PILLOW:
            try:
                pil_img = Image.open(f)
                pil_thumb = pil_img.copy()
                pil_thumb.thumbnail((120, 162), Image.Resampling.LANCZOS)
                if self.sw_grayscale.get():
                    pil_thumb = pil_thumb.convert("L")
                self._ctk_preview_image = ctk.CTkImage(light_image=pil_thumb, dark_image=pil_thumb, size=pil_thumb.size)
                self.lbl_image_preview.configure(image=self._ctk_preview_image, text="")
            except Exception as e:
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
            ok, msg = self.ops.backup_stock_partitions(slot=slot)
            if ok:
                messagebox.showinfo("Backup Success", msg)
            else:
                messagebox.showerror("Backup Failed", msg)
        threading.Thread(target=_run, daemon=True).start()

    def _action_install_magisk(self):
        assets_apk = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "magisk.apk")
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
        assets_zip = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "c69hd-wake.zip")
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
            self.after(0, lambda: self.lbl_active_mapping.configure(text=txt))
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
                self.after(0, lambda b=btn, p=pkg: b.configure(text="Enable", fg_color="#283042", hover_color="#37435C", command=lambda: self._toggle_package(p, False)))
            else:
                self.after(0, lambda b=btn, p=pkg: b.configure(text="Disable", fg_color=self.COLOR_RED, hover_color="#DC2626", command=lambda: self._toggle_package(p, True)))

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
            self.after(0, lambda: self._update_settings_ui(s, show_dialog=False))
        threading.Thread(target=_run, daemon=True).start()

    def _action_query_settings(self):
        def _run():
            s = self.ops.get_system_settings()
            self.after(0, lambda: self._update_settings_ui(s, show_dialog=True))
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

        if show_dialog:
            messagebox.showinfo("Settings Queried", f"Current Device Values:\nTimeout: {s.get('screen_off_timeout')}ms\nFont: {s.get('font_scale')}\nDensity: {s.get('density')}")
