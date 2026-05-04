from __future__ import annotations

import re


KNOWN_DIAGNOSES = [
    (
        re.compile(r"icons[/\\]icon\.ico.*not found", re.IGNORECASE),
        "Tauri Windows resource generation requires an icon file. Run `python app.py doctor --fix`.",
    ),
    (
        re.compile(r"cargo.*not found|program not found", re.IGNORECASE),
        "Rust/Cargo is required to compile Tauri. Install Rustup, restart the terminal, then rerun the command.",
    ),
    (
        re.compile(r"pydantic-core.*failed|failed building wheel for pydantic-core", re.IGNORECASE | re.DOTALL),
        "Likely Python/wheel mismatch. Prefer Python 3.12 or upgrade pip/setuptools/wheel.",
    ),
    (
        re.compile(r"failed building wheel for pillow|pillow.*failed", re.IGNORECASE | re.DOTALL),
        "Use `Pillow>=11,<12` and upgrade pip/setuptools/wheel.",
    ),
    (
        re.compile(r"spawn EPERM", re.IGNORECASE),
        "A child process was blocked by OS policy, antivirus, OneDrive sync, or sandbox permissions. Run from a trusted local folder and allow Node/esbuild to spawn.",
    ),
]


def diagnose_error(output: str) -> str:
    for pattern, diagnosis in KNOWN_DIAGNOSES:
        if pattern.search(output):
            return diagnosis
    return ""
