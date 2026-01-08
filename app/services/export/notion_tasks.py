import os
import requests
from typing import List, Dict, Any
from datetime import datetime

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json", 
    "Notion-Version": "2022-06-28"
}

def create_notion_task(title: str, description: str = "", trace_id: str = "") -> Dict[str, Any]:
    """Create REAL Notion page with trace_id"""
    if not all([NOTION_TOKEN, NOTION_DB_ID]):
        return {"status": "skipped", "reason": "NOTION_TOKEN or NOTION_DB_ID missing"}
    
    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": f"✅ {title}"}}]},
            "Status": {"status": {"name": "To Do"}},
            "Trace ID": {"rich_text": [{"text": {"content": trace_id[:36]}}]},
            "Source": {"rich_text": [{"text": {"content": "KIRP Agent"}}]},
            "Created": {"date": {"start": datetime.utcnow().isoformat()}}
        }
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        if res.status_code == 200:
            return {"status": "created", "title": title, "trace_id": trace_id}
        return {"status": "failed", "error": res.text}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def create_notion_tasks_batch(trace_id: str, tasks: List[Dict]) -> Dict[str, Any]:
    """Create multiple Notion tasks from agent suggestions"""
    results = []
    for task_data in tasks:
        title = task_data.get("title", "Unnamed task")
        desc = task_data.get("description", "")
        result = create_notion_task(title, desc, trace_id)
        results.append(result)
    
    return {
        "status": "executed",
        "action": "create_notion_tasks", 
        "tasks_created": len(tasks),
        "notion_pages": len([r for r in results if r["status"] == "created"]),
        "results": results,
        "trace_id": trace_id
    }
