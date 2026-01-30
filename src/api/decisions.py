"""
Decisions API — minimal JSON endpoints for the frontend.

Backs:
- GET /api/decisions
- GET /api/decisions/{id}
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List

from fastapi import APIRouter, Query

from src.schemas.api_models import (
    Decision,
    DecisionsListResponse,
    DecisionItemResponse,
)


router = APIRouter(prefix="/api/decisions", tags=["Decisions"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _demo_decision(
    decision_id: str,
    tenant_id: str,
    space_id: str | None,
    agent_id: str,
) -> Decision:
    created = datetime.now(timezone.utc) - timedelta(minutes=5)
    return Decision(
        id=decision_id,
        createdAt=created.isoformat().replace("+00:00", "Z"),
        tenantId=tenant_id,
        spaceId=space_id,
        agentId=agent_id,
        workflowId=None,
        inputs=[],
        trace=[],
        output={"summary": "Placeholder decision output"},
        confidence=0.9,
        status="completed",
        errorMessage=None,
    )


@router.get("", response_model=DecisionsListResponse)
async def list_decisions(
    agentId: str | None = Query(None),
    tenantId: str | None = Query(None),
    spaceId: str | None = Query(None),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
) -> DecisionsListResponse:
    """
    List decisions (placeholder implementation).
    """
    tenant = tenantId or "demo-tenant"
    space = spaceId or "default-space"
    agent = agentId or "demo-agent"
    decisions: List[Decision] = [
        _demo_decision("dec-1", tenant, space, agent),
        _demo_decision("dec-2", tenant, space, agent),
    ]
    return DecisionsListResponse(
        data=decisions,
        meta={
            "placeholder": True,
            "tenantId": tenant,
            "spaceId": space,
            "agentId": agent,
            "from": from_,
            "to": to,
        },
    )


@router.get("/{decision_id}", response_model=DecisionItemResponse)
async def get_decision(
    decision_id: str,
    tenantId: str | None = Query(None),
    spaceId: str | None = Query(None),
) -> DecisionItemResponse:
    """
    Get a single decision (placeholder).
    """
    tenant = tenantId or "demo-tenant"
    space = spaceId or "default-space"
    decision = _demo_decision(decision_id, tenant, space, "demo-agent")
    return DecisionItemResponse(data=decision, meta={"placeholder": True})

