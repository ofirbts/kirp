from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.event_store import Event, EventStore


@pytest.mark.asyncio
async def test_get_by_id_for_tenant_filters_query() -> None:
    store = EventStore("mongodb://localhost:27017")
    store._db = MagicMock()
    event_id = uuid4()
    store._db.events.find_one = AsyncMock(
        return_value={
            "_id": str(event_id),
            "tenant_id": "tenant-a",
            "space_id": "all",
            "user_id": "u1",
            "source": "test",
            "content": "c",
            "metadata": {},
            "event_type": "ingest",
            "timestamp": "2026-06-02T10:00:00+00:00",
        }
    )
    ev = await store.get_by_id_for_tenant(event_id, "tenant-a")
    assert ev is not None
    assert ev.tenant_id == "tenant-a"
    store._db.events.find_one.assert_awaited_once_with(
        {"_id": str(event_id), "tenant_id": "tenant-a"},
    )


@pytest.mark.asyncio
async def test_get_by_id_for_tenant_wrong_tenant_returns_none() -> None:
    store = EventStore("mongodb://localhost:27017")
    store._db = MagicMock()
    event_id = uuid4()
    store._db.events.find_one = AsyncMock(return_value=None)
    ev = await store.get_by_id_for_tenant(event_id, "tenant-b")
    assert ev is None


@pytest.mark.asyncio
async def test_replay_requires_tenant_scope() -> None:
    store = EventStore("mongodb://localhost:27017")
    event_id = uuid4()
    event = Event(
        id=event_id,
        tenant_id="t1",
        space_id="all",
        user_id="u1",
        source="s",
        content="body",
        metadata={},
    )
    store.get_by_id_for_tenant = AsyncMock(return_value=event)
    payload = await store.replay(event_id, "t1")
    assert payload["tenant_id"] == "t1"
    store.get_by_id_for_tenant.assert_awaited_once_with(event_id, "t1")
