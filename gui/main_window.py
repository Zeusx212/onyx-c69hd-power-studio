"""
Main GUI window for Onyx Boox C69HD Customization Tool.
Provides a modern dark-slate aesthetic, intuitive cards, real-time device probing,
personalization studio (screensavers & boot animation), debloating, and button remapping.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import datetime
import os

from core.device_ops import BUTTON_ACTIONS, DEBLOAT_CATALOG, HAS_PILLOW

if HAS_PILLOW:
    from PIL import Image, ImageTk

class MainWindow(tk.Tk):
    def __init__(self, adb_manager, device_ops):
        super().__init__()
        self.adb = adb_manager
        self.ops = device_ops
        self.adb.log_callback = self.append_log

        self.title("Onyx Boox C69HD Customizer • Faust 5 OEM Suite")
        self.geometry("1020x760")
        self.minsize(920, 680)

        # Cache image thumbnails
        self._preview_image = None
        self._selected_image_path = None
        self._selected_bootanim_path = None

        self._configure_modern_theme()
        self._build_header()
        self._build_notebook()
        self._build_footer()

        # Initial device probe
        self.refresh_device_status_async()

    def _configure_modern_theme(self):
        self.configure(bg="#0B0F19")
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Dark Slate Palette
        self.BG_MAIN = "#0B0F19"
        self.BG_CARD = "#161E2E"
        self.BG_HEADER = "#111827"
        self.BORDER_COLOR = "#293548"
        self.TEXT_PRIMARY = "#F8FAFC"
        self.TEXT_SECONDARY = "#94A3B8"
        self.ACCENT_CYAN = "#38BDF8"
        self.ACCENT_BLUE = "#2563EB"
        self.ACCENT_GREEN = "#10B981"
        self.ACCENT_RED = "#EF4444"
        self.ACCENT_AMBER = "#F59E0B"

        self.style.configure(".", font=("Segoe UI", 9), background=self.BG_MAIN, foreground=self.TEXT_PRIMARY)
        
        # Header Styles
        self.style.configure("Header.TFrame", background=self.BG_HEADER)
        self.style.configure("Header.TLabel", background=self.BG_HEADER, foreground=self.TEXT_PRIMARY, font=("Segoe UI", 12, "bold"))
        self.style.configure("HeaderSub.TLabel", background=self.BG_HEADER, foreground=self.TEXT_SECONDARY, font=("Segoe UI", 9))
        self.style.configure("StatusPill.TLabel", background="#1E293B", foreground=self.ACCENT_CYAN, font=("Segoe UI", 9, "bold"), padding=(8, 4))

        # Notebook (Tabs)
        self.style.configure("TNotebook", background=self.BG_MAIN, borderwidth=0)
        self.style.configure("TNotebook.Tab", background="#1E293B", foreground=self.TEXT_SECONDARY, font=("Segoe UI", 9, "bold"), padding=(14, 8))
        self.style.map("TNotebook.Tab",
            background=[("selected", self.BG_CARD), ("active", "#283548")],
            foreground=[("selected", self.ACCENT_CYAN), ("active", self.TEXT_PRIMARY)]
        )

        # Cards / LabelFrames
        self.style.configure("Card.TLabelframe", background=self.BG_CARD, relief="solid", borderwidth=1, bordercolor=self.BORDER_COLOR)
        self.style.configure("Card.TLabelframe.Label", background=self.BG_CARD, foreground=self.ACCENT_CYAN, font=("Segoe UI", 10, "bold"))
        self.style.configure("CardInner.TFrame", background=self.BG_CARD)

        # Buttons
        self.style.configure("Primary.TButton", background=self.ACCENT_BLUE, foreground="#FFFFFF", font=("Segoe UI", 9, "bold"), padding=(10, 6))
        self.style.map("Primary.TButton", background=[("active", "#1D4ED8"), ("disabled", "#334155")])

        self.style.configure("Success.TButton", background=self.ACCENT_GREEN, foreground="#FFFFFF", font=("Segoe UI", 9, "bold"), padding=(10, 6))
        self.style.map("Success.TButton", background=[("active", "#059669")])

        self.style.configure("Action.TButton", background="#334155", foreground="#F8FAFC", font=("Segoe UI", 9), padding=(8, 5))
        self.style.map("Action.TButton", background=[("active", "#475569")])

        self.style.configure("Danger.TButton", background=self.ACCENT_RED, foreground="#FFFFFF", font=("Segoe UI", 9, "bold"), padding=(8, 5))
        self.style.map("Danger.TButton", background=[("active", "#DC2626")])

    def _build_header(self):
        header_frame = ttk.Frame(self, style="Header.TFrame", padding=(20, 14))
        header_frame.pack(fill="x", side="top")

        left_box = ttk.Frame(header_frame, style="Header.TFrame")
        left_box.pack(side="left", fill="y")

        self.lbl_title = ttk.Label(left_box, text="Onyx Boox C69HD Customization Suite", style="Header.TLabel")
        self.lbl_title.pack(anchor="w")

        self.lbl_sub = ttk.Label(left_box, text="Faust 5 OEM Variant • Probing ADB connection...", style="HeaderSub.TLabel")
        self.lbl_sub.pack(anchor="w", pady=(2, 0))

        right_box = ttk.Frame(header_frame, style="Header.TFrame")
        right_box.pack(side="right", fill="y")

        self.lbl_status_pill = ttk.Label(right_box, text="PROBING...", style="StatusPill.TLabel")
        self.lbl_status_pill.pack(side="left", padx=(0, 10))

        self.btn_refresh = ttk.Button(right_box, text="↻ Refresh Status", style="Action.TButton", command=self.refresh_device_status_async)
        self.btn_refresh.pack(side="left")

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=10)

        # Tab 1: Root & Partitions
        self.tab_root = ttk.Frame(self.notebook, style="CardInner.TFrame", padding=14)
        self.notebook.add(self.tab_root, text="  🛡️ Root & Partitions  ")
        self._build_tab_root()

        # Tab 2: Button Remap
        self.tab_button = ttk.Frame(self.notebook, style="CardInner.TFrame", padding=14)
        self.notebook.add(self.tab_button, text="  🔘 Button Remapper  ")
        self._build_tab_button()

        # Tab 3: Screensaver & Boot Animation (NEW!)
        self.tab_media = ttk.Frame(self.notebook, style="CardInner.TFrame", padding=14)
        self.notebook.add(self.tab_media, text="  🎨 Screensaver & Boot Media  ")
        self._build_tab_media()

        # Tab 4: Debloating
        self.tab_debloat = ttk.Frame(self.notebook, style="CardInner.TFrame", padding=14)
        self.notebook.add(self.tab_debloat, text="  🧹 Debloater  ")
        self._build_tab_debloat()

        # Tab 5: Device Settings
        self.tab_settings = ttk.Frame(self.notebook, style="CardInner.TFrame", padding=14)
        self.notebook.add(self.tab_settings, text="  ⚙️ Device Settings  ")
        self._build_tab_settings()

        # Tab 6: Device Info & Shell Logs
        self.tab_logs = ttk.Frame(self.notebook, style="CardInner.TFrame", padding=14)
        self.notebook.add(self.tab_logs, text="  📊 Device Info & Logs  ")
        self._build_tab_logs()

    def _build_footer(self):
        footer = ttk.Frame(self, padding=(16, 6))
        footer.pack(fill="x", side="bottom")

        self.lbl_footer = ttk.Label(
            footer,
            text="Onyx Boox C69HD (Snapdragon 662 • Carta 6\" 758x1024) | Zeusx212/onyx-c69hd-root • Zeusx212/onyx-c69hd-button-remap | Credits: @7sarus",
            font=("Segoe UI", 8),
            foreground=self.TEXT_SECONDARY
        )
        self.lbl_footer.pack(side="left")

    # =========================================================================
    # TAB 1: ROOT & PARTITIONS
    # =========================================================================
    def _build_tab_root(self):
        # Partition Backup Card
        card_backup = ttk.LabelFrame(self.tab_root, text="1. Stock Partition Backup", style="Card.TLabelframe", padding=14)
        card_backup.pack(fill="x", pady=6)

        ttk.Label(
            card_backup,
            text="Dumps current active boot (boot_a / boot_b) and vbmeta partitions into './backups/'.\n"
                 "Recommended before any fastboot operations or flashing custom images.",
            style="HeaderSub.TLabel"
        ).pack(anchor="w", pady=(0, 8))

        self.btn_backup = ttk.Button(card_backup, text="📥 Backup Active Stock Partitions", style="Primary.TButton", command=self._action_backup_partitions)
        self.btn_backup.pack(anchor="w")

        # Magisk Root Card
        card_magisk = ttk.LabelFrame(self.tab_root, text="2. Magisk Root Installation & Fastboot Flashing", style="Card.TLabelframe", padding=14)
        card_magisk.pack(fill="x", pady=6)

        ttk.Label(
            card_magisk,
            text="Step-by-step root procedure:\n"
                 "• Step 1: Push & Install Magisk APK to device (bundled in assets/).\n"
                 "• Step 2: Patch your dumped stock_boot.img in Magisk app.\n"
                 "• Step 3: Reboot device to Fastboot and flash patched image.",
            style="HeaderSub.TLabel"
        ).pack(anchor="w", pady=(0, 8))

        m_box = ttk.Frame(card_magisk, style="CardInner.TFrame")
        m_box.pack(anchor="w", pady=4)

        ttk.Button(m_box, text="📦 1. Install Magisk APK", style="Action.TButton", command=self._action_install_magisk).pack(side="left", padx=(0, 8))
        ttk.Button(m_box, text="⚡ 2. Reboot to Fastboot", style="Action.TButton", command=lambda: self.ops.reboot_device("bootloader")).pack(side="left", padx=(0, 8))
        ttk.Button(m_box, text="🚀 3. Flash Patched Boot Image...", style="Primary.TButton", command=self._action_flash_patched_boot).pack(side="left", padx=(0, 8))
        ttk.Button(m_box, text="🔄 Restore Stock Boot Image...", style="Danger.TButton", command=self._action_restore_stock_boot).pack(side="left")

        # Hardware Wake Module Card
        card_wake = ttk.LabelFrame(self.tab_root, text="3. Hardware Physical Button Wake (Magisk Module)", style="Card.TLabelframe", padding=14)
        card_wake.pack(fill="x", pady=6)

        ttk.Label(
            card_wake,
            text="On Onyx Boox C69HD, only the top power button wakes the device from sleep.\n"
                 "This Magisk module patches gpio-keys.kl so pressing the front center button or side keys instantly wakes the e-reader.",
            style="HeaderSub.TLabel"
        ).pack(anchor="w", pady=(0, 8))

        ttk.Button(card_wake, text="⚡ Install 'c69hd-wake' Magisk Module", style="Success.TButton", command=self._action_install_wake_module).pack(anchor="w")

    # =========================================================================
    # TAB 2: BUTTON REMAPPING
    # =========================================================================
    def _build_tab_button(self):
        card_info = ttk.LabelFrame(self.tab_button, text="C69HD Front Hardware Button Context", style="Card.TLabelframe", padding=14)
        card_info.pack(fill="x", pady=6)

        ttk.Label(
            card_info,
            text="The Onyx Boox C69HD has a physical center button (KEYCODE_BACK).\n"
                 "• Factory Default HOLD: Toggles frontlight/backlight — BUT the C69HD has NO frontlight hardware, so it does nothing!\n"
                 "• Recommended Remap: Hold -> Recent Apps (App Switcher) | Tap -> Standard Back.",
            style="HeaderSub.TLabel"
        ).pack(anchor="w")

        card_remap = ttk.LabelFrame(self.tab_button, text="Configure Center Physical Button", style="Card.TLabelframe", padding=16)
        card_remap.pack(fill="x", pady=6)

        grid_frame = ttk.Frame(card_remap, style="CardInner.TFrame")
        grid_frame.pack(fill="x", pady=4)

        ttk.Label(grid_frame, text="Long-Press (Hold) Action:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=8)
        self.combo_long_press = ttk.Combobox(grid_frame, width=54, state="readonly")
        self.combo_long_press["values"] = [f"{v} [{k}]" if k else f"{v} [Standard Back]" for k, v in BUTTON_ACTIONS.items()]
        self.combo_long_press.current(0)
        self.combo_long_press.grid(row=0, column=1, padx=12, pady=8, sticky="w")

        ttk.Label(grid_frame, text="Short-Press (Single Tap) Action:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=8)
        self.combo_short_press = ttk.Combobox(grid_frame, width=54, state="readonly")
        self.combo_short_press["values"] = [
            "Standard Back Key Event [Recommended] []",
            "Recent Apps / App Switcher [KEYCODE_APP_SWITCH]",
            "Full Screen E-Ink Refresh (Clears Ghosting) [fullRefreshScreen]",
            "Take Screenshot [screenshot]",
            "Return to Home Screen [back_to_home]"
        ]
        self.combo_short_press.current(0)
        self.combo_short_press.grid(row=1, column=1, padx=12, pady=8, sticky="w")

        action_box = ttk.Frame(card_remap, style="CardInner.TFrame")
        action_box.pack(anchor="w", pady=(14, 4))

        ttk.Button(action_box, text="💾 Apply Button Mapping", style="Primary.TButton", command=self._action_apply_button_remap).pack(side="left", padx=(0, 8))
        ttk.Button(action_box, text="📖 Query Device Mapping", style="Action.TButton", command=self._action_read_button_remap).pack(side="left", padx=(0, 8))
        ttk.Button(action_box, text="🔄 Reset to Factory Default", style="Danger.TButton", command=self._action_reset_button_remap).pack(side="left")

        # Active configuration card
        card_active = ttk.LabelFrame(self.tab_button, text="Active Mapping on Connected Device", style="Card.TLabelframe", padding=12)
        card_active.pack(fill="x", pady=6)

        self.lbl_active_mapping = ttk.Label(card_active, text="Press 'Query Device Mapping' to inspect...", font=("Consolas", 9), foreground=self.ACCENT_CYAN)
        self.lbl_active_mapping.pack(anchor="w")

    # =========================================================================
    # TAB 3: SCREENSAVER & BOOT MEDIA (NEW!)
    # =========================================================================
    def _build_tab_media(self):
        # 1. Screensaver & Standby Card
        card_ss = ttk.LabelFrame(self.tab_media, text="1. Custom Screensaver & Standby Sleep Screens", style="Card.TLabelframe", padding=14)
        card_ss.pack(fill="x", pady=6)

        split_ss = ttk.Frame(card_ss, style="CardInner.TFrame")
        split_ss.pack(fill="x")

        # Left Column: Image Controls
        left_ss = ttk.Frame(split_ss, style="CardInner.TFrame")
        left_ss.pack(side="left", fill="both", expand=True)

        ttk.Label(
            left_ss,
            text="Select any image (.png, .jpg, .webp). The tool will automatically scale/crop it to\n"
                 "758 × 1024 (native C69HD Carta resolution) and optimize contrast for E-Ink.",
            style="HeaderSub.TLabel"
        ).pack(anchor="w", pady=(0, 6))

        file_picker_row = ttk.Frame(left_ss, style="CardInner.TFrame")
        file_picker_row.pack(anchor="w", pady=4)

        ttk.Button(file_picker_row, text="📁 Choose Image...", style="Action.TButton", command=self._action_choose_screensaver_file).pack(side="left", padx=(0, 8))
        self.lbl_chosen_image = ttk.Label(file_picker_row, text="No image selected", foreground=self.TEXT_SECONDARY)
        self.lbl_chosen_image.pack(side="left")

        # Options
        self.var_auto_grayscale = tk.IntVar(value=1)
        ttk.Checkbutton(left_ss, text="Convert to high-contrast E-Ink grayscale (LANCZOS 758x1024)", variable=self.var_auto_grayscale).pack(anchor="w", pady=4)

        # Target selector
        target_row = ttk.Frame(left_ss, style="CardInner.TFrame")
        target_row.pack(anchor="w", pady=4)
        ttk.Label(target_row, text="Target Location:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))

        self.var_ss_target = tk.StringVar(value="user")
        ttk.Radiobutton(target_row, text="User Gallery (/sdcard/Pictures/Screensaver)", variable=self.var_ss_target, value="user").pack(side="left", padx=4)
        ttk.Radiobutton(target_row, text="System Standby (standby-1.png)", variable=self.var_ss_target, value="standby").pack(side="left", padx=4)
        ttk.Radiobutton(target_row, text="System Shutdown (shutdown-default.png)", variable=self.var_ss_target, value="shutdown").pack(side="left", padx=4)

        ss_btn_row = ttk.Frame(left_ss, style="CardInner.TFrame")
        ss_btn_row.pack(anchor="w", pady=(10, 4))

        ttk.Button(ss_btn_row, text="🚀 Push Screensaver to Device", style="Primary.TButton", command=self._action_push_screensaver).pack(side="left", padx=(0, 8))
        ttk.Button(ss_btn_row, text="📱 Open Wallpaper Settings on Device", style="Action.TButton", command=self.ops.open_device_screensaver_settings).pack(side="left", padx=(0, 8))
        ttk.Button(ss_btn_row, text="💤 Test Sleep Screen (Lock Device)", style="Action.TButton", command=lambda: self.ops.reboot_device("sleep")).pack(side="left")

        # Right Column: Live Thumbnail Preview Box
        right_ss = ttk.Frame(split_ss, style="CardInner.TFrame", padding=(14, 0))
        right_ss.pack(side="right")

        ttk.Label(right_ss, text="Preview (758x1024)", font=("Segoe UI", 8, "bold"), foreground=self.ACCENT_CYAN).pack(anchor="center")
        self.lbl_image_preview = ttk.Label(right_ss, background="#0F172A", text="No Preview", foreground=self.TEXT_SECONDARY, relief="solid", borderwidth=1, anchor="center")
        self.lbl_image_preview.pack(pady=4)
        self.lbl_image_preview.configure(width=16)

        # 2. Boot Animation Card
        card_boot = ttk.LabelFrame(self.tab_media, text="2. Custom Boot Animation", style="Card.TLabelframe", padding=14)
        card_boot.pack(fill="x", pady=6)

        ttk.Label(
            card_boot,
            text="Install custom bootanimation.zip systemlessly via Magisk media overlay.\n"
                 "You can select an existing bootanimation.zip or a folder of PNG animation frames.",
            style="HeaderSub.TLabel"
        ).pack(anchor="w", pady=(0, 8))

        b_file_row = ttk.Frame(card_boot, style="CardInner.TFrame")
        b_file_row.pack(anchor="w", pady=4)

        ttk.Button(b_file_row, text="📁 Select bootanimation.zip...", style="Action.TButton", command=self._action_choose_bootanim_zip).pack(side="left", padx=(0, 8))
        ttk.Button(b_file_row, text="🖼️ Create from Folder of Frames...", style="Action.TButton", command=self._action_create_bootanim_from_folder).pack(side="left", padx=(0, 8))
        self.lbl_chosen_bootanim = ttk.Label(b_file_row, text="No animation selected", foreground=self.TEXT_SECONDARY)
        self.lbl_chosen_bootanim.pack(side="left")

        b_btn_row = ttk.Frame(card_boot, style="CardInner.TFrame")
        b_btn_row.pack(anchor="w", pady=(10, 4))

        ttk.Button(b_btn_row, text="⚡ Install Boot Animation (Magisk)", style="Primary.TButton", command=self._action_install_bootanim).pack(side="left", padx=(0, 8))
        ttk.Button(b_btn_row, text="▶️ Live Preview on Device Screen", style="Success.TButton", command=lambda: threading.Thread(target=self.ops.preview_bootanimation_on_device, daemon=True).start()).pack(side="left", padx=(0, 8))
        ttk.Button(b_btn_row, text="🔄 Restore Stock Boot Animation", style="Danger.TButton", command=self._action_restore_stock_bootanim).pack(side="left")

    # =========================================================================
    # TAB 4: DEBLOATING
    # =========================================================================
    def _build_tab_debloat(self):
        top_ctrl = ttk.Frame(self.tab_debloat, style="CardInner.TFrame")
        top_ctrl.pack(fill="x", pady=(0, 10))

        ttk.Button(top_ctrl, text="🛡️ 1-Click Safe Debloat (Cellular & SVA)", style="Primary.TButton", command=self._action_safe_debloat).pack(side="left", padx=(0, 8))
        ttk.Button(top_ctrl, text="🔄 Re-enable All Catalog Packages", style="Action.TButton", command=self._action_enable_all_debloated).pack(side="left", padx=(0, 8))
        ttk.Button(top_ctrl, text="↻ Refresh List", style="Action.TButton", command=self._action_refresh_debloat_list).pack(side="left", padx=(0, 14))

        # Filter box
        ttk.Label(top_ctrl, text="🔍 Filter:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self.entry_filter = ttk.Entry(top_ctrl, width=24)
        self.entry_filter.pack(side="left")
        self.entry_filter.bind("<KeyRelease>", lambda e: self._filter_debloat_items())

        # Scrollable container
        container = ttk.Frame(self.tab_debloat, style="CardInner.TFrame")
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg=self.BG_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.debloat_inner = ttk.Frame(canvas, style="CardInner.TFrame", padding=10)

        self.debloat_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.debloat_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.pkg_widgets = {}
        self._populate_debloat_items()

        # Custom Package Entry Box
        custom_box = ttk.LabelFrame(self.tab_debloat, text="Manual Package Control", style="Card.TLabelframe", padding=10)
        custom_box.pack(fill="x", pady=(10, 0))

        ttk.Label(custom_box, text="Package Identifier:").pack(side="left", padx=4)
        self.entry_custom_pkg = ttk.Entry(custom_box, width=38)
        self.entry_custom_pkg.pack(side="left", padx=4)

        ttk.Button(custom_box, text="Disable Package", style="Danger.TButton", command=self._action_custom_disable).pack(side="left", padx=4)
        ttk.Button(custom_box, text="Enable Package", style="Action.TButton", command=self._action_custom_enable).pack(side="left", padx=4)

    def _populate_debloat_items(self):
        for widget in self.debloat_inner.winfo_children():
            widget.destroy()

        self.pkg_widgets.clear()

        for cat in DEBLOAT_CATALOG:
            cat_title = cat["category"]
            lbl_cat = ttk.Label(self.debloat_inner, text=cat_title, font=("Segoe UI", 10, "bold"), foreground=self.ACCENT_CYAN)
            lbl_cat.pack(anchor="w", pady=(12, 4))

            for pkg, desc in cat["packages"]:
                row = ttk.Frame(self.debloat_inner, style="CardInner.TFrame")
                row.pack(fill="x", pady=2)

                lbl_name = ttk.Label(row, text=pkg, font=("Consolas", 9, "bold"), width=38, anchor="w", foreground=self.TEXT_PRIMARY)
                lbl_name.pack(side="left", padx=4)

                lbl_desc = ttk.Label(row, text=desc, font=("Segoe UI", 8), foreground=self.TEXT_SECONDARY)
                lbl_desc.pack(side="left", padx=4)

                btn_toggle = ttk.Button(row, text="Checking...", width=11)
                btn_toggle.pack(side="right", padx=6)

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
                data["row"].pack(fill="x", pady=2)
            else:
                data["row"].pack_forget()

    # =========================================================================
    # TAB 5: DEVICE SETTINGS
    # =========================================================================
    def _build_tab_settings(self):
        # Screen Timeout Card
        card_timeout = ttk.LabelFrame(self.tab_settings, text="Screen Timeout (Fix Infinite 24.8-Day Sleep Bug)", style="Card.TLabelframe", padding=14)
        card_timeout.pack(fill="x", pady=6)

        self.lbl_timeout_alert = ttk.Label(
            card_timeout,
            text="⚠️ Factory C69HD Bug: Timeout often defaults to 2147483647 ms (24.8 days) causing battery drain!\n"
                 "Set to 5 Minutes (Recommended) so the device automatically enters deep sleep.",
            foreground=self.ACCENT_AMBER
        )
        self.lbl_timeout_alert.pack(anchor="w", pady=(0, 8))

        to_box = ttk.Frame(card_timeout, style="CardInner.TFrame")
        to_box.pack(anchor="w")

        ttk.Label(to_box, text="Select Screen Timeout:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))
        self.combo_timeout = ttk.Combobox(to_box, width=34, state="readonly")
        self.combo_timeout["values"] = [
            "1 Minute (60000 ms)",
            "2 Minutes (120000 ms)",
            "5 Minutes [Recommended] (300000 ms)",
            "10 Minutes (600000 ms)",
            "30 Minutes (1800000 ms)",
            "Never Sleep [Buggy default] (2147483647 ms)"
        ]
        self.combo_timeout.current(2)
        self.combo_timeout.pack(side="left", padx=(0, 10))

        ttk.Button(to_box, text="⚡ Fix to 5 Minutes Now", style="Success.TButton", command=self._action_fix_timeout_preset).pack(side="left")

        # Battery & Privacy Card
        card_telemetry = ttk.LabelFrame(self.tab_settings, text="Battery & Privacy Optimizations", style="Card.TLabelframe", padding=14)
        card_telemetry.pack(fill="x", pady=6)

        self.var_telemetry = tk.IntVar(value=0)
        ttk.Checkbutton(card_telemetry, text="Disable background error & crash reporting (send_action_app_error = 0)", variable=self.var_telemetry).pack(anchor="w", pady=3)

        self.var_ble_scan = tk.IntVar(value=0)
        ttk.Checkbutton(card_telemetry, text="Disable background Bluetooth LE scanning (ble_scan_always_enabled = 0)", variable=self.var_ble_scan).pack(anchor="w", pady=3)

        self.var_wifi_scan = tk.IntVar(value=0)
        ttk.Checkbutton(card_telemetry, text="Disable background Wi-Fi scanning (wifi_scan_always_enabled = 0)", variable=self.var_wifi_scan).pack(anchor="w", pady=3)

        self.var_location = tk.IntVar(value=0)
        ttk.Checkbutton(card_telemetry, text="Turn off Location services on e-reader (location_mode = 0)", variable=self.var_location).pack(anchor="w", pady=3)

        # Display Card
        card_display = ttk.LabelFrame(self.tab_settings, text="Display & Reading Clarity", style="Card.TLabelframe", padding=14)
        card_display.pack(fill="x", pady=6)

        disp_grid = ttk.Frame(card_display, style="CardInner.TFrame")
        disp_grid.pack(anchor="w")

        ttk.Label(disp_grid, text="Font Scale:").grid(row=0, column=0, sticky="w", pady=4)
        self.combo_font = ttk.Combobox(disp_grid, width=22, state="readonly")
        self.combo_font["values"] = ["0.85 (Small)", "1.00 (Standard)", "1.05 (Optimized)", "1.10 (Large)", "1.15 (Extra Large)"]
        self.combo_font.current(2)
        self.combo_font.grid(row=0, column=1, padx=8, pady=4)

        ttk.Label(disp_grid, text="Display Density (DPI):").grid(row=1, column=0, sticky="w", pady=4)
        self.combo_dpi = ttk.Combobox(disp_grid, width=22, state="readonly")
        self.combo_dpi["values"] = ["Reset to 212 DPI (Default)", "200 DPI", "225 DPI", "240 DPI"]
        self.combo_dpi.current(0)
        self.combo_dpi.grid(row=1, column=1, padx=8, pady=4)

        self.var_high_contrast = tk.IntVar(value=0)
        ttk.Checkbutton(disp_grid, text="High Contrast Text (high_text_contrast_enabled)", variable=self.var_high_contrast).grid(row=2, column=0, columnspan=2, sticky="w", pady=4)

        # Actions
        set_btn_box = ttk.Frame(self.tab_settings, style="CardInner.TFrame")
        set_btn_box.pack(anchor="w", pady=12)

        ttk.Button(set_btn_box, text="💾 Apply System Settings", style="Primary.TButton", command=self._action_apply_settings).pack(side="left", padx=(0, 8))
        ttk.Button(set_btn_box, text="📖 Query Device Settings", style="Action.TButton", command=self._action_query_settings).pack(side="left")

    # =========================================================================
    # TAB 6: DEVICE INFO & LOGS
    # =========================================================================
    def _build_tab_logs(self):
        top_split = ttk.Frame(self.tab_logs, style="CardInner.TFrame")
        top_split.pack(fill="x", pady=(0, 8))

        # Device Specs Box
        specs_box = ttk.LabelFrame(top_split, text="Hardware & Platform Specifications", style="Card.TLabelframe", padding=12)
        specs_box.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.lbl_specs = ttk.Label(specs_box, text="Probing device specs...", font=("Consolas", 9), justify="left")
        self.lbl_specs.pack(anchor="w")

        # Power Controls Box
        reboot_box = ttk.LabelFrame(top_split, text="Power & State Controls", style="Card.TLabelframe", padding=12)
        reboot_box.pack(side="right", fill="both")

        ttk.Button(reboot_box, text="⚡ Reboot System", style="Action.TButton", command=lambda: self.ops.reboot_device("system")).pack(fill="x", pady=2)
        ttk.Button(reboot_box, text="⚡ Reboot Recovery", style="Action.TButton", command=lambda: self.ops.reboot_device("recovery")).pack(fill="x", pady=2)
        ttk.Button(reboot_box, text="⚡ Reboot Fastboot", style="Action.TButton", command=lambda: self.ops.reboot_device("bootloader")).pack(fill="x", pady=2)
        ttk.Button(reboot_box, text="🔄 Restart SystemUI", style="Action.TButton", command=lambda: self.ops.reboot_device("systemui")).pack(fill="x", pady=2)

        # Log Window
        ttk.Label(self.tab_logs, text="ADB Command Output & Real-time Console Log:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 2))

        self.txt_log = scrolledtext.ScrolledText(self.tab_logs, wrap="word", bg="#050811", fg=self.ACCENT_CYAN, font=("Consolas", 9), insertbackground=self.ACCENT_CYAN)
        self.txt_log.pack(fill="both", expand=True, pady=4)

        log_actions = ttk.Frame(self.tab_logs, style="CardInner.TFrame")
        log_actions.pack(fill="x")
        ttk.Button(log_actions, text="Clear Log Console", style="Action.TButton", command=lambda: self.txt_log.delete("1.0", "end")).pack(side="left", padx=4)

    # =========================================================================
    # LOGGING & DEVICE STATUS
    # =========================================================================
    def append_log(self, text):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        msg = f"[{now}] {text}\n"
        def _insert():
            self.txt_log.insert("end", msg)
            self.txt_log.see("end")
        self.after(0, _insert)

    def refresh_device_status_async(self):
        self.lbl_status_pill.configure(text="PROBING...", background="#1E293B", foreground=self.ACCENT_CYAN)
        threading.Thread(target=self._worker_probe_device, daemon=True).start()

    def _worker_probe_device(self):
        info = self.adb.get_connected_device_info()
        self.after(0, lambda: self._update_ui_device_status(info))

    def _update_ui_device_status(self, info):
        if info["connected"]:
            if info["mode"] == "adb":
                root_status = "Magisk Rooted" if info["rooted"] else "Unrooted"
                self.lbl_status_pill.configure(
                    text=f"CONNECTED ({root_status.upper()})",
                    background="#064E3B" if info["rooted"] else "#075985",
                    foreground="#FFFFFF"
                )
                self.lbl_sub.configure(
                    text=f"Model: {info['model']} ({info['manufacturer']}) • Slot: {info['boot_slot']} • Battery: {info['battery_level']}"
                )
            elif info["mode"] == "fastboot":
                self.lbl_status_pill.configure(text="FASTBOOT MODE", background="#78350F", foreground="#FFFFFF")
                self.lbl_sub.configure(text=f"Device in Bootloader / Fastboot (Serial: {info['serial']})")

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
            self.lbl_status_pill.configure(text="DISCONNECTED", background="#7F1D1D", foreground="#FFFFFF")
            self.lbl_sub.configure(text="No device detected. Connect Onyx Boox via USB with Debugging enabled.")
            self.lbl_specs.configure(text="No device connected.")

    # =========================================================================
    # TAB 3: SCREENSAVER & BOOT MEDIA ACTIONS
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

        # Generate live preview
        if HAS_PILLOW:
            try:
                with Image.open(f) as img:
                    img_thumb = img.copy()
                    img_thumb.thumbnail((120, 162), Image.Resampling.LANCZOS)
                    if self.var_auto_grayscale.get():
                        img_thumb = img_thumb.convert("L")
                    self._preview_image = ImageTk.PhotoImage(img_thumb)
                    self.lbl_image_preview.configure(image=self._preview_image, text="")
            except Exception as e:
                self.lbl_image_preview.configure(image="", text="Preview Error")
        else:
            self.lbl_image_preview.configure(image="", text="Pillow missing")

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
    # TAB 1 & 2 ACTIONS
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
        long_sel = self.combo_long_press.get()
        short_sel = self.combo_short_press.get()

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
    # TAB 4 & 5 ACTIONS (DEBLOAT & SETTINGS)
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
                self.after(0, lambda b=btn, p=pkg: b.configure(text="Enable", style="Action.TButton", command=lambda: self._toggle_package(p, False)))
            else:
                self.after(0, lambda b=btn, p=pkg: b.configure(text="Disable", style="Danger.TButton", command=lambda: self._toggle_package(p, True)))

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
        to_str = self.combo_timeout.get()
        timeout_val = "300000"
        if "60000" in to_str: timeout_val = "60000"
        elif "120000" in to_str: timeout_val = "120000"
        elif "300000" in to_str: timeout_val = "300000"
        elif "600000" in to_str: timeout_val = "600000"
        elif "1800000" in to_str: timeout_val = "1800000"
        elif "2147483647" in to_str: timeout_val = "2147483647"

        font_str = self.combo_font.get()
        font_val = "1.05" if "1.05" in font_str else ("1.00" if "1.00" in font_str else ("0.85" if "0.85" in font_str else "1.15"))

        dpi_str = self.combo_dpi.get()
        dpi_val = "reset" if "Reset" in dpi_str else ("200" if "200" in dpi_str else ("225" if "225" in dpi_str else "240"))

        payload = {
            "screen_off_timeout": timeout_val,
            "send_action_app_error": str(self.var_telemetry.get()),
            "ble_scan": str(self.var_ble_scan.get()),
            "wifi_scan": str(self.var_wifi_scan.get()),
            "location_mode": str(self.var_location.get()),
            "font_scale": font_val,
            "density": dpi_val,
            "high_contrast": str(self.var_high_contrast.get())
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
        if to == "60000": self.combo_timeout.current(0)
        elif to == "120000": self.combo_timeout.current(1)
        elif to == "300000": self.combo_timeout.current(2)
        elif to == "600000": self.combo_timeout.current(3)
        elif to == "1800000": self.combo_timeout.current(4)
        elif to == "2147483647": self.combo_timeout.current(5)

        self.var_telemetry.set(int(s.get("send_action_app_error", "0") or "0"))
        self.var_ble_scan.set(int(s.get("ble_scan", "0") or "0"))
        self.var_wifi_scan.set(int(s.get("wifi_scan", "0") or "0"))
        self.var_location.set(int(s.get("location_mode", "0") or "0"))
        self.var_high_contrast.set(int(s.get("high_contrast", "0") or "0"))

        if show_dialog:
            messagebox.showinfo("Settings Queried", f"Current Device Values:\nTimeout: {s.get('screen_off_timeout')}ms\nFont: {s.get('font_scale')}\nDensity: {s.get('density')}")
