from __future__ import annotations

from typing import Any

import pyautogui
from fastapi import HTTPException

from ace_auto_click.api.models import (
    ActionStepModel,
    AppSettings,
    AutomationProfile,
    ClickStepModel,
    DragStepModel,
    KeyTapStepModel,
    LoopEndStepModel,
    LoopStartStepModel,
    MoveStepModel,
    PixelCheckStepModel,
    WaitStepModel,
)
from ace_auto_click.automation.actions import ClickStep, DragStep, KeyTapStep, MoveStep, PixelCheckStep, WaitStep
from ace_auto_click.automation.engine import SequenceTimelineNode


def sequence_for_run(settings: AppSettings) -> tuple[list[ActionStepModel], int]:
    profile = active_profile(settings)
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


def active_profile(settings: AppSettings) -> AutomationProfile | None:
    return next(
        (
            candidate
            for candidate in settings.profiles
            if candidate.id == settings.active_profile_id
        ),
        settings.profiles[0] if settings.profiles else None,
    )


def loop_iterations(step: LoopStartStepModel, infinite_cap: int | None = None) -> int:
    if step.loop_infinite:
        return infinite_cap if infinite_cap is not None else 1000
    return max(1, step.loop_count, step.repeats)


def expand_loop_markers(steps: list[ActionStepModel]) -> list[ActionStepModel]:
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
            body = expand_loop_markers(steps[index + 1 : end_index - 1])
            if step.loop_infinite:
                output.extend(body * 1000)
            else:
                output.extend(body * loop_iterations(step))
            index = end_index
            continue
        if isinstance(step, LoopEndStepModel):
            raise HTTPException(status_code=400, detail=f"Unmatched loop_end for {step.loop_id}")
        output.append(step)
        index += 1
    return output


def compile_sequence_timeline(steps: list[ActionStepModel]) -> list[SequenceTimelineNode]:
    timeline: list[SequenceTimelineNode] = []

    def append_range(items: list[ActionStepModel]) -> None:
        index = 0
        while index < len(items):
            step = items[index]
            if isinstance(step, LoopStartStepModel):
                depth = 1
                end_index = index + 1
                while end_index < len(items) and depth > 0:
                    probe = items[end_index]
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
                body = items[index + 1 : end_index - 1]
                end_step = items[end_index - 1]
                iterations = loop_iterations(step, infinite_cap=1000)
                for iteration in range(iterations):
                    timeline.append(SequenceTimelineNode(step.id, step.type, "loop_enter"))
                    append_range(body)
                    if isinstance(end_step, LoopEndStepModel) and end_step.enabled:
                        timeline.append(SequenceTimelineNode(end_step.id, end_step.type, "loop_repeat" if iteration < iterations - 1 else "loop_exit"))
                index = end_index
                continue
            if isinstance(step, LoopEndStepModel):
                raise HTTPException(status_code=400, detail=f"Unmatched loop_end for {step.loop_id}")
            if step.enabled:
                timeline.append(SequenceTimelineNode(step.id, step.type, "execute", to_action_step(step)))
            index += 1

    append_range(steps)
    return timeline


def to_action_step(step: ActionStepModel) -> ClickStep | MoveStep | DragStep | WaitStep | PixelCheckStep | KeyTapStep:
    data: dict[str, Any] = step.model_dump()
    if isinstance(step, ClickStepModel):
        return ClickStep(**data)
    if isinstance(step, MoveStepModel):
        return MoveStep(**data)
    if isinstance(step, DragStepModel):
        return DragStep(**data)
    if isinstance(step, WaitStepModel):
        return WaitStep(**data)
    if isinstance(step, PixelCheckStepModel):
        return PixelCheckStep(**data)
    if isinstance(step, KeyTapStepModel):
        return KeyTapStep(**data)
    if isinstance(step, (LoopStartStepModel, LoopEndStepModel)):
        raise ValueError("Loop markers must be compiled before execution.")
    raise ValueError(f"Unsupported step type: {step.type}")
