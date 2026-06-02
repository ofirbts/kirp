from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_dev(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "1")
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("KIRP_TRACE_LOG_PATH", "")
    from src.main import app

    return TestClient(app)


def test_health_degraded_in_development_when_stores_fail(client_dev: TestClient) -> None:
    with (
        patch("src.main.get_event_store", new_callable=AsyncMock, side_effect=RuntimeError("mongo down")),
        patch("src.main.get_rag_engine", new_callable=AsyncMock, side_effect=RuntimeError("rag down")),
    ):
        r = client_dev.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degraded"
    assert "telemetry" in body
    assert body["telemetry"]["governed_runtime_mode"] == "shadow"
