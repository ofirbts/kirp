from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio
import logging

from app.api.auth import get_current_user
from app.api.status import mark_query, mark_error
from app.rag.rag_engine import rag_engine
from app.rag.vector_store import search_vectors
from app.rag.retrieval_pipeline import retrieval_pipeline

router = APIRouter(tags=["Query Stream"])
logger = logging.getLogger(__name__)


class StreamQueryRequest(BaseModel):
    question: str
    k: int = 5
    session_id: str = "default"


async def stream_answer(req: StreamQueryRequest, user_id: str):
    try:
        # 1. שליפת הקשר מה-Vector Store
        raw_results = await search_vectors(req.question, k=req.k, user_id=user_id)
        memories = retrieval_pipeline(query=req.question, raw_results=raw_results)

        # 2. תשובה מה-LLM דרך RAGEngine (שכבה מסודרת)
        rag_result = await rag_engine.query(req.question, user_id=user_id, k=req.k)
        full_answer = rag_result.get("answer", "")

        # 3. סטרימינג של הטקסט (פשוט לפי מילים)
        for token in full_answer.split():
            yield f"data: {json.dumps({'delta': token + ' '})}\n\n"
            await asyncio.sleep(0.0)

        confidences = [
            m.get("explanation", {}).get("confidence")
            for m in memories
            if m.get("explanation", {}).get("confidence") is not None
        ]
        confidence_overall = (
            round(sum(confidences) / len(confidences), 3)
            if confidences else None
        )

        explainability_summary = {
            "top_concepts": sorted({
                c
                for m in memories
                for c in (m.get("explanation", {}).get("matched_concepts") or [])
            }),
            "top_overlap_terms": sorted({
                t
                for m in memories
                for t in (m.get("explanation", {}).get("query_overlap") or [])
            }),
            "confidence_overall": confidence_overall,
            "memories_used": len(memories),
        }

        final_payload = {
            "question": req.question,
            "answer_text": full_answer,
            "confidence_overall": confidence_overall,
            "explainability_summary": explainability_summary,
            "sources": memories,
            "session_id": req.session_id,
            "user_id": user_id,
        }

        yield f"data: {json.dumps(final_payload)}\n\n"
        yield "data: [DONE]\n\n"

        mark_query()

    except Exception as e:
        logger.exception(f"stream_answer failed: {e}")
        mark_error(f"stream_failed: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"


@router.post("/stream")
async def query_stream(
    req: StreamQueryRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["username"]
    return StreamingResponse(
        stream_answer(req, user_id=user_id),
        media_type="text/event-stream",
    )
