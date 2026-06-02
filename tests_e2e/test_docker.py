"""E2E: Dockerfile.brand_os_api exists; validate structure (no actual docker build)."""
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DOCKERFILE = REPO / "Dockerfile.brand_os_api"


def test_dockerfile_exists() -> None:
    assert DOCKERFILE.is_file()


def test_dockerfile_content() -> None:
    text = DOCKERFILE.read_text()
    assert "FROM" in text
    assert "python" in text.lower()
    assert "brand_os_v3" in text or "brand_os" in text
    assert "uvicorn" in text or "api.main" in text
    assert "EXPOSE" in text
