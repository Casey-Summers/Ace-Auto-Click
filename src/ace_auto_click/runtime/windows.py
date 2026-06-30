from __future__ import annotations

import ctypes
import os
import sys


_dpi_mode = "not-applicable"


def configure_process_dpi_awareness() -> str:
    """Select physical, per-monitor coordinates before input libraries load."""
    global _dpi_mode
    if sys.platform != "win32":
        return _dpi_mode
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            _dpi_mode = "per-monitor-v2"
            return _dpi_mode
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        _dpi_mode = "per-monitor"
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
            _dpi_mode = "system-aware"
        except (AttributeError, OSError):
            _dpi_mode = "unavailable"
    return _dpi_mode


def dpi_awareness_mode() -> str:
    return _dpi_mode


def is_process_elevated() -> bool:
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def process_identity() -> dict[str, object]:
    return {
        "pid": os.getpid(),
        "elevated": is_process_elevated(),
        "dpi_awareness": dpi_awareness_mode(),
    }
