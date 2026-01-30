"""
Workflow and Task projections.

Translate workflow definitions and run/task events into relational
projections backed by the `Workflow`, `WorkflowRun`, and `Task` models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Workflow, WorkflowRun, Task


async def upsert_workflow(
    session: AsyncSession,
    *,
    workflow_id: Optional[UUID] = None,
    name: str,
    status: str,
    tenant_id: str,
    space_id: Optional[str] = None,
    description: Optional[str] = None,
    owner_user_id: Optional[str] = None,
    connected_agent_ids: Optional[list[UUID]] = None,
    triggers: Optional[list[str]] = None,
    last_run_at: Optional[str] = None,
) -> Workflow:
    """Insert or update a Workflow projection."""
    wf_id = workflow_id or uuid4()

    stmt = select(Workflow).where(Workflow.id == wf_id)
    result = await session.execute(stmt)
    existing: Optional[Workflow] = result.scalar_one_or_none()

    if existing:
        existing.name = name
        existing.status = status
        existing.description = description
        existing.owner_user_id = owner_user_id
        existing.tenant_id = tenant_id
        existing.space_id = space_id
        existing.connected_agent_ids = list(connected_agent_ids or [])
        existing.triggers = list(triggers or [])
        existing.last_run_at = last_run_at
        await session.flush()
        return existing

    wf = Workflow(
        id=wf_id,
        name=name,
        description=description,
        status=status,
        ownerUserId=owner_user_id,
        tenantId=tenant_id,
        spaceId=space_id,
        connectedAgentIds=list(connected_agent_ids or []),
        triggers=list(triggers or []),
        lastRunAt=last_run_at,
    )
    session.add(wf)
    await session.flush()
    return wf


async def record_workflow_run(
    session: AsyncSession,
    *,
    workflow_id: UUID,
    run_id: Optional[UUID] = None,
    status: str,
    started_at: str,
    finished_at: Optional[str] = None,
    triggered_by: str,
    trigger_ref: Optional[UUID] = None,
    input: Optional[Mapping[str, Any]] = None,
    output: Optional[Mapping[str, Any]] = None,
    logs: Optional[list[str]] = None,
) -> WorkflowRun:
    """Create a WorkflowRun projection row."""
    wr_id = run_id or uuid4()

    wr = WorkflowRun(
        id=wr_id,
        workflowId=workflow_id,
        startedAt=started_at,
        finishedAt=finished_at,
        status=status,
        triggeredBy=triggered_by,
        triggerRef=trigger_ref,
        input=dict(input or {}),
        output=dict(output or {}) if output is not None else None,
        logs=list(logs or []),
    )
    session.add(wr)
    await session.flush()
    return wr


async def record_task(
    session: AsyncSession,
    *,
    task_id: Optional[UUID] = None,
    queue: str,
    status: str,
    created_at: str,
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
    worker_id: Optional[str] = None,
    attempts: int = 0,
    max_attempts: int = 0,
    payload: Optional[Mapping[str, Any]] = None,
    result: Optional[Mapping[str, Any]] = None,
    error: Optional[str] = None,
    logs: Optional[list[str]] = None,
) -> Task:
    """Create or update a Task projection row."""
    t_id = task_id or uuid4()

    stmt = select(Task).where(Task.id == t_id)
    result = await session.execute(stmt)
    existing: Optional[Task] = result.scalar_one_or_none()

    if existing:
        existing.queue = queue
        existing.worker_id = worker_id
        existing.status = status
        existing.created_at = created_at
        existing.started_at = started_at
        existing.finished_at = finished_at
        existing.attempts = attempts
        existing.max_attempts = max_attempts
        existing.payload = dict(payload or {})
        existing.result = dict(result or {}) if result is not None else None
        existing.error = error
        existing.logs = list(logs or []) if logs is not None else existing.logs
        await session.flush()
        return existing

    task = Task(
        id=t_id,
        queue=queue,
        workerId=worker_id,
        status=status,
        createdAt=created_at,
        startedAt=started_at,
        finishedAt=finished_at,
        attempts=attempts,
        maxAttempts=max_attempts,
        payload=dict(payload or {}),
        result=dict(result or {}) if result is not None else None,
        error=error,
        logs=list(logs or []) if logs is not None else None,
    )
    session.add(task)
    await session.flush()
    return task

