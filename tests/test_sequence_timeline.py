from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from pynput import keyboard, mouse as pynput_mouse

from ace_auto_click.api.models import (
    ClickStepModel,
    DragStepModel,
    KeyHoldStepModel,
    LoopEndStepModel,
    LoopStartStepModel,
    MoveStepModel,
    PixelCheckStepModel,
    WaitStepModel,
    KeyTapStepModel,
)
from ace_auto_click.automation import actions
from ace_auto_click.api.sequence_service import compile_sequence_timeline
from ace_auto_click.automation.engine import ClickEngine
from ace_auto_click.automation.actions import ActionStep, ClickStep, DragStep, KeyHoldStep, KeyTapStep, MoveStep, PixelCheckStep, WaitStep


def timeline_signature(steps: list[Any]) -> list[tuple[str, str]]:
    return [(node.row_step_id, node.phase_kind) for node in compile_sequence_timeline(steps)]


def test_compile_sequence_timeline_preserves_simple_visible_order() -> None:
    assert timeline_signature([
        ClickStepModel(id="click-1"),
        WaitStepModel(id="wait-1"),
    ]) == [
        ("click-1", "execute"),
        ("wait-1", "execute"),
    ]


def test_compile_sequence_timeline_includes_move_steps() -> None:
    assert timeline_signature([
        MoveStepModel(id="move-1", x=10, y=20),
        ClickStepModel(id="click-1"),
    ]) == [
        ("move-1", "execute"),
        ("click-1", "execute"),
    ]


def test_compile_sequence_timeline_includes_drag_steps() -> None:
    assert timeline_signature([
        DragStepModel(id="drag-1", x=10, y=20),
        ClickStepModel(id="click-1"),
    ]) == [
        ("drag-1", "execute"),
        ("click-1", "execute"),
    ]


def test_compile_sequence_timeline_includes_key_hold_steps() -> None:
    assert timeline_signature([
        KeyHoldStepModel(id="hold-1", key="space", hold_ms=200),
        ClickStepModel(id="click-1"),
    ]) == [
        ("hold-1", "execute"),
        ("click-1", "execute"),
    ]


def test_compile_sequence_timeline_includes_pixel_wait_until_mismatch_steps() -> None:
    assert timeline_signature([
        PixelCheckStepModel(id="pixel-1", mode="wait_until_mismatch"),
        ClickStepModel(id="click-1"),
    ]) == [
        ("pixel-1", "execute"),
        ("click-1", "execute"),
    ]


def test_compile_sequence_timeline_treats_loop_markers_as_ordered_nodes() -> None:
    assert timeline_signature([
        LoopStartStepModel(id="loop-start", loop_id="loop-a", loop_count=1),
        ClickStepModel(id="click-inside"),
        LoopEndStepModel(id="loop-end", loop_id="loop-a"),
        WaitStepModel(id="wait-after"),
    ]) == [
        ("loop-start", "loop_enter"),
        ("click-inside", "execute"),
        ("loop-end", "loop_exit"),
        ("wait-after", "execute"),
    ]


def test_compile_sequence_timeline_preserves_nested_loop_order_and_repeat_exit() -> None:
    assert timeline_signature([
        LoopStartStepModel(id="outer-start", loop_id="outer", loop_count=1),
        ClickStepModel(id="outer-click"),
        LoopStartStepModel(id="inner-start", loop_id="inner", loop_count=2),
        WaitStepModel(id="inner-wait"),
        LoopEndStepModel(id="inner-end", loop_id="inner"),
        LoopEndStepModel(id="outer-end", loop_id="outer"),
    ]) == [
        ("outer-start", "loop_enter"),
        ("outer-click", "execute"),
        ("inner-start", "loop_enter"),
        ("inner-wait", "execute"),
        ("inner-end", "loop_repeat"),
        ("inner-start", "loop_enter"),
        ("inner-wait", "execute"),
        ("inner-end", "loop_exit"),
        ("outer-end", "loop_exit"),
    ]


def test_compile_sequence_timeline_honors_loop_marker_repeats_fallback() -> None:
    assert timeline_signature([
        LoopStartStepModel(id="loop-start", loop_id="loop-a", loop_count=1, repeats=2),
        ClickStepModel(id="click-inside"),
        LoopEndStepModel(id="loop-end", loop_id="loop-a"),
    ]) == [
        ("loop-start", "loop_enter"),
        ("click-inside", "execute"),
        ("loop-end", "loop_repeat"),
        ("loop-start", "loop_enter"),
        ("click-inside", "execute"),
        ("loop-end", "loop_exit"),
    ]


