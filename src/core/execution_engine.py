"""
Execution Layer — Run outbound actions: Notion task, WhatsApp, Calendar event, Email, Slack.

Every execution is audited via EventStore (event_type=execution). Optional approval workflow.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CommandType(str, Enum):
    CREATE_NOTION_TASK = "create_notion_task"
    UPDATE_NOTION_TASK = "update_notion_task"
    SEND_WHATSAPP = "send_whatsapp"
    CREATE_CALENDAR_EVENT = "create_calendar_event"
    SEND_EMAIL = "send_email"
    POST_SLACK = "post_slack"


async def execute_command(
    command_type: str | CommandType,
    payload: dict[str, Any],
    tenant_id: str,
    user_id: str,
    space_id: str = "all",
    event_store: Any = None,
) -> dict[str, Any]:
    """
    Execute a single command. Audits to EventStore (event_type=execution).
    Returns { ok, result?, error? }.
    """
    cmd = CommandType(command_type) if isinstance(command_type, str) else command_type
    result: dict[str, Any] = {"ok": False}
    try:
        if cmd == CommandType.CREATE_NOTION_TASK:
            from src.integrations.notion import NotionIntegration
            notion = NotionIntegration()
            notion.connect()
            title = payload.get("title", "Untitled")
            trace_id = payload.get("trace_id", str(uuid4()))
            result = await notion.create_task(title=title, trace_id=trace_id, source=payload.get("source", "KIRP"))

        elif cmd == CommandType.UPDATE_NOTION_TASK:
            from src.integrations.notion import NotionIntegration
            from src.core.schema_engine import get_schema_engine
            node_id = payload.get("node_id")
            if not node_id:
                result = {"ok": False, "error": "missing 'node_id'"}
            else:
                schema = await get_schema_engine()
                node = await schema.get_node(node_id, tenant_id)
                if not node:
                    result = {"ok": False, "error": f"node not found: {node_id}"}
                else:
                    meta = node.get("metadata") or node.get("extra") or {}
                    page_id = meta.get("notion_page_id")
                    if not page_id:
                        result = {"ok": False, "error": "node has no notion_page_id (not from Notion)"}
                    else:
                        notion = NotionIntegration()
                        notion.connect()
                        result = await notion.update_page(
                            page_id=page_id,
                            title=payload.get("title"),
                            status=payload.get("status"),
                            due_date=payload.get("due_date"),
                        )

        elif cmd == CommandType.SEND_WHATSAPP:
            from src.integrations.whatsapp import WhatsAppIntegration
            wa = WhatsAppIntegration()
            wa.connect()
            to = payload.get("to") or payload.get("to_number")
            text = payload.get("text", "")
            if not to:
                result = {"ok": False, "error": "missing 'to' or 'to_number'"}
            else:
                result = await wa.send_message(to=to, text=text, user_id=user_id)

        elif cmd == CommandType.CREATE_CALENDAR_EVENT:
            from src.integrations.calendar import CalendarIntegration
            cal = CalendarIntegration()
            cal.connect()
            calendar_id = payload.get("calendar_id", "primary")
            summary = payload.get("summary", "Event")
            start_s = payload.get("start")
            end_s = payload.get("end")
            if not start_s or not end_s:
                result = {"ok": False, "error": "missing 'start' and 'end' (ISO datetime)"}
            else:
                start_dt = datetime.fromisoformat(start_s.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end_s.replace("Z", "+00:00"))
                result = await cal.create_event(
                    calendar_id=calendar_id,
                    summary=summary,
                    start=start_dt,
                    end=end_dt,
                    user_id=user_id,
                )

        elif cmd == CommandType.SEND_EMAIL:
            from src.integrations.email import EmailIntegration
            email = EmailIntegration()
            to = payload.get("to")
            subject = payload.get("subject", "")
            body = payload.get("body", "")
            if not to:
                result = {"ok": False, "error": "missing 'to'"}
            else:
                result = await email.send(to=to, subject=subject, body=body, user_id=user_id)

        elif cmd == CommandType.POST_SLACK:
            from src.integrations.slack import SlackIntegration
            slack = SlackIntegration()
            slack.connect()
            channel = payload.get("channel")
            text = payload.get("text", "")
            if not channel:
                result = {"ok": False, "error": "missing 'channel'"}
            else:
                result = await slack.post_message(channel=channel, text=text, user_id=user_id)

        else:
            result = {"ok": False, "error": f"unknown command type: {cmd}"}
    except Exception as e:
        logger.exception("Execution failed: %s", e)
        result = {"ok": False, "error": str(e)}

    # Audit: store execution event in EventStore
    try:
        if event_store is None:
            import os
            from src.core.event_store import EventStore, Event
            event_store = EventStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
            await event_store.connect()
        ev = Event(
            id=uuid4(),
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            source="execution_engine",
            content=f"{cmd.value}: {result.get('ok', False)}",
            metadata={
                "command_type": cmd.value,
                "payload": payload,
                "result": result,
                "trace_id": payload.get("trace_id"),
            },
            event_type="execution",
        )
        await event_store.ingest(ev)
    except Exception as audit_err:
        logger.warning("Execution audit log failed: %s", audit_err)

    return result
