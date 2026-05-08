from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from collections import deque
from typing import Any, Callable, Dict, List, Optional

import pyautogui
from pynput import keyboard, mouse
# Optimize pyautogui without disabling the emergency corner failsafe.
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True

from ace_auto_click.automation.actions import ActionStep
from ace_auto_click.automation.pixels import PixelCondition, should_run_clicking

StatusCb = Callable[[str], None]


@dataclass
class ClickSettings:
    enabled: bool
    x: int
    y: int
    interval_ms: int
    interval_rnd_ms: int = 0
    button: str = "left"  # "left", "right", "middle"
    key_to_tap: Optional[str] = None
    random_offset_px: int = 0


@dataclass
class SequenceTimelineNode:
    row_step_id: str
    step_type: str
    phase_kind: str
    action: ActionStep | None = None


class ClickEngine:
    def __init__(self, on_status: Optional[StatusCb] = None) -> None:
        self._on_status = on_status or (lambda _: None)
        self._stop_evt = threading.Event()
        self._active_thread: Optional[threading.Thread] = None

        self._mouse_ctl = mouse.Controller()
        self._kb_ctl = keyboard.Controller()
        self.current_step_id: str | None = None
        self.current_step_state: str | None = None
        self._execution_events: deque[dict[str, Any]] = deque(maxlen=512)
        self._execution_seq = 0
        self._execution_run_id = 0
        self._execution_lock = threading.Lock()

    def emit_execution_event(self, step_id: str, step_type: str, phase: str) -> None:
        with self._execution_lock:
            self._execution_seq += 1
            self._execution_events.append({
                "step_id": step_id,
                "step_type": step_type,
                "phase": phase,
                "run_id": self._execution_run_id,
                "sequence_no": self._execution_seq,
                "ts_ms": int(time.time() * 1000),
            })

    def _begin_execution_run(self) -> int:
        with self._execution_lock:
            self._execution_run_id += 1
            return self._execution_run_id

    def get_execution_events(self, after: int = 0) -> list[dict[str, Any]]:
        with self._execution_lock:
            return [event for event in self._execution_events if int(event["sequence_no"]) > after]

    def is_running(self) -> bool:
        return self._active_thread is not None and self._active_thread.is_alive()

    def stop(self) -> None:
        """Stops the current thread without blocking the UI."""
        self._stop_evt.set()

    def start_clicking(
        self, settings: ClickSettings, pixel_cond: PixelCondition
    ) -> None:
        """Simple Mode: Repeat a single action (click or key) at an interval."""
        if self.is_running():
            return

        def run() -> None:
            self._stop_evt.clear()
            self._on_status("Simple Mode: ON")
            try:
                while not self._stop_evt.is_set():
                    if not should_run_clicking(pixel_cond):
                        time.sleep(0.05)
                        continue

                    if settings.key_to_tap:
                        self._kb_ctl.tap(settings.key_to_tap)
                    else:
                        x, y = settings.x, settings.y
                        ro = max(0, int(settings.random_offset_px))
                        if ro > 0:
                            x += random.randint(-ro, ro)
                            y += random.randint(-ro, ro)

                        btn_str = settings.button.lower().strip()
                        btn = mouse.Button.left
                        if "right" in btn_str:
                            btn = mouse.Button.right
                        elif "middle" in btn_str:
                            btn = mouse.Button.middle

                        self._mouse_ctl.position = (x, y)
                        self._mouse_ctl.click(btn)

                    base_sleep = max(0.0, int(settings.interval_ms)) / 1000.0
                    if settings.interval_rnd_ms > 0:
                        base_sleep += random.uniform(
                            0, settings.interval_rnd_ms / 1000.0
                        )

                    # Sleep in small bursts to allow fast stopping
                    burst_start = time.perf_counter()
                    while time.perf_counter() - burst_start < base_sleep:
                        if self._stop_evt.is_set():
                            break
                        time.sleep(0.01)

            except Exception as e:
                self._on_status(f"Error: {e}")
            finally:
                self._on_status("Simple Mode: OFF")
                self._active_thread = None

        self._active_thread = threading.Thread(target=run, daemon=True)
        self._active_thread.start()

    def start_sequence(self, steps: List[ActionStep], loops: int = 1) -> None:
        """Advanced Mode: Execute a list of steps."""
        if self.is_running():
            return

        def run() -> None:
            self._begin_execution_run()
            self._stop_evt.clear()
            self._on_status("Advanced Mode: ON")
            try:
                loop_count = 0
                while (
                    loops == 0 or loop_count < loops
                ) and not self._stop_evt.is_set():
                    for step in steps:
                        if self._stop_evt.is_set():
                            break
                        self.current_step_id = step.id
                        self.current_step_state = "running"
                        cont = step.execute(self)
                        if not cont:
                            # Step logic requested stop
                            break

                    loop_count += 1
                    if loops == 0:
                        self._on_status(f"Advanced Mode: Running (Loop {loop_count})")
                    else:
                        self._on_status(
                            f"Advanced Mode: Running ({loop_count}/{loops})"
                        )

            except Exception as e:
                self._on_status(f"Error: {e}")
            finally:
                self.current_step_id = None
                self.current_step_state = None
                self._on_status("Advanced Mode: OFF")
                self._active_thread = None

        self._active_thread = threading.Thread(target=run, daemon=True)
        self._active_thread.start()

    def start_sequence_timeline(self, timeline: List[SequenceTimelineNode], loops: int = 1) -> None:
        if self.is_running():
            return

        def run() -> None:
            self._begin_execution_run()
            self._stop_evt.clear()
            self._on_status("Advanced Mode: ON")
            try:
                loop_count = 0
                while (loops == 0 or loop_count < loops) and not self._stop_evt.is_set():
                    for node in timeline:
                        if self._stop_evt.is_set():
                            break
                        self.current_step_id = node.row_step_id
                        self.current_step_state = "waiting" if node.phase_kind == "step_wait" else "running"
                        if node.phase_kind != "execute":
                            self.emit_execution_event(node.row_step_id, node.step_type, node.phase_kind)
                            continue
                        if node.action is None or not node.action.enabled:
                            continue
                        cont = node.action.execute(self)
                        if not cont:
                            break

                    loop_count += 1
                    if loops == 0:
                        self._on_status(f"Advanced Mode: Running (Loop {loop_count})")
                    else:
                        self._on_status(f"Advanced Mode: Running ({loop_count}/{loops})")

            except Exception as e:
                self._on_status(f"Error: {e}")
            finally:
                self.current_step_id = None
                self.current_step_state = None
                self._on_status("Advanced Mode: OFF")
                self._active_thread = None

        self._active_thread = threading.Thread(target=run, daemon=True)
        self._active_thread.start()

    # ---------- Legacy Macro playback (can be refactored into sequence later if needed) ----------

    def macro_play(
        self, events: List[Dict], repeats: int, pixel_cond: PixelCondition
    ) -> None:
        if self.is_running():
            return

        # ... (rest of macro_play logic retained or integrated) ...
        # For brevity in this update, I'll keep the core macro logic but move it to the thread management

        def run() -> None:
            self._on_status("Macro: ON")
            try:
                sorted_events = sorted(events, key=lambda e: float(e.get("dt", 0.0)))
                for rep in range(repeats):
                    if self._stop_evt.is_set():
                        break
                    t0 = time.perf_counter()
                    for ev in sorted_events:
                        if self._stop_evt.is_set():
                            break
                        if not should_run_clicking(pixel_cond):
                            time.sleep(0.02)
                            continue

                        target_dt = float(ev.get("dt", 0.0))
                        while not self._stop_evt.is_set():
                            if (time.perf_counter() - t0) >= target_dt:
                                break
                            time.sleep(0.001)

                        # Execution logic (mouse/kb)
                        self._execute_event(ev)
            finally:
                self._on_status("Macro: OFF")
                self._active_thread = None

        self._active_thread = threading.Thread(target=run, daemon=True)
        self._active_thread.start()

    def _execute_event(self, ev: Dict) -> None:
        et = ev.get("type")
        if et == "mouse_click":
            x, y = int(ev["x"]), int(ev["y"])
            btn = self._parse_button(str(ev.get("button", "Button.left")))
            pressed = bool(ev.get("pressed", True))
            if pressed:
                self._mouse_ctl.position = (x, y)
                self._mouse_ctl.press(btn)
            else:
                self._mouse_ctl.release(btn)
        elif et in ("key_press", "key_release"):
            k = self._parse_key(str(ev.get("key", "")))
            if k:
                if et == "key_press":
                    self._kb_ctl.press(k)
                else:
                    self._kb_ctl.release(k)

    def _parse_button(self, s: str) -> mouse.Button:
        if "right" in s:
            return mouse.Button.right
        if "middle" in s:
            return mouse.Button.middle
        return mouse.Button.left

    def _parse_key(self, s: str):
        if s.startswith("char:") and len(s) >= 6:
            return s[5:]
        if s.startswith("key:"):
            name = s[4:]
            if "Key." in name:
                attr = name.split("Key.", 1)[1].strip()
                return getattr(keyboard.Key, attr, None)
        return None
