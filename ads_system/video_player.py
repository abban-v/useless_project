"""
Ad Video Player for Fullscreen Ad System.
Renders hardware-accelerated full-screen video using native OpenCV windows (60+ FPS)
with perfectly synchronized 100% volume audio via WMPlayer.OCX.
Supports single-video playback (with duration limits) and multi-step sequence transitions
(e.g., Countdown 4s -> Explosion Video + MP3).
"""

import time
import threading
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any

import cv2
import pythoncom
import win32com.client
import win32gui
import win32con


class AdVideoPlayer:
    """
    Manages full-screen video playback and audio synchronization in a background thread.
    Communicates completion back to Tkinter via master.after().
    """

    def __init__(self, master=None):
        self.master = master
        self.is_playing = False
        self._stop_requested = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.win_name = "USLESS_FULLSCREEN_AD"

    def play_video(
        self,
        video_path: Path,
        audio_path: Optional[Path] = None,
        max_duration: Optional[float] = None,
        on_finish: Optional[Callable] = None,
    ):
        """
        Plays a single video fullscreen. If max_duration is specified, stops after that many seconds.
        """
        steps = [
            {
                "video": video_path,
                "audio": audio_path or video_path,
                "max_duration": max_duration,
            }
        ]
        self.play_sequence(steps, on_finish=on_finish)

    def play_sequence(self, steps: List[Dict[str, Any]], on_finish: Optional[Callable] = None):
        """
        Plays a multi-stage video sequence in a single continuous fullscreen window.
        Each step in `steps` is a dict:
            {"video": Path, "audio": Optional[Path], "max_duration": Optional[float]}
        """
        with self._lock:
            if self.is_playing:
                self.stop()

            self.is_playing = True
            self._stop_requested = False
            self._thread = threading.Thread(
                target=self._run_sequence,
                args=(steps, on_finish),
                daemon=True,
                name="AdVideoPlayerThread",
            )
            self._thread.start()

    def _run_sequence(self, steps: List[Dict[str, Any]], on_finish: Optional[Callable]):
        pythoncom.CoInitialize()
        player = None

        try:
            player = win32com.client.Dispatch("WMPlayer.OCX")
            player.settings.volume = 100

            # Create native OpenCV fullscreen window
            cv2.namedWindow(self.win_name, cv2.WINDOW_NORMAL)
            cv2.setWindowProperty(self.win_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

            # Ensure the window is topmost
            time.sleep(0.05)
            hwnd = win32gui.FindWindow(None, self.win_name)
            if hwnd:
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOPMOST,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW,
                )

            for step in steps:
                if self._stop_requested:
                    break

                video_file = str(Path(step["video"]).resolve())
                audio_file = str(Path(step.get("audio") or step["video"]).resolve())
                max_duration = step.get("max_duration")

                cap = cv2.VideoCapture(video_file)
                if not cap.isOpened():
                    print(f"[AdVideoPlayer] Could not open video file: {video_file}")
                    continue

                fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                if fps <= 0 or fps > 120:
                    fps = 30.0

                # Start audio track with 100% volume and unmuted
                try:
                    player.controls.stop()
                    player.URL = audio_file
                    player.settings.volume = 100
                    player.settings.mute = False
                    player.controls.play()
                except Exception as e:
                    print(f"[AdVideoPlayer] Audio playback warning: {e}")

                # Initial COM message pump to transition WMPlayer to playing state
                for _ in range(5):
                    pythoncom.PumpWaitingMessages()
                    time.sleep(0.01)

                start_time = time.time()
                frame_idx = 0

                while not self._stop_requested:
                    pythoncom.PumpWaitingMessages()
                    elapsed = time.time() - start_time
                    if max_duration is not None and elapsed >= max_duration:
                        break

                    ret, frame = cap.read()
                    if not ret:
                        break

                    cv2.imshow(self.win_name, frame)
                    frame_idx += 1

                    # Synchronization delay
                    target_time = start_time + (frame_idx / fps)
                    sleep_s = target_time - time.time()
                    delay_ms = max(1, int(sleep_s * 1000)) if sleep_s > 0 else 1
                    key = cv2.waitKey(delay_ms) & 0xFF
                    if key == 27:  # Esc (failsafe within CV)
                        break

                cap.release()
                try:
                    player.controls.stop()
                except Exception:
                    pass

        except Exception as e:
            print(f"[AdVideoPlayer] Playback error: {e}")
        finally:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass

            if player:
                try:
                    player.close()
                except Exception:
                    pass
                del player

            pythoncom.CoUninitialize()

            with self._lock:
                self.is_playing = False

            if on_finish and not self._stop_requested:
                if self.master:
                    try:
                        self.master.after(0, on_finish)
                    except Exception:
                        on_finish()
                else:
                    on_finish()

    def stop(self):
        """Immediately halts video and audio playback and destroys window."""
        with self._lock:
            self._stop_requested = True

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

        self.is_playing = False
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        print("[AdVideoPlayer] Video player stopped and windows closed.")
