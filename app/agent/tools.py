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

from app.services.export.notion_tasks import create_notion_tasks_batch

def execute_notion_action(trace_id: str, action_data: dict):
    """Execute Notion task creation from agent suggestion"""
    tasks = action_data.get("tasks", [])
    if not tasks:
        return {"status": "no_tasks", "trace_id": trace_id}
    
    return create_notion_tasks_batch(trace_id, tasks)
