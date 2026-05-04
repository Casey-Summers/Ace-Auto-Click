from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ace_auto_click.api.models import AppSettings, AutomationProfile, ProfileExport


ROOT = Path(__file__).resolve().parents[3]
PROFILES_DIR = ROOT / "profiles"
PROFILE_SUFFIX = ".aceprofile.json"


def ensure_profiles_dir() -> Path:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILES_DIR


def _safe_profile_stem(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip()).strip(".-")
    return stem or "profile"


def _profile_path(profile_name: str) -> Path:
    stem = _safe_profile_stem(profile_name)
    return ensure_profiles_dir() / f"{stem}{PROFILE_SUFFIX}"


def list_profile_files() -> list[dict[str, Any]]:
    directory = ensure_profiles_dir()
    files: list[dict[str, Any]] = []
    for path in sorted(directory.glob(f"*{PROFILE_SUFFIX}")):
        try:
            stat = path.stat()
            display_name = path.name.removesuffix(PROFILE_SUFFIX)
            try:
                with path.open("r", encoding="utf-8") as handle:
                    raw = json.load(handle)
                display_name = str(raw.get("profile", {}).get("name") or display_name)
            except (OSError, json.JSONDecodeError):
                pass
            files.append(
                {
                    "file_name": path.name,
                    "profile_name": display_name,
                    "modified_at": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                    "size": stat.st_size,
                }
            )
        except OSError:
            continue
    return files


def profile_directory_status() -> dict[str, Any]:
    directory = ensure_profiles_dir()
    return {
        "path": str(directory),
        "available": directory.exists() and directory.is_dir(),
        "file_count": len(list(directory.glob(f"*{PROFILE_SUFFIX}"))),
    }


def save_profile_export(settings: AppSettings, profile: AutomationProfile) -> dict[str, Any]:
    export = ProfileExport(
        profile=profile,
        app_settings={
            "mode": settings.mode,
            "run_toggle_hotkey": settings.run_toggle_hotkey,
            "emergency_stop_hotkey": settings.emergency_stop_hotkey,
            "show_event_log": settings.show_event_log,
            "theme": settings.theme,
        },
    )
    path = _profile_path(profile.name)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(export.model_dump(), handle, indent=2)
    return {
        "file_name": path.name,
        "profile_name": profile.name,
        "modified_at": datetime.now(timezone.utc).isoformat(),
        "size": path.stat().st_size,
    }


def load_profile_export(file_name: str) -> ProfileExport:
    if Path(file_name).name != file_name or not file_name.endswith(PROFILE_SUFFIX):
        raise ValueError("Invalid profile file name.")
    path = ensure_profiles_dir() / file_name
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return ProfileExport.model_validate(raw)


def open_profiles_folder() -> None:
    directory = ensure_profiles_dir()
    if os.name == "nt":
        os.startfile(directory)  # type: ignore[attr-defined]
        return
    raise RuntimeError("Opening the profiles folder is only supported on Windows.")
