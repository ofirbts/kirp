from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.rag.retriever import retrieve_context
import uuid

router = APIRouter(tags=["Agent"])

class AgentRequest(BaseModel):
    question: str

class ConfirmRequest(BaseModel):
    trace_id: str
    confirm: bool = True

# In-memory pending actions
pending_actions = {}

async def agent_query(question: str) -> Dict[str, Any]:
    context = retrieve_context(question)
    
    tasks = [s for s in context if "task" in s.lower()]
    events = [s for s in context if "event" in s.lower()]
    
    suggestions = []
    if len(tasks) >= 1:
        trace_id = str(uuid.uuid4())
        pending_actions[trace_id] = {
            "action": "create_notion_tasks",
            "tasks": len(tasks),
            "sources": tasks[:2]
        }
        suggestions.append({
            "action": "create_notion_tasks",
            "count": len(tasks),
            "trace_id": trace_id
        })
    
    answer = f"Found {len(tasks)} tasks, {len(events)} events."
    if suggestions:
        answer += f"\n\n💡 Reply POST /agent/confirm with trace_id: {suggestions[0]['trace_id']}"
    
    return {
        "answer": answer,
        "agent_mode": True,
        "sources": context[:3],
        "suggestions": suggestions
    }

@router.post("/")
async def agent_endpoint(data: AgentRequest):
    return await agent_query(data.question)

@router.post("/confirm")
async def confirm_action(data: ConfirmRequest):
    trace_id = data.trace_id
    
    if trace_id not in pending_actions:
        raise HTTPException(404, f"No pending action for trace_id: {trace_id}")
    
    action = pending_actions[trace_id]
    del pending_actions[trace_id]
    
    if data.confirm:
        # Mock execution (Notion would go here)
        return {
            "status": "executed",
            "action": action["action"],
            "tasks_created": action["tasks"],
            "trace_id": trace_id
        }
    else:
        return {"status": "cancelled", "trace_id": trace_id}
