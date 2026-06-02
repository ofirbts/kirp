from __future__ import annotations

import pytest

from src.core.registry import _allow_degraded_dependency_connect


def test_allow_degraded_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "development")
    assert _allow_degraded_dependency_connect() is True


def test_allow_degraded_in_test(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "test")
    assert _allow_degraded_dependency_connect() is True


def test_production_requires_explicit_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("KIRP_ALLOW_DEGRADED_DEPS", raising=False)
    assert _allow_degraded_dependency_connect() is False


def test_production_allows_with_env_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("KIRP_ALLOW_DEGRADED_DEPS", "1")
    assert _allow_degraded_dependency_connect() is True
