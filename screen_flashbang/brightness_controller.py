"""
Windows Display Brightness Controller for Screen Flashbang Module.
Forces display brightness to 100% across internal laptop displays (via WMI)
and external monitors (via DDC/CI dxva2.dll).
Leaves brightness permanently at 100% as requested.
"""

import subprocess
import ctypes
from ctypes import wintypes


def set_brightness_wmi(level: int = 100) -> bool:
    """Sets internal panel brightness to 100% via Windows WMI."""
    try:
        import win32com.client
        wmi = win32com.client.GetObject("winmgmts:\\\\.\\root\\wmi")
        methods = wmi.InstancesOf("WmiMonitorBrightnessMethods")
        for m in methods:
            in_param = m.Methods_("WmiSetBrightness").inParameters.SpawnInstance_()
            in_param.Properties_("Timeout").Value = 1
            in_param.Properties_("Brightness").Value = int(level)
            m.ExecMethod_("WmiSetBrightness", in_param)
        return True
    except Exception:
        # Fallback to PowerShell WMI invocation
        try:
            cmd = f'(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})'
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                creationflags=0x08000000,  # CREATE_NO_WINDOW
                timeout=3,
            )
            return True
        except Exception:
            return False


def set_brightness_dxva2(level: int = 100):
    """Sets external monitor brightness via DDC/CI dxva2.dll."""
    try:
        user32 = ctypes.windll.user32
        dxva2 = ctypes.windll.dxva2

        class PHYSICAL_MONITOR(ctypes.Structure):
            _fields_ = [
                ("hPhysicalMonitor", wintypes.HANDLE),
                ("szPhysicalMonitorDescription", wintypes.WCHAR * 128),
            ]

        def monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
            num_monitors = wintypes.DWORD()
            if dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(hMonitor, ctypes.byref(num_monitors)):
                if num_monitors.value > 0:
                    monitors = (PHYSICAL_MONITOR * num_monitors.value)()
                    if dxva2.GetPhysicalMonitorsFromHMONITOR(hMonitor, num_monitors.value, monitors):
                        for mon in monitors:
                            dxva2.SetMonitorBrightness(mon.hPhysicalMonitor, int(level))
                            dxva2.DestroyPhysicalMonitor(mon.hPhysicalMonitor)
            return True

        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HMONITOR,
            wintypes.HDC,
            ctypes.POINTER(wintypes.RECT),
            wintypes.LPARAM,
        )
        user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.c_void_p, MONITORENUMPROC, wintypes.LPARAM]
        user32.EnumDisplayMonitors.restype = wintypes.BOOL

        dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR.argtypes = [wintypes.HMONITOR, ctypes.POINTER(wintypes.DWORD)]
        dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR.restype = wintypes.BOOL

        dxva2.GetPhysicalMonitorsFromHMONITOR.argtypes = [wintypes.HMONITOR, wintypes.DWORD, ctypes.c_void_p]
        dxva2.GetPhysicalMonitorsFromHMONITOR.restype = wintypes.BOOL

        dxva2.SetMonitorBrightness.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        dxva2.SetMonitorBrightness.restype = wintypes.BOOL

        dxva2.DestroyPhysicalMonitor.argtypes = [wintypes.HANDLE]
        dxva2.DestroyPhysicalMonitor.restype = wintypes.BOOL

        user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(monitor_enum_proc), 0)
    except Exception:
        pass


def force_maximum_brightness():
    """Forces all connected displays to 100% brightness and keeps it there."""
    print("[BrightnessController] Blasting display brightness to 100%!")
    set_brightness_wmi(100)
    set_brightness_dxva2(100)
