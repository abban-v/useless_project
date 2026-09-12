"""
Virtual Mode for Shoe Game Module.
Implements the 2D comic Shoe Game:
1. Scene 1: Shoe resting on shoerack (2D front view).
2. Camera slowly pans left to reveal a person's comical leg sliding into the shoe.
3. Plays scream.m4a for 3 seconds at 100% locked volume with screen shake.
4. Scene 2: Displays 'SAVE THE LEAF!' in laughable stupid font at the top.
5. 2D side-scrolling walking simulation over leaves, poop, and random road garbage.
6. The Irony: Pressing keys and clicking mouse does NOT steer the shoe; instead,
   every key press and click frantically increases hurdle frequency and velocity!
7. Hurdle contact triggers BOTH scream.m4a and scream2.m4a simultaneously for 3 seconds at 100% volume!
8. Auto-dismisses after walking phase.
"""

import math
import random
import time
import tkinter as tk
from typing import Callable, List, Optional

from config import (
    SHOE_GAME_SCREAM_SECONDS,
    SHOE_GAME_VIRTUAL_MODE_SECONDS,
)
from shoe_game.audio_enforcer import ShoeAudioEnforcer


class Hurdle:
    __slots__ = ("kind", "x", "y", "w", "h", "stepped", "canvas_items")

    def __init__(self, kind: str, x: float, y: float, w: float, h: float):
        self.kind = kind
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.stepped = False
        self.canvas_items: List[int] = []


