"""
Audio Enforcer & Media Player for Shoe Game Module.
Guarantees master volume stays at 100% and unmuted while shoe game audio plays:
- Blocks hardware volume keys (Volume Up, Volume Down, Volume Mute)
- Blocks media keys
- Continuously clamps master volume to 1.0 (100%) and unmutes every 20ms
- Plays scream tracks (scream.m4a, scream2.m4a) and all tracks in music/ concurrently via WMPlayer.OCX
- Leaves emergency safety keys (F8, Ctrl+Shift+Q) completely functional
"""

import atexit
import ctypes
import os
import threading
import time
from ctypes import wintypes
from pathlib import Path
from typing import List, Optional
import win32com.client

user32 = ctypes.windll.user32
ole32 = ctypes.windll.ole32

LRESULT = ctypes.c_longlong
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK

user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL

WH_KEYBOARD_LL = 13
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_Q = 0x51
VK_F8 = 0x77

MUSIC_DIR = Path(__file__).parent.parent / "music"
SCREAM_PATH = MUSIC_DIR / "scream.m4a"
SCREAM2_PATH = MUSIC_DIR / "scream2.m4a"


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class ShoeAudioEnforcer:
    """
    Manages 100% volume lock and multi-track audio playback for the Shoe Game.
    """

    BLOCKED_KEYS = {
        0xAF,  # VK_VOLUME_UP
        0xAE,  # VK_VOLUME_DOWN
        0xAD,  # VK_VOLUME_MUTE
        0xB0,  # VK_MEDIA_NEXT_TRACK
        0xB1,  # VK_MEDIA_PREV_TRACK
        0xB2,  # VK_MEDIA_STOP
        0xB3,  # VK_MEDIA_PLAY_PAUSE
    }

    def __init__(self, audio_ctrl=None, master=None):
        self.audio_ctrl = audio_ctrl
        self.master = master
        if self.audio_ctrl is None:
            try:
                from audio_pump.audio_controller import WindowsAudioController
                self.audio_ctrl = WindowsAudioController()
            except Exception:
                pass

        self.hook_id: Optional[int] = None
        self.is_locking = False
        self._lock_thread: Optional[threading.Thread] = None
        self._c_callback = HOOKPROC(self._hook_callback)
        self._active_players: List[any] = []
        self._original_volume = 1.0
        self._original_mute = False
        self._lock = threading.Lock()

        atexit.register(self.cleanup)

    def _hook_callback(self, nCode, wParam, lParam):
        if nCode >= 0 and self.is_locking:
            try:
                kb = KBDLLHOOKSTRUCT.from_address(lParam)
                vk = kb.vkCode

                # NEVER block safety keys (F8 or Ctrl+Shift+Q)
                if vk == VK_F8:
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)

                ctrl_down = (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
                shift_down = (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0
                if ctrl_down and shift_down and vk == VK_Q:
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)

                if vk in self.BLOCKED_KEYS:
                    return 1
            except Exception:
                pass
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def start_lock(self):
        """Locks volume to 100%, unmutes, and installs volume key blocker."""
        with self._lock:
            if self.is_locking:
                return
            self.is_locking = True

            if self.audio_ctrl is not None:
                try:
                    self._original_volume = self.audio_ctrl.get_volume()
                    self._original_mute = self.audio_ctrl.get_mute()
                    self.audio_ctrl.set_mute(False)
                    self.audio_ctrl.set_volume(1.0)
                except Exception:
                    pass

            if not self.hook_id:
                self.hook_id = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._c_callback, 0, 0)
                if self.hook_id:
                    print("[ShoeAudioEnforcer] Volume locked to 100% and volume keys BLOCKED.")

            self._lock_thread = threading.Thread(target=self._enforce_loop, daemon=True)
            self._lock_thread.start()

    def stop_lock(self):
        """Releases volume clamp, unhooks keys, and restores volume."""
        with self._lock:
            if not self.is_locking and not self.hook_id:
                return
            self.is_locking = False

            if self.hook_id:
                user32.UnhookWindowsHookEx(self.hook_id)
                self.hook_id = None
                print("[ShoeAudioEnforcer] Volume controls RESTORED.")

            if self.audio_ctrl is not None:
                try:
                    self.audio_ctrl.set_volume(self._original_volume)
                    self.audio_ctrl.set_mute(self._original_mute)
                except Exception:
                    pass

    def _enforce_loop(self):
        """Continuously re-applies 100% volume and unmuted state every 20ms."""
        ole32.CoInitialize(None)
        try:
            while self.is_locking:
                if self.audio_ctrl is not None:
                    try:
                        if self.audio_ctrl.get_volume() < 0.99:
                            self.audio_ctrl.set_volume(1.0)
                        if self.audio_ctrl.get_mute():
                            self.audio_ctrl.set_mute(False)
                    except Exception:
                        pass
                time.sleep(0.02)
        finally:
            try:
                ole32.CoUninitialize()
            except Exception:
                pass

    def _play_single_player(self, file_path: str) -> Optional[any]:
        """Instantiates a WMPlayer.OCX player for a track."""
        if not os.path.exists(file_path):
            return None
        try:
            player = win32com.client.Dispatch("WMPlayer.OCX")
            player.settings.volume = 100
            player.URL = str(Path(file_path).resolve())
            player.controls.play()
            return player
        except Exception as err:
            print(f"[ShoeAudioEnforcer] Error playing {file_path}: {err}")
            return None

    def _schedule_stop(self, players: list, duration: float):
        """Safely schedules stopping and closing of players on the main thread or with COM apartment init."""
        def _do_stop():
            for p in players:
                try:
                    p.controls.stop()
                    p.close()
                except Exception:
                    pass
                if p in self._active_players:
                    try:
                        self._active_players.remove(p)
                    except Exception:
                        pass

        if self.master:
            try:
                self.master.after(int(duration * 1000), _do_stop)
                return
            except Exception:
                pass

        def _thread_stop():
            time.sleep(duration)
            try:
                ole32.CoInitialize(None)
                _do_stop()
            except Exception:
                pass
            finally:
                try:
                    ole32.CoUninitialize()
                except Exception:
                    pass

        threading.Thread(target=_thread_stop, daemon=True).start()

    def play_single_scream(self, duration: float = 3.0):
        """Plays scream.m4a for duration seconds at 100% locked volume."""
        self.start_lock()
        player = self._play_single_player(str(SCREAM_PATH))
        if player:
            self._active_players.append(player)
            self._schedule_stop([player], duration)

    def play_double_scream(self, duration: float = 3.0):
        """Plays BOTH scream.m4a AND scream2.m4a simultaneously for duration seconds at 100% locked volume."""
        self.start_lock()
        p1 = self._play_single_player(str(SCREAM_PATH))
        p2 = self._play_single_player(str(SCREAM2_PATH))

        players = [p for p in (p1, p2) if p is not None]
        self._active_players.extend(players)
        if players:
            self._schedule_stop(players, duration)

    def play_all_music(self, duration: float = 10.0):
        """Blasts ALL audio tracks in music/ simultaneously at 100% locked volume."""
        self.start_lock()
        if not MUSIC_DIR.exists():
            return

        valid_exts = {".m4a", ".mp3", ".wav", ".aac", ".ogg"}
        tracks = [p for p in MUSIC_DIR.iterdir() if p.is_file() and p.suffix.lower() in valid_exts]

        players = []
        for t in tracks:
            p = self._play_single_player(str(t))
            if p:
                players.append(p)

        self._active_players.extend(players)
        print(f"[ShoeAudioEnforcer] Blasting {len(players)} music tracks simultaneously at 100% volume for {duration}s!")
        if players:
            self._schedule_stop(players, duration)

    def stop_all_audio(self):
        """Stops and closes all active players and stops volume lock."""
        players = list(self._active_players)
        self._active_players.clear()
        for p in players:
            try:
                p.settings.volume = 0
                p.controls.stop()
                p.close()
            except Exception:
                pass
        self.stop_lock()

    def cleanup(self):
        """Ensures all audio is stopped and lock released on exit."""
        self.stop_all_audio()
