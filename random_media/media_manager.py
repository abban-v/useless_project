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

import config
from config import CLICK_CHAOS_CHANCE, CLICK_MUSIC_CHANCE, KEYBOARD_SOUND_CHANCE
from random_media.audio_chaos import ChaosAudioEngine, is_chaos_audio_blocked
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
        self.is_ad_active = False

    def start(self):
        """Starts listening for mouse clicks system-wide and starts meme caching."""
        self.is_running = True
        self.meme_fetcher.start_background_worker()
        self.listener.start()
        print("[MediaChaosManager] Click Chaos Engine ACTIVE (memes on click, 30% sounds on key press).")

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
        if not self.is_running or self.is_ad_active or is_chaos_audio_blocked():
            return
        # Post to Tkinter root event loop
        self.root.after(0, self._evaluate_click_chaos)

    def _evaluate_click_chaos(self):
        """Evaluates 60% chance for meme frames and ambient music on click (cats & rats removed)."""
        if not self.is_running or self.is_ad_active or is_chaos_audio_blocked():
            return

        # 1. 60% Chance for 2-5 Small Rectangular Meme/Video Frames
        meme_roll = random.random()
        chance = getattr(config, "CLICK_CHAOS_CHANCE", CLICK_CHAOS_CHANCE)
        if meme_roll < chance:
            print(f"[MediaChaos] {int(chance * 100)}% MEMES HIT! (roll: {meme_roll:.3f}) Spawning meme frames...")
            self.overlay.spawn_video_frames()

        # 2. Independent 60% Chance for each music track in music/ (excluding meow.m4a)
        music_chance = getattr(config, "CLICK_MUSIC_CHANCE", CLICK_MUSIC_CHANCE)
        self.audio_engine.roll_music_chaos(music_chance)

    def _on_keyboard_key(self):
        """Dispatched from keyboard hook when a typing key is clicked."""
        if not self.is_running or self.is_ad_active or is_chaos_audio_blocked():
            return
        # Post to Tkinter root event loop
        self.root.after(0, self._evaluate_keyboard_chaos)

    def _evaluate_keyboard_chaos(self):
        """30% chance on each keyboard click to play any sound in music/ folder."""
        if not self.is_running or self.is_ad_active or is_chaos_audio_blocked():
            return

        kb_chance = getattr(config, "KEYBOARD_SOUND_CHANCE", KEYBOARD_SOUND_CHANCE)
        roll = random.random()
        if roll < kb_chance:
            self.audio_engine.play_random_sound()



    def is_chaos_audio_playing(self) -> bool:
        """Returns True if any chaos audio track or meow is currently active."""
        return self.audio_engine.is_chaos_audio_playing()
