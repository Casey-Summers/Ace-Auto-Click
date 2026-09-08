from __future__ import annotations

import time
import random
import math
from dataclasses import dataclass
from typing import Any, Literal, Tuple

from ace_auto_click.automation.pixels import get_pixel_rgb, rgb_close
from ace_auto_click.automation.keybinds import normalize_side_button, parse_keybind_text


@dataclass
class ActionStep:
    id: str
    type: str  # "click", "move", "wait", "pixel_check", "key_tap"
    enabled: bool = True
    repeats: int = 1
    interval_ms: int = 100  # pre-step delay
    randomness_ms: int = 0  # randomness for interval
    _execution_details: dict[str, Any] | None = None

    def _compute_delay_s(self) -> float:
        delay_s = max(0, int(self.interval_ms)) / 1000.0
        if self.randomness_ms > 0:
            delay_s += random.uniform(0, max(0, int(self.randomness_ms)) / 1000.0)
        return max(0.0, delay_s)

    def _sleep_with_stop(self, engine: Any, delay_s: float, chunk_s: float = 0.01) -> bool:
        start = time.perf_counter()
        while time.perf_counter() - start < delay_s:
            if engine._stop_evt.is_set():
                return False
            time.sleep(chunk_s)
        return True

    def execute(self, engine: Any) -> bool:
        """Executes the step. Returns True if execution should continue, False to stop sequence."""
        if not self.enabled:
            return True

        for _ in range(max(1, self.repeats)):
            if engine._stop_evt.is_set():
                return False

            if hasattr(engine, "current_step_state"):
                engine.current_step_state = "waiting"
            if not self._sleep_with_stop(engine, self._compute_delay_s()):
                return False

            try:
                self._validate(engine)
                self._prepare_execution_details(engine)
                if hasattr(engine, "current_step_state"):
                    engine.current_step_state = "running"
                if hasattr(engine, "emit_execution_event"):
                    engine.emit_execution_event(self.id, self.type, "step_execute", self._execution_details)
                if not self._run(engine):
                    self._execution_details = None
                    return False
            except Exception as exc:
                self._report_dispatch_failure(engine, str(exc))
                self._execution_details = None
                return False

            if hasattr(engine, "emit_execution_event"):
                engine.emit_execution_event(self.id, self.type, "step_complete")
            self._execution_details = None

        return True

    def _run(self, engine: Any) -> bool:
        raise NotImplementedError

    def _validate(self, engine: Any) -> None:
        return None

    def _prepare_execution_details(self, engine: Any) -> None:
        return None

    def _report_dispatch_failure(self, engine: Any, message: str) -> None:
        if hasattr(engine, "_on_status"):
            engine._on_status(f"Step {self.id} ({self.type}) failed: {message}")


@dataclass
class PointerTargetStep(ActionStep):
    x: int = 0
    y: int = 0
    random_offset: int = 0

    def target_position(self) -> tuple[int, int]:
        rx, ry = self.x, self.y
        if self.random_offset > 0:
            rx += random.randint(-self.random_offset, self.random_offset)
            ry += random.randint(-self.random_offset, self.random_offset)
        return rx, ry


@dataclass
class ClickStep(PointerTargetStep):
    button: str = "left"
    clicks: int = 1

    def _run(self, engine: Any) -> bool:
        btn = "left"
        if "right" in self.button:
            btn = "right"
        elif "middle" in self.button:
            btn = "middle"

        engine.move_cursor(self.target_position())
        engine.click_mouse(btn, self.clicks)
        return True


