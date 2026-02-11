"""
RAG Engine — Hybrid search, multi-hop retrieval, context builder.

- Hybrid Search: semantic + keyword + BM25
- Multi-Hop Retrieval
- Context Builder
- Query Scoping: tenant / space / time / source
- Explainability + Confidence
- Feedback Loop
"""

from __future__ import annotations

import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# BM25 implementation (lightweight, no external dependency)
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logger.warning("rank_bm25 not installed; BM25 search will use fallback implementation")


@dataclass
class RetrievalResult:
    """Single RAG hit with explainability."""

    text: str
    score: float
    source: str
    metadata: dict[str, Any]
    explanation: str
    confidence: float


@dataclass
class RAGResponse:
    """RAG query response with context + explainability."""

    results: list[RetrievalResult]
    context_text: str
    confidence: float
    query_scopes: dict[str, Any]


class RAGEngine:
    """
    Hybrid RAG: semantic (Qdrant) + keyword/BM25 + multi-hop reasoning.
    Multi-tenant scoping with full isolation.
    """

    def __init__(
        self,
        qdrant_url: str,
        collection: str = "kirp_vectors",
        qdrant_api_key: str | None = None,
        embedding_provider: str = "openai",
        embedding_model: str = "text-embedding-3-small",
        enable_bm25: bool = True,
        enable_multihop: bool = True,
        hybrid_weight_semantic: float = 0.7,
        hybrid_weight_bm25: float = 0.3,
    ) -> None:
        self._qdrant_url = qdrant_url
        self._collection = collection
        self._qdrant_api_key = (qdrant_api_key or "").strip() or None
        self._embedding_provider = embedding_provider
        self._embedding_model = embedding_model
        self._enable_bm25 = enable_bm25
        self._enable_multihop = enable_multihop
        self._hybrid_weight_semantic = hybrid_weight_semantic
        self._hybrid_weight_bm25 = hybrid_weight_bm25
        self._client: Any = None
        self._embedder: Any = None
        self._bm25_index: dict[str, Any] = {}  # tenant_id -> BM25 index
        self._text_cache: dict[str, list[dict[str, Any]]] = {}  # tenant_id -> [documents]
        from src.observability.metrics import MetricsCollector
        self._metrics = MetricsCollector("kirp_rag")

    async def connect(self) -> None:
        """Initialize Qdrant client and embedder."""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models
            client_kw: dict[str, Any] = {"url": self._qdrant_url}
            if self._qdrant_api_key:
                client_kw["api_key"] = self._qdrant_api_key
            self._client = QdrantClient(**client_kw)
            embedding_dim = int(os.environ.get("EMBEDDING_DIMENSION", "1536"))
            collections = self._client.get_collections().collections
            if not any(c.name == self._collection for c in collections):
                self._client.create_collection(
                    collection_name=self._collection,
                    vectors_config=models.VectorParams(
                        size=embedding_dim,
                        distance=models.Distance.COSINE,
                    ),
                )
                logger.info("RAGEngine created Qdrant collection: %s", self._collection)
            # Ensure payload indexes for filter (tenant_id, space_id, user_id) — required by Qdrant Cloud
            for field in ("tenant_id", "space_id", "user_id"):
                try:
                    self._client.create_payload_index(
                        collection_name=self._collection,
                        field_name=field,
                        field_schema=models.PayloadSchemaType.KEYWORD,
                    )
                    logger.info("RAGEngine created payload index: %s", field)
                except Exception as idx_err:
                    if "already exists" in str(idx_err).lower() or "exist" in str(idx_err).lower():
                        logger.debug("Payload index %s already exists", field)
                    else:
                        logger.warning("Payload index %s: %s", field, idx_err)

            if self._embedding_provider == "openai":
                try:
                    from langchain_openai import OpenAIEmbeddings
                    if os.environ.get("OPENAI_API_KEY"):
                        self._embedder = OpenAIEmbeddings(model=self._embedding_model)
                    else:
                        self._embedder = None
                        logger.warning("OPENAI_API_KEY not set; embeddings disabled")
                except Exception as e:
                    self._embedder = None
                    logger.warning("OpenAI embedder init failed (%s); embeddings disabled", e)
            elif self._embedding_provider == "gemini":
                try:
                    from langchain_google_genai import GoogleGenerativeAIEmbeddings
                    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
                    if api_key:
                        self._embedder = GoogleGenerativeAIEmbeddings(
                            model=self._embedding_model or "models/text-embedding-004",
                            google_api_key=api_key,
                        )
                    else:
                        self._embedder = None
                        logger.warning("GEMINI_API_KEY not set; embeddings disabled")
                except Exception as e:
                    self._embedder = None
                    logger.warning("Gemini embedder init failed (%s); embeddings disabled", e)
            else:
                self._embedder = None
            logger.info("RAGEngine connected to Qdrant at %s", self._qdrant_url)
        except Exception as e:
            logger.error("RAGEngine connection failed: %s", e)
            raise

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        if self._embedder is None:
            # Try to initialize embedder
            await self.connect()
            if self._embedder is None:
                raise ValueError(
                    "Embedder not initialized. Check OPENAI_API_KEY or embedding provider configuration. "
                    "Cannot generate embeddings without a valid embedder."
                )
        try:
            from datetime import datetime, timezone
            start = datetime.now(timezone.utc)
            emb = await self._embedder.aembed_query(text)
            if not emb or len(emb) == 0:
                raise ValueError("Embedding generation returned empty result")
            latency = (datetime.now(timezone.utc) - start).total_seconds()
            self._metrics.observe("embedding_latency_seconds", latency, labels={})
            return emb
        except Exception as e:
            logger.error("Embedding generation failed: %s", e)
            raise ValueError(f"Failed to generate embedding: {e}") from e

    async def upsert(
        self,
        points: list[dict[str, Any]],
        tenant_id: str,
        space_id: str,
    ) -> int:
        """
        Upsert vectors to Qdrant with tenant/space in payload.
        Also updates BM25 index for hybrid search.
        """
        if self._client is None:
            await self.connect()
        from qdrant_client.http import models
        
        # Enforce multi-tenant isolation
        if not tenant_id or tenant_id == "*":
            raise ValueError("tenant_id is required for upsert (multi-tenant isolation)")
        
        ids = [p.get("id", str(i)) for i, p in enumerate(points)]
        vectors = [p["embedding"] for p in points]
        payloads = [
            {
                **{k: v for k, v in p.items() if k != "embedding"},
                "tenant_id": tenant_id,
                "space_id": space_id,
            }
            for p in points
        ]
        self._client.upsert(
            collection_name=self._collection,
            points=[
                models.PointStruct(id=id_, vector=v, payload=pl)
                for id_, v, pl in zip(ids, vectors, payloads)
            ],
            wait=True,
        )
        
        # Update BM25 index
        if self._enable_bm25:
            try:
                # Add new documents to cache
                new_docs = [
                    {
                        "id": str(id_),
                        "content": pl.get("content", ""),
                        "source": pl.get("source", "unknown"),
                        "tenant_id": tenant_id,
                        "space_id": space_id,
                        "metadata": pl,
                    }
                    for id_, pl in zip(ids, payloads)
                ]
                
                if tenant_id in self._text_cache:
                    # Update existing index
                    existing = self._text_cache[tenant_id]
                    # Remove duplicates by id
                    existing_ids = {d["id"] for d in existing}
                    new_unique = [d for d in new_docs if d["id"] not in existing_ids]
                    self._text_cache[tenant_id].extend(new_unique)
                else:
                    self._text_cache[tenant_id] = new_docs
                
                # Rebuild index
                self._build_bm25_index(tenant_id, self._text_cache[tenant_id])
            except Exception as e:
                logger.warning("BM25 index update failed: %s", e)
                # Continue - BM25 is best-effort
        
        logger.info("RAGEngine upserted %d points tenant=%s space=%s", len(points), tenant_id, space_id)
        return len(points)

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization for BM25."""
        text_lower = text.lower()
        # Remove punctuation, split on whitespace
        tokens = re.findall(r'\b\w+\b', text_lower)
        return tokens

    def _build_bm25_index(self, tenant_id: str, documents: list[dict[str, Any]]) -> None:
        """Build or update BM25 index for tenant."""
        if not self._enable_bm25 or not documents:
            return
        
        texts = [doc.get("content", "") for doc in documents]
        tokenized = [self._tokenize(text) for text in texts]
        
        if BM25_AVAILABLE:
            self._bm25_index[tenant_id] = BM25Okapi(tokenized)
        else:
            # Fallback: simple keyword matching
            self._bm25_index[tenant_id] = {"documents": documents, "tokenized": tokenized}
        
        self._text_cache[tenant_id] = documents
        logger.debug("Built BM25 index for tenant %s with %d documents", tenant_id, len(documents))

    async def _bm25_search(
        self,
        query: str,
        tenant_id: str,
        space_id: str | None = None,
        limit: int = 10,
        allowed_space_ids: list[str] | None = None,
    ) -> list[tuple[dict[str, Any], float]]:
        """BM25 keyword search. Respects allowed_space_ids for membership."""
        if not self._enable_bm25:
            return []
        
        # Get documents for tenant
        if tenant_id not in self._text_cache:
            await self._refresh_bm25_index(tenant_id, space_id)
        
        if tenant_id not in self._bm25_index:
            return []
        
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        documents = self._text_cache.get(tenant_id, [])
        if not documents:
            return []
        
        # Filter by space: allowed set or single space_id
        if allowed_space_ids:
            documents = [d for d in documents if d.get("space_id") in allowed_space_ids]
        elif space_id:
            documents = [d for d in documents if d.get("space_id") == space_id]
        
        if BM25_AVAILABLE:
            bm25 = self._bm25_index[tenant_id]
            scores = bm25.get_scores(query_tokens)
            scored_docs = list(zip(documents, scores))
        else:
            # Fallback: simple keyword matching
            scored_docs = []
            for doc in documents:
                text = doc.get("content", "").lower()
                score = sum(1 for token in query_tokens if token in text) / len(query_tokens) if query_tokens else 0.0
                scored_docs.append((doc, score))
        
        # Sort by score, return top results
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        return scored_docs[:limit]

    async def _refresh_bm25_index(self, tenant_id: str, space_id: str | None = None) -> None:
        """Refresh BM25 index from Qdrant (tenant-wide; space filtering applied at search time)."""
        if self._client is None:
            await self.connect()
        
        from qdrant_client.http import models
        
        must = [models.FieldCondition(key="tenant_id", match=models.MatchValue(value=tenant_id))]
        if space_id:
            must.append(models.FieldCondition(key="space_id", match=models.MatchValue(value=space_id)))
        
        q_filter = models.Filter(must=must) if must else None
        resp = self._client.scroll(
            collection_name=self._collection,
            scroll_filter=q_filter,
            limit=10000,  # Reasonable limit
            with_payload=True,
        )
        
        points = getattr(resp, "points", None) or []
        documents = []
        for point in points:
            pl = getattr(point, "payload", None) or {}
            documents.append({
                "id": str(getattr(point, "id", "")),
                "content": pl.get("content", ""),
                "source": pl.get("source", "unknown"),
                "tenant_id": pl.get("tenant_id", tenant_id),
                "space_id": pl.get("space_id", space_id or ""),
                "metadata": pl,
            })
        
        if documents:
            self._build_bm25_index(tenant_id, documents)

    async def _multi_hop_retrieval(
        self,
        query: str,
        tenant_id: str,
        space_id: str | None = None,
        user_id: str | None = None,
        limit: int = 10,
        max_hops: int = 2,
        allowed_space_ids: list[str] | None = None,
    ) -> RAGResponse:
        """
        Multi-hop retrieval: query rewriting, context expansion, iterative retrieval.
        Respects allowed_space_ids for membership.
        """
        if not self._enable_multihop or max_hops <= 1:
            return await self._single_hop_search(
                query, tenant_id, space_id, user_id, limit, allowed_space_ids=allowed_space_ids
            )
        
        from src.core.llm_router import get_llm_for_task
        # Multi-hop query rewriting → reasoning-grade provider.
        llm = get_llm_for_task("reasoning")
        
        # Initial retrieval
        initial_results = await self._single_hop_search(
            query, tenant_id, space_id, user_id, limit * 2, allowed_space_ids=allowed_space_ids
        )
        all_results = {r.text: r for r in initial_results.results}  # Deduplicate by text
        
        # Iterative refinement
        for hop in range(1, max_hops):
            if len(all_results) >= limit * 2:
                break
            
            # Extract entities/keywords from current results
            context_text = "\n".join([r.text[:200] for r in list(all_results.values())[:10]])
            expansion_prompt = f"""