def test_compile_sequence_timeline_skips_disabled_loop_block() -> None:
    assert timeline_signature([
        LoopStartStepModel(id="loop-start", loop_id="loop-a", enabled=False),
        ClickStepModel(id="click-inside"),
        LoopEndStepModel(id="loop-end", loop_id="loop-a"),
        ClickStepModel(id="click-after"),
    ]) == [
        ("click-after", "execute"),
    ]


def test_compile_sequence_timeline_skips_disabled_non_loop_actions() -> None:
    assert timeline_signature([
        ClickStepModel(id="click-off", enabled=False),
        WaitStepModel(id="wait-on", enabled=True),
    ]) == [
        ("wait-on", "execute"),
    ]


@dataclass
class RecordingStep(ActionStep):
    calls: list[str] = field(default_factory=list)

    def _run(self, engine: Any) -> bool:
        self.calls.append("run")
        return True


class RecordingEngine:
    def __init__(self) -> None:
        self._stop_evt = threading.Event()
        self.events: list[tuple[str, str]] = []
        self.event_details: list[dict[str, Any] | None] = []
        self.current_step_state: str | None = None
        self.status_messages: list[str] = []
        self.side_buttons_supported = True

    def emit_execution_event(self, step_id: str, step_type: str, phase: str, details: dict[str, Any] | None = None) -> None:
        self.events.append((step_id, phase))
        self.event_details.append(details)

    def _on_status(self, message: str) -> None:
        self.status_messages.append(message)

    @property
    def cursor_position(self) -> tuple[int, int]:
        return self._mouse_ctl.position

    def move_cursor(self, value: tuple[int, int]) -> None:
        self._mouse_ctl.position = value

    def _button(self, value: object):
        return getattr(pynput_mouse.Button, str(value).replace("Button.", ""), value)

    def _key(self, value: object):
        return getattr(keyboard.Key, str(value).replace("Key.", ""), value)

    def click_mouse(self, button: object, count: int = 1) -> None:
        for _ in range(count): self._mouse_ctl.click(self._button(button))

    def mouse_down(self, button: object) -> None: self._mouse_ctl.press(self._button(button))
    def mouse_up(self, button: object) -> None: self._mouse_ctl.release(self._button(button))
    def key_down(self, key: object) -> None: self._kb_ctl.press(self._key(key))
    def key_up(self, key: object) -> None: self._kb_ctl.release(self._key(key))
    def tap_key(self, key: object) -> None:
        key = self._key(key)
        tap = getattr(self._kb_ctl, "tap", None)
        if tap: tap(key)
        else:
            self._kb_ctl.press(key); self._kb_ctl.release(key)


def test_action_execution_event_is_emitted_before_run_finishes() -> None:
    engine = RecordingEngine()
    step = RecordingStep(id="step-1", type="custom", interval_ms=0)

    assert step.execute(engine) is True

    assert step.calls == ["run"]
    assert engine.events == [("step-1", "step_execute"), ("step-1", "step_complete")]


def test_action_delay_occurs_before_run() -> None:
    engine = RecordingEngine()
    step = RecordingStep(id="step-1", type="custom", interval_ms=50)
    started_at: list[float] = []
    states: list[str | None] = []

    def record_run(self: RecordingStep, engine: Any) -> bool:
        started_at.append(time.perf_counter())
        states.append(engine.current_step_state)
        self.calls.append("run")
        return True

    step._run = record_run.__get__(step, RecordingStep)  # type: ignore[method-assign]
    before = time.perf_counter()

    assert step.execute(engine) is True

    assert step.calls == ["run"]
    assert started_at and (started_at[0] - before) >= 0.045
    assert states == ["running"]
    assert engine.events[0] == ("step-1", "step_execute")


def test_click_step_runs_after_pre_delay() -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    step = ClickStep(id="click-1", type="click", x=10, y=20, interval_ms=50)
    click_times: list[float] = []

    def record_click(self: RecordingMouse, button: Any) -> None:
        click_times.append(time.perf_counter())
        self.clicks.append(button)

    mouse.click = record_click.__get__(mouse, RecordingMouse)  # type: ignore[method-assign]
    before = time.perf_counter()

    assert step.execute(engine) is True

    assert mouse.clicks
    assert click_times and (click_times[0] - before) >= 0.045
    assert engine.current_step_state == "running"


def test_key_tap_step_runs_after_pre_delay() -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    keyboard_ctl = RecordingKeyboard()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    engine._kb_ctl = keyboard_ctl  # type: ignore[attr-defined]
    step = KeyTapStep(id="key-1", type="key_tap", key="space", interval_ms=50)
    tap_times: list[float] = []

    def record_tap(self: RecordingKeyboard, key: Any) -> None:
        tap_times.append(time.perf_counter())
        self.presses.append(key)
        self.releases.append(key)

    keyboard_ctl.tap = record_tap.__get__(keyboard_ctl, RecordingKeyboard)  # type: ignore[method-assign]
    before = time.perf_counter()

    assert step.execute(engine) is True

    assert keyboard_ctl.presses
    assert tap_times and (tap_times[0] - before) >= 0.045
    assert engine.current_step_state == "running"