@dataclass
class MoveStep(PointerTargetStep):
    movement_mode: Literal["instant", "smooth", "natural"] = "instant"
    movement_duration_ms: int = 0
    movement_smoothness: int = 70
    path_randomness: int = 20
    arc_direction: Literal["auto", "left", "right"] = "auto"
    natural_randomness: int = 35
    natural_overshoot_chance: int = 30
    natural_overshoot_px: int = 14
    natural_overshoot_severity: int = 45
    natural_period_min_px: int = 18
    natural_period_max_px: int = 48
    natural_amplitude_min_px: int = 2
    natural_amplitude_max_px: int = 9
    natural_peak_reversal_chance: int = 28

    def _run(self, engine: Any) -> bool:
        if self.movement_mode == "smooth":
            return self._run_smooth(engine)
        if self.movement_mode == "natural":
            return self._run_natural(engine)
        engine.move_cursor(self.target_position())
        return True

    def _run_smooth(self, engine: Any) -> bool:
        start = engine.cursor_position
        start_x, start_y = (int(start[0]), int(start[1])) if start is not None else (self.x, self.y)
        end_x, end_y = int(self.x), int(self.y)
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        if distance == 0:
            engine.move_cursor((end_x, end_y))
            return True

        duration_ms = int(self.movement_duration_ms)
        if duration_ms <= 0:
            duration_ms = int(max(260, min(900, 220 + (distance * 0.35))))
        duration_s = max(0.0, duration_ms / 1000.0)
        step_count = max(12, min(240, int(duration_s / 0.008) if duration_s > 0 else 12))

        smoothness = max(0.0, min(100.0, float(self.movement_smoothness))) / 100.0
        randomness = max(0.0, min(100.0, float(self.path_randomness))) / 100.0
        direction = (self.arc_direction or "auto").lower()
        direction_sign = -1 if direction == "left" else 1 if direction == "right" else random.choice([-1, 1])
        dx, dy = end_x - start_x, end_y - start_y
        perp_x, perp_y = -dy / distance, dx / distance
        arc_strength = distance * (0.08 + (0.22 * smoothness))
        arc_strength *= 1.0 + random.uniform(-0.35, 0.35) * randomness
        mid_x = start_x + (dx * 0.5)
        mid_y = start_y + (dy * 0.5)
        control_x = mid_x + (perp_x * arc_strength * direction_sign) + (random.uniform(-distance, distance) * 0.03 * randomness)
        control_y = mid_y + (perp_y * arc_strength * direction_sign) + (random.uniform(-distance, distance) * 0.03 * randomness)
        ease_power = 1.0 + (smoothness * 0.7) + (random.uniform(-0.2, 0.2) * randomness)

        start_time = time.perf_counter()
        for index in range(1, step_count + 1):
            if engine._stop_evt.is_set():
                return False
            linear_t = index / step_count
            smooth_t = linear_t * linear_t * (3 - (2 * linear_t))
            t = max(0.0, min(1.0, smooth_t ** ease_power))
            inv_t = 1.0 - t
            x = (inv_t * inv_t * start_x) + (2 * inv_t * t * control_x) + (t * t * end_x)
            y = (inv_t * inv_t * start_y) + (2 * inv_t * t * control_y) + (t * t * end_y)
            engine.move_cursor((int(round(x)), int(round(y))))
            if duration_s > 0 and index < step_count:
                target_elapsed = duration_s * linear_t
                while time.perf_counter() - start_time < target_elapsed:
                    if engine._stop_evt.is_set():
                        return False
                    time.sleep(0.005)

        if engine._stop_evt.is_set():
            return False
        engine.move_cursor((end_x, end_y))
        return True

    def _run_natural(self, engine: Any) -> bool:
        start = engine.cursor_position
        start_x, start_y = (int(start[0]), int(start[1])) if start is not None else (self.x, self.y)
        end_x, end_y = int(self.x), int(self.y)
        dx, dy = end_x - start_x, end_y - start_y
        distance = ((dx * dx) + (dy * dy)) ** 0.5
        if distance == 0:
            engine.move_cursor((end_x, end_y))
            return True

        duration_ms = int(self.movement_duration_ms)
        if duration_ms <= 0:
            duration_ms = int(max(260, min(900, 220 + (distance * 0.35))))
        duration_s = max(0.0, duration_ms / 1000.0)
        step_count = max(12, min(240, int(duration_s / 0.008) if duration_s > 0 else 12))

        randomness = max(0.0, min(100.0, float(self.natural_randomness))) / 100.0
        overshoot_chance = max(0.0, min(100.0, float(self.natural_overshoot_chance))) / 100.0
        overshoot_limit = max(0.0, min(500.0, float(self.natural_overshoot_px)))
        overshoot_severity = max(0.0, min(100.0, float(self.natural_overshoot_severity))) / 100.0
        period_min = max(6.0, min(200.0, float(self.natural_period_min_px)))
        period_max = max(6.0, min(300.0, float(self.natural_period_max_px)))
        if period_max < period_min:
            period_max = period_min
        amp_min = max(0.0, min(60.0, float(self.natural_amplitude_min_px)))
        amp_max = max(0.0, min(80.0, float(self.natural_amplitude_max_px)))
        if amp_max < amp_min:
            amp_max = amp_min
        reversal_chance = max(0.0, min(100.0, float(self.natural_peak_reversal_chance))) / 100.0
        ux, uy = dx / distance, dy / distance
        px, py = -uy, ux

        should_overshoot = random.random() < overshoot_chance and distance >= 12
        overshoot_distance = 0.0
        if should_overshoot:
            base_over = max(2.0, distance * (0.02 + (0.08 * overshoot_severity)))
            overshoot_distance = min(overshoot_limit * (0.65 + (1.35 * overshoot_severity)), base_over + (overshoot_limit * 0.35 * overshoot_severity))

        travel_distance = distance + overshoot_distance

        segment_ends: list[float] = []
        seg_end = 0.0
        while seg_end < travel_distance:
            period = random.uniform(period_min, period_max)
            seg_end += period
            segment_ends.append(min(travel_distance, seg_end))
        if not segment_ends:
            segment_ends = [travel_distance]

        segment_signs: list[float] = []
        current_sign = 1.0 if random.random() >= 0.5 else -1.0
        for idx in range(len(segment_ends)):
            if idx > 0 and random.random() < reversal_chance:
                current_sign *= -1.0
            segment_signs.append(current_sign)
        segment_amps: list[float] = [random.uniform(amp_min, amp_max) for _ in segment_ends]

        def local_y_at(local_x: float) -> float:
            prev_end = 0.0
            for idx, seg_end_x in enumerate(segment_ends):
                if local_x <= seg_end_x or idx == len(segment_ends) - 1:
                    seg_len = max(1e-6, seg_end_x - prev_end)
                    seg_t = max(0.0, min(1.0, (local_x - prev_end) / seg_len))
                    base = math.sin(seg_t * math.pi)  # one hump per segment
                    decay = 1.0 - ((local_x / max(1.0, travel_distance)) ** (0.7 + (0.6 * randomness)))
                    return segment_signs[idx] * segment_amps[idx] * base * max(0.05, decay)
                prev_end = seg_end_x
            return 0.0

        start_time = time.perf_counter()

        for index in range(1, step_count + 1):
            if engine._stop_evt.is_set():
                return False
            linear_t = index / step_count
            ease_exp = 0.88 + (0.18 * randomness)
            progress_t = linear_t ** ease_exp
            local_x = min(travel_distance, max(0.0, travel_distance * progress_t))
            local_y = local_y_at(local_x)
            x = start_x + (ux * local_x) + (px * local_y)
            y = start_y + (uy * local_x) + (py * local_y)
            engine.move_cursor((int(round(x)), int(round(y))))
            if duration_s > 0 and index < step_count:
                target_elapsed = duration_s * linear_t
                while time.perf_counter() - start_time < target_elapsed:
                    if engine._stop_evt.is_set():
                        return False
                    time.sleep(0.005)

        if should_overshoot and overshoot_distance > 0:
            correction_steps = max(5, min(48, int(7 + (overshoot_distance * (1.4 + (1.9 * overshoot_severity))))))
            correction_start = engine.cursor_position
            if correction_start is None:
                correction_start = (
                    int(round(start_x + (ux * travel_distance))),
                    int(round(start_y + (uy * travel_distance))),
                )
            for index in range(1, correction_steps + 1):
                if engine._stop_evt.is_set():
                    return False
                t = index / correction_steps
                eased = t * t * (3 - (2 * t))
                x = correction_start[0] + ((end_x - correction_start[0]) * eased)
                y = correction_start[1] + ((end_y - correction_start[1]) * eased)
                engine.move_cursor((int(round(x)), int(round(y))))
                time.sleep(max(0.002, 0.005 - (0.0015 * overshoot_severity)))

        if engine._stop_evt.is_set():
            return False
        engine.move_cursor((end_x, end_y))
        return True


