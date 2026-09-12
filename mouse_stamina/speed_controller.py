"""
Mouse Speed & Freeze Controller for Mouse Stamina Module.
Manages Windows SystemParametersInfo mouse speed, ClipCursor immobilization, friction,
and low-level mouse & gesture event blocking.
Guarantees cursor movement, clicks, and Windows gestures are completely disabled during 'ONE MOMENT OF SILENCE'.
"""

import atexit
import ctypes
from ctypes import wintypes
from config import MOUSE_EXHAUSTED_SPEED, MOUSE_EXHAUSTED_DAMPING_FACTOR
from mouse_stamina.gesture_blocker import WindowsGestureBlocker

user32 = ctypes.windll.user32
SPI_GETMOUSESPEED = 0x0070
SPI_SETMOUSESPEED = 0x0071

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]

# Explicit ctypes function signatures for 64-bit safety
user32.ClipCursor.argtypes = [ctypes.c_void_p]
user32.ClipCursor.restype = wintypes.BOOL

user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL

user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
user32.SystemParametersInfoW.restype = wintypes.BOOL


def attach_input_desktop():
    """Attaches thread to the active interactive input desktop if needed."""
    try:
        h_desk = user32.OpenInputDesktop(0, False, 0x01FF)
        if h_desk:
            user32.SetThreadDesktop(h_desk)
    except Exception:
        pass


class MouseSpeedController:
    """Safely throttles, immobilizes, and blocks mouse & gesture inputs during exhaustion."""

    def __init__(self, on_click_callback=None):
        attach_input_desktop()
        self.original_speed = self._get_current_speed()
        self.is_throttled = False
        self.is_frozen = False
        self.freeze_x = 0
        self.freeze_y = 0

        self.gesture_blocker = WindowsGestureBlocker(on_click_callback=on_click_callback)
        atexit.register(self.cleanup)

    def _get_current_speed(self) -> int:
        speed = ctypes.c_int(10)
        res = user32.SystemParametersInfoW(SPI_GETMOUSESPEED, 0, ctypes.byref(speed), 0)
        return speed.value if res != 0 else 10

    def set_speed(self, speed: int):
        clamped = max(1, min(20, int(speed)))
        user32.SystemParametersInfoW(SPI_SETMOUSESPEED, 0, clamped, 0)

    def freeze_cursor(self, x: int, y: int):
        """Freezes the mouse in place and blocks all mouse clicks and Windows gestures."""
        self.freeze_x = x
        self.freeze_y = y
        self.is_frozen = True

        # Clip cursor to a 1x1 rectangle at (x, y)
        rc = RECT(x, y, x + 1, y + 1)
        user32.ClipCursor(ctypes.byref(rc))
        user32.SetCursorPos(x, y)
        self.slow_down()

        # Block all mouse clicks, scrolls, and touchpad gestures
        self.gesture_blocker.start()
        print(f"[MouseStamina] Mouse & Gestures FROZEN at ({x}, {y}) for ONE MOMENT OF SILENCE!")

    def enforce_freeze(self):
        """Continuously re-pins the cursor to the frozen coordinates."""
        if self.is_frozen:
            user32.SetCursorPos(self.freeze_x, self.freeze_y)

    def unfreeze_cursor(self):
        """Releases cursor freeze clip and restores mouse/gesture handling."""
        if self.is_frozen:
            user32.ClipCursor(None)
            self.gesture_blocker.stop()
            self.is_frozen = False
            print("[MouseStamina] Mouse & Gestures UNFROZEN! Movement restored.")

    def slow_down(self):
        """Reduces Windows mouse speed setting to 1."""
        if not self.is_throttled:
            self.set_speed(MOUSE_EXHAUSTED_SPEED)
            self.is_throttled = True

    def restore_speed(self):
        """Restores Windows mouse speed back to original setting."""
        if self.is_throttled:
            self.set_speed(self.original_speed)
            self.is_throttled = False
            print(f"[MouseStamina] Mouse RECOVERED! Restored speed to {self.original_speed}")

    def cleanup(self):
        """Failsafe cleanup to guarantee cursor and gestures are freed on exit."""
        self.unfreeze_cursor()
        self.restore_speed()

    def apply_exhaustion_friction(self, cur_x: int, cur_y: int, last_x: int, last_y: int):
        """Actively damps mouse cursor movement if not completely frozen."""
        if self.is_frozen:
            self.enforce_freeze()
            return self.freeze_x, self.freeze_y

        dx = cur_x - last_x
        dy = cur_y - last_y

        if abs(dx) > 1 or abs(dy) > 1:
            damped_x = int(last_x + (dx * MOUSE_EXHAUSTED_DAMPING_FACTOR))
            damped_y = int(last_y + (dy * MOUSE_EXHAUSTED_DAMPING_FACTOR))
            user32.SetCursorPos(damped_x, damped_y)
            return damped_x, damped_y

        return cur_x, cur_y