def test_step_stays_waiting_until_pre_delay_finishes() -> None:
    engine = RecordingEngine()
    step = RecordingStep(id="step-1", type="custom", interval_ms=50)
    observed_states: list[str | None] = []

    original_sleep = step._sleep_with_stop

    def wrapped_sleep(engine: Any, delay_s: float, chunk_s: float = 0.01) -> bool:
        observed_states.append(engine.current_step_state)
        return original_sleep(engine, delay_s, chunk_s)

    step._sleep_with_stop = wrapped_sleep  # type: ignore[method-assign]

    assert step.execute(engine) is True

    assert observed_states and observed_states[0] == "waiting"
    assert engine.events[0] == ("step-1", "step_execute")


def test_pre_action_delay_can_be_interrupted() -> None:
    engine = RecordingEngine()
    step = RecordingStep(id="step-1", type="custom", interval_ms=1000)
    timer = threading.Timer(0.05, engine._stop_evt.set)
    timer.start()
    try:
        assert step.execute(engine) is False
    finally:
        timer.cancel()

    assert step.calls == []


def test_wait_completion_event_is_emitted_after_wait_logic() -> None:
    engine = RecordingEngine()
    step = WaitStep(id="wait-1", type="wait", ms=1, interval_ms=0)

    assert step.execute(engine) is True

    assert engine.current_step_state == "waiting"
    assert engine.events == [("wait-1", "step_execute"), ("wait-1", "step_complete")]


def test_pixel_wait_until_mismatch_continues_when_mismatch_is_found(monkeypatch) -> None:
    engine = RecordingEngine()
    step = PixelCheckStep(
        id="pixel-1",
        type="pixel_check",
        x=10,
        y=20,
        expected_rgb=(255, 255, 255),
        tolerance=0,
        mode="wait_until_mismatch",
        interval_ms=0,
    )
    monkeypatch.setattr(actions, "get_pixel_rgb", lambda x, y: (0, 0, 0))

    assert step.execute(engine) is True

    assert engine.current_step_state == "running"
    assert engine.events == [
        ("pixel-1", "step_execute"),
        ("pixel-1", "condition_met"),
        ("pixel-1", "step_complete"),
    ]


def test_sequence_continues_after_wait_until_mismatch_condition(monkeypatch) -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    pixel = PixelCheckStep(
        id="pixel-1",
        type="pixel_check",
        x=10,
        y=20,
        expected_rgb=(255, 255, 255),
        tolerance=0,
        mode="wait_until_mismatch",
        interval_ms=0,
    )
    click = ClickStep(id="click-1", type="click", x=30, y=40, interval_ms=0)
    monkeypatch.setattr(actions, "get_pixel_rgb", lambda x, y: (0, 0, 0))

    assert pixel.execute(engine) is True
    assert click.execute(engine) is True

    assert mouse.position == (30, 40)
    assert len(mouse.clicks) == 1
    assert engine.events == [
        ("pixel-1", "step_execute"),
        ("pixel-1", "condition_met"),
        ("pixel-1", "step_complete"),
        ("click-1", "step_execute"),
        ("click-1", "step_complete"),
    ]


def test_pixel_exit_loop_when_match_requests_loop_exit(monkeypatch) -> None:
    class LoopAwareEngine(RecordingEngine):
        def __init__(self) -> None:
            super().__init__()
            self.exit_requested = False

        def request_exit_current_loop(self) -> None:
            self.exit_requested = True

    engine = LoopAwareEngine()
    step = PixelCheckStep(
        id="pixel-1",
        type="pixel_check",
        x=10,
        y=20,
        expected_rgb=(255, 255, 255),
        tolerance=0,
        mode="exit_loop_when_match",
        interval_ms=0,
    )
    monkeypatch.setattr(actions, "get_pixel_rgb", lambda x, y: (255, 255, 255))

    assert step.execute(engine) is True
    assert engine.exit_requested is True


def test_pixel_exit_loop_when_match_is_noop_without_loop_context(monkeypatch) -> None:
    engine = RecordingEngine()
    step = PixelCheckStep(
        id="pixel-1",
        type="pixel_check",
        x=10,
        y=20,
        expected_rgb=(255, 255, 255),
        tolerance=0,
        mode="exit_loop_when_match",
        interval_ms=0,
    )
    monkeypatch.setattr(actions, "get_pixel_rgb", lambda x, y: (255, 255, 255))

    assert step.execute(engine) is True


