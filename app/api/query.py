from fastapi import APIRouter
from pydantic import BaseModel
from app.rag.retriever import retrieve_context
from app.rag.rag_engine import generate_answer
from app.api.status import mark_query, mark_error

router = APIRouter(tags=["Query"])

# Cache פשוט בזיכרון (משימה 5)
_query_cache = {}

class QueryRequest(BaseModel):
    query: str  # שונה מ-question ל-query כדי להתאים ל-UI
    k: int = 5
    session_id: str = "default"

@router.post("")
async def query_endpoint(req: QueryRequest):
    # בדיקת Cache
    if req.query in _query_cache:
        return _query_cache[req.query]

    try:
        memories = retrieve_context(req.query, k=req.k)
        answer_text = generate_answer(memories, req.query)
        
        result = {
            "query": req.query,
            "answer_text": answer_text,
            "sources": memories,
            "session_id": req.session_id
        }
        
        # שמירה ב-Cache
        _query_cache[req.query] = result
        mark_query()
        return result

    except Exception as e:
        mark_error(f"query_failed: {e}")
        raise
