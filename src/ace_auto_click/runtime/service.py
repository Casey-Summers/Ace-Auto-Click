from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from shutil import which


ROOT = Path(__file__).resolve().parents[3]
UI_DIR = ROOT / "apps" / "desktop-ui"
MIN_PYTHON = (3, 12)


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

    if not which("cargo"):
        raise SystemExit(
            "Rust/Cargo is required to run the Tauri desktop app. Install Rust "
            "from https://rustup.rs/, restart your terminal so PATH is refreshed, "
            "then run: python app.py desktop"
        )

    run_tauri_dev()


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
