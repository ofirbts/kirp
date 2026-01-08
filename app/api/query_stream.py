from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, List
from app.rag.retriever import retrieve_context
from app.rag.rag_engine import generate_answer
from app.api.status import mark_query, mark_error
import json
import asyncio


router = APIRouter(tags=["Query Stream"])


class StreamQueryRequest(BaseModel):
    question: str
    k: int = 5
    session_id: str = "default"


async def stream_answer(req: StreamQueryRequest):
    """
    SSE generator:
    - מזרים את התשובה בהדרגה דרך delta
    - בסוף שולח sources + explainability + confidence_overall
    """
    try:
        # 1. Retrieve memories (RAG)
        memories = retrieve_context(req.question, k=req.k)

        # 2. Build full answer text
        full_answer = generate_answer(memories, req.question)

        # 3. Stream answer token-by-token
        for token in full_answer.split():
            chunk = {"delta": token + " "}
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.0)  # אפשר לשנות ל-0.01 לסימולציה "אנושית"

        # 4. Compute confidence_overall
        confidences = [
            m.get("explanation", {}).get("confidence")
            for m in memories
            if m.get("explanation", {}).get("confidence") is not None
        ]
        confidence_overall = round(sum(confidences) / len(confidences), 3) if confidences else None

        # 5. Build explainability summary
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

        # 6. Final payload – תואם ל-/query
        final_payload = {
            "question": req.question,
            "answer_text": full_answer,
            "confidence_overall": confidence_overall,
            "explainability_summary": explainability_summary,
            "sources": memories,
            "session_id": req.session_id,
        }

        yield f"data: {json.dumps(final_payload)}\n\n"
        yield "data: [DONE]\n\n"

        mark_query()

    except Exception as e:
        mark_error(f"stream_failed: {e}")
        err = {"error": str(e)}
        yield f"data: {json.dumps(err)}\n\n"
        yield "data: [DONE]\n\n"


@router.post("/stream")
async def query_stream(req: StreamQueryRequest):
    return StreamingResponse(
        stream_answer(req),
        media_type="text/event-stream"
    )
