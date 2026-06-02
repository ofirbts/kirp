from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.m3.governance import enqueue_m3_whatsapp_escalation


@pytest.mark.asyncio
async def test_enqueue_m3_escalation_no_direct_whatsapp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("M3_ESCALATION_PHONE", "+15551234567")
    with patch(
        "src.core.whatsapp_outbound.enqueue_whatsapp_outbound",
        new_callable=AsyncMock,
    ) as enqueue:
        enqueue.return_value = {
            "ok": True,
            "pending_id": "pending-abc",
            "queued": True,
            "duplicate": False,
        }
        with patch("src.integrations.whatsapp.WhatsAppIntegration") as wa_cls:
            result = await enqueue_m3_whatsapp_escalation(
                tenant_id="t1",
                space_id="all",
                user_id="u1",
                event_type="m3.reflection",
                reason="high_entropy",
                identity_entropy_score=0.72,
                resource_type="m3.reflection",
                trace_id="tr-m3-1",
            )

    assert result["ok"] is True
    assert result["pending_id"] == "pending-abc"
    assert result.get("queued") is True
    wa_cls.assert_not_called()
    enqueue.assert_awaited_once()
    call_kw = enqueue.await_args.kwargs
    assert call_kw["tenant_id"] == "t1"
    assert call_kw["idempotency_key"] == "tr-m3-1"
    assert call_kw["extra_payload"]["m3_escalation"] is True
    assert "+15551234567" == call_kw["to"]


@pytest.mark.asyncio
async def test_enqueue_m3_escalation_no_phone_skips_pending() -> None:
    with patch("src.core.whatsapp_outbound.enqueue_whatsapp_outbound", new_callable=AsyncMock) as enqueue:
        with patch("src.modules.m3.governance._resolve_m3_escalation_phone", return_value=None):
            result = await enqueue_m3_whatsapp_escalation(
                tenant_id="t1",
                space_id="all",
                user_id="u1",
                event_type="m3.reflection",
                reason="x",
                identity_entropy_score=0.8,
            )

    assert result["ok"] is False
    assert result.get("reason") == "no_phone_configured"
    enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_pending_m3_sends_whatsapp() -> None:
    from src.core.execution_engine import CommandType, execute_command

    enforcement = MagicMock()
    enforcement.enforce = AsyncMock()

    with patch("src.core.execution_engine._governance_enforcement", return_value=enforcement):
        with patch("src.integrations.whatsapp.WhatsAppIntegration") as wa_cls:
            inst = MagicMock()
            inst.connect = MagicMock()
            inst.send_message = AsyncMock(return_value={"ok": True})
            wa_cls.return_value = inst
            mock_store = MagicMock()
            mock_store.connect = AsyncMock()
            mock_store.ingest = AsyncMock()
            with patch("src.core.event_store.EventStore", return_value=mock_store):
                result = await execute_command(
                    CommandType.SEND_WHATSAPP,
                    {"to": "+1", "text": "M3 Identity: test", "m3_escalation": True},
                    tenant_id="t1",
                    user_id="u1",
                    governance_approved=True,
                )

    assert result["ok"] is True
    enforcement.enforce.assert_not_called()
    inst.send_message.assert_awaited_once()
