from app.services.notion import notion
from typing import Dict, Any

async def create_notion_tasks(tasks: list[Dict]) -> Dict[str, Any]:
    """Create Notion tasks from agent suggestions"""
    results = []
    for task in tasks:
        result = notion.create_task_page(
            title=task["title"],
            memory_type=task["type"],
            content=task["content"]
        )
        results.append(result)
    return {"created": len(results), "results": results}

async def send_reminder(email: str, message: str) -> Dict[str, Any]:
    """Future: Email reminder"""
    return {"status": "sent", "email": email, "message": message}
