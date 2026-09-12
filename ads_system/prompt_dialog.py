"""
Ad Prompt Dialog for Fullscreen Ad System.
Displays a modal prompt asking "Should you disable ads?" with Yes and No buttons:
- Clicking "No" calls on_no_callback() (returns to normal operation).
- Clicking "Yes" calls on_yes_callback() (triggers countdown -> explosion -> next ad sequence).
"""

import tkinter as tk
from typing import Optional, Callable


class AdPromptDialog(tk.Toplevel):
    """
    Modal question dialog centered on screen asking 'Should you disable ads?'.
    """

    def __init__(
        self,
        master: tk.Tk,
        on_yes: Optional[Callable] = None,
        on_no: Optional[Callable] = None,
    ):
        super().__init__(master)
        self.on_yes_callback = on_yes
        self.on_no_callback = on_no

        self.title("Ad Preferences")
        self.configure(bg="#1c1c24")
        self.resizable(False, False)

        # Center the dialog on screen
        dialog_w = 420
        dialog_h = 220
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        pos_x = (screen_w - dialog_w) // 2
        pos_y = (screen_h - dialog_h) // 2
        self.geometry(f"{dialog_w}x{dialog_h}+{pos_x}+{pos_y}")

        # Topmost & modal protocols
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._on_no_click)  # Closing window defaults to No

        # Container frame
        container = tk.Frame(self, bg="#1c1c24", padx=25, pady=20)
        container.pack(fill="both", expand=True)

        # Icon / Badge label
        badge = tk.Label(
            container,
            text="[!] SPONSORED AD FINISHED",
            font=("Consolas", 10, "bold"),
            fg="#FFA500",
            bg="#1c1c24",
        )
        badge.pack(pady=(0, 10))

        # Main Question
        question_label = tk.Label(
            container,
            text="Should you disable ads?",
            font=("Comic Sans MS", 16, "bold"),
            fg="#FFFFFF",
            bg="#1c1c24",
        )
        question_label.pack(pady=(0, 20))

        # Buttons frame
        btn_frame = tk.Frame(container, bg="#1c1c24")
        btn_frame.pack(fill="x", pady=(5, 0))

        # "Yes" button (Trap!)
        self.btn_yes = tk.Button(
            btn_frame,
            text="YES (Disable)",
            font=("Arial", 11, "bold"),
            bg="#2e7d32",
            fg="#FFFFFF",
            activebackground="#388e3c",
            activeforeground="#FFFFFF",
            width=14,
            height=2,
            relief="raised",
            bd=3,
            cursor="hand2",
            command=self._on_yes_click,
        )
        self.btn_yes.pack(side="left", padx=(15, 10), expand=True)

        # "No" button (Safe)
        self.btn_no = tk.Button(
            btn_frame,
            text="NO (Keep Ads)",
            font=("Arial", 11, "bold"),
            bg="#c62828",
            fg="#FFFFFF",
            activebackground="#d32f2f",
            activeforeground="#FFFFFF",
            width=14,
            height=2,
            relief="raised",
            bd=3,
            cursor="hand2",
            command=self._on_no_click,
        )
        self.btn_no.pack(side="right", padx=(10, 15), expand=True)

        # Key bindings
        self.bind("<y>", lambda e: self._on_yes_click())
        self.bind("<Y>", lambda e: self._on_yes_click())
        self.bind("<n>", lambda e: self._on_no_click())
        self.bind("<N>", lambda e: self._on_no_click())

        self.lift()
        self.focus_force()

    def _on_yes_click(self):
        print("[AdPromptDialog] User clicked YES to disable ads!")
        try:
            self.destroy()
        except Exception:
            pass
        if self.on_yes_callback:
            self.on_yes_callback()

    def _on_no_click(self):
        print("[AdPromptDialog] User clicked NO to disable ads.")
        try:
            self.destroy()
        except Exception:
            pass
        if self.on_no_callback:
            self.on_no_callback()
