"""Kirp API key middleware: Authorization: Kirp <secret_key>."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

import src.core.run_controller as rcmod


@pytest.fixture
def no_skip_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKIP_AUTH", "0")


@pytest.fixture
def client(no_skip_auth: None) -> TestClient:
    from src.main import app

    return TestClient(app)


@pytest.fixture
def seeded_run_default(monkeypatch: pytest.MonkeyPatch) -> str:
    async def _seed() -> str:
        c = rcmod.RunController(redis_ping_max_attempts=1)

        async def _no_redis(self: rcmod.RunController) -> object:
            return None

        monkeypatch.setattr(rcmod.RunController, "_redis_client", _no_redis)
        monkeypatch.setattr(rcmod, "_run_controller", c)
        rid = "run_kirp_test_001"
        await c.create_run("ingest", "default", trace_id="trace_k", run_id=rid)
        await c.update_step(rid, "pipeline_complete", "completed")
        return rid

    return asyncio.run(_seed())


async def _principal_good(secret: str) -> dict | None:
    if secret == "kirp_sk_valid_test":
        return {
            "tenant_id": "default",
            "space_id": "all",
            "user_id": "api_key",
            "roles": ["api_key"],
            "auth_via": "kirp_api_key",
        }
    return None


def test_kirp_valid_run_status_200(
    client: TestClient,
    seeded_run_default: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.middleware.api_key_auth.resolve_kirp_principal",
        _principal_good,
    )
    r = client.get(
        f"/api/v1/run/{seeded_run_default}/status",
        headers={"Authorization": "Kirp kirp_sk_valid_test"},
    )
    assert r.status_code == 200
    assert r.json()["run_id"] == seeded_run_default


def test_kirp_invalid_401(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _none(_secret: str) -> dict | None:
        return None

    monkeypatch.setattr("src.middleware.api_key_auth.resolve_kirp_principal", _none)
    r = client.get(
        "/api/v1/run/any/status",
        headers={"Authorization": "Kirp kirp_sk_invalid"},
    )
    assert r.status_code == 401
    assert r.json().get("detail") == "Unauthorized"


def test_kirp_suspended_403(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _suspended(_secret: str) -> dict | None:
        return {"_blocked": True, "reason": "tenant_suspended", "status": 403}

    monkeypatch.setattr("src.middleware.api_key_auth.resolve_kirp_principal", _suspended)
    r = client.get(
        "/api/v1/run/any/status",
        headers={"Authorization": "Kirp kirp_sk_x"},
    )
    assert r.status_code == 403
    assert r.json().get("detail") == "tenant_suspended"
