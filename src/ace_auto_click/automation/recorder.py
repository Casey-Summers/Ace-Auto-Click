from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pynput import keyboard, mouse


@dataclass
class RecorderState:
    recording: bool = False
    t0: float = 0.0


class ActionRecorder:
    """
    Records:
      - mouse clicks (x, y, button, pressed)
      - key press/release (key)

    Each event includes a delta time "dt" from start of recording.
    """

    def __init__(self) -> None:
        self._state = RecorderState()
        self._events: List[Dict[str, Any]] = []
        self._mouse_listener: Optional[mouse.Listener] = None
        self._key_listener: Optional[keyboard.Listener] = None

    def start(self) -> None:
        if self._state.recording:
            return
        self._state = RecorderState(recording=True, t0=time.perf_counter())
        self._events = []

        self._mouse_listener = mouse.Listener(on_click=self._on_click)
        self._key_listener = keyboard.Listener(on_press=self._on_key_press, on_release=self._on_key_release)

        self._mouse_listener.start()
        self._key_listener.start()

    def stop(self) -> List[Dict[str, Any]]:
        if not self._state.recording:
            return list(self._events)

        self._state.recording = False

        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None

        if self._key_listener:
            self._key_listener.stop()
            self._key_listener = None

        return list(self._events)

    def is_recording(self) -> bool:
        return self._state.recording

    def get_events(self) -> List[Dict[str, Any]]:
        return list(self._events)

    def _dt(self) -> float:
        return max(0.0, time.perf_counter() - self._state.t0)

    def _on_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        if not self._state.recording:
            return
        self._events.append({
            "type": "mouse_click",
            "dt": self._dt(),
            "x": int(x),
            "y": int(y),
            "button": str(button),  # e.g. 'Button.left'
            "pressed": bool(pressed),
        })

    def _key_to_str(self, key: keyboard.Key | keyboard.KeyCode) -> str:
        try:
            # KeyCode
            if hasattr(key, "char") and key.char is not None:
                return f"char:{key.char}"
        except Exception:
            pass
        # Special Key
        return f"key:{key}"

    def _on_key_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if not self._state.recording:
            return
        self._events.append({
            "type": "key_press",
            "dt": self._dt(),
            "key": self._key_to_str(key),
        })

    def _on_key_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if not self._state.recording:
            return
        self._events.append({
            "type": "key_release",
            "dt": self._dt(),
            "key": self._key_to_str(key),
        })
