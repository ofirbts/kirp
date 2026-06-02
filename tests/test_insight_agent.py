from __future__ import annotations

import asyncio
from types import SimpleNamespace

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


class _EmptyRag:
    async def search(self, **kwargs):  # type: ignore[no-untyped-def]
        return SimpleNamespace(results=[], confidence=0.0, context_text="")


class _FakeEventStore:
    async def list(self, **kwargs):  # type: ignore[no-untyped-def]
        return [
            SimpleNamespace(
                content="Met Daniel and discussed launch priorities for next week",
                source="dashboard",
                metadata={"kind": "note"},
            )
        ]


def test_insight_agent_uses_event_store_when_rag_is_empty(monkeypatch) -> None:
    async def _fake_get_event_store():  # type: ignore[no-untyped-def]
        return _FakeEventStore()

    monkeypatch.setattr("src.main.get_event_store", _fake_get_event_store)

    agent = InsightAgent(_EmptyRag())  # type: ignore[arg-type]
    out = asyncio.run(
        agent.ask(
            tenant_id="default",
            space_id="all",
            query="What do I know about Daniel?",
            user_id="u1",
        )
    )

    assert out.needs_external_info is False
    assert len(out.sources) == 1
    assert "recent activity" in out.answer.lower()


def test_insight_agent_uses_event_store_when_rag_raises(monkeypatch) -> None:
    async def _fake_get_event_store():  # type: ignore[no-untyped-def]
        return _FakeEventStore()

    monkeypatch.setattr("src.main.get_event_store", _fake_get_event_store)

    agent = InsightAgent(_FailingRag())  # type: ignore[arg-type]
    out = asyncio.run(
        agent.ask(
            tenant_id="default",
            space_id="all",
            query="What changed recently?",
            user_id="u1",
        )
    )

    assert out.needs_external_info is False
    assert len(out.sources) == 1
    assert "not yet indexed" in out.answer.lower()
