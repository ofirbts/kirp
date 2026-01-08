from fastapi import APIRouter
from pydantic import BaseModel
from app.rag.self_improving_agent import self_improving_query


router = APIRouter()

class SelfImprovingRequest(BaseModel):
    question: str
    session_id: str = "default"
    k: int = 5
    feedback: float | None = None

@router.post("/")
async def self_improving_endpoint(req: SelfImprovingRequest):
    return self_improving_query(
        question=req.question,
        session_id=req.session_id,
        k=req.k,
        feedback=req.feedback
    )
