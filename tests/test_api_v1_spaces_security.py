"""GET/POST /api/v1/spaces — tenant from JWT context only."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_skip_auth(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "1")
    from src.main import app

    return TestClient(app)


def test_list_spaces_uses_jwt_tenant_not_query(
    client_skip_auth: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []

    async def fake_list(tenant_id: str) -> list[object]:
        captured.append(tenant_id)
        return []

    monkeypatch.setattr(
        "src.api.v1_tenants_spaces.tenants_service.list_spaces_for_tenant",
        fake_list,
    )
    r = client_skip_auth.get("/api/v1/spaces", params={"tenant_id": "evil"})
    assert r.status_code == 200
    assert captured == ["default"]
