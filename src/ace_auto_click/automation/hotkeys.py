from __future__ import annotations

from collections.abc import Callable

from pynput import keyboard


SPECIAL_KEYS = {
    "alt": "<alt>",
    "ctrl": "<ctrl>",
    "control": "<ctrl>",
    "cmd": "<cmd>",
    "command": "<cmd>",
    "esc": "<esc>",
    "escape": "<esc>",
    "shift": "<shift>",
    "space": "<space>",
    "tab": "<tab>",
}


def hotkey_to_pynput(value: str) -> str:
    parts = [part.strip().lower() for part in value.split("+") if part.strip()]
    if not parts:
        raise ValueError("Hotkey cannot be empty.")

    normalized: list[str] = []
    for part in parts:
        if part in SPECIAL_KEYS:
            normalized.append(SPECIAL_KEYS[part])
        elif part.startswith("f") and part[1:].isdigit():
            normalized.append(f"<{part}>")
        elif len(part) == 1:
            normalized.append(part)
        else:
            normalized.append(f"<{part}>")
    return "+".join(normalized)


class EmergencyHotkeyManager:
    def __init__(self, on_trigger: Callable[[], None]) -> None:
        self._on_trigger = on_trigger
        self._listener: keyboard.GlobalHotKeys | None = None
        self._hotkey = ""

    def bind(self, hotkey: str) -> None:
        next_hotkey = hotkey.strip()
        if next_hotkey == self._hotkey and self._listener is not None:
            return
        self.stop()
        binding = hotkey_to_pynput(next_hotkey)
        self._listener = keyboard.GlobalHotKeys({binding: self._on_trigger})
        self._listener.start()
        self._hotkey = next_hotkey

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._hotkey = ""
