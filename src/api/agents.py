"""
Agents API — minimal JSON endpoints for the frontend.

Backs:
- GET  /api/agents
- GET  /api/agents/{id}
- POST /api/agents/{id}/run

These handlers return placeholder data shaped to match the frontend
TypeScript types, and are fully tenant-aware via query/body params.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.schemas.api_models import AgentsListResponse, AgentItemResponse, RunAgentResponse
from src.services import agents_service


router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.get("", response_model=AgentsListResponse)
async def list_agents(
    ctx: TenantContext = Depends(get_effective_tenant_context),
    status: str | None = Query(None),
    type: str | None = Query(None),
) -> AgentsListResponse:
    """List agents (read-only). Tenant/space from JWT; query params validated against context."""
    agents = await agents_service.list_agents(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id,
        status=status,
        agent_type=type,
    )
    return AgentsListResponse(data=agents, meta={})


@router.get("/{agent_id}", response_model=AgentItemResponse)
async def get_agent(
    agent_id: str,
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> AgentItemResponse:
    """Get a single agent (read-only). Tenant/space from JWT; query params validated against context."""
    agent = await agents_service.get_agent(
        agent_id=agent_id,
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id,
    )
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentItemResponse(data=agent, meta={})


@router.post("/{agent_id}/run", response_model=RunAgentResponse)
async def run_agent(
    agent_id: str,
    ctx: TenantContext = Depends(get_effective_tenant_context),
    body: dict | None = None,
) -> RunAgentResponse:
    """Enqueue agent run. Returns run_id; poll GET /api/agents/runs/{run_id} for status."""
    from src.core.agent_engine import AgentRun, AgentRunState, get_agent_engine
    from uuid import uuid4

    engine = get_agent_engine()
    run = AgentRun(
        run_id=uuid4(),
        agent_name=agent_id,
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id or "private",
        user_id=ctx.user_id or "system",
        trigger="manual",
        input_context=dict(body or {}),
    )
    await engine.enqueue_run(run)
    return RunAgentResponse(data={"decisionId": str(run.run_id), "status": AgentRunState.IDLE.value}, meta={})


@router.get("/runs/{run_id}")
async def get_agent_run_status(
    run_id: str,
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> dict:
    """Get agent run status (idle → running → completed | failed)."""
    from uuid import UUID
    from src.core.agent_engine import get_agent_engine

    try:
        engine = get_agent_engine()
        state = await engine.get_run_state(UUID(run_id))
        if not state:
            raise HTTPException(status_code=404, detail="Run not found")
        return {"runId": run_id, "status": state.get("state", "idle"), "output": state.get("output"), "error": state.get("error")}
    except ValueError:
        raise HTTPException(status_code=404, detail="Run not found")
