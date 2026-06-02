from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.control_plane.access import get_event_for_governance_mutate


@pytest.mark.asyncio
async def test_governance_mutate_never_uses_global_get_by_id() -> None:
    store = MagicMock()
    event_id = uuid4()
    store.get_by_id = AsyncMock()
    store.get_by_id_for_tenant = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as exc:
        await get_event_for_governance_mutate(
            store,
            event_id,
            ctx_tenant_id="tenant-a",
            roles=["admin"],
        )
    assert exc.value.status_code == 404
    store.get_by_id.assert_not_called()
    store.get_by_id_for_tenant.assert_awaited_once_with(event_id, "tenant-a")
