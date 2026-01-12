# app/api/agent_query.py
from fastapi import APIRouter
from pydantic import BaseModel
from uuid import uuid4
from app.agent.agent import agent

router = APIRouter()

class AgentQueryRequest(BaseModel):
    question: str

@router.post("")
async def agent_query(req: AgentQueryRequest):
    trace_id = str(uuid4())

    try:
        result = await agent.agent_query(req.question)

        return {
            "trace_id": trace_id,
            "answer": result.get("answer"),
            "confidence": result.get("confidence", 0.7),
        }

    except Exception as e:
        return {
            "trace_id": trace_id,
            "answer": None,
            "confidence": 0.0,
            "detail": str(e),
        }