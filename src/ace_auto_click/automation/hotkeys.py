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


class RuntimeHotkeyManager:
    def __init__(self, on_emergency_stop: Callable[[], None], on_run_toggle: Callable[[], None]) -> None:
        self._on_emergency_stop = on_emergency_stop
        self._on_run_toggle = on_run_toggle
        self._listener: keyboard.GlobalHotKeys | None = None
        self._bindings: dict[str, str] = {}

    def bind(self, emergency_stop_hotkey: str, run_toggle_hotkey: str) -> None:
        emergency_binding = hotkey_to_pynput(emergency_stop_hotkey.strip())
        run_binding = hotkey_to_pynput(run_toggle_hotkey.strip())
        next_bindings = {emergency_binding: "emergency"}
        if run_binding != emergency_binding:
            next_bindings[run_binding] = "run_toggle"
        if next_bindings == self._bindings and self._listener is not None:
            return
        self.stop()
        callbacks = {}
        for binding, action in next_bindings.items():
            callbacks[binding] = self._on_emergency_stop if action == "emergency" else self._on_run_toggle
        self._listener = keyboard.GlobalHotKeys(callbacks)
        self._listener.start()
        self._bindings = next_bindings

    def set_run_toggle_handler(self, on_run_toggle: Callable[[], None]) -> None:
        self._on_run_toggle = on_run_toggle

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._bindings = {}
