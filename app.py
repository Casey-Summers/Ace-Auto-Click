from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ace_auto_click.runtime.service import check_runtime, run_api, run_desktop_dev


def main() -> None:
    parser = argparse.ArgumentParser(prog="Ace Auto Click")
    parser.add_argument(
        "target",
        nargs="?",
        choices=("api", "desktop", "check"),
        default="desktop",
        help="Run the desktop app, backend API, or runtime check.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if args.target == "api":
        run_api(args.host, args.port)
    elif args.target == "check":
        check_runtime()
    else:
        run_desktop_dev()


if __name__ == "__main__":
    main()
