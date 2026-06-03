from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.reminder_agent import _deliver_reminder
from src.api.whatsapp_os import _queue_inbound_reply


@pytest.mark.asyncio
async def test_reminder_whatsapp_uses_governed_outbound() -> None:
    with patch(
        "src.core.whatsapp_outbound.enqueue_and_dispatch_whatsapp",
        new_callable=AsyncMock,
    ) as dispatch:
        dispatch.return_value = {
            "ok": True,
            "queued": True,
            "dispatched": True,
            "dispatch_result": {"ok": True},
        }
        with patch("src.integrations.whatsapp.WhatsAppIntegration") as wa_cls:
            ok = await _deliver_reminder(
                "whatsapp",
                "+15550001",
                "Task A",
                "2026-06-02T12:00:00Z",
                "t1",
                "u1",
                "node-1",
            )
    assert ok is True
    wa_cls.assert_not_called()
    dispatch.assert_awaited_once()


@pytest.mark.asyncio
async def test_whatsapp_os_inbound_reply_no_direct_send() -> None:
    with patch(
        "src.core.whatsapp_outbound.enqueue_and_dispatch_whatsapp",
        new_callable=AsyncMock,
    ) as dispatch:
        dispatch.return_value = {
            "ok": True,
            "queued": True,
            "dispatched": True,
            "pending_id": "p-1",
        }
        with patch("src.integrations.whatsapp.WhatsAppIntegration") as wa_cls:
            result = await _queue_inbound_reply(
                "t1", "all", "u1", "+15550002", "hello", "conversational"
            )
    assert result["ok"] is True
    assert result.get("dispatched") is True
    wa_cls.assert_not_called()
    dispatch.assert_awaited_once()
    assert dispatch.await_args.kwargs["source"] == "whatsapp_os_conversational"


@pytest.mark.asyncio
async def test_dispatch_pending_whatsapp_executes_approved() -> None:
    from src.core.whatsapp_outbound import dispatch_pending_whatsapp

    store = MagicMock()
    store.connect = AsyncMock()
    store.get = AsyncMock(
        return_value={
            "id": "p-9",
            "tenant_id": "t1",
            "user_id": "u1",
            "space_id": "all",
            "command_type": "send_whatsapp",
            "payload": {"to": "+1", "text": "hi"},
            "status": "pending",
        }
    )
    store.set_status = AsyncMock(return_value=True)

    with patch("src.core.whatsapp_outbound._pending_store", return_value=store):
        with patch(
            "src.core.execution_engine.execute_command",
            new_callable=AsyncMock,
            return_value={"ok": True},
        ) as execute:
            result = await dispatch_pending_whatsapp("p-9", "t1", "u1", "all")

    assert result["ok"] is True
    execute.assert_awaited_once()
    assert execute.await_args.kwargs["governance_approved"] is True
    store.set_status.assert_awaited_once()
