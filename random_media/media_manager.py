"""
Central Coordinator for Click Chaos Engine.
Manages mouse click hook, 60% chance evaluations for:
- 500 tiny bouncing cats with staggered spawning + meow track
- 50 spinning low-poly rats
- 4 soul-staring corner Furbys
- Concurrent music track chaos (independent 60% roll for each .m4a in music/)
"""

import random
import tkinter as tk
from typing import Optional

from config import CLICK_CHAOS_CHANCE, CLICK_MUSIC_CHANCE
from random_media.audio_chaos import ChaosAudioEngine
from random_media.chaos_overlay import ChaosOverlay
from random_media.click_listener import ClickListener
from random_media.reddit_memes import get_reddit_fetcher


class MediaChaosManager:
    """
    Coordinates click-triggered chaotic media popups and multi-track audio.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.audio_engine = ChaosAudioEngine(root)
        self.overlay = ChaosOverlay(root, self.audio_engine)
        self.listener = ClickListener(on_click_callback=self._on_mouse_click)
        self.meme_fetcher = get_reddit_fetcher()
        self.is_running = False

    def start(self):
        """Starts listening for mouse clicks system-wide and starts meme caching."""
        self.is_running = True
        self.meme_fetcher.start_background_worker()
        self.listener.start()
        print("[MediaChaosManager] Click Chaos Engine ACTIVE (60% event chances on every click).")

    def stop(self):
        """Cleanly stops listener, meme worker, halts all audio, and destroys overlay."""
        self.is_running = False
        self.listener.stop()
        self.meme_fetcher.stop()
        self.audio_engine.stop_all()
        self.overlay.clear_all()
        print("[MediaChaosManager] Click Chaos Engine STOPPED.")

    def _on_mouse_click(self):
        """Dispatched from low-level mouse hook on left/right click."""
        if not self.is_running:
            return
        # Post to Tkinter root event loop
        self.root.after(0, self._evaluate_click_chaos)

    def _evaluate_click_chaos(self):
        """Evaluates independent 60% chances for each chaos event."""
        if not self.is_running:
            return

        cat_hit = False
        rat_hit = False
        furby_hit = False

        # 1. 60% Chance for 500 Tiny Bouncing Cats
        cat_roll = random.random()
        if cat_roll < CLICK_CHAOS_CHANCE:
            print(f"[MediaChaos] 60% CATS HIT! (roll: {cat_roll:.3f}) Spawning 500 bouncing cats...")
            self.overlay.spawn_cats()
            cat_hit = True

        # 2. 60% Chance for 50 Spinning Low-Poly Rats
        rat_roll = random.random()
        if rat_roll < CLICK_CHAOS_CHANCE:
            print(f"[MediaChaos] 60% RATS HIT! (roll: {rat_roll:.3f}) Spawning 50 spinning rats...")
            self.overlay.spawn_rats()
            rat_hit = True

        # 3. 60% Chance for 4 Corner Furbys
        furby_roll = random.random()
        if furby_roll < CLICK_CHAOS_CHANCE:
            print(f"[MediaChaos] 60% FURBYS HIT! (roll: {furby_roll:.3f}) Spawning 4 corner Furbys...")
            self.overlay.spawn_furbys()
            furby_hit = True

        # 4. 2-5 Small Rectangular Video Frames (only active if cats, rats, or furbys are active)
        if cat_hit or rat_hit or furby_hit or self.overlay.has_active_visuals():
            self.overlay.spawn_video_frames()

        # 5. Independent 60% Chance for each music track in music/ (excluding meow.m4a)
        self.audio_engine.roll_music_chaos(CLICK_MUSIC_CHANCE)


    def is_chaos_audio_playing(self) -> bool:
        """Returns True if any chaos audio track or meow is currently active."""
        return self.audio_engine.is_chaos_audio_playing()
