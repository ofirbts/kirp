from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.execution_engine import CommandType, execute_command
from src.core.governance import GovernanceCheck


@pytest.mark.asyncio
async def test_execute_command_denied_before_side_effect() -> None:
    denied = GovernanceCheck(
        allowed=False,
        reason="policy_denied",
        requires_approval=False,
    )
    enforcement = MagicMock()
    enforcement.enforce = AsyncMock(return_value=denied)

    with patch("src.core.execution_engine._governance_enforcement", return_value=enforcement):
        with patch("src.integrations.notion.NotionIntegration") as notion_cls:
            result = await execute_command(
                CommandType.CREATE_NOTION_TASK,
                {"title": "x"},
                tenant_id="t1",
                user_id="u1",
            )

    assert result["ok"] is False
    assert result.get("governance_denied") is True
    notion_cls.assert_not_called()


@pytest.mark.asyncio
async def test_execute_command_skips_governance_when_approved() -> None:
    enforcement = MagicMock()
    enforcement.enforce = AsyncMock()

    with patch("src.core.execution_engine._governance_enforcement", return_value=enforcement):
        with patch("src.integrations.notion.NotionIntegration") as notion_cls:
            inst = MagicMock()
            inst.connect = MagicMock()
            inst.create_task = AsyncMock(return_value={"ok": True})
            notion_cls.return_value = inst
            mock_store = MagicMock()
            mock_store.connect = AsyncMock()
            mock_store.ingest = AsyncMock()
            with patch("src.core.event_store.EventStore", return_value=mock_store):
                result = await execute_command(
                    CommandType.CREATE_NOTION_TASK,
                    {"title": "x"},
                    tenant_id="t1",
                    user_id="u1",
                    governance_approved=True,
                )

    enforcement.enforce.assert_not_called()
    assert result.get("governance_denied") is not True


@pytest.mark.asyncio
async def test_high_risk_commands_require_approval_by_default() -> None:
    from src.api.v1_execute import ExecuteRequest
    from src.core.execution_engine import HIGH_RISK_COMMANDS

    assert CommandType.SEND_WHATSAPP in HIGH_RISK_COMMANDS
    req = ExecuteRequest(command_type="send_whatsapp", payload={"to": "+1", "text": "hi"})
    assert req.require_approval is False
    require_approval = req.require_approval or CommandType(req.command_type) in HIGH_RISK_COMMANDS
    assert require_approval is True
