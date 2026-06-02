# src/agents/command_executor.py

from __future__ import annotations

from typing import Optional


class CommandExecutorAgent:
    """
    Modernized executor agent for KIRP.
    Executes approved events via the Execution Engine (Notion, WhatsApp, etc.) with audit.
    """

    async def process_task(self, event: dict) -> bool:
        """
        Processes a single approved event through the execution layer (audit + Notion task).
        Expected event structure:
        {
            "id": "...",
            "status": "approved",
            "tenant_id": "...",
            "user_id": "...",
            "data": { "task": "Some task title" }
        }
        """
        if not event:
            return False

        if event.get("status") != "approved":
            return False

        title = event.get("data", {}).get("task", "Untitled Task")
        trace_id = str(event.get("id", ""))
        tenant_id = event.get("tenant_id", "default")
        user_id = event.get("user_id", "system")

        try:
            from src.core.execution_engine import execute_command
            result = await execute_command(
                command_type="create_notion_task",
                payload={"title": title, "trace_id": trace_id, "source": "KIRP"},
                tenant_id=tenant_id,
                user_id=user_id,
                space_id=event.get("space_id", "all"),
            )
            return result.get("ok") is True
        except Exception:
            pass
        return False


# Spec used by meta-agent / agent registry
command_executor_spec = {
    "name": "command_executor",
    "description": "Executes approved commands (e.g., creating tasks)",
    "capabilities": ["task_execution", "event_processing"],
}
