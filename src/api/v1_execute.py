"""
Execution API — Run outbound commands (Notion, WhatsApp, Calendar, Email, Slack) with audit and optional approval.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.auth.tenant_context import get_tenant_context
from src.core.structured_logging import log_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["execute"])


class ExecuteRequest(BaseModel):
    command_type: str
    payload: dict[str, Any]
    require_approval: bool = False


@router.post("/execute")
async def execute(request: Request, req: ExecuteRequest) -> dict[str, Any]:
    """
    Execute a command (create_notion_task, update_notion_task, send_whatsapp, create_calendar_event, send_email, post_slack).
    update_notion_task payload: node_id, optional title, status, due_date (ISO). Node must have notion_page_id in metadata.
    If require_approval=True, enqueue to pending and return pending_id; otherwise run immediately and audit.
    Tenant, space, and user are taken only from the authenticated context (JWT / SKIP_AUTH), never from the request body.
    """
    from src.core.execution_engine import execute_command, CommandType, HIGH_RISK_COMMANDS
    from src.core.pending_executions import PendingExecutionsStore

    try:
        CommandType(req.command_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown command_type: {req.command_type}")

    ctx = get_tenant_context(request)
    tenant_id = ctx.tenant_id
    user_id = ctx.user_id
    space_id = ctx.space_id or "all"
    log_json(
        logger,
        "info",
        "execute_request",
        tenant_id=tenant_id,
        user_id=user_id,
        command_type=req.command_type,
        require_approval=req.require_approval,
    )

    cmd_enum = CommandType(req.command_type)
    require_approval = req.require_approval or cmd_enum in HIGH_RISK_COMMANDS

    if require_approval:
        store = PendingExecutionsStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
        await store.connect()
        pending_id = await store.add(
            tenant_id=tenant_id,
            user_id=user_id,
            space_id=space_id,
            command_type=req.command_type,
            payload=req.payload,
        )
        return {"ok": True, "pending_id": pending_id, "message": "Command queued for approval"}

    result = await execute_command(
        command_type=req.command_type,
        payload=req.payload,
        tenant_id=tenant_id,
        user_id=user_id,
        space_id=space_id,
    )
    if result.get("governance_denied"):
        raise HTTPException(status_code=403, detail=result.get("error", "governance_denied"))
    if result.get("requires_approval"):
        raise HTTPException(status_code=403, detail=result.get("error", "requires_approval"))
    return {"ok": result.get("ok", False), "result": result}


@router.get("/execute/pending")
async def list_pending(request: Request, user_id: str | None = None) -> dict[str, Any]:
    """List pending commands awaiting approval for the authenticated tenant."""
    from src.core.pending_executions import PendingExecutionsStore

    ctx = get_tenant_context(request)
    store = PendingExecutionsStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
    await store.connect()
    items = await store.list_pending(tenant_id=ctx.tenant_id, user_id=user_id or ctx.user_id)
    return {"ok": True, "pending": items}


@router.post("/execute/approve/{pending_id}")
async def approve_and_execute(request: Request, pending_id: str) -> dict[str, Any]:
    """Approve a pending command and run it. Returns execution result."""
    from src.core.pending_executions import PendingExecutionsStore
    from src.core.execution_engine import execute_command

    ctx = get_tenant_context(request)
    store = PendingExecutionsStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
    await store.connect()
    doc = await store.get(pending_id, ctx.tenant_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Pending command not found")
    if doc.get("status") != "pending":
        raise HTTPException(status_code=400, detail=f"Command status is {doc.get('status')}")

    result = await execute_command(
        command_type=doc["command_type"],
        payload=doc["payload"],
        tenant_id=doc["tenant_id"],
        user_id=doc["user_id"],
        space_id=doc["space_id"],
        governance_approved=True,
    )
    await store.set_status(pending_id, "executed", executed_result=result)
    return {"ok": True, "pending_id": pending_id, "result": result}


@router.post("/execute/reject/{pending_id}")
async def reject_pending(request: Request, pending_id: str) -> dict[str, Any]:
    """Reject a pending command without executing."""
    from src.core.pending_executions import PendingExecutionsStore

    ctx = get_tenant_context(request)
    store = PendingExecutionsStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
    await store.connect()
    doc = await store.get(pending_id, ctx.tenant_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Pending command not found")
    if doc.get("status") != "pending":
        raise HTTPException(status_code=400, detail=f"Command status is {doc.get('status')}")
    await store.set_status(pending_id, "rejected")
    return {"ok": True, "pending_id": pending_id, "message": "Command rejected"}
