import os, requests
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "mock")
NOTION_DB_ID = os.getenv("NOTION_DB_ID", "mock")

def create_kirp_tasks(tasks):
    return {
        "created": len(tasks),
        "notion_url": f"https://notion.so/{NOTION_DB_ID}",
        "mock_pages": [{"title": t["text"][:30]} for t in tasks]
    }
