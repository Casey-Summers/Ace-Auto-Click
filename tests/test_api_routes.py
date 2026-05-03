from __future__ import annotations

from fastapi.testclient import TestClient

from ace_auto_click.api.app import app


client = TestClient(app)


def test_state_route_exposes_runtime_contract() -> None:
    response = client.get("/state")

    assert response.status_code == 200
    assert response.json()["product_name"] == "Ace Auto Click"
    assert "running" in response.json()
    assert "recording" in response.json()
    assert "last_error" in response.json()


def test_sequence_route_rejects_empty_sequence() -> None:
    response = client.post("/run/sequence", json={"steps": [], "loops": 0})

    assert response.status_code == 400


def test_emergency_stop_route_is_available() -> None:
    response = client.post("/emergency-stop")

    assert response.status_code == 200
    assert response.json()["state"]["status"] == "Emergency stop"

