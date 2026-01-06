from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from app.rag.retriever import retrieve_context

router = APIRouter(tags=["Agent"])

class AgentRequest(BaseModel):
    question: str

async def agent_query(question: str) -> Dict[str, Any]:
    """Agent without LLM - pattern detection only"""
    context = retrieve_context(question)
    
    # Simple pattern detection
    tasks = []
    events = []
    
    for source in context:
        if "task" in source.lower() or "buy" in source.lower():
            tasks.append(source)
        if "event" in source.lower() or "doctor" in source.lower():
            events.append(source)
    
    suggestions = []
    if tasks:
        suggestions.append("📝 Create Notion task list?")
    if events:
        suggestions.append("📅 Add to calendar?")
    
    answer = f"Your memories show: {len(tasks)} tasks, {len(events)} events."
    if suggestions:
        answer += "\n\nI can help: " + " | ".join(suggestions)
    
    return {
        "answer": answer,
        "agent_mode": True,
        "sources": context[:3],
        "suggestions": suggestions
    }

@router.post("/")
async def agent_endpoint(data: AgentRequest):
    return await agent_query(data.question)
