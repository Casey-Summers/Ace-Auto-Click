import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import pyautogui
from pynput import keyboard, mouse
from typing import List, Optional, Any, Dict

from click_engine import ClickEngine, ClickSettings
from pixel_match import PixelCondition, get_pixel_rgb, rgb_close
from actions import ActionStep, ClickStep, WaitStep, PixelCheckStep, KeyTapStep
from storage import save_settings, load_settings

# Set theme and appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

try:
    import ctypes

    # Query DPI awareness for Windows
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class AceAutoClicker(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Ace Auto Clicker")
        # Narrower and shorter as requested
        self.geometry("700x550")
        self.attributes("-topmost", True)

        # Core engine
        self.engine = ClickEngine(on_status=self.update_status)

        # State and Persistence
        self.settings = load_settings()
        self.start_stop_hotkey = self.settings.get("hotkey", "F8")
        self.simple_action_type = self.settings.get("simple_action_type", "mouse")
        self.simple_action_value = self.settings.get("simple_action_value", "left")

        self.current_mode = "Simple"
        self.active_steps: List[ActionStep] = []
        self.selected_step: Optional[ActionStep] = None
        self.current_hotkey_listener = None

        # Variables (Simple Mode)
        self.simple_interval = ctk.IntVar(
            value=self.settings.get("simple_interval", 100)
        )
        self.simple_interval_rnd = ctk.IntVar(
            value=self.settings.get("simple_interval_rnd", 0)
        )
        self.simple_x = ctk.IntVar(value=self.settings.get("simple_x", 0))
        self.simple_y = ctk.IntVar(value=self.settings.get("simple_y", 0))
        self.simple_pos_rnd = ctk.IntVar(value=self.settings.get("simple_pos_rnd", 0))

        # UI Setup
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_header()

        # Main content container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.create_status_bar()
        self.select_mode("Simple")
        self.setup_hotkeys()

        # Pixel monitor thread
        self.stop_pixel_monitor = threading.Event()
        threading.Thread(target=self.pixel_monitor_loop, daemon=True).start()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_header(self):
        self.header = ctk.CTkFrame(self, height=60, corner_radius=0)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_columnconfigure(1, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header,
            text="ACE AUTO CLICKER",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=10)

        # Mode Selector (Top Right)
        self.mode_switch = ctk.CTkSegmentedButton(
            self.header, values=["Simple", "Advanced"], command=self.select_mode
        )
        self.mode_switch.set("Simple")
        self.mode_switch.grid(row=0, column=1, padx=10, sticky="e")

        # Settings & Stop (Top Right)
        btn_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=10)

        self.settings_btn = ctk.CTkButton(
            btn_frame, text="⚙", width=35, height=35, command=self.open_settings
        )
        self.settings_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="STOP",
            width=80,
            height=35,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            command=self.stop_all,
        )
        self.stop_btn.pack(side="left", padx=5)

    def create_status_bar(self):
        self.status_bar = ctk.CTkFrame(self, height=25, corner_radius=0)
        self.status_bar.grid(row=2, column=0, sticky="ew")
        self.status_label = ctk.CTkLabel(
            self.status_bar, text="Status: Idle", font=ctk.CTkFont(size=11)
        )
        self.status_label.pack(side="left", padx=20)

    def select_mode(self, mode):
        self.current_mode = mode
        for widget in self.main_container.winfo_children():
            widget.destroy()

        if mode == "Simple":
            self.show_simple_mode()
        else:
            self.show_advanced_mode()

        self.update_status("Idle")

    def show_simple_mode(self):
        frame = ctk.CTkFrame(self.main_container, corner_radius=15)
        frame.grid(row=0, column=0, sticky="n", pady=20, padx=20)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text="Quick Connect", font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, pady=15)

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.grid(row=1, column=0, padx=40, pady=10, sticky="ew")

        # Row 1: Interval
        ctk.CTkLabel(content, text="Click Interval (ms):", width=120, anchor="w").grid(
            row=0, column=0, sticky="w", pady=5
        )
        ctk.CTkEntry(content, textvariable=self.simple_interval, width=80).grid(
            row=0, column=1, sticky="w", padx=5
        )
        ctk.CTkLabel(content, text="+ Randomness:", width=100, anchor="w").grid(
            row=0, column=2, sticky="w", padx=(20, 0)
        )
        ctk.CTkEntry(content, textvariable=self.simple_interval_rnd, width=80).grid(
            row=0, column=3, sticky="w", padx=5
        )

        # Row 2: Position
        ctk.CTkLabel(content, text="Target Pos (X, Y):", width=120, anchor="w").grid(
            row=1, column=0, sticky="w", pady=5
        )
        pos_entry_f = ctk.CTkFrame(content, fg_color="transparent")
        pos_entry_f.grid(row=1, column=1, sticky="w", padx=5)
        ctk.CTkEntry(pos_entry_f, textvariable=self.simple_x, width=60).pack(
            side="left", padx=2
        )
        ctk.CTkEntry(pos_entry_f, textvariable=self.simple_y, width=60).pack(
            side="left", padx=2
        )
        ctk.CTkButton(
            pos_entry_f, text="Pick", width=50, command=self.pick_simple_pos
        ).pack(side="left", padx=5)

        ctk.CTkLabel(content, text="+ Randomness (px):", width=100, anchor="w").grid(
            row=1, column=2, sticky="w", padx=(20, 0)
        )
        ctk.CTkEntry(content, textvariable=self.simple_pos_rnd, width=80).grid(
            row=1, column=3, sticky="w", padx=5
        )

        # Row 3: Action Type & Value
        ctk.CTkLabel(content, text="Hotkey Type:", width=120, anchor="w").grid(
            row=2, column=0, sticky="w", pady=10
        )
        self.action_type_switch = ctk.CTkSegmentedButton(
            content, values=["keyboard", "mouse"], command=self.set_action_type
        )
        self.action_type_switch.set(self.simple_action_type)
        self.action_type_switch.grid(row=2, column=1, sticky="w", padx=5)

        self.action_val_label = ctk.CTkLabel(
            content, text="Action Key:", width=100, anchor="w"
        )
        self.action_val_label.grid(row=2, column=2, sticky="w", padx=(20, 0))

        self.action_val_container = ctk.CTkFrame(content, fg_color="transparent")
        self.action_val_container.grid(row=2, column=3, sticky="w", padx=5)
        self.refresh_simple_action_control()

        # Start Button
        self.run_btn = ctk.CTkButton(
            frame,
            text=f"START ({self.start_stop_hotkey})",
            height=50,
            width=250,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.toggle_engine,
        )
        self.run_btn.grid(row=4, column=0, pady=25)

    def refresh_simple_action_control(self):
        for w in self.action_val_container.winfo_children():
            w.destroy()

        if self.simple_action_type == "keyboard":
            self.action_val_label.configure(text="Action Key:")
            entry = ctk.CTkEntry(self.action_val_container, width=80)
            entry.insert(0, self.simple_action_value)
            entry.pack(side="left")

            def save(e):
                self.simple_action_value = entry.get()
                self.save_all_settings()

            entry.bind("<FocusOut>", save)
            entry.bind("<Return>", save)
        else:
            self.action_val_label.configure(text="Action Btn:")
            opt = ctk.CTkOptionMenu(
                self.action_val_container,
                values=["left", "right", "middle"],
                width=80,
                command=self.set_simple_action_value,
            )
            opt.set(
                self.simple_action_value
                if self.simple_action_value in ["left", "right", "middle"]
                else "left"
            )
            opt.pack(side="left")

    def show_advanced_mode(self):
        # Action Bar (Directly between header and list)
        self.action_bar = ctk.CTkFrame(self.main_container, corner_radius=10, height=50)
        self.action_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            self.action_bar, text="Add Actions:", font=ctk.CTkFont(weight="bold")
        ).pack(side="left", padx=15, pady=10)
        for act in ["Click", "Wait", "Pixel", "Key Tap"]:
            ctk.CTkButton(
                self.action_bar,
                text=f"+ {act}",
                width=80,
                command=lambda a=act.lower().replace(" ", "_"): self.add_step(a),
            ).pack(side="left", padx=5)
        ctk.CTkButton(
            self.action_bar,
            text="Clear All",
            width=80,
            fg_color="#616161",
            command=self.clear_steps,
        ).pack(side="right", padx=15)

        # List and Properties
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=3)
        self.main_container.grid_columnconfigure(1, weight=2)

        self.steps_list = ctk.CTkScrollableFrame(self.main_container, corner_radius=10)
        self.steps_list.grid(row=1, column=0, sticky="nsew", padx=(0, 5))

        self.prop_frame = ctk.CTkFrame(self.main_container, corner_radius=10)
        self.prop_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        ctk.CTkLabel(
            self.prop_frame, text="Properties", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=5)

        self.prop_container = ctk.CTkFrame(self.prop_frame, fg_color="transparent")
        self.prop_container.pack(fill="both", expand=True, padx=10, pady=2)

        # Run Sequence (Full Width Bottom)
        self.adv_run_f = ctk.CTkFrame(self.main_container, corner_radius=10, height=60)
        self.adv_run_f.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.adv_run_f.grid_propagate(False)

        self.adv_run_btn = ctk.CTkButton(
            self.adv_run_f,
            text=f"RUN SEQUENCE ({self.start_stop_hotkey})",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.toggle_engine,
        )
        self.adv_run_btn.pack(expand=True, fill="both", padx=10, pady=5)

        self.refresh_steps_ui()

    def update_status(self, msg):
        self.status_label.configure(text=f"Status: {msg}")
        is_on = "ON" in msg or "Running" in msg
        is_stopping = "Stopping" in msg
        is_starting = "Starting" in msg

        if is_on:
            label = "STOP"
            color = "#d32f2f"
        elif is_stopping:
            label = "STOPPING..."
            color = "#b71c1c"
        elif is_starting:
            label = "STARTING..."
            color = "#1F6AA5"
        else:
            label = f"START ({self.start_stop_hotkey})"
            color = ["#3B8ED0", "#1F6AA5"]

        if self.current_mode == "Simple" and hasattr(self, "run_btn"):
            self.run_btn.configure(text=label, fg_color=color)
        elif self.current_mode == "Advanced" and hasattr(self, "adv_run_btn"):
            self.adv_run_btn.configure(
                text=(
                    f"STOP ({self.start_stop_hotkey})"
                    if (is_on or is_stopping)
                    else f"RUN SEQUENCE ({self.start_stop_hotkey})"
                ),
                fg_color=color,
            )

    def toggle_engine(self):
        if self.engine.is_running():
            self.update_status("Stopping...")
            self.engine.stop()
        else:
            if self.current_mode == "Simple":
                self.update_status("Starting Simple Mode...")
                settings = ClickSettings(
                    enabled=True,
                    x=self.simple_x.get(),
                    y=self.simple_y.get(),
                    interval_ms=self.simple_interval.get(),
                    interval_rnd_ms=self.simple_interval_rnd.get(),
                    button=(
                        self.simple_action_value
                        if self.simple_action_type == "mouse"
                        else "left"
                    ),
                    key_to_tap=(
                        self.simple_action_value
                        if self.simple_action_type == "keyboard"
                        else None
                    ),
                    random_offset_px=self.simple_pos_rnd.get(),
                )
                self.engine.start_clicking(
                    settings, PixelCondition(False, 0, 0, (0, 0, 0), 0, "")
                )
            else:
                if not self.active_steps:
                    messagebox.showwarning("Ace Auto Clicker", "No steps in sequence!")
                    return
                self.update_status("Starting Advanced Mode...")
                self.engine.start_sequence(self.active_steps, loops=0)

    def stop_all(self):
        self.engine.stop()

    def set_action_type(self, val):
        self.simple_action_type = val
        self.save_all_settings()
        self.refresh_simple_action_control()

    def set_simple_action_value(self, val):
        self.simple_action_value = val
        self.save_all_settings()

    def setup_hotkeys(self):
        """Sets up a robust global listener for the start/stop hotkey."""
        if self.current_hotkey_listener:
            try:
                self.current_hotkey_listener.stop()
            except:
                pass

        # Normalize target: remove brackets and 'key.' prefix if present
        target_raw = self.start_stop_hotkey.lower().strip()
        target_clean = target_raw.replace("<", "").replace(">", "").replace("key.", "")

        def on_press(key):
            try:
                # Extract character or name (e.g., 'a' or 'f8')
                k_char = getattr(key, "char", None)
                k_name = getattr(key, "name", None)

                # Normalize the pressed key string
                pressed_str = (k_char or k_name or str(key)).lower().replace("key.", "")

                if pressed_str == target_clean:
                    # Use after() to ensure thread-safe UI updates in tkinter
                    self.after(0, self.toggle_engine)
            except Exception:
                pass

        # Using a raw Listener is often more robust for special characters like `
        self.current_hotkey_listener = keyboard.Listener(on_press=on_press)
        self.current_hotkey_listener.daemon = True
        self.current_hotkey_listener.start()

    def open_settings(self):
        d = ctk.CTkToplevel(self)
        d.title("Settings")
        d.geometry("350x200")
        d.attributes("-topmost", True)
        ctk.CTkLabel(
            d, text="Global Configuration", font=ctk.CTkFont(weight="bold")
        ).pack(pady=15)
        row = ctk.CTkFrame(d, fg_color="transparent")
        row.pack(pady=10)
        ctk.CTkLabel(row, text="Start/Stop Key:").pack(side="left", padx=10)
        hk_entry = ctk.CTkEntry(row, width=120)
        hk_entry.insert(0, self.start_stop_hotkey)
        hk_entry.pack(side="left")

        def save():
            self.start_stop_hotkey = hk_entry.get()
            self.save_all_settings()
            self.setup_hotkeys()
            self.update_status("Idle")
            d.destroy()

        ctk.CTkButton(d, text="Save Settings", command=save).pack(pady=15)

    def save_all_settings(self):
        s = {
            "hotkey": self.start_stop_hotkey,
            "simple_action_type": self.simple_action_type,
            "simple_action_value": self.simple_action_value,
            "simple_interval": self.simple_interval.get(),
            "simple_interval_rnd": self.simple_interval_rnd.get(),
            "simple_x": self.simple_x.get(),
            "simple_y": self.simple_y.get(),
            "simple_pos_rnd": self.simple_pos_rnd.get(),
        }
        save_settings(s)

    # --- Advanced Mode Helpers ---

    def add_step(self, stype):
        sid = f"step_{int(time.time()*1000)}"
        if stype == "click":
            step = ClickStep(
                id=sid, type="click", x=self.simple_x.get(), y=self.simple_y.get()
            )
        elif stype == "wait":
            step = WaitStep(id=sid, type="wait", ms=1000)
        elif stype == "pixel":
            step = PixelCheckStep(id=sid, type="pixel_check", x=500, y=500)
        elif stype == "key_tap":
            step = KeyTapStep(id=sid, type="key_tap")
        else:
            return
        self.active_steps.append(step)
        self.refresh_steps_ui()
        self.edit_step(step)

    def clear_steps(self):
        self.active_steps.clear()
        self.selected_step = None
        self.refresh_steps_ui()
        for w in self.prop_container.winfo_children():
            w.destroy()

    def refresh_steps_ui(self):
        for w in self.steps_list.winfo_children():
            w.destroy()
        for i, step in enumerate(self.active_steps):
            border = ctk.CTkFrame(
                self.steps_list, fg_color=["#D1D5DB", "#374151"], corner_radius=8
            )
            border.pack(fill="x", pady=2, padx=5)
            sf = ctk.CTkFrame(border, fg_color="transparent", height=40)
            sf.pack(fill="x", padx=2, pady=2)
            btn_f = ctk.CTkFrame(sf, fg_color="transparent")
            btn_f.pack(side="left", padx=5)
            ctk.CTkButton(
                btn_f,
                text="▲",
                width=22,
                height=16,
                command=lambda idx=i: self.move_step(idx, -1),
            ).pack(pady=1)
            ctk.CTkButton(
                btn_f,
                text="▼",
                width=22,
                height=16,
                command=lambda idx=i: self.move_step(idx, 1),
            ).pack(pady=1)
            ctk.CTkLabel(
                sf,
                text=f"{i+1}. {step.type.upper()}",
                width=110,
                anchor="w",
                font=ctk.CTkFont(weight="bold"),
            ).pack(side="left", padx=5)
            ctk.CTkButton(
                sf,
                text="X",
                width=30,
                height=25,
                fg_color="#d32f2f",
                command=lambda s=step: self.remove_step(s),
            ).pack(side="right", padx=3)
            ctk.CTkButton(
                sf,
                text="Edit",
                width=45,
                height=25,
                command=lambda s=step: self.edit_step(s),
            ).pack(side="right", padx=3)

    def move_step(self, idx, dir):
        new_idx = idx + dir
        if 0 <= new_idx < len(self.active_steps):
            self.active_steps[idx], self.active_steps[new_idx] = (
                self.active_steps[new_idx],
                self.active_steps[idx],
            )
            self.refresh_steps_ui()

    def edit_step(self, step):
        self.selected_step = step
        for w in self.prop_container.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.prop_container,
            text=step.type.upper(),
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=5)
        p_f = ctk.CTkScrollableFrame(
            self.prop_container, fg_color="transparent", height=300
        )
        p_f.pack(fill="both", expand=True)
        self.add_prop(p_f, step, "Repeats", "repeats", "int")
        self.add_prop(p_f, step, "Delay (ms)", "interval_ms", "int")
        if isinstance(step, ClickStep):
            self.add_prop(p_f, step, "X", "x", "int")
            self.add_prop(p_f, step, "Y", "y", "int")
            self.add_prop_opt(
                p_f, step, "Button", "button", ["left", "right", "middle"]
            )
            ctk.CTkButton(
                p_f, text="Capture Mouse", command=lambda: self.capture_prop_pos(step)
            ).pack(pady=5)
        elif isinstance(step, WaitStep):
            self.add_prop(p_f, step, "Wait (ms)", "ms", "int")
        elif isinstance(step, PixelCheckStep):
            self.add_prop(p_f, step, "X", "x", "int")
            self.add_prop(p_f, step, "Y", "y", "int")
            self.add_prop(p_f, step, "Tolerance", "tolerance", "int")
            self.add_prop_opt(
                p_f,
                step,
                "Mode",
                "mode",
                ["wait_until_match", "stop_if_mismatch", "skip_if_mismatch"],
            )
            self.pixel_ui_f = ctk.CTkFrame(p_f)
            self.pixel_ui_f.pack(fill="x", pady=5)
            comp_f = ctk.CTkFrame(self.pixel_ui_f, fg_color="transparent")
            comp_f.pack(pady=2)
            self.target_color_box = tk.Label(comp_f, text="T", width=4, bg="#FFF")
            self.target_color_box.pack(side="left", padx=2)
            self.current_color_box = tk.Label(comp_f, text="L", width=4, bg="#000")
            self.current_color_box.pack(side="left", padx=2)
            self.match_status_box = ctk.CTkFrame(
                self.pixel_ui_f, height=15, fg_color="red"
            )
            self.match_status_box.pack(fill="x", pady=2, padx=5)
            ctk.CTkButton(
                p_f, text="Sample Pixel", command=lambda: self.capture_pixel_props(step)
            ).pack(pady=2)
        elif isinstance(step, KeyTapStep):
            self.add_prop(p_f, step, "Key", "key", "str")

    def add_prop(self, parent, obj, label, attr, ptype):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=1)
        ctk.CTkLabel(
            row, text=label, width=80, anchor="w", font=ctk.CTkFont(size=11)
        ).pack(side="left")
        e = ctk.CTkEntry(row, height=24)
        e.insert(0, str(getattr(obj, attr)))
        e.pack(side="left", fill="x", expand=True)

        def save(ev=None):
            try:
                v = e.get()
                setattr(
                    obj,
                    attr,
                    int(v) if ptype == "int" else float(v) if ptype == "float" else v,
                )
            except:
                pass

        e.bind("<FocusOut>", save)
        e.bind("<Return>", save)

    def add_prop_opt(self, parent, obj, label, attr, vals):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=1)
        ctk.CTkLabel(
            row, text=label, width=80, anchor="w", font=ctk.CTkFont(size=11)
        ).pack(side="left")
        m = ctk.CTkOptionMenu(
            row, values=vals, height=24, command=lambda v: setattr(obj, attr, v)
        )
        m.set(getattr(obj, attr))
        m.pack(side="left", fill="x", expand=True)

    def capture_prop_pos(self, step):
        time.sleep(1.0)
        x, y = pyautogui.position()
        step.x, step.y = x, y
        self.edit_step(step)

    def capture_pixel_props(self, step):
        time.sleep(1.0)
        x, y = pyautogui.position()
        rgb = get_pixel_rgb(x, y)
        step.x, step.y = x, y
        step.expected_rgb = rgb
        self.edit_step(step)

    def pixel_monitor_loop(self):
        while not self.stop_pixel_monitor.is_set():
            if self.current_mode == "Advanced" and isinstance(
                self.selected_step, PixelCheckStep
            ):
                try:
                    s = self.selected_step
                    curr = get_pixel_rgb(s.x, s.y)
                    match = rgb_close(curr, s.expected_rgb, s.tolerance)
                    self.after(
                        0,
                        lambda c=curr, t=s.expected_rgb, m=match: self.update_pixel_ui(
                            c, t, m
                        ),
                    )
                except:
                    pass
            time.sleep(0.2)

    def update_pixel_ui(self, curr, target, match):
        if not hasattr(self, "target_color_box"):
            return
        try:
            th = "#%02x%02x%02x" % target
            ch = "#%02x%02x%02x" % curr
            self.target_color_box.configure(bg=th)
            self.current_color_box.configure(bg=ch)
            self.match_status_box.configure(fg_color="green" if match else "red")
        except:
            pass

    def pick_simple_pos(self):
        self.update_status("Capturing...")
        time.sleep(1.0)
        x, y = pyautogui.position()
        self.simple_x.set(x)
        self.simple_y.set(y)
        self.update_status(f"Captured: {x}, {y}")

    def remove_step(self, step):
        if step in self.active_steps:
            self.active_steps.remove(step)
            self.refresh_steps_ui()

    def on_close(self):
        self.stop_pixel_monitor.set()
        self.engine.stop()
        self.destroy()
        sys.exit()


if __name__ == "__main__":
    AceAutoClicker().mainloop()
