from typing import List, Dict, Any
from app.rag.agent_rag import agent_rag_pipeline
from app.core.persistence import PersistenceManager
from app.core.invariants import assert_invariant

_sessions: Dict[str, List[Dict[str, Any]]] = {}


def update_session_memory(session_id: str, memories: List[Dict[str, Any]]):
    _sessions.setdefault(session_id, []).extend(memories)
    assert_invariant(session_id is not None, "Session mutation without session_id")

    # 🔥 Persistence hook — session update
    PersistenceManager.append_event("session_update", {
        "session_id": session_id,
        "added_memories": len(memories)
    })


def summarize_session(session_id: str) -> str:
    mems = _sessions.get(session_id, [])
    return "Session {sid} summary:\n".format(sid=session_id) + "\n".join(
        [m.get("text", "") for m in mems]
    )


def session_rag_pipeline(
    query: str,
    session_id: str,
    k: int = 5,
) -> Dict[str, Any]:
    result = agent_rag_pipeline(query, session_id, k)

    update_session_memory(session_id, result["memories"])

    result["session_summary"] = summarize_session(session_id)

    return result
