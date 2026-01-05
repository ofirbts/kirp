from fastapi import APIRouter, Body
from pydantic import BaseModel
from typing import Optional

# שתי הפונקציות החכמות שלך
from app.agent.router import agent_handle
from app.services.query_engine import intelligent_query

router = APIRouter(
    prefix="/agent", 
    tags=["Agent"]
)

class AgentInput(BaseModel):
    text: str
    question: Optional[str] = None

@router.post("/", response_model=dict)
async def agent_query(input: AgentInput = Body(...)):
    """
    Agent API - תומך בשתי הגישות:
    1. text → agent_handle (ישן)
    2. question → intelligent_query (חדש)
    """
    if input.question:
        # גרסה חדשה - intelligent query
        answer = await intelligent_query(input.question)
        return {"answer": answer}
    else:
        # גרסה ישנה - agent handle
        return await agent_handle(input.text)
