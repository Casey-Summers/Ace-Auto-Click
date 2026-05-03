from __future__ import annotations

from typing import Annotated, Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field


ProductName = "Ace Auto Click"


class SimpleSettings(BaseModel):
    action_type: Literal["mouse", "keyboard"] = "mouse"
    action_value: str = "left"
    interval_ms: Annotated[int, Field(ge=1, le=3_600_000)] = 100
    interval_random_ms: Annotated[int, Field(ge=0, le=3_600_000)] = 0
    x: int = 0
    y: int = 0
    position_random_px: Annotated[int, Field(ge=0, le=5_000)] = 0


class AppSettings(BaseModel):
    hotkey: str = "F8"
    emergency_stop_hotkey: str = "F12"
    simple: SimpleSettings = Field(default_factory=SimpleSettings)
    theme: Literal["dark", "light"] = "dark"


class BaseStep(BaseModel):
    id: str
    type: str
    enabled: bool = True
    repeats: Annotated[int, Field(ge=1, le=100_000)] = 1
    interval_ms: Annotated[int, Field(ge=0, le=3_600_000)] = 100
    randomness_ms: Annotated[int, Field(ge=0, le=3_600_000)] = 0


class ClickStepModel(BaseStep):
    type: Literal["click"] = "click"
    x: int = 0
    y: int = 0
    button: Literal["left", "right", "middle"] = "left"
    clicks: Annotated[int, Field(ge=1, le=100)] = 1
    random_offset: Annotated[int, Field(ge=0, le=5_000)] = 0


class WaitStepModel(BaseStep):
    type: Literal["wait"] = "wait"
    ms: Annotated[int, Field(ge=0, le=3_600_000)] = 1000
    random_ms: Annotated[int, Field(ge=0, le=3_600_000)] = 0


class PixelCheckStepModel(BaseStep):
    type: Literal["pixel_check"] = "pixel_check"
    x: int = 0
    y: int = 0
    expected_rgb: Tuple[int, int, int] = (255, 255, 255)
    tolerance: Annotated[int, Field(ge=0, le=255)] = 10
    mode: Literal["wait_until_match", "stop_if_mismatch", "skip_if_mismatch"] = (
        "wait_until_match"
    )


class KeyTapStepModel(BaseStep):
    type: Literal["key_tap"] = "key_tap"
    key: str = "space"


ActionStepModel = Annotated[
    Union[ClickStepModel, WaitStepModel, PixelCheckStepModel, KeyTapStepModel],
    Field(discriminator="type"),
]


class SequenceRunRequest(BaseModel):
    steps: list[ActionStepModel]
    loops: Annotated[int, Field(ge=0, le=100_000)] = 0


class SimpleRunRequest(BaseModel):
    settings: SimpleSettings


class PixelSample(BaseModel):
    x: int
    y: int
    rgb: Tuple[int, int, int]


class RuntimeState(BaseModel):
    product_name: str = ProductName
    running: bool = False
    recording: bool = False
    status: str = "Idle"
    last_error: Optional[str] = None


class CommandResult(BaseModel):
    ok: bool = True
    state: RuntimeState
    message: str = ""
