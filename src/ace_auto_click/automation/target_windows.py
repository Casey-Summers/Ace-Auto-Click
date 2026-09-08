from __future__ import annotations

import ctypes
import os
import time
from dataclasses import dataclass
from typing import Any

from ace_auto_click.automation.input_driver import Point
from ace_auto_click.runtime.windows import process_is_elevated


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class ResolvedTarget:
    hwnd: int
    pid: int
    executable_path: str
    window_title: str
    client_rect: Rect
    foreground: bool
    elevated: bool | None


class TargetWindowError(RuntimeError): pass
class TargetMissingError(TargetWindowError): pass
class TargetFocusError(TargetWindowError): pass
class ElevationRequiredError(TargetWindowError): pass


class TargetWindowService:
    def __init__(self, user32: Any | None = None, kernel32: Any | None = None) -> None:
        if os.name != "nt": raise RuntimeError("Target windows are only supported on Windows.")
        self.user32 = user32 or ctypes.windll.user32
        self.kernel32 = kernel32 or ctypes.windll.kernel32

    def _title(self, hwnd: int) -> str:
        length = self.user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buffer, len(buffer))
        return buffer.value

    def _pid(self, hwnd: int) -> int:
        pid = ctypes.c_ulong(); self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid)); return int(pid.value)

    def _path(self, pid: int) -> str:
        handle = self.kernel32.OpenProcess(0x1000, False, pid)
        if not handle: return ""
        try:
            size = ctypes.c_ulong(32768); buffer = ctypes.create_unicode_buffer(size.value)
            return buffer.value if self.kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)) else ""
        finally: self.kernel32.CloseHandle(handle)

    def _client_rect(self, hwnd: int) -> Rect:
        class RECT(ctypes.Structure): _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        class POINT(ctypes.Structure): _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        rect = RECT(); origin = POINT(0, 0)
        if not self.user32.GetClientRect(hwnd, ctypes.byref(rect)) or not self.user32.ClientToScreen(hwnd, ctypes.byref(origin)):
            raise TargetWindowError("Could not read target client rectangle.")
        return Rect(origin.x, origin.y, rect.right - rect.left, rect.bottom - rect.top)

    def from_point(self, point: Point | tuple[int, int]) -> ResolvedTarget:
        p = point if isinstance(point, Point) else Point(*point)
        packed = (p.y << 32) | (p.x & 0xFFFFFFFF)
        hwnd = int(self.user32.WindowFromPoint(packed) or 0)
        hwnd = int(self.user32.GetAncestor(hwnd, 2) or hwnd)
        if not hwnd: raise TargetMissingError("No target window exists at that point.")
        return self.describe(hwnd)

    def describe(self, hwnd: int) -> ResolvedTarget:
        pid = self._pid(hwnd)
        return ResolvedTarget(hwnd, pid, self._path(pid), self._title(hwnd), self._client_rect(hwnd), int(self.user32.GetForegroundWindow() or 0) == hwnd, process_is_elevated(pid))

    def resolve(self, executable_path: str, window_title: str) -> ResolvedTarget:
        matches: list[ResolvedTarget] = []
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def visit(raw_hwnd: int, _lparam: int) -> bool:
            hwnd = int(raw_hwnd)
            if self.user32.IsWindowVisible(hwnd):
                pid = self._pid(hwnd); path = self._path(pid); title = self._title(hwnd)
                if ((not executable_path or path.lower() == executable_path.lower()) and
                        (not window_title or title == window_title)):
                    try: matches.append(self.describe(hwnd))
                    except TargetWindowError: pass
            return True
        self.user32.EnumWindows(callback_type(visit), 0)
        if len(matches) != 1: raise TargetMissingError(f"Expected one target window, found {len(matches)}.")
        return matches[0]

    def restore_maximize(self, hwnd: int) -> Rect:
        self.user32.ShowWindow(hwnd, 3)
        previous = None
        for _ in range(20):
            current = self._client_rect(hwnd)
            if current == previous: return current
            previous = current; time.sleep(0.05)
        return previous or self._client_rect(hwnd)

    def require_foreground(self, hwnd: int, timeout_s: float = 1.0) -> None:
        self.user32.SetForegroundWindow(hwnd)
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if int(self.user32.GetForegroundWindow() or 0) == hwnd: return
            time.sleep(0.05)
        raise TargetFocusError("The target window could not be brought to the foreground.")

    @staticmethod
    def transform(point: Point | tuple[int, int], reference: Rect, current: Rect) -> Point:
        p = point if isinstance(point, Point) else Point(*point)
        if reference.width <= 0 or reference.height <= 0: raise TargetWindowError("Invalid reference rectangle.")
        x = current.left + round((p.x - reference.left) * current.width / reference.width)
        y = current.top + round((p.y - reference.top) * current.height / reference.height)
        if not (current.left <= x < current.left + current.width and current.top <= y < current.top + current.height):
            raise TargetWindowError(f"Transformed point {x},{y} is outside the target client area.")
        return Point(x, y)

    @staticmethod
    def reverse_transform(point: Point | tuple[int, int], reference: Rect, current: Rect) -> Point:
        p = point if isinstance(point, Point) else Point(*point)
        return Point(reference.left + round((p.x - current.left) * reference.width / current.width),
                     reference.top + round((p.y - current.top) * reference.height / current.height))
