from __future__ import annotations

from typing import Any
import threading

import pyautogui
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ace_auto_click.api.models import (
    ActionStepModel,
    AppSettings,
    AutomationProfile,
    ClickStepModel,
    CommandResult,
    KeyTapStepModel,
    PixelCheckStepModel,
    LoopStartStepModel,
    LoopEndStepModel,
    PixelSample,
    ProfileDirectoryStatus,
    ProfileFile,
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
from ace_auto_click.automation.hotkeys import RuntimeHotkeyManager
from ace_auto_click.automation.pixels import PixelCondition, get_pixel_rgb
from pynput import mouse
from ace_auto_click.automation.recorder import ActionRecorder
from ace_auto_click.storage.profiles import (
    ensure_profiles_dir,
    list_profile_files,
    load_profile_export,
    open_profiles_folder,
    profile_directory_status,
    save_profile_export,
)
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


def _trigger_emergency_stop() -> RuntimeState:
    engine.stop()
    if recorder.is_recording():
        recorder.stop()
    _set_status("Emergency stop")
    return _state()


def _sequence_for_run(settings: AppSettings) -> tuple[list[ActionStepModel], int]:
    profile = next(
        (
            candidate
            for candidate in settings.profiles
            if candidate.id == settings.active_profile_id
        ),
        settings.profiles[0] if settings.profiles else None,
    )
    if profile is None:
        return [], 0
    if settings.mode == "advanced":
        loops = 0 if profile.loops_infinite else max(1, profile.loops_count or 1)
        return profile.steps, loops
    normal = profile.normal
    x, y = pyautogui.position() if normal.use_current_mouse else (0, 0)
    return [
        ClickStepModel(
            id="normal-click",
            interval_ms=normal.interval_ms,
            randomness_ms=normal.interval_random_ms,
            x=int(x),
            y=int(y),
            button=normal.button,
            clicks=2 if normal.double_click else normal.clicks_per_cycle,
            random_offset=normal.position_random_px,
        )
    ], (0 if profile.loops_infinite else max(1, profile.loops_count or 1))


def _expand_loop_markers(steps: list[ActionStepModel]) -> list[ActionStepModel]:
    output: list[ActionStepModel] = []
    index = 0
    while index < len(steps):
        step = steps[index]
        if isinstance(step, LoopStartStepModel):
            depth = 1
            end_index = index + 1
            while end_index < len(steps) and depth > 0:
                probe = steps[end_index]
                if isinstance(probe, LoopStartStepModel) and probe.loop_id == step.loop_id:
                    depth += 1
                elif isinstance(probe, LoopEndStepModel) and probe.loop_id == step.loop_id:
                    depth -= 1
                end_index += 1
            if depth != 0:
                raise HTTPException(status_code=400, detail=f"Unmatched loop_start for {step.loop_id}")
            if not step.enabled:
                index = end_index
                continue
            body = _expand_loop_markers(steps[index + 1 : end_index - 1])
            if step.loop_infinite:
                output.extend(body * 1000)
            else:
                output.extend(body * max(1, step.loop_count))
            index = end_index
            continue
        if isinstance(step, LoopEndStepModel):
            raise HTTPException(status_code=400, detail=f"Unmatched loop_end for {step.loop_id}")
        output.append(step)
        index += 1
    return output


def _trigger_run_toggle() -> RuntimeState:
    if engine.is_running():
        engine.stop()
        _set_status("Idle")
        return _state()
    settings = _load_app_settings()
    steps, loops = _sequence_for_run(settings)
    if not steps:
        _set_status("Error: no active profile sequence")
        return _state()
    engine.start_sequence([_to_action_step(step) for step in steps], loops=loops)
    return _state()


hotkeys = RuntimeHotkeyManager(
    on_emergency_stop=_trigger_emergency_stop,
    on_run_toggle=_trigger_run_toggle,
)


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
        settings = AppSettings.model_validate(raw)
        return _with_default_profile(settings)

    # Backward compatibility with the original flat settings file.
    return _with_default_profile(AppSettings(
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


def _with_default_profile(settings: AppSettings) -> AppSettings:
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
    if isinstance(step, (LoopStartStepModel, LoopEndStepModel)):
        raise ValueError("Loop markers must be compiled before execution.")
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
    _bind_runtime_hotkeys(settings)
    return settings


def _bind_runtime_hotkeys(settings: AppSettings | None = None) -> None:
    try:
        next_settings = settings or _load_app_settings()
        hotkeys.bind(next_settings.emergency_stop_hotkey, next_settings.run_toggle_hotkey)
    except Exception as exc:
        _set_status(f"Error: global hotkeys unavailable ({exc})")


@app.on_event("startup")
def startup() -> None:
    ensure_profiles_dir()
    _bind_runtime_hotkeys()


@app.on_event("shutdown")
def shutdown() -> None:
    hotkeys.stop()


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
    compiled = _expand_loop_markers(request.steps)
    steps = [_to_action_step(step) for step in compiled]
    loops = 0 if request.loops_infinite else max(1, request.loops_count)
    engine.start_sequence(steps, loops=loops)
    return CommandResult(state=_state(), message="Sequence run started.")


@app.post("/run/toggle", response_model=CommandResult)
def run_toggle() -> CommandResult:
    return CommandResult(state=_trigger_run_toggle(), message="Run toggle handled.")


@app.post("/stop", response_model=CommandResult)
def stop() -> CommandResult:
    engine.stop()
    _set_status("Idle")
    return CommandResult(state=_state(), message="Stopped.")


@app.post("/emergency-stop", response_model=CommandResult)
def emergency_stop() -> CommandResult:
    return CommandResult(state=_trigger_emergency_stop(), message="Emergency stop triggered.")


@app.get("/profiles", response_model=list[ProfileFile])
def profiles() -> list[ProfileFile]:
    return [ProfileFile.model_validate(item) for item in list_profile_files()]


@app.get("/profiles/status", response_model=ProfileDirectoryStatus)
def profiles_status() -> ProfileDirectoryStatus:
    return ProfileDirectoryStatus.model_validate(profile_directory_status())


@app.post("/profiles/save", response_model=ProfileFile)
def save_profile(settings: AppSettings) -> ProfileFile:
    profile = next(
        (
            candidate
            for candidate in settings.profiles
            if candidate.id == settings.active_profile_id
        ),
        None,
    )
    if profile is None:
        raise HTTPException(status_code=400, detail="Active profile was not found.")
    save_settings(settings.model_dump())
    _bind_runtime_hotkeys(settings)
    return ProfileFile.model_validate(save_profile_export(settings, profile))


@app.post("/profiles/load/{file_name}", response_model=AppSettings)
def load_profile(file_name: str) -> AppSettings:
    try:
        profile_export = load_profile_export(file_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    settings = _load_app_settings()
    imported_profile = profile_export.profile
    profiles = [
        profile
        for profile in settings.profiles
        if profile.id != imported_profile.id
    ]
    profiles.append(imported_profile)
    settings.profiles = profiles
    settings.active_profile_id = imported_profile.id
    for key, value in profile_export.app_settings.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    try:
        settings = AppSettings.model_validate(settings.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    save_settings(settings.model_dump())
    _bind_runtime_hotkeys(settings)
    return settings


@app.post("/profiles/open-folder")
def open_profile_folder() -> dict[str, str]:
    try:
        open_profiles_folder()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"message": "Profiles folder opened."}


@app.get("/mouse-position")
def mouse_position() -> dict[str, int]:
    x, y = pyautogui.position()
    return {"x": int(x), "y": int(y)}


@app.post("/mouse-position/next-click")
def next_click_position() -> dict[str, int]:
    clicked: dict[str, int] = {}
    ready = threading.Event()

    def on_click(x: int, y: int, _button: object, pressed: bool) -> bool | None:
        if pressed:
            clicked["x"] = int(x)
            clicked["y"] = int(y)
            ready.set()
            return False
        return None

    listener = mouse.Listener(on_click=on_click)
    listener.start()
    if not ready.wait(timeout=30):
        listener.stop()
        raise HTTPException(status_code=408, detail="Timed out waiting for click location.")
    listener.join(timeout=1)
    return clicked


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
