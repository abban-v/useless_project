"""
Shoe Game Manager for Shoe Game Module.
Periodically (every 60s) rolls a 40% chance to launch the non-closable fullscreen Shoe Game.
Randomly alternates between:
- Virtual Mode: 2D comic shoerack pan, leg intrusion, scream, and 'SAVE THE LEAF!' walking hurdles.
- Real Mode: Pitch-black window with 'shoes can't think' blasted with music tracks for 10s.
"""

import random
import tkinter as tk
from typing import Optional

from config import SHOE_GAME_INTERVAL_SECONDS, SHOE_GAME_CHANCE
from shoe_game.virtual_mode import VirtualShoeGame
from shoe_game.real_mode import RealShoeGame


class ShoeGameManager:
    """
    Coordinates periodic evaluation and spawning of the Shoe Game.
    """

    def __init__(self, root: tk.Tk, audio_ctrl=None):
        self.root = root
        self.audio_ctrl = audio_ctrl
        self.is_running = False
        self.active_game = None
        self._timer_id: Optional[str] = None

    def start(self):
        """Starts periodic 60-second evaluation checks."""
        self.is_running = True
        self._schedule_check()
        print(
            f"[ShoeGameManager] Periodic Shoe Game timer started (every {SHOE_GAME_INTERVAL_SECONDS}s, {int(SHOE_GAME_CHANCE * 100)}% chance)."
        )

    def stop(self):
        """Cleanly terminates timer and closes any active shoe game."""
        self.is_running = False
        if self._timer_id is not None:
            try:
                self.root.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

        if self.active_game is not None:
            try:
                self.active_game.dismiss()
            except Exception:
                pass
            self.active_game = None

    def _schedule_check(self):
        if not self.is_running:
            return
        interval_ms = int(SHOE_GAME_INTERVAL_SECONDS * 1000)
        self._timer_id = self.root.after(interval_ms, self._evaluate_roll)

    def _evaluate_roll(self):
        if not self.is_running:
            return

        # Do not launch a new game if one is already currently open
        if self.active_game is not None:
            self._schedule_check()
            return

        roll = random.random()
        print(f"[ShoeGameManager] Minute check: roll {roll:.3f} vs chance {SHOE_GAME_CHANCE}")

        if roll < SHOE_GAME_CHANCE:
            mode = "virtual" if random.random() < 0.5 else "real"
            self.launch_game(mode)

        self._schedule_check()

    def launch_game(self, mode: str = "virtual"):
        """Launches the fullscreen Shoe Game in the specified mode ('virtual' or 'real')."""
        if self.active_game is not None:
            return

        print(f"[ShoeGameManager] 40% HIT! Launching Shoe Game in [{mode.upper()} MODE] fullscreen!")

        if mode == "virtual":
            self.active_game = VirtualShoeGame(
                self.root,
                audio_ctrl=self.audio_ctrl,
                on_finish=self._on_game_finished,
            )
        else:
            self.active_game = RealShoeGame(
                self.root,
                audio_ctrl=self.audio_ctrl,
                on_finish=self._on_game_finished,
            )

    def _on_game_finished(self):
        self.active_game = None
        print("[ShoeGameManager] Shoe Game completed. Returned to desktop.")
