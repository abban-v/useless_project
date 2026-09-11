"""
Main Application Orchestrator for Useless Project (Windows Chaos Assistant).
Coordinates:
1. Audio drop hazard (80% chance on sound playback) & interactive pump mini-game
2. Extensible periodic visual hazard (60% chance every 60s) -> 100% Brightness Screen Flashbang
3. Mouse stamina system with floating cursor HUD and 1-minute 'ONE MOMENT OF SILENCE' freeze
4. Keyboard scrambler (40% chance to substitute typed letters with neighboring/random keys)
5. Emergency global safety kill switch (F8 or Ctrl+Shift+Q) to restore all system settings
"""

import sys
import time
import signal
import threading
import ctypes
import tkinter as tk

from config import (
    AUDIO_DROP_CHANCE,
    AUDIO_COOLDOWN_SECONDS,
    HAZARD_INTERVAL_SECONDS,
    FLASHBANG_CHANCE,
    MOUSE_EXHAUSTED_SPEED,
    KEYBOARD_SCRAMBLE_CHANCE,
)
from audio_pump import WindowsAudioController, AudioHazardMonitor, PumpOverlay
from screen_flashbang import HazardManager
from mouse_stamina import MouseSpeedController, MouseStaminaHUD, attach_input_desktop
from keyboard_scramble import KeyboardScrambler

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

user32 = ctypes.windll.user32
VK_F8 = 0x77
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_Q = 0x51


class UselessApp:
    """Central orchestrator managing all chaos modules."""

    def __init__(self):
        # Attach desktop before creating Tkinter windows for flawless cursor tracking
        attach_input_desktop()

        print("=" * 60)
        print(" [!] USELESS PROJECT: RANDOMLY ASSEMBLED GARBAGE [!]")
        print("=" * 60)
        print(" Active Modules:")
        print(f"  * Audio Hazard:    {int(AUDIO_DROP_CHANCE * 100)}% chance on sound -> Volume 0 -> Pump mini-game")
        print(f"  * Visual Hazard:   {int(FLASHBANG_CHANCE * 100)}% chance every {int(HAZARD_INTERVAL_SECONDS)}s -> 100% Brightness Flashbang")
        print(f"  * Mouse Stamina:   Floating HUD above cursor -> Exhaustion freeze & 'ONE MOMENT OF SILENCE'")
        print(f"  * Keyboard Chaos:  {int(KEYBOARD_SCRAMBLE_CHANCE * 100)}% chance of typed letter swapping (e.g. g -> h)")
        print(" Safety:")
        print("  * Press [F8] or [Ctrl + Shift + Q] anywhere to EMERGENCY EXIT & RESTORE!")
        print("=" * 60)

        # 1. Tkinter Hidden Root
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Useless Project Background Host")

        # 2. Mouse Speed Controller & Floating Stamina HUD
        self.mouse_speed_ctrl = MouseSpeedController()
        self.mouse_hud = MouseStaminaHUD(self.root, self.mouse_speed_ctrl)

        # 3. Windows Audio Controller & Pump Overlay
        self.audio_ctrl = WindowsAudioController()
        self.pump_overlay = PumpOverlay(
            master=self.root,
            on_progress=self._on_pump_progress,
            on_complete=self._on_pump_complete,
        )

        # 4. Audio Hazard Monitor
        self.audio_monitor = AudioHazardMonitor(
            audio_ctrl=self.audio_ctrl,
            on_drop_callback=self._on_audio_dropped,
            drop_chance=AUDIO_DROP_CHANCE,
            cooldown_seconds=AUDIO_COOLDOWN_SECONDS,
        )

        # 5. Extensible Periodic Visual Hazard Manager (with 100% brightness blast)
        self.hazard_manager = HazardManager(self.root)

        # 6. Keyboard Scrambler (40% letter swapping)
        self.keyboard_scrambler = KeyboardScrambler(chance=KEYBOARD_SCRAMBLE_CHANCE)

        # 7. Safety Hotkey Thread
        self.is_running = True
        self.hotkey_thread = threading.Thread(target=self._hotkey_listener, daemon=True)

        signal.signal(signal.SIGINT, lambda s, f: self.shutdown())
        signal.signal(signal.SIGTERM, lambda s, f: self.shutdown())

    def _on_audio_dropped(self):
        """Dispatched when 80% audio hazard drops volume to 0."""
        self.root.after(0, self.pump_overlay.show_hazard)

    def _on_pump_progress(self, current_percent: float):
        """Called as user pumps the handle."""
        self.audio_monitor.set_pump_progress(current_percent)

    def _on_pump_complete(self):
        """Called when user successfully reaches 100%."""
        self.audio_monitor.complete_pump()

    def _hotkey_listener(self):
        """Background listener for global emergency kill switch (F8 or Ctrl+Shift+Q)."""
        while self.is_running:
            time.sleep(0.05)
            f8_pressed = (user32.GetAsyncKeyState(VK_F8) & 0x8000) != 0

            ctrl_pressed = (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
            shift_pressed = (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0
            q_pressed = (user32.GetAsyncKeyState(VK_Q) & 0x8000) != 0

            if f8_pressed or (ctrl_pressed and shift_pressed and q_pressed):
                print("\n[Safety] Emergency Hotkey detected! Shutting down and restoring system...")
                self.root.after(0, self.shutdown)
                break

    def run(self):
        """Starts all background monitors and runs the main event loop."""
        self.audio_monitor.start()
        self.hazard_manager.start()
        self.keyboard_scrambler.start()
        self.hotkey_thread.start()

        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        """Gracefully restores all system parameters and exits."""
        if not self.is_running:
            return
        self.is_running = False
        print("\n[UselessApp] Cleaning up and restoring Windows parameters...")

        try:
            self.keyboard_scrambler.stop()
        except Exception:
            pass

        try:
            self.audio_monitor.stop()
        except Exception:
            pass

        try:
            self.hazard_manager.stop()
        except Exception:
            pass

        try:
            self.mouse_speed_ctrl.cleanup()
        except Exception as err:
            print(f"[Cleanup] Error restoring mouse state: {err}")

        try:
            self.audio_ctrl.restore_original_volume()
            print("[Cleanup] Master volume restored.")
        except Exception as err:
            print(f"[Cleanup] Error restoring volume: {err}")

        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

        print("[UselessApp] Goodbye! System returned to normal.")
        sys.exit(0)


if __name__ == "__main__":
    app = UselessApp()
    app.run()
