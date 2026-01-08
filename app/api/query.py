from fastapi import APIRouter
from pydantic import BaseModel
from app.rag.retriever import retrieve_context
from app.rag.rag_engine import generate_answer

router = APIRouter(tags=["Query"])

class QueryRequest(BaseModel):
    question: str
    k: int = 5

@router.post("/")
async def query_endpoint(req: QueryRequest):
    context = retrieve_context(req.question, k=req.k)
    answer = generate_answer(context, req.question)

    return {
        "question": req.question,
        "answer": answer,
        "sources": context
    }
