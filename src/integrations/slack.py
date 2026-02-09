"""
Slack Integration — Inbound + Outbound.

- Inbound: messages, files → Events
- Outbound: post messages, create channels → Actions
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class SlackIntegration:
    """Slack API client. Supports OAuth token or SLACK_BOT_TOKEN env."""

    def __init__(self, access_token: str | None = None) -> None:
        import os
        self._token = access_token or os.getenv("SLACK_BOT_TOKEN", "")
        self._client: Any = None

    def connect(self, access_token: str | None = None) -> None:
        token = access_token or self._token
        if not token:
            logger.warning("Slack token missing; integration disabled")
            return
        try:
            from slack_sdk import WebClient
            self._client = WebClient(token=token)
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
        """Parse Slack event payload into unified ingestion events (tenant_id etc. must be set by caller)."""
        events: list[dict[str, Any]] = []
        if body.get("type") == "event_callback":
            ev = body.get("event", {})
            if ev.get("type") == "message" and "text" in ev:
                ts = ev.get("ts", "")
                events.append({
                    "source": "slack",
                    "content": ev.get("text", ""),
                    "metadata": {"external_id": ts, "channel": ev.get("channel"), "user": ev.get("user"), "ts": ts},
                })
        return events

    async def fetch_recent_messages(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str,
        channel_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        Pull messages from a channel (conversations.history). Returns (unified payloads, next_cursor).
        Each payload has source=slack, metadata.external_id=ts for idempotency.
        """
        if not self._client:
            self.connect()
        if not self._client:
            return [], None
        try:
            from slack_sdk import WebClient
            kwargs: dict[str, Any] = {"channel": channel_id, "limit": limit}
            if cursor:
                kwargs["cursor"] = cursor
            r = await asyncio.to_thread(lambda: self._client.conversations_history(**kwargs))
            events = []
            for msg in r.get("messages", []):
                ts = msg.get("ts")
                if not ts or msg.get("subtype") == "bot_message":
                    continue
                text = msg.get("text", "")
                events.append({
                    "tenant_id": tenant_id,
                    "space_id": space_id,
                    "user_id": user_id,
                    "source": "slack",
                    "content": text,
                    "metadata": {"external_id": ts, "channel": channel_id, "user": msg.get("user"), "ts": ts},
                })
            next_cursor = r.get("response_metadata", {}).get("next_cursor") or None
            return events, next_cursor
        except Exception as e:
            logger.error("Slack fetch_recent_messages failed: %s", e)
            return [], None
