"""
Low-level Keyboard Hook to intercept and block hardware volume keys.
Prevents user from increasing or unmuting audio via keyboard when hazard is active.
Fully typed with 64-bit ctypes Win32 signatures.
"""

import atexit
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

LRESULT = ctypes.c_longlong
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

# Explicit 64-bit ctypes function signatures to prevent ArgumentError/OverflowError
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK

user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class VolumeKeyBlocker:
    """
    Blocks multimedia volume keys (Volume Up, Volume Down, Volume Mute)
    system-wide using WH_KEYBOARD_LL.
    """

    BLOCKED_KEYS = {
        0xAF,  # VK_VOLUME_UP
        0xAE,  # VK_VOLUME_DOWN
        0xAD,  # VK_VOLUME_MUTE
    }

    def __init__(self):
        self.hook_id = None
        self._c_callback = HOOKPROC(self._hook_callback)
        atexit.register(self.stop)

    def _hook_callback(self, nCode, wParam, lParam):
        if nCode >= 0:
            try:
                kb = KBDLLHOOKSTRUCT.from_address(lParam)
                if kb.vkCode in self.BLOCKED_KEYS:
                    return 1
            except Exception:
                pass
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def start(self):
        """Installs the low-level keyboard hook."""
        if not self.hook_id:
            self.hook_id = user32.SetWindowsHookExW(13, self._c_callback, 0, 0)
            if self.hook_id:
                print("[VolumeKeyBlocker] Hardware volume keys BLOCKED.")

    def stop(self):
        """Removes the low-level keyboard hook."""
        if self.hook_id:
            user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None
            print("[VolumeKeyBlocker] Hardware volume keys RESTORED.")
