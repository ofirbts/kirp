"""
Tasks API — minimal JSON endpoints for the frontend.

Backs:
- GET  /api/tasks
- GET  /api/tasks/{id}
- POST /api/tasks/{id}/retry
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.schemas.api_models import TasksListResponse, TaskItemResponse
from src.services import tasks_service


router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.get("", response_model=TasksListResponse)
async def list_tasks(
    ctx: TenantContext = Depends(get_effective_tenant_context),
    queue: str | None = Query(None),
    status: str | None = Query(None),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
) -> TasksListResponse:
    """List tasks (read-only, backed by service layer). Tenant context required but not yet used for filtering."""
    tasks = await tasks_service.list_tasks(
        queue=queue,
        status=status,
        from_ts=from_,
        to_ts=to,
    )
    return TasksListResponse(data=tasks, meta={})


@router.get("/{task_id}", response_model=TaskItemResponse)
async def get_task(task_id: str) -> TaskItemResponse:
    """Get a single task (read-only, backed by service layer)."""
    task = await tasks_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskItemResponse(data=task, meta={})


@router.post("/{task_id}/retry")
async def retry_task(task_id: str) -> dict[str, Any]:
    """Queue task for retry. Returns 200; when task store exists, will re-queue."""
    from src.services import tasks_service
    await tasks_service.retry_task(task_id)
    return {"ok": True, "task_id": task_id, "message": "Task queued for retry"}

