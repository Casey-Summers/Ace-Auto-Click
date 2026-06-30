from __future__ import annotations

import json
import threading
import urllib.request
from multiprocessing.connection import Listener
from typing import Any

from pynput import keyboard, mouse

from ace_auto_click.automation.hotkeys import RuntimeHotkeyManager
from ace_auto_click.runtime.windows import process_identity


def _keyboard_value(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("Key."):
        return getattr(keyboard.Key, value[4:], value)
    return value


def _mouse_value(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("Button."):
        return getattr(mouse.Button, value[7:], value)
    return value


def _post_event(callback_url: str, token: str, action: str) -> None:
    def send() -> None:
        body = json.dumps({"action": action}).encode("utf-8")
        request = urllib.request.Request(
            callback_url,
            data=body,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=2).close()
        except OSError:
            pass

    threading.Thread(target=send, daemon=True).start()


def run_input_broker(pipe_name: str, token_hex: str, callback_url: str) -> None:
    token = bytes.fromhex(token_hex)
    mouse_ctl = mouse.Controller()
    keyboard_ctl = keyboard.Controller()
    hotkeys = RuntimeHotkeyManager(
        on_emergency_stop=lambda: _post_event(callback_url, token_hex, "emergency_stop"),
        on_run_toggle=lambda: _post_event(callback_url, token_hex, "run_toggle"),
    )
    listener = Listener(pipe_name, family="AF_PIPE", authkey=token)
    connection = listener.accept()
    try:
        while True:
            try:
                request = connection.recv()
            except EOFError:
                break
            request_id = request.get("id")
            operation = request.get("op")
            args = request.get("args", [])
            try:
                result: Any = None
                if operation == "mouse.position.get":
                    result = tuple(mouse_ctl.position)
                elif operation == "mouse.position.set":
                    mouse_ctl.position = (int(args[0]), int(args[1]))
                elif operation == "mouse.click":
                    mouse_ctl.click(_mouse_value(args[0]), int(args[1]))
                elif operation == "mouse.press":
                    mouse_ctl.press(_mouse_value(args[0]))
                elif operation == "mouse.release":
                    mouse_ctl.release(_mouse_value(args[0]))
                elif operation == "keyboard.press":
                    keyboard_ctl.press(_keyboard_value(args[0]))
                elif operation == "keyboard.release":
                    keyboard_ctl.release(_keyboard_value(args[0]))
                elif operation == "keyboard.tap":
                    keyboard_ctl.tap(_keyboard_value(args[0]))
                elif operation == "hotkeys.bind":
                    hotkeys.bind(str(args[0]), str(args[1]))
                elif operation == "runtime.info":
                    result = process_identity()
                elif operation == "shutdown":
                    connection.send({"id": request_id, "ok": True, "result": None})
                    break
                else:
                    raise ValueError(f"Unknown input broker operation: {operation}")
                connection.send({"id": request_id, "ok": True, "result": result})
            except Exception as exc:
                connection.send({"id": request_id, "ok": False, "error": str(exc)})
    finally:
        hotkeys.stop()
        connection.close()
        listener.close()
