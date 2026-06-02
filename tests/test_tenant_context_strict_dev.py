from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_strict_dev(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "0")
    monkeypatch.setenv("ENV", "development")
    from src.main import app

    return TestClient(app)


def test_development_without_skip_auth_requires_jwt(client_strict_dev: TestClient) -> None:
    r = client_strict_dev.get("/api/v1/events")
    assert r.status_code == 401


def test_development_with_jwt_uses_token_tenant(
    client_strict_dev: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.jwt_utils import create_access_token

    captured: list[str] = []

    async def fake_list(*, tenant_id: str, **_kw: object) -> list[dict[str, str]]:
        captured.append(tenant_id)
        return []

    monkeypatch.setattr("src.api.v1_events.events_service.list_events", fake_list)
    token = create_access_token("user_a", "tenant_a", roles=["user"])
    r = client_strict_dev.get(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert captured == ["tenant_a"]
