"""
Screen Flashbang Module for Useless Project.
Coordinates periodic minute timer, 60% chance evaluation, 100% display brightness blasting,
and fullscreen flashbang whiteout.
"""

from screen_flashbang.flashbang_overlay import FlashbangOverlay
from screen_flashbang.hazard_manager import HazardManager
from screen_flashbang.brightness_controller import force_maximum_brightness

__all__ = ["FlashbangOverlay", "HazardManager", "force_maximum_brightness"]
