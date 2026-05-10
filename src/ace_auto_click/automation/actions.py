from __future__ import annotations

import time
import random
import ctypes
from dataclasses import dataclass
from typing import Any, Tuple

from pynput import keyboard, mouse

from ace_auto_click.automation.pixels import get_pixel_rgb, rgb_close


@dataclass
class ActionStep:
    id: str
    type: str  # "click", "move", "wait", "pixel_check", "key_tap"
    enabled: bool = True
    repeats: int = 1
    interval_ms: int = 100  # pre-step delay
    randomness_ms: int = 0  # randomness for interval

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
                if hasattr(engine, "current_step_state"):
                    engine.current_step_state = "running"
                if hasattr(engine, "emit_execution_event"):
                    engine.emit_execution_event(self.id, self.type, "step_execute")
                if not self._run(engine):
                    return False
            except Exception as exc:
                self._report_dispatch_failure(engine, str(exc))
                return False

            if hasattr(engine, "emit_execution_event"):
                engine.emit_execution_event(self.id, self.type, "step_complete")

        return True

    def _run(self, engine: Any) -> bool:
        raise NotImplementedError

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
    def _run(self, engine: Any) -> bool:
        engine._mouse_ctl.position = self.target_position()
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
        if self._run_with_sendinput(engine, start_x, start_y, end_x, end_y, held_buttons, duration_s, step_count, acceleration):
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
        "wait_until_match"  # "wait_until_match", "stop_if_mismatch", "skip_if_mismatch"
    )

    def _run(self, engine: Any) -> bool:
        if self.mode == "wait_until_match":
            engine.current_step_state = "waiting"
            waiting_emitted = False
            while not engine._stop_evt.is_set():
                current = get_pixel_rgb(self.x, self.y)
                if rgb_close(current, self.expected_rgb, self.tolerance):
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


@dataclass
class KeyTapStep(ActionStep):
    key: str = "space"

    def _mouse_button(self, engine: Any) -> Any | None:
        normalized = (self.key or "").strip().lower().replace(" ", "")
        button_attr = {"btnm4": "x1", "mouse4": "x1", "button.x1": "x1", "btnm5": "x2", "mouse5": "x2", "button.x2": "x2"}.get(normalized)
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
        parts = [part.strip().lower() for part in (self.key or "").split("+") if part.strip()]
        mod_map: dict[str, keyboard.Key] = {"ctrl": keyboard.Key.ctrl, "shift": keyboard.Key.shift, "alt": keyboard.Key.alt}
        mods: list[keyboard.Key] = []
        base: str | keyboard.Key = "space"
        for part in parts:
            if part in mod_map:
                mods.append(mod_map[part])
            elif part.startswith("key."):
                base = getattr(keyboard.Key, part.split("key.", 1)[1], part)
            else:
                base = part
        return mods, base

    def _run_with_mods(self, engine: Any, mods: list[keyboard.Key], action: Any) -> bool:
        for mod in mods:
            engine._kb_ctl.press(mod)
        try:
            action()
            return True
        finally:
            for mod in reversed(mods):
                engine._kb_ctl.release(mod)

    def _run(self, engine: Any) -> bool:
        mods, base = self._parse_combo()
        mouse_button = self._mouse_button(engine)
        if mouse_button is not None:
            return self._run_with_mods(engine, mods, lambda: engine._mouse_ctl.click(mouse_button))

        return self._run_with_mods(engine, mods, lambda: engine._kb_ctl.tap(base))


@dataclass
class KeyHoldStep(ActionStep):
    key: str = "space"
    hold_ms: int = 300

    def _mouse_button(self, engine: Any) -> Any | None:
        normalized = (self.key or "").strip().lower().replace(" ", "")
        button_attr = {"btnm4": "x1", "mouse4": "x1", "button.x1": "x1", "btnm5": "x2", "mouse5": "x2", "button.x2": "x2"}.get(normalized)
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
        parts = [part.strip().lower() for part in (self.key or "").split("+") if part.strip()]
        mod_map: dict[str, keyboard.Key] = {"ctrl": keyboard.Key.ctrl, "shift": keyboard.Key.shift, "alt": keyboard.Key.alt}
        mods: list[keyboard.Key] = []
        base: str | keyboard.Key = "space"
        for part in parts:
            if part in mod_map:
                mods.append(mod_map[part])
            elif part.startswith("key."):
                base = getattr(keyboard.Key, part.split("key.", 1)[1], part)
            else:
                base = part
        return mods, base

    def _run(self, engine: Any) -> bool:
        mods, resolved = self._parse_combo()
        mouse_button = self._mouse_button(engine)
        delay_s = max(0, int(self.hold_ms)) / 1000.0

        if mouse_button is not None:
            for mod in mods:
                engine._kb_ctl.press(mod)
            try:
                engine._mouse_ctl.press(mouse_button)
                start = time.perf_counter()
                while time.perf_counter() - start < delay_s:
                    if engine._stop_evt.is_set():
                        return False
                    time.sleep(0.005)
                return True
            finally:
                engine._mouse_ctl.release(mouse_button)
                for mod in reversed(mods):
                    engine._kb_ctl.release(mod)

        for mod in mods:
            engine._kb_ctl.press(mod)
        engine._kb_ctl.press(resolved)
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
            for mod in reversed(mods):
                engine._kb_ctl.release(mod)
