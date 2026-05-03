from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from shutil import which
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[3]
UI_DIR = ROOT / "apps" / "desktop-ui"
API_URL = "http://127.0.0.1:8765"
UI_URL = "http://127.0.0.1:1420"


def run_api(host: str = "127.0.0.1", port: int = 8765) -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "Missing API dependencies. Run: python -m pip install -r requirements.txt"
        ) from exc

    uvicorn.run("ace_auto_click.api.app:app", host=host, port=port, reload=False)


def run_desktop_dev() -> None:
    if not UI_DIR.exists():
        raise SystemExit("Desktop UI workspace is missing: apps/desktop-ui")

    if which("cargo"):
        run_tauri_dev()
        return

    run_webview_dev()


def run_tauri_dev() -> None:
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    api_process = subprocess.Popen(
        [sys.executable, str(ROOT / "app.py"), "api"],
        cwd=ROOT,
    )
    try:
        try:
            subprocess.run([npm, "run", "tauri", "dev"], cwd=UI_DIR, check=True)
        except subprocess.CalledProcessError as exc:
            raise SystemExit(
                "Tauri failed to start. If Rust/Cargo was just installed, restart "
                "your terminal so PATH is refreshed. Otherwise run "
                "`npm.cmd --prefix apps/desktop-ui run tauri dev` for the full "
                "Tauri error output."
            ) from exc
    finally:
        _terminate_process(api_process)


def run_webview_dev() -> None:
    try:
        import webview
    except ImportError as exc:
        raise SystemExit(
            "Tauri requires Rust/Cargo, but cargo was not found on PATH. "
            "Install Rust from https://rustup.rs/ or install Python dependencies "
            "with: python -m pip install -r requirements.txt"
        ) from exc

    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    api_process = subprocess.Popen(
        [sys.executable, str(ROOT / "app.py"), "api"],
        cwd=ROOT,
    )
    ui_process = subprocess.Popen(
        [npm, "run", "dev"],
        cwd=UI_DIR,
    )

    try:
        _wait_for_url(f"{API_URL}/health", timeout_s=15)
        _wait_for_url(UI_URL, timeout_s=15)
        webview.create_window(
            "Ace Auto Click",
            UI_URL,
            width=1280,
            height=820,
            min_size=(960, 720),
        )
        webview.start()
    finally:
        _terminate_process(ui_process)
        _terminate_process(api_process)


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def _wait_for_url(url: str, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=1):
                return
        except URLError:
            time.sleep(0.2)
    raise SystemExit(f"Timed out waiting for desktop UI dev server at {url}.")


def check_runtime() -> None:
    from ace_auto_click.api.app import _load_app_settings, create_app

    create_app()
    _load_app_settings()
    print("Ace Auto Click runtime check passed.")
