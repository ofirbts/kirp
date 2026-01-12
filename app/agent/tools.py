import ast
import requests
from typing import Dict, Any, List
from app.services.notion import notion
from app.services.export.notion_tasks import create_notion_tasks_batch

async def create_notion_tasks(tasks: List[Dict]) -> Dict[str, Any]:
    """Create Notion tasks from agent suggestions"""
    results = []
    for task in tasks:
        # עכשיו השם create_task_page קיים ב-notion.py
        result = notion.create_task_page(
            title=task.get("title", "No Title"),
            memory_type=task.get("type", "general"),
            content=task.get("content", "")
        )
        results.append(result)
    return {"created": len(results), "results": results}

def tool_search_web(q): 
    return requests.get(f"https://api.duckduckgo.com/?q={q}&format=json").json() 

def tool_calc(expr): 
    # הערה: eval הוא מסוכן, אבל למטרת הפרויקט כרגע זה יעבוד
    try:
        return ast.literal_eval(expr)
    except Exception as e:
        return str(e)

# רישום הכלים לשימוש ה-Agent
TOOL_REGISTRY = { 
    "search": tool_search_web, 
    "calc": tool_calc,
    "create_notion_tasks": create_notion_tasks # הוספתי את הכלי לשימוש ה-Agent
}