def test_disabled_action_does_not_emit_completion_event() -> None:
    engine = RecordingEngine()
    step = RecordingStep(id="step-1", type="custom", enabled=False, interval_ms=0)

    assert step.execute(engine) is True

    assert step.calls == []
    assert engine.events == []


def test_start_sequence_skips_disabled_steps_before_execution() -> None:
    status_messages: list[str] = []
    engine = ClickEngine(on_status=status_messages.append)
    step = RecordingStep(id="step-1", type="custom", enabled=False, interval_ms=0)

    engine.start_sequence([step], loops=1)
    deadline = time.time() + 5
    while engine.is_running() and time.time() < deadline:
        time.sleep(0.01)

    assert engine.is_running() is False
    assert step.calls == []
    assert engine.get_execution_events() == []


class RecordingMouse:
    def __init__(self) -> None:
        self.clicks: list[Any] = []
        self.presses: list[Any] = []
        self.releases: list[Any] = []
        self.positions: list[tuple[int, int]] = []
        self.position: tuple[int, int] | None = None

    @property
    def position(self) -> tuple[int, int] | None:
        return self._position

    @position.setter
    def position(self, value: tuple[int, int] | None) -> None:
        self._position = value
        if value is not None:
            self.positions.append(value)

    def click(self, button: Any) -> None:
        self.clicks.append(button)

    def press(self, button: Any) -> None:
        self.presses.append(button)

    def release(self, button: Any) -> None:
        self.releases.append(button)


class RecordingKeyboard:
    def __init__(self) -> None:
        self.presses: list[Any] = []
        self.releases: list[Any] = []

    def press(self, key: Any) -> None:
        self.presses.append(key)

    def release(self, key: Any) -> None:
        self.releases.append(key)


class RecordingInputDriver:
    def __init__(self, pressed: list[str]) -> None:
        self.pressed = pressed
        self._cursor = actions.Point(0, 0) if hasattr(actions, "Point") else None

    @property
    def cursor_position(self):
        from ace_auto_click.automation.input_driver import Point
        return self._cursor or Point(0, 0)

    def move(self, point): self._cursor = point
    def mouse_down(self, button): return None
    def mouse_up(self, button): return None
    def click(self, button, count=1): return None
    def key_down(self, key): self.pressed.append(str(key).replace("Key.", ""))
    def key_up(self, key): return None
    def tap(self, key): self.pressed.append(str(key).replace("Key.", ""))
    def release_all(self): return None
    def diagnostics(self): return {"driver": "recording", "checked": True}


def test_move_step_moves_mouse_without_clicking() -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    step = MoveStep(id="move-1", type="move", x=10, y=20, interval_ms=0)

    assert step.execute(engine) is True

    assert mouse.position == (10, 20)
    assert mouse.clicks == []


def test_smooth_move_step_moves_through_arc_and_lands_exactly() -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    mouse.position = (0, 0)
    mouse.positions.clear()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    step = MoveStep(
        id="move-1",
        type="move",
        x=100,
        y=0,
        interval_ms=0,
        movement_mode="smooth",
        movement_duration_ms=1,
        movement_smoothness=100,
        path_randomness=0,
        arc_direction="right",
    )

    assert step.execute(engine) is True

    assert len(mouse.positions) > 2
    assert any(y != 0 for _, y in mouse.positions[:-1])
    assert mouse.position == (100, 0)
    assert mouse.clicks == []


def test_smooth_move_randomness_never_changes_final_target() -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    mouse.position = (5, 5)
    mouse.positions.clear()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    step = MoveStep(
        id="move-1",
        type="move",
        x=40,
        y=30,
        interval_ms=0,
        movement_mode="smooth",
        movement_duration_ms=1,
        path_randomness=100,
    )

    assert step.execute(engine) is True

    assert mouse.position == (40, 30)
    assert mouse.positions[-1] == (40, 30)


def test_smooth_move_stop_event_interrupts_without_forcing_target() -> None:
    engine = RecordingEngine()

    class StoppingMouse(RecordingMouse):
        @RecordingMouse.position.setter
        def position(self, value: tuple[int, int] | None) -> None:
            RecordingMouse.position.fset(self, value)  # type: ignore[attr-defined]
            if value is not None and value != (0, 0):
                engine._stop_evt.set()

    mouse = StoppingMouse()
    mouse.position = (0, 0)
    mouse.positions.clear()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    step = MoveStep(id="move-1", type="move", x=100, y=0, interval_ms=0, movement_mode="smooth", movement_duration_ms=100)

    assert step.execute(engine) is False

    assert mouse.position != (100, 0)


