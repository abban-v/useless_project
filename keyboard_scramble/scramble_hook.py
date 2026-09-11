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
import ctypes
from ctypes import wintypes
from config import KEYBOARD_SCRAMBLE_CHANCE

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
VK_LWIN = 0x5B
VK_RWIN = 0x5C

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
    Substitutes 40% of typed letters with another letter.
    """

    def __init__(self, chance: float = KEYBOARD_SCRAMBLE_CHANCE):
        self.chance = chance
        self.hook_id = None
        self.is_active = False
        self.swallowed_keys = set()
        self._is_synthesizing = False

        self._c_callback = HOOKPROC(self._hook_callback)
        atexit.register(self.stop)

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

                # Only target letter keys A-Z (0x41 to 0x5A)
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

                    # Key Down event
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
        """Installs the keyboard scramble hook."""
        if not self.is_active:
            self.is_active = True
            if not self.hook_id:
                self.hook_id = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._c_callback, 0, 0)
                print(f"[KeyboardScrambler] Keyboard scramble hook ACTIVE ({int(self.chance * 100)}% chance).")

    def stop(self):
        """Uninstalls the keyboard scramble hook."""
        if self.is_active:
            self.is_active = False
            if self.hook_id:
                user32.UnhookWindowsHookEx(self.hook_id)
                self.hook_id = None
                print("[KeyboardScrambler] Keyboard scramble hook STOPPED.")
