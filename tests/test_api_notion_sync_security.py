"""POST /api/v1/notion/sync — tenant/space/user from auth context only."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


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


def test_notion_sync_401_without_auth_when_skip_auth_off(client_no_skip: TestClient) -> None:
    r = client_no_skip.post("/api/v1/notion/sync")
    assert r.status_code == 401


def test_notion_sync_uses_context_tenant(
    client_skip_auth: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    async def fake_run(
        tenant_id: str,
        space_id: str,
        user_id: str,
        **kwargs: object,
    ) -> dict[str, object]:
        captured["tenant_id"] = tenant_id
        captured["space_id"] = space_id
        captured["user_id"] = user_id
        return {"ingested": 0, "skipped": 0, "errors": []}

    async def fake_store() -> object:
        return object()

    async def fake_pipe() -> object:
        return object()

    mock_cls = MagicMock()
    mock_inst = MagicMock()
    mock_inst.connect = MagicMock()
    mock_cls.return_value = mock_inst

    monkeypatch.setattr("src.main.get_event_store", fake_store)
    monkeypatch.setattr("src.main.get_pipeline", fake_pipe)
    monkeypatch.setattr("src.workers.notion_sync.run_notion_sync", fake_run)
    monkeypatch.setattr("src.integrations.notion.NotionIntegration", mock_cls)

    r = client_skip_auth.post("/api/v1/notion/sync")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert captured.get("tenant_id") == "default"
    assert captured.get("user_id") == "dev"
