"""GET /api/v1/tenant/{tenant_id}/runs"""

from __future__ import annotations

import asyncio
import os
import sys

import pytest
from fastapi.testclient import TestClient

import src.core.run_controller as rcmod


@pytest.fixture
def skip_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKIP_AUTH", "1")


@pytest.fixture
def client(skip_auth: None) -> TestClient:
    from src.main import app

    return TestClient(app)


@pytest.fixture
def seeded_tenant_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _seed() -> None:
        c = rcmod.RunController(redis_ping_max_attempts=1)

        async def _no_redis(self: rcmod.RunController) -> object:
            return None

        monkeypatch.setattr(rcmod.RunController, "_redis_client", _no_redis)
        monkeypatch.setattr(rcmod, "_run_controller", c)

        await c.create_run("ingest", "default", run_id="run_z_old")
        c.run_states["run_z_old"].state = "failed"
        c.run_states["run_z_old"].started_at = "2026-01-01T00:00:00+00:00"

        await c.create_run("ingest", "default", run_id="run_m_mid")
        c.run_states["run_m_mid"].state = "partial"
        c.run_states["run_m_mid"].started_at = "2026-01-02T00:00:00+00:00"

        await c.create_run("ingest", "default", run_id="run_a_new")
        c.run_states["run_a_new"].state = "completed"
        c.run_states["run_a_new"].started_at = "2026-01-03T00:00:00+00:00"
        c.run_states["run_a_new"].steps.append(
            {
                "step": "llm_call_gemma4",
                "status": "completed",
                "error": None,
                "ts": "2026-01-03T00:01:00+00:00",
            }
        )

    asyncio.run(_seed())


def test_get_tenant_runs_ok(client: TestClient, seeded_tenant_runs: None) -> None:
    r = client.get("/api/v1/tenant/default/runs?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == "default"
    assert body["stats"]["total"] == 3
    assert body["stats"]["completed"] == 1
    assert body["stats"]["partial"] == 1
    assert body["stats"]["failed"] == 1
    ids = [x["run_id"] for x in body["runs"]]
    assert ids == ["run_a_new", "run_m_mid", "run_z_old"]
    assert all("steps_count" in x for x in body["runs"])
    assert all("model" in x for x in body["runs"])
    assert body["runs"][0]["model"] == "gemma4"
    assert body["runs"][1]["model"] is None


def test_get_tenant_runs_tenant_mismatch_403(client: TestClient, seeded_tenant_runs: None) -> None:
    r = client.get("/api/v1/tenant/other_tenant/runs")
    assert r.status_code == 403
    assert "mismatch" in r.json().get("detail", "").lower()


def test_get_tenant_runs_limit(client: TestClient, seeded_tenant_runs: None) -> None:
    r = client.get("/api/v1/tenant/default/runs?limit=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body["runs"]) == 2
    assert body["stats"]["total"] == 2
    assert body["stats"]["completed"] == 1
    assert body["stats"]["partial"] == 1
    assert body["stats"]["failed"] == 0
