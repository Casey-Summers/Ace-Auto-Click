from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import uuid
from pathlib import Path


def request_elevated_replacement() -> str:
    instance_id = str(uuid.uuid4())
    app_path = Path(__file__).resolve().parents[3] / "app.py"
    arguments = subprocess.list2cmdline([
        str(app_path), "api", "--replace-pid", str(os.getpid()),
        "--instance-id", instance_id, "--lease-required",
    ])
    shell_execute = ctypes.windll.shell32.ShellExecuteW
    shell_execute.restype = ctypes.c_void_p
    result = int(shell_execute(None, "runas", sys.executable, arguments, str(app_path.parent), 0) or 0)
    if result <= 32:
        raise RuntimeError("Administrator approval was cancelled or the elevated backend could not start.")
    return instance_id
