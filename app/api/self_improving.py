from fastapi import APIRouter
from pydantic import BaseModel
from app.rag.self_improving_agent import self_improving_query


router = APIRouter()

class SelfImprovingRequest(BaseModel):
    question: str
    user_id: str
    k: int = 5
    feedback: float | None = None

@router.post("/")
async def self_improving_endpoint(req: SelfImprovingRequest):
    return self_improving_query(
        query=req.question,
        user_id=req.user_id,
        k=req.k,
        feedback=req.feedback
    )
