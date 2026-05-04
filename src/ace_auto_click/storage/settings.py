from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[3]
SETTINGS_PATH = ROOT / "app_settings.json"


def save_macro(path: str, events: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "events": events}, f, indent=2)


def load_macro(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "events" not in data:
        raise ValueError("Invalid macro file.")
    events = data["events"]
    if not isinstance(events, list):
        raise ValueError("Invalid macro events.")
    return events


def save_settings(settings: Dict[str, Any]) -> None:
    with SETTINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def load_settings() -> Dict[str, Any]:
    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
