# app/rag/memory_ranker.py

from datetime import datetime, timezone
from typing import List, Dict, Any
import math


# 🧮 משקלים – ניתן לכוונון
ALPHA_SIMILARITY = 0.6
BETA_RECENCY = 0.3
GAMMA_DECAY = 0.1

HALF_LIFE_HOURS = 72  # אחרי 3 ימים – ירידה משמעותית


def _parse_timestamp(meta: Dict[str, Any]) -> datetime | None:
    ts = meta.get("INGESTED_AT") or meta.get("ingested_at")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "")).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def recency_score(meta: Dict[str, Any]) -> float:
    """
    ציון טריות: 1.0 = עכשיו, דועך אקספוננציאלית
    """
    ts = _parse_timestamp(meta)
    if not ts:
        return 0.2  # ברירת מחדל – זיכרון ישן/לא ידוע

    now = datetime.now(timezone.utc)
    hours = max((now - ts).total_seconds() / 3600, 0)

    return math.exp(-hours / HALF_LIFE_HOURS)


def decay_penalty(meta: Dict[str, Any]) -> float:
    """
    עונש על זיכרונות עם decay קיים (אם יש)
    """
    return float(meta.get("decay", 0.0))


def rank_memories(
    docs: List[Any],  # LangChain Document
    similarities: List[float] | None = None
) -> List[Dict[str, Any]]:
    """
    מחזיר רשימה מדורגת עם score + הסבר
    """
    ranked = []

    for i, doc in enumerate(docs):
        meta = getattr(doc, "metadata", {}) or {}
        similarity = similarities[i] if similarities else 0.5

        r_score = recency_score(meta)
        d_penalty = decay_penalty(meta)

        final_score = (
            ALPHA_SIMILARITY * similarity
            + BETA_RECENCY * r_score
            - GAMMA_DECAY * d_penalty
        )

        ranked.append({
            "text": doc.page_content,
            "metadata": meta,
            "similarity": round(similarity, 4),
            "recency": round(r_score, 4),
            "decay": round(d_penalty, 4),
            "score": round(final_score, 4),
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked
