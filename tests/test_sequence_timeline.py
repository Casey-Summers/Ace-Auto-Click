from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from ace_auto_click.api.models import (
    ClickStepModel,
    LoopEndStepModel,
    LoopStartStepModel,
    WaitStepModel,
)
from ace_auto_click.api.sequence_service import compile_sequence_timeline
from ace_auto_click.automation.actions import ActionStep, WaitStep


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