def test_natural_move_step_moves_imperfectly_and_lands_exactly() -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    mouse.position = (0, 0)
    mouse.positions.clear()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    step = MoveStep(
        id="move-natural-1",
        type="move",
        x=120,
        y=0,
        interval_ms=0,
        movement_mode="natural",
        movement_duration_ms=1,
        natural_randomness=80,
        natural_overshoot_chance=100,
        natural_overshoot_px=18,
        natural_overshoot_severity=70,
        natural_period_min_px=10,
        natural_period_max_px=40,
        natural_amplitude_min_px=2,
        natural_amplitude_max_px=12,
        natural_peak_reversal_chance=60,
    )

    assert step.execute(engine) is True

    assert len(mouse.positions) > 3
    assert any(y != 0 for _, y in mouse.positions[:-1])
    assert mouse.positions[-1] == (120, 0)
    assert mouse.position == (120, 0)


def test_natural_move_stop_event_interrupts_without_forcing_target() -> None:
    engine = RecordingEngine()

    class StoppingMouse(RecordingMouse):
        @RecordingMouse.position.setter
        def position(self, value: tuple[int, int] | None) -> None:
            RecordingMouse.position.fset(self, value)  # type: ignore[attr-defined]
            if value is not None and value != (0, 0):
                engine._stop_evt.set()

    mouse = StoppingMouse()
    mouse.position = (0, 0)
    mouse.positions.clear()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    step = MoveStep(id="move-natural-2", type="move", x=140, y=0, interval_ms=0, movement_mode="natural", movement_duration_ms=100)

    assert step.execute(engine) is False
    assert mouse.position != (140, 0)


def test_natural_move_overshoot_severity_changes_peak_reach(monkeypatch) -> None:
    monkeypatch.setattr(actions.random, "random", lambda: 0.0)
    monkeypatch.setattr(actions.random, "uniform", lambda a, b: (a + b) / 2.0)
    engine = RecordingEngine()
    low_mouse = RecordingMouse()
    high_mouse = RecordingMouse()
    low_mouse.position = (0, 0)
    high_mouse.position = (0, 0)
    low_mouse.positions.clear()
    high_mouse.positions.clear()

    low_step = MoveStep(
        id="move-low",
        type="move",
        x=100,
        y=0,
        interval_ms=0,
        movement_mode="natural",
        movement_duration_ms=1,
        natural_overshoot_chance=100,
        natural_overshoot_px=30,
        natural_overshoot_severity=10,
    )
    high_step = MoveStep(
        id="move-high",
        type="move",
        x=100,
        y=0,
        interval_ms=0,
        movement_mode="natural",
        movement_duration_ms=1,
        natural_overshoot_chance=100,
        natural_overshoot_px=30,
        natural_overshoot_severity=95,
    )

    engine._mouse_ctl = low_mouse  # type: ignore[attr-defined]
    assert low_step.execute(engine) is True
    engine._mouse_ctl = high_mouse  # type: ignore[attr-defined]
    assert high_step.execute(engine) is True

    assert max(x for x, _ in high_mouse.positions) > max(x for x, _ in low_mouse.positions)


def test_drag_step_holds_buttons_moves_and_releases() -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    step = DragStep(id="drag-1", type="drag", x=10, y=20, buttons=["left", "right"], direction="right", length_px=30, speed=5000, interval_ms=0)

    assert step.execute(engine) is True

    assert len(mouse.presses) == 2
    assert mouse.positions[0] == (10, 20)
    assert mouse.position == (40, 20)
    assert mouse.releases == list(reversed(mouse.presses))


def test_drag_step_acceleration_changes_motion_curve() -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    step = DragStep(id="drag-1", type="drag", x=0, y=0, buttons=["left"], direction="right", length_px=100, speed=5000, acceleration=2, interval_ms=0)

    assert step.execute(engine) is True

    assert mouse.positions[1][0] < 50
    assert mouse.position == (100, 0)


def test_drag_step_releases_buttons_when_stopped() -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]

    def stop_after_press(button: Any) -> None:
        mouse.presses.append(button)
        engine._stop_evt.set()

    mouse.press = stop_after_press  # type: ignore[method-assign]
    step = DragStep(id="drag-1", type="drag", x=10, y=20, buttons=["left", "right"], direction="right", length_px=30, speed=500, interval_ms=0)

    assert step.execute(engine) is False

    assert len(mouse.presses) == 2
    assert mouse.releases == list(reversed(mouse.presses))


