from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_skip(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "1")
    monkeypatch.setenv("ENV", "development")
    from src.main import app

    return TestClient(app)


@pytest.fixture
def client_no_skip(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKIP_AUTH", "0")
    monkeypatch.setenv("ENV", "test")
    from src.main import app

    return TestClient(app)
