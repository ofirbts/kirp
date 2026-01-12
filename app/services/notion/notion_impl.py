# app/services/notion/notion_impl.py
import os
import logging
from datetime import datetime
from notion_client import Client
from .base import NotionAdapter

logger = logging.getLogger(__name__)

class RealNotionService(NotionAdapter):
    def __init__(self):
        token = os.getenv("NOTION_TOKEN")
        # שים לב לשם המשתנה - ב-Docker שלך זה NOTION_TASKS_DB_ID
        self.db_id = os.getenv("NOTION_TASKS_DB_ID")

        if not token or token in ["mock", "YOUR_NOTION_TOKEN"]:
            self.client = None
            logger.warning("Notion Token is missing or mock.")
        else:
            self.client = Client(auth=token)
            logger.info("Notion Client connected successfully.")

    def enabled(self) -> bool:
        return self.client is not None and self.db_id is not None

    def create_task(self, title: str, trace_id: str = "N/A", source: str = "KIRP Agent", confidence: float = 1.0):
        if not self.enabled():
            return None

        try:
            return self.client.pages.create(
                parent={"database_id": self.db_id},
                properties={
                    "Name": {"title": [{"text": {"content": title}}]},
                    "Trace ID": {"rich_text": [{"text": {"content": trace_id}}]},
                    "Source": {"select": {"name": source}},
                    # אם הוספת שדה 'Created' בנשן מסוג Date:
                    "Created": {"date": {"start": datetime.utcnow().isoformat()}}
                },
            )
        except Exception as e:
            logger.error(f"Notion Page Creation Failed: {e}")
            return None

    def get_pending_approvals(self):
        if not self.enabled(): return []
        # כאן אפשר להוסיף שאילתה שמחפשת דפים שבהם הסטטוס הוא 'Pending'
        try:
            results = self.client.databases.query(
                database_id=self.db_id,
                filter={"property": "Status", "status": {"equals": "Pending Approval"}}
            ).get("results", [])
            return results
        except:
            return []