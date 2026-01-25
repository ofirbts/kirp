# app/rag/qa_engine.py
"""
KIRP QA Engine v4
Thin but production-ready wrapper around the unified RAG engine.
Adds:
- Logging
- Error handling
- Trace ID
- Consistent return format
"""

import logging
import uuid
from typing import Dict, Any

from app.rag.rag_engine import rag_engine

logger = logging.getLogger(__name__)


async def answer_with_rag(
    question: str,
    user_id: str,
    k: int = 5,
) -> Dict[str, Any]:
    """
    High-level RAG answer function.

    Returns:
    {
        "answer": str,
        "context": [...],
        "trace_id": str,
        "error": Optional[str]
    }
    """

    trace_id = f"qa_{uuid.uuid4().hex[:8]}"
    logger.info(f"🧠 QA Engine triggered | trace={trace_id} | user={user_id}")

    try:
        result = await rag_engine.query(
            question=question,
            user_id=user_id,
            k=k,
        )

        return {
            "answer": result.get("answer"),
            "context": result.get("context", []),
            "timestamp_utc": result.get("timestamp_utc"),
            "trace_id": trace_id,
            "error": None,
        }

    except Exception as e:
        logger.error(f"❌ QA Engine error | trace={trace_id} | {e}")
        return {
            "answer": "RAG QA Engine Error",
            "context": [],
            "timestamp_utc": None,
            "trace_id": trace_id,
            "error": str(e),
        }
