from __future__ import annotations

from fastapi.testclient import TestClient

from ace_auto_click.api import routes
from ace_auto_click.api.app import app
from ace_auto_click.api.models import ClickStepModel


client = TestClient(app)


def test_state_route_exposes_runtime_contract() -> None:
    response = client.get("/state")

    assert response.status_code == 200
    assert response.json()["product_name"] == "Ace Auto Click"
    assert "running" in response.json()
    assert "recording" in response.json()
    assert "last_error" in response.json()


def test_runtime_info_exposes_identity_and_input_service() -> None:
    response = client.get("/runtime/info")

    assert response.status_code == 200
    payload = response.json()
    assert payload["instance_id"]
    assert payload["pid"] > 0
    assert payload["dpi_awareness"]
    assert payload["input_broker"]["status"] in {"local", "ready", "starting", "error"}


def test_broker_event_rejects_unauthenticated_requests() -> None:
    response = client.post("/runtime/broker-event", json={"action": "run_toggle"})

    assert response.status_code == 401


def test_sequence_route_rejects_empty_sequence() -> None:
    response = client.post("/run/sequence", json={"steps": [], "loops": 0})

    assert response.status_code == 400


def test_run_toggle_uses_the_same_sequence_compiler(monkeypatch) -> None:
    calls: list[str] = []

    def fake_sequence_for_run(settings):
      calls.append("sequence")
      return [ClickStepModel(id="step-1", x=1, y=2)], 0

    def fake_compile_sequence_timeline(steps):
      calls.append("compile")
      return []

    monkeypatch.setattr(routes, "sequence_for_run", fake_sequence_for_run)
    monkeypatch.setattr(routes, "compile_sequence_timeline", fake_compile_sequence_timeline)

    response = client.post("/run/toggle")

    assert response.status_code == 200
    assert calls == ["sequence", "compile"]


def test_emergency_stop_route_is_available() -> None:
    response = client.post("/emergency-stop")

    assert response.status_code == 200
    assert response.json()["state"]["status"] == "Emergency stop"


def test_profiles_status_route_initializes_directory() -> None:
    response = client.get("/profiles/status")

    assert response.status_code == 200
    assert response.json()["available"] is True
    assert response.json()["path"]
