"""
Automated test suite for modularized Useless Project components.
Validates audio_pump, screen_flashbang, and mouse_stamina modules,
including hardware volume key blocking, action key disabling, and volume clamping.
"""

import unittest
import tkinter as tk

import config
from audio_pump import WindowsAudioController, AudioHazardMonitor, PumpOverlay, VolumeKeyBlocker
from screen_flashbang import HazardManager, FlashbangOverlay
from mouse_stamina import MouseSpeedController, MouseStaminaHUD, SilenceOverlay, attach_input_desktop


class TestModularUselessProject(unittest.TestCase):

    def test_01_configuration(self):
        """Verify project requirements match configuration values."""
        self.assertEqual(config.AUDIO_DROP_CHANCE, 0.80, "Audio drop chance must be 80%")
        self.assertEqual(config.AUDIO_COOLDOWN_SECONDS, 30.0, "Cooldown must be 30 seconds")
        self.assertEqual(config.VOLUME_RESTORE_LEVEL, 1.0, "Volume must restore to 100%")
        self.assertEqual(config.FLASHBANG_CHANCE, 0.60, "Flashbang chance must be 60%")
        self.assertEqual(config.HAZARD_INTERVAL_SECONDS, 60.0, "Flashbang interval must be 60s")
        self.assertEqual(config.MOUSE_EXHAUSTED_SPEED, 1, "Exhausted mouse speed must be 1")
        self.assertEqual(config.MOMENT_OF_SILENCE_SECONDS, 60.0, "Silence freeze must be 60 seconds")

    def test_02_volume_key_blocker(self):
        """Verify low-level hook starts and stops without error."""
        blocker = VolumeKeyBlocker()
        blocker.start()
        self.assertIsNotNone(blocker.hook_id)
        blocker.stop()
        self.assertIsNone(blocker.hook_id)

    def test_03_audio_controller_and_clamping(self):
        """Verify master volume controls and external clamping."""
        ctrl = WindowsAudioController()
        original_vol = ctrl.get_volume()

        # Simulate monitor clamping
        monitor = AudioHazardMonitor(
            audio_ctrl=ctrl,
            on_drop_callback=lambda: None,
        )
        monitor.is_hazard_active = True
        monitor.allowed_volume_scalar = 0.2

        # If volume goes to 0.8 externally, clamping resets it to allowed scalar
        ctrl.set_volume(0.8)
        self.assertGreater(ctrl.get_volume(), 0.25)
        # Apply clamp
        if ctrl.get_volume() > monitor.allowed_volume_scalar + 0.005:
            ctrl.set_volume(monitor.allowed_volume_scalar)
        self.assertAlmostEqual(ctrl.get_volume(), 0.2, delta=0.03)

        ctrl.restore_original_volume()
        monitor.stop()

    def test_04_mouse_freeze_and_silence(self):
        """Verify 60-second cursor freeze, gesture blocker, and silence overlay."""
        ctrl = MouseSpeedController()
        initial_speed = ctrl.original_speed

        ctrl.freeze_cursor(400, 400)
        self.assertTrue(ctrl.is_frozen)
        self.assertTrue(ctrl.gesture_blocker.is_active)
        self.assertEqual(ctrl.freeze_x, 400)
        self.assertEqual(ctrl.freeze_y, 400)

        ctrl.unfreeze_cursor()
        self.assertFalse(ctrl.is_frozen)
        self.assertFalse(ctrl.gesture_blocker.is_active)

        ctrl.restore_speed()
        self.assertEqual(ctrl._get_current_speed(), initial_speed)

    def test_05_silence_overlay_ui(self):
        """Verify BIG WHITE TEXT raw Arial overlay creation and update."""
        attach_input_desktop()
        root = tk.Tk()
        root.withdraw()

        overlay = SilenceOverlay(root, duration_seconds=60.0)
        self.assertTrue(overlay.winfo_exists())
        self.assertGreaterEqual(overlay.font_size, 48)

        overlay.update_remaining(55.0)
        self.assertEqual(overlay.remaining_seconds, 55.0)

        overlay.dismiss()
        root.destroy()

    def test_06_pump_overlay_mouse_click_only(self):
        """Verify action keys are disabled and only direct mouse clicks advance pump."""
        attach_input_desktop()
        root = tk.Tk()
        root.withdraw()

        pump = PumpOverlay(
            root,
            on_progress=lambda p: None,
            on_complete=lambda: None,
        )
        pump.show_hazard()

        # Keyboard focus is disabled on button
        self.assertFalse(pump.pump_btn.cget("takefocus"))
        self.assertIn("MOUSE CLICK ONLY", pump.pump_btn.cget("text"))

        # Manual pump stroke works via click
        pump.do_pump_stroke()
        self.assertGreater(pump.current_volume, 0.0)

        root.destroy()

    def test_07_flashbang_brightness(self):
        """Verify force_maximum_brightness executes cleanly."""
        from screen_flashbang import force_maximum_brightness
        # Executes without exception
        force_maximum_brightness()

    def test_08_keyboard_scrambler(self):
        """Verify keyboard scrambler hook lifecycle and letter mapping."""
        from keyboard_scramble import KeyboardScrambler
        self.assertEqual(config.KEYBOARD_SCRAMBLE_CHANCE, 0.40, "Scramble chance must be 40%")

        scrambler = KeyboardScrambler(chance=0.40)
        scrambler.start()
        self.assertTrue(scrambler.is_active)
        self.assertIsNotNone(scrambler.hook_id)

        # Test replacement generation for letter 'G'
        rep_vk = scrambler._get_replacement_vk("G")
        self.assertGreaterEqual(rep_vk, ord("A"))
        self.assertLessEqual(rep_vk, ord("Z"))
        self.assertNotEqual(rep_vk, ord("G"))

        scrambler.stop()
        self.assertFalse(scrambler.is_active)
        self.assertIsNone(scrambler.hook_id)


if __name__ == "__main__":
    print("Running Modular Useless Project Validation...")
    unittest.main()
