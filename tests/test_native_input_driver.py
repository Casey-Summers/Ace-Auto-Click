from __future__ import annotations

import pytest

from ace_auto_click.automation.input_driver import InputDispatchError, Win32InputDriver, canonical_button, virtual_key
from ace_auto_click.automation.target_windows import Rect, TargetWindowError, TargetWindowService


class FakeUser32:
    def __init__(self, inserted: int) -> None:
        self.inserted = inserted

    def MapVirtualKeyW(self, vk, mode): return vk
    def SendInput(self, count, payload, size): return self.inserted
    def GetForegroundWindow(self): return 123
    def GetWindowThreadProcessId(self, hwnd, pid): pid._obj.value = 456
    def GetSystemMetrics(self, index):
        return {76: 0, 77: 0, 78: 1920, 79: 1080}.get(index, 0)
    def GetCursorPos(self, point):
        point._obj.x = 10; point._obj.y = 20; return True


def test_key_and_button_mapping_is_dependency_neutral() -> None:
    assert virtual_key("shift") == 0x10
    assert virtual_key("6") == 0x36
    assert virtual_key("f12") == 0x7B
    assert canonical_button("Button.x1") == "x1"


def test_sendinput_partial_result_raises_typed_failure() -> None:
    driver = Win32InputDriver(user32=FakeUser32(inserted=0))
    with pytest.raises(InputDispatchError) as caught:
        driver.tap("a")
    assert caught.value.result.submitted == 2
    assert caught.value.result.inserted == 0
    assert caught.value.result.foreground_pid == 456


def test_target_coordinates_scale_from_reference_client() -> None:
    point = TargetWindowService.transform((960, 540), Rect(0, 0, 1920, 1080), Rect(100, 50, 2560, 1440))
    assert (point.x, point.y) == (1380, 770)
    restored = TargetWindowService.reverse_transform(point, Rect(0, 0, 1920, 1080), Rect(100, 50, 2560, 1440))
    assert (restored.x, restored.y) == (960, 540)


def test_target_transform_rejects_points_outside_client() -> None:
    with pytest.raises(TargetWindowError):
        TargetWindowService.transform((2500, 540), Rect(0, 0, 1920, 1080), Rect(0, 0, 1920, 1080))
