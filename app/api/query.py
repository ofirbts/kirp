from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from app.rag.vector_store import search_vectors as search_vector_store
from app.rag.retrieval_pipeline import retrieval_pipeline
from app.agent.agent import agent

# הגדרת לוגר מקומי
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["Query"])

class QueryRequest(BaseModel):
    query: str
    user_id: str = "ofir"
    context_query: Optional[str] = None

@router.post("")
async def query_endpoint(req: QueryRequest):
    """
    נקודת קצה להרצה מלאה דרך ה-Agent (כולל ביצוע משימות)
    """
    try:
        # אם יש לך פונקציה לרישום סטטוס, וודא שהיא קיימת ב-app.api.status
        # mark_query() 
        
        result = await agent.process_task(
            task_description=req.query,
            user_id=req.user_id,
            context_query=req.context_query or req.query,
        )
        return {"answer": result}
    except Exception as e:
        logger.error(f"Error in query_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal agent error")

@router.get("/ask")
async def ask_question(q: str):
    """
    נקודת קצה לחיפוש ידע (RAG) בלבד עם הסברים
    """
    try:
        # 1. חיפוש ראשוני ב-Vector Store
        raw_results = await search_vector_store(q, limit=15)
        
        # 2. הרצת ה-Retrieval Pipeline (Deduplication + Confidence)
        refined_results = retrieval_pipeline(query=q, raw_results=raw_results)
        
        return {
            "query": q,
            "results": refined_results,
            "count": len(refined_results)
        }
    except Exception as e:
        logger.error(f"Error in ask_question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Search pipeline failed")