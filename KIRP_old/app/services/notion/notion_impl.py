# app/services/notion/notion_impl.py
"""
KIRP Unified Notion Integration v7
Enterprise task sync + metadata + safe fallback
"""

import os
import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class NotionClient:
    """Unified Notion client with enterprise metadata + safe fallback."""

    def __init__(self):
        self.token = os.getenv("NOTION_TOKEN")
        self.database_id = os.getenv("NOTION_DATABASE_ID")
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    def enabled(self) -> bool:
        return bool(self.token and self.database_id)

    def create_task(
        self,
        title: str,
        trace_id: str = "N/A",
        source: str = "KIRP"
    ) -> Optional[Dict[str, Any]]:
        """
        Create a Notion task with enterprise metadata.
        """
        if not self.enabled():
            logger.warning("⚠️ Notion disabled or missing configuration")
            return None

        payload = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Name": {"title": [{"text": {"content": title[:100]}}]},
                "Source": {"rich_text": [{"text": {"content": source}}]},
                "TraceID": {"rich_text": [{"text": {"content": trace_id[:36]}}]},
                "Status": {"select": {"name": "Backlog"}},
                "Created": {
                    "date": {"start": datetime.now(timezone.utc).isoformat()}
                },
            },
        }

        try:
            resp = requests.post(
                f"{self.base_url}/pages",
                json=payload,
                headers=self.headers,
                timeout=10,
            )

            if resp.status_code == 200:
                logger.info(f"📝 Notion task created: {trace_id}")
                return resp.json()

            logger.error(f"❌ Notion API error {resp.status_code}: {resp.text[:200]}")
            return None

        except Exception as e:
            logger.error(f"❌ Notion connection failed: {e}")
            return None

    async def batch_create_tasks(self, tasks: list) -> Dict[str, int]:
        """
        Batch creation for worker pipelines.
        """
        results = {"created": 0, "failed": 0}

        for task in tasks:
            if self.create_task(**task):
                results["created"] += 1
            else:
                results["failed"] += 1

        return results


# Singleton
notion = NotionClient()
