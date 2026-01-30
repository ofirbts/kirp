"""
Workflows API — minimal JSON endpoints for the frontend.

Backs:
- GET  /api/workflows
- GET  /api/workflows/{id}
- POST /api/workflows/{id}/trigger
- GET  /api/workflows/{id}/runs
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.schemas.api_models import (
    WorkflowsListResponse,
    WorkflowItemResponse,
    WorkflowRunsListResponse,
)
from src.services import workflows_service


router = APIRouter(prefix="/api/workflows", tags=["Workflows"])


@router.get("", response_model=WorkflowsListResponse)
async def list_workflows(
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> WorkflowsListResponse:
    """List workflows (read-only, backed by service layer). Tenant context required but not yet used for filtering."""
    workflows = await workflows_service.list_workflows()
    return WorkflowsListResponse(data=workflows, meta={})


@router.get("/{workflow_id}", response_model=WorkflowItemResponse)
async def get_workflow(workflow_id: str) -> WorkflowItemResponse:
    """Get a single workflow (read-only, backed by service layer)."""
    wf = await workflows_service.get_workflow(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowItemResponse(data=wf, meta={})


@router.post("/{workflow_id}/trigger")
async def trigger_workflow(
    workflow_id: str,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """Trigger a workflow. Not implemented yet in Phase 4.1."""
    raise HTTPException(status_code=501, detail="Workflow trigger not implemented yet")


@router.get("/{workflow_id}/runs", response_model=WorkflowRunsListResponse)
async def list_workflow_runs(
    workflow_id: str,
    status: str | None = Query(None),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
) -> WorkflowRunsListResponse:
    """List workflow runs (read-only, backed by service layer)."""
    runs = await workflows_service.list_workflow_runs(
        workflow_id=workflow_id,
        status=status,
        from_ts=from_,
        to_ts=to,
    )
    return WorkflowRunsListResponse(data=runs, meta={})

