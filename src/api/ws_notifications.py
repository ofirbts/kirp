"""
WebSocket for real-time notifications. Subscribe by tenant_id + user_id.
Pushes new notifications and unread count updates.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Notifications WS"])


class NotificationWSManager:
    """Per-user subscription: (tenant_id, user_id) -> list of WebSockets."""

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], list[WebSocket]] = {}

    def _key(self, tenant_id: str, user_id: str) -> tuple[str, str]:
        return (tenant_id or "default", user_id or "default")

    async def connect(self, websocket: WebSocket, tenant_id: str, user_id: str) -> None:
        await websocket.accept()
        key = self._key(tenant_id, user_id)
        self._by_key.setdefault(key, []).append(websocket)

    def disconnect(self, websocket: WebSocket, tenant_id: str, user_id: str) -> None:
        key = self._key(tenant_id, user_id)
        if key in self._by_key:
            self._by_key[key] = [ws for ws in self._by_key[key] if ws != websocket]
            if not self._by_key[key]:
                del self._by_key[key]

    async def broadcast_to_user(self, tenant_id: str, user_id: str, payload: dict[str, Any]) -> None:
        key = self._key(tenant_id, user_id)
        for ws in self._by_key.get(key, [])[:]:
            try:
                await ws.send_json(payload)
            except Exception:
                self._by_key[key] = [w for w in self._by_key[key] if w != ws]


_notification_ws_manager = NotificationWSManager()


async def push_notification_to_user(tenant_id: str, user_id: str, notification: dict[str, Any], unread_count: int) -> None:
    """Call from NotificationStore or API when a new notification is created."""
    await _notification_ws_manager.broadcast_to_user(tenant_id, user_id, {
        "type": "notification",
        "notification": notification,
        "unread_count": unread_count,
    })


async def push_unread_count(tenant_id: str, user_id: str, unread_count: int) -> None:
    await _notification_ws_manager.broadcast_to_user(tenant_id, user_id, {"type": "unread_count", "unread_count": unread_count})


@router.websocket("/ws/notifications")
async def ws_notifications(
    websocket: WebSocket,
    tenant_id: str = Query("default"),
    user_id: str = Query("default"),
) -> None:
    """Subscribe to notifications for tenant_id + user_id.

    On connect we try to send the current unread count. If the notifications
    store is unavailable (e.g. Mongo not running in dev), we log and continue
    with a 0 count instead of killing the WebSocket, so the client connection
    still succeeds.
    """
    await _notification_ws_manager.connect(websocket, tenant_id, user_id)
    try:
        from src.core.notifications import get_notification_store

        try:
            store = get_notification_store()
            await store.connect()
            count = await store.unread_count(tenant_id, user_id)
        except Exception as e:
            logger.warning(
                "ws_notifications: failed to load initial unread count (defaulting to 0): %s",
                e,
            )
            count = 0

        await websocket.send_json({"type": "unread_count", "unread_count": count})
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("ping"):
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        _notification_ws_manager.disconnect(websocket, tenant_id, user_id)
