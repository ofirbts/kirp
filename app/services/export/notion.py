import requests
from app.models.memory import MemoryRecord

def export_to_notion(memories: list[MemoryRecord], notion_token: str, database_id: str):
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    for m in memories:
        payload = {
            "parent": {"database_id": database_id},
            "properties": {
                "Content": {
                    "title": [{"text": {"content": m.content[:200]}}]
                },
                "Type": {
                    "select": {"name": m.memory_type}
                }
            }
        }

        requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=payload
        )
