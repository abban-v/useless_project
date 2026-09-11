"""
Fullscreen Click-Through Chaos Overlay for Click Chaos Module.
Renders all active chaotic entities on a single transparent overlay:
- 500 tiny bouncing cats with staggered spawning and meow track integration
- 50 spinning low-poly rats placed at random desktop coordinates
- 4 soul-staring Furbys locked in the 4 corners of the desktop
Fully click-through via WS_EX_TRANSPARENT | WS_EX_LAYERED so user apps are never blocked.
"""

import random
import ctypes
import tkinter as tk
from typing import List, Dict, Any, Optional

from config import (
    CLICK_CAT_COUNT,
    CLICK_RAT_COUNT,
    CLICK_FURBY_COUNT,
    CAT_SPAWN_STAGGER_MS,
    CLICK_VISUAL_DURATION_SECONDS,
    CLICK_VIDEO_MIN_COUNT,
    CLICK_VIDEO_MAX_COUNT,
    CLICK_VIDEO_WIDTH,
    CLICK_VIDEO_HEIGHT,
)
from random_media.assets.sprites import (
    get_cat_sprite,
    get_rat_frames,
    get_furby_sprite,
)
from random_media.assets.video_frames import (
    get_video_tk_frames,
    get_media_tk_frames,
    get_available_videos,
    get_available_media_items,
)

user32 = ctypes.windll.user32
TRANSPARENT_COLOR = "#010101"


class BouncingCat:
    __slots__ = ("item_id", "x", "y", "vx", "vy")

    def __init__(self, item_id: int, x: float, y: float, vx: float, vy: float):
        self.item_id = item_id
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy


class SpinningRat:
    __slots__ = ("item_id", "x", "y", "frame_idx")

    def __init__(self, item_id: int, x: float, y: float, frame_idx: int):
        self.item_id = item_id
        self.x = x
        self.y = y
        self.frame_idx = frame_idx


class VideoPlayer:
    __slots__ = ("img_id", "border_id", "header_id", "text_id", "x", "y", "frame_idx", "frames")

    def __init__(self, img_id: int, border_id: int, header_id: int, text_id: int, x: float, y: float, frame_idx: int, frames: list):
        self.img_id = img_id
        self.border_id = border_id
        self.header_id = header_id
        self.text_id = text_id
        self.x = x
        self.y = y
        self.frame_idx = frame_idx
        self.frames = frames


