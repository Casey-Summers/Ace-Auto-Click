from __future__ import annotations

import os
import subprocess
import sys
import urllib.error
import urllib.request
import json
import time
import uuid
import socket
import threading
from pathlib import Path
from shutil import which


ROOT = Path(__file__).resolve().parents[3]
UI_DIR = ROOT / "apps" / "desktop-ui"
MIN_PYTHON = (3, 12)
CARGO_TARGET_ENV = "CARGO_TARGET_DIR"


_active_server = None


def request_api_shutdown() -> None:
    if _active_server is not None:
        _active_server.should_exit = True


def _wait_for_process_exit(pid: int) -> None:
    if sys.platform != "win32" or pid <= 0: return
    import ctypes
    handle = ctypes.windll.kernel32.OpenProcess(0x00100000, False, pid)
    if handle:
        try: ctypes.windll.kernel32.WaitForSingleObject(handle, 30000)
        finally: ctypes.windll.kernel32.CloseHandle(handle)


def run_api(host: str = "127.0.0.1", port: int = 8765, replace_pid: int = 0,
            instance_id: str | None = None, lease_required: bool = False) -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "Missing API dependencies. Run: python -m pip install -r requirements.txt"
        ) from exc

    if instance_id: os.environ["ACE_BACKEND_INSTANCE_ID"] = instance_id
    if lease_required: os.environ["ACE_LEASE_REQUIRED"] = "1"
    _wait_for_process_exit(replace_pid)
    global _active_server
    _active_server = uvicorn.Server(uvicorn.Config("ace_auto_click.api.app:app", host=host, port=port, reload=False))
    from ace_auto_click.runtime.lease import start_monitor
    start_monitor(request_api_shutdown)
    _active_server.run()
    _active_server = None


def run_desktop_dev() -> None:
    if not UI_DIR.exists():
        raise SystemExit("Desktop UI workspace is missing: apps/desktop-ui")

    if not which("cargo"):
        raise SystemExit(
            "Rust/Cargo is required to run the Tauri desktop app. Install Rust "
            "from https://rustup.rs/, restart your terminal so PATH is refreshed, "
            "then run: python app.py desktop"
        )

    run_tauri_dev()


def run_tauri_dev() -> None:
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    env = os.environ.copy()
    env.setdefault(CARGO_TARGET_ENV, str(default_cargo_target_dir()))
    existing = _api_identity()
    if existing is not None:
        raise SystemExit(
            "Ace Auto Click refused to reuse an existing backend on 127.0.0.1:8765 "
            f"(instance {existing.get('instance_id', 'unknown')}). Close the older app/backend and try again."
        )
    if _port_in_use("127.0.0.1", 8765):
        raise SystemExit(
            "Port 8765 is already owned by an unrelated or incompatible process. "
            "Ace Auto Click will not attach to it; close that process or free the port and try again."
        )
    instance_id = str(uuid.uuid4())
    api_env = env.copy()
    api_env["ACE_BACKEND_INSTANCE_ID"] = instance_id
    api_process = subprocess.Popen(
        [sys.executable, str(ROOT / "app.py"), "api"],
        cwd=ROOT,
        env=api_env,
    )
    try:
        _wait_for_api(instance_id, api_process)
        try:
            subprocess.run([npm, "run", "tauri", "dev"], cwd=UI_DIR, check=True, env=env)
        except subprocess.CalledProcessError as exc:
            raise SystemExit(
                "Tauri failed to start. If Rust/Cargo was just installed, restart "
                "your terminal so PATH is refreshed. Otherwise run "
                "`npm.cmd --prefix apps/desktop-ui run tauri dev` for the full "
                "Tauri error output."
            ) from exc
    finally:
        if api_process is not None:
            _terminate_process(api_process)


def default_cargo_target_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "AceAutoClick" / "cargo-target"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "AceAutoClick" / "cargo-target"
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "ace-auto-click" / "cargo-target"


def _api_identity(host: str = "127.0.0.1", port: int = 8765) -> dict[str, object] | None:
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=0.7) as response:
            if not 200 <= response.status < 300:
                return None
            value = json.loads(response.read().decode("utf-8"))
            return value if isinstance(value, dict) else {"instance_id": "unknown"}
    except (OSError, urllib.error.URLError):
        return None


def _api_is_running(host: str = "127.0.0.1", port: int = 8765) -> bool:
    return _api_identity(host, port) is not None


def _port_in_use(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except OSError:
        return False


def _wait_for_api(instance_id: str, process: subprocess.Popen[bytes], timeout_s: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise SystemExit("Ace Auto Click backend exited during startup.")
        identity = _api_identity()
        if identity is not None:
            actual = identity.get("instance_id")
            if actual != instance_id:
                raise SystemExit(f"Backend ownership check failed: expected {instance_id}, received {actual}.")
            return
        time.sleep(0.1)
    raise SystemExit("Timed out waiting for the owned Ace Auto Click backend.")


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def check_runtime() -> None:
    from ace_auto_click.api.app import _load_app_settings, create_app
    from ace_auto_click.storage.profiles import ensure_profiles_dir

    failures: list[str] = []
    if sys.version_info < MIN_PYTHON:
        failures.append(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required; "
            f"found {sys.version.split()[0]}."
        )

    _check_command("node", "Install Node.js from https://nodejs.org/.", failures)
    npm_command = "npm.cmd" if sys.platform == "win32" else "npm"
    _check_command(npm_command, "Install npm with Node.js.", failures)
    _check_command(
        "cargo",
        "Install Rust/Cargo from https://rustup.rs/ and restart your terminal.",
        failures,
    )

    create_app()
    _load_app_settings()
    ensure_profiles_dir()

    if failures:
        raise SystemExit(
            "Ace Auto Click environment check failed:\n- " + "\n- ".join(failures)
        )

    print("Ace Auto Click runtime check passed.")


def _check_command(command: str, guidance: str, failures: list[str]) -> None:
    if not which(command):
        failures.append(f"`{command}` was not found on PATH. {guidance}")
