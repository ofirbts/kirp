"""Connections validate/errors — tenant and user from JWT only."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.core.jwt_utils import create_access_token


@pytest.fixture
def client_auth(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "0")
    from src.main import app

    return TestClient(app)


def test_validate_uses_jwt_identity(
    client_auth: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, str] = {}

    class FakeTS:
        async def connect(self) -> None:
            pass

        async def get_token(self, tenant_id: str, user_id: str, integration: str) -> None:
            seen["tenant_id"] = tenant_id
            seen["user_id"] = user_id
            seen["integration"] = integration
            return None

    async def fake_ensure() -> tuple[FakeTS, FakeTS]:
        return FakeTS(), FakeTS()

    monkeypatch.setattr("src.api.v1_connections._ensure_stores", fake_ensure)
    token = create_access_token("conn_user", "conn_tenant", roles=["user"])
    r = client_auth.get(
        "/api/v1/connections/gmail/validate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert seen["tenant_id"] == "conn_tenant"
    assert seen["user_id"] == "conn_user"
    assert seen["integration"] == "gmail"


def test_errors_uses_jwt_identity(
    client_auth: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, str | int] = {}

    class FakeSL:
        async def connect(self) -> None:
            pass

        async def get_errors(
            self,
            *,
            tenant_id: str,
            user_id: str,
            integration: str,
            limit: int,
        ) -> list:
            seen["tenant_id"] = tenant_id
            seen["user_id"] = user_id
            seen["integration"] = integration
            seen["limit"] = limit
            return []

    monkeypatch.setattr("src.api.v1_connections._sync_log_store", lambda: FakeSL())
    token = create_access_token("e_user", "e_tenant", roles=["user"])
    r = client_auth.get(
        "/api/v1/connections/slack/errors?limit=5",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert seen["tenant_id"] == "e_tenant"
    assert seen["user_id"] == "e_user"
    assert seen["integration"] == "slack"
    assert seen["limit"] == 5
