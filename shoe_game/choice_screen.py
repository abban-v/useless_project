"""
Choice Screen for Shoe Game Module.
Displays a fullscreen, non-closable selection interface with heading "SHOE GAME".
Allows player to choose between:
- Virtual Mode: 'SAVE THE LEAF!' 2D side-scrolling comic hurdle journey
- Real Mode: 'shoes can't think' 10-second audio blast in the void
No exit button is provided; the player must pick a mode to proceed.
"""

import tkinter as tk
from typing import Callable, Optional


class ShoeGameChoiceScreen(tk.Toplevel):
    """
    Fullscreen selection screen displaying 'SHOE GAME' heading and choices
    for Virtual Mode and Real Mode.
    """

    def __init__(
        self,
        master: tk.Tk,
        on_select_mode: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(master)
        self.master = master
        self.on_select_mode = on_select_mode

        self.screen_w = self.winfo_screenwidth()
        self.screen_h = self.winfo_screenheight()

        # Non-closable fullscreen
        self.geometry(f"{self.screen_w}x{self.screen_h}+0+0")
        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.configure(bg="#11111a")

        self.canvas = tk.Canvas(
            self,
            width=self.screen_w,
            height=self.screen_h,
            bg="#11111a",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.focus_set()

        self._font_title = self._pick_font(["Comic Sans MS", "Jokerman", "Impact", "Arial"])
        self._font_body = self._pick_font(["Comic Sans MS", "Arial"])

        self._card_rects = {}
        self._selected = False

        self._block_closing()
        self._bind_keys()
        self._render()

    def _pick_font(self, candidates):
        try:
            avail = tk.font.families()
            for c in candidates:
                if c in avail:
                    return c
        except Exception:
            pass
        return "Arial"

    def _block_closing(self):
        """Disables standard window closing shortcuts."""
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.bind("<Escape>", lambda e: "break")
        self.bind("<Alt-F4>", lambda e: "break")
        self.canvas.bind("<Escape>", lambda e: "break")
        self.canvas.bind("<Alt-F4>", lambda e: "break")

    def _bind_keys(self):
        """Keyboard shortcuts: 1/V for Virtual, 2/R for Real."""
        for k in ("1", "v", "V"):
            self.bind(f"<{k}>", lambda e: self._choose("virtual"))
            self.canvas.bind(f"<{k}>", lambda e: self._choose("virtual"))
        for k in ("2", "r", "R"):
            self.bind(f"<{k}>", lambda e: self._choose("real"))
            self.canvas.bind(f"<{k}>", lambda e: self._choose("real"))

        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_motion)

    def _render(self, hover_mode: Optional[str] = None):
        self.canvas.delete("all")
        sw = self.screen_w
        sh = self.screen_h
        cx = sw // 2

        # 1. Background grid accent
        grid_step = 60
        for x in range(0, sw, grid_step):
            self.canvas.create_line(x, 0, x, sh, fill="#181826", width=1)
        for y in range(0, sh, grid_step):
            self.canvas.create_line(0, y, sw, y, fill="#181826", width=1)

        # 2. Main Title: "SHOE GAME"
        title_y = int(sh * 0.16)
        # Drop shadow for cartoon punch
        self.canvas.create_text(
            cx + 6, title_y + 6,
            text="SHOE GAME",
            font=(self._font_title, 64, "bold"),
            fill="#05050a",
        )
        self.canvas.create_text(
            cx, title_y,
            text="SHOE GAME",
            font=(self._font_title, 64, "bold"),
            fill="#FFD60A",
        )

        # 3. Comic Tagline
        self.canvas.create_text(
            cx, title_y + 68,
            text="CHOOSE YOUR FOOTWEAR DESTINY",
            font=(self._font_body, 18, "bold"),
            fill="#00E5FF",
        )

        # 4. Mode Cards
        card_w = min(420, int(sw * 0.38))
        card_h = min(360, int(sh * 0.52))
        gap = 40
        card_y1 = int(sh * 0.34)
        card_y2 = card_y1 + card_h

        # Left Card: Virtual Mode
        c1_x1 = cx - card_w - gap // 2
        c1_x2 = cx - gap // 2
        self._card_rects["virtual"] = (c1_x1, card_y1, c1_x2, card_y2)

        # Right Card: Real Mode
        c2_x1 = cx + gap // 2
        c2_x2 = cx + card_w + gap // 2
        self._card_rects["real"] = (c2_x1, card_y1, c2_x2, card_y2)

        self._draw_card(
            mode="virtual",
            rect=self._card_rects["virtual"],
            title="[1] VIRTUAL MODE",
            subtitle="SAVE THE LEAF!",
            desc="2D comic shoerack pan, leg intrusion, and\nfrantic walking road hurdles.\nMash keys to 'control' the shoe\n(it actually accelerates the garbage).\nDouble screams on hurdle collision!",
            accent_color="#FF3366",
            is_hover=(hover_mode == "virtual"),
        )

        self._draw_card(
            mode="real",
            rect=self._card_rects["real"],
            title="[2] REAL MODE",
            subtitle="shoes can't think",
            desc="10 seconds of pitch-black void.\nNo obstacles. No steering.\nJust raw philosophical truth and\nALL audio tracks blasted simultaneously\nat 100% locked volume.",
            accent_color="#7C4DFF",
            is_hover=(hover_mode == "real"),
        )

        # 5. Bottom Instructions (No exit button! Must pick mode)
        self.canvas.create_text(
            cx, sh - 60,
            text="Press [1] or [V] for Virtual Mode   *   Press [2] or [R] for Real Mode   *   Click any card to begin",
            font=(self._font_body, 15, "bold"),
            fill="#8888AA",
        )

    def _draw_card(self, mode: str, rect: tuple, title: str, subtitle: str, desc: str, accent_color: str, is_hover: bool):
        x1, y1, x2, y2 = rect
        cx = (x1 + x2) // 2

        bg_color = "#242436" if is_hover else "#1b1b28"
        border_color = accent_color if is_hover else "#33334d"
        border_width = 4 if is_hover else 2

        # Card shadow
        self.canvas.create_rectangle(x1 + 6, y1 + 6, x2 + 6, y2 + 6, fill="#080810", outline="")

        # Card background
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=bg_color, outline=border_color, width=border_width)

        # Header bar
        bar_h = 56
        self.canvas.create_rectangle(x1, y1, x2, y1 + bar_h, fill=accent_color, outline="")

        # Card Title
        self.canvas.create_text(
            cx, y1 + bar_h // 2,
            text=title,
            font=(self._font_body, 18, "bold"),
            fill="#FFFFFF",
        )

        # Card Subtitle
        self.canvas.create_text(
            cx, y1 + bar_h + 35,
            text=f'"{subtitle}"',
            font=(self._font_body, 18, "bold"),
            fill="#FFD60A",
        )

        # Card Description
        self.canvas.create_text(
            cx, y1 + bar_h + 135,
            text=desc,
            font=("Arial", 12),
            fill="#DDDDFF",
            justify="center",
        )

        # Action Button at bottom of card
        btn_w = 160
        btn_h = 42
        btn_y = y2 - 40
        btn_x1 = cx - btn_w // 2
        btn_y1 = btn_y - btn_h // 2
        btn_x2 = cx + btn_w // 2
        btn_y2 = btn_y + btn_h // 2

        btn_bg = accent_color if is_hover else "#2c2c42"
        btn_fg = "#FFFFFF"

        self.canvas.create_rectangle(btn_x1, btn_y1, btn_x2, btn_y2, fill=btn_bg, outline=accent_color, width=2)
        self.canvas.create_text(
            cx, btn_y,
            text="SELECT MODE",
            font=(self._font_body, 13, "bold"),
            fill=btn_fg,
        )

    def _get_mode_at_pos(self, x: int, y: int) -> Optional[str]:
        for mode, (x1, y1, x2, y2) in self._card_rects.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                return mode
        return None

    def _on_motion(self, event):
        mode = self._get_mode_at_pos(event.x, event.y)
        if mode != getattr(self, "_cur_hover", None):
            self._cur_hover = mode
            self._render(hover_mode=mode)

    def _on_click(self, event):
        mode = self._get_mode_at_pos(event.x, event.y)
        if mode:
            self._choose(mode)

    def _choose(self, mode: str):
        if self._selected:
            return
        self._selected = True
        print(f"[ShoeGameChoice] Player selected: [{mode.upper()} MODE]!")

        callback = self.on_select_mode

        try:
            self.destroy()
        except Exception:
            pass

        if callback:
            try:
                callback(mode)
            except Exception as err:
                print(f"[ShoeGameChoice] Callback error: {err}")
