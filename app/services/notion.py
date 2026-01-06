import os
import requests
from typing import Dict, Any, List
from datetime import datetime

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_TASKS_DB_ID")

class NotionClient:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    def create_task_page(self, title: str, memory_type: str, content: str) -> Dict[str, Any]:
        """Create Notion task from memory"""
        url = f"https://api.notion.com/v1/pages"
        
        payload = {
            "parent": {"database_id": NOTION_DB_ID},
            "properties": {
                "Name": {"title": [{"text": {"content": title}}]},
                "Type": {"select": {"name": memory_type}},
                "Source": {"rich_text": [{"text": {"content": "KIRP Agent"}}]},
                "Status": {"select": {"name": "To Do"}}
            },
            "children": [
                {
                    "object": "block",
                    "type": "rich_text",
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                }
            ]
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        return response.json()

notion = NotionClient()
