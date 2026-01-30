"""
Real-time Gateway — WebSockets for live events, metrics, agent status, audit feed.

- Live events stream
- Live metrics
- Live agent status
- Live audit feed
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/realtime", tags=["Realtime"])


class ConnectionManager:
    """Broadcast to all connected WebSocket clients."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._subscriptions: dict[WebSocket, set[str]] = {}  # ws -> set of channels

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        self._subscriptions[websocket] = set()

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)
        self._subscriptions.pop(websocket, None)

    def subscribe(self, websocket: WebSocket, channel: str) -> None:
        self._subscriptions.setdefault(websocket, set()).add(channel)

    def unsubscribe(self, websocket: WebSocket, channel: str) -> None:
        self._subscriptions.get(websocket, set()).discard(channel)

    async def broadcast(self, channel: str, payload: dict[str, Any]) -> None:
        dead = []
        for ws in self._connections:
            if channel not in self._subscriptions.get(ws, set()) and "*" not in self._subscriptions.get(ws, set()):
                continue
            try:
                await ws.send_json({"channel": channel, "data": payload})
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


_manager = ConnectionManager()


async def publish_event(channel: str, data: dict[str, Any]) -> None:
    """Call from pipeline/workers to push live updates."""
    await _manager.broadcast(channel, data)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Single WebSocket: client sends { "subscribe": "events" | "metrics" | "agents" | "audit" | "*" } to subscribe."""
    await _manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("subscribe"):
                    _manager.subscribe(websocket, msg["subscribe"])
                if msg.get("unsubscribe"):
                    _manager.unsubscribe(websocket, msg["unsubscribe"])
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        _manager.disconnect(websocket)


@router.get("/events/stream")
async def sse_events_stream() -> Any:
    """SSE endpoint for live events (alternative to WebSocket)."""
    from fastapi.responses import StreamingResponse
    import queue
    q: queue.Queue = queue.Queue()

    async def gen() -> Any:
        while True:
            try:
                item = await asyncio.get_event_loop().run_in_executor(None, q.get, True)
                yield f"data: {json.dumps(item)}\n\n"
            except Exception:
                break
    return StreamingResponse(gen(), media_type="text/event-stream")
