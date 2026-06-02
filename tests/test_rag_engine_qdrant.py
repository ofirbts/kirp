from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.rag_engine import RAGEngine, _qdrant_timeout_sec


def test_qdrant_timeout_sec_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KIRP_QDRANT_TIMEOUT_SEC", raising=False)
    assert _qdrant_timeout_sec() == 15.0


def test_qdrant_timeout_sec_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KIRP_QDRANT_TIMEOUT_SEC", "8")
    assert _qdrant_timeout_sec() == 8.0


@pytest.mark.asyncio
async def test_connect_requests_payload_indexes_without_wait() -> None:
    engine = RAGEngine(qdrant_url="http://localhost:6333")
    mock_client = MagicMock()
    mock_client.get_collections.return_value.collections = [MagicMock(name="kirp_vectors")]

    with patch("qdrant_client.QdrantClient", return_value=mock_client), patch(
        "src.core.embedding_provider.get_embedder",
        return_value=object(),
    ):
        await engine.connect()

    assert mock_client.create_payload_index.call_count == 3
    for call in mock_client.create_payload_index.call_args_list:
        assert call.kwargs.get("wait") is False


@pytest.mark.asyncio
async def test_upsert_uses_non_blocking_wait() -> None:
    engine = RAGEngine(qdrant_url="http://localhost:6333")
    mock_client = MagicMock()
    engine._client = mock_client
    engine._embedder = object()

    await engine.upsert(
        points=[{"id": "p1", "embedding": [0.1, 0.2], "content": "hello"}],
        tenant_id="tenant_a",
        space_id="all",
    )

    mock_client.upsert.assert_called_once()
    assert mock_client.upsert.call_args.kwargs.get("wait") is False


@pytest.mark.asyncio
async def test_upsert_timeout_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = RAGEngine(qdrant_url="http://localhost:6333")
    engine._client = MagicMock()
    engine._embedder = object()

    def slow_upsert(*_args: object, **_kwargs: object) -> None:
        import time

        time.sleep(0.2)

    engine._upsert_sync = slow_upsert  # type: ignore[method-assign]
    monkeypatch.setattr("src.core.rag_engine._qdrant_timeout_sec", lambda: 0.05)

    with pytest.raises(TimeoutError, match="timed out"):
        await engine.upsert(
            points=[{"id": "p1", "embedding": [0.1], "content": "x"}],
            tenant_id="tenant_a",
            space_id="all",
        )