@dataclass
class DragStep(PointerTargetStep):
    buttons: list[str] | None = None
    direction: str = "right"
    length_px: int = 100
    speed: int = 500
    acceleration: float = 1.6
    hold_delay_ms: int = 60
    release_delay_ms: int = 0
    button_order: list[str] | None = None

    def _button(self, name: str) -> str:
        if "right" in name:
            return "right"
        if "middle" in name:
            return "middle"
        return "left"

    def _run(self, engine: Any) -> bool:
        start_x, start_y = self.target_position()
        length = max(0, int(self.length_px))
        dir_name = (self.direction or "right").lower()
        dx, dy = 1, 0
        if dir_name == "left":
            dx, dy = -1, 0
        elif dir_name == "up":
            dx, dy = 0, -1
        elif dir_name == "down":
            dx, dy = 0, 1
        end_x = start_x + (dx * length)
        end_y = start_y + (dy * length)
        px_per_second = max(50.0, min(5000.0, float(self.speed)))
        duration_s = 0.0 if length == 0 else length / px_per_second
        step_count = max(1, min(240, int(duration_s / 0.006) if duration_s > 0 else 1))
        acceleration = max(0.2, min(5.0, float(self.acceleration)))
        button_names = list(dict.fromkeys(self.button_order or self.buttons or ["left", "right"]))
        held_buttons = [self._button(name) for name in button_names]
        return self._run_with_pynput_fallback(engine, start_x, start_y, end_x, end_y, held_buttons, duration_s, step_count, acceleration)

    def _run_with_pynput_fallback(self, engine: Any, start_x: int, start_y: int, end_x: float, end_y: float, held_buttons: list[str], duration_s: float, step_count: int, acceleration: float) -> bool:
        engine.move_cursor((start_x, start_y))
        try:
            for btn in held_buttons:
                engine.mouse_down(btn)
            if not self._sleep_with_stop(engine, max(0, self.hold_delay_ms) / 1000.0):
                return False
            start_time = time.perf_counter()
            for index in range(1, step_count + 1):
                if engine._stop_evt.is_set():
                    return False
                elapsed_ratio = index / step_count
                ratio = elapsed_ratio ** acceleration
                engine.move_cursor((
                    int(round(start_x + ((end_x - start_x) * ratio))),
                    int(round(start_y + ((end_y - start_y) * ratio))),
                ))
                if duration_s > 0 and index < step_count:
                    target_elapsed = duration_s * elapsed_ratio
                    while time.perf_counter() - start_time < target_elapsed:
                        if engine._stop_evt.is_set():
                            return False
                        time.sleep(0.005)
            return self._sleep_with_stop(engine, max(0, self.release_delay_ms) / 1000.0)
        finally:
            for btn in reversed(held_buttons):
                engine.mouse_up(btn)