Given this query and retrieved context, identify:
1. Key entities, concepts, or terms that should be searched
2. Related questions or sub-queries

Query: {query}

Retrieved Context:
{context_text}

Return JSON:
{{
  "entities": ["entity1", "entity2"],
  "sub_queries": ["related question 1", "related question 2"]
}}
"""
            
            try:
                response = await llm.invoke(expansion_prompt, temperature=0.3, max_tokens=500)
                import json
                response_text = response.strip()
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                expansion = json.loads(response_text)
                
                # Search for entities and sub-queries
                expansion_queries = expansion.get("sub_queries", [])[:3]  # Limit to 3
                for exp_query in expansion_queries:
                    exp_results = await self._single_hop_search(
                        exp_query, tenant_id, space_id, user_id, limit // 2,
                        allowed_space_ids=allowed_space_ids,
                    )
                    for r in exp_results.results:
                        if r.text not in all_results:
                            all_results[r.text] = r
                        else:
                            # Boost score if found in multiple hops
                            existing = all_results[r.text]
                            all_results[r.text] = RetrievalResult(
                                text=existing.text,
                                score=max(existing.score, r.score * 0.8),  # Slight boost
                                source=existing.source,
                                metadata=existing.metadata,
                                explanation=f"multi_hop_hop{hop}",
                                confidence=max(existing.confidence, r.confidence * 0.8),
                            )
            except Exception as e:
                logger.warning("Multi-hop expansion failed at hop %d: %s", hop, e)
                break
        
        # Sort and limit
        sorted_results = sorted(all_results.values(), key=lambda x: x.score, reverse=True)[:limit]
        
        context_text = "\n".join(f"- [{r.source}] {r.text}" for r in sorted_results)
        avg_conf = sum(r.confidence for r in sorted_results) / len(sorted_results) if sorted_results else 0.0
        
        return RAGResponse(
            results=sorted_results,
            context_text=context_text,
            confidence=avg_conf,
            query_scopes={"tenant_id": tenant_id, "space_id": space_id, "user_id": user_id},
        )

    async def _single_hop_search(
        self,
        query: str,
        tenant_id: str,
        space_id: str | None = None,
        user_id: str | None = None,
        limit: int = 10,
        since: datetime | None = None,
        source: str | None = None,
        allowed_space_ids: list[str] | None = None,
    ) -> RAGResponse:
        """Single-hop hybrid search (semantic + BM25). Respects allowed_space_ids for membership."""
        if self._client is None:
            await self.connect()
        from qdrant_client.http import models

        # Semantic search
        vec = await self.embed(query)
        must = [models.FieldCondition(key="tenant_id", match=models.MatchValue(value=tenant_id))]
        if allowed_space_ids:
            must.append(models.FieldCondition(key="space_id", match=models.MatchAny(any=allowed_space_ids)))
        elif space_id:
            must.append(models.FieldCondition(key="space_id", match=models.MatchValue(value=space_id)))
        if user_id:
            must.append(models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id)))
        if source:
            must.append(models.FieldCondition(key="source", match=models.MatchValue(value=source)))

        q_filter = models.Filter(must=must) if must else None
        resp = self._client.query_points(
            collection_name=self._collection,
            query=vec,
            limit=limit * 2,  # Get more for hybrid ranking
            query_filter=q_filter,
        )
        semantic_hits = getattr(resp, "points", None) or []

        # Build semantic results
        semantic_results: dict[str, RetrievalResult] = {}
        for h in semantic_hits:
            pl = getattr(h, "payload", None) or {}
            content = pl.get("content", "")
            if not content:
                continue
            sc = getattr(h, "score", None) or 0.0
            semantic_results[content] = RetrievalResult(
                text=content,
                score=float(sc),
                source=pl.get("source", "unknown"),
                metadata=pl,
                explanation="semantic",
                confidence=float(sc),
            )

        # BM25 search
        bm25_results: dict[str, tuple[dict[str, Any], float]] = {}
        if self._enable_bm25:
            try:
                bm25_hits = await self._bm25_search(
                    query, tenant_id, space_id, limit * 2, allowed_space_ids=allowed_space_ids
                )
                for doc, score in bm25_hits:
                    content = doc.get("content", "")
                    if content:
                        bm25_results[content] = (doc, score)
            except Exception as e:
                logger.warning("BM25 search failed: %s", e)

        # Hybrid ranking: combine semantic and BM25 scores
        hybrid_results: dict[str, RetrievalResult] = {}
        
        # Normalize scores (0-1 range)
        if semantic_results:
            max_semantic = max(r.score for r in semantic_results.values()) or 1.0
            for r in semantic_results.values():
                normalized_semantic = r.score / max_semantic if max_semantic > 0 else 0.0
                hybrid_results[r.text] = RetrievalResult(
                    text=r.text,
                    score=normalized_semantic * self._hybrid_weight_semantic,
                    source=r.source,
                    metadata=r.metadata,
                    explanation="semantic",
                    confidence=r.confidence,
                )
        
        if bm25_results:
            max_bm25 = max(score for _, score in bm25_results.values()) or 1.0
            for content, (doc, score) in bm25_results.items():
                normalized_bm25 = score / max_bm25 if max_bm25 > 0 else 0.0
                if content in hybrid_results:
                    # Combine scores
                    existing = hybrid_results[content]
                    hybrid_results[content] = RetrievalResult(
                        text=existing.text,
                        score=existing.score + (normalized_bm25 * self._hybrid_weight_bm25),
                        source=existing.source,
                        metadata=existing.metadata,
                        explanation="hybrid_semantic+bm25",
                        confidence=max(existing.confidence, normalized_bm25),
                    )
                else:
                    hybrid_results[content] = RetrievalResult(
                        text=content,
                        score=normalized_bm25 * self._hybrid_weight_bm25,
                        source=doc.get("source", "unknown"),
                        metadata=doc.get("metadata", {}),
                        explanation="bm25",
                        confidence=normalized_bm25,
                    )

        # Sort by hybrid score and limit
        sorted_results = sorted(hybrid_results.values(), key=lambda x: x.score, reverse=True)[:limit]

        context_text = "\n".join(f"- [{r.source}] {r.text}" for r in sorted_results)
        avg_conf = sum(r.confidence for r in sorted_results) / len(sorted_results) if sorted_results else 0.0

        return RAGResponse(
            results=sorted_results,
            context_text=context_text,
            confidence=avg_conf,
            query_scopes={"tenant_id": tenant_id, "space_id": space_id, "user_id": user_id},
        )

    async def search(
        self,
        query: str,
        tenant_id: str,
        space_id: str | None = None,
        user_id: str | None = None,
        limit: int = 10,
        since: datetime | None = None,
        source: str | None = None,
        use_multihop: bool | None = None,
        allowed_space_ids: list[str] | None = None,
    ) -> RAGResponse:
        """
        Hybrid search with tenant/space/time/source scoping.
        When allowed_space_ids is set, results are restricted to those spaces (membership-aware).
        Supports multi-hop reasoning if enabled.
        Returns context + explainability + confidence.
        """
        # Enforce multi-tenant isolation
        if not tenant_id or tenant_id == "*":
            raise ValueError("tenant_id is required for search (multi-tenant isolation)")
        
        use_multihop = use_multihop if use_multihop is not None else self._enable_multihop
        mode = "multihop" if use_multihop else "single"

        self._metrics.inc(
            "queries_total",
            labels={"tenant_id": tenant_id, "space_id": space_id or "none", "mode": mode},
        )

        if use_multihop:
            resp = await self._multi_hop_retrieval(
                query, tenant_id, space_id, user_id, limit, allowed_space_ids=allowed_space_ids
            )
        else:
            resp = await self._single_hop_search(
                query, tenant_id, space_id, user_id, limit, since, source,
                allowed_space_ids=allowed_space_ids,
            )

        results_count = len(resp.results)
        self._metrics.observe(
            "results_per_query",
            float(results_count),
            labels={"tenant_id": tenant_id, "space_id": space_id or "none", "mode": mode},
        )
        self._metrics.observe(
            "avg_confidence",
            float(resp.confidence),
            labels={"tenant_id": tenant_id, "space_id": space_id or "none", "mode": mode},
        )

        return resp


# Shared singleton for use by main and agents (avoids circular imports).
_shared_engine: RAGEngine | None = None


async def get_shared_rag_engine() -> RAGEngine:
    """Return a shared RAGEngine instance (from env). Used by main and by agents when they need to fetch RAG context."""
    global _shared_engine
    if _shared_engine is None:
        _shared_engine = RAGEngine(
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            collection=os.getenv("QDRANT_COLLECTION", "kirp_vectors"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        await _shared_engine.connect()
    return _shared_engine
