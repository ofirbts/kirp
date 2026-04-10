"""GET /api/v1/tenant/{tenant_id}/usage/details"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def skip_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKIP_AUTH", "1")


@pytest.fixture
def client(skip_auth: None) -> TestClient:
    from src.main import app

    return TestClient(app)


@pytest.fixture
def fake_rc(monkeypatch: pytest.MonkeyPatch) -> None:
    class _RC:
        async def get_recent_runs(self, tenant_id: str, limit: int = 50) -> list[dict]:
            return [
                {
                    "run_id": "r1",
                    "model": "gemma4",
                    "started_at": "2026-04-09T12:00:00+00:00",
                    "cost": 0.12,
                },
                {
                    "run_id": "r2",
                    "model": "openai",
                    "started_at": "2026-04-09T15:00:00+00:00",
                    "cost": 0.05,
                },
            ]

    monkeypatch.setattr("src.api.v1_tenant_usage.get_run_controller", lambda: _RC())


@pytest.fixture
def fake_tenant_trial(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _row(_tid: str) -> SimpleNamespace:
        return SimpleNamespace(
            extra={
                "lifecycle": "trial",
                "trial_ends_at": "2099-06-01T00:00:00Z",
            }
        )

    monkeypatch.setattr("src.api.v1_tenant_usage._load_tenant_row", _row)


def test_usage_details_ok(
    client: TestClient,
    fake_rc: None,
    fake_tenant_trial: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_QUOTA_LIMIT_USD", "25")

    async def _used(_tid: str) -> float:
        return 3.5

    monkeypatch.setattr("src.api.v1_tenant_usage.get_tenant_llm_cost_used", _used)

    r = client.get("/api/v1/tenant/default/usage/details")
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == "default"
    assert body["llm_cost_used"] == 3.5
    assert body["quota_enabled"] is True
    assert body["llm_quota_limit_usd"] == 25.0
    assert body["lifecycle"] == "trial"
    assert body["suspended"] is False
    assert body["trial_days_remaining"] is not None
    assert body["trial_days_remaining"] > 0
    assert len(body["breakdown"]) >= 1
    models = {b["model_used"] for b in body["breakdown"]}
    assert "gemma4" in models


def test_usage_details_tenant_mismatch_403(client: TestClient, fake_rc: None, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _row(_tid: str) -> SimpleNamespace:
        return SimpleNamespace(extra={})

    async def _used(_tid: str) -> float:
        return 0.0

    monkeypatch.setattr("src.api.v1_tenant_usage._load_tenant_row", _row)
    monkeypatch.setattr("src.api.v1_tenant_usage.get_tenant_llm_cost_used", _used)
    r = client.get("/api/v1/tenant/other/usage/details")
    assert r.status_code == 403


def test_usage_details_suspended_flag(
    client: TestClient,
    fake_rc: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _row(_tid: str) -> SimpleNamespace:
        return SimpleNamespace(extra={"lifecycle": "suspended"})

    monkeypatch.setattr("src.api.v1_tenant_usage._load_tenant_row", _row)

    async def _used(_tid: str) -> float:
        return 1.0

    monkeypatch.setattr("src.api.v1_tenant_usage.get_tenant_llm_cost_used", _used)

    r = client.get("/api/v1/tenant/default/usage/details")
    assert r.status_code == 200
    assert r.json()["suspended"] is True
    assert r.json()["lifecycle"] == "suspended"
