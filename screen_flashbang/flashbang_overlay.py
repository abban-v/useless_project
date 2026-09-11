"""
Full-Screen Whiteout Flashbang Overlay for Screen Flashbang Module.
Flashes 100% white across the display and smoothly fades back to desktop over 2.5 seconds.
"""

import tkinter as tk
from config import FLASHBANG_FADE_SECONDS, FLASHBANG_HOLD_SECONDS


class FlashbangOverlay(tk.Toplevel):
    """
    Full-screen blinding flashbang overlay.
    Flashes 100% white and gradually fades back to desktop.
    """

    def __init__(self, master: tk.Tk):
        super().__init__(master)

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        self.geometry(f"{screen_w}x{screen_h}+0+0")
        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        self.wm_attributes("-alpha", 1.0)
        self.configure(bg="#FFFFFF")

        self.canvas = tk.Canvas(
            self,
            width=screen_w,
            height=screen_h,
            bg="#FFFFFF",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.current_alpha = 1.0
        self.fade_steps = int(FLASHBANG_FADE_SECONDS * 33)  # ~30 FPS fade
        self.alpha_step = 1.0 / max(1, self.fade_steps)

        # Hold peak flash, then begin smooth fadeout
        hold_ms = int(FLASHBANG_HOLD_SECONDS * 1000)
        self.after(hold_ms, self._fade_step)

    def _fade_step(self):
        self.current_alpha -= self.alpha_step
        if self.current_alpha <= 0.02:
            self.destroy()
        else:
            try:
                self.wm_attributes("-alpha", max(0.0, self.current_alpha))
                self.after(30, self._fade_step)
            except Exception:
                self.destroy()
