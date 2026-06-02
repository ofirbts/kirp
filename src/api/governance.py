"""
Governance API — Approvals, audit, policy simulation.

Endpoints:
- GET /governance/approvals — pending approvals
- POST /governance/approve/{event_id} — approve
- POST /governance/reject/{event_id} — reject
- GET /governance/audit — audit logs
- POST /governance/policy-simulate — policy simulation
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from src.core.event_store import EventStore
from src.core.governance import GovernanceEngine
from src.auth.tenant_context import get_tenant_context
from src.control_plane.access import get_event_for_governance_mutate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/governance", tags=["Governance"])


async def _get_event_store() -> EventStore:
    import os
    store = EventStore(os.getenv("MONGO_URI", "mongodb://root:example@mongodb:27017/kirp?authSource=admin"))
    await store.connect()
    return store


def _effective_list_tenant_id(request: Request, query_tenant_id: str | None) -> str:
    ctx = get_tenant_context(request)
    raw = (query_tenant_id or "").strip()
    if not raw:
        return ctx.tenant_id
    if raw != ctx.tenant_id and "admin" not in (ctx.roles or []):
        raise HTTPException(status_code=403, detail="Tenant scope does not match authenticated context")
    return raw


@router.get("/approvals")
async def get_pending_approvals(
    request: Request,
    limit: int = Query(200, le=1000),
    tenant_id: str | None = Query(None),
) -> dict[str, Any]:
    store = await _get_event_store()
    tid = _effective_list_tenant_id(request, tenant_id)
    all_events = await store.list(tenant_id=tid, limit=limit * 2)
    approval_events = [e for e in all_events if e.event_type == "human_approval_required"]
    resolution_ids = {
        e.metadata.get("original_event_id")
        for e in all_events
        if e.event_type in ("governance_approval", "governance_rejection")
    }
    pending = [e for e in approval_events if str(e.id) not in resolution_ids][:limit]
    return {"pending": [e.to_json_payload() for e in pending], "count": len(pending)}


@router.post("/approve/{event_id}")
async def approve_event(request: Request, event_id: str) -> dict[str, Any]:
    from uuid import UUID

    ctx = get_tenant_context(request)
    store = await _get_event_store()
    ev = await get_event_for_governance_mutate(
        store,
        UUID(event_id),
        ctx_tenant_id=ctx.tenant_id,
        roles=ctx.roles,
    )

    from src.core.event_store import Event, Sensitivity
    from uuid import uuid4
    resolution = Event(
        id=uuid4(),
        tenant_id=ev.tenant_id,
        space_id=ev.space_id,
        user_id=ev.user_id,
        source="governance",
        content=f"Approved event {event_id}",
        metadata={
            "original_event_id": event_id,
            "decision": "approved",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        },
        embedding=[],
        timestamp=datetime.now(timezone.utc),
        sensitivity=Sensitivity.PRIVATE,
        event_type="governance_approval",
        trace_id=ev.trace_id,
    )
    await store.ingest(resolution)

    return {"status": "approved", "event_id": event_id}


@router.post("/reject/{event_id}")
async def reject_event(request: Request, event_id: str) -> dict[str, Any]:
    from uuid import UUID

    ctx = get_tenant_context(request)
    store = await _get_event_store()
    ev = await get_event_for_governance_mutate(
        store,
        UUID(event_id),
        ctx_tenant_id=ctx.tenant_id,
        roles=ctx.roles,
    )

    from src.core.event_store import Event, Sensitivity
    from uuid import uuid4
    resolution = Event(
        id=uuid4(),
        tenant_id=ev.tenant_id,
        space_id=ev.space_id,
        user_id=ev.user_id,
        source="governance",
        content=f"Rejected event {event_id}",
        metadata={
            "original_event_id": event_id,
            "decision": "rejected",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        },
        embedding=[],
        timestamp=datetime.now(timezone.utc),
        sensitivity=Sensitivity.PRIVATE,
        event_type="governance_rejection",
        trace_id=ev.trace_id,
    )
    await store.ingest(resolution)

    return {"status": "rejected", "event_id": event_id}


@router.get("/audit")
async def get_audit_log(
    request: Request,
    event_type: str | None = Query(None),
    tenant_id: str | None = Query(None),
    limit: int = Query(200, le=2000),
) -> dict[str, Any]:
    store = await _get_event_store()
    tid = _effective_list_tenant_id(request, tenant_id)
    events = await store.list(tenant_id=tid, limit=limit)

    if event_type:
        events = [e for e in events if e.event_type == event_type]

    return {
        "events": [e.to_json_payload() for e in events],
        "count": len(events),
        "filter": {"event_type": event_type, "tenant_id": tid, "limit": limit},
    }


@router.post("/policy-simulate")
async def policy_simulate(
    request: Request,
    policy_id: str,
    change_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    import os

    ctx = get_tenant_context(request)
    if "admin" not in (ctx.roles or []):
        raise HTTPException(status_code=403, detail="policy-simulate requires admin role")
    store = await _get_event_store()
    gov = GovernanceEngine(opa_url=os.getenv("OPA_URL"))

    check = await gov.check(
        tenant_id="*",
        space_id="all",
        user_id="system",
        action="simulate",
        resource=policy_id,
        context=change_set or {},
    )
    simulated_risk = check.risk_score if check.risk_score else 0.37
    impacted_events = await store.list(tenant_id="*", limit=100, allow_all_tenants=True)
    approval_events = [e for e in impacted_events if e.event_type == "human_approval_required"]

    return {
        "policy_id": policy_id,
        "proposed_changes": change_set or {},
        "simulated_risk": simulated_risk,
        "impacted_events_sample": [e.to_json_payload() for e in approval_events[:10]],
    }
