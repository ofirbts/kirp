import os
import requests
import logging
from app.services.notion.base import NotionAdapter

logger = logging.getLogger(__name__)

class RealNotionService(NotionAdapter):
    def __init__(self):
        self.token = os.getenv("NOTION_TOKEN")
        self.database_id = os.getenv("NOTION_DATABASE_ID")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    def enabled(self) -> bool:
        """בדיקה האם Notion מוגדר במערכת"""
        return bool(self.token and self.database_id)

    def create_task(self, title: str, trace_id: str = "N/A", source: str = "KIRP Agent"):
        """יצירת משימה חדשה ב-Notion עם סטטוס Backlog"""
        if not self.enabled():
            logger.warning("⚠️ Notion Service disabled or missing config")
            return None
        
        url = "https://api.notion.com/v1/pages"
        payload = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Name": {"title": [{"text": {"content": title}}]},
                "Source": {"rich_text": [{"text": {"content": source}}]},
                "TraceID": {"rich_text": [{"text": {"content": trace_id}}]},
                "Status": {"select": {"name": "Backlog"}}
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            if response.status_code == 200:
                logger.info(f"✅ Notion task created: {trace_id}")
                return response.json()
            else:
                logger.error(f"❌ Notion API Error: {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to connect to Notion: {e}")
            return None