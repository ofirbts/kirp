"""
V1 Notifications API — List, mark read, unread count.
Uses JWT for tenant_id / user_id when authenticated (same as other v1 endpoints).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

import logging

logger = logging.getLogger(__name__)

from src.core.notifications import get_notification_store
from src.auth.tenant_context import get_tenant_context

router = APIRouter(prefix="/api/v1", tags=["V1 Notifications"])


def _ctx_ids(request: Request) -> tuple[str, str]:
    """Derive tenant_id and user_id from JWT context."""
    ctx = get_tenant_context(request)
    return ctx.tenant_id, ctx.user_id


@router.get("/notifications")
async def list_notifications_v1(
    request: Request,
    tenant_id: str = Query("default", description="Ignored when auth present"),
    user_id: str = Query("default", description="Ignored when auth present"),
    limit: int = Query(50, ge=1, le=200),
    type: str | None = Query(None, description="Filter by type"),
) -> list[dict[str, Any]]:
    """List notifications (all or filtered by type). Tenant/user from JWT."""
    tid, uid = _ctx_ids(request)
    store = get_notification_store()
    try:
        await store.connect()
        notifications = await store.list_all(tid, uid, limit=limit, type_filter=type)
        return [n.to_json() for n in notifications]
    except Exception as e:
        logger.warning("list_notifications_v1 failed (returning empty list): %s", e)
        return []


@router.get("/notifications/unread-count")
async def unread_count_v1(request: Request) -> dict[str, Any]:
    """Get unread notification count. Tenant/user from JWT."""
    tid, uid = _ctx_ids(request)
    store = get_notification_store()
    try:
        await store.connect()
        count = await store.unread_count(tid, uid)
    except Exception as e:
        logger.warning("unread_count_v1 failed (returning 0): %s", e)
        count = 0
    return {"unread_count": count}


@router.post("/notifications/read-all")
async def mark_all_read_v1(request: Request) -> dict[str, Any]:
    """Mark all notifications as read for tenant/user. Tenant/user from JWT."""
    tid, uid = _ctx_ids(request)
    store = get_notification_store()
    try:
        await store.connect()
        count = await store.mark_all_read(tid, uid)
    except Exception as e:
        logger.warning("mark_all_read_v1 failed (no notifications updated): %s", e)
        count = 0
    try:
        from src.api.ws_notifications import push_unread_count
        await push_unread_count(tid, uid, 0)
    except Exception:
        pass
    return {"ok": True, "marked_count": count}


@router.post("/notifications/{notification_id}/read")
async def mark_read_v1(notification_id: str) -> dict[str, Any]:
    """Mark one notification as read."""
    store = get_notification_store()
    await store.connect()
    ok = await store.mark_read(notification_id)
    return {"ok": ok}
