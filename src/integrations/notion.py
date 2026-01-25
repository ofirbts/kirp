"""
Notion Integration — Bi-directional.

- Inbound: ingest pages/databases → Events
- Outbound: create/update tasks, pages → Actions
- Real-time: webhooks → Events
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class NotionPage:
    id: str
    title: str
    content: str
    metadata: dict[str, Any]


class NotionIntegration:
    """
    Notion API client. Bi-directional sync.
    """

    def __init__(self, token: str | None = None, database_id: str | None = None) -> None:
        import os
        self._token = token or os.getenv("NOTION_TOKEN", "")
        self._database_id = database_id or os.getenv("NOTION_DATABASE_ID", "")
        self._client: Any = None

    def connect(self) -> None:
        """Initialize Notion client."""
        if not self._token or not self._database_id:
            logger.warning("Notion token/database_id missing; integration disabled")
            return
        try:
            from notion_client import AsyncClient
            self._client = AsyncClient(auth=self._token)
            logger.info("NotionIntegration connected")
        except Exception as e:
            logger.error("NotionIntegration connection failed: %s", e)
            raise

    async def ingest_database(self, tenant_id: str, space_id: str, user_id: str) -> list[dict[str, Any]]:
        """Fetch database pages and return as event payloads for ingestion."""
        if not self._client:
            self.connect()
        if not self._client:
            return []
        events: list[dict[str, Any]] = []
        try:
            resp = await self._client.databases.query(database_id=self._database_id)
            for page in resp.get("results", []):
                props = page.get("properties", {})
                title = ""
                if "title" in props and props["title"].get("title"):
                    title = " ".join(t.get("plain_text", "") for t in props["title"]["title"])
                events.append({
                    "tenant_id": tenant_id,
                    "space_id": space_id,
                    "user_id": user_id,
                    "source": "notion",
                    "content": title,
                    "metadata": {"page_id": page.get("id"), "url": page.get("url")},
                })
        except Exception as e:
            logger.error("Notion ingest failed: %s", e)
        return events

    async def create_task(self, title: str, trace_id: str, source: str = "KIRP") -> dict[str, Any]:
        """Create a task in Notion database. Outbound action."""
        if not self._client:
            self.connect()
        if not self._client:
            return {"ok": False, "error": "Notion not configured"}
        try:
            await self._client.pages.create(
                parent={"database_id": self._database_id},
                properties={
                    "Name": {"title": [{"text": {"content": title}}]},
                },
            )
            logger.info("Notion task created: %s trace=%s", title[:50], trace_id)
            return {"ok": True, "trace_id": trace_id}
        except Exception as e:
            logger.error("Notion create_task failed: %s", e)
            return {"ok": False, "error": str(e)}
