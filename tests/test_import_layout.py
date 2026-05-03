from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_automation_modules_are_not_loose_at_repo_root() -> None:
    forbidden = {
        "ace_auto_click_api.py",
        "ace_auto_click_models.py",
        "actions.py",
        "click_engine.py",
        "pixel_match.py",
        "recorder.py",
        "storage.py",
        "main.py",
    }

    present = {path.name for path in ROOT.iterdir() if path.is_file()}

    assert forbidden.isdisjoint(present)

