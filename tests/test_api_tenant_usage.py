"""GET /api/v1/tenant/{tenant_id}/usage"""

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


def test_tenant_usage_ok(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_QUOTA_LIMIT_USD", "5.0")

    async def fake_used(tenant_id: str) -> float:
        assert tenant_id == "default"
        return 1.2

    monkeypatch.setattr("src.core.quotas.get_tenant_llm_cost_used", fake_used)

    r = client.get("/api/v1/tenant/default/usage")
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == "default"
    assert body["llm_cost_used"] == 1.2
    assert body["limit"] == 5.0


def test_tenant_usage_mismatch_403(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_used(tenant_id: str) -> float:
        return 0.0

    monkeypatch.setattr("src.core.quotas.get_tenant_llm_cost_used", fake_used)
    r = client.get("/api/v1/tenant/other/usage")
    assert r.status_code == 403


def test_tenant_usage_unlimited_limit_null(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_QUOTA_LIMIT_USD", raising=False)

    async def fake_used(tenant_id: str) -> float:
        return 0.5

    monkeypatch.setattr("src.core.quotas.get_tenant_llm_cost_used", fake_used)
    r = client.get("/api/v1/tenant/default/usage")
    assert r.status_code == 200
    assert r.json()["limit"] is None
