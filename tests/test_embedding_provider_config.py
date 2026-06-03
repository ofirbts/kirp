from __future__ import annotations

import pytest

from src.core.embedding_provider import embedding_model_name, embedding_provider_name


def test_embedding_provider_name_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
    assert embedding_provider_name() == "openai"


def test_embedding_provider_name_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "Gemini")
    assert embedding_provider_name() == "gemini"


def test_embedding_model_name_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
    assert "embedding" in embedding_model_name()
