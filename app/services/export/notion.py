import httpx
import os

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

async def export_task_to_notion(task):
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": task["title"]}}]
            },
            "Completed": {
                "checkbox": task["completed"]
            }
        }
    }

    async with httpx.AsyncClient() as client:
        await client.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=payload
        )
