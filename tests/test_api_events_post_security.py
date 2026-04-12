"""POST /api/v1/events — tenant/space/user from JWT only."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_skip_auth(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "1")
    from src.main import app

    return TestClient(app)


def test_create_event_ignores_body_tenant_ids(
    client_skip_auth: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    class _FakeKafka:
        def emit(self, envelope: object) -> bool:
            captured["tenant_id"] = getattr(envelope, "tenant_id", "")
            captured["space_id"] = getattr(envelope, "space_id", "")
            captured["user_id"] = getattr(envelope, "user_id", "")
            return True

    monkeypatch.setattr(
        "src.agents.kafka_event_agent.KafkaEventAgent",
        lambda *a, **k: _FakeKafka(),
    )

    r = client_skip_auth.post(
        "/api/v1/events",
        json={
            "tenant_id": "evil_tenant",
            "space_id": "evil_space",
            "user_id": "evil_user",
            "content": "hello",
            "source": "test",
        },
    )
    assert r.status_code == 201
    assert captured.get("tenant_id") == "default"
    assert captured.get("user_id") == "dev"
