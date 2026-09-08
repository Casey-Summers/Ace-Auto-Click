from __future__ import annotations

import ctypes
import os
from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Point:
    x: int
    y: int


@dataclass(frozen=True)
class DispatchResult:
    operation: str
    submitted: int
    inserted: int
    foreground_hwnd: int
    foreground_pid: int
    windows_error: int


class InputDispatchError(RuntimeError):
    def __init__(self, result: DispatchResult) -> None:
        self.result = result
        super().__init__(
            f"{result.operation} inserted {result.inserted}/{result.submitted} events "
            f"for foreground PID {result.foreground_pid} (HWND {result.foreground_hwnd}, "
            f"Windows error {result.windows_error})."
        )


class InputDriver(Protocol):
    @property
    def cursor_position(self) -> Point: ...
    def move(self, point: Point | tuple[int, int]) -> DispatchResult: ...
    def mouse_down(self, button: object) -> DispatchResult: ...
    def mouse_up(self, button: object) -> DispatchResult: ...
    def click(self, button: object, count: int = 1) -> DispatchResult: ...
    def key_down(self, key: object) -> DispatchResult: ...
    def key_up(self, key: object) -> DispatchResult: ...
    def tap(self, key: object) -> DispatchResult: ...
    def release_all(self) -> None: ...
    def diagnostics(self) -> dict[str, Any]: ...


if os.name == "nt":
    from ctypes import wintypes

    ULONG_PTR = ctypes.c_size_t

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class INPUT_UNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("value",)
        _fields_ = [("type", wintypes.DWORD), ("value", INPUT_UNION)]


SPECIAL_VK = {
    "backspace": 0x08, "tab": 0x09, "enter": 0x0D, "shift": 0x10, "ctrl": 0x11,
    "control": 0x11, "alt": 0x12, "esc": 0x1B, "escape": 0x1B, "space": 0x20,
    "page_up": 0x21, "page_down": 0x22, "end": 0x23, "home": 0x24, "left": 0x25,
    "up": 0x26, "right": 0x27, "down": 0x28, "delete": 0x2E,
}
OEM_VK = {"`": 0xC0, "-": 0xBD, "=": 0xBB, "[": 0xDB, "]": 0xDD,
          "\\": 0xDC, ";": 0xBA, "'": 0xDE, ",": 0xBC, ".": 0xBE, "/": 0xBF}


def canonical_key_name(value: object) -> str:
    text = str(value).strip().lower().replace("key.", "")
    return {"return": "enter", "control": "ctrl"}.get(text, text)


def virtual_key(value: object) -> int:
    name = canonical_key_name(value)
    if len(name) == 1 and name.isalpha():
        return ord(name.upper())
    if len(name) == 1 and name.isdigit():
        return ord(name)
    if name.startswith("f") and name[1:].isdigit():
        number = int(name[1:])
        if 1 <= number <= 24:
            return 0x6F + number
    if name in SPECIAL_VK:
        return SPECIAL_VK[name]
    if name in OEM_VK:
        return OEM_VK[name]
    raise ValueError(f"Unsupported key: {value}")


def canonical_button(value: object) -> str:
    text = str(value).strip().lower().replace("button.", "")
    aliases = {"btnm4": "x1", "mouse4": "x1", "btnm5": "x2", "mouse5": "x2"}
    text = aliases.get(text, text)
    if text not in {"left", "right", "middle", "x1", "x2"}:
        raise ValueError(f"Unsupported mouse button: {value}")
    return text


