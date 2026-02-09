"""ExecutionAgent — Executes queued actions from AgentActionsStore."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from src.core.agents.base import BaseAgent
from src.core.agent_actions import get_agent_actions_store, ACTION_CREATE_TASK, ACTION_UPDATE_TASK, ACTION_CREATE_COMMITMENT, ACTION_SEND_NOTIFICATION, ACTION_SEND_MESSAGE, ACTION_UPDATE_PROJECT

logger = logging.getLogger(__name__)


class ExecutionAgent(BaseAgent):
    name = "ExecutionAgent"
    description = "Executes queued actions: create_task, update_task, send_notification, send_message, update_project."
    triggers = ["scheduled", "manual", "after_agent"]

    async def run(self, tenant_id: str, space_id: str, user_id: str = "system", context: dict[str, Any] | None = None) -> dict[str, Any]:
        store = get_agent_actions_store()
        await store.connect()
        pending = await store.get_pending(tenant_id=tenant_id, limit=50)
        executed = failed = 0
        errors: list[str] = []
        for act in pending:
            try:
                ok = await self._execute_one(act, tenant_id, space_id, user_id)
                if ok:
                    await store.mark_executed(act["id"])
                    executed += 1
                else:
                    await store.mark_failed(act["id"], "execute returned False")
                    failed += 1
            except Exception as e:
                await store.mark_failed(act["id"], str(e))
                failed += 1
                errors.append(str(e)[:80])
        return {"ok": True, "actions": [], "insights": [{"title": "Execution", "body": f"Executed: {executed}, Failed: {failed}.", "data": {"executed": executed, "failed": failed, "errors": errors[:10]}}]}

    async def _execute_one(self, act: dict[str, Any], tenant_id: str, space_id: str, user_id: str) -> bool:
        from src.core.schema_engine import get_schema_engine
        from src.models.schema import SchemaEntity
        from src.main import get_event_store
        from uuid import uuid4

        schema = await get_schema_engine()
        event_store = await get_event_store()
        atype = act.get("type", "")
        payload = act.get("payload", {})
        if atype == ACTION_CREATE_TASK:
            due = payload.get("due_date")
            due_dt = datetime.fromisoformat(due.replace("Z", "+00:00")) if isinstance(due, str) else None
            await schema.upsert_node(tenant_id=tenant_id, space_id=space_id, entity=SchemaEntity.TASK, title=payload.get("title", "Task"), due_date=due_dt, status=payload.get("status"), metadata={"user_id": user_id})
            return True
        if atype == ACTION_UPDATE_TASK:
            node_id = payload.get("node_id")
            if not node_id:
                return False
            due = payload.get("due_date")
            due_dt = datetime.fromisoformat(due.replace("Z", "+00:00")) if due else None
            await schema.update_node(node_id, tenant_id, title=payload.get("title"), status=payload.get("status"), due_date=due_dt)
            return True
        if atype == ACTION_CREATE_COMMITMENT:
            due = payload.get("due_date")
            due_dt = datetime.fromisoformat(due.replace("Z", "+00:00")) if isinstance(due, str) else None
            await schema.upsert_node(tenant_id=tenant_id, space_id=space_id, entity=SchemaEntity.COMMITMENT, title=payload.get("title", "Commitment"), due_date=due_dt, status=payload.get("status"), metadata={"user_id": user_id})
            return True
        if atype == ACTION_SEND_NOTIFICATION:
            from src.core.event_store import Event
            ev = Event(id=uuid4(), tenant_id=tenant_id, space_id=space_id, user_id=user_id, source="execution_agent", content=payload.get("body", payload.get("title", "Notification")), metadata=payload.get("metadata", {}), event_type="notification")
            await event_store.ingest(ev)
            return True
        if atype == ACTION_SEND_MESSAGE:
            from src.core.execution_engine import execute_command
            r = await execute_command("send_whatsapp" if payload.get("channel") == "whatsapp" else "send_email", payload, tenant_id, user_id, space_id, event_store)
            return r.get("ok") is True
        if atype == ACTION_UPDATE_PROJECT:
            node_id = payload.get("node_id")
            if not node_id:
                return False
            await schema.update_node(node_id, tenant_id, title=payload.get("title"), description=payload.get("description"))
            return True
        return False
