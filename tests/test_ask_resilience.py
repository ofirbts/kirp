from __future__ import annotations

import asyncio
from types import SimpleNamespace

import src.main as main_mod


class _DummyReq:
    def __init__(self, query: str) -> None:
        self.query = query


class _DummyRag:
    pass


def test_ask_returns_fallback_payload_on_unexpected_failure(monkeypatch) -> None:
    async def _fake_get_rag_engine():  # type: ignore[no-untyped-def]
        return _DummyRag()

    async def _broken_ask(self, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("forced failure")

    monkeypatch.setattr(main_mod, "get_rag_engine", _fake_get_rag_engine)
    monkeypatch.setattr("src.agents.insight.InsightAgent.ask", _broken_ask)

    out = asyncio.run(
        main_mod.ask(
            req=_DummyReq("What should I focus on?"),  # type: ignore[arg-type]
            _auth={"ok": True},
            user=SimpleNamespace(tenant_id="default", id="u1"),
        )
    )

    assert isinstance(out, dict)
    assert out.get("needs_external_info") is True
    assert "could not complete this insight" in str(out.get("answer", "")).lower()
