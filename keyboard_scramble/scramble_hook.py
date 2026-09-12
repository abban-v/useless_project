"""
Random Keyboard Scrambler for Keyboard Scramble Module.
Intercepts keystrokes via low-level keyboard hook (WH_KEYBOARD_LL).
40% of the time, letters are randomly substituted with an adjacent or different letter
(e.g., typing 'g' produces 'h' or another letter).
Shortcuts (Ctrl, Alt, Win) and system keys are left untouched.
Properly typed with 64-bit Windows ctypes signatures to prevent integer overflow.
"""

import atexit
import random
import string
import threading
import ctypes
from ctypes import wintypes
from typing import Callable, Optional
import config
from config import KEYBOARD_SCRAMBLE_CHANCE

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

LRESULT = ctypes.c_longlong
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

# Explicit 64-bit ctypes function signatures to prevent ArgumentError/OverflowError
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK

user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL

kernel32.GetCurrentThreadId.restype = wintypes.DWORD

user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostThreadMessageW.restype = wintypes.BOOL

user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = wintypes.BOOL

user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL

user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = LRESULT

user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]
user32.keybd_event.restype = None

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
KEYEVENTF_KEYUP = 0x0002
LLKHF_INJECTED = 0x00000010
MAGIC_EXTRA_INFO = 0xBEEF

VK_CONTROL = 0x11
VK_MENU = 0x12     # Alt
VK_SHIFT = 0x10
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_F8 = 0x77
VK_Q = 0x51

# Modifier virtual keycodes to exclude from standalone "clicks"
MODIFIER_VKS = {
    VK_CONTROL, VK_MENU, VK_SHIFT, VK_LWIN, VK_RWIN,
    0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5,  # L/R Shift, Ctrl, Alt
}

