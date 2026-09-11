"""
Multi-Track Chaos Audio Engine for Click Chaos Module.
Plays 'music/meow.m4a' on cat spawn thresholds and manages independent 60% chance
playback of all ambient chaos tracks (coconut.m4a, scream.m4a, scream2.m4a, song.m4a)
concurrently using native Windows COM WMPlayer.OCX dispatched via the Tkinter message loop.
"""

import os
import random
import time
import tkinter as tk
from pathlib import Path
from typing import List, Optional
import win32com.client

from config import CLICK_MUSIC_CHANCE

MUSIC_DIR = Path(__file__).parent.parent / "music"
MEOW_PATH = MUSIC_DIR / "meow.m4a"

_active_engines = set()


def is_chaos_audio_playing() -> bool:
    """Returns True if any ChaosAudioEngine is currently playing tracks."""
    for eng in list(_active_engines):
        if eng.is_chaos_audio_playing():
            return True
    return False


def stop_all_chaos_audio():
    """Stops all active ChaosAudioEngine instances."""
    for eng in list(_active_engines):
        eng.stop_all()


class ChaosAudioEngine:
    """
    Manages concurrent multi-track audio playback for the Click Chaos module.
    Runs on the Tkinter main thread message loop so WMPlayer.OCX can transition
    to playing state immediately without apartment deadlocks or threading issues.
    """

    def __init__(self, master: Optional[tk.Tk] = None):
        self.master = master or getattr(tk, "_default_root", None)
        self._active_players: List[any] = []
        self._active_music_players: List[any] = []
        self._playback_end_time = 0.0
        self._music_playback_end_time = 0.0
        self._last_meow_time = 0.0
        self._polling = False
        _active_engines.add(self)

    def play_track(self, file_path: str, duration: float = 10.0, is_music: bool = False):
        """Dispatches track playback onto Tkinter's message-pumped main thread."""
        self._playback_end_time = max(self._playback_end_time, time.time() + duration)
        if is_music:
            self._music_playback_end_time = max(self._music_playback_end_time, time.time() + duration)
        if self.master:
            try:
                self.master.after(0, self._play_track_on_main, file_path, duration, is_music)
            except Exception:
                pass

    def _play_track_on_main(self, file_path: str, duration: float, is_music: bool = False):
        """Instantiates and starts WMPlayer.OCX on the main thread."""
        if not os.path.exists(file_path):
            return

        try:
            player = win32com.client.Dispatch("WMPlayer.OCX")
            player.settings.volume = 100
            player.URL = file_path
            player.controls.play()

            self._active_players.append(player)
            if is_music:
                self._active_music_players.append(player)
                self._music_playback_end_time = max(self._music_playback_end_time, time.time() + duration)
            self._playback_end_time = max(self._playback_end_time, time.time() + duration)

            if not self._polling and self.master:
                self._polling = True
                self.master.after(200, self._poll_players)
        except Exception as err:
            print(f"[ChaosAudio] Playback dispatch error for {file_path}: {err}")

    def _poll_players(self):
        """Periodically cleans up finished or stopped WMP players."""
        alive = []
        for p in self._active_players:
            try:
                state = p.playState
                # 3 = wmppsPlaying, 9 = wmppsTransitioning, 6 = wmppsBuffering
                if state in (3, 9, 6):
                    alive.append(p)
                else:
                    p.controls.stop()
                    p.close()
            except Exception:
                pass

        self._active_players = alive
        self._active_music_players = [p for p in self._active_music_players if p in alive]
        if self._active_players and self.master:
            self.master.after(250, self._poll_players)
        else:
            self._polling = False

    def play_meow(self):
        """Plays music/meow.m4a on cat spawn threshold."""
        now = time.time()
        # Allow natural overlapping meows while preventing runaway instantiation
        if now - self._last_meow_time > 0.35:
            self._last_meow_time = now
            self.play_track(str(MEOW_PATH.resolve()), 3.0, is_music=False)

    def roll_music_chaos(self, chance: float = CLICK_MUSIC_CHANCE):
        """
        Evaluates an independent 60% chance for EACH track in music/ (excluding meow.m4a).
        Multiple tracks can play simultaneously.
        """
        if not MUSIC_DIR.exists():
            return

        for track_path in MUSIC_DIR.glob("*.m4a"):
            if track_path.name.lower() == "meow.m4a":
                continue

            roll = random.random()
            if roll < chance:
                print(f"[ChaosAudio] Track 60% HIT: Playing {track_path.name} (roll: {roll:.2f})")
                self.play_track(str(track_path.resolve()), 30.0, is_music=True)

    def is_chaos_audio_playing(self) -> bool:
        """Returns True if any chaos track or meow is currently active."""
        if self._active_players:
            return True
        if time.time() < self._playback_end_time:
            return True
        return False

    def is_music_track_playing(self) -> bool:
        """Returns True if any ambient background music track (excluding meow) is currently active."""
        if self._active_music_players:
            return True
        if time.time() < self._music_playback_end_time:
            return True
        return False

    def stop_all(self):
        """Immediately halts and closes all active players."""
        self._playback_end_time = 0.0
        self._music_playback_end_time = 0.0
        self._polling = False
        players = list(self._active_players)
        self._active_players.clear()
        self._active_music_players.clear()
        for player in players:
            try:
                player.controls.stop()
                player.close()
            except Exception:
                pass
        print("[ChaosAudio] All chaos audio stopped.")

