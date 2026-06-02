from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import src.core.embedding_provider as ep


@pytest.fixture(autouse=True)
def reset_embedder_cache() -> None:
    ep._embedder = None
    ep._provider = None
    ep._model = None
    yield
    ep._embedder = None
    ep._provider = None
    ep._model = None


def test_get_embedder_openai_none_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert ep.get_embedder(provider="openai") is None


def test_get_embedder_openai_instantiates_without_langchain_proxies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    embedder = ep.get_embedder(provider="openai", model="text-embedding-3-small")
    assert embedder is not None
    assert isinstance(embedder, ep._OpenAIEmbedder)


@pytest.mark.asyncio
async def test_embed_text_openai_returns_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    with patch("openai.AsyncOpenAI", return_value=mock_client):
        ep._embedder = None
        result = await ep.embed_text("hello", provider="openai", model="text-embedding-3-small")
    assert result == [0.1, 0.2, 0.3]
    mock_client.embeddings.create.assert_awaited_once_with(
        input="hello",
        model="text-embedding-3-small",
    )


@pytest.mark.asyncio
async def test_embed_text_raises_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="not configured"):
        await ep.embed_text("hello", provider="openai")
