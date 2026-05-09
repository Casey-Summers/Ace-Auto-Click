from __future__ import annotations

import pytest
from pydantic import ValidationError

from ace_auto_click.api.models import AppSettings, AutomationProfile, ClickStepModel, MoveStepModel, ProfileExport, SequenceRunRequest, SimpleSettings


def test_simple_settings_rejects_zero_interval() -> None:
    with pytest.raises(ValidationError):
        SimpleSettings(interval_ms=0)


def test_click_step_accepts_professional_defaults() -> None:
    step = ClickStepModel(id="click-1")

    assert step.type == "click"
    assert step.button == "left"
    assert step.clicks == 1


def test_move_step_accepts_pointer_target_defaults() -> None:
    step = MoveStepModel(id="move-1")

    assert step.type == "move"
    assert step.x == 0
    assert step.y == 0
    assert step.random_offset == 0


def test_app_settings_accepts_profiles_and_mode_fields() -> None:
    settings = AppSettings(
        mode="normal",
        run_toggle_hotkey="F8",
        emergency_stop_hotkey="F12",
        show_event_log=False,
        active_profile_id="profile-1",
        profiles=[AutomationProfile(id="profile-1", name="Starter", mode="normal")],
    )

    assert settings.mode == "normal"
    assert settings.profiles[0].normal.use_current_mouse is True
    assert settings.show_event_log is False


def test_sequence_request_accepts_loop_count() -> None:
    request = SequenceRunRequest(steps=[ClickStepModel(id="click-1")], loops=5)

    assert request.loops == 5


def test_profile_export_preserves_profile_contract() -> None:
    export = ProfileExport(
        profile=AutomationProfile(
            id="profile-1",
            name="Saved Profile",
            mode="advanced",
            steps=[ClickStepModel(id="click-1", x=10, y=20)],
            loops=3,
        ),
        app_settings={"run_toggle_hotkey": "F8", "emergency_stop_hotkey": "F12"},
    )

    assert export.schema_version == 1
    assert export.profile.steps[0].x == 10
    assert export.profile.loops == 3
