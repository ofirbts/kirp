"""
InsightAgent — Ask / Search / Insights over your own data.

Lightweight helper used by /api/v1/ask:
- Uses existing RAGEngine for semantic search over events/knowledge.
- Can be extended later to pull tasks and schema nodes explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import logging

from src.core.rag_engine import RAGEngine, RAGResponse
from src.core.llm_router import get_llm_for_task

logger = logging.getLogger(__name__)


@dataclass
class InsightAnswer:
    answer: str
    sources: list[dict[str, Any]]
    needs_external_info: bool


class InsightAgent:
    """Simple insight agent on top of RAGEngine."""

    def __init__(self, rag: RAGEngine) -> None:
        self._rag = rag

    async def _fallback_from_recent_events(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str | None,
    ) -> list[dict[str, Any]]:
        """Fallback context when vector index is empty but raw events exist."""
        try:
            from src.main import get_event_store

            store = await get_event_store()
            recent = await store.list(
                tenant_id=tenant_id,
                space_id=space_id,
                user_id=user_id,
                limit=8,
            )
        except Exception as e:
            logger.warning("InsightAgent.ask fallback event-store lookup failed: %s", e)
            return []

        out: list[dict[str, Any]] = []
        for ev in recent:
            text = (getattr(ev, "content", "") or "").strip()
            if not text:
                continue
            out.append(
                {
                    "text": text,
                    "score": None,
                    "source": getattr(ev, "source", "event_store"),
                    "metadata": getattr(ev, "metadata", {}) or {},
                    "explanation": "fallback_from_event_store",
                    "confidence": 0.55,
                }
            )
        return out

    async def ask(
        self,
        tenant_id: str,
        space_id: str,
        query: str,
        user_id: str | None = None,
    ) -> InsightAnswer:
        """
        Run a scoped RAG query and turn it into an insight answer.

        The agent does NOT call external web search; it only uses the user's data
        and the existing RAG indexes. Pass user_id for user-scoped retrieval when available.
        """
        logger.info("InsightAgent.ask start tenant=%s space=%s user=%s", tenant_id, space_id, user_id)

        # Reuse existing RAG behavior (semantic search + context building).
        # When user_id is provided (e.g. from JWT), use it for scoping; otherwise tenant/space only.
        try:
            resp: RAGResponse = await self._rag.search(  # type: ignore[assignment]
                query=query,
                tenant_id=tenant_id,
                space_id=space_id,
                user_id=user_id,
                limit=10,
            )
        except Exception as e:
            # Keep Ask stable when vector backend is temporarily unavailable.
            # Returning a graceful fallback avoids surfacing intermittent infra
            # timeouts as 500s in the UI.
            logger.warning("InsightAgent.ask RAG search failed: %s", e)
            fallback_sources = await self._fallback_from_recent_events(
                tenant_id=tenant_id,
                space_id=space_id,
                user_id=user_id,
            )
            if fallback_sources:
                bullets = "\n".join(f"- {s['text'][:220]}" for s in fallback_sources[:3])
                return InsightAnswer(
                    answer=(
                        "Based on recent activity (not yet indexed), I can already see:\n"
                        f"{bullets}\n\n"
                        "Indexed semantic search is temporarily unavailable."
                    ),
                    sources=fallback_sources,
                    needs_external_info=False,
                )
            return InsightAnswer(
                answer=(
                    "I could not reach your indexed knowledge right now. "
                    "Please try again in a moment."
                ),
                sources=[],
                needs_external_info=True,
            )

        logger.info(
            "InsightAgent.ask RAG results tenant=%s space=%s count=%d confidence=%.3f",
            tenant_id,
            space_id,
            len(resp.results),
            float(resp.confidence),
        )

        sources: list[dict[str, Any]] = []
        for r in resp.results:
            sources.append(
                {
                    "text": r.text,
                    "score": r.score,
                    "source": r.source,
                    "metadata": r.metadata,
                    "explanation": r.explanation,
                    "confidence": r.confidence,
                }
            )

        # If vector index has no hits, try recent raw events before giving up.
        if not resp.results:
            fallback_sources = await self._fallback_from_recent_events(
                tenant_id=tenant_id,
                space_id=space_id,
                user_id=user_id,
            )
            if fallback_sources:
                bullets = "\n".join(f"- {s['text'][:220]}" for s in fallback_sources[:3])
                answer = (
                    "I could not find indexed matches yet, but I can see recent activity in your data:\n"
                    f"{bullets}\n\n"
                    "This means ingestion likely arrived, but semantic indexing is still catching up."
                )
                return InsightAnswer(
                    answer=answer,
                    sources=fallback_sources,
                    needs_external_info=False,
                )

            answer = (
                "I could not find anything in your current data that directly answers this. "
                "Try adding more knowledge or syncing Notion."
            )
            return InsightAnswer(answer=answer, sources=sources, needs_external_info=True)

        # Summarize with LLM over the retrieved context (reasoning-grade).
        llm = get_llm_for_task("reasoning")
        context_snippets = "\n".join(
            f"- [{r.source}] {r.text}" for r in resp.results[:10] if r.text
        )

        system_prompt = (
            "You are the KIRP Insight Agent. You answer questions ONLY based on the provided "
            "context from the user's own data (events, tasks, schema nodes). "
            "Do NOT hallucinate facts that are not implied by the context. "
            "Answer clearly and naturally, in the same language as the question."
        )
        user_prompt = (
            f"Question:\n{query}\n\n"
            f"Context from the user's KIRP data:\n{context_snippets or '(no context)'}\n\n"
            "Answer the question concisely, based only on this context."
        )

        try:
            llm_answer = await llm.invoke(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=400,
            )
            answer = (llm_answer or "").strip()
        except Exception as e:
            logger.warning("InsightAgent.ask LLM failed: %s", e)
            # Fallback to context-only answer.
            answer = resp.context_text or "\n".join(
                r.text for r in resp.results[:3] if r.text
            )

        if not answer:
            answer = (
                "I found some related items in your data, but could not synthesize a clear answer yet."
            )

        # Heuristic: rely on RAG confidence to decide whether external info is needed.
        needs_external = bool(resp.confidence < 0.3)

        if needs_external:
            answer = (
                answer
                + "\n\nNote: This answer is based only on your current KIRP data. "
                "It may benefit from external information."
            )

        logger.info(
            "InsightAgent.ask done tenant=%s space=%s sources=%d needs_external=%s",
            tenant_id,
            space_id,
            len(sources),
            needs_external,
        )

        return InsightAnswer(
            answer=answer,
            sources=sources,
            needs_external_info=needs_external,
        )

