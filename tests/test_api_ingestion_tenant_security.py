"""v1_ingestion: connector sync from JWT; Slack/WhatsApp webhooks tenant from env only."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_skip(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "1")
    from src.main import app

    return TestClient(app)


@pytest.fixture
def client_no_skip(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "0")
    from src.main import app

    return TestClient(app)


def test_gmail_sync_401_without_auth(client_no_skip: TestClient) -> None:
    r = client_no_skip.post("/api/v1/gmail/sync")
    assert r.status_code == 401


def test_gmail_sync_uses_context_tenant(
    client_skip: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    async def fake_gmail(**kwargs: object) -> dict[str, object]:
        captured["tenant_id"] = str(kwargs.get("tenant_id", ""))
        captured["user_id"] = str(kwargs.get("user_id", ""))
        return {"ingested": 0}

    monkeypatch.setattr("src.workers.connector_sync.run_gmail_sync", fake_gmail)
    r = client_skip.post("/api/v1/gmail/sync")
    assert r.status_code == 200
    assert captured.get("tenant_id") == "default"
    assert captured.get("user_id") == "dev"


def test_slack_webhook_uses_env_tenant_not_body(
    client_skip: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_TENANT_ID", "from_env_tenant")
    monkeypatch.setenv("SLACK_WEBHOOK_SPACE_ID", "from_env_space")
    monkeypatch.setenv("SLACK_WEBHOOK_USER_ID", "from_env_user")

    tenants_seen: list[str] = []

    async def cap_ingest(tenant_id: str, *_a: object, **_kw: object) -> dict[str, object]:
        tenants_seen.append(tenant_id)
        return {"ok": True, "run_id": "r", "trace_id": "t"}

    monkeypatch.setattr("src.api.v1_ingestion._ingest_one", cap_ingest)

    class _Slack:
        def connect(self) -> None:
            return None

        def parse_webhook(self, _body: dict) -> list[dict]:
            return [{"content": "hi", "source": "slack", "metadata": {}}]

    monkeypatch.setattr("src.integrations.slack.SlackIntegration", _Slack)

    r = client_skip.post(
        "/api/v1/webhooks/slack",
        json={
            "tenant_id": "evil_body_tenant",
            "space_id": "evil_space",
            "user_id": "evil_user",
            "event": {"type": "message"},
        },
    )
    assert r.status_code == 200
    assert tenants_seen == ["from_env_tenant"]


def test_whatsapp_webhook_ignores_body_tenant_for_routing(
    client_skip: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WHATSAPP_WEBHOOK_TENANT_ID", "wa_env_t")
    monkeypatch.setenv("WHATSAPP_WEBHOOK_SPACE_ID", "wa_env_s")
    monkeypatch.setenv("WHATSAPP_WEBHOOK_USER_ID", "wa_env_u")

    tenants_seen: list[str] = []

    async def cap_ingest(tenant_id: str, *_a: object, **_kw: object) -> dict[str, object]:
        tenants_seen.append(tenant_id)
        return {"ok": True, "run_id": "r", "trace_id": "t"}

    monkeypatch.setattr("src.api.v1_ingestion._ingest_one", cap_ingest)

    class _WA:
        def parse_webhook_payload(self, _body: dict) -> list[dict]:
            return [{"content": "x", "source": "wa", "metadata": {}}]

    monkeypatch.setattr("src.integrations.whatsapp.WhatsAppIntegration", _WA)

    r = client_skip.post(
        "/api/v1/webhooks/whatsapp",
        json={"tenant_id": "evil", "From": "+1"},
    )
    assert r.status_code == 200
    assert tenants_seen == ["wa_env_t"]
