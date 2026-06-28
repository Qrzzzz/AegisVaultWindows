"""Windows material effects with safe fallback."""

from __future__ import annotations

import ctypes
import sys


def apply_windows_backdrop(hwnd: int, *, dark: bool = True) -> bool:
    """Try to enable Windows 11 Mica. Returns ``False`` when unsupported."""

    if sys.platform != "win32":
        return False
    try:
        value = ctypes.c_int(1 if dark else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        backdrop = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(backdrop), ctypes.sizeof(backdrop))
        return True
    except Exception:
        return False


