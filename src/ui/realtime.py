"""
Realtime Client — SSE / WebSocket for live event flow, agent activity, notifications.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import httpx

logger = logging.getLogger(__name__)


class RealtimeClient:
    """SSE / WebSocket client for live updates."""

    def __init__(self, base_url: str, token: str | None = None) -> None:
        self._base = base_url.rstrip("/")
        self._token = token

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Accept": "text/event-stream"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def stream_events(self, path: str = "/api/v1/events/stream") -> AsyncIterator[dict[str, Any]]:
        """Consume SSE stream of events."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "GET",
                f"{self._base}{path}",
                headers=self._headers(),
            ) as r:
                r.raise_for_status()
                buffer = ""
                async for chunk in r.aiter_text():
                    buffer += chunk
                    while "\n\n" in buffer:
                        part, buffer = buffer.split("\n\n", 1)
                        for line in part.splitlines():
                            if line.startswith("data: "):
                                try:
                                    yield json.loads(line[6:])
                                except json.JSONDecodeError:
                                    pass
