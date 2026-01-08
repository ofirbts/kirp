from typing import List, Dict, Any, Optional
import math
from datetime import datetime, timezone
import hashlib

# ======================
# Utils
# ======================

def safe_cosine_similarity(v1: Optional[list], v2: Optional[list]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if not norm1 or not norm2:
        return 0.0
    return dot / (norm1 * norm2)


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
    lower = text.lower()
    return sorted([
        concept
        for concept, kws in CONCEPTS.items()
        if any(k in lower for k in kws)
    ])


def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def compute_recency_boost(meta: Dict[str, Any]) -> float:
    ts = meta.get("updated_at") or meta.get("created_at")
    dt = parse_iso_datetime(ts)
    if not dt:
        return 0.0
    now = datetime.now(timezone.utc)
    days = (now - dt).total_seconds() / 86400.0
    return round(max(0.0, 1.0 - min(days / 30.0, 1.0)), 3)


def text_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# ======================
# Deduplication
# ======================

DEDUP_THRESHOLD = 0.92


def semantic_dedup(memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not memories or not any(m.get("embedding") for m in memories):
        return memories
    unique: List[Dict[str, Any]] = []
    for m in memories:
        emb = m.get("embedding")
        if not emb:
            unique.append(m)
            continue
        duplicate = any(
            safe_cosine_similarity(emb, u.get("embedding")) > DEDUP_THRESHOLD
            for u in unique
            if u.get("embedding")
        )
        if not duplicate:
            unique.append(m)
    return unique


def logical_dedup(memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_keys = set()
    result: List[Dict[str, Any]] = []
    for m in memories:
        meta = m.get("meta") or {}
        key_tuple = (
            m.get("id"),
            meta.get("source"),
            text_hash(m.get("text", "")),
        )
        if key_tuple in seen_keys:
            continue
        seen_keys.add(key_tuple)
        result.append(m)
    return result


# ======================
# Explainability
# ======================

def build_explanation(query: str, memory: Dict[str, Any]) -> Dict[str, Any]:
    text = memory.get("text", "")
    meta = memory.get("meta") or {}
    recency = compute_recency_boost(meta)
    base_score = memory.get("score")
    overlap = keyword_overlap(query, text)
    concepts = matched_concepts(text)
    confidence = None
    if base_score is not None:
        overlap_factor = len(overlap) / max(1, len(query.split()))
        concept_factor = len(concepts) / max(1, len(CONCEPTS))
        raw_conf = (
            (base_score or 0)
            + 0.2 * recency
            + 0.1 * overlap_factor
            + 0.1 * concept_factor
        )
        confidence = round(min(1.0, max(0.0, raw_conf)), 3)
    important_meta_keys = ["id", "doc_type", "owner", "created_at", "updated_at"]
    return {
        "similarity_score": base_score,
        "recency_boost": recency,
        "confidence": confidence,
        "query_overlap": overlap,
        "matched_concepts": concepts,
        "source": meta.get("source"),
        "meta": {k: meta.get(k) for k in important_meta_keys if k in meta},
    }


# ======================
# Main Pipeline
# ======================

def retrieval_pipeline(
    query: str,
    raw_results: List[Dict[str, Any]],
    final_k: int = 6,
) -> List[Dict[str, Any]]:
    step1 = semantic_dedup(raw_results)
    step2 = logical_dedup(step1)
    enriched: List[Dict[str, Any]] = []
    for m in step2:
        enriched.append({
            "id": m.get("id"),
            "text": m.get("text", ""),
            "score": m.get("score"),
            "explanation": build_explanation(query, m),
        })
    return enriched[:final_k]
