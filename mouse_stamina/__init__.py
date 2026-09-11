"""
Mouse Stamina Module for Useless Project.
Coordinates cursor tracking, stamina depletion/regeneration, click-through HUD,
1-minute cursor freeze, Windows gesture blocking, and the 'ONE MOMENT OF SILENCE' overlay.
"""

from mouse_stamina.speed_controller import MouseSpeedController, attach_input_desktop
from mouse_stamina.stamina_hud import MouseStaminaHUD
from mouse_stamina.silence_overlay import SilenceOverlay
from mouse_stamina.gesture_blocker import WindowsGestureBlocker

__all__ = [
    "MouseSpeedController",
    "MouseStaminaHUD",
    "SilenceOverlay",
    "WindowsGestureBlocker",
    "attach_input_desktop",
]
