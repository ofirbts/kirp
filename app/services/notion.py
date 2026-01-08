import os

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "mock")
NOTION_DB_ID = os.getenv("NOTION_DB_ID", "mock")

class NotionService:
    def __init__(self):
        self.token = NOTION_TOKEN
        self.db_id = NOTION_DB_ID

    def create_task_page(self, title: str, memory_type: str = "general", content: str = ""):
        """יצירת משימה בודדת ב-Notion"""
        # כאן הלוגיקה של ה-Mock או קריאת API אמיתית בעתיד
        return {
            "id": "mock-uuid",
            "title": title,
            "url": f"https://notion.so/{self.db_id}",
            "status": "success"
        }

    def create_kirp_tasks(self, tasks):
        """תמיכה בגרסה הישנה אם יש כזו"""
        return {"created": len(tasks), "notion_url": f"https://notion.so/{self.db_id}"}

# האובייקט שכולם מייבאים
notion = NotionService()