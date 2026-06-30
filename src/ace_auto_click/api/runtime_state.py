from __future__ import annotations

from ace_auto_click.api.models import RuntimeState
from ace_auto_click.automation.engine import ClickEngine
from ace_auto_click.automation.hotkeys import RuntimeHotkeyManager
from ace_auto_click.automation.recorder import ActionRecorder
from ace_auto_click.runtime.broker_manager import InputBrokerManager

_status = "Idle"
_last_error: str | None = None


def set_status(message: str) -> None:
    global _status, _last_error
    _status = message
    if message.startswith("Error:"):
        _last_error = message


engine = ClickEngine(on_status=set_status)
recorder = ActionRecorder()


def state() -> RuntimeState:
    return RuntimeState(
        running=engine.is_running(),
        recording=recorder.is_recording(),
        status=_status,
        last_error=_last_error,
        current_step_id=engine.current_step_id,
        current_step_state=engine.current_step_state,
    )


def trigger_emergency_stop() -> RuntimeState:
    engine.stop()
    if recorder.is_recording():
        recorder.stop()
    set_status("Emergency stop")
    return state()


hotkeys = RuntimeHotkeyManager(
    on_emergency_stop=trigger_emergency_stop,
    on_run_toggle=lambda: state(),
)
input_broker = InputBrokerManager(engine, hotkeys)
