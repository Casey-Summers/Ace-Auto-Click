from __future__ import annotations

import pytest
from pydantic import ValidationError

from ace_auto_click.api.models import ClickStepModel, SimpleSettings


def test_simple_settings_rejects_zero_interval() -> None:
    with pytest.raises(ValidationError):
        SimpleSettings(interval_ms=0)


def test_click_step_accepts_professional_defaults() -> None:
    step = ClickStepModel(id="click-1")

    assert step.type == "click"
    assert step.button == "left"
    assert step.clicks == 1

