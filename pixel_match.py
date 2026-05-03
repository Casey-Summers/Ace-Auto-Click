from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import sys
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
else:
    import pyautogui

@dataclass(frozen=True)
class PixelCondition:
    enabled: bool
    x: int
    y: int
    rgb: Tuple[int, int, int]
    tolerance: int
    mode: str  # "start_when_match", "stop_when_match", "stop_when_mismatch"


def _clamp(v: int) -> int:
    return max(0, min(255, v))


def rgb_close(a: Tuple[int, int, int], b: Tuple[int, int, int], tol: int) -> bool:
    tol = max(0, tol)
    return (
        abs(a[0] - b[0]) <= tol
        and abs(a[1] - b[1]) <= tol
        and abs(a[2] - b[2]) <= tol
    )


def get_pixel_rgb(x: int, y: int) -> Tuple[int, int, int]:
    if sys.platform == "win32":
        hdc = user32.GetDC(0)
        pixel = gdi32.GetPixel(hdc, x, y)
        user32.ReleaseDC(0, hdc)
        r = pixel & 0xFF
        g = (pixel >> 8) & 0xFF
        b = (pixel >> 16) & 0xFF
        return (r, g, b)
    else:
        r, g, b = pyautogui.pixel(x, y)
        return (_clamp(int(r)), _clamp(int(g)), _clamp(int(b)))


def should_run_clicking(cond: PixelCondition) -> bool:
    """
    Returns True if clicking should run given the condition and its mode.
    - start_when_match: only run when pixel matches
    - stop_when_match: run unless pixel matches (stop when it matches)
    - stop_when_mismatch: run unless pixel mismatches (stop when it mismatches)
    """
    if not cond.enabled:
        return True

    current = get_pixel_rgb(cond.x, cond.y)
    match = rgb_close(current, cond.rgb, cond.tolerance)

    if cond.mode == "start_when_match":
        return match
    if cond.mode == "stop_when_match":
        return not match
    if cond.mode == "stop_when_mismatch":
        return match

    # Unknown mode -> fail safe: don't run
    return False
