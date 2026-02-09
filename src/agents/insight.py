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
from src.core.llm_client import get_llm

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

    async def ask(
        self,
        tenant_id: str,
        space_id: str,
        query: str,
    ) -> InsightAnswer:
        """
        Run a scoped RAG query and turn it into an insight answer.

        The agent does NOT call external web search; it only uses the user's data
        and the existing RAG indexes.
        """
        logger.info("InsightAgent.ask start tenant=%s space=%s", tenant_id, space_id)

        # Reuse existing RAG behavior (semantic search + context building).
        # Do NOT over‑filter by user_id so we see all knowledge for this tenant/space.
        resp: RAGResponse = await self._rag.search(  # type: ignore[assignment]
            query=query,
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=None,
            limit=10,
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

        # If no internal sources at all, fall back immediately.
        if not resp.results:
            answer = (
                "I could not find anything in your current data that directly answers this. "
                "Try adding more knowledge or syncing Notion."
            )
            return InsightAnswer(answer=answer, sources=sources, needs_external_info=True)

        # Summarize with LLM over the retrieved context.
        llm = get_llm()
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

