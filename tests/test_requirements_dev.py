from pathlib import Path


def test_requirements_dev_includes_pytest_asyncio() -> None:
    text = Path("requirements-dev.txt").read_text(encoding="utf-8")
    assert "pytest-asyncio" in text


def test_pytest_asyncio_plugin_importable() -> None:
    import pytest_asyncio

    assert pytest_asyncio is not None
