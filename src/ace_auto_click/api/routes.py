from __future__ import annotations

from typing import Any

import pyautogui
from fastapi import APIRouter, HTTPException

from ace_auto_click.api.models import (
    AppSettings,
    CommandResult,
    PixelSample,
    ProductName,
    ExecutionEvent,
    ProfileDirectoryStatus,
    ProfileFile,
    RuntimeState,
    SequenceRunRequest,
    SimpleRunRequest,
)
from ace_auto_click.api.runtime_state import engine, hotkeys, recorder, set_status, state, trigger_emergency_stop
from ace_auto_click.api.sequence_service import active_profile, compile_sequence_timeline, sequence_for_run
from ace_auto_click.api.settings_service import load_app_settings, save_app_settings
from ace_auto_click.automation.engine import ClickSettings
from ace_auto_click.automation import input_capture
from ace_auto_click.automation.pixels import PixelCondition, get_pixel_rgb
from ace_auto_click.storage.profiles import (
    ensure_profiles_dir,
    list_profile_files,
    load_profile_export,
    open_profiles_folder,
    profile_directory_status,
    save_profile_export,
)

router = APIRouter()


def bind_runtime_hotkeys(settings: AppSettings | None = None) -> None:
    try:
        next_settings = settings or load_app_settings()
        hotkeys.bind(next_settings.emergency_stop_hotkey, next_settings.run_toggle_hotkey)
    except Exception as exc:
        set_status(f"Error: global hotkeys unavailable ({exc})")


def trigger_run_toggle() -> RuntimeState:
    if engine.is_running():
        engine.stop()
        set_status("Idle")
        return state()
    settings = load_app_settings()
    steps, loops = sequence_for_run(settings)
    if not steps:
        set_status("Error: no active profile sequence")
        return state()
    engine.start_sequence_timeline(compile_sequence_timeline(steps), loops=loops)
    return state()


hotkeys.set_run_toggle_handler(trigger_run_toggle)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "product": ProductName}


@router.get("/state", response_model=RuntimeState)
def get_state() -> RuntimeState:
    return state()


@router.get("/execution-events", response_model=list[ExecutionEvent])
def execution_events(after: int = 0) -> list[ExecutionEvent]:
    return [ExecutionEvent.model_validate(item) for item in engine.get_execution_events(after)]


@router.get("/settings", response_model=AppSettings)
def get_settings() -> AppSettings:
    return load_app_settings()


@router.put("/settings", response_model=AppSettings)
def put_settings(settings: AppSettings) -> AppSettings:
    save_app_settings(settings)
    bind_runtime_hotkeys(settings)
    return settings


@router.post("/run/simple", response_model=CommandResult)
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
    return CommandResult(state=state(), message="Simple run started.")


@router.post("/run/sequence", response_model=CommandResult)
def run_sequence(request: SequenceRunRequest) -> CommandResult:
    if not request.steps:
        raise HTTPException(status_code=400, detail="Sequence must include at least one step.")
    loops = 0 if request.loops_infinite else max(1, request.loops_count)
    engine.start_sequence_timeline(compile_sequence_timeline(request.steps), loops=loops)
    return CommandResult(state=state(), message="Sequence run started.")


@router.post("/run/toggle", response_model=CommandResult)
def run_toggle() -> CommandResult:
    return CommandResult(state=trigger_run_toggle(), message="Run toggle handled.")


@router.post("/stop", response_model=CommandResult)
def stop() -> CommandResult:
    engine.stop()
    set_status("Idle")
    return CommandResult(state=state(), message="Stopped.")


@router.post("/emergency-stop", response_model=CommandResult)
def emergency_stop() -> CommandResult:
    return CommandResult(state=trigger_emergency_stop(), message="Emergency stop triggered.")


@router.get("/profiles", response_model=list[ProfileFile])
def profiles() -> list[ProfileFile]:
    return [ProfileFile.model_validate(item) for item in list_profile_files()]


@router.get("/profiles/status", response_model=ProfileDirectoryStatus)
def profiles_status() -> ProfileDirectoryStatus:
    return ProfileDirectoryStatus.model_validate(profile_directory_status())