class Win32InputDriver:
    INPUT_MOUSE = 0
    INPUT_KEYBOARD = 1
    KEYEVENTF_EXTENDEDKEY = 0x0001
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_SCANCODE = 0x0008
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_ABSOLUTE = 0x8000
    MOUSEEVENTF_VIRTUALDESK = 0x4000
    BUTTON_FLAGS = {
        "left": (0x0002, 0x0004, 0), "right": (0x0008, 0x0010, 0),
        "middle": (0x0020, 0x0040, 0), "x1": (0x0080, 0x0100, 1), "x2": (0x0080, 0x0100, 2),
    }
    EXTENDED_KEYS = {0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2E}

    def __init__(self, user32: Any | None = None) -> None:
        if os.name != "nt":
            raise RuntimeError("Win32InputDriver is only available on Windows.")
        self._user32 = user32 or ctypes.windll.user32
        self._held_keys: set[int] = set()
        self._held_buttons: set[str] = set()
        self._last_result: DispatchResult | None = None

    @property
    def cursor_position(self) -> Point:
        point = wintypes.POINT()
        if not self._user32.GetCursorPos(ctypes.byref(point)):
            raise OSError(ctypes.get_last_error(), "GetCursorPos failed")
        return Point(point.x, point.y)

    def _foreground(self) -> tuple[int, int]:
        hwnd = int(self._user32.GetForegroundWindow() or 0)
        pid = wintypes.DWORD()
        if hwnd:
            self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return hwnd, int(pid.value)

    def _send(self, operation: str, inputs: list[INPUT]) -> DispatchResult:
        payload = (INPUT * len(inputs))(*inputs)
        ctypes.set_last_error(0)
        inserted = int(self._user32.SendInput(len(inputs), payload, ctypes.sizeof(INPUT)))
        error = int(ctypes.get_last_error())
        hwnd, pid = self._foreground()
        result = DispatchResult(operation, len(inputs), inserted, hwnd, pid, error)
        self._last_result = result
        if inserted != len(inputs):
            raise InputDispatchError(result)
        return result

    def _key_input(self, vk: int, key_up: bool = False) -> INPUT:
        scan = int(self._user32.MapVirtualKeyW(vk, 0))
        flags = self.KEYEVENTF_SCANCODE | (self.KEYEVENTF_KEYUP if key_up else 0)
        if vk in self.EXTENDED_KEYS:
            flags |= self.KEYEVENTF_EXTENDEDKEY
        return INPUT(self.INPUT_KEYBOARD, INPUT_UNION(ki=KEYBDINPUT(0, scan, flags, 0, 0)))

    def _mouse_input(self, flags: int, data: int = 0, dx: int = 0, dy: int = 0) -> INPUT:
        return INPUT(self.INPUT_MOUSE, INPUT_UNION(mi=MOUSEINPUT(dx, dy, data, flags, 0, 0)))

    def move(self, point: Point | tuple[int, int]) -> DispatchResult:
        p = point if isinstance(point, Point) else Point(int(point[0]), int(point[1]))
        left = int(self._user32.GetSystemMetrics(76)); top = int(self._user32.GetSystemMetrics(77))
        width = max(1, int(self._user32.GetSystemMetrics(78)) - 1)
        height = max(1, int(self._user32.GetSystemMetrics(79)) - 1)
        dx = round((p.x - left) * 65535 / width); dy = round((p.y - top) * 65535 / height)
        return self._send("mouse.move", [self._mouse_input(self.MOUSEEVENTF_MOVE | self.MOUSEEVENTF_ABSOLUTE | self.MOUSEEVENTF_VIRTUALDESK, dx=dx, dy=dy)])

    def mouse_down(self, button: object) -> DispatchResult:
        name = canonical_button(button); down, _up, data = self.BUTTON_FLAGS[name]
        result = self._send(f"mouse.{name}.down", [self._mouse_input(down, data)])
        self._held_buttons.add(name); return result

    def mouse_up(self, button: object) -> DispatchResult:
        name = canonical_button(button); _down, up, data = self.BUTTON_FLAGS[name]
        result = self._send(f"mouse.{name}.up", [self._mouse_input(up, data)])
        self._held_buttons.discard(name); return result

    def click(self, button: object, count: int = 1) -> DispatchResult:
        name = canonical_button(button); down, up, data = self.BUTTON_FLAGS[name]
        events = [event for _ in range(max(1, count)) for event in (self._mouse_input(down, data), self._mouse_input(up, data))]
        return self._send(f"mouse.{name}.click", events)

    def key_down(self, key: object) -> DispatchResult:
        vk = virtual_key(key); result = self._send(f"key.{canonical_key_name(key)}.down", [self._key_input(vk)])
        self._held_keys.add(vk); return result

    def key_up(self, key: object) -> DispatchResult:
        vk = virtual_key(key); result = self._send(f"key.{canonical_key_name(key)}.up", [self._key_input(vk, True)])
        self._held_keys.discard(vk); return result

    def tap(self, key: object) -> DispatchResult:
        vk = virtual_key(key)
        return self._send(f"key.{canonical_key_name(key)}.tap", [self._key_input(vk), self._key_input(vk, True)])

    def release_all(self) -> None:
        for vk in list(self._held_keys):
            try: self._send("key.release_all", [self._key_input(vk, True)])
            except InputDispatchError: pass
            self._held_keys.discard(vk)
        for name in list(self._held_buttons):
            try: self.mouse_up(name)
            except InputDispatchError: pass

    def diagnostics(self) -> dict[str, Any]:
        return {"driver": "win32-sendinput", "checked": True, "last_dispatch": asdict(self._last_result) if self._last_result else None}


def current_cursor_position() -> Point:
    if os.name != "nt":
        raise RuntimeError("Native cursor position is only implemented on Windows.")
    point = wintypes.POINT()
    if not ctypes.windll.user32.GetCursorPos(ctypes.byref(point)):
        raise OSError(ctypes.get_last_error(), "GetCursorPos failed")
    return Point(point.x, point.y)
