"""
Ad Input Blocker for Fullscreen Ad System.
Disables all keyboard and mouse interactions while an ad or revenge sequence is playing:
- Intercepts and swallows ALL mouse movement, clicks, scrolls, and drag gestures via WH_MOUSE_LL.
- Intercepts and swallows ALL keyboard input via WH_KEYBOARD_LL.
- Guarantees the emergency failsafe (F8 or Ctrl + Shift + Q) remains fully operational.
- Runs in an isolated background Win32 message pump thread to prevent Tkinter GIL lockups.
"""

import atexit
import ctypes
import threading
from ctypes import wintypes
from typing import Optional, Callable

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

LRESULT = ctypes.c_longlong
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

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

user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = wintypes.SHORT

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14

VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_F8 = 0x77
VK_Q = 0x51


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class AdInputBlocker:
    """
    Blocks all keyboard and mouse events during fullscreen ad playback.
    Operates on a dedicated background message pump thread.
    """

    def __init__(self, emergency_exit_callback: Optional[Callable] = None):
        self.mouse_hook = None
        self.kbd_hook = None
        self.is_active = False
        self.emergency_exit_callback = emergency_exit_callback

        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._ready_event = threading.Event()
        self._lock = threading.Lock()

        self._c_mouse_cb = HOOKPROC(self._mouse_hook_callback)
        self._c_kbd_cb = HOOKPROC(self._kbd_hook_callback)

        atexit.register(self.stop)

    def _mouse_hook_callback(self, nCode, wParam, lParam):
        if nCode >= 0 and self.is_active:
            # Block ALL mouse events: movement, clicks, scrolls, drags
            return 1
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def _kbd_hook_callback(self, nCode, wParam, lParam):
        if nCode >= 0 and self.is_active:
            try:
                kb = KBDLLHOOKSTRUCT.from_address(lParam)
                vk = kb.vkCode

                # Check for emergency failsafe keys: F8 or Ctrl + Shift + Q
                if vk == VK_F8:
                    if self.emergency_exit_callback:
                        self.emergency_exit_callback()
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)

                ctrl_down = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
                shift_down = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
                if vk == VK_Q and ctrl_down and shift_down:
                    if self.emergency_exit_callback:
                        self.emergency_exit_callback()
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)

                # Swallowing all other keys
                return 1
            except Exception:
                return 1
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def start(self):
        """Installs the hooks on the background thread and activates blocking."""
        with self._lock:
            if self.is_active:
                return

            self.is_active = True
            if self._thread is None or not self._thread.is_alive():
                self._ready_event.clear()
                self._thread = threading.Thread(target=self._hook_thread_loop, daemon=True, name="AdInputBlockerThread")
                self._thread.start()
                self._ready_event.wait(timeout=2.0)

            print("[AdInputBlocker] Keyboard and mouse input BLOCKED during ad playback.")

    def _hook_thread_loop(self):
        """Thread worker installing low-level hooks and running a Win32 message pump."""
        self._thread_id = kernel32.GetCurrentThreadId()

        self.mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._c_mouse_cb, None, 0)
        self.kbd_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._c_kbd_cb, None, 0)

        self._ready_event.set()

        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self.mouse_hook:
            user32.UnhookWindowsHookEx(self.mouse_hook)
            self.mouse_hook = None
        if self.kbd_hook:
            user32.UnhookWindowsHookEx(self.kbd_hook)
            self.kbd_hook = None

    def stop(self):
        """Stops blocking and restores keyboard and mouse controls."""
        with self._lock:
            if not self.is_active and self._thread is None:
                return

            self.is_active = False

            if self._thread_id:
                user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT

            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)

            self._thread = None
            self._thread_id = None
            print("[AdInputBlocker] Keyboard and mouse input RESTORED.")
