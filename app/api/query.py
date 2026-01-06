from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import uuid
from app.rag.retriever import retrieve_context
from app.rag.rag_engine import generate_answer

router = APIRouter(tags=["Query"])

class QueryRequest(BaseModel):
    question: str

@router.post("/")
async def query_knowledge(data: QueryRequest):
    # Retrieve
    context = retrieve_context(data.question)
    
    if not context:
        return {
            "answer": "I don't have enough information yet.",
            "sources": [],
            "confidence": 0.0,
            "trace_id": str(uuid.uuid4())
        }
    
    # Generate
    answer = generate_answer(context, data.question)
    
    # 🔥 NEW: confidence + trace_id
    confidence = round(min(1.0, len(context) / 5), 2)  # 0.2-1.0
    trace_id = str(uuid.uuid4())
    
    return {
        "answer": answer,
        "sources": context,
        "confidence": confidence,      # 🔥 חדש!
        "trace_id": trace_id           # 🔥 חדש!
    }
