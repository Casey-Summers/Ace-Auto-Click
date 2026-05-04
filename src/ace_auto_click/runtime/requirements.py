from __future__ import annotations

import re
from pathlib import Path


def parse_requirements(path: Path) -> list[str]:
    entries = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line:
            entries.append(line)
    return entries


def requirement_name(requirement: str) -> str:
    if requirement.startswith("-r "):
        return ""
    match = re.match(r"([A-Za-z0-9_.-]+)", requirement)
    return match.group(1) if match else ""
