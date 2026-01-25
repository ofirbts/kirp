# app/rag/agent_rag.py
"""
Agent-level RAG pipeline:
- Intent detection
- Context retrieval
- RAG query
- Explainability + persistence
"""

from datetime import datetime
from typing import List, Dict, Any

from app.rag.retriever import retrieve_context
from app.rag.rag_engine import rag_engine
from app.core.persistence import PersistenceManager


def detect_intents(query: str) -> List[str]:
    intents: List[str] = []
    q_lower = query.lower()
    if any(w in q_lower for w in ["price", "pricing", "subscription", "tier"]):
        intents.append("pricing")
    if any(w in q_lower for w in ["login", "auth", "token", "signin", "jwt"]):
        intents.append("auth")
    return intents


async def agent_rag_pipeline(
    query: str,
    session_id: str,
    user_id: str,
    k: int = 5,
) -> Dict[str, Any]:
    """
    Full agent-level RAG pipeline:
    - Retrieve ranked memories
    - Detect intents
    - Aggregate confidence
    - Persist decision event
    - Query RAG engine
    """
    # 1. Retrieve context (ranked memories)
    memories = await retrieve_context(query=query, user_id=user_id, k=k)

    # 2. Intent detection
    intents = detect_intents(query)

    # 3. Explainability summary
    explain_summary: Dict[str, Any] = {
        "top_concepts": [],
        "top_overlap_terms": [],
        "confidence_overall": None,
        "actions_taken": [],
    }

    confidences = [
        m.get("explanation", {}).get("confidence")
        for m in memories
        if m.get("explanation", {}).get("confidence") is not None
    ]
    explain_summary["confidence_overall"] = (
        round(sum(confidences) / len(confidences), 3)
        if confidences
        else None
    )
    explain_summary["actions_taken"] = [
        {"intent": i, "action": "reason"}
        for i in intents
    ]

    # 4. Persist agent decision event
    await PersistenceManager.append_event(
        "agent_decision",
        {
            "session_id": session_id,
            "query": query,
            "intents": intents,
            "confidence": explain_summary["confidence_overall"],
            "memories_used": len(memories),
        },
    )

    # 5. RAG engine query
    rag_result = await rag_engine.query(
        question=query,
        user_id=user_id,
        k=k,
    )

    return {
        "answer_text": rag_result["answer"],
        "memories": rag_result["context"],
        "explain_summary": explain_summary,
    }


async def intelligent_query(
    query: str,
    user_id: str,
    k: int = 5,
) -> Dict[str, Any]:
    """
    Public entrypoint for intelligent RAG queries.
    """
    session_id = f"{user_id}_{int(datetime.now().timestamp())}"

    result = await agent_rag_pipeline(
        query=query,
        session_id=session_id,
        user_id=user_id,
        k=k,
    )

    return {
        "intent": detect_intents(query),
        "effects": result["explain_summary"],
        "answer": result["answer_text"],
        "context": result["memories"],
    }
