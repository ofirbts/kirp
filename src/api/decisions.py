"""
Decisions API — JSON endpoints backed by domain store (Mongo).

Backs:
- GET /api/decisions
- GET /api/decisions/{id}
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.core import domain_store
from src.schemas.api_models import (
    Decision,
    DecisionsListResponse,
    DecisionItemResponse,
)


router = APIRouter(prefix="/api/decisions", tags=["Decisions"])


def _doc_to_decision(doc: dict) -> Decision:
    return Decision(
        id=doc["id"],
        createdAt=doc["createdAt"],
        tenantId=doc["tenantId"],
        spaceId=doc.get("spaceId"),
        agentId=doc["agentId"],
        workflowId=doc.get("workflowId"),
        inputs=doc.get("inputs", []),
        trace=doc.get("trace", []),
        output=doc.get("output", {}),
        confidence=doc.get("confidence", 0),
        status=doc.get("status", "completed"),
        errorMessage=doc.get("errorMessage"),
    )


@router.get("", response_model=DecisionsListResponse)
async def list_decisions(
    ctx: TenantContext = Depends(get_effective_tenant_context),
    agentId: str | None = Query(None),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
) -> DecisionsListResponse:
    """List decisions for tenant/space from domain store."""
    since = None
    if from_:
        try:
            since = datetime.fromisoformat(from_.replace("Z", "+00:00"))
        except Exception:
            pass
    docs = await domain_store.list_decisions(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id or None,
        agent_id=agentId,
        limit=100,
        since=since,
    )
    decisions: List[Decision] = [_doc_to_decision(d) for d in docs]
    return DecisionsListResponse(
        data=decisions,
        meta={"tenantId": ctx.tenant_id, "spaceId": ctx.space_id, "from": from_, "to": to},
    )


@router.get("/{decision_id}", response_model=DecisionItemResponse)
async def get_decision(
    decision_id: str,
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> DecisionItemResponse:
    """Get a single decision by id."""
    doc = await domain_store.get_decision(decision_id, ctx.tenant_id)
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Decision not found")
    return DecisionItemResponse(data=_doc_to_decision(doc), meta={})


class CreateDecisionBody(BaseModel):
    agent_id: str
    output: dict
    confidence: float = 0.9
    status: str = "completed"
    inputs: list | None = None
    trace: list | None = None


@router.post("", status_code=201)
async def create_decision(
    body: CreateDecisionBody,
    ctx: TenantContext = Depends(get_effective_tenant_context),
):
    """Create a decision (for seeding)."""
    did = await domain_store.create_decision(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id or "all",
        agent_id=body.agent_id,
        output=body.output,
        confidence=body.confidence,
        status=body.status,
        inputs=body.inputs,
        trace=body.trace,
    )
    return {"ok": True, "id": did}

