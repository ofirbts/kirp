from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.whatsapp_outbound import enqueue_whatsapp_outbound


@pytest.mark.asyncio
async def test_enqueue_whatsapp_no_direct_integration() -> None:
    store = MagicMock()
    store.connect = AsyncMock()
    store.add_or_get_pending = AsyncMock(return_value=("p-1", False))
    store.count_pending = AsyncMock(return_value=1)

    with patch("src.core.whatsapp_outbound._pending_store", return_value=store):
        with patch("src.integrations.whatsapp.WhatsAppIntegration") as wa_cls:
            result = await enqueue_whatsapp_outbound(
                "t1", "u1", "all", "+1", "hello", idempotency_key="k1"
            )

    assert result["ok"] is True
    assert result["pending_id"] == "p-1"
    wa_cls.assert_not_called()
