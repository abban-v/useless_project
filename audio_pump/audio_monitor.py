"""
Audio Hazard Monitor for Audio Pump Module.
Runs a background listener on Windows peak audio meter.
When audio playback is detected, evaluates an 80% random chance to drop volume to 0.
Strictly blocks all other means of increasing audio:
- Hardware volume keys are blocked via low-level keyboard hook
- Master volume is continuously clamped so taskbar sliders/mixers cannot raise volume
"""

import time
import random
import threading
import ctypes
from typing import Callable, Optional

from config import (
    AUDIO_DROP_CHANCE,
    AUDIO_COOLDOWN_SECONDS,
    AUDIO_PEAK_THRESHOLD,
    AUDIO_POLL_INTERVAL,
    VOLUME_RESTORE_LEVEL,
)
from audio_pump.audio_controller import WindowsAudioController
from audio_pump.key_blocker import VolumeKeyBlocker

ole32 = ctypes.windll.ole32


class AudioHazardMonitor:
    """
    Background worker that monitors audio playback.
    When sound plays, has an 80% chance to drop master volume to 0.
    Enforces that ONLY pump mouse clicks can increase volume.
    """

    def __init__(
        self,
        audio_ctrl: WindowsAudioController,
        on_drop_callback: Callable[[], None],
        drop_chance: float = AUDIO_DROP_CHANCE,
        cooldown_seconds: float = AUDIO_COOLDOWN_SECONDS,
    ):
        self.audio_ctrl = audio_ctrl
        self.on_drop_callback = on_drop_callback
        self.drop_chance = drop_chance
        self.cooldown_seconds = cooldown_seconds

        self.is_hazard_active = False
        self.last_restored_time = 0.0
        self.allowed_volume_scalar = 0.0
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self.key_blocker = VolumeKeyBlocker()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self.key_blocker.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def set_pump_progress(self, progress_percent: float):
        """Updates live master volume according to pump progress (0.0 to 100.0)."""
        if self.is_hazard_active:
            scalar = max(0.0, min(1.0, progress_percent / 100.0))
            self.allowed_volume_scalar = scalar
            self.audio_ctrl.set_volume(scalar)

    def complete_pump(self):
        """Called when user successfully reaches 100% on the pump."""
        self.key_blocker.stop()
        self.allowed_volume_scalar = VOLUME_RESTORE_LEVEL
        self.audio_ctrl.set_volume(VOLUME_RESTORE_LEVEL)
        self.is_hazard_active = False
        self.last_restored_time = time.time()
        print(
            f"[AudioHazard] Volume restored to 100%. Cooldown {self.cooldown_seconds}s active."
        )

    def _monitor_loop(self):
        ole32.CoInitialize(None)
        print("[AudioHazard] Audio monitor thread active.")

        while self._running:
            # When hazard is active, poll fast (~30ms) to aggressively clamp volume
            # against taskbar sliders or mixer tampering
            if self.is_hazard_active:
                time.sleep(0.03)
                try:
                    actual_vol = self.audio_ctrl.get_volume()
                    # If any external means tried to raise volume higher than pump progress, clamp it!
                    if actual_vol > self.allowed_volume_scalar + 0.005:
                        self.audio_ctrl.set_volume(self.allowed_volume_scalar)
                except Exception:
                    pass
                continue

            time.sleep(AUDIO_POLL_INTERVAL)

            now = time.time()
            if now - self.last_restored_time < self.cooldown_seconds:
                continue

            try:
                peak = self.audio_ctrl.get_peak_value()
                current_vol = self.audio_ctrl.get_volume()

                if peak > AUDIO_PEAK_THRESHOLD and current_vol > 0.02:
                    roll = random.random()
                    print(
                        f"[AudioHazard] Sound detected! Peak: {peak:.3f}, Vol: {current_vol:.2f} | Roll: {roll:.3f} vs {self.drop_chance}"
                    )

                    if roll < self.drop_chance:
                        print("[AudioHazard] 80% HIT! Dropping volume to 0!")
                        self.is_hazard_active = True
                        self.allowed_volume_scalar = 0.0
                        self.audio_ctrl.set_volume(0.0)
                        # Block hardware volume keys
                        self.key_blocker.start()

                        if self.on_drop_callback:
                            self.on_drop_callback()
                    else:
                        self.last_restored_time = now - (self.cooldown_seconds - 3.0)
            except Exception as err:
                print(f"[AudioHazard] Monitor error: {err}")
