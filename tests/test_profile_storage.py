from __future__ import annotations

from ace_auto_click.api.models import AppSettings, AutomationProfile, ClickStepModel
from ace_auto_click.automation.hotkeys import hotkey_to_pynput
from ace_auto_click.storage import profiles


def test_profile_export_round_trip_preserves_sequence(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(profiles, "PROFILES_DIR", tmp_path)
    profile = AutomationProfile(
        id="profile-1",
        name="Saved Profile",
        mode="advanced",
        steps=[ClickStepModel(id="click-1", x=12, y=34)],
        loops=2,
    )
    settings = AppSettings(
        active_profile_id=profile.id,
        profiles=[profile],
        run_toggle_hotkey="F8",
        emergency_stop_hotkey="F12",
    )

    saved = profiles.save_profile_export(settings, profile)
    loaded = profiles.load_profile_export(saved["file_name"])

    assert saved["file_name"] == "Saved-Profile.aceprofile.json"
    assert loaded.profile.name == "Saved Profile"
    assert loaded.profile.steps[0].x == 12
    assert loaded.profile.loops == 2
    assert loaded.app_settings["emergency_stop_hotkey"] == "F12"


def test_hotkey_to_pynput_normalizes_common_keys() -> None:
    assert hotkey_to_pynput("F12") == "<f12>"
    assert hotkey_to_pynput("Ctrl+Alt+F8") == "<ctrl>+<alt>+<f8>"
    assert hotkey_to_pynput("Space") == "<space>"
