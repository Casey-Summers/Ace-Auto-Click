from __future__ import annotations

from typing import Any

import pyautogui
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ace_auto_click.api.models import (
    ActionStepModel,
    AppSettings,
    ClickStepModel,
    CommandResult,
    KeyTapStepModel,
    PixelCheckStepModel,
    PixelSample,
    ProductName,
    RuntimeState,
    SequenceRunRequest,
    SimpleRunRequest,
    WaitStepModel,
)
from ace_auto_click.automation.actions import (
    ClickStep,
    KeyTapStep,
    PixelCheckStep,
    WaitStep,
)
from ace_auto_click.automation.engine import ClickEngine, ClickSettings
from ace_auto_click.automation.pixels import PixelCondition, get_pixel_rgb
from ace_auto_click.automation.recorder import ActionRecorder
from ace_auto_click.storage.settings import load_settings, save_settings


app = FastAPI(title=ProductName, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "http://127.0.0.1:1420"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_status = "Idle"
_last_error: str | None = None


def _set_status(message: str) -> None:
    global _status, _last_error
    _status = message
    if message.startswith("Error:"):
        _last_error = message


engine = ClickEngine(on_status=_set_status)
recorder = ActionRecorder()


def _state() -> RuntimeState:
    return RuntimeState(
        running=engine.is_running(),
        recording=recorder.is_recording(),
        status=_status,
        last_error=_last_error,
    )


def _load_app_settings() -> AppSettings:
    raw = load_settings()
    if "simple" in raw:
        return AppSettings.model_validate(raw)

    # Backward compatibility with the original flat settings file.
    return AppSettings(
        hotkey=raw.get("hotkey", "F8"),
        simple={
            "action_type": raw.get("simple_action_type", "mouse"),
            "action_value": raw.get("simple_action_value", "left"),
            "interval_ms": raw.get("simple_interval", 100),
            "interval_random_ms": raw.get("simple_interval_rnd", 0),
            "x": raw.get("simple_x", 0),
            "y": raw.get("simple_y", 0),
            "position_random_px": raw.get("simple_pos_rnd", 0),
        },
    )


def _to_action_step(step: ActionStepModel) -> ClickStep | WaitStep | PixelCheckStep | KeyTapStep:
    data: dict[str, Any] = step.model_dump()
    if isinstance(step, ClickStepModel):
        return ClickStep(**data)
    if isinstance(step, WaitStepModel):
        return WaitStep(**data)
    if isinstance(step, PixelCheckStepModel):
        return PixelCheckStep(**data)
    if isinstance(step, KeyTapStepModel):
        return KeyTapStep(**data)
    raise ValueError(f"Unsupported step type: {step.type}")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "product": ProductName}


@app.get("/state", response_model=RuntimeState)
def state() -> RuntimeState:
    return _state()


@app.get("/settings", response_model=AppSettings)
def get_settings() -> AppSettings:
    return _load_app_settings()


@app.put("/settings", response_model=AppSettings)
def put_settings(settings: AppSettings) -> AppSettings:
    save_settings(settings.model_dump())
    return settings


@app.post("/run/simple", response_model=CommandResult)
def run_simple(request: SimpleRunRequest) -> CommandResult:
    settings = request.settings
    click_settings = ClickSettings(
        enabled=True,
        x=settings.x,
        y=settings.y,
        interval_ms=settings.interval_ms,
        interval_rnd_ms=settings.interval_random_ms,
        button=settings.action_value if settings.action_type == "mouse" else "left",
        key_to_tap=settings.action_value if settings.action_type == "keyboard" else None,
        random_offset_px=settings.position_random_px,
    )
    engine.start_clicking(click_settings, PixelCondition(False, 0, 0, (0, 0, 0), 0, ""))
    return CommandResult(state=_state(), message="Simple run started.")


@app.post("/run/sequence", response_model=CommandResult)
def run_sequence(request: SequenceRunRequest) -> CommandResult:
    if not request.steps:
        raise HTTPException(status_code=400, detail="Sequence must include at least one step.")
    steps = [_to_action_step(step) for step in request.steps]
    engine.start_sequence(steps, loops=request.loops)
    return CommandResult(state=_state(), message="Sequence run started.")


@app.post("/stop", response_model=CommandResult)
def stop() -> CommandResult:
    engine.stop()
    _set_status("Idle")
    return CommandResult(state=_state(), message="Stopped.")


@app.post("/emergency-stop", response_model=CommandResult)
def emergency_stop() -> CommandResult:
    engine.stop()
    if recorder.is_recording():
        recorder.stop()
    _set_status("Emergency stop")
    return CommandResult(state=_state(), message="Emergency stop triggered.")


@app.get("/mouse-position")
def mouse_position() -> dict[str, int]:
    x, y = pyautogui.position()
    return {"x": int(x), "y": int(y)}


@app.get("/pixel", response_model=PixelSample)
def pixel(x: int, y: int) -> PixelSample:
    return PixelSample(x=x, y=y, rgb=get_pixel_rgb(x, y))


@app.post("/record/start", response_model=CommandResult)
def record_start() -> CommandResult:
    recorder.start()
    _set_status("Recording")
    return CommandResult(state=_state(), message="Recording started.")


@app.post("/record/stop")
def record_stop() -> dict[str, Any]:
    events = recorder.stop()
    _set_status("Idle")
    return {"state": _state().model_dump(), "events": events}


@app.get("/debug/settings-raw")
def debug_settings_raw() -> dict[str, Any]:
    return _load_app_settings().model_dump()


def create_app() -> FastAPI:
    return app
