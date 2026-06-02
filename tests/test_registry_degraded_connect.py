from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_rag_engine_degraded_on_connect_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "development")
    from src.core.registry import ServiceRegistry

    reg = ServiceRegistry()
    reg._rag_engine = None
    with patch("src.core.rag_engine.RAGEngine.connect", new=AsyncMock(side_effect=RuntimeError("qdrant down"))):
        rag = await reg.get_rag_engine()
    assert rag is not None


@pytest.mark.asyncio
async def test_get_schema_engine_degraded_on_connect_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "development")
    from src.core.registry import ServiceRegistry

    reg = ServiceRegistry()
    reg._schema_engine = None
    with patch("src.core.schema_engine.SchemaEngine.connect", new=AsyncMock(side_effect=RuntimeError("postgres down"))):
        schema = await reg.get_schema_engine()
    assert schema is not None
