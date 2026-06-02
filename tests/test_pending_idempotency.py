from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.pending_executions import PendingExecutionsStore


@pytest.mark.asyncio
async def test_add_or_get_pending_deduplicates() -> None:
    store = PendingExecutionsStore("mongodb://localhost:27017")
    store._db = MagicMock()
    coll = MagicMock()
    store._db.pending_executions = coll
    coll.find_one = AsyncMock(
        side_effect=[
            None,
            {
                "_id": "existing-1",
                "tenant_id": "t1",
                "user_id": "u1",
                "space_id": "all",
                "command_type": "send_whatsapp",
                "payload": {"idempotency_key": "idem-1"},
                "status": "pending",
            },
        ]
    )
    coll.insert_one = AsyncMock()
    coll.count_documents = AsyncMock(return_value=1)

    pid1, dup1 = await store.add_or_get_pending(
        "t1", "u1", "all", "send_whatsapp", {"to": "+1", "text": "a"},
        idempotency_key="idem-1",
    )
    pid2, dup2 = await store.add_or_get_pending(
        "t1", "u1", "all", "send_whatsapp", {"to": "+1", "text": "a"},
        idempotency_key="idem-1",
    )
    assert dup1 is False
    assert dup2 is True
    assert pid2 == "existing-1"
    coll.insert_one.assert_awaited_once()
