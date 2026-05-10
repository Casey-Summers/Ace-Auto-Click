from __future__ import annotations

from ace_auto_click.api.app import _to_action_step
from ace_auto_click.api.models import ClickStepModel, DragStepModel, KeyHoldStepModel, KeyTapStepModel, MoveStepModel
from ace_auto_click.automation.actions import ClickStep, DragStep, KeyHoldStep, KeyTapStep, MoveStep


def test_api_click_model_converts_to_runtime_step() -> None:
    step = _to_action_step(ClickStepModel(id="click-1", x=10, y=20))

    assert isinstance(step, ClickStep)
    assert step.x == 10
    assert step.y == 20


def test_api_move_model_converts_to_runtime_step() -> None:
    step = _to_action_step(MoveStepModel(id="move-1", x=10, y=20))

    assert isinstance(step, MoveStep)
    assert step.x == 10
    assert step.y == 20


def test_api_drag_model_converts_to_runtime_step() -> None:
    step = _to_action_step(DragStepModel(id="drag-1", x=10, y=20, direction="down", length_px=300, speed=500))

    assert isinstance(step, DragStep)
    assert step.x == 10
    assert step.y == 20
    assert step.buttons == ["left", "right"]
    assert step.direction == "down"
    assert step.length_px == 300
    assert step.acceleration == 1.6


def test_api_key_tap_model_converts_to_runtime_step() -> None:
    step = _to_action_step(KeyTapStepModel(id="key-1", key="space"))

    assert isinstance(step, KeyTapStep)
    assert step.key == "space"


def test_api_key_hold_model_converts_to_runtime_step() -> None:
    step = _to_action_step(KeyHoldStepModel(id="hold-1", key="space", hold_ms=450))

    assert isinstance(step, KeyHoldStep)
    assert step.key == "space"
    assert step.hold_ms == 450