@dataclass
class WaitStep(ActionStep):
    ms: int = 1000
    random_ms: int = 0

    def _run(self, engine: Any) -> bool:
        engine.current_step_state = "waiting"
        # Sleep in small chunks to allow interruption
        if not self._sleep_with_stop(engine, max(0, int(self.ms)) / 1000.0 + (random.uniform(0, max(0, int(self.random_ms)) / 1000.0) if self.random_ms > 0 else 0.0)):
            return False
        return True


@dataclass
class PixelCheckStep(ActionStep):
    x: int = 0
    y: int = 0
    expected_rgb: Tuple[int, int, int] = (255, 255, 255)
    tolerance: int = 10
    mode: str = (
        "wait_until_match"  # "wait_until_match", "wait_until_mismatch", "stop_if_mismatch", "skip_if_mismatch", "exit_loop_when_match"
    )

    def _condition_satisfied(self, current: Tuple[int, int, int]) -> bool:
        is_match = rgb_close(current, self.expected_rgb, self.tolerance)
        if self.mode == "wait_until_mismatch":
            return not is_match
        return is_match

    def _wait_until_condition(self, engine: Any) -> bool:
        engine.current_step_state = "waiting"
        waiting_emitted = False
        while not engine._stop_evt.is_set():
            current = get_pixel_rgb(self.x, self.y)
            if self._condition_satisfied(current):
                engine.current_step_state = "running"
                if hasattr(engine, "emit_execution_event"):
                    engine.emit_execution_event(self.id, self.type, "condition_met")
                return True
            engine.current_step_state = "condition_false"
            if not waiting_emitted and hasattr(engine, "emit_execution_event"):
                engine.emit_execution_event(self.id, self.type, "condition_waiting")
                waiting_emitted = True
            if not self._sleep_with_stop(engine, 0.1, 0.1):
                return False
        return False

    def _run(self, engine: Any) -> bool:
        if self.mode in {"wait_until_match", "wait_until_mismatch"}:
            return self._wait_until_condition(engine)

        current = get_pixel_rgb(self.x, self.y)
        is_match = rgb_close(current, self.expected_rgb, self.tolerance)
        engine.current_step_state = "running" if is_match else "condition_false"
        if hasattr(engine, "emit_execution_event"):
            engine.emit_execution_event(self.id, self.type, "condition_met" if is_match else "condition_waiting")

        if self.mode == "stop_if_mismatch" and not is_match:
            return False
        if self.mode == "skip_if_mismatch" and not is_match:
            # This is tricky - how to "skip"?
            # For now, we'll just return True but maybe we need a way to return "skip next N steps"
            return True
        if self.mode == "exit_loop_when_match" and is_match:
            if hasattr(engine, "request_exit_current_loop"):
                engine.request_exit_current_loop()
            return True

        return True


