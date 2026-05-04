from __future__ import annotations

from ace_auto_click.api.models import AppSettings, AutomationProfile, ClickStepModel, WaitStepModel
from ace_auto_click.storage.settings import load_settings, save_settings


def load_app_settings() -> AppSettings:
    raw = load_settings()
    if "simple" in raw:
        settings = AppSettings.model_validate(raw)
        return with_default_profile(settings)

    return with_default_profile(AppSettings(
        hotkey=raw.get("hotkey", "F8"),
        run_toggle_hotkey=raw.get("hotkey", "F8"),
        simple={
            "action_type": raw.get("simple_action_type", "mouse"),
            "action_value": raw.get("simple_action_value", "left"),
            "interval_ms": raw.get("simple_interval", 100),
            "interval_random_ms": raw.get("simple_interval_rnd", 0),
            "x": raw.get("simple_x", 0),
            "y": raw.get("simple_y", 0),
            "position_random_px": raw.get("simple_pos_rnd", 0),
        },
    ))


def with_default_profile(settings: AppSettings) -> AppSettings:
    if settings.profiles:
        return settings
    settings.profiles = [
        AutomationProfile(
            id=settings.active_profile_id or "default-profile",
            name="Default Profile",
            mode=settings.mode,
            steps=[
                ClickStepModel(id="step-click-1", x=settings.simple.x, y=settings.simple.y),
                WaitStepModel(id="step-wait-1", ms=1000, interval_ms=0),
            ],
            loops=1,
            loops_count=1,
            loops_infinite=False,
        )
    ]
    settings.active_profile_id = settings.profiles[0].id
    return settings


def save_app_settings(settings: AppSettings) -> None:
    save_settings(settings.model_dump())
