from __future__ import annotations

import secrets
import sys
import threading
import time

import pytest

from ace_auto_click.automation.input_backend import BrokerInputBackend
from ace_auto_click.automation.input_backend import BrokerKeyboardController, BrokerMouseController
from ace_auto_click.runtime import input_broker


class RecordingConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def call(self, operation: str, *args: object):
        self.calls.append((operation, args))
        if operation == "mouse.position.get":
            return [12, 34]
        return None


def test_broker_controller_preserves_mouse_controller_contract() -> None:
    connection = RecordingConnection()
    controller = BrokerMouseController(connection)  # type: ignore[arg-type]

    assert controller.position == (12, 34)
    controller.position = (50, 60)
    controller.click("Button.left", 2)

    assert connection.calls == [
        ("mouse.position.get", ()),
        ("mouse.position.set", (50, 60)),
        ("mouse.click", ("Button.left", 2)),
    ]


def test_broker_keyboard_controller_is_marked_remote() -> None:
    connection = RecordingConnection()
    controller = BrokerKeyboardController(connection)  # type: ignore[arg-type]

    controller.tap("a")

    assert controller.is_remote is True
    assert connection.calls == [("keyboard.tap", ("a",))]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows named-pipe integration")
def test_named_pipe_broker_authenticates_routes_hotkeys_and_shuts_down(monkeypatch) -> None:
    bound: list[tuple[str, str]] = []
    stopped: list[bool] = []

    class FakeHotkeys:
        def __init__(self, on_emergency_stop, on_run_toggle) -> None:
            self.on_emergency_stop = on_emergency_stop
            self.on_run_toggle = on_run_toggle

        def bind(self, emergency: str, run_toggle: str) -> None:
            bound.append((emergency, run_toggle))

        def stop(self) -> None:
            stopped.append(True)

    monkeypatch.setattr(input_broker, "RuntimeHotkeyManager", FakeHotkeys)
    token_hex = secrets.token_hex(32)
    pipe_name = rf"\\.\pipe\AceAutoClick-test-{secrets.token_hex(8)}"
    thread = threading.Thread(
        target=input_broker.run_input_broker,
        args=(pipe_name, token_hex, "http://127.0.0.1:1/unreachable"),
        daemon=True,
    )
    thread.start()

    backend = None
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            backend = BrokerInputBackend(pipe_name, bytes.fromhex(token_hex))
            break
        except (FileNotFoundError, OSError):
            time.sleep(0.05)

    assert backend is not None
    assert backend.runtime_info()["pid"] > 0
    backend.bind_hotkeys("F12", "F8")
    backend.close()
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert bound == [("F12", "F8")]
    assert stopped == [True]
