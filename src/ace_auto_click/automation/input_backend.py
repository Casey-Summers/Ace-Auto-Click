from __future__ import annotations

import threading
from multiprocessing.connection import Client
from typing import Any, Protocol

from pynput import keyboard, mouse


class InputBackend(Protocol):
    mouse: Any
    keyboard: Any

    def close(self) -> None: ...


class LocalInputBackend:
    def __init__(self) -> None:
        self.mouse = mouse.Controller()
        self.keyboard = keyboard.Controller()

    def close(self) -> None:
        return None


def _wire_value(value: Any) -> Any:
    if isinstance(value, (keyboard.Key, mouse.Button)):
        return str(value)
    return value


class _BrokerConnection:
    def __init__(self, pipe_name: str, token: bytes) -> None:
        self._connection = Client(pipe_name, family="AF_PIPE", authkey=token)
        self._lock = threading.Lock()
        self._request_id = 0

    def call(self, operation: str, *args: Any) -> Any:
        with self._lock:
            self._request_id += 1
            request_id = self._request_id
            self._connection.send({"id": request_id, "op": operation, "args": [_wire_value(arg) for arg in args]})
            response = self._connection.recv()
        if response.get("id") != request_id:
            raise RuntimeError("Input broker returned an invalid response.")
        if not response.get("ok"):
            raise RuntimeError(response.get("error") or "Input broker operation failed.")
        return response.get("result")

    def close(self) -> None:
        try:
            self.call("shutdown")
        except (EOFError, OSError, RuntimeError):
            pass
        self._connection.close()


class BrokerMouseController:
    def __init__(self, connection: _BrokerConnection) -> None:
        self._connection = connection

    @property
    def position(self) -> tuple[int, int]:
        value = self._connection.call("mouse.position.get")
        return int(value[0]), int(value[1])

    @position.setter
    def position(self, value: tuple[int, int]) -> None:
        self._connection.call("mouse.position.set", int(value[0]), int(value[1]))

    def click(self, button: Any, count: int = 1) -> None:
        self._connection.call("mouse.click", button, int(count))

    def press(self, button: Any) -> None:
        self._connection.call("mouse.press", button)

    def release(self, button: Any) -> None:
        self._connection.call("mouse.release", button)


class BrokerKeyboardController:
    is_remote = True

    def __init__(self, connection: _BrokerConnection) -> None:
        self._connection = connection

    def press(self, key: Any) -> None:
        self._connection.call("keyboard.press", key)

    def release(self, key: Any) -> None:
        self._connection.call("keyboard.release", key)

    def tap(self, key: Any) -> None:
        self._connection.call("keyboard.tap", key)


class BrokerInputBackend:
    def __init__(self, pipe_name: str, token: bytes) -> None:
        self._connection = _BrokerConnection(pipe_name, token)
        self.mouse = BrokerMouseController(self._connection)
        self.keyboard = BrokerKeyboardController(self._connection)

    def bind_hotkeys(self, emergency: str, run_toggle: str) -> None:
        self._connection.call("hotkeys.bind", emergency, run_toggle)

    def runtime_info(self) -> dict[str, Any]:
        value = self._connection.call("runtime.info")
        return dict(value)

    def close(self) -> None:
        self._connection.close()
