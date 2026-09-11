"""
Threaded Mouse Click Listener for Click Chaos Module.
Detects left and right mouse clicks system-wide using GetAsyncKeyState.
Eliminates high-frequency WH_MOUSE_LL hook overhead and GIL thread state corruption in Python 3.14.
"""

import time
import threading
import ctypes
from typing import Callable, Optional

user32 = ctypes.windll.user32

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02


class ClickListener:
    """
    Background polling listener detecting left/right mouse clicks system-wide.
    """

    def __init__(self, on_click_callback: Callable[[], None], poll_interval: float = 0.012):
        self.on_click_callback = on_click_callback
        self.poll_interval = poll_interval
        self.is_active = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Starts the background click detection thread."""
        if not self.is_active:
            self.is_active = True
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()
            print("[ClickListener] Background mouse click listener ACTIVE.")

    def stop(self):
        """Stops the click listener."""
        self.is_active = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        print("[ClickListener] Mouse click listener STOPPED.")

    def _poll_loop(self):
        """Polls mouse button states and fires callback on button down transition."""
        was_left_down = False
        was_right_down = False

        while self.is_active:
            try:
                left_down = (user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000) != 0
                right_down = (user32.GetAsyncKeyState(VK_RBUTTON) & 0x8000) != 0

                if (left_down and not was_left_down) or (right_down and not was_right_down):
                    if self.on_click_callback:
                        self.on_click_callback()

                was_left_down = left_down
                was_right_down = right_down
            except Exception:
                pass

            time.sleep(self.poll_interval)