@router.post("/profiles/save", response_model=ProfileFile)
def save_profile(settings: AppSettings) -> ProfileFile:
    profile = active_profile(settings)
    if profile is None:
        raise HTTPException(status_code=400, detail="Active profile was not found.")
    save_app_settings(settings)
    bind_runtime_hotkeys(settings)
    return ProfileFile.model_validate(save_profile_export(settings, profile))


@router.post("/profiles/load/{file_name}", response_model=AppSettings)
def load_profile(file_name: str) -> AppSettings:
    try:
        profile_export = load_profile_export(file_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    settings = load_app_settings()
    imported_profile = profile_export.profile
    settings.profiles = [
        profile
        for profile in settings.profiles
        if profile.id != imported_profile.id
    ]
    settings.profiles.append(imported_profile)
    settings.active_profile_id = imported_profile.id
    for key, value in profile_export.app_settings.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    try:
        settings = AppSettings.model_validate(settings.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    save_app_settings(settings)
    bind_runtime_hotkeys(settings)
    return settings


@router.post("/profiles/open-folder")
def open_profile_folder() -> dict[str, str]:
    try:
        open_profiles_folder()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"message": "Profiles folder opened."}


@router.get("/mouse-position")
def mouse_position() -> dict[str, int]:
    x, y = pyautogui.position()
    return {"x": int(x), "y": int(y)}


@router.post("/mouse-position/next-click")
def next_click_position() -> dict[str, int]:
    try:
        captured = input_capture.capture_next_mouse_click(timeout_s=30, cancel_keys={"esc"})
    except input_capture.InputCaptureTimeoutError as exc:
        raise HTTPException(status_code=408, detail=str(exc)) from exc
    except input_capture.InputCaptureCancelledError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if captured.x is None or captured.y is None:
        raise HTTPException(status_code=500, detail="Mouse capture did not return coordinates.")
    return {"x": captured.x, "y": captured.y}


def _capture_snapshot_payload(snapshot: input_capture.CaptureSessionSnapshot) -> dict[str, Any]:
    payload: dict[str, Any] = {"id": snapshot.id, "status": snapshot.status, "error": snapshot.error}
    if snapshot.result is not None:
        payload["result"] = {
            "kind": snapshot.result.kind,
            "x": snapshot.result.x,
            "y": snapshot.result.y,
            "button": snapshot.result.button,
            "key": snapshot.result.key,
            "cancelled": snapshot.result.cancelled,
        }
    else:
        payload["result"] = None
    return payload


@router.post("/input-capture/mouse-click/start")
def start_mouse_click_capture() -> dict[str, Any]:
    snapshot = input_capture.capture_manager.start_mouse_click(timeout_s=30, cancel_keys={"esc"})
    if snapshot.status == "failed":
        raise HTTPException(status_code=500, detail=snapshot.error or "Mouse capture could not start.")
    return _capture_snapshot_payload(snapshot)


@router.get("/input-capture/{session_id}")
def input_capture_status(session_id: str) -> dict[str, Any]:
    snapshot = input_capture.capture_manager.get(session_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Input capture session was not found.")
    return _capture_snapshot_payload(snapshot)


@router.post("/input-capture/{session_id}/cancel")
def cancel_input_capture(session_id: str) -> dict[str, Any]:
    snapshot = input_capture.capture_manager.cancel(session_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Input capture session was not found.")
    return _capture_snapshot_payload(snapshot)


@router.get("/pixel", response_model=PixelSample)
def pixel(x: int, y: int) -> PixelSample:
    return PixelSample(x=x, y=y, rgb=get_pixel_rgb(x, y))


@router.post("/record/start", response_model=CommandResult)
def record_start() -> CommandResult:
    recorder.start()
    set_status("Recording")
    return CommandResult(state=state(), message="Recording started.")


@router.post("/record/stop")
def record_stop() -> dict[str, Any]:
    events = recorder.stop()
    set_status("Idle")
    return {"state": state().model_dump(), "events": events}


@router.get("/debug/settings-raw")
def debug_settings_raw() -> dict[str, Any]:
    return load_app_settings().model_dump()


def startup() -> None:
    ensure_profiles_dir()
    bind_runtime_hotkeys()


def shutdown() -> None:
    hotkeys.stop()
    input_capture.capture_manager.cancel_pending("Application shutting down.")
