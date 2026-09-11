"""
Silence Overlay for Mouse Stamina Module.
Displays extremely informal, raw white Arial 72pt text: 'ONE MOMENT OF SILENCE'
floating directly across the screen with no borders or fancy containers.
"""

import tkinter as tk
import win32gui
import win32con

TRANSPARENT_COLOR_KEY = "#000001"


class SilenceOverlay(tk.Toplevel):
    """
    Informal overlay displaying giant raw Arial text: 'ONE MOMENT OF SILENCE'
    """

    def __init__(self, master: tk.Tk, duration_seconds: float = 60.0):
        super().__init__(master)
        self.duration_seconds = duration_seconds
        self.remaining_seconds = duration_seconds

        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        self.wm_attributes("-transparentcolor", TRANSPARENT_COLOR_KEY)

        self.screen_w = self.winfo_screenwidth()
        self.screen_h = self.winfo_screenheight()

        # Scale font size slightly on smaller laptop screens so it never overflows
        if self.screen_w >= 1400:
            self.font_size = 72
        elif self.screen_w >= 1200:
            self.font_size = 60
        else:
            self.font_size = 48

        self.height = 240
        pos_y = (self.screen_h - self.height) // 2

        self.geometry(f"{self.screen_w}x{self.height}+0+{pos_y}")

        self._build_ui()
        self._init_win32_styles()

    def _build_ui(self):
        self.configure(bg=TRANSPARENT_COLOR_KEY)

        self.canvas = tk.Canvas(
            self,
            width=self.screen_w,
            height=self.height,
            bg=TRANSPARENT_COLOR_KEY,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self._redraw_text()

    def _init_win32_styles(self):
        self.update()
        w_id = self.winfo_id()
        hwnd = win32gui.GetParent(w_id)
        if not hwnd:
            hwnd = w_id

        # Make window click-through, toolwindow, no-activate
        styles = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(
            hwnd,
            win32con.GWL_EXSTYLE,
            styles
            | win32con.WS_EX_LAYERED
            | win32con.WS_EX_TRANSPARENT
            | win32con.WS_EX_TOOLWINDOW
            | win32con.WS_EX_NOACTIVATE,
        )

    def _redraw_text(self):
        self.canvas.delete("all")

        cx = self.screen_w // 2
        cy = 90

        # Subtle dark shadow outline so white text stays readable on white apps
        for ox, oy in [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, 3)]:
            self.canvas.create_text(
                cx + ox,
                cy + oy,
                text="ONE MOMENT OF SILENCE",
                font=("Arial", self.font_size),
                fill="#000000",
            )

        # Raw massive white Arial text (like Word cranked to 72)
        self.canvas.create_text(
            cx,
            cy,
            text="ONE MOMENT OF SILENCE",
            font=("Arial", self.font_size),
            fill="#FFFFFF",
        )

        # Informal raw countdown below
        secs = max(0, int(self.remaining_seconds))
        countdown_str = f"({secs} seconds remaining)"

        self.canvas.create_text(
            cx + 1, cy + 71, text=countdown_str, font=("Arial", 18), fill="#000000"
        )
        self.canvas.create_text(
            cx, cy + 70, text=countdown_str, font=("Arial", 18), fill="#FFFFFF"
        )

    def update_remaining(self, seconds_left: float):
        """Updates remaining seconds countdown."""
        self.remaining_seconds = max(0.0, seconds_left)
        if self.canvas.winfo_exists():
            self._redraw_text()

    def dismiss(self):
        """Cleanly destroys overlay."""
        try:
            self.destroy()
        except Exception:
            pass
