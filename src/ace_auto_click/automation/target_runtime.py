from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ace_auto_click.api.models import AppSettings, TargetWindowConfig
from ace_auto_click.automation.input_driver import Point
from ace_auto_click.automation.target_windows import ElevationRequiredError, Rect, ResolvedTarget, TargetWindowService
from ace_auto_click.runtime.windows import is_process_elevated


def _rect(model: Any) -> Rect:
    return Rect(model.left, model.top, model.width, model.height)


class TargetRuntime:
    def __init__(self, windows: TargetWindowService | None = None) -> None:
        self.windows = windows or TargetWindowService()
        self._last: dict[str, Any] = {"configured": False, "resolved": False}

    def status(self, settings: AppSettings, restore: bool = False, require_focus: bool = False) -> dict[str, Any]:
        profile = next((p for p in settings.profiles if p.id == settings.active_profile_id), settings.profiles[0] if settings.profiles else None)
        config = profile.target if profile else None
        if not config or not config.enabled:
            self._last = {"configured": False, "resolved": False}
            return self._last
        try:
            target = self.windows.resolve(config.executable_path, config.window_title)
            current = self.windows.restore_maximize(target.hwnd) if restore else target.client_rect
            if target.elevated is True and not is_process_elevated():
                message = f"{target.window_title or target.executable_path} requires administrator input access."
                if restore or require_focus:
                    raise ElevationRequiredError(message)
                self._last = {"configured": True, "resolved": True, "hwnd": target.hwnd, "pid": target.pid,
                              "executable_path": target.executable_path, "window_title": target.window_title,
                              "foreground": target.foreground, "elevated": True, "current_client_rect": asdict(current),
                              "warning": message}
                return self._last
            if require_focus:
                self.windows.require_foreground(target.hwnd)
                target = self.windows.describe(target.hwnd)
            reference = _rect(config.reference_client_rect)
            scale_x = current.width / reference.width; scale_y = current.height / reference.height
            stale = abs(scale_x - scale_y) > 0.01 or abs(scale_x - 1.0) > 0.01 or abs(scale_y - 1.0) > 0.01
            self._last = {"configured": True, "resolved": True, "hwnd": target.hwnd, "pid": target.pid,
                          "executable_path": target.executable_path, "window_title": target.window_title,
                          "foreground": target.foreground if not require_focus else True, "elevated": target.elevated,
                          "current_client_rect": asdict(current), "scale_x": scale_x, "scale_y": scale_y,
                          "pixel_checks_stale": stale,
                          "warning": "Target size changed; pixel checks must be resampled." if stale else None}
            return self._last
        except ElevationRequiredError:
            raise
        except Exception as exc:
            self._last = {"configured": True, "resolved": False, "warning": str(exc)}
            return self._last

    def bind_at(self, settings: AppSettings, point: Point) -> TargetWindowConfig:
        target = self.windows.from_point(point)
        rect = self.windows.restore_maximize(target.hwnd)
        return TargetWindowConfig(executable_path=target.executable_path, window_title=target.window_title,
                                  reference_client_rect=asdict(rect))

    def transform(self, config: TargetWindowConfig | None, point: tuple[int, int], current: dict[str, Any] | None = None) -> tuple[int, int]:
        if not config: return point
        state = current or self._last
        raw = state.get("current_client_rect")
        if not raw: raise RuntimeError("Target window is not resolved.")
        result = self.windows.transform(point, _rect(config.reference_client_rect), Rect(**raw))
        return result.x, result.y

    def reverse_transform(self, config: TargetWindowConfig | None, point: tuple[int, int], current: dict[str, Any] | None = None) -> tuple[int, int]:
        if not config: return point
        state = current or self._last
        raw = state.get("current_client_rect")
        if not raw: raise RuntimeError("Target window is not resolved.")
        result = self.windows.reverse_transform(point, _rect(config.reference_client_rect), Rect(**raw))
        return result.x, result.y