SHIFTED_SYMBOL_BASES: dict[str, str] = {
    "!": "1",
    "@": "2",
    "#": "3",
    "$": "4",
    "%": "5",
    "^": "6",
    "&": "7",
    "*": "8",
    "(": "9",
    ")": "0",
    "_": "-",
    "+": "=",
    "{": "[",
    "}": "]",
    "|": "\\",
    ":": ";",
    '"': "'",
    "<": ",",
    ">": ".",
    "?": "/",
    "~": "`",
}


@dataclass
class KeyTapStep(ActionStep):
    key: str = "space"

    def _mouse_button(self, engine: Any) -> Any | None:
        button_attr = None
        for part in (self.key or "").split("+"):
            button_attr = normalize_side_button(part)
            if button_attr:
                break
        if not button_attr:
            return None
        side_buttons_supported = bool(getattr(engine, "side_buttons_supported", True))
        if not side_buttons_supported:
            raise RuntimeError("Side mouse buttons are not supported on this runtime.")
        return button_attr

    def _parse_combo(self) -> tuple[list[str], str]:
        return parse_keybind_text(self.key or "")

    def _key_name(self, value: Any) -> str:
        return str(value).replace("Key.", "").lower()

    def _press_escape_key(self, engine: Any, operations: list[str]) -> None:
        operations.append("press escape")
        engine.tap_key("esc")

    def _run_with_mods(self, engine: Any, mods: list[str], action: Any, operations: list[str]) -> bool:
        for mod in mods:
            engine.key_down(mod)
            operations.append(f"press {self._key_name(mod)}")
        try:
            action()
            return True
        finally:
            for mod in reversed(mods):
                engine.key_up(mod)
                operations.append(f"release {self._key_name(mod)}")

    def _tap_key(self, engine: Any, key: str, operations: list[str], has_modifiers: bool) -> None:
        if key == "esc":
            self._press_escape_key(engine, operations)
            return
        operations.append(f"tap {self._key_name(key)}")
        engine.tap_key(key)

    def _run(self, engine: Any) -> bool:
        mods, base = self._parse_combo()
        mouse_button = self._mouse_button(engine)
        details = self._execution_details or {
            "configured_combo": self.key or "",
            "parsed_modifiers": [self._key_name(mod) for mod in mods],
            "parsed_base": self._key_name(base),
            "dispatch_path": "keyboard_tap",
            "operations": [],
        }
        operations = details["operations"]
        self._execution_details = details
        if mouse_button is not None:
            details["dispatch_path"] = "mouse_side_button"
            details["parsed_base"] = str(mouse_button).replace("Button.", "").lower()
            return self._run_with_mods(engine, mods, lambda: (operations.append(f"click {details['parsed_base']}"), engine.click_mouse(mouse_button)), operations)

        return self._run_with_mods(engine, mods, lambda: self._tap_key(engine, base, operations, bool(mods)), operations)

    def _validate(self, engine: Any) -> None:
        self._mouse_button(engine)

    def _prepare_execution_details(self, engine: Any) -> None:
        mods, base = self._parse_combo()
        mouse_button = self._mouse_button(engine)
        self._execution_details = {
            "configured_combo": self.key or "",
            "parsed_modifiers": [self._key_name(mod) for mod in mods],
            "parsed_base": str(mouse_button).replace("Button.", "").lower() if mouse_button is not None else self._key_name(base),
            "dispatch_path": "mouse_side_button" if mouse_button is not None else "keyboard_tap",
            "operations": [],
        }


