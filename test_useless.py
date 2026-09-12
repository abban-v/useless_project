import sys
import unittest
import tkinter as tk
from pathlib import Path

# Ensure useless_project root is in sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

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
        self.assertGreater(config.FLASHBANG_CHANCE, 0.0, "Flashbang chance must be > 0")
        self.assertLessEqual(config.FLASHBANG_CHANCE, 1.0, "Flashbang chance must be <= 1.0")
        self.assertGreater(config.HAZARD_INTERVAL_SECONDS, 0.0, "Flashbang interval must be > 0")
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

        # Verify chaos click triggering during stamina depletion freeze
        clicked = []
        ctrl_click = MouseSpeedController(on_click_callback=lambda: clicked.append(True))
        ctrl_click.freeze_cursor(400, 400)
        res = ctrl_click.gesture_blocker._mouse_hook_callback(0, 0x0201, 0)
        self.assertEqual(res, 1, "Click must remain blocked from OS")
        self.assertEqual(len(clicked), 1, "Chaos callback must be invoked when user clicks during freeze")
        ctrl_click.unfreeze_cursor()

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

        # Test MouseStaminaHUD creation, idle tick, and cleanup
        speed_ctrl = MouseSpeedController()
        hud = MouseStaminaHUD(root, speed_ctrl)
        self.assertTrue(hud.winfo_exists())
        self.assertIsNotNone(hud._tick_id)
        hud.cleanup()
        self.assertIsNone(hud._tick_id)
        speed_ctrl.cleanup()

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

        # Test on_key_callback and dynamic chance property
        keys_clicked = []
        scrambler2 = KeyboardScrambler(on_key_callback=lambda: keys_clicked.append(True))
        self.assertEqual(scrambler2.chance, config.KEYBOARD_SCRAMBLE_CHANCE)
        scrambler2.chance = 0.55
        self.assertEqual(scrambler2.chance, 0.55)

    def test_09_flashbang_audio_and_volume(self):
        """Verify audioloud.mp3 exists, audio player loads, and volume boosts to 100%."""
        from pathlib import Path
        from screen_flashbang import play_flashbang_audio, stop_flashbang_audio
        from audio_pump import WindowsAudioController

        mp3 = (Path(__file__).parent / "memes" / "audioloud.mp3").resolve()
        self.assertTrue(mp3.exists(), "audioloud.mp3 must exist in memes folder")

        # Test audio playback lifecycle
        played = play_flashbang_audio(mp3)
        self.assertTrue(played)
        stop_flashbang_audio()

        # Test volume boost
        ctrl = WindowsAudioController()
        orig = ctrl.get_volume()
        ctrl.set_volume(0.2)
        if ctrl.get_volume() < 1.0:
            ctrl.set_volume(1.0)
        self.assertAlmostEqual(ctrl.get_volume(), 1.0, delta=0.03)
        ctrl.set_volume(orig)

    def test_10_audio_hazard_suppression(self):
        """Verify program audio from flashbang suppresses audio drop hazard and pump popup."""
        from screen_flashbang import (
            play_flashbang_audio,
            stop_flashbang_audio,
            is_flashbang_audio_playing,
        )
        ctrl = WindowsAudioController()
        monitor = AudioHazardMonitor(
            audio_ctrl=ctrl,
            on_drop_callback=lambda: None,
        )

        # 1. Test manual timed suppression
        self.assertFalse(monitor.is_suppressed())
        monitor.suppress_for(5.0)
        self.assertTrue(monitor.is_suppressed())

        # 2. Test dynamic detection of flashbang audio playback
        play_flashbang_audio()
        self.assertTrue(is_flashbang_audio_playing(), "Flashbang audio must report as playing")
        self.assertTrue(monitor.is_suppressed(), "Audio monitor must be suppressed while flashbang audio plays")

        # Stop audio and verify reset
        stop_flashbang_audio()
        self.assertFalse(is_flashbang_audio_playing(), "Flashbang audio must not report playing when stopped")

        # 3. Test HazardManager suppression integration
        root = tk.Tk()
        root.withdraw()
        pump = PumpOverlay(root, on_progress=lambda p: None, on_complete=lambda: None)
        hazard_mgr = HazardManager(root, audio_ctrl=ctrl, audio_monitor=monitor, pump_overlay=pump)

        # Simulate pump hazard active before flashbang
        monitor.is_hazard_active = True
        pump.show_hazard()
        self.assertTrue(pump.is_active)

        # Trigger flashbang: must suppress monitor, dismiss hazard, and dismiss pump
        hazard_mgr.trigger_flashbang()
        self.assertTrue(monitor.is_suppressed(), "Monitor must be suppressed for 14s")
        self.assertFalse(monitor.is_hazard_active, "Hazard state must be dismissed by flashbang")
        self.assertFalse(pump.is_active, "Pump overlay must be dismissed by flashbang")

        stop_flashbang_audio()

        # 4. Test HazardManager dynamic properties and timer cancellation
        self.assertEqual(hazard_mgr.chance, config.FLASHBANG_CHANCE)
        hazard_mgr.chance = 0.85
        self.assertEqual(hazard_mgr.chance, 0.85)
        hazard_mgr.chance = config.FLASHBANG_CHANCE
        hazard_mgr.start()
        self.assertTrue(hazard_mgr.is_running)
        self.assertIsNotNone(hazard_mgr._timer_id)
        hazard_mgr.stop()
        self.assertFalse(hazard_mgr.is_running)
        self.assertIsNone(hazard_mgr._timer_id)

        root.destroy()
        monitor.stop()

    def test_11_flashbang_action_keys_and_volume_lock(self):
        """Verify action keys and volume lowering attempts are blocked during flashbang."""
        import time
        from screen_flashbang import FlashbangActionKeyBlocker
        ctrl = WindowsAudioController()
        orig_vol = ctrl.get_volume()
        orig_mute = ctrl.get_mute()

        # 1. Verify get_mute and set_mute methods
        ctrl.set_mute(True)
        self.assertTrue(ctrl.get_mute())
        ctrl.set_mute(False)
        self.assertFalse(ctrl.get_mute())

        # 2. Test FlashbangActionKeyBlocker hooks and blocked keys
        blocker = FlashbangActionKeyBlocker(ctrl)
        blocker.start()
        self.assertTrue(blocker.is_active)
        self.assertIsNotNone(blocker.hook_id)

        # Ensure safety keys (F8, Ctrl, Shift, Q) are NEVER blocked
        self.assertNotIn(0x77, blocker.BLOCKED_KEYS, "F8 must NOT be blocked!")
        self.assertNotIn(0x11, blocker.BLOCKED_KEYS, "Ctrl must NOT be blocked!")
        self.assertNotIn(0x10, blocker.BLOCKED_KEYS, "Shift must NOT be blocked!")
        self.assertNotIn(0x51, blocker.BLOCKED_KEYS, "Q must NOT be blocked!")

        # Ensure volume and action keys ARE blocked
        self.assertIn(0xAE, blocker.BLOCKED_KEYS, "Volume Down must be blocked")
        self.assertIn(0xAD, blocker.BLOCKED_KEYS, "Volume Mute must be blocked")
        self.assertIn(0x20, blocker.BLOCKED_KEYS, "Space action key must be blocked")
        self.assertIn(0x0D, blocker.BLOCKED_KEYS, "Return action key must be blocked")
        self.assertIn(0x1B, blocker.BLOCKED_KEYS, "Escape action key must be blocked")

        blocker.stop()
        self.assertFalse(blocker.is_active)
        self.assertIsNone(blocker.hook_id)

        # Restore original volume and mute
        ctrl.set_volume(orig_vol)
        ctrl.set_mute(orig_mute)

    def test_12_media_chaos_engine(self):
        """Verify Click-Triggered Media Chaos engine (cats, rats, furbys, audio, suppression)."""
        import time
        from unittest.mock import patch
        from random_media import (
            MediaChaosManager,
            ChaosAudioEngine,
            ChaosOverlay,
            ClickListener,
            is_chaos_audio_playing,
        )
        from random_media.assets.sprites import (
            get_cat_sprite,
            get_rat_frames,
            get_furby_sprite,
        )

        # 1. Verify configuration values
        self.assertEqual(config.CLICK_CHAOS_CHANCE, 0.60, "Click event chance must be 60%")
        self.assertIn(config.CLICK_CAT_COUNT, (0, 500))
        self.assertIn(config.CLICK_RAT_COUNT, (0, 50))
        self.assertIn(config.CLICK_FURBY_COUNT, (0, 4))
        self.assertEqual(config.KEYBOARD_SOUND_CHANCE, 0.30, "Keyboard sound chance must be 30%")
        self.assertEqual(config.CLICK_MUSIC_CHANCE, 0.60, "Music chance must be 60%")
        self.assertEqual(config.CLICK_VISUAL_DURATION_SECONDS, 10.0, "Visual chaos duration must be 10 seconds")
        self.assertEqual(config.CLICK_VIDEO_MIN_COUNT, 2, "Min video frames must be 2")
        self.assertEqual(config.CLICK_VIDEO_MAX_COUNT, 5, "Max video frames must be 5")

        # 2. Verify sprites and video assets load
        root = tk.Tk()
        root.withdraw()

        cat_img = get_cat_sprite()
        self.assertIsNotNone(cat_img)
        rat_frames = get_rat_frames()
        self.assertEqual(len(rat_frames), 8, "Low-poly rat must have 8 rotation frames")
        furby_img = get_furby_sprite()
        self.assertIsNotNone(furby_img)

        from random_media.assets.video_frames import get_available_videos, load_video_pil_frames
        available_vids = get_available_videos()
        self.assertGreater(len(available_vids), 0, "explosionvideo.mp4 must be discovered")
        sample_frames = load_video_pil_frames(str(available_vids[0]))
        self.assertGreater(len(sample_frames), 0, "Video frames must be extracted")

        # 3. Test ClickListener lifecycle
        clicked = []
        listener = ClickListener(on_click_callback=lambda: clicked.append(True))
        listener.start()
        self.assertTrue(listener.is_active)
        self.assertIsNotNone(listener._thread)
        listener.stop()
        self.assertFalse(listener.is_active)

        # 4. Test ChaosAudioEngine, music tracking, and suppression
        audio_engine = ChaosAudioEngine()
        self.assertFalse(audio_engine.is_chaos_audio_playing())
        self.assertFalse(audio_engine.is_music_track_playing())

        # Test meow trigger
        audio_engine.play_meow()
        self.assertTrue(audio_engine.is_chaos_audio_playing())
        self.assertFalse(audio_engine.is_music_track_playing(), "Meow is sound effect, not background music")
        self.assertTrue(is_chaos_audio_playing())

        # Test music track trigger
        audio_engine.roll_music_chaos(1.0)
        self.assertTrue(audio_engine.is_music_track_playing(), "Music track must be active")

        # Test audio monitor suppression integration
        ctrl = WindowsAudioController()
        monitor = AudioHazardMonitor(audio_ctrl=ctrl, on_drop_callback=lambda: None)
        self.assertTrue(monitor.is_suppressed(), "Monitor must be suppressed while chaos audio plays")

        # Test play_random_sound (keyboard sound trigger)
        audio_engine.play_random_sound()
        self.assertTrue(audio_engine.is_chaos_audio_playing())
        self.assertTrue(audio_engine.is_music_track_playing())

        audio_engine.stop_all()
        self.assertFalse(audio_engine.is_chaos_audio_playing())
        self.assertFalse(audio_engine.is_music_track_playing())

        # Test MediaChaosManager keyboard chaos evaluation
        media_mgr = MediaChaosManager(root)
        media_mgr.is_running = True
        with patch("random.random", return_value=0.10):  # 0.10 < 0.30
            with patch.object(media_mgr.audio_engine, "play_random_sound") as mock_play:
                media_mgr._evaluate_keyboard_chaos()
                mock_play.assert_called_once()

        with patch("random.random", return_value=0.50):  # 0.50 >= 0.30
            with patch.object(media_mgr.audio_engine, "play_random_sound") as mock_play:
                media_mgr._evaluate_keyboard_chaos()
                mock_play.assert_not_called()
        media_mgr.stop()

        # 5. Test ChaosOverlay entity spawning, video frames, auto-dismiss, and music retention
        overlay = ChaosOverlay(root, audio_engine)
        self.assertFalse(overlay.has_active_visuals())

        overlay.spawn_cats(20)
        self.assertGreater(len(overlay.cats), 0)
        self.assertTrue(overlay.has_active_visuals())
        self.assertIsNotNone(overlay._dismiss_timer_id, "Dismiss timer must be scheduled on spawn")

        overlay.spawn_rats(10)
        self.assertEqual(len(overlay.rats), 10)

        overlay.spawn_furbys()
        self.assertEqual(len(overlay.furby_items), 4)

        # Spawn 2-5 video frames
        overlay.spawn_video_frames()
        self.assertGreaterEqual(len(overlay.video_players), config.CLICK_VIDEO_MIN_COUNT)
        self.assertLessEqual(len(overlay.video_players), config.CLICK_VIDEO_MAX_COUNT)

        # Test simulation step
        overlay._sim_loop()

        # Test music retention: if music is active, visual chaos must NOT dismiss
        class MockActiveMusic:
            def is_music_track_playing(self):
                return True
        overlay.audio_engine = MockActiveMusic()
        overlay._on_dismiss_timer()
        self.assertIsNotNone(overlay.toplevel, "Visual chaos must be retained while music plays!")
        self.assertGreater(len(overlay.video_players), 0)

        # When music finishes, visual chaos dismisses
        class MockFinishedMusic:
            def is_music_track_playing(self):
                return False
        overlay.audio_engine = MockFinishedMusic()
        overlay._on_dismiss_timer()
        self.assertIsNone(overlay.toplevel, "Visual chaos must dismiss once music finishes")
        self.assertEqual(len(overlay.cats), 0)
        self.assertEqual(len(overlay.rats), 0)
        self.assertEqual(len(overlay.video_players), 0)

        monitor.stop()
        root.destroy()

    def test_13_reddit_meme_sourcing(self):
        """Test Reddit meme fetcher, cache management, media frame decoders, and frame overlay."""
        from random_media.reddit_memes import RedditMemeFetcher, MemeItem, get_reddit_fetcher
        from random_media.audio_chaos import ChaosAudioEngine
        from random_media.chaos_overlay import ChaosOverlay
        from random_media.assets.video_frames import (
            get_available_media_items,
            load_media_pil_frames,
            get_media_tk_frames,
            _fit_image_to_frame,
        )
        import tempfile
        from pathlib import Path
        from PIL import Image

        # 1. Test media URL validation
        fetcher = get_reddit_fetcher()
        self.assertTrue(fetcher._is_supported_media_url("https://i.redd.it/test1.png"))
        self.assertTrue(fetcher._is_supported_media_url("https://i.redd.it/test2.jpg"))
        self.assertTrue(fetcher._is_supported_media_url("https://i.redd.it/test3.gif"))
        self.assertTrue(fetcher._is_supported_media_url("https://example.com/vid.mp4"))
        self.assertFalse(fetcher._is_supported_media_url("https://reddit.com/r/memes/comments/123/text_post"))
        self.assertFalse(fetcher._is_supported_media_url("https://youtube.com/watch?v=123"))

        # 2. Test cache loading and retrieval
        available = fetcher.get_available_memes()
        self.assertIsInstance(available, list)
        if available:
            meme = fetcher.get_random_meme()
            self.assertIsNotNone(meme)
            self.assertTrue(meme.file_path.exists())
            self.assertIn(meme.media_type, ("image", "gif", "video"))

        # 3. Test multi-format media decoder and letterbox scaling
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Create a test synthetic static image
            test_img_path = tmp_path / "test_meme.png"
            img = Image.new("RGB", (300, 200), (255, 0, 128))
            img.save(test_img_path)

            frames = load_media_pil_frames(str(test_img_path), target_width=160, target_height=218)
            self.assertEqual(len(frames), 1)
            self.assertEqual(frames[0].size, (160, 218))

            # Test letterbox aspect ratio helper
            fitted = _fit_image_to_frame(img, 160, 218)
            self.assertEqual(fitted.size, (160, 218))

        # 4. Test unified media pool discovery
        media_pool = get_available_media_items()
        self.assertGreater(len(media_pool), 0)
        # Should include both local video and Reddit memes if cached
        sources = {item.source for item in media_pool}
        self.assertIn("local", sources)

        # 5. Test Tkinter integration with ChaosOverlay
        root = tk.Tk()
        root.withdraw()
        audio_engine = ChaosAudioEngine(root)
        overlay = ChaosOverlay(root, audio_engine)

        overlay.spawn_video_frames()
        self.assertGreaterEqual(len(overlay.video_players), config.CLICK_VIDEO_MIN_COUNT)
        self.assertLessEqual(len(overlay.video_players), config.CLICK_VIDEO_MAX_COUNT)

        for player in overlay.video_players:
            self.assertGreater(len(player.frames), 0)
            self.assertEqual(player.frames[0].width(), config.CLICK_VIDEO_WIDTH)
            self.assertEqual(player.frames[0].height(), config.CLICK_VIDEO_HEIGHT)

        overlay.clear_all()
        root.destroy()

    def test_14_shoe_game(self):
        """Verify Shoe Game module: ShoeGameManager, ShoeAudioEnforcer, Real Mode, and Virtual Mode with double scream."""
        import time
        from unittest.mock import MagicMock, patch
        from shoe_game import ShoeGameManager, ShoeAudioEnforcer, RealShoeGame, VirtualShoeGame
        from shoe_game.virtual_mode import Hurdle
        import config

        # 1. Config validation
        self.assertIn(config.SHOE_GAME_INTERVAL_SECONDS, (30.0, 60.0))
        self.assertGreaterEqual(config.SHOE_GAME_CHANCE, 0.0)
        self.assertLessEqual(config.SHOE_GAME_CHANCE, 1.0)
        self.assertEqual(config.SHOE_GAME_REAL_MODE_SECONDS, 10.0)
        self.assertEqual(config.SHOE_GAME_SCREAM_SECONDS, 3.0)

        # 2. ShoeAudioEnforcer safety keys and lock
        ctrl = WindowsAudioController()
        enforcer = ShoeAudioEnforcer(ctrl)
        self.assertNotIn(0x77, enforcer.BLOCKED_KEYS, "F8 must NOT be blocked by ShoeAudioEnforcer!")
        self.assertNotIn(0x11, enforcer.BLOCKED_KEYS, "Ctrl must NOT be blocked!")
        self.assertNotIn(0x10, enforcer.BLOCKED_KEYS, "Shift must NOT be blocked!")
        self.assertNotIn(0x51, enforcer.BLOCKED_KEYS, "Q must NOT be blocked!")
        self.assertIn(0xAE, enforcer.BLOCKED_KEYS, "Volume Down must be blocked!")
        self.assertIn(0xAD, enforcer.BLOCKED_KEYS, "Volume Mute must be blocked!")

        # 3. VirtualShoeGame Irony & Double Scream Verification
        root = tk.Tk()
        root.withdraw()

        with patch.object(enforcer, "play_double_scream") as mock_double_scream:
            virtual_game = VirtualShoeGame(root, audio_ctrl=ctrl, duration_seconds=5.0)
            virtual_game.audio_enforcer = enforcer
            virtual_game.withdraw()

            # Verify initial state
            initial_speed = virtual_game.hurdle_speed
            initial_delay = virtual_game.hurdle_spawn_delay_ms
            virtual_game.state = "WALKING"

            # Test Irony: Player mashing keys INCREASES hurdle speed and spawn frequency
            mock_key_event = MagicMock()
            mock_key_event.char = "a"
            virtual_game._on_player_key(mock_key_event)
            self.assertEqual(virtual_game.keys_mashed, 1)
            self.assertGreater(virtual_game.hurdle_speed, initial_speed)
            self.assertLess(virtual_game.hurdle_spawn_delay_ms, initial_delay)

            # Test Irony: Player clicking mouse also INCREASES hurdle speed and spawn frequency
            prev_speed = virtual_game.hurdle_speed
            mock_click_event = MagicMock()
            mock_click_event.x = 200
            mock_click_event.y = 300
            virtual_game._on_player_click(mock_click_event)
            self.assertEqual(virtual_game.clicks_count, 1)
            self.assertGreater(virtual_game.hurdle_speed, prev_speed)

            # Test Hurdle Collision: Stepping on leaf triggers play_double_scream(duration=3.0)
            test_hurdle = Hurdle("leaf", x=virtual_game.shoe_x, y=virtual_game.shoe_y, w=40, h=25)
            virtual_game.hurdles = [test_hurdle]
            virtual_game._update_hurdles(time.time())

            self.assertTrue(test_hurdle.stepped, "Hurdle must be marked stepped upon shoe collision")
            self.assertEqual(virtual_game.leaves_crushed, 1)
            mock_double_scream.assert_called_with(duration=3.0)

            virtual_game.dismiss()

        # 4. RealShoeGame Verification
        with patch.object(ShoeAudioEnforcer, "play_all_music"):
            real_game = RealShoeGame(root, audio_ctrl=ctrl, duration_seconds=1.0)
            real_game.withdraw()
            self.assertTrue(real_game.canvas.winfo_exists())
            real_game.dismiss()

        # 5. ShoeGameManager Verification
        mgr = ShoeGameManager(root, ctrl)
        self.assertEqual(mgr.chance, config.SHOE_GAME_CHANCE)
        mgr.chance = 0.75
        self.assertEqual(mgr.chance, 0.75)
        mgr.chance = config.SHOE_GAME_CHANCE
        mgr.start()
        self.assertTrue(mgr.is_running)
        self.assertIsNotNone(mgr._timer_id)

        # Test manual launch
        with patch.object(ShoeAudioEnforcer, "play_all_music"):
            mgr.force_launch("real")
            self.assertIsNotNone(mgr.active_game)
            mgr.stop()
            self.assertFalse(mgr.is_running)
            self.assertIsNone(mgr.active_game)

        root.destroy()


if __name__ == "__main__":
    print("Running Modular Useless Project Validation...")
    unittest.main()
