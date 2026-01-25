# app/rag/retrieval_pipeline.py
"""
KIRP Enterprise RAG Pipeline v8
Production semantic ranking + deduplication + explainability

Responsibilities:
- Deduplicate semantically similar results
- Rank by multiple signals (similarity, recency, keyword overlap, decay)
- Attach explanation block per memory
"""

import logging
import math
from typing import List, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetrievalScore:
    similarity: float = 0.0
    recency: float = 0.0
    decay: float = 0.0
    final_score: float = 0.0


class EnterpriseRAGPipeline:
    """Production RAG with multi-signal ranking"""

    # Production weights (tuned)
    WEIGHTS = {
        "similarity": 0.6,
        "recency": 0.25,
        "keyword_overlap": 0.1,
        "concept_match": 0.05,  # שמור לעתיד
    }

    RECENCY_HALF_LIFE_HOURS = 72  # 3 days

    @staticmethod
    def _parse_timestamp(meta: Dict[str, Any]) -> datetime | None:
        ts = (
            meta.get("INGESTED_AT")
            or meta.get("ingested_at")
            or meta.get("created_at")
        )
        if not ts:
            return None
        try:
            return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            return None

    @classmethod
    def recency_score(cls, metadata: Dict[str, Any]) -> float:
        """Exponential recency decay"""
        ts = cls._parse_timestamp(metadata)
        if not ts:
            return 0.2

        try:
            hours_old = max(
                0,
                (datetime.now(timezone.utc) - ts).total_seconds() / 3600,
            )
            return math.exp(-hours_old / cls.RECENCY_HALF_LIFE_HOURS)
        except Exception:
            return 0.2

    @staticmethod
    def keyword_overlap(query: str, text: str) -> float:
        """Keyword matching boost"""
        q_words = set(query.lower().split())
        t_words = set(text.lower().split())
        if not q_words:
            return 0.0
        overlap = len(q_words & t_words)
        return min(overlap / max(1, len(q_words)), 1.0)

    @staticmethod
    def cosine_similarity(v1: list, v2: list) -> float:
        """Fast cosine similarity"""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(x * x for x in v1))
        norm2 = math.sqrt(sum(x * x for x in v2))
        return dot / (norm1 * norm2) if norm1 and norm2 else 0.0

    @classmethod
    def semantic_deduplication(cls, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove semantic duplicates (cosine > 0.95) if embeddings exist.
        If no embeddings are present, returns as-is.
        """
        unique: List[Dict[str, Any]] = []
        for doc in results:
            emb = doc.get("embedding") or doc.get("metadata", {}).get("embedding")
            if not emb:
                unique.append(doc)
                continue

            is_duplicate = any(
                cls.cosine_similarity(
                    emb,
                    u.get("embedding") or u.get("metadata", {}).get("embedding"),
                )
                > 0.95
                for u in unique
                if (u.get("embedding") or u.get("metadata", {}).get("embedding"))
            )
            if not is_duplicate:
                unique.append(doc)
        return unique

    @classmethod
    def rank_results(
        cls,
        query: str,
        raw_results: List[Dict[str, Any]],
        k: int = 6,
    ) -> List[Dict[str, Any]]:
        """Production multi-signal ranking with explanation."""
        scored: List[Dict[str, Any]] = []

        for doc in raw_results[:20]:  # Top-20 candidates
            text = doc.get("text") or ""
            meta = doc.get("metadata", {}) or {}

            scores = RetrievalScore(
                similarity=doc.get("score", 0.5),
                recency=cls.recency_score(meta),
                decay=float(meta.get("decay", 0.0)),
            )

            keyword_boost = cls.keyword_overlap(query, text)

            scores.final_score = (
                scores.similarity * cls.WEIGHTS["similarity"]
                + scores.recency * cls.WEIGHTS["recency"]
                + keyword_boost * cls.WEIGHTS["keyword_overlap"]
                - scores.decay * 0.1
            )

            ranked_doc = {
                **doc,
                "ranking": {
                    "similarity": round(scores.similarity, 3),
                    "recency": round(scores.recency, 3),
                    "keyword_boost": round(keyword_boost, 3),
                    "final_score": round(scores.final_score, 3),
                },
            }

            # הסבר מובנה – מה ישפיע על self_improving / dashboard
            ranked_doc["explanation"] = {
                "reason": "multi_signal_ranking(similarity+recency+keywords-decay)",
                "confidence": round(scores.final_score, 3),
                "signals": ranked_doc["ranking"],
            }

            scored.append(ranked_doc)

        return sorted(
            scored,
            key=lambda x: x["ranking"]["final_score"],
            reverse=True,
        )[:k]


def retrieval_pipeline(
    query: str,
    raw_results: List[Dict[str, Any]],
    final_k: int = 6,
) -> List[Dict[str, Any]]:
    """
    Production RAG pipeline entrypoint.

    raw_results expected format (from search_vectors):
    [
      {
        "text": str,
        "metadata": {...},
        "score": float,
        ...
      },
      ...
    ]
    """
    # 1. Deduplication
    deduped = EnterpriseRAGPipeline.semantic_deduplication(raw_results)

    # 2. Multi-signal ranking + explanation
    ranked = EnterpriseRAGPipeline.rank_results(query, deduped, final_k)

    logger.info(
        f"📊 RAG Pipeline: {len(raw_results)} → {len(deduped)} → {len(ranked)} results"
    )
    return ranked
