"""
Main GUI window for Onyx Boox C69HD Customization Tool.
Built with Tkinter and ttk with a clean, modern interface.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import datetime
import os

from core.device_ops import BUTTON_ACTIONS, DEBLOAT_CATALOG

class MainWindow(tk.Tk):
    def __init__(self, adb_manager, device_ops):
        super().__init__()
        self.adb = adb_manager
        self.ops = device_ops
        self.adb.log_callback = self.append_log

        self.title("Onyx Boox C69HD Customizer (Faust 5 OEM)")
        self.geometry("960x720")
        self.minsize(860, 640)

        # Apply Modern Styling
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self._configure_styles()
        self._build_header()
        self._build_notebook()
        self._build_footer()

        # Start initial background device probe
        self.refresh_device_status_async()

    def _configure_styles(self):
        # Configure custom TTK styles
        self.configure(bg="#F4F6F9")
        self.style.configure(".", font=("Segoe UI", 9), background="#F4F6F9")
        self.style.configure("Header.TFrame", background="#1E293B")
        self.style.configure("Header.TLabel", background="#1E293B", foreground="#F8FAFC", font=("Segoe UI", 11, "bold"))
        self.style.configure("HeaderSub.TLabel", background="#1E293B", foreground="#94A3B8", font=("Segoe UI", 9))
        self.style.configure("StatusPill.TLabel", background="#334155", foreground="#38BDF8", font=("Segoe UI", 9, "bold"), padding=4)
        
        self.style.configure("Card.TLabelframe", background="#FFFFFF", relief="solid", borderwidth=1)
        self.style.configure("Card.TLabelframe.Label", background="#FFFFFF", foreground="#0F172A", font=("Segoe UI", 10, "bold"))
        
        self.style.configure("Primary.TButton", font=("Segoe UI", 9, "bold"), padding=6)
        self.style.configure("Action.TButton", font=("Segoe UI", 9), padding=5)
        self.style.configure("Danger.TButton", font=("Segoe UI", 9, "bold"), padding=5)

    def _build_header(self):
        header_frame = ttk.Frame(self, style="Header.TFrame", padding=(16, 12))
        header_frame.pack(fill="x", side="top")

        left_box = ttk.Frame(header_frame, style="Header.TFrame")
        left_box.pack(side="left", fill="y")

        self.lbl_title = ttk.Label(left_box, text="Onyx Boox C69HD Customizer", style="Header.TLabel")
        self.lbl_title.pack(anchor="w")

        self.lbl_sub = ttk.Label(left_box, text="Device: Probing connection...", style="HeaderSub.TLabel")
        self.lbl_sub.pack(anchor="w")

        right_box = ttk.Frame(header_frame, style="Header.TFrame")
        right_box.pack(side="right", fill="y")

        self.lbl_status_pill = ttk.Label(right_box, text="DISCONNECTED", style="StatusPill.TLabel")
        self.lbl_status_pill.pack(side="left", padx=8)

        self.btn_refresh = ttk.Button(right_box, text="↻ Refresh Device", style="Action.TButton", command=self.refresh_device_status_async)
        self.btn_refresh.pack(side="left")

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=8)

        # Tab 1: Root & Partitions
        self.tab_root = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_root, text="  Root & Partitions  ")
        self._build_tab_root()

        # Tab 2: Button Remap
        self.tab_button = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_button, text="  Hardware Button Remap  ")
        self._build_tab_button()

        # Tab 3: Debloating
        self.tab_debloat = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_debloat, text="  Debloating  ")
        self._build_tab_debloat()

        # Tab 4: System Settings
        self.tab_settings = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_settings, text="  Device Settings  ")
        self._build_tab_settings()

        # Tab 5: Device Info & Shell Logs
        self.tab_logs = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_logs, text="  Device Info & Logs  ")
        self._build_tab_logs()

    def _build_footer(self):
        footer = ttk.Frame(self, padding=(12, 6))
        footer.pack(fill="x", side="bottom")

        self.lbl_footer = ttk.Label(
            footer,
            text="Onyx Boox C69HD (Faust 5 OEM) | Repos: Zeusx212/onyx-c69hd-root • Zeusx212/onyx-c69hd-button-remap | Credits: 7sarus",
            font=("Segoe UI", 8),
            foreground="#64748B"
        )
        self.lbl_footer.pack(side="left")

    # =========================================================================
    # TAB 1: ROOT & PARTITIONS
    # =========================================================================
    def _build_tab_root(self):
        # 1. Partition Backup Card
        card_backup = ttk.LabelFrame(self.tab_root, text="1. Stock Partition Backup", style="Card.TLabelframe", padding=12)
        card_backup.pack(fill="x", pady=6)

        lbl_binfo = ttk.Label(
            card_backup,
            text="Dumps current active boot (boot_a / boot_b) and vbmeta partitions into the local 'backups/' folder.\nEssential before flashing custom boot images.",
            wraplength=800,
            foreground="#475569"
        )
        lbl_binfo.pack(anchor="w", pady=(0, 8))

        btn_box = ttk.Frame(card_backup)
        btn_box.pack(anchor="w")

        self.btn_backup = ttk.Button(btn_box, text="📥 Backup Stock Partitions (dd + adb pull)", style="Primary.TButton", command=self._action_backup_partitions)
        self.btn_backup.pack(side="left", padx=(0, 8))

        # 2. Magisk Rooting & Flashing Card
        card_magisk = ttk.LabelFrame(self.tab_root, text="2. Magisk Root Installation & Fastboot Flashing", style="Card.TLabelframe", padding=12)
        card_magisk.pack(fill="x", pady=6)

        lbl_minfo = ttk.Label(
            card_magisk,
            text="Step-by-step root setup:\n1. Install Magisk APK to device -> 2. Patch your dumped stock_boot.img inside Magisk -> 3. Flash patched image via Fastboot.",
            wraplength=800,
            foreground="#475569"
        )
        lbl_minfo.pack(anchor="w", pady=(0, 8))

        m_btn_box = ttk.Frame(card_magisk)
        m_btn_box.pack(anchor="w", pady=4)

        self.btn_install_magisk = ttk.Button(m_btn_box, text="📦 1. Install Magisk APK", style="Action.TButton", command=self._action_install_magisk)
        self.btn_install_magisk.pack(side="left", padx=(0, 8))

        self.btn_reboot_fb = ttk.Button(m_btn_box, text="⚡ 2. Reboot to Bootloader (Fastboot)", style="Action.TButton", command=lambda: self.ops.reboot_device("bootloader"))
        self.btn_reboot_fb.pack(side="left", padx=(0, 8))

        self.btn_flash_patched = ttk.Button(m_btn_box, text="🚀 3. Flash Patched Boot Image...", style="Primary.TButton", command=self._action_flash_patched_boot)
        self.btn_flash_patched.pack(side="left", padx=(0, 8))

        self.btn_restore_stock = ttk.Button(m_btn_box, text="🔄 Restore Stock Boot Image...", style="Danger.TButton", command=self._action_restore_stock_boot)
        self.btn_restore_stock.pack(side="left")

        # 3. Hardware Button Wake Module Card
        card_wake = ttk.LabelFrame(self.tab_root, text="3. Hardware Button Wake (Magisk Module)", style="Card.TLabelframe", padding=12)
        card_wake.pack(fill="x", pady=6)

        lbl_winfo = ttk.Label(
            card_wake,
            text="On Onyx C69HD, only the top power button wakes the device by default. This module patches gpio-keys.kl\nso pressing the front center button or side page-turn keys instantly wakes the e-reader from sleep.",
            wraplength=800,
            foreground="#475569"
        )
        lbl_winfo.pack(anchor="w", pady=(0, 8))

        self.btn_flash_wake_mod = ttk.Button(card_wake, text="⚡ Install 'c69hd-wake' Magisk Module", style="Action.TButton", command=self._action_install_wake_module)
        self.btn_flash_wake_mod.pack(anchor="w")

    # =========================================================================
    # TAB 2: BUTTON REMAPPING
    # =========================================================================
    def _build_tab_button(self):
        card_info = ttk.LabelFrame(self.tab_button, text="C69HD Front Hardware Button Details", style="Card.TLabelframe", padding=12)
        card_info.pack(fill="x", pady=6)

        lbl_desc = ttk.Label(
            card_info,
            text="The Onyx Boox C69HD (Faust 5 OEM) features a physical center button (KEYCODE_BACK).\n"
                 "By factory default, HOLDING this button toggles the frontlight. However, because the C69HD has NO frontlight hardware, "
                 "holding it does nothing!\nThis tool allows you to remap it to Recent Apps (App Switcher), E-Ink full refresh, screenshot, or home.",
            wraplength=800,
            foreground="#334155"
        )
        lbl_desc.pack(anchor="w")

        card_remap = ttk.LabelFrame(self.tab_button, text="Configure Button Actions", style="Card.TLabelframe", padding=16)
        card_remap.pack(fill="x", pady=6)

        grid_frame = ttk.Frame(card_remap)
        grid_frame.pack(fill="x", pady=4)

        # Long Press selection
        ttk.Label(grid_frame, text="Long-Press (Hold) Action:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=6)
        self.combo_long_press = ttk.Combobox(grid_frame, width=55, state="readonly")
        long_choices = [f"{v} [{k}]" if k else f"{v} [Standard Back]" for k, v in BUTTON_ACTIONS.items()]
        self.combo_long_press["values"] = long_choices
        self.combo_long_press.current(0)  # KEYCODE_APP_SWITCH
        self.combo_long_press.grid(row=0, column=1, padx=12, pady=6, sticky="w")

        # Short Press selection
        ttk.Label(grid_frame, text="Short-Press (Single Tap) Action:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=6)
        self.combo_short_press = ttk.Combobox(grid_frame, width=55, state="readonly")
        self.combo_short_press["values"] = [
            "Standard Back Key Event [Recommended] []",
            "Recent Apps / App Switcher [KEYCODE_APP_SWITCH]",
            "Full Screen E-Ink Refresh (Clears Ghosting) [fullRefreshScreen]",
            "Take Screenshot [screenshot]",
            "Return to Home Screen [back_to_home]"
        ]
        self.combo_short_press.current(0)
        self.combo_short_press.grid(row=1, column=1, padx=12, pady=6, sticky="w")

        # Buttons
        action_box = ttk.Frame(card_remap)
        action_box.pack(anchor="w", pady=(12, 4))

        self.btn_apply_remap = ttk.Button(action_box, text="💾 Apply Button Mapping", style="Primary.TButton", command=self._action_apply_button_remap)
        self.btn_apply_remap.pack(side="left", padx=(0, 8))

        self.btn_read_remap = ttk.Button(action_box, text="📖 Read Current Mapping", style="Action.TButton", command=self._action_read_button_remap)
        self.btn_read_remap.pack(side="left", padx=(0, 8))

        self.btn_reset_remap = ttk.Button(action_box, text="🔄 Reset to Factory Default", style="Danger.TButton", command=self._action_reset_button_remap)
        self.btn_reset_remap.pack(side="left")

        # Active configuration card
        self.card_active_remap = ttk.LabelFrame(self.tab_button, text="Active Mapping on Device", style="Card.TLabelframe", padding=12)
        self.card_active_remap.pack(fill="x", pady=6)

        self.lbl_active_mapping = ttk.Label(self.card_active_remap, text="Press 'Read Current Mapping' to query device...", font=("Consolas", 9), foreground="#0369A1")
        self.lbl_active_mapping.pack(anchor="w")

    # =========================================================================
    # TAB 3: DEBLOATING
    # =========================================================================
    def _build_tab_debloat(self):
        top_ctrl = ttk.Frame(self.tab_debloat)
        top_ctrl.pack(fill="x", pady=(0, 8))

        ttk.Button(top_ctrl, text="🛡️ 1-Click Safe Debloat (Qualcomm SVA / Cellular)", style="Primary.TButton", command=self._action_safe_debloat).pack(side="left", padx=(0, 8))
        ttk.Button(top_ctrl, text="🔄 Re-enable All Debloated Packages", style="Action.TButton", command=self._action_enable_all_debloated).pack(side="left", padx=(0, 8))
        ttk.Button(top_ctrl, text="↻ Refresh Package Status", style="Action.TButton", command=self._action_refresh_debloat_list).pack(side="left")

        # Canvas & Scrollbar for debloat items
        container = ttk.Frame(self.tab_debloat)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg="#FFFFFF", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.debloat_inner = ttk.Frame(canvas, style="Card.TLabelframe", padding=10)

        self.debloat_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.debloat_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.pkg_widgets = {}
        self._populate_debloat_items()

        # Custom Package Entry Box
        custom_box = ttk.LabelFrame(self.tab_debloat, text="Custom Package Control", style="Card.TLabelframe", padding=8)
        custom_box.pack(fill="x", pady=(8, 0))

        ttk.Label(custom_box, text="Package Name:").pack(side="left", padx=4)
        self.entry_custom_pkg = ttk.Entry(custom_box, width=40)
        self.entry_custom_pkg.pack(side="left", padx=4)

        ttk.Button(custom_box, text="Disable", style="Danger.TButton", command=self._action_custom_disable).pack(side="left", padx=4)
        ttk.Button(custom_box, text="Enable", style="Action.TButton", command=self._action_custom_enable).pack(side="left", padx=4)

    def _populate_debloat_items(self):
        for widget in self.debloat_inner.winfo_children():
            widget.destroy()

        self.pkg_widgets.clear()

        for cat in DEBLOAT_CATALOG:
            cat_title = cat["category"]
            lbl_cat = ttk.Label(self.debloat_inner, text=cat_title, font=("Segoe UI", 10, "bold"), foreground="#0F172A")
            lbl_cat.pack(anchor="w", pady=(10, 4))

            for pkg, desc in cat["packages"]:
                row = ttk.Frame(self.debloat_inner, style="Card.TLabelframe")
                row.pack(fill="x", pady=2)

                lbl_name = ttk.Label(row, text=pkg, font=("Consolas", 9, "bold"), width=38, anchor="w")
                lbl_name.pack(side="left", padx=4)

                lbl_desc = ttk.Label(row, text=desc, font=("Segoe UI", 8), foreground="#475569")
                lbl_desc.pack(side="left", padx=4)

                btn_toggle = ttk.Button(row, text="Querying...", width=12)
                btn_toggle.pack(side="right", padx=6)

                self.pkg_widgets[pkg] = {
                    "button": btn_toggle,
                    "desc": desc,
                    "disabled": False
                }

    # =========================================================================
    # TAB 4: DEVICE SETTINGS
    # =========================================================================
    def _build_tab_settings(self):
        # 1. Screen Timeout Card
        card_timeout = ttk.LabelFrame(self.tab_settings, text="Screen Timeout (Fix Infinite 24.8-Day Sleep Bug)", style="Card.TLabelframe", padding=12)
        card_timeout.pack(fill="x", pady=6)

        lbl_to = ttk.Label(
            card_timeout,
            text="The C69HD factory configuration often leaves screen_off_timeout set to 2147483647 ms (24.8 days),\n"
                 "causing battery drain because the device never automatically enters deep sleep when left unattended.",
            wraplength=800,
            foreground="#475569"
        )
        lbl_to.pack(anchor="w", pady=(0, 6))

        to_box = ttk.Frame(card_timeout)
        to_box.pack(anchor="w")

        ttk.Label(to_box, text="Select Screen Timeout:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))
        self.combo_timeout = ttk.Combobox(to_box, width=32, state="readonly")
        self.combo_timeout["values"] = [
            "1 Minute (60000 ms)",
            "2 Minutes (120000 ms)",
            "5 Minutes [Recommended] (300000 ms)",
            "10 Minutes (600000 ms)",
            "30 Minutes (1800000 ms)",
            "Never Sleep [Buggy default] (2147483647 ms)"
        ]
        self.combo_timeout.current(2)
        self.combo_timeout.pack(side="left")

        # 2. System Radios & Telemetry Card
        card_telemetry = ttk.LabelFrame(self.tab_settings, text="Battery & Privacy Optimizations", style="Card.TLabelframe", padding=12)
        card_telemetry.pack(fill="x", pady=6)

        self.var_telemetry = tk.IntVar(value=0)
        chk_tel = ttk.Checkbutton(card_telemetry, text="Disable background crash/error telemetry (send_action_app_error = 0)", variable=self.var_telemetry)
        chk_tel.pack(anchor="w", pady=3)

        self.var_ble_scan = tk.IntVar(value=0)
        chk_ble = ttk.Checkbutton(card_telemetry, text="Disable background Bluetooth LE scanning (ble_scan_always_enabled = 0)", variable=self.var_ble_scan)
        chk_ble.pack(anchor="w", pady=3)

        self.var_wifi_scan = tk.IntVar(value=0)
        chk_wifi = ttk.Checkbutton(card_telemetry, text="Disable background Wi-Fi scanning (wifi_scan_always_enabled = 0)", variable=self.var_wifi_scan)
        chk_wifi.pack(anchor="w", pady=3)

        self.var_location = tk.IntVar(value=0)
        chk_loc = ttk.Checkbutton(card_telemetry, text="Turn Off Location Services on e-reader (location_mode = 0)", variable=self.var_location)
        chk_loc.pack(anchor="w", pady=3)

        # 3. Display & Font Card
        card_display = ttk.LabelFrame(self.tab_settings, text="Display & Reading Clarity", style="Card.TLabelframe", padding=12)
        card_display.pack(fill="x", pady=6)

        disp_grid = ttk.Frame(card_display)
        disp_grid.pack(anchor="w")

        ttk.Label(disp_grid, text="Font Scale:").grid(row=0, column=0, sticky="w", pady=4)
        self.combo_font = ttk.Combobox(disp_grid, width=20, state="readonly")
        self.combo_font["values"] = ["0.85 (Small)", "1.00 (Standard)", "1.05 (Optimized)", "1.10 (Large)", "1.20 (Extra Large)"]
        self.combo_font.current(2)
        self.combo_font.grid(row=0, column=1, padx=8, pady=4)

        ttk.Label(disp_grid, text="Display Density (DPI):").grid(row=1, column=0, sticky="w", pady=4)
        self.combo_dpi = ttk.Combobox(disp_grid, width=20, state="readonly")
        self.combo_dpi["values"] = ["Reset to 212 DPI (Default)", "200 DPI", "225 DPI", "240 DPI"]
        self.combo_dpi.current(0)
        self.combo_dpi.grid(row=1, column=1, padx=8, pady=4)

        self.var_high_contrast = tk.IntVar(value=0)
        ttk.Checkbutton(disp_grid, text="High Contrast Text (high_text_contrast_enabled)", variable=self.var_high_contrast).grid(row=2, column=0, columnspan=2, sticky="w", pady=4)

        # Action Buttons
        set_btn_box = ttk.Frame(self.tab_settings)
        set_btn_box.pack(anchor="w", pady=10)

        ttk.Button(set_btn_box, text="💾 Apply System Settings", style="Primary.TButton", command=self._action_apply_settings).pack(side="left", padx=(0, 8))
        ttk.Button(set_btn_box, text="📖 Query Device Settings", style="Action.TButton", command=self._action_query_settings).pack(side="left")

    # =========================================================================
    # TAB 5: DEVICE INFO & LOGS
    # =========================================================================
    def _build_tab_logs(self):
        top_split = ttk.Frame(self.tab_logs)
        top_split.pack(fill="x", pady=(0, 8))

        # Device Specs Box
        specs_box = ttk.LabelFrame(top_split, text="Hardware & Firmware Specs", style="Card.TLabelframe", padding=10)
        specs_box.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.lbl_specs = ttk.Label(specs_box, text="Querying specs...", font=("Consolas", 8), justify="left")
        self.lbl_specs.pack(anchor="w")

        # Reboot Controls Box
        reboot_box = ttk.LabelFrame(top_split, text="Device Power Controls", style="Card.TLabelframe", padding=10)
        reboot_box.pack(side="right", fill="both", padx=(6, 0))

        ttk.Button(reboot_box, text="⚡ Reboot System", style="Action.TButton", command=lambda: self.ops.reboot_device("system")).pack(fill="x", pady=2)
        ttk.Button(reboot_box, text="⚡ Reboot Recovery", style="Action.TButton", command=lambda: self.ops.reboot_device("recovery")).pack(fill="x", pady=2)
        ttk.Button(reboot_box, text="⚡ Reboot Fastboot", style="Action.TButton", command=lambda: self.ops.reboot_device("bootloader")).pack(fill="x", pady=2)
        ttk.Button(reboot_box, text="🔄 Restart SystemUI", style="Action.TButton", command=lambda: self.ops.reboot_device("systemui")).pack(fill="x", pady=2)

        # Log Window
        lbl_log = ttk.Label(self.tab_logs, text="ADB Command Output & Execution Log:", font=("Segoe UI", 9, "bold"))
        lbl_log.pack(anchor="w")

        self.txt_log = scrolledtext.ScrolledText(self.tab_logs, wrap="word", bg="#0F172A", fg="#38BDF8", font=("Consolas", 9))
        self.txt_log.pack(fill="both", expand=True, pady=4)

        log_actions = ttk.Frame(self.tab_logs)
        log_actions.pack(fill="x")
        ttk.Button(log_actions, text="Clear Log", style="Action.TButton", command=lambda: self.txt_log.delete("1.0", "end")).pack(side="left", padx=4)

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
        self.lbl_status_pill.configure(text="CHECKING...", style="StatusPill.TLabel")
        threading.Thread(target=self._worker_probe_device, daemon=True).start()

    def _worker_probe_device(self):
        info = self.adb.get_connected_device_info()
        self.after(0, lambda: self._update_ui_device_status(info))

    def _update_ui_device_status(self, info):
        if info["connected"]:
            mode_text = f"MODE: {info['mode'].upper()}"
            if info["mode"] == "adb":
                root_status = "Rooted" if info["rooted"] else "Unrooted"
                self.lbl_status_pill.configure(
                    text=f"CONNECTED ({root_status})",
                    background="#15803D" if info["rooted"] else "#0369A1",
                    foreground="#FFFFFF"
                )
                self.lbl_sub.configure(
                    text=f"Model: {info['model']} ({info['manufacturer']}) | Slot: {info['boot_slot']} | Battery: {info['battery_level']}"
                )
            elif info["mode"] == "fastboot":
                self.lbl_status_pill.configure(text="FASTBOOT MODE", background="#D97706", foreground="#FFFFFF")
                self.lbl_sub.configure(text=f"Device in Bootloader / Fastboot (Serial: {info['serial']})")

            specs_text = (
                f"Model            : {info['model']} ({info['device']})\n"
                f"Manufacturer     : {info['manufacturer']}\n"
                f"Display Build ID : {info['display_id']}\n"
                f"Android Version  : Android {info['android_version']}\n"
                f"Active Boot Slot : {info['boot_slot']}\n"
                f"Bootloader State : {'Unlocked' if info['unlocked'] else 'Locked'}\n"
                f"Root (Magisk/su) : {'Present (UID 0)' if info['rooted'] else 'No root binary detected'}\n"
                f"Battery Status   : {info['battery_level']} (Charging: {info['battery_charging']})\n"
            )
            self.lbl_specs.configure(text=specs_text)
            self._action_refresh_debloat_list_async()
        else:
            self.lbl_status_pill.configure(text="DISCONNECTED", background="#B91C1C", foreground="#FFFFFF")
            self.lbl_sub.configure(text="No device detected. Connect Onyx Boox via USB with Debugging enabled.")
            self.lbl_specs.configure(text="No device connected.")

    # =========================================================================
    # ACTION HANDLERS
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
        img_path = filedialog.askopenfilename(title="Select Stock Boot Image to Restore (.img)", filetypes=[("Disk Image", "*.img")])
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
        # Extract selected actions
        long_sel = self.combo_long_press.get()
        short_sel = self.combo_short_press.get()

        # Parse action key
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

    # Debloat actions
    def _action_refresh_debloat_list_async(self):
        threading.Thread(target=self._action_refresh_debloat_list, daemon=True).start()

    def _action_refresh_debloat_list(self):
        disabled_set = self.ops.get_disabled_packages()
        for pkg, item in self.pkg_widgets.items():
            is_dis = pkg in disabled_set
            item["disabled"] = is_dis
            btn = item["button"]
            if is_dis:
                self.after(0, lambda b=btn, p=pkg: b.configure(text="Enable", command=lambda: self._toggle_package(p, False)))
            else:
                self.after(0, lambda b=btn, p=pkg: b.configure(text="Disable", command=lambda: self._toggle_package(p, True)))

    def _toggle_package(self, pkg_name, disable):
        def _run():
            if disable:
                self.ops.disable_package(pkg_name)
            else:
                self.ops.enable_package(pkg_name)
            self._action_refresh_debloat_list()
        threading.Thread(target=_run, daemon=True).start()

    def _action_safe_debloat(self):
        if not messagebox.askyesno("Safe Debloat", "Disable Qualcomm cellular, dual-SIM, and voice activation services?"):
            return
        def _run():
            res = self.ops.apply_safe_debloat_preset()
            self._action_refresh_debloat_list()
            messagebox.showinfo("Debloat Done", f"Processed {len(res)} packages. Device freed from telephony background drain.")
        threading.Thread(target=_run, daemon=True).start()

    def _action_enable_all_debloated(self):
        def _run():
            for pkg in self.pkg_widgets:
                self.ops.enable_package(pkg)
            self._action_refresh_debloat_list()
            messagebox.showinfo("Enabled", "All catalog packages re-enabled.")
        threading.Thread(target=_run, daemon=True).start()

    def _action_custom_disable(self):
        pkg = self.entry_custom_pkg.get().strip()
        if not pkg: return
        threading.Thread(target=lambda: [self.ops.disable_package(pkg), self._action_refresh_debloat_list()], daemon=True).start()

    def _action_custom_enable(self):
        pkg = self.entry_custom_pkg.get().strip()
        if not pkg: return
        threading.Thread(target=lambda: [self.ops.enable_package(pkg), self._action_refresh_debloat_list()], daemon=True).start()

    # Settings actions
    def _action_apply_settings(self):
        # Extract timeout
        to_str = self.combo_timeout.get()
        timeout_val = "300000"
        if "60000" in to_str: timeout_val = "60000"
        elif "120000" in to_str: timeout_val = "120000"
        elif "300000" in to_str: timeout_val = "300000"
        elif "600000" in to_str: timeout_val = "600000"
        elif "1800000" in to_str: timeout_val = "1800000"
        elif "2147483647" in to_str: timeout_val = "2147483647"

        # Font
        font_str = self.combo_font.get()
        font_val = "1.05" if "1.05" in font_str else ("1.00" if "1.00" in font_str else ("0.85" if "0.85" in font_str else "1.10"))

        # Density
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

    def _action_query_settings(self):
        def _run():
            s = self.ops.get_system_settings()
            self.after(0, lambda: self._update_settings_ui(s))
        threading.Thread(target=_run, daemon=True).start()

    def _update_settings_ui(self, s):
        # Update UI with current values
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

        messagebox.showinfo("Settings Queried", f"Current Device Values:\nTimeout: {s.get('screen_off_timeout')}ms\nFont: {s.get('font_scale')}\nDensity: {s.get('density')}")