def test_key_hold_step_presses_and_releases_once() -> None:
    engine = RecordingEngine()
    kb = RecordingKeyboard()
    engine._kb_ctl = kb  # type: ignore[attr-defined]
    engine._register_held_key = lambda key: None  # type: ignore[attr-defined]
    engine._unregister_held_key = lambda key: None  # type: ignore[attr-defined]
    step = KeyHoldStep(id="hold-1", type="key_hold", key="space", hold_ms=1, interval_ms=0)

    assert step.execute(engine) is True
    assert len(kb.presses) == 1
    assert len(kb.releases) == 1


def test_key_hold_step_dispatches_captured_escape_as_special_key() -> None:
    engine = RecordingEngine()
    kb = RecordingKeyboard()
    engine._kb_ctl = kb  # type: ignore[attr-defined]
    engine._register_held_key = lambda key: None  # type: ignore[attr-defined]
    engine._unregister_held_key = lambda key: None  # type: ignore[attr-defined]
    step = KeyHoldStep(id="hold-esc", type="key_hold", key="escape", hold_ms=1, interval_ms=0)

    assert step.execute(engine) is True

    assert kb.presses == [keyboard.Key.esc]
    assert kb.releases == [keyboard.Key.esc]
    assert engine.events == [("hold-esc", "step_execute"), ("hold-esc", "step_complete")]


def test_key_tap_step_clicks_side_mouse_button() -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    step = KeyTapStep(id="tap-mouse-4", type="key_tap", key="btnm4", interval_ms=0)

    assert step.execute(engine) is True
    assert mouse.clicks == [pynput_mouse.Button.x1]


def test_key_tap_step_supports_shifted_number_keys() -> None:
    engine = RecordingEngine()
    kb = RecordingKeyboard()
    engine._kb_ctl = kb  # type: ignore[attr-defined]
    step = KeyTapStep(id="tap-1", type="key_tap", key="shift+6", interval_ms=0)

    assert step.execute(engine) is True

    assert kb.presses[0] == keyboard.Key.shift
    assert kb.presses[1] == "6"
    assert kb.releases == ["6", keyboard.Key.shift]
    details = engine.event_details[0]
    assert details is not None
    assert details["dispatch_path"] == "keyboard_tap"
    assert details["configured_combo"] == "shift+6"
    assert details["operations"] == ["press shift", "tap 6", "release shift"]


def test_key_tap_step_supports_ctrl_modifier_combo() -> None:
    engine = RecordingEngine()
    kb = RecordingKeyboard()
    engine._kb_ctl = kb  # type: ignore[attr-defined]
    step = KeyTapStep(id="tap-ctrl-a", type="key_tap", key="ctrl+a", interval_ms=0)

    assert step.execute(engine) is True

    assert kb.presses[0] == keyboard.Key.ctrl
    assert kb.presses[1] == "a"
    assert kb.releases == ["a", keyboard.Key.ctrl]


def test_key_tap_step_dispatches_captured_escape_as_special_key() -> None:
    engine = RecordingEngine()
    kb = RecordingKeyboard()
    engine._kb_ctl = kb  # type: ignore[attr-defined]
    step = KeyTapStep(id="tap-esc", type="key_tap", key="esc", interval_ms=0)
    assert step.execute(engine) is True
    assert kb.presses == [keyboard.Key.esc]
    assert kb.releases == [keyboard.Key.esc]
    assert engine.events == [("tap-esc", "step_execute"), ("tap-esc", "step_complete")]


def test_sequence_continues_after_wait_until_mismatch_then_escape_keybind(monkeypatch) -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    kb = RecordingKeyboard()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    engine._kb_ctl = kb  # type: ignore[attr-defined]
    pixel = PixelCheckStep(
        id="pixel-1",
        type="pixel_check",
        x=10,
        y=20,
        expected_rgb=(255, 255, 255),
        tolerance=0,
        mode="wait_until_mismatch",
        interval_ms=0,
    )
    key = KeyTapStep(id="tap-esc", type="key_tap", key="esc", interval_ms=0)
    click = ClickStep(id="click-1", type="click", x=30, y=40, interval_ms=0)
    monkeypatch.setattr(actions, "get_pixel_rgb", lambda x, y: (0, 0, 0))

    assert pixel.execute(engine) is True
    assert key.execute(engine) is True
    assert click.execute(engine) is True

    assert kb.presses == [keyboard.Key.esc]
    assert kb.releases == [keyboard.Key.esc]
    assert mouse.position == (30, 40)
    assert len(mouse.clicks) == 1


def test_key_tap_step_normalizes_shifted_symbol_digits() -> None:
    engine = RecordingEngine()
    kb = RecordingKeyboard()
    engine._kb_ctl = kb  # type: ignore[attr-defined]
    step = KeyTapStep(id="tap-1", type="key_tap", key="shift+!", interval_ms=0)

    assert step.execute(engine) is True

    assert kb.presses[0] == keyboard.Key.shift
    assert kb.presses[1] == "1"
    assert kb.releases == ["1", keyboard.Key.shift]


