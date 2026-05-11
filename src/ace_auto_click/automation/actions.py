from __future__ import annotations

import time
import random
import ctypes
from dataclasses import dataclass
from typing import Any, Literal, Tuple

import pyautogui
from pynput import keyboard, mouse

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
        btn = mouse.Button.left
        if "right" in self.button:
            btn = mouse.Button.right
        elif "middle" in self.button:
            btn = mouse.Button.middle

        engine._mouse_ctl.position = self.target_position()
        for _ in range(self.clicks):
            engine._mouse_ctl.click(btn)
        return True


@dataclass
class MoveStep(PointerTargetStep):
    movement_mode: Literal["instant", "smooth"] = "instant"
    movement_duration_ms: int = 0
    movement_smoothness: int = 70
    path_randomness: int = 20
    arc_direction: Literal["auto", "left", "right"] = "auto"

    def _run(self, engine: Any) -> bool:
        if self.movement_mode == "smooth":
            return self._run_smooth(engine)
        engine._mouse_ctl.position = self.target_position()
        return True

    def _run_smooth(self, engine: Any) -> bool:
        start = engine._mouse_ctl.position
        start_x, start_y = (int(start[0]), int(start[1])) if start is not None else (self.x, self.y)
        end_x, end_y = int(self.x), int(self.y)
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        if distance == 0:
            engine._mouse_ctl.position = (end_x, end_y)
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
            engine._mouse_ctl.position = (int(round(x)), int(round(y)))
            if duration_s > 0 and index < step_count:
                target_elapsed = duration_s * linear_t
                while time.perf_counter() - start_time < target_elapsed:
                    if engine._stop_evt.is_set():
                        return False
                    time.sleep(0.005)

        if engine._stop_evt.is_set():
            return False
        engine._mouse_ctl.position = (end_x, end_y)
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

    def _button(self, name: str) -> mouse.Button:
        if "right" in name:
            return mouse.Button.right
        if "middle" in name:
            return mouse.Button.middle
        return mouse.Button.left

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
        if getattr(engine, "use_sendinput_mouse", False) and self._run_with_sendinput(engine, start_x, start_y, end_x, end_y, held_buttons, duration_s, step_count, acceleration):
            return True
        return self._run_with_pynput_fallback(engine, start_x, start_y, end_x, end_y, held_buttons, duration_s, step_count, acceleration)

    def _run_with_pynput_fallback(self, engine: Any, start_x: int, start_y: int, end_x: float, end_y: float, held_buttons: list[mouse.Button], duration_s: float, step_count: int, acceleration: float) -> bool:
        engine._mouse_ctl.position = (start_x, start_y)
        try:
            for btn in held_buttons:
                engine._mouse_ctl.press(btn)
            if not self._sleep_with_stop(engine, max(0, self.hold_delay_ms) / 1000.0):
                return False
            start_time = time.perf_counter()
            for index in range(1, step_count + 1):
                if engine._stop_evt.is_set():
                    return False
                elapsed_ratio = index / step_count
                ratio = elapsed_ratio ** acceleration
                engine._mouse_ctl.position = (
                    int(round(start_x + ((end_x - start_x) * ratio))),
                    int(round(start_y + ((end_y - start_y) * ratio))),
                )
                if duration_s > 0 and index < step_count:
                    target_elapsed = duration_s * elapsed_ratio
                    while time.perf_counter() - start_time < target_elapsed:
                        if engine._stop_evt.is_set():
                            return False
                        time.sleep(0.005)
            return self._sleep_with_stop(engine, max(0, self.release_delay_ms) / 1000.0)
        finally:
            for btn in reversed(held_buttons):
                engine._mouse_ctl.release(btn)

    def _run_with_sendinput(self, engine: Any, start_x: int, start_y: int, end_x: float, end_y: float, held_buttons: list[mouse.Button], duration_s: float, step_count: int, acceleration: float) -> bool:
        if "Windows" not in __import__("platform").system():
            return False
        if not hasattr(ctypes, "windll") or not hasattr(ctypes.windll, "user32"):
            return False
        user32 = ctypes.windll.user32
        left_down, left_up = 0x0002, 0x0004
        right_down, right_up = 0x0008, 0x0010
        middle_down, middle_up = 0x0020, 0x0040
        move_flag, absolute_flag = 0x0001, 0x8000
        btn_map = {
            mouse.Button.left: (left_down, left_up),
            mouse.Button.right: (right_down, right_up),
            mouse.Button.middle: (middle_down, middle_up),
        }
        screen_w = max(1, int(user32.GetSystemMetrics(0)) - 1)
        screen_h = max(1, int(user32.GetSystemMetrics(1)) - 1)

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.c_ulonglong)]
        class INPUT_UNION(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT)]
        class INPUT(ctypes.Structure):
            _fields_ = [("type", ctypes.c_ulong), ("union", INPUT_UNION)]

        def send(flags: int, x: int | None = None, y: int | None = None) -> None:
            if x is None or y is None:
                dx = dy = 0
            else:
                dx = int(round((max(0, min(screen_w, x)) * 65535) / screen_w))
                dy = int(round((max(0, min(screen_h, y)) * 65535) / screen_h))
                flags |= absolute_flag
            payload = INPUT(0, INPUT_UNION(MOUSEINPUT(dx, dy, 0, flags, 0, 0)))
            user32.SendInput(1, ctypes.byref(payload), ctypes.sizeof(INPUT))

        pressed: list[mouse.Button] = []
        try:
            send(move_flag, start_x, start_y)
            for btn in held_buttons:
                down_flags = btn_map.get(btn)
                if down_flags is None:
                    continue
                send(down_flags[0])
                pressed.append(btn)
                if not self._sleep_with_stop(engine, max(0, self.hold_delay_ms) / 1000.0):
                    return False
            start_time = time.perf_counter()
            for index in range(1, step_count + 1):
                if engine._stop_evt.is_set():
                    return False
                elapsed_ratio = index / step_count
                ratio = elapsed_ratio ** acceleration
                send(move_flag, int(round(start_x + ((end_x - start_x) * ratio))), int(round(start_y + ((end_y - start_y) * ratio))))
                if duration_s > 0 and index < step_count:
                    target_elapsed = duration_s * elapsed_ratio
                    while time.perf_counter() - start_time < target_elapsed:
                        if engine._stop_evt.is_set():
                            return False
                        time.sleep(0.005)
            if not self._sleep_with_stop(engine, max(0, self.release_delay_ms) / 1000.0):
                return False
            for btn in reversed(pressed):
                up_flags = btn_map.get(btn)
                if up_flags is not None:
                    send(up_flags[1])
            return True
        except Exception:
            return False


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
        "wait_until_match"  # "wait_until_match", "wait_until_mismatch", "stop_if_mismatch", "skip_if_mismatch"
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
        side_buttons_supported = bool(getattr(engine, "side_buttons_supported", hasattr(mouse.Button, "x1") and hasattr(mouse.Button, "x2")))
        if not side_buttons_supported:
            raise RuntimeError("Side mouse buttons are not supported on this runtime.")
        button = getattr(mouse.Button, button_attr, None)
        if button is None:
            raise RuntimeError(f"Mouse button mapping '{button_attr}' is unavailable.")
        return button

    def _parse_combo(self) -> tuple[list[keyboard.Key], str | keyboard.Key]:
        return parse_keybind_text(self.key or "")

    def _key_name(self, value: Any) -> str:
        return str(value).replace("Key.", "").lower()

    def _press_escape_key(self, operations: list[str]) -> None:
        operations.append("press escape")
        pyautogui.press("esc")

    def _run_with_mods(self, engine: Any, mods: list[keyboard.Key], action: Any, operations: list[str]) -> bool:
        for mod in mods:
            engine._kb_ctl.press(mod)
            operations.append(f"press {self._key_name(mod)}")
        try:
            action()
            return True
        finally:
            for mod in reversed(mods):
                engine._kb_ctl.release(mod)
                operations.append(f"release {self._key_name(mod)}")

    def _tap_key(self, engine: Any, key: str | keyboard.Key, operations: list[str]) -> None:
        if key == keyboard.Key.esc:
            self._press_escape_key(operations)
            return
        tap = getattr(engine._kb_ctl, "tap", None)
        if callable(tap):
            operations.append(f"tap {self._key_name(key)}")
            tap(key)
            return
        operations.append(f"press {self._key_name(key)}")
        engine._kb_ctl.press(key)
        operations.append(f"release {self._key_name(key)}")
        engine._kb_ctl.release(key)

    def _run(self, engine: Any) -> bool:
        mods, base = self._parse_combo()
        mouse_button = self._mouse_button(engine)
        operations: list[str] = []
        details = {
            "configured_combo": self.key or "",
            "parsed_modifiers": [self._key_name(mod) for mod in mods],
            "parsed_base": self._key_name(base),
            "dispatch_path": "keyboard_tap",
            "operations": operations,
        }
        self._execution_details = details
        if mouse_button is not None:
            details["dispatch_path"] = "mouse_side_button"
            details["parsed_base"] = str(mouse_button).replace("Button.", "").lower()
            return self._run_with_mods(engine, mods, lambda: (operations.append(f"click {details['parsed_base']}"), engine._mouse_ctl.click(mouse_button)), operations)

        return self._run_with_mods(engine, mods, lambda: self._tap_key(engine, base, operations), operations)

    def _validate(self, engine: Any) -> None:
        self._mouse_button(engine)


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
        side_buttons_supported = bool(getattr(engine, "side_buttons_supported", hasattr(mouse.Button, "x1") and hasattr(mouse.Button, "x2")))
        if not side_buttons_supported:
            raise RuntimeError("Side mouse buttons are not supported on this runtime.")
        button = getattr(mouse.Button, button_attr, None)
        if button is None:
            raise RuntimeError(f"Mouse button mapping '{button_attr}' is unavailable.")
        return button

    def _parse_combo(self) -> tuple[list[keyboard.Key], str | keyboard.Key]:
        return parse_keybind_text(self.key or "")

    def _run(self, engine: Any) -> bool:
        mods, resolved = self._parse_combo()
        mouse_button = self._mouse_button(engine)
        delay_s = max(0, int(self.hold_ms)) / 1000.0
        operations: list[str] = []
        details = {
            "configured_combo": self.key or "",
            "parsed_modifiers": [str(mod).replace("Key.", "").lower() for mod in mods],
            "parsed_base": str(resolved).replace("Key.", "").lower(),
            "dispatch_path": "keyboard_hold",
            "hold_ms": int(self.hold_ms),
            "operations": operations,
        }
        self._execution_details = details

        if mouse_button is not None:
            details["dispatch_path"] = "mouse_side_button"
            details["parsed_base"] = str(mouse_button).replace("Button.", "").lower()
            for mod in mods:
                engine._kb_ctl.press(mod)
                operations.append(f"press {str(mod).replace('Key.', '').lower()}")
            try:
                operations.append(f"press {details['parsed_base']}")
                engine._mouse_ctl.press(mouse_button)
                start = time.perf_counter()
                while time.perf_counter() - start < delay_s:
                    if engine._stop_evt.is_set():
                        return False
                    time.sleep(0.005)
                return True
            finally:
                engine._mouse_ctl.release(mouse_button)
                operations.append(f"release {details['parsed_base']}")
                for mod in reversed(mods):
                    engine._kb_ctl.release(mod)
                    operations.append(f"release {str(mod).replace('Key.', '').lower()}")

        for mod in mods:
            engine._kb_ctl.press(mod)
            operations.append(f"press {str(mod).replace('Key.', '').lower()}")
        engine._kb_ctl.press(resolved)
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
            engine._kb_ctl.release(resolved)
            operations.append(f"release {str(resolved).replace('Key.', '').lower()}")
            for mod in reversed(mods):
                engine._kb_ctl.release(mod)
                operations.append(f"release {str(mod).replace('Key.', '').lower()}")

    def _validate(self, engine: Any) -> None:
        self._mouse_button(engine)