@dataclass
class KeyHoldStep(ActionStep):
    key: str = "space"
    hold_ms: int = 300

    def _mouse_button(self, engine: Any) -> Any | None:
        button_attr = None
        for part in (self.key or "").split("+"):
            button_attr = normalize_side_button(part)
            if button_attr:
                break
        if not button_attr:
            return None
        side_buttons_supported = bool(getattr(engine, "side_buttons_supported", True))
        if not side_buttons_supported:
            raise RuntimeError("Side mouse buttons are not supported on this runtime.")
        return button_attr

    def _parse_combo(self) -> tuple[list[str], str]:
        return parse_keybind_text(self.key or "")

    def _run(self, engine: Any) -> bool:
        mods, resolved = self._parse_combo()
        mouse_button = self._mouse_button(engine)
        delay_s = max(0, int(self.hold_ms)) / 1000.0
        details = self._execution_details or {
            "configured_combo": self.key or "",
            "parsed_modifiers": [str(mod).replace("Key.", "").lower() for mod in mods],
            "parsed_base": str(resolved).replace("Key.", "").lower(),
            "dispatch_path": "keyboard_hold",
            "hold_ms": int(self.hold_ms),
            "operations": [],
        }
        operations = details["operations"]
        self._execution_details = details

        if mouse_button is not None:
            details["dispatch_path"] = "mouse_side_button"
            details["parsed_base"] = str(mouse_button).replace("Button.", "").lower()
            for mod in mods:
                engine.key_down(mod)
                operations.append(f"press {str(mod).replace('Key.', '').lower()}")
            try:
                operations.append(f"press {details['parsed_base']}")
                engine.mouse_down(mouse_button)
                start = time.perf_counter()
                while time.perf_counter() - start < delay_s:
                    if engine._stop_evt.is_set():
                        return False
                    time.sleep(0.005)
                return True
            finally:
                engine.mouse_up(mouse_button)
                operations.append(f"release {details['parsed_base']}")
                for mod in reversed(mods):
                    engine.key_up(mod)
                    operations.append(f"release {str(mod).replace('Key.', '').lower()}")

        for mod in mods:
            engine.key_down(mod)
            operations.append(f"press {str(mod).replace('Key.', '').lower()}")
        engine.key_down(resolved)
        operations.append(f"press {str(resolved).replace('Key.', '').lower()}")
        if hasattr(engine, "_register_held_key"):
            engine._register_held_key(resolved)
            for mod in mods:
                engine._register_held_key(mod)
        try:
            start = time.perf_counter()
            while time.perf_counter() - start < delay_s:
                if engine._stop_evt.is_set():
                    return False
                time.sleep(0.005)
            return True
        finally:
            if hasattr(engine, "_unregister_held_key"):
                engine._unregister_held_key(resolved)
                for mod in mods:
                    engine._unregister_held_key(mod)
            engine.key_up(resolved)
            operations.append(f"release {str(resolved).replace('Key.', '').lower()}")
            for mod in reversed(mods):
                engine.key_up(mod)
                operations.append(f"release {str(mod).replace('Key.', '').lower()}")

    def _validate(self, engine: Any) -> None:
        self._mouse_button(engine)

    def _prepare_execution_details(self, engine: Any) -> None:
        mods, resolved = self._parse_combo()
        mouse_button = self._mouse_button(engine)
        self._execution_details = {
            "configured_combo": self.key or "",
            "parsed_modifiers": [str(mod).replace("Key.", "").lower() for mod in mods],
            "parsed_base": str(mouse_button if mouse_button is not None else resolved).replace("Button.", "").replace("Key.", "").lower(),
            "dispatch_path": "mouse_side_button" if mouse_button is not None else "keyboard_hold",
            "hold_ms": int(self.hold_ms),
            "operations": [],
        }