def test_key_tap_step_supports_modded_mouse_buttons() -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    kb = RecordingKeyboard()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    engine._kb_ctl = kb  # type: ignore[attr-defined]
    step = KeyTapStep(id="tap-1", type="key_tap", key="shift+btnm4", interval_ms=0)

    assert step.execute(engine) is True

    assert kb.presses == [keyboard.Key.shift]
    assert mouse.clicks == [pynput_mouse.Button.x1]
    assert kb.releases == [keyboard.Key.shift]
    details = engine.event_details[0]
    assert details is not None
    assert details["dispatch_path"] == "mouse_side_button"
    assert details["operations"] == ["press shift", "click x1", "release shift"]


def test_key_hold_step_holds_side_mouse_button() -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    step = KeyHoldStep(id="hold-mouse-5", type="key_hold", key="btnm5", hold_ms=1, interval_ms=0)

    assert step.execute(engine) is True
    assert mouse.presses == [pynput_mouse.Button.x2]
    assert mouse.releases == [pynput_mouse.Button.x2]


def test_key_hold_step_supports_shifted_number_keys() -> None:
    engine = RecordingEngine()
    kb = RecordingKeyboard()
    engine._kb_ctl = kb  # type: ignore[attr-defined]
    step = KeyHoldStep(id="hold-1", type="key_hold", key="shift+6", hold_ms=1, interval_ms=0)

    assert step.execute(engine) is True

    assert kb.presses == [keyboard.Key.shift, "6"]
    assert kb.releases == ["6", keyboard.Key.shift]
    details = engine.event_details[0]
    assert details is not None
    assert details["dispatch_path"] == "keyboard_hold"
    assert details["configured_combo"] == "shift+6"
    assert details["operations"] == ["press shift", "press 6", "release 6", "release shift"]


def test_key_hold_step_supports_ctrl_modifier_combo() -> None:
    engine = RecordingEngine()
    kb = RecordingKeyboard()
    engine._kb_ctl = kb  # type: ignore[attr-defined]
    step = KeyHoldStep(id="hold-ctrl-a", type="key_hold", key="ctrl+a", hold_ms=1, interval_ms=0)

    assert step.execute(engine) is True

    assert kb.presses == [keyboard.Key.ctrl, "a"]
    assert kb.releases == ["a", keyboard.Key.ctrl]


def test_key_hold_step_normalizes_shifted_symbol_digits() -> None:
    engine = RecordingEngine()
    kb = RecordingKeyboard()
    engine._kb_ctl = kb  # type: ignore[attr-defined]
    step = KeyHoldStep(id="hold-1", type="key_hold", key="shift+!", hold_ms=1, interval_ms=0)

    assert step.execute(engine) is True

    assert kb.presses == [keyboard.Key.shift, "1"]
    assert kb.releases == ["1", keyboard.Key.shift]


def test_key_hold_step_supports_modded_mouse_buttons() -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    kb = RecordingKeyboard()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    engine._kb_ctl = kb  # type: ignore[attr-defined]
    step = KeyHoldStep(id="hold-1", type="key_hold", key="shift+btnm5", hold_ms=1, interval_ms=0)

    assert step.execute(engine) is True

    assert kb.presses == [keyboard.Key.shift]
    assert mouse.presses == [pynput_mouse.Button.x2]
    assert mouse.releases == [pynput_mouse.Button.x2]
    assert kb.releases == [keyboard.Key.shift]


def test_key_tap_step_fails_without_side_button_support() -> None:
    engine = RecordingEngine()
    engine.side_buttons_supported = False
    mouse = RecordingMouse()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    step = KeyTapStep(id="tap-mouse-4", type="key_tap", key="btnm4", interval_ms=0)

    assert step.execute(engine) is False
    assert mouse.clicks == []
    assert engine.events == []
    assert any("failed" in message.lower() for message in engine.status_messages)


def test_duplicate_key_tap_steps_both_dispatch() -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    first = KeyTapStep(id="tap-1", type="key_tap", key="btnm4", interval_ms=0)
    duplicate = KeyTapStep(id="tap-1-copy", type="key_tap", key="btnm4", interval_ms=0)

    assert first.execute(engine) is True
    assert duplicate.execute(engine) is True
    assert len(mouse.clicks) == 2
    assert engine.events == [
        ("tap-1", "step_execute"),
        ("tap-1", "step_complete"),
        ("tap-1-copy", "step_execute"),
        ("tap-1-copy", "step_complete"),
    ]