class VirtualShoeGame(tk.Toplevel):
    """
    Fullscreen 2D comic Shoe Game window.
    """

    def __init__(
        self,
        master: tk.Tk,
        audio_ctrl=None,
        on_finish: Optional[Callable[[], None]] = None,
        duration_seconds: float = SHOE_GAME_VIRTUAL_MODE_SECONDS,
    ):
        super().__init__(master)
        self.audio_ctrl = audio_ctrl
        self.on_finish = on_finish
        self.duration_seconds = duration_seconds
        self.audio_enforcer = ShoeAudioEnforcer(self.audio_ctrl, master=master)

        self.screen_w = self.winfo_screenwidth()
        self.screen_h = self.winfo_screenheight()

        # Non-closable fullscreen
        self.geometry(f"{self.screen_w}x{self.screen_h}+0+0")
        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.configure(bg="#1a1a24")

        self.canvas = tk.Canvas(
            self,
            width=self.screen_w,
            height=self.screen_h,
            bg="#1a1a24",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.focus_set()

        self._block_closing()

        # Game State
        self.state = "INTRO_RACK"  # INTRO_RACK -> INTRO_PAN -> INTRO_SCREAM -> WALKING -> GAMEOVER
        self.camera_offset_x = 0.0
        self.leg_y = -350.0

        # Walking & Hurdle Mechanics
        self.road_y = int(self.screen_h * 0.72)
        self.shoe_x = int(self.screen_w * 0.28)
        self.shoe_y = self.road_y - 30
        self.walk_cycle = 0.0

        self.hurdles: List[Hurdle] = []
        self.hurdle_speed = 6.5
        self.hurdle_spawn_delay_ms = 1200
        self.last_spawn_time = time.time()
        self.last_double_scream_time = 0.0

        # Frantic Key/Click Irony Tracking
        self.keys_mashed = 0
        self.clicks_count = 0
        self.panic_level = 100
        self.leaves_crushed = 0
        self.poop_stepped = 0
        self.garbage_hit = 0

        # Floating comic popups
        self.popups = []  # dict of {text, x, y, life, color}

        # Select comic laughable font
        self.font_stupid = self._pick_stupid_font()

        # Bind ironical key and click inputs
        self.bind("<KeyPress>", self._on_player_key)
        self.canvas.bind("<Button-1>", self._on_player_click)

        # Start game loop
        self._is_running = True
        self._intro_start_time = time.time()
        self._walking_start_time = 0.0
        self._loop_after_id = None
        self._tick()

    def _pick_stupid_font(self) -> str:
        """Returns the most laughable available font."""
        try:
            avail = tk.font.families()
            for candidate in ("Comic Sans MS", "Jokerman", "Papyrus", "Chalkduster", "Impact"):
                if candidate in avail:
                    return candidate
        except Exception:
            pass
        return "Comic Sans MS"

    def _block_closing(self):
        """Disables closing via Alt+F4 or Escape."""
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.bind("<Escape>", lambda e: "break")
        self.bind("<Alt-F4>", lambda e: "break")

    def _on_player_key(self, event):
        """Every key press ironically INCREASES the hurdle frequency and speed!"""
        if self.state == "WALKING":
            self.keys_mashed += 1
            self.panic_level += random.randint(35, 95)
            # Irony: keys make hurdles spawn faster and rush at the shoe faster!
            self.hurdle_speed = min(32.0, self.hurdle_speed + 0.35)
            self.hurdle_spawn_delay_ms = max(180, int(self.hurdle_spawn_delay_ms * 0.94))
            self._add_comic_popup("STEERING FAILED! KEYS DO NOTHING!", self.shoe_x + random.randint(-40, 40), self.shoe_y - 90, "#FF3B30")

    def _on_player_click(self, event):
        """Every mouse click also ironically INCREASES the hurdle frequency!"""
        if self.state == "WALKING":
            self.clicks_count += 1
            self.panic_level += random.randint(40, 110)
            self.hurdle_speed = min(32.0, self.hurdle_speed + 0.40)
            self.hurdle_spawn_delay_ms = max(180, int(self.hurdle_spawn_delay_ms * 0.93))
            self._add_comic_popup("CLICKING FAILS! MORE HURDLES!", event.x, event.y, "#FF9500")

    def _add_comic_popup(self, text: str, x: float, y: float, color: str = "#FFFF00"):
        self.popups.append({
            "text": text,
            "x": x,
            "y": y,
            "life": 22,
            "color": color,
        })

    def _tick(self):
        """Main game animation & physics loop running at ~40 FPS (25ms)."""
        if not self._is_running or not self.canvas.winfo_exists():
            return

        self.canvas.delete("all")
        now = time.time()

        if self.state in ("INTRO_RACK", "INTRO_PAN", "INTRO_SCREAM"):
            self._update_intro(now)
        elif self.state == "WALKING":
            self._update_walking(now)
        elif self.state == "GAMEOVER":
            self._update_gameover(now)

        # Render floating comic popups
        surviving_popups = []
        for p in self.popups:
            p["y"] -= 1.8
            p["life"] -= 1
            if p["life"] > 0:
                self.canvas.create_text(
                    p["x"], p["y"], text=p["text"],
                    font=(self.font_stupid, 12, "bold"), fill=p["color"]
                )
                surviving_popups.append(p)
        self.popups = surviving_popups

        self._loop_after_id = self.after(25, self._tick)

    # ==========================================
    # Phase 1: Shoerack & Leg Intrusion
    # ==========================================
    def _update_intro(self, now: float):
        elapsed = now - self._intro_start_time

        # Step 1: Still on shoerack (0 to 0.8s)
        if elapsed < 0.8:
            self.state = "INTRO_RACK"
            cam_x = 0.0
        # Step 2: Camera pans left (rack shifts right) (0.8s to 2.4s)
        elif elapsed < 2.4:
            self.state = "INTRO_PAN"
            progress = (elapsed - 0.8) / 1.6
            # Smooth ease-in-out camera pan towards left (shifting world right)
            cam_x = (math.sin((progress - 0.5) * math.pi) * 0.5 + 0.5) * (self.screen_w * 0.35)
            # Leg starts descending from above left
            self.leg_y = -350.0 + (progress * 550.0)
        # Step 3: Leg lands in shoe & scream audio triggers for 3s (2.4s to 5.4s)
        elif elapsed < 5.4:
            if self.state != "INTRO_SCREAM":
                self.state = "INTRO_SCREAM"
                print("[VirtualShoeGame] Leg entered shoe! Blasting scream.m4a for 3.0s!")
                self.audio_enforcer.play_single_scream(duration=SHOE_GAME_SCREAM_SECONDS)

            cam_x = self.screen_w * 0.35
            self.leg_y = 200.0  # Leg fully inside shoe

            # Comic screen shake while screaming!
            shake_x = random.randint(-8, 8)
            shake_y = random.randint(-8, 8)
            cam_x += shake_x

            # Scream text
            self.canvas.create_text(
                self.screen_w // 2 + shake_x,
                int(self.screen_h * 0.22) + shake_y,
                text="AAAAAAAUUUUUGHHHHH!!!!!",
                font=(self.font_stupid, 42, "bold"),
                fill="#FF2222",
            )
        # Transition to Walking Phase!
        else:
            self.state = "WALKING"
            self._walking_start_time = now
            return

        self._draw_shoerack_scene(cam_x)

    def _draw_shoerack_scene(self, cam_x: float):
        """Draws the 2D wooden shoerack with our goofy shoe and the incoming foot."""
        sw = self.screen_w
        sh = self.screen_h

        # Hallway wallpaper
        self.canvas.create_rectangle(0, 0, sw, sh, fill="#2c2d30", outline="")

        # Floor boards
        floor_y = int(sh * 0.75)
        self.canvas.create_rectangle(0, floor_y, sw, sh, fill="#4a3728", outline="")
        for lx in range(0, sw, 90):
            self.canvas.create_line(lx, floor_y, lx, sh, fill="#38291e", width=2)

        # Wooden Shoerack
        rx = int(sw * 0.45) + cam_x
        ry = int(sh * 0.55)
        rw, rh = 400, 180

        # Rack frame & shelves
        self.canvas.create_rectangle(rx, ry, rx + rw, ry + rh, fill="#8d6e63", outline="#5d4037", width=5)
        self.canvas.create_rectangle(rx + 10, ry + 80, rx + rw - 10, ry + 95, fill="#6d4c41", outline="#4e342e", width=3)
        self.canvas.create_rectangle(rx + 10, ry + 160, rx + rw - 10, ry + 175, fill="#6d4c41", outline="#4e342e", width=3)

        # Our Hero Shoe sitting on top shelf
        shoe_x = rx + 80
        shoe_y = ry + 80
        self._draw_cartoon_shoe(shoe_x, shoe_y, scale=1.3)

        # Another goofy smelly shoe on bottom shelf
        self._draw_other_shoe(rx + 220, ry + 160)

        # Title hint
        self.canvas.create_text(
            sw // 2, 70,
            text="[ SCENE 1: INNOCENT SHOE ON SHOERACK ]",
            font=(self.font_stupid, 18, "bold"),
            fill="#FFAA00",
        )

        # Incoming gigantic comical leg
        if self.leg_y > -300:
            leg_x = shoe_x - 15
            # Hairy pale leg
            self.canvas.create_rectangle(leg_x - 20, self.leg_y - 250, leg_x + 25, self.leg_y, fill="#ffdbac", outline="#e0ac69", width=3)
            # Leg hairs
            for hy in range(int(self.leg_y - 230), int(self.leg_y - 30), 25):
                self.canvas.create_line(leg_x - 20, hy, leg_x - 30, hy - 8, fill="#443322", width=2)
                self.canvas.create_line(leg_x + 25, hy, leg_x + 35, hy - 8, fill="#443322", width=2)
            # Neon pink/green striped sock with toe hole
            sock_y = self.leg_y
            self.canvas.create_rectangle(leg_x - 22, sock_y - 70, leg_x + 27, sock_y, fill="#FF007F", outline="#00FFCC", width=3)
            self.canvas.create_rectangle(leg_x - 22, sock_y - 45, leg_x + 27, sock_y - 25, fill="#00FFCC", outline="")
            # Foot sliding into shoe
            self.canvas.create_oval(leg_x - 10, sock_y - 15, leg_x + 45, sock_y + 20, fill="#ffdbac", outline="#e0ac69", width=2)

    def _draw_cartoon_shoe(self, x: float, y: float, scale: float = 1.0, angle: float = 0.0):
        """Draws the ridiculously absurd cartoon sneaker."""
        w = 110 * scale
        h = 55 * scale

        # Thick white rubber sole
        self.canvas.create_rectangle(x - w // 2, y - 12 * scale, x + w // 2, y, fill="#FFFFFF", outline="#000000", width=2)
        for sx in range(int(x - w // 2 + 10 * scale), int(x + w // 2), int(12 * scale)):
            self.canvas.create_line(sx, y - 12 * scale, sx, y, fill="#CCCCCC", width=1)

        # Red/Blue Canvas Body
        body_pts = [
            (x - w // 2, y - 12 * scale),
            (x - w // 2 + 15 * scale, y - 48 * scale),
            (x - 5 * scale, y - 45 * scale),
            (x + 20 * scale, y - 25 * scale),
            (x + w // 2, y - 12 * scale),
        ]
        self.canvas.create_polygon(body_pts, fill="#0A84FF", outline="#FF3B30", width=3)

        # White toe cap
        self.canvas.create_arc(
            x + w // 2 - 35 * scale, y - 28 * scale,
            x + w // 2 + 5 * scale, y + 2 * scale,
            start=0, extent=180, fill="#FFFFFF", outline="#000000", width=2
        )

        # Goofy yellow laces and tangled bow
        self.canvas.create_line(x - 15 * scale, y - 35 * scale, x + 5 * scale, y - 25 * scale, fill="#FFD60A", width=3)
        self.canvas.create_line(x - 20 * scale, y - 28 * scale, x, y - 20 * scale, fill="#FFD60A", width=3)
        self.canvas.create_oval(x - 22 * scale, y - 46 * scale, x - 6 * scale, y - 32 * scale, outline="#FFD60A", width=3)

        # Goofy eyeball on the side
        self.canvas.create_oval(x - 10 * scale, y - 32 * scale, x + 10 * scale, y - 12 * scale, fill="#FFFFFF", outline="#000000", width=2)
        self.canvas.create_oval(x - 2 * scale, y - 26 * scale, x + 6 * scale, y - 18 * scale, fill="#000000")

    def _draw_other_shoe(self, x: float, y: float):
        """Draws an old smelly boot on the shelf."""
        self.canvas.create_rectangle(x - 45, y - 40, x - 15, y, fill="#4E6E58", outline="#2E4E38", width=2)
        self.canvas.create_rectangle(x - 45, y - 12, x + 35, y, fill="#2E4E38", outline="#1E2E18", width=2)
        # Stink lines
        self.canvas.create_text(x, y - 55, text="~ ~ ~", font=("Arial", 12, "bold"), fill="#76FF03")

    # ==========================================
    # Phase 2: "SAVE THE LEAF!" Walking Hurdles
    # ==========================================
    def _update_walking(self, now: float):
        sw = self.screen_w
        sh = self.screen_h

        # Check total walking duration
        if now - self._walking_start_time > self.duration_seconds:
            self.state = "GAMEOVER"
            return

        # 1. Draw Road and Background
        # Sky/Urban Void
        self.canvas.create_rectangle(0, 0, sw, sh, fill="#1c1c24", outline="")

        # City skyline silhouette
        for bx, bw, bh in [(50, 90, 220), (160, 120, 300), (320, 80, 180), (450, 140, 350),
                           (650, 110, 260), (820, 130, 310), (1020, 90, 200), (1200, 150, 330),
                           (1400, 110, 280), (1600, 130, 290)]:
            self.canvas.create_rectangle(bx, self.road_y - bh, bx + bw, self.road_y, fill="#282834", outline="")

        # Curbside Grass Strip
        self.canvas.create_rectangle(0, self.road_y - 20, sw, self.road_y, fill="#2e7d32", outline="")

        # Asphalt Road
        self.canvas.create_rectangle(0, self.road_y, sw, sh, fill="#37474f", outline="")
        # Road dashed line
        dash_offset = int((now * self.hurdle_speed * 15) % 80)
        for dx in range(-80 + dash_offset, sw + 80, 80):
            self.canvas.create_rectangle(dx, self.road_y + 60, dx + 45, self.road_y + 70, fill="#fdd835", outline="")

        # 2. Stupid Font Header: "SAVE THE LEAF!"
        # Shadow
        self.canvas.create_text(
            sw // 2 + 4, 54,
            text="SAVE THE LEAF!",
            font=(self.font_stupid, 48, "bold"),
            fill="#000000",
        )
        # Giant raw white text
        self.canvas.create_text(
            sw // 2, 50,
            text="SAVE THE LEAF!",
            font=(self.font_stupid, 48, "bold"),
            fill="#FFFFFF",
        )

        # Laughable instructions & ironic panic readout
        sub_text = (
            f"[ PRO-TIP: MASH KEYS TO DODGE! (DOES NOTHING) ]\n"
            f"PANIC LEVEL: {self.panic_level}% | HURDLE SPEED: {self.hurdle_speed:.1f} MPH | KEYS MASHED: {self.keys_mashed} | CLICKS: {self.clicks_count}"
        )
        self.canvas.create_text(
            sw // 2, 115,
            text=sub_text,
            font=(self.font_stupid, 14, "bold"),
            fill="#FFD60A",
            justify="center",
        )

        # Score tally
        tally = f"🍂 Leaves Crushed: {self.leaves_crushed} | 💩 Direct Poop Contacts: {self.poop_stepped} | 🥫 Garbage Kicked: {self.garbage_hit}"
        self.canvas.create_text(
            sw // 2, 160,
            text=tally,
            font=("Arial", 13, "bold"),
            fill="#30D158",
        )

        # 3. Spawning Hurdles
        if (now - self.last_spawn_time) * 1000 > self.hurdle_spawn_delay_ms:
            self.last_spawn_time = now
            self._spawn_random_hurdle()

        # 4. Animate & Step on Hurdles
        self._update_hurdles(now)

        # 5. Animate Walking Shoe and Leg
        self.walk_cycle += 0.18
        shoe_lift = max(0.0, math.sin(self.walk_cycle)) * 45.0
        cur_shoe_y = self.road_y - shoe_lift

        # Leg above shoe
        leg_top_y = cur_shoe_y - 260
        self.canvas.create_rectangle(
            self.shoe_x - 20, leg_top_y, self.shoe_x + 25, cur_shoe_y - 30,
            fill="#ffdbac", outline="#e0ac69", width=3
        )
        # Sock
        self.canvas.create_rectangle(
            self.shoe_x - 22, cur_shoe_y - 80, self.shoe_x + 27, cur_shoe_y - 25,
            fill="#FF007F", outline="#00FFCC", width=3
        )
        # Shoe
        self._draw_cartoon_shoe(self.shoe_x, cur_shoe_y, scale=1.3)

    def _spawn_random_hurdle(self):
        """Spawns a hurdle (leaf, poop, banana, can, fish bone) off-screen to the right."""
        kind = random.choices(
            ["leaf", "poop", "banana", "can", "fish"],
            weights=[40, 25, 15, 10, 10],
            k=1
        )[0]
        sw = self.screen_w
        x = sw + random.randint(20, 80)
        y = self.road_y + random.randint(-5, 15)

        if kind == "leaf":
            w, h = 40, 25
        elif kind == "poop":
            w, h = 35, 30
        elif kind == "banana":
            w, h = 38, 20
        else:
            w, h = 30, 25

        self.hurdles.append(Hurdle(kind, x, y, w, h))

    def _update_hurdles(self, now: float):
        """Moves hurdles leftward and checks for shoe step collisions."""
        active_hurdles = []

        for h in self.hurdles:
            h.x -= self.hurdle_speed

            # Collision check with shoe
            shoe_left = self.shoe_x - 55
            shoe_right = self.shoe_x + 55

            if not h.stepped and (shoe_left <= h.x <= shoe_right):
                # SHOE CONTACT OCCURRED!
                h.stepped = True
                self._handle_hurdle_contact(h, now)

            # Draw hurdle on road
            self._draw_hurdle(h)

            # Keep if still on screen
            if h.x > -100:
                active_hurdles.append(h)

        self.hurdles = active_hurdles

    def _handle_hurdle_contact(self, h: Hurdle, now: float):
        """
        Executed when the shoe touches ANY hurdle:
        Plays BOTH scream tracks (scream.m4a AND scream2.m4a) for 3 seconds at 100% volume!
        """
        # Throttle double scream slightly so overlapping doesn't overload
        if now - self.last_double_scream_time > 1.2:
            self.last_double_scream_time = now
            print(f"[VirtualShoeGame] Stepped on {h.kind.upper()}! Blasting DOUBLE SCREAM for 3.0s!")
            self.audio_enforcer.play_double_scream(duration=SHOE_GAME_SCREAM_SECONDS)

        if h.kind == "leaf":
            self.leaves_crushed += 1
            self._add_comic_popup("CRUNCH! LEAF OBLITERATED!", h.x, h.y - 40, "#FF9500")
        elif h.kind == "poop":
            self.poop_stepped += 1
            self._add_comic_popup("SQUISH! 100% DIRECT POOP CONTACT!", h.x, h.y - 45, "#795548")
        elif h.kind == "banana":
            self.garbage_hit += 1
            self._add_comic_popup("SLIP! BANANA CRUSHED!", h.x, h.y - 40, "#FFEB3B")
        else:
            self.garbage_hit += 1
            self._add_comic_popup("CLANG! GARBAGE KICKED!", h.x, h.y - 40, "#00E5FF")

    def _draw_hurdle(self, h: Hurdle):
        """Renders 2D comic hurdle items."""
        x, y = h.x, h.y

        if h.kind == "leaf":
            # Crispy golden/orange leaf
            color = "#FF9800" if not h.stepped else "#8D6E63"
            leaf_pts = [
                (x - 18, y), (x - 8, y - 14), (x + 5, y - 16),
                (x + 20, y - 4), (x + 8, y + 10), (x - 10, y + 8)
            ]
            self.canvas.create_polygon(leaf_pts, fill=color, outline="#E65100", width=2)
            self.canvas.create_line(x - 18, y, x + 20, y - 4, fill="#BF360C", width=1)
            if h.stepped:
                self.canvas.create_text(x, y - 10, text="*CRUNCH*", font=("Arial", 9, "bold"), fill="#FFD54F")

        elif h.kind == "poop":
            # Steaming brown poop coil
            fill_col = "#5D4037" if not h.stepped else "#3E2723"
            # 3-tier coil
            self.canvas.create_oval(x - 18, y - 8, x + 18, y + 10, fill=fill_col, outline="#3E2723", width=2)
            self.canvas.create_oval(x - 13, y - 18, x + 13, y - 2, fill=fill_col, outline="#3E2723", width=2)
            self.canvas.create_oval(x - 7, y - 26, x + 7, y - 14, fill=fill_col, outline="#3E2723", width=2)
            # Flies buzzing above
            fly_off = random.randint(-4, 4)
            self.canvas.create_oval(x + fly_off - 12, y - 32, x + fly_off - 9, y - 29, fill="#000000")
            self.canvas.create_oval(x - fly_off + 10, y - 34, x - fly_off + 13, y - 31, fill="#000000")
            if h.stepped:
                self.canvas.create_text(x, y - 25, text="*SQUISH*", font=("Arial", 9, "bold"), fill="#8D6E63")

        elif h.kind == "banana":
            # Yellow banana peel with 3 flared peels
            self.canvas.create_arc(x - 16, y - 16, x + 16, y + 12, start=20, extent=140, fill="#FFEB3B", outline="#F57F17", width=2)
            self.canvas.create_line(x, y, x - 15, y + 5, fill="#F57F17", width=3)
            self.canvas.create_line(x, y, x + 15, y + 5, fill="#F57F17", width=3)

        elif h.kind == "can":
            # Crushed red soda tin
            self.canvas.create_rectangle(x - 12, y - 15, x + 12, y + 5, fill="#E53935", outline="#B71C1C", width=2)
            self.canvas.create_line(x - 10, y - 5, x + 10, y - 5, fill="#FFFFFF", width=2)

        elif h.kind == "fish":
            # Fish bone
            self.canvas.create_line(x - 16, y, x + 16, y, fill="#ECEFF1", width=2)
            for fx in (x - 8, x, x + 8):
                self.canvas.create_line(fx, y - 8, fx, y + 8, fill="#ECEFF1", width=2)
            self.canvas.create_polygon([(x + 16, y), (x + 22, y - 6), (x + 22, y + 6)], fill="#ECEFF1")

    # ==========================================
    # Phase 3: Game Over & Auto-Dismiss
    # ==========================================
    def _update_gameover(self, now: float):
        sw = self.screen_w
        sh = self.screen_h

        self.canvas.create_rectangle(0, 0, sw, sh, fill="#000000", outline="")

        self.canvas.create_text(
            sw // 2, sh // 2 - 120,
            text="GAME OVER!",
            font=(self.font_stupid, 56, "bold"),
            fill="#FF3B30",
        )

        self.canvas.create_text(
            sw // 2, sh // 2 - 40,
            text="YOU FAILED TO SAVE THE LEAF.",
            font=(self.font_stupid, 34, "bold"),
            fill="#FFFFFF",
        )

        summary = (
            f"100% OF ALL LEAVES WERE CRUNCHED.\n\n"
            f"🍂 Leaves Obliterated: {self.leaves_crushed}\n"
            f"💩 Poop Directly Absorbed: {self.poop_stepped}\n"
            f"🥫 Garbage Mangled: {self.garbage_hit}\n"
            f"KEYS MASHED IN PANIC: {self.keys_mashed}\n\n"
            f"Conclusion: Shoes can't be steered. Resuming your desktop..."
        )

        self.canvas.create_text(
            sw // 2, sh // 2 + 100,
            text=summary,
            font=("Arial", 16, "bold"),
            fill="#FFD60A",
            justify="center",
        )

        if not hasattr(self, "_auto_close_scheduled"):
            self._auto_close_scheduled = True
            self.after(3500, self.dismiss)

    def dismiss(self):
        """Cleans up game, stops all audio, and closes window."""
        self._is_running = False

        if self._loop_after_id:
            try:
                self.after_cancel(self._loop_after_id)
            except Exception:
                pass
            self._loop_after_id = None

        try:
            self.audio_enforcer.stop_all_audio()
        except Exception:
            pass

        try:
            self.destroy()
        except Exception:
            pass

        if self.on_finish:
            try:
                self.on_finish()
            except Exception:
                pass
