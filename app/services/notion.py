import os
import requests
from notion_client import Client
from app.core.tenant import TenantContext
from app.core.persistence import PersistenceManager

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")

class NotionService:
    def __init__(self):
        self.client = Client(auth=NOTION_TOKEN) if NOTION_TOKEN != "mock" else None
        self.db_id = NOTION_DB_ID

    def exists(self, trace_id: str) -> bool:
        """בדיקה האם קיים כבר דף עם ה-trace_id הזה כדי למנוע כפילויות ברמת ה-Replay"""
        if not self.client or not trace_id:
            return False
            
        results = self.client.databases.query(
            database_id=self.db_id,
            filter={
                "property": "Trace ID",
                "rich_text": {"equals": trace_id}
            }
        ).get("results")
        return results[0]["id"] if results else None

    def create_task_page(self, title: str, trace_id: str = None, source: str = "Agent"):
        """יצירת משימה אמיתית ב-Notion עם הגנת Idempotency"""
        if NOTION_TOKEN == "mock":
            print(f"🛠️ Mock Notion: Creating task '{title}'")
            return {"id": "mock-uuid", "status": "mock_success"}

        # 1. בדיקת כפילות
        existing_id = self.exists(trace_id)
        if existing_id:
            return {"id": existing_id, "status": "already_exists"}

        # 2. בניית הפרופרטיז לפי הקונטרקט הרשמי
        properties = {
            "Title": {"title": [{"text": {"content": title}}]},
            "Source": {"select": {"name": source}},
            "Tenant": {"rich_text": [{"text": {"content": TenantContext.get()}}]},
            "Memory Plane": {"select": {"name": "session"}},
            "Created By Agent": {"checkbox": True}
        }
        
        if trace_id:
            properties["Trace ID"] = {"rich_text": [{"text": {"content": trace_id}}]}

        # 3. יצירת הדף
        try:
            page = self.client.pages.create(
                parent={"database_id": self.db_id},
                properties=properties
            )
            
            # 4. רישום אירוע ב-Persistence
            PersistenceManager.append_event("notion_page_created", {
                "page_id": page["id"],
                "trace_id": trace_id,
                "tenant": TenantContext.get()
            })
            
            return {"id": page["id"], "status": "success"}
        except Exception as e:
            print(f"❌ Notion Error: {e}")
            return {"status": "error", "message": str(e)}

    def create_kirp_tasks(self, tasks, trace_id: str = None):
        """מעטפת למספר משימות"""
        results = []
        for task in tasks:
            res = self.create_task_page(task.get("title", "Untitled"), trace_id)
            results.append(res)
        return results

# אובייקט סינגלטון לשימוש בכל האפליקציה
notion = NotionService()