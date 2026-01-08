from typing import List, Dict, Any
from app.rag.retriever import retrieve_context
from app.rag.rag_engine import generate_answer
from app.core.persistence import PersistenceManager


def detect_intents(query: str) -> List[str]:
    intents: List[str] = []
    q_lower = query.lower()
    if any(w in q_lower for w in ["price", "pricing", "subscription", "tier"]):
        intents.append("pricing")
    if any(w in q_lower for w in ["login", "auth", "token", "signin", "jwt"]):
        intents.append("auth")
    return intents


def agent_rag_pipeline(
    query: str,
    session_id: str,
    k: int = 5,
) -> Dict[str, Any]:
    memories = retrieve_context(query, k)
    intents = detect_intents(query)

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
        if confidences else None
    )
    explain_summary["actions_taken"] = [
        {"intent": i, "action": "reason"}
        for i in intents
    ]

    # 🔥 Persistence hook — agent decision
    PersistenceManager.append_event("agent_decision", {
        "session_id": session_id,
        "query": query,
        "intents": intents,
        "confidence": explain_summary["confidence_overall"],
        "memories_used": len(memories)
    })

    return {
        "answer_text": generate_answer(memories, query),
        "memories": memories,
        "explain_summary": explain_summary,
    }
