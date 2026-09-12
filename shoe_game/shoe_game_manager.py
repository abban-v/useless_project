"""
Shoe Game Manager for Shoe Game Module.
Periodically (every 60s) rolls a 40% chance to launch the non-closable fullscreen Shoe Game.
Randomly alternates between:
- Virtual Mode: 2D comic shoerack pan, leg intrusion, scream, and 'SAVE THE SHOE!' walking hurdles.
- Real Mode: Pitch-black window with 'shoes can't think' blasted with music tracks for 10s.
"""

import random
import tkinter as tk
from typing import Optional

import config
from shoe_game.choice_screen import ShoeGameChoiceScreen
from shoe_game.virtual_mode import VirtualShoeGame
from shoe_game.real_mode import RealShoeGame


class ShoeGameManager:
    """
    Coordinates periodic evaluation and spawning of the Shoe Game.
    Dynamically tracks chance and interval settings.
    Presents the fullscreen 'SHOE GAME' choice screen allowing selection between
    Virtual Mode and Real Mode.
    """

    def __init__(
        self,
        root: tk.Tk,
        audio_ctrl=None,
        audio_monitor=None,
        pump_overlay=None,
        chance: Optional[float] = None,
        interval_seconds: Optional[float] = None,
    ):
        self.root = root
        self.audio_ctrl = audio_ctrl
        self.audio_monitor = audio_monitor
        self.pump_overlay = pump_overlay
        self._custom_chance = chance
        self._custom_interval = interval_seconds
        self.is_running = False
        self.active_game = None
        self._timer_id: Optional[str] = None

    @property
    def chance(self) -> float:
        if self._custom_chance is not None:
            return float(self._custom_chance)
        return float(getattr(config, "SHOE_GAME_CHANCE", 0.40))

    @chance.setter
    def chance(self, val: float):
        self._custom_chance = float(val)

    @property
    def interval_seconds(self) -> float:
        if self._custom_interval is not None:
            return float(self._custom_interval)
        return float(getattr(config, "SHOE_GAME_INTERVAL_SECONDS", 60.0))

    @interval_seconds.setter
    def interval_seconds(self, val: float):
        self._custom_interval = float(val)

    def start(self, initial_delay_seconds: Optional[float] = None):
        """Starts periodic evaluation checks."""
        self.is_running = True
        if initial_delay_seconds is not None:
            delay = initial_delay_seconds
        elif self.chance >= 1.0:
            # Immediate testing convenience: launch within 1.5 seconds instead of waiting 60 seconds
            delay = 1.5
        else:
            delay = self.interval_seconds

        self._schedule_check(delay_seconds=delay)
        print(
            f"[ShoeGameManager] Periodic Shoe Game timer started (every {self.interval_seconds}s, {int(self.chance * 100)}% chance)."
        )

    def stop(self):
        """Cleanly terminates timer and closes any active shoe game or choice screen."""
        self.is_running = False
        if self._timer_id is not None:
            try:
                self.root.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

        if self.active_game is not None:
            try:
                if hasattr(self.active_game, "dismiss"):
                    self.active_game.dismiss()
                else:
                    self.active_game.destroy()
            except Exception:
                pass
            self.active_game = None

    def _schedule_check(self, delay_seconds: Optional[float] = None):
        if not self.is_running:
            return
        sec = delay_seconds if delay_seconds is not None else self.interval_seconds
        interval_ms = max(100, int(sec * 1000))
        self._timer_id = self.root.after(interval_ms, self._evaluate_roll)

    def _evaluate_roll(self):
        if not self.is_running:
            return

        # Do not launch a new game if one is already currently open or if an ad is active
        if self.active_game is not None:
            self._schedule_check()
            return

        if hasattr(self, "ad_manager") and self.ad_manager and getattr(self.ad_manager, "is_ad_active", False):
            self._schedule_check()
            return

        cur_chance = self.chance
        roll = random.random()
        print(f"[ShoeGameManager] Minute check: roll {roll:.3f} vs chance {cur_chance:.2f}")

        if roll < cur_chance or cur_chance >= 1.0:
            self.launch_game()

        self._schedule_check()

    def launch_game(self, mode: Optional[str] = None):
        """
        Launches the fullscreen Shoe Game.
        If mode is None or 'choice', presents the ShoeGameChoiceScreen with heading 'SHOE GAME'.
        Otherwise launches the requested mode ('virtual' or 'real') directly.
        """
        if self.active_game is not None:
            return

        cur_chance = self.chance
        if mode in ("virtual", "real"):
            self._start_mode(mode)
        else:
            print(f"[ShoeGameManager] {int(cur_chance * 100)}% HIT! Launching Shoe Game Choice Screen...")
            self.active_game = ShoeGameChoiceScreen(
                master=self.root,
                on_select_mode=self._on_mode_selected,
            )

    def _on_mode_selected(self, mode: str):
        """Called when player selects a mode on the ShoeGameChoiceScreen."""
        self.active_game = None
        self._start_mode(mode)

    def _start_mode(self, mode: str):
        """Starts the chosen Shoe Game mode fullscreen."""
        print(f"[ShoeGameManager] Starting Shoe Game in [{mode.upper()} MODE] fullscreen!")

        # Suppress audio monitor and dismiss pump overlay so shoe audio plays without triggering pump volume drops
        if self.audio_monitor is not None:
            suppress_dur = (
                getattr(config, "SHOE_GAME_VIRTUAL_MODE_SECONDS", 20.0) + 5.0
                if mode == "virtual"
                else getattr(config, "SHOE_GAME_REAL_MODE_SECONDS", 10.0) + 5.0
            )
            try:
                self.audio_monitor.suppress_for(suppress_dur)
                self.audio_monitor.dismiss_hazard()
            except Exception:
                pass

        if self.pump_overlay is not None:
            try:
                self.pump_overlay.dismiss()
            except Exception:
                pass

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

    def force_launch(self, mode: Optional[str] = None):
        """Convenience method to immediately trigger shoe game without waiting."""
        self.launch_game(mode)

    def _on_game_finished(self):
        self.active_game = None
        print("[ShoeGameManager] Shoe Game completed. Main application continuing normally.")
