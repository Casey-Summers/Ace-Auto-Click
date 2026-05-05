from __future__ import annotations

import threading
import time
import uuid
import os
import ctypes
from dataclasses import dataclass

import pyautogui
from pynput import keyboard, mouse


class InputCaptureTimeoutError(TimeoutError):
    """Raised when no matching global input arrives before the timeout."""


class InputCaptureCancelledError(RuntimeError):
    """Raised when a global input capture is cancelled by a configured key."""


@dataclass(frozen=True)
class CapturedInput:
    kind: str
    x: int | None = None
    y: int | None = None
    button: str | None = None
    key: str | None = None
    cancelled: bool = False


VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_MBUTTON = 0x04
VK_ESCAPE = 0x1B


def _get_async_key_state(vk_code: int) -> int:
    return ctypes.windll.user32.GetAsyncKeyState(vk_code)


def _is_windows_polling_available() -> bool:
    return os.name == "nt" and hasattr(ctypes, "windll") and hasattr(ctypes.windll, "user32")


def _button_down(vk_code: int) -> bool:
    return bool(_get_async_key_state(vk_code) & 0x8000)


def _windows_cancel_requested(cancel_keys: set[str] | None) -> bool:
    if not cancel_keys:
        return False
    normalized = {value.lower().removeprefix("key.") for value in cancel_keys}
    return "esc" in normalized and _button_down(VK_ESCAPE)


def _poll_windows_mouse_click(
    timeout_s: float,
    cancel_keys: set[str] | None = None,
    stop_event: threading.Event | None = None,
) -> CapturedInput:
    started_at = time.monotonic()
    buttons = (
        (VK_LBUTTON, "Button.left"),
        (VK_RBUTTON, "Button.right"),
        (VK_MBUTTON, "Button.middle"),
    )
    was_down = {vk_code: _button_down(vk_code) for vk_code, _name in buttons}

    while True:
        if stop_event is not None and stop_event.is_set():
            raise InputCaptureCancelledError("Input capture cancelled.")
        if _windows_cancel_requested(cancel_keys):
            raise InputCaptureCancelledError("Input capture cancelled.")
        if time.monotonic() - started_at >= timeout_s:
            raise InputCaptureTimeoutError("Timed out waiting for click location.")

        for vk_code, button_name in buttons:
            down = _button_down(vk_code)
            if down and not was_down[vk_code]:
                x, y = pyautogui.position()
                return CapturedInput(kind="mouse_click", x=int(x), y=int(y), button=button_name)
            was_down[vk_code] = down

        time.sleep(0.01)


@dataclass(frozen=True)
class CaptureSessionSnapshot:
    id: str
    status: str
    result: CapturedInput | None = None
    error: str | None = None


def _key_variants(key: keyboard.Key | keyboard.KeyCode) -> set[str]:
    values = {str(key).lower()}
    name = getattr(key, "name", None)
    if name:
        values.add(str(name).lower())
    char = getattr(key, "char", None)
    if char:
        values.add(str(char).lower())
    if str(key).lower().startswith("key."):
        values.add(str(key).lower().removeprefix("key."))
    return values


def _is_cancel_key(key: keyboard.Key | keyboard.KeyCode, cancel_keys: set[str] | None) -> bool:
    if not cancel_keys:
        return False
    normalized = {value.lower().removeprefix("key.") for value in cancel_keys}
    return bool(_key_variants(key) & normalized)


def _stop_listener(listener: object | None) -> None:
    if listener is None:
        return
    stop = getattr(listener, "stop", None)
    if callable(stop):
        stop()
    join = getattr(listener, "join", None)
    if callable(join):
        try:
            if getattr(listener, "ident", None) != threading.current_thread().ident:
                join(timeout=1)
        except RuntimeError:
            pass


def capture_next_mouse_click(timeout_s: float = 30, cancel_keys: set[str] | None = None) -> CapturedInput:
    if _is_windows_polling_available():
        return _poll_windows_mouse_click(timeout_s=timeout_s, cancel_keys=cancel_keys)

    ready = threading.Event()
    lock = threading.Lock()
    result: CapturedInput | None = None

    def store(next_result: CapturedInput) -> None:
        nonlocal result
        with lock:
            if result is None:
                result = next_result
                ready.set()

    def on_click(x: int, y: int, button: mouse.Button, pressed: bool) -> bool | None:
        if pressed:
            store(CapturedInput(kind="mouse_click", x=int(x), y=int(y), button=str(button)))
            return False
        return None

    def on_press(key: keyboard.Key | keyboard.KeyCode) -> bool | None:
        if _is_cancel_key(key, cancel_keys):
            store(CapturedInput(kind="key_press", key=str(key), cancelled=True))
            return False
        return None

    mouse_listener: mouse.Listener | None = None
    key_listener: keyboard.Listener | None = None
    try:
        mouse_listener = mouse.Listener(on_click=on_click)
        key_listener = keyboard.Listener(on_press=on_press)
        mouse_listener.start()
        key_listener.start()
        if not ready.wait(timeout=timeout_s):
            raise InputCaptureTimeoutError("Timed out waiting for click location.")
        with lock:
            captured = result
        if captured is None:
            raise InputCaptureTimeoutError("Timed out waiting for click location.")
        if captured.cancelled:
            raise InputCaptureCancelledError("Input capture cancelled.")
        return captured
    finally:
        _stop_listener(mouse_listener)
        _stop_listener(key_listener)


