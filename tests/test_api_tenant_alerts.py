"""GET /api/v1/tenant/{tenant_id}/alerts"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def skip_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKIP_AUTH", "1")


@pytest.fixture
def client(skip_auth: None) -> TestClient:
    from src.main import app

    return TestClient(app)


def test_tenant_alerts_ok(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_alerts(tenant_id: str) -> list:
        return [
            {
                "id": "a1",
                "type": "hourly_failures",
                "severity": "warning",
                "message": "5 failed run steps this hour",
                "raised_at": "2026-04-09T12:00:00+00:00",
                "meta": {},
            }
        ]

    monkeypatch.setattr("src.core.alerting.get_active_alerts", fake_alerts)

    r = client.get("/api/v1/tenant/default/alerts")
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == "default"
    assert body["count"] == 1
    assert body["alerts"][0]["type"] == "hourly_failures"


def test_tenant_alerts_mismatch_403(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_alerts(_tid: str) -> list:
        return []

    monkeypatch.setattr("src.core.alerting.get_active_alerts", fake_alerts)
    r = client.get("/api/v1/tenant/other/alerts")
    assert r.status_code == 403
