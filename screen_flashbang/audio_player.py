"""
Native Windows MP3 Audio Player for Screen Flashbang Module.
Plays 'memes/audioloud.mp3' asynchronously via Windows MCI (winmm.dll)
without requiring any 3rd-party audio libraries.
"""

import os
import time
import ctypes
from pathlib import Path

winmm = ctypes.windll.winmm
MEMES_AUDIO_PATH = Path(__file__).parent.parent / "memes" / "audioloud.mp3"

_playback_end_time = 0.0


def play_flashbang_audio(mp3_path: Path = MEMES_AUDIO_PATH) -> bool:
    """
    Plays audioloud.mp3 asynchronously via Windows MCI.
    Tracks duration and sets playback window to prevent audio drop hazards.
    """
    global _playback_end_time
    try:
        path_str = str(mp3_path.resolve())
        if not os.path.exists(path_str):
            print(f"[FlashbangAudio] Warning: {path_str} not found.")
            return False

        alias = "flashbang_mp3"
        # Close previous instance if open
        winmm.mciSendStringW(f"close {alias}", None, 0, 0)

        # Open and play
        ret = winmm.mciSendStringW(f'open "{path_str}" type mpegvideo alias {alias}', None, 0, 0)
        if ret == 0:
            duration_sec = 12.0
            buf = ctypes.create_unicode_buffer(128)
            winmm.mciSendStringW(f"set {alias} time format milliseconds", None, 0, 0)
            len_ret = winmm.mciSendStringW(f"status {alias} length", buf, 128, 0)
            if len_ret == 0 and buf.value.isdigit():
                duration_sec = max(1.0, int(buf.value) / 1000.0)

            # Keep suppression active throughout duration + 2s decay margin
            _playback_end_time = time.time() + duration_sec + 2.0

            winmm.mciSendStringW(f"play {alias} from 0", None, 0, 0)
            print(f"[FlashbangAudio] Blasting loud meme audio ({duration_sec:.1f}s): {path_str}")
            return True
        else:
            print(f"[FlashbangAudio] MCI open returned error code {ret}")
            return False
    except Exception as err:
        print(f"[FlashbangAudio] Error playing audio: {err}")
        return False


def is_flashbang_audio_playing() -> bool:
    """
    Returns True if flashbang audio is currently playing or in decay window.
    Checks both playback timestamp and native Windows MCI status.
    """
    global _playback_end_time
    if time.time() < _playback_end_time:
        return True

    try:
        buf = ctypes.create_unicode_buffer(128)
        ret = winmm.mciSendStringW("status flashbang_mp3 mode", buf, 128, 0)
        if ret == 0 and buf.value.strip().lower() == "playing":
            return True
    except Exception:
        pass
    return False


def stop_flashbang_audio():
    """Stops and closes any currently playing flashbang audio."""
    global _playback_end_time
    _playback_end_time = 0.0
    try:
        winmm.mciSendStringW("close flashbang_mp3", None, 0, 0)
    except Exception:
        pass
