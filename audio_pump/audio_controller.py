"""
Windows Core Audio Controller for Audio Pump Module.
Directly communicates with Windows Core Audio APIs via ctypes COM interfaces.
"""

import threading
import ctypes
from ctypes import wintypes, Structure, c_float, c_void_p, byref, c_int, WINFUNCTYPE, HRESULT

ole32 = ctypes.windll.ole32


class GUID(Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]


def parse_guid(guid_str: str) -> GUID:
    guid = GUID()
    ole32.CLSIDFromString(ctypes.c_wchar_p(guid_str), byref(guid))
    return guid


CLSID_MMDeviceEnumerator = parse_guid("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
IID_IMMDeviceEnumerator = parse_guid("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
IID_IAudioEndpointVolume = parse_guid("{5CDF2C82-841E-4546-9722-0CF74078229A}")
IID_IAudioMeterInformation = parse_guid("{C02216F6-8C67-4B5B-9D00-D008E73E0064}")


class WindowsAudioController:
    """Controls Windows Master Volume and reads peak audio meter."""

    def __init__(self):
        ole32.CoInitialize(None)
        self.p_enumerator = c_void_p()
        self.p_device = c_void_p()
        self.p_endpoint_volume = c_void_p()
        self.p_audio_meter = c_void_p()

        self._init_com_interfaces()
        self._lock = threading.Lock()
        self._original_volume = self.get_volume()
        self._original_mute = self.get_mute()

    def _init_com_interfaces(self):
        # 1. Create MMDeviceEnumerator
        hr = ole32.CoCreateInstance(
            byref(CLSID_MMDeviceEnumerator),
            None,
            1,  # CLSCTX_INPROC_SERVER
            byref(IID_IMMDeviceEnumerator),
            byref(self.p_enumerator),
        )
        if hr != 0:
            raise RuntimeError(f"CoCreateInstance failed with hr={hr}")

        # 2. GetDefaultAudioEndpoint (eRender=0, eConsole=0)
        vtable_enum = ctypes.cast(
            ctypes.cast(self.p_enumerator, ctypes.POINTER(c_void_p)).contents,
            ctypes.POINTER(c_void_p),
        )
        get_default_endpoint = WINFUNCTYPE(
            HRESULT, c_void_p, c_int, c_int, ctypes.POINTER(c_void_p)
        )(vtable_enum[4])

        hr = get_default_endpoint(self.p_enumerator, 0, 0, byref(self.p_device))
        if hr != 0:
            raise RuntimeError(f"GetDefaultAudioEndpoint failed with hr={hr}")

        # 3. Activate IAudioEndpointVolume and IAudioMeterInformation
        vtable_dev = ctypes.cast(
            ctypes.cast(self.p_device, ctypes.POINTER(c_void_p)).contents,
            ctypes.POINTER(c_void_p),
        )
        activate = WINFUNCTYPE(
            HRESULT,
            c_void_p,
            ctypes.POINTER(GUID),
            wintypes.DWORD,
            c_void_p,
            ctypes.POINTER(c_void_p),
        )(vtable_dev[3])

        CLSCTX_ALL = 0x17
        hr = activate(
            self.p_device,
            byref(IID_IAudioEndpointVolume),
            CLSCTX_ALL,
            None,
            byref(self.p_endpoint_volume),
        )
        if hr != 0:
            raise RuntimeError(f"Activate IAudioEndpointVolume failed with hr={hr}")

        hr = activate(
            self.p_device,
            byref(IID_IAudioMeterInformation),
            CLSCTX_ALL,
            None,
            byref(self.p_audio_meter),
        )
        if hr != 0:
            raise RuntimeError(f"Activate IAudioMeterInformation failed with hr={hr}")

        # Bind Volume methods
        vtable_vol = ctypes.cast(
            ctypes.cast(self.p_endpoint_volume, ctypes.POINTER(c_void_p)).contents,
            ctypes.POINTER(c_void_p),
        )
        self._set_master_vol = WINFUNCTYPE(HRESULT, c_void_p, c_float, c_void_p)(
            vtable_vol[7]
        )
        self._get_master_vol = WINFUNCTYPE(
            HRESULT, c_void_p, ctypes.POINTER(c_float)
        )(vtable_vol[9])

        # Bind Mute methods (vtable index 14 & 15)
        self._set_mute = WINFUNCTYPE(
            HRESULT, c_void_p, wintypes.BOOL, c_void_p
        )(vtable_vol[14])
        self._get_mute = WINFUNCTYPE(
            HRESULT, c_void_p, ctypes.POINTER(wintypes.BOOL)
        )(vtable_vol[15])

        # Bind Meter methods
        vtable_meter = ctypes.cast(
            ctypes.cast(self.p_audio_meter, ctypes.POINTER(c_void_p)).contents,
            ctypes.POINTER(c_void_p),
        )
        self._get_peak_val = WINFUNCTYPE(
            HRESULT, c_void_p, ctypes.POINTER(c_float)
        )(vtable_meter[3])

    def get_volume(self) -> float:
        """Returns current master volume between 0.0 and 1.0."""
        vol = c_float()
        with self._lock:
            self._get_master_vol(self.p_endpoint_volume, byref(vol))
        return float(vol.value)

    def set_volume(self, level: float):
        """Sets master volume between 0.0 and 1.0."""
        clamped = max(0.0, min(1.0, float(level)))
        with self._lock:
            self._set_master_vol(self.p_endpoint_volume, c_float(clamped), None)

    def get_mute(self) -> bool:
        """Returns True if master volume is currently muted."""
        muted = wintypes.BOOL()
        with self._lock:
            self._get_mute(self.p_endpoint_volume, byref(muted))
        return bool(muted.value)

    def set_mute(self, is_muted: bool):
        """Sets master volume mute state."""
        with self._lock:
            self._set_mute(self.p_endpoint_volume, wintypes.BOOL(is_muted), None)

    def get_peak_value(self) -> float:
        """Returns peak audio meter value between 0.0 and 1.0."""
        peak = c_float()
        with self._lock:
            self._get_peak_val(self.p_audio_meter, byref(peak))
        return float(peak.value)

    def restore_original_volume(self):
        """Restores volume and mute state back to pre-launch state."""
        self.set_volume(self._original_volume)
        if hasattr(self, "_original_mute"):
            self.set_mute(self._original_mute)
