"""
Real Mode for Shoe Game Module.
Opens a fullscreen pitch-black window for 10 seconds with laughable text:
'shoes can't think'
Blasts all music tracks concurrently at 100% volume with volume lock.
Automatically closes after 10 seconds and restores normal system state.
"""

import tkinter as tk
from typing import Callable, Optional

from config import SHOE_GAME_REAL_MODE_SECONDS
from shoe_game.audio_enforcer import ShoeAudioEnforcer


class RealShoeGame(tk.Toplevel):
    """
    Fullscreen black window displaying 'shoes can't think' while blasted with audio.
    """

    def __init__(
        self,
        master: tk.Tk,
        audio_ctrl=None,
        on_finish: Optional[Callable[[], None]] = None,
        duration_seconds: float = SHOE_GAME_REAL_MODE_SECONDS,
    ):
        super().__init__(master)
        self.audio_ctrl = audio_ctrl
        self.on_finish = on_finish
        self.duration_seconds = duration_seconds
        self.audio_enforcer = ShoeAudioEnforcer(self.audio_ctrl, master=master)

        self.screen_w = self.winfo_screenwidth()
        self.screen_h = self.winfo_screenheight()

        # Non-closable fullscreen
        self.geometry(f"{self.screen_w}x{self.screen_h}+0+0")
        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.configure(bg="#000000")

        self.canvas = tk.Canvas(
            self,
            width=self.screen_w,
            height=self.screen_h,
            bg="#000000",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.focus_set()

        self._block_closing()
        self._render_stupid_text()

        # Blast all music tracks at 100% locked volume
        self.audio_enforcer.play_all_music(duration=self.duration_seconds)

        # Automatically dismiss after duration
        self._dismiss_after_id = self.after(int(self.duration_seconds * 1000), self.dismiss)

    def _block_closing(self):
        """Disables standard window closing shortcuts (Alt+F4, Esc)."""
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.bind("<Escape>", lambda e: "break")
        self.bind("<Alt-F4>", lambda e: "break")
        self.canvas.bind("<Escape>", lambda e: "break")
        self.canvas.bind("<Alt-F4>", lambda e: "break")

    def _render_stupid_text(self):
        """Draws the laughable, ultra-stupid text across the black void."""
        cx = self.screen_w // 2
        cy = self.screen_h // 2

        # Comic / laughable font selection
        font_family = "Comic Sans MS"
        try:
            # Check available font families
            avail = tk.font.families()
            if "Comic Sans MS" in avail:
                font_family = "Comic Sans MS"
            elif "Jokerman" in avail:
                font_family = "Jokerman"
            elif "Papyrus" in avail:
                font_family = "Papyrus"
        except Exception:
            font_family = "Comic Sans MS"

        # Shadow text for ridiculous contrast
        self.canvas.create_text(
            cx + 4,
            cy + 4,
            text="shoes can't think",
            font=(font_family, 54, "bold"),
            fill="#333333",
        )
        # Giant raw white text
        self.canvas.create_text(
            cx,
            cy,
            text="shoes can't think",
            font=(font_family, 54, "bold"),
            fill="#FFFFFF",
        )

        # Absurd subtitle
        self.canvas.create_text(
            cx,
            cy + 90,
            text="(they have no brain cells. obviously.)",
            font=("Arial", 16, "italic"),
            fill="#888888",
        )

        # ASCII / unicode shoe art
        self.canvas.create_text(
            cx,
            cy - 100,
            text="___/\n/__/\n|__|",
            font=("Consolas", 20, "bold"),
            fill="#00FFCC",
        )

    def dismiss(self):
        """Halts all audio, unlocks volume, and destroys the window."""
        try:
            if hasattr(self, "_dismiss_after_id") and self._dismiss_after_id:
                self.after_cancel(self._dismiss_after_id)
                self._dismiss_after_id = None
        except Exception:
            pass

        try:
            self.audio_enforcer.stop_all_audio()
        except Exception:
            pass

        try:
            self.destroy()
        except Exception:
            pass

        if self.on_finish:
            try:
                self.on_finish()
            except Exception:
                pass
