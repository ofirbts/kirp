"""
Slack Integration — Inbound + Outbound.

- Inbound: messages, files → Events
- Outbound: post messages, create channels → Actions
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SlackIntegration:
    """Slack API client."""

    def __init__(self) -> None:
        import os
        self._token = os.getenv("SLACK_BOT_TOKEN", "")
        self._client: Any = None

    def connect(self) -> None:
        if not self._token:
            logger.warning("SLACK_BOT_TOKEN missing; integration disabled")
            return
        try:
            from slack_sdk import WebClient
            self._client = WebClient(token=self._token)
            logger.info("SlackIntegration connected")
        except Exception as e:
            logger.error("SlackIntegration init failed: %s", e)

    async def post_message(self, channel: str, text: str, user_id: str = "system") -> dict[str, Any]:
        """Post message to channel. Outbound action."""
        if not self._client:
            self.connect()
        if not self._client:
            return {"ok": False, "error": "Slack not configured"}
        try:
            from slack_sdk import WebClient
            r = self._client.chat_postMessage(channel=channel, text=text)
            return {"ok": True, "ts": r.get("ts")}
        except Exception as e:
            logger.error("Slack post failed: %s", e)
            return {"ok": False, "error": str(e)}

    def parse_webhook(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse Slack event payload into ingestion events."""
        events: list[dict[str, Any]] = []
        if body.get("type") == "event_callback":
            ev = body.get("event", {})
            if ev.get("type") == "message" and "text" in ev:
                events.append({
                    "source": "slack",
                    "channel": ev.get("channel"),
                    "user": ev.get("user"),
                    "text": ev.get("text", ""),
                    "ts": ev.get("ts"),
                })
        return events
