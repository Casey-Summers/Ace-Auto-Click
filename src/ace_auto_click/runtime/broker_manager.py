from __future__ import annotations

import ctypes
import os
import secrets
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any

from ace_auto_click.automation.input_backend import BrokerInputBackend, LocalInputBackend
from ace_auto_click.runtime.windows import is_process_elevated


def _shell_execute_elevated(executable: str, parameters: str) -> int:
    shell_execute = ctypes.windll.shell32.ShellExecuteW
    shell_execute.restype = ctypes.c_void_p
    return int(shell_execute(None, "runas", executable, parameters, None, 0) or 0)


@dataclass
class BrokerStatus:
    supported: bool
    connected: bool = False
    elevated: bool = False
    status: str = "local"
    last_error: str | None = None


class InputBrokerManager:
    def __init__(self, engine: Any, local_hotkeys: Any, callback_url: str = "http://127.0.0.1:8765/runtime/broker-event") -> None:
        self._engine = engine
        self._local_hotkeys = local_hotkeys
        self._callback_url = callback_url
        self._backend: BrokerInputBackend | None = None
        self._token_hex: str | None = None
        self._lock = threading.Lock()
        self._status = BrokerStatus(supported=sys.platform == "win32", elevated=is_process_elevated())
        self._hotkeys: tuple[str, str] | None = None

    def snapshot(self) -> BrokerStatus:
        backend = self._backend
        if backend is not None:
            try:
                backend.runtime_info()
            except Exception as exc:
                self._mark_disconnected(f"Elevated input service disconnected: {exc}")
        with self._lock:
            return BrokerStatus(**self._status.__dict__)

    def authenticate(self, authorization: str | None) -> bool:
        with self._lock:
            expected = f"Bearer {self._token_hex}" if self._token_hex else None
        return bool(expected and secrets.compare_digest(authorization or "", expected))

    def set_hotkeys(self, emergency: str, run_toggle: str) -> None:
        self._hotkeys = (emergency, run_toggle)
        backend = self._backend
        if backend is not None:
            try:
                backend.bind_hotkeys(emergency, run_toggle)
            except Exception as exc:
                self._mark_disconnected(f"Elevated input service disconnected: {exc}")
                raise
        else:
            self._local_hotkeys.bind(emergency, run_toggle)

    def start_elevated(self, timeout_s: float = 15.0) -> BrokerStatus:
        if sys.platform != "win32":
            raise RuntimeError("Elevated input service is only available on Windows.")
        with self._lock:
            if self._backend is not None:
                return BrokerStatus(**self._status.__dict__)
            self._status.status = "starting"
            self._status.last_error = None

        token_hex = secrets.token_hex(32)
        pipe_name = rf"\\.\pipe\AceAutoClick-{os.getpid()}-{secrets.token_hex(8)}"
        args = [
            str(os.path.abspath(sys.argv[0])),
            "input-broker",
            "--pipe", pipe_name,
            "--token", token_hex,
            "--callback-url", self._callback_url,
        ]
        parameters = subprocess.list2cmdline(args)
        result = _shell_execute_elevated(sys.executable, parameters)
        if result <= 32:
            self._set_failure("Administrator approval was cancelled or the input service could not start.")
            raise RuntimeError(self.snapshot().last_error or "Input service launch failed.")

        deadline = time.monotonic() + timeout_s
        last_error: Exception | None = None
        backend: BrokerInputBackend | None = None
        while time.monotonic() < deadline:
            try:
                backend = BrokerInputBackend(pipe_name, bytes.fromhex(token_hex))
                break
            except (FileNotFoundError, ConnectionRefusedError, OSError) as exc:
                last_error = exc
                time.sleep(0.15)
        if backend is None:
            message = f"Elevated input service did not connect: {last_error or 'timed out'}"
            self._set_failure(message)
            raise RuntimeError(message)

        try:
            broker_info = backend.runtime_info()
            if not bool(broker_info.get("elevated")):
                raise RuntimeError("The input broker started without administrator privileges.")
            self._local_hotkeys.stop()
            self._engine.set_input_backend(backend)
            with self._lock:
                self._backend = backend
                self._token_hex = token_hex
                self._status = BrokerStatus(supported=True, connected=True, elevated=True, status="ready")
            if self._hotkeys:
                backend.bind_hotkeys(*self._hotkeys)
        except Exception as exc:
            if self._backend is backend:
                self._mark_disconnected(f"Elevated input service failed: {exc}")
            else:
                backend.close()
                self._set_failure(f"Elevated input service failed: {exc}")
            raise
        with self._lock:
            return BrokerStatus(**self._status.__dict__)

    def stop(self) -> BrokerStatus:
        with self._lock:
            backend = self._backend
            self._backend = None
            self._token_hex = None
        if backend is not None:
            self._engine.stop()
            self._engine.set_input_backend(LocalInputBackend())
        if self._hotkeys:
            self._local_hotkeys.bind(*self._hotkeys)
        with self._lock:
            self._status = BrokerStatus(supported=sys.platform == "win32", elevated=is_process_elevated(), status="local")
            return BrokerStatus(**self._status.__dict__)

    def _set_failure(self, message: str) -> None:
        with self._lock:
            self._status.connected = False
            self._status.elevated = False
            self._status.status = "error"
            self._status.last_error = message

    def _mark_disconnected(self, message: str) -> None:
        with self._lock:
            if self._backend is None:
                return
            self._backend = None
            self._token_hex = None
            self._status = BrokerStatus(supported=sys.platform == "win32", status="error", last_error=message)
        if not self._engine.is_running():
            try:
                self._engine.set_input_backend(LocalInputBackend())
            except Exception:
                pass
        if self._hotkeys:
            try:
                self._local_hotkeys.bind(*self._hotkeys)
            except Exception:
                pass
