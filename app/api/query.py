from fastapi import APIRouter
from pydantic import BaseModel
from app.rag.retriever import retrieve_context
from app.rag.rag_engine import generate_answer
from app.api.status import mark_query, mark_error

router = APIRouter(tags=["Query"])

conversation_history = {}

class QueryRequest(BaseModel):
    question: str
    k: int = 5
    session_id: str = "default"

@router.post("/")
async def query_endpoint(req: QueryRequest):
    try:
        # 1. Retrieve RAG memories
        memories = retrieve_context(req.question, k=req.k)

        # 2. Add conversation history (not part of retrieval)
        history = conversation_history.get(req.session_id, [])
        full_context = history + memories

        # 3. Generate answer
        answer_text = generate_answer(full_context, req.question)

        # 4. Compute overall confidence
        confidences = [
            m.get("explanation", {}).get("confidence")
            for m in memories
            if m.get("explanation", {}).get("confidence") is not None
        ]
        confidence_overall = round(sum(confidences) / len(confidences), 3) if confidences else None

        # 5. Explainability summary
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
            "memories_used": len(memories)
        }

        # 6. Save to conversation history
        conversation_history.setdefault(req.session_id, []).append({
            "role": "user",
            "text": req.question
        })
        conversation_history[req.session_id].append({
            "role": "assistant",
            "text": answer_text
        })

        mark_query()

        return {
            "question": req.question,
            "answer_text": answer_text,
            "confidence_overall": confidence_overall,
            "explainability_summary": explainability_summary,
            "sources": memories,
            "session_id": req.session_id
        }

    except Exception as e:
        mark_error(f"query_failed: {e}")
        raise
