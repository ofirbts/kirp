"""POST /api/v1/query — tenant/space/user from JWT or SKIP_AUTH only (not request body)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.core.rag_engine import RAGResponse


@pytest.fixture
def client_skip_auth(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "1")
    from src.main import app

    return TestClient(app)


@pytest.fixture
def client_no_skip(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "0")
    from src.main import app

    return TestClient(app)


def test_query_401_without_auth_when_skip_auth_off(client_no_skip: TestClient) -> None:
    r = client_no_skip.post("/api/v1/query", json={"query": "hello", "k": 3})
    assert r.status_code == 401


def test_query_uses_context_tenant_not_body_tenant(
    client_skip_auth: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[dict[str, object]] = []

    async def fake_get_rag_engine() -> object:
        class _RAG:
            async def search(self, **kwargs: object) -> RAGResponse:
                captured.append(dict(kwargs))
                return RAGResponse(
                    results=[],
                    context_text="ok",
                    confidence=0.0,
                    query_scopes={},
                )

        return _RAG()

    monkeypatch.setattr("src.main.get_rag_engine", fake_get_rag_engine)
    r = client_skip_auth.post(
        "/api/v1/query",
        json={
            "query": "x",
            "k": 2,
            "tenant_id": "evil_other_tenant",
            "user_id": "attacker",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert body.get("answer") == "ok"
    assert len(captured) == 1
    assert captured[0].get("tenant_id") == "default"
    assert captured[0].get("user_id") == "dev"
