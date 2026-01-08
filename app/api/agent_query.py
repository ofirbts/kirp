from fastapi import APIRouter
from pydantic import BaseModel
from app.agent.agent import agent
from app.core.persistence import PersistenceManager
from uuid import uuid4

router = APIRouter(tags=["Agent"])

class AgentQueryRequest(BaseModel):
    question: str

@router.post("/")
async def agent_query(req: AgentQueryRequest):
    """
    Endpoint איכותי שמפעיל את ה-Agent,
    מייצר explainability events,
    שומר trace,
    ומחזיר תשובה מלאה.
    """

    trace_id = str(uuid4())

    # 1. שמירת event של קבלת השאלה
    PersistenceManager.append_event("agent_query_received", {
        "trace_id": trace_id,
        "question": req.question,
    })

    # 2. הפעלת ה-Agent
    result = await agent.agent_query(req.question)

    # 3. שמירת event של התשובה
    PersistenceManager.append_event("agent_query_completed", {
        "trace_id": trace_id,
        "answer": result.get("answer"),
        "suggestions": result.get("suggestions"),
    })

    # 4. החזרת תשובה מלאה
    return {
        "trace_id": trace_id,
        **result
    }
