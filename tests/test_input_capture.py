from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ace_auto_click.api import routes
from ace_auto_click.api.app import app
from ace_auto_click.automation import input_capture


class FakeButton:
    left = "Button.left"


def test_capture_next_mouse_click_records_press_and_cleans_up(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[object] = []
    monkeypatch.setattr(input_capture, "_is_windows_polling_available", lambda: False)

    class FakeMouseListener:
        def __init__(self, on_click):
            self.on_click = on_click
            self.stopped = False
            self.joined = False
            created.append(self)

        def start(self) -> None:
            self.on_click(101, 202, FakeButton.left, True)

        def stop(self) -> None:
            self.stopped = True

        def join(self, timeout=None) -> None:
            self.joined = True

    class FakeKeyListener:
        def __init__(self, on_press):
            self.on_press = on_press
            self.stopped = False
            self.joined = False
            created.append(self)

        def start(self) -> None:
            return None

        def stop(self) -> None:
            self.stopped = True

        def join(self, timeout=None) -> None:
            self.joined = True

    monkeypatch.setattr(input_capture.mouse, "Listener", FakeMouseListener)
    monkeypatch.setattr(input_capture.keyboard, "Listener", FakeKeyListener)

    captured = input_capture.capture_next_mouse_click(timeout_s=0.1, cancel_keys={"esc"})

    assert captured.kind == "mouse_click"
    assert captured.x == 101
    assert captured.y == 202
    assert all(getattr(listener, "stopped") for listener in created)
    assert all(getattr(listener, "joined") for listener in created)


def test_capture_next_mouse_click_can_be_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(input_capture, "_is_windows_polling_available", lambda: False)

    class FakeMouseListener:
        def __init__(self, on_click):
            self.on_click = on_click

        def start(self) -> None:
            return None

        def stop(self) -> None:
            return None

        def join(self, timeout=None) -> None:
            return None

    class FakeKeyListener:
        def __init__(self, on_press):
            self.on_press = on_press

        def start(self) -> None:
            self.on_press(input_capture.keyboard.Key.esc)

        def stop(self) -> None:
            return None

        def join(self, timeout=None) -> None:
            return None

    monkeypatch.setattr(input_capture.mouse, "Listener", FakeMouseListener)
    monkeypatch.setattr(input_capture.keyboard, "Listener", FakeKeyListener)

    with pytest.raises(input_capture.InputCaptureCancelledError):
        input_capture.capture_next_mouse_click(timeout_s=0.1, cancel_keys={"esc"})


def test_capture_next_mouse_click_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(input_capture, "_is_windows_polling_available", lambda: False)

    class FakeListener:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def start(self) -> None:
            return None

        def stop(self) -> None:
            return None

        def join(self, timeout=None) -> None:
            return None

    monkeypatch.setattr(input_capture.mouse, "Listener", FakeListener)
    monkeypatch.setattr(input_capture.keyboard, "Listener", FakeListener)

    with pytest.raises(input_capture.InputCaptureTimeoutError):
        input_capture.capture_next_mouse_click(timeout_s=0.01)


def test_windows_polling_capture_records_click_transition(monkeypatch: pytest.MonkeyPatch) -> None:
    states = {
        input_capture.VK_LBUTTON: [0, 0x8000],
        input_capture.VK_RBUTTON: [0, 0],
        input_capture.VK_MBUTTON: [0, 0],
        input_capture.VK_ESCAPE: [0, 0],
    }

    def fake_key_state(vk_code: int) -> int:
        values = states[vk_code]
        return values.pop(0) if len(values) > 1 else values[0]

    monkeypatch.setattr(input_capture, "_get_async_key_state", fake_key_state)
    monkeypatch.setattr(input_capture.pyautogui, "position", lambda: (321, 654))

    captured = input_capture._poll_windows_mouse_click(timeout_s=0.5, cancel_keys={"esc"})

    assert captured.x == 321
    assert captured.y == 654
    assert captured.button == "Button.left"


def test_next_click_route_returns_captured_position(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_capture_next_mouse_click(timeout_s: float, cancel_keys: set[str]):
        return input_capture.CapturedInput(kind="mouse_click", x=12, y=34)

    monkeypatch.setattr(routes.input_capture, "capture_next_mouse_click", fake_capture_next_mouse_click)

    response = TestClient(app).post("/mouse-position/next-click")

    assert response.status_code == 200
    assert response.json() == {"x": 12, "y": 34}


def test_next_click_route_maps_timeout_and_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout_capture(timeout_s: float, cancel_keys: set[str]):
        raise input_capture.InputCaptureTimeoutError("Timed out waiting for click location.")

    monkeypatch.setattr(routes.input_capture, "capture_next_mouse_click", timeout_capture)
    response = TestClient(app).post("/mouse-position/next-click")
    assert response.status_code == 408

    def cancel_capture(timeout_s: float, cancel_keys: set[str]):
        raise input_capture.InputCaptureCancelledError("Input capture cancelled.")

    monkeypatch.setattr(routes.input_capture, "capture_next_mouse_click", cancel_capture)
    response = TestClient(app).post("/mouse-position/next-click")
    assert response.status_code == 409
