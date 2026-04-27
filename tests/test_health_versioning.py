from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def skip_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKIP_AUTH", "1")


@pytest.fixture
def client(skip_auth: None, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    import src.main as main

    async def _ok_store() -> object:
        return object()

    async def _ok_rag() -> object:
        return object()

    monkeypatch.setattr(main, "get_event_store", _ok_store)
    monkeypatch.setattr(main, "get_rag_engine", _ok_rag)
    monkeypatch.setattr(main, "APP_GIT_SHA", "1234567890abcdef1234567890abcdef12345678")
    return TestClient(main.app)


def test_health_includes_version_shape(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "version" in body
    assert body["version"]["sha"] == "1234567890abcdef1234567890abcdef12345678"
    assert body["version"]["short"] == "1234567"
    assert body["version"]["source"] == "env:APP_GIT_SHA"


def test_health_sets_version_header(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-KIRP-Version") == "1234567890abcdef1234567890abcdef12345678"
