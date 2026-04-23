"""POST /api/v1/tasks — contract used by monitoring Next Action (createTaskV1)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.models.schema import SchemaEntity


@pytest.fixture
def skip_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKIP_AUTH", "1")


@pytest.fixture
def client(skip_auth: None) -> TestClient:
    from src.main import app

    return TestClient(app)


@pytest.fixture
def fake_schema_engine(monkeypatch: pytest.MonkeyPatch) -> dict[str, dict[str, Any]]:
    """In-memory store; no PostgreSQL required."""
    store: dict[str, dict[str, Any]] = {}

    class FakeSchema:
        async def upsert_node(
            self,
            tenant_id: str,
            space_id: str,
            entity: SchemaEntity,
            title: str,
            node_id: str | None = None,
            description: str | None = None,
            parent_id: str | None = None,
            status: str | None = None,
            priority: str | None = None,
            due_date: Any = None,
            metadata: dict[str, Any] | None = None,
        ) -> str:
            assert node_id is not None
            meta = metadata or {}
            store[node_id] = {
                "id": node_id,
                "title": title,
                "due_date": None,
                "tenant_id": tenant_id,
                "space_id": space_id,
                "status": status,
                "entity": entity.value,
                "metadata": meta,
            }
            return node_id

        async def get_node(self, node_id: str, tenant_id: str) -> dict[str, Any] | None:
            row = store.get(node_id)
            if not row or row.get("tenant_id") != tenant_id:
                return None
            return row

    fake = FakeSchema()

    async def _get() -> FakeSchema:
        return fake

    monkeypatch.setattr("src.api.v1_tasks.get_schema_engine", _get)
    return store


def test_post_tasks_creates_entity_shape(
    client: TestClient,
    fake_schema_engine: dict[str, dict[str, Any]],
) -> None:
    """Monitoring treats ok + data.id as success; list shape matches TaskV1."""
    r = client.post(
        "/api/v1/tasks?tenant_id=default&space_id=all",
        json={
            "title": "KIRP monitoring follow-up",
            "status": "open",
            "priority": "normal",
            "description": "From test_api_v1_tasks_post",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    data = body.get("data") or {}
    assert "id" in data and data["id"]
    assert data.get("title") == "KIRP monitoring follow-up"
    assert len(fake_schema_engine) == 1


def test_post_tasks_empty_title_fallback(
    client: TestClient,
    fake_schema_engine: dict[str, dict[str, Any]],
) -> None:
    """API coerces empty title to a placeholder (monitoring should send non-empty)."""
    r = client.post(
        "/api/v1/tasks?tenant_id=default&space_id=all",
        json={"title": ""},
    )
    assert r.status_code == 200, r.text
    data = (r.json() or {}).get("data") or {}
    assert data.get("title") == "Untitled"
    assert len(fake_schema_engine) == 1
