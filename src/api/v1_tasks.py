"""
V1 Tasks API — Life-object tasks from SchemaEngine.

GET /api/v1/tasks returns tasks (entity=task) with id, title, due_date, source,
source_event_id, tenant_id, space_id, user_id, status.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Body, HTTPException, Request

from src.core.schema_engine import get_schema_engine
from src.auth.tenant_context import get_tenant_context, is_local_or_skip_auth
from src.models.schema import SchemaEntity


router = APIRouter(prefix="/api/v1", tags=["V1 Tasks"])


def _task_from_node(node: dict[str, Any]) -> dict[str, Any]:
    """Map schema node to API task shape."""
    meta = node.get("metadata") or {}
    return {
        "id": node.get("id"),
        "title": node.get("title"),
        "due_date": node.get("due_date"),
        "source": meta.get("source"),
        "source_event_id": meta.get("source_event_id"),
        "tenant_id": node.get("tenant_id"),
        "space_id": node.get("space_id"),
        "user_id": meta.get("user_id"),
        "status": node.get("status"),
    }


@router.get("/tasks")
async def list_tasks_v1(
    request: Request,
    tenant_id: str = Query("default", description="Tenant ID"),  # kept for backwards compat; ignored for auth flows
    space_id: str | None = Query(None, description="Optional space filter"),
    status: str | None = Query(None, description="Optional status filter"),
    limit: int = Query(500, ge=1, le=2000),
) -> dict[str, Any]:
    """
    List tasks from SchemaEngine (entity=task).
    Returns id, title, due_date, source, source_event_id, tenant_id, space_id, user_id, status.
    """
    ctx = get_tenant_context(request)
    # For authenticated flows, always derive tenant_id from context (JWT), not query param.
    tid = ctx.tenant_id
    schema = await get_schema_engine()
    nodes = await schema.list_nodes(
        tenant_id=tid,
        space_id=space_id or ctx.space_id or None,
        entity=SchemaEntity.TASK,
        status=status,
        limit=limit,
        use_cache=False,
    )
    tasks = [_task_from_node(n) for n in nodes]
    return {"data": tasks, "meta": {"tenant_id": tid, "space_id": space_id or ctx.space_id, "count": len(tasks)}}


@router.get("/nodes")
async def list_nodes_v1(
    request: Request,
    tenant_id: str = Query("default", description="Tenant ID"),  # ignored for auth flows; kept for compat
    space_id: str | None = Query(None, description="Optional space filter"),
    entity: str | None = Query(None, description="Filter by entity: task, commitment, project, life_area"),
    status: str | None = Query(None, description="Optional status filter"),
    limit: int = Query(500, ge=1, le=2000),
) -> dict[str, Any]:
    """
    List schema nodes (tasks, commitments, projects, life areas) for Second Brain UI.
    """
    ctx = get_tenant_context(request)
    tid = ctx.tenant_id
    schema = await get_schema_engine()
    entity_enum = None
    if entity:
        try:
            entity_enum = SchemaEntity(entity.strip().lower())
        except ValueError:
            entity_enum = None
    nodes = await schema.list_nodes(
        tenant_id=tid,
        space_id=space_id or ctx.space_id or None,
        entity=entity_enum,
        status=status,
        limit=limit,
        use_cache=False,
    )
    return {"data": nodes, "meta": {"tenant_id": tid, "space_id": space_id or ctx.space_id, "entity": entity, "count": len(nodes)}}


@router.get("/nodes/{node_id}")
async def get_node_v1(
    node_id: str,
    request: Request,
    tenant_id: str = Query("default"),  # ignored for auth flows; kept for compat
) -> dict[str, Any]:
    """Get a single schema node by ID."""
    ctx = get_tenant_context(request)
    tid = ctx.tenant_id
    schema = await get_schema_engine()
    node = await schema.get_node(node_id, tid)
    if not node:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Node not found")
    return {"ok": True, "node": node}


@router.patch("/nodes/{node_id}")
async def update_node_v1(
    node_id: str,
    request: Request,
    tenant_id: str = Query("default"),  # ignored for auth flows; kept for compat
    user_id: str = Query("system"),
    title: str | None = Body(None),
    description: str | None = Body(None),
    status: str | None = Body(None),
    priority: str | None = Body(None),
    due_date: str | None = Body(None),
    parent_id: str | None = Body(None),
) -> dict[str, Any]:
    """Partial update of a schema node (task, commitment, project)."""
    from datetime import datetime, timezone
    ctx = get_tenant_context(request)
    tid = ctx.tenant_id
    schema = await get_schema_engine()
    due_dt = None
    if due_date is not None:
        try:
            due_dt = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
        except ValueError:
            due_dt = None
    updated = await schema.update_node(
        node_id=node_id,
        tenant_id=tid,
        title=title,
        description=description,
        status=status,
        priority=priority,
        due_date=due_dt,
        parent_id=parent_id,
    )
    if not updated:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Node not found")
    if updated.get("entity") == "task":
        try:
            from src.core.notifications import notify_user
            await notify_user(tid, user_id, "task_updated", "Task updated", updated.get("title") or "Task", entity_id=node_id, meta={"task_id": node_id})
        except Exception:
            pass
        try:
            from src.core.history import record_history
            tit = updated.get("title") or "Task"
            if status == "completed":
                await record_history(tid, updated.get("space_id") or "all", user_id, "task_completed", "Task completed: " + tit, tit, source="api", entity_id=node_id)
            else:
                await record_history(tid, updated.get("space_id") or "all", user_id, "task_updated", "Task updated", tit, source="api", entity_id=node_id)
        except Exception:
            pass
    elif updated.get("entity") == "project":
        try:
            from src.core.history import record_history
            tit = updated.get("title") or "Project"
            await record_history(tid, updated.get("space_id") or "all", user_id, "project_updated", "Project updated: " + tit, tit, source="api", entity_id=node_id)
        except Exception:
            pass
    return {"ok": True, "node": updated}


@router.post("/tasks")
async def create_task_v1(
    request: Request,
    tenant_id: str = Query("default"),  # ignored for auth flows; kept for compat
    space_id: str = Query("all"),
    user_id: str = Query("system"),
    title: str = Body(..., embed=True),
    due_date: str | None = Body(None, embed=True),
    status: str | None = Body("pending", embed=True),
    priority: str | None = Body(None, embed=True),
    description: str | None = Body(None, embed=True),
) -> dict[str, Any]:
    """Quick add a task. Creates a schema node with entity=task."""
    from datetime import datetime, timezone
    import uuid as uuid_mod
    ctx = get_tenant_context(request)
    tid = ctx.tenant_id
    schema = await get_schema_engine()
    due_dt = None
    if due_date:
        try:
            due_dt = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
        except ValueError:
            pass
    node_id = str(uuid_mod.uuid4())
    meta = {"source": "dashboard", "user_id": user_id}
    await schema.upsert_node(
        tenant_id=tid,
        space_id=space_id or ctx.space_id or "all",
        entity=SchemaEntity.TASK,
        title=title or "Untitled",
        node_id=node_id,
        description=description,
        status=status or "pending",
        priority=priority,
        due_date=due_dt,
        metadata=meta,
    )
    node = await schema.get_node(node_id, tid)
    task = _task_from_node(node) if node else {"id": node_id, "title": title, "due_date": due_date, "source": "dashboard", "status": status}
    try:
        from src.core.notifications import notify_user
        await notify_user(tid, user_id, "task_created", "Task created", title or "Untitled", space_id=space_id, entity_id=node_id, meta={"task_id": node_id})
    except Exception:
        pass
    try:
        from src.core.history import record_history
        await record_history(tid, space_id, user_id, "task_created", "Task created: " + (title or "Untitled"), title or "Untitled", source="api", entity_id=node_id)
    except Exception:
        pass
    return {"ok": True, "data": task}


@router.post("/nodes")
async def create_node_v1(
    request: Request,
    tenant_id: str = Query("default"),  # ignored for auth flows; kept for compat
    space_id: str = Query("all"),
    user_id: str = Query("system"),
    entity: str = Body("task", embed=True),
    title: str = Body(..., embed=True),
    due_date: str | None = Body(None, embed=True),
    status: str | None = Body(None, embed=True),
    priority: str | None = Body(None, embed=True),
    description: str | None = Body(None, embed=True),
    parent_id: str | None = Body(None, embed=True),
) -> dict[str, Any]:
    """Create a schema node (task, project, commitment, etc.)."""
    from datetime import datetime, timezone
    import uuid as uuid_mod
    ctx = get_tenant_context(request)
    tid = ctx.tenant_id
    try:
        entity_enum = SchemaEntity(entity.strip().lower())
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid entity: {entity}")
    schema = await get_schema_engine()
    due_dt = None
    if due_date:
        try:
            due_dt = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
        except ValueError:
            pass
    node_id = str(uuid_mod.uuid4())
    meta = {"source": "dashboard", "user_id": user_id}
    await schema.upsert_node(
        tenant_id=tid,
        space_id=space_id or ctx.space_id or "all",
        entity=entity_enum,
        title=title or "Untitled",
        node_id=node_id,
        description=description,
        status=status or ("pending" if entity_enum == SchemaEntity.TASK else None),
        priority=priority,
        due_date=due_dt,
        parent_id=parent_id,
        metadata=meta,
    )
    node = await schema.get_node(node_id, tid)
    if entity_enum == SchemaEntity.COMMITMENT:
        try:
            from src.core.history import record_history
            await record_history(tid, space_id or ctx.space_id or "all", user_id, "commitment_created", "Commitment added", title or "Untitled", source="api", entity_id=node_id)
        except Exception:
            pass
    return {"ok": True, "node": node}
