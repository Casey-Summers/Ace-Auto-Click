from __future__ import annotations

import pytest
from pydantic import ValidationError

from ace_auto_click.api.models import AppSettings, AutomationProfile, ClickStepModel, DragStepModel, MoveStepModel, ProfileExport, SequenceRunRequest, SimpleSettings


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
    assert step.movement_mode == "instant"
    assert step.movement_duration_ms == 0
    assert step.movement_smoothness == 70
    assert step.path_randomness == 20
    assert step.arc_direction == "auto"


def test_move_step_accepts_smooth_transition_fields() -> None:
    step = MoveStepModel(
        id="move-1",
        movement_mode="smooth",
        movement_duration_ms=450,
        movement_smoothness=90,
        path_randomness=35,
        arc_direction="left",
    )

    assert step.movement_mode == "smooth"
    assert step.movement_duration_ms == 450
    assert step.movement_smoothness == 90
    assert step.path_randomness == 35
    assert step.arc_direction == "left"


def test_move_step_rejects_out_of_range_smooth_transition_fields() -> None:
    with pytest.raises(ValidationError):
        MoveStepModel(id="move-1", movement_smoothness=101)
    with pytest.raises(ValidationError):
        MoveStepModel(id="move-1", path_randomness=-1)


def test_drag_step_accepts_left_right_defaults() -> None:
    step = DragStepModel(id="drag-1")

    assert step.type == "drag"
    assert step.buttons == ["left", "right"]
    assert step.angle_degrees == 0
    assert step.distance_px == 100
    assert step.duration_ms == 120
    assert step.acceleration == 1.6


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
