# app/rag/self_improving_agent.py
"""
KIRP Unified Self-Improving RAG Engine
Combines:
- Context retrieval
- LLM reasoning
- Feedback-based confidence adjustment
- Knowledge-gap detection
"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import logging

from app.core.persistence import PersistenceManager
from app.rag.rag_engine import rag_engine
from app.llm.client import get_llm

logger = logging.getLogger(__name__)


async def self_improving_query(
    query: str,
    user_id: str,
    k: int = 5,
    feedback: Optional[float] = None,
) -> Dict[str, Any]:

    # 1. Retrieve context
    context = await rag_engine.get_relevant_context(query, user_id=user_id)

    # 2. LLM reasoning
    llm = get_llm()
    now_utc = datetime.now(timezone.utc).isoformat()

    prompt = (
        f"Current Time (UTC): {now_utc}\n"
        f"User ID: {user_id}\n"
        f"Relevant Context:\n{context}\n\n"
        f"User Question:\n{query}\n\n"
        "You are a precise assistant. Use the context when helpful, "
        "but if it is not relevant, answer from your general knowledge. "
        "Explain your reasoning briefly."
    )

    res = await llm.ainvoke(prompt)
    answer = res.content if hasattr(res, "content") else str(res)

    # 3. Confidence calculation
    base_confidence = 0.75
    if feedback is not None:
        confidence_overall = round(
            min(1.0, max(0.0, base_confidence * 0.5 + float(feedback) * 0.5)),
            3,
        )
    else:
        confidence_overall = base_confidence

    # 4. Knowledge gap detection
    if "i don't have enough information" in answer.lower():
        await PersistenceManager.append_event(
            "knowledge_gap_detected",
            {"query": query, "user_id": user_id},
        )

    # 5. Persist event
    try:
        await PersistenceManager.save_event(
            "self_improving_query",
            {
                "user_id": user_id,
                "query": query,
                "confidence": confidence_overall,
                "feedback": feedback,
                "created_at": now_utc,
            },
        )
    except Exception:
        pass

    return {
        "answer": answer,
        "context": context,
        "confidence": confidence_overall,
        "timestamp_utc": now_utc,
    }
