"""
Event projections.

Translate canonical EventStore events into relational EventModel rows in
Postgres. These are *projections* of the event log, used for fast querying
and analytics; the MongoDB EventStore remains the system of record.
"""

from __future__ import annotations;

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.event_store import Event as EventRecord
from src.models import EventModel


async def project_event(
    session: AsyncSession,
    event: EventRecord,
    *,
    risk_score: Optional[float] = None,
    requires_approval: Optional[bool] = None,
    approved: Optional[bool] = None,
    approved_by: Optional[str] = None,
    approved_at: Optional[datetime] = None,
) -> EventModel:
    """
    Project a canonical EventStore event into the `events` table.

    This function does not commit the session; callers are responsible for
    transaction boundaries.
    """
    model = EventModel(
        id=event.id,
        tenant_id=event.tenant_id,
        space_id=event.space_id,
        user_id=event.user_id,
        source=event.source,
        event_type=event.event_type,
        sensitivity=event.sensitivity.value,
        trace_id=event.trace_id,
        extra=event.metadata or {},
        timestamp=event.timestamp or datetime.utcnow(),
        embedding=event.embedding or None,
        risk_score=risk_score,
        requires_approval=requires_approval if requires_approval is not None else False,
        approved=approved,
        approved_by=approved_by,
        approved_at=approved_at,
    )
    session.add(model)
    await session.flush()
    return model

