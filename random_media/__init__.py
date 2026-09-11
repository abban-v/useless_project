"""
Click-Triggered Random Media Chaos Module for Useless Project.
Coordinates 60% chance click hazards:
- 500 tiny bouncing cats with staggered spawning & meow sound
- 50 spinning low-poly rats
- 4 soul-staring corner Furbys
- Multi-track simultaneous ambient chaos music
"""

from random_media.media_manager import MediaChaosManager
from random_media.audio_chaos import (
    ChaosAudioEngine,
    is_chaos_audio_playing,
    stop_all_chaos_audio,
)
from random_media.chaos_overlay import ChaosOverlay
from random_media.click_listener import ClickListener
from random_media.reddit_memes import RedditMemeFetcher, get_reddit_fetcher

__all__ = [
    "MediaChaosManager",
    "ChaosAudioEngine",
    "ChaosOverlay",
    "ClickListener",
    "RedditMemeFetcher",
    "get_reddit_fetcher",
    "is_chaos_audio_playing",
    "stop_all_chaos_audio",
]
