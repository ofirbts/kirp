"""
V1 Notifications API — List, mark read, unread count.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

import logging

logger = logging.getLogger(__name__)

from src.core.notifications import get_notification_store

router = APIRouter(prefix="/api/v1", tags=["V1 Notifications"])


@router.get("/notifications")
async def list_notifications_v1(
    tenant_id: str = Query("default"),
    user_id: str = Query("default"),
    limit: int = Query(50, ge=1, le=200),
    type: str | None = Query(None, description="Filter by type"),
) -> list[dict[str, Any]]:
    """List notifications (all or filtered by type)."""
    store = get_notification_store()
    try:
        await store.connect()
        notifications = await store.list_all(tenant_id, user_id, limit=limit, type_filter=type)
        return [n.to_json() for n in notifications]
    except Exception as e:
        # In dev / when Mongo is unavailable, fail soft with an empty list so the
        # dashboard keeps working instead of surfacing 500/CORS-like errors.
        logger.warning("list_notifications_v1 failed (returning empty list): %s", e)
        return []


@router.get("/notifications/unread-count")
async def unread_count_v1(
    tenant_id: str = Query("default"),
    user_id: str = Query("default"),
) -> dict[str, Any]:
    """Get unread notification count."""
    store = get_notification_store()
    try:
        await store.connect()
        count = await store.unread_count(tenant_id, user_id)
    except Exception as e:
        # If the notifications store is down, surface 0 instead of crashing the
        # request so the UI does not see connection/CORS failures.
        logger.warning("unread_count_v1 failed (returning 0): %s", e)
        count = 0
    return {"unread_count": count}


@router.post("/notifications/read-all")
async def mark_all_read_v1(
    tenant_id: str = Query("default"),
    user_id: str = Query("default"),
) -> dict[str, Any]:
    """Mark all notifications as read for tenant/user."""
    store = get_notification_store()
    try:
        await store.connect()
        count = await store.mark_all_read(tenant_id, user_id)
    except Exception as e:
        logger.warning("mark_all_read_v1 failed (no notifications updated): %s", e)
        count = 0
    try:
        from src.api.ws_notifications import push_unread_count
        await push_unread_count(tenant_id, user_id, 0)
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
