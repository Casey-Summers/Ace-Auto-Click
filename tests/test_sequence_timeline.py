from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from ace_auto_click.api.models import (
    ClickStepModel,
    DragStepModel,
    KeyHoldStepModel,
    LoopEndStepModel,
    LoopStartStepModel,
    MoveStepModel,
    WaitStepModel,
)
from ace_auto_click.api.sequence_service import compile_sequence_timeline
from ace_auto_click.automation.actions import ActionStep, DragStep, KeyHoldStep, MoveStep, WaitStep


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
        self.current_step_state: str | None = None

    def emit_execution_event(self, step_id: str, step_type: str, phase: str) -> None:
        self.events.append((step_id, phase))


def test_action_completion_event_is_emitted_after_run_finishes() -> None:
    engine = RecordingEngine()
    step = RecordingStep(id="step-1", type="custom", interval_ms=0)

    assert step.execute(engine) is True

    assert step.calls == ["run"]
    assert engine.events == [("step-1", "step_complete")]


def test_wait_completion_event_is_emitted_after_wait_logic() -> None:
    engine = RecordingEngine()
    step = WaitStep(id="wait-1", type="wait", ms=1, interval_ms=0)

    assert step.execute(engine) is True

    assert engine.current_step_state == "waiting"
    assert engine.events == [("wait-1", "step_complete")]


def test_disabled_action_does_not_emit_completion_event() -> None:
    engine = RecordingEngine()
    step = RecordingStep(id="step-1", type="custom", enabled=False, interval_ms=0)

    assert step.execute(engine) is True

    assert step.calls == []
    assert engine.events == []


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


def test_move_step_moves_mouse_without_clicking() -> None:
    engine = RecordingEngine()
    mouse = RecordingMouse()
    engine._mouse_ctl = mouse  # type: ignore[attr-defined]
    step = MoveStep(id="move-1", type="move", x=10, y=20, interval_ms=0)

    assert step.execute(engine) is True

    assert mouse.position == (10, 20)
    assert mouse.clicks == []


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
