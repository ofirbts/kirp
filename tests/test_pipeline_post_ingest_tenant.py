from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.pipeline import EventPipeline


@pytest.mark.asyncio
async def test_run_post_ingest_uses_tenant_scoped_fetch() -> None:
    event_id = uuid4()
    store = MagicMock()
    store.get_by_id_for_tenant = AsyncMock(return_value=None)
    pipe = EventPipeline(store, MagicMock(), MagicMock(), MagicMock(), MagicMock())
    ok = await pipe.run_post_ingest_for_event(event_id, "tenant-x")
    assert ok is False
    store.get_by_id_for_tenant.assert_awaited_once_with(event_id, "tenant-x")
    store.get_by_id.assert_not_called()
