import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_TASKS_DB_ID")

class NotionService:
    def __init__(self):
        if NOTION_TOKEN and NOTION_TOKEN != "mock":
            self.client = Client(auth=NOTION_TOKEN)
        else:
            self.client = None
        self.db_id = NOTION_DB_ID

    def create_task_page(self, title, trace_id="manual", source="api", confidence=1.0):
        if not self.client:
            return {"status": "no_client"}
        try:
            new_page = {
                "parent": {"database_id": self.db_id},
                "properties": {
                    "Name": {"title": [{"text": {"content": title}}]},
                    "Status": {"status": {"name": "Pending"}},
                    "Source": {"select": {"name": source}}
                }
            }
            return self.client.pages.create(**new_page)
        except Exception as e:
            print(f"❌ Notion Error: {e}")
            return {"status": "error", "message": str(e)}

    def get_tasks(self):
        if not self.client: return []
        try:
            # שימוש ב-databases.query הנכון
            response = self.client.databases.query(database_id=self.db_id)
            tasks = []
            for page in response.get("results", []):
                props = page.get("properties", {})
                # חילוץ הטקסט בצורה בטוחה
                name_obj = props.get("Name", {}).get("title", [])
                title = name_obj[0]["text"]["content"] if name_obj else "Untitled"
                status = props.get("Status", {}).get("status", {}).get("name", "Unknown")
                tasks.append({"Title": title, "Status": status})
            return tasks
        except Exception as e:
            print(f"❌ Notion Fetch Error: {e}")
            return []

notion = NotionService()