from __future__ import annotations

from ace_auto_click.api.app import _to_action_step
from ace_auto_click.api.models import ClickStepModel, KeyTapStepModel
from ace_auto_click.automation.actions import ClickStep, KeyTapStep


def test_api_click_model_converts_to_runtime_step() -> None:
    step = _to_action_step(ClickStepModel(id="click-1", x=10, y=20))

    assert isinstance(step, ClickStep)
    assert step.x == 10
    assert step.y == 20


def test_api_key_tap_model_converts_to_runtime_step() -> None:
    step = _to_action_step(KeyTapStepModel(id="key-1", key="space"))

    assert isinstance(step, KeyTapStep)
    assert step.key == "space"