# QWERTY adjacent key map for realistic typos / letter drifts
QWERTY_NEIGHBORS = {
    "A": ["Q", "W", "S", "Z"],
    "B": ["V", "G", "H", "N"],
    "C": ["X", "D", "F", "V"],
    "D": ["E", "R", "S", "F", "X", "C"],
    "E": ["W", "R", "S", "D", "F"],
    "F": ["R", "T", "D", "G", "C", "V"],
    "G": ["T", "Y", "F", "H", "V", "B"],  # g -> h, etc.
    "H": ["Y", "U", "G", "J", "B", "N"],
    "I": ["U", "O", "J", "K", "L"],
    "J": ["U", "I", "H", "K", "N", "M"],
    "K": ["I", "O", "J", "L", "M"],
    "L": ["O", "P", "K"],
    "M": ["J", "K", "N"],
    "N": ["H", "J", "B", "M"],
    "O": ["I", "P", "K", "L"],
    "P": ["O", "L"],
    "Q": ["W", "A", "S"],
    "R": ["E", "T", "D", "F", "G"],
    "S": ["W", "E", "A", "D", "Z", "X"],
    "T": ["R", "Y", "F", "G", "H"],
    "U": ["Y", "I", "H", "J", "K"],
    "V": ["F", "G", "C", "B"],
    "W": ["Q", "E", "A", "S", "D"],
    "X": ["S", "D", "Z", "C"],
    "Y": ["T", "U", "G", "H", "J"],
    "Z": ["A", "S", "X"],
}


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class KeyboardScrambler:
    """
    Substitutes 40% of typed letters with another letter,
    and notifies callbacks on keyboard clicks (for 30% audio chaos).
    Runs on an isolated background message pump thread to eliminate GIL thread state
    corruption and PyEval_RestoreThread crashes in Python 3.14 during Tkinter mainloop execution.
    """

    def __init__(
        self,
        chance: Optional[float] = None,
        on_key_callback: Optional[Callable[[], None]] = None,
    ):
        self._custom_chance = chance
        self.on_key_callback = on_key_callback
        self.hook_id = None
        self.is_active = False
        self.swallowed_keys = set()
        self._is_synthesizing = False
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._ready_event = threading.Event()
        self._lock = threading.Lock()

        self._c_callback = HOOKPROC(self._hook_callback)
        atexit.register(self.stop)

    @property
    def chance(self) -> float:
        if self._custom_chance is not None:
            return float(self._custom_chance)
        return float(getattr(config, "KEYBOARD_SCRAMBLE_CHANCE", 0.40))

    @chance.setter
    def chance(self, val: float):
        self._custom_chance = float(val)

    def _get_replacement_vk(self, original_char: str) -> int:
        """Picks an adjacent QWERTY neighbor or random letter."""
        char = original_char.upper()
        neighbors = QWERTY_NEIGHBORS.get(char)
        if neighbors and random.random() < 0.75:
            replacement = random.choice(neighbors)
        else:
            candidates = [c for c in string.ascii_uppercase if c != char]
            replacement = random.choice(candidates)
        return ord(replacement)

    def _hook_callback(self, nCode, wParam, lParam):
        if nCode >= 0 and self.is_active:
            try:
                kb = KBDLLHOOKSTRUCT.from_address(lParam)

                # Ignore our own synthetic injected keys to avoid infinite recursion
                if self._is_synthesizing or (kb.flags & LLKHF_INJECTED) != 0:
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)

                vk = kb.vkCode

                # Key Down event: trigger on_key_callback for physical typing clicks
                if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                    # Never trigger on emergency safety killswitch keys or pure modifier keys
                    ctrl_down = (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
                    shift_down = (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0

                    is_killswitch = (vk == VK_F8) or (ctrl_down and shift_down and vk == VK_Q)
                    if not is_killswitch and vk not in MODIFIER_VKS:
                        if self.on_key_callback:
                            try:
                                self.on_key_callback()
                            except Exception:
                                pass

                # Only target letter keys A-Z (0x41 to 0x5A) for scrambling
                if 0x41 <= vk <= 0x5A:
                    # Do NOT scramble when modifier keys (Ctrl, Alt, Win) are pressed
                    ctrl_down = (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
                    alt_down = (user32.GetAsyncKeyState(VK_MENU) & 0x8000) != 0
                    win_down = (
                        (user32.GetAsyncKeyState(VK_LWIN) & 0x8000) != 0
                        or (user32.GetAsyncKeyState(VK_RWIN) & 0x8000) != 0
                    )

                    if ctrl_down or alt_down or win_down:
                        return user32.CallNextHookEx(None, nCode, wParam, lParam)

                    # Key Down event for letter scrambling
                    if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                        if random.random() < self.chance:
                            orig_char = chr(vk)
                            replacement_vk = self._get_replacement_vk(orig_char)

                            self.swallowed_keys.add(vk)

                            # Inject the replacement key press & release
                            self._is_synthesizing = True
                            try:
                                user32.keybd_event(replacement_vk, 0, 0, MAGIC_EXTRA_INFO)
                                user32.keybd_event(replacement_vk, 0, KEYEVENTF_KEYUP, MAGIC_EXTRA_INFO)
                            finally:
                                self._is_synthesizing = False

                            # Swallow the original key press
                            return 1

                    # Key Up event: swallow if the keydown was scrambled
                    elif wParam in (WM_KEYUP, WM_SYSKEYUP):
                        if vk in self.swallowed_keys:
                            self.swallowed_keys.remove(vk)
                            return 1
            except Exception:
                pass

        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def start(self):
        """Installs the keyboard scramble hook on an isolated background message loop thread."""
        with self._lock:
            if self.is_active:
                return
            self.is_active = True
            self._ready_event.clear()
            self._thread = threading.Thread(target=self._hook_thread_loop, daemon=True)
            self._thread.start()
            self._ready_event.wait(timeout=1.0)
            print(f"[KeyboardScrambler] Keyboard scramble hook ACTIVE ({int(self.chance * 100)}% chance).")

    def _hook_thread_loop(self):
        """Dedicated message pump running WH_KEYBOARD_LL to protect Tkinter mainloop from GIL corruption."""
        self._thread_id = kernel32.GetCurrentThreadId()
        self.hook_id = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._c_callback, 0, 0)
        self._ready_event.set()

        msg = wintypes.MSG()
        try:
            while self.is_active and user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            if self.hook_id:
                user32.UnhookWindowsHookEx(self.hook_id)
                self.hook_id = None

    def stop(self):
        """Uninstalls the keyboard scramble hook and stops the background pump thread."""
        with self._lock:
            if not self.is_active:
                return
            self.is_active = False
            if self._thread_id:
                user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)
            self._thread = None
            self._thread_id = None
            print("[KeyboardScrambler] Keyboard scramble hook STOPPED.")
