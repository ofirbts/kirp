from typing import List, Dict, Any, Optional
import math
from datetime import datetime, timezone


# ======================
# Utils
# ======================

def safe_cosine_similarity(v1: Optional[list], v2: Optional[list]) -> float:
    """
    גרסה בטוחה של cosine:
    - אם אחד מהם None → 0.0
    - אם אורך לא תואם → 0.0
    - אם אחד הוא וקטור אפס → 0.0
    """
    if not v1 or not v2:
        return 0.0
    if len(v1) != len(v2):
        return 0.0

    dot = 0.0
    norm1 = 0.0
    norm2 = 0.0

    for a, b in zip(v1, v2):
        dot += a * b
        norm1 += a * a
        norm2 += b * b

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot / math.sqrt(norm1 * norm2)


def keyword_overlap(query: str, text: str) -> List[str]:
    q = {w for w in query.lower().split() if w}
    t = {w for w in text.lower().split() if w}
    return sorted(list(q & t))


CONCEPTS = {
    "pricing": ["price", "pricing", "cost", "subscription", "plan", "tier"],
    "auth": ["login", "token", "jwt", "auth", "oauth", "signin"],
    "performance": ["latency", "speed", "slow", "fast", "optimize"],
    "retention": ["churn", "retention", "cancel", "renewal"],
}


def matched_concepts(text: str) -> List[str]:
    found = []
    lower = text.lower()
    for concept, keywords in CONCEPTS.items():
        if any(k in lower for k in keywords):
            found.append(concept)
    return sorted(found)


def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def compute_recency_boost(meta: Dict[str, Any]) -> float:
    """
    אם יש created_at / updated_at במטאדאטה בפורמט ISO – נותן בוסט קל לחדשים.
    אחרת: 0.0
    """
    ts = meta.get("updated_at") or meta.get("created_at")
    dt = parse_iso_datetime(ts)
    if not dt:
        return 0.0

    now = datetime.now(timezone.utc)
    days = (now - dt).total_seconds() / 86400.0
    # ככל שיותר חדש → בוסט קצת יותר גבוה, אבל מוגבל
    boost = max(0.0, 1.0 - min(days / 30.0, 1.0))  # בין 0 ל־1 על פני חודש
    return round(boost, 3)


# ======================
# Deduplication
# ======================

DEDUP_THRESHOLD = 0.92


def semantic_dedup(memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Dedup על בסיס embedding, עם:
    - הגנה מלאה על embedding חסר/לא תקין
    - fallback אוטומטי אם אין בכלל embedding
    """
    if not memories:
        return memories

    # אם אין embedding באף אחד → דילוג
    if not any(m.get("embedding") for m in memories):
        return memories

    unique: List[Dict[str, Any]] = []

    for m in memories:
        emb = m.get("embedding")
        if not emb:
            # אין embedding לפריט הזה – פשוט נוסיף אותו כמו שהוא
            unique.append(m)
            continue

        duplicate = False
        for u in unique:
            u_emb = u.get("embedding")
            sim = safe_cosine_similarity(emb, u_emb)
            if sim > DEDUP_THRESHOLD:
                duplicate = True
                break

        if not duplicate:
            unique.append(m)

    return unique


# ======================
# Explainability
# ======================

def build_explanation(query: str, memory: Dict[str, Any]) -> Dict[str, Any]:
    text = memory.get("text", "")
    meta = memory.get("meta") or {}
    recency_boost = compute_recency_boost(meta)

    base_score = memory.get("score")  # similarity מה־vector store
    # confidence משולב: similarity + recency
    confidence = None
    if base_score is not None:
        confidence = round(min(1.0, max(0.0, base_score + recency_boost * 0.2)), 3)

    explanation = {
        "similarity_score": base_score,
        "recency_boost": recency_boost or 0.0,
        "confidence": confidence,
        "query_overlap": keyword_overlap(query, text),
        "matched_concepts": matched_concepts(text),
        "source": meta.get("source"),
    }

    # אם יש שדות מעניינים נוספים במטאדאטה – אפשר להעביר אותם תחת "meta"
    important_meta_keys = ["id", "doc_type", "owner", "created_at", "updated_at"]
    explanation["meta"] = {k: meta.get(k) for k in important_meta_keys if k in meta}

    return explanation


# ======================
# Main Pipeline
# ======================

def logical_dedup(memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    שלב לוגי עתידי (כפילויות לפי id, source וכו').
    כרגע: passthrough.
    """
    return memories


def retrieval_pipeline(
    query: str,
    raw_results: List[Dict[str, Any]],
    final_k: int = 6,
) -> List[Dict[str, Any]]:
    """
    raw_results – פלט גולמי מה־vector store, בפורמט:
    [
      {
        "id": str | None,
        "text": str,
        "score": float,
        "embedding": List[float] | None,
        "meta": dict
      }
    ]
    מחזיר:
    [
      {
        "id": ...,
        "text": ...,
        "score": ...,
        "explanation": { ... }
      }
    ]
    """

    # 1. Semantic dedup עם fallback
    step1 = semantic_dedup(raw_results)

    # 2. Logical dedup
    step2 = logical_dedup(step1)

    # 3. Explainability + JSON קריא
    enriched: List[Dict[str, Any]] = []
    for m in step2:
        enriched.append({
            "id": m.get("id"),
            "text": m.get("text", ""),
            "score": m.get("score"),
            "explanation": build_explanation(query, m),
        })

    # 4. Final cut (כבר אחרי explainability)
    return enriched[:final_k]