def capture_next_key_press(timeout_s: float = 30, cancel_keys: set[str] | None = None) -> CapturedInput:
    ready = threading.Event()
    lock = threading.Lock()
    result: CapturedInput | None = None

    def store(next_result: CapturedInput) -> None:
        nonlocal result
        with lock:
            if result is None:
                result = next_result
                ready.set()

    def on_press(key: keyboard.Key | keyboard.KeyCode) -> bool | None:
        captured = CapturedInput(kind="key_press", key=str(key), cancelled=_is_cancel_key(key, cancel_keys))
        store(captured)
        return False

    listener: keyboard.Listener | None = None
    try:
        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        if not ready.wait(timeout=timeout_s):
            raise InputCaptureTimeoutError("Timed out waiting for key press.")
        with lock:
            captured = result
        if captured is None:
            raise InputCaptureTimeoutError("Timed out waiting for key press.")
        if captured.cancelled:
            raise InputCaptureCancelledError("Input capture cancelled.")
        return captured
    finally:
        _stop_listener(listener)


class InputCaptureSession:
    def __init__(self, session_id: str, timeout_s: float, cancel_keys: set[str] | None = None) -> None:
        self.id = session_id
        self._timeout_s = timeout_s
        self._cancel_keys = cancel_keys
        self._started_at = time.monotonic()
        self._lock = threading.Lock()
        self._status = "pending"
        self._result: CapturedInput | None = None
        self._error: str | None = None
        self._mouse_listener: mouse.Listener | None = None
        self._key_listener: keyboard.Listener | None = None
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None

    def start_mouse_click(self) -> None:
        if _is_windows_polling_available():
            self._worker = threading.Thread(target=self._run_windows_mouse_poll, name=f"input-capture-{self.id}", daemon=True)
            self._worker.start()
            return

        def on_click(x: int, y: int, button: mouse.Button, pressed: bool) -> bool | None:
            if pressed:
                self.complete(CapturedInput(kind="mouse_click", x=int(x), y=int(y), button=str(button)))
                return False
            return None

        def on_press(key: keyboard.Key | keyboard.KeyCode) -> bool | None:
            if _is_cancel_key(key, self._cancel_keys):
                self.cancel("Input capture cancelled.")
                return False
            return None

        self._mouse_listener = mouse.Listener(on_click=on_click)
        self._key_listener = keyboard.Listener(on_press=on_press)
        self._mouse_listener.start()
        self._key_listener.start()

    def _run_windows_mouse_poll(self) -> None:
        try:
            self.complete(_poll_windows_mouse_click(self._timeout_s, self._cancel_keys, self._stop_event))
        except InputCaptureCancelledError as exc:
            self.cancel(str(exc))
        except InputCaptureTimeoutError as exc:
            self.fail(str(exc))
        except Exception as exc:
            self.fail(str(exc))

    def complete(self, result: CapturedInput) -> None:
        should_stop = False
        with self._lock:
            if self._status == "pending":
                self._status = "complete"
                self._result = result
                should_stop = True
        if should_stop:
            self.stop()

    def fail(self, message: str) -> None:
        should_stop = False
        with self._lock:
            if self._status == "pending":
                self._status = "failed"
                self._error = message
                should_stop = True
        if should_stop:
            self.stop()

    def cancel(self, message: str = "Input capture cancelled.") -> None:
        should_stop = False
        with self._lock:
            if self._status == "pending":
                self._status = "cancelled"
                self._error = message
                should_stop = True
        if should_stop:
            self.stop()

    def refresh_timeout(self) -> None:
        with self._lock:
            pending = self._status == "pending"
        if pending and time.monotonic() - self._started_at >= self._timeout_s:
            self.fail("Timed out waiting for click location.")

    def snapshot(self) -> CaptureSessionSnapshot:
        self.refresh_timeout()
        with self._lock:
            return CaptureSessionSnapshot(
                id=self.id,
                status=self._status,
                result=self._result,
                error=self._error,
            )

    def stop(self) -> None:
        self._stop_event.set()
        mouse_listener = self._mouse_listener
        key_listener = self._key_listener
        worker = self._worker
        self._mouse_listener = None
        self._key_listener = None
        self._worker = None
        _stop_listener(mouse_listener)
        _stop_listener(key_listener)
        if worker is not None and worker.ident != threading.current_thread().ident:
            worker.join(timeout=1)


class InputCaptureManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, InputCaptureSession] = {}

    def start_mouse_click(self, timeout_s: float = 30, cancel_keys: set[str] | None = None) -> CaptureSessionSnapshot:
        self.cancel_pending("Starting a new capture session.")
        session = InputCaptureSession(str(uuid.uuid4()), timeout_s, cancel_keys)
        with self._lock:
            self._sessions[session.id] = session
        try:
            session.start_mouse_click()
        except Exception as exc:
            session.fail(str(exc))
        return session.snapshot()

    def get(self, session_id: str) -> CaptureSessionSnapshot | None:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            return None
        snapshot = session.snapshot()
        if snapshot.status != "pending":
            self._forget(session_id)
        return snapshot

    def cancel(self, session_id: str) -> CaptureSessionSnapshot | None:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            return None
        session.cancel()
        snapshot = session.snapshot()
        self._forget(session_id)
        return snapshot

    def cancel_pending(self, message: str = "Input capture cancelled.") -> None:
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            session.cancel(message)

    def _forget(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)


capture_manager = InputCaptureManager()
