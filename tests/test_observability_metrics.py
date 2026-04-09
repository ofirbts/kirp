"""GET /observability/metrics/prometheus vs /snapshot — wiring smoke (see SYSTEM_STATUS Metrics exposure)."""

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


def test_metrics_prometheus_returns_200(client: TestClient) -> None:
    r = client.get("/observability/metrics/prometheus")
    assert r.status_code == 200
    assert isinstance(r.text, str)


def test_metrics_snapshot_returns_json_stub(client: TestClient) -> None:
    r = client.get("/observability/metrics/snapshot")
    assert r.status_code == 200
    body = r.json()
    assert "last_updated" in body
    assert "namespaces" in body
