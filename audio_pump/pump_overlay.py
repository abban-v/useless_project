"""
Interactive Bottom-Right Bicycle Pump Mini-Game for Audio Pump Module.
Pops up when audio drops to 0. User must frantically click the pump to increase volume.
Action keys (Space, Enter, etc.) are strictly disabled; mouse clicks are the only allowed input.
Features diminishing returns (gets harder near 100%) and continuous decay when idle.
"""

import time
import tkinter as tk
from typing import Callable
from config import PUMP_DECAY_RATE_PER_SEC


class PumpOverlay(tk.Toplevel):
    """
    Floating animated pump mini-game positioned in the bottom-right corner.
    Action keys disabled: requires direct mouse clicks.
    """

    def __init__(
        self,
        master: tk.Tk,
        on_progress: Callable[[float], None],
        on_complete: Callable[[], None],
    ):
        super().__init__(master)
        self.on_progress = on_progress
        self.on_complete = on_complete

        self.withdraw()  # Initially hidden
        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)

        self.width = 280
        self.height = 360

        self.current_volume = 0.0  # 0.0 to 100.0
        self.is_active = False
        self.is_completed = False
        self.handle_offset = 0  # Stroke animation
        self.last_tick_time = time.time()

        self._build_ui()
        self._block_action_keys()

    def _build_ui(self):
        self.configure(bg="#1a1a1a")

        # Container card with border
        self.container = tk.Frame(self, bg="#242428", bd=2, relief="solid")
        self.container.pack(fill="both", expand=True, padx=4, pady=4)

        # Title / Warning Banner
        self.title_label = tk.Label(
            self.container,
            text="[!] AUDIO COLLAPSED! [!]",
            font=("Impact", 15),
            fg="#FF3B30",
            bg="#242428",
        )
        self.title_label.pack(pady=(10, 2))

        self.sub_label = tk.Label(
            self.container,
            text="MANUAL PRESSURE REQUIRED",
            font=("Arial", 9, "bold"),
            fg="#8E8E93",
            bg="#242428",
        )
        self.sub_label.pack(pady=(0, 6))

        # Canvas for animated bicycle pump & pressure gauge
        self.canvas = tk.Canvas(
            self.container,
            width=260,
            height=180,
            bg="#1c1c1e",
            highlightthickness=1,
            highlightbackground="#3a3a3c",
            takefocus=False,
        )
        self.canvas.pack(pady=4)

        # Status readout
        self.vol_label = tk.Label(
            self.container,
            text="PRESSURE: 0%",
            font=("Consolas", 14, "bold"),
            fg="#FF9500",
            bg="#242428",
        )
        self.vol_label.pack(pady=(6, 2))

        # Big tactile PUMP button - MOUSE CLICKS ONLY, keyboard focus disabled
        self.pump_btn = tk.Button(
            self.container,
            text="PUMP IT! (MOUSE CLICK ONLY)",
            font=("Impact", 12),
            bg="#34C759",
            fg="#FFFFFF",
            activebackground="#30D158",
            activeforeground="#FFFFFF",
            relief="raised",
            bd=3,
            cursor="hand2",
            takefocus=False,
            command=self.do_pump_stroke,
        )
        self.pump_btn.pack(fill="x", padx=16, pady=(4, 10))

        self._draw_pump()

    def _block_action_keys(self):
        """
        Explicitly disable all action keys (Space, Enter, etc.).
        Only direct mouse clicks on the canvas or button can pump!
        """
        # Block keys on entire window, container, and button
        def swallow_key(e):
            return "break"

        self.bind("<KeyPress>", swallow_key)
        self.container.bind("<KeyPress>", swallow_key)
        self.pump_btn.bind("<KeyPress>", swallow_key)
        self.canvas.bind("<KeyPress>", swallow_key)

        # Mouse click triggers
        self.canvas.bind("<Button-1>", lambda e: self.do_pump_stroke())

    def _draw_pump(self):
        """Draws the animated mechanical pump cylinder, plunger handle, and hose."""
        self.canvas.delete("all")

        # Gauge background box
        self.canvas.create_rectangle(20, 150, 240, 168, fill="#2c2c2e", outline="#48484a")

        # Gauge fill bar
        fill_width = (self.current_volume / 100.0) * 218
        if self.current_volume < 40:
            bar_color = "#FF453A"
        elif self.current_volume < 75:
            bar_color = "#FF9F0A"
        else:
            bar_color = "#32D74B"

        if fill_width > 0:
            self.canvas.create_rectangle(
                21, 151, 21 + fill_width, 167, fill=bar_color, outline=""
            )

        # Pump base plate
        self.canvas.create_rectangle(90, 130, 170, 142, fill="#48484a", outline="#636366", width=2)

        # Pump cylinder barrel
        self.canvas.create_rectangle(115, 45, 145, 130, fill="#0A84FF", outline="#0040DD", width=2)
        self.canvas.create_line(120, 48, 120, 127, fill="#64D2FF", width=2)

        # Plunger rod & T-handle
        y_top = 20 + self.handle_offset
        y_rod_bot = 55 + self.handle_offset

        self.canvas.create_line(130, y_top, 130, y_rod_bot, fill="#AEAEB2", width=6)
        self.canvas.create_rectangle(
            95, y_top - 8, 165, y_top + 2, fill="#FF453A", outline="#8E201C", width=2
        )

        # Air hose
        self.canvas.create_line(145, 125, 190, 135, 210, 150, fill="#FFD60A", width=3, smooth=True)

    def show_hazard(self):
        """Called when 80% audio hazard drops volume."""
        self.current_volume = 0.0
        self.is_completed = False
        self.is_active = True
        self.last_tick_time = time.time()

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        pos_x = screen_w - self.width - 25
        pos_y = screen_h - self.height - 60

        self.geometry(f"{self.width}x{self.height}+{pos_x}+{pos_y}")
        self.deiconify()
        self.lift()

        self.title_label.config(text="[!] AUDIO COLLAPSED! [!]", fg="#FF3B30")
        self.vol_label.config(text="PRESSURE: 0%", fg="#FF9500")
        self.pump_btn.config(state="normal", text="PUMP IT! (MOUSE CLICK ONLY)", bg="#34C759")

        self._draw_pump()
        self._decay_loop()

    def do_pump_stroke(self):
        """Executed ONLY on mouse clicks."""
        if not self.is_active or self.is_completed:
            return

        # Animate handle push down
        self.handle_offset = 18
        self._draw_pump()
        self.after(60, self._release_handle)

        # Progressive diminishing returns logic
        v = self.current_volume
        if v < 25.0:
            gain = 8.0
        elif v < 55.0:
            gain = 5.0
        elif v < 75.0:
            gain = 3.0
        elif v < 90.0:
            gain = 1.8
        elif v < 96.0:
            gain = 1.0
        else:
            gain = 0.55

        self.current_volume = min(100.0, self.current_volume + gain)
        self.vol_label.config(text=f"PRESSURE: {int(self.current_volume)}%")

        if self.on_progress:
            self.on_progress(self.current_volume)

        if self.current_volume >= 100.0:
            self._handle_victory()

    def _release_handle(self):
        self.handle_offset = 0
        self._draw_pump()

    def _decay_loop(self):
        """Continuous decay loop running every 50ms while pump is active."""
        if not self.is_active or self.is_completed:
            return

        now = time.time()
        dt = now - self.last_tick_time
        self.last_tick_time = now

        if self.current_volume > 0:
            decay_amount = PUMP_DECAY_RATE_PER_SEC * dt
            self.current_volume = max(0.0, self.current_volume - decay_amount)
            self.vol_label.config(text=f"PRESSURE: {int(self.current_volume)}%")
            self._draw_pump()

            if self.on_progress:
                self.on_progress(self.current_volume)

        self.after(50, self._decay_loop)

    def _handle_victory(self):
        """User succeeded in pumping back to 100%."""
        self.is_completed = True

        self.title_label.config(text="SUCCESS: 100% RESTORED!", fg="#30D158")
        self.vol_label.config(text="MAX PRESSURE ACHIEVED!", fg="#30D158")
        self.pump_btn.config(state="disabled", text="DONE! ENJOY AUDIO", bg="#3a3a3c")
        self._draw_pump()

        if self.on_complete:
            self.on_complete()

        self.after(1200, self._dismiss)

    def _dismiss(self):
        self.is_active = False
        self.withdraw()

    def dismiss(self):
        """Immediately closes and resets the pump overlay."""
        self._dismiss()
