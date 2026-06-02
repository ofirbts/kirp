from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_dev_user_seed_skipped_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    with patch("src.core.auth.get_user_store") as get_store:
        from src.main import _seed_dev_user_if_needed

        await _seed_dev_user_if_needed()
        get_store.assert_not_called()
