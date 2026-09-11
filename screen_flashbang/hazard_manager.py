"""
Extensible Periodic Visual Hazard Manager for Screen Flashbang Module.
Checks every minute (60s) for a 60% chance to trigger an active visual hazard.
Before triggering the flashbang, forces the display brightness to 100% and keeps it there.
Easily extensible for future pranks.
"""

import random
import tkinter as tk
from typing import Callable, List

from config import HAZARD_INTERVAL_SECONDS, FLASHBANG_CHANCE
from screen_flashbang.flashbang_overlay import FlashbangOverlay
from screen_flashbang.brightness_controller import force_maximum_brightness


class HazardManager:
    """
    Coordinates periodic random hazards.
    Checks every minute (60s) for a 60% chance to trigger an active hazard.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.is_running = False

        # Registry of hazard triggering functions for easy future extension
        self.hazard_registry: List[Callable[[], None]] = [
            self.trigger_flashbang,
        ]

    def start(self):
        self.is_running = True
        self._schedule_next_check()
        print(
            f"[HazardManager] Periodic hazard timer started (every {HAZARD_INTERVAL_SECONDS}s, {int(FLASHBANG_CHANCE * 100)}% chance)."
        )

    def stop(self):
        self.is_running = False

    def register_hazard(self, hazard_func: Callable[[], None]):
        """Allows registering future hazards into the pool."""
        self.hazard_registry.append(hazard_func)

    def _schedule_next_check(self):
        if not self.is_running:
            return
        interval_ms = int(HAZARD_INTERVAL_SECONDS * 1000)
        self.root.after(interval_ms, self._evaluate_hazard)

    def _evaluate_hazard(self):
        if not self.is_running:
            return

        roll = random.random()
        print(f"[HazardManager] Minute check: roll {roll:.3f} vs chance {FLASHBANG_CHANCE}")

        if roll < FLASHBANG_CHANCE and self.hazard_registry:
            selected_hazard = random.choice(self.hazard_registry)
            print(f"[HazardManager] Triggering hazard: {selected_hazard.__name__}")
            selected_hazard()

        self._schedule_next_check()

    def trigger_flashbang(self):
        """
        Sets display brightness to 100% first, then spawns the screen flashbang effect.
        Brightness is left at 100% permanently.
        """
        try:
            # 1. Force display brightness to 100%
            force_maximum_brightness()

            # 2. Spawn blinding white flashbang overlay
            FlashbangOverlay(self.root)
        except Exception as err:
            print(f"[HazardManager] Error spawning flashbang: {err}")
