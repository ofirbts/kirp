from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_skip(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "1")
    from src.main import app

    return TestClient(app)


def test_slack_webhook_503_when_kafka_emit_false(
    client_skip: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_TENANT_ID", "t_slack")
    monkeypatch.setenv("SLACK_WEBHOOK_SPACE_ID", "s1")
    monkeypatch.setenv("SLACK_WEBHOOK_USER_ID", "u1")

    class _Slack:
        def connect(self) -> None:
            return None

        def parse_webhook(self, _body: dict) -> list[dict]:
            return [{"content": "hi", "source": "slack", "metadata": {}}]

    monkeypatch.setattr("src.integrations.slack.SlackIntegration", _Slack)

    class _Agent:
        def emit(self, *_a: object, **_kw: object) -> bool:
            return False

    monkeypatch.setattr("src.agents.kafka_event_agent.KafkaEventAgent", _Agent)

    r = client_skip.post("/api/v1/webhooks/slack", json={"event": {"type": "message"}})
    assert r.status_code == 503