class ChaosOverlay:
    """
    Manages the fullscreen click-through canvas and entity physics simulation.
    Visual entities persist for 10 seconds per trigger (or retained until music ends).
    """

    def __init__(self, master: tk.Tk, audio_engine):
        self.master = master
        self.audio_engine = audio_engine

        self.screen_w = master.winfo_screenwidth()
        self.screen_h = master.winfo_screenheight()

        self.toplevel: Optional[tk.Toplevel] = None
        self.canvas: Optional[tk.Canvas] = None

        self.cats: List[BouncingCat] = []
        self.rats: List[SpinningRat] = []
        self.furby_items: List[int] = []
        self.video_players: List[VideoPlayer] = []
        self.video_tk_frames: Dict[str, list] = {}

        self._pending_cat_spawns = 0
        self._cats_spawned_since_meow = 0
        self._is_simulating = False
        self._is_spawning_cats = False
        self._rat_anim_tick = 0
        self._dismiss_timer_id: Optional[str] = None

        # Sprite references
        self.cat_img = None
        self.rat_frames = []
        self.furby_img = None

    def _ensure_overlay(self):
        """Creates and configures the fullscreen transparent click-through window."""
        if self.toplevel and self.toplevel.winfo_exists():
            return

        self.toplevel = tk.Toplevel(self.master)
        self.toplevel.overrideredirect(True)
        self.toplevel.wm_attributes("-topmost", True)
        self.toplevel.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        self.toplevel.config(bg=TRANSPARENT_COLOR)
        self.toplevel.geometry(f"{self.screen_w}x{self.screen_h}+0+0")

        # Explicitly show and raise the toplevel window
        self.toplevel.deiconify()
        self.toplevel.lift()
        self.toplevel.update_idletasks()

        # Set WS_EX_TRANSPARENT (0x00000020) on parent wrapper HWND ONLY.
        parent_hwnd = user32.GetParent(self.toplevel.winfo_id())
        target_hwnd = parent_hwnd if parent_hwnd else self.toplevel.winfo_id()
        style = user32.GetWindowLongW(target_hwnd, -20)
        user32.SetWindowLongW(target_hwnd, -20, style | 0x00000020)
        user32.SetWindowPos(target_hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0020)

        self.canvas = tk.Canvas(
            self.toplevel,
            width=self.screen_w,
            height=self.screen_h,
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        # Load sprites bound to active canvas
        self.cat_img = get_cat_sprite(master=self.canvas)
        self.rat_frames = get_rat_frames(master=self.canvas)
        self.furby_img = get_furby_sprite(master=self.canvas)

    def _schedule_auto_dismiss(self, duration: float = CLICK_VISUAL_DURATION_SECONDS):
        """Schedules clearing of all visual entities after 10 seconds."""
        if self._dismiss_timer_id is not None:
            try:
                self.master.after_cancel(self._dismiss_timer_id)
            except Exception:
                pass
        self._dismiss_timer_id = self.master.after(int(duration * 1000), self._on_dismiss_timer)

    def _on_dismiss_timer(self):
        """Called when the 10-second visual chaos duration expires."""
        # If ambient music is still playing, retain all visual chaos until the song stops!
        if (
            self.audio_engine
            and hasattr(self.audio_engine, "is_music_track_playing")
            and self.audio_engine.is_music_track_playing()
        ):
            # Check again in 300ms until the song finishes
            self._dismiss_timer_id = self.master.after(300, self._on_dismiss_timer)
            return

        self._dismiss_timer_id = None
        print(f"[ChaosOverlay] {CLICK_VISUAL_DURATION_SECONDS}s visual chaos and music finished! Auto-dismissing entities.")
        self.clear_all()

    def has_active_visuals(self) -> bool:
        """Returns True if any visual chaos entities are currently active on screen."""
        return bool(self.cats or self.rats or self.furby_items or self.video_players or self._pending_cat_spawns)

    def spawn_video_frames(self):
        """Spawns 2-5 small rectangular video frames anywhere within display bounds."""
        self._ensure_overlay()
        self._schedule_auto_dismiss()

        count = random.randint(CLICK_VIDEO_MIN_COUNT, CLICK_VIDEO_MAX_COUNT)
        available_media = get_available_media_items()
        w = CLICK_VIDEO_WIDTH
        h = CLICK_VIDEO_HEIGHT

        margin_x = w // 2 + 30
        margin_y = h // 2 + 50
        min_x, max_x = margin_x, max(margin_x + 10, self.screen_w - margin_x)
        min_y, max_y = margin_y, max(margin_y + 10, self.screen_h - margin_y)

        for _ in range(count):
            media_item = random.choice(available_media) if available_media else None
            media_path = str(media_item.path) if media_item else None
            media_key = media_path or "default"

            if media_key not in self.video_tk_frames or not self.video_tk_frames[media_key]:
                self.video_tk_frames[media_key] = get_media_tk_frames(
                    self.canvas,
                    media_path=media_path,
                    target_width=w,
                    target_height=h,
                )

            frames = self.video_tk_frames[media_key]
            if not frames:
                continue

            x = random.randint(min_x, max_x)
            y = random.randint(min_y, max_y)
            start_frame = random.randint(0, len(frames) - 1)

            # Outer border & retro title bar
            border_id = self.canvas.create_rectangle(
                x - w // 2 - 2, y - h // 2 - 18, x + w // 2 + 2, y + h // 2 + 2,
                outline="#00FFCC", width=2, fill="#111116"
            )
            header_id = self.canvas.create_rectangle(
                x - w // 2 - 1, y - h // 2 - 17, x + w // 2 + 1, y - h // 2 - 1,
                fill="#1c1c24", outline=""
            )

            # Title label: show source and title (e.g. "r/memes: Title..." or "▶ EXPLOSION")
            if media_item and media_item.source != "local":
                title_text = f"{media_item.source}: {media_item.title}"
            else:
                title_text = f"▶ {media_item.title if media_item else 'EXPLOSION'}"

            text_id = self.canvas.create_text(
                x - w // 2 + 8, y - h // 2 - 9,
                text=title_text[:20], fill="#00FFCC", anchor="w",
                font=("Consolas", 8, "bold")
            )
            img_id = self.canvas.create_image(x, y, image=frames[start_frame], anchor="center")

            self.video_players.append(VideoPlayer(img_id, border_id, header_id, text_id, x, y, start_frame, frames))

        print(f"[ChaosOverlay] Spawned {count} rectangular meme/video frames (total: {len(self.video_players)}).")
        self._start_simulation()

    def spawn_cats(self, count: int = CLICK_CAT_COUNT):
        """Enqueues cats to be spawned with staggered delays."""
        self._ensure_overlay()
        self._schedule_auto_dismiss()
        self._pending_cat_spawns += count
        print(f"[ChaosOverlay] Queued {count} bouncing cats (total pending: {self._pending_cat_spawns})")
        self._start_simulation()
        if not self._is_spawning_cats:
            self._is_spawning_cats = True
            self._process_cat_spawn_batch()



    def _process_cat_spawn_batch(self):
        """Spawns a batch of cats every stagger interval and triggers meow audio."""
        if not self._pending_cat_spawns or not self.canvas:
            self._is_spawning_cats = False
            return

        # Spawn batch of 10 cats per tick
        batch_size = min(10, self._pending_cat_spawns)
        margin = 25
        min_x, max_x = margin, self.screen_w - margin
        min_y, max_y = margin, self.screen_h - margin

        for _ in range(batch_size):
            x = random.randint(min_x, max_x)
            y = random.randint(min_y, max_y)
            # Velocity between 4 and 9 pixels/tick in random directions
            speed_x = random.choice([-1, 1]) * random.uniform(4.0, 9.0)
            speed_y = random.choice([-1, 1]) * random.uniform(4.0, 9.0)

            item = self.canvas.create_image(x, y, image=self.cat_img, anchor="center")
            self.cats.append(BouncingCat(item, x, y, speed_x, speed_y))

            self._cats_spawned_since_meow += 1
            if self._cats_spawned_since_meow >= 10:
                self._cats_spawned_since_meow = 0
                if self.audio_engine:
                    self.audio_engine.play_meow()

        self._pending_cat_spawns -= batch_size

        if self._pending_cat_spawns > 0:
            self.master.after(CAT_SPAWN_STAGGER_MS, self._process_cat_spawn_batch)
        else:
            self._is_spawning_cats = False

    def spawn_rats(self, count: int = CLICK_RAT_COUNT):
        """Spawns low-poly spinning rats at random desktop positions."""
        self._ensure_overlay()
        self._schedule_auto_dismiss()
        margin = 40
        for _ in range(count):
            x = random.randint(margin, self.screen_w - margin)
            y = random.randint(margin, self.screen_h - margin)
            frame_idx = random.randint(0, len(self.rat_frames) - 1)
            item = self.canvas.create_image(x, y, image=self.rat_frames[frame_idx], anchor="center")
            self.rats.append(SpinningRat(item, x, y, frame_idx))

        print(f"[ChaosOverlay] Spawned {count} spinning low-poly rats (total: {len(self.rats)})")
        self._start_simulation()

    def spawn_furbys(self):
        """Places 4 soul-staring Furbys in the 4 corners of the display."""
        self._ensure_overlay()
        self._schedule_auto_dismiss()
        offset = 95
        jitter_x = random.randint(-15, 15) if self.furby_items else 0
        jitter_y = random.randint(-15, 15) if self.furby_items else 0
        corners = [
            (offset + jitter_x, offset + jitter_y),                                 # Top-Left
            (self.screen_w - offset + jitter_x, offset + jitter_y),                 # Top-Right
            (offset + jitter_x, self.screen_h - offset + jitter_y),                 # Bottom-Left
            (self.screen_w - offset + jitter_x, self.screen_h - offset + jitter_y), # Bottom-Right
        ]

        for cx, cy in corners:
            item = self.canvas.create_image(cx, cy, image=self.furby_img, anchor="center")
            self.furby_items.append(item)

        print(f"[ChaosOverlay] 4 Soul-Staring Furbys spawned at screen corners (total: {len(self.furby_items)}).")
        self._start_simulation()

    def _start_simulation(self):
        if not self._is_simulating:
            self._is_simulating = True
            self._sim_loop()

    def _sim_loop(self):
        """Main physics & animation loop running at ~40 FPS (25ms)."""
        if not self._is_simulating or not self.canvas:
            return

        try:
            # 1. Update Bouncing Cats Physics
            sw = self.screen_w
            sh = self.screen_h
            cat_rad = 22

            for cat in self.cats:
                cat.x += cat.vx
                cat.y += cat.vy

                # Bounce off horizontal walls
                if cat.x <= cat_rad:
                    cat.x = cat_rad
                    cat.vx = abs(cat.vx)
                elif cat.x >= sw - cat_rad:
                    cat.x = sw - cat_rad
                    cat.vx = -abs(cat.vx)

                # Bounce off vertical walls
                if cat.y <= cat_rad:
                    cat.y = cat_rad
                    cat.vy = abs(cat.vy)
                elif cat.y >= sh - cat_rad:
                    cat.y = sh - cat_rad
                    cat.vy = -abs(cat.vy)

                self.canvas.coords(cat.item_id, cat.x, cat.y)

            # 2. Update Spinning Rats Animation (every 2 ticks = ~50ms per rotation step)
            self._rat_anim_tick += 1
            if self._rat_anim_tick % 2 == 0 and self.rat_frames:
                num_frames = len(self.rat_frames)
                for rat in self.rats:
                    rat.frame_idx = (rat.frame_idx + 1) % num_frames
                    self.canvas.itemconfig(rat.item_id, image=self.rat_frames[rat.frame_idx])

            # 3. Update Video Players Animation (every 2 ticks = ~50ms per video frame)
            if self._rat_anim_tick % 2 == 0 and self.video_players:
                for vp in self.video_players:
                    if vp.frames:
                        vp.frame_idx = (vp.frame_idx + 1) % len(vp.frames)
                        self.canvas.itemconfig(vp.img_id, image=vp.frames[vp.frame_idx])

            self.master.after(25, self._sim_loop)
        except Exception:
            pass

    def clear_all(self):
        """Cleans up all entities and destroys the canvas overlay."""
        if self._dismiss_timer_id is not None:
            try:
                self.master.after_cancel(self._dismiss_timer_id)
            except Exception:
                pass
            self._dismiss_timer_id = None

        self._is_simulating = False
        self._is_spawning_cats = False
        self._pending_cat_spawns = 0
        self.cats.clear()
        self.rats.clear()
        self.furby_items.clear()
        self.video_players.clear()
        self.video_tk_frames.clear()
        self.cat_img = None
        self.rat_frames.clear()
        self.furby_img = None

        if self.toplevel:
            try:
                self.toplevel.destroy()
            except Exception:
                pass
            self.toplevel = None
            self.canvas = None
        print("[ChaosOverlay] All chaos visual entities cleared.")



