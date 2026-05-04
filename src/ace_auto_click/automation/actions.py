from __future__ import annotations

import time
import random
from dataclasses import dataclass
from typing import Any, Tuple

from pynput import mouse

from ace_auto_click.automation.pixels import get_pixel_rgb, rgb_close


@dataclass
class ActionStep:
    id: str
    type: str  # "click", "wait", "pixel_check", "key_tap"
    enabled: bool = True
    repeats: int = 1
    interval_ms: int = 100  # post-step delay
    randomness_ms: int = 0  # randomness for interval

    def execute(self, engine: Any) -> bool:
        """Executes the step. Returns True if execution should continue, False to stop sequence."""
        if not self.enabled:
            return True

        for _ in range(max(1, self.repeats)):
            if engine._stop_evt.is_set():
                return False

            if not self._run(engine):
                return False

            # Post-action delay
            delay_s = self.interval_ms / 1000.0
            if self.randomness_ms > 0:
                delay_s += random.uniform(0, self.randomness_ms / 1000.0)

            if delay_s > 0:
                start = time.perf_counter()
                while time.perf_counter() - start < delay_s:
                    if engine._stop_evt.is_set():
                        return False
                    time.sleep(0.01)

        return True

    def _run(self, engine: Any) -> bool:
        raise NotImplementedError


@dataclass
class ClickStep(ActionStep):
    x: int = 0
    y: int = 0
    button: str = "left"
    clicks: int = 1
    random_offset: int = 0

    def _run(self, engine: Any) -> bool:
        rx, ry = self.x, self.y
        if self.random_offset > 0:
            rx += random.randint(-self.random_offset, self.random_offset)
            ry += random.randint(-self.random_offset, self.random_offset)

        btn = mouse.Button.left
        if "right" in self.button:
            btn = mouse.Button.right
        elif "middle" in self.button:
            btn = mouse.Button.middle

        engine._mouse_ctl.position = (rx, ry)
        for _ in range(self.clicks):
            engine._mouse_ctl.click(btn)
        return True


@dataclass
class WaitStep(ActionStep):
    ms: int = 1000
    random_ms: int = 0

    def _run(self, engine: Any) -> bool:
        delay_s = self.ms / 1000.0
        if self.random_ms > 0:
            delay_s += random.uniform(0, self.random_ms / 1000.0)

        # Sleep in small chunks to allow interruption
        start = time.perf_counter()
        while time.perf_counter() - start < delay_s:
            if hasattr(engine, "_stop_evt") and engine._stop_evt.is_set():
                return False
            time.sleep(0.01)
        return True


@dataclass
class PixelCheckStep(ActionStep):
    x: int = 0
    y: int = 0
    expected_rgb: Tuple[int, int, int] = (255, 255, 255)
    tolerance: int = 10
    mode: str = (
        "wait_until_match"  # "wait_until_match", "stop_if_mismatch", "skip_if_mismatch"
    )

    def _run(self, engine: Any) -> bool:
        if self.mode == "wait_until_match":
            while not engine._stop_evt.is_set():
                current = get_pixel_rgb(self.x, self.y)
                if rgb_close(current, self.expected_rgb, self.tolerance):
                    return True
                time.sleep(0.1)
            return False

        current = get_pixel_rgb(self.x, self.y)
        is_match = rgb_close(current, self.expected_rgb, self.tolerance)

        if self.mode == "stop_if_mismatch" and not is_match:
            return False
        if self.mode == "skip_if_mismatch" and not is_match:
            # This is tricky - how to "skip"?
            # For now, we'll just return True but maybe we need a way to return "skip next N steps"
            return True

        return True


@dataclass
class KeyTapStep(ActionStep):
    key: str = "space"

    def _run(self, engine: Any) -> bool:
        engine._kb_ctl.tap(self.key)
        return True
