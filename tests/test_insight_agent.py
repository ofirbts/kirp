from __future__ import annotations

import asyncio

from src.agents.insight import InsightAgent


class _FailingRag:
    async def search(self, **kwargs):  # type: ignore[no-untyped-def]
        raise TimeoutError("qdrant timeout")


def test_insight_agent_returns_graceful_fallback_on_rag_failure() -> None:
    agent = InsightAgent(_FailingRag())  # type: ignore[arg-type]

    out = asyncio.run(
        agent.ask(
            tenant_id="default",
            space_id="all",
            query="What should I do next?",
            user_id="u1",
        )
    )

    assert out.needs_external_info is True
    assert out.sources == []
    assert "try again" in out.answer.lower() or "could not reach" in out.answer.lower()
