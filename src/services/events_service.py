"""
Events service — EventStore-backed list, DLQ, replay, retry.

Uses MongoDB EventStore for events and dlq_events collection for DLQ.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from src.core.event_store import EventStore, Event
from src.schemas.api_models import Event as EventSchema


_store: EventStore | None = None


async def _get_store() -> EventStore:
    global _store
    if _store is None:
        _store = EventStore(os.getenv("MONGO_URI", "mongodb://root:example@mongodb:27017/kirp?authSource=admin"))
        await _store.connect()
    return _store


def _event_to_schema(ev: Event) -> EventSchema:
    return EventSchema(
        id=str(ev.id),
        tenantId=ev.tenant_id,
        spaceId=ev.space_id,
        timestamp=ev.timestamp.isoformat() if ev.timestamp else "",
        topic=ev.event_type,
        severity="info",
        agentId=ev.metadata.get("agent_id"),
        status="delivered",
        payload=ev.to_json_payload(),
        payloadPreview=(ev.content or "")[:200],
        source=ev.source or "api",
    )


async def list_events(
    tenant_id: Optional[str] = None,
    space_id: Optional[str] = None,
    topic: Optional[str] = None,
    severity: Optional[str] = None,
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
    limit: int = 100,  
) -> List[EventSchema]:
    """List events from EventStore. Tenant required for multi-tenant isolation."""
    if not tenant_id:
        return []
    store = await _get_store()
    since = None
    if from_ts:
        try:
            since = datetime.fromisoformat(from_ts.replace("Z", "+00:00"))
        except Exception:
            pass
    events = await store.list(
        tenant_id=tenant_id,
        space_id=space_id or None,
        limit=100,
        since=since,
        agent_id=agent_id,
    )
    if topic:
        events = [e for e in events if e.event_type == topic]
    return [_event_to_schema(e) for e in events]


async def list_dlq_events(
    tenant_id: Optional[str] = None,
    space_id: Optional[str] = None,
    topic: Optional[str] = None,
    agent_id: Optional[str] = None,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
) -> List[EventSchema]:
    """List DLQ events."""
    if not tenant_id:
        return []
    store = await _get_store()
    since = None
    if from_ts:
        try:
            since = datetime.fromisoformat(from_ts.replace("Z", "+00:00"))
        except Exception:
            pass
    events = await store.list_dlq(tenant_id=tenant_id, limit=100, since=since)
    return [_event_to_schema(e) for e in events]


async def replay_event(event_id: str, tenant_id: str) -> dict:
    """Replay: return event payload for re-ingest. Caller can POST to /api/v1/ingest or publish to Kafka."""
    store = await _get_store()
    ev = await store.get_by_id(UUID(event_id))
    if not ev or ev.tenant_id != tenant_id:
        raise ValueError("Event not found or tenant mismatch")
    return await store.replay(ev.id)


async def retry_dlq_event(event_id: str, tenant_id: str) -> dict:
    """Return DLQ event payload for retry. Caller re-ingests."""
    store = await _get_store()
    return await store.retry_dlq(UUID(event_id))
