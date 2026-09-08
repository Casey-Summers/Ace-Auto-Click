from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException
from ace_auto_click.automation.input_driver import current_cursor_position

from ace_auto_click.api.models import (
    ActionStepModel,
    AppSettings,
    AutomationProfile,
    ClickStepModel,
    DragStepModel,
    KeyTapStepModel,
    KeyHoldStepModel,
    LoopEndStepModel,
    LoopStartStepModel,
    MoveStepModel,
    PixelCheckStepModel,
    WaitStepModel,
)
from ace_auto_click.automation.actions import ClickStep, DragStep, KeyHoldStep, KeyTapStep, MoveStep, PixelCheckStep, WaitStep
from ace_auto_click.automation.engine import SequenceTimelineNode
from ace_auto_click.automation.target_runtime import TargetRuntime


def sequence_for_run(settings: AppSettings) -> tuple[list[ActionStepModel], int]:
    profile = active_profile(settings)
    if profile is None:
        return [], 0
    if settings.mode == "advanced":
        loops = 0 if profile.loops_infinite else max(1, profile.loops_count or 1)
        return profile.steps, loops
    normal = profile.normal
    point = current_cursor_position() if normal.use_current_mouse else None
    x, y = (point.x, point.y) if point else (0, 0)
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


def prepare_steps_for_target(settings: AppSettings, steps: list[ActionStepModel], runtime: TargetRuntime) -> list[ActionStepModel]:
    profile = active_profile(settings)
    config = profile.target if profile else None
    if not config:
        return steps
    status = runtime.status(settings, restore=True, require_focus=True)
    if not status.get("resolved"):
        raise HTTPException(status_code=409, detail={"code": "target_missing", "message": status.get("warning")})
    if status.get("pixel_checks_stale") and any(isinstance(step, PixelCheckStepModel) for step in steps):
        raise HTTPException(status_code=409, detail={"code": "pixel_checks_stale", "message": status.get("warning")})
    output: list[ActionStepModel] = []
    for step in steps:
        if isinstance(step, (ClickStepModel, MoveStepModel, DragStepModel, PixelCheckStepModel)):
            x, y = runtime.transform(config, (step.x, step.y), status)
            output.append(step.model_copy(update={"x": x, "y": y}))
        else:
            output.append(step)
    return output


def loop_iterations(step: LoopStartStepModel, infinite_cap: int | None = None) -> int:
    if step.loop_infinite:
        return infinite_cap if infinite_cap is not None else 1000
    return max(1, step.loop_count, step.repeats)


def _walk_loop_ranges(
    steps: list[ActionStepModel],
    on_action: Callable[[ActionStepModel], list[Any]],
    on_loop: Callable[[LoopStartStepModel, list[Any], LoopEndStepModel], list[Any]],
) -> list[Any]:
    output: list[Any] = []
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
            body = _walk_loop_ranges(steps[index + 1 : end_index - 1], on_action, on_loop)
            end_step = steps[end_index - 1]
            output.extend(on_loop(step, body, end_step))
            index = end_index
            continue
        if isinstance(step, LoopEndStepModel):
            raise HTTPException(status_code=400, detail=f"Unmatched loop_end for {step.loop_id}")
        output.extend(on_action(step))
        index += 1
    return output


def expand_loop_markers(steps: list[ActionStepModel]) -> list[ActionStepModel]:
    return _walk_loop_ranges(
        steps,
        lambda step: [step],
        lambda step, body, _end_step: body * (1000 if step.loop_infinite else loop_iterations(step)),
    )  # type: ignore[return-value]


def compile_sequence_timeline(steps: list[ActionStepModel]) -> list[SequenceTimelineNode]:
    def compile_action(step: ActionStepModel) -> list[SequenceTimelineNode]:
        if step.enabled is not True:
            return []
        return [SequenceTimelineNode(step.id, step.type, "execute", to_action_step(step))]

    def compile_loop(step: LoopStartStepModel, body: list[Any], end_step: LoopEndStepModel) -> list[SequenceTimelineNode]:
        iterations = loop_iterations(step, infinite_cap=1000)
        output: list[SequenceTimelineNode] = []
        for iteration in range(iterations):
            output.append(SequenceTimelineNode(step.id, step.type, "loop_enter"))
            output.extend(body)
            if end_step.enabled is True:
                output.append(
                    SequenceTimelineNode(
                        end_step.id,
                        end_step.type,
                        "loop_repeat" if iteration < iterations - 1 else "loop_exit",
                    )
                )
        return output

    return _walk_loop_ranges(
        steps,
        compile_action,
        compile_loop,
    )


def to_action_step(step: ActionStepModel) -> ClickStep | MoveStep | DragStep | WaitStep | PixelCheckStep | KeyTapStep | KeyHoldStep:
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
    if isinstance(step, KeyHoldStepModel):
        return KeyHoldStep(**data)
    if isinstance(step, (LoopStartStepModel, LoopEndStepModel)):
        raise ValueError("Loop markers must be compiled before execution.")
    raise ValueError(f"Unsupported step type: {step.type}")
