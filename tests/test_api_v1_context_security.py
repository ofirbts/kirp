"""Context API — tenant/user from JWT only."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_context_accessible_spaces_401_without_auth(client_no_skip: TestClient) -> None:
    r = client_no_skip.get("/api/v1/context/accessible-spaces")
    assert r.status_code == 401


def test_context_uses_jwt_identity_not_query(
    client_skip: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[str, str]] = []

    async def fake_get(tenant_id: str, user_id: str) -> list[str]:
        seen.append((tenant_id, user_id))
        return ["s1"]

    monkeypatch.setattr("src.api.v1_context.get_accessible_space_ids", fake_get)
    r = client_skip.get(
        "/api/v1/context/accessible-spaces",
        params={"tenant_id": "evil", "user_id": "evil"},
    )
    assert r.status_code == 200
    assert seen == [("default", "dev")]
    assert r.json()["tenant_id"] == "default"
