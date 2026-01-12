import os
import logging
from dotenv import load_dotenv
from notion_client import Client

# טעינת משתני סביבה
load_dotenv()
logger = logging.getLogger(__name__)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_TASKS_DB_ID")

class NotionService:
    def __init__(self):
        # אתחול בטוח של ה-Client
        if NOTION_TOKEN and NOTION_TOKEN not in ["mock", "YOUR_NOTION_TOKEN"]:
            try:
                self.client = Client(auth=NOTION_TOKEN)
                logger.info("Notion Client initialized")
            except Exception as e:
                logger.error(f"Notion init failed: {e}")
                self.client = None
        else:
            self.client = None
            logger.warning("Notion token missing or mock")
        
        self.db_id = NOTION_DB_ID

    def create_task_page(self, title, trace_id="manual", source="api", confidence=1.0):
        if not self.client or not self.db_id:
            logger.warning("Notion not configured, skipping task creation")
            return None
        
        try:
            new_page = {
                "parent": {"database_id": self.db_id},
                "properties": {
                    "Name": {"title": [{"text": {"content": title}}]},
                    "Source": {"select": {"name": source}}
                }
            }
            return self.client.pages.create(**new_page)
        except Exception as e:
            logger.error(f"Error creating Notion page: {e}")
            return None

    def get_tasks(self):
        if not self.client or not self.db_id:
            return []
        try:
            response = self.client.databases.query(database_id=self.db_id)
            tasks = []
            for page in response.get("results", []):
                props = page.get("properties", {})
                name_obj = props.get("Name", {}).get("title", [])
                title = name_obj[0]["text"]["content"] if name_obj else "Untitled"
                
                status_obj = props.get("Status", {}).get("status") or {}
                status = status_obj.get("name", "Unknown")
                
                tasks.append({"Title": title, "Status": status})
            return tasks
        except Exception as e:
            logger.error(f"Error fetching tasks: {e}")
            return []

# יצירת המופע לייצוא
notion = NotionService()