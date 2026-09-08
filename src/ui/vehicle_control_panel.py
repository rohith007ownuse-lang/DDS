"""
vehicle_control_panel.py
Separate window for manual vehicle control.
Provides directional buttons, speed slider, and connection status.
Communicates with Arduino via SerialCommunicator.
"""

import tkinter as tk
from tkinter import font as tkfont
from src.hardware.serial_communicator import get_serial_communicator
from src.utils.config_manager import get_config


BG = "#f5f7fa"
CARD = "#ffffff"
BORDER = "#d0d7e2"
TEXT = "#1a1a2e"
MUTED = "#6b7280"
RED = "#e53935"
GREEN = "#22a447"
YELLOW = "#b8860b"
BLUE = "#1a73e8"
DARK_BTN = "#e8edf2"
DARK_BTN_ACTIVE = "#c9d4e0"
RESET_BTN = "#2e7d32"
RESET_BTN_ACTIVE = "#388e3c"


class VehicleControlPanel(tk.Toplevel):
    def __init__(self, master=None, engine=None):
        super().__init__(master)
        self.title("Vehicle Control Panel")
        self.configure(bg=BG)
        self.geometry("320x560")
        self.minsize(300, 520)
        self.resizable(False, False)

        self.engine = engine
        self.serial_comm = get_serial_communicator()
        self.config = get_config()
        self.hardware_enabled = self.config.get('hardware.enabled', False)
        self.current_speed = 170
        self.current_direction = "STOPPED"
        self.is_running = False

        self._build_ui()
        self._update_status_periodic()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # Title bar
        title_frame = tk.Frame(self, bg=DARK_BTN, height=40)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text="VEHICLE CONTROL", bg=DARK_BTN, fg=BLUE,
                 font=("JetBrains Mono", 11, "bold")).pack(side="left", padx=10, pady=8)
        tk.Label(title_frame, text="DDS", bg=DARK_BTN, fg=MUTED,
                 font=("JetBrains Mono", 9)).pack(side="right", padx=10)

        # Connection status
        conn_frame = tk.Frame(self, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        conn_frame.pack(fill="x", padx=10, pady=(10, 5))

        inner = tk.Frame(conn_frame, bg=CARD)
        inner.pack(fill="x", padx=8, pady=6)

        tk.Label(inner, text="Connection", bg=CARD, fg=MUTED,
                 font=("JetBrains Mono", 8)).pack(side="left")

        self.conn_dot = tk.Label(inner, text="\u25cf", bg=CARD, fg=RED,
                                 font=("JetBrains Mono", 10))
        self.conn_dot.pack(side="right")
        self.conn_label = tk.Label(inner, text="Disconnected", bg=CARD, fg=RED,
                                   font=("JetBrains Mono", 8))
        self.conn_label.pack(side="right", padx=(0, 6))

        # Vehicle state display
        state_frame = tk.Frame(self, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        state_frame.pack(fill="x", padx=10, pady=5)

        inner2 = tk.Frame(state_frame, bg=CARD)
        inner2.pack(fill="x", padx=8, pady=6)

        tk.Label(inner2, text="Vehicle State", bg=CARD, fg=MUTED,
                 font=("JetBrains Mono", 8)).pack(side="left")

        self.state_label = tk.Label(inner2, text="STOPPED", bg=CARD, fg=GREEN,
                                    font=("JetBrains Mono", 9, "bold"))
        self.state_label.pack(side="right")

        # Safety detail line (stop reason / face-loss timer)
        detail_frame = tk.Frame(self, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        detail_frame.pack(fill="x", padx=10, pady=5)
        detail_inner = tk.Frame(detail_frame, bg=CARD)
        detail_inner.pack(fill="x", padx=8, pady=4)
        tk.Label(detail_inner, text="Safety", bg=CARD, fg=MUTED,
                 font=("JetBrains Mono", 8)).pack(side="left")
        self.detail_label = tk.Label(detail_inner, text="Face present / eyes open", bg=CARD, fg=GREEN,
                                     font=("JetBrains Mono", 8))
        self.detail_label.pack(side="right")

        # Speed slider
        speed_frame = tk.Frame(self, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        speed_frame.pack(fill="x", padx=10, pady=5)

        speed_inner = tk.Frame(speed_frame, bg=CARD)
        speed_inner.pack(fill="x", padx=8, pady=8)

        tk.Label(speed_inner, text="Motor Speed", bg=CARD, fg=MUTED,
                 font=("JetBrains Mono", 8)).pack(anchor="w")

        slider_row = tk.Frame(speed_inner, bg=CARD)
        slider_row.pack(fill="x", pady=(4, 0))

        self.speed_var = tk.IntVar(value=self.current_speed)
        self.speed_slider = tk.Scale(slider_row, from_=0, to=255, orient="horizontal",
                                     variable=self.speed_var, bg=CARD, fg=TEXT,
                                     troughcolor=DARK_BTN, highlightthickness=0,
                                     sliderlength=20, length=180,
                                     command=self._on_speed_change)
        self.speed_slider.pack(side="left")

        self.speed_value_label = tk.Label(slider_row, text=f"{self.current_speed}",
                                          bg=CARD, fg=TEXT,
                                          font=("JetBrains Mono", 12, "bold"))
        self.speed_value_label.pack(side="right", padx=(10, 0))

        tk.Label(speed_inner, text="PWM (0-255)", bg=CARD, fg=MUTED,
                 font=("JetBrains Mono", 7)).pack(anchor="w", pady=(2, 0))

        # Direction buttons - D-pad layout
        dir_frame = tk.Frame(self, bg=BG)
        dir_frame.pack(pady=(10, 5))

        btn_style = {
            "bg": DARK_BTN, "fg": TEXT,
            "activebackground": DARK_BTN_ACTIVE, "activeforeground": TEXT,
            "font": ("JetBrains Mono", 12, "bold"),
            "width": 5, "height": 2,
            "highlightbackground": BORDER, "highlightthickness": 1,
            "relief": "flat", "cursor": "hand2"
        }

        # Forward button
        self.btn_forward = tk.Button(dir_frame, text="\u25b2\nFWD", command=self._cmd_forward, **btn_style)
        self.btn_forward.grid(row=0, column=1, padx=3, pady=3)

        # Left button
        self.btn_left = tk.Button(dir_frame, text="\u25c0\nLEFT", command=self._cmd_left, **btn_style)
        self.btn_left.grid(row=1, column=0, padx=3, pady=3)

        # Stop button (red)
        stop_style = dict(btn_style)
        stop_style["bg"] = RED
        stop_style["activebackground"] = "#c62828"
        self.btn_stop = tk.Button(dir_frame, text="\u25a0\nSTOP", command=self._cmd_stop, **stop_style)
        self.btn_stop.grid(row=1, column=1, padx=3, pady=3)

        # Right button
        self.btn_right = tk.Button(dir_frame, text="\u25b6\nRIGHT", command=self._cmd_right, **btn_style)
        self.btn_right.grid(row=1, column=2, padx=3, pady=3)

        # Backward button
        self.btn_backward = tk.Button(dir_frame, text="\u25bc\nBACK", command=self._cmd_backward, **btn_style)
        self.btn_backward.grid(row=2, column=1, padx=3, pady=3)

        # Emergency stop latch indicator
        latch_frame = tk.Frame(self, bg=BG)
        latch_frame.pack(pady=(0, 5))
        self.latch_dot = tk.Label(latch_frame, text="\u25cf", bg=BG, fg=GREEN,
                                  font=("JetBrains Mono", 9))
        self.latch_dot.pack(side="left")
        self.latch_label = tk.Label(latch_frame, text="Normal operation", bg=BG, fg=GREEN,
                                    font=("JetBrains Mono", 8))
        self.latch_label.pack(side="left", padx=(4, 0))

        # Reset button (clears latched emergency stop)
        reset_style = {
            "bg": RESET_BTN, "fg": "#ffffff",
            "activebackground": RESET_BTN_ACTIVE, "activeforeground": "#ffffff",
            "font": ("JetBrains Mono", 10, "bold"),
            "highlightbackground": BORDER, "highlightthickness": 1,
            "relief": "flat", "cursor": "hand2"
        }
        self.btn_reset = tk.Button(self, text="RESET VEHICLE", command=self._cmd_reset, **reset_style)
        self.btn_reset.pack(fill="x", padx=10, pady=(0, 5))

        # Last command display
        cmd_frame = tk.Frame(self, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        cmd_frame.pack(fill="x", padx=10, pady=5)

        cmd_inner = tk.Frame(cmd_frame, bg=CARD)
        cmd_inner.pack(fill="x", padx=8, pady=6)

        tk.Label(cmd_inner, text="Last Command", bg=CARD, fg=MUTED,
                 font=("JetBrains Mono", 8)).pack(side="left")
        self.cmd_label = tk.Label(cmd_inner, text="--", bg=CARD, fg=TEXT,
                                  font=("JetBrains Mono", 9, "bold"))
        self.cmd_label.pack(side="right")

        # Command log
        log_frame = tk.Frame(self, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        tk.Label(log_frame, text="Command Log", bg=CARD, fg=MUTED,
                 font=("JetBrains Mono", 8)).pack(anchor="w", padx=8, pady=(6, 2))

        self.log_text = tk.Text(log_frame, bg="#ffffff", fg=TEXT,
                                insertbackground=TEXT,
                                font=("JetBrains Mono", 8), height=6,
                                borderwidth=0, highlightthickness=0,
                                state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    def _send_command(self, command, description=""):
        if not self.hardware_enabled:
            self._log(f"[SIM] {command} - {description} (hardware disabled)")
            self.cmd_label.configure(text=command)
            return

        if self.serial_comm.is_available():
            self.serial_comm.send_command(command)
            self.cmd_label.configure(text=command)
            self._log(f"Sent: {command} - {description}")
        else:
            self._log(f"FAILED: {command} - not connected")

    def _cmd_forward(self):
        self._send_command("F", "Forward")
        self.current_direction = "FORWARD"
        self.state_label.configure(text="FORWARD", fg=BLUE)

    def _cmd_backward(self):
        self._send_command("B", "Backward")
        self.current_direction = "BACKWARD"
        self.state_label.configure(text="BACKWARD", fg=YELLOW)

    def _cmd_left(self):
        self._send_command("L", "Turn Left")
        self.current_direction = "LEFT"
        self.state_label.configure(text="LEFT", fg=TEXT)

    def _cmd_right(self):
        self._send_command("T", "Turn Right")
        self.current_direction = "RIGHT"
        self.state_label.configure(text="RIGHT", fg=TEXT)

    def _cmd_stop(self):
        self._send_command("S", "Emergency Stop")
        self.current_direction = "STOPPED"
        self.state_label.configure(text="STOPPED", fg=GREEN)

    def _cmd_reset(self):
        # Clear the latched emergency stop: send RESET to Arduino and clear
        # the engine's latch so the vehicle can operate again.
        if self.engine is not None:
            self.engine.clear_emergency_stop()
        else:
            self._send_command("R", "Reset (manual)")
        self.current_direction = "STOPPED"
        if self.engine is not None:
            self.state_label.configure(text="READY", fg=BLUE)
        else:
            self.state_label.configure(text="STOPPED", fg=GREEN)
        self._log("RESET - emergency stop cleared")

    def _on_speed_change(self, val):
        self.current_speed = int(val)
        self.speed_value_label.configure(text=str(self.current_speed))
        speed_cmd = f"W{self.current_speed}"
        if self.hardware_enabled and self.serial_comm.is_available():
            self.serial_comm.send_command(speed_cmd)

    def _log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 50:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", f"{lines - 50}.0")
            self.log_text.configure(state="disabled")

    def _update_status_periodic(self):
        if self.serial_comm.is_available():
            self.conn_dot.configure(fg=GREEN)
            self.conn_label.configure(text="Connected", fg=GREEN)
        else:
            self.conn_dot.configure(fg=RED)
            self.conn_label.configure(text="Disconnected", fg=RED)

        # Show latched emergency-stop state from the fatigue engine.
        if self.engine is not None and self.engine.emergency_stop_latched:
            self.latch_dot.configure(fg=RED)
            reason = self.engine.stop_reason or "unknown"
            if self.engine.braking_active:
                self.latch_label.configure(text="BRAKING - PROGRESSIVE STOP", fg=YELLOW)
            else:
                self.latch_label.configure(text="EMERGENCY STOP - LATCHED", fg=RED)
            self.state_label.configure(text="STOPPED (LATCH)", fg=RED)
            self.detail_label.configure(
                text=f"Stopped via {reason.replace('_', ' ')}", fg=RED)
        else:
            self.latch_dot.configure(fg=GREEN)
            self.latch_label.configure(text="Normal operation", fg=GREEN)
            if self.engine is not None and self.engine.face_lost_time > 0:
                self.detail_label.configure(
                    text=f"Face lost {self.engine.face_lost_time:.1f}s / {self.engine.face_loss_stop_threshold:.1f}s",
                    fg=YELLOW)
            else:
                self.detail_label.configure(text="Face present / eyes open", fg=GREEN)

        if not self.is_running:
            return
        self.after(500, self._update_status_periodic)

    def start_monitoring(self):
        self.is_running = True
        self._update_status_periodic()

    def _on_close(self):
        self.is_running = False
        self.withdraw()
