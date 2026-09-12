"""
Extensible Periodic Visual Hazard Manager for Screen Flashbang Module.
Checks every minute (60s) for a 60% chance to trigger an active visual hazard.
When the flashbang triggers:
- Display brightness is forced to 100% and kept there
- If volume is below 100%, it is boosted to 100%
- Plays 'memes/audioloud.mp3'
- Spawns the blinding white screen overlay with smooth fadeout
"""

import random
import tkinter as tk
from typing import Callable, List, Optional

import config
from screen_flashbang.flashbang_overlay import FlashbangOverlay
from screen_flashbang.brightness_controller import force_maximum_brightness
from screen_flashbang.audio_player import play_flashbang_audio
from screen_flashbang.action_key_blocker import FlashbangActionKeyBlocker


class HazardManager:
    """
    Coordinates periodic random hazards.
    Dynamically tracks chance and interval settings.
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
        self._timer_id: Optional[str] = None

        # Lazy load audio_ctrl if not provided
        if self.audio_ctrl is None:
            try:
                from audio_pump.audio_controller import WindowsAudioController
                self.audio_ctrl = WindowsAudioController()
            except Exception:
                pass

        # Action key & volume lock blocker active during flashbang audio
        self.key_blocker = FlashbangActionKeyBlocker(self.audio_ctrl)

        # Registry of hazard triggering functions for easy future extension
        self.hazard_registry: List[Callable[[], None]] = [
            self.trigger_flashbang,
        ]

    @property
    def chance(self) -> float:
        if self._custom_chance is not None:
            return float(self._custom_chance)
        return float(getattr(config, "FLASHBANG_CHANCE", 0.70))

    @chance.setter
    def chance(self, val: float):
        self._custom_chance = float(val)

    @property
    def interval_seconds(self) -> float:
        if self._custom_interval is not None:
            return float(self._custom_interval)
        return float(getattr(config, "HAZARD_INTERVAL_SECONDS", 30.0))

    @interval_seconds.setter
    def interval_seconds(self, val: float):
        self._custom_interval = float(val)

    def start(self, initial_delay_seconds: Optional[float] = None):
        self.is_running = True
        if initial_delay_seconds is not None:
            delay = initial_delay_seconds
        elif self.chance >= 1.0:
            delay = 1.5  # Immediate prompt check for 100% testing
        else:
            delay = self.interval_seconds

        self._schedule_next_check(delay_seconds=delay)
        print(
            f"[HazardManager] Periodic hazard timer started (every {self.interval_seconds}s, {int(self.chance * 100)}% chance)."
        )

    def stop(self):
        self.is_running = False
        if self._timer_id is not None:
            try:
                self.root.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

        if hasattr(self, "key_blocker"):
            self.key_blocker.stop()

    def register_hazard(self, hazard_func: Callable[[], None]):
        """Allows registering future hazards into the pool."""
        self.hazard_registry.append(hazard_func)

    def _schedule_next_check(self, delay_seconds: Optional[float] = None):
        if not self.is_running:
            return
        sec = delay_seconds if delay_seconds is not None else self.interval_seconds
        interval_ms = max(100, int(sec * 1000))
        self._timer_id = self.root.after(interval_ms, self._evaluate_hazard)

    def _evaluate_hazard(self):
        if not self.is_running:
            return

        # Do not interrupt or blast audio over active fullscreen ads
        if hasattr(self, "ad_manager") and self.ad_manager and getattr(self.ad_manager, "is_ad_active", False):
            self._schedule_next_check()
            return

        cur_chance = self.chance
        roll = random.random()
        print(f"[HazardManager] Periodic check: roll {roll:.3f} vs chance {cur_chance:.2f}")

        if (roll < cur_chance or cur_chance >= 1.0) and self.hazard_registry:
            selected_hazard = random.choice(self.hazard_registry)
            print(f"[HazardManager] Triggering hazard: {selected_hazard.__name__}")
            selected_hazard()

        self._schedule_next_check()

    def trigger_flashbang(self):
        """
        1. Suppresses audio monitor so meme audio does NOT trigger audio pump drops.
        2. Sets display brightness to 100% and keeps it there.
        3. Sets master volume to 100% and unmutes it.
        4. Blocks action keys and enforces 100% volume against lowering attempts.
        5. Plays 'memes/audioloud.mp3'.
        6. Spawns the blinding white screen overlay.
        """
        try:
            # 1. Suppress audio monitor and dismiss any active pump minigame
            if self.audio_monitor is not None:
                self.audio_monitor.suppress_for(14.0)
                self.audio_monitor.dismiss_hazard()
            if self.pump_overlay is not None:
                self.pump_overlay.dismiss()

            # 2. Force display brightness to 100%
            force_maximum_brightness()

            # 3. Boost volume to 100% and ensure unmuted
            if self.audio_ctrl is not None:
                try:
                    self.audio_ctrl.set_mute(False)
                    cur_vol = self.audio_ctrl.get_volume()
                    if cur_vol < 1.0:
                        print(f"[HazardManager] Volume was {cur_vol * 100:.0f}%, boosting to 100%!")
                        self.audio_ctrl.set_volume(1.0)
                except Exception as vol_err:
                    print(f"[HazardManager] Volume boost error: {vol_err}")

            # 4. Block action keys and clamp volume at 100% so user cannot lower it
            if hasattr(self, "key_blocker"):
                self.key_blocker.start()

            # 5. Play memes/audioloud.mp3 (loud meme audio)
            play_flashbang_audio()

            # 6. Spawn blinding white flashbang overlay
            FlashbangOverlay(self.root)
        except Exception as err:
            print(f"[HazardManager] Error spawning flashbang: {err}")
