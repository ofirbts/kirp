from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException

from src.core.event_store import Event, EventStore


async def get_event_for_governance_mutate(
    store: EventStore,
    event_id: UUID,
    *,
    ctx_tenant_id: str,
    roles: list[str] | None,
) -> Event:
    del roles
    ev = await store.get_by_id_for_tenant(event_id, ctx_tenant_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev
