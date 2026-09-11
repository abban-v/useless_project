"""
Action Key & Volume Control Blocker for Screen Flashbang Module.
System-wide hook and volume clamp active during flashbang audio playback:
- Swallows hardware volume keys (Volume Down, Volume Mute, Volume Up)
- Swallows multimedia keys (Play/Pause, Stop, Prev, Next)
- Swallows action keys (Space, Return, Escape, Tab, Pause)
- Continuously enforces Master Volume at 100% and unmuted (countering any taskbar/mixer sliders)
- Leaves emergency failsafe keys (F8, Ctrl+Shift+Q) completely functional
- Automatically releases hooks when flashbang audio completes
"""

import atexit
import time
import threading
import ctypes
from ctypes import wintypes
from typing import Optional

from screen_flashbang.audio_player import is_flashbang_audio_playing

user32 = ctypes.windll.user32
ole32 = ctypes.windll.ole32

LRESULT = ctypes.c_longlong
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

# Explicit 64-bit ctypes function signatures to prevent ArgumentError/OverflowError
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK

user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL

WH_KEYBOARD_LL = 13


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class FlashbangActionKeyBlocker:
    """
    Blocks action keys and hardware volume adjustments while flashbang sound plays.
    Also continuously locks master volume at 1.0 (100%) and unmutes it.
    """

    BLOCKED_KEYS = {
        # Hardware Volume & Media
        0xAE,  # VK_VOLUME_DOWN
        0xAD,  # VK_VOLUME_MUTE
        0xAF,  # VK_VOLUME_UP
        0xB0,  # VK_MEDIA_NEXT_TRACK
        0xB1,  # VK_MEDIA_PREV_TRACK
        0xB2,  # VK_MEDIA_STOP
        0xB3,  # VK_MEDIA_PLAY_PAUSE
        0xB5,  # VK_LAUNCH_MEDIA_SELECT
        # General Action Keys
        0x20,  # VK_SPACE
        0x0D,  # VK_RETURN
        0x1B,  # VK_ESCAPE
        0x09,  # VK_TAB
        0x13,  # VK_PAUSE
    }

    def __init__(self, audio_ctrl=None):
        self.audio_ctrl = audio_ctrl
        self.hook_id: Optional[int] = None
        self.is_active = False
        self._thread: Optional[threading.Thread] = None
        self._c_callback = HOOKPROC(self._hook_callback)
        self._lock = threading.Lock()
        atexit.register(self.stop)

    def _hook_callback(self, nCode, wParam, lParam):
        if nCode >= 0 and self.is_active:
            try:
                kb = KBDLLHOOKSTRUCT.from_address(lParam)
                if kb.vkCode in self.BLOCKED_KEYS:
                    # Swallow key: do not pass to OS, applications, or downstream hooks
                    return 1
            except Exception:
                pass
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def start(self):
        """Installs low-level hook and starts 100% volume enforcement thread."""
        with self._lock:
            if self.is_active:
                return
            self.is_active = True

            if not self.hook_id:
                self.hook_id = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._c_callback, 0, 0)
                if self.hook_id:
                    print("[FlashbangActionKeys] Action keys & volume controls BLOCKED during flashbang.")

            self._thread = threading.Thread(target=self._enforce_loop, daemon=True)
            self._thread.start()

    def stop(self):
        """Releases low-level hook and terminates volume enforcement."""
        with self._lock:
            if not self.is_active and not self.hook_id:
                return
            self.is_active = False

            if self.hook_id:
                user32.UnhookWindowsHookEx(self.hook_id)
                self.hook_id = None
                print("[FlashbangActionKeys] Action keys & volume controls RESTORED.")

    def _enforce_loop(self):
        """
        Background enforcement thread:
        Runs while flashbang audio is active.
        Continuously clamps volume to 100% and keeps unmuted every 20ms.
        """
        ole32.CoInitialize(None)
        while self.is_active:
            # Check if flashbang audio is done
            if not is_flashbang_audio_playing():
                break

            # Clamping: override any attempt to lower volume or mute
            if self.audio_ctrl is not None:
                try:
                    vol = self.audio_ctrl.get_volume()
                    if vol < 0.99:
                        self.audio_ctrl.set_volume(1.0)
                    if self.audio_ctrl.get_mute():
                        self.audio_ctrl.set_mute(False)
                except Exception:
                    pass

            time.sleep(0.02)

        # Once audio finishes or stop requested, clean up
        self.stop()
