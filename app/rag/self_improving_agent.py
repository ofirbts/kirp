from typing import Optional, Dict, Any
from app.rag.long_term_memory import session_rag_pipeline
from app.observability.alerts import check_confidence

def self_improving_query(
    query: str,
    user_id: str, # שיוך למשתמש הספציפי
    k: int = 5,
    feedback: Optional[float] = None,
) -> Dict[str, Any]:
    # שליפת מידע מה-RAG המשויך למשתמש
    result = session_rag_pipeline(query, user_id, k)

    # עדכון רמת הביטחון (Confidence) על בסיס משוב המשתמש
    if feedback is not None:
        conf = result.get("explain_summary", {}).get("confidence_overall")
        if conf is not None:
            # נוסחת שקלול בין הביטחון המקורי למשוב המשתמש
            result["explain_summary"]["confidence_overall"] = round(
                min(1.0, conf * 0.5 + feedback * 0.5),
                3,
            )

    # בדיקת רמת הביטחון והתראה במידה והיא נמוכה מדי
    confidence = result.get("explain_summary", {}).get("confidence_overall")
    check_confidence(confidence)

    return result