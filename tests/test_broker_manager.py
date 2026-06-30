from __future__ import annotations

from ace_auto_click.runtime import broker_manager


class FakeEngine:
    def __init__(self) -> None:
        self.backends: list[object] = []

    def set_input_backend(self, backend: object) -> None:
        self.backends.append(backend)

    def is_running(self) -> bool:
        return False

    def stop(self) -> None:
        return None


class FakeHotkeys:
    def __init__(self) -> None:
        self.bindings: list[tuple[str, str]] = []
        self.stopped = False

    def bind(self, emergency: str, run_toggle: str) -> None:
        self.bindings.append((emergency, run_toggle))

    def stop(self) -> None:
        self.stopped = True


class FakeBroker:
    def __init__(self, pipe_name: str, token: bytes) -> None:
        self.pipe_name = pipe_name
        self.token = token
        self.bindings: list[tuple[str, str]] = []
        self.closed = False

    def runtime_info(self):
        return {"elevated": True, "pid": 42}

    def bind_hotkeys(self, emergency: str, run_toggle: str) -> None:
        self.bindings.append((emergency, run_toggle))

    def close(self) -> None:
        self.closed = True


def test_manager_switches_to_authenticated_elevated_backend(monkeypatch) -> None:
    engine = FakeEngine()
    hotkeys = FakeHotkeys()
    created: list[FakeBroker] = []

    def create_broker(pipe_name: str, token: bytes) -> FakeBroker:
        instance = FakeBroker(pipe_name, token)
        created.append(instance)
        return instance

    monkeypatch.setattr(broker_manager, "_shell_execute_elevated", lambda executable, parameters: 42)
    monkeypatch.setattr(broker_manager, "BrokerInputBackend", create_broker)
    manager = broker_manager.InputBrokerManager(engine, hotkeys)
    manager.set_hotkeys("F12", "F8")

    status = manager.start_elevated(timeout_s=0.1)

    assert status.connected is True
    assert status.elevated is True
    assert hotkeys.stopped is True
    assert engine.backends == created
    assert created[0].bindings == [("F12", "F8")]


def test_manager_reports_cancelled_uac(monkeypatch) -> None:
    manager = broker_manager.InputBrokerManager(FakeEngine(), FakeHotkeys())
    monkeypatch.setattr(broker_manager, "_shell_execute_elevated", lambda executable, parameters: 5)

    try:
        manager.start_elevated(timeout_s=0.1)
    except RuntimeError as exc:
        assert "cancelled" in str(exc).lower()
    else:
        raise AssertionError("Expected cancelled UAC to fail.")

    assert manager.snapshot().status == "error"
