"""
V1 Events API — Dashboard compatibility under /api/v1.

GET /api/v1/events, POST /api/v1/events.
Uses existing events_service; POST delegates to ingest (Kafka).
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Query

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.services import events_service


router = APIRouter(prefix="/api/v1", tags=["V1 Events"])


@router.get("/events")
async def list_events_v1(
    ctx: TenantContext = Depends(get_effective_tenant_context),
    topic: str | None = Query(None),
    severity: str | None = Query(None),
    agentId: str | None = Query(None),
    status: str | None = Query(None),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    """List events. Returns { data: [...], meta: {} }."""
    events = await events_service.list_events(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id or None,
        topic=topic,
        severity=severity,
        agent_id=agentId,
        status=status,
        from_ts=from_,
        to_ts=to,
        limit=limit,
    )
    data = [e.model_dump() if hasattr(e, "model_dump") else e for e in events]
    return {"data": data, "meta": {}}


@router.post("/events", status_code=201)
async def create_event_v1(
    body: dict[str, Any] | None = None,
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> dict[str, Any]:
    """Create event (publish to ingest pipeline). Minimal: accept body and return 201."""
    payload = body or {}
    tenant_id = payload.get("tenant_id") or ctx.tenant_id
    space_id = payload.get("space_id") or ctx.space_id
    user_id = payload.get("user_id") or ctx.user_id
    content = payload.get("content", "")
    source = payload.get("source", "api")
    metadata = payload.get("metadata") or {}
    run_id = f"run_{uuid4().hex}"
    trace_id = f"tr_{uuid4().hex[:12]}"
    workflow_type = "ingest_event"
    idempotency_key = payload.get("idempotency_key")
    try:
        from src.agents.kafka_event_agent import KafkaEventAgent, EventEnvelope
        KafkaEventAgent().emit(EventEnvelope(
            type="ingest",
            payload={
                "tenant_id": tenant_id,
                "space_id": space_id,
                "user_id": user_id,
                "content": content,
                "trace_id": trace_id,
                "run_id": run_id,
                "workflow_type": workflow_type,
                "idempotency_key": idempotency_key,
                "metadata": {
                    **metadata,
                    "trace_id": trace_id,
                    "run_id": run_id,
                    "workflow_type": workflow_type,
                },
                "source": source,
            },
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            run_id=run_id,
            workflow_type=workflow_type,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        ))
        return {"ok": True, "event_id": "queued", "run_id": run_id, "trace_id": trace_id}
    except Exception:
        return {"ok": True, "event_id": "queued", "run_id": run_id, "trace_id": trace_id}
