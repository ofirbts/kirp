"""POST /api/v1/rag/search — cannot override JWT tenant via body."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.core.jwt_utils import create_access_token
from src.core.rag_engine import RAGResponse


@pytest.fixture
def client_no_skip(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "0")
    from src.main import app

    return TestClient(app)


def test_rag_search_403_when_body_tenant_differs_from_jwt(
    client_no_skip: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_engine() -> object:
        class _E:
            async def search(self, **kwargs: object) -> RAGResponse:
                return RAGResponse(results=[], context_text="", confidence=0.0, query_scopes={})

        return _E()

    monkeypatch.setattr("src.api.v1_rag._get_rag_engine_for_v1", fake_engine)

    token = create_access_token("user_z", "tenant_alpha", roles=["user"])
    r = client_no_skip.post(
        "/api/v1/rag/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "hello", "tenant_id": "tenant_other"},
    )
    assert r.status_code == 403
