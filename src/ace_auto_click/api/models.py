from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field, field_validator


ProductName = "Ace Auto Click"
MouseButtonName = Literal["left", "right", "middle"]


class SimpleSettings(BaseModel):
    action_type: Literal["mouse", "keyboard"] = "mouse"
    action_value: str = "left"
    interval_ms: Annotated[int, Field(ge=1, le=3_600_000)] = 100
    interval_random_ms: Annotated[int, Field(ge=0, le=3_600_000)] = 0
    x: int = 0
    y: int = 0
    position_random_px: Annotated[int, Field(ge=0, le=5_000)] = 0


class NormalProfileSettings(BaseModel):
    use_current_mouse: bool = True
    button: Literal["left", "right", "middle"] = "left"
    interval_ms: Annotated[int, Field(ge=1, le=3_600_000)] = 100
    interval_random_ms: Annotated[int, Field(ge=0, le=3_600_000)] = 0
    position_random_px: Annotated[int, Field(ge=0, le=5_000)] = 0
    clicks_per_cycle: Annotated[int, Field(ge=1, le=100)] = 1
    double_click: bool = False


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


class MoveStepModel(BaseStep):
    type: Literal["move"] = "move"
    x: int = 0
    y: int = 0
    random_offset: Annotated[int, Field(ge=0, le=5_000)] = 0


class DragStepModel(BaseStep):
    type: Literal["drag"] = "drag"
    x: int = 0
    y: int = 0
    buttons: Annotated[list[MouseButtonName], Field(min_length=1, max_length=3)] = Field(
        default_factory=lambda: ["left", "right"]
    )
    direction: Literal["right", "left", "up", "down"] = "right"
    length_px: Annotated[int, Field(ge=0, le=100_000)] = 100
    speed: Annotated[int, Field(ge=50, le=5000)] = 500
    acceleration: Annotated[float, Field(ge=0.2, le=5.0)] = 1.6
    hold_delay_ms: Annotated[int, Field(ge=0, le=10_000)] = 60
    release_delay_ms: Annotated[int, Field(ge=0, le=10_000)] = 0
    button_order: Annotated[list[MouseButtonName], Field(min_length=1, max_length=3)] | None = None
    random_offset: Annotated[int, Field(ge=0, le=5_000)] = 0

    @field_validator("speed", mode="before")
    @classmethod
    def coerce_legacy_speed(cls, value: Any) -> Any:
        if isinstance(value, str):
            legacy = value.strip().lower()
            if legacy == "slow":
                return 280
            if legacy == "fast":
                return 900
            if legacy == "normal":
                return 500
        return value

    @property
    def angle_degrees(self) -> float:
        return 0.0

    @property
    def distance_px(self) -> int:
        return self.length_px

    @property
    def duration_ms(self) -> int:
        return 120


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


class KeyHoldStepModel(BaseStep):
    type: Literal["key_hold"] = "key_hold"
    key: str = "space"
    hold_ms: Annotated[int, Field(ge=0, le=60_000)] = 300


class LoopStartStepModel(BaseStep):
    type: Literal["loop_start"] = "loop_start"
    loop_id: str
    loop_count: Annotated[int, Field(ge=1, le=100_000)] = 1
    loop_infinite: bool = False
    collapsed: bool = False


class LoopEndStepModel(BaseStep):
    type: Literal["loop_end"] = "loop_end"
    loop_id: str


ActionStepModel = Annotated[
    Union[ClickStepModel, MoveStepModel, DragStepModel, WaitStepModel, PixelCheckStepModel, KeyTapStepModel, KeyHoldStepModel, LoopStartStepModel, LoopEndStepModel],
    Field(discriminator="type"),
]


class AutomationProfile(BaseModel):
    id: str = "default-profile"
    name: str = "Default Profile"
    mode: Literal["normal", "advanced"] = "advanced"
    normal: NormalProfileSettings = Field(default_factory=NormalProfileSettings)
    steps: list[ActionStepModel] = Field(default_factory=list)
    loops: Annotated[int, Field(ge=0, le=100_000)] = 0
    loops_count: Annotated[int, Field(ge=1, le=100_000)] = 1
    loops_infinite: bool = False
    action_icon_colors: dict[
        Literal["click", "move", "drag", "wait", "pixel_check", "key_tap", "key_hold", "loop_start", "loop_end"],
        str,
    ] = Field(default_factory=dict)


class ProfileExport(BaseModel):
    schema_version: Literal[1] = 1
    exported_by: str = ProductName
    profile: AutomationProfile
    app_settings: dict[str, Any] = Field(default_factory=dict)


class ProfileFile(BaseModel):
    file_name: str
    profile_name: str
    modified_at: str
    size: int


class ProfileDirectoryStatus(BaseModel):
    path: str
    available: bool = True
    file_count: int = 0


class AppSettings(BaseModel):
    hotkey: str = "F8"
    run_toggle_hotkey: str = "F8"
    emergency_stop_hotkey: str = "F12"
    show_event_log: bool = True
    active_profile_id: str = "default-profile"
    mode: Literal["normal", "advanced"] = "advanced"
    simple: SimpleSettings = Field(default_factory=SimpleSettings)
    theme: Literal["dark", "light"] = "dark"
    icon_colors_profile_dependent: bool = False
    action_icon_colors: dict[
        Literal["click", "move", "drag", "wait", "pixel_check", "key_tap", "key_hold", "loop_start", "loop_end"],
        str,
    ] = Field(default_factory=dict)
    profiles: list[AutomationProfile] = Field(default_factory=list)


class SequenceRunRequest(BaseModel):
    steps: list[ActionStepModel]
    loops: Annotated[int, Field(ge=0, le=100_000)] = 0
    loops_count: Annotated[int, Field(ge=1, le=100_000)] = 1
    loops_infinite: bool = False


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
    current_step_id: Optional[str] = None
    current_step_state: Optional[str] = None


class ExecutionEvent(BaseModel):
    step_id: str
    step_type: str
    phase: Literal["step_execute", "step_wait", "step_complete", "loop_enter", "loop_exit", "loop_repeat", "condition_waiting", "condition_met"]
    run_id: int
    sequence_no: int
    ts_ms: int
    details: dict[str, Any] | None = None


class CommandResult(BaseModel):
    ok: bool = True
    state: RuntimeState
    message: str = ""


class BootstrapData(BaseModel):
    settings: AppSettings
    state: RuntimeState
    profiles: list[ProfileFile] = Field(default_factory=list)
    profile_status: ProfileDirectoryStatus
