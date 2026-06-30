from __future__ import annotations

from ace_auto_click.runtime import service


class FakeProcess:
    def poll(self):
        return None


def test_wait_for_api_accepts_only_the_owned_instance(monkeypatch) -> None:
    monkeypatch.setattr(service, "_api_identity", lambda: {"instance_id": "owned"})

    service._wait_for_api("owned", FakeProcess(), timeout_s=0.01)  # type: ignore[arg-type]


def test_wait_for_api_rejects_a_stale_instance(monkeypatch) -> None:
    monkeypatch.setattr(service, "_api_identity", lambda: {"instance_id": "stale"})

    try:
        service._wait_for_api("owned", FakeProcess(), timeout_s=0.01)  # type: ignore[arg-type]
    except SystemExit as exc:
        assert "ownership check failed" in str(exc).lower()
    else:
        raise AssertionError("Expected stale backend ownership to be rejected.")
