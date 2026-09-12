"""
Shoe Game Module for Useless Project.
Coordinates periodic 40% chance fullscreen shoe game launches:
- Virtual Mode: 2D front view shoerack, leg step-in scream, 'SAVE THE LEAF!' walking simulation,
  hurdle frequency acceleration upon player key/click mashing, and double scream collisions.
- Real Mode: Pitch-black fullscreen window with 'shoes can't think' blasted with music tracks for 10s.
"""

from shoe_game.shoe_game_manager import ShoeGameManager
from shoe_game.virtual_mode import VirtualShoeGame
from shoe_game.real_mode import RealShoeGame
from shoe_game.audio_enforcer import ShoeAudioEnforcer

__all__ = [
    "ShoeGameManager",
    "VirtualShoeGame",
    "RealShoeGame",
    "ShoeAudioEnforcer",
]
