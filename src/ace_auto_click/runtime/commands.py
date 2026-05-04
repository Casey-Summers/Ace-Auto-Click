from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass
class CommandResult:
    args: Sequence[str]
    cwd: Path
    returncode: int
    stdout: str
    stderr: str

    def output_summary(self) -> str:
        text = (self.stdout or self.stderr).strip().splitlines()
        return text[0] if text else f"exit {self.returncode}"


def run_command(args: Sequence[str], cwd: Path) -> CommandResult:
    try:
        completed = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=180)
        return CommandResult(args, cwd, completed.returncode, completed.stdout, completed.stderr)
    except FileNotFoundError as exc:
        return CommandResult(args, cwd, 127, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        return CommandResult(args, cwd, 124, exc.stdout or "", exc.stderr or "Command timed out.")


def npm_command() -> str:
    return "npm.cmd" if sys.platform == "win32" else "npm"
