"""
Events API — minimal JSON endpoints for the frontend.

Backs:
- GET  /api/events
- GET  /api/events/dlq
- POST /api/events/{id}/replay
- POST /api/events/dlq/{id}/retry

All endpoints are tenant-aware and return placeholder JSON.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.schemas.api_models import EventsListResponse
from src.services import events_service


router = APIRouter(prefix="/api/events", tags=["Events"])


@router.get("", response_model=EventsListResponse)
async def list_events(
    ctx: TenantContext = Depends(get_effective_tenant_context),
    topic: str | None = Query(None),
    severity: str | None = Query(None),
    agentId: str | None = Query(None),
    status: str | None = Query(None),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
) -> EventsListResponse:
    """List events (read-only). Tenant/space from JWT; query params validated against context."""
    events = await events_service.list_events(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id,
        topic=topic,
        severity=severity,
        agent_id=agentId,
        status=status,
        from_ts=from_,
        to_ts=to,
    )
    return EventsListResponse(data=events, meta={})


@router.get("/dlq", response_model=EventsListResponse)
async def list_dlq_events(
    ctx: TenantContext = Depends(get_effective_tenant_context),
    topic: str | None = Query(None),
    agentId: str | None = Query(None),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
) -> EventsListResponse:
    """List dead-letter queue events (read-only). Tenant/space from JWT; query params validated against context."""
    events = await events_service.list_dlq_events(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id,
        topic=topic,
        agent_id=agentId,
        from_ts=from_,
        to_ts=to,
    )
    return EventsListResponse(data=events, meta={})


@router.post("/{event_id}/replay")
async def replay_event(
    event_id: str,
    ctx: TenantContext = Depends(get_effective_tenant_context),
    body: dict[str, Any] = Body(default={}),
) -> dict[str, Any]:
    """Replay an event: returns payload for re-ingest (caller can POST to ingest or publish to Kafka)."""
    try:
        payload = await events_service.replay_event(event_id, ctx.tenant_id)
        return {"ok": True, "payload": payload}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/dlq/{event_id}/retry")
async def retry_dlq_event(
    event_id: str,
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> dict[str, Any]:
    """Return DLQ event payload for retry; caller re-ingests via POST /api/v1/ingest or Kafka."""
    try:
        payload = await events_service.retry_dlq_event(event_id, ctx.tenant_id)
        return {"ok": True, "payload": payload}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

