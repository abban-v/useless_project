"""
Screen Flashbang Module for Useless Project.
Coordinates periodic minute timer, 60% chance evaluation, 100% display brightness blasting,
100% volume boosting, 'memes/audioloud.mp3' playback, and fullscreen flashbang whiteout.
"""

from screen_flashbang.flashbang_overlay import FlashbangOverlay
from screen_flashbang.hazard_manager import HazardManager
from screen_flashbang.brightness_controller import force_maximum_brightness
from screen_flashbang.action_key_blocker import FlashbangActionKeyBlocker
from screen_flashbang.audio_player import (
    play_flashbang_audio,
    stop_flashbang_audio,
    is_flashbang_audio_playing,
)

__all__ = [
    "FlashbangOverlay",
    "HazardManager",
    "force_maximum_brightness",
    "FlashbangActionKeyBlocker",
    "play_flashbang_audio",
    "stop_flashbang_audio",
    "is_flashbang_audio_playing",
]
