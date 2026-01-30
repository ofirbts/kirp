from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from src.main import app


def test_health_ok() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


def test_observability_contracts() -> None:
    client = TestClient(app)
    resp = client.get("/observability/contracts")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert "models" in data

