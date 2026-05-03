from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run_api(host: str, port: int) -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "Missing API dependencies. Run: python -m pip install -r requirements.txt"
        ) from exc

    uvicorn.run("ace_auto_click_api:app", host=host, port=port, reload=False)


def run_desktop() -> None:
    ui_dir = ROOT / "apps" / "desktop-ui"
    if not ui_dir.exists():
        raise SystemExit("Desktop UI workspace is missing: apps/desktop-ui")

    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    api_process = subprocess.Popen(
        [sys.executable, str(ROOT / "main.py"), "api"],
        cwd=ROOT,
    )
    try:
        subprocess.run([npm, "run", "tauri", "dev"], cwd=ui_dir, check=True)
    finally:
        api_process.terminate()
        try:
            api_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_process.kill()


def main() -> None:
    parser = argparse.ArgumentParser(prog="Ace Auto Click")
    parser.add_argument(
        "target",
        nargs="?",
        choices=("api", "desktop"),
        default="api",
        help="Run the local API backend or the Tauri desktop frontend.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if args.target == "desktop":
        run_desktop()
    else:
        run_api(args.host, args.port)


if __name__ == "__main__":
    main()