def _wait_engine_stopped(engine: ClickEngine, timeout_s: float = 5.0) -> None:
    deadline = time.time() + timeout_s
    while engine.is_running() and time.time() < deadline:
        time.sleep(0.01)
    assert engine.is_running() is False


def test_exit_loop_when_match_skips_blocking_middle_condition_and_continues(monkeypatch) -> None:
    status_messages: list[str] = []
    pressed: list[str] = []
    engine = ClickEngine(on_status=status_messages.append, input_driver=RecordingInputDriver(pressed))
    monkeypatch.setattr(actions, "get_pixel_rgb", lambda x, y: (65, 65, 71))

    steps = [
        LoopStartStepModel(id="loop-start", loop_id="loop-a", loop_count=3),
        PixelCheckStepModel(id="px-exit-a", mode="exit_loop_when_match", x=884, y=857, expected_rgb=(65, 65, 71), tolerance=0),
        PixelCheckStepModel(id="px-block", mode="wait_until_mismatch", x=884, y=857, expected_rgb=(65, 65, 71), tolerance=0),
        PixelCheckStepModel(id="px-exit-b", mode="exit_loop_when_match", x=884, y=857, expected_rgb=(65, 65, 71), tolerance=0),
        KeyTapStepModel(id="tap-inside", key="1"),
        LoopEndStepModel(id="loop-end", loop_id="loop-a"),
        KeyTapStepModel(id="tap-after", key="esc"),
    ]

    engine.start_sequence_timeline(compile_sequence_timeline(steps), loops=1)
    _wait_engine_stopped(engine)
    events = engine.get_execution_events()
    phases_by_step = [(e["step_id"], e["phase"]) for e in events]

    assert ("px-exit-a", "condition_met") in phases_by_step
    assert not any(step_id == "px-block" and phase in {"step_execute", "condition_waiting"} for step_id, phase in phases_by_step)
    assert ("tap-after", "step_execute") in phases_by_step
    assert pressed == ["esc"]


def test_exit_loop_when_match_exits_innermost_loop_only(monkeypatch) -> None:
    pressed: list[str] = []
    engine = ClickEngine(on_status=lambda _: None, input_driver=RecordingInputDriver(pressed))
    monkeypatch.setattr(actions, "get_pixel_rgb", lambda x, y: (65, 65, 71))

    steps = [
        LoopStartStepModel(id="outer-start", loop_id="outer", loop_count=1),
        KeyTapStepModel(id="outer-before", key="a"),
        LoopStartStepModel(id="inner-start", loop_id="inner", loop_count=2),
        PixelCheckStepModel(id="inner-exit", mode="exit_loop_when_match", x=884, y=857, expected_rgb=(65, 65, 71), tolerance=0),
        PixelCheckStepModel(id="inner-block", mode="wait_until_mismatch", x=884, y=857, expected_rgb=(65, 65, 71), tolerance=0),
        LoopEndStepModel(id="inner-end", loop_id="inner"),
        KeyTapStepModel(id="outer-after-inner", key="b"),
        LoopEndStepModel(id="outer-end", loop_id="outer"),
        KeyTapStepModel(id="after-all", key="esc"),
    ]

    engine.start_sequence_timeline(compile_sequence_timeline(steps), loops=1)
    _wait_engine_stopped(engine)
    events = engine.get_execution_events()
    phases_by_step = [(e["step_id"], e["phase"]) for e in events]

    assert ("inner-exit", "condition_met") in phases_by_step
    assert not any(step_id == "inner-block" and phase in {"step_execute", "condition_waiting"} for step_id, phase in phases_by_step)
    assert ("outer-after-inner", "step_execute") in phases_by_step
    assert ("after-all", "step_execute") in phases_by_step
    assert pressed == ["a", "b", "esc"]


def test_exit_loop_when_match_root_level_is_noop_and_continues(monkeypatch) -> None:
    pressed: list[str] = []
    engine = ClickEngine(on_status=lambda _: None, input_driver=RecordingInputDriver(pressed))
    monkeypatch.setattr(actions, "get_pixel_rgb", lambda x, y: (65, 65, 71))

    steps = [
        PixelCheckStepModel(id="px-root-exit", mode="exit_loop_when_match", x=884, y=857, expected_rgb=(65, 65, 71), tolerance=0),
        KeyTapStepModel(id="tap-next", key="esc"),
    ]

    engine.start_sequence_timeline(compile_sequence_timeline(steps), loops=1)
    _wait_engine_stopped(engine)
    events = engine.get_execution_events()
    phases_by_step = [(e["step_id"], e["phase"]) for e in events]

    assert ("px-root-exit", "condition_met") in phases_by_step
    assert ("tap-next", "step_execute") in phases_by_step
    assert pressed == ["esc"]
