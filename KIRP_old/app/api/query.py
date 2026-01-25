# app/api/query.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from app.rag.vector_store import search_vectors as search_vector_store
from app.rag.retrieval_pipeline import retrieval_pipeline
from app.agent.agent import agent
from app.api.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["Query"])


class QueryRequest(BaseModel):
    query: str
    context_query: Optional[str] = None


class SearchResult(BaseModel):
    text: str
    score: float
    source: str
    created_at: str
    meta: Dict[str, Any]


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    count: int


@router.post("")
async def query_endpoint(
    req: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Main conversational endpoint — routes the query to the OmniAgent.
    """
    try:
        user_id = current_user["username"]
        result = await agent.process_task(
            task_description=req.query,
            user_id=user_id,
            context_query=req.context_query or req.query,
        )
        return {"answer": result}

    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ask")
async def search_vectors_endpoint(
    query: str,
    k: int = 15,
    current_user: dict = Depends(get_current_user),
):
    """
    Direct vector search endpoint — returns raw + refined RAG results.
    """
    try:
        raw_results = await search_vector_store(
            query=query,
            k=k,
            user_id=current_user["username"],
        )

        refined_results = retrieval_pipeline(
            query=query,
            raw_results=raw_results
        )

        return {
            "query": query,
            "results": refined_results,
            "count": len(refined_results),
        }

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")
