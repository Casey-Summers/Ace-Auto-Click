from __future__ import annotations

import json
from pathlib import Path

from ace_auto_click.runtime.doctor import (
    Doctor,
    diagnose_error,
    missing_icon_paths,
    parse_requirements,
    requirement_name,
)


def test_parse_requirements_ignores_comments_and_empty_lines(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(
        "\n# comment\nPillow>=11,<12\n\nfastapi>=0.115,<1 # inline\n",
        encoding="utf-8",
    )

    assert parse_requirements(requirements) == ["Pillow>=11,<12", "fastapi>=0.115,<1"]


def test_requirement_name_extracts_distribution_name() -> None:
    assert requirement_name("Pillow>=11,<12") == "Pillow"
    assert requirement_name("fastapi==0.115.6") == "fastapi"
    assert requirement_name("-r requirements.txt") == ""


def test_missing_icon_paths_reports_only_absent_files(tmp_path: Path) -> None:
    icons = tmp_path / "icons"
    icons.mkdir()
    (icons / "32x32.png").write_bytes(b"png")
    config = {
        "bundle": {
            "icon": ["icons/32x32.png", "icons/icon.ico"],
        }
    }

    assert missing_icon_paths(config, tmp_path) == ["icons/icon.ico"]


def test_known_tauri_icon_error_has_actionable_diagnosis() -> None:
    output = "`icons/icon.ico` not found; required for generating a Windows Resource file"

    assert "Tauri Windows resource generation" in diagnose_error(output)


def test_spawn_eperm_has_actionable_diagnosis() -> None:
    output = "error when starting dev server: Error: spawn EPERM"

    assert "child process was blocked" in diagnose_error(output)


def test_missing_command_is_reported(monkeypatch) -> None:
    doctor = Doctor()
    monkeypatch.setattr("ace_auto_click.runtime.doctor.which", lambda command: None)

    doctor._check_commands()

    assert any(result.status == "FAIL" and "cargo" in result.name for result in doctor.results)
