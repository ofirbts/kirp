"""GET /api/v1/tenants — only current tenant row."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.schemas.api_models import Tenant as TenantSchema


@pytest.fixture
def client_skip(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "1")
    from src.main import app

    return TestClient(app)


def test_list_tenants_filters_to_context_tenant(
    client_skip: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    iso = "2026-01-01T00:00:00+00:00"

    async def fake_list() -> list[TenantSchema]:
        return [
            TenantSchema(
                id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                name="Other",
                slug="other",
                lifecycle="active",
                createdAt=iso,
                updatedAt=iso,
            ),
            TenantSchema(
                id="default",
                name="Default Org",
                slug="default",
                lifecycle="active",
                createdAt=iso,
                updatedAt=iso,
            ),
        ]

    monkeypatch.setattr("src.api.v1_tenants_spaces.tenants_service.list_tenants", fake_list)
    r = client_skip.get("/api/v1/tenants")
    assert r.status_code == 200
    data = r.json().get("data") or []
    assert len(data) == 1
    assert data[0]["slug"] == "default"
