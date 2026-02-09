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
        self._database_id = (
            database_id
            or os.getenv("NOTION_TASKS_DB_ID")
            or os.getenv("NOTION_DATABASE_ID", "")
        )
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

    def _page_title_and_meta(self, page: dict[str, Any], page_id: str) -> tuple[str, dict[str, Any]]:
        """Extract title and metadata from a Notion page/database result."""
        props = page.get("properties", {})
        title = ""
        for key in ("Name", "title", "Title"):
            if key in props and props[key].get("title"):
                title = " ".join(t.get("plain_text", "") for t in props[key]["title"])
                break
        meta: dict[str, Any] = {
            "page_id": page_id,
            "external_id": page_id,
            "url": page.get("url"),
        }
        if page.get("last_edited_time"):
            meta["last_edited_time"] = page["last_edited_time"]
        return title or "(no title)", meta

    async def ingest_database(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str,
        page_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch database pages and return as event payloads. Optional page_ids to limit to specific pages."""
        if not self._client:
            self.connect()
        if not self._client:
            return []
        events: list[dict[str, Any]] = []
        try:
            if page_ids:
                for page_id in page_ids:
                    payload = await self.fetch_page(page_id, tenant_id, space_id, user_id)
                    if payload:
                        events.append(payload)
                return events
            resp = await self._client.databases.query(database_id=self._database_id)
            for page in resp.get("results", []):
                page_id = page.get("id", "")
                title, meta = self._page_title_and_meta(page, page_id)
                events.append({
                    "tenant_id": tenant_id,
                    "space_id": space_id,
                    "user_id": user_id,
                    "source": "notion",
                    "content": title,
                    "metadata": meta,
                })
        except Exception as e:
            logger.error("Notion ingest failed: %s", e)
        return events

    async def fetch_page(
        self,
        page_id: str,
        tenant_id: str,
        space_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single page by id (for webhook re-sync). Returns same shape as one ingest_database item or None."""
        if not self._client:
            self.connect()
        if not self._client:
            return None
        try:
            page = await self._client.pages.retrieve(page_id=page_id)
            title, meta = self._page_title_and_meta(page, page_id)
            return {
                "tenant_id": tenant_id,
                "space_id": space_id,
                "user_id": user_id,
                "source": "notion",
                "content": title,
                "metadata": meta,
            }
        except Exception as e:
            logger.error("Notion fetch_page failed for %s: %s", page_id, e)
            return None

    async def create_task(self, title: str, trace_id: str, source: str = "KIRP") -> dict[str, Any]:
        """Create a task in Notion database. Returns page_id for bi-directional sync."""
        if not self._client:
            self.connect()
        if not self._client:
            return {"ok": False, "error": "Notion not configured"}
        try:
            created = await self._client.pages.create(
                parent={"database_id": self._database_id},
                properties={
                    "Name": {"title": [{"text": {"content": title}}]},
                },
            )
            page_id = created.get("id", "")
            logger.info("Notion task created: %s trace=%s page_id=%s", title[:50], trace_id, page_id)
            return {"ok": True, "trace_id": trace_id, "page_id": page_id}
        except Exception as e:
            logger.error("Notion create_task failed: %s", e)
            return {"ok": False, "error": str(e)}

    async def update_page(
        self,
        page_id: str,
        title: str | None = None,
        status: str | None = None,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Update a Notion page. Schema mapping: title -> Name, status -> Status (if DB has it), due_date -> Due (ISO string).
        """
        if not self._client:
            self.connect()
        if not self._client:
            return {"ok": False, "error": "Notion not configured"}
        try:
            props: dict[str, Any] = {}
            if title is not None:
                props["Name"] = {"title": [{"text": {"content": title}}]}
            if status is not None:
                props["Status"] = {"select": {"name": status}}
            if due_date is not None:
                props["Due"] = {"date": {"start": due_date}}
            if not props:
                return {"ok": True, "page_id": page_id}
            await self._client.pages.update(page_id=page_id, properties=props)
            logger.info("Notion page updated: %s", page_id)
            return {"ok": True, "page_id": page_id}
        except Exception as e:
            logger.error("Notion update_page failed for %s: %s", page_id, e)
            return {"ok": False, "error": str(e)}
