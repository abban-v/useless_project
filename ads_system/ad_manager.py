"""
Ad Manager for Fullscreen Ad System.
Coordinates:
- 1-minute periodic timer for alternating fullscreen ads (amul.mp4 and seemati.mp4).
- Stopping all background music during ad playback.
- Disabling keyboard and mouse via AdInputBlocker.
- Presenting the 'Should you disable ads?' prompt upon ad completion.
- Handling 'No': resumes normal desktop operations until the next minute.
- Handling 'Yes': launches the trap revenge sequence:
    1. countdown.mp4 (plays first 4.0 seconds)
    2. explosionsmall.mp4 + explosion.mp3 simultaneously
    3. Next ad in the alternating order.
"""

import tkinter as tk
from pathlib import Path
from typing import Optional, Callable, List

import config
from ads_system.input_blocker import AdInputBlocker
from ads_system.video_player import AdVideoPlayer
from ads_system.prompt_dialog import AdPromptDialog
from random_media.audio_chaos import set_chaos_audio_blocked, stop_all_chaos_audio
from screen_flashbang.audio_player import stop_flashbang_audio


class AdManager:
    """
    Manages periodic ad scheduling, fullscreen video transitions, input blocking,
    and prompt interactions.
    """

    def __init__(
        self,
        master: tk.Tk,
        media_chaos=None,
        audio_engine=None,
        audio_monitor=None,
        audio_ctrl=None,
        shoe_game=None,
        hazard_manager=None,
        emergency_exit_callback: Optional[Callable] = None,
    ):
        self.master = master
        self.media_chaos = media_chaos
        self.audio_engine = audio_engine or (media_chaos.audio_engine if media_chaos else None)
        self.audio_monitor = audio_monitor
        self.audio_ctrl = audio_ctrl
        if self.audio_ctrl is None:
            try:
                from audio_pump.audio_controller import WindowsAudioController
                self.audio_ctrl = WindowsAudioController()
            except Exception:
                pass
        self.shoe_game = shoe_game
        self.hazard_manager = hazard_manager
        self.emergency_exit_callback = emergency_exit_callback

        self.blocker = AdInputBlocker(emergency_exit_callback=self.emergency_exit_callback)
        self.player = AdVideoPlayer(master=self.master)
        self.active_prompt: Optional[AdPromptDialog] = None

        self.is_running = False
        self._timer_id: Optional[str] = None
        self.current_ad_index = 0

        # Load available ad videos
        self.ads_list = self._discover_ads()

    def _discover_ads(self) -> List[Path]:
        """Discovers ad video files in ads/ directory, ensuring amul.mp4 and seemati.mp4 order."""
        ads_dir = getattr(config, "ADS_DIR", config.BASE_DIR / "ads")
        preferred = ["amul.mp4", "seemati.mp4"]
        found = []
        for name in preferred:
            p = ads_dir / name
            if p.exists():
                found.append(p)

        # Append any other .mp4 in ads/
        if ads_dir.exists():
            for p in sorted(ads_dir.glob("*.mp4")):
                if p not in found:
                    found.append(p)

        return found

    @property
    def is_ad_active(self) -> bool:
        """Returns True if an ad, prompt, or revenge sequence is currently active."""
        return self.player.is_playing or (self.active_prompt is not None and self.active_prompt.winfo_exists())

    def _silence_all_other_audio(self):
        """
        Immediately silences and blocks all other application audio (Chaos tracks,
        keyboard sounds, flashbang MCI audio, shoe game audio).
        """
        # 1. Global block for chaos audio engine & stop any active players
        set_chaos_audio_blocked(True)
        stop_all_chaos_audio()
        if self.audio_engine and hasattr(self.audio_engine, "stop_all"):
            self.audio_engine.stop_all()

        # 2. Halt screen flashbang MCI audio
        try:
            stop_flashbang_audio()
        except Exception:
            pass

        # 3. Halt Shoe Game audio & release volume lock if active
        if self.shoe_game:
            try:
                active_game = getattr(self.shoe_game, "active_game", None)
                if active_game and hasattr(active_game, "audio_enforcer") and active_game.audio_enforcer:
                    active_game.audio_enforcer.stop_all_audio()
            except Exception:
                pass

        # 4. Mark media chaos as ad active and clear on-screen meme frames
        if self.media_chaos:
            self.media_chaos.is_ad_active = True
            if hasattr(self.media_chaos, "overlay") and self.media_chaos.overlay:
                try:
                    self.media_chaos.overlay.clear_all()
                except Exception:
                    pass

        # 5. Suppress audio hazard detection so ad sound doesn't trigger volume drops
        if self.audio_monitor:
            if hasattr(self.audio_monitor, "suppress_for"):
                self.audio_monitor.suppress_for(120.0)
            if hasattr(self.audio_monitor, "suppress_detection"):
                self.audio_monitor.suppress_detection(120.0)
            if hasattr(self.audio_monitor, "dismiss_hazard"):
                self.audio_monitor.dismiss_hazard()

        # 6. Ensure master volume is at 100% and unmuted for ad playback
        if self.audio_ctrl:
            try:
                self.audio_ctrl.set_mute(False)
                try:
                    vol = float(self.audio_ctrl.get_volume())
                    if vol < 1.0:
                        self.audio_ctrl.set_volume(1.0)
                except Exception:
                    self.audio_ctrl.set_volume(1.0)
            except Exception:
                pass

        print("[AdManager] ALL other application sounds silenced and blocked.")

    def _restore_audio_permission(self):
        """
        Restores normal audio permissions after ad sequence has completely finished.
        """
        set_chaos_audio_blocked(False)
        if self.media_chaos:
            self.media_chaos.is_ad_active = False
        print("[AdManager] Background audio permissions restored.")

    @property
    def interval_seconds(self) -> float:
        return getattr(config, "ADS_INTERVAL_SECONDS", 60.0)

    def start(self, initial_delay_seconds: Optional[float] = None):
        """Starts the periodic ad manager timer."""
        if self.is_running:
            return

        self.is_running = True
        delay = initial_delay_seconds if initial_delay_seconds is not None else self.interval_seconds
        self._schedule_timer(delay)
        print(f"[AdManager] Periodic Fullscreen Ad timer started (every {self.interval_seconds}s, {len(self.ads_list)} ads loaded).")

    def _schedule_timer(self, delay_seconds: Optional[float] = None):
        """Schedules the next ad check after delay_seconds."""
        if self._timer_id is not None:
            try:
                self.master.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

        delay = delay_seconds if delay_seconds is not None else self.interval_seconds
        delay_ms = max(100, int(delay * 1000))
        self._timer_id = self.master.after(delay_ms, self._on_periodic_timer)

    def _on_periodic_timer(self):
        """Triggered periodically to pop up an alternating fullscreen ad."""
        self._timer_id = None
        if not self.is_running:
            return

        # If an ad or revenge sequence is already active, wait and re-check
        if self.player.is_playing or (self.active_prompt and self.active_prompt.winfo_exists()):
            self._schedule_timer(self.interval_seconds)
            return

        self.launch_ad()

    def launch_ad(self, ad_path: Optional[Path] = None):
        """
        Launches an alternating ad fullscreen, stops other music, and disables keyboard/mouse.
        """
        if not self.ads_list:
            print("[AdManager] No ad videos found in ads/ directory.")
            self._schedule_timer(self.interval_seconds)
            return

        if ad_path is None:
            ad_path = self.ads_list[self.current_ad_index % len(self.ads_list)]
            self.current_ad_index += 1

        print(f"[AdManager] Launching Fullscreen Ad: {ad_path.name}")

        # 1. Stop all other music and silence entire application
        self._silence_all_other_audio()

        # 2. Disable keyboard and mouse input
        self.blocker.start()

        # 3. Play ad video fullscreen
        self.player.play_video(ad_path, on_finish=self._on_ad_finished)

    def _on_ad_finished(self):
        """Called on Tkinter main thread when the ad video finishes."""
        print("[AdManager] Ad playback finished.")

        # Re-enable keyboard and mouse so user can interact with the prompt
        self.blocker.stop()

        # Display the prompt dialog: "Should you disable ads?"
        if self.active_prompt and self.active_prompt.winfo_exists():
            try:
                self.active_prompt.destroy()
            except Exception:
                pass

        self.active_prompt = AdPromptDialog(
            master=self.master,
            on_yes=self._on_user_yes,
            on_no=self._on_user_no,
        )

    def _on_user_no(self):
        """User clicked 'No': do nothing and continue as usual."""
        print("[AdManager] User clicked NO. Resuming normal operations.")
        self.active_prompt = None
        self._restore_audio_permission()
        # Schedule next ad popup after normal interval
        if self.is_running:
            self._schedule_timer(self.interval_seconds)

    def _on_user_yes(self):
        """
        User clicked 'Yes': trigger trap sequence:
        1. countdown.mp4 (only first 4.0 seconds)
        2. explosionsmall.mp4 + explosion.mp3 simultaneously
        3. next ad in alternating order!
        """
        print("[AdManager] User clicked YES! Launching countdown trap & revenge sequence...")
        self.active_prompt = None

        # 1. Ensure all other audio remains silenced
        self._silence_all_other_audio()

        # 2. Disable keyboard and mouse
        self.blocker.start()

        # 3. Build sequence steps
        countdown_vid = getattr(config, "COUNTDOWN_VIDEO", config.MUSIC_DIR / "countdown.mp4")
        explosion_vid = getattr(config, "EXPLOSION_VIDEO", config.MEMES_DIR / "explosionsmall.mp4")
        explosion_aud = getattr(config, "EXPLOSION_AUDIO", config.MEMES_DIR / "explosion.mp3")
        countdown_sec = getattr(config, "ADS_COUNTDOWN_PLAY_SECONDS", 4.0)

        steps = [
            {
                "video": countdown_vid,
                "audio": countdown_vid,
                "max_duration": countdown_sec,
            },
            {
                "video": explosion_vid,
                "audio": explosion_aud,
                "max_duration": None,
            },
        ]

        self.player.play_sequence(steps, on_finish=self._on_revenge_sequence_finished)

    def _on_revenge_sequence_finished(self):
        """Explosion finished! Immediately launch the next ad in order."""
        if not self.ads_list:
            self.blocker.stop()
            self._restore_audio_permission()
            if self.is_running:
                self._schedule_timer(self.interval_seconds)
            return

        next_ad = self.ads_list[self.current_ad_index % len(self.ads_list)]
        self.current_ad_index += 1
        print(f"[AdManager] Trap sequence complete! Blasting next ad in order: {next_ad.name}")

        # Ensure all other audio is silenced
        self._silence_all_other_audio()

        # Input blocker is already active; play the ad!
        self.player.play_video(next_ad, on_finish=self._on_ad_finished)

    def stop(self):
        """Stops the ad manager, terminates video/audio, restores input, and cleans up."""
        self.is_running = False

        if self._timer_id is not None:
            try:
                self.master.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

        if self.active_prompt:
            try:
                if self.active_prompt.winfo_exists():
                    self.active_prompt.destroy()
            except Exception:
                pass
            self.active_prompt = None

        self.player.stop()
        self.blocker.stop()
        self._restore_audio_permission()
        print("[AdManager] Ad Manager stopped and resources cleaned up.")
