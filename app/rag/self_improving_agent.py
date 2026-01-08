from typing import Optional, Dict, Any
from app.rag.long_term_memory import session_rag_pipeline
from app.observability.alerts import check_confidence   # ← חדש


def self_improving_query(
    query: str,
    session_id: str,
    k: int = 5,
    feedback: Optional[float] = None,
) -> Dict[str, Any]:
    result = session_rag_pipeline(query, session_id, k)

    # Adjust confidence with feedback
    if feedback is not None:
        conf = result.get("explain_summary", {}).get("confidence_overall")
        if conf is not None:
            result["explain_summary"]["confidence_overall"] = round(
                min(1.0, conf * 0.5 + feedback * 0.5),
                3,
            )

    # 🔔 NEW: trigger alert if confidence is low
    confidence = result.get("explain_summary", {}).get("confidence_overall")
    check_confidence(confidence)

    return result
