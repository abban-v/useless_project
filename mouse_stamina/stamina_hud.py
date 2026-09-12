"""
Floating Mouse Stamina HUD for Mouse Stamina Module.
Follows mouse cursor with an unobtrusive click-through stamina bar.
White -> Orange -> Red color progression.
When exhausted:
- Displays 'RIP' on the bar
- Freezes mouse cursor completely for 1 minute
- Spawns BIG WHITE TEXT: 'ONE MOMENT OF SILENCE' overlay
- Refills bar back to 100% over the 1-minute period
"""

import time
import math
import ctypes
from ctypes import wintypes
import tkinter as tk
import win32gui
import win32con

from config import (
    MOUSE_MAX_STAMINA,
    MOUSE_DRAIN_PER_PIXEL,
    MOUSE_RECOVERY_RATE_PER_SEC,
    MOUSE_EXHAUSTED_RECOVERY_RATE_PER_SEC,
    MOMENT_OF_SILENCE_SECONDS,
    MOUSE_HUD_TICK_MS,
    STAMINA_COLOR_HIGH,
    STAMINA_COLOR_MID,
    STAMINA_COLOR_LOW,
    BAR_WIDTH,
    BAR_HEIGHT,
    BAR_Y_OFFSET,
)
from mouse_stamina.speed_controller import MouseSpeedController
from mouse_stamina.silence_overlay import SilenceOverlay

user32 = ctypes.windll.user32

SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
HWND_TOPMOST = -1
TRANSPARENT_COLOR_KEY = "#000001"

SetWindowPos = user32.SetWindowPos
SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
SetWindowPos.restype = wintypes.BOOL

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL


