from fastapi import APIRouter
from pydantic import BaseModel

from app.rag.retriever import retrieve_context
from app.rag.rag_engine import generate_answer

router = APIRouter(tags=["Query"])


class QueryRequest(BaseModel):
    question: str


@router.post("/")
async def query_knowledge(data: QueryRequest):
    context = retrieve_context(data.question)

    if not context:
        return {
            "answer": "I don't have enough information yet.",
            "sources": [],
        }

    answer = generate_answer(context, data.question)

    return {
        "answer": answer,
        "sources": context,
    }
