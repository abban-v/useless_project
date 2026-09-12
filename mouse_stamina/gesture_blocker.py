"""
Windows Gesture & Mouse Event Blocker for Mouse Stamina Module.
When the mouse is 'dead' during the 1-minute moment of silence:
- Intercepts and blocks ALL mouse events (movement, clicks, scroll wheel, drag) via WH_MOUSE_LL.
- Intercepts and blocks Windows gesture shortcuts (Task View, Show Desktop, Action Center,
  Widgets, Virtual Desktop switching) via WH_KEYBOARD_LL.
- Guarantees the emergency failsafe (F8 or Ctrl+Shift+Q) remains fully functional.
- Fully typed with 64-bit ctypes Win32 signatures.
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

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14

VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_MENU = 0x12     # Alt
VK_CONTROL = 0x11  # Ctrl
VK_SHIFT = 0x10    # Shift
VK_TAB = 0x09
VK_LEFT = 0x25
VK_RIGHT = 0x27
VK_F8 = 0x77
VK_Q = 0x51

# Keys used in Windows gestures: Tab, D (0x44), A (0x41), W (0x57), S (0x53), Left, Right
GESTURE_KEYS = {VK_TAB, 0x44, 0x41, 0x57, 0x53, VK_LEFT, VK_RIGHT}


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class WindowsGestureBlocker:
    """
    Immobilizes all mouse events and touchpad/edge gesture shortcuts
    while the mouse is dead.
    """

    def __init__(self, on_click_callback=None):
        self.mouse_hook = None
        self.kbd_hook = None
        self.is_active = False
        self.on_click_callback = on_click_callback

        self._c_mouse_cb = HOOKPROC(self._mouse_hook_callback)
        self._c_kbd_cb = HOOKPROC(self._kbd_hook_callback)

        atexit.register(self.stop)

    def _mouse_hook_callback(self, nCode, wParam, lParam):
        if nCode >= 0 and self.is_active:
            # If user clicked while frozen, notify callback so chaos effects trigger!
            if wParam in (0x0201, 0x0204, 0x0207):  # WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_MBUTTONDOWN
                if self.on_click_callback:
                    try:
                        self.on_click_callback()
                    except Exception:
                        pass
            # Block ALL mouse movement, clicks, scrolls, and drag gestures from reaching OS/apps
            return 1
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def _kbd_hook_callback(self, nCode, wParam, lParam):
        if nCode >= 0 and self.is_active:
            try:
                kb = KBDLLHOOKSTRUCT.from_address(lParam)
                vk = kb.vkCode

                # NEVER block emergency safety hotkeys (F8 or Ctrl+Shift+Q)
                if vk == VK_F8:
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)

                ctrl_down = (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
                shift_down = (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0
                if ctrl_down and shift_down and vk == VK_Q:
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)

                # Check if Windows key or Alt key is held
                win_down = (
                    (user32.GetAsyncKeyState(VK_LWIN) & 0x8000) != 0
                    or (user32.GetAsyncKeyState(VK_RWIN) & 0x8000) != 0
                )
                alt_down = (user32.GetAsyncKeyState(VK_MENU) & 0x8000) != 0

                # Block standalone Windows key presses (prevents Start menu gesture)
                if vk in (VK_LWIN, VK_RWIN):
                    return 1

                # Block Windows touchpad/edge gesture chords
                if win_down and (vk in GESTURE_KEYS):
                    return 1

                if alt_down and vk == VK_TAB:
                    return 1
            except Exception:
                pass

        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def start(self):
        """Installs the mouse and keyboard gesture hooks."""
        if not self.is_active:
            self.is_active = True
            if not self.mouse_hook:
                self.mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._c_mouse_cb, 0, 0)
            if not self.kbd_hook:
                self.kbd_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._c_kbd_cb, 0, 0)
            print("[GestureBlocker] Mouse events & Windows gestures BLOCKED.")

    def stop(self):
        """Uninstalls the hooks and restores normal input."""
        if self.is_active:
            self.is_active = False
            if self.mouse_hook:
                user32.UnhookWindowsHookEx(self.mouse_hook)
                self.mouse_hook = None
            if self.kbd_hook:
                user32.UnhookWindowsHookEx(self.kbd_hook)
                self.kbd_hook = None
            print("[GestureBlocker] Mouse events & Windows gestures RESTORED.")
