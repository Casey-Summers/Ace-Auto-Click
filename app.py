from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ace_auto_click.runtime.doctor import run_doctor
from ace_auto_click.runtime.service import check_runtime, run_api, run_desktop_dev


def main() -> None:
    parser = argparse.ArgumentParser(prog="Ace Auto Click")
    subparsers = parser.add_subparsers(dest="target")

    desktop_parser = subparsers.add_parser("desktop", help="Run the Tauri desktop app.")
    desktop_parser.set_defaults(target="desktop")

    api_parser = subparsers.add_parser("api", help="Run the local backend API.")
    api_parser.add_argument("--host", default="127.0.0.1")
    api_parser.add_argument("--port", type=int, default=8765)
    api_parser.set_defaults(target="api")

    check_parser = subparsers.add_parser("check", help="Run a quick environment check.")
    check_parser.set_defaults(target="check")

    doctor_parser = subparsers.add_parser("doctor", help="Run the dependency doctor.")
    doctor_parser.add_argument("--fix", action="store_true", help="Attempt safe automated fixes.")
    doctor_parser.add_argument("--dev", action="store_true", help="Check development dependencies too.")
    doctor_parser.add_argument("--build-check", action="store_true", help="Run the frontend build check.")
    doctor_parser.add_argument("--log-dir", default=str(ROOT / "logs" / "dependency-doctor"))
    doctor_parser.set_defaults(target="doctor")

    parser.set_defaults(target="desktop")
    args = parser.parse_args()

    if args.target == "api":
        run_api(args.host, args.port)
    elif args.target == "check":
        check_runtime()
    elif args.target == "doctor":
        raise SystemExit(run_doctor(args))
    else:
        run_desktop_dev()

if __name__ == "__main__":
    main()