class MouseStaminaHUD(tk.Toplevel):
    """
    Floating stamina bar HUD rendered directly above the cursor.
    Click-through enabled so it never obstructs desktop interaction.
    """

    def __init__(self, master: tk.Tk, speed_ctrl: MouseSpeedController):
        super().__init__(master)
        self.speed_ctrl = speed_ctrl

        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        self.wm_attributes("-transparentcolor", TRANSPARENT_COLOR_KEY)

        self.bar_width = BAR_WIDTH
        self.bar_height = BAR_HEIGHT
        self.win_width = self.bar_width + 12
        self.win_height = self.bar_height + 16

        self.stamina = MOUSE_MAX_STAMINA
        self.is_exhausted = False
        self.exhausted_pulse = False
        self.silence_time_remaining = 0.0
        self.silence_overlay = None

        self.last_x, self.last_y = self._get_cursor_pos()
        self.last_time = time.time()
        self.hwnd = None

        self.last_drawn_stamina = -1.0
        self.last_drawn_state = None
        self.last_win_x = -99999
        self.last_win_y = -99999
        self._tick_id = None

        self._build_canvas()
        self._init_win32_styles()
        self._tick()

    def _get_cursor_pos(self):
        """Dual resolution cursor position retrieval: ctypes GetCursorPos + Tkinter pointer."""
        pt = POINT()
        if user32.GetCursorPos(ctypes.byref(pt)) and (pt.x != 0 or pt.y != 0):
            return pt.x, pt.y
        try:
            px = self.master.winfo_pointerx()
            py = self.master.winfo_pointery()
            return px, py
        except Exception:
            return self.last_x, self.last_y

    def _build_canvas(self):
        self.canvas = tk.Canvas(
            self,
            width=self.win_width,
            height=self.win_height,
            bg=TRANSPARENT_COLOR_KEY,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

    def _init_win32_styles(self):
        self.update()
        w_id = self.winfo_id()
        self.hwnd = win32gui.GetParent(w_id)
        if not self.hwnd:
            self.hwnd = w_id

        styles = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(
            self.hwnd,
            win32con.GWL_EXSTYLE,
            styles
            | win32con.WS_EX_LAYERED
            | win32con.WS_EX_TRANSPARENT
            | win32con.WS_EX_TOOLWINDOW
            | win32con.WS_EX_NOACTIVATE,
        )

    def _draw_bar(self):
        current_state = (self.is_exhausted, self.exhausted_pulse)
        if (
            self.last_drawn_state == current_state
            and abs(self.stamina - self.last_drawn_stamina) < 0.2
        ):
            return

        self.last_drawn_stamina = self.stamina
        self.last_drawn_state = current_state

        self.canvas.delete("all")

        x0, y0 = 6, 11
        x1, y1 = x0 + self.bar_width, y0 + self.bar_height

        # Dark border and backing
        self.canvas.create_rectangle(
            x0 - 1, y0 - 1, x1 + 1, y1 + 1, fill="#000000", outline="#3a3a3c", width=1
        )

        pct = max(0.0, min(1.0, self.stamina / MOUSE_MAX_STAMINA))
        fill_width = int(pct * self.bar_width)

        if self.is_exhausted:
            bar_color = "#FF2D55" if self.exhausted_pulse else "#8B0000"
            # Draw 'RIP' instead of 'TIRED!'
            self.canvas.create_text(
                x0 + self.bar_width // 2,
                y0 - 5,
                text="RIP",
                fill="#FF3B30",
                font=("Arial", 7, "bold"),
            )
        else:
            if self.stamina >= 50.0:
                bar_color = STAMINA_COLOR_HIGH
            elif self.stamina >= 20.0:
                bar_color = STAMINA_COLOR_MID
            else:
                bar_color = STAMINA_COLOR_LOW

        if fill_width > 0:
            self.canvas.create_rectangle(
                x0, y0, x0 + fill_width, y1, fill=bar_color, outline=""
            )

    def _enter_exhaustion(self, cur_x: int, cur_y: int):
        """Triggers the 1-minute moment of silence and freezes the cursor."""
        self.stamina = 0.0
        self.is_exhausted = True
        self.silence_time_remaining = MOMENT_OF_SILENCE_SECONDS

        # Freeze the mouse physically at current coordinates
        self.speed_ctrl.freeze_cursor(cur_x, cur_y)

        # Spawn 'ONE MOMENT OF SILENCE' overlay
        try:
            if self.silence_overlay and self.silence_overlay.winfo_exists():
                self.silence_overlay.dismiss()
            self.silence_overlay = SilenceOverlay(self.master, duration_seconds=MOMENT_OF_SILENCE_SECONDS)
        except Exception as err:
            print(f"[MouseStamina] Error spawning silence overlay: {err}")

    def _exit_exhaustion(self):
        """Releases the cursor freeze and restores normal movement."""
        self.stamina = MOUSE_MAX_STAMINA
        self.is_exhausted = False
        self.silence_time_remaining = 0.0

        self.speed_ctrl.unfreeze_cursor()
        self.speed_ctrl.restore_speed()

        if self.silence_overlay and self.silence_overlay.winfo_exists():
            self.silence_overlay.dismiss()
            self.silence_overlay = None

    def _tick(self):
        now = time.time()
        dt = max(0.001, now - self.last_time)
        self.last_time = now

        cur_x, cur_y = self._get_cursor_pos()

        if self.is_exhausted:
            # Recharging & Silent Freeze Phase
            self.speed_ctrl.enforce_freeze()
            cur_x, cur_y = self.speed_ctrl.freeze_x, self.speed_ctrl.freeze_y

            self.silence_time_remaining = max(0.0, self.silence_time_remaining - dt)
            if self.silence_overlay and self.silence_overlay.winfo_exists():
                self.silence_overlay.update_remaining(self.silence_time_remaining)

            # Steadily refill stamina across the 60s silence
            self.stamina += MOUSE_EXHAUSTED_RECOVERY_RATE_PER_SEC * dt
            self.exhausted_pulse = int(now * 4) % 2 == 0

            # Exit exhaustion when 60s completes or stamina reaches 100%
            if self.stamina >= MOUSE_MAX_STAMINA or self.silence_time_remaining <= 0.0:
                self._exit_exhaustion()
        else:
            dist = math.hypot(cur_x - self.last_x, cur_y - self.last_y)
            if dist > 1.2:
                drain = dist * MOUSE_DRAIN_PER_PIXEL
                self.stamina = max(0.0, self.stamina - drain)
                if self.stamina <= 0.0:
                    self._enter_exhaustion(cur_x, cur_y)
            else:
                self.stamina = min(
                    MOUSE_MAX_STAMINA, self.stamina + (MOUSE_RECOVERY_RATE_PER_SEC * dt)
                )

        self.last_x, self.last_y = cur_x, cur_y
        self._draw_bar()

        win_x = cur_x - (self.win_width // 2)
        win_y = cur_y + BAR_Y_OFFSET

        if win_x != self.last_win_x or win_y != self.last_win_y:
            self.last_win_x = win_x
            self.last_win_y = win_y
            if self.hwnd:
                SetWindowPos(
                    self.hwnd,
                    HWND_TOPMOST,
                    win_x,
                    win_y,
                    0,
                    0,
                    SWP_NOSIZE | SWP_NOACTIVATE,
                )
            else:
                self.geometry(f"+{win_x}+{win_y}")

        self._tick_id = self.after(MOUSE_HUD_TICK_MS, self._tick)

    def cleanup(self):
        """Cleanly cancels timers, dismisses silence overlay, and destroys the HUD."""
        if self._tick_id is not None:
            try:
                self.after_cancel(self._tick_id)
            except Exception:
                pass
            self._tick_id = None

        if self.silence_overlay and self.silence_overlay.winfo_exists():
            try:
                self.silence_overlay.dismiss()
            except Exception:
                pass
            self.silence_overlay = None

        try:
            self.destroy()
        except Exception:
            pass
