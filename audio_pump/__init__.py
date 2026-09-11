"""
Audio Pump Module for Useless Project.
Coordinates peak audio monitoring, random volume dropping, the bicycle pump mini-game,
and hardware volume key blocking.
"""

from audio_pump.audio_controller import WindowsAudioController
from audio_pump.audio_monitor import AudioHazardMonitor
from audio_pump.pump_overlay import PumpOverlay
from audio_pump.key_blocker import VolumeKeyBlocker

__all__ = ["WindowsAudioController", "AudioHazardMonitor", "PumpOverlay", "VolumeKeyBlocker"]
