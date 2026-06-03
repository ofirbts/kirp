from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_embedder: Any = None
_provider: str | None = None
_model: str | None = None


class _OpenAIEmbedder:
    def __init__(self, model: str) -> None:
        from openai import AsyncOpenAI

        self._model = model
        self._client = AsyncOpenAI()

    async def aembed_query(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(input=text, model=self._model)
        return list(response.data[0].embedding)


def _init_embedder(provider: str, model: str) -> Any:
    if provider == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            return None
        return _OpenAIEmbedder(model=model)
    if provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            return None
        return GoogleGenerativeAIEmbeddings(
            model=model or "models/text-embedding-004",
            google_api_key=api_key,
        )
    return None


def get_embedder(
    *,
    provider: str | None = None,
    model: str | None = None,
) -> Any:
    global _embedder, _provider, _model
    prov = (provider or os.getenv("EMBEDDING_PROVIDER", "openai")).strip()
    mdl = (model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")).strip()
    if _embedder is not None and _provider == prov and _model == mdl:
        return _embedder
    _embedder = _init_embedder(prov, mdl)
    _provider = prov
    _model = mdl
    return _embedder


async def embed_text(
    text: str,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> list[float]:
    embedder = get_embedder(provider=provider, model=model)
    if embedder is None:
        raise ValueError("Embedding provider not configured")
    emb = await embedder.aembed_query(text)
    if not emb:
        raise ValueError("Embedding generation returned empty result")
    return emb


def embedding_provider_name() -> str:
    return (os.getenv("EMBEDDING_PROVIDER") or "openai").strip().lower()


def embedding_model_name() -> str:
    return (os.getenv("EMBEDDING_MODEL") or "text-embedding-3-small").strip()
