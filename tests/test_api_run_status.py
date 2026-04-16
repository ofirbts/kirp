"""GET /api/v1/run/{run_id}/status"""

from __future__ import annotations

import asyncio
import os

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
def seeded_run(monkeypatch: pytest.MonkeyPatch) -> str:
    async def _seed() -> str:
        c = rcmod.RunController(redis_ping_max_attempts=1)

        async def _no_redis(self: rcmod.RunController) -> object:
            return None

        monkeypatch.setattr(rcmod.RunController, "_redis_client", _no_redis)
        monkeypatch.setattr(rcmod, "_run_controller", c)
        rid = "run_75c5752911fa4a6db5057f5664eb572f"
        await c.create_run("ingest", "default", trace_id="trace_1", run_id=rid)
        await c.update_step(rid, "kafka_emitted", "completed")
        await c.update_step(rid, "pipeline_start", "processing")
        await c.update_step(rid, "governance_check", "completed")
        await c.update_step(rid, "mongo_write", "completed")
        await c.update_step(rid, "history_write", "completed")
        await c.update_step(rid, "pipeline_start", "completed")
        await c.update_step(rid, "llm_call_gemma4", "completed")
        await c.update_step(rid, "pipeline_complete", "completed")
        return rid

    return asyncio.run(_seed())


def test_get_run_status_ok(client: TestClient, seeded_run: str) -> None:
    r = client.get(f"/api/v1/run/{seeded_run}/status")
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == seeded_run
    assert body["state"] == "completed"
    assert body["overall_status"] == body["state"]
    assert body["is_complete"] is True
    assert isinstance(body["timeline"], list)
    assert any(s.get("step") == "history_write" for s in body["timeline"])
    assert body.get("model") == "gemma4"
    assert any(s.get("step") == "llm_call_gemma4" for s in body["timeline"])


def test_get_run_visibility_ok(client: TestClient, seeded_run: str) -> None:
    r = client.get(f"/runs/{seeded_run}")
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == seeded_run
    assert body["trace_id"] == "trace_1"
    assert body["state"] == "completed"
    assert isinstance(body["duration_ms"], int)
    assert isinstance(body["steps"], list)
    assert body["steps"]
    for s in body["steps"]:
        assert "name" in s and "status" in s and "duration_ms" in s


def test_get_run_status_not_found(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop() -> None:
        c = rcmod.RunController(redis_ping_max_attempts=1)

        async def _no_redis(self: rcmod.RunController) -> object:
            return None

        monkeypatch.setattr(rcmod.RunController, "_redis_client", _no_redis)
        monkeypatch.setattr(rcmod, "_run_controller", c)

    asyncio.run(_noop())
    r = client.get("/api/v1/run/run_does_not_exist_zzzz/status")
    assert r.status_code == 404
