"""PATCH /api/v1/tenants/{tenant_id}/lifecycle — SaaS tenant lifecycle."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.schemas.api_models import Tenant as TenantSchema
from src.services.tenants_service import TenantLifecycleError


@pytest.fixture
def skip_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKIP_AUTH", "1")


@pytest.fixture
def client(skip_auth: None) -> TestClient:
    from src.main import app

    return TestClient(app)


def test_patch_lifecycle_tenant_mismatch_403(client: TestClient) -> None:
    r = client.patch(
        "/api/v1/tenants/00000000-0000-0000-0000-000000000001/lifecycle",
        json={"lifecycle": "active"},
    )
    assert r.status_code == 403
    assert r.json().get("detail") == "tenant mismatch"


def test_patch_lifecycle_ok(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    tid = "default"

    async def _fake_update(tenant_id: str, lifecycle: str) -> TenantSchema:
        assert tenant_id == tid
        assert lifecycle == "active"
        return TenantSchema(
            id=tenant_id,
            name="Default",
            slug="default",
            lifecycle=lifecycle,
            createdAt="2026-01-01T00:00:00Z",
            updatedAt="2026-01-01T00:00:00Z",
        )

    monkeypatch.setattr(
        "src.api.v1_tenants_spaces.update_tenant_lifecycle",
        _fake_update,
    )

    r = client.patch(f"/api/v1/tenants/{tid}/lifecycle", json={"lifecycle": "active"})
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["lifecycle"] == "active"
    assert body["data"]["id"] == tid


def test_patch_lifecycle_service_error_400(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    tid = "default"

    async def _boom(_tenant_id: str, _lifecycle: str) -> TenantSchema:
        raise TenantLifecycleError("tenant not found")

    monkeypatch.setattr(
        "src.api.v1_tenants_spaces.update_tenant_lifecycle",
        _boom,
    )

    r = client.patch(f"/api/v1/tenants/{tid}/lifecycle", json={"lifecycle": "active"})
    assert r.status_code == 400
    assert "not found" in r.json().get("detail", "")
