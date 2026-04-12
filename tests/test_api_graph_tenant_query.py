"""GET /api/v1/graph — optional tenant_id query must match JWT context."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_skip_auth(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "1")
    from src.main import app

    return TestClient(app)


def test_graph_rejects_mismatched_tenant_query(client_skip_auth: TestClient) -> None:
    r = client_skip_auth.get("/api/v1/graph", params={"tenant_id": "not_default"})
    assert r.status_code == 403
    assert "mismatch" in r.json().get("detail", "").lower()
