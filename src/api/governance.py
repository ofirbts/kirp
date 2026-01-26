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

from fastapi import APIRouter, HTTPException, Query

from src.core.event_store import EventStore
from src.core.governance import GovernanceEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/governance", tags=["Governance"])


async def _get_event_store() -> EventStore:
    """Get event store instance."""
    import os
    store = EventStore(os.getenv("MONGO_URI", "mongodb://root:example@mongodb:27017/kirp?authSource=admin"))
    await store.connect()
    return store


@router.get("/approvals")
async def get_pending_approvals(limit: int = Query(200, le=1000)) -> dict[str, Any]:
    """
    Get all events waiting for approval (human_approval_required).
    """
    store = await _get_event_store()
    # Query events with event_type=human_approval_required that haven't been resolved
    # Check for resolution events (governance_approval/governance_rejection) to filter
    all_events = await store.list(tenant_id="*", limit=limit * 2, allow_all_tenants=True)
    approval_events = [e for e in all_events if e.event_type == "human_approval_required"]
    resolution_ids = {
        e.metadata.get("original_event_id")
        for e in all_events
        if e.event_type in ("governance_approval", "governance_rejection")
    }
    pending = [e for e in approval_events if str(e.id) not in resolution_ids][:limit]
    return {"pending": [e.to_json_payload() for e in pending], "count": len(pending)}


@router.post("/approve/{event_id}")
async def approve_event(event_id: str) -> dict[str, Any]:
    """
    Approve a tool/action requiring human approval.
    Marks event as resolved + decision=approved.
    """
    from uuid import UUID
    store = await _get_event_store()
    ev = await store.get_by_id(UUID(event_id))
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    # Emit resolution event (event-sourced: no mutation, only new events)
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

    # TODO: Trigger the tool/action that originally requested approval
    # based on ev.payload

    return {"status": "approved", "event_id": event_id}


@router.post("/reject/{event_id}")
async def reject_event(event_id: str) -> dict[str, Any]:
    """
    Reject a request requiring human approval.
    """
    from uuid import UUID
    store = await _get_event_store()
    ev = await store.get_by_id(UUID(event_id))
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    # Emit resolution event
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
    event_type: str | None = Query(None),
    tenant_id: str | None = Query(None),
    limit: int = Query(200, le=2000),
) -> dict[str, Any]:
    """
    Get events for audit purposes.
    If event_type not provided, returns all recent events.
    """
    store = await _get_event_store()
    if tenant_id:
        events = await store.list(tenant_id=tenant_id, limit=limit)
    else:
        # Get from all tenants (admin operation)
        events = await store.list(tenant_id="*", limit=limit, allow_all_tenants=True)

    if event_type:
        events = [e for e in events if e.event_type == event_type]

    return {
        "events": [e.to_json_payload() for e in events],
        "count": len(events),
        "filter": {"event_type": event_type, "tenant_id": tenant_id, "limit": limit},
    }


@router.post("/policy-simulate")
async def policy_simulate(
    policy_id: str,
    change_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Simulate policy changes.
    Placeholder — ready for connection to policy engine.
    """
    store = await _get_event_store()
    gov = GovernanceEngine()

    # TODO: Call policy_engine to calculate real risk/impact
    simulated_risk = 0.37  # placeholder
    impacted_events = await store.list(tenant_id="*", limit=100, allow_all_tenants=True)
    approval_events = [e for e in impacted_events if e.event_type == "human_approval_required"]

    return {
        "policy_id": policy_id,
        "proposed_changes": change_set or {},
        "simulated_risk": simulated_risk,
        "impacted_events_sample": [e.to_json_payload() for e in approval_events[:10]],
    }
